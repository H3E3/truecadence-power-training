from __future__ import annotations

import json

import streamlit as st

from auth import get_rider_data_path, save_rider_data

DAY_ORDER = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

PLAN_PREF_DEFAULTS = {
    "goal": "提升 FTP / 阈值能力",
    "weeks": 4,
    "hours": 8,
    "training_experience": "未填写",
    "historical_best_ftp": 0,
    "detraining_duration": "未填写",
    "historical_best_wkg": 0.0,
    "progression_preference": "标准",
    "event_type": "无比赛",
    "event_date": "",
    "event_priority": "B",
    "training_days": ["周二", "周三", "周五", "周六", "周日"],
    "preferred_long_day": "周日",
    "no_hard_days": [],
}


def normalize_plan_prefs(data: dict | None = None) -> dict:
    prefs = {**PLAN_PREF_DEFAULTS, **(data or {})}
    training_days = [d for d in prefs.get("training_days", []) if d in DAY_ORDER]
    prefs["training_days"] = training_days or list(PLAN_PREF_DEFAULTS["training_days"])
    if prefs.get("preferred_long_day") not in prefs["training_days"]:
        prefs["preferred_long_day"] = "周日" if "周日" in prefs["training_days"] else prefs["training_days"][-1]
    prefs["no_hard_days"] = [d for d in prefs.get("no_hard_days", []) if d in prefs["training_days"]]
    return prefs


def load_current_plan_prefs() -> dict:
    user = st.session_state.get("user")
    rider = st.session_state.get("rider", "默认骑手")
    if user:
        path = get_rider_data_path(user["user_id"], rider, "plan_prefs")
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return normalize_plan_prefs(data)
            except Exception:
                pass
    return normalize_plan_prefs({})


def save_current_plan_prefs(data: dict) -> None:
    user = st.session_state.get("user")
    rider = st.session_state.get("rider", "默认骑手")
    if user:
        save_rider_data(user["user_id"], rider, "plan_prefs", normalize_plan_prefs(data))
