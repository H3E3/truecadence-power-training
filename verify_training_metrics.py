#!/usr/bin/env python3
"""Stage-H regression checks for services.training_metrics."""
from __future__ import annotations

import datetime

from services.training_metrics import (
    compute_daily_pmc,
    enrich_rides,
    estimate_ftp,
    estimate_ftp_explain,
    hr_zones_by_lthr,
    hr_zones_by_max,
    tsb_zone_text,
)


def assert_eq(name, actual, expected):
    if actual != expected:
        raise AssertionError(f"{name}: expected {expected!r}, got {actual!r}")
    print(f"PASS {name}")


def assert_true(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} failed {detail}")
    print(f"PASS {name}")


def main() -> int:
    rides = [
        {"date": "2026-05-01", "dur": 65, "avg_p": 180, "np": 200, "tss": 0, "power_curve": {"20min": 260, "40min": 240, "60min": 220}},
        {"date": "2026-05-03", "dur": 45, "avg_p": 150, "np": 170, "tss": 55, "power_curve": {"20min": 210}},
    ]

    # FTP should prefer record-level rolling windows over whole-ride summaries.
    assert_eq("estimate_ftp_prefers_power_curve", estimate_ftp(rides), 229)
    exp = estimate_ftp_explain(rides)
    assert_eq("estimate_ftp_explain_value", exp["ftp"], 229)
    assert_true("estimate_ftp_explain_basis_mentions_20min", "20min" in exp["basis"])
    assert_true("estimate_ftp_explain_window_rows", len(exp["window_rows"]) >= 3)

    # Default and invalid-data behavior must stay conservative.
    assert_eq("estimate_ftp_default", estimate_ftp([]), 160)
    assert_eq("estimate_ftp_ignores_implausible", estimate_ftp([{"dur": 60, "avg_p": 9999, "np": 9999}]), 160)

    # enrich_rides fills NP before TSS and mutates current ride list intentionally.
    enriched = enrich_rides([{"date": "2026-05-04", "dur": 60, "avg_p": 200, "np": 0, "tss": 0}], ftp=250)
    assert_eq("enrich_np_from_avg", enriched[0]["np"], 210)
    assert_eq("enrich_tss_from_np", enriched[0]["tss"], 70.6)

    # PMC must fill rest days through end_date so CTL/ATL decay naturally.
    pmc = compute_daily_pmc(rides, end_date="2026-05-05")
    assert_eq("pmc_rows_include_rest_days", len(pmc), 5)
    assert_eq("pmc_first_date", pmc.iloc[0]["date"], "2026-05-01")
    assert_eq("pmc_last_date", pmc.iloc[-1]["date"], "2026-05-05")
    assert_eq("pmc_rest_day_tss_zero", float(pmc[pmc["date"] == "2026-05-02"].iloc[0]["tss"]), 0.0)
    assert_true("pmc_has_ctl_atl_tsb", all(c in pmc.columns for c in ["ctl", "atl", "tsb"]))

    # HR zone helpers and TSB text contract.
    assert_eq("hrmax_zone_count", len(hr_zones_by_max(190)), 5)
    assert_eq("lthr_zone_count", len(hr_zones_by_lthr(170)), 5)
    assert_true("tsb_negative_warns_recovery", "疲劳" in tsb_zone_text(-30) or "恢复" in tsb_zone_text(-30))

    print("OK training_metrics regression checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
