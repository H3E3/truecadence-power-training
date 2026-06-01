from __future__ import annotations

import datetime
import hashlib
import io
import os
import tempfile
import time
from pathlib import Path

import requests
import streamlit as st
from integrations.intervals_icu import intervals_get_bytes
from fitparse import FitFile

APP_DIR = Path(__file__).resolve().parents[1]

try:
    from fitparse.base import FitFile as _FitParseBaseFile
    from fitparse.profile import MESSAGE_TYPES as _FIT_MESSAGE_TYPES
    from fitparse.records import (
        FieldDefinition as _FitFieldDefinition,
        DevFieldDefinition as _FitDevFieldDefinition,
        DefinitionMessage as _FitDefinitionMessage,
        BASE_TYPES as _FIT_BASE_TYPES,
        BASE_TYPE_BYTE as _FIT_BASE_TYPE_BYTE,
        get_dev_type as _fit_get_dev_type,
    )
except Exception:
    _FitParseBaseFile = None
    _FIT_MESSAGE_TYPES = {}
    _FIT_BASE_TYPES = {}
    _FIT_BASE_TYPE_BYTE = None
    _FitFieldDefinition = None
    _FitDevFieldDefinition = None
    _FitDefinitionMessage = None
    _fit_get_dev_type = None


def cleanup_old_fit_uploads(temp_dir, hours=48):
    """Keep uploaded FIT originals only for a short testing retention window."""
    cutoff = datetime.datetime.now().timestamp() - hours * 3600
    try:
        for fp in Path(temp_dir).glob("*.fit"):
            try:
                if fp.stat().st_mtime < cutoff:
                    fp.unlink()
            except Exception:
                pass
    except Exception:
        pass

def rolling_best_average(values, window):
    """Return best rolling average over a fixed sample window. Assumes ~1 Hz FIT record samples."""
    if not values or window <= 0 or len(values) < window:
        return 0
    vals = [float(v or 0) for v in values]
    cur = sum(vals[:window])
    best = cur
    for i in range(window, len(vals)):
        cur += vals[i] - vals[i-window]
        if cur > best:
            best = cur
    return round(best / window)

class TolerantFitFile(_FitParseBaseFile if _FitParseBaseFile else FitFile):
    """FIT parser fallback for files that contain malformed native field definitions.

    Some COROS DURA FIT exports seen in beta declare event.data as uint32 with
    field size 1. fitparse 1.2.0 aborts on that definition even though the
    activity/session/record data is otherwise readable. For upload analysis we
    can safely read that malformed field as raw byte and continue, because
    TrueCadence uses session + record power/HR/cadence fields, not event.data.
    """

    def _parse_definition_message(self, header):
        if not all([_FIT_MESSAGE_TYPES is not None, _FIT_BASE_TYPES is not None, _FIT_BASE_TYPE_BYTE, _FitFieldDefinition, _FitDefinitionMessage]):
            return super()._parse_definition_message(header)
        endian = '>' if self._read_struct('xB') else '<'
        global_mesg_num, num_fields = self._read_struct('HB', endian=endian)
        mesg_type = _FIT_MESSAGE_TYPES.get(global_mesg_num)
        field_defs = []

        for _ in range(num_fields):
            field_def_num, field_size, base_type_num = self._read_struct('3B', endian=endian)
            field = mesg_type.fields.get(field_def_num) if mesg_type else None
            base_type = _FIT_BASE_TYPES.get(base_type_num, _FIT_BASE_TYPE_BYTE)
            if base_type and base_type.size and (field_size % base_type.size) != 0:
                base_type = _FIT_BASE_TYPE_BYTE
            field_defs.append(_FitFieldDefinition(field=field, def_num=field_def_num, base_type=base_type, size=field_size))

        dev_field_defs = []
        if header.is_developer_data:
            num_dev_fields = self._read_struct('B', endian=endian)
            for _ in range(num_dev_fields):
                field_def_num, field_size, dev_data_index = self._read_struct('3B', endian=endian)
                field = _fit_get_dev_type(dev_data_index, field_def_num) if _fit_get_dev_type else None
                dev_field_defs.append(_FitDevFieldDefinition(field=field, dev_data_index=dev_data_index, def_num=field_def_num, size=field_size))

        def_mesg = _FitDefinitionMessage(header=header, endian=endian, mesg_type=mesg_type, mesg_num=global_mesg_num, field_defs=field_defs, dev_field_defs=dev_field_defs)
        self._local_mesgs[header.local_mesg_num] = def_mesg
        return def_mesg

