# check_theme_change.py
from qfluentwidgets import setTheme, Theme, qconfig
from PySide6.QtCore import QThread, Signal
from PySide6.QtCore import QTimer
import os
import subprocess
import sys
import darkdetect


class SystemThemeListener(QThread):
    """系统主题监听线程

    darkdetect.listener() 是阻塞调用，会一直运行监听系统主题变化，
    需要在单独的线程中运行。
    """
    systemThemeChanged = Signal(Theme)  # 系统主题变化信号
    initCompleted = Signal(bool)  # 初始化完成信号，参数表示是否支持

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._isSupported = False
        self._stopFlag = False
        self._proc = None

    def run(self):
        try:
            # darkdetect.listener() 是阻塞调用
            # 如果平台不支持会抛出 NotImplementedError
            # 如果支持则会一直阻塞运行
            self._isSupported = True
            self.initCompleted.emit(True)

            if sys.platform == "darwin":
                self._listenMac()
            else:
                # 这个调用会阻塞，直到线程被终止
                darkdetect.listener(self._onThemeChanged)
        except NotImplementedError as e:
            self._isSupported = False
            self.initCompleted.emit(False)
        except Exception as e:
            self._isSupported = False
            self.initCompleted.emit(False)

    def _listenMac(self):
        """macOS 上 darkdetect.listener 会另起监听子进程 主程序退出时不会跟着结束
        这里照它的方式自己启动子进程 停止时能一并结束"""
        if not darkdetect._mac_detect._can_listen:
            raise NotImplementedError()
        self._proc = subprocess.Popen(
            (sys.executable, "-c", "import _mac_detect as m; m._listen_child()"),
            stdout=subprocess.PIPE,
            universal_newlines=True,
            cwd=os.path.dirname(darkdetect._mac_detect.__file__),
        )
        for line in self._proc.stdout:
            self._onThemeChanged(line.strip())

    def _onThemeChanged(self, theme: str):
        """系统主题变化回调"""
        if self._stopFlag:
            return

        new_theme = Theme.DARK if theme.lower() == "dark" else Theme.LIGHT

        # 避免重复触发
        if new_theme == qconfig.theme:
            return

        self.systemThemeChanged.emit(new_theme)

    def stop(self):
        """停止监听线程"""
        self._stopFlag = True
        # macOS 结束监听子进程后 读取循环会自己结束
        if self._proc is not None and self._proc.poll() is None:
            self._proc.kill()
            self._proc.wait(1)
            self.wait(500)
        # darkdetect.listener 无法被中断，只能等待或强制终止
        if self.isRunning():
            self.terminate()  # 强制终止线程
            self.wait(500)  # 等待最多500ms


def checkThemeChange(self):
    """初始化系统主题监听

    在 MainWindow 中调用，self 是 MainWindow 实例
    """
    def handle_theme_change(theme):
        """根据程序是否最小化到托盘决定 lazy 参数：
        - 如果窗口不可见且托盘图标可见（认为已最小化到托盘），则立即应用主题（lazy=False）
        - 否则使用默认延迟应用（lazy=True）
        """
        is_minimized_to_tray = hasattr(self, 'tray_icon') and (not self.isVisible()) and self.tray_icon.isVisible()
        setTheme(theme, lazy=not is_minimized_to_tray)
        # 从 Light 主题切换至 Dark 主题时窗口背景无法正常切换
        # 解决方法 https://github.com/zhiyiYo/PyQt-Frameless-Window/issues/158
        QTimer.singleShot(500, lambda: self.setMicaEffectEnabled(True))

    def on_init_completed(is_supported):
        if is_supported:
            pass
        else:
            # 清理不支持的监听器
            if hasattr(self, 'themeListener') and self.themeListener:
                self.themeListener.quit()
                self.themeListener = None

    # 创建监听器
    self.themeListener = SystemThemeListener(self)
    self.themeListener.systemThemeChanged.connect(handle_theme_change)
    self.themeListener.initCompleted.connect(on_init_completed)

    # 启动线程（阻塞调用会在线程中运行）
    self.themeListener.start()

    return self.themeListener
