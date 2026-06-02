from __future__ import annotations

import datetime

import pandas as pd
import streamlit as st

from ui_components import (
    render_empty_data_state,
    render_power_dashboard_top_metrics,
    render_power_ftp_reference,
    render_power_profile_and_durability,
    render_training_load_guidance,
    render_training_load_styles,
    render_training_load_summary,
)


def render_power_dashboard_page(
    *,
    select_ride_scope,
    merge_rides,
    load_historical,
    enrich_rides,
    load_profile,
    estimate_ftp,
    calculate_power_zones,
    hr_zones_by_max,
    hr_zones_by_lthr,
    plot_power_curve,
    estimate_best_powers,
    calculate_fatigue_resistance,
    summarize_durability,
    ftp_wkg_bucket,
    peer_samples_for_bucket,
    record_power_profile_sample,
    power_profile_rating_rows,
    apply_power_exclusions_to_rides,
    render_power_exclusion_manager,
    estimate_ftp_explain,
    data_scope_caption,
    POWER_PROFILE_MIN_PEER_SAMPLES,
):
    st.title("📊 功率仪表盘")
    st.caption("功率曲线、区间、疲劳抗性一览")

    uploaded_rides, historical, use_all, rides, source_label = select_ride_scope(
        "合并全历史数据",
        key="power_use_all",
        help_text="开启=上传文件+历史数据一起分析;关闭=只看本次上传文件。",
    )

    rides.sort(key=lambda x: x['date'])
    rides = enrich_rides(rides)

    if not rides:
        render_empty_data_state(
            "还没有可分析的骑行数据",
            "功率仪表盘需要 FIT 数据才能计算 FTP、功率曲线、功率区间和疲劳抗性。建议先上传最近 4-12 周的 FIT 文件;如果你已经知道实测 FTP,也先在骑手档案里填好。",
            ["填写骑手档案里的体重、实测 FTP 和最大心率", "上传最近 4-12 周 FIT 文件", "回到功率仪表盘查看 FTP、功率曲线和区间"]
        )
        st.stop()

    st.caption(data_scope_caption(rides, historical, uploaded_rides, source_label))
    power_exclusions = render_power_exclusion_manager(rides)
    rides = apply_power_exclusions_to_rides(rides, power_exclusions)
    excluded_window_count = sum(len(r.get('power_exclude_durations') or []) for r in rides)
    if excluded_window_count:
        st.info(f"已从功率画像/峰值曲线中排除 {excluded_window_count} 个异常峰值窗口；原始 FIT 和历史记录未改写。")

    profile = load_profile()
    pweight = profile.get('weight', 69)

    ftp_detail = estimate_ftp_explain(rides)
    est_ftp = ftp_detail.get("ftp") or estimate_ftp(rides)
    actual_ftp = profile.get('ftp_test', 0)
    ftp = actual_ftp if actual_ftp > 0 else est_ftp

    best = estimate_best_powers(rides, ftp)

    user_for_sample = st.session_state.get("user") or {}
    rider_for_sample = st.session_state.get("rider", "默认骑手")
    record_power_profile_sample(
        user_for_sample.get("user_id", "local"),
        rider_for_sample,
        best,
        ftp,
        pweight,
        "manual_ftp" if actual_ftp > 0 else "estimated_ftp",
    )

    render_power_ftp_reference(actual_ftp, est_ftp, ftp, pweight, ftp_detail, best)

    # Top metrics - uniform cards
    render_power_dashboard_top_metrics(ftp, pweight, best, len(rides))

    # Power curve
    st.subheader("功率持续时间曲线")
    st.plotly_chart(plot_power_curve(best, ftp), use_container_width=True)

    # Power zones table
    if ftp:
        st.subheader("🏷️ 功率区间 - 练什么功率代表练什么能力")
        profile_hr_method = profile.get('hr_zone_method', '按最大心率')
        lthr = profile.get('lthr', 0) or 0
        max_hr = profile.get('max_hr', 0) or 0
        hr_rows = hr_zones_by_lthr(lthr) if profile_hr_method == "按乳酸阈值心率 LTHR" and lthr else hr_zones_by_max(max_hr)
        hr_map = {}
        if len(hr_rows) >= 5:
            hr_map = {
                'Z1 Active Recovery': hr_rows[0].get('心率范围', ''),
                'Z2 Endurance': hr_rows[1].get('心率范围', ''),
                'Z3 Tempo': hr_rows[2].get('心率范围', ''),
                'Z4 Sweet Spot': f"{hr_rows[2].get('心率范围', '')} 至 {hr_rows[3].get('心率范围', '')}",
                'Z5 Threshold': hr_rows[3].get('心率范围', ''),
                'Z6 VO2max': hr_rows[4].get('心率范围', ''),
                'Z7 Anaerobic': hr_rows[4].get('心率范围', ''),
            }
        zone_desc = {
            'Z1 Active Recovery': '恢复骑、热身放松、排乳酸',
            'Z2 Endurance': '有氧耐力、脂肪氧化、基础量',
            'Z3 Tempo': '节奏耐力、提升有氧效率',
            'Z4 Sweet Spot': '甜区、FTP基础、性价比高',
            'Z5 Threshold': '阈值、提升FTP和乳酸清除',
            'Z6 VO2max': '最大摄氧量、爬坡/追击能力',
            'Z7 Anaerobic': '无氧容量、冲刺和短坡爆发',
        }
        zone_duration = {
            'Z1 Active Recovery': '20-60min 连续',
            'Z2 Endurance': '60-180min 连续,新手先45-90min',
            'Z3 Tempo': '10-30min×2-3组',
            'Z4 Sweet Spot': '12-30min×2-4组',
            'Z5 Threshold': '8-20min×2-4组',
            'Z6 VO2max': '3-5min×3-6组',
            'Z7 Anaerobic': '30s-2min×4-8组',
        }
        zone_rest = {
            'Z1 Active Recovery': '不需要组间休息',
            'Z2 Endurance': '不需要;可每45-60min补给/放松2-5min',
            'Z3 Tempo': '组间轻松骑5-8min',
            'Z4 Sweet Spot': '组间轻松骑5-10min',
            'Z5 Threshold': '组间轻松骑5-10min;新手可接近工作时长1:1',
            'Z6 VO2max': '组间轻松骑等时长或略长,约3-6min',
            'Z7 Anaerobic': '组间充分恢复,约2-5min;冲刺课可3-8min',
        }
        zone_cadence = {
            'Z1 Active Recovery': '85-100rpm,自然轻松',
            'Z2 Endurance': '85-95rpm;新手先稳定80-95rpm',
            'Z3 Tempo': '80-95rpm,保持圆顺',
            'Z4 Sweet Spot': '85-95rpm;爬坡可75-90rpm',
            'Z5 Threshold': '85-100rpm;爬坡不低于75rpm为宜',
            'Z6 VO2max': '95-105rpm,避免低踏频硬顶',
            'Z7 Anaerobic': '100-120rpm冲刺/高踏频;低踏频力量课需谨慎',
        }
        zone_data = []
        zones = calculate_power_zones(ftp)
        for name, (lo, hi) in zones.items():
            zone_data.append({
                '区间': name,
                '功率': f"{lo}-{hi}W",
                '参考心率': hr_map.get(name, '先在骑手档案填写最大心率/LTHR'),
                '练什么': zone_desc.get(name, ''),
                '建议时长': zone_duration.get(name, ''),
                '组间休息': zone_rest.get(name, ''),
                '踏频建议': zone_cadence.get(name, ''),
            })
        _zone_df = pd.DataFrame(zone_data).astype(str)
        st.dataframe(_zone_df, use_container_width=True, hide_index=True,
                     column_config={'区间': '区间', '功率': '功率', '参考心率': '参考心率', '练什么': '练什么', '建议时长': '建议时长', '组间休息': '组间休息', '踏频建议': '踏频建议'})
        st.caption("心率是辅助参照,不替代功率:高温、睡眠、咖啡因、脱水和疲劳都会让心率漂移。若同一稳定功率下,后半程心率比前半程高出约10%以上,通常提示有氧基础/耐热/补给或恢复需要关注。")

    # Power profile fixed reference + peer percentile display
    current_bucket = ftp_wkg_bucket(ftp, pweight)
    peer_samples = peer_samples_for_bucket(current_bucket)
    fatigue = calculate_fatigue_resistance(rides, ftp, best, pweight, peer_samples=peer_samples)
    durability_summary = summarize_durability(rides)
    if fatigue:
        profile_rows = power_profile_rating_rows(fatigue)
        render_power_profile_and_durability(
            fatigue,
            durability_summary,
            profile_rows,
            len(peer_samples),
            POWER_PROFILE_MIN_PEER_SAMPLES,
            len(rides),
        )



