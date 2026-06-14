from __future__ import annotations

from datetime import date

from services.training_calendar import week_plan_context
from services.plan_preferences import normalize_plan_prefs

TODAY = date(2026, 6, 11)  # 周四
PREFS = normalize_plan_prefs({
    "training_days": ["周一", "周三", "周四", "周六", "周日"],
    "preferred_long_day": "周日",
    "no_hard_days": ["周三"],
    "goal": "提升 FTP / 阈值能力",
})


def assert_true(name, cond, value=None):
    if not cond:
        raise AssertionError(f"{name}: failed {value!r}")
    print(f"PASS {name}")


def titles(ctx):
    return {s.weekday_label: s.title for s in ctx["sessions"]}


def kinds(ctx):
    return {s.weekday_label: s.kind for s in ctx["sessions"]}


def test_normal_keeps_plan():
    ctx = week_plan_context(TODAY, PREFS, {"level": "可推进", "intensity_cap": "normal"})
    t = titles(ctx)
    k = kinds(ctx)
    assert_true("normal_quality_kept", "轻甜区" in t["周一"], t)
    assert_true("normal_long_kept", "长距离" in t["周日"], t)
    assert_true("normal_rest_kept", k["周二"] == "休息", k)


def test_caution_downgrades_quality_and_long_only():
    ctx = week_plan_context(TODAY, PREFS, {"level": "谨慎推进", "intensity_cap": "caution"})
    t = titles(ctx)
    k = kinds(ctx)
    assert_true("caution_quality_downgraded", t["周一"] == "Z2 有氧 45–60 分钟", t)
    assert_true("caution_long_shortened", t["周日"] == "Z2 耐力 75–90 分钟", t)
    assert_true("caution_regular_z2_kept", "Z2 有氧" in t["周四"], t)
    assert_true("caution_rest_kept", k["周二"] == "休息", k)


def test_recovery_downgrades_all_training_days_not_rest_days():
    ctx = week_plan_context(TODAY, PREFS, {"level": "恢复优先", "intensity_cap": "recovery"})
    t = titles(ctx)
    k = kinds(ctx)
    training_days = ["周一", "周三", "周四", "周六", "周日"]
    assert_true("recovery_all_training_low", all(t[d] == "恢复骑 30–45 分钟 / 休息" for d in training_days), t)
    assert_true("recovery_rest_still_rest", k["周二"] == "休息", k)
    assert_true("recovery_context_today", ctx["today_context"]["session"].title == "恢复骑 30–45 分钟 / 休息", ctx["today_context"])


if __name__ == "__main__":
    test_normal_keeps_plan()
    test_caution_downgrades_quality_and_long_only()
    test_recovery_downgrades_all_training_days_not_rest_days()
    print("OK training calendar readiness gate checks passed")
