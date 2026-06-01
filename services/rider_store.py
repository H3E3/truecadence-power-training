from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd


DEFAULT_PROFILE = {
    'weight': 69,
    'height': 175,
    'age': 30,
    'gender': '男',
    'ftp_test': 0,
    'max_hr': 190,
    'rest_hr': 60,
    'cycle_enabled': False,
    'cycle_last_start': '',
    'cycle_length': 28,
    'period_days': 5,
    'cycle_sensitivity': '正常',
}


def profile_with_defaults(profile=None, defaults=None):
    """Fill missing/empty profile fields without mutating caller input."""
    out = dict(profile or {})
    for k, v in (defaults or DEFAULT_PROFILE).items():
        if k not in out or not out[k]:
            out[k] = v
    return out


def load_profile_for_context(
    user=None,
    rider: str = "默认骑手",
    profile_file: Path | str | None = None,
    load_rider_profile_func=None,
):
    """Load rider profile, falling back to legacy profile JSON and defaults."""
    try:
        if user and load_rider_profile_func:
            profile = load_rider_profile_func(user["user_id"], rider)
            if profile:
                return profile_with_defaults(profile)
        if profile_file and os.path.exists(profile_file):
            with open(profile_file, encoding="utf-8") as f:
                return profile_with_defaults(json.load(f))
    except Exception:
        pass
    return dict(DEFAULT_PROFILE)


def parse_ride_date(value):
    try:
        dt = pd.to_datetime(value, errors="coerce")
        if pd.notna(dt):
            return dt.normalize()
    except Exception:
        pass
    return pd.NaT


def ride_date_key(r):
    dt = parse_ride_date((r or {}).get("date", ""))
    return dt.strftime("%Y-%m-%d") if pd.notna(dt) else ""


def sort_rides_by_date(rides):
    """Sort ride summaries without dropping older history."""
    return sorted([r for r in (rides or []) if isinstance(r, dict)], key=lambda x: str(x.get("date", "")))


def trim_rides_to_recent_weeks(rides, days=84):
    """Return a recent analysis window without deleting stored history."""
    valid_dates = [parse_ride_date((r or {}).get("date", "")) for r in (rides or []) if isinstance(r, dict)]
    valid_dates = [d for d in valid_dates if pd.notna(d)]
    if not valid_dates:
        return rides or []
    latest = max(valid_dates)
    cutoff = latest - pd.Timedelta(days=days - 1)
    kept = []
    for r in rides or []:
        if not isinstance(r, dict):
            continue
        dt = parse_ride_date(r.get("date", ""))
        if pd.isna(dt) or dt >= cutoff:
            kept.append(r)
    return sort_rides_by_date(kept)


def load_historical_for_context(
    user=None,
    rider: str = "默认骑手",
    data_file: Path | str | None = None,
    load_rider_rides_func=None,
):
    """Load stored historical session data for current rider without dropping older rides."""
    try:
        if user and load_rider_rides_func:
            data = load_rider_rides_func(user["user_id"], rider)
            if data:
                return sort_rides_by_date(data)
        if data_file and os.path.exists(data_file):
            with open(data_file, encoding="utf-8-sig") as f:
                data = json.load(f)
            if data:
                return data
    except Exception:
        pass
    return []


def ride_identity(r):
    """Stable key for de-duplicating ride summaries without collapsing distinct platform activities."""
    if r.get("file_hash"):
        return f"hash:{r.get('file_hash')}"
    if r.get("external_id"):
        return f"external:{r.get('source', '')}:{r.get('external_id')}"
    return "|".join(str(r.get(k, "")) for k in ("date", "dur", "dist", "avg_p", "np", "max_p", "hr_avg", "hr_max", "tss"))


def merge_rides(existing, incoming):
    """Merge ride summaries with beta retention rules.

    Rules:
    - Incoming dates replace existing records on the same calendar date.
    - Remaining duplicates are de-duplicated by file_hash/session identity; newest wins.
    - Stored history is kept; analysis pages can choose their own recent window.
    """
    incoming = [r for r in (incoming or []) if isinstance(r, dict)]
    existing = [r for r in (existing or []) if isinstance(r, dict)]

    def is_summary_only(r):
        """Rows created from platform summaries have weak/no record-level power data."""
        source = str((r or {}).get("source") or "")
        file_name = str((r or {}).get("file_name") or "")
        return source.startswith("intervals_icu_summary") or file_name.startswith("intervals_summary_")

    # Only real FIT/current-file rows are allowed to replace same-date history.
    # Summary-only rows must never delete a FIT row from the same calendar day.
    replace_dates = {ride_date_key(r) for r in incoming if ride_date_key(r) and not is_summary_only(r)}

    merged = {}
    for r in existing:
        r_date = ride_date_key(r)
        if r_date in replace_dates:
            continue
        merged[ride_identity(r)] = r
    for r in incoming:
        merged[ride_identity(r)] = r
    return sort_rides_by_date(list(merged.values()))


def save_current_rides_for_context(
    rides,
    user=None,
    rider: str = "默认骑手",
    data_file: Path | str | None = None,
    save_rider_data_func=None,
):
    """Persist current rider history. Cache clearing remains app-layer responsibility."""
    rides = sort_rides_by_date(rides)
    if user and save_rider_data_func:
        save_rider_data_func(user["user_id"], rider, "rides", rides)
    elif data_file:
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(rides, f, ensure_ascii=False, indent=2)
    return rides
