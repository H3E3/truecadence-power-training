from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Callable

import pandas as pd

from services.training_calendar import local_today


@dataclass(frozen=True)
class TrainingReadiness:
    level: str
    headline: str
    reason: str
    intensity_cap: str
    factor: float
    flags: list[str]
    actions: list[str]
    source: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "headline": self.headline,
            "reason": self.reason,
            "intensity_cap": self.intensity_cap,
            "factor": self.factor,
            "flags": list(self.flags),
            "actions": list(self.actions),
            "source": dict(self.source),
        }


def _parse_day(value: Any) -> date | None:
    try:
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value)[:10]).date()
    except Exception:
        return None


def _recent_items(items: list[dict[str, Any]], today: date, days: int) -> list[dict[str, Any]]:
    cutoff = today - timedelta(days=days - 1)
    out: list[dict[str, Any]] = []
    for item in items or []:
        d = _parse_day(item.get("date"))
        if d and cutoff <= d <= today:
            out.append(item)
    return sorted(out, key=lambda x: (str(x.get("date") or ""), str(x.get("created_at") or "")), reverse=True)


def _avg(items: list[dict[str, Any]], key: str, *, positive_only: bool = False) -> float | None:
    vals: list[float] = []
    for item in items:
        value = item.get(key)
        if not isinstance(value, (int, float)):
            continue
        if positive_only and value <= 0:
            continue
        vals.append(float(value))
    return round(sum(vals) / len(vals), 1) if vals else None


def _flatten(items: list[dict[str, Any]], key: str) -> list[str]:
    values: list[str] = []
    for item in items:
        raw = item.get(key) or []
        if isinstance(raw, str):
            raw = [raw]
        values.extend(str(x) for x in raw if x)
    return values


