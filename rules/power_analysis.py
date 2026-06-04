from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


POWER_PROFILE_DURATIONS = ['5s', '30s', '1min', '5min', '20min', '60min']
POWER_PROFILE_FIXED_THRESHOLDS = {
    # Thresholds are pct_ftp cutoffs for: 一般 / 良好 / 优秀 / 卓越.
    # This is the fixed-reference fallback; later peer percentile ratings can override it.
    '5s': [250, 300, 350, 400],
    '30s': [140, 160, 180, 200],
    '1min': [130, 145, 160, 175],
    '5min': [105, 112, 120, 128],
    '20min': [95, 98, 100, 105],
    '60min': [88, 92, 95, 100],
}


def estimate_best_powers(rides, ftp=None):
    """Estimate best powers at various durations, preferring FIT record-level power_curve."""
    best = {'5s': 0, '30s': 0, '1min': 0, '5min': 0, '20min': 0, '40min': 0, '60min': 0, '2h': 0, '3h': 0}
    keys = ['5s', '30s', '1min', '5min', '20min', '40min', '60min', '2h', '3h']

    for r in rides or []:
        pc = r.get('power_curve') or {}
        excluded_durations = set(r.get('power_exclude_durations') or [])
        for key in keys:
            if key in excluded_durations:
                continue
            val = pc.get(key) or r.get(f"best_{key}") or 0
            try:
                val = float(val or 0)
            except Exception:
                val = 0
            if val > best[key]:
                best[key] = round(val)

        # Legacy/near-window fallback. Some FIT rows have ~40min duration but
        # slightly fewer than 2400 record-power samples after pauses/missing
        # records. Do not drop their 40min capability to 0; use a conservative
        # sustained-effort estimate from avg power and NP.
        dur = float(r.get('dur', 0) or 0)
        np_val = float(r.get('np', 0) or 0)
        avg_val = float(r.get('avg_p', 0) or 0)
        if '40min' not in excluded_durations and (pc.get('40min') or r.get('best_40min') or 0) == 0 and 38 <= dur <= 45 and (np_val or avg_val):
            if np_val and avg_val:
                near_40 = round((np_val + avg_val) / 2)
            else:
                near_40 = round(np_val or avg_val)
            if near_40 > best['40min']:
                best['40min'] = near_40

        # Legacy summary fallback for old rows without power_curve.
        if not pc and np_val > 0:
            if '3h' not in excluded_durations and dur >= 180 and np_val > best['3h']:
                best['3h'] = round(np_val)
            if '2h' not in excluded_durations and dur >= 120 and np_val > best['2h']:
                best['2h'] = round(np_val)
            if '60min' not in excluded_durations and dur >= 60 and np_val > best['60min']:
                best['60min'] = round(np_val)
            if '40min' not in excluded_durations and dur >= 40 and np_val > best['40min']:
                best['40min'] = round(np_val)
            if '20min' not in excluded_durations and dur >= 20 and np_val > best['20min']:
                best['20min'] = round(np_val)
        # Only use session-level max_power as a legacy fallback when no record-level
        # 5s curve exists. A single power-meter spike can make max_power absurd
        # (e.g. 2000W) while the true rolling 5s from records is normal.
        if not pc and '5s' not in excluded_durations and r.get('max_p', 0) > best['5s']:
            best['5s'] = r['max_p']

    excluded_anywhere = set()
    for r in rides or []:
        excluded_anywhere.update(r.get('power_exclude_durations') or [])

    # Fill gaps with FTP-based estimates so charts remain usable for incomplete legacy data.
    # If the rider explicitly excluded a window, keep that window at real evidence from other rides
    # instead of back-filling a synthetic value that could hide the exclusion.
    if ftp is None:
        ftp = 160
    if best['60min'] == 0 and '60min' not in excluded_anywhere:
        best['60min'] = ftp
    if best['40min'] == 0 and best['60min'] and '40min' not in excluded_anywhere:
        best['40min'] = round(max(best['60min'], ftp * 1.01))
    if best['40min'] == 0 and best['20min'] and '40min' not in excluded_anywhere:
        best['40min'] = round(ftp * 1.02)
    if best['20min'] == 0 and '20min' not in excluded_anywhere:
        best['20min'] = round(ftp * 1.05)
    if best['5min'] == 0 and '5min' not in excluded_anywhere:
        best['5min'] = round(ftp * 1.20)
    if best['1min'] == 0 and '1min' not in excluded_anywhere:
        best['1min'] = round(ftp * 1.60)
    if best['30s'] == 0 and '30s' not in excluded_anywhere:
        best['30s'] = round(best['5s'] * 0.80) if best['5s'] > 0 else round(ftp * 2.0)

    # A power-duration curve must be non-increasing as duration gets longer:
    # best 40min cannot be lower than best 60min, best 20min cannot be lower
    # than best 40min, etc. In real data, longer-window values can come from
    # FIT record curves while a shorter neighboring window is missing or only
    # has a conservative legacy fallback. Raise shorter windows to at least the
    # next longer known value so the displayed curve preserves the physical
    # constraint without inventing higher-than-evidence long-duration power.
    for shorter, longer in reversed(list(zip(keys, keys[1:]))):
        if shorter in excluded_anywhere:
            continue
        short_val = best.get(shorter, 0) or 0
        long_val = best.get(longer, 0) or 0
        if long_val and short_val < long_val:
            best[shorter] = round(long_val)
    return best

