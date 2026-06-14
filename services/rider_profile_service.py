from __future__ import annotations

import datetime
from typing import Any

from auth import add_rider, load_rider_profile, load_users, save_rider_profile

PROFILE_GOAL_OPTIONS = [
    "恢复体能 / 重建基础",
    "减脂减重 / 燃脂骑",
    "提升 FTP / 功体比",
    "备战绕圈赛",
    "备战爬坡赛",
    "备战个人计时赛",
    "备战长距离耐力赛",
    "备战公路赛",
    "赛前减量 / 巅峰",
    "维持现状 / 休闲骑",
]


def normalize_profile_goal(value: Any) -> str:
    goal = str(value or "").strip()
    return goal if goal in PROFILE_GOAL_OPTIONS else PROFILE_GOAL_OPTIONS[0]


def goal_training_background(goal: str):
    goal = str(goal or "").strip()
    mapping = {
        "恢复体能 / 重建基础": ("恢复体能 / 重建基础", "计划优先恢复连续性和基础耐力，强度不急着堆高。"),
        "减脂减重 / 燃脂骑": ("减脂减重 / 燃脂骑", "计划会提高低中强度骑行占比，控制高强度密度，避免疲劳反噬。"),
        "提升 FTP / 功体比": ("提升 FTP / 功体比", "计划会围绕甜区、阈值和恢复节奏推进，重点提升可持续输出。"),
        "备战绕圈赛": ("备战绕圈赛 / 短强度", "计划会保留短强度、反复加速和恢复能力，但不连续堆高。"),
        "备战爬坡赛": ("备战爬坡赛 / 持续输出", "计划会强化阈值、甜区和功体比相关能力，控制体重变化风险。"),
        "备战个人计时赛": ("个人计时 / 稳态功率", "计划会强化稳定踏频、阈值维持和长时间姿势耐受。"),
        "备战长距离耐力赛": ("长距离耐力 / 补给耐受", "计划会优先长时间耐力、疲劳耐受和补给执行能力。"),
        "备战公路赛": ("公路赛 / 综合能力", "计划会兼顾有氧底盘、短强度、跟集团恢复和关键时刻输出。"),
        "赛前减量 / 巅峰": ("赛前减量 / 巅峰", "计划会减少训练量，保留唤醒强度，让状态更轻而不是更累。"),
        "维持现状 / 休闲骑": ("维持现状 / 休闲骑", "计划会保持规律骑行和恢复平衡，不追求激进提升。"),
    }
    return mapping.get(goal, ("训练背景待完善", "设置训练目标后，计划会自动调整训练背景和重点。"))


def profile_completeness(profile: dict) -> tuple[int, str]:
    items = [
        bool(profile.get("ftp_test") or profile.get("ftp")),
        bool(profile.get("weight")),
        bool(profile.get("goal")),
        bool(profile.get("max_hr") or profile.get("lthr")),
        bool(profile.get("notes")),
    ]
    completeness = int(sum(items) / len(items) * 100)
    missing = []
    if not (profile.get("ftp_test") or profile.get("ftp")):
        missing.append("FTP")
    if not profile.get("weight"):
        missing.append("体重")
    if not profile.get("goal"):
        missing.append("训练目标")
    if not (profile.get("max_hr") or profile.get("lthr")):
        missing.append("心率区间")
    missing_text = "，还缺" + "、".join(missing[:3]) if missing else "，基础资料已较完整"
    return completeness, missing_text


def _as_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _as_int(value, default=0):
    try:
        return int(float(value))
    except Exception:
        return default


def build_profile_from_payload(payload: dict, existing: dict | None = None) -> dict:
    profile = dict(existing or {})
    profile.update({
        "name": str(payload.get("rider_name") or payload.get("name") or "").strip(),
        "weight": _as_float(payload.get("weight"), 0.0),
        "ftp_test": _as_int(payload.get("ftp_test"), 0),
        "max_hr": _as_int(payload.get("max_hr"), 0),
        "lthr": _as_int(payload.get("lthr"), 0),
        "height": _as_int(payload.get("height"), 0),
        "goal": normalize_profile_goal(payload.get("goal")),
        "notes": str(payload.get("notes") or ""),
        "updated_at": datetime.datetime.now().isoformat(timespec="seconds"),
    })
    return profile


def profile_ui_payload(user: dict, rider: str, profile: dict) -> dict:
    completeness, missing_text = profile_completeness(profile)
    training_bg_title, training_bg_text = goal_training_background(profile.get("goal"))
    users = load_users()
    latest_user = users.get(user["user_id"], {}) if isinstance(users, dict) else {}
    rider_count = len((latest_user.get("riders") or {})) or 1
    return {
        "rider": rider,
        "rider_count": rider_count,
        "rider_count_text": f"当前账号 {rider_count}/20 位骑手" if latest_user.get("plan") == "coach" else "当前套餐支持 1 位骑手",
        "name": profile.get("name") or rider,
        "summary": f"FTP {profile.get('ftp_test') or profile.get('ftp') or '未填'}W · {profile.get('weight') or '未填'}kg · 训练目标：{profile.get('goal') or '未设置训练目标'}。资料完整度 {completeness}%{missing_text}。",
        "training_bg_title": training_bg_title,
        "training_bg_text": training_bg_text,
    }


def save_rider_profile_from_payload(user: dict, payload: dict) -> tuple[bool, dict, int]:
    mode = str(payload.get("tc_profile_mode") or "current").strip()
    target_rider = str(payload.get("target_rider") or "").strip()
    rider_name = str(payload.get("rider_name") or payload.get("name") or "").strip()

    if mode == "new":
        if user.get("plan") != "coach":
            return False, {"error": "plan_not_allowed"}, 403
        if not rider_name:
            return False, {"error": "missing_rider_name"}, 400
        ok, msg = add_rider(user["user_id"], rider_name)
        if not ok:
            return False, {"error": msg}, 400
        rider = rider_name
        users = load_users()
        user = {"user_id": user["user_id"], **users.get(user["user_id"], {})}
        existing = {}
    else:
        rider = target_rider or str(payload.get("rider") or user.get("active_rider") or "默认骑手").strip() or "默认骑手"
        existing = load_rider_profile(user["user_id"], rider)

    profile = build_profile_from_payload(payload, existing)
    save_rider_profile(user["user_id"], rider, profile)
    return True, {"profile": profile, "ui": profile_ui_payload(user, rider, profile)}, 200
