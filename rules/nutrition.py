"""Nutrition and fueling rules for TrueCadence.

Pure rule helpers extracted from app.py during Stage-H code split.
Keep Streamlit, file IO, and session state out of this module.
"""
from __future__ import annotations

from typing import Any


def feedback_sets_from_recent_feedback(recent_feedback: list[dict[str, Any]]) -> tuple[set[str], set[str]]:
    """Collect special-condition and fueling flags from recent feedback records."""
    special_set: set[str] = set()
    fueling_set: set[str] = set()
    for item in recent_feedback:
        for s_item in item.get("specials", []) or []:
            special_set.add(s_item)
        if item.get("fueling") and item.get("fueling") != "正常":
            fueling_set.add(item.get("fueling"))
    return special_set, fueling_set


def calculate_nutrition_targets(
    *,
    weight: float | int,
    ride_hours: float,
    workout_type: str,
    environment: str,
    fueling_set: set[str] | list[str] | tuple[str, ...] | None = None,
    feedback_count: int = 0,
) -> dict[str, Any]:
    """Calculate carb, water, sodium and timing guidance for one ride."""
    fueling_set = set(fueling_set or [])

    if workout_type == "恢复骑":
        carb_lo, carb_hi = 0, 20
        water_lo, water_hi = 400, 600
        sodium_lo, sodium_hi = 0, 300
        intensity_note = "恢复骑主要目标是促进血液循环,不需要强行补很多糖。"
    elif workout_type == "Z2 长距离":
        carb_lo, carb_hi = (30, 50) if ride_hours <= 2 else (50, 70)
        water_lo, water_hi = 500, 750
        sodium_lo, sodium_hi = 300, 600
        intensity_note = "Z2 长距离要从前 20 分钟就开始少量多次补,不要等饿了再吃。"
    elif workout_type == "甜区/阈值":
        carb_lo, carb_hi = 60, 80
        water_lo, water_hi = 600, 850
        sodium_lo, sodium_hi = 500, 800
        intensity_note = "甜区/阈值会明显消耗糖原,训练前和训练中都要有碳水支持。"
    elif workout_type == "VO2max/间歇":
        carb_lo, carb_hi = 50, 70
        water_lo, water_hi = 600, 850
        sodium_lo, sodium_hi = 500, 800
        intensity_note = "VO2max 更怕胃里太撑,训练前吃够,训练中小口补。"
    else:
        carb_lo, carb_hi = 80, 100
        water_lo, water_hi = 750, 1000
        sodium_lo, sodium_hi = 700, 1000
        intensity_note = "比赛日目标是稳定供能,不要尝试没测试过的新补给。"

    if environment in ["天气太热", "室内骑行"]:
        water_lo += 150
        water_hi += 250
        sodium_lo += 200
        sodium_hi += 300
    if "低血糖感" in fueling_set or "吃少了" in fueling_set:
        carb_lo += 10
        carb_hi += 10
    if "胃不舒服" in fueling_set:
        carb_hi = min(carb_hi, 70)

    total_carb_lo = round(carb_lo * ride_hours)
    total_carb_hi = round(carb_hi * ride_hours)
    total_water_lo = round(water_lo * ride_hours)
    total_water_hi = round(water_hi * ride_hours)
    total_sodium_lo = round(sodium_lo * ride_hours)
    total_sodium_hi = round(sodium_hi * ride_hours)

    pre_carb = round(weight * (1.5 if ride_hours <= 2 else 2.0))
    pre_protein = round(weight * 0.3)
    post_carb = round(weight * (0.8 if workout_type == "恢复骑" else 1.2))
    post_protein = round(weight * 0.35)

    return {
        "carb_lo": carb_lo,
        "carb_hi": carb_hi,
        "water_lo": water_lo,
        "water_hi": water_hi,
        "sodium_lo": sodium_lo,
        "sodium_hi": sodium_hi,
        "intensity_note": intensity_note,
        "total_carb_lo": total_carb_lo,
        "total_carb_hi": total_carb_hi,
        "total_water_lo": total_water_lo,
        "total_water_hi": total_water_hi,
        "total_sodium_lo": total_sodium_lo,
        "total_sodium_hi": total_sodium_hi,
        "pre_carb": pre_carb,
        "pre_protein": pre_protein,
        "post_carb": post_carb,
        "post_protein": post_protein,
        "feedback_count": feedback_count,
    }


