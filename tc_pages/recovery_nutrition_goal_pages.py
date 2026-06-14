from __future__ import annotations

import datetime
import json
import math
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from tc_pages.v2.router import render_v2_page

from ui_components import (
    render_empty_data_state,
    render_v2_decision_grid,
    render_v2_page_hero,
    render_goal_action_and_risk,
    render_goal_phase_path,
    render_goal_reassessment_notes,
    render_goal_styles,
    render_goal_verdict_summary,
    render_nutrition_feedback_adjustments,
    render_nutrition_intro,
    render_nutrition_quick_reference,
    render_nutrition_supplement_guidance,
    render_nutrition_target,
    render_nutrition_timing_guidance,
    render_recovery_action_and_feedback,
    render_recovery_advice_summary,
    render_recovery_intro,
)


def render_recovery_sleep_page(
    *,
    require_plan,
    select_ride_scope,
    merge_rides,
    load_historical,
    enrich_rides,
    compute_daily_pmc,
    load_feedback,
    summarize_recent_feedback,
    save_wearable_sleep,
    data_scope_caption,
    load_wearable_sleep,
    load_profile,
    get_effective_ftp,
    infer_cycle_status_for_date,
    summarize_recovery_inputs,
    build_recovery_advice,
):
    require_plan(2, "🛌 恢复与睡眠")
    render_v2_page("recovery")
    st.stop()

    uploaded_rides, historical, use_all, rides, source_label = select_ride_scope(
        "合并全历史数据",
        key="recovery_use_all",
        help_text="开启=上传文件+历史数据一起分析;关闭=只看本次上传文件。",
    )
    rides.sort(key=lambda x: x.get('date', ''))
    rides = enrich_rides(rides)
    st.caption(data_scope_caption(rides, historical, uploaded_rides, source_label))

    feedback = load_feedback()
    sleep_records = load_wearable_sleep()
    feedback_summary = summarize_recent_feedback(feedback)
    profile = load_profile()
    pweight = profile.get('weight', 69)
    ftp = get_effective_ftp(rides) if rides else (profile.get('ftp_test') or 0)

    recovery_summary = summarize_recovery_inputs(
        rides,
        feedback,
        sleep_records,
        profile,
        compute_daily_pmc_func=compute_daily_pmc,
        infer_cycle_status_func=infer_cycle_status_for_date,
    )
    recovery_advice = build_recovery_advice(recovery_summary, ftp=ftp)

    ctl = recovery_summary['ctl']
    atl = recovery_summary['atl']
    tsb = recovery_summary['tsb']
    weekly_h = recovery_summary['weekly_h']
    watch_sleep_hours = recovery_summary['watch_sleep_hours']
    watch_sleep_score = recovery_summary['watch_sleep_score']
    watch_hrv = recovery_summary['watch_hrv']
    avg_nap_min = recovery_summary['avg_nap_min']
    nap_refresh_count = recovery_summary['nap_refresh_count']
    nap_sluggish_count = recovery_summary['nap_sluggish_count']
    nap_records = recovery_summary['nap_records']
    pain_counts = recovery_summary['pain_counts']
    special_counts = recovery_summary['special_counts']
    cycle_counts = recovery_summary['cycle_counts']
    advice_class = recovery_advice['advice_class']
    advice_tag = recovery_advice['advice_tag']
    advice_main = recovery_advice['advice_main']
    next_action = recovery_advice['next_action']
    reasons = recovery_advice['reasons']
    stale_notes = recovery_advice['stale_notes']

    render_v2_decision_grid([
        ("TODAY", advice_tag, advice_main, True),
        ("DO", next_action, "如果 20 分钟后仍腿沉，直接收工；今天优先保留低强度活动。", False),
        ("DON'T", "别硬顶阈值 / VO2", "不是怕强度，是今天的收益风险比不高。", False),
        ("EVIDENCE", f"CTL {ctl} / ATL {atl} / TSB {tsb}", "训练负荷、睡眠和主观反馈共同决定今天是否降级。", True),
    ])

    with st.expander("恢复依据与详细反馈", expanded=False):
        render_recovery_advice_summary(
            advice_class, advice_tag, advice_main, reasons, tsb, ctl, atl, weekly_h,
            feedback_summary.get('count', 0), watch_sleep_hours, watch_sleep_score, watch_hrv,
            avg_nap_min, nap_refresh_count, nap_sluggish_count,
        )
        render_recovery_action_and_feedback(next_action, stale_notes, ftp, nap_records, feedback_summary, pain_counts, special_counts, cycle_counts, bool(feedback))

    st.divider()
    st.subheader("记录今日恢复反馈")
    st.caption("先用手动录入打通字段;后续佳明/Apple/华为/COROS 的截图 OCR、CSV 或 API 都落到这套数据里。")

    latest_sleep = sorted(sleep_records, key=lambda x: x.get("date", ""), reverse=True)[0] if sleep_records else {}
    with st.form("wearable_sleep_form"):
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            sleep_date = st.date_input("日期", value=datetime.date.today(), key="wear_sleep_date")
            sleep_source = st.selectbox("数据来源", ["手动", "佳明 Garmin", "Apple Health", "华为运动健康", "COROS", "其他"], key="wear_sleep_source")
        with sc2:
            sleep_hours = st.number_input("睡眠时长 h", 0.0, 14.0, float(latest_sleep.get("sleep_hours", 7.0) or 7.0), 0.1, key="wear_sleep_hours")
            sleep_score = st.number_input("睡眠评分", 0, 100, int(latest_sleep.get("sleep_score", 0) or 0), key="wear_sleep_score")
        with sc3:
            rest_hr = st.number_input("静息心率", 0, 120, int(latest_sleep.get("rest_hr", 0) or 0), key="wear_rest_hr")
            hrv = st.number_input("HRV", 0, 200, int(latest_sleep.get("hrv", 0) or 0), key="wear_hrv")
        with sc4:
            stress_score = st.number_input("压力分", 0, 100, int(latest_sleep.get("stress_score", 0) or 0), key="wear_stress")
            body_battery = st.number_input("Body Battery/恢复分", 0, 100, int(latest_sleep.get("body_battery", 0) or 0), key="wear_body_battery")
        st.markdown("**午睡 / 小睡(可选)**")
        nc1, nc2, nc3, nc4 = st.columns(4)
        with nc1:
            nap_minutes = st.number_input("午睡时长 min", 0, 180, int(latest_sleep.get("nap_minutes", 0) or 0), 5, key="wear_nap_minutes")
        with nc2:
            nap_quality = st.slider("午睡质量", 1, 5, int(latest_sleep.get("nap_quality", 3) or 3), key="wear_nap_quality", help="1=很差,5=很好;0分钟午睡时可忽略")
        with nc3:
            nap_after = st.selectbox("醒后状态", ["未午睡", "更困", "无变化", "更清醒"], index=["未午睡", "更困", "无变化", "更清醒"].index(latest_sleep.get("nap_after", "未午睡") if latest_sleep.get("nap_after", "未午睡") in ["未午睡", "更困", "无变化", "更清醒"] else "未午睡"), key="wear_nap_after")
        with nc4:
            nap_to_training = st.selectbox("到训练间隔", ["不训练/未知", "<30分钟", "30-90分钟", ">90分钟"], index=["不训练/未知", "<30分钟", "30-90分钟", ">90分钟"].index(latest_sleep.get("nap_to_training", "不训练/未知") if latest_sleep.get("nap_to_training", "不训练/未知") in ["不训练/未知", "<30分钟", "30-90分钟", ">90分钟"] else "不训练/未知"), key="wear_nap_to_training")
        sleep_note = st.text_input("备注", value=str(latest_sleep.get("note", "") or ""), placeholder="例如:夜醒多、午睡后清醒、饮酒、晚训、出差、戴表不准等", key="wear_sleep_note")
        submitted_sleep = st.form_submit_button("保存手表睡眠数据", type="primary")

    if submitted_sleep:
        entry = {
            "date": sleep_date.isoformat(),
            "source": sleep_source,
            "sleep_hours": float(sleep_hours),
            "sleep_score": int(sleep_score),
            "rest_hr": int(rest_hr),
            "hrv": int(hrv),
            "stress_score": int(stress_score),
            "body_battery": int(body_battery),
            "nap_minutes": int(nap_minutes),
            "nap_quality": int(nap_quality) if int(nap_minutes) > 0 else 0,
            "nap_after": nap_after if int(nap_minutes) > 0 else "未午睡",
            "nap_to_training": nap_to_training if int(nap_minutes) > 0 else "不训练/未知",
            "note": sleep_note.strip(),
            "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        sleep_records = [x for x in sleep_records if x.get("date") != entry["date"]]
        sleep_records.append(entry)
        sleep_records.sort(key=lambda x: x.get("date", ""), reverse=True)
        save_wearable_sleep(sleep_records)
        st.session_state["wearable_sleep_saved_msg"] = f"已保存 {entry['date']} 的睡眠/午睡数据。恢复判断会优先参考最近 14 天记录。"
        st.success(st.session_state["wearable_sleep_saved_msg"])

    if st.session_state.get("wearable_sleep_saved_msg") and not submitted_sleep:
        st.success(st.session_state.pop("wearable_sleep_saved_msg"))

    if sleep_records:
        show_sleep = pd.DataFrame(sleep_records[:10]).rename(columns={
            "date": "日期", "source": "来源", "sleep_hours": "夜间睡眠h", "sleep_score": "评分",
            "rest_hr": "静息心率", "hrv": "HRV", "stress_score": "压力", "body_battery": "恢复分",
            "nap_minutes": "午睡min", "nap_quality": "午睡质量", "nap_after": "醒后状态", "nap_to_training": "到训练间隔", "note": "备注"
        })
        keep_cols = [c for c in ["日期", "来源", "夜间睡眠h", "评分", "静息心率", "HRV", "压力", "恢复分", "午睡min", "午睡质量", "醒后状态", "到训练间隔", "备注"] if c in show_sleep.columns]
        st.dataframe(show_sleep[keep_cols].astype(str), use_container_width=True, hide_index=True)

        with st.expander("🗑️ 删除手表睡眠数据", expanded=False):
            sleep_dates = [x.get("date", "") for x in sleep_records if x.get("date")]
            del_date = st.selectbox("选择要删除的日期", sleep_dates, key="wear_delete_date")
            dc1, dc2 = st.columns([1, 1])
            if dc1.button("删除选中日期", key="delete_wearable_sleep_one", use_container_width=True):
                before = len(sleep_records)
                sleep_records = [x for x in sleep_records if x.get("date") != del_date]
                save_wearable_sleep(sleep_records)
                st.success(f"已删除 {del_date} 的手表睡眠数据。剩余 {len(sleep_records)} 条。")
                st.rerun()
            confirm_clear_sleep = dc2.checkbox("确认清空全部", key="confirm_clear_wearable_sleep")
            if dc2.button("清空全部手表数据", key="clear_wearable_sleep_all", use_container_width=True, disabled=not confirm_clear_sleep):
                save_wearable_sleep([])
                st.success("已清空当前骑手全部手表睡眠数据。")
                st.rerun()
    else:
        st.info("还没有手表睡眠记录。先手动录入 1 条,后面可以升级为截图识别或官方 API 自动同步。")

    st.divider()
    st.subheader("数据依据")
    st.caption(f"FIT 记录 {len(rides)} 条;训练反馈 {len(feedback)} 条;睡眠/午睡记录 {len(sleep_records)} 条。午睡只作为当日准备度修正,不直接等同夜间睡眠;CTL/ATL/TSB 基于 TSS 指数加权估算,不替代医学诊断。")
    col1, col2, col3 = st.columns(3)
    col1.metric("体能 CTL", ctl, "长期积累" if ctl < 40 else "中等" if ctl < 70 else "高")
    col2.metric("疲劳 ATL", atl, "轻" if atl < 40 else "适中" if atl < 65 else "高")
    col3.metric("状态 TSB", tsb, "好" if tsb > 10 else "正常" if tsb > -10 else "疲劳")



def render_nutrition_page(
    *,
    require_plan,
    load_profile,
    select_ride_scope,
    merge_rides,
    load_historical,
    enrich_rides,
    data_scope_caption,
    get_effective_ftp,
    load_feedback,
    summarize_recent_feedback,
    feedback_sets_from_recent_feedback,
    calculate_nutrition_targets,
    rank_supplements,
    supplement_card_context,
    APP_DIR,
):
    require_plan(2, "🍝 营养与补给")
    st.title("🍝 营养与补给")
    st.caption("不是泛泛说多吃碳水,而是按今天的训练、体重、强度和反馈,算出怎么吃、怎么喝、怎么补。")

    render_nutrition_intro()

    uploaded_rides, historical, use_all, rides, source_label = select_ride_scope(
        "合并全历史数据",
        key="nutrition_use_all",
        help_text="开启=上传文件+历史数据一起分析;关闭=只看本次上传文件。",
    )
    rides.sort(key=lambda x: x.get('date', ''))
    rides = enrich_rides(rides) if rides else []
    st.caption(data_scope_caption(rides, historical, uploaded_rides, source_label))

    profile = load_profile()
    ftp = get_effective_ftp(rides) if rides else (profile.get('ftp_test') or 0)
    pweight = profile.get('weight', 69)
    feedback = load_feedback()
    feedback_summary = summarize_recent_feedback(feedback)
    recent_feedback = sorted(feedback, key=lambda x: (x.get('date', ''), x.get('created_at', '')), reverse=True)[:5]

    special_set, fueling_set = feedback_sets_from_recent_feedback(recent_feedback)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        weight = st.number_input("体重 kg", min_value=40, max_value=120, value=int(pweight or 69), key="nut_weight_v2")
    with c2:
        ride_hours = st.slider("今天骑多久 h", 0.5, 24.0, 2.0, 0.5, key="nut_ride_hours")
    with c3:
        workout_type = st.selectbox("训练类型", ["恢复骑", "Z2 长距离", "甜区/阈值", "VO2max/间歇", "比赛/绕圈赛"], key="nut_workout_type")
    with c4:
        environment = st.selectbox("环境", ["正常", "天气太热", "天气太冷", "室内骑行"], index=1 if "天气太热" in special_set else 0, key="nut_environment")

    nutrition_targets = calculate_nutrition_targets(
        weight=weight,
        ride_hours=ride_hours,
        workout_type=workout_type,
        environment=environment,
        fueling_set=fueling_set,
        feedback_count=feedback_summary.get('count', 0),
    )
    carb_lo = nutrition_targets['carb_lo']
    carb_hi = nutrition_targets['carb_hi']
    water_lo = nutrition_targets['water_lo']
    water_hi = nutrition_targets['water_hi']
    sodium_lo = nutrition_targets['sodium_lo']
    sodium_hi = nutrition_targets['sodium_hi']
    intensity_note = nutrition_targets['intensity_note']
    total_carb_lo = nutrition_targets['total_carb_lo']
    total_carb_hi = nutrition_targets['total_carb_hi']
    total_water_lo = nutrition_targets['total_water_lo']
    total_water_hi = nutrition_targets['total_water_hi']
    total_sodium_lo = nutrition_targets['total_sodium_lo']
    total_sodium_hi = nutrition_targets['total_sodium_hi']
    pre_carb = nutrition_targets['pre_carb']
    pre_protein = nutrition_targets['pre_protein']
    post_carb = nutrition_targets['post_carb']
    post_protein = nutrition_targets['post_protein']

    render_nutrition_target(
        carb_lo,
        carb_hi,
        water_lo,
        water_hi,
        sodium_lo,
        sodium_hi,
        workout_type,
        ride_hours,
        environment,
        weight,
        intensity_note,
        total_carb_lo,
        total_carb_hi,
        total_water_lo,
        total_water_hi,
        total_sodium_lo,
        total_sodium_hi,
        feedback_summary.get('count', 0),
    )

    pre_carb = round(weight * (1.5 if ride_hours <= 2 else 2.0))
    pre_protein = round(weight * 0.3)
    post_carb = round(weight * (0.8 if workout_type == "恢复骑" else 1.2))
    post_protein = round(weight * 0.35)
    render_nutrition_timing_guidance(pre_carb, pre_protein, post_carb, post_protein)
    render_nutrition_quick_reference()

    # ─── 补剂推荐 ───
    st.subheader("🧪 推荐补剂组合")
    sup_db_path = Path(os.environ.get("TRUECADENCE_SUPPLEMENT_DB", APP_DIR / "nutrition_database" / "supplement_db.json"))
    supplements = []
    try:
        with open(sup_db_path, encoding="utf-8") as f:
            supplements = json.load(f)
    except Exception:
        pass

    if supplements:
        top = rank_supplements(supplements, environment=environment, fueling_set=fueling_set, workout_type=workout_type, limit=3)

        sup_cols = st.columns(len(top))
        for i, sup in enumerate(top):
            with sup_cols[i]:
                tags_text = " · ".join(sup.get("tags", [])[:3])
                card_ctx = supplement_card_context(sup, index=i, carb_hi=carb_hi, environment=environment, fueling_set=fueling_set, workout_type=workout_type)
                servings_needed = card_ctx["servings_needed"]
                badge = card_ctx["badge"]
                border_color = card_ctx["border_color"]
                bg_glow = card_ctx["bg_glow"]
                shadow_glow = card_ctx["shadow_glow"]
                accent_color = card_ctx["accent_color"]
                reason_text = card_ctx["reason_text"]
                st.markdown(f"""<div style="background:linear-gradient(135deg, {bg_glow}, var(--tc-surface) 72%); border:1.5px solid {border_color}; box-shadow:0 0 0 1px {shadow_glow}, 0 10px 26px rgba(0,0,0,0.16); border-radius:13px; padding:0.85em; margin:0.3em 0;">
    <div style="color:{accent_color}; font-size:0.72em; font-weight:780; letter-spacing:0.08em; margin-bottom:0.3em;">{badge}</div>
    <div style="color:#f0f6fc; font-size:1.02em; font-weight:760;">{sup['name']}</div>
    <div style="color:var(--tc-subtle); font-size:0.76em; margin-top:0.15em;">{sup['type']} · {sup['flavor']} · {sup['serving_g']}g/份</div>
    <div style="color:#aab6c3; font-size:0.82em; margin-top:0.5em; line-height:1.5;">碳水 <b>{sup['carbs_g']}g</b> · 钠 <b>{sup['sodium_mg']}mg</b> · {sup['kcal']}kcal</div>
    <div style="color:#6e7681; font-size:0.74em; margin-top:0.35em;">{tags_text}</div>
    <div style="color:{accent_color}; font-size:0.72em; margin-top:0.42em;">{reason_text}</div>
    <div style="color:var(--tc-subtle); font-size:0.74em; margin-top:0.5em; border-top:1px solid var(--tc-surface-2); padding-top:0.4em;">约需 <b>{servings_needed}</b> 份/小时</div>
    </div>""", unsafe_allow_html=True)

        render_nutrition_supplement_guidance(environment, fueling_set, workout_type)
    else:
        st.caption("补剂产品库未加载,请确认 supplement_db.json 存在。")

    render_nutrition_feedback_adjustments(fueling_set, special_set, weight, ftp, len(feedback))



def render_goal_tracking_page(
    *,
    require_plan,
    select_ride_scope,
    merge_rides,
    load_historical,
    enrich_rides,
    load_profile,
    get_effective_ftp,
    compute_daily_pmc,
    data_scope_caption,
    load_feedback,
    render_footer,
):
    require_plan(2, "🎯 目标追踪")
    st.title("🎯 目标追踪")
    st.caption("把目标拆成路径、阶段和本周动作:不是许愿,而是知道下一步怎么走。")

    render_goal_styles()

    uploaded_rides, historical, use_all, rides, source_label = select_ride_scope(
        "合并全历史数据",
        key="goal_use_all",
        help_text="开启=上传文件+历史数据一起分析;关闭=只看本次上传文件。",
    )
    rides.sort(key=lambda x: x.get('date', ''))
    rides = enrich_rides(rides)

    if not rides:
        render_empty_data_state(
            "目标追踪需要先知道当前能力",
            "系统需要 FIT 或实测 FTP 来判断当前 FTP、W/kg、训练负荷和达成目标的周期。",
            ["填写骑手档案里的体重和实测 FTP", "上传 FIT 让系统校准当前能力", "设置目标 FTP / W/kg 和目标日期"]
        )
        st.stop()

    st.caption(data_scope_caption(rides, historical, uploaded_rides, source_label))

    profile = load_profile()
    ftp = get_effective_ftp(rides)
    pweight = profile.get('weight', 69)
    feedback = load_feedback()
    recent_feedback = sorted(feedback, key=lambda x: (x.get('date', ''), x.get('created_at', '')), reverse=True)[:5]

    df = pd.DataFrame(rides).sort_values('date')
    pmc_goal = compute_daily_pmc(rides)
    ctl = int(pmc_goal.iloc[-1]['ctl']) if not pmc_goal.empty else 0
    atl = int(pmc_goal.iloc[-1]['atl']) if not pmc_goal.empty else 0
    tsb = int(pmc_goal.iloc[-1]['tsb']) if not pmc_goal.empty else 0

    avg_sleep = 0; avg_fatigue = 0; avg_energy = 0
    if recent_feedback:
        def avg_key(k):
            vals=[x.get(k) for x in recent_feedback if isinstance(x.get(k),(int,float))]
            return round(sum(vals)/len(vals),1) if vals else 0
        avg_sleep=avg_key('sleep_quality'); avg_fatigue=avg_key('leg_fatigue'); avg_energy=avg_key('energy')

    col1, col2, col3 = st.columns(3)
    with col1:
        goal_type = st.selectbox("目标类型", ["提升 FTP", "提升 W/kg", "减脂不掉功率", "比赛备战", "长距离耐力", "恢复体能"], key="goal_type_v2")
    with col2:
        weight = st.number_input("体重 kg", value=int(pweight or 69), min_value=40, max_value=120, key="goal_weight_v2")
    with col3:
        weekly_h = st.number_input("每周稳定可练 h", value=8, min_value=2, max_value=25, step=1, key="goal_weekly_h_v2")

    target_ftp_default = ftp + 30 if ftp < 250 else ftp + 15
    target_wkg_default = round(target_ftp_default / weight, 1) if weight else 3.5
    c4, c5, c6 = st.columns(3)
    with c4:
        if goal_type in ["提升 W/kg", "减脂不掉功率"]:
            target_wkg = st.number_input("目标 W/kg", value=float(target_wkg_default), min_value=1.5, max_value=7.0, step=0.1, key="goal_target_wkg")
            target_ftp = round(target_wkg * weight)
        else:
            target_ftp = st.number_input("目标 FTP W", value=int(target_ftp_default), min_value=100, max_value=500, step=5, key="goal_target_ftp_v2")
            target_wkg = round(target_ftp / weight, 1) if weight else 0
    with c5:
        target_weeks = st.selectbox("希望周期", ["8周", "12周", "16周", "24周"], index=1, key="goal_target_weeks")
        target_weeks_n = int(target_weeks.replace("周", ""))
    with c6:
        event_date = st.date_input("目标日期/比赛日", value=datetime.date.today() + datetime.timedelta(days=target_weeks_n*7), key="goal_event_date")

    current_wkg = round(ftp / weight, 1) if weight else 0
    ftp_gap = target_ftp - ftp
    wkg_gap = round(target_wkg - current_wkg, 1)

    if weekly_h < 4:
        weekly_gain = 1.5; capacity = "训练时间偏少"
    elif weekly_h < 7:
        weekly_gain = 3.0; capacity = "缓慢稳定"
    elif weekly_h < 10:
        weekly_gain = 4.5; capacity = "稳定进步"
    elif weekly_h < 14:
        weekly_gain = 5.5; capacity = "进步空间较好"
    else:
        weekly_gain = 6.0; capacity = "高投入,但恢复要求高"

    if current_wkg >= 4.0:
        weekly_gain = max(1.0, weekly_gain - 2.5)
        capacity += "|高阶涨功更慢"
    if goal_type == "恢复体能":
        weekly_gain = max(weekly_gain, 3.0)
    if goal_type == "减脂不掉功率":
        weekly_gain = max(1.0, weekly_gain - 1.5)

    needed_weeks = max(1, math.ceil(max(0, ftp_gap) / weekly_gain)) if ftp_gap > 0 else 1
    feasible = needed_weeks <= target_weeks_n
    risk_flags = []
    if weekly_h < 5 and ftp_gap > 25:
        risk_flags.append("每周训练时间偏少,目标涨幅较大")
    if tsb < -15:
        risk_flags.append("当前 TSB 偏低,疲劳较高")
    if avg_fatigue and avg_fatigue >= 4:
        risk_flags.append("最近腿疲劳偏高")
    if avg_sleep and avg_sleep <= 2.5:
        risk_flags.append("最近睡眠偏差")
    if goal_type == "减脂不掉功率" and weekly_h >= 10:
        risk_flags.append("减脂期训练量较高,注意能量可用性不足")

    if feasible and not risk_flags:
        verdict = "目标合理,可以推进"
        verdict_text = "以当前训练时间和状态,目标具备可执行性。关键是稳定执行,不要每周都临时改方向。"
    elif feasible and risk_flags:
        verdict = "目标可行,但要管理风险"
        verdict_text = "时间上够,但恢复、睡眠或疲劳会影响完成质量。目标不是问题,节奏管理是关键。"
    else:
        verdict = "目标偏激进,建议拆成两段"
        verdict_text = f"按当前投入估算约需 {needed_weeks} 周,而你设定的是 {target_weeks_n} 周。建议先设中间目标,再冲最终目标。"

    render_goal_verdict_summary(
        verdict,
        verdict_text,
        ftp,
        current_wkg,
        target_ftp,
        target_wkg,
        ftp_gap,
        needed_weeks,
        target_weeks_n,
        weekly_h,
        capacity,
        ctl,
        tsb,
        len(recent_feedback),
        avg_sleep,
        avg_fatigue,
        event_date,
    )

    progress = min(max(ftp / target_ftp, 0), 1) if target_ftp else 0
    st.progress(progress, f"当前进度:{round(progress*100)}%|还差 {max(0, ftp_gap)}W / {max(0, wkg_gap)} W/kg")

    phase_rows = []
    phase_count = max(1, target_weeks_n // 4)
    for i in range(1, phase_count + 1):
        wk = i * 4
        phase_target = min(target_ftp, round(ftp + weekly_gain * wk)) if ftp_gap > 0 else ftp
        if i == 1:
            focus = "建立节奏:Z2 连续性 + 1 次轻强度"
            risk = "别一开始就堆 VO2"
        elif i == phase_count:
            focus = "专项收束:接近目标强度,减少无效疲劳"
            risk = "避免最后阶段练过头"
        else:
            focus = "主要提升:阈值/甜区 + 长耐力"
            risk = "每周保留恢复窗口"
        if goal_type == "比赛备战":
            focus = "比赛专项:节奏变化、冲刺、补给演练"
        elif goal_type == "长距离耐力":
            focus = "长耐力:逐步拉长 Z2,练补给和姿势稳定"
        elif goal_type == "减脂不掉功率":
            focus = "控体重:Z2 稳定输出,强度课前后不缺碳水"
        phase_rows.append({"阶段": f"第 {max(1, wk-3)}-{wk} 周", "目标": f"FTP ~{phase_target}W / {round(phase_target/weight,1)} W/kg", "训练重点": focus, "风险提醒": risk})
    render_goal_phase_path(phase_rows)

    if weekly_h <= 4:
        actions = ["完成 3 次骑行,比单次骑很猛更重要", "全部以 Z2/轻松骑为主", "本周不要追 FTP 测试"]
    elif goal_type in ["提升 FTP", "提升 W/kg"]:
        actions = ["安排 1 次阈值/甜区质量课", "安排 1 次 2h 左右 Z2", "其余训练保持低强度,不要把恢复骑骑成强度课"]
    elif goal_type == "比赛备战":
        actions = ["安排 1 次比赛模拟或节奏变化训练", "至少 1 次补给演练", "保留 1-2 天恢复窗口"]
    elif goal_type == "长距离耐力":
        actions = ["最长单次比上周增加不超过 10-15%", "从前 20 分钟开始补给", "关注后半程功率是否明显掉"]
    elif goal_type == "减脂不掉功率":
        actions = ["不要在质量课前低碳", "用 Z2 增加能量消耗", "每周体重下降不宜过快"]
    else:
        actions = ["先恢复规律训练频率", "只做轻到中等强度", "连续 2 周稳定后再提高目标"]
    render_goal_action_and_risk(actions, risk_flags, feasible, ftp, ftp_gap, target_ftp)
    render_goal_reassessment_notes()

    st.sidebar.caption("TrueCadence v1.0")
    st.sidebar.caption(f"{datetime.date.today()}")
    if render_footer:
        render_footer()


