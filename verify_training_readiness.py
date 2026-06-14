from __future__ import annotations

from datetime import date, timedelta

from services.training_metrics import compute_daily_pmc
from services.training_readiness import build_training_readiness

TODAY = date(2026, 6, 11)


def assert_eq(name, actual, expected):
    if actual != expected:
        raise AssertionError(f"{name}: expected {expected!r}, got {actual!r}")
    print(f"PASS {name}")


def assert_true(name, cond, value=None):
    if not cond:
        raise AssertionError(f"{name}: failed {value!r}")
    print(f"PASS {name}")


def sample_rides(days=28, tss=45):
    start = TODAY - timedelta(days=days - 1)
    rows = []
    for i in range(days):
        d = start + timedelta(days=i)
        if d.weekday() in {1, 3, 5, 6}:
            rows.append({"date": d.isoformat(), "dur": 75, "tss": tss, "avg_p": 170, "np": 185})
    return rows


def test_normal_push():
    readiness = build_training_readiness(
        rides=sample_rides(tss=28),
        feedback=[{"date": TODAY.isoformat(), "sleep_quality": 4, "energy": 4, "leg_fatigue": 2, "rpe": 5, "completion": "正常完成"}],
        sleep_records=[{"date": TODAY.isoformat(), "sleep_hours": 7.2, "sleep_score": 78}],
        profile={"weight": 69},
        compute_daily_pmc_func=compute_daily_pmc,
        today=TODAY,
    )
    assert_eq("normal_level", readiness.level, "可推进")
    assert_eq("normal_cap", readiness.intensity_cap, "normal")
    assert_true("normal_reason", "红旗" in readiness.reason or readiness.source["pmc_available"], readiness.as_dict())


def test_caution_feedback():
    readiness = build_training_readiness(
        rides=sample_rides(tss=65),
        feedback=[{"date": TODAY.isoformat(), "sleep_quality": 3, "energy": 3, "leg_fatigue": 4, "rpe": 7, "completion": "正常完成", "fueling": "吃少了"}],
        sleep_records=[],
        profile={},
        compute_daily_pmc_func=compute_daily_pmc,
        today=TODAY,
    )
    assert_eq("caution_level", readiness.level, "谨慎推进")
    assert_eq("caution_cap", readiness.intensity_cap, "caution")
    assert_true("caution_action", any("质量课" in x for x in readiness.actions), readiness.actions)


def test_recovery_red_flags():
    readiness = build_training_readiness(
        rides=sample_rides(tss=80),
        feedback=[{"date": TODAY.isoformat(), "sleep_quality": 2, "energy": 2, "leg_fatigue": 5, "rpe": 9, "completion": "没完成", "specials": ["发烧"], "pains": ["膝盖痛"]}],
        sleep_records=[{"date": TODAY.isoformat(), "sleep_hours": 4.8, "sleep_score": 48}],
        profile={},
        compute_daily_pmc_func=compute_daily_pmc,
        today=TODAY,
    )
    assert_eq("recovery_level", readiness.level, "恢复优先")
    assert_eq("recovery_cap", readiness.intensity_cap, "recovery")
    assert_true("recovery_flags", any("发烧" in x or "睡眠" in x for x in readiness.flags), readiness.flags)


def test_no_pmc_conservative():
    readiness = build_training_readiness(
        rides=[],
        feedback=[],
        sleep_records=[],
        profile={},
        compute_daily_pmc_func=compute_daily_pmc,
        today=TODAY,
    )
    assert_eq("no_pmc_level", readiness.level, "谨慎推进")
    assert_true("no_pmc_source", readiness.source["pmc_available"] is False, readiness.source)


if __name__ == "__main__":
    test_normal_push()
    test_caution_feedback()
    test_recovery_red_flags()
    test_no_pmc_conservative()
    print("OK training readiness checks passed")
