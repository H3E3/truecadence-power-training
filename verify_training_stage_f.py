"""Local verification for TrueCadence automatic-plan Stage F.

Stage F is the training-background / stable-progression layer. It must never
become a difficulty booster and must not override Stage A/B/C/D safety gates.
Run locally before any production deployment.
"""
from __future__ import annotations

from training_plan_rules import (
    build_cadence_torque_state,
    build_event_context,
    build_progression_state_v1,
    build_rider_state_v1,
    build_week_plan,
)

DAYS = ["周二", "周三", "周五", "周六", "周日"]
BEST = {"5s": 900, "1min": 500, "5min": 320, "20min": 250, "40min": 238, "60min": 232}


def active(rows):
    return [r for r in rows if not r.get("rest")]


def names(rows):
    return " | ".join((r.get("name", "") + " " + r.get("detail", "")).strip() for r in rows)


def tags(rows):
    out = []
    for r in active(rows):
        out.extend(list(r.get("source_tags") or ()))
    return out


def hard_kinds(rows):
    return [r.get("kind") for r in active(rows) if r.get("kind") in {"sweet", "threshold", "vo2", "crit", "climb", "openers", "race"}]


def assert_true(cond: bool, msg) -> None:
    if not cond:
        raise AssertionError(msg)


def normal_state():
    return build_rider_state_v1(
        ftp=250,
        ftp_source="客户填写 FTP 250W",
        best_powers=BEST,
        rides_count=8,
        current_tsb=0,
        current_ctl=50,
        current_atl=50,
    )


def case_f01_new_rider_advanced_preference_does_not_add_difficulty() -> None:
    state = normal_state()
    prog = build_progression_state_v1(
        goal="恢复体能 / 重建基础",
        current_ftp=180,
        weight=70,
        recent_rides_count=2,
        recent_weekly_hours=2,
        rider_state=state,
        mmp_confidence="低",
        training_experience="新手",
        detraining_duration="未填写",
        progression_preference="略进阶",
    )
    rows, *_ = build_week_plan(
        phase="rebuild", wk=1, ftp=180, hours=6, readiness_factor=1.0, intensity_cap="normal",
        selected_training_days=DAYS, preferred_long_day="周日", no_hard_days=[],
        ftp_status=state.ftp_status, forbidden_modules=state.forbidden_modules, caution_notes=[],
        progression_state=prog,
    )
    assert_true(prog["mode"] == "stable_rebuild", prog)
    assert_true("stage_f_progression" not in tags(rows), (prog, tags(rows), names(rows)))
    assert_true("VO2" not in names(rows) and "FTP测试" not in names(rows), names(rows))


def case_f02_trained_return_only_slightly_biases_z2_tempo_sweet() -> None:
    state = normal_state()
    prog = build_progression_state_v1(
        goal="恢复体能 / 重建基础",
        current_ftp=220,
        weight=65,
        recent_rides_count=8,
        recent_weekly_hours=5,
        rider_state=state,
        mmp_confidence="高",
        training_experience="有结构化训练经验",
        detraining_duration="3月以上",
        historical_best_ftp=270,
        historical_best_wkg=4.1,
        progression_preference="标准",
    )
    rows, *_ = build_week_plan(
        phase="build", wk=1, ftp=220, hours=8, readiness_factor=1.0, intensity_cap="normal",
        selected_training_days=DAYS, preferred_long_day="周日", no_hard_days=[],
        ftp_status=state.ftp_status, forbidden_modules=state.forbidden_modules, caution_notes=[],
        progression_state=prog,
    )
    text = names(rows)
    assert_true(prog["mode"] == "trained_return", prog)
    assert_true(1.0 <= float(prog["volume_multiplier"]) <= 1.08, prog)
    assert_true("stage_f_progression" in tags(rows), (prog, tags(rows), text))
    assert_true("不按历史FTP" in text or "历史能力只作背景" in "；".join(prog.get("notes", [])), (prog, text))
    assert_true(hard_kinds(rows).count("vo2") <= 1, (hard_kinds(rows), text))


def case_f03_trained_but_recovery_bad_disables_progression() -> None:
    state = build_rider_state_v1(
        ftp=250,
        ftp_source="客户填写 FTP 250W",
        best_powers=BEST,
        rides_count=8,
        current_tsb=-32,
        current_ctl=50,
        current_atl=88,
        avg_sleep=2,
        avg_fatigue=5,
    )
    prog = build_progression_state_v1(
        current_ftp=250,
        weight=65,
        recent_rides_count=8,
        recent_weekly_hours=6,
        rider_state=state,
        mmp_confidence="高",
        training_experience="有比赛经验",
        detraining_duration="无停训",
        progression_preference="略进阶",
    )
    assert_true(prog["mode"] == "disabled_by_safety", prog)
    assert_true(float(prog["volume_multiplier"]) <= 1.0, prog)
    assert_true(any("恢复" in x or "谨慎" in x for x in prog.get("notes", [])), prog)


