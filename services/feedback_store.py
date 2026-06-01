from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd


def _read_list(path):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
    except Exception:
        return []
    return []


def load_beta_feedback_from_file(path):
    return _read_list(path)


def save_beta_feedback_to_file(items, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load_feedback_for_rider(user, rider, get_rider_data_path, get_user_dir, trim_func):
    if not user:
        return []
    try:
        p = get_rider_data_path(user["user_id"], rider, "feedback")
        if os.path.exists(p):
            data = _read_list(p)
            return trim_func(data)
    except Exception:
        pass

    merged = []
    try:
        user_dir = get_user_dir(user["user_id"])
        for fp in Path(user_dir).glob("feedback_*.json"):
            merged.extend(_read_list(fp))
        if merged:
            by_date = {}
            for item in merged:
                key = item.get("date") or item.get("created_at") or str(len(by_date))
                by_date[key] = item
            return sorted(by_date.values(), key=lambda x: (x.get("date", ""), x.get("created_at", "")), reverse=True)
    except Exception:
        pass
    return []


def save_feedback_for_rider(data, user, rider, save_rider_data):
    if not user:
        return
    save_rider_data(user["user_id"], rider, "feedback", data)


def load_wearable_sleep_for_rider(user, rider, get_rider_data_path):
    if not user:
        return []
    try:
        p = get_rider_data_path(user["user_id"], rider, "wearable_sleep")
        return _read_list(p)
    except Exception:
        return []


def save_wearable_sleep_for_rider(data, user, rider, save_rider_data):
    if not user:
        return
    save_rider_data(user["user_id"], rider, "wearable_sleep", data)


def infer_cycle_status_for_date(item, profile=None):
    """Return explicit or profile-inferred female cycle status."""
    if isinstance(item, pd.Timestamp):
        target_date = item
        explicit = None
    else:
        try:
            import datetime as _dt
            is_date = isinstance(item, _dt.date)
        except Exception:
            is_date = False
        if is_date:
            target_date = item
            explicit = None
        else:
            explicit = item.get("cycle_status")
            if explicit and explicit != "不记录":
                return explicit
            target_date = pd.to_datetime(item.get("date"), errors="coerce")
            if pd.isna(target_date):
                return ""
    profile = profile or {}
    if not profile.get("cycle_enabled"):
        return ""
    last_start = profile.get("cycle_last_start") or ""
    if not last_start:
        return ""
    try:
        target_dt = pd.Timestamp(target_date)
        start = pd.to_datetime(last_start, errors="coerce")
        if pd.isna(target_dt) or pd.isna(start):
            return ""
        cycle_len = int(profile.get("cycle_length") or 28)
        period_days = int(profile.get("period_days") or 5)
        day = ((target_dt.normalize() - start.normalize()).days % cycle_len) + 1
        if day <= 2:
            return "经期第1-2天"
        if day <= period_days:
            return f"经期第3-{period_days}天"
        if day <= period_days + 3:
            return "经期后恢复期"
        if abs(day - round(cycle_len / 2)) <= 2:
            return "排卵期附近"
        if day >= cycle_len - 5:
            return "经前期/PMS"
        return "周期正常,无明显影响"
    except Exception:
        return ""


def summarize_recent_feedback(feedback, profile=None, days=14):
    if not feedback:
        return {"count": 0, "lines": ["最近没有训练反馈记录;恢复、疼痛和生病风险只能根据功率数据间接判断。"], "risk_flags": [], "last_date": ""}

    today = pd.Timestamp.today().normalize()
    profile = profile or {}
    recent = []
    for item in feedback:
        try:
            d = pd.to_datetime(item.get("date"), errors="coerce")
        except Exception:
            d = pd.NaT
        if pd.notna(d) and (today - d.normalize()).days <= days:
            recent.append(item)
    if not recent:
        recent = sorted(feedback, key=lambda x: x.get("date", ""), reverse=True)[:5]

    def avg(key):
        vals = [x.get(key) for x in recent if isinstance(x.get(key), (int, float))]
        return round(sum(vals) / len(vals), 1) if vals else 0

    pain_counts, special_counts, cycle_counts = {}, {}, {}
    for item in recent:
        for pain in item.get("pains", []) or []:
            pain_counts[pain] = pain_counts.get(pain, 0) + 1
        for special in item.get("specials", []) or []:
            special_counts[special] = special_counts.get(special, 0) + 1
        cycle_status = infer_cycle_status_for_date(item, profile)
        if cycle_status:
            cycle_counts[cycle_status] = cycle_counts.get(cycle_status, 0) + 1

    risk_flags = []
    avg_sleep = avg("sleep_quality")
    avg_fatigue = avg("leg_fatigue")
    avg_rpe = avg("rpe")
    avg_stress = avg("stress")
    if avg_sleep and avg_sleep <= 2.5:
        risk_flags.append("近期睡眠偏差,建议降低高强度密度。")
    if avg_fatigue and avg_fatigue >= 4:
        risk_flags.append("腿部疲劳偏高,下一次质量课前应优先恢复。")
    if avg_rpe and avg_rpe >= 8:
        risk_flags.append("主观强度偏高,注意不要把每次训练都骑成比赛。")
    if avg_stress and avg_stress >= 4:
        risk_flags.append("生活/工作压力偏高,训练恢复储备可能不足。")
    if any(k in special_counts for k in ["感冒", "发烧"]):
        risk_flags.append("近期记录过感冒/发烧,恢复前不建议做 VO2max 或阈值课。")
    if any(k in cycle_counts for k in ["经期第1-2天", "经前期/PMS"]):
        risk_flags.append("近期处在经期前段或经前期,建议结合腹痛、睡眠和腿疲劳调整强度。")
    for pain, n in pain_counts.items():
        if n >= 2:
            risk_flags.append(f"{pain} 不适重复出现 {n} 次,需关注训练量、姿势设定或装备因素。")

    top_pains = "、".join(f"{k}×{v}" for k, v in sorted(pain_counts.items(), key=lambda kv: kv[1], reverse=True)[:4]) or "无明显疼痛记录"
    top_specials = "、".join(f"{k}×{v}" for k, v in sorted(special_counts.items(), key=lambda kv: kv[1], reverse=True)[:4]) or "无特殊情况记录"
    top_cycles = "、".join(f"{k}×{v}" for k, v in sorted(cycle_counts.items(), key=lambda kv: kv[1], reverse=True)[:4]) or "未记录"
    last_date = max((x.get("date", "") for x in recent), default="")
    lines = [
        f"最近反馈:**{len(recent)}** 条,最新记录 **{last_date or '未知日期'}**。",
        f"平均睡眠/精神/腿疲劳/压力/RPE:**{avg_sleep or '-'} / {avg('energy') or '-'} / {avg_fatigue or '-'} / {avg_stress or '-'} / {avg_rpe or '-'}**。",
        f"不适记录:{top_pains}。",
        f"特殊情况:{top_specials}。",
        f"女性周期:{top_cycles}。",
    ]
    if risk_flags:
        lines.append("主观风险:" + ";".join(risk_flags[:5]))
    else:
        lines.append("主观风险:近期没有明显红旗,但仍建议关键强度课后持续记录。")
    return {"count": len(recent), "lines": lines, "risk_flags": risk_flags, "last_date": last_date}
