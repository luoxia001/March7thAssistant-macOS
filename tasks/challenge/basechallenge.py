from abc import ABC, abstractmethod
from typing import Optional
from module.automation import auto
from module.logger import log
import time


class BaseChallenge(ABC):
    def __init__(self, name: str, total_star: Optional[int], hotkey_technique: str, auto_battle_detect_enable: bool) -> None:
        self.name = name
        self.total_star = total_star
        self.hotkey_technique = hotkey_technique
        self.auto_battle_detect_enable = auto_battle_detect_enable
        self.max_level = 0
        self.max_star = 3

    @abstractmethod
    def run(self):
        '''执行挑战'''
        pass

    def prepare(self):
        '''切换场景并判断是否刷新'''
        raise NotImplementedError

    def start_challenges(self):
        '''查找关卡并判断星数'''
        raise NotImplementedError

    def start_challenge(self):
        '''开始挑战'''
        raise NotImplementedError

    def prepare_level(self):
        '''配置队伍'''
        raise NotImplementedError

    def start_level(self):
        '''开始关卡'''
        raise NotImplementedError

    def start_battle(self):
        '''开始战斗'''
        raise NotImplementedError

    def check_fight(self):
        '''检查战斗是否结束'''
        raise NotImplementedError

    def collect_rewards(self):
        '''领取奖励'''
        raise NotImplementedError

    def check_star_in_ocr_results(self, ocr_results):
        '''根据星数判断是否刷新'''
        target_format = f"/{self.total_star}"
        for box in ocr_results:
            text = box[1][0]
            if target_format in text:
                text = text.replace("*", "")
                log.info(f"星数：{text}")
                current_star, _ = text.split('/')
                if current_star == str(self.total_star):
                    log.info(f"{self.name}未刷新")
                    return True
                else:
                    return False
        return False

    def select_characters(self, team_config, team_image_path):
        '''选择角色'''
        # 切换队伍
        if auto.click_element(team_image_path, "image", 0.8, max_retries=10, crop=(592.0 / 1920, 556.0 / 1080, 256.0 / 1920, 424.0 / 1080)):
            time.sleep(1)
            auto.take_screenshot(crop=(30 / 1920, 115 / 1080, 530 / 1920, 810 / 1080))
            # 选择角色
            for character in team_config:
                scrolling_counter = 0  # 统计滚动次数
                max_scroll_times = 4  # 最大滚动次数
                scroll_line = 19  # 26滚动1页，13滚动半页
                while (not auto.click_element(f"./assets/images/share/character/{character[0]}.png", "image", 0.7, max_retries=10, take_screenshot=False)):
                    if scrolling_counter > max_scroll_times:
                        # 滚动超过2页强制结束
                        log.info(f"{character[0]}未找到")
                        return False
                    auto.click_element("等级", "text", include=True, action="move")
                    # ，尝试向下滚动
                    auto.mouse_scroll(scroll_line, -1, False)
                    time.sleep(0.5)
                    auto.click_element("角色列表", "text", include=True, action="move")
                    scrolling_counter += 1
                for _ in range(scrolling_counter):
                    # 尝试向上滚动 恢复初始位置
                    auto.click_element("等级", "text", include=True, action="move")
                    auto.mouse_scroll(scroll_line, 1, False)
                    time.sleep(0.5)
                    auto.click_element("角色列表", "text", include=True, action="move")
                time.sleep(0.5)
            time.sleep(0.5)
            # 尝试关闭命途切换窗口
            if auto.click_element("切换命途", "text", offset=(0, -68), crop=(804 / 1920, 8 / 1080, 154 / 1920, 294 / 1080)):
                time.sleep(0.5)
            return True
        return False

    def switch_to_normal_mode(self):
        '''最高难度有星启模式 挑战前切换回常规模式（忘却之庭第12层 末日幻影难度04）'''
        for _ in range(3):
            result = auto.find_element("星启模式", "text", max_retries=2, include=True)
            if not result:
                return True
            # 切换按钮在文字左侧 中心距文字左边约 1 个文字宽度
            (left, top), (right, bottom) = result
            width = right - left
            auto.click_element_with_pos(((left - int(width * 1.25), top), (left - int(width * 0.75), bottom)))
            log.info("关闭星启模式")
            time.sleep(2)
        return not auto.find_element("星启模式", "text", max_retries=2, include=True)

    def select_preset_team(self, preset, team_image_path):
        '''从「预设编队」里选择队伍填入指定的队伍位置'''
        # 先选中要填入的队伍位置 再点预设 预设会填入当前选中的位置
        if not auto.click_element(team_image_path, "image", 0.8, max_retries=10, crop=(592.0 / 1920, 556.0 / 1080, 256.0 / 1920, 424.0 / 1080)):
            return False
        time.sleep(1)
        if not auto.click_element("预设编队", "text", max_retries=4, retry_delay=0.5, crop=(6 / 1920, 8 / 1080, 778 / 1920, 168 / 1080)):
            return False
        time.sleep(1)
        team_name = f"队伍{int(preset)}"
        team_name_crop = (6 / 1920, 116 / 1080, 700 / 1920, 900 / 1080)
        for _ in range(4):
            pos = self._find_preset_title(team_name, team_name_crop)
            if pos:
                auto.click_element_with_pos(pos)
                log.info(f"已选择预设编队{team_name}")
                time.sleep(1)
                return True
            log.info(f"未找到预设编队{team_name}，尝试滚动")
            auto.click_element(team_name_crop, "crop", action="move")
            auto.mouse_scroll(28, -1, False)
            time.sleep(1)
        log.error(f"未找到预设编队{team_name}")
        return False

    @staticmethod
    def _find_preset_title(team_name, crop):
        '''
        查找预设编队的标题位置

        角色头像下方也会显示「队伍N」表示该角色所在的队伍 文字和标题相同
        头像标签的正下方紧跟着「等级」 标题下方没有 以此区分
        '''
        auto.take_screenshot(crop=crop)
        auto.perform_ocr()
        boxes = [(box, text.strip().lstrip("★☆*").strip()) for box, (text, _) in auto.ocr_result]
        levels = [box for box, text in boxes if text.startswith("等级")]
        for box, text in boxes:
            if text != team_name:
                continue
            height = box[2][1] - box[0][1]
            is_label = any(abs(level[0][0] - box[0][0]) < height * 2 and 0 < level[0][1] - box[2][1] < height * 2 for level in levels)
            if not is_label:
                return auto.calculate_text_position(box, False)
        return None

    def click_message_box(self):
        '''等待游戏加载并点击弹窗'''
        if auto.find_element("空白", "text", max_retries=120, crop=(12.0 / 1920, 731.0 / 1080, 1904.0 / 1920, 280.0 / 1080), include=True):
            time.sleep(1)
            # 关闭弹窗
            auto.press_key("esc")
            time.sleep(1)

    def wait_next_room(self, timeout=20):
        '''
        等待传送到下一间

        上一间战斗结束后会先回到大世界（出现左上角灯泡） 再自动传送到下一间 传送期间的输入无效
        先等灯泡消失（开始传送） 再等它重新出现（下一间加载完成）
        5 秒内灯泡一直没有消失时认为没有传送过程
        '''
        prepare_fight = "./assets/images/purefiction/prepare_fight.png"
        crop = (0 / 1920, 0 / 1080, 300.0 / 1920, 300.0 / 1080)
        start = time.monotonic()
        teleporting = False
        while time.monotonic() - start < timeout:
            visible = auto.find_element(prepare_fight, "image", 200000, crop=crop)
            if not visible:
                teleporting = True
            elif teleporting:
                time.sleep(1)
                return True
            elif time.monotonic() - start > 5:
                return True
            time.sleep(0.3)
        log.warning("等待传送到下一间超时")
        return False

    def use_technique_and_attack_monster(self, team):
        '''使用秘技并攻击怪物'''
        # 靠近怪物 末日幻影的首领比忘却之庭/虚构叙事远 可按玩法覆盖前进时间
        from module import mobile
        auto.press_key("w", mobile.layout(f"challenge_forward_seconds_{type(self).__name__}", 4))

        # 使用秘技
        last_index = None
        opener_count = 1
        for index, (_, count) in enumerate(team, 1):
            if count > 0:
                auto.press_key(str(index))
                time.sleep(1)
                for _ in range(count):
                    auto.press_key(self.hotkey_technique)
                    time.sleep(1)
            elif count < 0:
                # 负数表示开怪角色 绝对值是开怪时按秘技的次数（如遐蝶需要按两下）
                last_index = index
                opener_count = -count

        # 切换到开怪角色
        if last_index is not None:
            auto.press_key(str(last_index))
            time.sleep(1)

        # 开怪
        for i in range(opener_count):
            if i > 0:
                time.sleep(1)
            auto.press_key(self.hotkey_technique)
        for _ in range(3):
            auto.press_mouse()
            time.sleep(1)
