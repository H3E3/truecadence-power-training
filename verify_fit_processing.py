#!/usr/bin/env python3
"""Stage-H smoke/regression checks for services.fit_processing."""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

from services.fit_processing import (
    cleanup_old_fit_uploads,
    compute_durability_from_series,
    compute_power_curve_from_series,
    rolling_best_average,
    sanitize_session_max_power,
    summarize_durability,
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
    assert_eq("rolling_best_average_basic", rolling_best_average([100, 200, 300, 100], 2), 250)
    assert_eq("rolling_best_average_short", rolling_best_average([100], 2), 0)

    powers = [100] * 100 + [300] * 5 + [200] * 1200
    curve = compute_power_curve_from_series(powers)
    assert_eq("curve_5s", curve["5s"], 300)
    assert_eq("curve_20min", curve["20min"], 200)
    assert_eq("curve_missing_40min", curve["40min"], 0)

    assert_eq("sanitize_spike_uses_5s", sanitize_session_max_power(2000, {"5s": 600}), 600)
    assert_eq("sanitize_normal_keeps_max", sanitize_session_max_power(900, {"5s": 600}), 900)

    durability = compute_durability_from_series(([220] * 1800) + ([200] * 1800), ftp=250)
    assert_eq("durability_duration", durability["duration_min"], 60.0)
    assert_true("durability_score_present", durability["score"] > 0)
    assert_true("durability_rating_present", durability["rating"] in {"卓越", "优秀", "良好", "一般", "待提升"})

    summary = summarize_durability([
        {"date": "2026-05-01", "file_name": "a.fit", "durability": durability},
        {"date": "2026-05-02", "file_name": "b.fit", "durability": {**durability, "score": max(0, durability["score"] - 5), "duration_min": 90}},
    ])
    assert_eq("summarize_count", summary["count"], 2)
    assert_true("summarize_best_score", summary["best_score"]["score"] >= summary["recent"]["score"])

    with tempfile.TemporaryDirectory() as d:
        old_fit = Path(d) / "old.fit"
        keep_txt = Path(d) / "old.txt"
        old_fit.write_bytes(b"x")
        keep_txt.write_bytes(b"x")
        old_ts = time.time() - 72 * 3600
        old_fit.touch()
        keep_txt.touch()
        import os
        os.utime(old_fit, (old_ts, old_ts))
        os.utime(keep_txt, (old_ts, old_ts))
        cleanup_old_fit_uploads(d, hours=48)
        assert_true("cleanup_removes_old_fit", not old_fit.exists())
        assert_true("cleanup_keeps_non_fit", keep_txt.exists())

    print("OK fit_processing smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
