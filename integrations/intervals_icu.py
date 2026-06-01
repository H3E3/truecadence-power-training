from __future__ import annotations

import base64
import csv
import datetime
import io
import json
import os
import time
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import requests


INTERVALS_API_BASE = "https://intervals.icu/api/v1"

APP_DIR = Path(__file__).resolve().parents[1]


def interval_seconds_to_min(value):
    try:
        return round(float(value or 0) / 60, 1)
    except Exception:
        return 0


def interval_distance_to_km(value):
    try:
        return round(float(value or 0) / 1000, 1)
    except Exception:
        return 0


def get_intervals_pref_path_for_context(user=None, rider="默认骑手", get_rider_data_path_func=None):
    if user and get_rider_data_path_func:
        return get_rider_data_path_func(user["user_id"], rider, "intervals_pref")
    return APP_DIR / "intervals_pref.json"


def _intervals_auth_headers(api_key=None, bearer_token=None):
    """Intervals.icu auth headers. Prefer OAuth Bearer token; API key remains a manual fallback."""
    if bearer_token:
        return {"Authorization": f"Bearer {bearer_token}", "Accept": "application/json"}
    token = base64.b64encode(("API_KEY:" + str(api_key or "")).encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}", "Accept": "application/json"}

def intervals_get_json(path, api_key=None, params=None, timeout=20, bearer_token=None):
    url = "https://intervals.icu" + path
    r = requests.get(url, headers=_intervals_auth_headers(api_key, bearer_token), params=params or {}, timeout=timeout)
    r.raise_for_status()
    return r.json()

def intervals_get_bytes(path, api_key=None, params=None, timeout=45, bearer_token=None):
    url = "https://intervals.icu" + path
    r = requests.get(url, headers=_intervals_auth_headers(api_key, bearer_token), params=params or {}, timeout=timeout)
    r.raise_for_status()
    return r.content, r.headers.get("content-type", "")

def normalize_intervals_athlete_id(value):
    v = str(value or "").strip()
    if not v:
        return "0"
    if v == "0":
        return "0"
    if v.startswith("i") and v[1:].isdigit():
        return v
    if v.isdigit():
        return "i" + v
    return v

def intervals_get_field(activity, *names):
    """Get a field from JSON/CSV Intervals rows, tolerant of case/space/underscore differences."""
    if not isinstance(activity, dict):
        return None
    lowered = {str(k).strip().lower().replace(" ", "_"): v for k, v in activity.items()}
    for name in names:
        key = str(name).strip().lower().replace(" ", "_")
        if key in lowered and lowered[key] not in (None, ""):
            return lowered[key]
    return None

def extract_intervals_activity_id(activity):
    v = intervals_get_field(activity, "id", "icu_id", "activity_id", "activity id", "external_id", "external id")
    return str(v) if v is not None else ""

def intervals_activity_date(activity):
    v = intervals_get_field(activity, "start_date_local", "start date local", "start_date", "start date", "date", "start_time", "start time", "activity_date", "activity date")
    return str(v)[:10] if v else ""

def intervals_activity_name(activity):
    return str(intervals_get_field(activity, "name", "filename", "file_name", "file name", "type", "sport") or "Intervals Activity")

def get_intervals_pref_path():
    return get_intervals_pref_path_for_context()

def load_intervals_pref():
    p = get_intervals_pref_path()
    try:
        if p.exists():
            data = json.load(open(p, "r", encoding="utf-8-sig"))
            exp = pd.to_datetime(data.get("expires_at"), errors="coerce")
            if pd.notna(exp) and exp >= pd.Timestamp.now(tz=exp.tz if exp.tzinfo else None):
                return data
    except Exception:
        pass
    return {}

def save_intervals_pref(athlete_id, hours=24):
    p = get_intervals_pref_path()
    expires_at = (datetime.datetime.now() + datetime.timedelta(hours=hours)).isoformat()
    data = {"athlete_id": athlete_id, "expires_at": expires_at}
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def clear_intervals_pref():
    try:
        p = get_intervals_pref_path()
        if p.exists():
            p.unlink()
    except Exception:
        pass

