"""
移动端（iOS / PlayCover）画面适配

iOS 版星穹铁道是移动端 UI：大部分图标和 PC 版一样，只是整体放大约 1.25 倍，位置也略有不同。
这里集中处理 PC 资源到移动端的转换，业务代码不需要知道当前是不是移动端：

- 模板：默认按 template_scale 缩放 PC 模板；assets/mobile/images/ 下有同名文件时优先使用（不再缩放）
- 裁剪区域：assets/mobile/profile.yaml 的 crops 里按 PC 裁剪区域查表替换
- 触控布局：PC 按键在移动端对应的屏幕按钮坐标（1920x1080 标准坐标）
"""
import json
import os
from functools import lru_cache

import cv2
from ruamel.yaml import YAML

from module.config import cfg
from utils.image_utils import ImageUtils

PROFILE_PATH = "./assets/mobile/profile.yaml"
IMAGE_ROOT = "./assets/images/"
MOBILE_IMAGE_ROOT = "./assets/mobile/images/"


def is_mobile() -> bool:
    """当前是否在操作移动端（PlayCover）游戏"""
    return bool(cfg.get_value("playcover_enable", False)) and not bool(cfg.get_value("cloud_game_enable", False))


@lru_cache(maxsize=1)
def profile() -> dict:
    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        data = YAML(typ="safe").load(f) or {}
    data.setdefault("template_scale", 1.0)
    data.setdefault("templates", {})
    data.setdefault("crops", {})
    data.setdefault("touch", {})
    return data


def _normalize_path(target: str) -> str:
    path = target.replace("\\", "/")
    if path.startswith("assets/"):
        path = "./" + path
    return path


def _mobile_image_path(target: str) -> str | None:
    path = _normalize_path(target)
    if not path.startswith(IMAGE_ROOT):
        return None
    mobile_path = MOBILE_IMAGE_ROOT + path[len(IMAGE_ROOT):]
    return mobile_path if os.path.exists(mobile_path) else None


# 没有配置也没有学到缩放比例时依次尝试的比例：图标约 1.25 倍 文字约 1.05 倍
CANDIDATE_SCALES = (1.25, 1.0, 1.05, 1.1, 1.15, 1.2, 1.3, 1.35, 1.4)
LEARNED_SCALES_PATH = "./assets/mobile/learned_scales.json"
_learned_scales: dict | None = None


def template_info(target: str) -> tuple[str, float | None, dict]:
    """
    PC 模板在移动端的实际文件和缩放

    Returns:
        (文件路径, 缩放比例 没有确定时为 None, 该模板的额外配置)
    """
    key = _normalize_path(target)
    conf = profile()["templates"].get(key, {}) or {}
    mobile_path = _mobile_image_path(target)
    if mobile_path is not None:
        return mobile_path, float(conf.get("scale", 1.0)), conf
    if "scale" in conf:
        return target, float(conf["scale"]), conf
    learned = _load_learned_scales().get(key)
    return target, (float(learned) if learned is not None else None), conf


def template_scales(target: str) -> tuple[float, ...]:
    """模板要尝试的缩放比例"""
    if not is_mobile():
        return (1.0,)
    _, scale, _ = template_info(target)
    return (scale,) if scale is not None else CANDIDATE_SCALES


def _load_learned_scales() -> dict:
    global _learned_scales
    if _learned_scales is None:
        try:
            with open(LEARNED_SCALES_PATH, "r", encoding="utf-8") as f:
                _learned_scales = json.load(f)
        except (OSError, ValueError):
            _learned_scales = {}
    return _learned_scales


def learn_scale(target: str, scale: float) -> None:
    """记住模板匹配成功时的缩放比例 之后只用这个比例匹配"""
    key = _normalize_path(target)
    learned = _load_learned_scales()
    if key in profile()["templates"] or _mobile_image_path(target) is not None or learned.get(key) == scale:
        return
    learned[key] = scale
    try:
        with open(LEARNED_SCALES_PATH, "w", encoding="utf-8") as f:
            json.dump(learned, f, ensure_ascii=False, indent=2, sort_keys=True)
    except OSError:
        pass