def case_f04_pain_and_cadence_stage_c_override_stage_f() -> None:
    state = build_rider_state_v1(
        ftp=250,
        ftp_source="客户填写 FTP 250W",
        best_powers=BEST,
        rides_count=8,
        pain_items=["膝盖疼"],
    )
    cad = build_cadence_torque_state(avg_cadence=68, low_cadence_ratio=0.42, pain_items=["膝盖疼"], readiness=state.readiness, ftp_status=state.ftp_status)
    prog = build_progression_state_v1(
        current_ftp=250,
        weight=65,
        recent_rides_count=8,
        recent_weekly_hours=6,
        rider_state=state,
        mmp_confidence="高",
        cadence_state=cad,
        training_experience="有比赛经验",
        detraining_duration="无停训",
        progression_preference="略进阶",
    )
    rows, *_ = build_week_plan(
        phase="climb", wk=2, ftp=250, hours=8, readiness_factor=state.readiness_factor, intensity_cap=state.readiness,
        selected_training_days=DAYS, preferred_long_day="周日", no_hard_days=[],
        ftp_status=state.ftp_status, forbidden_modules=state.forbidden_modules, caution_notes=[],
        cadence_state=cad, progression_state=prog,
    )
    text = names(rows)
    assert_true(prog["mode"] == "disabled_by_safety", prog)
    assert_true("踏频扭矩保护" in text, text)
    assert_true("stage_f_progression" not in tags(rows), (tags(rows), text))


def case_f05_race_week_taper_overrides_advanced_preference() -> None:
    state = normal_state()
    ev = build_event_context(event_type="绕圈赛", days_to_event=5, readiness="normal")
    prog = build_progression_state_v1(
        current_ftp=250,
        weight=65,
        recent_rides_count=8,
        recent_weekly_hours=7,
        rider_state=state,
        mmp_confidence="高",
        event_context=ev,
        training_experience="有比赛经验",
        detraining_duration="无停训",
        progression_preference="略进阶",
    )
    rows, *_ = build_week_plan(
        phase=ev.get("phase_override") or "crit", wk=2, ftp=250, hours=8, readiness_factor=1.0, intensity_cap="normal",
        selected_training_days=DAYS, preferred_long_day="周日", no_hard_days=[],
        ftp_status=state.ftp_status, forbidden_modules=state.forbidden_modules, caution_notes=[],
        event_context=ev, progression_state=prog,
    )
    text = names(rows)
    assert_true(prog["mode"] == "disabled_by_safety", prog)
    assert_true("赛前激活" in text or any(r.get("kind") == "openers" for r in active(rows)), text)
    assert_true("stage_f_progression" not in tags(rows), (tags(rows), text))


def case_f06_ftp_unknown_disables_progression_and_blocks_test() -> None:
    state = build_rider_state_v1(
        ftp=0,
        ftp_source="",
        best_powers={},
        rides_count=1,
    )
    prog = build_progression_state_v1(
        current_ftp=0,
        weight=65,
        recent_rides_count=1,
        recent_weekly_hours=1,
        rider_state=state,
        mmp_confidence="低",
        training_experience="有结构化训练经验",
        detraining_duration="无停训",
        progression_preference="略进阶",
    )
    rows, *_ = build_week_plan(
        phase="build", wk=4, ftp=250, hours=8, readiness_factor=state.readiness_factor, intensity_cap=state.readiness,
        selected_training_days=DAYS, preferred_long_day="周日", no_hard_days=[],
        ftp_status=state.ftp_status, forbidden_modules=state.forbidden_modules, caution_notes=state.ftp_reasons + state.data_warnings,
        progression_state=prog,
    )
    text = names(rows)
    assert_true(prog["mode"] == "disabled_by_safety", prog)
    assert_true("FTP未确认保护" in text, (state, prog, text))
    assert_true("stage_f_progression" not in tags(rows), (tags(rows), text))


CASES = [
    case_f01_new_rider_advanced_preference_does_not_add_difficulty,
    case_f02_trained_return_only_slightly_biases_z2_tempo_sweet,
    case_f03_trained_but_recovery_bad_disables_progression,
    case_f04_pain_and_cadence_stage_c_override_stage_f,
    case_f05_race_week_taper_overrides_advanced_preference,
    case_f06_ftp_unknown_disables_progression_and_blocks_test,
]


def main() -> None:
    for case in CASES:
        case()
        print(f"PASS {case.__name__}")
    print(f"OK {len(CASES)} Stage-F progression checks passed")


if __name__ == "__main__":
    main()
