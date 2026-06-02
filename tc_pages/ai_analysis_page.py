from __future__ import annotations

import datetime
import json

import pandas as pd
import streamlit as st

from ui_components import (
    render_ai_analysis_styles,
    render_ai_cached_notice,
    render_ai_context_summary,
    render_ai_usage_panel,
    render_empty_data_state,
)


def render_ai_power_analysis_page(
    *,
    PLANS,
    DATA_DIR,
    get_ai_usage,
    get_ai_limit,
    increment_ai_usage,
    load_historical,
    select_ride_scope,
    enrich_rides,
    data_scope_caption,
    load_profile,
    estimate_ftp,
    load_feedback,
    summarize_recent_feedback,
    load_wearable_sleep,
    infer_cycle_status_for_date,
    estimate_best_powers,
    generate_diagnosis,
):
    st.title("🧠 AI 功率分析")
    st.caption("把骑行数据转成训练判断:当前强弱项、该练什么、什么时候该恢复。")

    render_ai_analysis_styles()

    # AI usage tracking
    uid = st.session_state.user["user_id"]
    used = get_ai_usage(uid)
    limit = get_ai_limit(uid)
    current_plan_key = st.session_state.user.get("plan", "free")
    unlimited_ai = current_plan_key in ("pro", "coach")
    remaining = None if unlimited_ai else max(0, limit - used)
    quota_text = "♾️" if unlimited_ai else f"{remaining}/{limit} 次"
    billing_rule_text = "不扣次数" if unlimited_ai else "按钮触发扣除1次"
    plan_name = PLANS[current_plan_key]["name"]

    ai_over_limit = (not unlimited_ai) and remaining <= 0
    if ai_over_limit:
        st.warning(f"🔒 本月 AI 分析次数已用完({used}/{limit})。已生成的分析结果仍可查看;只有重新生成才需要额度。")
        st.caption("在侧边栏「账户」中选择套餐并输入内测邀请码升级")

    uploaded_rides = st.session_state.get('uploaded_rides', [])
    historical = load_historical()

    render_ai_usage_panel(unlimited_ai, plan_name, quota_text, billing_rule_text)

    st.subheader("1. 选择分析数据")
    uploaded_rides, historical, use_all, rides, source_label = select_ride_scope(
        "合并全历史数据",
        key="ai_use_all",
        help_text="开启=上传文件+历史数据一起分析;关闭=只看本次上传文件。",
    )
    rides.sort(key=lambda x: x['date'])
    rides = enrich_rides(rides)

    if not rides:
        render_empty_data_state(
            "AI 分析需要先有骑行数据",
            "AI 会综合 FIT、FTP、训练反馈、睡眠和恢复记录。没有 FIT 时,系统无法判断能力结构和训练负荷。",
            ["先在骑手档案填写基础信息", "上传最近 4-12 周 FIT 文件", "补一条训练反馈后再生成 AI 分析"]
        )
        st.stop()

    st.caption(data_scope_caption(rides, historical, uploaded_rides, source_label))

    profile = load_profile()
    pweight = profile.get('weight', 69)
    actual_ftp = profile.get('ftp_test', 0)
    est_ftp = estimate_ftp(rides)
    effective_ftp = actual_ftp if actual_ftp > 0 else est_ftp

    feedback = load_feedback()
    feedback_latest = max((x.get("date", "") for x in feedback), default="")
    feedback_stamp = max((x.get("created_at", "") for x in feedback), default="")
    feedback_summary = summarize_recent_feedback(feedback)
    sleep_records = load_wearable_sleep()
    sleep_latest = max((x.get("date", "") for x in sleep_records), default="")
    sleep_stamp = max((x.get("created_at", "") for x in sleep_records), default="")
    feedback_rows = []
    if feedback:
        df_ai_fb = pd.DataFrame(feedback[:5]).copy()
        show_cols = [
            "date", "sleep_quality", "energy", "leg_fatigue", "stress", "rpe",
            "completion", "leg_feel", "fueling", "pains", "specials",
            "cycle_status", "cycle_pain", "cycle_training_impact", "notes"
        ]
        df_ai_fb = df_ai_fb[[c for c in show_cols if c in df_ai_fb.columns]].copy()
        for col in ["pains", "specials"]:
            if col in df_ai_fb.columns:
                df_ai_fb[col] = df_ai_fb[col].apply(lambda x: "、".join(x) if isinstance(x, list) and x else "无")
        rename_map = {
            "date": "日期", "sleep_quality": "睡眠", "energy": "精神", "leg_fatigue": "腿疲劳",
            "stress": "压力", "rpe": "RPE", "completion": "完成度", "leg_feel": "腿感",
            "fueling": "补给", "pains": "不适", "specials": "特殊情况",
            "cycle_status": "女性周期", "cycle_pain": "腹痛/腰酸", "cycle_training_impact": "周期影响",
            "notes": "备注"
        }
        profile_for_cycle = load_profile()
        inferred_cycles = [infer_cycle_status_for_date(item, profile_for_cycle) or "未记录" for item in feedback[:len(df_ai_fb)]]
        if "cycle_status" in df_ai_fb.columns:
            df_ai_fb["cycle_status"] = inferred_cycles
        elif "女性周期" in df_ai_fb.columns:
            df_ai_fb["女性周期"] = inferred_cycles
        df_ai_fb = df_ai_fb.rename(columns=rename_map)
        feedback_rows = df_ai_fb.to_dict(orient="records")
    render_ai_context_summary(source_label, len(rides), actual_ftp, effective_ftp, pweight, feedback_summary, feedback_latest, feedback_rows, sleep_records, sleep_latest)

    # Keep the last AI diagnosis for this exact data/profile/feedback signature.
    # This prevents page switches or refreshes from clearing the result and forcing another paid analysis.
    ai_signature = f"{len(rides)}|{feedback_latest}|{feedback_stamp}|{len(feedback)}|{sleep_latest}|{sleep_stamp}|{len(sleep_records)}|{actual_ftp}|{pweight}"
    ai_cache_file = DATA_DIR / uid / "ai_analysis_cache.json"
    cached_ai = {}
    try:
        if ai_cache_file.exists():
            with open(ai_cache_file, "r", encoding="utf-8") as f:
                cached_ai = json.load(f)
    except Exception:
        cached_ai = {}

    if st.session_state.get("ai_signature") != ai_signature:
        st.session_state.pop("ai_diagnosis", None)
        st.session_state.ai_signature = ai_signature

    if not st.session_state.get("ai_diagnosis") and cached_ai.get("signature") == ai_signature and cached_ai.get("diagnosis"):
        st.session_state.ai_diagnosis = cached_ai.get("diagnosis")
        st.session_state.ai_diagnosis_cached_at = cached_ai.get("generated_at", "")

    st.subheader("2. 生成 AI 诊断")
    st.info("AI 分析结果会自动保留:切换页面或刷新后仍可查看;只有点击「重新分析」并再次生成,才会消耗新的 AI 次数。")

    # Show persisted diagnosis if available
    if "ai_diagnosis" in st.session_state:
        cached_at = st.session_state.get("ai_diagnosis_cached_at") or cached_ai.get("generated_at", "")
        render_ai_cached_notice(cached_at, unlimited_ai)
        st.markdown(st.session_state.ai_diagnosis)
        if st.button("🔄 重新分析", key="ai_reanalyze",
                     disabled=ai_over_limit,
                     use_container_width=True,
                     help=("清除当前诊断,下一次点击开始分析也不扣次数" if unlimited_ai else ("清除当前诊断,下一次点击开始分析会重新扣 1 次" if not ai_over_limit else "本月额度已用完,暂不能重新分析"))):
            st.session_state.pop("ai_diagnosis", None)
            st.session_state.pop("ai_diagnosis_cached_at", None)
            try:
                if ai_cache_file.exists():
                    ai_cache_file.unlink()
            except Exception:
                pass
            st.rerun()
    else:
        st.caption("当前暂无已保留诊断。点击下方「🔬 开始 AI 分析」后,结果会自动保留;之后切换页面再回来会显示为「诊断已保留」。")

    # Only analyze on button click - disable after analysis
    already_analyzed = bool(st.session_state.get("ai_diagnosis"))
    if not already_analyzed:
        if unlimited_ai:
            st.caption("Pro / Coach 分析不扣次数。页面刷新、切换数据范围、查看训练一致性不会自动扣费。")
        else:
            st.caption("点击后将消耗 1 次 AI 分析额度。页面刷新、切换数据范围、查看训练一致性不会自动扣费。")
    if ai_over_limit and not already_analyzed:
        st.stop()
    if st.button("🔬 开始 AI 分析", type="primary", use_container_width=True,
                 key="ai_analyze_btn", disabled=already_analyzed,
                 help="已分析完成" if already_analyzed else ("点击开始分析,Pro / Coach 不扣次数" if unlimited_ai else "点击开始分析,会消耗 1 次 AI 额度")):
        try:
            ftp = effective_ftp
            best = estimate_best_powers(rides, ftp)

            if actual_ftp > 0:
                st.info(f"FTP: **{actual_ftp}W**" + (f"(估算: {est_ftp}W)" if abs(actual_ftp - est_ftp) > 10 else ""))
            else:
                st.info(f"估算 FTP: **{est_ftp}W**")

            result = generate_diagnosis(rides, ftp, best, pweight, feedback, sleep_records)
            st.session_state.ai_diagnosis = result
            generated_at = datetime.datetime.now().isoformat(timespec="seconds")
            st.session_state.ai_diagnosis_cached_at = generated_at
            # Persist the visible diagnosis so page switches / refreshes do not force another paid analysis.
            try:
                user_dir = DATA_DIR / uid
                user_dir.mkdir(parents=True, exist_ok=True)
                with open(ai_cache_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "signature": ai_signature,
                        "generated_at": generated_at,
                        "data_source": source_label,
                        "ride_count": len(rides),
                        "feedback_count": len(feedback),
                        "sleep_count": len(sleep_records),
                        "ftp": ftp,
                        "ftp_source": "客户填写" if actual_ftp > 0 else "FIT估算",
                        "diagnosis": result,
                    }, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            # Persist a structured AI context so the training-plan page can actually read it.
            try:
                ai_ctx = {
                    "generated_at": generated_at,
                    "ftp": ftp,
                    "ftp_source": "客户填写" if actual_ftp > 0 else "FIT估算",
                    "weight": pweight,
                    "wkg": round(ftp / pweight, 1) if ftp and pweight else 0,
                    "data_source": source_label,
                    "ride_count": len(rides),
                    "feedback_count": len(feedback),
                    "feedback_last_date": feedback_latest,
                    "feedback_risk_flags": feedback_summary.get("risk_flags", []),
                    "feedback_lines": feedback_summary.get("lines", []),
                    "sleep_count": len(sleep_records),
                    "sleep_last_date": sleep_latest,
                    "sleep_recent": sleep_records[:7],
                    "diagnosis_excerpt": result[:1200],
                }
                user_dir = DATA_DIR / uid
                user_dir.mkdir(parents=True, exist_ok=True)
                with open(user_dir / "ai_training_plan_context.json", "w", encoding="utf-8") as f:
                    json.dump(ai_ctx, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            increment_ai_usage(uid)
            st.rerun()
        except Exception as e:
            st.error(f"诊断生成失败: {e}")

    st.subheader("3. 训练一致性")
    st.caption("这部分只根据数据统计,不消耗 AI 次数。")
    try:
        df = pd.DataFrame(rides)
        df['date_dt'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date_dt'])
        if df.empty:
            st.warning("没有有效日期的骑行数据")
        else:
            df['week'] = df['date_dt'].dt.isocalendar().week
            df['year'] = df['date_dt'].dt.isocalendar().year
            weekly = df.groupby(['year', 'week']).agg(n=('date', 'count'), h=('dur', 'sum')).reset_index()
            weekly['h'] = round(weekly['h'] / 60, 1)
            recent_weekly = weekly.tail(12)
            c1, c2 = st.columns([1, 3])
            if len(recent_weekly) >= 4:
                weeks_rode = sum(1 for h in recent_weekly['h'] if h > 0)
                consistency = round(weeks_rode / len(recent_weekly) * 100)
                c1.metric("近12周训练率", f"{consistency}%",
                         "优秀" if consistency >= 80 else ("良好" if consistency >= 60 else "待提升"))
            c2.dataframe(weekly.sort_values(['year', 'week'], ascending=False).head(12).astype(str),
                         use_container_width=True, hide_index=True, height=280,
                         column_config={'year': '年', 'week': '周', 'n': '次数', 'h': '小时'})
    except Exception as e:
        st.error(f"训练一致性计算失败: {e}")

