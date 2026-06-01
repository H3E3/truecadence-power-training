from __future__ import annotations

import pandas as pd


def estimate_ftp(rides):
    """Estimate FTP from uploaded ride data.

    Prefer record-level best rolling powers when available. Whole-ride session avg/NP is
    only a fallback because it can under-estimate riders who have high 20min power inside
    a longer easy/interval ride.
    """
    candidates = []

    def valid_power(x):
        try:
            x = float(x or 0)
        except Exception:
            return 0
        return x if 50 <= x <= 800 else 0

    # 1) Best rolling powers from FIT record data - primary evidence.
    curve_20 = []
    curve_40 = []
    curve_60 = []
    for r in rides or []:
        pc = r.get('power_curve') or {}
        p20 = valid_power(pc.get('20min') or r.get('best_20min'))
        p40 = valid_power(pc.get('40min') or r.get('best_40min'))
        p60 = valid_power(pc.get('60min') or r.get('best_60min'))
        if p20:
            curve_20.append(p20)
        if p40:
            curve_40.append(p40)
        if p60:
            curve_60.append(p60)
    if curve_20:
        candidates.append(max(curve_20) * 0.88)
    if curve_40:
        candidates.append(max(curve_40) * 0.95)
    if curve_60:
        candidates.append(max(curve_60) * 1.00)

    # 2) Session summary fallback: useful for old data without record-level power curve.
    best_60_avg = max([valid_power(r.get('avg_p')) for r in rides or [] if (r.get('dur', 0) or 0) >= 55], default=0)
    if best_60_avg:
        candidates.append(best_60_avg * 1.00)

    best_40_avg = max([valid_power(r.get('avg_p')) for r in rides or [] if (r.get('dur', 0) or 0) >= 38], default=0)
    if best_40_avg:
        candidates.append(best_40_avg * 0.95)

    best_20_avg = max([valid_power(r.get('avg_p')) for r in rides or [] if (r.get('dur', 0) or 0) >= 20], default=0)
    if best_20_avg:
        candidates.append(best_20_avg * 0.88)

    # 3) NP-based fallback, intentionally conservative for normal training rides.
    long = [r for r in rides or [] if (r.get('dur', 0) or 0) >= 30 and valid_power(r.get('np'))]
    if long:
        top3 = sorted(long, key=lambda x: valid_power(x.get('np')), reverse=True)[:3]
        avg = sum(valid_power(r.get('np')) for r in top3) / len(top3)
        all_np = [valid_power(r.get('np')) for r in long]
        median_np = sorted(all_np)[len(all_np)//2]
        if median_np > 0 and valid_power(top3[0].get('np')) > median_np * 1.3:
            candidates.append(avg * 0.90)
        else:
            candidates.append(avg * 0.85)

    if candidates:
        return round(max(candidates))

    powered = [valid_power(r.get('avg_p')) for r in rides or [] if valid_power(r.get('avg_p'))]
    if powered:
        return round(max(powered) * 1.1)
    return 160

def estimate_ftp_explain(rides):
    """Explain the evidence behind auto FTP for user-facing display."""
    def valid_power(x):
        try:
            x = float(x or 0)
        except Exception:
            return 0
        return x if 50 <= x <= 800 else 0

    candidates = []
    best_20_curve = 0
    best_40_curve = 0
    best_60_curve = 0
    best_20_avg = 0
    best_40_avg = 0
    best_60_avg = 0
    best_np = 0

    for r in rides or []:
        pc = r.get('power_curve') or {}
        p20 = valid_power(pc.get('20min') or r.get('best_20min'))
        p40 = valid_power(pc.get('40min') or r.get('best_40min'))
        p60 = valid_power(pc.get('60min') or r.get('best_60min'))
        best_20_curve = max(best_20_curve, p20)
        best_40_curve = max(best_40_curve, p40)
        best_60_curve = max(best_60_curve, p60)

        if (r.get('dur', 0) or 0) >= 20:
            best_20_avg = max(best_20_avg, valid_power(r.get('avg_p')))
        if (r.get('dur', 0) or 0) >= 38:
            best_40_avg = max(best_40_avg, valid_power(r.get('avg_p')))
        if (r.get('dur', 0) or 0) >= 55:
            best_60_avg = max(best_60_avg, valid_power(r.get('avg_p')))
        if (r.get('dur', 0) or 0) >= 30:
            best_np = max(best_np, valid_power(r.get('np')))

    if best_20_curve:
        candidates.append((best_20_curve * 0.88, f"20min 最佳滑动功率 {round(best_20_curve)}W × 0.88(普通骑行保守折算)", "中"))
    if best_40_curve:
        candidates.append((best_40_curve * 0.95, f"40min 最佳滑动功率 {round(best_40_curve)}W × 0.95", "中高"))
    if best_60_curve:
        candidates.append((best_60_curve * 1.00, f"60min 最佳滑动功率 {round(best_60_curve)}W × 1.00(接近FTP概念)", "高"))
    if best_60_avg:
        candidates.append((best_60_avg * 1.00, f"≥55min 整场平均功率 {round(best_60_avg)}W × 1.00", "中高"))
    if best_40_avg:
        candidates.append((best_40_avg * 0.95, f"≥38min 整场平均功率 {round(best_40_avg)}W × 0.95", "中"))
    if best_20_avg:
        candidates.append((best_20_avg * 0.88, f"≥20min 整场平均功率 {round(best_20_avg)}W × 0.88(普通骑行保守折算)", "中低"))
    if best_np:
        candidates.append((best_np * 0.85, f"长时间训练 NP {round(best_np)}W 保守折算", "低"))

    if not candidates:
        return {"ftp": 160, "basis": "缺少有效功率数据,使用默认值", "confidence": "低", "best_20": 0, "best_40": 0, "best_60": 0, "window_rows": []}

    val, basis, confidence = max(candidates, key=lambda x: x[0])
    best_20 = round(best_20_curve or best_20_avg)
    best_40 = round(best_40_curve or best_40_avg)
    best_60 = round(best_60_curve or best_60_avg)
    window_rows = []
    if best_20:
        window_rows.append({"窗口": "20min", "最佳功率": f"{best_20}W", "FTP参考": f"{round(best_20 * 0.85)}-{round(best_20 * 0.90)}W", "说明": "普通骑行按 ×0.85-0.90 更稳;只有标准20min测试才接近 ×0.95"})
    if best_40:
        window_rows.append({"窗口": "40min", "最佳功率": f"{best_40}W", "FTP参考": f"{round(best_40 * 0.95)}W", "说明": "更接近长时间阈值支撑;稳定全力时可接近原值"})
    if best_60:
        window_rows.append({"窗口": "60min", "最佳功率": f"{best_60}W", "FTP参考": f"{round(best_60)}W", "说明": "60min本身接近FTP概念,通常不再额外打折;前提是记录连续且强度充分"})
    return {"ftp": round(val), "basis": basis, "confidence": confidence, "best_20": best_20, "best_40": best_40, "best_60": best_60, "window_rows": window_rows}

def hr_zones_by_max(max_hr):
    """Conservative 5-zone HR model based on max heart rate."""
    if not max_hr or max_hr <= 0:
        return []
    bands = [
        ("Z1 恢复", 0.50, 0.60, "轻松恢复、热身放松"),
        ("Z2 有氧", 0.60, 0.70, "基础耐力、长距离有氧"),
        ("Z3 节奏", 0.70, 0.80, "中等强度、节奏骑"),
        ("Z4 阈值", 0.80, 0.90, "阈值附近、较难维持"),
        ("Z5 高强度", 0.90, 1.00, "VO2max/冲刺,不宜长时间堆叠"),
    ]
    return [{"区间": name, "心率范围": f"{round(max_hr*lo)}-{round(max_hr*hi)} bpm", "依据": f"{round(lo*100)}-{round(hi*100)}% HRmax", "用途": note} for name, lo, hi, note in bands]

def hr_zones_by_lthr(lthr):
    """Cycling LTHR-style 5-zone model. Use as training reference, not medical advice."""
    if not lthr or lthr <= 0:
        return []
    bands = [
        ("Z1 恢复", 0.00, 0.81, "恢复骑、热身放松"),
        ("Z2 耐力", 0.81, 0.89, "有氧耐力、长距离"),
        ("Z3 节奏", 0.89, 0.95, "Tempo/节奏骑"),
        ("Z4 阈值", 0.95, 1.00, "乳酸阈值附近"),
        ("Z5 阈上", 1.00, 1.06, "阈上/VO2,短时间使用"),
    ]
    rows = []
    for name, lo, hi, note in bands:
        low = max(0, round(lthr*lo)) if lo > 0 else 0
        high = round(lthr*hi)
        hr_range = f"≤{high} bpm" if lo == 0 else f"{low}-{high} bpm"
        rows.append({"区间": name, "心率范围": hr_range, "依据": f"{round(lo*100)}-{round(hi*100)}% LTHR" if lo > 0 else f"≤{round(hi*100)}% LTHR", "用途": note})
    return rows

def tsb_zone_text(tsb):
    if tsb <= -25:
        return "恢复风险较高:疲劳可能压住状态,需结合腿疲劳、睡眠、晨脉和疼痛反馈,谨慎安排高强度。"
    if tsb <= -10:
        return "负荷较高:有训练刺激,但要关注恢复,不建议连续堆强度。"
    if tsb <= 5:
        return "常规训练区:多数训练日可正常推进,仍需结合主观反馈。"
    if tsb <= 15:
        return "偏新鲜:适合质量课、测试或比赛准备;如果非减量期,注意训练刺激是否不足。"
    return "非常新鲜/可能刺激不足:适合比赛或测试前状态;若长期如此,可能需要增加规律训练。"

def compute_daily_pmc(rides, ctl_tau=42, atl_tau=7, end_date=None):
    """Compute PMC by natural calendar day, filling rest days with TSS=0.

    Returns date, tss, duration_h, ride_count, avg_power, normalized_power, ctl, atl, tsb.
    Multiple rides on the same day are summed/aggregated. By default the timeline
    extends to today, so CTL/ATL/TSB keep decaying naturally after the last uploaded ride,
    similar to Intervals.icu / PMC.
    """
    cols = ["date", "date_dt", "tss", "duration_h", "ride_count", "avg_power", "normalized_power", "ctl", "atl", "tsb"]
    if not rides:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rides).copy()
    if "date" not in df.columns:
        return pd.DataFrame(columns=cols)
    df["date_dt"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df = df[pd.notna(df["date_dt"])]
    if df.empty:
        return pd.DataFrame(columns=cols)
    df["tss"] = pd.to_numeric(df.get("tss", 0), errors="coerce").fillna(0)
    df["duration_min"] = pd.to_numeric(df.get("dur", 0), errors="coerce").fillna(0)
    df["duration_h"] = df["duration_min"] / 60
    df["avg_power"] = pd.to_numeric(df.get("avg_p", 0), errors="coerce").fillna(0)
    df["normalized_power"] = pd.to_numeric(df.get("np", 0), errors="coerce").fillna(0)

    daily_base = df.groupby("date_dt", as_index=True).agg(
        tss=("tss", "sum"),
        duration_h=("duration_h", "sum"),
        ride_count=("date", "count"),
        avg_power=("avg_power", "mean"),
        normalized_power=("normalized_power", "mean"),
    ).sort_index()

    if end_date is None:
        end_dt = pd.Timestamp.today().normalize()
    else:
        end_dt = pd.to_datetime(end_date, errors="coerce")
        end_dt = end_dt.normalize() if pd.notna(end_dt) else pd.Timestamp.today().normalize()
    end_dt = max(daily_base.index.max(), end_dt)
    full_index = pd.date_range(daily_base.index.min(), end_dt, freq="D")
    daily_base = daily_base.reindex(full_index, fill_value=0)

    c, a = 0.0, 0.0
    rows = []
    for dt, row in daily_base.iterrows():
        tss_val = float(row.get("tss", 0) or 0)
        c = c + (tss_val - c) / ctl_tau
        a = a + (tss_val - a) / atl_tau
        rows.append({
            "date": dt.strftime("%Y-%m-%d"),
            "date_dt": dt,
            "tss": round(tss_val, 1),
            "duration_h": round(float(row.get("duration_h", 0) or 0), 2),
            "ride_count": int(row.get("ride_count", 0) or 0),
            "avg_power": round(float(row.get("avg_power", 0) or 0)),
            "normalized_power": round(float(row.get("normalized_power", 0) or 0)),
            "ctl": round(c),
            "atl": round(a),
            "tsb": round(c - a),
        })
    return pd.DataFrame(rows)

def enrich_rides(rides, ftp=None):
    if ftp is None:
        ftp = estimate_ftp(rides)
    for r in rides:
        # Step 1: estimate NP from avg_p if missing
        if r.get('np', 0) == 0 and r.get('avg_p', 0) > 0:
            r['np'] = round(r['avg_p'] * 1.05)
    for r in rides:
        # Step 2: estimate TSS from NP (now that NP is filled)
        if r.get('tss', 0) == 0 and r.get('dur', 0) > 0 and r.get('np', 0) > 0:
            if_val = r['np'] / ftp
            tss_est = (r['dur'] * 60 * r['np'] * if_val) / (ftp * 3600) * 100
            r['tss'] = round(tss_est, 1)
    return rides