def calculate_power_zones(ftp):
    """Coggan power zones"""
    return {
        'Z1 Active Recovery': (0, round(ftp * 0.55)),
        'Z2 Endurance': (round(ftp * 0.55), round(ftp * 0.75)),
        'Z3 Tempo': (round(ftp * 0.75), round(ftp * 0.90)),
        'Z4 Sweet Spot': (round(ftp * 0.88), round(ftp * 0.95)),
        'Z5 Threshold': (round(ftp * 0.95), round(ftp * 1.05)),
        'Z6 VO2max': (round(ftp * 1.05), round(ftp * 1.20)),
        'Z7 Anaerobic': (round(ftp * 1.20), 999),
    }

def rider_type_profile(best, ftp, weight=69):
    """Determine rider type based on power profile"""
    if not ftp:
        return "Unknown"

    wkg_5s = best['5s'] / weight if best['5s'] else 0
    wkg_1min = best.get('1min', best['30s']) / weight if best.get('1min', best['30s']) else 0
    wkg_5min = best['5min'] / weight if best['5min'] else 0
    wkg_20min = best['20min'] / weight if best['20min'] else 0
    wkg_60min = best['60min'] / weight if best['60min'] else 0
    wkg_ftp = ftp / weight

    # Relative to FTP
    r_5s = wkg_5s / wkg_ftp if wkg_ftp else 0
    r_1min = wkg_1min / wkg_ftp if wkg_ftp else 0
    r_5min = wkg_5min / wkg_ftp if wkg_5min else 0

    if r_5s > 7.5 and wkg_5s > 14:
        return "冲刺手 Sprinter - 爆发力极强,擅长终点冲刺和短时攻击"
    elif r_1min > 3.5 and wkg_1min > 7:
        return "攻击手 Puncheur - 短陡坡和起伏路段优势明显,擅长反复进攻"
    elif r_5min > 1.5 and wkg_5min > 5:
        return "爬坡手 Climber - 长时间爬坡为王,功体比高是核心优势"
    elif wkg_60min > wkg_ftp * 0.92:
        return "计时赛手 TT - 稳定持续输出,适合平路和单人计时"
    else:
        return "全能型 All-Rounder - 各方面均衡,无明显短板也暂无突出长板"


POWER_PROFILE_MIN_PEER_SAMPLES = 30
POWER_PROFILE_SAMPLES_FILE = DATA_DIR / "power_profile_samples.json"
POWER_PROFILE_SAMPLE_SCHEMA_VERSION = 1

def rating_from_thresholds(value, thresholds):
    """Return Chinese rating from four ascending thresholds: 一般/良好/优秀/卓越."""
    if value is None or not thresholds or len(thresholds) < 4:
        return "待提升"
    if value >= thresholds[3]:
        return "卓越"
    if value >= thresholds[2]:
        return "优秀"
    if value >= thresholds[1]:
        return "良好"
    if value >= thresholds[0]:
        return "一般"
    return "待提升"

def anonymize_power_profile_user_id(user_id):
    """One-way hash for peer-profile samples; keeps raw user id out of the shared sample file."""
    if not user_id:
        return "anonymous"
    return hashlib.sha256(f"tc_power_profile::{user_id}".encode("utf-8")).hexdigest()[:16]

def ftp_wkg_bucket(ftp, weight):
    wkg = ftp / weight if ftp and weight else 0
    if wkg <= 0:
        return "ftp_wkg_unknown"
    if wkg < 2.5:
        return "ftp_wkg_lt_2_5"
    if wkg < 3.5:
        return "ftp_wkg_2_5_3_5"
    if wkg < 4.5:
        return "ftp_wkg_3_5_4_5"
    return "ftp_wkg_gt_4_5"

