#!/usr/bin/env python3
"""Stage-H smoke/regression checks for recovery and nutrition rule modules."""
from __future__ import annotations

import pandas as pd

from rules.nutrition import (
    calculate_nutrition_targets,
    feedback_sets_from_recent_feedback,
    rank_supplements,
    score_supplement,
    supplement_card_context,
)
from rules.recovery import (
    build_recovery_advice,
    split_today_and_stale_records,
    summarize_diagnosis_sleep_recovery,
    summarize_recovery_inputs,
)


def assert_eq(name, actual, expected):
    if actual != expected:
        raise AssertionError(f"{name}: expected {expected!r}, got {actual!r}")
    print(f"PASS {name}")


def assert_true(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed {detail}")
    print(f"PASS {name}")


class DummyPMC:
    empty = False
    def __init__(self):
        self._rows = {"ctl": 50, "atl": 75, "tsb": -25}
    @property
    def iloc(self):
        return self
    def __getitem__(self, key):
        if isinstance(key, int):
            return self._rows
        if key == "date_dt":
            return pd.Series([pd.Timestamp("2026-06-02")])
        raise KeyError(key)


def fake_pmc(_rides):
    return DummyPMC()


def fake_cycle(item, _profile):
    return item.get("cycle_status")


def main() -> int:
    today = pd.Timestamp("2026-06-02")
    records = [{"date": "2026-06-02"}, {"date": "2026-06-01"}, {"date": "bad"}]
    current, stale = split_today_and_stale_records(records, today)
    assert_eq("split_today", len(current), 1)
    assert_eq("split_stale", len(stale), 1)

    rides = [{"date": "2026-06-01", "dur": 120}, {"date": "2026-06-02", "dur": 120}]
    feedback = [{
        "date": "2026-06-02", "sleep_quality": 2, "energy": 4, "leg_fatigue": 5,
        "stress": 4, "rpe": 8, "pains": ["膝盖"], "specials": ["发烧"],
        "cycle_status": "经期第1-2天", "cycle_pain": "中", "cycle_training_impact": "明显",
    }]
    sleep = [{"date": "2026-06-02", "sleep_hours": 5.0, "sleep_score": 50, "stress_score": 80, "nap_minutes": 30, "nap_quality": 4, "nap_after": "更清醒"}]
    summary = summarize_recovery_inputs(rides, feedback, sleep, {}, compute_daily_pmc_func=fake_pmc, infer_cycle_status_func=fake_cycle, today=today)
    advice = build_recovery_advice(summary, ftp=250)
    assert_eq("recovery_red", advice["advice_class"], "recovery-red")
    assert_true("recovery_has_fever", "近期记录过发烧" in advice["reasons"])
    assert_eq("recovery_tsb", summary["tsb"], -25)

    special_set, fueling_set = feedback_sets_from_recent_feedback([{"specials": ["天气太热"], "fueling": "吃少了"}])
    assert_true("feedback_sets_special", "天气太热" in special_set)
    assert_true("feedback_sets_fueling", "吃少了" in fueling_set)

    targets = calculate_nutrition_targets(weight=70, ride_hours=3, workout_type="Z2 长距离", environment="天气太热", fueling_set=fueling_set, feedback_count=1)
    assert_eq("nutrition_carb_lo", targets["carb_lo"], 60)
    assert_eq("nutrition_water_hi", targets["water_hi"], 1000)
    assert_eq("nutrition_total_carb_hi", targets["total_carb_hi"], 240)
    assert_eq("nutrition_pre_protein", targets["pre_protein"], 21)

    supplements = [
        {"name": "gel", "carbs_g": 45, "electrolytes_mg": 50, "type": "胶", "caffeine": False, "tags": []},
        {"name": "salt", "carbs_g": 20, "electrolytes_mg": 300, "type": "饮料", "caffeine": False, "tags": ["电解质"]},
        {"name": "caff", "carbs_g": 40, "electrolytes_mg": 250, "type": "软糖", "caffeine": True, "tags": ["电解质"]},
    ]
    ranked = rank_supplements(supplements, environment="天气太热", fueling_set={"胃不舒服"}, workout_type="比赛/绕圈赛")
    assert_eq("supplement_top", ranked[0]["name"], "caff")
    assert_true("supplement_score", score_supplement(ranked[0], environment="天气太热", fueling_set={"胃不舒服"}, workout_type="比赛/绕圈赛") >= 5)
    ctx = supplement_card_context(ranked[0], index=0, carb_hi=90, environment="天气太热", fueling_set={"胃不舒服"}, workout_type="比赛/绕圈赛")
    assert_eq("supplement_badge", ctx["badge"], "⭐ 首选")
    assert_true("supplement_reason", bool(ctx["reason_text"]))

    diag = summarize_diagnosis_sleep_recovery({"count": 1, "last_date": "2026-06-02", "lines": ["反馈行"], "risk_flags": ["反馈风险"]}, sleep)
    assert_true("diagnosis_feedback_badge", "已纳入最近" in diag["feedback_badge"])
    assert_true("diagnosis_combined_flags", "反馈风险" in diag["combined_recovery_flags"])

    print("OK recovery/nutrition Stage-H checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
