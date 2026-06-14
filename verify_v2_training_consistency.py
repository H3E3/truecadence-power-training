from __future__ import annotations

from pathlib import Path

from services.plan_preferences import DAY_ORDER, normalize_plan_prefs
from services.training_calendar import week_plan_context


ROOT = Path(__file__).resolve().parent


def assert_true(name: str, cond: bool, value=None) -> None:
    if not cond:
        raise AssertionError(f"{name}: failed {value!r}")
    print(f"PASS {name}")


def read_rel(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_week_context_uses_same_plan_prefs() -> None:
    prefs = normalize_plan_prefs({
        "goal": "提升 FTP / 阈值能力",
        "event_type": "公路赛",
        "event_date": "2026-07-12",
        "event_priority": "A",
        "training_days": ["周一", "周三", "周五"],
        "preferred_long_day": "周五",
        "no_hard_days": ["周三", "周四"],
    })
    ctx = week_plan_context(prefs=prefs, readiness={"level": "可推进", "intensity_cap": "normal"})
    assert_true("ctx_training_days", ctx["training_days"] == ["周一", "周三", "周五"], ctx["training_days"])
    assert_true("ctx_rest_days", ctx["rest_days"] == ["周二", "周四", "周六", "周日"], ctx["rest_days"])
    assert_true("ctx_long_day", ctx["preferred_long_day"] == "周五", ctx["preferred_long_day"])
    assert_true("ctx_no_hard_filtered", ctx["no_hard_days"] == ["周三"], ctx["no_hard_days"])
    assert_true("ctx_event_type", ctx["event_type"] == "公路赛", ctx.get("event_type"))
    assert_true("ctx_event_date", ctx["event_date"] == "2026-07-12", ctx.get("event_date"))
    assert_true("ctx_event_priority", ctx["event_priority"] == "A", ctx.get("event_priority"))
    weekday_titles = {s.weekday_label: s.title for s in ctx["sessions"]}
    assert_true("ctx_rest_day_is_rest", weekday_titles["周四"] == "休息日", weekday_titles)
    assert_true("ctx_long_day_title", "Z2" in weekday_titles["周五"] or "长距离" in weekday_titles["周五"], weekday_titles)


def test_v2_pages_do_not_keep_old_training_placeholders() -> None:
    combined = "\n".join(read_rel(path) for path in [
        "tc_pages/v2/profile.py",
        "tc_pages/v2/dashboard.py",
        "tc_pages/v2/plan.py",
        "tc_pages/v2/recovery.py",
        "tc_pages/v2/fueling.py",
    ])
    forbidden = [
        "二 / 四 / 六",
        "后续等其他页面完成后再接入真实设置",
        "3 次训练</span><span>约 4.5–5 小时</span><span>1 次质量课",
        "周四质量课优先降级",
    ]
    for text in forbidden:
        assert_true(f"no_old_placeholder:{text}", text not in combined)


def test_profile_reads_plan_prefs() -> None:
    profile_py = read_rel("tc_pages/v2/profile.py")
    assert_true("profile_imports_plan_prefs", "load_current_plan_prefs" in profile_py)
    assert_true("profile_displays_training_days_text", "training_days_text" in profile_py)
    assert_true("profile_data_source_plan_settings", "训练计划设置" in profile_py)


def test_primary_training_loop_actions_are_orange() -> None:
    shell_py = read_rel("tc_pages/v2/shell.py")
    dashboard_py = read_rel("tc_pages/v2/dashboard.py")
    plan_py = read_rel("tc_pages/v2/plan.py")
    recovery_py = read_rel("tc_pages/v2/recovery.py")
    fueling_py = read_rel("tc_pages/v2/fueling.py")
    assert_true("accordion_primary_style", ".accordion.primary" in shell_py and "#f06f32" in shell_py)
    assert_true("accordion_blue_style", ".accordion{" in shell_py and "88,166,255" in shell_py)
    assert_true("dashboard_record_feedback_primary", "记录反馈</a>" in dashboard_py and "btn primary" in dashboard_py)
    assert_true("dashboard_bottom_fueling_blue", "accordion blue" in dashboard_py and "今天吃什么" in dashboard_py)
    assert_true("dashboard_bottom_fueling_not_primary", "accordion primary" not in dashboard_py)
    assert_true("plan_today_detail_primary", "查看今日详情</a>" in plan_py and "btn primary" in plan_py)
    assert_true("plan_has_arrangement_handoff", "今日 / 本周安排" in plan_py and "本周策略已同步到下方 7 天课表" in plan_py)
    assert_true("plan_top_actions_orange", '查看今日详情</a><a target="_self" class="btn primary" href="#tc-plan-rationale-modal-layer">查看计划依据</a>' in plan_py and "记录反馈</a>" not in plan_py)
    assert_true("plan_top_no_fueling_jump", "今天吃什么</a>" not in plan_py)
    assert_true("recovery_single_feedback_entry", recovery_py.count("记录今日反馈") == 2)
    assert_true("recovery_bottom_fueling_blue", "accordion blue" in recovery_py and "今天吃什么" in recovery_py)
    assert_true("fueling_no_duplicate_feedback", "记录反馈</a>" not in fueling_py)


def test_dashboard_week_modal_dynamic_summary() -> None:
    dashboard_py = read_rel("tc_pages/v2/dashboard.py")
    assert_true("dashboard_uses_training_sessions", "training_sessions = ctx.get" in dashboard_py)
    assert_true("dashboard_uses_rest_days", "rest_days = ctx.get" in dashboard_py)
    assert_true("dashboard_dynamic_adaptive_rule", "adaptive_rule" in dashboard_py)
    assert_true("dashboard_shows_training_days", "可训练日：" in dashboard_py)


def test_plan_event_date_lightweight_integration() -> None:
    plan_py = read_rel("tc_pages/v2/plan.py")
    app_py = read_rel("app.py")
    assert_true("plan_settings_event_type", "name=\"event_type\"" in plan_py)
    assert_true("plan_settings_event_date", "name=\"event_date\"" in plan_py)
    assert_true("plan_settings_event_priority", "name=\"event_priority\"" in plan_py)
    assert_true("plan_event_summary", "_event_summary_text" in plan_py and "比赛：" in plan_py)
    assert_true("app_saves_event_date", "_tc_event_date" in app_py and "event_date" in app_py)


if __name__ == "__main__":
    test_week_context_uses_same_plan_prefs()
    test_v2_pages_do_not_keep_old_training_placeholders()
    test_profile_reads_plan_prefs()
    test_primary_training_loop_actions_are_orange()
    test_dashboard_week_modal_dynamic_summary()
    test_plan_event_date_lightweight_integration()
    print("OK V2 training consistency checks passed")
