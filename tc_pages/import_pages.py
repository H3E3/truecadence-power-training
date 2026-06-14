from __future__ import annotations

import datetime
import html
import os

import pandas as pd
import streamlit as st
from tc_pages.v2.router import render_v2_page

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


def _render_v2_dialog_style() -> None:
    st.markdown("""
<style>
div[data-testid="stDialog"] { align-items:flex-start!important; padding-top:54px!important; }
div[data-testid="stDialog"] > div { background:linear-gradient(180deg, rgba(15,18,24,.98), rgba(8,10,13,.985)); border:1.4px solid rgba(240,111,50,.40); border-radius:28px; color:#f4f0ea; box-shadow:0 26px 70px rgba(0,0,0,.46),0 0 0 1px rgba(255,255,255,.035) inset,0 0 44px rgba(240,111,50,.10); width:min(720px,calc(100vw - 88px))!important; max-width:720px!important; height:auto!important; min-height:0!important; max-height:min(760px,calc(100vh - 92px))!important; overflow:auto!important; margin:0 auto!important; transform:none!important; padding:0!important; }
div[data-testid="stDialog"] [role="dialog"] { width:100%!important; max-width:none!important; margin:0!important; padding:0!important; }
div[data-testid="stDialog"] [role="dialog"] > div:first-child { display:none!important; min-height:0!important; height:0!important; padding:0!important; margin:0!important; overflow:hidden!important; }
div[data-testid="stDialog"] [role="dialog"] > div:nth-child(2) { padding:0 34px 28px!important; box-sizing:border-box!important; }
div[data-testid="stDialog"] h2, div[data-testid="stDialog"] h3,
div[data-testid="stDialog"] [role="dialog"] > div:first-child [data-testid="stMarkdownContainer"] p { color:#f4f0ea!important; letter-spacing:-.02em!important; font-size:19px!important; font-weight:760!important; line-height:1.2!important; margin:0!important; font-family:inherit!important; }
div[data-testid="stDialog"] button[aria-label="Close"],
div[data-testid="stDialog"] button[aria-label="关闭"] { display:none!important; }
div[data-testid="stDialog"] [data-testid="stWidgetLabel"] { color:#a7a19a!important; }
div[data-testid="stDialog"] [data-testid="stFileUploader"] { margin-left:0!important; margin-right:0!important; }
div[data-testid="stDialog"] [data-testid="stFileUploader"] section {
    background:#080a0d;
    border-color:#253244;
    min-height:128px;
    display:flex!important;
    flex-direction:column!important;
    align-items:center!important;
    justify-content:center!important;
    text-align:center!important;
    gap:10px!important;
}
div[data-testid="stDialog"] [data-testid="stFileUploader"] section > span,
div[data-testid="stDialog"] [data-testid="stFileUploader"] section [data-testid="stFileUploaderDropzoneInstructions"] {
    width:auto!important;
    max-width:100%!important;
    margin:0!important;
    align-self:center!important;
    justify-content:center!important;
    text-align:center!important;
}
div[data-testid="stDialog"] [data-testid="stFileUploader"] section [data-testid="stBaseButton-secondary"] {
    margin:0 auto!important;
}
div[data-testid="stDialog"] [data-testid="stTextInput"], div[data-testid="stDialog"] [data-testid="stNumberInput"], div[data-testid="stDialog"] [data-testid="stDateInput"], div[data-testid="stDialog"] [data-testid="stRadio"], div[data-testid="stDialog"] [data-testid="stExpander"] { margin-bottom:.72rem!important; }
div[data-testid="stDialog"] .stButton>button, div[data-testid="stDialog"] [data-testid="stBaseButton-primary"], div[data-testid="stDialog"] [data-testid="stBaseButton-secondary"] {
    min-height:42px!important;
    border-radius:16px!important;
    background:#10151d!important;
    border:1px solid rgba(255,255,255,.10)!important;
    color:#f4f0ea!important;
    font-weight:760!important;
}
div[data-testid="stDialog"] .stButton>button:hover, div[data-testid="stDialog"] [data-testid="stBaseButton-primary"]:hover, div[data-testid="stDialog"] [data-testid="stBaseButton-secondary"]:hover {
    background:#151b25!important;
    border-color:rgba(240,111,50,.30)!important;
    color:#fff7ef!important;
}
.tc-v2-modal-topbar { display:grid; grid-template-columns:1fr 48px; align-items:center; min-height:72px; margin:0 -34px; padding:18px 24px 14px; box-sizing:border-box; background:linear-gradient(180deg, rgba(15,18,24,.98), rgba(15,18,24,.88)); border-bottom:1px solid rgba(255,255,255,.06); }
.tc-v2-modal-title { color:#f4f0ea; font-size:19px; font-weight:760; letter-spacing:-.02em; line-height:1.2; }
.tc-v2-modal-close { width:36px; height:36px; justify-self:end; display:inline-flex; align-items:center; justify-content:center; border-radius:13px; color:#bdb4aa!important; text-decoration:none!important; border:1px solid rgba(255,255,255,.07); background:rgba(255,255,255,.035); font-size:22px; line-height:1; box-sizing:border-box; }
.tc-v2-modal-close:hover { color:#fff4ea!important; background:rgba(240,111,50,.13); border-color:rgba(240,111,50,.30); }
.tc-v2-dialog-hint { color:#a7a19a; line-height:1.65; margin:0 0 20px; padding-top:22px; font-size:.94rem; }
.tc-v2-dialog-mini-note { color:#8c867e; font-size:.88rem; line-height:1.55; margin:.25rem 0 .75rem; }
.tc-v2-step-card,.tc-v2-result-card { border:1px solid rgba(255,255,255,.08); background:rgba(255,255,255,.035); border-radius:22px; padding:18px 20px; margin:2px 0 18px; }
.tc-v2-step-kicker { color:#f06f32; font-size:.74rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; margin-bottom:8px; }
.tc-v2-step-title { color:#f4f0ea; font-size:1.12rem; font-weight:760; letter-spacing:-.03em; margin-bottom:6px; }
.tc-v2-step-text,.tc-v2-step-muted,.tc-v2-result-sub { color:#a7a19a; line-height:1.62; font-size:.93rem; }
.tc-v2-step-muted { margin:.3rem 0 .6rem; }
.tc-v2-result-ok { color:#9cf0c9; font-size:.82rem; font-weight:800; margin-bottom:6px; }
.tc-v2-result-main { color:#f4f0ea; font-size:1rem; font-weight:740; margin-bottom:4px; }
.tc-v2-choice-card { border:1px solid rgba(240,111,50,.22); background:rgba(240,111,50,.055); border-radius:20px; padding:16px 18px; margin:8px 0 14px; }
.tc-v2-action-row { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; margin:4px 0 18px; }
.tc-v2-dialog-btn { display:flex; align-items:center; justify-content:center; min-height:42px; padding:.72rem .8rem; border-radius:16px; box-sizing:border-box; text-decoration:none!important; color:#f4f0ea!important; background:#10151d; border:1px solid rgba(255,255,255,.10); font-weight:760; font-size:.92rem; letter-spacing:-.01em; text-align:center; }
.tc-v2-dialog-btn:hover { background:#151b25; border-color:rgba(240,111,50,.30); color:#fff7ef!important; }
.tc-v2-dialog-btn.primary { background:#f06f32; border-color:#f06f32; color:#11151b!important; box-shadow:0 12px 28px rgba(240,111,50,.18); }
.tc-v2-dialog-btn.primary:hover { background:#ff8248; border-color:#ff8248; }
.tc-v2-insight-card { border:1px solid rgba(240,111,50,.26); background:linear-gradient(180deg,rgba(240,111,50,.085),rgba(255,255,255,.035)); border-radius:22px; padding:17px 19px; margin:0 0 18px; box-shadow:0 14px 34px rgba(0,0,0,.18); }
.tc-v2-insight-card .kicker { color:#f06f32; font-size:.72rem; font-weight:850; letter-spacing:.12em; margin-bottom:8px; }
.tc-v2-insight-card .title { color:#fff7ef; font-size:1.06rem; font-weight:800; letter-spacing:-.03em; margin-bottom:8px; }
.tc-v2-insight-card .body { color:#d5cec7; font-size:.94rem; line-height:1.72; }
.tc-v2-insight-card .note { color:#8c867e; font-size:.82rem; line-height:1.55; margin-top:10px; }
@media (max-width: 640px) { .tc-v2-action-row { grid-template-columns:1fr; } }
</style>
""", unsafe_allow_html=True)


