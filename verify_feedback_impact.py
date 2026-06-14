from __future__ import annotations

from datetime import date

from services.feedback_impact import build_feedback_impact_notice, describe_feedback_entry
from services.plan_preferences import normalize_plan_prefs
from services.training_calendar import week_plan_context

TODAY = date(2026, 6, 11)
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


def test_entry_summary():
    entry = {"sleep_quality": 2, "leg_fatigue": 5, "rpe": 9, "completion": "没完成", "fueling": "吃少了", "pains": ["膝盖"], "specials": ["发烧"]}
    text = describe_feedback_entry(entry)
    assert_true("summary_sleep", "睡眠 2/5" in text, text)
    assert_true("summary_special", "发烧" in text, text)


def test_notice_with_changes():
    baseline = week_plan_context(TODAY, PREFS, readiness=None)
    gated = week_plan_context(TODAY, PREFS, readiness={"level": "谨慎推进", "intensity_cap": "caution"})
    notice = build_feedback_impact_notice(
        entry={"sleep_quality": 3, "leg_fatigue": 4, "rpe": 7, "completion": "正常完成"},
        readiness={"level": "谨慎推进", "headline": "本周可以练，但不要加码", "reason": "腿部疲劳偏高", "intensity_cap": "caution", "actions": ["最多保留 1 次质量课"]},
        baseline_ctx=baseline,
        gated_ctx=gated,
    )
    assert_true("notice_level", notice["level"] == "谨慎推进", notice)
    assert_true("notice_change_count", notice["change_count"] >= 2, notice)
    assert_true("notice_impact_quality", "轻甜区" in notice["impact"] and "Z2 有氧 45–60" in notice["impact"], notice)


def test_notice_no_changes():
    baseline = week_plan_context(TODAY, PREFS, readiness=None)
    gated = week_plan_context(TODAY, PREFS, readiness={"level": "可推进", "intensity_cap": "normal"})
    notice = build_feedback_impact_notice(
        entry={"sleep_quality": 4, "leg_fatigue": 2, "rpe": 4, "completion": "轻松完成"},
        readiness={"level": "可推进", "headline": "本周可以按目标推进", "reason": "状态稳定", "intensity_cap": "normal"},
        baseline_ctx=baseline,
        gated_ctx=gated,
    )
    assert_true("notice_no_changes", notice["change_count"] == 0, notice)
    assert_true("notice_no_changes_text", "暂未触发" in notice["impact"], notice)


if __name__ == "__main__":
    test_entry_summary()
    test_notice_with_changes()
    test_notice_no_changes()
    print("OK feedback impact checks passed")