def intervals_activity_summary_rows(activities):
    rows = []
    for a in activities or []:
        # Intervals activity list fields can be seconds/meters; show user-facing units here.
        # Do NOT use icu_training_load as duration (that is load/TSS-like, not time).
        dur = intervals_get_field(a, "moving_time", "moving time", "elapsed_time", "elapsed time", "duration", "icu_duration", "time") or 0
        dist = intervals_get_field(a, "distance", "icu_distance", "icu distance") or 0
        rows.append({
            "选择": False,
            "日期": intervals_activity_date(a),
            "名称": intervals_activity_name(a),
            "时长": f"{interval_seconds_to_min(dur)} min" if dur else "-",
            "距离": f"{interval_distance_to_km(dist)} km" if dist else "-",
            "负荷": intervals_get_field(a, "icu_training_load", "training_load", "training load", "tss") or "-",
        })
    return rows

def extract_intervals_rows(data):
    """Normalize Intervals list responses to a row list."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("activities", "items", "data", "results"):
            if isinstance(data.get(key), list):
                return data.get(key)
    return []

def summarize_intervals_response(data):
    """Safe debug summary for Intervals responses. Never includes API key."""
    summary = {"type": type(data).__name__}
    if isinstance(data, dict):
        summary["top_keys"] = list(data.keys())[:30]
        for key in ("activities", "items", "data", "results"):
            if isinstance(data.get(key), list):
                rows = data.get(key)
                summary["list_key"] = key
                summary["list_len"] = len(rows)
                if rows and isinstance(rows[0], dict):
                    summary["first_row_keys"] = list(rows[0].keys())[:40]
                break
        for key in ("next", "next_page", "page", "pages", "total", "total_count", "count", "offset", "limit"):
            if key in data:
                summary[key] = data.get(key)
    elif isinstance(data, list):
        summary["list_len"] = len(data)
        if data and isinstance(data[0], dict):
            summary["first_row_keys"] = list(data[0].keys())[:40]
    return summary

def summarize_intervals_csv_dates(rows):
    """Summarize date distribution in CSV rows for safe diagnostics."""
    dates = []
    bad_dates = 0
    for row in rows or []:
        d = intervals_activity_date(row)
        dt = pd.to_datetime(d, errors="coerce")
        if pd.isna(dt):
            bad_dates += 1
            continue
        dates.append(dt.normalize())
    if not dates:
        return {"date_count": 0, "bad_date_rows": bad_dates}
    s = pd.Series(dates).sort_values()
    month_counts = s.dt.strftime("%Y-%m").value_counts().sort_index()
    return {
        "date_count": int(len(s)),
        "bad_date_rows": int(bad_dates),
        "min_date": s.iloc[0].strftime("%Y-%m-%d"),
        "max_date": s.iloc[-1].strftime("%Y-%m-%d"),
        "recent_20_dates": [x.strftime("%Y-%m-%d") for x in s.tail(20).tolist()],
        "month_counts_recent_18": month_counts.tail(18).to_dict(),
    }

def fetch_intervals_activities_csv(athlete_id, api_key, oldest, newest, bearer_token=None):
    """Fetch Intervals full activity CSV export and filter locally by date."""
    path = f"/api/v1/athlete/{athlete_id}/activities.csv"
    raw, ctype = intervals_get_bytes(path, api_key, timeout=60, bearer_token=bearer_token)
    text = raw.decode("utf-8-sig", errors="replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    date_summary = summarize_intervals_csv_dates(rows)
    oldest_ts = pd.to_datetime(oldest, errors="coerce")
    newest_ts = pd.to_datetime(newest, errors="coerce")
    filtered = []
    for row in rows:
        d = intervals_activity_date(row)
        dt = pd.to_datetime(d, errors="coerce")
        if pd.isna(dt):
            continue
        if not pd.isna(oldest_ts) and dt < oldest_ts:
            continue
        if not pd.isna(newest_ts) and dt > newest_ts:
            continue
        filtered.append(row)
    date_summary["filtered_count"] = len(filtered)
    date_summary["total_rows"] = len(rows)
    date_summary["filter_range"] = f"{oldest}..{newest}"
    return filtered, f"{path} → local filter {oldest}..{newest} ({len(filtered)}/{len(rows)})", date_summary

def fetch_intervals_activities(athlete_id, api_key=None, oldest=None, newest=None, debug=False, bearer_token=None):
    """Fetch Intervals activities; fall back to full CSV export when JSON list is capped."""
    path = f"/api/v1/athlete/{athlete_id}/activities"
    base_params = {"oldest": oldest, "newest": newest, "limit": 100}
    last_error = None
    best_data = []
    best_source = f"{path}?" + "&".join([f"{k}={v}" for k, v in base_params.items()])
    debug_summaries = []
    try:
        data = intervals_get_json(path, api_key, params=base_params, bearer_token=bearer_token)
        best_data = extract_intervals_rows(data)
        if debug:
            item = summarize_intervals_response(data)
            item["source"] = best_source
            debug_summaries.append(item)
    except Exception as e:
        last_error = e
        if debug:
            debug_summaries.append({"source": best_source, "error": str(e)[:220]})

    # Some accounts / states appear to return only the latest 5 rows from JSON.
    # CSV export is documented and usually returns the full activity history.
    if len(best_data) <= 5:
        try:
            csv_rows, csv_source, csv_date_summary = fetch_intervals_activities_csv(athlete_id, api_key, oldest, newest, bearer_token=bearer_token)
            if debug:
                debug_summaries.append({
                    "source": csv_source,
                    "type": "csv",
                    "list_len": len(csv_rows),
                    "date_summary": csv_date_summary,
                    "first_row_keys": list(csv_rows[0].keys())[:40] if csv_rows else [],
                })
            if len(csv_rows) > len(best_data):
                best_data = csv_rows
                best_source = csv_source
        except Exception as e:
            last_error = e
            if debug:
                debug_summaries.append({"source": f"/api/v1/athlete/{athlete_id}/activities.csv", "error": str(e)[:220]})

    if best_data:
        if debug:
            return best_data, best_source, debug_summaries
        return best_data, best_source
    raise RuntimeError(f"无法读取 Intervals 活动列表:{last_error}")

def ride_from_intervals_summary(activity):
    """Fallback: create a ride summary directly from Intervals activity JSON if FIT download fails."""
    if not isinstance(activity, dict):
        return None
    aid = extract_intervals_activity_id(activity)
    date = intervals_activity_date(activity) or "unknown"
    def first_num(keys):
        for k in keys:
            v = intervals_get_field(activity, k)
            try:
                if v not in (None, ""):
                    return float(v)
            except Exception:
                continue
        return 0
    dur = first_num(["moving_time", "elapsed_time", "duration", "icu_duration", "time"])
    dist = first_num(["distance", "icu_distance"])
    avg_p = first_num(["average_watts", "avg_watts", "avg_power", "power", "icu_average_watts"])
    np = first_num(["weighted_average_watts", "normalized_power", "icu_weighted_avg_watts", "icu_normalized_power"])
    max_p = first_num(["max_watts", "max_power", "icu_max_watts"])
    hr_avg = first_num(["average_heartrate", "avg_heartrate", "avg_hr", "icu_average_heartrate"])
    hr_max = first_num(["max_heartrate", "max_hr", "icu_max_heartrate"])
    tss = first_num(["icu_training_load", "training_load", "tss"])
    return {
        "date": date,
        "dur": interval_seconds_to_min(dur),
        "dist": interval_distance_to_km(dist),
        "avg_p": round(avg_p),
        "np": round(np),
        "max_p": round(max_p),
        "hr_avg": round(hr_avg),
        "hr_max": round(hr_max),
        "tss": round(tss, 1) if tss else 0,
        "cal": round(first_num(["calories", "total_calories"])),
        "source": "intervals_icu_summary",
        "external_id": aid,
        "file_name": f"intervals_summary_{aid}",
    }

