from __future__ import annotations

from tc_pages.v2.plan import _four_week_focus


def assert_true(name, cond, value=None):
    if not cond:
        raise AssertionError(f"{name}: failed {value!r}")
    print(f"PASS {name}")


def test_normal_goal_direction():
    rows = _four_week_focus("提升 FTP / 阈值能力", {"level": "可推进", "intensity_cap": "normal", "reason": "TSB 在常规训练区间"})
    assert_true("normal_four_rows", len(rows) == 4, rows)
    assert_true("normal_status_note", "当前状态允许推进" in rows[0][2], rows[0])
    assert_true("normal_goal", rows[2][1] == "目标刺激", rows)


def test_caution_overrides_goal():
    rows = _four_week_focus("提升 FTP / 阈值能力", {"level": "谨慎推进", "intensity_cap": "caution", "reason": "腿部疲劳偏高"})
    assert_true("caution_first", rows[0][1] == "谨慎承接", rows)
    assert_true("caution_recovery_rule", "恢复 1 次质量课" in rows[1][2], rows[1])


def test_recovery_overrides_goal():
    rows = _four_week_focus("比赛专项", {"level": "恢复优先", "intensity_cap": "recovery", "reason": "发烧"})
    assert_true("recovery_first", rows[0][1] == "恢复优先", rows)
    assert_true("recovery_no_hard", "取消结构化高强度" in rows[0][2], rows[0])
    assert_true("recovery_rebuild", "重新定方向" in rows[3][1], rows)


if __name__ == "__main__":
    test_normal_goal_direction()
    test_caution_overrides_goal()
    test_recovery_overrides_goal()
    print("OK four-week direction checks passed")
