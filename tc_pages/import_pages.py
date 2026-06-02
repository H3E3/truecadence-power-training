from __future__ import annotations

import datetime
import os

import pandas as pd
import streamlit as st

from services.fit_processing import NamedBytesFile
from ui_components import (
    render_empty_data_state,
    render_intervals_manual_import_note,
    render_intervals_oauth_import_note,
    render_strava_export_note,
    render_upload_cta_note,
    render_upload_intro,
    render_upload_next_steps,
)


def render_upload_analysis_page(
    *,
    parse_fit_files,
    enrich_rides,
    load_historical,
    merge_rides,
    save_current_rides,
    render_upload_quick_diagnosis,
    load_profile,
):
    st.title("📤 上传分析")
    st.caption("上传码表、骑行台或训练平台导出的 FIT 文件,系统会自动解析功率、心率和训练负荷。")

    render_upload_intro()

    with st.expander("📁 从哪里导出 FIT 文件?", expanded=True):
        st.markdown("""
    **推荐准备:**最近 4-12 周、有功率数据的 FIT 文件。一次最多上传 28 个;历史摘要会长期保存;同日期新上传会覆盖旧记录。

    **常见导出方式:**
    - **Garmin Connect / 佳明:**进入一次骑行活动 → 右上角更多/齿轮 → 导出原始数据 / Export Original → 得到 `.fit` 文件。
    - **Zwift:**登录 Zwift 活动页面 → 选择对应骑行 → 下载 FIT 文件;也可从本机 `Documents/Zwift/Activities` 找到 `.fit`。
    - **Wahoo / ELEMNT:**活动详情里选择分享/导出,优先选择 FIT 原始文件。
    - **COROS / 其他码表:**活动详情 → 导出数据 → 选择 FIT。若只有 `.tcx/.gpx`,功率和 TSS 可能不完整。
    - **骑行台平台:**优先从训练平台活动详情下载 FIT,而不是截图或 CSV。

    **上传建议:**先上传最近 28 个 FIT 看结果;如果需要补更早的数据,再分批上传。系统会自动去重合并。
    """)

    st.info("🔐 数据说明:内测阶段上传的 FIT 原始文件最多保留 48 小时;系统会保存解析后的训练摘要用于分析、课表和历史趋势。你的数据不会公开展示。")

    render_upload_cta_note()

    uploaded = st.file_uploader(
        "📂 选择或拖拽 FIT 文件",
        type=['fit'],
        accept_multiple_files=True,
        key="fit_file_uploader",
        help="从码表、骑行台或训练平台导出的 .fit 文件。历史摘要会长期保存;为保证稳定,一次最多上传 28 个,单次总大小最多 50MB。网络不稳定或使用代理时,建议每批 5-10 个。"
    )

    MAX_FIT_UPLOADS = 28
    MAX_TOTAL_UPLOAD_MB = 50
    if uploaded and len(uploaded) > MAX_FIT_UPLOADS:
        st.error(f"一次最多上传 {MAX_FIT_UPLOADS} 个 FIT 文件。你当前选择了 {len(uploaded)} 个,请分批上传。")
        st.info("建议按时间顺序分批上传:网络不稳定时每批 5-10 个更稳;例如先传最近一批,保存后再上传更早的数据。历史摘要会长期保存;同日期新上传会覆盖旧记录,系统也会按文件指纹/记录去重。")
        st.stop()
    if uploaded:
        total_bytes = sum(getattr(f, "size", 0) or 0 for f in uploaded)
        total_mb = total_bytes / 1024 / 1024
        if total_mb > MAX_TOTAL_UPLOAD_MB:
            st.error(f"本次文件总大小约 {total_mb:.1f}MB,超过单次 {MAX_TOTAL_UPLOAD_MB}MB 限制。请分批上传。")
            st.info("建议先上传最近 4-12 周内最关键的一批 FIT;如果文件很多,可按月份或按最近/更早分批上传。网络不稳定时每批 5-10 个更稳。")
            st.stop()

    if not uploaded:
        render_empty_data_state(
            "选择 FIT 文件开始建立训练画像",
            "建议一次上传最近 4-12 周的 FIT 文件。数据越完整,FTP 估算、训练负荷、疲劳抗性和 AI 诊断越稳定。",
            ["展开上方说明,从码表 / Zwift / 训练平台导出 .fit 文件", "一次最多选择 28 个;网络不稳定时建议每批 5-10 个,系统会自动去重合并", "上传后先看功率仪表盘和训练负荷"]
        )
        st.stop()

    current_fit_sig = tuple((getattr(f, "name", ""), getattr(f, "size", 0) or 0) for f in (uploaded or []))
    st.session_state["fit_upload_busy"] = True
    with st.spinner(f"正在解析 {len(uploaded)} 个文件..."):
        new_rides = parse_fit_files(uploaded)
    st.session_state["last_fit_upload_sig"] = current_fit_sig
    st.session_state["fit_upload_busy"] = False

    if new_rides:
        # Fill missing NP and TSS from available data
        new_rides = enrich_rides(new_rides)
        st.success(f"✅ 解析完成:获取 {len(new_rides)} 条骑行记录")
        parse_total = st.session_state.get("last_fit_parse_total_seconds")
        parse_timings = st.session_state.get("last_fit_parse_timings") or []
        cached_count = sum(1 for item in parse_timings if item.get("cached"))
        if parse_total is not None and parse_timings:
            detail = f"解析耗时:{parse_total:.2f}s|缓存命中 {cached_count}/{len(parse_timings)}"
            slow_items = [item for item in parse_timings if not item.get("cached") and item.get("seconds", 0) >= 1.0]
            if slow_items:
                detail += "|较慢文件:" + "、".join(f"{item.get('file','')[:24]} {item.get('seconds',0):.1f}s" for item in slow_items[:3])
            st.caption(detail)
            with st.expander("查看本次 FIT 解析耗时", expanded=False):
                timing_df = pd.DataFrame(parse_timings)
                show_cols = ["file", "parser", "cached", "seconds", "size_kb", "records"]
                if "error" in timing_df.columns:
                    show_cols.append("error")
                st.dataframe(timing_df[[c for c in show_cols if c in timing_df.columns]].astype(str), use_container_width=True, hide_index=True)

        # Preview table - cast to text so Streamlit does not right-align numeric cells.
        df = pd.DataFrame(new_rides)
        cols = ['date', 'dur', 'dist', 'avg_p', 'np', 'max_p', 'raw_max_p', 'hr_avg', 'hr_max', 'tss']
        rename_cols = {
            'date': '日期', 'dur': '时长(min)', 'dist': '距离(km)',
            'avg_p': '平均功率', 'np': 'NP', 'max_p': '最大功率(修正)', 'raw_max_p': '原始最大功率',
            'hr_avg': '平均心率', 'hr_max': '最大心率', 'tss': 'TSS'
        }
        show_df = df[[c for c in cols if c in df.columns]].rename(columns=rename_cols)
        st.dataframe(show_df.astype(str), use_container_width=True, hide_index=True)

        # Keep current upload in session; other pages use merge_rides(...) so it will not double-count.
        # This guarantees the user can analyse the just-uploaded files even before/if persistence is delayed.
        historical_before = load_historical()
        merged_rides = merge_rides(historical_before, new_rides)
        added_count = max(0, len(merged_rides) - len(historical_before))
        save_current_rides(merged_rides)
        st.session_state['uploaded_rides'] = new_rides
        st.session_state['uploaded'] = True
        st.success(f"✅ 已合并保存到历史:本次新增 {added_count} 条,当前历史共 {len(merged_rides)} 条")
        st.caption("历史规则:长期保存已解析摘要;新上传中出现的日期会覆盖历史中同日期旧记录,避免重复和旧数据残留。")

        render_upload_quick_diagnosis(merged_rides, load_profile())

        render_upload_next_steps(len(new_rides))
    else:
        st.warning("未找到有效骑行数据。请确认文件为 .fit 格式,并包含骑行记录;如果没有功率数据,部分分析会受限。")