def open_fit_file(path):
    """Open FIT with strict parser first, then tolerant parser for known malformed exports."""
    try:
        fit = FitFile(path)
        list(fit.get_messages('session'))
        return fit, False
    except Exception as first_error:
        if _FitParseBaseFile is None:
            raise first_error
        tolerant = TolerantFitFile(path, check_crc=False)
        list(tolerant.get_messages('session'))
        return tolerant, True

def extract_fit_power_series(fit):
    """Extract ~1Hz power series from FIT record messages."""
    powers = []
    try:
        for msg in fit.get_messages('record'):
            v = msg.get_values()
            pw = v.get('power')
            if pw is None:
                continue
            try:
                pw = float(pw)
            except Exception:
                continue
            if pw < 0 or pw > 2500:
                continue
            powers.append(pw)
    except Exception:
        return []
    return powers

def extract_fit_cadence_summary(fit):
    """Extract conservative cadence summary from FIT record messages."""
    vals = []
    try:
        for msg in fit.get_messages('record'):
            v = msg.get_values()
            cad = v.get('cadence') or v.get('avg_cadence')
            if cad is None:
                continue
            try:
                cad = float(cad)
            except Exception:
                continue
            if 20 <= cad <= 180:
                vals.append(cad)
    except Exception:
        return {}
    if not vals:
        return {}
    avg = round(sum(vals) / len(vals), 1)
    low_ratio = round(sum(1 for x in vals if x < 75) / len(vals), 3)
    high_ratio = round(sum(1 for x in vals if x > 100) / len(vals), 3)
    return {
        'avg_cadence': avg,
        'low_cadence_ratio': low_ratio,
        'high_cadence_ratio': high_ratio,
        'record_cadence_count': len(vals),
    }

def compute_power_curve_from_series(powers):
    """Compute best rolling powers from a record-level power series."""
    if not powers:
        return {}
    windows = {
        '5s': 5,
        '30s': 30,
        '1min': 60,
        '5min': 300,
        '20min': 1200,
        '40min': 2400,
        '60min': 3600,
        '2h': 7200,
        '3h': 10800,
    }
    curve = {}
    for key, sec in windows.items():
        val = rolling_best_average(powers, sec)
        # If an activity is just shy of a named window (e.g. 40.8min total but
        # only ~39.5min record-power samples after pauses/missing records),
        # still expose the best available sustained effort instead of dropping
        # the window to 0. This matches rider/platform expectations better for
        # near-threshold tests and avoids under-reporting 40min power.
        if val == 0 and key in ('40min', '60min', '2h', '3h') and powers:
            min_required = int(sec * 0.95)
            if len(powers) >= min_required:
                val = rolling_best_average(powers, len(powers))
        curve[key] = val
    return curve

def compute_power_curve_from_fit(fit):
    """Compute best rolling powers from FIT record messages."""
    return compute_power_curve_from_series(extract_fit_power_series(fit))