def load_power_profile_samples():
    try:
        if POWER_PROFILE_SAMPLES_FILE.exists():
            with open(POWER_PROFILE_SAMPLES_FILE, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []
    return []

def save_power_profile_samples(samples):
    POWER_PROFILE_SAMPLES_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = POWER_PROFILE_SAMPLES_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(samples, f, ensure_ascii=False, indent=2)
    os.replace(tmp, POWER_PROFILE_SAMPLES_FILE)

def power_profile_sample_key(user_id_hash, rider_name, ftp, weight):
    rider_hash = hashlib.sha256(str(rider_name or "默认骑手").encode("utf-8")).hexdigest()[:12]
    return f"{user_id_hash}:{rider_hash}:{round(ftp or 0)}:{round(weight or 0, 1)}"

def build_power_profile_sample(user_id, rider_name, best, ftp, weight, ftp_source=""):
    if not ftp or not weight or not best:
        return None
    metrics = build_power_profile_metrics(best, ftp, weight)
    compact_profile = {}
    for duration, item in metrics.items():
        if item.get("power", 0) > 0:
            compact_profile[duration] = {
                "power": item.get("power", 0),
                "wkg": item.get("wkg", 0),
                "pct_ftp": item.get("pct_ftp", 0),
            }
    if not compact_profile:
        return None
    user_id_hash = anonymize_power_profile_user_id(user_id)
    sample = {
        "schema": POWER_PROFILE_SAMPLE_SCHEMA_VERSION,
        "sample_key": power_profile_sample_key(user_id_hash, rider_name, ftp, weight),
        "user_id_hash": user_id_hash,
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "updated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "ftp": round(ftp),
        "weight": round(weight, 1),
        "ftp_wkg": round(ftp / weight, 2) if ftp and weight else 0,
        "bucket": ftp_wkg_bucket(ftp, weight),
        "ftp_source": ftp_source,
        "profile": compact_profile,
    }
    return sample

def upsert_power_profile_sample(sample):
    if not sample or not sample.get("sample_key"):
        return False, 0
    samples = load_power_profile_samples()
    key = sample["sample_key"]
    replaced = False
    for idx, old in enumerate(samples):
        if isinstance(old, dict) and old.get("sample_key") == key:
            sample["created_at"] = old.get("created_at") or sample.get("created_at")
            samples[idx] = sample
            replaced = True
            break
    if not replaced:
        samples.append(sample)
    save_power_profile_samples(samples)
    return True, len(samples)

def record_power_profile_sample(user_id, rider_name, best, ftp, weight, ftp_source=""):
    try:
        sample = build_power_profile_sample(user_id, rider_name, best, ftp, weight, ftp_source)
        return upsert_power_profile_sample(sample)
    except Exception:
        return False, 0

def percentile_rank(value, samples, min_samples=POWER_PROFILE_MIN_PEER_SAMPLES):
    """Return percentile rank 0-100 for value against peer samples, or None if insufficient."""
    if value is None or value <= 0 or not samples:
        return None
    valid = []
    for sample in samples:
        try:
            x = float(sample)
        except (TypeError, ValueError):
            continue
        if x > 0:
            valid.append(x)
    if len(valid) < min_samples:
        return None
    below_or_equal = sum(1 for x in valid if x <= value)
    return round(below_or_equal / len(valid) * 100)

def rating_from_percentile(percentile):
    """Convert percentile rank to the same rating labels used by fixed thresholds."""
    if percentile is None:
        return None
    if percentile >= 80:
        return "卓越"
    if percentile >= 60:
        return "优秀"
    if percentile >= 40:
        return "良好"
    if percentile >= 20:
        return "一般"
    return "待提升"

def choose_percentile_metric(duration):
    """Choose the primary metric for future peer-percentile comparison."""
    if duration in ('5s', '30s', '1min', '5min'):
        return 'wkg'
    if duration in ('20min', '60min'):
        return 'pct_ftp'
    return 'pct_ftp'

def get_peer_samples(peer_samples, duration, metric):
    """Read peer sample values from flexible sample containers.

    Supported shapes for future callers:
    - {'5s': {'wkg': [..], 'pct_ftp': [..]}}
    - {'5s': [{'wkg': 12.3}, {'wkg': 13.1}]}
    - [{'profile': {'5s': {'wkg': 12.3}}}, {'5s': {'wkg': 13.1}}]
    """
    if not peer_samples:
        return []
    values = []
    if isinstance(peer_samples, dict):
        bucket = peer_samples.get(duration) or {}
        if isinstance(bucket, dict):
            metric_values = bucket.get(metric)
            if isinstance(metric_values, (list, tuple)):
                return list(metric_values)
            if isinstance(metric_values, (int, float)):
                return [metric_values]
        if isinstance(bucket, (list, tuple)):
            for item in bucket:
                if isinstance(item, dict):
                    val = item.get(metric)
                    if val is not None:
                        values.append(val)
                elif isinstance(item, (int, float)):
                    values.append(item)
            return values
    if isinstance(peer_samples, (list, tuple)):
        for sample in peer_samples:
            if not isinstance(sample, dict):
                continue
            profile = sample.get('profile') if isinstance(sample.get('profile'), dict) else sample
            item = profile.get(duration) if isinstance(profile, dict) else None
            if isinstance(item, dict):
                val = item.get(metric)
                if val is not None:
                    values.append(val)
    return values

def peer_samples_for_bucket(bucket):
    """Load same FTP-W/kg bucket samples for percentile display."""
    if not bucket:
        return []
    return [s for s in load_power_profile_samples() if isinstance(s, dict) and s.get('bucket') == bucket]

def power_profile_rating_rows(profile):
    rows = []
    for duration in POWER_PROFILE_DURATIONS:
        val = (profile or {}).get(duration)
        if not val:
            continue
        if val.get('percentile') is not None:
            peer_text = f"超过同水平用户约 {val.get('percentile')}%"
        else:
            peer_text = f"样本不足,暂用固定参考线(至少{POWER_PROFILE_MIN_PEER_SAMPLES}条)"
        rows.append({
            '时间': duration,
            '功率': f"{val.get('power', 0)}W",
            'W/kg': val.get('wkg', 0),
            '占FTP': f"{val.get('pct_ftp', 0)}%",
            '当前评级': val.get('rating', ''),
            '评级来源': '同水平用户分位数' if val.get('rating_source') == 'peer_percentile' else '固定参考线',
            '同类分位': peer_text,
            '固定线评级': val.get('fixed_rating', ''),
        })
    return rows

def build_power_profile_metrics(best, ftp, weight=0):
    """Build normalized power-profile metrics for each duration.

    Each duration carries absolute power, W/kg, and pct_ftp so fixed thresholds,
    future peer percentiles, UI, and AI summaries can share one data structure.
    """
    metrics = {}
    best = best or {}
    for duration in POWER_PROFILE_DURATIONS:
        power = best.get(duration, 0) or 0
        wkg = round(power / weight, 1) if power and weight else 0
        pct_ftp = round(power / ftp * 100) if power and ftp else 0
        metrics[duration] = {
            'power': power,
            'wkg': wkg,
            'pct_ftp': pct_ftp,
            '%FTP': pct_ftp,  # Backward-compatible key used by existing UI/report code.
        }
    return metrics

def evaluate_power_profile(best, ftp, weight=0, peer_samples=None):
    """Evaluate power profile with fixed thresholds plus optional peer percentile.

    If peer samples are insufficient, final rating remains the fixed-reference rating.
    When enough peer samples are available, percentile rating becomes the final rating
    while fixed_rating stays visible for explanation and fallback.
    """
    if not ftp:
        return None
    profile = build_power_profile_metrics(best, ftp, weight)
    results = {}
    for duration, item in profile.items():
        power = item.get('power', 0) or 0
        if power <= 0:
            continue
        thresholds = POWER_PROFILE_FIXED_THRESHOLDS.get(duration)
        fixed_rating = rating_from_thresholds(item.get('pct_ftp', 0), thresholds)

        percentile_metric = choose_percentile_metric(duration)
        samples = get_peer_samples(peer_samples, duration, percentile_metric) if peer_samples else []
        percentile = percentile_rank(item.get(percentile_metric), samples)
        percentile_rating = rating_from_percentile(percentile)
        final_rating = percentile_rating or fixed_rating
        rating_source = 'peer_percentile' if percentile_rating else 'fixed_threshold'

        results[duration] = {
            **item,
            'fixed_rating': fixed_rating,
            'percentile_metric': percentile_metric,
            'percentile': percentile,
            'percentile_rating': percentile_rating,
            'rating': final_rating,
            'rating_source': rating_source,
        }
    return results

def calculate_fatigue_resistance(rides, ftp, best, weight=0, peer_samples=None):
    """Backward-compatible wrapper for the power-profile rating table."""
    return evaluate_power_profile(best, ftp, weight, peer_samples=peer_samples)

