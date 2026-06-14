from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import re
from typing import Any, Callable

from rules.nutrition import calculate_nutrition_targets, feedback_sets_from_recent_feedback
from services.training_calendar import WeekSession, fueling_advice_for_session, local_today


@dataclass(frozen=True)
class V2FuelingRecommendation:
    headline: str
    context_line: str
    feedback_line: str
    before: str
    during: str
    hydration: str
    after: str
    adjustment: str
    warning: str
    workout_type: str
    ride_hours: float
    carb_range: tuple[int, int]
    water_range: tuple[int, int]
    sodium_range: tuple[int, int]
    total_carb_range: tuple[int, int]
    basis: list[str]


def _infer_ride_hours(session: WeekSession) -> float:
    title = session.title or ""
    detail = session.detail or ""
    text = f"{title} {detail}"
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:小時|小时|h|H)", text)
    if match:
        return max(0.25, float(match.group(1)))
    match = re.search(r"(\d+)\s*(?:分钟|min)", text, re.I)
    if match:
        return max(0.25, round(int(match.group(1)) / 60, 2))
    if session.is_rest:
        return 0.0
    if "长距离" in title:
        return 2.0
    if "90" in title:
        return 1.5
    if "75" in title:
        return 1.25
    if "60" in title:
        return 1.0
    return 1.25


def _workout_type_for_session(session: WeekSession) -> str:
    title = session.title or ""
    if session.is_rest:
        return "恢复骑"
    if "比赛" in title:
        return "比赛/绕圈赛"
    if "VO2" in title or "间歇" in title:
        return "VO2max/间歇"
    if "甜区" in title or "阈值" in title or session.kind == "质量课":
        return "甜区/阈值"
    if "长距离" in title or session.kind == "耐力":
        return "Z2 长距离"
    if session.kind in {"低强度", "恢复"}:
        return "恢复骑" if "恢复" in title else "Z2 长距离"
    return "Z2 长距离"


def _recent_feedback(feedback: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    cutoff = today - timedelta(days=3)
    items: list[dict[str, Any]] = []
    for item in feedback or []:
        try:
            item_date = date.fromisoformat(str(item.get("date") or ""))
        except Exception:
            continue
        if cutoff <= item_date <= today:
            items.append(item)
    return sorted(items, key=lambda x: (x.get("date", ""), x.get("created_at", "")), reverse=True)[:5]


def _feedback_line(recent: list[dict[str, Any]]) -> str:
    if not recent:
        return "最近没有新的训练反馈；先按课程强度给默认建议，练后再记录反馈，明天会更准。"
    latest = recent[0]
    bits = []
    if latest.get("fueling") and latest.get("fueling") != "正常":
        bits.append(f"补给：{latest.get('fueling')}")
    if latest.get("leg_fatigue"):
        bits.append(f"腿疲劳 {latest.get('leg_fatigue')}/5")
    if latest.get("sleep_quality"):
        bits.append(f"睡眠 {latest.get('sleep_quality')}/5")
    specials = latest.get("specials") or []
    if specials:
        bits.append("特殊情况：" + "、".join(map(str, specials[:2])))
    return f"读取到 {latest.get('date', '最近')} 反馈：" + ("；".join(bits) if bits else "状态正常") + "。"


def _adjustment_from_feedback(fueling_set: set[str], special_set: set[str], session: WeekSession) -> str:
    notes: list[str] = []
    if "吃少了" in fueling_set or "低血糖感" in fueling_set:
        notes.append("上次有吃少/低血糖感：今天骑前先补 20–30g 碳水，骑中从前 20 分钟开始少量多次。")
    if "喝少了" in fueling_set:
        notes.append("上次喝少了：今天提前准备水，按下沿也至少 400–500ml/h，热天加电解质。")
    if "胃不舒服" in fueling_set:
        notes.append("上次胃不舒服：今天不要一次性猛吃，优先运动饮料/软糖/半包胶，小口分次。")
    if "天气太热" in special_set or "室内骑行" in special_set:
        notes.append("高温或室内：水和钠上调，别只补糖不补液。")
    if any(x in special_set for x in ["感冒", "发烧", "睡眠不足"]):
        notes.append("有恢复红旗：先按降级规则执行，补给服务于完成训练，不靠咖啡因硬顶。")
    if session.is_rest:
        notes.append("今天休息：正常三餐，把主食和蛋白补回来，不需要训练补给。")
    return " ".join(notes) if notes else "反馈没有明显补给红旗：按今天课程强度正常补，练后记录是否吃少、喝少或胃不舒服。"


def build_v2_fueling_recommendation(
    session: WeekSession,
    *,
    feedback: list[dict[str, Any]] | None = None,
    profile: dict[str, Any] | None = None,
    today: date | None = None,
) -> V2FuelingRecommendation:
    today = today or local_today()
    profile = profile or {}
    recent = _recent_feedback(feedback or [], today)
    special_set, fueling_set = feedback_sets_from_recent_feedback(recent)
    workout_type = _workout_type_for_session(session)
    ride_hours = _infer_ride_hours(session)
    environment = "天气太热" if "天气太热" in special_set else "室内骑行" if "室内骑行" in special_set else "正常"
    weight = float(profile.get("weight") or 69)
    targets = calculate_nutrition_targets(
        weight=weight,
        ride_hours=max(0.5, ride_hours or 0.5),
        workout_type=workout_type,
        environment=environment,
        fueling_set=fueling_set,
        feedback_count=len(recent),
    )
    base = fueling_advice_for_session(session)
    carb = (int(targets["carb_lo"]), int(targets["carb_hi"]))
    water = (int(targets["water_lo"]), int(targets["water_hi"]))
    sodium = (int(targets["sodium_lo"]), int(targets["sodium_hi"]))
    total_carb = (int(targets["total_carb_lo"]), int(targets["total_carb_hi"]))

    if session.is_rest:
        headline = "今天不用训练补给，重点是正常吃饭和恢复"
    else:
        headline = f"今天按 {workout_type} 补给：{carb[0]}–{carb[1]}g/h 碳水"

    warning = "这不是医学或减重处方；如果有持续胃肠不适、低血糖样症状、发热或疼痛，优先降级/停止训练并寻求线下专业支持。"

    return V2FuelingRecommendation(
        headline=headline,
        context_line=f"课程：{session.title}；预计 {ride_hours:g} 小时；强度类型：{workout_type}。",
        feedback_line=_feedback_line(recent),
        before=base.before,
        during=f"骑中目标：{carb[0]}–{carb[1]}g/h 碳水；预计总量 {total_carb[0]}–{total_carb[1]}g。{base.during}",
        hydration=f"喝水 {water[0]}–{water[1]}ml/h；钠 {sodium[0]}–{sodium[1]}mg/h。热天、室内或出汗大时靠近上沿；胃里顶时小口分次。",
        after=base.after,
        adjustment=_adjustment_from_feedback(fueling_set, special_set, session),
        warning=warning,
        workout_type=workout_type,
        ride_hours=ride_hours,
        carb_range=carb,
        water_range=water,
        sodium_range=sodium,
        total_carb_range=total_carb,
        basis=[
            f"今日课程：{session.kind} / {session.title}",
            f"最近反馈：{len(recent)} 条",
            f"环境修正：{environment}",
            f"体重估算：{int(weight)}kg",
        ],
    )
