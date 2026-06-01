"""TrueCadence training plan rules layer.

This module converts distilled cycling-training knowledge into stable, code-callable
rules for the Streamlit app. It intentionally stores executable rules instead of
asking the app to read long markdown references at runtime.

Knowledge basis (distilled, not runtime-read):
- cycling-training-assistant/references/workout-design.md
- cycling-training-assistant/references/periodization.md
- cycling-training-assistant/references/power-zones.md
- cycling-training-assistant/references/friel-key-concepts.md
- cycling-training-assistant/references/coggan-key-concepts.md
- /Users/hk/Documents/骑行资料/学习视频/_pdf_ocr/功率训练完全指南_精密吸收.md
- /Users/hk/Documents/骑行资料/学习视频/_pdf_ocr/Coggan功率训练_精密吸收.md
- /Users/hk/Documents/骑行资料/学习视频/_pdf_ocr/功率训练突破_精密吸收.md
- /Users/hk/Documents/骑行资料/学习视频/_pdf_ocr/运动医学建议_Ch3_精密吸收.md

Public-facing note: do not expose real source/blogger names in customer copy.
Use neutral wording like "训练规则层 / 踏频单车方法论".
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

DAY_ORDER = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
HARD_KINDS = {"sweet", "threshold", "vo2", "crit", "climb", "openers", "race"}


@dataclass
class RuleSession:
    kind: str
    name: str
    detail: str
    share: float = 1.0
    min: float = 0.5
    max: float = 2.0
    source_tags: tuple[str, ...] = ()

    def to_app_item(self) -> dict[str, Any]:
        d = asdict(self)
        # App currently expects mutable dict with keys kind/name/detail/share/min/max.
        return d


@dataclass
class RiderStateV1:
    """Stage-A anti-conflict state for automatic plan generation.

    This is deliberately small: it protects readiness, FTP confidence and
    forbidden modules before later MMP/event/cadence features are allowed to
    steer the plan.
    """
    readiness: str
    readiness_factor: float
    readiness_reasons: list[str]
    ftp_status: str
    ftp_reasons: list[str]
    data_warnings: list[str]
    forbidden_modules: list[str]


def _num(x: Any) -> float:
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def assess_plan_data_confidence(
    *,
    ftp: float | int = 0,
    ftp_source: str = "",
    best_powers: dict[str, Any] | None = None,
    rides_count: int = 0,
) -> dict[str, Any]:
    """Stage-A data confidence gate.

    Conservative rules:
    - Missing MMP windows never mean weakness.
    - Auto-estimated FTP is a candidate/working baseline, not a confirmed FTP.
    - A strong 20min value without 40/60min support should not globally raise FTP.
    """
    best_powers = best_powers or {}
    ftp = _num(ftp)
    src = (ftp_source or "").lower()
    p5s = _num(best_powers.get("5s") or best_powers.get("5sec"))
    p1 = _num(best_powers.get("1min"))
    p5m = _num(best_powers.get("5min"))
    p20 = _num(best_powers.get("20min"))
    p40 = _num(best_powers.get("40min"))
    p60 = _num(best_powers.get("60min"))
    core_windows = [p5s, p1, p5m, p20, p40, p60]
    present = sum(1 for v in core_windows if v > 0)
    data_warnings: list[str] = []
    ftp_reasons: list[str] = []

    if present >= 5 and rides_count >= 4:
        mmp_confidence = "高"
    elif present >= 3 or rides_count >= 3:
        mmp_confidence = "中"
    elif present > 0:
        mmp_confidence = "低"
        data_warnings.append("功率曲线窗口不足:只用于保守提示,不把缺失窗口判为短板。")
    else:
        mmp_confidence = "无"
        data_warnings.append("暂无可用MMP窗口:不判断能力短板。")

    source_is_manual = any(k in src for k in ("实测", "客户填写", "manual", "test", "confirmed"))
    source_is_auto = any(k in src for k in ("自动", "估算", "fit", "auto"))
    if ftp <= 0:
        ftp_status = "unknown"
        ftp_reasons.append("缺少FTP:只能生成保守课表。")
    elif source_is_manual:
        ftp_status = "confirmed"
        ftp_reasons.append("使用用户填写/实测FTP作为训练基准。")
    elif source_is_auto:
        ftp_status = "candidate"
        ftp_reasons.append("当前FTP来自自动估算:作为候选训练基准,不视为已确认。")
    else:
        ftp_status = "candidate"
        ftp_reasons.append("FTP来源未明确:按候选基准保守处理。")

    if ftp > 0 and p20 >= ftp * 1.05 and max(p40, p60) <= 0:
        if ftp_status == "confirmed":
            ftp_status = "candidate_up"
        else:
            ftp_status = "candidate"
        ftp_reasons.append("20min证据偏强但缺少40/60min支撑:不直接上调全局FTP。")
        data_warnings.append("20min强、40/60min缺失:优先安排TTE/开放式感受,避免强行提FTP。")
    if ftp > 0 and p60 > 0 and p60 < ftp * 0.88:
        ftp_status = "suspected_high"
        ftp_reasons.append("60min支撑明显低于当前FTP:课表强度需保守。")
    elif ftp > 0 and p40 > 0 and p40 < ftp * 0.90 and p60 <= 0:
        ftp_status = "suspected_high"
        ftp_reasons.append("40min支撑偏低且缺60min证据:课表强度需保守。")

    return {
        "mmp_confidence": mmp_confidence,
        "ftp_status": ftp_status,
        "ftp_reasons": ftp_reasons,
        "data_warnings": data_warnings,
        "present_windows": present,
    }


def build_rider_state_v1(
    *,
    ftp: float | int = 0,
    ftp_source: str = "",
    best_powers: dict[str, Any] | None = None,
    rides_count: int = 0,
    base_cap: str = "normal",
    current_tsb: float | int = 0,
    current_ctl: float | int = 0,
    current_atl: float | int = 0,
    ramp_rate: float | int = 0,
    avg_sleep: float | None = None,
    avg_fatigue: float | None = None,
    pain_items: list[str] | None = None,
    special_items: list[str] | None = None,
) -> RiderStateV1:
    """Build the Stage-A anti-conflict state used by the plan builder."""
    cap, factor, readiness_reasons = refined_readiness_cap(
        base_cap=base_cap,
        current_tsb=current_tsb,
        current_ctl=current_ctl,
        current_atl=current_atl,
        ramp_rate=ramp_rate,
        avg_sleep=avg_sleep,
        avg_fatigue=avg_fatigue,
        pain_items=pain_items,
        special_items=special_items,
    )
    confidence = assess_plan_data_confidence(
        ftp=ftp, ftp_source=ftp_source, best_powers=best_powers, rides_count=rides_count
    )
    forbidden: set[str] = set()
    pain_text = " ".join(pain_items or [])
    if any(k in pain_text for k in ("膝", "髋", "腰", "跟腱", "胯")):
        forbidden.add("low_cadence_torque")
    if cap == "recovery":
        forbidden.update({"ftp_test", "matchbook", "low_cadence_torque"})
    if confidence["ftp_status"] in {"unknown", "suspected_high", "candidate", "candidate_up"}:
        forbidden.add("ftp_test")
    if confidence["ftp_status"] in {"unknown", "suspected_high"}:
        forbidden.add("max_vo2_density")

    return RiderStateV1(
        readiness=cap,
        readiness_factor=factor,
        readiness_reasons=readiness_reasons,
        ftp_status=confidence["ftp_status"],
        ftp_reasons=confidence["ftp_reasons"],
        data_warnings=confidence["data_warnings"],
        forbidden_modules=sorted(forbidden),
    )


def _w(ftp: float | int, frac: float) -> int:
    return round((ftp or 0) * frac)


def refined_readiness_cap(
    *,
    base_cap: str = "normal",
    current_tsb: float | int = 0,
    current_ctl: float | int = 0,
    current_atl: float | int = 0,
    ramp_rate: float | int = 0,
    avg_sleep: float | None = None,
    avg_fatigue: float | None = None,
    resting_hr_delta: float | None = None,
    pain_items: list[str] | None = None,
    special_items: list[str] | None = None,
) -> tuple[str, float, list[str]]:
    """Distilled readiness gate from PMC + Friel/Coggan/Luo + sports-medicine notes.

    Returns (intensity_cap, readiness_factor, reasons). This is intentionally
    conservative: it gates intensity density, not medical diagnosis.
    """
    cap_order = {"normal": 0, "caution": 1, "recovery": 2}
    cap = base_cap if base_cap in cap_order else "normal"
    factor = 1.0
    reasons: list[str] = []
    pain_items = pain_items or []
    special_items = special_items or []

    def raise_cap(new_cap: str, new_factor: float, reason: str) -> None:
        nonlocal cap, factor
        if cap_order[new_cap] > cap_order[cap]:
            cap = new_cap
        factor = min(factor, new_factor)
        reasons.append(reason)

    # Coggan/Friel: TSB is relative, but long efforts generally need freshness;
    # Friel peak target +15~+25, and CTL should not fall >10% during taper.
    if current_tsb <= -25:
        raise_cap("recovery", 0.65, "TSB≤-25:疲劳很深,高强度替换为恢复/Z2")
    elif current_tsb <= -12:
        raise_cap("caution", 0.82, "TSB<-12:可以训练但不宜堆高强度密度")
    if current_atl and current_ctl and current_atl > current_ctl + 10:
        raise_cap("caution", 0.85, "ATL明显高于CTL:短期疲劳偏高")
    if ramp_rate > 8:
        raise_cap("caution", 0.9, "CTL近一周上升>8:加量偏快")

    # 罗誉寅:晨脉高于均值7bpm以上,不适合高强度。
    if resting_hr_delta is not None and resting_hr_delta >= 7:
        raise_cap("recovery", 0.65, "晨脉较基线+7bpm以上:不安排高强度")
    elif resting_hr_delta is not None and resting_hr_delta >= 4:
        raise_cap("caution", 0.85, "晨脉较基线升高:谨慎推进")

    if avg_sleep is not None and avg_sleep <= 2.2:
        raise_cap("recovery", 0.65, "睡眠评分很低:恢复优先")
    elif avg_sleep is not None and avg_sleep <= 3:
        raise_cap("caution", 0.85, "睡眠一般:降低强度密度")
    if avg_fatigue is not None and avg_fatigue >= 4.3:
        raise_cap("recovery", 0.65, "腿部疲劳很高:恢复优先")
    elif avg_fatigue is not None and avg_fatigue >= 3.5:
        raise_cap("caution", 0.85, "腿部疲劳偏高:质量课降级")

    # Sports medicine notes: illness, cramping/stiffness, poor sleep/mood are red flags.
    if any(x in special_items for x in ["感冒/发烧", "生病", "胸闷", "头晕"]):
        raise_cap("recovery", 0.55, "生病/异常症状:暂停高强度")
    if pain_items:
        raise_cap("caution", 0.85, "有疼痛反馈:不做激进强度叠加")

    return cap, factor, reasons



def _level_from_wkg(value: float, bands: tuple[float, ...]) -> int:
    """Return 1-5 ability level from conservative W/kg bands."""
    if value <= 0:
        return 0
    level = 1
    for band in bands:
        if value >= band:
            level += 1
    return min(level, 5)


def analyze_power_profile(*, ftp: float | int, weight: float | int, best_powers: dict[str, Any] | None = None) -> dict[str, Any]:
    """Second-batch rule draft: Coggan-style power profile.

    Uses 5s/1min/5min/FTP W/kg to classify relative rider type. This is not
    the official Coggan table; it is a conservative TrueCadence internal layer
    for coaching direction and should be presented as "功率画像" not ranking.
    """
    best_powers = best_powers or {}
    weight = float(weight or 0)
    ftp = float(ftp or 0)
    keys = ("5s", "1min", "5min", "ftp")
    watts = {
        "5s": float(best_powers.get("5s") or best_powers.get("5sec") or 0),
        "1min": float(best_powers.get("1min") or 0),
        "5min": float(best_powers.get("5min") or 0),
        "ftp": ftp,
    }
    wkg = {k: round(v / weight, 2) if weight and v else 0 for k, v in watts.items()}
    levels = {
        "5s": _level_from_wkg(wkg["5s"], (8.0, 10.5, 13.0, 15.5)),
        "1min": _level_from_wkg(wkg["1min"], (4.5, 5.8, 7.0, 8.2)),
        "5min": _level_from_wkg(wkg["5min"], (3.0, 3.8, 4.6, 5.4)),
        "ftp": _level_from_wkg(wkg["ftp"], (2.5, 3.2, 4.0, 4.8)),
    }
    valid = {k: v for k, v in levels.items() if v > 0}
    if not valid:
        return {"type": "数据不足", "confidence": "低", "wkg": wkg, "levels": levels, "strengths": [], "weaknesses": [], "notes": ["缺少5s/1min/5min/FTP功率证据,暂不判断车手类型。"], "recommendations": ["继续积累含功率计的骑行数据。"]}
    avg = sum(valid.values()) / len(valid)
    strengths = [k for k, v in valid.items() if v >= avg + 0.8]
    weaknesses = [k for k, v in valid.items() if v <= avg - 0.8]
    rider_type = "全能型"
    if levels["5s"] >= avg + 0.8 and levels["ftp"] <= avg + 0.3:
        rider_type = "冲刺型"
    elif levels["1min"] >= avg + 0.8:
        rider_type = "追逐/突围型"
    elif levels["5min"] >= avg + 0.5 and levels["ftp"] >= avg + 0.3 and levels["5s"] <= avg:
        rider_type = "爬坡/TT型"
    elif levels["ftp"] >= avg + 0.8 and levels["5s"] <= avg:
        rider_type = "耐力阈值型"
    notes = []
    if strengths:
        notes.append("相对强项:" + "、".join(strengths) + "。")
    if weaknesses:
        notes.append("相对短板:" + "、".join(weaknesses) + "。")
    if not notes:
        notes.append("四个核心时长相对均衡,适合按目标比赛类型微调。")
    rec_map = {
        "冲刺型": ["保留短冲/神经肌肉刺激,同时补FTP与5min支撑。", "绕圈赛策略宜减少无谓拉扯,把火柴留给关键位置。"],
        "追逐/突围型": ["适合加入1-3min无氧耐力与反复追击课。", "需要用Z2/甜区提高多次出力后的恢复速度。"],
        "爬坡/TT型": ["优先维持FTP和5min,补一点起跳/变速能力。", "长爬或TT要强调开局保守、后程稳定。"],
        "耐力阈值型": ["适合甜区、阈值和长距离容量递进。", "若要绕圈赛表现,需额外补短时加速能力。"],
        "全能型": ["基础能力均衡,按近期目标选择专项块。", "避免每种能力都练一点但缺少主线。"],
    }
    confidence = "高" if all(wkg[k] for k in keys) else ("中" if len(valid) >= 3 else "低")
    return {"type": rider_type, "confidence": confidence, "wkg": wkg, "levels": levels, "strengths": strengths, "weaknesses": weaknesses, "notes": notes, "recommendations": rec_map.get(rider_type, [])}


def analyze_aerobic_decoupling(*, first_half_power: float | int = 0, second_half_power: float | int = 0, first_half_hr: float | int = 0, second_half_hr: float | int = 0, duration_h: float | int = 0) -> dict[str, Any]:
    """Second-batch rule draft: EF/decoupling for long steady rides."""
    p1, p2, h1, h2 = map(lambda x: float(x or 0), (first_half_power, second_half_power, first_half_hr, second_half_hr))
    duration_h = float(duration_h or 0)
    if min(p1, p2, h1, h2) <= 0 or duration_h < 1.0:
        return {"status": "数据不足", "decoupling_pct": None, "ef_first": None, "ef_second": None, "notes": ["需要至少约1小时且同时有功率/心率的稳定骑行,才能判断EF/解耦。"], "recommendations": ["选择Z2长距离或稳定耐力骑作为观察样本。"]}
    ef1 = p1 / h1
    ef2 = p2 / h2
    dec = (ef1 - ef2) / ef1 * 100 if ef1 else 0
    if dec <= 5:
        status = "有氧稳定"
        rec = ["当前Z2耐力承接较好,可以小幅增加容量或加入甜区。"]
    elif dec <= 8:
        status = "轻度解耦"
        rec = ["有氧基础可用但后程有漂移,优先稳定Z2和补给节奏。"]
    elif dec <= 12:
        status = "明显解耦"
        rec = ["暂不急着加高强度密度,先提高长距离Z2耐受和补给执行。"]
    else:
        status = "解耦偏高"
        rec = ["建议降低长距离强度,检查睡眠、热应激、补水补糖和近期负荷。"]
    notes = [f"前半EF {ef1:.2f},后半EF {ef2:.2f},估算解耦 {dec:.1f}%。"]
    return {"status": status, "decoupling_pct": round(dec, 1), "ef_first": round(ef1, 2), "ef_second": round(ef2, 2), "notes": notes, "recommendations": rec}


def analyze_matchbook(*, ftp: float | int, best_powers: dict[str, Any] | None = None, event: str = "crit") -> dict[str, Any]:
    """Second-batch rule draft: FRC/PMAX/matchbook proxy.

    Uses available short-power ratios as a safe proxy. It does not claim to
    calculate real WKO FRC/PMAX; it gives coaching direction for repeated surges.
    """
    best_powers = best_powers or {}
    ftp = float(ftp or 0)
    if ftp <= 0:
        return {"status": "数据不足", "notes": ["缺少FTP,无法判断火柴盒。"], "recommendations": ["先填写或估算FTP。"]}
    p5 = float(best_powers.get("5s") or 0)
    p1 = float(best_powers.get("1min") or 0)
    p5m = float(best_powers.get("5min") or 0)
    ratios = {"pmax_ratio": round(p5 / ftp, 2) if p5 else 0, "one_min_ratio": round(p1 / ftp, 2) if p1 else 0, "five_min_ratio": round(p5m / ftp, 2) if p5m else 0}
    notes = []
    rec = []
    if ratios["one_min_ratio"] >= 2.0:
        status = "短时火柴充足"
        rec.append("可考虑关键位置主动跟跳/短突围,但避免早段反复无意义消耗。")
    elif ratios["one_min_ratio"] >= 1.6:
        status = "火柴中等"
        rec.append("适合跟随关键动作,主动进攻要控制次数。")
    else:
        status = "火柴偏少"
        rec.append("更适合稳住位置、少拉风,把输出留给爬坡/终点前关键段。")
    if ratios["pmax_ratio"] and ratios["pmax_ratio"] < 4.0:
        rec.append("冲刺峰值不突出,终点策略应更重视提前位置和速度。")
    if ratios["five_min_ratio"] >= 1.18:
        rec.append("5min支撑较好,中长追击/爬坡段可作为优势窗口。")
    notes.append(f"短时比值:5s/FTP {ratios['pmax_ratio']},1min/FTP {ratios['one_min_ratio']},5min/FTP {ratios['five_min_ratio']}。")
    notes.append("这是火柴盒代理判断,不是WKO FRC/PMAX精确模型。")
    return {"status": status, "ratios": ratios, "notes": notes, "recommendations": rec}


def choose_mmp_training_focus(
    *,
    phase: str,
    ftp: float | int = 0,
    best_powers: dict[str, Any] | None = None,
    mmp_confidence: str = "低",
    readiness: str = "normal",
    ftp_status: str = "confirmed",
) -> dict[str, Any]:
    """Stage-B conservative MMP focus selector.

    It may suggest a focus only when the data and safety gates allow it. Missing
    MMP windows never create a weakness prescription.
    """
    best_powers = best_powers or {}
    ftp = _num(ftp)
    notes: list[str] = []
    if readiness != "normal":
        return {"focus": "readiness_first", "allowed": False, "notes": ["恢复/谨慎状态优先,MMP短板暂不驱动课表。"]}
    if ftp_status not in {"confirmed", "candidate_up"}:
        return {"focus": "ftp_first", "allowed": False, "notes": ["FTP未确认或疑似偏高,MMP短板只提示不改课。"]}
    if mmp_confidence not in {"高", "中"} or ftp <= 0:
        return {"focus": "insufficient_data", "allowed": False, "notes": ["MMP证据不足,不把缺失窗口当短板。"]}

    p1 = _num(best_powers.get("1min"))
    p5 = _num(best_powers.get("5min"))
    p20 = _num(best_powers.get("20min"))
    p40 = _num(best_powers.get("40min"))
    p60 = _num(best_powers.get("60min"))
    one_ratio = p1 / ftp if p1 and ftp else 0
    five_ratio = p5 / ftp if p5 and ftp else 0

    if phase == "crit" and one_ratio and one_ratio < 1.60:
        return {"focus": "matchbook", "allowed": True, "notes": [f"1min/FTP≈{one_ratio:.2f},绕圈赛优先补反复短出力,但不覆盖恢复门控。"]}
    if phase in {"build", "climb", "crit"} and five_ratio and five_ratio < 1.12:
        return {"focus": "vo2", "allowed": True, "notes": [f"5min/FTP≈{five_ratio:.2f},可加入保守VO2刺激。"]}
    if p20 and p20 >= ftp * 1.02 and max(p40, p60) > 0 and max(p40, p60) < ftp * 0.95:
        return {"focus": "tte", "allowed": True, "notes": ["20min较强但40/60min支撑不足,优先TTE/甜区阈值持续,不直接改FTP。"]}
    return {"focus": "balanced", "allowed": False, "notes": ["MMP未触发明确保守短板,按原阶段主线执行。"]}



def build_progression_state_v1(
    *,
    goal: str = "",
    current_ftp: float | int = 0,
    weight: float | int = 0,
    recent_rides_count: int = 0,
    recent_weekly_hours: float | int = 0,
    rider_state: RiderStateV1 | None = None,
    mmp_confidence: str = "低",
    cadence_state: dict[str, Any] | None = None,
    event_context: dict[str, Any] | None = None,
    training_experience: str = "未填写",
    detraining_duration: str = "未填写",
    historical_best_ftp: float | int | None = None,
    historical_best_wkg: float | int | None = None,
    progression_preference: str = "标准",
) -> dict[str, Any]:
    """Stage-F training background and stable progression state.

    Stage-F is not a difficulty booster. It only adjusts progression speed
    slightly when safety, data quality and recovery gates already allow it.
    """
    cadence_state = cadence_state or {}
    event_context = event_context or {}
    notes: list[str] = []
    disable_reasons: list[str] = []
    ftp = _num(current_ftp)
    wt = _num(weight)
    current_wkg = ftp / wt if ftp > 0 and wt > 0 else 0.0
    hist_ftp = _num(historical_best_ftp)
    hist_wkg = _num(historical_best_wkg)
    recent_h = _num(recent_weekly_hours)
    exp = training_experience or "未填写"
    detrain = detraining_duration or "未填写"
    pref = progression_preference or "标准"

    readiness = getattr(rider_state, "readiness", "normal") if rider_state else "normal"
    ftp_status = getattr(rider_state, "ftp_status", "confirmed") if rider_state else "confirmed"
    forbidden = set(getattr(rider_state, "forbidden_modules", []) if rider_state else [])
    if readiness != "normal":
        disable_reasons.append("恢复/谨慎状态优先,阶段F不加速推进。")
    if ftp_status in {"unknown", "suspected_high"}:
        disable_reasons.append("FTP证据不足或疑似偏高,阶段F不加速推进。")
    if "low_cadence_torque" in forbidden or "low_cadence_torque" in (cadence_state.get("forbidden_modules", []) or []):
        disable_reasons.append("疼痛/踏频扭矩风险存在,阶段F不加速推进。")
    if event_context.get("focus") in {"race_week", "taper"}:
        disable_reasons.append("比赛减量窗口优先,阶段F不增加训练量。")
    has_training_background = exp in {"有结构化训练经验", "有比赛经验"}
    if mmp_confidence in {"低", "无", "low", "none"} and pref == "略进阶" and has_training_background:
        disable_reasons.append("MMP数据可信度不足,不能仅凭偏好进入略进阶。")

    if disable_reasons:
        return {
            "mode": "disabled_by_safety",
            "confidence": "中",
            "volume_multiplier": 1.0,
            "quality_session_cap": 1,
            "sweet_spot_bias": "none",
            "z2_capacity_bias": "none",
            "vo2_permission": "no_extra",
            "test_permission": "no_extra",
            "notes": disable_reasons,
            "disable_reason": "；".join(disable_reasons),
        }

    long_detraining = detrain in {"1-3月", "3月以上", "伤病后恢复"}
    historical_above_current = (hist_ftp > ftp * 1.08 if ftp > 0 and hist_ftp > 0 else False) or (hist_wkg > current_wkg * 1.08 if current_wkg > 0 and hist_wkg > 0 else False)

    mode = "standard_progression"
    volume_multiplier = 1.0
    quality_cap = 2
    sweet_bias = "none"
    z2_bias = "none"
    confidence = "中"

    if exp in {"新手", "普通骑行者"} and recent_rides_count < 4:
        mode = "stable_rebuild"
        quality_cap = 1
        notes.append("训练背景/近期数据偏少:优先稳定重建和连续完成。")
    elif has_training_background and long_detraining and historical_above_current:
        mode = "trained_return"
        volume_multiplier = 1.05 if pref in {"标准", "略进阶"} else 1.0
        quality_cap = 2
        sweet_bias = "light"
        z2_bias = "light"
        confidence = "中" if mmp_confidence in {"中", "高"} else "低"
        notes.append("有历史训练基础但停训较久:按有基础复训推进,只小幅增加Z2/甜区容量。")
        notes.append("历史能力只作背景,不直接按历史FTP排课。")
    elif pref == "略进阶" and has_training_background and mmp_confidence in {"中", "高"} and recent_h >= 5:
        mode = "cautious_advanced"
        volume_multiplier = 1.08
        quality_cap = 2
        sweet_bias = "light"
        z2_bias = "light"
        confidence = "中"
        notes.append("当前数据和恢复允许略进阶:只小幅提高推进感,不新增高风险强度。")
    else:
        notes.append("按标准推进:优先保持连续性,不因偏好或目标盲目加量。")

    if pref == "保守":
        volume_multiplier = min(volume_multiplier, 1.0)
        quality_cap = min(quality_cap, 1)
        notes.append("用户选择保守推进:限制质量课密度和额外容量。")

    volume_multiplier = max(0.85, min(1.12, volume_multiplier))
    return {
        "mode": mode,
        "confidence": confidence,
        "volume_multiplier": volume_multiplier,
        "quality_session_cap": quality_cap,
        "sweet_spot_bias": sweet_bias,
        "z2_capacity_bias": z2_bias,
        "vo2_permission": "no_extra",
        "test_permission": "no_extra",
        "notes": notes,
        "disable_reason": None,
    }

def build_cadence_torque_state(
    *,
    avg_cadence: float | int = 0,
    low_cadence_ratio: float | int = 0,
    high_cadence_ratio: float | int = 0,
    pain_items: list[str] | None = None,
    readiness: str = "normal",
    ftp_status: str = "confirmed",
) -> dict[str, Any]:
    """Stage-C cadence/torque safety state.

    This is a safety modifier, not a diagnosis and not a full bike-fit model.
    It only blocks or nudges modules when evidence is enough.
    """
    pain_items = pain_items or []
    pain_text = " ".join(pain_items)
    avg = _num(avg_cadence)
    low_ratio = _num(low_cadence_ratio)
    high_ratio = _num(high_cadence_ratio)
    notes: list[str] = []
    forbidden: set[str] = set()
    recommended: set[str] = set()
    status = "insufficient_data"

    if avg <= 0 and low_ratio <= 0 and high_ratio <= 0:
        notes.append("缺少踏频数据:阶段C不改变课表。")
        return {"status": status, "forbidden_modules": [], "recommended_modules": [], "notes": notes}

    status = "normal"
    if avg > 0 and avg < 75:
        status = "low_cadence_torque_risk"
        recommended.add("cadence_skill")
        notes.append(f"平均踏频约{avg:.0f}rpm偏低:优先轻齿比技术骑,避免长期硬踩。")
    if low_ratio >= 0.30:
        status = "low_cadence_torque_risk"
        recommended.add("cadence_skill")
        notes.append(f"低踏频比例约{low_ratio:.0%}:低踏频高扭矩课需谨慎。")
    if avg >= 98 or high_ratio >= 0.35:
        if status == "normal":
            status = "high_cadence_control_need"
        recommended.add("cadence_skill")
        notes.append("高踏频比例偏高:保留踏频协调,不盲目增加更高踏频刺激。")

    if any(k in pain_text for k in ("膝", "髋", "腰", "跟腱", "胯")):
        forbidden.add("low_cadence_torque")
        notes.append("疼痛反馈存在:禁用低踏频高扭矩课。")
    if readiness != "normal":
        forbidden.add("low_cadence_torque")
        notes.append("恢复/谨慎状态:低踏频高扭矩课后移或降级。")
    if ftp_status in {"unknown", "suspected_high"}:
        forbidden.add("low_cadence_torque")
        notes.append("FTP未稳或疑似偏高:不叠加低踏频高扭矩。")

    return {
        "status": status,
        "forbidden_modules": sorted(forbidden),
        "recommended_modules": sorted(recommended),
        "notes": notes,
    }


def build_event_context(
    *,
    event_type: str = "无比赛",
    days_to_event: int | None = None,
    priority: str = "B",
    readiness: str = "normal",
) -> dict[str, Any]:
    """Stage-D event countdown and specificity context.

    Minimal version: it changes the plan only by broad countdown windows and
    event type. It never overrides recovery/safety gates.
    """
    et = str(event_type or "无比赛")
    notes: list[str] = []
    forbidden: set[str] = set()
    recommended: set[str] = set()
    phase_override = None
    focus = "none"
    if et in {"无比赛", "无", "None", ""} or days_to_event is None:
        return {"event_type": et, "days_to_event": None, "focus": "none", "phase_override": None, "forbidden_modules": [], "recommended_modules": [], "notes": ["未设置比赛日期:不启用倒计时覆盖。"]}
    try:
        d = int(days_to_event)
    except Exception:
        return {"event_type": et, "days_to_event": None, "focus": "none", "phase_override": None, "forbidden_modules": [], "recommended_modules": [], "notes": ["比赛日期无效:不启用倒计时覆盖。"]}
    if d < 0:
        return {"event_type": et, "days_to_event": d, "focus": "post_event", "phase_override": "rebuild", "forbidden_modules": ["new_peak_work"], "recommended_modules": ["recovery"], "notes": ["比赛已结束:优先恢复和复盘。"]}

    if readiness != "normal":
        notes.append("恢复/谨慎状态优先,比赛倒计时不覆盖安全门控。")

    if d <= 7:
        focus = "race_week"
        phase_override = "taper"
        forbidden.update({"new_weakness_block", "ftp_test", "max_vo2_density", "low_cadence_torque"})
        recommended.update({"openers", "strategy"})
        notes.append(f"距离比赛{d}天:不再补大短板,只保留短激活/策略/恢复。")
    elif d <= 14:
        focus = "taper"
        phase_override = "taper"
        forbidden.update({"ftp_test", "new_weakness_block"})
        recommended.add("openers")
        notes.append(f"距离比赛{d}天:进入减量窗口,降总量保感觉。")
    elif d <= 56:
        focus = "specific"
        if "绕圈" in et:
            phase_override = "crit"
            recommended.add("matchbook")
            notes.append("绕圈赛专项:保留出弯加速/火柴管理/位置意识。")
        elif "爬坡" in et:
            phase_override = "climb"
            recommended.add("climb_specific")
            notes.append("爬坡专项:甜区/阈值爬坡与补给节奏优先。")
        elif "TT" in et or "计时" in et:
            phase_override = "build"
            recommended.add("steady_pacing")
            notes.append("TT专项:稳定输出和VI控制优先。")
        elif "长距离" in et or "耐力" in et:
            phase_override = "build"
            recommended.add("endurance")
            notes.append("长距离专项:Z2容量、补给和后程稳定优先。")
        else:
            notes.append("已进入专项准备窗口:围绕目标项目微调。")
    else:
        focus = "base_build"
        notes.append(f"距离比赛{d}天:仍可按基础/短板建设推进,避免过早专项化。")

    return {
        "event_type": et,
        "days_to_event": d,
        "priority": priority,
        "focus": focus,
        "phase_override": phase_override,
        "forbidden_modules": sorted(forbidden),
        "recommended_modules": sorted(recommended),
        "notes": notes,
    }

def workout_library(ftp: float | int) -> dict[str, dict[str, Any]]:
    """Reusable workout structures from the precision-absorbed sources."""
    return {
        "lt_alternates": {
            "kind": "threshold",
            "name": "阈值交替 2×20min",
            "detail": f"20min内每2min插入30s@{_w(ftp,1.20)}W,其余回到{_w(ftp,.92)}-{_w(ftp,1.00)}W;练乳酸清除。",
            "share": 1.15,
            "min": 1.0,
            "max": 1.6,
            "source_tags": ("coggan_pm20", "lactate_clearance"),
        },
        "ac_w3": {
            "kind": "crit",
            "name": "比赛获胜 AC-W3",
            "detail": f"8×2min@≥{_w(ftp,1.30)}W + 3×1min@≥{_w(ftp,1.40)}W,只在恢复良好时使用。",
            "share": 1.1,
            "min": 0.9,
            "max": 1.4,
            "source_tags": ("coggan_pm20", "anaerobic_capacity", "matchbook"),
        },
        "vo2_tt_sim": {
            "kind": "vo2",
            "name": "VO2/TT模拟 6×6min",
            "detail": f"6×6min@{_w(ftp,.96)}-{_w(ftp,1.02)}W,重点是节奏控制和接近阈值的稳定输出。",
            "share": 1.05,
            "min": 1.0,
            "max": 1.5,
            "source_tags": ("coggan_pm20", "pacing"),
        },
        "sweet_vo2_combo": {
            "kind": "sweet",
            "name": "甜区+VO2穿插",
            "detail": f"2×20min@{_w(ftp,.88)}-{_w(ftp,.93)}W + Z2巡航 + 4×3min@{_w(ftp,1.10)}W。",
            "share": 1.35,
            "min": 1.2,
            "max": 2.0,
            "source_tags": ("coggan_pm20", "sweet_spot", "vo2"),
        },
        "pre_race_activation": {
            "kind": "openers",
            "name": "赛前激活:耐力+1min+30s",
            "detail": f"低量耐力中加入3×1min@{_w(ftp,1.20)}W + 3×30s全力感觉,目标是唤醒不是训练。",
            "share": 0.65,
            "min": 0.6,
            "max": 1.1,
            "source_tags": ("coggan_pm20", "friel_peak"),
        },
        "no_computer_ride": {
            "kind": "z2",
            "name": "无表体感骑",
            "detail": "每周可安排一次不盯数字,校准RPE和身体感觉;强度保持可控。",
            "share": 0.75,
            "min": 0.6,
            "max": 1.4,
            "source_tags": ("friel_fm6", "rpe_calibration"),
        },
    }


def _inject_precision_rules(items: list[dict[str, Any]], phase: str, block_week: int, ftp: float | int) -> list[dict[str, Any]]:
    """Replace selected generic sessions with precision-source workouts."""
    lib = workout_library(ftp)
    items = [dict(x) for x in items]

    def replace_first(kinds: set[str], replacement_key: str) -> None:
        for i, x in enumerate(items):
            if x.get("kind") in kinds:
                repl = dict(lib[replacement_key])
                # Preserve broad duration intent where sensible.
                repl["share"] = max(float(x.get("share", repl["share"])), float(repl["share"]))
                repl["min"] = max(float(x.get("min", repl["min"])), float(repl["min"]))
                repl["max"] = max(float(x.get("max", repl["max"])), float(repl["max"]))
                items[i] = repl
                return

    if phase == "build" and block_week == 3:
        replace_first({"threshold"}, "lt_alternates")
    elif phase == "crit" and block_week == 2:
        replace_first({"crit", "vo2"}, "ac_w3")
    elif phase == "crit" and block_week == 3:
        replace_first({"vo2", "threshold"}, "vo2_tt_sim")
    elif phase == "climb" and block_week == 3:
        replace_first({"climb", "threshold"}, "vo2_tt_sim")
    elif phase == "taper" and block_week in {1, 2, 3}:
        replace_first({"openers"}, "pre_race_activation")
    elif phase == "maintain" and block_week == 1:
        # Friel: occasionally ride without staring at the head unit to keep body feel calibrated.
        replace_first({"z2"}, "no_computer_ride")
    return items


def detect_phase(goal: str, wkg: float) -> str:
    goal = goal or ""
    if "减脂" in goal or "燃脂" in goal or "减重" in goal:
        return "fatloss"
    if wkg < 2.5 or "恢复" in goal:
        return "rebuild"
    if "绕圈" in goal:
        return "crit"
    if "爬坡" in goal:
        return "climb"
    if "减量" in goal:
        return "taper"
    if wkg < 3 or "FTP" in goal:
        return "build"
    return "maintain"


def phase_meta() -> dict[str, dict[str, str]]:
    return {
        "rebuild": {"name": "基础重建", "icon": "🧱", "desc": "低强度高频次,重建有氧引擎", "color": "#3fb950"},
        "fatloss": {"name": "减脂燃脂", "icon": "🔥", "desc": "Z2 为主,稳定消耗,保护恢复和力量感", "color": "#ff9a3d"},
        "build": {"name": "提升期", "icon": "📈", "desc": "甜区+阈值,稳健提升 FTP", "color": "#d29922"},
        "crit": {"name": "绕圈赛专项", "icon": "🔥", "desc": "阈值、VO2max、反复冲刺与比赛节奏", "color": "#f85149"},
        "climb": {"name": "爬坡专项", "icon": "⛰️", "desc": "甜区爬坡、阈值爬坡与长距离耐力", "color": "#bc8cff"},
        "taper": {"name": "赛前减量", "icon": "🎯", "desc": "降低总量,保留神经与比赛强度", "color": "#ff6b35"},
        "maintain": {"name": "巩固期", "icon": "🔄", "desc": "维持功体比和骑行习惯", "color": "#58a6ff"},
    }


def week_theme(phase: str, wk: int) -> tuple[str, str, tuple[str, ...]]:
    block_week = ((wk - 1) % 4) + 1
    block_no = ((wk - 1) // 4) + 1
    src = ("periodization", "friel_two_phase", "coggan_3up1down")
    themes = {
        "rebuild": {
            1: ("适应周", "建立骑行频率和 Z2 节奏,不追求刺激。", src),
            2: ("有氧容量周", "延长 Z2 时间,练补给和稳定踏频。", src + ("aerobic_distillation",)),
            3: ("节奏唤醒周", "加入少量 Tempo/变速,但不做力竭。", src + ("tempo_for_amateurs",)),
            4: ("吸收周", "明显降量,让身体吸收前三周训练。", src + ("deload",)),
        },
        "fatloss": {
            1: ("习惯建立周", "先把训练频率和饮食执行稳定下来。", src),
            2: ("燃脂容量周", "增加连续 Z2 时间,提高可持续消耗。", src + ("z2_fatmax",)),
            3: ("代谢刺激周", "加入 Tempo/高踏频变化,避免每周都只是慢骑。", src + ("z3_not_junk",)),
            4: ("恢复防崩周", "降量保护睡眠和食欲,避免疲劳性暴食。", src + ("deload",)),
        },
        "build": {
            1: ("甜区适应周", "用甜区和 Tempo 建立质量课节奏。", src + ("sweet_spot",)),
            2: ("甜区容量周", "增加有效甜区时间和 Z2 支撑。", src + ("sweet_spot", "tss_progression")),
            3: ("阈值刺激周", "本周期最明确的阈值/VO2刺激。", src + ("threshold", "vo2")),
            4: ("吸收评估周", "降量吸收,状态好可做开放式 FTP 感受。", src + ("deload", "ftp_check")),
        },
        "crit": {
            1: ("阈值基础周", "先建立可重复输出和出弯后回到节奏的能力。", src + ("matchbook", "threshold")),
            2: ("追击 VO2 周", "提高短时间追击和反复加速能力。", src + ("vo2", "anaerobic")),
            3: ("比赛模拟周", "更接近绕圈赛节奏,练随机变速和站位。", src + ("race_specificity",)),
            4: ("减量激活周", "降低总量,保留短刺激和新鲜感。", src + ("taper",)),
        },
        "climb": {
            1: ("甜区爬坡适应周", "适应爬坡姿势和稳定输出。", src + ("sweet_spot",)),
            2: ("长爬容量周", "延长爬坡/耐力时间,练补给和踏频。", src + ("aerobic_capacity",)),
            3: ("阈值爬坡专项周", "本周期最关键的爬坡强度刺激。", src + ("threshold", "specificity")),
            4: ("吸收测试周", "降量恢复,状态好可做短爬坡测试。", src + ("deload",)),
        },
        "taper": {
            1: ("降量保感觉周", "总量下降,保留少量比赛强度。", ("friel_tsb_peak", "coggan_taper")),
            2: ("比赛激活周", "短刺激唤醒,避免堆疲劳。", ("pre_race_openers", "taper")),
            3: ("新鲜度优先周", "只保留必要预检,睡眠和补给优先。", ("taper",)),
            4: ("比赛/测试周", "围绕目标日安排热身、比赛和恢复。", ("race_week",)),
        },
        "maintain": {
            1: ("规律维持周", "维持训练频率和基础有氧。", src),
            2: ("趣味容量周", "加入路线/技术变化,提升执行意愿。", src),
            3: ("力量感维持周", "少量 Tempo/阈值维持输出感觉。", src + ("threshold_maintenance",)),
            4: ("轻松恢复周", "降量恢复,避免维持期堆成疲劳期。", src + ("deload",)),
        },
    }
    name, desc, tags = themes.get(phase, themes["maintain"]).get(block_week, themes["maintain"][1])
    if block_no > 1:
        block_desc = {
            2: "第二训练块:在完成率和恢复允许的前提下,提高有效时间或专项性。",
            3: "第三训练块:更接近目标项目,加入测试/模拟/专项整合。",
        }.get(block_no, "后续训练块:不盲目堆量,根据完成率、TSB、睡眠和疼痛反馈决定进阶或保持。")
        name = f"第{block_no}块 · {name}"
        desc = f"{desc} {block_desc}"
        tags = tuple(tags) + (f"block_{block_no}_progression",)
    return name, desc, tags


def week_factor(phase: str, wk: int, readiness_factor: float = 1.0) -> float:
    # Periodization reference: 3 weeks build + 1 deload; deload -30~50%.
    if phase == "taper":
        base = max(0.45, 0.75 - 0.08 * ((wk - 1) % 4))
    else:
        base = [0.92, 1.00, 1.08, 0.68][(wk - 1) % 4]
    return round(base * (readiness_factor if wk == 1 else 1.0), 2)


def tss_for_kind(kind: str, h: float) -> int:
    # Approximate TSS/h derived from IF^2*100 and simplified product defaults.
    return int((h or 0) * {
        "recovery": 30,
        "z2": 50,
        "fatloss": 48,
        "long": 52,
        "tempo": 65,
        "sweet": 75,
        "threshold": 85,
        "vo2": 95,
        "crit": 90,
        "climb": 82,
        "openers": 60,
        "race": 100,
    }.get(kind, 50))


def zone_style(kind: str) -> tuple[str, str, str]:
    return {
        "rest": ("var(--tc-surface-2)", "#484f58", "休息"),
        "recovery": ("#1a2332", "#58a6ff", "Z1"),
        "z2": ("#1a2e1a", "#3fb950", "Z2"),
        "fatloss": ("#2e2416", "#ff9a3d", "燃脂"),
        "long": ("#1a2e1a", "#3fb950", "Z2"),
        "tempo": ("#2e2416", "#d29922", "Tempo"),
        "sweet": ("#2e2016", "#db6d28", "甜区"),
        "threshold": ("#2e1616", "#f85149", "阈值"),
        "vo2": ("#261a2e", "#bc8cff", "VO2max"),
        "crit": ("#2e1a16", "#ff6b35", "冲刺"),
        "climb": ("#261a2e", "#bc8cff", "爬坡"),
        "openers": ("#2e1616", "#ff6b35", "激活"),
        "race": ("#2e1616", "#ff6b35", "比赛"),
    }.get(kind, ("var(--tc-surface-2)", "var(--tc-subtle)", "混合"))


def _base_pool(phase: str, ftp: float | int) -> list[RuleSession]:
    z2_lo, z2_hi = _w(ftp, .55), _w(ftp, .75)
    sweet, thresh, vo2, sprint = _w(ftp, .90), _w(ftp, .97), _w(ftp, 1.10), _w(ftp, 1.50)
    common = ("workout_design", "power_zones")
    pools = {
        "rebuild": [
            RuleSession("z2", "Z2 有氧耐力", f"{z2_lo}-{z2_hi}W,能完整说短句", 1.0, .8, 3.0, common + ("aerobic_base",)),
            RuleSession("z2", "Z2 + 轻微变速", "Z2 为主,每 30min 来 15s 轻冲刺", 1.0, .8, 2.5, common),
            RuleSession("long", "长距离 Z2", "全程可控,不追均速", 1.6, 1.4, 5.0, common + ("endurance",)),
            RuleSession("recovery", "恢复骑 / 晃腿", f"≤{z2_lo}W,越轻松越好", .45, .4, 1.0, common + ("friel_recovery",)),
            RuleSession("z2", "Z2 技术骑", "踏频、转弯、补给节奏练习", .8, .7, 2.0, common),
            RuleSession("recovery", "核心力量 20min + 轻松骑", "不做力竭训练", .35, .3, .8, common),
            RuleSession("recovery", "主动恢复", "散步/拉伸/超轻松骑", .3, .2, .7, common),
        ],
        "taper": [
            RuleSession("openers", "赛前激活 3×5min", f"{_w(ftp,.95)}W,保感觉不堆疲劳", .7, .6, 1.0, ("friel_tsb_peak", "pre_race_openers")),
            RuleSession("recovery", "Z1 轻松晃腿", f"≤{z2_lo}W", .5, .4, .8, ("friel_recovery",)),
            RuleSession("openers", "赛前预检 2×3min", "比赛强度,检查装备和补给", .6, .5, .8, ("pre_race_openers",)),
            RuleSession("race", "比赛日 / 模拟测试", "热身充分,执行策略", 1.0, .8, 2.5, ("race_week",)),
            RuleSession("recovery", "完全休息或散步", "睡眠和碳水优先", .25, .0, .5, ("taper",)),
            RuleSession("recovery", "轻松转腿", "只唤醒,不训练", .35, .3, .6, ("taper",)),
            RuleSession("recovery", "休息", "装备检查", .2, .0, .4, ("taper",)),
        ],
        "maintain": [
            RuleSession("z2", "Z2 或甜区维持", "按当天状态二选一", 1.0, .8, 2.5, common),
            RuleSession("z2", "Z2 + 爬坡", "享受骑行,不堆疲劳", 1.2, 1.0, 3.0, common),
            RuleSession("threshold", "阈值维持 3×10min", f"{_w(ftp,.95)}W", 1.1, 1.0, 1.5, common + ("threshold",)),
            RuleSession("long", "长距离探险骑", "新路线、美景、稳定补给", 1.8, 1.4, 4.5, common),
            RuleSession("recovery", "轻松骑 / 团体骑", "社交节奏,别拼", .6, .5, 1.2, common),
            RuleSession("tempo", "Tempo 维持", "中等强度,不做力竭", .9, .8, 1.8, common),
            RuleSession("recovery", "主动恢复", "轻松活动", .3, .2, .7, common),
        ],
    }
    return pools.get(phase, pools["maintain"])


def _progress_items_for_block(items: list[dict[str, Any]], phase: str, wk: int) -> list[dict[str, Any]]:
    """Progress repeated 4-week mesocycles so week 5+ is not a copy of week 1.

    Week pattern remains 3-build + 1-deload, but each 4-week block changes the
    coaching target: block 1 builds habit/entry, block 2 extends effective time,
    block 3 adds specificity/testing, later blocks prioritize maintaining quality.
    """
    block_idx = (wk - 1) // 4
    if block_idx <= 0:
        return items

    block_no = block_idx + 1
    block_focus = {
        "rebuild": [
            "从建立习惯转向延长连续 Z2 时间,仍不追求力竭。",
            "加入更多心率漂移/EF 观察,判断有氧基础是否稳定。",
            "维持恢复优先,用完成率和腿感决定是否进入提升期。",
        ],
        "fatloss": [
            "提高单次连续有氧时间和每周执行稳定性。",
            "加入少量 Tempo/高踏频变化,避免长期只有低刺激慢骑。",
            "控制疲劳性饥饿,优先维持可持续消耗。",
        ],
        "build": [
            "增加甜区/阈值有效时间,不盲目加最大强度。",
            "从 FTP 建设转向更接近目标项目的专项刺激。",
            "如果完成率高,安排测试或比赛模拟;否则保持当前块。",
        ],
        "crit": [
            "提高反复加速和追击后的恢复能力。",
            "加入更真实的绕圈赛随机变速和站位模拟。",
            "减少总量,保留锐度,准备测试/比赛。",
        ],
        "climb": [
            "延长爬坡甜区时间,练稳定姿势与补给。",
            "提高阈值爬坡和疲劳后输出能力。",
            "以目标爬坡/长距离模拟检验训练效果。",
        ],
        "taper": [
            "继续降量,只保留必要激活。",
            "围绕目标日微调,避免新增疲劳。",
            "比赛/测试后进入恢复或新周期。",
        ],
        "maintain": [
            "维持规律,略提高趣味性和路线变化。",
            "维持关键能力,避免长期平台化。",
            "恢复优先,准备重新选择目标。",
        ],
    }
    note = block_focus.get(phase, block_focus["maintain"])[min(block_idx - 1, 2)]

    progressed: list[dict[str, Any]] = []
    for item in items:
        x = dict(item)
        kind = x.get("kind", "")
        x["block_no"] = block_no
        x["source_tags"] = tuple(x.get("source_tags", ())) + (f"block_{block_no}_progression",)
        if kind in HARD_KINDS:
            x["name"] = f"第{block_no}块进阶 · {x.get('name', '')}"
            x["detail"] = f"{x.get('detail', '')}｜进阶重点:{note}"
            x["share"] = round(float(x.get("share", 1.0)) * min(1.12, 1.04 + 0.03 * block_idx), 2)
            x["max"] = round(float(x.get("max", 2.0)) + min(0.4, 0.15 * block_idx), 1)
        elif kind in {"z2", "fatloss", "long", "tempo"}:
            x["name"] = f"第{block_no}块 · {x.get('name', '')}"
            x["detail"] = f"{x.get('detail', '')}｜本训练块:{note}"
            x["share"] = round(float(x.get("share", 1.0)) * min(1.10, 1.03 + 0.02 * block_idx), 2)
            x["max"] = round(float(x.get("max", 2.0)) + min(0.5, 0.2 * block_idx), 1)
        elif kind == "recovery":
            x["name"] = f"第{block_no}块恢复 · {x.get('name', '')}"
            x["detail"] = f"{x.get('detail', '')}｜不要把恢复日补成训练日;用恢复质量决定下一块能否进阶。"
        progressed.append(x)
    return progressed


def phase_week_items(phase: str, wk: int, ftp: float | int) -> list[dict[str, Any]]:
    """Return full 7-item candidate list for a week.

    A plan is organized as 4-week mesocycles. Weeks 1-4 define the weekly role;
    weeks 5+ repeat the role but progress the block target so long plans do not
    become copy-paste loops.
    """
    z2_lo, z2_hi = _w(ftp, .55), _w(ftp, .75)
    sweet, thresh, vo2, sprint = _w(ftp, .90), _w(ftp, .97), _w(ftp, 1.10), _w(ftp, 1.50)
    b = ((wk - 1) % 4) + 1
    wd = ("workout_design", "periodization")

    def S(kind: str, name: str, detail: str, share=1.0, min_h=0.5, max_h=2.0, tags: tuple[str, ...] = ()) -> RuleSession:
        return RuleSession(kind, name, detail, share, min_h, max_h, wd + tags)

    plans: dict[str, dict[int, list[RuleSession]]] = {
        "rebuild": {
            1: [
                S("z2", "Z2 适应骑", f"{z2_lo}-{z2_hi}W,能完整说短句,先把频率做稳", 1.15, .8, 2.2, ("aerobic_base",)),
                S("recovery", "Z1 恢复转腿", f"≤{z2_lo}W,越轻松越好", .55, .35, 1.0, ("friel_recovery",)),
                S("z2", "Z2 技术骑", "高踏频/圆顺踩踏/放松上肢,不追均速", .95, .7, 1.8, ("skills",)),
                S("long", "短长距离 Z2", "全程可控,结束时仍有余力", 1.45, 1.1, 3.0, ("endurance",)),
                S("recovery", "核心激活 + 轻松骑", "核心 15-20min + Z1,不做力竭", .45, .3, .8, ("general_conditioning",)),
                S("z2", "Z2 轻松耐力", f"{z2_lo}-{_w(ftp,.68)}W,建立骑行习惯", .9, .7, 1.8, ("aerobic_base",)),
                S("recovery", "完全休息 / 散步", "恢复优先,记录睡眠和腿感", .25, 0, .5, ("recovery",)),
            ],
            2: [
                S("z2", "Z2 容量延长", f"{z2_lo}-{z2_hi}W,比第1周略延长", 1.35, 1.0, 2.8, ("aerobic_capacity",)),
                S("z2", "Z2 + 高踏频唤醒", "Z2 中加入 6×1min 高踏频,只练神经不冲功率", 1.0, .8, 2.0, ("cadence",)),
                S("recovery", "Z1 恢复骑", f"≤{z2_lo}W,让容量训练被吸收", .45, .3, .9, ("friel_recovery",)),
                S("long", "长距离 Z2 + 补给练习", "稳定 Z2,每 30-40min 小口补给/喝水", 1.75, 1.4, 3.8, ("endurance", "fueling_practice")),
                S("z2", "Z2 稳态观察心率", f"{z2_lo}-{z2_hi}W,观察后半程心率漂移", 1.05, .8, 2.2, ("ef_decoupling",)),
                S("recovery", "主动恢复", "散步/拉伸/超轻松骑", .35, 0, .7, ("recovery",)),
                S("z2", "轻松有氧补量", "只补总时间,不加强度", .75, .6, 1.5, ("aerobic_base",)),
            ],
            3: [
                S("tempo", "节奏唤醒 2×10min", f"{_w(ftp,.78)}-{_w(ftp,.82)}W,不力竭,找力量感", .8, .7, 1.2, ("tempo_for_amateurs",)),
                S("z2", "Z2 恢复承接", f"{z2_lo}-{z2_hi}W,为节奏课做吸收", 1.0, .8, 2.0, ("aerobic_base",)),
                S("z2", "Z2 + 轻微变速", "Z2 为主,每 20-30min 15s 轻加速", 1.0, .8, 2.0, ("neuromuscular",)),
                S("long", "长距离渐进 Z2", "后半程保持 Z2 中段,练疲劳后动作稳定", 1.65, 1.3, 3.6, ("endurance",)),
                S("recovery", "Z1 晃腿", "腿沉直接休息,不要补课", .35, 0, .8, ("recovery",)),
                S("tempo", "Tempo 技术稳态", f"{_w(ftp,.76)}-{_w(ftp,.80)}W,短时间即可", .65, .6, 1.1, ("tempo_for_amateurs",)),
                S("recovery", "完全休息", "睡眠优先,准备吸收周", .2, 0, .4, ("recovery",)),
            ],
            4: [
                S("recovery", "吸收周 Z1/Z2", "明显降量,让前三周训练转化", .55, .35, 1.0, ("deload",)),
                S("z2", "轻松 Z2 技术骑", f"{z2_lo}-{_w(ftp,.68)}W,动作放松", .85, .6, 1.6, ("deload", "skills")),
                S("recovery", "完全休息", "不补课,优先恢复", .2, 0, .4, ("deload",)),
                S("long", "短长距离 Z2", "比第2/3周明显短,全程舒适", 1.05, .9, 2.4, ("deload", "endurance")),
                S("z2", "轻松有氧回顾", "看心率、RPE、腿感是否比第1周稳定", .7, .5, 1.3, ("ef_review",)),
                S("recovery", "散步/灵活性", "恢复、睡眠、身体反馈记录", .25, 0, .5, ("recovery",)),
                S("recovery", "完全休息", "准备下一个训练块", .2, 0, .4, ("deload",)),
            ],
        },
        "build": {
            1: [S("sweet", "甜区适应 3×12min", f"{sweet}W 左右,先稳住动作和呼吸", 1.15, 1.0, 1.5, ("sweet_spot",)), S("tempo", "Tempo 技术稳态", f"{_w(ftp,.80)}-{_w(ftp,.84)}W,不顶爆,练踏频稳定", .85, .7, 1.4), S("long", "基础长距离 Z2", f"{z2_lo}-{z2_hi}W,全程可控,重点补给节奏", 1.9, 1.4, 5.0), S("z2", "Z2 有氧耐力", f"{z2_lo}-{z2_hi}W,低压积累", 1.15, .8, 3.0), S("recovery", "恢复骑 / 灵活性", "Z1 轻松转腿,结束后拉伸", .45, .3, 1.0), S("z2", "Z2 技术骑", "高踏频/单腿感知/踩踏圆顺,不追功率", .75, .6, 1.5), S("recovery", "完全休息或散步", "恢复优先,不做力竭力量", .25, 0, .6)],
            2: [S("sweet", "甜区容量 3×15min", f"{sweet}W 左右,增加有效甜区时间", 1.25, 1.1, 1.7, ("sweet_spot",)), S("z2", "Z2 长稳态", f"{z2_lo}-{z2_hi}W,观察心率漂移", 1.45, 1.1, 3.5, ("ef_decoupling",)), S("tempo", "Tempo 3×12min", f"{_w(ftp,.80)}-{_w(ftp,.84)}W,作为容量支撑", .95, .8, 1.5), S("long", "长距离 Z2 + 补给演练", "Z2 为主,每 30-40min 固定补给", 2.05, 1.6, 5.5), S("recovery", "Z1 晃腿", f"≤{z2_lo}W,促进恢复", .45, .3, 1.0), S("z2", "Z2 高踏频唤醒", "Z2 中加入 6×1min 高踏频,不冲功率", .8, .6, 1.6), S("recovery", "主动恢复", "轻松骑或完全休息", .3, 0, .7)],
            3: [S("threshold", "阈值刺激 4×8min", f"{thresh}W,本周期关键质量课", 1.25, 1.1, 1.7, ("threshold",)), S("vo2", "VO2max 5×3min", f"{vo2}W 左右,宁可少一组也不炸", 1.0, .9, 1.4, ("vo2",)), S("long", "长距离渐进 Z2", "后半程保持 Z2 中上沿,练疲劳后稳定输出", 1.8, 1.4, 5.0), S("z2", "Z2 恢复承接", f"{z2_lo}-{z2_hi}W,给强度课做吸收", 1.1, .8, 2.5), S("recovery", "Z1 晃腿", "如果腿沉可直接休息", .45, 0, .9), S("tempo", "Tempo 稳态 35-45min", f"{_w(ftp,.78)}-{_w(ftp,.82)}W,不顶爆", .8, .7, 1.4), S("recovery", "完全休息", "睡眠和碳水优先", .2, 0, .4)],
            4: [S("recovery", "吸收周恢复骑", "Z1/Z2 下沿,让身体恢复", .6, .4, 1.2, ("deload",)), S("z2", "轻松 Z2 技术骑", f"{z2_lo}-{_w(ftp,.68)}W,动作放松", 1.0, .7, 2.0), S("openers", "开放式 FTP 感受 / 小测试", "状态好做短测试;状态差改 Z2", .75, .5, 1.0, ("ftp_check",)), S("long", "短长距离 Z2", "比前三周明显缩短,不追均速", 1.25, 1.0, 3.0), S("recovery", "完全休息", "恢复和复盘优先", .2, 0, .4), S("z2", "轻松有氧", "只保持节奏,不加练", .7, .5, 1.4), S("recovery", "主动恢复", "散步/拉伸/超轻松骑", .2, 0, .5)],
        },
        # For brevity MVP keeps these compact but explicit; app no longer owns rules.
        "fatloss": {
            1: [S("fatloss", "燃脂习惯 Z2", f"{z2_lo}-{z2_hi}W,先稳定频率", 1.25, .9, 2.5, ("z2_fatmax",)), S("recovery", "Z1 恢复骑", f"≤{z2_lo}W,保留习惯", .55, .4, 1.0), S("fatloss", "Z2 稳态", f"{z2_lo}-{z2_hi}W,能说短句", 1.1, .8, 2.2), S("long", "长距离燃脂骑", "Z2 下沿,补水电解质", 1.8, 1.3, 4.0), S("recovery", "散步/拉伸", "睡眠和饮食执行优先", .25, 0, .5), S("fatloss", "通勤/轻松有氧", "累计消耗,不追均速", .8, .6, 1.8), S("recovery", "完全休息", "避免疲劳性饥饿", .2, 0, .4)],
            2: [S("fatloss", "燃脂 Z2 长稳态", f"{z2_lo}-{z2_hi}W,延长连续时间", 1.4, 1.1, 3.0), S("z2", "Z2 高踏频", f"{z2_lo}-{z2_hi}W + 6×1min 高踏频", 1.0, .8, 1.8), S("recovery", "Z1 恢复骑", f"≤{z2_lo}W", .45, .3, .9), S("long", "长距离燃脂 + 补给", "避免空腹硬撑,练水和电解质", 2.0, 1.5, 4.5), S("fatloss", "轻松有氧", "可户外轻松骑/通勤", .75, .6, 1.5), S("tempo", "短 Tempo 唤醒", f"{_w(ftp,.78)}-{_w(ftp,.82)}W,2×10min", .65, .6, 1.1), S("recovery", "完全休息", "恢复优先", .2, 0, .4)],
            3: [S("tempo", "代谢刺激 Tempo", f"{_w(ftp,.80)}-{_w(ftp,.84)}W,不过度乳酸堆积", .85, .7, 1.3), S("fatloss", "Z2 稳态恢复", f"{z2_lo}-{z2_hi}W,低压力承接", 1.0, .8, 2.0), S("fatloss", "Z2 + 高踏频变化", "每 12-15min 加 1min 高踏频", 1.05, .8, 2.0), S("long", "长距离 Z2", "总时间为主,不要冲坡", 1.8, 1.4, 4.2), S("recovery", "Z1 晃腿", "腿沉则休息", .35, 0, .8), S("fatloss", "轻松有氧", "累计消耗", .75, .6, 1.5), S("recovery", "完全休息", "睡眠优先", .2, 0, .4)],
            4: [S("recovery", "恢复防崩骑", "Z1/Z2 下沿,降低压力", .6, .4, 1.2), S("fatloss", "短 Z2 维持", f"{z2_lo}-{_w(ftp,.68)}W,只保持节奏", .9, .7, 1.8), S("recovery", "散步/拉伸", "减轻疲劳性食欲", .25, 0, .5), S("long", "短长距离 Z2", "比前几周缩短", 1.2, 1.0, 2.8), S("recovery", "完全休息", "饮食复盘", .2, 0, .4), S("z2", "轻松 Z2", "恢复为主", .7, .5, 1.4), S("recovery", "完全休息", "睡眠优先", .2, 0, .4)],
        },
        "crit": {
            1: [
                S("threshold", "绕圈阈值基础 3×8min", f"{thresh}W,建立可重复输出和出弯后回节奏能力", 1.1, 1.0, 1.5, ("crit", "threshold", "matchbook")),
                S("z2", "Z2 低压积累", f"{z2_lo}-{z2_hi}W,为高强度做底座", 1.1, .9, 2.5, ("aerobic_base",)),
                S("tempo", "出弯回节奏 Tempo", f"{_w(ftp,.82)}W 左右,每 8-10min 加 10s 轻加速", .9, .8, 1.4, ("race_specificity",)),
                S("crit", "绕圈技术模拟", "弯道/站位/跟轮/短加速意识,可用团骑替代但别乱拼", 1.55, 1.2, 3.5, ("skills", "race_specificity")),
                S("recovery", "Z1 晃腿", f"≤{z2_lo}W,让阈值课吸收", .45, .3, .9, ("recovery",)),
                S("z2", "Z2 技术骑", "高踏频、控车、补水,不追均速", .75, .6, 1.5, ("skills",)),
                S("recovery", "完全休息", "恢复优先,不要补课", .2, 0, .4, ("recovery",)),
            ],
            2: [
                S("vo2", "VO2 追击 6×3min", f"{vo2}W,等时长恢复,宁可少一组也不爆", 1.15, 1.0, 1.5, ("vo2", "matchbook")),
                S("z2", "Z2 承接", f"{z2_lo}-{z2_hi}W,低压承接高强度", 1.0, .8, 2.2, ("aerobic_base",)),
                S("crit", "反复追击 + 短冲", f"4min 追击 + 15s {sprint}W 起跳,练火柴管理", 1.15, 1.0, 1.6, ("anaerobic", "matchbook")),
                S("long", "耐力团骑 / 长 Z2", "低压积累,练跟轮位置和补给,不抢风", 1.6, 1.3, 3.8, ("endurance", "group_ride")),
                S("recovery", "Z1 晃腿 + 3次起跳", "只唤醒神经,不堆疲劳", .5, .4, .9, ("neuromuscular",)),
                S("tempo", "Tempo + 小冲刺", "节奏中加入 6-8 次短冲,每次后回到节奏", .8, .7, 1.4, ("race_specificity",)),
                S("recovery", "完全休息", "睡眠优先", .2, 0, .4, ("recovery",)),
            ],
            3: [
                S("crit", "比赛节奏模拟", "多次 20s-2min 变速 + 回到 Z3/Z4,练随机性", 1.25, 1.1, 1.8, ("race_specificity", "matchbook")),
                S("threshold", "阈值维持 2×15min", f"{thresh}W,稳定输出不要冲开头", 1.0, .9, 1.4, ("threshold",)),
                S("vo2", "VO2 4×4min", f"{vo2}W,少组数高质量", .95, .8, 1.3, ("vo2",)),
                S("long", "绕圈专项团骑/模拟", "含站位、出弯、追击,赛后复盘火柴使用", 1.7, 1.3, 3.5, ("race_simulation",)),
                S("recovery", "Z1 恢复骑", f"≤{z2_lo}W", .4, .3, .8, ("recovery",)),
                S("z2", "Z2 放松骑", "低压补有氧,不要额外加冲刺", .8, .6, 1.5, ("aerobic_base",)),
                S("recovery", "完全休息", "准备减量/测试", .2, 0, .4, ("recovery",)),
            ],
            4: [
                S("openers", "绕圈赛激活 3×1min", f"{_w(ftp,1.15)}W + 3×15s 起跳,总量很少", .55, .45, .8, ("taper", "openers")),
                S("recovery", "Z1 轻松转腿", f"≤{z2_lo}W,保持新鲜感", .45, .3, .8, ("recovery",)),
                S("z2", "短 Z2 技术骑", "检查弯道、刹车、补给,不做疲劳课", .7, .5, 1.2, ("skills", "deload")),
                S("crit", "短模拟 / 开腿", "低总量,少量比赛节奏,不要骑成训练赛", .85, .7, 1.5, ("taper", "race_specificity")),
                S("recovery", "完全休息", "睡眠、碳水、装备优先", .2, 0, .4, ("taper",)),
                S("recovery", "轻松晃腿", "只唤醒,不堆疲劳", .3, .2, .6, ("recovery",)),
                S("recovery", "完全休息", "准备下一训练块或比赛", .2, 0, .4, ("deload",)),
            ],
        },
        "climb": {
            1: [
                S("sweet", "甜区爬坡适应 3×12min", f"{sweet}W,坡度温和,稳定坐姿和呼吸", 1.15, 1.0, 1.6, ("sweet_spot", "climb")),
                S("z2", "Z2 + 自然爬坡", f"{z2_lo}-{z2_hi}W,爬坡不冲过阈值", 1.25, 1.0, 3.0, ("aerobic_base", "climb")),
                S("tempo", "爬坡 Tempo", f"{_w(ftp,.80)}-{_w(ftp,.84)}W,练稳定踏频", .9, .8, 1.4, ("tempo", "climb")),
                S("long", "长距离含爬升", "总爬升优先,强度不失控,练补给", 1.85, 1.4, 4.8, ("endurance", "fueling_practice")),
                S("recovery", "Z1 晃腿", f"≤{z2_lo}W,放松髋和下背", .45, .3, .9, ("recovery",)),
                S("z2", "Z2 高踏频爬坡", "轻齿比,不硬踩,保护膝髋", .8, .6, 1.6, ("cadence", "climb")),
                S("recovery", "完全休息", "不要补课", .2, 0, .4, ("recovery",)),
            ],
            2: [
                S("sweet", "甜区爬坡容量 3×18min", f"{sweet}W,延长有效爬坡时间", 1.3, 1.1, 1.8, ("sweet_spot", "climb")),
                S("z2", "Z2 长稳态", f"{z2_lo}-{z2_hi}W,观察心率漂移", 1.35, 1.0, 3.2, ("ef_decoupling",)),
                S("climb", "低踏频力量耐力 5×5min", f"{_w(ftp,.85)}W 左右,低踏频但不顶膝", .9, .8, 1.3, ("muscular_endurance", "climb")),
                S("long", "长爬容量日", "爬升/时间优先,每 30-40min 补给", 2.0, 1.6, 5.5, ("endurance", "climb", "fueling_practice")),
                S("recovery", "Z1 恢复", f"≤{z2_lo}W", .4, .3, .8, ("recovery",)),
                S("tempo", "Tempo 爬坡稳态", f"{_w(ftp,.80)}-{_w(ftp,.84)}W,不追 PR", .85, .7, 1.4, ("tempo",)),
                S("recovery", "完全休息", "睡眠和腿感优先", .2, 0, .4, ("recovery",)),
            ],
            3: [
                S("climb", "阈值爬坡 4×10min", f"{thresh}W,本周期关键课", 1.25, 1.1, 1.8, ("threshold", "climb")),
                S("vo2", "短坡 VO2 5×3min", f"{vo2}W,控制动作不塌腰", .95, .8, 1.3, ("vo2", "climb")),
                S("z2", "Z2 恢复承接", f"{z2_lo}-{z2_hi}W,不额外加坡冲", 1.0, .8, 2.2, ("recovery_support",)),
                S("long", "目标爬坡模拟", "接近目标路线/爬升,练配速和补给", 1.9, 1.5, 5.0, ("race_simulation", "climb")),
                S("recovery", "Z1 晃腿", "腿沉直接休息", .35, 0, .8, ("recovery",)),
                S("tempo", "爬坡 Tempo 收尾", f"{_w(ftp,.78)}-{_w(ftp,.82)}W,短而稳", .75, .6, 1.2, ("tempo", "climb")),
                S("recovery", "完全休息", "准备吸收周", .2, 0, .4, ("recovery",)),
            ],
            4: [
                S("recovery", "吸收周轻松骑", "Z1/Z2 下沿,释放爬坡疲劳", .55, .35, 1.0, ("deload",)),
                S("z2", "短 Z2 技术爬坡", f"{z2_lo}-{_w(ftp,.68)}W,轻齿比高踏频", .8, .6, 1.5, ("skills", "deload")),
                S("openers", "短爬坡开放感受", "状态好做 2-3 段短坡;状态差改 Z2", .65, .5, .9, ("test", "deload")),
                S("long", "短长距离含小爬升", "明显缩短,不追坡段 PR", 1.15, .9, 2.8, ("deload", "endurance")),
                S("recovery", "完全休息", "恢复髋、腰背和小腿", .2, 0, .4, ("recovery",)),
                S("z2", "轻松有氧回顾", "看同坡段 RPE/心率是否改善", .7, .5, 1.3, ("ef_review",)),
                S("recovery", "完全休息", "准备下一块", .2, 0, .4, ("deload",)),
            ],
        },
        "taper": {
            1: [
                S("openers", "降量保感觉 3×5min", f"{_w(ftp,.95)}W,保留节奏不堆疲劳", .7, .6, 1.0, ("taper", "friel_tsb_peak")),
                S("recovery", "Z1 轻松晃腿", f"≤{z2_lo}W,越轻松越好", .45, .3, .8, ("recovery",)),
                S("z2", "短 Z2 保持", f"{z2_lo}-{_w(ftp,.68)}W,只保持腿感", .75, .5, 1.2, ("taper",)),
                S("openers", "赛前预检 2×3min", "比赛强度短刺激,检查装备/补给", .6, .5, .8, ("pre_race_openers",)),
                S("recovery", "完全休息", "睡眠和碳水优先", .2, 0, .4, ("recovery",)),
                S("recovery", "轻松转腿", "只唤醒,不训练", .3, .2, .6, ("recovery",)),
                S("recovery", "休息 / 装备检查", "确认码表、功率计、补给", .2, 0, .4, ("race_prep",)),
            ],
            2: [
                S("openers", "比赛激活 3×1min", f"{_w(ftp,1.10)}W,间隔充分,不要做成训练", .55, .45, .8, ("openers",)),
                S("recovery", "Z1 晃腿", f"≤{z2_lo}W", .35, .25, .6, ("recovery",)),
                S("openers", "起跳唤醒 4×15s", f"{sprint}W 感觉即可,不追最大", .45, .35, .7, ("neuromuscular",)),
                S("race", "比赛 / 目标模拟", "执行配速、站位和补给策略", 1.0, .8, 2.5, ("race_week",)),
                S("recovery", "完全休息", "尽量多睡,别临时加练", .2, 0, .4, ("recovery",)),
                S("recovery", "赛后恢复骑", "如果已比赛,只做 Z1;未比赛则休息", .35, 0, .7, ("post_race",)),
                S("recovery", "完全休息", "记录比赛反馈", .2, 0, .4, ("recovery",)),
            ],
            3: [
                S("recovery", "新鲜度优先 Z1", "保持活动,不制造疲劳", .35, .25, .7, ("taper",)),
                S("z2", "短 Z2 保腿感", f"{z2_lo}-{_w(ftp,.65)}W,轻松出汗即可", .55, .4, .9, ("taper",)),
                S("openers", "极短激活", "2×1min + 2×10s,感觉好就停", .4, .3, .6, ("openers",)),
                S("race", "目标日 / 测试日", "热身充分,不要临场改策略", .9, .7, 2.2, ("race_week",)),
                S("recovery", "完全休息", "睡眠、补给、装备", .2, 0, .4, ("recovery",)),
                S("recovery", "恢复转腿", "赛后只恢复,不补强度", .3, 0, .6, ("post_race",)),
                S("recovery", "完全休息", "准备过渡周", .2, 0, .4, ("transition",)),
            ],
            4: [
                S("recovery", "过渡恢复", "比赛/测试后身心恢复,不急着进下个周期", .4, .25, .8, ("transition",)),
                S("z2", "轻松 Z2", f"{z2_lo}-{_w(ftp,.65)}W,仅恢复节奏", .55, .4, 1.0, ("transition",)),
                S("recovery", "完全休息", "复盘比赛和身体反馈", .2, 0, .4, ("transition",)),
                S("z2", "轻松有氧", "恢复性活动,不测试", .6, .4, 1.2, ("transition",)),
                S("recovery", "完全休息", "准备重新选目标", .2, 0, .4, ("transition",)),
                S("recovery", "散步 / 灵活性", "恢复髋、腰背、小腿", .25, 0, .5, ("recovery",)),
                S("recovery", "完全休息", "进入新周期前检查疲劳", .2, 0, .4, ("transition",)),
            ],
        },
        "maintain": {
            1: [
                S("z2", "规律 Z2", f"{z2_lo}-{z2_hi}W,维持骑行频率", 1.1, .8, 2.4, ("maintenance",)),
                S("tempo", "Tempo 维持 2×12min", f"{_w(ftp,.80)}-{_w(ftp,.84)}W,保留力量感", .85, .7, 1.3, ("tempo",)),
                S("recovery", "Z1 恢复", f"≤{z2_lo}W", .4, .3, .8, ("recovery",)),
                S("long", "长距离探险骑", "新路线、美景、稳定补给,不堆疲劳", 1.6, 1.2, 4.0, ("endurance",)),
                S("z2", "Z2 技术骑", "踏频、控车、补给节奏", .8, .6, 1.6, ("skills",)),
                S("recovery", "轻松活动", "散步/拉伸/超轻松骑", .3, 0, .6, ("recovery",)),
                S("recovery", "完全休息", "维持期也需要休息", .2, 0, .4, ("recovery",)),
            ],
            2: [
                S("z2", "趣味容量 Z2", f"{z2_lo}-{z2_hi}W,换路线增加执行意愿", 1.25, .9, 2.8, ("maintenance", "variety")),
                S("sweet", "甜区维持 2×12min", f"{sweet}W,不过度追求进步", .9, .8, 1.3, ("sweet_spot",)),
                S("recovery", "Z1 恢复", f"≤{z2_lo}W", .4, .3, .8, ("recovery",)),
                S("long", "团骑 / 长 Z2", "社交骑可以,不要变成训练赛", 1.7, 1.3, 4.2, ("group_ride", "endurance")),
                S("tempo", "Tempo 稳态", f"{_w(ftp,.78)}-{_w(ftp,.82)}W,中等刺激", .8, .7, 1.3, ("tempo",)),
                S("z2", "轻松补量", "补一点总时间,不补强度", .65, .5, 1.2, ("maintenance",)),
                S("recovery", "完全休息", "恢复优先", .2, 0, .4, ("recovery",)),
            ],
            3: [
                S("threshold", "阈值维持 3×8min", f"{thresh}W,保留上限能力", 1.0, .9, 1.4, ("threshold_maintenance",)),
                S("z2", "Z2 承接", f"{z2_lo}-{z2_hi}W,别追加高强度", 1.0, .8, 2.2, ("aerobic_base",)),
                S("tempo", "力量感 Tempo", f"{_w(ftp,.80)}-{_w(ftp,.84)}W,短而稳", .85, .7, 1.3, ("tempo",)),
                S("long", "长距离 Z2", "维持耐力底座,不过量", 1.5, 1.2, 3.8, ("endurance",)),
                S("recovery", "Z1 晃腿", "腿沉则休息", .35, 0, .7, ("recovery",)),
                S("z2", "技术/路线变化", "保持新鲜感", .7, .5, 1.4, ("variety",)),
                S("recovery", "完全休息", "避免维持期堆成疲劳期", .2, 0, .4, ("recovery",)),
            ],
            4: [
                S("recovery", "轻松恢复周", "降量,避免平台期变疲劳", .5, .3, .9, ("deload",)),
                S("z2", "轻松 Z2", f"{z2_lo}-{_w(ftp,.68)}W,只保持节奏", .75, .5, 1.4, ("deload",)),
                S("recovery", "完全休息", "恢复优先", .2, 0, .4, ("recovery",)),
                S("long", "短长距离 Z2", "明显缩短,轻松结束", 1.0, .8, 2.4, ("deload", "endurance")),
                S("z2", "轻松技术骑", "动作放松,不做测试", .6, .4, 1.0, ("skills",)),
                S("recovery", "散步/灵活性", "恢复和复盘", .25, 0, .5, ("recovery",)),
                S("recovery", "完全休息", "准备下一个维持块或新目标", .2, 0, .4, ("deload",)),
            ],
        },
    }
    if phase in plans:
        items = [x.to_app_item() for x in plans[phase][b]]
    else:
        items = [x.to_app_item() for x in _base_pool(phase, ftp)]
    items = _inject_precision_rules(items, phase, b, ftp)
    return _progress_items_for_block(items, phase, wk)


def allocate_durations(items: list[dict[str, Any]], target_h: float) -> list[dict[str, Any]]:
    """Allocate target hours while protecting intensity quality.

    Hard workouts keep conservative caps; extra user-requested time is absorbed by
    endurance/long/tempo support sessions instead of stretching VO2/threshold work.
    """
    items = [dict(x) for x in items]
    total_share = sum(x.get("share", 1.0) for x in items) or 1
    for x in items:
        raw = target_h * x.get("share", 1.0) / total_share
        x["dur_h"] = round(max(x.get("min", 0), min(x.get("max", 99), raw)), 1)

    def current_total() -> float:
        return round(sum(x.get("dur_h", 0) for x in items), 1)

    diff = round(target_h - current_total(), 1)
    flex = [x for x in items if x.get("kind") in ("long", "z2", "fatloss", "tempo")]
    if diff > 0:
        # First fill normal caps.
        for x in flex:
            add = min(round(x.get("max", x["dur_h"]) - x["dur_h"], 1), diff)
            if add > 0:
                x["dur_h"] = round(x["dur_h"] + add, 1)
                diff = round(diff - add, 1)
            if diff <= 0:
                break
        # If the user's weekly target is still not met, create safe endurance headroom.
        if diff > 0 and flex:
            priority = {"long": 0, "z2": 1, "fatloss": 1, "tempo": 2}
            flex2 = sorted(flex, key=lambda y: priority.get(y.get("kind"), 9))
            while diff > 0 and flex2:
                progressed = False
                for x in flex2:
                    safe_extra_cap = {
                        "long": 2.5,
                        "z2": 1.5,
                        "fatloss": 1.5,
                        "tempo": 0.8,
                    }.get(x.get("kind"), 0.6)
                    add = min(safe_extra_cap, diff)
                    if add > 0:
                        x["dur_h"] = round(x["dur_h"] + add, 1)
                        x["max"] = max(float(x.get("max", 0)), x["dur_h"])
                        x["detail"] = f"{x.get('detail','')}｜为匹配周总时长,额外时间放在低风险有氧容量,不要提高强度。"
                        diff = round(diff - add, 1)
                        progressed = True
                    if diff <= 0:
                        break
                if not progressed:
                    break
                # prevent a pathological infinite fill; normal UI targets are far below this.
                if current_total() >= max(target_h, 24):
                    break
    elif diff < 0:
        flex_down = [x for x in reversed(flex or items)]
        for x in flex_down:
            sub = min(round(x["dur_h"] - x.get("min", 0), 1), -diff)
            if sub > 0:
                x["dur_h"] = round(x["dur_h"] - sub, 1)
                diff = round(diff + sub, 1)
            if diff >= 0:
                break

    # Final small rounding correction on the longest safe session.
    final_diff = round(target_h - current_total(), 1)
    if abs(final_diff) > 0 and abs(final_diff) <= 0.3:
        candidates = sorted(flex or items, key=lambda y: y.get("dur_h", 0), reverse=True)
        if candidates:
            candidates[0]["dur_h"] = max(0, round(candidates[0].get("dur_h", 0) + final_diff, 1))
    return items


def select_sessions_for_days(source_items: list[dict[str, Any]], days: int) -> list[dict[str, Any]]:
    """Choose sessions for available days.

    True long/Z2 capacity work must not be displaced by crit/race workouts. Crit
    and race sessions are hard/specific sessions; they should not consume the
    weekly long-ride slot when a real long ride exists.
    """
    true_long_items = [x for x in source_items if x.get("kind") == "long"]
    hard_items = [x for x in source_items if x.get("kind") in HARD_KINDS and x not in true_long_items]
    support_items = [x for x in source_items if x not in true_long_items and x not in hard_items]
    selected: list[dict[str, Any]] = []
    hard_limit = 1 if days <= 3 else 2 if days <= 5 else 3
    if true_long_items:
        selected.append(true_long_items[0])
    selected.extend(hard_items[:hard_limit])
    for x in support_items + hard_items[hard_limit:] + true_long_items[1:]:
        if len(selected) >= days:
            break
        selected.append(x)
    return selected[:days]


def arrange_week_rows(
    items: list[dict[str, Any]],
    selected_training_days: list[str],
    preferred_long_day: str,
    no_hard_days: list[str],
) -> list[dict[str, Any]]:
    active_days = [d for d in DAY_ORDER if d in selected_training_days]
    by_day: dict[str, dict[str, Any]] = {}
    items = [dict(x) for x in items]
    long_idx = next((i for i, x in enumerate(items) if x.get("kind") in ("long", "crit", "race")), None)
    if long_idx is not None and preferred_long_day in active_days:
        by_day[preferred_long_day] = items.pop(long_idx)
        active_days = [d for d in active_days if d != preferred_long_day]
    remaining = [dict(x) for x in items]
    last_hard_idx: int | None = None
    for d in active_days:
        day_idx = DAY_ORDER.index(d)
        chosen_idx = None
        for i, candidate in enumerate(remaining):
            would_be_hard = candidate.get("kind") in HARD_KINDS
            if d in no_hard_days and would_be_hard:
                continue
            if would_be_hard and last_hard_idx is not None and day_idx - last_hard_idx < 2:
                continue
            chosen_idx = i
            break
        if chosen_idx is None:
            # Fallback: pick first item and downgrade if it violates scheduling constraints.
            chosen_idx = 0
        item = dict(remaining.pop(chosen_idx))
        if d in no_hard_days and item.get("kind") in HARD_KINDS:
            original = item.get("name", "")
            item.update({
                "kind": "z2",
                "name": f"避开高强度日 Z2(原:{original})",
                "detail": "该日被设置为不安排高强度,自动改为 Z2/技术骑。",
                "share": max(0.8, item.get("share", 1.0) * 0.75),
                "min": 0.6,
                "max": 2.2,
            })
        if item.get("kind") in HARD_KINDS and last_hard_idx is not None and day_idx - last_hard_idx < 2:
            original = item.get("name", "")
            item.update({
                "kind": "z2",
                "name": f"间隔保护 Z2(原:{original})",
                "detail": "为避免连续高强度,自动改为 Z2/技术骑。",
                "share": max(0.8, item.get("share", 1.0) * 0.75),
                "min": 0.6,
                "max": 2.5,
            })
        if item.get("kind") in HARD_KINDS:
            last_hard_idx = day_idx
        by_day[d] = item
    rows = []
    for day in DAY_ORDER:
        if day in by_day:
            item = dict(by_day[day])
            item.update({"day": day, "rest": False})
        else:
            item = {"day": day, "kind": "rest", "name": "休息 / 恢复", "detail": "固定休息日或不安排结构化训练", "dur_h": 0, "rest": True}
        rows.append(item)
    return rows


def validate_week_plan(
    *,
    rows: list[dict[str, Any]],
    phase: str,
    wk: int,
    target_h: float,
    preferred_long_day: str,
    no_hard_days: list[str],
    intensity_cap: str = "normal",
) -> dict[str, Any]:
    """Coach-style quality gate for a generated week.

    The generator should already avoid most issues; this layer makes the result
    auditable and visible in the UI.
    """
    issues: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []
    active = [r for r in rows if not r.get("rest") and r.get("dur_h", 0) > 0]
    actual_h = round(sum(float(r.get("dur_h", 0) or 0) for r in active), 1)
    hard_rows = [r for r in active if r.get("kind") in HARD_KINDS]
    hard_days = [DAY_ORDER.index(r.get("day")) for r in hard_rows if r.get("day") in DAY_ORDER]
    rest_like = [r for r in rows if r.get("rest") or r.get("kind") in {"recovery", "rest"} or float(r.get("dur_h", 0) or 0) <= 0.4]
    long_rows = [r for r in active if r.get("kind") == "long"]

    for a, b in zip(hard_days, hard_days[1:]):
        if b - a < 2:
            issues.append("高强度课间隔不足48h,建议中间插入恢复/Z2。")
            break
    for r in hard_rows:
        if r.get("day") in no_hard_days:
            issues.append(f"{r.get('day')} 被设为不安排高强度,但仍出现 {r.get('name')}。")
    if not rest_like:
        issues.append("本周没有明确休息或Z1恢复日。")
    if long_rows and preferred_long_day and all(r.get("day") != preferred_long_day for r in long_rows):
        warnings.append("长距离/模拟课没有排在指定长距离日。")
    if len(hard_rows) > 3:
        warnings.append("一周高强度课超过3个,仅适合恢复很好且目标明确的骑手。")
    if intensity_cap == "recovery" and hard_rows:
        issues.append("恢复优先状态下仍存在高强度课。")
    if intensity_cap == "caution" and len(hard_rows) > 1:
        warnings.append("谨慎推进状态下高强度超过1个,建议只保留最关键课。")

    if target_h:
        deviation = actual_h - target_h
        if abs(deviation) > max(1.0, target_h * 0.18):
            warnings.append(f"实际时长 {actual_h}h 与目标 {target_h}h 偏差较大。")
    if ((wk - 1) % 4) == 3:
        hard_deload_rows = [r for r in hard_rows if r.get("kind") not in {"openers"}]
        long_hard_deload_rows = [r for r in hard_deload_rows if float(r.get("dur_h", 0) or 0) > 0.8]
        if phase not in {"taper"} and long_hard_deload_rows:
            warnings.append("第4周应以吸收/降量为主,不建议保留较长阈值/VO2/专项硬课。")
        elif phase not in {"taper"} and hard_rows:
            notes.append("第4周保留了短激活/开放式感受课:可做但不要力竭,状态差直接改Z2。")
        notes.append("第4周为吸收/恢复周:重点是降低总量并吸收前三周刺激。")
    if phase == "taper":
        if actual_h > target_h * 1.15 if target_h else False:
            warnings.append("减量期实际时长偏高,可能影响新鲜度。")
        notes.append("赛前减量目标:降低TSS,保留短刺激,避免新增疲劳。")
    if phase == "rebuild" and len(hard_rows) > 1:
        warnings.append("基础重建阶段高强度不宜过密,优先Z2、技术和恢复。")

    # Positive, week-specific audit notes. Keep them concrete so the UI is not repetitive.
    hard_names = [f"{r.get('day')} {r.get('name')}" for r in hard_rows]
    if hard_rows:
        notes.append(f"质量课数量:{len(hard_rows)}个(" + "；".join(hard_names[:3]) + ")。")
        if len(hard_rows) >= 2 and len(hard_days) >= 2:
            gaps = [DAY_ORDER[b] + "距" + DAY_ORDER[a] + f"约{b-a}天" for a, b in zip(hard_days, hard_days[1:])]
            notes.append("高强度间隔:" + "；".join(gaps) + "。")
        elif len(hard_rows) == 1:
            notes.append("本周只保留1个主要质量课,强度密度较可控。")
    else:
        notes.append("本周无硬强度课,以恢复/Z2/容量承接为主。")
    if rest_like:
        rest_desc = [f"{r.get('day')} {r.get('name')}" for r in rest_like[:3]]
        notes.append("恢复安排:" + "；".join(rest_desc) + "。")
    if long_rows:
        notes.append("长距离安排:" + "；".join(f"{r.get('day')} {r.get('name')} {float(r.get('dur_h',0) or 0):.1f}h" for r in long_rows[:2]) + "。")
    if target_h:
        notes.append(f"时长匹配:目标{target_h:.1f}h,实际{actual_h:.1f}h,差值{actual_h-target_h:+.1f}h。")

    score = 100 - 18 * len(issues) - 8 * len(warnings)
    score = max(0, min(100, score))
    if issues:
        status = "需调整"
    elif warnings:
        status = "可用但需留意"
    else:
        status = "通过"
    return {"status": status, "score": score, "issues": issues, "warnings": warnings, "notes": notes}


def build_week_plan(
    *,
    phase: str,
    wk: int,
    ftp: float | int,
    hours: float,
    readiness_factor: float,
    intensity_cap: str,
    selected_training_days: list[str],
    preferred_long_day: str,
    no_hard_days: list[str],
    ftp_status: str = "confirmed",
    forbidden_modules: list[str] | None = None,
    caution_notes: list[str] | None = None,
    mmp_focus: str | None = None,
    mmp_focus_notes: list[str] | None = None,
    cadence_state: dict[str, Any] | None = None,
    event_context: dict[str, Any] | None = None,
    progression_state: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], str, str, tuple[str, ...]]:
    theme_name, theme_desc, theme_sources = week_theme(phase, wk)
    days = len(selected_training_days)
    forbidden = set(forbidden_modules or [])
    caution_notes = caution_notes or []
    mmp_focus_notes = mmp_focus_notes or []
    cadence_state = cadence_state or {}
    event_context = event_context or {}
    progression_state = progression_state or {}
    for mod in cadence_state.get("forbidden_modules", []) or []:
        forbidden.add(mod)
    for mod in event_context.get("forbidden_modules", []) or []:
        forbidden.add(mod)
    cadence_notes = cadence_state.get("notes", []) or []
    event_notes = event_context.get("notes", []) or []
    progression_notes = progression_state.get("notes", []) or []
    source_items = phase_week_items(phase, wk, ftp)
    if event_notes and event_context.get("focus") == "taper":
        for x in source_items:
            if x.get("kind") in HARD_KINDS:
                x["detail"] = (x.get("detail", "") + "｜阶段D-比赛:" + "；".join(event_notes[:2]) + " 减量保感觉,不要新增疲劳。").strip()
                x["max"] = min(float(x.get("max", 1.5) or 1.5), 1.2)
                x["source_tags"] = tuple(x.get("source_tags") or ()) + ("stage_d_event", "taper")
                break
    if ftp_status in {"unknown", "suspected_high"}:
        # FTP is the ruler for threshold/VO2 prescriptions; when the ruler is
        # unreliable, preserve structure but reduce maximal intensity density.
        forbidden.add("ftp_test")
        forbidden.add("max_vo2_density")
    if ftp_status in {"candidate", "candidate_up"}:
        forbidden.add("ftp_test")

    def apply_stage_d_event(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not event_context or event_context.get("focus") in {None, "none", "base_build"}:
            return items
        out = [dict(x) for x in items]
        focus = event_context.get("focus")
        note = "｜阶段D-比赛:" + "；".join(event_notes[:2]) if event_notes else "｜阶段D-比赛:按比赛倒计时微调。"
        if focus in {"race_week", "taper"}:
            for x in out:
                if x.get("kind") in HARD_KINDS and x.get("kind") != "openers":
                    original = x.get("name", "")
                    if focus == "race_week":
                        x.update({
                            "kind": "openers",
                            "name": f"赛前激活(原:{original})",
                            "detail": "阶段D-比赛:赛前7天内不补短板,改为短激活/恢复,不做力竭。",
                            "share": .6,
                            "min": .4,
                            "max": 1.0,
                        })
                    else:
                        x["detail"] = (x.get("detail", "") + note + " 减量保感觉,不要新增疲劳。").strip()
                        x["max"] = min(float(x.get("max", 1.5) or 1.5), 1.2)
                    x["source_tags"] = tuple(x.get("source_tags") or ()) + ("stage_d_event", focus)
                    break
        elif focus == "specific":
            for x in out:
                if x.get("kind") in HARD_KINDS or x.get("kind") in {"long", "tempo", "sweet"}:
                    x["detail"] = (x.get("detail", "") + note).strip()
                    x["source_tags"] = tuple(x.get("source_tags") or ()) + ("stage_d_event", "specific")
                    break
        return out

    source_items = apply_stage_d_event(source_items)

    def apply_stage_b_focus(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not mmp_focus or mmp_focus in {"balanced", "readiness_first", "ftp_first", "insufficient_data"}:
            return items
        out = [dict(x) for x in items]
        note = "｜阶段B-MMP:" + "；".join(mmp_focus_notes[:2]) if mmp_focus_notes else "｜阶段B-MMP:按功率画像微调训练重点。"
        if mmp_focus == "matchbook" and phase == "crit":
            for x in out:
                if x.get("kind") in {"crit", "vo2"}:
                    x["detail"] = (x.get("detail", "") + note + " 火柴课只做到可重复,不做力竭。").strip()
                    x["source_tags"] = tuple(x.get("source_tags") or ()) + ("stage_b_mmp", "matchbook_focus")
                    break
        elif mmp_focus == "vo2" and phase in {"build", "climb", "crit"}:
            for x in out:
                if x.get("kind") in {"vo2", "threshold", "climb"}:
                    if x.get("kind") != "vo2":
                        x.update({
                            "kind": "vo2",
                            "name": f"MMP保守VO2(原:{x.get('name','')})",
                            "detail": "阶段B-MMP:5min证据提示VO2可作为本周重点,采用保守组数,宁可少做不炸。",
                            "share": min(float(x.get("share", 1.0) or 1.0), 1.0),
                            "min": 0.8,
                            "max": 1.3,
                        })
                    else:
                        x["detail"] = (x.get("detail", "") + note + " 保守组数,不做力竭。").strip()
                    x["source_tags"] = tuple(x.get("source_tags") or ()) + ("stage_b_mmp", "vo2_focus")
                    break
        elif mmp_focus == "tte" and phase in {"build", "climb", "maintain"}:
            for x in out:
                if x.get("kind") in {"sweet", "threshold", "tempo"}:
                    x["detail"] = (x.get("detail", "") + note + " 重点是延长可控持续时间,不是上调FTP。").strip()
                    x["source_tags"] = tuple(x.get("source_tags") or ()) + ("stage_b_mmp", "tte_focus")
                    break
        return out

    source_items = apply_stage_b_focus(source_items)

    def apply_stage_f_progression(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not progression_state or progression_state.get("mode") in {None, "disabled_by_safety", "stable_rebuild"}:
            return items
        out = [dict(x) for x in items]
        mode = progression_state.get("mode")
        note = "｜阶段F-稳定推进:" + "；".join(progression_notes[:2]) if progression_notes else "｜阶段F-稳定推进:按训练背景小幅调整推进速度。"
        adjusted = 0
        for x in out:
            if x.get("kind") in {"z2", "tempo", "sweet", "long"}:
                old_share = float(x.get("share", 1.0) or 1.0)
                factor = 1.06 if mode == "trained_return" else 1.08
                x["share"] = min(old_share * factor, old_share + 0.12)
                x["max"] = min(float(x.get("max", 2.0) or 2.0) + 0.15, 3.5)
                x["detail"] = (x.get("detail", "") + note + " 不按历史FTP加码,只小幅提高可持续容量。").strip("｜")
                x["source_tags"] = tuple(x.get("source_tags") or ()) + ("stage_f_progression", mode)
                adjusted += 1
                if adjusted >= 2:
                    break
        return out

    source_items = apply_stage_f_progression(source_items)

    def apply_stage_a_guards(x: dict[str, Any]) -> dict[str, Any]:
        item = dict(x)
        name = item.get("name", "")
        detail = item.get("detail", "")
        tags = set(item.get("source_tags") or ())
        label = name + " " + detail + " " + " ".join(tags)
        if "ftp_test" in forbidden and ("FTP" in label or "小测试" in label or "ftp_check" in tags):
            item.update({
                "kind": "z2",
                "name": f"FTP未确认保护 Z2(原:{name})",
                "detail": "阶段A保护:FTP证据不足或状态不适合测试,本次不做FTP测试/开放式冲击,改为轻松Z2。",
                "share": max(0.8, float(item.get("share", 1.0) or 1.0) * 0.85),
                "min": 0.6,
                "max": 2.0,
            })
        if "low_cadence_torque" in forbidden and ("低踏频" in label or "muscular_endurance" in tags):
            reason = "阶段C保护:" + ("；".join(cadence_notes[:2]) if cadence_notes else "踏频/扭矩或疼痛风险提示,禁用低踏频高扭矩课。")
            item.update({
                "kind": "z2",
                "name": f"踏频扭矩保护 Z2(原:{name})",
                "detail": reason + " 改为轻齿比Z2/技术骑。",
                "share": max(0.8, float(item.get("share", 1.0) or 1.0) * 0.85),
                "min": 0.6,
                "max": 2.2,
            })
        elif "cadence_skill" in (cadence_state.get("recommended_modules", []) or []) and item.get("kind") in {"z2", "tempo"} and ("高踏频" in label or "技术" in label or "cadence" in tags or "skills" in tags):
            item["detail"] = (item.get("detail", "") + "｜阶段C-踏频:" + "；".join(cadence_notes[:2]) + "").strip("｜")
            item["source_tags"] = tuple(item.get("source_tags") or ()) + ("stage_c_cadence",)
        if "max_vo2_density" in forbidden and item.get("kind") == "vo2":
            item.update({
                "kind": "sweet",
                "name": f"FTP保护甜区(原:{name})",
                "detail": "阶段A保护:FTP证据不足/疑似偏高时不做高密度VO2,改为可控甜区或Z2承接。",
                "share": max(0.9, float(item.get("share", 1.0) or 1.0) * 0.9),
                "min": 0.8,
                "max": 1.5,
            })
        if caution_notes:
            item["detail"] = (item.get("detail", "") + "｜" + "；".join(caution_notes[:2])).strip("｜")
        return item

    source_items = [apply_stage_a_guards(x) for x in source_items]
    items = select_sessions_for_days(source_items, days)
    if intensity_cap in ("recovery", "caution"):
        hard_seen = 0
        for x in items:
            if x.get("kind") in HARD_KINDS:
                hard_seen += 1
                original = x.get("name", "")
                if intensity_cap == "recovery":
                    x.update({"kind": "recovery", "name": f"恢复替代(原:{original})", "detail": "因训练负荷/睡眠/反馈风险,本周改为 Z1-Z2 恢复。", "share": .55, "min": .4, "max": 1.2})
                elif hard_seen == 1:
                    x["detail"] = (x.get("detail", "") + " 谨慎推进:保留本周最关键质量课,只做到可控完成,不做力竭。").strip()
                    x["max"] = min(float(x.get("max", 2.0) or 2.0), 1.8)
                elif hard_seen == 2:
                    x.update({"kind": "z2", "name": f"降级执行(原:{original})", "detail": "谨慎推进:减少本周强度密度,第二个质量课改为 Z2/技术骑。", "share": .9, "min": .8, "max": 2.2})
                else:
                    x.update({"kind": "recovery", "name": f"恢复替代(原:{original})", "detail": "谨慎推进:本周不堆第三个高强度,改为 Z1-Z2 恢复。", "share": .55, "min": .4, "max": 1.2})
    progression_multiplier = _num(progression_state.get("volume_multiplier", 1.0)) or 1.0
    if intensity_cap != "normal" or progression_state.get("mode") == "disabled_by_safety" or event_context.get("focus") in {"race_week", "taper"}:
        progression_multiplier = min(progression_multiplier, 1.0)
    target_h = round(hours * week_factor(phase, wk, readiness_factor) * min(progression_multiplier, 1.12), 1)
    items = allocate_durations(items, target_h)
    rows = arrange_week_rows(items, selected_training_days, preferred_long_day, no_hard_days)
    return rows, theme_name, theme_desc, theme_sources


def rules_summary() -> str:
    return "规则层来源:功率区间、课表设计、周期化、PMC/TSB、Friel/Coggan核心训练原则与踏频单车训练方法论。"