def _safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _fmt_num(value, suffix="", digits=0):
    v = _safe_float(value, None)
    if v is None:
        return "暂无"
    if digits == 0:
        return f"{v:.0f}{suffix}"
    return f"{v:.{digits}f}{suffix}"


def _build_today_plain_advice(rides, profile=None):
    rides = rides or []
    if not rides:
        return "现在训练数据还不够，今天先不要急着做高强度。更稳的做法是轻松骑 45-60 分钟，感觉能聊天、不憋气就对了。等再上传几次骑行后，系统会更准确判断你该休息、该稳骑，还是可以加一点强度。"
    latest = sorted(rides, key=lambda r: str(r.get("date", "")), reverse=True)[0]
    dur = _safe_float(latest.get("dur"))
    avg_p = _safe_float(latest.get("avg_p"))
    np_val = _safe_float(latest.get("np")) or avg_p
    tss = _safe_float(latest.get("tss"))
    hr = _safe_float(latest.get("hr_avg"))
    hard = (tss >= 85) or (dur >= 150 and np_val >= 160)
    moderate = (tss >= 45) or (dur >= 70)
    if hard:
        main = "上一骑对身体消耗不小，今天别急着证明自己。"
        action = "建议轻松骑 45-75 分钟，或者直接休息；如果腿沉、心率飘，就不要做间歇。"
    elif moderate:
        main = "最近这次训练有一定刺激，但还没到必须完全躺平的程度。"
        action = "今天适合 Z2 轻松有氧 60-90 分钟，重点是稳，不要把轻松骑变成暗中较劲。"
    else:
        main = "上一骑负担不重，身体大概率还有余量。"
        action = "如果睡眠和腿感正常，今天可以做 60-90 分钟有氧；想加一点质量，也只加短一点的甜区，不要上来就冲。"
    detail = f"系统看到的最近一次大概是 {_fmt_num(dur, '分钟')}、平均功率 {_fmt_num(avg_p, 'W')}、训练负荷 {_fmt_num(tss)}。"
    if hr:
        detail += f" 平均心率约 {_fmt_num(hr)}，可以作为疲劳参考。"
    return f"{main}{action}{detail} 简单说：今天先把节奏骑稳，身体反馈比硬顶数字更重要。"


