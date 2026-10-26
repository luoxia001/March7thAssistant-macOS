import os
import subprocess
import threading
import time
from typing import Optional

import cv2
import psutil
from PIL import Image

from module.config.config import Config
from module.game.base import GameControllerBase
from module.game.maatools_client import MaaToolsClient
from utils.logger.logger import Logger

STANDARD_WIDTH = 1920
STANDARD_HEIGHT = 1080


class PlayCoverGameController(GameControllerBase):
    """
    macOS 上通过 PlayCover 运行的 iOS 版星穹铁道

    截图和触控都走 hguandl/PlayCover 分支版内置的 MaaTools 服务（游戏设置里打开 MaaTools）：
    - 截图在游戏进程内完成 不需要窗口在前台 也不受窗口位置、标题栏、Retina 缩放影响
    - 触控直接注入 UITouch 支持多指
    对外统一使用 1920x1080 标准坐标 和云游戏模式一样
    """

    PLAYCOVER_APPS_DIR = os.path.expanduser("~/Library/Containers/io.playcover.PlayCover/Applications")

    def __init__(self, cfg: Config, logger: Optional[Logger] = None) -> None:
        super().__init__(script_path=cfg.script_path, logger=logger)
        self.cfg = cfg
        self.bundle_id = cfg.get_value("playcover_bundle_id", "com.HoYoverse.hkrpgoversea")
        self.client = MaaToolsClient(
            host=cfg.get_value("playcover_maatools_host", "127.0.0.1"),
            port=int(cfg.get_value("playcover_maatools_port", 1717)),
        )
        self._input_handler = None
        self._lock = threading.Lock()

    @property
    def app_path(self) -> str:
        return os.path.join(self.PLAYCOVER_APPS_DIR, f"{self.bundle_id}.app")

    def _find_process(self) -> Optional[psutil.Process]:
        exe_dir = self.app_path + os.sep
        for proc in psutil.process_iter(attrs=["pid", "exe"]):
            try:
                exe = proc.info["exe"] or ""
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if exe.startswith(exe_dir):
                return proc
        return None

    def start_game_process(self) -> bool:
        if not os.path.exists(self.app_path):
            self.log_error(f"未找到 PlayCover 游戏：{self.app_path}")
            return False
        if self._find_process() is not None:
            return True
        # -g 不把游戏切到前台 截图和触控都不需要前台
        result = subprocess.run(["open", "-g", self.app_path], capture_output=True, text=True)
        if result.returncode != 0:
            self.log_error(f"启动游戏失败：{result.stderr.strip()}")
            return False
        self.log_info(f"游戏启动：{self.app_path}")
        return True

    def stop_game(self) -> bool:
        try:
            if self._input_handler is not None:
                self._input_handler.release_all()
            proc = self._find_process()
            if proc is None:
                return True
            self.client.close()
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except psutil.TimeoutExpired:
                proc.kill()
            self.log_info(f"游戏终止：{self.bundle_id}")
            return True
        except Exception as e:
            self.log_error(f"终止游戏时发生错误：{e}")
            return False

    def get_window_handle(self) -> int:
        """没有 Win32 窗口句柄 游戏进程在运行且 MaaTools 能连上时返回进程号"""
        proc = self._find_process()
        if proc is None:
            return 0
        if not self.client.connect():
            return 0
        return proc.pid

    def switch_to_game(self) -> bool:
        """MaaTools 不需要游戏在前台 只要能连上即可"""
        if self.get_window_handle() == 0:
            self.log_debug("游戏未运行或 MaaTools 未连接")
            return False
        return True

    def get_resolution(self):
        return STANDARD_WIDTH, STANDARD_HEIGHT

    def get_input_handler(self):
        if self._input_handler is None:
            from module.automation.playcover_input import PlayCoverInput
            self._input_handler = PlayCoverInput(self, self.logger)
        return self._input_handler

    def copy(self, text: str) -> None:
        # iOS 游戏和 macOS 共用剪贴板
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=False)

    def screenshot_bgr(self):
        """标准分辨率的 BGR 截图 失败返回 None"""
        image = self.client.screenshot()
        if image is None:
            return None
        if image.shape[1] != STANDARD_WIDTH or image.shape[0] != STANDARD_HEIGHT:
            image = cv2.resize(image, (STANDARD_WIDTH, STANDARD_HEIGHT), interpolation=cv2.INTER_AREA)
        return image

    def take_screenshot(self, crop=(0, 0, 1, 1)):
        """
        截图并按比例裁剪

        Returns:
            (PIL RGB 图像, (left, top, width, height), 缩放比例) 坐标为标准坐标；失败返回 None
        """
        image = self.screenshot_bgr()
        if image is None:
            return None
        # 调用方算出的裁剪区域可能超出画面 限制在画面内
        left = min(max(int(STANDARD_WIDTH * crop[0]), 0), STANDARD_WIDTH - 1)
        top = min(max(int(STANDARD_HEIGHT * crop[1]), 0), STANDARD_HEIGHT - 1)
        width = max(min(int(STANDARD_WIDTH * crop[2]), STANDARD_WIDTH - left), 1)
        height = max(min(int(STANDARD_HEIGHT * crop[3]), STANDARD_HEIGHT - top), 1)
        image = image[top:top + height, left:left + width]
        screenshot = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        return screenshot, (left, top, width, height), 1

    def to_touch(self, x: float, y: float) -> tuple[int, int]:
        """标准坐标转 MaaTools 触控坐标"""
        if not self.client.is_connected:
            self.client.connect()
        tw = self.client.touch_width or STANDARD_WIDTH
        th = self.client.touch_height or STANDARD_HEIGHT
        return round(x * tw / STANDARD_WIDTH), round(y * th / STANDARD_HEIGHT)

    def wait_maatools(self, timeout: float = 120) -> bool:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if self.client.connect():
                return True
            time.sleep(2)
        return False
