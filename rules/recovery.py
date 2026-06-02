"""Recovery/readiness rules for TrueCadence.

Pure rule helpers extracted from app.py during Stage-H code split.
Keep Streamlit, file IO, and session state out of this module.
"""
from __future__ import annotations

import datetime
from collections.abc import Callable, Iterable
from typing import Any

import pandas as pd


def _avg_numeric(items: Iterable[dict[str, Any]], key: str, *, positive_only: bool = False) -> float:
    vals = []
    for item in items:
        value = item.get(key)
        if not isinstance(value, (int, float)):
            continue
        if positive_only and value <= 0:
            continue
        vals.append(value)
    return round(sum(vals) / len(vals), 1) if vals else 0


def split_today_and_stale_records(records: list[dict[str, Any]], today: pd.Timestamp | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split dated records into today records and older records."""
    today = today or pd.Timestamp.today().normalize()
    todays_records = []
    stale_records = []
    for item in records:
        d = pd.to_datetime(item.get("date"), errors="coerce")
        if pd.notna(d) and d.normalize() == today:
            todays_records.append(item)
        elif pd.notna(d) and d.normalize() < today:
            stale_records.append(item)
    todays_records = sorted(todays_records, key=lambda x: (x.get("date", ""), x.get("created_at", "")), reverse=True)
    stale_records = sorted(stale_records, key=lambda x: (x.get("date", ""), x.get("created_at", "")), reverse=True)
    return todays_records, stale_records


def summarize_recovery_inputs(
    rides: list[dict[str, Any]],
    feedback: list[dict[str, Any]],
    sleep_records: list[dict[str, Any]],
    profile: dict[str, Any],
    *,
    compute_daily_pmc_func: Callable[[list[dict[str, Any]]], Any],
    infer_cycle_status_func: Callable[[dict[str, Any], dict[str, Any]], str | None],
    today: pd.Timestamp | None = None,
) -> dict[str, Any]:
    """Summarize FIT, subjective feedback, sleep, nap and cycle inputs for readiness rules."""
    today = today or pd.Timestamp.today().normalize()
    today_str = today.strftime("%Y-%m-%d")
    recent_feedback, stale_feedback = split_today_and_stale_records(feedback, today)
    recent_sleep_records, stale_sleep_records = split_today_and_stale_records(sleep_records, today)

    if rides:
        df = pd.DataFrame(rides).sort_values("date")
        df["date_dt"] = pd.to_datetime(df["date"], errors="coerce")
        pmc_recovery = compute_daily_pmc_func(rides)
        ctl = int(pmc_recovery.iloc[-1]["ctl"]) if not pmc_recovery.empty else 0
        atl = int(pmc_recovery.iloc[-1]["atl"]) if not pmc_recovery.empty else 0
        tsb = int(pmc_recovery.iloc[-1]["tsb"]) if not pmc_recovery.empty else 0
        latest_date_recovery = pmc_recovery["date_dt"].max() if not pmc_recovery.empty else df["date_dt"].max()
        recent14 = df[df["date_dt"] >= latest_date_recovery - pd.Timedelta(days=13)] if pd.notna(latest_date_recovery) else df.tail(14)
        recent_h = sum(r.get("dur", 0) for r in recent14.to_dict("records")) / 60
        weekly_h = round(recent_h / 2, 1)
    else:
        ctl = atl = tsb = 0
        weekly_h = 0

    avg_sleep = _avg_numeric(recent_feedback, "sleep_quality")
    avg_energy = _avg_numeric(recent_feedback, "energy")
    avg_fatigue = _avg_numeric(recent_feedback, "leg_fatigue")
    avg_stress = _avg_numeric(recent_feedback, "stress")
    avg_rpe = _avg_numeric(recent_feedback, "rpe")

    watch_sleep_hours = _avg_numeric(recent_sleep_records, "sleep_hours", positive_only=True)
    watch_sleep_score = _avg_numeric(recent_sleep_records, "sleep_score", positive_only=True)
    watch_hrv = _avg_numeric(recent_sleep_records, "hrv", positive_only=True)
    watch_rest_hr = _avg_numeric(recent_sleep_records, "rest_hr", positive_only=True)
    watch_stress = _avg_numeric(recent_sleep_records, "stress_score", positive_only=True)

    nap_records = [x for x in recent_sleep_records if x.get("nap_minutes", 0)]
    avg_nap_min = round(sum(float(x.get("nap_minutes", 0) or 0) for x in nap_records) / len(nap_records), 1) if nap_records else 0
    nap_refresh_count = sum(1 for x in nap_records if x.get("nap_after") == "更清醒")
    nap_sluggish_count = sum(1 for x in nap_records if x.get("nap_after") == "更困")
    nap_good_count = sum(1 for x in nap_records if (x.get("nap_quality", 0) or 0) >= 4)

    pain_counts: dict[str, int] = {}
    special_counts: dict[str, int] = {}
    cycle_counts: dict[str, int] = {}
    for item in recent_feedback:
        for pain in item.get("pains", []) or []:
            pain_counts[pain] = pain_counts.get(pain, 0) + 1
        for special in item.get("specials", []) or []:
            special_counts[special] = special_counts.get(special, 0) + 1
        cycle_status = infer_cycle_status_func(item, profile)
        if cycle_status:
            cycle_counts[cycle_status] = cycle_counts.get(cycle_status, 0) + 1

    return {
        "today_str": today_str,
        "recent_feedback": recent_feedback,
        "stale_feedback": stale_feedback,
        "recent_sleep_records": recent_sleep_records,
        "stale_sleep_records": stale_sleep_records,
        "ctl": ctl,
        "atl": atl,
        "tsb": tsb,
        "weekly_h": weekly_h,
        "avg_sleep": avg_sleep,
        "avg_energy": avg_energy,
        "avg_fatigue": avg_fatigue,
        "avg_stress": avg_stress,
        "avg_rpe": avg_rpe,
        "watch_sleep_hours": watch_sleep_hours,
        "watch_sleep_score": watch_sleep_score,
        "watch_hrv": watch_hrv,
        "watch_rest_hr": watch_rest_hr,
        "watch_stress": watch_stress,
        "nap_records": nap_records,
        "avg_nap_min": avg_nap_min,
        "nap_refresh_count": nap_refresh_count,
        "nap_sluggish_count": nap_sluggish_count,
        "nap_good_count": nap_good_count,
        "pain_counts": pain_counts,
        "special_counts": special_counts,
        "cycle_counts": cycle_counts,
    }


def build_recovery_advice(summary: dict[str, Any], *, ftp: float | int = 0) -> dict[str, Any]:
    """Build readiness flags, advice class and next actions from summarized recovery inputs."""
    red_flags: list[str] = []
    caution_flags: list[str] = []
    special_counts = summary.get("special_counts", {})
    cycle_counts = summary.get("cycle_counts", {})
    recent_feedback = summary.get("recent_feedback", [])
    avg_sleep = summary.get("avg_sleep", 0)
    avg_energy = summary.get("avg_energy", 0)
    avg_fatigue = summary.get("avg_fatigue", 0)
    avg_stress = summary.get("avg_stress", 0)
    avg_rpe = summary.get("avg_rpe", 0)
    watch_sleep_hours = summary.get("watch_sleep_hours", 0)
    watch_sleep_score = summary.get("watch_sleep_score", 0)
    watch_stress = summary.get("watch_stress", 0)
    nap_records = summary.get("nap_records", [])
    nap_sluggish_count = summary.get("nap_sluggish_count", 0)
    nap_refresh_count = summary.get("nap_refresh_count", 0)
    nap_good_count = summary.get("nap_good_count", 0)
    avg_nap_min = summary.get("avg_nap_min", 0)
    pain_counts = summary.get("pain_counts", {})
    tsb = summary.get("tsb", 0)
    weekly_h = summary.get("weekly_h", 0)

    if any(k in special_counts for k in ["发烧"]):
        red_flags.append("近期记录过发烧")
    if any(k in cycle_counts for k in ["经期第1-2天"]):
        latest_cycle = next((x for x in recent_feedback if x.get("cycle_status") == "经期第1-2天"), {})
        if latest_cycle.get("cycle_pain") in ["中", "重"] or latest_cycle.get("cycle_training_impact") == "明显":
            red_flags.append("经期前段且身体反应明显")
        else:
            caution_flags.append("经期前段,建议降低训练强度")
    if any(k in cycle_counts for k in ["经前期/PMS"]):
        caution_flags.append("经前期/PMS,注意睡眠、情绪和腿感波动")
    if any(k in special_counts for k in ["感冒"]):
        caution_flags.append("近期感冒/身体不适")
    if avg_sleep and avg_sleep <= 2:
        red_flags.append("睡眠质量很差")
    elif avg_sleep and avg_sleep <= 3:
        caution_flags.append("睡眠质量一般")
    if watch_sleep_hours and watch_sleep_hours < 5.5:
        red_flags.append(f"手表睡眠 {watch_sleep_hours}h,明显不足")
    elif watch_sleep_hours and watch_sleep_hours < 6.5:
        caution_flags.append(f"手表睡眠 {watch_sleep_hours}h,偏少")
    if watch_sleep_score and watch_sleep_score < 55:
        red_flags.append(f"睡眠评分 {watch_sleep_score},恢复很差")
    elif watch_sleep_score and watch_sleep_score < 70:
        caution_flags.append(f"睡眠评分 {watch_sleep_score},恢复一般")
    if watch_stress and watch_stress >= 70:
        caution_flags.append(f"手表压力 {watch_stress},自主神经压力偏高")
    if nap_records:
        if nap_sluggish_count:
            caution_flags.append("午睡后仍昏沉,下午高强度需谨慎")
        elif nap_refresh_count and 15 <= avg_nap_min <= 45 and nap_good_count:
            caution_flags.append("午睡对下午训练有小幅恢复加成,但不等同于夜间睡眠")
        elif avg_nap_min > 90:
            caution_flags.append("午睡时间较长,注意睡眠惯性和夜间睡眠节律")
    if avg_fatigue and avg_fatigue >= 5:
        red_flags.append("腿部疲劳很高")
    elif avg_fatigue and avg_fatigue >= 4:
        caution_flags.append("腿部疲劳偏高")
    if avg_rpe and avg_rpe >= 8:
        caution_flags.append("最近训练主观强度偏高")
    if avg_stress and avg_stress >= 4:
        caution_flags.append("生活/工作压力偏高")
    for pain, n in pain_counts.items():
        if n >= 2:
            caution_flags.append(f"{pain} 不适重复出现")
    if tsb < -20:
        red_flags.append(f"TSB {tsb},深度疲劳")
    elif tsb < -10:
        caution_flags.append(f"TSB {tsb},疲劳偏高")
    if weekly_h > 12:
        caution_flags.append(f"近两周周均 {weekly_h}h,训练量偏高")

    if red_flags:
        advice_class = "recovery-red"
        advice_tag = "RED FLAG"
        advice_main = "今天建议完全休息,或只做非常轻松恢复活动"
        next_action = ["取消 VO2max、阈值、冲刺和大扭矩爬坡。", "优先睡眠、补水、正常进食;发烧/明显感染时不要训练。", "如果疼痛或症状持续,先处理身体问题,不要硬顶课表。"]
    elif caution_flags:
        advice_class = "recovery-yellow"
        advice_tag = "CAUTION"
        advice_main = "今天建议降强度:Z1-Z2 恢复骑或缩短训练"
        next_action = [f"恢复骑 30-60 分钟,功率控制在 <{round(ftp*0.55) if ftp else 90}W。", "如果必须训练,把质量课改成短 Z2,不做力竭间歇。", "今晚优先睡眠,明天根据腿感和精神再决定是否恢复强度。"]
    elif tsb > 10 and avg_energy and avg_energy >= 4:
        advice_class = "recovery-blue"
        advice_tag = "READY"
        advice_main = "状态较好,可以安排关键训练或测试"
        next_action = ["适合做阈值、VO2max、FTP测试或比赛模拟。", "热身要充分,训练后及时补碳水和蛋白。", "不要因为状态好连续多天堆高强度。"]
    else:
        advice_class = "recovery-green"
        advice_tag = "NORMAL"
        advice_main = "今天可以正常训练,但保持计划内强度"
        next_action = ["按原计划训练,不额外加码。", "强度课后记录 RPE、腿感、睡眠和疼痛。", "如果热身中感觉异常疲劳,主动降为 Z2。"]

    reasons = red_flags + caution_flags
    stale_notes = []
    if not summary.get("recent_feedback") and summary.get("stale_feedback"):
        latest_feedback_date = summary["stale_feedback"][0].get("date", "")
        stale_notes.append(f"今天({summary.get('today_str')})没有新的主观反馈;旧反馈最新为 {latest_feedback_date},只展示历史,不参与今天建议")
    if not summary.get("recent_sleep_records") and summary.get("stale_sleep_records"):
        latest_sleep_date = summary["stale_sleep_records"][0].get("date", "")
        stale_notes.append(f"今天({summary.get('today_str')})没有新的手表睡眠/午睡记录;旧记录最新为 {latest_sleep_date},只展示历史,不参与今天建议")
    if not reasons:
        reasons = ["训练负荷和今天记录没有明显红旗"]

    return {
        "red_flags": red_flags,
        "caution_flags": caution_flags,
        "advice_class": advice_class,
        "advice_tag": advice_tag,
        "advice_main": advice_main,
        "next_action": next_action,
        "reasons": reasons,
        "stale_notes": stale_notes,
    }


def summarize_diagnosis_sleep_recovery(feedback_summary: dict[str, Any], sleep_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize subjective feedback and wearable sleep for AI diagnosis text."""
    feedback_lines = feedback_summary.get("lines", [])
    feedback_risk_flags = feedback_summary.get("risk_flags", [])

    sleep_records = sleep_records or []
    sleep_sorted = sorted(sleep_records, key=lambda x: x.get("date", ""), reverse=True)
    recent_sleep = []
    cutoff = datetime.date.today() - datetime.timedelta(days=14)
    for item in sleep_sorted:
        try:
            if datetime.date.fromisoformat(str(item.get("date"))) >= cutoff:
                recent_sleep.append(item)
        except Exception:
            continue
    if not recent_sleep:
        recent_sleep = sleep_sorted[:5]

    def sleep_avg(key):
        vals = [x.get(key) for x in recent_sleep if isinstance(x.get(key), (int, float)) and x.get(key) > 0]
        return round(sum(vals) / len(vals), 1) if vals else 0

    sleep_avg_hours = sleep_avg("sleep_hours")
    sleep_avg_score = sleep_avg("sleep_score")
    sleep_avg_hrv = sleep_avg("hrv")
    sleep_avg_rest_hr = sleep_avg("rest_hr")
    sleep_avg_stress = sleep_avg("stress_score")
    sleep_avg_body_battery = sleep_avg("body_battery")
    latest_sleep = sleep_sorted[0] if sleep_sorted else {}
    sleep_lines: list[str] = []
    sleep_risk_flags: list[str] = []
    if recent_sleep:
        nap_items = [x for x in recent_sleep if x.get("nap_minutes", 0)]
        avg_nap = round(sum(float(x.get("nap_minutes", 0) or 0) for x in nap_items) / len(nap_items), 1) if nap_items else 0
        nap_refresh = sum(1 for x in nap_items if x.get("nap_after") == "更清醒")
        nap_sluggish = sum(1 for x in nap_items if x.get("nap_after") == "更困")
        nap_phrase = f",午睡 {len(nap_items)} 次,平均 **{avg_nap}min**,更清醒 {nap_refresh} 次,更困 {nap_sluggish} 次" if nap_items else ""
        sleep_lines.append(f"最近 {len(recent_sleep)} 条手表睡眠:平均夜间睡眠 **{sleep_avg_hours or '-'}h**,评分 **{sleep_avg_score or '-'}**,HRV **{sleep_avg_hrv or '-'}**,静息心率 **{sleep_avg_rest_hr or '-'}**,压力 **{sleep_avg_stress or '-'}**,Body Battery/恢复分 **{sleep_avg_body_battery or '-'}**{nap_phrase}。")
        if nap_items:
            if nap_sluggish:
                sleep_risk_flags.append("午睡后仍昏沉,下午训练不宜直接上高强度。")
            elif nap_refresh and 15 <= avg_nap <= 45:
                sleep_lines.append("短午睡且醒后更清醒,可作为下午训练准备度的小幅加成,但不能完全抵消夜间睡眠债。")
        if sleep_avg_hours and sleep_avg_hours < 5.5:
            sleep_risk_flags.append(f"平均睡眠 {sleep_avg_hours}h,明显不足,质量课建议下调或取消。")
        elif sleep_avg_hours and sleep_avg_hours < 6.5:
            sleep_risk_flags.append(f"平均睡眠 {sleep_avg_hours}h,偏少,高强度训练需谨慎。")
        if sleep_avg_score and sleep_avg_score < 55:
            sleep_risk_flags.append(f"睡眠评分 {sleep_avg_score},恢复很差,优先恢复而非加训练量。")
        elif sleep_avg_score and sleep_avg_score < 70:
            sleep_risk_flags.append(f"睡眠评分 {sleep_avg_score},恢复一般,避免连续高强度。")
        if sleep_avg_stress and sleep_avg_stress >= 70:
            sleep_risk_flags.append(f"压力分 {sleep_avg_stress},自主神经压力偏高,训练日应保守。")
        if sleep_avg_body_battery and sleep_avg_body_battery < 35:
            sleep_risk_flags.append(f"恢复分 {sleep_avg_body_battery},恢复储备偏低。")
        if not sleep_risk_flags:
            sleep_lines.append("手表睡眠未见明显红旗,可作为正常训练的辅助确认。")
    else:
        sleep_lines.append("暂未录入手表睡眠数据;AI 恢复判断主要依赖训练反馈和训练负荷。")

    feedback_badge = ""
    if feedback_summary.get("count", 0):
        feedback_badge = f"\n> ✅ 本报告已纳入最近 **{feedback_summary.get('count', 0)}** 条训练反馈,最新记录:**{feedback_summary.get('last_date', '未知')}**。\n"
    else:
        feedback_badge = "\n> ⚠️ 本报告暂未读取到训练反馈,恢复和疼痛判断主要来自功率数据。\n"

    sleep_badge = f"> ✅ 本报告已纳入 **{len(recent_sleep)}** 条手表睡眠/恢复记录,最新记录:**{latest_sleep.get('date', '未知')}**。\n" if recent_sleep else "> ⚠️ 本报告暂未读取到手表睡眠/恢复记录。\n"
    combined_recovery_flags = (feedback_risk_flags or []) + (sleep_risk_flags or [])

    return {
        "feedback_lines": feedback_lines,
        "feedback_risk_flags": feedback_risk_flags,
        "sleep_lines": sleep_lines,
        "sleep_risk_flags": sleep_risk_flags,
        "feedback_badge": feedback_badge,
        "sleep_badge": sleep_badge,
        "combined_recovery_flags": combined_recovery_flags,
        "recent_sleep_count": len(recent_sleep),
        "latest_sleep": latest_sleep,
    }