def _build_power_plain_summary(rides, profile=None):
    rides = rides or []
    if not rides:
        return "现在还缺少功率数据，暂时不要急着判断自己是冲刺型、爬坡型还是耐力型。先补最近几次有功率的 FIT，尤其是一次较长有氧和一次相对用力的训练。数据够了以后，系统会把专业功率曲线翻译成：你短时间爆发强不强、长时间稳不稳、后半程会不会掉得明显。"
    valid_power = [r for r in rides if _safe_float(r.get("avg_p")) or _safe_float(r.get("np")) or _safe_float(r.get("max_p"))]
    best_avg = max((_safe_float(r.get("avg_p")) for r in valid_power), default=0)
    best_np = max((_safe_float(r.get("np")) for r in valid_power), default=0)
    max_p = max((_safe_float(r.get("max_p")) or _safe_float(r.get("raw_max_p")) for r in valid_power), default=0)
    long_rides = [r for r in rides if _safe_float(r.get("dur")) >= 90]
    if len(valid_power) < 3:
        confidence = "目前数据量还偏少，画像先作为初步参考。"
    elif len(long_rides) < 2:
        confidence = "已有部分短中距离训练数据，但长时间稳定性还需要继续观察。"
    else:
        confidence = "现有训练记录已经可以看出大致能力结构，后续会随新数据继续校准。"
    if best_np >= best_avg * 1.12 and best_np >= 180:
        trait = "你具备一定的强度提升能力，下一步重点是看这种输出能否在更长时间里保持稳定。"
    elif long_rides:
        trait = "当前更值得关注的是持续输出能力，也就是训练后段还能不能保持稳定节奏。"
    else:
        trait = "现在还看不出完整画像，先不要用一次骑行下结论。"
    metrics = f"当前已读到 {len(rides)} 条训练，其中 {len(valid_power)} 条包含功率数据；最高平均功率约 {_fmt_num(best_avg, 'W')}，最高 NP 约 {_fmt_num(best_np, 'W')}。"
    if max_p:
        metrics += f" 峰值功率约 {_fmt_num(max_p, 'W')}。"
    return f"{confidence}{trait}{metrics} 简单理解：功率画像看的不是单次爆发，而是强度、耐力和稳定性的组合。"