def _pmc_summary(rides: list[dict[str, Any]], compute_daily_pmc_func: Callable | None, today: date) -> dict[str, Any]:
    empty = {
        "available": False,
        "ctl": 0,
        "atl": 0,
        "tsb": 0,
        "ramp_rate": 0,
        "tss_7": 0,
        "tss_28": 0,
        "hours_7": 0,
        "hours_28": 0,
        "latest_ride_date": "",
        "latest_ride_gap_days": None,
    }
    if not rides or not compute_daily_pmc_func:
        return empty
    try:
        pmc = compute_daily_pmc_func(rides)
        if pmc is None or pmc.empty:
            return empty
        latest = pmc.iloc[-1]
        ctl = int(latest.get("ctl") or 0)
        atl = int(latest.get("atl") or 0)
        tsb = int(latest.get("tsb") or 0)
        ctl_7 = float(pmc.iloc[-8].get("ctl") if len(pmc) >= 8 else pmc.iloc[0].get("ctl") or 0)
        ramp_rate = round(ctl - ctl_7, 1)
        df = pd.DataFrame(rides).copy()
        df["date_dt"] = pd.to_datetime(df.get("date"), errors="coerce").dt.normalize()
        df["duration_h"] = pd.to_numeric(df.get("dur", 0), errors="coerce").fillna(0) / 60
        latest_ride_dt = df["date_dt"].dropna().max()
        if pd.isna(latest_ride_dt):
            latest_ride_date = ""
            latest_gap = None
            recent_7 = df.tail(7)
            recent_28 = df.tail(28)
        else:
            latest_ride_date = latest_ride_dt.strftime("%Y-%m-%d")
            latest_gap = max(0, (today - latest_ride_dt.date()).days)
            recent_7 = df[df["date_dt"] >= latest_ride_dt - pd.Timedelta(days=6)]
            recent_28 = df[df["date_dt"] >= latest_ride_dt - pd.Timedelta(days=27)]
        tss_7 = int(round(float(pd.to_numeric(recent_7.get("tss", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()))) if len(recent_7) else 0
        tss_28 = int(round(float(pd.to_numeric(recent_28.get("tss", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()))) if len(recent_28) else 0
        hours_7 = float(round(float(pd.to_numeric(recent_7.get("duration_h", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()), 1)) if len(recent_7) else 0.0
        hours_28 = float(round(float(pd.to_numeric(recent_28.get("duration_h", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()), 1)) if len(recent_28) else 0.0
        return {
            "available": True,
            "ctl": ctl,
            "atl": atl,
            "tsb": tsb,
            "ramp_rate": ramp_rate,
            "tss_7": tss_7,
            "tss_28": tss_28,
            "hours_7": hours_7,
            "hours_28": hours_28,
            "latest_ride_date": latest_ride_date,
            "latest_ride_gap_days": latest_gap,
        }
    except Exception:
        return empty


def build_training_readiness(
    *,
    rides: list[dict[str, Any]] | None = None,
    feedback: list[dict[str, Any]] | None = None,
    sleep_records: list[dict[str, Any]] | None = None,
    profile: dict[str, Any] | None = None,
    compute_daily_pmc_func: Callable | None = None,
    today: date | None = None,
) -> TrainingReadiness:
    """Build the V2 lightweight training-readiness gate.

    Output is intentionally rider-facing and compact: three levels only. It is
    not a medical diagnosis and should be used to gate training intensity, not
    to explain every PMC detail on the main page.
    """
    today = today or local_today()
    rides = rides or []
    feedback = feedback or []
    sleep_records = sleep_records or []
    profile = profile or {}

    recent_feedback = _recent_items(feedback, today, 5)
    recent_sleep = _recent_items(sleep_records, today, 7)
    pmc = _pmc_summary(rides, compute_daily_pmc_func, today)

    avg_sleep = _avg(recent_feedback, "sleep_quality")
    avg_energy = _avg(recent_feedback, "energy")
    avg_fatigue = _avg(recent_feedback, "leg_fatigue")
    avg_rpe = _avg(recent_feedback, "rpe")
    watch_sleep_hours = _avg(recent_sleep, "sleep_hours", positive_only=True)
    watch_sleep_score = _avg(recent_sleep, "sleep_score", positive_only=True)
    pains = _flatten(recent_feedback, "pains")
    specials = _flatten(recent_feedback, "specials")
    fueling_flags = [str(x.get("fueling")) for x in recent_feedback if x.get("fueling") and x.get("fueling") != "正常"]
    completion_flags = [str(x.get("completion")) for x in recent_feedback if x.get("completion") and x.get("completion") not in {"正常完成", "完成"}]

    red_flags: list[str] = []
    caution_flags: list[str] = []
    good_flags: list[str] = []

    red_keywords = {"发烧", "感冒/发烧", "生病", "明显不适"}
    caution_keywords = {"感冒", "睡眠不足", "出差", "天气太热", "室内骑行"}
    if any(x in red_keywords for x in specials):
        red_flags.append("反馈出现发烧/生病，暂停结构化高强度")
    elif any(x in caution_keywords for x in specials):
        caution_flags.append("反馈存在睡眠/天气/身体状态干扰")

    if avg_sleep is not None:
        if avg_sleep <= 2.2:
            red_flags.append(f"睡眠质量 {avg_sleep}/5 偏低")
        elif avg_sleep <= 3.0:
            caution_flags.append(f"睡眠质量 {avg_sleep}/5 一般")
    if watch_sleep_hours is not None:
        if watch_sleep_hours < 5.5:
            red_flags.append(f"手表睡眠 {watch_sleep_hours}h 明显不足")
        elif watch_sleep_hours < 6.5:
            caution_flags.append(f"手表睡眠 {watch_sleep_hours}h 偏少")
    if watch_sleep_score is not None:
        if watch_sleep_score < 55:
            red_flags.append(f"睡眠评分 {watch_sleep_score} 恢复很差")
        elif watch_sleep_score < 70:
            caution_flags.append(f"睡眠评分 {watch_sleep_score} 恢复一般")

    if avg_fatigue is not None:
        if avg_fatigue >= 4.3:
            red_flags.append(f"腿部疲劳 {avg_fatigue}/5 偏高")
        elif avg_fatigue >= 3.5:
            caution_flags.append(f"腿部疲劳 {avg_fatigue}/5，强度课谨慎")
    if avg_rpe is not None and avg_rpe >= 8:
        caution_flags.append(f"近期 RPE {avg_rpe}/10 偏高")
    if completion_flags:
        caution_flags.append("近期有未完成/降级训练记录")
    if pains:
        caution_flags.append("近期有不适记录：" + "、".join(sorted(set(pains))[:3]))
    if fueling_flags:
        caution_flags.append("近期补给反馈：" + "、".join(sorted(set(fueling_flags))[:3]))

    if pmc["available"]:
        tsb = pmc["tsb"]
        atl_gap = pmc["atl"] - pmc["ctl"]
        if tsb <= -25:
            red_flags.append(f"TSB {tsb}，疲劳明显压住状态")
        elif tsb <= -12:
            caution_flags.append(f"TSB {tsb}，适合降一点强度")
        elif tsb <= 8:
            good_flags.append("TSB 在常规训练区间")
        else:
            good_flags.append("TSB 偏新鲜，可训练但不必临时加码")
        if atl_gap >= 25:
            red_flags.append(f"ATL 高于 CTL {round(atl_gap)}，近期冲得过猛")
        elif atl_gap >= 12:
            caution_flags.append(f"ATL 高于 CTL {round(atl_gap)}，疲劳正在累积")
        if pmc["ramp_rate"] >= 10:
            caution_flags.append(f"CTL 近 7 天约 +{round(pmc['ramp_rate'])}，加量偏快")
        elif pmc["ramp_rate"] <= -7:
            caution_flags.append(f"CTL 近 7 天约 {round(pmc['ramp_rate'])}，训练连续性下滑")
        if pmc["latest_ride_gap_days"] and pmc["latest_ride_gap_days"] >= 7:
            caution_flags.append(f"最新 FIT 距今天 {pmc['latest_ride_gap_days']} 天，负荷判断可信度下降")
    else:
        caution_flags.append("缺少近期 FIT/PMC，先按反馈和保守规则生成建议")

    if avg_energy is not None and avg_energy >= 4 and not red_flags and not caution_flags:
        good_flags.append("主观精神状态较好")

    if red_flags:
        level = "恢复优先"
        intensity_cap = "recovery"
        factor = 0.65
        headline = "本周先恢复，不安排结构化高强度"
        actions = ["暂停阈值、VO2、冲刺和大扭矩爬坡", "保留休息、Z1/Z2 或 30–60 分钟恢复骑", "连续观察睡眠、腿感、疼痛和身体不适"]
    elif caution_flags:
        level = "谨慎推进"
        intensity_cap = "caution"
        factor = 0.82
        headline = "本周可以练，但不要加码"
        actions = ["最多保留 1 次质量课", "其余训练用 Z2/恢复骑承接", "腿沉、睡眠差或疼痛时直接降级"]
    else:
        level = "可推进"
        intensity_cap = "normal"
        factor = 1.0
        headline = "本周可以按目标推进"
        actions = ["按本周计划执行关键训练", "强度课后记录 RPE、腿感和补给", "不要因为状态好临时连续加高强度"]
        if not good_flags:
            good_flags.append("反馈和训练负荷未见明显红旗")

    flags = red_flags + caution_flags + good_flags
    reason = "；".join(flags[:4]) if flags else "反馈和训练负荷未见明显红旗"

    source = {
        "feedback_count": len(recent_feedback),
        "sleep_count": len(recent_sleep),
        "pmc_available": bool(pmc["available"]),
        "ctl": pmc["ctl"],
        "atl": pmc["atl"],
        "tsb": pmc["tsb"],
        "ramp_rate": pmc["ramp_rate"],
        "tss_7": pmc["tss_7"],
        "tss_28": pmc["tss_28"],
        "hours_7": pmc["hours_7"],
        "hours_28": pmc["hours_28"],
        "latest_ride_date": pmc["latest_ride_date"],
        "latest_ride_gap_days": pmc["latest_ride_gap_days"],
    }

    return TrainingReadiness(
        level=level,
        headline=headline,
        reason=reason,
        intensity_cap=intensity_cap,
        factor=factor,
        flags=flags,
        actions=actions,
        source=source,
    )
