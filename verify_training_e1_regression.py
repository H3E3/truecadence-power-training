#!/usr/bin/env python3
"""Stage-E1 local regression checks for TrueCadence training plan bridge.

These are integration-style checks across A/B/C/D priorities. They are kept
separate from verify_training_rules_bridge.py so production deployment can run
both the rule-unit checks and the end-to-end regression gate.
"""
from __future__ import annotations

from training_plan_rules import (
    build_cadence_torque_state,
    build_event_context,
    build_week_plan,
    choose_mmp_training_focus,
)

DAYS = ["周二", "周三", "周五", "周六", "周日"]


def active(rows):
    return [r for r in rows if r.get("kind") != "rest"]


def text(rows):
    return " | ".join(f"{r.get('name','')} {r.get('detail','')}" for r in rows)


def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)


def plan(**kw):
    defaults = dict(
        phase="build",
        wk=1,
        ftp=250,
        hours=8,
        readiness_factor=1.0,
        intensity_cap="normal",
        selected_training_days=DAYS,
        preferred_long_day="周日",
        no_hard_days=[],
        ftp_status="confirmed",
        forbidden_modules=[],
        caution_notes=[],
        mmp_focus=None,
        mmp_focus_notes=[],
        cadence_state={},
        event_context={},
    )
    defaults.update(kw)
    rows, *_ = build_week_plan(**defaults)
    return rows


def case_e01_normal_no_event_no_stage_d_pollution():
    ev = build_event_context(event_type="无比赛", days_to_event=None, readiness="normal")
    rows = plan(phase="build", event_context=ev)
    t = text(rows)
    assert_true("阶段D-比赛" not in t and "赛前激活" not in t, t)


def case_e02_recovery_overrides_race_week():
    ev = build_event_context(event_type="绕圈赛", days_to_event=5, readiness="recovery")
    rows = plan(phase=ev.get("phase_override") or "crit", intensity_cap="recovery", readiness_factor=0.65, event_context=ev)
    t = text(rows)
    hard = [r for r in active(rows) if r.get("kind") in {"vo2", "threshold", "crit", "climb"}]
    assert_true(not hard, t)
    assert_true("恢复" in t, t)


def case_e03_ftp_unknown_blocks_test_even_with_taper_event():
    ev = build_event_context(event_type="公路赛", days_to_event=10, readiness="normal")
    rows = plan(phase=ev.get("phase_override") or "taper", wk=4, ftp_status="unknown", event_context=ev)
    t = text(rows)
    assert_true("FTP" not in " ".join(r.get("name", "") for r in active(rows)) or "FTP未确认保护" in t, t)
    assert_true("FTP小测试" not in t, t)


def case_e04_cadence_pain_overrides_climb_specific():
    ev = build_event_context(event_type="爬坡赛", days_to_event=35, readiness="normal")
    cad = build_cadence_torque_state(avg_cadence=68, low_cadence_ratio=0.4, pain_items=["膝盖疼"], readiness="normal", ftp_status="confirmed")
    rows = plan(phase=ev.get("phase_override") or "climb", wk=2, event_context=ev, cadence_state=cad)
    t = text(rows)
    assert_true("踏频扭矩保护" in t, t)
    assert_true(not any(r.get("kind") == "climb" and "低踏频力量耐力" in r.get("name", "") for r in active(rows)), t)


def case_e05_mmp_focus_does_not_override_low_confidence():
    focus = choose_mmp_training_focus(
        phase="crit", ftp=250, best_powers={60: 310}, mmp_confidence="低", readiness="normal", ftp_status="confirmed"
    )
    assert_true(focus["focus"] == "insufficient_data", focus)
    rows = plan(phase="crit", mmp_focus=focus["focus"], mmp_focus_notes=focus["notes"])
    assert_true("阶段B-MMP" not in text(rows), text(rows))


def case_e06_race_week_openers_not_full_weakness_block():
    ev = build_event_context(event_type="绕圈赛", days_to_event=3, readiness="normal")
    rows = plan(phase=ev.get("phase_override") or "crit", event_context=ev)
    t = text(rows)
    assert_true("赛前激活" in t or any(r.get("kind") == "openers" for r in active(rows)), t)
    assert_true(not any(r.get("kind") in {"vo2", "threshold", "crit", "climb"} for r in active(rows)), t)


def case_e07_goal_event_mapping_contract():
    # Product contract mirrored from app.py: non-race goals must clear Stage-D.
    mapping = {
        "备战绕圈赛": "绕圈赛",
        "备战爬坡赛": "爬坡赛",
        "备战个人计时赛": "个人计时赛",
        "备战长距离耐力赛": "长距离耐力赛",
        "备战公路赛": "公路赛",
    }
    non_race = [
        "恢复体能 / 重建基础",
        "减脂减重 / 燃脂骑",
        "提升 FTP / 功体比",
        "赛前减量 / 巅峰",
        "维持现状 / 休闲骑",
    ]
    for goal in non_race:
        assert_true(mapping.get(goal, "无比赛") == "无比赛", goal)
    assert_true(mapping["备战个人计时赛"] == "个人计时赛", mapping)


def case_e08_export_steady_sessions_are_segmented():
    # Static guard for Intervals.icu compatibility: long steady exports should not be one huge SteadyState.
    app = open("app.py", "r", encoding="utf-8").read()
    training_plan_page = open("tc_pages/training_plan_page.py", "r", encoding="utf-8").read()
    workout_export = open("services/workout_export.py", "r", encoding="utf-8").read()
    combined_ui = app + "\n" + training_plan_page
    assert_true("remaining > 3600" in workout_export and "use = min(1800, remaining)" in workout_export, "long steady split missing")
    assert_true("Intervals.icu / Zwift .ZWO" in combined_ui and "ERG 功率训练台 / Intervals 备选 .ERG" in combined_ui, "export labels missing")


def case_e09_taper_goal_is_not_auto_road_race():
    app = open("app.py", "r", encoding="utf-8").read()
    training_plan_page = open("tc_pages/training_plan_page.py", "r", encoding="utf-8").read()
    combined_ui = app + "\n" + training_plan_page
    start = combined_ui.index("GOAL_TO_EVENT_TYPE = {")
    end = combined_ui.index("TRAINING_EXPERIENCE_OPTIONS", start)
    block = combined_ui[start:end]
    assert_true("赛前减量 / 巅峰" not in block, block)


CASES = [
    case_e01_normal_no_event_no_stage_d_pollution,
    case_e02_recovery_overrides_race_week,
    case_e03_ftp_unknown_blocks_test_even_with_taper_event,
    case_e04_cadence_pain_overrides_climb_specific,
    case_e05_mmp_focus_does_not_override_low_confidence,
    case_e06_race_week_openers_not_full_weakness_block,
    case_e07_goal_event_mapping_contract,
    case_e08_export_steady_sessions_are_segmented,
    case_e09_taper_goal_is_not_auto_road_race,
]


def main():
    for c in CASES:
        c()
        print(f"PASS {c.__name__}")
    print(f"OK {len(CASES)} Stage-E1 regression checks passed")


if __name__ == "__main__":
    main()
