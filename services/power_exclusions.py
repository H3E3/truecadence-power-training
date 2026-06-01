from __future__ import annotations

import datetime
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Callable

import streamlit as st


POWER_EXCLUSION_DURATIONS = ['5s', '30s', '1min', '5min', '20min', '40min', '60min', '2h', '3h']
POWER_EXCLUSION_REASON_OPTIONS = ['功率计飘值', '设备断连/重连', '室内台或功率源异常', '数据导入异常', '其他']


def current_rider_power_exclusions_path(
    user=None,
    rider: str = "默认骑手",
    app_dir: Path | str | None = None,
    get_rider_data_path_func: Callable | None = None,
) -> Path:
    """Per-rider analysis-layer exclusions; never mutates original FIT or ride history."""
    if user and get_rider_data_path_func:
        return get_rider_data_path_func(user["user_id"], rider, "power_exclusions")
    base_dir = Path(app_dir) if app_dir is not None else Path.cwd()
    return base_dir / "power_exclusions.json"


def load_power_exclusions(path: Path | str) -> list:
    try:
        p = Path(path)
        if p.exists():
            with open(p, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
    except Exception:
        return []
    return []


def save_power_exclusions(items, path: Path | str):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items if isinstance(items, list) else [], f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def ride_exclusion_key(r):
    """Stable key used only by analysis exclusions. Prefer FIT hash; fall back to summary identity."""
    if not isinstance(r, dict):
        return ""
    if r.get("file_hash"):
        return f"hash:{r.get('file_hash')}"
    if r.get("external_id"):
        return f"external:{r.get('source', '')}:{r.get('external_id')}"
    return "summary:" + "|".join(str(r.get(k, "")) for k in ("date", "dur", "dist", "avg_p", "np", "max_p", "hr_avg", "hr_max", "tss"))


def ride_exclusion_label(r):
    date = str((r or {}).get("date") or "unknown")
    name = str((r or {}).get("file_name") or "")
    dist = (r or {}).get("dist", 0) or 0
    dur = (r or {}).get("dur", 0) or 0
    max_p = (r or {}).get("max_p", 0) or 0
    parts = [date]
    if dist:
        parts.append(f"{dist}km")
    if dur:
        parts.append(f"{dur}min")
    if max_p:
        parts.append(f"max {max_p}W")
    if name:
        parts.append(name[:48])
    return " · ".join(parts)


def apply_power_exclusions_to_rides(rides, exclusions=None):
    """Mark ride dicts with excluded peak durations for downstream Power Profile calculations."""
    by_key = {}
    for item in exclusions or []:
        if not isinstance(item, dict):
            continue
        key = item.get("ride_key") or ""
        durations = [d for d in (item.get("durations") or []) if d in POWER_EXCLUSION_DURATIONS]
        if key and durations:
            by_key.setdefault(key, set()).update(durations)
    out = []
    for r in rides or []:
        if not isinstance(r, dict):
            continue
        rr = dict(r)
        durations = sorted(by_key.get(ride_exclusion_key(rr), set()), key=lambda x: POWER_EXCLUSION_DURATIONS.index(x))
        if durations:
            rr["power_exclude_durations"] = durations
        out.append(rr)
    return out


def render_power_exclusion_manager(rides, exclusions_path: Path | str):
    """MVP: exclude selected ride peak windows from Power Profile / power curve only."""
    exclusions = load_power_exclusions(exclusions_path)
    active_count = sum(len([d for d in (x.get("durations") or []) if d in POWER_EXCLUSION_DURATIONS]) for x in exclusions if isinstance(x, dict))
    with st.expander(f"🧹 异常功率排除（仅影响功率画像/峰值曲线）{f' · 已排除 {active_count} 项' if active_count else ''}", expanded=False):
        st.caption("用于处理功率计飘值、断连重连等造成的假峰值。这里不会删除原始 FIT，也不会改写历史骑行记录；只在本页 Power Profile / 峰值曲线计算时跳过被标记的窗口。")
        ride_options = []
        seen = set()
        for r in sorted([x for x in (rides or []) if isinstance(x, dict)], key=lambda x: str(x.get("date", "")), reverse=True):
            key = ride_exclusion_key(r)
            if not key or key in seen:
                continue
            seen.add(key)
            ride_options.append((ride_exclusion_label(r), key, r))

        if not ride_options:
            st.info("当前没有可标记的骑行记录。")
            return exclusions

        labels = [x[0] for x in ride_options]
        selected_label = st.selectbox("选择有异常峰值的骑行", labels, key="power_exclusion_select_ride")
        selected = ride_options[labels.index(selected_label)]
        selected_ride = selected[2]
        pc = selected_ride.get("power_curve") or {}
        current_vals = []
        for d in POWER_EXCLUSION_DURATIONS:
            v = pc.get(d) or selected_ride.get(f"best_{d}") or 0
            if d == '5s' and not v:
                v = selected_ride.get('max_p', 0) or 0
            if v:
                current_vals.append(f"{d}: {round(float(v))}W")
        if current_vals:
            st.caption("这条记录当前峰值：" + " ｜ ".join(current_vals))

        c1, c2 = st.columns([2, 1])
        durations = c1.multiselect("排除哪些峰值窗口", POWER_EXCLUSION_DURATIONS, default=['5s'], key="power_exclusion_durations")
        reason = c2.selectbox("原因", POWER_EXCLUSION_REASON_OPTIONS, key="power_exclusion_reason")
        note = st.text_input("备注（可选）", placeholder="例如：功率计飘到 5s 2000W", key="power_exclusion_note")
        if st.button("标记为异常并从功率画像排除", type="primary", use_container_width=True, disabled=not durations, key="power_exclusion_add"):
            new_item = {
                "id": hashlib.sha256(f"{selected[1]}:{','.join(durations)}:{time.time()}".encode("utf-8")).hexdigest()[:12],
                "ride_key": selected[1],
                "ride_label": selected[0],
                "date": selected_ride.get("date", ""),
                "durations": durations,
                "reason": reason,
                "note": note,
                "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
            }
            exclusions.append(new_item)
            save_power_exclusions(exclusions, exclusions_path)
            st.success("已标记。原始 FIT 不变，功率画像会跳过这条记录对应窗口。")
            st.rerun()

        if exclusions:
            st.markdown("**已生效的排除项**")
            for item in list(exclusions):
                if not isinstance(item, dict):
                    continue
                cols = st.columns([5, 1])
                desc = f"{item.get('ride_label', item.get('date', ''))} ｜ {', '.join(item.get('durations') or [])} ｜ {item.get('reason', '')}"
                if item.get("note"):
                    desc += f" ｜ {item.get('note')}"
                cols[0].caption(desc)
                if cols[1].button("撤销", key=f"power_exclusion_del_{item.get('id', hashlib.sha1(desc.encode()).hexdigest()[:8])}", use_container_width=True):
                    exclusions = [x for x in exclusions if x is not item and x.get("id") != item.get("id")]
                    save_power_exclusions(exclusions, exclusions_path)
                    st.rerun()
        return exclusions