def render_training_load_page(
    *,
    select_ride_scope,
    merge_rides,
    load_historical,
    enrich_rides,
    load_profile,
    compute_daily_pmc,
    plot_pmc,
    tsb_zone_text,
    load_feedback,
    data_scope_caption,
):
    st.title("📈 训练负荷")
    st.caption("判断最近练得是太少、刚好,还是太猛。")

    render_training_load_styles()

    uploaded_rides = st.session_state.get('uploaded_rides', [])
    historical = load_historical()
    has_current_upload = bool(uploaded_rides)
    use_all = st.toggle(
        "默认合并历史数据(推荐)",
        value=True,
        key="load_use_all",
        disabled=not has_current_upload,
        help=(
            "训练负荷应优先看历史累计趋势。开启=历史数据+本次上传一起看;关闭=仅临时查看本次上传文件。"
            if has_current_upload else
            "当前没有本次上传文件;重启/刷新会清空临时上传态,已保存的 FIT 会进入历史存档。"
        ),
    )
    if use_all:
        rides = merge_rides(historical, uploaded_rides)
        source_label = "合并历史 + 本次上传" if uploaded_rides else "历史数据"
    elif uploaded_rides:
        rides = uploaded_rides
        source_label = "仅本次上传(临时查看)"
    else:
        rides = historical
        source_label = "历史数据"

    rides.sort(key=lambda x: x.get('date', ''))
    rides = enrich_rides(rides)

    if not rides:
        render_empty_data_state(
            "训练负荷需要先有 FIT 历史",
            "CTL、ATL、TSB 都基于 TSS 计算。上传 FIT 后,系统会按自然日计算 PMC;即使后面几天没有训练,也会按 TSS=0 自然回落到今天。",
            ["上传至少 1 条带训练负荷的 FIT", "建议上传最近 4-12 周,让 CTL/ATL 更稳定", "回到训练负荷页查看疲劳、状态和风险提示"]
        )
        st.stop()

    st.caption(data_scope_caption(rides, historical, uploaded_rides, source_label))
    if uploaded_rides and use_all:
        st.success("训练负荷已按「历史数据 + 本次上传」合并计算；单次训练只作为历史负荷的一部分，不再孤立判断。")
    elif uploaded_rides and not use_all:
        st.warning("当前只看本次上传文件,适合临时排查;训练负荷、CTL/ATL/TSB 的正式判断建议打开「合并历史数据」。")
    elif not uploaded_rides:
        st.info("当前没有本次上传文件,训练负荷只能读取历史存档。若要临时查看某一批 FIT,请重新上传后再关闭合并历史数据。")

    today = pd.Timestamp.today().normalize()
    today_str = today.strftime("%Y-%m-%d")
    df_raw = pd.DataFrame(rides).sort_values('date')
    df_raw['date_dt'] = pd.to_datetime(df_raw['date'], errors='coerce').dt.normalize()
    df_raw['duration_h'] = pd.to_numeric(df_raw.get('dur', 0), errors='coerce').fillna(0) / 60
    df_pmc = compute_daily_pmc(rides)
    latest_date = df_pmc['date_dt'].max() if not df_pmc.empty else pd.NaT
    latest_ride_date = df_raw['date_dt'].dropna().max() if 'date_dt' in df_raw.columns else pd.NaT
    latest_ride_gap_days = int((today - latest_ride_date).days) if pd.notna(latest_ride_date) else None
    has_today_ride = bool(pd.notna(latest_ride_date) and latest_ride_date == today)

    current_ctl = int(df_pmc.iloc[-1]['ctl']) if not df_pmc.empty else 0
    current_atl = int(df_pmc.iloc[-1]['atl']) if not df_pmc.empty else 0
    current_tsb = int(df_pmc.iloc[-1]['tsb']) if not df_pmc.empty else 0
    ctl_series = df_pmc['ctl'].tolist() if not df_pmc.empty else [0]

    if pd.isna(latest_date):
        recent_7 = df_raw.tail(7)
        recent_28 = df_raw.tail(28)
        recent_42 = df_raw.tail(42)
    else:
        recent_7 = df_raw[df_raw['date_dt'] >= latest_date - pd.Timedelta(days=6)]
        recent_28 = df_raw[df_raw['date_dt'] >= latest_date - pd.Timedelta(days=27)]
        recent_42 = df_raw[df_raw['date_dt'] >= latest_date - pd.Timedelta(days=41)]

    tss_7 = round(recent_7.get('tss', pd.Series(dtype=float)).fillna(0).sum()) if len(recent_7) else 0
    tss_28 = round(recent_28.get('tss', pd.Series(dtype=float)).fillna(0).sum()) if len(recent_28) else 0
    tss_42 = round(recent_42.get('tss', pd.Series(dtype=float)).fillna(0).sum()) if len(recent_42) else 0
    hours_7 = round(recent_7.get('duration_h', pd.Series(dtype=float)).fillna(0).sum(), 1) if len(recent_7) else 0
    hours_28 = round(recent_28.get('duration_h', pd.Series(dtype=float)).fillna(0).sum(), 1) if len(recent_28) else 0
    hours_42 = round(recent_42.get('duration_h', pd.Series(dtype=float)).fillna(0).sum(), 1) if len(recent_42) else 0
    avg_weekly_hours = round(hours_28 / 4, 1)
    ctl_7_days_ago = df_pmc.iloc[-8]['ctl'] if len(df_pmc) >= 8 else df_pmc.iloc[0]['ctl'] if not df_pmc.empty else 0
    ramp_rate = current_ctl - ctl_7_days_ago
    valid_dates = df_raw['date_dt'].dropna()
    data_span_days = max(1, int((valid_dates.max() - valid_dates.min()).days) + 1) if len(valid_dates) else len(df_raw)
    upload_tss = round(sum(float(r.get('tss', 0) or 0) for r in uploaded_rides)) if uploaded_rides else 0
    history_tss = round(sum(float(r.get('tss', 0) or 0) for r in historical)) if historical else 0
    latest_ride_tss = round(float(df_raw.sort_values('date_dt').tail(1).get('tss', pd.Series([0])).iloc[0] or 0)) if len(df_raw) else 0

    feedback = load_feedback()
    todays_feedback = []
    stale_feedback = []
    for item in feedback:
        d = pd.to_datetime(item.get('date'), errors='coerce')
        if pd.notna(d) and d.normalize() == today:
            todays_feedback.append(item)
        elif pd.notna(d) and d.normalize() < today:
            stale_feedback.append(item)
    recent_feedback = sorted(todays_feedback, key=lambda x: (x.get('date', ''), x.get('created_at', '')), reverse=True)
    stale_feedback = sorted(stale_feedback, key=lambda x: (x.get('date', ''), x.get('created_at', '')), reverse=True)
    avg_fatigue = None
    avg_sleep = None
    avg_energy = None
    pain_items = []
    special_items = []
    if recent_feedback:
        def avg_key(k):
            vals = [x.get(k) for x in recent_feedback if isinstance(x.get(k), (int, float))]
            return round(sum(vals) / len(vals), 1) if vals else None
        avg_fatigue = avg_key('leg_fatigue')
        avg_sleep = avg_key('sleep_quality')
        avg_energy = avg_key('energy')
        for item in recent_feedback:
            pain_items.extend(item.get('pains', []) or [])
            special_items.extend(item.get('specials', []) or [])

    # Adaptive load-risk thresholds: keep safety for beginners/recovery goals,
    # but avoid over-warning trained riders during normal build blocks.
    profile = load_profile()
    goal_text = str(profile.get('goal') or '')
    notes_text = str(profile.get('notes') or '')
    exp_years = profile.get('exp_years') or 0
    try:
        exp_years = float(exp_years)
    except Exception:
        exp_years = 0
    intent_text = goal_text + ' ' + notes_text

    conservative_keywords = ['恢复', '重建', '减脂', '减重', '休闲', '健康', '新手', '刚开始']
    performance_keywords = ['提升', 'FTP', '功体比', '备赛', '比赛', '绕圈', '爬坡', '冲刺', '竞赛', '训练计划']

    if any(k in intent_text for k in conservative_keywords) or exp_years <= 1:
        risk_mode = '保守'
        risk_desc = '新手/恢复/减脂目标,提前提醒,优先安全。'
        thresholds = dict(tsb_red=-25, tsb_caution=-12, fresh=15,
                          atl_red=20, atl_caution=10, ramp_fast=8, ramp_drop=-5,
                          fatigue_red=4.0, fatigue_caution=3.3, sleep_red=2.5)
    elif any(k in intent_text for k in performance_keywords) or exp_years >= 3:
        risk_mode = '进阶'
        risk_desc = '规律训练/备赛目标,允许一定负荷积累。'
        thresholds = dict(tsb_red=-35, tsb_caution=-18, fresh=20,
                          atl_red=30, atl_caution=15, ramp_fast=12, ramp_drop=-7,
                          fatigue_red=4.3, fatigue_caution=3.7, sleep_red=2.2)
    else:
        risk_mode = '标准'
        risk_desc = '普通规律训练,兼顾训练刺激和恢复风险。'
        thresholds = dict(tsb_red=-30, tsb_caution=-15, fresh=18,
                          atl_red=25, atl_caution=12, ramp_fast=10, ramp_drop=-6,
                          fatigue_red=4.2, fatigue_caution=3.5, sleep_red=2.3)

    red_flags = []
    caution_flags = []
    good_flags = []
    good_flags.append(f"风险档位:{risk_mode}({risk_desc})")

    if current_tsb < thresholds['tsb_red']:
        red_flags.append(f"TSB {current_tsb},近期疲劳明显压过体能")
    elif current_tsb < thresholds['tsb_caution']:
        caution_flags.append(f"TSB {current_tsb},适合降一点强度")
    elif current_tsb > thresholds['fresh']:
        caution_flags.append(f"TSB {current_tsb},状态很新鲜;如果不是比赛/测试期,可能训练刺激偏少")
    else:
        good_flags.append("TSB 在可训练区间,整体状态可控")

    atl_gap = current_atl - current_ctl
    if atl_gap > thresholds['atl_red']:
        red_flags.append(f"ATL 高于 CTL {round(atl_gap)},最近训练冲得比较猛")
    elif atl_gap > thresholds['atl_caution']:
        caution_flags.append(f"ATL 高于 CTL {round(atl_gap)},近期疲劳正在累积")

    if ramp_rate > thresholds['ramp_fast']:
        caution_flags.append(f"CTL 近 7 天约 +{round(ramp_rate)},加量速度偏快")
    elif ramp_rate < thresholds['ramp_drop']:
        caution_flags.append(f"CTL 近 7 天约 {round(ramp_rate)},训练连续性有下滑")
    else:
        good_flags.append("近期训练负荷变化比较平稳")

    if avg_fatigue and avg_fatigue >= thresholds['fatigue_red']:
        red_flags.append(f"主观腿疲劳 {avg_fatigue}/5 偏高")
    elif avg_fatigue and avg_fatigue >= thresholds['fatigue_caution']:
        caution_flags.append(f"主观腿疲劳 {avg_fatigue}/5,强度课要谨慎")
    if avg_sleep and avg_sleep <= thresholds['sleep_red']:
        red_flags.append(f"睡眠评分 {avg_sleep}/5 偏低")
    if '感冒/发烧' in special_items or '生病' in special_items:
        red_flags.append("反馈里出现感冒/发烧/生病,暂停高强度")
    if pain_items:
        caution_flags.append("近期有不适记录:" + "、".join(sorted(set(pain_items))[:5]))

    if not use_all and uploaded_rides:
        status_label = "单次上传预览,不作正式负荷结论"
        status_tone = "当前关闭了合并历史,只按本次上传文件临时查看;CTL/ATL/TSB 和下面建议都只反映本次上传视角。"
        action_items = [
            "把这里当作单次/本批 FIT 排查:看这次训练的 TSS、时长和功率是否合理。",
            "不要用关闭合并后的结果安排未来一周训练;正式负荷判断请打开合并历史数据。",
            "如果本次上传是很久以前的 FIT,它只说明当时那次训练,不代表今天状态。",
        ]
    elif red_flags:
        status_label = "恢复优先,别硬顶"
        status_tone = "今天记录和训练负荷提示风险偏高。"
        action_items = ["今天优先 Z1/Z2 或完全休息", "暂停 VO2、阈值、冲刺等高强度", "先把睡眠、补水、碳水和疼痛处理好", "连续 2-3 天观察腿疲劳和晨脉变化"]
    elif caution_flags:
        status_label = "适度疲劳,控制强度"
        status_tone = "可以训练,但不适合连续堆强度。"
        action_items = ["保留 1 个关键训练,其余用 Z2/恢复骑承接", "如果腿沉或睡眠差,把强度课改成耐力骑", "下一次关键课前至少留 24-48 小时恢复窗口"]
    elif current_ctl < 25 and tss_7 < 250:
        status_label = "刺激不足,需要建立规律"
        status_tone = "当前训练压力不高,更重要的是稳定频率。"
        action_items = ["先做到每周 3-4 次规律骑行", "以 Z2 为主,逐步增加单次时长", "不要急着堆 VO2,先把基础做起来"]
    else:
        status_label = "负荷合理,可以正常推进"
        status_tone = "体能、疲劳和状态处在相对健康的训练区间。"
        action_items = ["可以按计划进行关键训练", "高强度后安排 1-2 天低强度承接", "继续记录训练反馈,用主观状态校准 PMC"]

    stale_notes = []
    if latest_ride_gap_days is not None and latest_ride_gap_days > 0:
        if not use_all and uploaded_rides:
            stale_notes.append(f"当前只看本次上传文件,最新 FIT 是 {latest_ride_date.strftime('%Y-%m-%d')},距离今天 {latest_ride_gap_days} 天;这是单次/本批文件预览,不代表今天训练状态。")
        else:
            stale_notes.append(f"当前最新 FIT 是 {latest_ride_date.strftime('%Y-%m-%d')},距离今天 {latest_ride_gap_days} 天;CTL/ATL/TSB 已按休息日自然衰减到今天,但不会把旧 FIT 当作今天训练。")
    if not recent_feedback and stale_feedback:
        latest_feedback_date = stale_feedback[0].get('date', '')
        stale_notes.append(f"今天({today_str})没有新的主观反馈;旧反馈最新为 {latest_feedback_date},只展示历史,不参与本页今日风险判断。")

    reasons = red_flags + caution_flags + good_flags
    reason_text = ";".join(reasons[:4]) if reasons else "训练负荷和今天记录没有明显异常。"

    render_training_load_summary(
        status_label,
        status_tone,
        reason_text,
        current_ctl,
        current_atl,
        current_tsb,
        tss_7,
        hours_7,
        tss_28,
        hours_28,
        tss_42,
        hours_42,
        avg_weekly_hours,
        ramp_rate,
        data_span_days,
        history_tss,
        upload_tss,
        latest_ride_tss,
        risk_mode,
        risk_desc,
        len(recent_feedback),
        avg_sleep,
        avg_fatigue,
        thresholds['tsb_caution'],
        thresholds['tsb_red'],
        thresholds['atl_caution'],
        thresholds['atl_red'],
        thresholds['fatigue_caution'],
        thresholds['fatigue_red'],
    )

    render_training_load_guidance(
        action_items,
        stale_notes,
        red_flags,
        caution_flags,
        use_all,
        bool(uploaded_rides),
        bool(recent_feedback),
        tsb_zone_text(current_tsb),
    )

    st.subheader("PMC 曲线")
    st.plotly_chart(plot_pmc(rides), use_container_width=True)
    st.caption("蓝线=体能 CTL · 橙线=疲劳 ATL · 柱状=状态 TSB。TSB 不是越高越好,关键看是否匹配训练阶段。")

    with st.expander("查看训练记录明细", expanded=False):
        show_cols = [c for c in ['date', 'duration_h', 'avg_power', 'normalized_power', 'tss'] if c in df_pmc.columns]
        if show_cols:
            st.dataframe(df_pmc[show_cols].tail(30).astype(str), use_container_width=True, hide_index=True)
        else:
            st.info("当前记录缺少可展示字段。")