def render_data_import_page(
    *,
    load_intervals_pref,
    save_intervals_pref,
    clear_intervals_pref,
    normalize_intervals_athlete_id,
    fetch_intervals_activities,
    summarize_intervals_response,
    extract_intervals_activity_id,
    intervals_activity_summary_rows,
    download_intervals_activity_fit,
    parse_fit_files,
    ride_from_intervals_summary,
    load_historical,
    merge_rides,
    save_current_rides,
    set_nav,
):
    st.title("🔗 数据导入")
    st.caption("从训练平台或文件导入骑行数据。当前已支持 Intervals.icu 手动导入;Strava / Garmin 授权导入后续接入。")

    import_source = st.selectbox("选择导入来源", ["Intervals.icu", "Strava(正在申请中...)"], key="data_import_source")

    if import_source == "Intervals.icu":
        render_intervals_manual_import_note()
        icu_jump_1, icu_jump_2 = st.columns([1, 1])
        with icu_jump_1:
            st.link_button("打开 Intervals.icu", "https://intervals.icu/", type="primary", use_container_width=True)
        with icu_jump_2:
            st.link_button("打开 Intervals 设置", "https://intervals.icu/settings", type="primary", use_container_width=True)

    if import_source == "Strava(正在申请中...)":
        render_strava_export_note()
        strava_jump_1, strava_jump_2 = st.columns([1, 1])
        with strava_jump_1:
            st.link_button("打开 Strava", "https://www.strava.com/", type="primary", use_container_width=True)
        with strava_jump_2:
            st.link_button("查看 FIT 导出说明", "https://support.strava.com/hc/en-us/articles/216918437-Exporting-your-Data-and-Bulk-Export", type="primary", use_container_width=True)

    if import_source == "Strava(正在申请中...)":
        st.subheader("Strava 授权导入(申请接入中)")
        st.info("TrueCadence 计划通过 Strava OAuth 提供只读导入。当前仍在申请 Strava Developer Program / Athlete Capacity 审核;正式上线前,Strava 不会作为唯一导入方式。")

        st.markdown("""
    **计划用途**
    - 用户主动点击授权后,导入本人最近骑行活动用于训练分析。
    - 默认读取最近 30 天,最多 90 天;不做无限历史同步。
    - 分析内容包括训练负荷、功率画像、耐力趋势、心率/踏频背景和恢复相关提示。

    **数据边界**
    - 只读:不写入、不修改、不删除、不发布 Strava 活动。
    - 只给本人看:不会把某位运动员的 Strava 数据展示给其他用户。
    - 不复制 Strava 的社交、路线、路段、排行榜或动态流功能。
    - 不使用 Strava 数据训练、微调、评测或构建 AI/ML 模型。
    - 用户可断开 Strava,并请求删除已导入的 Strava 数据。
    """)

        st.warning("当前可用替代方式:1)从 Strava / Garmin / 码表导出 FIT 后进入 📤 上传分析;2)使用 Intervals.icu 手动导入最近 7-90 天活动。")
        with st.expander("审核用技术说明", expanded=True):
            st.markdown("""
    - OAuth callback domain: `truecadence.cn`
    - Proposed redirect URI: `https://truecadence.cn/auth-bridge/strava/callback`
    - Requested scopes: `read`, `activity:read`, and only when用户明确授权私密活动时使用 `activity:read_all`
    - Raw activity files / stream data, if temporarily downloaded for parsing, will be retained only for a limited period and then deleted.
    - Parsed training summaries are used only inside the authorized user's TrueCadence dashboard.
    """)
        st.stop()

    st.subheader("Intervals.icu")
    render_intervals_oauth_import_note()

    # ─── OAuth connect / disconnect ───
    from intervals_oauth import get_token, is_connected, get_authorize_url, disconnect_user
    user_id_oauth = st.session_state.get("user", {}).get("user_id", "")
    oauth_token = get_token(user_id_oauth) if user_id_oauth else None
    oauth_connected = bool(oauth_token)

    local_import_test_mode = os.environ.get("TRUECADENCE_DEPLOY_MODE", "local").lower() != "production"
    if oauth_connected:
        st.success("✅ 已连接 Intervals.icu（OAuth 授权）")
        if st.button("断开 Intervals.icu 连接", key="intervals_oauth_disconnect", use_container_width=True):
            disconnect_user(user_id_oauth)
            st.success("已断开 Intervals.icu 连接。")
            st.rerun()
    elif local_import_test_mode:
        st.info("本地测试模式：OAuth 授权按钮已隐藏，避免跳转到生产服务器。请使用下方 Personal API Key 方式读取和导入 Intervals 活动。")
    else:
        authorize_url, _ = get_authorize_url(user_id_oauth)
        st.markdown(f"""
    <div style="text-align:center;padding:1em 0">
    <a href="{authorize_url}" target="_self" style="display:inline-block;padding:.8em 1.8em;background:#ff6b35;color:#fff;border-radius:10px;text-decoration:none;font-weight:700;font-size:1.05em;width:100%;text-align:center;box-sizing:border-box">前往 Intervals.icu 授权</a>
    </div>
    """, unsafe_allow_html=True)
        st.caption("授权完成后自动返回此页面，请勿关闭本窗口。")

    st.divider()
    st.caption("以下 API Key 方式为内测临时兼容入口。")

    with st.expander("如何获取 Intervals.icu API Key?", expanded=False):
        st.markdown("""
    1. 点击上方"打开 Intervals 设置",并登录 Intervals.icu。
    2. 进入 设置 / 开发者设置。
    3. 点击"API密钥 (view)"查看并复制 Personal API Key。
    4. 回到 TrueCadence 的"数据导入 → Intervals.icu",填写 API Key 后手动导入。
    5. Athlete ID 可留空;系统会使用 `0` 代表当前 API Key 对应的本人。如果你确实要导入其他已授权运动员,再填写对应 ID,例如 `i149556`。

    当前 Intervals.icu 官方建议:个人自己使用可以用 API Key;面向多用户的第三方应用应使用 OAuth 和 Bearer token。TrueCadence 当前 API Key 导入仅作为内测临时方案;正式多用户版本会切换到 OAuth。不要把 API Key 发给别人,也不要在公开视频截图里露出。
    """)

    saved_pref = load_intervals_pref()
    default_athlete_id = ""
    c1, c2 = st.columns([1, 1])
    athlete_raw = c1.text_input("Athlete ID(可留空)", value=default_athlete_id, placeholder="留空=本人;或填 i12345", key="intervals_athlete_id", help="OAuth/API Key 推荐留空,系统会用 0 表示授权账号本人。")
    api_key = c2.text_input("Personal API Key", type="password", key="intervals_api_key", help="只在当前会话使用,不保存。已完成 OAuth 授权时可留空。")
    pref_col1, pref_col2 = st.columns([1, 1])
    remember_athlete = pref_col1.checkbox("记住 Athlete ID 24 小时(不保存 API Key)", value=False, help="通常建议留空,用 0 表示当前 API Key 本人;只有导入其他已授权运动员时才需要记住 ID。")
    if pref_col2.button("清除已记住的 Athlete ID", use_container_width=True):
        clear_intervals_pref()
        st.success("已清除本地记住的 Intervals Athlete ID。")
        st.rerun()
    today = pd.Timestamp.today().normalize()
    range_mode = st.radio("导入范围", ["最近30天", "最近90天", "今年以来", "最近12个月", "全部历史", "自定义"], horizontal=True, index=1, help='训练频率低或最近活动少时，建议用「最近12个月」「全部历史」或「自定义」。')
    if range_mode == "最近30天":
        oldest = (today - pd.Timedelta(days=29)).strftime("%Y-%m-%d")
        newest = today.strftime("%Y-%m-%d")
    elif range_mode == "最近90天":
        oldest = (today - pd.Timedelta(days=89)).strftime("%Y-%m-%d")
        newest = today.strftime("%Y-%m-%d")
    elif range_mode == "今年以来":
        oldest = f"{today.year}-01-01"
        newest = today.strftime("%Y-%m-%d")
    elif range_mode == "最近12个月":
        oldest = (today - pd.Timedelta(days=365)).strftime("%Y-%m-%d")
        newest = today.strftime("%Y-%m-%d")
    elif range_mode == "全部历史":
        oldest = "2000-01-01"
        newest = today.strftime("%Y-%m-%d")
    else:
        dc1, dc2 = st.columns([1, 1])
        start_date = dc1.date_input("开始日期", value=datetime.date(today.year, 1, 1), max_value=today.date(), key="intervals_start_date")
        end_date = dc2.date_input("结束日期", value=today.date(), max_value=today.date(), key="intervals_end_date")
        if start_date > end_date:
            st.error("开始日期不能晚于结束日期。")
            st.stop()
        oldest = start_date.strftime("%Y-%m-%d")
        newest = end_date.strftime("%Y-%m-%d")
    intervals_debug = False
    athlete_id = normalize_intervals_athlete_id(athlete_raw)
    if athlete_id and remember_athlete and athlete_id != default_athlete_id:
        save_intervals_pref(athlete_id, hours=24)

    st.caption(f"计划读取范围:{oldest} → {newest}")

    intervals_can_read = bool(oauth_token or api_key)
    intervals_auth_label = "OAuth 授权" if oauth_token else "API Key"
    if st.button("读取 Intervals 活动列表", type="primary", disabled=not intervals_can_read):
        try:
            with st.spinner(f"正在通过 {intervals_auth_label} 读取 Intervals.icu 活动列表..."):
                result = fetch_intervals_activities(athlete_id, api_key, oldest, newest, debug=intervals_debug, bearer_token=oauth_token)
                if intervals_debug:
                    acts, endpoint_used, debug_summaries = result
                    st.session_state["intervals_debug_summaries"] = debug_summaries
                else:
                    acts, endpoint_used = result
                    st.session_state.pop("intervals_debug_summaries", None)
            acts = [a for a in acts if isinstance(a, dict)]
            if len(acts) > 100:
                st.warning(f"当前范围读取到 {len(acts)} 条活动,已截取最近/前 100 条。建议缩小日期范围分批导入。")
                acts = acts[:100]
            st.session_state["intervals_activities"] = acts
            st.session_state["intervals_endpoint_used"] = endpoint_used
            st.success(f"读取成功:{len(acts)} 条活动")
            debug_summaries = st.session_state.get("intervals_debug_summaries") or []
            if debug_summaries:
                st.subheader("Intervals 导入诊断结果")
                st.json({
                    "athlete_id_used": athlete_id,
                    "range": f"{oldest} → {newest}",
                    "final_count": len(acts),
                    "final_endpoint": endpoint_used,
                    "diagnostics": debug_summaries,
                })
        except Exception as e:
            st.error(f"读取失败:{e}")
            st.info("如果失败,可能是 Athlete ID/API Key 不正确,或 Intervals API 路径与当前实现不一致。第一版会先本地调通后再上线。")

    if st.session_state.get("last_import_message"):
        st.success(st.session_state.get("last_import_message"))
        if st.session_state.get("last_import_warning"):
            st.warning(st.session_state.get("last_import_warning"))
        last_table = st.session_state.get("last_import_table") or []
        if last_table:
            cols = ['date', 'dur', 'dist', 'avg_p', 'np', 'max_p', 'hr_avg', 'hr_max', 'tss', 'source']
            rename_cols = {'date': '日期', 'dur': '时长(min)', 'dist': '距离(km)', 'avg_p': '平均功率', 'np': 'NP', 'max_p': '最大功率', 'hr_avg': '平均心率', 'hr_max': '最大心率', 'tss': 'TSS', 'source': '来源'}
            df_last = pd.DataFrame(last_table)
            st.dataframe(df_last[[c for c in cols if c in df_last.columns]].rename(columns=rename_cols).astype(str), use_container_width=True, hide_index=True)
            st.caption("导入后可去 📊 功率仪表盘 / 📈 训练负荷 查看;本次导入数据也会作为当前上传批次参与合并预览。")

    acts = st.session_state.get("intervals_activities") or []
    if acts:
        st.subheader("选择要导入的活动")
        select_mode = st.radio(
            "选择方式",
            ["手动选择", "全选当前列表", "只选最近10条"],
            horizontal=True,
            index=0,
            help="全选最多会导入当前列表显示的 100 条;第一次测试建议只选最近10条或手动选 1-3 条。",
            key="intervals_select_mode",
        )
        rows = intervals_activity_summary_rows(acts)
        if select_mode == "全选当前列表":
            for r in rows:
                r["选择"] = True
        elif select_mode == "只选最近10条":
            for i, r in enumerate(rows):
                r["选择"] = i < 10
        edited = st.data_editor(pd.DataFrame(rows), use_container_width=True, hide_index=True, key=f"intervals_activity_picker_{select_mode}")
        selected_ids = []
        try:
            selected_indexes = edited.index[edited["选择"] == True].tolist()
            selected_ids = [extract_intervals_activity_id(acts[i]) for i in selected_indexes if i < len(acts)]
            selected_ids = [str(x) for x in selected_ids if str(x)]
        except Exception:
            selected_ids = []
        st.caption(f"已选择 {len(selected_ids)} 条。建议第一次先选 1-3 条测试;确认稳定后再全选当前列表。")

        if st.session_state.get("intervals_import_busy"):
            st.warning("正在下载并导入 Intervals 活动,请不要切换页面或清除数据。")

        if st.button("下载并导入选中活动", disabled=st.session_state.get("intervals_import_busy") or not selected_ids or not intervals_can_read or not athlete_id):
            st.session_state["intervals_import_busy"] = True
            st.session_state["intervals_pending_ids"] = selected_ids
            set_nav("导入数据", "平台导入")
            st.rerun()

        pending_ids = st.session_state.get("intervals_pending_ids") or []
        if st.session_state.get("intervals_import_busy") and pending_ids:
            selected_ids = pending_ids
            id_set = set(selected_ids)
            id_to_activity = {extract_intervals_activity_id(a): a for a in acts}
            fit_files = []
            failures = []
            progress = st.progress(0)
            for idx, activity_id in enumerate(selected_ids, start=1):
                try:
                    data, path_used = download_intervals_activity_fit(athlete_id, activity_id, api_key, bearer_token=oauth_token)
                    name = f"intervals_{activity_id}.fit"
                    fit_files.append(NamedBytesFile(name, data))
                except Exception as e:
                    failures.append(f"{activity_id}: {e}")
                progress.progress(idx / max(len(selected_ids), 1))

            new_rides = []
            if fit_files:
                with st.spinner(f"正在解析 {len(fit_files)} 个 Intervals FIT..."):
                    new_rides = parse_fit_files(fit_files)
                for r in new_rides:
                    r["source"] = "intervals_icu"
                    if r.get("file_name", "").startswith("intervals_"):
                        r["external_id"] = r.get("file_name", "").replace("intervals_", "").replace(".fit", "")
            parsed_ids = {str(r.get("external_id", "")) for r in new_rides if r.get("external_id")}
            fallback_rides = []
            for activity_id in selected_ids:
                if activity_id in parsed_ids:
                    continue
                a = id_to_activity.get(activity_id)
                rr = ride_from_intervals_summary(a)
                if rr:
                    fallback_rides.append(rr)
            if fallback_rides:
                st.info(f"有 {len(fallback_rides)} 条活动未能下载 FIT,已先用 Intervals 活动摘要导入。功率曲线/疲劳抗性会弱一些,后续再补 FIT 下载 endpoint。")
                new_rides.extend(fallback_rides)

            if new_rides:
                new_rides = enrich_rides(new_rides)
                historical_before = load_historical()
                merged_rides = merge_rides(historical_before, new_rides)
                added_count = max(0, len(merged_rides) - len(historical_before))
                save_current_rides(merged_rides)
                st.session_state["uploaded_rides"] = new_rides
                st.session_state["last_import_rides"] = new_rides
                st.session_state["last_import_count"] = len(new_rides)
                st.session_state["last_import_message"] = f"✅ Intervals 导入完成:解析/摘要 {len(new_rides)} 条,新增 {added_count} 条,当前历史 {len(merged_rides)} 条。"
                st.session_state["last_import_table"] = new_rides
                if failures:
                    st.session_state["last_import_warning"] = f"有 {len(failures)} 条活动未能下载原始 FIT,已使用 Intervals 活动摘要导入。基础训练负荷、功率/心率摘要可用;逐点功率曲线和疲劳抗性会弱一些。常见原因是这些活动来自 Strava API 同步,Intervals 不提供原始 FIT 下载。"
                else:
                    st.session_state.pop("last_import_warning", None)
                st.session_state.pop("intervals_import_busy", None)
                st.session_state.pop("intervals_pending_ids", None)
                st.cache_data.clear()
                set_nav("导入数据", "平台导入")
                st.rerun()
            else:
                st.session_state.pop("intervals_import_busy", None)
                st.session_state.pop("intervals_pending_ids", None)
                if failures:
                    st.error("导入失败:无法下载 FIT,也无法生成活动摘要。请确认这些活动在 Intervals 中有日期、时长、距离或训练负荷等摘要字段。")
                else:
                    st.error("导入失败:没有生成有效活动。")