def sanitize_session_max_power(max_power, power_curve):
    """Return a display/summary max power that is consistent with record-level evidence.

    FIT session max_power is a single instantaneous summary field and can be polluted by
    one-sample power-meter spikes. For TrueCadence summaries, prefer record-level rolling
    5s when the session max is implausibly above the available record curve.
    """
    try:
        max_power = float(max_power or 0)
    except Exception:
        max_power = 0
    pc = power_curve or {}
    try:
        p5 = float(pc.get('5s') or 0)
    except Exception:
        p5 = 0
    if max_power <= 0:
        return 0
    if p5 > 0 and max_power > max(1200, p5 * 1.8):
        return round(p5)
    return round(max_power)

def best_rolling_after_index(powers, window, start_idx):
    """Best rolling average after a given sample index."""
    if not powers or window <= 0 or len(powers) - start_idx < window:
        return 0
    segment = powers[max(0, start_idx):]
    return rolling_best_average(segment, window)

def compute_durability_from_series(powers, ftp=None):
    """Durability 2.0: evaluate late-ride power retention from record-level power.

    This is different from the classic power curve: it asks whether the rider can still
    produce useful 5/20min power after the ride has already accumulated fatigue.
    """
    if not powers or len(powers) < 1800:  # need at least 30min to say anything useful
        return {}
    total = len(powers)
    first_half = powers[:max(1, total // 2)]
    second_half = powers[total // 2:]
    first_avg = round(sum(first_half) / len(first_half)) if first_half else 0
    second_avg = round(sum(second_half) / len(second_half)) if second_half else 0
    half_drop_pct = round((first_avg - second_avg) / first_avg * 100, 1) if first_avg > 0 else 0

    whole_5m = rolling_best_average(powers, 300)
    whole_20m = rolling_best_average(powers, 1200)
    late_5m = best_rolling_after_index(powers, 300, total // 2)
    late_20m = best_rolling_after_index(powers, 1200, total // 2)
    late_5m_retention = round(late_5m / whole_5m * 100, 1) if whole_5m else 0
    late_20m_retention = round(late_20m / whole_20m * 100, 1) if whole_20m else 0

    after_60_5m = best_rolling_after_index(powers, 300, 3600) if total >= 3900 else 0
    after_60_20m = best_rolling_after_index(powers, 1200, 3600) if total >= 4800 else 0
    after_60_5m_pct_ftp = round(after_60_5m / ftp * 100, 1) if ftp and after_60_5m else 0
    after_60_20m_pct_ftp = round(after_60_20m / ftp * 100, 1) if ftp and after_60_20m else 0

    score_parts = []
    if late_5m_retention:
        score_parts.append(late_5m_retention)
    if late_20m_retention:
        score_parts.append(late_20m_retention)
    if first_avg and second_avg:
        score_parts.append(max(0, 100 - half_drop_pct))
    score = round(sum(score_parts) / len(score_parts), 1) if score_parts else 0
    if score >= 92 and half_drop_pct <= 8:
        rating = "卓越"
    elif score >= 86 and half_drop_pct <= 12:
        rating = "优秀"
    elif score >= 78 and half_drop_pct <= 18:
        rating = "良好"
    elif score >= 68:
        rating = "一般"
    else:
        rating = "待提升"

    return {
        "duration_min": round(total / 60, 1),
        "first_half_avg": first_avg,
        "second_half_avg": second_avg,
        "half_drop_pct": half_drop_pct,
        "whole_5m": whole_5m,
        "late_5m": late_5m,
        "late_5m_retention": late_5m_retention,
        "whole_20m": whole_20m,
        "late_20m": late_20m,
        "late_20m_retention": late_20m_retention,
        "after_60_5m": after_60_5m,
        "after_60_20m": after_60_20m,
        "after_60_5m_pct_ftp": after_60_5m_pct_ftp,
        "after_60_20m_pct_ftp": after_60_20m_pct_ftp,
        "score": score,
        "rating": rating,
    }

class NamedBytesFile:
    """Small adapter so downloaded FIT bytes can reuse parse_fit_files(...)."""
    def __init__(self, name, data):
        self.name = name
        self._data = data
        self.size = len(data or b"")
    def read(self):
        return self._data

def download_intervals_activity_fit(athlete_id, activity_id, api_key=None, bearer_token=None):
    """Download one activity as FIT bytes using common Intervals API URL forms.

    Intervals has had several API URL shapes in examples/integrations, so this MVP tries
    multiple read-only download endpoints. If none returns binary data, caller can still
    fall back to summary import from the activity list.
    """
    aid = str(activity_id or "").strip()
    aid_no_i = aid[1:] if aid.startswith("i") and aid[1:].isdigit() else aid
    # Official Intervals endpoints: original file and generated FIT.
    # Generated FIT is not supported for Strava activities, so summary fallback is expected there.
    paths = [
        f"/api/v1/activity/{aid}/fit-file",
        f"/api/v1/activity/{aid}/fit-file?power=true&hr=true",
        f"/api/v1/activity/{aid}/file",
    ]
    if aid_no_i != aid:
        paths += [
            f"/api/v1/activity/{aid_no_i}/fit-file",
            f"/api/v1/activity/{aid_no_i}/fit-file?power=true&hr=true",
            f"/api/v1/activity/{aid_no_i}/file",
        ]
    errors = []
    for path in paths:
        try:
            data, ctype = intervals_get_bytes(path, api_key, bearer_token=bearer_token)
            head = (data or b"")[:32].lstrip()
            if data and len(data) > 32 and not head.startswith((b"{", b"[", b"<")):
                return data, path
            errors.append(f"{path}: 非FIT响应 {ctype} {len(data or b'')} bytes")
        except Exception as e:
            errors.append(f"{path}: {e}")
    raise RuntimeError("原始 FIT 不可下载(常见于 Strava API 同步活动),已改用 Intervals 摘要导入。")

def parse_fit_files(files):
    """Parse uploaded FIT files for session data, with per-session hash cache and timing."""
    results = []
    timings = []
    cache = st.session_state.setdefault("fit_parse_cache", {})
    temp_dir = Path(os.environ.get("TRUECADENCE_TMP_DIR", APP_DIR / "tmp_uploads"))
    temp_dir.mkdir(parents=True, exist_ok=True)
    cleanup_old_fit_uploads(temp_dir, hours=48)
    batch_t0 = time.perf_counter()
    for f in files:
        tmp_path = None
        name = getattr(f, 'name', '')
        file_t0 = time.perf_counter()
        try:
            raw = f.read()
            file_hash_full = hashlib.sha256(raw).hexdigest()
            file_hash = file_hash_full[:16]
            cache_key = f"{file_hash_full}:{len(raw)}"
            if cache_key in cache:
                cached = dict(cache[cache_key])
                cached['file_name'] = name or cached.get('file_name', '')
                cached['parse_cached'] = True
                results.append(cached)
                timings.append({
                    "file": name or file_hash,
                    "parser": cached.get('fit_parser', 'cache'),
                    "cached": True,
                    "seconds": round(time.perf_counter() - file_t0, 3),
                    "size_kb": round(len(raw) / 1024, 1),
                    "records": cached.get('record_power_count', 0),
                })
                continue

            with tempfile.NamedTemporaryFile(delete=False, suffix='.fit', dir=temp_dir) as tmp:
                tmp.write(raw)
                tmp_path = tmp.name

            fit, tolerant_fit = open_fit_file(tmp_path)
            power_series = extract_fit_power_series(fit)
            cadence_summary = extract_fit_cadence_summary(fit)
            power_curve = compute_power_curve_from_series(power_series)
            durability = compute_durability_from_series(power_series)
            sessions = list(fit.get_messages('session'))
            if sessions:
                s = sessions[0].get_values()
                start = s.get('start_time')
                ride = {
                    'date': start.strftime('%Y-%m-%d') if start else 'unknown',
                    'dur': round(s.get('total_timer_time', 0) / 60, 1),
                    'dist': round(s.get('total_distance', 0) / 1000, 1),
                    'avg_p': s.get('avg_power', 0) or 0,
                    'np': s.get('normalized_power', 0) or 0,
                    'max_p': sanitize_session_max_power(s.get('max_power', 0) or 0, power_curve),
                    'raw_max_p': s.get('max_power', 0) or 0,
                    'hr_avg': s.get('avg_heart_rate', 0) or 0,
                    'hr_max': s.get('max_heart_rate', 0) or 0,
                    'avg_cadence': cadence_summary.get('avg_cadence', s.get('avg_cadence', 0) or 0),
                    'low_cadence_ratio': cadence_summary.get('low_cadence_ratio', 0),
                    'high_cadence_ratio': cadence_summary.get('high_cadence_ratio', 0),
                    'record_cadence_count': cadence_summary.get('record_cadence_count', 0),
                    'tss': s.get('training_stress_score', 0) or 0,
                    'cal': s.get('total_calories', 0) or 0,
                    'power_curve': power_curve,
                    'durability': durability,
                    'best_5s': power_curve.get('5s', 0),
                    'best_30s': power_curve.get('30s', 0),
                    'best_1min': power_curve.get('1min', 0),
                    'best_5min': power_curve.get('5min', 0),
                    'best_20min': power_curve.get('20min', 0),
                    'best_40min': power_curve.get('40min', 0),
                    'best_60min': power_curve.get('60min', 0),
                    'best_2h': power_curve.get('2h', 0),
                    'best_3h': power_curve.get('3h', 0),
                    'file_hash': file_hash,
                    'file_name': name,
                    'fit_parser': 'tolerant' if tolerant_fit else 'standard',
                    'record_power_count': len(power_series),
                    'parse_cached': False,
                }
                cache[cache_key] = dict(ride)
                results.append(ride)
                timings.append({
                    "file": name or file_hash,
                    "parser": ride['fit_parser'],
                    "cached": False,
                    "seconds": round(time.perf_counter() - file_t0, 3),
                    "size_kb": round(len(raw) / 1024, 1),
                    "records": len(power_series),
                })
        except Exception as e:
            timings.append({
                "file": name or "unknown.fit",
                "parser": "failed",
                "cached": False,
                "seconds": round(time.perf_counter() - file_t0, 3),
                "size_kb": 0,
                "records": 0,
                "error": str(e)[:160],
            })
            st.warning(f"解析失败: {name} - {e}")
        finally:
            # Testing-stage retention: keep uploaded FIT originals for up to 48h for debugging,
            # then cleanup_old_fit_uploads(...) removes them automatically on later uploads.
            pass
    st.session_state["last_fit_parse_timings"] = timings
    st.session_state["last_fit_parse_total_seconds"] = round(time.perf_counter() - batch_t0, 3)
    return results

def summarize_durability(rides):
    """Aggregate ride-level durability metrics and keep the best/most informative records."""
    items = []
    for r in rides or []:
        d = r.get('durability') or {}
        if not d or not d.get('score'):
            continue
        x = dict(d)
        x['date'] = r.get('date', '')
        x['file_name'] = r.get('file_name', '')
        items.append(x)
    if not items:
        return None
    best_score = max(items, key=lambda x: x.get('score', 0))
    longest = max(items, key=lambda x: x.get('duration_min', 0))
    recent = sorted(items, key=lambda x: x.get('date', ''))[-1]
    avg_score = round(sum(x.get('score', 0) for x in items) / len(items), 1)
    avg_drop = round(sum(x.get('half_drop_pct', 0) for x in items) / len(items), 1)
    return {
        'count': len(items),
        'avg_score': avg_score,
        'avg_drop': avg_drop,
        'best_score': best_score,
        'longest': longest,
        'recent': recent,
        'items': sorted(items, key=lambda x: (x.get('score', 0), x.get('duration_min', 0)), reverse=True),
    }

