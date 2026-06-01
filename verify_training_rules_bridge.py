"""Local verification for TrueCadence automatic-plan bridge Stage A.

Run only locally. These cases protect anti-conflict rules before production.
"""
from __future__ import annotations

from training_plan_rules import (
    assess_plan_data_confidence,
    build_cadence_torque_state,
    build_event_context,
    build_rider_state_v1,
    build_week_plan,
    choose_mmp_training_focus,
)

DAYS = ["周二", "周三", "周五", "周六", "周日"]


def active(rows):
    return [r for r in rows if not r.get("rest")]


def names(rows):
    return " | ".join(r.get("name", "") + " " + r.get("detail", "") for r in rows)


def hard_count(rows):
    return sum(1 for r in active(rows) if r.get("kind") in {"sweet", "threshold", "vo2", "crit", "climb", "openers", "race"})


def assert_true(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def case_01_20min_strong_60_missing_no_global_ftp_update() -> None:
    c = assess_plan_data_confidence(
        ftp=250,
        ftp_source="客户填写 FTP 250W",
        best_powers={"20min": 270, "5min": 320, "1min": 520},
        rides_count=3,
    )
    assert_true(c["ftp_status"] == "candidate_up", c)
    assert_true(any("不直接上调" in x for x in c["ftp_reasons"]), c)


def case_02_one_min_weak_but_tsb_low_no_matchbook() -> None:
    state = build_rider_state_v1(
        ftp=250,
        ftp_source="客户填写 FTP 250W",
        best_powers={"1min": 300, "5min": 320, "20min": 250},
        rides_count=6,
        current_tsb=-30,
        current_ctl=60,
        current_atl=95,
    )
    rows, *_ = build_week_plan(
        phase="crit",
        wk=2,
        ftp=250,
        hours=8,
        readiness_factor=state.readiness_factor,
        intensity_cap=state.readiness,
        selected_training_days=DAYS,
        preferred_long_day="周日",
        no_hard_days=[],
        ftp_status=state.ftp_status,
        forbidden_modules=state.forbidden_modules,
        caution_notes=state.ftp_reasons + state.data_warnings,
    )
    text = names(rows)
    assert_true(state.readiness == "recovery", state)
    assert_true(all(r.get("kind") not in {"crit", "vo2", "threshold", "climb", "openers", "race"} for r in active(rows)), text)
    assert_true(hard_count(rows) == 0, text)


def case_03_auto_ftp_candidate_blocks_ftp_test() -> None:
    state = build_rider_state_v1(
        ftp=250,
        ftp_source="FIT 自动估算 FTP 250W",
        best_powers={"20min": 260, "5min": 310, "1min": 500},
        rides_count=3,
    )
    rows, *_ = build_week_plan(
        phase="build",
        wk=4,
        ftp=250,
        hours=8,
        readiness_factor=state.readiness_factor,
        intensity_cap=state.readiness,
        selected_training_days=DAYS,
        preferred_long_day="周日",
        no_hard_days=[],
        ftp_status=state.ftp_status,
        forbidden_modules=state.forbidden_modules,
        caution_notes=state.ftp_reasons + state.data_warnings,
    )
    text = names(rows)
    assert_true(state.ftp_status == "candidate", state)
    assert_true(all(r.get("kind") != "openers" for r in active(rows)), text)
    assert_true("FTP未确认保护" in text, text)


def case_06_knee_pain_climb_no_low_cadence_torque() -> None:
    state = build_rider_state_v1(
        ftp=250,
        ftp_source="客户填写 FTP 250W",
        best_powers={"5s": 900, "1min": 500, "5min": 320, "20min": 250, "40min": 235, "60min": 230},
        rides_count=8,
        pain_items=["膝盖疼"],
    )
    rows, *_ = build_week_plan(
        phase="climb",
        wk=2,
        ftp=250,
        hours=8,
        readiness_factor=state.readiness_factor,
        intensity_cap=state.readiness,
        selected_training_days=DAYS,
        preferred_long_day="周日",
        no_hard_days=[],
        ftp_status=state.ftp_status,
        forbidden_modules=state.forbidden_modules,
        caution_notes=state.ftp_reasons + state.data_warnings,
    )
    text = names(rows)
    assert_true("low_cadence_torque" in state.forbidden_modules, state)
    assert_true(all(not ("低踏频" in r.get("name", "") and r.get("kind") == "climb") for r in active(rows)), text)
    assert_true("踏频扭矩保护" in text or "疼痛保护" in text, text)


def case_07_high_hours_extra_goes_z2_not_vo2_stretch() -> None:
    state = build_rider_state_v1(
        ftp=250,
        ftp_source="客户填写 FTP 250W",
        best_powers={"5s": 900, "1min": 500, "5min": 320, "20min": 250, "40min": 235, "60min": 230},
        rides_count=8,
    )
    rows, *_ = build_week_plan(
        phase="build",
        wk=3,
        ftp=250,
        hours=18,
        readiness_factor=state.readiness_factor,
        intensity_cap=state.readiness,
        selected_training_days=DAYS,
        preferred_long_day="周日",
        no_hard_days=[],
        ftp_status=state.ftp_status,
        forbidden_modules=state.forbidden_modules,
        caution_notes=state.ftp_reasons + state.data_warnings,
    )
    vo2 = [r for r in rows if r.get("kind") == "vo2"]
    assert_true(all(float(r.get("dur_h", 0)) <= 1.5 for r in vo2), rows)


def case_08_no_5min_data_does_not_mark_weakness() -> None:
    c = assess_plan_data_confidence(
        ftp=250,
        ftp_source="客户填写 FTP 250W",
        best_powers={"20min": 245},
        rides_count=1,
    )
    assert_true(c["mmp_confidence"] == "低", c)
    assert_true(any("不把缺失窗口判为短板" in x for x in c["data_warnings"]), c)


def case_10_week4_absorption_still_deload() -> None:
    state = build_rider_state_v1(
        ftp=250,
        ftp_source="客户填写 FTP 250W",
        best_powers={"5s": 900, "1min": 500, "5min": 320, "20min": 250, "40min": 235, "60min": 230},
        rides_count=8,
    )
    rows, theme, desc, _ = build_week_plan(
        phase="build",
        wk=4,
        ftp=250,
        hours=8,
        readiness_factor=state.readiness_factor,
        intensity_cap=state.readiness,
        selected_training_days=DAYS,
        preferred_long_day="周日",
        no_hard_days=[],
        ftp_status=state.ftp_status,
        forbidden_modules=state.forbidden_modules,
        caution_notes=state.ftp_reasons + state.data_warnings,
    )
    assert_true("吸收" in theme or "吸收" in desc, (theme, desc))
    assert_true(hard_count(rows) <= 1, names(rows))


def case_b01_mmp_does_not_override_recovery() -> None:
    focus = choose_mmp_training_focus(
        phase="crit",
        ftp=250,
        best_powers={"1min": 330, "5min": 280, "20min": 250, "40min": 235, "60min": 230},
        mmp_confidence="高",
        readiness="recovery",
        ftp_status="confirmed",
    )
    assert_true(focus["allowed"] is False and focus["focus"] == "readiness_first", focus)


def case_b02_crit_weak_1min_marks_matchbook_when_safe() -> None:
    focus = choose_mmp_training_focus(
        phase="crit",
        ftp=250,
        best_powers={"1min": 360, "5min": 310, "20min": 250, "40min": 238, "60min": 230},
        mmp_confidence="高",
        readiness="normal",
        ftp_status="confirmed",
    )
    rows, *_ = build_week_plan(
        phase="crit", wk=2, ftp=250, hours=8, readiness_factor=1.0, intensity_cap="normal",
        selected_training_days=DAYS, preferred_long_day="周日", no_hard_days=[],
        ftp_status="confirmed", forbidden_modules=[], caution_notes=[],
        mmp_focus=focus["focus"], mmp_focus_notes=focus["notes"],
    )
    text = names(rows)
    assert_true(focus["focus"] == "matchbook" and focus["allowed"] is True, focus)
    assert_true("阶段B-MMP" in text and "火柴" in text, text)


def case_b03_build_weak_5min_adds_conservative_vo2() -> None:
    focus = choose_mmp_training_focus(
        phase="build",
        ftp=250,
        best_powers={"1min": 500, "5min": 270, "20min": 250, "40min": 235, "60min": 230},
        mmp_confidence="高",
        readiness="normal",
        ftp_status="confirmed",
    )
    rows, *_ = build_week_plan(
        phase="build", wk=3, ftp=250, hours=8, readiness_factor=1.0, intensity_cap="normal",
        selected_training_days=DAYS, preferred_long_day="周日", no_hard_days=[],
        ftp_status="confirmed", forbidden_modules=[], caution_notes=[],
        mmp_focus=focus["focus"], mmp_focus_notes=focus["notes"],
    )
    text = names(rows)
    assert_true(focus["focus"] == "vo2" and focus["allowed"] is True, focus)
    assert_true("阶段B-MMP" in text and "VO2" in text, text)


def case_b04_low_confidence_mmp_does_not_prescribe_weakness() -> None:
    focus = choose_mmp_training_focus(
        phase="build", ftp=250, best_powers={"20min": 250}, mmp_confidence="低", readiness="normal", ftp_status="confirmed"
    )
    assert_true(focus["allowed"] is False and focus["focus"] == "insufficient_data", focus)


def case_c01_low_cadence_pain_blocks_torque() -> None:
    cad = build_cadence_torque_state(
        avg_cadence=68, low_cadence_ratio=0.42, pain_items=["膝盖疼"], readiness="normal", ftp_status="confirmed"
    )
    rows, *_ = build_week_plan(
        phase="climb", wk=2, ftp=250, hours=8, readiness_factor=1.0, intensity_cap="normal",
        selected_training_days=DAYS, preferred_long_day="周日", no_hard_days=[],
        ftp_status="confirmed", forbidden_modules=[], caution_notes=[], cadence_state=cad,
    )
    text = names(rows)
    assert_true(cad["status"] == "low_cadence_torque_risk", cad)
    assert_true("low_cadence_torque" in cad["forbidden_modules"], cad)
    assert_true("踏频扭矩保护" in text and all(not (r.get("kind") == "climb" and "低踏频" in r.get("name", "")) for r in active(rows)), text)


def case_c02_no_cadence_data_does_not_change_plan() -> None:
    cad = build_cadence_torque_state(avg_cadence=0, low_cadence_ratio=0, high_cadence_ratio=0)
    assert_true(cad["status"] == "insufficient_data", cad)
    assert_true(not cad["forbidden_modules"] and not cad["recommended_modules"], cad)


def case_c03_low_cadence_without_pain_recommends_skill_only() -> None:
    cad = build_cadence_torque_state(avg_cadence=70, low_cadence_ratio=0.35, pain_items=[], readiness="normal", ftp_status="confirmed")
    rows, *_ = build_week_plan(
        phase="build", wk=1, ftp=250, hours=8, readiness_factor=1.0, intensity_cap="normal",
        selected_training_days=DAYS, preferred_long_day="周日", no_hard_days=[],
        ftp_status="confirmed", forbidden_modules=[], caution_notes=[], cadence_state=cad,
    )
    text = names(rows)
    assert_true("cadence_skill" in cad["recommended_modules"], cad)
    assert_true("阶段C-踏频" in text, text)


def case_d01_race_week_replaces_hard_with_openers() -> None:
    ev = build_event_context(event_type="绕圈赛", days_to_event=5, readiness="normal")
    rows, *_ = build_week_plan(
        phase=ev.get("phase_override") or "crit", wk=2, ftp=250, hours=8, readiness_factor=1.0, intensity_cap="normal",
        selected_training_days=DAYS, preferred_long_day="周日", no_hard_days=[],
        ftp_status="confirmed", forbidden_modules=[], caution_notes=[], event_context=ev,
    )
    text = names(rows)
    assert_true(ev["focus"] == "race_week" and ev["phase_override"] == "taper", ev)
    assert_true("赛前激活" in text or any(r.get("kind") == "openers" for r in active(rows)), text)
    assert_true("比赛获胜 AC-W3" not in text, text)


def case_d02_two_week_window_taper_not_new_weakness() -> None:
    ev = build_event_context(event_type="爬坡赛", days_to_event=12, readiness="normal")
    rows, *_ = build_week_plan(
        phase=ev.get("phase_override") or "climb", wk=1, ftp=250, hours=8, readiness_factor=1.0, intensity_cap="normal",
        selected_training_days=DAYS, preferred_long_day="周日", no_hard_days=[],
        ftp_status="confirmed", forbidden_modules=[], caution_notes=[], event_context=ev,
    )
    text = names(rows)
    assert_true(ev["focus"] == "taper", ev)
    assert_true("阶段D-比赛" in text and "减量" in text, text)


def case_d03_specific_window_overrides_to_crit() -> None:
    ev = build_event_context(event_type="绕圈赛", days_to_event=35, readiness="normal")
    assert_true(ev["focus"] == "specific" and ev["phase_override"] == "crit", ev)
    rows, *_ = build_week_plan(
        phase=ev.get("phase_override"), wk=1, ftp=250, hours=8, readiness_factor=1.0, intensity_cap="normal",
        selected_training_days=DAYS, preferred_long_day="周日", no_hard_days=[],
        ftp_status="confirmed", forbidden_modules=[], caution_notes=[], event_context=ev,
    )
    assert_true("阶段D-比赛" in names(rows), names(rows))


def case_d04_no_event_does_not_change() -> None:
    ev = build_event_context(event_type="无比赛", days_to_event=None, readiness="normal")
    assert_true(ev["focus"] == "none" and not ev["phase_override"], ev)


CASES = [
    case_01_20min_strong_60_missing_no_global_ftp_update,
    case_02_one_min_weak_but_tsb_low_no_matchbook,
    case_03_auto_ftp_candidate_blocks_ftp_test,
    case_06_knee_pain_climb_no_low_cadence_torque,
    case_07_high_hours_extra_goes_z2_not_vo2_stretch,
    case_08_no_5min_data_does_not_mark_weakness,
    case_10_week4_absorption_still_deload,
    case_b01_mmp_does_not_override_recovery,
    case_b02_crit_weak_1min_marks_matchbook_when_safe,
    case_b03_build_weak_5min_adds_conservative_vo2,
    case_b04_low_confidence_mmp_does_not_prescribe_weakness,
    case_c01_low_cadence_pain_blocks_torque,
    case_c02_no_cadence_data_does_not_change_plan,
    case_c03_low_cadence_without_pain_recommends_skill_only,
    case_d01_race_week_replaces_hard_with_openers,
    case_d02_two_week_window_taper_not_new_weakness,
    case_d03_specific_window_overrides_to_crit,
    case_d04_no_event_does_not_change,
]


def main() -> None:
    for case in CASES:
        case()
        print(f"PASS {case.__name__}")
    print(f"OK {len(CASES)} Stage-A/B/C/D bridge checks passed")


if __name__ == "__main__":
    main()