def _render_plain_insight_card(kind, rides, profile=None):
    if kind == "power":
        title = "功率画像：先看稳定能力，不急着贴标签"
        body = _build_power_plain_summary(rides, profile)
        note = "专业曲线先藏起来；客户第一眼只需要知道：强项在哪里、短板在哪里、下一步怎么补。"
    else:
        title = "今日建议：今天怎么骑更划算"
        body = _build_today_plain_advice(rides, profile)
        note = "这是上传后的快速建议，不替代教练现场判断；如果明显不舒服，优先休息或降低强度。"
    st.markdown(f"""
<div class="tc-v2-insight-card">
  <div class="kicker">PLAIN LANGUAGE</div>
  <div class="title">{html.escape(title)}</div>
  <div class="body">{html.escape(body)}</div>
  <div class="note">{html.escape(note)}</div>
</div>
""", unsafe_allow_html=True)


def _render_upload_fit_controls(
    *,
    parse_fit_files,
    enrich_rides,
    load_historical,
    merge_rides,
    save_current_rides,
    render_upload_quick_diagnosis,
    load_profile,
):
    st.markdown("""
<div class="tc-v2-step-card">
  <div class="tc-v2-step-kicker">STEP 1 · FILE</div>
  <div class="tc-v2-step-title">选择最近的 FIT 文件</div>
  <div class="tc-v2-step-text">建议先传最近 1-2 次或最近 4-12 周关键训练。上传后系统会解析、合并历史，并更新诊断入口。</div>
</div>
""", unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "选择或拖拽 FIT 文件",
        type=['fit'],
        accept_multiple_files=True,
        key="fit_file_uploader",
        help="从码表、骑行台或训练平台导出的 .fit 文件。一次最多上传 28 个, 单次总大小最多 50MB。网络不稳定时建议每批 5-10 个。"
    )

    MAX_FIT_UPLOADS = 28
    MAX_TOTAL_UPLOAD_MB = 50
    if uploaded and len(uploaded) > MAX_FIT_UPLOADS:
        st.error(f"一次最多上传 {MAX_FIT_UPLOADS} 个 FIT 文件。你当前选择了 {len(uploaded)} 个,请分批上传。")
        st.stop()
    if uploaded:
        total_bytes = sum(getattr(f, "size", 0) or 0 for f in uploaded)
        total_mb = total_bytes / 1024 / 1024
        if total_mb > MAX_TOTAL_UPLOAD_MB:
            st.error(f"本次文件总大小约 {total_mb:.1f}MB,超过单次 {MAX_TOTAL_UPLOAD_MB}MB 限制。请分批上传。")
            st.stop()

    if not uploaded:
        st.markdown('<div class="tc-v2-step-muted">尚未选择文件。这里不会提前展开旧版诊断表，上传后只显示本次结果摘要。</div>', unsafe_allow_html=True)
        st.stop()

    current_fit_sig = tuple((getattr(f, "name", ""), getattr(f, "size", 0) or 0) for f in (uploaded or []))
    st.session_state["fit_upload_busy"] = True
    with st.spinner(f"正在解析 {len(uploaded)} 个文件..."):
        new_rides = parse_fit_files(uploaded)
    st.session_state["last_fit_upload_sig"] = current_fit_sig
    st.session_state["fit_upload_busy"] = False

    if not new_rides:
        st.warning("未找到有效骑行数据。请确认文件为 .fit 格式,并包含骑行记录;如果没有功率数据,部分分析会受限。")
        st.stop()

    new_rides = enrich_rides(new_rides)
    historical_before = load_historical()
    merged_rides = merge_rides(historical_before, new_rides)
    added_count = max(0, len(merged_rides) - len(historical_before))
    save_current_rides(merged_rides)
    st.session_state['uploaded_rides'] = new_rides
    st.session_state['uploaded'] = True

    st.markdown(f"""
<div class="tc-v2-result-card">
  <div class="tc-v2-result-ok">解析完成</div>
  <div class="tc-v2-result-main">识别 {len(new_rides)} 条骑行 · 新增 {added_count} 条 · 历史共 {len(merged_rides)} 条</div>
  <div class="tc-v2-result-sub">数据已保存到当前骑手历史，后续页面会基于新历史更新建议。</div>
</div>
""", unsafe_allow_html=True)

    insight_col1, insight_col2, insight_col3 = st.columns([1, 1, 1])
    with insight_col1:
        if st.button("展开今日建议", key="fit_result_today_plain", use_container_width=True):
            st.session_state["fit_result_insight"] = "today"
    with insight_col2:
        if st.button("展开功率画像", key="fit_result_power_plain", use_container_width=True):
            st.session_state["fit_result_insight"] = "power"
    with insight_col3:
        if st.button("收起说明", key="fit_result_hide_plain", use_container_width=True):
            st.session_state.pop("fit_result_insight", None)

    if st.session_state.get("fit_result_insight"):
        _render_plain_insight_card(st.session_state.get("fit_result_insight"), merged_rides, load_profile())

    st.markdown('<div class="tc-v2-dialog-mini-note">想继续补数据，直接重新选择 FIT 文件即可；系统会自动合并历史并去重。</div>', unsafe_allow_html=True)

    parse_total = st.session_state.get("last_fit_parse_total_seconds")
    parse_timings = st.session_state.get("last_fit_parse_timings") or []
    with st.expander("查看解析详情", expanded=False):
        if parse_total is not None and parse_timings:
            cached_count = sum(1 for item in parse_timings if item.get("cached"))
            st.caption(f"解析耗时:{parse_total:.2f}s · 缓存命中 {cached_count}/{len(parse_timings)}")
            timing_df = pd.DataFrame(parse_timings)
            show_cols = ["file", "parser", "cached", "seconds", "size_kb", "records"]
            if "error" in timing_df.columns:
                show_cols.append("error")
            st.dataframe(timing_df[[c for c in show_cols if c in timing_df.columns]].astype(str), use_container_width=True, hide_index=True)
        df = pd.DataFrame(new_rides)
        cols = ['date', 'dur', 'dist', 'avg_p', 'np', 'max_p', 'raw_max_p', 'hr_avg', 'hr_max', 'tss']
        rename_cols = {
            'date': '日期', 'dur': '时长(min)', 'dist': '距离(km)',
            'avg_p': '平均功率', 'np': 'NP', 'max_p': '最大功率(修正)', 'raw_max_p': '原始最大功率',
            'hr_avg': '平均心率', 'hr_max': '最大心率', 'tss': 'TSS'
        }
        show_df = df[[c for c in cols if c in df.columns]].rename(columns=rename_cols)
        st.dataframe(show_df.astype(str), use_container_width=True, hide_index=True)
        st.caption("历史规则:长期保存已解析摘要;新上传中出现的日期会覆盖历史中同日期旧记录,避免重复和旧数据残留。")

    with st.expander("查看本次快速诊断", expanded=False):
        render_upload_quick_diagnosis(merged_rides, load_profile())
        render_upload_next_steps(len(new_rides))


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
    action = st.query_params.get("action")
    render_v2_page("upload")
    if action == "upload-fit":
        _render_v2_dialog_style()

        @st.dialog(" ", width="medium")
        def _upload_fit_dialog():
            st.markdown(
                '<div class="tc-v2-modal-topbar"><div class="tc-v2-modal-title">上传 FIT 文件</div><a class="tc-v2-modal-close" href="?nav=%E4%B8%8A%E4%BC%A0%E4%B8%8E%E8%AF%8A%E6%96%AD&sub=%E4%B8%8A%E4%BC%A0%20FIT" target="_self" aria-label="关闭">×</a></div><div class="tc-v2-dialog-hint">选择最近 4-12 周、有功率数据的 FIT。系统会解析、合并历史，并把结果接入新版诊断卡片。</div>',
                unsafe_allow_html=True,
            )
            _render_upload_fit_controls(
                parse_fit_files=parse_fit_files,
                enrich_rides=enrich_rides,
                load_historical=load_historical,
                merge_rides=merge_rides,
                save_current_rides=save_current_rides,
                render_upload_quick_diagnosis=render_upload_quick_diagnosis,
                load_profile=load_profile,
            )

        _upload_fit_dialog()
    st.stop()


