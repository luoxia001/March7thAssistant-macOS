import math
import subprocess
import threading
import time

import cv2

from module.automation.input_base import InputBase
from module.game.maatools_client import TouchPhase
from module.mobile import profile
from utils.image_utils import ImageUtils

# 手指编号 不同编号互相独立 可以同时按住
CONTACT_TAP = 0
CONTACT_JOYSTICK = 1
CONTACT_BUTTON = 2

MOVE_KEYS = {"w": (0, -1), "s": (0, 1), "a": (-1, 0), "d": (1, 0)}


class PlayCoverInput(InputBase):
    """
    把 PC 键鼠操作转换成 iOS 触控（MaaTools）

    - 鼠标点击、拖动、滚轮 → 单指点击和滑动 坐标是 1920x1080 标准坐标
    - WASD → 左下角虚拟摇杆按住
    - 其他按键 → assets/mobile/profile.yaml 里 keys 配置的屏幕按钮
    - Esc → 按当前画面决定：大世界点手机菜单，其他界面点右上角关闭
    """

    def __init__(self, game, logger):
        self.game = game
        self.logger = logger
        self._lock = threading.RLock()
        self._cursor = (960, 540)
        self._mouse_pressed = False
        self._move_pressed: set[str] = set()
        self._button_pressed: str | None = None
        self._templates = {}

    # ---------- 基础触控 ----------

    def _touch(self, phase: TouchPhase, x: float, y: float, contact: int) -> bool:
        tx, ty = self.game.to_touch(x, y)
        return self.game.client.touch(phase, tx, ty, contact)

    def tap(self, x: float, y: float, press_time: float = 0.05, contact: int = CONTACT_TAP) -> None:
        with self._lock:
            self._touch(TouchPhase.BEGAN, x, y, contact)
            time.sleep(max(press_time, 0.03))
            self._touch(TouchPhase.ENDED, x, y, contact)

    def swipe(self, start, end, duration: float = 0.5, contact: int = CONTACT_TAP, hold_end: float = 0.1) -> None:
        steps = max(int(duration / 0.016), 5)
        with self._lock:
            self._touch(TouchPhase.BEGAN, start[0], start[1], contact)
            time.sleep(0.05)
            for i in range(1, steps + 1):
                t = i / steps
                self._touch(TouchPhase.MOVED, start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t, contact)
                time.sleep(duration / steps)
            time.sleep(hold_end)
            self._touch(TouchPhase.ENDED, end[0], end[1], contact)

    def release_all(self) -> None:
        with self._lock:
            for contact in (CONTACT_TAP, CONTACT_JOYSTICK, CONTACT_BUTTON):
                self._touch(TouchPhase.ENDED, *self._cursor, contact)
            self._mouse_pressed = False
            self._move_pressed.clear()
            self._button_pressed = None

    # ---------- 鼠标 ----------

    def mouse_click(self, x, y):
        self._cursor = (x, y)
        self.tap(x, y)
        self.logger.debug(f"触控点击 ({x}, {y})")

    def mouse_down(self, x, y):
        self._cursor = (x, y)
        self._mouse_pressed = True
        self._touch(TouchPhase.BEGAN, x, y, CONTACT_TAP)
        self.logger.debug(f"触控按下 ({x}, {y})")

    def mouse_up(self):
        self._touch(TouchPhase.ENDED, *self._cursor, CONTACT_TAP)
        self._mouse_pressed = False
        self.logger.debug("触控抬起")

    def mouse_move(self, x, y):
        if self._mouse_pressed:
            self.swipe_to(x, y)
        self._cursor = (x, y)

    def swipe_to(self, x, y, duration=0.2):
        sx, sy = self._cursor
        steps = max(int(duration / 0.016), 3)
        for i in range(1, steps + 1):
            t = i / steps
            self._touch(TouchPhase.MOVED, sx + (x - sx) * t, sy + (y - sy) * t, CONTACT_TAP)
            time.sleep(duration / steps)
        self._cursor = (x, y)

    def mouse_drag(self, start_x, start_y, end_x, end_y, duration=0.5):
        self.swipe((start_x, start_y), (end_x, end_y), duration=max(float(duration or 0), 0.2))
        self._cursor = (end_x, end_y)
        self.logger.debug(f"触控拖动 ({start_x}, {start_y}) -> ({end_x}, {end_y})")
        return True

    def mouse_scroll(self, count, direction=-1, pause=True):
        """
        鼠标滚轮转换成在光标位置的滑动

        direction=-1 是向下滚动 内容向上移动 所以手指向上滑
        """
        rule = self._scroll_rule()
        step = float(rule.get("step", profile().get("scroll_step", 60)))
        max_distance = float(rule.get("max_distance", 600))
        total = step * count
        sign = -1 if direction < 0 else 1
        x, y = rule.get("at", self._cursor)
        # 一次滑动距离有限 滚动很多格时分几次滑
        for _ in range(min(max(math.ceil(total / max_distance), 1), 5)):
            distance = min(total, max_distance)
            total -= distance
            if rule.get("axis") == "horizontal":
                # 横向排列的界面（如忘却之庭关卡）PC 滚轮向下对应内容向左移动
                start = (x - sign * distance / 2, y)
                end = (x + sign * distance / 2, y)
            else:
                start = (x, y)
                end = (x, min(max(y + sign * distance, 10), 1070))
            # 结束时停顿一下再抬起 避免列表惯性继续滚动
            self.swipe(start, end, duration=0.4 + 0.02 * count, hold_end=0.3)
            self.logger.debug(f"触控滚动 {count} 次 方向 {direction} {start} -> {end}")
            if total <= 0:
                break
        if pause:
            time.sleep(0.3)

    def _scroll_rule(self) -> dict:
        """profile 的 scroll_rules 里第一个匹配当前画面的规则 没有时返回空字典"""
        rules = profile().get("scroll_rules", [])
        if not rules:
            return {}
        screen = self.game.screenshot_bgr()
        if screen is None:
            return {}
        from module import mobile
        for rule in rules:
            template = mobile.read_template(rule["template"])
            if template is None:
                continue
            x, y, w, h = rule.get("region", [0, 0, 1920, 1080])
            part = screen[y:y + h, x:x + w]
            if part.shape[0] < template.shape[0] or part.shape[1] < template.shape[1]:
                continue
            if cv2.matchTemplate(part, template, cv2.TM_CCOEFF_NORMED).max() >= rule.get("threshold", 0.85):
                return rule
        return {}

    def press_mouse(self, wait_time=0.2):
        """
        PC 大世界里左键是普通攻击

        有些状态下移动端没有普攻按钮 左键的功能换到了别的按钮上（如流萤秘技飞起后在秘技位置变成「下落」）
        profile 的 attack_alternatives 按区域文字识别这些状态
        """
        target = "attack"
        rules = profile().get("attack_alternatives", [])
        screen = self.game.screenshot_bgr() if rules else None
        if screen is not None:
            from module.ocr import ocr
            for rule in rules:
                x, y, w, h = rule["region"]
                part = cv2.cvtColor(screen[y:y + h, x:x + w], cv2.COLOR_BGR2RGB)
                result = ocr.recognize_single_line(part)
                if result and rule["text"] in result[0]:
                    self.logger.debug(f"左键 → {rule['text']} {rule['tap']}")
                    target = rule["tap"]
                    break
        self._press_button(target, wait_time)

    # ---------- 键盘 ----------

    @staticmethod
    def _normalize_key(key) -> str:
        key = str(key).lower()
        return {"escape": "esc", "space": "space"}.get(key, key)

    def _key_target(self, key: str):
        return profile().get("keys", {}).get(key)

    def press_key(self, key, wait_time=0.2):
        key = self._normalize_key(key)
        if key in MOVE_KEYS:
            self.press_key_down(key)
            time.sleep(wait_time)
            self.press_key_up(key)
        elif key == "esc":
            self.back()
        else:
            target = self._key_target(key)
            if target is None:
                self.logger.warning(f"移动端没有按键 {key} 对应的按钮 已忽略")
                return
            self._press_button(target, min(wait_time, 0.3))
        self.logger.debug(f"按键 {key}")

    def secretly_press_key(self, key, wait_time=0.2):
        key = self._normalize_key(key)
        if key in MOVE_KEYS or key == "esc":
            self.press_key(key, wait_time)
            return
        target = self._key_target(key)
        if target is not None:
            self._press_button(target, min(wait_time, 0.3))

    def press_key_down(self, key):
        key = self._normalize_key(key)
        if key in MOVE_KEYS:
            self._move_pressed.add(key)
            self._update_joystick(began=len(self._move_pressed) == 1)
            return
        target = self._key_target(key)
        if target is None:
            self.logger.debug(f"移动端没有按键 {key} 对应的按钮 已忽略")
            return
        point = self._button_point(target)
        if point is not None:
            self._button_pressed = target
            self._touch(TouchPhase.BEGAN, point[0], point[1], CONTACT_BUTTON)

    def press_key_up(self, key):
        key = self._normalize_key(key)
        if key in MOVE_KEYS:
            if key in self._move_pressed:
                self._move_pressed.discard(key)
                if self._move_pressed:
                    self._update_joystick(began=False)
                else:
                    center = profile()["touch"]["joystick"]
                    self._touch(TouchPhase.ENDED, center[0], center[1], CONTACT_JOYSTICK)
            return
        target = self._key_target(key)
        if target is not None and self._button_pressed == target:
            point = self._button_point(target)
            self._touch(TouchPhase.ENDED, point[0], point[1], CONTACT_BUTTON)
            self._button_pressed = None

    def _update_joystick(self, began: bool) -> None:
        center = profile()["touch"]["joystick"]
        radius = float(profile()["touch"].get("joystick_radius", 120))
        dx = sum(MOVE_KEYS[k][0] for k in self._move_pressed)
        dy = sum(MOVE_KEYS[k][1] for k in self._move_pressed)
        length = math.hypot(dx, dy) or 1
        x = center[0] + dx / length * radius
        y = center[1] + dy / length * radius
        if began:
            self._touch(TouchPhase.BEGAN, center[0], center[1], CONTACT_JOYSTICK)
            time.sleep(0.05)
            # 分几步推到目标位置 一下子跳过去有时不会识别成摇杆
            for t in (0.3, 0.6, 1.0):
                self._touch(TouchPhase.MOVED, center[0] + (x - center[0]) * t, center[1] + (y - center[1]) * t, CONTACT_JOYSTICK)
                time.sleep(0.02)
        else:
            self._touch(TouchPhase.MOVED, x, y, CONTACT_JOYSTICK)

    def _button_point(self, target):
        if isinstance(target, (list, tuple)):
            return target
        point = profile()["touch"].get(target)
        if point is None:
            self.logger.warning(f"移动端触控布局缺少按钮 {target}")
        return point

    def _press_button(self, target, press_time: float = 0.1) -> None:
        point = self._button_point(target)
        if point is not None:
            self.tap(point[0], point[1], press_time=press_time, contact=CONTACT_BUTTON)

    # ---------- Esc ----------

    def _template(self, name: str):
        if name not in self._templates:
            self._templates[name] = ImageUtils.read_image(f"./assets/mobile/images/ui/{name}.png")
        return self._templates[name]

    def _match(self, screen, name: str, region, threshold: float = 0.8):
        x, y, w, h = region
        part = screen[y:y + h, x:x + w]
        template = self._template(name)
        if template is None or part.shape[0] < template.shape[0] or part.shape[1] < template.shape[1]:
            return None
        result = cv2.matchTemplate(part, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val < threshold:
            return None
        return x + max_loc[0] + template.shape[1] // 2, y + max_loc[1] + template.shape[0] // 2

    def _ocr_texts(self, screen, region):
        from module.ocr import ocr
        x, y, w, h = region
        part = cv2.cvtColor(screen[y:y + h, x:x + w], cv2.COLOR_BGR2RGB)
        results = ocr.convert_format(ocr.run(part)) or []
        return [(box, text) for box, (text, _) in results], (x, y)

    def _match_text(self, screen, item):
        """按文字找按钮 when 指定时要求 when_region 里先出现这段文字（用来限定弹窗）"""
        if "when" in item:
            texts, _ = self._ocr_texts(screen, item.get("when_region", [0, 0, 1920, 1080]))
            if not any(item["when"] in text for _, text in texts):
                return None
        texts, (ox, oy) = self._ocr_texts(screen, item["region"])
        for box, text in texts:
            if item["text"] in text:
                return ox + (box[0][0] + box[2][0]) / 2, oy + (box[0][1] + box[2][1]) / 2
        return None

    def back(self) -> None:
        """
        PC 的 Esc 在移动端的等效操作

        - 大世界：点左上角手机图标打开菜单（PC 上 Esc 打开手机菜单）
        - 其他界面：点 profile 里 back_buttons 配置的关闭/返回按钮 都找不到时点右上角关闭位置
        """
        screen = self.game.screenshot_bgr()
        if screen is not None:
            for item in profile().get("back_buttons", []):
                if "text" in item:
                    pos = self._match_text(screen, item)
                else:
                    pos = self._match(screen, item["template"], item["region"], item.get("threshold", 0.8))
                if pos is not None:
                    self.logger.debug(f"Esc → 点击 {item.get('template') or item['text']} {pos}")
                    self.tap(*pos)
                    return
        fallback = profile()["touch"].get("back_fallback")
        if fallback:
            self.logger.debug(f"Esc → 未识别到返回按钮 点击默认位置 {fallback}")
            self.tap(*fallback)

    # ---------- 文字 ----------

    def secretly_write(self, text, interval=0.1):
        """
        iOS 游戏和 macOS 共用剪贴板 写入剪贴板后由调用方点游戏输入框粘贴

        MaaTools 不支持键盘输入；Cmd+V 需要把游戏切到前台并给辅助功能权限
        """
        subprocess.run(["pbcopy"], input=str(text).encode("utf-8"), check=False)
        self._paste_by_shortcut()

    def _paste_by_shortcut(self) -> None:
        try:
            import AppKit
            import Quartz
        except ImportError:
            self.logger.warning("缺少 pyobjc 无法发送 Cmd+V 请手动粘贴")
            return
        apps = AppKit.NSRunningApplication.runningApplicationsWithBundleIdentifier_(self.game.bundle_id)
        if not apps:
            return
        previous = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()
        apps[0].activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)
        time.sleep(0.4)
        for down in (True, False):
            event = Quartz.CGEventCreateKeyboardEvent(None, 9, down)  # 9 = V
            Quartz.CGEventSetFlags(event, Quartz.kCGEventFlagMaskCommand)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
            time.sleep(0.03)
        time.sleep(0.3)
        if previous is not None and previous.bundleIdentifier() != self.game.bundle_id:
            previous.activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)
