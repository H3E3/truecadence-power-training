from __future__ import annotations

from datetime import date, datetime, timedelta


def _num(value, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _latest(items: list[dict], date_key: str = "date") -> dict:
    if not items:
        return {}
    return sorted(items, key=lambda x: str(x.get(date_key, "")), reverse=True)[0]


def _recent_rides(rides: list[dict], days: int = 14, today: date | None = None) -> list[dict]:
    today = today or date.today()
    cutoff = today - timedelta(days=days)
    out = []
    for ride in rides or []:
        try:
            d = datetime.fromisoformat(str(ride.get("date", ""))[:10]).date()
        except Exception:
            continue
        if d >= cutoff:
            out.append(ride)
    return out


def _feedback_flags(feedback: list[dict]) -> list[str]:
    flags: list[str] = []
    latest = _latest(feedback)
    if not latest:
        return ["还没有近期主观反馈，恢复判断会偏保守。"]
    if int(_num(latest.get("sleep_quality"), 3)) <= 2:
        flags.append("最近反馈睡眠偏差，强度课不宜硬顶。")
    if int(_num(latest.get("energy"), 3)) <= 2:
        flags.append("精神状态偏低，优先保留低强度连续性。")
    if int(_num(latest.get("leg_fatigue"), 3)) >= 4:
        flags.append("腿部疲劳偏高，质量课需要看热身反应再决定。")
    if latest.get("pains"):
        flags.append("已记录疼痛/不适，训练建议应先避开加重风险。")
    if latest.get("specials"):
        flags.append("有特殊情况记录，后续计划需要继续观察反馈。")
    return flags or ["最近主观反馈没有明显红旗。"]


def build_v2_ai_summary(
    *,
    rides: list[dict] | None = None,
    profile: dict | None = None,
    feedback: list[dict] | None = None,
    sleep_records: list[dict] | None = None,
    readiness: dict | object | None = None,
    today: date | None = None,
) -> dict:
    """Build a short V2-facing AI summary without rendering the legacy long report."""
    rides = rides or []
    profile = profile or {}
    feedback = feedback or []
    sleep_records = sleep_records or []
    today = today or date.today()

    ftp = int(_num(profile.get("ftp_test") or profile.get("ftp") or profile.get("threshold_power"), 0))
    weight = _num(profile.get("weight"), 0)
    wkg = round(ftp / weight, 1) if ftp and weight else 0
    recent = _recent_rides(rides, 14, today)
    total_recent_minutes = sum(_num(r.get("dur")) for r in recent)
    recent_tss = sum(_num(r.get("tss")) for r in recent)
    latest = _latest(rides)
    latest_tss = _num(latest.get("tss"))
    latest_dur = _num(latest.get("dur"))

    readiness_level = "未计算"
    readiness_reason = "暂无状态原因"
    if isinstance(readiness, dict):
        readiness_level = str(readiness.get("level") or readiness_level)
        readiness_reason = str(readiness.get("reason") or readiness_reason)
    elif readiness is not None:
        readiness_level = str(getattr(readiness, "level", readiness_level) or readiness_level)
        readiness_reason = str(getattr(readiness, "reason", readiness_reason) or readiness_reason)

    if not rides:
        ability = "数据不足：先上传最近 4–12 周 FIT，再判断能力结构。"
    elif ftp:
        ability = f"当前 FTP 记录为 {ftp}W" + (f"，约 {wkg} W/kg" if wkg else "") + "；先用它作为训练区间锚点，后续随新数据校准。"
    else:
        ability = f"已有 {len(rides)} 条训练摘要，但缺少可信 FTP；现阶段先保守看趋势，不急着定强度上限。"

    risks = _feedback_flags(feedback)
    if latest_tss >= 85 or latest_dur >= 150:
        risks.insert(0, "最近一次训练消耗较大，短期内不建议连续堆强度。")
    if len(recent) == 0:
        risks.append("近 14 天缺少训练记录，回归训练要先恢复连续性。")
    if not sleep_records:
        risks.append("还没有手表睡眠/恢复数据，睡眠风险只能靠主观反馈判断。")

    if "恢复" in readiness_level:
        training = "先恢复：取消结构化高强度，保留休息、恢复骑或很轻松的 Z2。"
        recovery = "优先睡眠、正常进食和疼痛/不适观察；连续 2–3 天反馈好转后再谈加量。"
    elif "谨慎" in readiness_level:
        training = "谨慎推进：本周保留训练频率，但质量课和长距离都按降级规则执行。"
        recovery = "每天记录睡眠、腿感、疼痛和补给；反馈稳定后再恢复 1 次质量课。"
    else:
        training = "可推进：保留 1 次目标刺激，其余用 Z2/恢复骑托住连续性，不临时加码。"
        recovery = "维持基础恢复：骑后补主食和蛋白，睡眠差当天直接降级。"

    if recent_tss:
        load_line = f"近 14 天约 {len(recent)} 次训练 / {round(total_recent_minutes / 60, 1)} 小时 / TSS {round(recent_tss)}。"
    else:
        load_line = "近 14 天训练负荷暂不完整。"

    next_step = "下一步：先完成今天建议，并在状态与恢复里记录反馈；系统会把反馈回流到训练计划。"
    return {
        "ability": ability,
        "risk": "；".join(risks[:3]),
        "training": training,
        "recovery": recovery,
        "next_step": next_step,
        "data_basis": f"{load_line} 当前状态：{readiness_level}，原因：{readiness_reason}。",
        "readiness_level": readiness_level,
    }
