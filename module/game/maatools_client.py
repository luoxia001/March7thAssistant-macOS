import contextlib
import socket
import struct
import threading
from enum import IntEnum

import numpy as np


from module.logger import log


class TouchPhase(IntEnum):
    """触控阶段 数值与 PlayTools 的 MaaTools 协议一致"""

    BEGAN = 0
    MOVED = 1
    ENDED = 3


class MaaToolsClient:
    """
    MaaTools 协议客户端

    MaaTools 是 PlayCover 分支版（hguandl/PlayCover）在游戏进程内开启的 TCP 服务，
    可以直接截取游戏画面、注入多指触控，不需要游戏窗口在前台。

    协议格式：
    - 握手：客户端发送 b'MAA\\0'，服务端返回 b'OKAY'
    - 请求：2 字节大端长度 + 负载，负载前 4 字节是命令名
    - 所有整数都是大端
    """

    MIN_VERSION: int = 2

    # 连接后要抬起的手指编号范围 [0, STALE_CONTACT_CNT)
    # 脚本进程被强制结束时来不及抬起手指 PlayTools 会让这些手指一直按着 例如普通攻击按钮一直是按下状态
    STALE_CONTACT_CNT: int = 32

    def __init__(self, host: str = '127.0.0.1', port: int = 1717, timeout: float = 5) -> None:
        self.host: str = host
        self.port: int = port
        self.timeout: float = timeout

        self._sock: socket.socket | None = None
        self._lock: threading.Lock = threading.Lock()

        self.version: int = 0
        self.touch_width: int = 0  # 触控坐标空间的宽 即 iOS 屏幕原生像素
        self.touch_height: int = 0  # 触控坐标空间的高

    @property
    def is_connected(self) -> bool:
        return self._sock is not None

    def connect(self) -> bool:
        """
        连接 MaaTools 服务并读取版本和触控坐标空间大小

        Returns:
            是否连接成功
        """
        with self._lock:
            return self._connect_unlocked()

    def _connect_unlocked(self) -> bool:
        if self._sock is not None:
            return True
        try:
            sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self._sock = sock
            sock.sendall(b'MAA\0')
            if self._recv(4) != b'OKAY':
                raise ConnectionError('MaaTools 握手失败')

            self._send(b'VERN')
            self.version = struct.unpack('>I', self._recv(4))[0]
            if self.version < MaaToolsClient.MIN_VERSION:
                raise ConnectionError(f'MaaTools 协议版本过低 {self.version}')

            self._send(b'SIZE')
            self.touch_width, self.touch_height = struct.unpack('>HH', self._recv(4))
            self._release_stale_contacts_unlocked()
            log.info(f'MaaTools 已连接 {self.host}:{self.port} 版本 {self.version} '
                     f'触控空间 {self.touch_width}x{self.touch_height}')
            return True
        except OSError as e:
            log.debug(f'MaaTools 连接失败 {self.host}:{self.port} {e}')
            self._close_unlocked()
            return False

    def _release_stale_contacts_unlocked(self) -> None:
        """抬起上一次连接可能遗留的手指 没按下的手指收到抬起事件不会有影响"""
        x = self.touch_width // 2
        y = self.touch_height // 2
        for contact in range(MaaToolsClient.STALE_CONTACT_CNT):
            self._send(b'TUCH' + struct.pack('>BHHB', int(TouchPhase.ENDED), x, y, contact))

    def close(self) -> None:
        with self._lock:
            self._close_unlocked()

    def _close_unlocked(self) -> None:
        if self._sock is not None:
            with contextlib.suppress(OSError):
                self._sock.close()
        self._sock = None

    def _recv(self, n: int) -> bytearray:
        """
        读取 n 个字节

        先按长度一次分配好缓冲区 再用 recv_into 直接写进去
        截图一张约 15MB 如果边收边拼接（buf += chunk）再复制一份 每张图会临时分配好几份大内存
        截图很频繁 长时间运行时内存会越占越多
        """
        buf = bytearray(n)
        view = memoryview(buf)
        received = 0
        while received < n:
            size = self._sock.recv_into(view[received:], n - received)
            if size == 0:
                raise ConnectionError('MaaTools 连接已断开')
            received += size
        return buf

    def _send(self, payload: bytes) -> None:
        self._sock.sendall(struct.pack('>H', len(payload)) + payload)

    def screenshot(self) -> "np.ndarray | None":
        """
        截取游戏画面

        Returns:
            BGR 图像 尺寸为游戏窗口内容的实际像素 和触控坐标空间不一定相同；失败时返回 None
        """
        with self._lock:
            if not self._connect_unlocked():
                return None
            try:
                self._send(b'BGR\x01')
                width, height, length = struct.unpack('>III', self._recv(12))
                if length == 0:
                    return None
                data = self._recv(length)  # 长度不对也要读完 否则剩下的数据会让后面的命令读错位
                if length != width * height * 3:
                    return None
            except OSError as e:
                log.error(f'MaaTools 截图失败 {e}')
                self._close_unlocked()
                return None
        return np.frombuffer(data, dtype=np.uint8).reshape(height, width, 3)

    def touch(self, phase: TouchPhase, x: int, y: int, contact: int = 0) -> bool:
        """
        发送一个触控事件

        Args:
            phase: 触控阶段
            x: 横坐标 触控坐标空间
            y: 纵坐标 触控坐标空间
            contact: 手指编号 0~255 不同编号是互相独立的手指

        Returns:
            是否发送成功
        """
        x = min(max(int(x), 0), max(self.touch_width - 1, 0))
        y = min(max(int(y), 0), max(self.touch_height - 1, 0))
        with self._lock:
            if not self._connect_unlocked():
                return False
            try:
                self._send(b'TUCH' + struct.pack('>BHHB', int(phase), x, y, contact & 0xFF))
                return True
            except OSError as e:
                log.error(f'MaaTools 触控失败 {e}')
                self._close_unlocked()
                return False

    def terminate(self) -> None:
        """关闭游戏"""
        with self._lock:
            if not self._connect_unlocked():
                return
            with contextlib.suppress(OSError):
                self._send(b'TERM')
            self._close_unlocked()
