from __future__ import annotations

import datetime
import io
import json
import os
import zipfile

import pandas as pd
import streamlit as st

from ui_components import (
    render_empty_data_state,
    render_plan_builder_intro,
    render_plan_builder_styles,
    render_plan_source_scope,
    render_plan_summary_cards,
)


def render_training_plan_page(
    *,
    select_ride_scope,
    merge_rides,
    load_historical,
    enrich_rides,
    data_scope_caption,
    load_profile,
    save_rider_profile=None,
    estimate_ftp,
    estimate_best_powers,
    infer_cycle_status_for_date,
    load_plan_prefs,
    save_plan_prefs,
    PLAN_PREF_DEFAULTS,
    compute_daily_pmc,
    load_feedback,
    summarize_recent_feedback,
    load_wearable_sleep,
    rules_build_rider_state_v1,
    rules_build_cadence_torque_state,
    rules_build_progression_state_v1,
    rules_build_event_context,
    rules_detect_phase,
    rules_refined_readiness_cap,
    rules_choose_mmp_training_focus,
    rules_build_week_plan,
    rules_validate_week_plan,
    rules_phase_meta,
    rules_tss,
    rules_week_factor,
    rules_zone_style,
    estimate_tss_from_blocks,
    workout_blocks_for_item,
    workout_exports_for_item,
    require_plan,
    clamp_number,
    DATA_DIR,
    PLAN_HARD_KINDS,
):
    require_plan(1, "📋 训练课表")

    uploaded_rides, historical, use_all, rides, source_label = render_plan_source_scope(select_ride_scope, merge_rides)
    rides.sort(key=lambda x: x['date'])
    rides = enrich_rides(rides)
    if not rides:
        render_empty_data_state(
            "训练课表需要先建立功率基准",
            "课表会根据 FTP、训练负荷、恢复状态和训练目标生成。请先上传 FIT;如果有实测 FTP,先在骑手档案填写,课表会更准确。",
            ["填写体重、实测 FTP、最大心率和训练目标", "上传 FIT 建立功率和负荷数据", "再回来生成本周训练课表和 ZWO"]
        )
        st.stop()

    st.caption(data_scope_caption(rides, historical, uploaded_rides, source_label))

    profile = load_profile()
    est_ftp = estimate_ftp(rides)
    actual_ftp = profile.get('ftp_test', 0) or 0
    ftp = actual_ftp if actual_ftp > 0 else est_ftp
    ftp_source = f"客户填写 FTP {actual_ftp}W" if actual_ftp > 0 else f"FIT 自动估算 FTP {est_ftp}W"
    plan_best_powers = estimate_best_powers(rides, ftp)
    cycle_status = infer_cycle_status_for_date(datetime.date.today(), profile)
    weight = profile.get('weight', 69) or 69
    wkg = round(ftp / weight, 1) if ftp and weight else 0

    render_plan_builder_styles()
    render_plan_builder_intro()

    PLAN_GOAL_OPTIONS = [
        "恢复体能 / 重建基础",
        "减脂减重 / 燃脂骑",
        "提升 FTP / 功体比",
        "备战绕圈赛",
        "备战爬坡赛",
        "备战个人计时赛",
        "备战长距离耐力赛",
        "备战公路赛",
        "赛前减量 / 巅峰",
        "维持现状 / 休闲骑",
    ]
    EVENT_TYPE_OPTIONS = ["无比赛", "绕圈赛", "爬坡赛", "个人计时赛", "长距离耐力赛", "公路赛"]
    GOAL_TO_EVENT_TYPE = {
        "备战绕圈赛": "绕圈赛",
        "备战爬坡赛": "爬坡赛",
        "备战个人计时赛": "个人计时赛",
        "备战长距离耐力赛": "长距离耐力赛",
        "备战公路赛": "公路赛",
    }
    TRAINING_EXPERIENCE_OPTIONS = ["未填写", "新手", "普通骑行者", "有结构化训练经验", "有比赛经验"]
    DETRAINING_DURATION_OPTIONS = ["未填写", "无停训", "2-4周", "1-3月", "3月以上", "伤病后恢复"]
    PROGRESSION_OPTIONS = ["保守", "标准", "略进阶"]
    PROGRESSION_EXPLAIN = {
        "保守": "少加量、少冒险，适合恢复一般、刚回归或只想稳定完成。",
        "标准": "按当前周时长和状态稳健推进。",
        "略进阶": "不是直接把 TSS 拉到很高；只有数据、恢复和训练背景允许时，小幅增加容量/推进感。若想要 600+ TSS/周，需要把每周总时长调到相应范围，且安全门控不能触发降级。",
    }
    EVENT_PRIORITY_OPTIONS = ["A", "B", "C"]

    plan_prefs = load_plan_prefs()
    day_order = ['周一','周二','周三','周四','周五','周六','周日']
    default_training_days = [d for d in plan_prefs.get("training_days", PLAN_PREF_DEFAULTS["training_days"]) if d in day_order] or PLAN_PREF_DEFAULTS["training_days"]
    profile_goal = profile.get("goal") if profile.get("goal") in PLAN_GOAL_OPTIONS else ""
    default_goal = plan_prefs.get("goal") or profile_goal or PLAN_PREF_DEFAULTS["goal"]
    default_event_date = datetime.date.today() + datetime.timedelta(days=28)
    try:
        saved_event_date = datetime.date.fromisoformat(plan_prefs.get("event_date") or "")
    except Exception:
        saved_event_date = default_event_date

    if "plan_goal_select_v2" not in st.session_state:
        st.session_state["plan_goal_select_v2"] = default_goal if default_goal in PLAN_GOAL_OPTIONS else PLAN_GOAL_OPTIONS[0]
    if "plan_weeks_form_v2" not in st.session_state:
        st.session_state["plan_weeks_form_v2"] = clamp_number(plan_prefs.get("weeks"), 4, 1, 12)
    if "plan_hours_form_v2" not in st.session_state:
        st.session_state["plan_hours_form_v2"] = clamp_number(plan_prefs.get("hours"), 8, 4, 20)

    with st.form("training_plan_basic_settings_form_v2", border=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            goal = st.selectbox("训练目标", PLAN_GOAL_OPTIONS, key="plan_goal_select_v2")
        with c2:
            weeks = st.slider("计划周期", 1, 12, key="plan_weeks_form_v2")
        with c3:
            hours = st.slider("每周总时长 h", 4, 20, key="plan_hours_form_v2")
            st.caption("新手/刚恢复建议 3–5h；有基础 5–8h；进阶 8–12h；12h+ 适合训练基础和恢复都较稳定的人。TrueCadence 不按固定死档排课，会结合训练背景、FTP可信度、恢复/疼痛反馈和比赛时间自动调整。")
        applied_basic_settings = st.form_submit_button("应用课表基础设置", type="primary", use_container_width=True)
    if applied_basic_settings:
        st.success("已应用当前训练目标、计划周期和每周总时长。")

    suggested_event_type = GOAL_TO_EVENT_TYPE.get(goal, "无比赛")
    if st.session_state.get("plan_last_goal_for_event_sync") != goal:
        st.session_state["plan_last_goal_for_event_sync"] = goal
        # 训练目标是课表主意图。非比赛目标必须清空比赛类型,避免阶段D倒计时污染普通训练课表。
        st.session_state["plan_event_type_v2"] = suggested_event_type

    with st.expander("🧱 训练背景与稳定推进（阶段F，可选）", expanded=False):
        bg1, bg2, bg3 = st.columns(3)
        with bg1:
            saved_training_experience = plan_prefs.get("training_experience", PLAN_PREF_DEFAULTS["training_experience"])
            training_experience = st.selectbox("训练经验", TRAINING_EXPERIENCE_OPTIONS, index=TRAINING_EXPERIENCE_OPTIONS.index(saved_training_experience) if saved_training_experience in TRAINING_EXPERIENCE_OPTIONS else 0, key="plan_training_experience_v1")
            historical_best_ftp = st.number_input("历史最佳FTP W（可选）", min_value=0, max_value=600, value=clamp_number(plan_prefs.get("historical_best_ftp"), 0, 0, 600), step=5, key="plan_historical_best_ftp_v1")
        with bg2:
            saved_detraining_duration = plan_prefs.get("detraining_duration", PLAN_PREF_DEFAULTS["detraining_duration"])
            detraining_duration = st.selectbox("停训时间", DETRAINING_DURATION_OPTIONS, index=DETRAINING_DURATION_OPTIONS.index(saved_detraining_duration) if saved_detraining_duration in DETRAINING_DURATION_OPTIONS else 0, key="plan_detraining_duration_v1")
            historical_best_wkg = st.number_input("历史最佳W/kg（可选）", min_value=0.0, max_value=8.0, value=clamp_number(plan_prefs.get("historical_best_wkg"), 0.0, 0.0, 8.0, as_float=True), step=0.1, key="plan_historical_best_wkg_v1")
        with bg3:
            saved_progression = plan_prefs.get("progression_preference", PLAN_PREF_DEFAULTS["progression_preference"])
            progression_preference = st.selectbox("训练推进偏好", PROGRESSION_OPTIONS, index=PROGRESSION_OPTIONS.index(saved_progression) if saved_progression in PROGRESSION_OPTIONS else 1, key="plan_progression_preference_v1")
        st.caption("阶段F不是更难模式。" + PROGRESSION_EXPLAIN.get(progression_preference, "它只在恢复、疼痛、FTP可信度和比赛倒计时都允许时,根据训练背景小幅调整推进速度。"))

    with st.expander("🎯 比赛倒计时 / 专项设置（阶段D，可选）", expanded=False):
        ev1, ev2, ev3 = st.columns([1.2, 1.2, .8])
        with ev1:
            saved_event_type = st.session_state.get("plan_event_type_v2", plan_prefs.get("event_type", PLAN_PREF_DEFAULTS["event_type"]))
            event_type = st.selectbox("比赛类型", EVENT_TYPE_OPTIONS, index=EVENT_TYPE_OPTIONS.index(saved_event_type) if saved_event_type in EVENT_TYPE_OPTIONS else 0, key="plan_event_type_v2")
        with ev2:
            event_date = st.date_input("比赛日期", value=saved_event_date, key="plan_event_date_v1")
        with ev3:
            saved_priority = plan_prefs.get("event_priority", PLAN_PREF_DEFAULTS["event_priority"])
            event_priority = st.selectbox("优先级", EVENT_PRIORITY_OPTIONS, index=EVENT_PRIORITY_OPTIONS.index(saved_priority) if saved_priority in EVENT_PRIORITY_OPTIONS else 1, help="A=主要目标;B=重要训练赛;C=普通参与", key="plan_event_priority_v1")
        use_event_countdown = event_type != "无比赛"
        days_to_event = (event_date - datetime.date.today()).days if use_event_countdown else None
        if goal == "赛前减量 / 巅峰" and not use_event_countdown:
            st.caption("当前训练目标是赛前减量/巅峰:它是周期阶段,不是比赛类型。若这是为具体比赛减量,请在这里手动选择比赛类型和日期。")
        elif suggested_event_type != "无比赛" and event_type == suggested_event_type:
            st.caption(f"已根据训练目标同步为 {event_type}。距离比赛还有 {days_to_event} 天。阶段D只做倒计时和专项微调,不会覆盖恢复/疼痛/FTP安全门控。")
        elif use_event_countdown:
            st.caption(f"距离 {event_type} 还有 {days_to_event} 天。阶段D只做倒计时和专项微调,不会覆盖恢复/疼痛/FTP安全门控。")
        else:
            st.caption("未启用比赛倒计时:课表按目标与当前状态生成。")

    sc1, sc2, sc3 = st.columns([2.2, 1.2, 1.6])
    with sc1:
        selected_training_days = st.multiselect(
            "可训练日",
            day_order,
            default=default_training_days,
            help="直接决定每周训练天数。未选日期会固定显示为休息日。",
            key="plan_training_days_select_v2",
        )
    if len(selected_training_days) < 3:
        st.warning("请至少选择 3 个可训练日,否则课表无法保证关键课、耐力课和恢复之间的基本结构。")
        st.stop()
    selected_training_days = [d for d in day_order if d in selected_training_days]
    days = len(selected_training_days)
    with sc2:
        saved_long_day = plan_prefs.get("preferred_long_day", PLAN_PREF_DEFAULTS["preferred_long_day"])
        preferred_long_day = st.selectbox(
            "长距离日",
            selected_training_days,
            index=(selected_training_days.index(saved_long_day) if saved_long_day in selected_training_days else (selected_training_days.index('周日') if '周日' in selected_training_days else len(selected_training_days)-1)),
            help="长距离/Z2容量/模拟课会优先放在这一天。",
            key="plan_long_day_select_v2",
        )
    with sc3:
        saved_no_hard_days = [d for d in plan_prefs.get("no_hard_days", []) if d in selected_training_days]
        no_hard_days = st.multiselect(
            "不安排高强度日",
            selected_training_days,
            default=saved_no_hard_days,
            help="这些天仍可安排 Z2、恢复、技术骑,但会尽量避开阈值、VO2、冲刺等质量课。",
            key="plan_no_hard_days_select_v2",
        )
    fixed_rest_days = [d for d in day_order if d not in selected_training_days]
    if fixed_rest_days:
        st.caption(f"实际训练日:{days} 天 | 固定休息日:" + "、".join(fixed_rest_days) + f" | 长距离优先:{preferred_long_day}")
    else:
        st.caption(f"实际训练日:7 天 | 长距离优先:{preferred_long_day}。系统仍会安排恢复/轻松日,不建议每天都高强度。")

    current_plan_prefs = {
        "goal": goal,
        "weeks": int(weeks),
        "hours": int(hours),
        "training_experience": training_experience,
        "historical_best_ftp": int(historical_best_ftp or 0),
        "detraining_duration": detraining_duration,
        "historical_best_wkg": float(historical_best_wkg or 0),
        "progression_preference": progression_preference,
        "event_type": event_type,
        "event_date": event_date.isoformat() if hasattr(event_date, "isoformat") else str(event_date),
        "event_priority": event_priority,
        "training_days": selected_training_days,
        "preferred_long_day": preferred_long_day,
        "no_hard_days": no_hard_days,
    }
    saved_plan_prefs = {k: plan_prefs.get(k) for k in current_plan_prefs}
    prefs_changed = current_plan_prefs != saved_plan_prefs
    if prefs_changed:
        if st.button("保存当前课表设置", key="save_training_plan_prefs_v1", use_container_width=True):
            save_plan_prefs({**current_plan_prefs, "updated_at": datetime.datetime.now().isoformat(timespec="seconds")})
            try:
                profile_for_goal_sync = load_profile() or {}
                profile_for_goal_sync["goal"] = goal
                user_for_goal_sync = st.session_state.get("user")
                rider_for_goal_sync = st.session_state.get("rider", "默认骑手")
                if user_for_goal_sync and save_rider_profile:
                    save_rider_profile(user_for_goal_sync["user_id"], rider_for_goal_sync, profile_for_goal_sync)
            except Exception:
                pass
            st.success("已保存当前课表设置，训练目标已同步到骑手档案。")
            st.rerun()

    # ── dynamic readiness inputs: training load + feedback + sleep ──
    df_plan = pd.DataFrame(rides).sort_values('date')
    df_plan['date_dt'] = pd.to_datetime(df_plan['date'], errors='coerce')
    df_plan['duration_h'] = pd.to_numeric(df_plan.get('dur', 0), errors='coerce').fillna(0) / 60
    df_plan_pmc = compute_daily_pmc(rides)
    latest_date = df_plan_pmc['date_dt'].max() if not df_plan_pmc.empty else pd.NaT
    current_ctl = int(df_plan_pmc.iloc[-1]['ctl']) if not df_plan_pmc.empty else 0
    current_atl = int(df_plan_pmc.iloc[-1]['atl']) if not df_plan_pmc.empty else 0
    current_tsb = int(df_plan_pmc.iloc[-1]['tsb']) if not df_plan_pmc.empty else 0
    if pd.isna(latest_date):
        recent_7 = df_plan.tail(7)
        recent_28 = df_plan.tail(28)
    else:
        recent_7 = df_plan[df_plan['date_dt'] >= latest_date - pd.Timedelta(days=6)]
        recent_28 = df_plan[df_plan['date_dt'] >= latest_date - pd.Timedelta(days=27)]
    tss_7 = round(recent_7.get('tss', pd.Series(dtype=float)).fillna(0).sum()) if len(recent_7) else 0
    hours_7 = round(recent_7.get('duration_h', pd.Series(dtype=float)).fillna(0).sum(), 1) if len(recent_7) else 0
    hours_28 = round(recent_28.get('duration_h', pd.Series(dtype=float)).fillna(0).sum(), 1) if len(recent_28) else 0
    ctl_7_days_ago = df_plan_pmc.iloc[-8]['ctl'] if len(df_plan_pmc) >= 8 else df_plan_pmc.iloc[0]['ctl'] if not df_plan_pmc.empty else 0
    ramp_rate = current_ctl - ctl_7_days_ago

    feedback = load_feedback()
    recent_feedback = sorted(feedback, key=lambda x: (x.get('date', ''), x.get('created_at', '')), reverse=True)[:5]
    def _avg_feedback(k):
        vals = [x.get(k) for x in recent_feedback if isinstance(x.get(k), (int, float))]
        return round(sum(vals) / len(vals), 1) if vals else None
    avg_sleep = _avg_feedback('sleep_quality')
    avg_fatigue = _avg_feedback('leg_fatigue')
    avg_energy = _avg_feedback('energy')
    pain_items, special_items = [], []
    for item in recent_feedback:
        pain_items.extend(item.get('pains', []) or [])
        special_items.extend(item.get('specials', []) or [])

    readiness_reasons = []
    readiness_factor = 1.0
    intensity_cap = "normal"
    readiness_label = "状态可推进"
    if current_tsb < -25 or (avg_sleep and avg_sleep <= 2.2) or (avg_fatigue and avg_fatigue >= 4.3) or '感冒/发烧' in special_items or '生病' in special_items:
        readiness_label = "恢复优先"
        readiness_factor = 0.65
        intensity_cap = "recovery"
        readiness_reasons.append("负荷/反馈提示风险偏高,本周自动降量并替换高强度课")
    elif current_tsb < -12 or current_atl > current_ctl + 10 or (avg_sleep and avg_sleep <= 3) or (avg_fatigue and avg_fatigue >= 3.5) or pain_items:
        readiness_label = "谨慎推进"
        readiness_factor = 0.82
        intensity_cap = "caution"
        readiness_reasons.append("近期疲劳或主观反馈偏紧,本周保留少量质量课,其余降为 Z2/恢复")
    else:
        readiness_reasons.append("训练负荷和主观反馈未见明显红旗,可按目标推进")
    if ramp_rate > 8:
        readiness_factor = min(readiness_factor, 0.9)
        readiness_reasons.append(f"CTL 近 7 次约 +{round(ramp_rate)},加量偏快")
    if cycle_status and isinstance(cycle_status, str) and '经期' in cycle_status:
        readiness_factor = min(readiness_factor, 0.85)
        intensity_cap = "caution" if intensity_cap == "normal" else intensity_cap
        readiness_reasons.append("本周经期:高强度课可后移或降一级")
    if hours >= 16:
        readiness_reasons.append("用户设置周总量偏高,系统会优先保护质量课并限制过长训练")

    rules_cap, rules_factor, rules_reasons = rules_refined_readiness_cap(
        base_cap=intensity_cap,
        current_tsb=current_tsb,
        current_ctl=current_ctl,
        current_atl=current_atl,
        ramp_rate=ramp_rate,
        avg_sleep=avg_sleep,
        avg_fatigue=avg_fatigue,
        pain_items=pain_items,
        special_items=special_items,
    )
    if rules_factor < readiness_factor:
        readiness_factor = rules_factor
    if {"normal": 0, "caution": 1, "recovery": 2}.get(rules_cap, 0) > {"normal": 0, "caution": 1, "recovery": 2}.get(intensity_cap, 0):
        intensity_cap = rules_cap
        readiness_label = "恢复优先" if intensity_cap == "recovery" else "谨慎推进"
    for reason in rules_reasons:
        if reason not in readiness_reasons:
            readiness_reasons.append(reason)

    rider_state = rules_build_rider_state_v1(
        ftp=ftp,
        ftp_source=ftp_source,
        best_powers=plan_best_powers,
        rides_count=len(rides),
        base_cap=intensity_cap,
        current_tsb=current_tsb,
        current_ctl=current_ctl,
        current_atl=current_atl,
        ramp_rate=ramp_rate,
        avg_sleep=avg_sleep,
        avg_fatigue=avg_fatigue,
        pain_items=pain_items,
        special_items=special_items,
    )
    if rider_state.readiness_factor < readiness_factor:
        readiness_factor = rider_state.readiness_factor
    if {"normal": 0, "caution": 1, "recovery": 2}.get(rider_state.readiness, 0) > {"normal": 0, "caution": 1, "recovery": 2}.get(intensity_cap, 0):
        intensity_cap = rider_state.readiness
        readiness_label = "恢复优先" if intensity_cap == "recovery" else "谨慎推进"
    for reason in rider_state.readiness_reasons + rider_state.ftp_reasons + rider_state.data_warnings:
        if reason not in readiness_reasons:
            readiness_reasons.append(reason)

    phase = rules_detect_phase(goal, wkg)
    mmp_confidence_for_plan = "高" if len([v for v in plan_best_powers.values() if v]) >= 5 and len(rides) >= 4 else ("中" if len([v for v in plan_best_powers.values() if v]) >= 3 else "低")
    mmp_focus_state = rules_choose_mmp_training_focus(
        phase=phase,
        ftp=ftp,
        best_powers=plan_best_powers,
        mmp_confidence=mmp_confidence_for_plan,
        readiness=intensity_cap,
        ftp_status=rider_state.ftp_status,
    )
    recent_cadence_rides = [r for r in rides[-12:] if r.get('avg_cadence')]
    if recent_cadence_rides:
        plan_avg_cadence = round(sum(float(r.get('avg_cadence') or 0) for r in recent_cadence_rides) / len(recent_cadence_rides), 1)
        plan_low_cadence_ratio = round(sum(float(r.get('low_cadence_ratio') or 0) for r in recent_cadence_rides) / len(recent_cadence_rides), 3)
        plan_high_cadence_ratio = round(sum(float(r.get('high_cadence_ratio') or 0) for r in recent_cadence_rides) / len(recent_cadence_rides), 3)
    else:
        plan_avg_cadence = plan_low_cadence_ratio = plan_high_cadence_ratio = 0
    cadence_state = rules_build_cadence_torque_state(
        avg_cadence=plan_avg_cadence,
        low_cadence_ratio=plan_low_cadence_ratio,
        high_cadence_ratio=plan_high_cadence_ratio,
        pain_items=pain_items,
        readiness=intensity_cap,
        ftp_status=rider_state.ftp_status,
    )
    event_context = rules_build_event_context(
        event_type=event_type,
        days_to_event=days_to_event,
        priority=event_priority,
        readiness=intensity_cap,
    )
    if event_context.get("phase_override"):
        phase = event_context.get("phase_override")
    recent_weekly_hours_for_progression = 0
    try:
        recent_weekly_hours_for_progression = round(sum(float(r.get('dur_h') or r.get('hours') or 0) for r in rides[-8:]) / 2, 1) if rides else 0
    except Exception:
        recent_weekly_hours_for_progression = 0
    progression_state = rules_build_progression_state_v1(
        goal=goal,
        current_ftp=ftp,
        weight=weight,
        recent_rides_count=len(rides),
        recent_weekly_hours=recent_weekly_hours_for_progression,
        rider_state=rider_state,
        mmp_confidence=mmp_confidence_for_plan,
        cadence_state=cadence_state,
        event_context=event_context,
        training_experience=training_experience,
        detraining_duration=detraining_duration,
        historical_best_ftp=historical_best_ftp or None,
        historical_best_wkg=historical_best_wkg or None,
        progression_preference=progression_preference,
    )

    ai_plan_hint = "AI 未参与本次排课;当前已基于 FIT、训练负荷、睡眠/反馈动态生成,不影响使用。"
    ai_plan_ctx = {}
    try:
        user = st.session_state.get("user")
        if user:
            user_dir = DATA_DIR / user.get("user_id", "")
            ai_ctx_file = user_dir / "ai_training_plan_context.json"
            if ai_ctx_file.exists():
                with open(ai_ctx_file, "r", encoding="utf-8") as f:
                    ai_plan_ctx = json.load(f)
                ai_plan_hint = f"已接入 AI 分析({ai_plan_ctx.get('generated_at', '-') }):{ai_plan_ctx.get('ftp_source', '-') } FTP {ai_plan_ctx.get('ftp', '-')}W,反馈 {ai_plan_ctx.get('feedback_count', 0)} 条"
                ai_risks = ai_plan_ctx.get("feedback_risk_flags", []) or []
                if ai_risks:
                    readiness_factor = min(readiness_factor, 0.9)
                    readiness_reasons.append("AI 分析提示主观恢复风险:" + ";".join(ai_risks[:2]))
            elif st.session_state.get("ai_diagnosis"):
                ai_plan_hint = "已读取本次会话 AI 报告;未落盘结构化结论,但不影响当前动态排课。"
    except Exception:
        pass


    phase_meta = rules_phase_meta()
    pm = phase_meta[phase]
    hard_kinds = PLAN_HARD_KINDS

    def zone_style(kind):
        return rules_zone_style(kind)

    def tss(kind, h):
        return rules_tss(kind, h)

    def week_factor(wk):
        return rules_week_factor(phase, wk, readiness_factor)

    all_weeks = []
    for wk in range(1, weeks+1):
        rows, theme_name, theme_desc, theme_sources = rules_build_week_plan(
            phase=phase,
            wk=wk,
            ftp=ftp,
            hours=hours,
            readiness_factor=readiness_factor,
            intensity_cap=intensity_cap,
            selected_training_days=selected_training_days,
            preferred_long_day=preferred_long_day,
            no_hard_days=no_hard_days,
            ftp_status=rider_state.ftp_status,
            forbidden_modules=rider_state.forbidden_modules,
            caution_notes=rider_state.ftp_reasons + rider_state.data_warnings,
            mmp_focus=mmp_focus_state.get("focus"),
            mmp_focus_notes=mmp_focus_state.get("notes", []),
            cadence_state=cadence_state,
            event_context=event_context,
            progression_state=progression_state,
        )
        actual_h = round(sum(x.get('dur_h',0) for x in rows), 1)
        for x in rows:
            if not x.get('rest') and x.get('dur_h', 0) > 0:
                x['planned_tss'] = estimate_tss_from_blocks(workout_blocks_for_item(x))
            else:
                x['planned_tss'] = 0
        actual_tss = sum(int(x.get('planned_tss', 0) or 0) for x in rows)
        target_h = round(hours*week_factor(wk),1)
        quality = rules_validate_week_plan(
            rows=rows,
            phase=phase,
            wk=wk,
            target_h=target_h,
            preferred_long_day=preferred_long_day,
            no_hard_days=no_hard_days,
            intensity_cap=intensity_cap,
        )
        all_weeks.append({'wk':wk,'rows':rows,'theme':theme_name,'theme_desc':theme_desc,'theme_sources':theme_sources,'target_h':target_h,'actual_h':actual_h,'tss':actual_tss,'quality':quality})

    first = all_weeks[0]
    active_count = sum(1 for x in first['rows'] if not x.get('rest'))
    key_sessions = [x['name'] for x in first['rows'] if x['kind'] in ('sweet','threshold','vo2','crit','climb','openers')][:2]
    key_text = '、'.join(key_sessions) if key_sessions else '以 Z2 耐力和恢复为主'
    load_note = readiness_label
    if hours >= 16: load_note += '|高周量设置'
    elif hours <= 5: load_note += '|先建立连续性'
    if intensity_cap == 'recovery':
        key_text = '本周高强度自动替换为恢复/Z2'
    elif intensity_cap == 'caution' and key_sessions:
        key_text = '保留 1 个关键课,其余降级'

    evidence_text = ';'.join(readiness_reasons[:4])
    render_plan_summary_cards(pm, ftp, wkg, weight, first, key_text, load_note)

    # Explain why this week is arranged this way, like a coach briefing before the table.
    if intensity_cap == "recovery":
        plan_logic_title = "为什么本周偏恢复?"
        plan_logic_main = "当前负荷或主观反馈提示恢复风险,系统优先降低强度密度,把高强度课替换成恢复骑 / Z2。"
    elif intensity_cap == "caution":
        plan_logic_title = "为什么本周谨慎推进?"
        plan_logic_main = "当前可以训练,但恢复余量不算宽。系统保留少量关键课,其余用 Z2 / Tempo 承接,避免继续堆疲劳。"
    elif phase == "fatloss":
        plan_logic_title = "为什么本周以 Z2 燃脂为主?"
        plan_logic_main = "你的目标偏减脂/燃脂,系统优先安排稳定可持续的 Z2 和少量 Tempo,让消耗可持续,同时保护恢复。"
    elif phase in ("build", "climb", "crit"):
        plan_logic_title = "为什么本周有质量课?"
        plan_logic_main = "训练负荷和反馈没有明显红旗,目标需要能力提升,系统安排关键质量课,同时用 Z2/恢复日保证吸收。"
    elif phase == "taper":
        plan_logic_title = "为什么本周降量保强度?"
        plan_logic_main = "当前目标是赛前减量/巅峰,系统降低总量,只保留少量激活强度,重点是新鲜感和比赛状态。"
    else:
        plan_logic_title = "为什么本周这样安排?"
        plan_logic_main = "系统按当前 FTP、目标、周时长和训练负荷生成一个稳健方案,优先保持连续性而不是盲目加量。"

    plan_logic_points = [
        f"目标:{goal} → 当前阶段判定为 {pm['name']}。",
        f"负荷:CTL {current_ctl} / ATL {current_atl} / TSB {current_tsb},近 7 天 {tss_7} TSS。",
        f"阶段A保护:FTP状态 {rider_state.ftp_status};禁用模块 {', '.join(rider_state.forbidden_modules) if rider_state.forbidden_modules else '无'}。",
        f"阶段B-MMP:可信度 {mmp_confidence_for_plan};训练重点 {mmp_focus_state.get('focus')};{'；'.join(mmp_focus_state.get('notes', []))}",
        f"阶段C-踏频:状态 {cadence_state.get('status')};平均踏频 {plan_avg_cadence or '-'}rpm;低踏频比例 {round(plan_low_cadence_ratio*100) if plan_low_cadence_ratio else 0}%;{'；'.join(cadence_state.get('notes', []))}",
        f"阶段D-比赛:类型 {event_context.get('event_type')};倒计时 {event_context.get('days_to_event') if event_context.get('days_to_event') is not None else '-'}天;重点 {event_context.get('focus')};{'；'.join(event_context.get('notes', []))}",
        f"阶段F-稳定推进:模式 {progression_state.get('mode')};偏好 {progression_preference};系数 {progression_state.get('volume_multiplier')};{'；'.join(progression_state.get('notes', []))}",
        f"反馈:睡眠 {avg_sleep or '-'} / 腿疲劳 {avg_fatigue or '-'} / 能量 {avg_energy or '-'}。",
        f"本周:{first['theme']}。{active_count} 天、{first['actual_h']:.1f} 小时、约 {first['tss']} TSS,关键训练:{key_text}。",
    ]
    if ai_plan_hint and "未参与" not in ai_plan_hint:
        plan_logic_points.append(f"AI 上下文:{ai_plan_hint}")
    if evidence_text:
        plan_logic_points.append(f"调整依据:{evidence_text}")

    st.markdown(f"""
    <div style="border:1px solid rgba(255,107,53,.32);border-radius:16px;padding:1.05em 1.15em;margin:.9em 0 1em;background:linear-gradient(135deg,rgba(255,107,53,.14),rgba(22,27,34,.96));">
      <div style="color:#ff9a68;font-size:.76em;font-weight:850;letter-spacing:.10em;margin-bottom:.35em;">PLAN LOGIC</div>
      <div style="color:#f0f6fc;font-size:1.20em;font-weight:820;margin-bottom:.35em;">{plan_logic_title}</div>
      <div style="color:#aab6c3;font-size:.90em;line-height:1.7;">{plan_logic_main}</div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("🧭 查看详细排课依据", expanded=False):
        for point in plan_logic_points:
            st.markdown(f"- {point}")
        if first.get('theme_sources'):
            st.markdown("- 规则来源标签:" + "、".join(first.get('theme_sources') or []))
        st.markdown("""
    **读法:**如果 TSB 偏低、ATL 明显高于 CTL、睡眠差、腿疲劳高或有疼痛/生病记录,课表会自动降级;如果状态较好,才会保留阈值、VO2、绕圈赛或爬坡专项质量课。
    """)

    if progression_preference == "略进阶" and first['tss'] < 500:
        st.markdown('<div class="plan-warning">ℹ️ 当前选择了“略进阶”，但本周 TSS 没有拉到高周量。原因通常是：每周总时长设置、近期 CTL/ATL/TSB、睡眠/疲劳/疼痛反馈、FTP 可信度或训练天数限制。TrueCadence 会优先保证可完成和可恢复；如果你本来就能稳定承受 600+ TSS/周，请把每周总时长调高，并确认详细排课依据里没有恢复/FTP/疼痛门控。</div>', unsafe_allow_html=True)
    if hours >= 16:
        st.markdown('<div class="plan-warning">⚠️ 你设置的周总量偏高。系统会优先保护强度课质量,并把额外时间放进 Z2 / 长距离;如果睡眠、腿疲劳或经期状态不好,建议下调 10-25%。</div>', unsafe_allow_html=True)

    for week in all_weeks:
        title = f"第 {week['wk']} 周 · {week['theme']} | 目标 {week['target_h']:.1f}h | 实际 {week['actual_h']:.1f}h | 约 {week['tss']} TSS"
        with st.expander(title, expanded=(week['wk']==1)):
            st.caption("周主题:" + week.get('theme_desc', ''))
            bars = ''.join(f'<span style="display:inline-block;width:{max(7,int((x.get("dur_h",0)/max(week["actual_h"],0.1))*100))}%;height:6px;background:{zone_style(x["kind"])[1]};border-radius:2px;margin:0 1px;" title="{x["day"]}: {x["name"]}"></span>' for x in week['rows'] if not x.get('rest'))
            st.markdown(f'<div style="display:flex;gap:2px;margin:.2em 0 .8em;">{bars}</div>', unsafe_allow_html=True)
            q = week.get('quality') or {}
            q_status = q.get('status', '未检查')
            q_score = q.get('score', 0)
            if q_status == '通过':
                st.success(f"计划质量检查:{q_status} · {q_score}/100")
            elif q_status == '可用但需留意':
                st.warning(f"计划质量检查:{q_status} · {q_score}/100")
            else:
                st.error(f"计划质量检查:{q_status} · {q_score}/100")
            with st.expander("查看质量检查细节", expanded=False):
                for msg in q.get('issues', []):
                    st.markdown(f"- ❌ {msg}")
                for msg in q.get('warnings', []):
                    st.markdown(f"- ⚠️ {msg}")
                for msg in q.get('notes', []):
                    st.markdown(f"- ✅ {msg}")
            cols = st.columns(7)
            for i, item in enumerate(week['rows']):
                bg, border, zone = zone_style(item['kind'])
                dur = item.get('dur_h',0)
                dur_display = f"{dur:.1f}h" if dur > 0 else "休息"
                tss_str = '-' if dur <= 0 else f"~{int(item.get('planned_tss', 0) or 0)}"
                with cols[i]:
                    st.markdown(f"""
    <div class="plan-day" style="background:{bg}; border-top:3px solid {border};">
      <div class="dow">{item['day']}</div><div class="name">{item['name']}</div><div class="detail">{item['detail']}</div>
      <div style="margin-top:.55em;"><span class="plan-pill" style="color:var(--tc-subtle);">⏱ {dur_display}</span><span class="plan-pill" style="color:{border};">{zone}</span><span class="plan-pill" style="color:var(--tc-subtle);">TSS {tss_str}</span></div>
    </div>
    """, unsafe_allow_html=True)
            if week['wk'] % 4 == 0 and phase != 'taper':
                st.info("第 4 周为减量/吸收周:总量下降,保留轻刺激。状态好可安排 FTP 小测试;状态差就只做恢复和 Z2。")
            if week['wk'] == 1 and cycle_status and isinstance(cycle_status, str) and '经期' in cycle_status:
                st.info("🩸 本周正值经期:可以练,但建议把高强度课后移或降一级执行。恢复优先。")

    # Workout export helpers are defined above before plan TSS calculation,
    # so the page and exported files use the same structured-block TSS口径.
    st.divider()
    st.subheader("📥 导出训练课文件")
    import os as _os, io as _io, zipfile as _zipfile
    DEPLOY_MODE = os.environ.get("TRUECADENCE_DEPLOY_MODE", "local").lower()
    export_format_options = {
        "Intervals.icu / Zwift .ZWO": "zwo",
        "ERG 功率训练台 / Intervals 备选 .ERG": "erg",
        "MRC 百分比课程 / Intervals 备选 .MRC": "mrc",
    }
    selected_export_labels = st.multiselect(
        "选择导出格式",
        list(export_format_options.keys()),
        default=["Intervals.icu / Zwift .ZWO", "ERG 功率训练台 / Intervals 备选 .ERG"],
        help="Intervals.icu 用户优先试 ZWO;如果导入器变灰或不识别,再试 ERG/MRC。Z2/长距离/恢复课已拆成热身-主训练-放松多段,比单段稳态更兼容。",
        key="workout_export_format_select_v1",
    )
    selected_formats = [export_format_options[x] for x in selected_export_labels]
    all_workouts = []
    for week in all_weeks:
        for item in week['rows']:
            export_item = workout_exports_for_item(week['wk'], item, ftp)
            if export_item: all_workouts.append(export_item)
    export_files = []
    for export_item in all_workouts:
        for fmt in selected_formats:
            fname, content = export_item[fmt]
            export_files.append((export_item['week'], export_item['day'], export_item['name'], fname, content))

    if DEPLOY_MODE == "server":
        zip_buf = _io.BytesIO()
        with _zipfile.ZipFile(zip_buf, "w", compression=_zipfile.ZIP_DEFLATED) as zf:
            for wk, day, name, fname, content in export_files:
                zf.writestr(fname, content)
        st.download_button(
            f"📦 下载 {len(export_files)} 个训练文件 ZIP",
            data=zip_buf.getvalue(),
            file_name="TrueCadence_Workouts.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True,
            key="workout_export_zip_download_server_v2",
            disabled=not export_files,
        )
        st.caption("服务器内测版:训练文件会按所选格式打包成 ZIP 下载。Intervals.icu 优先试 ZWO;如文件选择器灰色,再试 ERG/MRC。")
    else:
        export_dir = _os.path.expanduser("~/Documents/TrueCadence/Workouts")
        _os.makedirs(export_dir, exist_ok=True)
        col_export, col_path = st.columns([1,2])
        with col_export:
            if st.button(f"📥 生成 {len(export_files)} 个训练文件", type="primary", key="workout_export_all_v3", disabled=not export_files):
                for wk, day, name, fname, content in export_files:
                    with open(_os.path.join(export_dir, fname), "w", encoding="utf-8") as f: f.write(content)
                st.success(f"已生成 {len(export_files)} 个训练文件")
                if hasattr(_os, "startfile"):
                    _os.startfile(export_dir)
        with col_path:
            st.caption(f"文件会直接写入:`{export_dir}`")
            st.caption("页面显示的课表和导出的训练文件使用同一份数据。Intervals.icu 优先试 ZWO;如变灰,试 ERG/MRC。FIT Workout / GPX 后续单独适配。")
    with st.expander("查看将生成的训练文件", expanded=False):
        for wk, day, name, fname, _content in export_files:
            st.caption(f"Week {wk}|{day}|{name} → {fname}")

    st.divider()
    st.caption("补给方案 →「🍝 营养与补给」| 恢复 →「🛌 恢复与睡眠」| 每 4 周更新 FTP")
