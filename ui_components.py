from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st


def image_data_uri(path: Path) -> str:
    try:
        raw = path.read_bytes()
        ext = path.suffix.lower()
        mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png" if ext == ".png" else "image/svg+xml"
        return f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")
    except Exception:
        return ""


def load_tc_logo_svg(logo_path: Path) -> str:
    return image_data_uri(logo_path)


def render_icp_footer(icp_record_no: str, icp_record_url: str, mps_record_no: str, mps_record_url: str, mps_record_icon_path: Path):
    mps_icon = image_data_uri(mps_record_icon_path)
    mps_icon_html = f'<img src="{mps_icon}" alt="公安备案图标" />' if mps_icon else ""
    st.markdown(
        f"""
<div class="tc-icp-footer">
  <span>© 2026 TrueCadence</span>
  <span class="tc-icp-separator">|</span>
  <a href="{icp_record_url}" target="_blank" rel="noopener noreferrer">{icp_record_no}</a>
  <span class="tc-icp-separator">|</span>
  <a class="tc-mps-record" href="{mps_record_url}" target="_blank" rel="noopener noreferrer">{mps_icon_html}<span>{mps_record_no}</span></a>
</div>
""",
        unsafe_allow_html=True,
    )


def render_empty_data_state(title, text, steps=None, primary="去上传 FIT", secondary="先填骑手档案"):
    """Friendly empty state for pages that need ride data."""
    steps = steps or ["在「骑手档案」填写体重、实测 FTP、最大心率和训练目标", "在「上传分析」上传最近 4-12 周 FIT 文件", "回到当前页面查看分析结果"]
    st.markdown(f"""
<div style="padding:1.15em 1.15em;border-radius:16px;background:linear-gradient(135deg,rgba(255,107,53,0.15),rgba(22,27,34,0.96));border:1px solid rgba(255,107,53,0.30);margin:0.85em 0 1em;">
  <div style="color:#ff9a68;font-size:0.78em;font-weight:800;letter-spacing:0.10em;margin-bottom:0.35em;">GET STARTED</div>
  <div style="color:#f0f6fc;font-size:1.28em;font-weight:820;margin-bottom:0.35em;">{title}</div>
  <div style="color:#aab6c3;font-size:0.92em;line-height:1.7;">{text}</div>
</div>
""", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    for i, step in enumerate(steps, 1):
        with [c1, c2, c3][min(i-1, 2)]:
            st.markdown(f"""
<div style="min-height:108px;background:var(--tc-surface);border:1px solid var(--tc-border);border-radius:13px;padding:0.9em;">
  <div style="color:#ff8c5a;font-size:0.78em;font-weight:800;margin-bottom:0.35em;">STEP {i:02d}</div>
  <div style="color:#d8dee9;font-size:0.88em;line-height:1.55;">{step}</div>
</div>
""", unsafe_allow_html=True)
    st.caption(f"建议路径:{secondary} → {primary} → 回来看本页结果。")


def render_mini_metric_card(label, value, delta=""):
    st.markdown(
        f"""
        <div class="tc-mini-metric-card">
          <div class="tc-mm-label">{label}</div>
          <div class="tc-mm-value">{value}</div>
          <div class="tc-mm-delta">{delta or '&nbsp;'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def data_scope_caption(rides, historical, uploaded_rides, source_label):
    return f"当前分析:{len(rides)} 条骑行记录|{source_label}|本次上传 {len(uploaded_rides)} 条|历史存档 {len(historical)} 条"


def select_ride_scope(load_historical_func, merge_rides_func, toggle_label="合并全历史数据", key=None, help_text=None, recommended=False):
    """Shared ride-scope selector for pages that compare history vs current upload.

    Streamlit keeps uploaded files only in session state. After a refresh/restart,
    parsed rides are already saved into history but `uploaded_rides` is empty, so
    a history toggle cannot change the downstream analysis. In that case disable
    the toggle and make the data scope explicit instead of silently falling back.
    """
    uploaded_rides = st.session_state.get('uploaded_rides', [])
    historical = load_historical_func()
    has_current_upload = bool(uploaded_rides)
    default_value = True if recommended or not has_current_upload else False
    use_all = st.toggle(
        toggle_label,
        value=default_value,
        key=key,
        disabled=not has_current_upload,
        help=(help_text if has_current_upload else "当前没有本次上传文件;重启/刷新会清空临时上传态,已保存的 FIT 会进入历史存档。"),
    )
    if use_all:
        rides = merge_rides_func(historical, uploaded_rides)
        source_label = "合并历史数据" if has_current_upload else "历史数据"
    elif has_current_upload:
        rides = uploaded_rides
        source_label = "仅本次上传"
    else:
        rides = historical
        source_label = "历史数据"
    if not has_current_upload:
        st.info("当前没有本次上传文件,只能读取历史存档。若要临时查看某一批 FIT,请重新上传后再关闭合并历史数据。")
    elif not use_all:
        st.warning("当前只看本次上传文件,适合临时排查;正式训练判断建议打开合并历史数据。")
    return uploaded_rides, historical, use_all, rides, source_label



def render_pricing_intro():
    st.markdown("""
<style>
.pricing-hero {
    padding: 1.25em 1.1em;
    border-radius: 14px;
    background: linear-gradient(135deg, rgba(255,107,53,0.13), rgba(22,27,34,0.92));
    border: 1px solid rgba(255,107,53,0.24);
    margin: 0.8em 0 1.1em;
}
.pricing-hero-title { color: #f0f6fc; font-size: 1.16em; font-weight: 760; margin-bottom: 0.35em; }
.pricing-hero-text { color: #aab6c3; font-size: 0.9em; line-height: 1.65; }
.plan-path {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.65em;
    margin: 0.9em 0 1.1em;
}
.path-step { background: var(--tc-surface); border: 1px solid var(--tc-surface-2); border-radius: 12px; padding: 0.75em; }
.path-step .k { color: #ff8c5a; font-weight: 750; margin-bottom: 0.2em; }
.path-step .v { color: var(--tc-subtle); font-size: 0.82em; line-height: 1.45; }
.plans-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.9em;
    align-items: stretch;
    margin-top: 0.8em;
}
.plan-card {
    border-radius: 16px;
    padding: 1.05em 0.95em;
    min-height: 520px;
    height: 100%;
    position: relative;
    box-shadow: 0 10px 28px rgba(0,0,0,0.24);
    display: flex;
    flex-direction: column;
}
.plan-name { font-size: 1.12em; font-weight: 780; margin-bottom: 0.22em; min-height: 32px; }
.plan-price { font-size: 1.22em; font-weight: 780; color: #f0f6fc; margin: 0.25em 0 0.35em; min-height: 38px; }
.plan-fit { color: var(--tc-subtle); font-size: 0.78em; line-height: 1.45; min-height: 44px; margin-bottom: 0.65em; }
.plan-result {
    color: #f0f6fc;
    font-size: 0.86em;
    font-weight: 700;
    padding: 0.65em 0.7em;
    border-radius: 10px;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 0.75em;
    min-height: 78px;
    line-height: 1.5;
}
.plan-feature { color:var(--tc-muted); font-size:0.82em; line-height:1.72; margin-bottom:0.18em; }
.plan-badge {
    display:inline-block; background:#238636; color:#fff; padding:3px 9px; border-radius:999px;
    font-size:0.72em; font-weight:700; margin-top:0.75em; width: fit-content;
}
.plan-rec {
    display:inline-block; background:rgba(255,107,53,0.16); color:#ff9a68;
    border:1px solid rgba(255,107,53,0.38); padding:3px 9px; border-radius:999px;
    font-size:0.72em; font-weight:750; margin-bottom:0.55em; width: fit-content;
}
.plan-card button, .plan-card [data-testid="stButton"] button { width:100% !important; }
/* 套餐卡片:用套餐色做外框,而不是只做内部色条 */
div[data-testid="stVerticalBlock"]:has(> .st-key-choose_card_free),
div[data-testid="stVerticalBlock"]:has(> .st-key-choose_card_core),
div[data-testid="stVerticalBlock"]:has(> .st-key-choose_card_pro),
div[data-testid="stVerticalBlock"]:has(> .st-key-choose_card_coach) { min-height: 578px !important; }
div[data-testid="stVerticalBlock"]:has(> .st-key-choose_card_free) > .st-key-choose_card_free,
div[data-testid="stVerticalBlock"]:has(> .st-key-choose_card_core) > .st-key-choose_card_core,
div[data-testid="stVerticalBlock"]:has(> .st-key-choose_card_pro) > .st-key-choose_card_pro,
div[data-testid="stVerticalBlock"]:has(> .st-key-choose_card_coach) > .st-key-choose_card_coach { margin-top: auto !important; }
div[data-testid="stVerticalBlock"]:has(> .st-key-choose_card_free) { border: 1.5px solid rgba(139,148,158,.72) !important; border-radius: 14px !important; box-shadow: 0 0 0 1px rgba(139,148,158,.20), 0 10px 28px rgba(0,0,0,.22) !important; }
div[data-testid="stVerticalBlock"]:has(> .st-key-choose_card_core) { border: 1.5px solid rgba(255,107,53,.86) !important; border-radius: 14px !important; box-shadow: 0 0 0 1px rgba(255,107,53,.26), 0 10px 28px rgba(0,0,0,.24) !important; }
div[data-testid="stVerticalBlock"]:has(> .st-key-choose_card_pro) { border: 1.5px solid rgba(240,192,64,.82) !important; border-radius: 14px !important; box-shadow: 0 0 0 1px rgba(240,192,64,.24), 0 10px 28px rgba(0,0,0,.24) !important; }
div[data-testid="stVerticalBlock"]:has(> .st-key-choose_card_coach) { border: 1.5px solid rgba(248,81,73,.82) !important; border-radius: 14px !important; box-shadow: 0 0 0 1px rgba(248,81,73,.24), 0 10px 28px rgba(0,0,0,.24) !important; }
.upgrade-note {
    background: rgba(35,134,54,0.08); border: 1px solid rgba(35,134,54,0.28);
    border-radius: 12px; padding: 0.95em 1em; margin-top: 1em;
    color: var(--tc-muted); line-height: 1.65; font-size: 0.9em;
}
@media (max-width: 900px) { .plan-path, .plans-grid { grid-template-columns: 1fr; } }
</style>
<div class="pricing-hero">
    <div class="pricing-hero-title">选择的不是功能,是训练方式</div>
    <div class="pricing-hero-text">Free 让你先看懂数据;Core 让你开始每周按课表训练;Pro 把训练、恢复、营养、目标追踪连起来;Coach 用来管理多个骑手。</div>
</div>
<div class="plan-path">
    <div class="path-step"><div class="k">Free</div><div class="v">体验数据<br>先看懂自己</div></div>
    <div class="path-step"><div class="k">Core</div><div class="v">开始训练<br>每周有课表</div></div>
    <div class="path-step"><div class="k">Pro</div><div class="v">完整闭环<br>训练+恢复+营养</div></div>
    <div class="path-step"><div class="k">Coach</div><div class="v">多骑手管理<br>教练/工作室</div></div>
</div>
""", unsafe_allow_html=True)


def render_upgrade_note():
    st.markdown("""
<div class="upgrade-note">
    <b>怎么升级:</b>内测阶段先使用人工收款确认开通。选择套餐并生成订单后,付款时备注手机号或订单号;管理员确认后会开通对应套餐。<br>
    如果你只是想体验,Free 足够;如果你想真正开始按计划训练,建议从 Core 开始。
</div>
""", unsafe_allow_html=True)



def render_upload_intro():
    st.markdown("""
<style>
.upload-hero {
    padding: 1.25em 1.1em;
    border-radius: 14px;
    background: linear-gradient(135deg, rgba(255,107,53,0.12), rgba(22,27,34,0.92));
    border: 1px solid rgba(255,107,53,0.22);
    margin-bottom: 1em;
}
.upload-hero-title {
    color: #f0f6fc;
    font-size: 1.18em;
    font-weight: 720;
    margin-bottom: 0.35em;
}
.upload-hero-text {
    color: #aab6c3;
    font-size: 0.92em;
    line-height: 1.65;
}
.upload-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.8em;
    margin: 0.9em 0 1.1em;
}
.upload-card {
    background: var(--tc-surface);
    border: 1px solid var(--tc-surface-2);
    border-radius: 12px;
    padding: 0.95em;
    min-height: 112px;
}
.upload-card .title {
    color: #f0f6fc;
    font-weight: 700;
    margin-bottom: 0.35em;
}
.upload-card .text {
    color: var(--tc-subtle);
    font-size: 0.84em;
    line-height: 1.55;
}
.upload-next {
    background: rgba(35,134,54,0.08);
    border: 1px solid rgba(35,134,54,0.28);
    border-radius: 12px;
    padding: 0.95em 1em;
    margin-top: 0.9em;
}
.upload-next .title {
    color: #7ee787;
    font-weight: 720;
    margin-bottom: 0.35em;
}
.upload-next .text {
    color: var(--tc-muted);
    font-size: 0.9em;
    line-height: 1.7;
}
/* Make Streamlit file uploader look like the primary action on this page. */
[data-testid="stFileUploader"] {
    margin: 1.0em 0 1.1em;
    padding: 1.05em 1.08em;
    border-radius: 18px;
    border: 1.5px dashed rgba(255,107,53,0.66);
    background:
        radial-gradient(circle at 18% 10%, rgba(255,255,255,0.10), transparent 30%),
        linear-gradient(135deg, rgba(255,107,53,0.20), rgba(22,27,34,0.97));
    box-shadow: 0 0 28px rgba(255,107,53,0.13), inset 0 0 16px rgba(255,107,53,0.05);
}
[data-testid="stFileUploader"] label,
[data-testid="stFileUploader"] label p {
    color: #f0f6fc !important;
    font-size: 1.08rem !important;
    font-weight: 850 !important;
}
[data-testid="stFileUploader"] section {
    border-color: rgba(255,107,53,0.42) !important;
    background: rgba(255,255,255,0.035) !important;
    border-radius: 14px !important;
}
[data-testid="stFileUploader"] button {
    background: linear-gradient(135deg, #ff7a3d, #ff5a1f) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255,255,255,0.22) !important;
    border-radius: 999px !important;
    font-weight: 850 !important;
    box-shadow: 0 0 16px rgba(255,107,53,0.42) !important;
}
.upload-cta-note {
    margin: 0.9em 0 -0.25em;
    padding: 0.9em 1em;
    border-radius: 14px;
    background: rgba(255,107,53,0.10);
    border: 1px solid rgba(255,107,53,0.26);
    color: #d8dee9;
    line-height: 1.65;
    font-size: 0.92em;
}
.upload-cta-note b { color:#ffb088; }
@media (max-width: 900px) {
    .upload-grid { grid-template-columns: 1fr; }
}
</style>
<div class="upload-hero">
    <div class="upload-hero-title">第一步:把你的真实骑行数据放进来</div>
    <div class="upload-hero-text">
        建议一次上传最近 4-12 周的 FIT 文件。数据越完整,FTP 估算、功率曲线、疲劳抗性和后续 AI 诊断会越稳定。
        如果只有 1-3 次骑行,也可以先上传体验基础分析。
    </div>
</div>
<div class="upload-grid">
    <div class="upload-card">
        <div class="title">⚡ 功率数据</div>
        <div class="text">用于计算 FTP、功率持续曲线、冲刺能力、20min/60min 能力和疲劳抗性。</div>
    </div>
    <div class="upload-card">
        <div class="title">❤️ 心率数据</div>
        <div class="text">用于辅助判断强度反应、恢复压力和训练负荷是否合理。</div>
    </div>
    <div class="upload-card">
        <div class="title">📈 训练负荷</div>
        <div class="text">用于生成 TSS、PMC、周训练量趋势,并为训练课表提供依据。</div>
    </div>
</div>
""", unsafe_allow_html=True)


def render_upload_cta_note():
    st.markdown("""
<div class="upload-cta-note">
    <b>👇 从这里开始:</b>点击下方按钮选择 FIT 文件,或直接把 FIT 文件拖到上传框里。一次最多 28 个,单次总大小最多 50MB;网络不稳定或使用代理时,建议每批 5-10 个 FIT,更稳。
</div>
""", unsafe_allow_html=True)



def render_profile_intro():
    st.markdown("""
<style>
.profile-priority-note {
    position: relative;
    background: linear-gradient(135deg, rgba(255,107,53,0.20), rgba(22,27,34,0.96));
    border: 1px solid rgba(255,107,53,0.42);
    border-radius: 16px;
    padding: 1.05em 1.15em;
    margin: 0.75em 0 1.05em;
    color: #f0f6fc;
    box-shadow: 0 0 22px rgba(255,107,53,0.10), inset 0 0 18px rgba(255,107,53,0.035);
}
.profile-priority-note .tag {
    color:#ff9a68;
    font-size:0.76em;
    font-weight:800;
    letter-spacing:0.10em;
    margin-bottom:0.35em;
}
.profile-priority-note .main {
    font-size:1.02em;
    font-weight:760;
    line-height:1.65;
}
.profile-priority-note .main b {
    color:#ffb088;
    text-shadow:0 0 8px rgba(255,107,53,0.42);
}
.profile-note {
    background: linear-gradient(135deg, rgba(255,107,53,0.10), rgba(22,27,34,0.92));
    border: 1px solid rgba(255,107,53,0.22);
    border-radius: 14px;
    padding: 0.95em 1em;
    margin: 0.7em 0 1em;
    color: #aab6c3;
    font-size: 0.9em;
    line-height: 1.65;
}
.profile-section-title {
    color: #f0f6fc;
    font-size: 1.02em;
    font-weight: 720;
    margin: 0.9em 0 0.45em;
}
.profile-help {
    color: var(--tc-subtle);
    font-size: 0.84em;
    line-height: 1.55;
    margin-bottom: 0.45em;
}
.danger-note {
    color: var(--tc-subtle);
    font-size: 0.82em;
    margin-top: 0.6em;
}
</style>
<div class="profile-priority-note">
    <div class="tag">PROFILE SETUP · 先填这几项</div>
    <div class="main">这些信息会直接影响 <b>FTP、功体比、训练区间、营养建议和 AI 分析</b>。建议优先填写:<b>体重、实测 FTP、最大心率、训练目标</b>。</div>
</div>
<div class="profile-note">
    <b>为什么要填:</b>体重决定 W/kg 和营养建议;FTP 决定功率区间、AI 分析和训练课表;心率用于判断强度反应和恢复压力;训练目标会影响后续建议方向。
</div>
""", unsafe_allow_html=True)


def render_profile_section_title(title: str):
    st.markdown(f'<div class="profile-section-title">{title}</div>', unsafe_allow_html=True)


def render_profile_help(text: str):
    st.markdown(f'<div class="profile-help">{text}</div>', unsafe_allow_html=True)


def render_danger_note(text: str):
    st.markdown(f'<div class="danger-note">{text}</div>', unsafe_allow_html=True)