def read_template(target: str, flags=cv2.IMREAD_COLOR, scale: float | None = None):
    """
    读取模板 移动端下替换文件并缩放

    scale 为 None 时使用确定的比例 没有确定的比例时使用第一个候选比例
    """
    if not is_mobile():
        return ImageUtils.read_image(target, flags)
    path, conf_scale, _ = template_info(target)
    if scale is None:
        scale = conf_scale if conf_scale is not None else CANDIDATE_SCALES[0]
    image = ImageUtils.read_image(path, flags)
    if image is not None and scale != 1.0:
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    return image


def read_template_mask(target: str, scale: float | None = None):
    """读取模板的透明通道掩码 移动端下替换文件并缩放"""
    if not is_mobile():
        return ImageUtils.read_template_with_mask(target)
    path, conf_scale, _ = template_info(target)
    if scale is None:
        scale = conf_scale if conf_scale is not None else CANDIDATE_SCALES[0]
    mask = ImageUtils.read_template_with_mask(path)
    if mask is not None and scale != 1.0:
        mask = cv2.resize(mask, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    return mask


def template_threshold(target: str, threshold, has_mask: bool, scale: float = 1.0):
    """
    模板在移动端的匹配阈值

    - profile 里配置了 threshold 时使用配置值
    - 带掩码的模板用 TM_SQDIFF（越小越好），数值和模板面积成正比，缩放后按面积放大阈值
    """
    if not is_mobile() or threshold is None:
        return threshold
    _, _, conf = template_info(target)
    if "threshold" in conf:
        return conf["threshold"]
    if has_mask and scale != 1.0:
        return threshold * scale * scale
    return threshold


def mask_threshold(target: str) -> float:
    """带透明通道的模板在移动端的匹配阈值（TM_CCOEFF_NORMED）"""
    _, _, conf = template_info(target)
    return float(conf.get("threshold", profile().get("mask_threshold", 0.7)))


def match_with_mask(screenshot, template, mask):
    """带掩码的归一化相关系数匹配 返回 (最大值, 位置)"""
    import numpy as np
    result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED, mask=mask)
    result[~np.isfinite(result)] = -1  # 掩码匹配在低方差区域可能产生 NaN/Inf
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    return max_val, max_loc


def badge_config(target: str):
    """带红点模板的 (图标模板, 红点区域)；不是这类模板时返回 None"""
    if not is_mobile():
        return None
    _, _, conf = template_info(target)
    if "icon" not in conf:
        return None
    return conf["icon"], conf.get("badge", [65, -55, 75, 70])


def has_red_badge(screenshot_bgr, region) -> bool:
    """区域里是否有红点（游戏里红色感叹号的颜色）"""
    x, y, w, h = (int(v) for v in region)
    x0, y0 = max(x, 0), max(y, 0)
    part = screenshot_bgr[y0:y + h, x0:x + w].astype("int32")
    if part.size == 0:
        return False
    b, g, r = part[..., 0], part[..., 1], part[..., 2]
    count = int(((r > 190) & (g < 90) & (b < 90)).sum())
    return count >= int(profile().get("badge_min_pixels", 150))


def _crop_key(crop) -> str:
    return ",".join(f"{round(float(v) * (1920 if i % 2 == 0 else 1080))}" for i, v in enumerate(crop))


def map_crop(crop):
    """
    PC 裁剪区域在移动端的对应区域

    profile.yaml 的 crops 以 PC 裁剪区域的标准像素坐标 "x,y,w,h" 为键，值是移动端的 [x, y, w, h]（标准像素）。
    没有配置的裁剪区域原样返回。
    """
    if not is_mobile() or crop is None or tuple(crop) == (0, 0, 1, 1):
        return crop
    mapped = profile()["crops"].get(_crop_key(crop))
    if mapped is None:
        return crop
    x, y, w, h = mapped
    return (x / 1920, y / 1080, w / 1920, h / 1080)


def touch_point(name: str, default=None):
    """触控布局里按钮的标准坐标"""
    return profile()["touch"].get(name, default)