def _render_intervals_import_controls(
    *,
    import_source,
    action,
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
    enrich_rides,
    load_historical,
    merge_rides,
    save_current_rides,
    set_nav,
    compact=False,
):
    if import_source == "Intervals.icu" and not compact:
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

    if compact:
        st.markdown('''
<div class="tc-v2-step-card">
  <div class="tc-v2-step-kicker">STEP 1 · CONNECT</div>
  <div class="tc-v2-step-title">选择连接方式</div>
  <div class="tc-v2-step-text">正式环境优先一键授权；本地预览或内测排查时，再展开 API Key 备用方式。</div>
</div>
''', unsafe_allow_html=True)
    else:
        st.subheader("Intervals.icu")
        render_intervals_oauth_import_note()

    # ─── OAuth connect / disconnect ───
    from intervals_oauth import get_token, is_connected, get_authorize_url, disconnect_user
    user_id_oauth = st.session_state.get("user", {}).get("user_id", "")
    oauth_token = get_token(user_id_oauth) if user_id_oauth else None
    oauth_connected = bool(oauth_token)

    deploy_mode = os.environ.get("TRUECADENCE_DEPLOY_MODE", "local").strip().lower()
    local_import_test_mode = deploy_mode in ("", "local", "dev", "development", "test", "testing")
    if oauth_connected:
        st.success("✅ 已连接 Intervals.icu（OAuth 授权）")
        if st.button("断开 Intervals.icu 连接", key="intervals_oauth_disconnect", use_container_width=True):
            disconnect_user(user_id_oauth)
            st.success("已断开 Intervals.icu 连接。")
            st.rerun()
    elif local_import_test_mode:
        if compact:
            st.markdown('<div class="tc-v2-choice-card"><b>一键授权</b><br><span class="tc-v2-step-text">本地预览暂不跳转生产 OAuth。上线环境这里会显示授权按钮。</span></div>', unsafe_allow_html=True)
        else:
            st.info("本地测试模式：OAuth 授权按钮已隐藏，避免跳转到生产服务器。请使用下方 Personal API Key 方式读取和导入 Intervals 活动。")
    else:
        authorize_url, _ = get_authorize_url(user_id_oauth)
        st.markdown(f"""
    <div class="tc-v2-choice-card">
      <div class="tc-v2-step-title">一键授权，推荐</div>
      <div class="tc-v2-step-text">授权后读取你的 Intervals.icu 活动列表，不写入、不修改外部活动。</div>
      <div style="margin-top:12px"><a href="{authorize_url}" target="_self" style="display:inline-block;padding:.78em 1.4em;background:#f06f32;color:#111;border-radius:14px;text-decoration:none;font-weight:800;width:100%;text-align:center;box-sizing:border-box">连接 Intervals.icu</a></div>
    </div>
    """, unsafe_allow_html=True)
        st.caption("授权完成后自动返回此页面，请勿关闭本窗口。")

    if not compact:
        st.divider()
        st.caption("以下 API Key 方式为内测临时兼容入口。")

    api_key_expander_label = "备用方式：使用 Personal API Key" if compact else "如何获取 Intervals.icu API Key?"
    with st.expander(api_key_expander_label, expanded=not compact):
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
    api_key_section = st.expander("读取设置", expanded=bool(oauth_token)) if compact else st.container()
    with api_key_section:
        c1, c2 = st.columns([1, 1])
        athlete_raw = c1.text_input("Athlete ID(可留空)", value=default_athlete_id, placeholder="留空=本人;或填 i12345", key="intervals_athlete_id", help="OAuth/API Key 推荐留空,系统会用 0 表示授权账号本人。")
        api_key = c2.text_input("Personal API Key", type="password", key="intervals_api_key", help="只在当前会话使用,不保存。已完成 OAuth 授权时可留空。")
        pref_col1, pref_col2 = st.columns([1, 1])
        remember_athlete = pref_col1.checkbox("记住 Athlete ID 24 小时(不保存 API Key)", value=False, help="通常建议留空,用 0 表示当前 API Key 本人;只有导入其他已授权运动员时才需要记住 ID。")
        if pref_col2.button("清除已记住的 Athlete ID", use_container_width=True):
            clear_intervals_pref()
            st.success("已清除本地记住的 Intervals Athlete ID。")
            st.rerun()
    if compact and not oauth_token and not api_key and not (st.session_state.get("intervals_activities") or st.session_state.get("last_import_message")):
        st.markdown('<div class="tc-v2-step-muted">填写 API Key 后，再显示读取范围和活动列表。这样默认不会把旧版导入流程一次性铺开。</div>', unsafe_allow_html=True)
        st.stop()
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
            if action == "connect-icu":
                st.query_params["nav"] = "上传与诊断"
                st.query_params["sub"] = "平台导入"
                st.query_params["action"] = "connect-icu"
            else:
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
                if action == "connect-icu":
                    st.query_params["nav"] = "上传与诊断"
                    st.query_params["sub"] = "平台导入"
                    st.query_params["action"] = "connect-icu"
                else:
                    set_nav("导入数据", "平台导入")
                st.rerun()
            else:
                st.session_state.pop("intervals_import_busy", None)
                st.session_state.pop("intervals_pending_ids", None)
                if failures:
                    st.error("导入失败:无法下载 FIT,也无法生成活动摘要。请确认这些活动在 Intervals 中有日期、时长、距离或训练负荷等摘要字段。")
                else:
                    st.error("导入失败:没有生成有效活动。")


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
    enrich_rides,
    load_historical,
    merge_rides,
    save_current_rides,
    set_nav,
):
    action = st.query_params.get("action")
    if action == "connect-icu":
        render_v2_page("upload")
        _render_v2_dialog_style()

        @st.dialog(" ", width="medium")
        def _connect_icu_dialog():
            st.markdown(
                '<div class="tc-v2-modal-topbar"><div class="tc-v2-modal-title">连接 Intervals.icu</div><a class="tc-v2-modal-close" href="?nav=%E4%B8%8A%E4%BC%A0%E4%B8%8E%E8%AF%8A%E6%96%AD&sub=%E5%B9%B3%E5%8F%B0%E5%AF%BC%E5%85%A5" target="_self" aria-label="关闭">×</a></div><div class="tc-v2-dialog-hint">读取活动列表，选择后导入当前骑手历史数据。</div>',
                unsafe_allow_html=True,
            )
            _render_intervals_import_controls(
                import_source="Intervals.icu",
                action=action,
                load_intervals_pref=load_intervals_pref,
                save_intervals_pref=save_intervals_pref,
                clear_intervals_pref=clear_intervals_pref,
                normalize_intervals_athlete_id=normalize_intervals_athlete_id,
                fetch_intervals_activities=fetch_intervals_activities,
                summarize_intervals_response=summarize_intervals_response,
                extract_intervals_activity_id=extract_intervals_activity_id,
                intervals_activity_summary_rows=intervals_activity_summary_rows,
                download_intervals_activity_fit=download_intervals_activity_fit,
                parse_fit_files=parse_fit_files,
                ride_from_intervals_summary=ride_from_intervals_summary,
                enrich_rides=enrich_rides,
                load_historical=load_historical,
                merge_rides=merge_rides,
                save_current_rides=save_current_rides,
                set_nav=set_nav,
                compact=True,
            )

        _connect_icu_dialog()
        st.stop()

    st.title("🔗 数据导入")
    st.caption("从训练平台或文件导入骑行数据。当前已支持 Intervals.icu 手动导入;Strava / Garmin 授权导入后续接入。")
    import_source = st.selectbox("选择导入来源", ["Intervals.icu", "Strava(正在申请中...)"], key="data_import_source")
    _render_intervals_import_controls(
        import_source=import_source,
        action=action,
        load_intervals_pref=load_intervals_pref,
        save_intervals_pref=save_intervals_pref,
        clear_intervals_pref=clear_intervals_pref,
        normalize_intervals_athlete_id=normalize_intervals_athlete_id,
        fetch_intervals_activities=fetch_intervals_activities,
        summarize_intervals_response=summarize_intervals_response,
        extract_intervals_activity_id=extract_intervals_activity_id,
        intervals_activity_summary_rows=intervals_activity_summary_rows,
        download_intervals_activity_fit=download_intervals_activity_fit,
        parse_fit_files=parse_fit_files,
        ride_from_intervals_summary=ride_from_intervals_summary,
        enrich_rides=enrich_rides,
        load_historical=load_historical,
        merge_rides=merge_rides,
        save_current_rides=save_current_rides,
        set_nav=set_nav,
        compact=False,
    )