def score_supplement(sup: dict[str, Any], *, environment: str, fueling_set: set[str] | list[str] | tuple[str, ...], workout_type: str) -> int:
    """Score one supplement for the current fueling context."""
    fueling_set = set(fueling_set or [])
    sc = 0
    if sup["carbs_g"] >= 40:
        sc += 1
    if environment in ["天气太热", "室内骑行"] and sup["electrolytes_mg"] >= 200:
        sc += 2
    if "胃不舒服" in fueling_set and sup["type"] == "软糖":
        sc += 2
    if workout_type in ["比赛/绕圈赛", "VO2max/间歇"] and sup.get("caffeine"):
        sc += 1
    if workout_type == "恢复骑" and sup.get("caffeine"):
        sc -= 1
    if workout_type == "比赛/绕圈赛" and "电解质" in sup.get("tags", []):
        sc += 1
    if environment in ["天气太热", "室内骑行"] and sup.get("electrolytes_mg", 0) < 100:
        sc -= 1
    return sc


def rank_supplements(
    supplements: list[dict[str, Any]],
    *,
    environment: str,
    fueling_set: set[str] | list[str] | tuple[str, ...],
    workout_type: str,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Rank supplements with score included, preserving original supplement fields."""
    ranked = sorted(
        supplements,
        key=lambda sup: score_supplement(sup, environment=environment, fueling_set=fueling_set, workout_type=workout_type),
        reverse=True,
    )
    result = []
    for sup in ranked[:limit]:
        item = dict(sup)
        item["score"] = score_supplement(sup, environment=environment, fueling_set=fueling_set, workout_type=workout_type)
        result.append(item)
    return result


def supplement_card_context(sup: dict[str, Any], *, index: int, carb_hi: float | int, environment: str, fueling_set: set[str] | list[str] | tuple[str, ...], workout_type: str) -> dict[str, Any]:
    """Build badge/tone/reason values for the existing supplement card UI."""
    fueling_set = set(fueling_set or [])
    servings_needed = max(1, round(carb_hi / sup["carbs_g"], 1)) if sup["carbs_g"] else 0
    badge = "⭐ 首选" if index == 0 else ("👍 备选" if index == 1 else "💡 调剂")
    score = sup.get("score", score_supplement(sup, environment=environment, fueling_set=fueling_set, workout_type=workout_type))
    card_tone = "normal"
    reason_parts: list[str] = []
    if environment in ["天气太热", "室内骑行"] and sup.get("electrolytes_mg", 0) >= 200:
        card_tone = "heat"
        reason_parts.append("高温/室内:补钠优先")
    if "胃不舒服" in fueling_set and sup.get("type") == "软糖":
        card_tone = "gut"
        reason_parts.append("胃不适:软糖更温和")
    if workout_type in ["比赛/绕圈赛", "VO2max/间歇"] and sup.get("caffeine"):
        card_tone = "caffeine"
        reason_parts.append("高强度:咖啡因加成")
    if workout_type == "恢复骑" and sup.get("caffeine"):
        card_tone = "caution"
        reason_parts.append("恢复骑:咖啡因谨慎")
    if index == 0 and card_tone == "normal":
        card_tone = "primary"
        reason_parts.append("当前最匹配")

    tone_styles = {
        "primary": ("rgba(255,107,53,0.72)", "rgba(255,107,53,0.15)", "rgba(255,107,53,0.20)", "#ff9a68"),
        "heat": ("rgba(88,166,255,0.72)", "rgba(88,166,255,0.13)", "rgba(88,166,255,0.20)", "#79c0ff"),
        "gut": ("rgba(35,134,54,0.72)", "rgba(35,134,54,0.13)", "rgba(35,134,54,0.20)", "#7ee787"),
        "caffeine": ("rgba(210,168,255,0.72)", "rgba(210,168,255,0.13)", "rgba(210,168,255,0.20)", "#d2a8ff"),
        "caution": ("rgba(240,192,64,0.72)", "rgba(240,192,64,0.12)", "rgba(240,192,64,0.20)", "#f0c040"),
        "normal": ("rgba(139,148,158,0.42)", "rgba(48,54,61,0.32)", "rgba(48,54,61,0.26)", "var(--tc-subtle)"),
    }
    border_color, bg_glow, shadow_glow, accent_color = tone_styles[card_tone]
    reason_text = " · ".join(reason_parts) if reason_parts else f"匹配分 {score}"
    return {
        "servings_needed": servings_needed,
        "badge": badge,
        "score": score,
        "card_tone": card_tone,
        "reason_text": reason_text,
        "border_color": border_color,
        "bg_glow": bg_glow,
        "shadow_glow": shadow_glow,
        "accent_color": accent_color,
    }
