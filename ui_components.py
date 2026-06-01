from __future__ import annotations

import base64
from pathlib import Path

import pandas as pd
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


def render_upload_next_steps(new_ride_count: int):
    st.markdown(f"""
<div class="upload-next">
    <div class="title">下一步建议</div>
    <div class="text">
        这 {new_ride_count} 条新解析数据已经并入历史。建议先看 <b>📊 功率仪表盘</b> 理解当前能力结构,
        再进入 <b>🧠 AI 功率分析</b> 获取训练判断;如果你已解锁 Core,可继续生成 <b>📋 训练课表</b>。
    </div>
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



def render_training_feedback_intro():
    st.markdown("""
<style>
.training-feedback-note {
    background: linear-gradient(135deg, rgba(255,107,53,0.10), rgba(22,27,34,0.92));
    border: 1px solid rgba(255,107,53,0.22);
    border-radius: 14px;
    padding: 0.95em 1em;
    margin: 0.7em 0 1em;
    color: #aab6c3;
    font-size: 0.9em;
    line-height: 1.65;
}
.training-feedback-section {
    color: #f0f6fc;
    font-size: 1.02em;
    font-weight: 720;
    margin: 0.9em 0 0.45em;
}
</style>
<div class="training-feedback-note">
    <b>为什么要记录:</b>功率只能告诉你做了多少,反馈能告诉你身体承受得怎么样。感冒、睡眠差、腿沉、膝盖痛、补给不足,都会影响今天该不该继续上强度。
</div>
""", unsafe_allow_html=True)


def render_training_feedback_section(title: str):
    st.markdown(f'<div class="training-feedback-section">{title}</div>', unsafe_allow_html=True)



def render_beta_feedback_intro():
    st.markdown("""
<style>
.feedback-hero {
    padding: 1.08em 1.15em;
    border-radius: 16px;
    background: linear-gradient(135deg, rgba(255,107,53,0.16), rgba(22,27,34,0.96));
    border: 1px solid rgba(255,107,53,0.30);
    margin: 0.8em 0 1.05em;
}
.feedback-hero .k { color:#ff9a68; font-size:0.78em; font-weight:820; letter-spacing:0.10em; margin-bottom:0.35em; }
.feedback-hero .t { color:#f0f6fc; font-size:1.18em; font-weight:780; margin-bottom:0.35em; }
.feedback-hero .d { color:#aab6c3; font-size:0.90em; line-height:1.7; }
.feedback-tip {
    background: var(--tc-surface);
    border: 1px solid var(--tc-border);
    border-radius: 13px;
    padding: 0.9em 1em;
    color: var(--tc-subtle);
    font-size: 0.88em;
    line-height: 1.65;
    margin-bottom: 1em;
}
</style>
<div class="feedback-hero">
  <div class="k">BETA FEEDBACK</div>
  <div class="t">发现问题就直接丢到这里</div>
  <div class="d">越具体越好:在哪个页面、点了什么、看到什么异常、你原本期待它怎么工作。反馈会保存到内测记录里,方便后续集中修复。</div>
</div>
<div class="feedback-tip">
  <b>建议反馈格式:</b>页面 + 操作步骤 + 看到的问题 + 期望结果。比如:"训练负荷页,上传 5 个 FIT 后,切到合并历史,图表没有变化,希望能提示是否已合并。"
</div>
<div class="feedback-tip" style="border-color:rgba(255,107,53,0.28);background:rgba(255,107,53,0.07);">
  <b>如果你只想快速反馈,回答这 3 个问题就够了:</b><br>
  1. 你最喜欢 TrueCadence 的哪个功能?为什么?<br>
  2. 你最不喜欢、最想吐槽的地方是什么?<br>
  3. 如果以后付费,你觉得哪个功能最值得付费?多少钱能接受?
</div>
""", unsafe_allow_html=True)



def render_intervals_manual_import_note():
    st.markdown("""
<div class="upload-cta-note">
<b>Intervals.icu 外部入口:</b>当前为内测临时手动导入方式。如果你还没打开 Intervals.icu,请先登录并进入设置页复制 Athlete ID 与 Personal API Key,然后回到本页导入。正式多用户版本会优先改为 OAuth 授权,不长期要求用户手动填写 API Key。
</div>
""", unsafe_allow_html=True)


def render_strava_export_note():
    st.markdown("""
<div class="upload-cta-note">
<b>Strava 外部入口:</b>Strava OAuth 正在申请接入。当前可先打开 Strava 导出 FIT,再回到 TrueCadence 的 FIT 上传页面分析。
</div>
""", unsafe_allow_html=True)


def render_intervals_oauth_import_note():
    st.markdown("""
<div class="upload-cta-note">
<b>Intervals.icu 导入：</b>本地测试建议优先使用下方 Personal API Key 方式读取和导入活动，避免 OAuth 授权跳到生产服务器。线上版本才使用一键 OAuth 授权。
</div>
""", unsafe_allow_html=True)



def render_training_load_guidance(action_items, stale_notes, red_flags, caution_flags, use_all, has_uploaded_rides, has_recent_feedback, current_tsb_text):
    c1, c2 = st.columns([1.05, 1])
    if stale_notes:
        st.info(";".join(stale_notes))

    with c1:
        st.subheader("接下来怎么练")
        for item in action_items:
            st.markdown(f"- {item}")
        st.markdown(f"""
<div class="load-panel">
    <div class="load-panel-title">怎么理解 CTL / ATL / TSB</div>
    <div class="load-panel-text">
        <b>CTL</b> 是长期训练积累,代表你目前能承受多少训练;<br>
        <b>ATL</b> 是短期疲劳,最近一周练得越猛越高,休息日会按 TSS=0 自然回落,并会从最后一次骑行持续衰减到今天;<br>
        <b>TSB</b> 是当前新鲜度,太低说明疲劳压住了状态,太高则可能训练刺激不足或正在减量。<br><br>
        <b>当前 TSB 解读:</b>{current_tsb_text}<br><br>
        <b>为什么默认合并历史:</b>训练负荷看的是连续刺激和恢复趋势,单次训练只说明当天贡献。系统会先把历史 FIT 和本次上传按日期去重合并,再计算近 7 / 28 / 42 天 TSS、CTL、ATL、TSB;只有临时排查上传文件时,才建议关闭合并历史。关闭合并后,上方 verdict 和"接下来怎么练"会切换为单次上传预览口径,不作为正式训练安排依据。<br><br>
        参考区间:&lt; -25 恢复风险较高;-25 到 -10 负荷较高;-10 到 +5 常规训练区;+5 到 +15 偏新鲜;&gt; +15 可能是比赛/测试前状态,也可能是训练刺激不足。区间不是医学或绝对过度训练判断,要结合睡眠、腿疲劳、晨脉、疼痛和训练阶段。
    </div>
</div>
""", unsafe_allow_html=True)
    with c2:
        st.subheader("风险提示")
        if red_flags:
            for item in red_flags:
                st.error(item)
        if caution_flags:
            for item in caution_flags:
                st.warning(item)
        if not red_flags and not caution_flags:
            st.success("当前没有明显训练负荷风险。")
        if not use_all and has_uploaded_rides:
            st.info("当前关闭合并历史:风险提示只用于本批上传文件排查,正式训练建议请打开合并历史数据。")
        if has_recent_feedback:
            st.caption("最近训练反馈已接入负荷判断。")
        else:
            st.info("还没有训练反馈。去「📝 训练反馈」记录后,负荷判断会更贴近真实状态。")



def render_training_load_styles():
    st.markdown("""
<style>
.load-hero {
    padding: 1.05em 1.1em;
    border-radius: 15px;
    margin: 0.8em 0 1em;
    border: 1px solid rgba(255,107,53,0.28);
    background: linear-gradient(135deg, rgba(255,107,53,0.14), rgba(22,27,34,0.94));
}
.load-eyebrow { color:#ff9a68; font-size:0.76em; font-weight:780; letter-spacing:0.11em; margin-bottom:0.45em; }
.load-main { color:#f0f6fc; font-size:1.45em; font-weight:820; line-height:1.35; margin-bottom:0.25em; }
.load-why { color:var(--tc-muted); line-height:1.65; font-size:0.92em; }
.load-grid { display:grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap:0.75em; margin:0.9em 0 1.1em; }
.load-card { background:var(--tc-surface); border:1px solid var(--tc-surface-2); border-radius:13px; padding:0.85em; }
.load-card .k { color:var(--tc-subtle); font-size:0.76em; margin-bottom:0.25em; }
.load-card .v { color:#f0f6fc; font-size:1.2em; font-weight:780; }
.load-card .d { color:var(--tc-subtle); font-size:0.78em; margin-top:0.25em; line-height:1.4; }
.load-panel { background:var(--tc-surface); border:1px solid var(--tc-surface-2); border-radius:14px; padding:1em; margin:0.75em 0; }
.load-panel-title { color:#f0f6fc; font-weight:760; margin-bottom:0.4em; }
.load-panel-text { color:#aab6c3; line-height:1.65; font-size:0.9em; }
@media (max-width: 900px) { .load-grid { grid-template-columns: 1fr; } }
</style>
""", unsafe_allow_html=True)


def render_training_load_summary(
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
    recent_feedback_count,
    avg_sleep,
    avg_fatigue,
    tsb_caution,
    tsb_red,
    atl_caution,
    atl_red,
    fatigue_caution,
    fatigue_red,
):
    st.markdown(f"""
<div class="load-hero">
    <div class="load-eyebrow">TRAINING LOAD VERDICT</div>
    <div class="load-main">{status_label}</div>
    <div class="load-why">{status_tone}<br><b>判断依据:</b>{reason_text}</div>
</div>
<div class="load-grid">
    <div class="load-card"><div class="k">体能 CTL</div><div class="v">{current_ctl}</div><div class="d">约 6 周训练积累</div></div>
    <div class="load-card"><div class="k">疲劳 ATL</div><div class="v">{current_atl}</div><div class="d">约 1 周近期疲劳</div></div>
    <div class="load-card"><div class="k">状态 TSB</div><div class="v">{current_tsb}</div><div class="d">CTL - ATL,新鲜度</div></div>
    <div class="load-card"><div class="k">近 7 天</div><div class="v">{tss_7} TSS</div><div class="d">{hours_7} 小时训练</div></div>
</div>
<div class="load-grid">
    <div class="load-card"><div class="k">近 28 天</div><div class="v">{tss_28} TSS</div><div class="d">{hours_28} 小时训练</div></div>
    <div class="load-card"><div class="k">近 42 天</div><div class="v">{tss_42} TSS</div><div class="d">{hours_42} 小时训练</div></div>
    <div class="load-card"><div class="k">周均训练</div><div class="v">{avg_weekly_hours}h</div><div class="d">近 28 天折算</div></div>
    <div class="load-card"><div class="k">CTL 变化</div><div class="v">{round(ramp_rate)}</div><div class="d">近 7 天变化</div></div>
</div>
<div class="load-grid">
    <div class="load-card"><div class="k">数据跨度</div><div class="v">{data_span_days} 天</div><div class="d">历史负荷可信度基础</div></div>
    <div class="load-card"><div class="k">历史 / 本次 TSS</div><div class="v">{history_tss} / {upload_tss}</div><div class="d">本次只作为累计负荷贡献</div></div>
    <div class="load-card"><div class="k">单次最新贡献</div><div class="v">{latest_ride_tss} TSS</div><div class="d">不再孤立判断训练负荷</div></div>
    <div class="load-card"><div class="k">风险档位</div><div class="v">{risk_mode}</div><div class="d">{risk_desc}</div></div>
</div>
<div class="load-grid">
    <div class="load-card"><div class="k">主观反馈</div><div class="v">{recent_feedback_count} 条</div><div class="d">睡眠 {avg_sleep or '-'} / 腿疲劳 {avg_fatigue or '-'}</div></div>
    <div class="load-card"><div class="k">TSB 阈值</div><div class="v">{tsb_caution} / {tsb_red}</div><div class="d">黄色 / 红色提醒线</div></div>
    <div class="load-card"><div class="k">ATL-CTL 阈值</div><div class="v">+{atl_caution} / +{atl_red}</div><div class="d">黄色 / 红色提醒线</div></div>
    <div class="load-card"><div class="k">主观疲劳阈值</div><div class="v">{fatigue_caution} / {fatigue_red}</div><div class="d">黄色 / 红色提醒线</div></div>
</div>
""", unsafe_allow_html=True)



def render_power_ftp_reference(actual_ftp, est_ftp, ftp, pweight, ftp_detail, best):
    # Show FTP source. Training calculations always prefer manually tested FTP when available.
    if actual_ftp > 0:
        st.success(f"当前使用 FTP: **{actual_ftp}W**(来源:用户实测)· 功体比: **{round(actual_ftp/pweight, 1)} W/kg**")
        st.caption(f"自动估算 FTP:{est_ftp}W,仅作参考;依据:{ftp_detail.get('basis', '-')};可信度:{ftp_detail.get('confidence', '-') }。训练区间、AI 分析和课表优先使用实测 FTP。")
    else:
        st.info(f"当前使用自动估算 FTP: **{est_ftp}W** · 功体比: **{round(est_ftp/pweight, 1)} W/kg**")
        st.caption(f"估算依据:{ftp_detail.get('basis', '-')};可信度:{ftp_detail.get('confidence', '-') }。如有正式 FTP 测试,请在骑手档案页填写实测 FTP。")

    if actual_ftp > 0 and est_ftp > 0 and abs(actual_ftp - est_ftp) / actual_ftp > 0.12:
        st.warning(f"自动估算 ({est_ftp}W) 与实测 FTP ({actual_ftp}W) 差异较大。当前训练建议以实测 FTP 为准;自动值仅说明已上传数据里的可见证据。")
    elif actual_ftp > 0 and best.get('20min', 0) >= actual_ftp * 0.98:
        st.info(f"已上传数据中存在接近/达到当前 FTP 的 20min 记录(20min {best.get('20min', 0)}W),当前实测 FTP 可信度较高。")

    window_rows = ftp_detail.get('window_rows') or []
    with st.expander("FTP 多窗口参考:20 / 40 / 60 分钟", expanded=False):
        st.caption("自动估算不会只看一个 20min 窗口。普通骑行中的 20min best 容易混入无氧贡献,默认按 ×0.85-0.90 理解;40min 按约 ×0.95;60min 本身接近 FTP 概念,通常不再额外打折。训练区间仍优先使用你在骑手档案填写的实测 FTP。")
        if window_rows:
            st.dataframe(pd.DataFrame(window_rows), use_container_width=True, hide_index=True)
        else:
            st.info("当前数据还没有足够的 20/40/60min 有效功率窗口。建议上传最近 4-12 周、包含较长稳定输出的 FIT 后再看。")
        p20_ref = ftp_detail.get('best_20') or best.get('20min', 0)
        p40_ref = ftp_detail.get('best_40') or best.get('40min', 0)
        p60_ref = ftp_detail.get('best_60') or best.get('60min', 0)
        if p20_ref and (p40_ref or p60_ref):
            long_ref = max([x for x in [p40_ref, p60_ref] if x])
            if p20_ref > long_ref * 1.12:
                st.warning("20min 明显高于 40/60min 参考,自动 FTP 可能偏乐观;建议结合实测 FTP 或更长时间测试。")
            elif p60_ref and p60_ref >= ftp * 0.90:
                st.success("已有较好的 60min 支撑记录,FTP 估算可信度相对更高。")



def render_power_profile_and_durability(fatigue, durability_summary, profile_rows, peer_sample_count, min_peer_samples, total_ride_count):
    st.subheader("⚡ 功率画像 - 固定参考线 / 同水平分位数")
    if any(v.get('rating_source') == 'peer_percentile' for v in fatigue.values()):
        st.caption("当前评级优先采用同 FTP W/kg 水平用户分位数;固定参考线保留为解释和兜底。")
    else:
        st.caption(f"当前同水平样本量不足({peer_sample_count}/{min_peer_samples}),评级暂用 TrueCadence 内测固定参考线;样本积累后会自动切换为同水平用户分位数。")
    if profile_rows:
        st.dataframe(pd.DataFrame(profile_rows).astype(str), use_container_width=True, hide_index=True)
    st.caption("短时窗口更看 W/kg 分位数;20min/60min 更看占 FTP 比例。FIT 数据如果没有做过对应时长全力测试,画像只代表已上传数据里的可见能力。")

    st.subheader("🔋 疲劳抗性 2.0 - 后程还能不能输出")
    st.caption("上半部分看功率曲线持续能力;下半部分在新上传 FIT 有逐点功率时,会进一步判断后半程保持能力。后程可分析骑行只统计时长和逐点功率足够计算后程保持的记录;短骑或数据不足记录不会计入。")

    if durability_summary:
        b = durability_summary['best_score']
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            render_mini_metric_card("后程保持评分", f"{durability_summary['avg_score']}", "多次骑行平均")
        with c2:
            render_mini_metric_card("平均后半程衰减", f"{durability_summary['avg_drop']}%")
        with c3:
            render_mini_metric_card("最佳单次评级", b.get('rating', '-'), f"{b.get('score', 0)} 分")
        with c4:
            render_mini_metric_card("后程可分析骑行", f"{durability_summary['count']} 条", f"总记录 {total_ride_count} 条")
        render_vertical_spacer(14)
        dur_rows = []
        for x in durability_summary['items'][:8]:
            dur_rows.append({
                '日期': x.get('date', ''),
                '时长': f"{x.get('duration_min', 0)} min",
                '评分': x.get('score', 0),
                '评级': x.get('rating', ''),
                '后半程衰减': f"{x.get('half_drop_pct', 0)}%",
                '后半程5min保持': f"{x.get('late_5m_retention', 0)}%",
                '后半程20min保持': f"{x.get('late_20m_retention', 0)}%" if x.get('late_20m_retention') else '-',
                '60min后5min': f"{x.get('after_60_5m', 0)}W" if x.get('after_60_5m') else '-',
                '60min后20min': f"{x.get('after_60_20m', 0)}W" if x.get('after_60_20m') else '-',
            })
        st.dataframe(pd.DataFrame(dur_rows).astype(str), use_container_width=True, hide_index=True)
        if durability_summary['avg_score'] >= 86:
            st.success("后程保持能力较好:长距离或训练后段仍能保留较高输出,可以逐步加入更专项的后段质量刺激。")
        elif durability_summary['avg_score'] >= 78:
            st.info("后程保持能力中等:基础耐力可以,但长骑后段的甜区/阈值保持仍有提升空间。")
        else:
            st.warning("后程保持能力偏弱:建议先补 Z2 长距离、甜区耐力和补给策略,不要过早堆高强度。")
    else:
        st.info("疲劳抗性 2.0 需要新上传的 FIT 包含逐点功率数据。旧历史摘要仍可显示功率曲线评分;重新上传最近 4-12 周 FIT 后会更准。")



def render_power_dashboard_top_metrics(ftp, pweight, best, ride_count):
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    wkg = round(ftp / pweight, 1) if ftp and pweight else 0
    col1.metric("FTP", f"{ftp}W", f"{wkg} W/kg" if wkg else "")
    s5_wkg = round(best.get('5s', 0) / pweight, 1) if best.get('5s') and pweight else ""
    col2.metric("5s 冲刺", f"{best.get('5s', 0)}W", f"{s5_wkg} W/kg" if s5_wkg else "")
    p20 = best.get('20min', 0)
    col3.metric("20min 功率", f"{p20}W", f"{round(p20 / ftp * 100)}% FTP" if ftp and p20 else "")
    p40 = best.get('40min', 0)
    col4.metric("40min 功率", f"{p40}W", f"{round(p40 / ftp * 100)}% FTP" if ftp and p40 else "")
    p60 = best.get('60min', 0)
    col5.metric("60min 功率", f"{p60}W", f"{round(p60 / ftp * 100)}% FTP" if ftp and p60 else "")
    col6.metric("总骑行次数", ride_count, f"{ride_count} 条记录")


def render_vertical_spacer(height_px: int = 12):
    st.markdown(f'<div style="height:{int(height_px)}px"></div>', unsafe_allow_html=True)



def render_nutrition_intro():
    st.markdown("""
<style>
.nutrition-hero {
    padding: 1.15em 1.1em;
    border-radius: 15px;
    background: linear-gradient(135deg, rgba(255,107,53,0.13), rgba(22,27,34,0.94));
    border: 1px solid rgba(255,107,53,0.25);
    margin: 0.8em 0 1em;
}
.nutrition-title { color:#f0f6fc; font-size:1.15em; font-weight:760; margin-bottom:0.35em; }
.nutrition-text { color:#aab6c3; font-size:0.9em; line-height:1.65; }
.nutrition-grid { display:grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap:0.75em; margin:0.9em 0 1.1em; }
.nutrition-card { background:var(--tc-surface); border:1px solid var(--tc-surface-2); border-radius:13px; padding:0.85em; }
.nutrition-card .k { color:var(--tc-subtle); font-size:0.76em; margin-bottom:0.25em; }
.nutrition-card .v { color:#f0f6fc; font-size:1.18em; font-weight:760; }
.nutrition-card .d { color:var(--tc-subtle); font-size:0.78em; margin-top:0.25em; line-height:1.4; }
.nutrition-advice { border-radius:16px; padding:1.05em 1.1em; margin:1em 0; border:1px solid rgba(255,107,53,0.34); background:linear-gradient(135deg, rgba(255,107,53,0.16), rgba(22,27,34,0.95)); }
.nutrition-advice .tag { color:#ff9a68; font-size:0.78em; font-weight:760; letter-spacing:0.08em; margin-bottom:0.4em; }
.nutrition-advice .main { font-size:1.38em; font-weight:800; color:#f0f6fc; margin-bottom:0.35em; }
.nutrition-advice .why { color:var(--tc-muted); line-height:1.65; font-size:0.92em; }
@media (max-width: 900px) { .nutrition-grid { grid-template-columns: 1fr; } }
</style>
<div class="nutrition-hero">
    <div class="nutrition-title">补给不是吃得越多越好,而是刚好支持今天的输出</div>
    <div class="nutrition-text">系统会根据体重、训练时长、强度、天气和训练反馈,给出每小时碳水、水、钠,以及训练前/中/后的执行建议。</div>
</div>
""", unsafe_allow_html=True)


def render_nutrition_target(
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
    feedback_count,
):
    st.markdown(f"""
<div class="nutrition-advice">
    <div class="tag">TODAY FUELING TARGET</div>
    <div class="main">每小时 {carb_lo}-{carb_hi}g 碳水 · {water_lo}-{water_hi}ml 水 · {sodium_lo}-{sodium_hi}mg 钠</div>
    <div class="why"><b>依据:</b>{workout_type}|{ride_hours}h|{environment}|体重 {weight}kg。{intensity_note}</div>
</div>
<div class="nutrition-grid">
    <div class="nutrition-card"><div class="k">本次总碳水</div><div class="v">{total_carb_lo}-{total_carb_hi}g</div><div class="d">约 {max(0, round(total_carb_lo/25))}-{max(1, round(total_carb_hi/25))} 根能量胶</div></div>
    <div class="nutrition-card"><div class="k">本次总饮水</div><div class="v">{total_water_lo}-{total_water_hi}ml</div><div class="d">分 15-20 分钟小口喝</div></div>
    <div class="nutrition-card"><div class="k">本次总钠</div><div class="v">{total_sodium_lo}-{total_sodium_hi}mg</div><div class="d">热天/室内优先补足</div></div>
    <div class="nutrition-card"><div class="k">反馈接入</div><div class="v">{feedback_count} 条</div><div class="d">低血糖/胃不适/高温会修正建议</div></div>
</div>
""", unsafe_allow_html=True)



def render_nutrition_timing_guidance(pre_carb, pre_protein, post_carb, post_protein):
    st.subheader("训练前 / 训练中 / 训练后")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown(f"""
**训练前 2-3 小时**
- 碳水:**{pre_carb}g**
- 蛋白:**{pre_protein}g**
- 低脂、低纤维,别吃太撑
""")
    with col_b:
        st.markdown("""
**训练中**
- 每 15-20 分钟吃/喝一次
- 不要等饿了再补
- >60g/h 建议葡萄糖+果糖组合
""")
    with col_c:
        st.markdown(f"""
**训练后 30 分钟内**
- 碳水:**{post_carb}g**
- 蛋白:**{post_protein}g**
- 强度课后优先补碳水
""")


def render_nutrition_quick_reference():
    st.subheader("按训练类型快速参考")
    rows = [
        ["恢复骑", "0-20g/h", "400-600ml/h", "0-300mg/h", "不饿不硬吃,重点恢复"],
        ["Z2 长距离", "50-70g/h", "500-750ml/h", "300-600mg/h", "从前 20 分钟开始补"],
        ["甜区/阈值", "60-80g/h", "600-850ml/h", "500-800mg/h", "训练前必须吃够"],
        ["VO2max/间歇", "50-70g/h", "600-850ml/h", "500-800mg/h", "别让胃太撑,小口补"],
        ["比赛/绕圈赛", "80-100g/h", "750-1000ml/h", "700-1000mg/h", "只用训练中测试过的补给"],
    ]
    st.dataframe(pd.DataFrame(rows, columns=["训练类型", "碳水", "水", "钠", "重点"]).astype(str), use_container_width=True, hide_index=True)



def render_nutrition_feedback_adjustments(fueling_set, special_set, weight, ftp, feedback_count):
    st.subheader("根据最近反馈的修正")
    if fueling_set or special_set:
        if "低血糖感" in fueling_set or "吃少了" in fueling_set:
            st.warning("你最近记录过低血糖感/吃少了:下次训练前 2-3 小时必须吃正餐,训练中碳水提前到前 15-20 分钟开始。")
        if "胃不舒服" in fueling_set:
            st.warning("你最近记录过胃不舒服:不要一下冲到 90g/h,先从 40-60g/h 做肠胃训练,并分小口摄入。")
        if "喝少了" in fueling_set:
            st.warning("你最近记录过喝少了:把水壶按时间喝,不要只凭口渴。")
        if "天气太热" in special_set:
            st.warning("近期有高温记录:饮水和钠已上调;热天强度课更容易心率漂移。")
        if "睡眠不足" in special_set or "工作压力大" in special_set:
            st.info("近期睡眠/压力不理想:不要用咖啡因硬顶长期疲劳,优先保证晚间恢复。")
    else:
        st.info("最近反馈没有明显补给风险。建议关键训练后继续记录:吃少了、胃不舒服、低血糖感、喝少了。")

    st.caption(f"数据依据:体重 {weight}kg;FTP {ftp or '-'}W;训练反馈 {feedback_count} 条。补给建议用于训练辅助,不替代医学或营养师建议。")



def render_recovery_intro():
    st.markdown("""
<style>
.recovery-hero {
    padding: 1.15em 1.1em;
    border-radius: 15px;
    background: linear-gradient(135deg, rgba(255,107,53,0.12), rgba(22,27,34,0.94));
    border: 1px solid rgba(255,107,53,0.24);
    margin: 0.8em 0 1em;
}
.recovery-title { color:#f0f6fc; font-size:1.15em; font-weight:760; margin-bottom:0.35em; }
.recovery-text { color:#aab6c3; font-size:0.9em; line-height:1.65; }
.recovery-grid { display:grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap:0.75em; margin:0.9em 0 1.1em; }
.recovery-card { background:var(--tc-surface); border:1px solid var(--tc-surface-2); border-radius:13px; padding:0.85em; }
.recovery-card .k { color:var(--tc-subtle); font-size:0.76em; margin-bottom:0.25em; }
.recovery-card .v { color:#f0f6fc; font-size:1.18em; font-weight:760; }
.recovery-card .d { color:var(--tc-subtle); font-size:0.78em; margin-top:0.25em; line-height:1.4; }
.recovery-advice { border-radius:16px; padding:1.05em 1.1em; margin:1em 0; border:1px solid; }
.recovery-advice .tag { font-size:0.78em; font-weight:760; letter-spacing:0.08em; margin-bottom:0.4em; }
.recovery-advice .main { font-size:1.45em; font-weight:800; color:#f0f6fc; margin-bottom:0.35em; }
.recovery-advice .why { color:var(--tc-muted); line-height:1.65; font-size:0.92em; }
.recovery-red { background:linear-gradient(135deg, rgba(248,81,73,0.16), rgba(22,27,34,0.95)); border-color:rgba(248,81,73,0.36); }
.recovery-yellow { background:linear-gradient(135deg, rgba(240,192,64,0.14), rgba(22,27,34,0.95)); border-color:rgba(240,192,64,0.34); }
.recovery-green { background:linear-gradient(135deg, rgba(35,134,54,0.14), rgba(22,27,34,0.95)); border-color:rgba(35,134,54,0.34); }
.recovery-blue { background:linear-gradient(135deg, rgba(88,166,255,0.14), rgba(22,27,34,0.95)); border-color:rgba(88,166,255,0.34); }
@media (max-width: 900px) { .recovery-grid { grid-template-columns: 1fr; } }
</style>
<div class="recovery-hero">
    <div class="recovery-title">今天不是问"能不能练",而是问"练多重才值得"</div>
    <div class="recovery-text">系统会综合 TSB/训练负荷、最近训练反馈、睡眠、腿疲劳、RPE、感冒发烧和疼痛记录,给出当天训练建议。</div>
</div>
""", unsafe_allow_html=True)


def render_recovery_advice_summary(
    advice_class,
    advice_tag,
    advice_main,
    reasons,
    tsb,
    ctl,
    atl,
    weekly_h,
    feedback_count,
    watch_sleep_hours,
    watch_sleep_score,
    watch_hrv,
    avg_nap_min,
    nap_refresh_count,
    nap_sluggish_count,
):
    st.markdown(f"""
<div class="recovery-advice {advice_class}">
    <div class="tag">{advice_tag}</div>
    <div class="main">{advice_main}</div>
    <div class="why"><b>主要依据:</b>{';'.join(reasons[:6])}</div>
</div>
<div class="recovery-grid">
    <div class="recovery-card"><div class="k">TSB 状态</div><div class="v">{tsb}</div><div class="d">CTL {ctl} / ATL {atl}</div></div>
    <div class="recovery-card"><div class="k">近两周周均</div><div class="v">{weekly_h}h</div><div class="d">来自 FIT 训练记录</div></div>
    <div class="recovery-card"><div class="k">训练反馈</div><div class="v">{feedback_count} 条</div><div class="d">最近主观状态</div></div>
    <div class="recovery-card"><div class="k">手表睡眠</div><div class="v">{watch_sleep_hours or '-'}h</div><div class="d">评分 {watch_sleep_score or '-'} / HRV {watch_hrv or '-'}</div></div>
    <div class="recovery-card"><div class="k">午睡修正</div><div class="v">{str(avg_nap_min) + 'min' if avg_nap_min else '-'}</div><div class="d">更清醒 {nap_refresh_count} 次 / 更困 {nap_sluggish_count} 次</div></div>
</div>
""", unsafe_allow_html=True)



def render_goal_styles():
    st.markdown("""
<style>
.goal-hero { padding:1.1em; border-radius:15px; margin:0.8em 0 1em; border:1px solid rgba(255,107,53,0.28); background:linear-gradient(135deg, rgba(255,107,53,0.14), rgba(22,27,34,0.94)); }
.goal-tag { color:#ff9a68; font-size:0.76em; font-weight:780; letter-spacing:0.12em; margin-bottom:0.45em; }
.goal-main { color:#f0f6fc; font-size:1.42em; font-weight:820; line-height:1.35; margin-bottom:0.25em; }
.goal-why { color:var(--tc-muted); line-height:1.65; font-size:0.92em; }
.goal-grid { display:grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap:0.75em; margin:0.9em 0 1.1em; }
.goal-card { background:var(--tc-surface); border:1px solid var(--tc-surface-2); border-radius:13px; padding:0.85em; }
.goal-card .k { color:var(--tc-subtle); font-size:0.76em; margin-bottom:0.25em; }
.goal-card .v { color:#f0f6fc; font-size:1.16em; font-weight:780; }
.goal-card .d { color:var(--tc-subtle); font-size:0.78em; margin-top:0.25em; line-height:1.4; }
.goal-step { background:var(--tc-surface); border:1px solid var(--tc-border); border-radius:14px; padding:0.9em; margin:0.55em 0; }
.goal-step .t { color:#f0f6fc; font-weight:780; margin-bottom:0.25em; }
.goal-step .x { color:#aab6c3; font-size:0.9em; line-height:1.6; }
@media (max-width: 900px) { .goal-grid { grid-template-columns: 1fr; } }
</style>
""", unsafe_allow_html=True)


def render_goal_verdict_summary(
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
    recent_feedback_count,
    avg_sleep,
    avg_fatigue,
    event_date,
):
    st.markdown(f"""
<div class="goal-hero">
    <div class="goal-tag">GOAL VERDICT</div>
    <div class="goal-main">{verdict}</div>
    <div class="goal-why">{verdict_text}</div>
</div>
<div class="goal-grid">
    <div class="goal-card"><div class="k">当前 FTP</div><div class="v">{ftp}W</div><div class="d">{current_wkg} W/kg</div></div>
    <div class="goal-card"><div class="k">目标</div><div class="v">{target_ftp}W</div><div class="d">{target_wkg} W/kg|差 {ftp_gap:+}W</div></div>
    <div class="goal-card"><div class="k">预计需要</div><div class="v">{needed_weeks}周</div><div class="d">设定周期 {target_weeks_n}周</div></div>
    <div class="goal-card"><div class="k">训练承载</div><div class="v">{weekly_h}h/周</div><div class="d">{capacity}</div></div>
</div>
<div class="goal-grid">
    <div class="goal-card"><div class="k">体能 CTL</div><div class="v">{ctl}</div><div class="d">长期训练积累</div></div>
    <div class="goal-card"><div class="k">状态 TSB</div><div class="v">{tsb}</div><div class="d">当前新鲜度</div></div>
    <div class="goal-card"><div class="k">反馈接入</div><div class="v">{recent_feedback_count} 条</div><div class="d">睡眠 {avg_sleep or '-'} / 腿疲劳 {avg_fatigue or '-'}</div></div>
    <div class="goal-card"><div class="k">目标日期</div><div class="v">{event_date}</div><div class="d">用于阶段倒推</div></div>
</div>
""", unsafe_allow_html=True)



def render_ai_analysis_styles():
    st.markdown("""
<style>
.ai-panel {
    background: var(--tc-surface);
    border: 1px solid var(--tc-surface-2);
    border-radius: 14px;
    padding: 1em;
    margin: 0.8em 0 1em;
}
.ai-panel.hot {
    background: linear-gradient(135deg, rgba(255,107,53,0.13), rgba(22,27,34,0.92));
    border-color: rgba(255,107,53,0.28);
}
.ai-panel.good {
    background: linear-gradient(135deg, rgba(35,134,54,0.12), rgba(22,27,34,0.92));
    border-color: rgba(35,134,54,0.28);
}
.ai-panel-title {
    color: #f0f6fc;
    font-size: 1.02em;
    font-weight: 720;
    margin-bottom: 0.35em;
}
.ai-panel-text {
    color: #aab6c3;
    font-size: 0.88em;
    line-height: 1.65;
}
.ai-small-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.75em;
    margin: 0.8em 0 1em;
}
.ai-mini {
    background: rgba(13,17,23,0.72);
    border: 1px solid var(--tc-border);
    border-radius: 12px;
    padding: 0.8em;
}
.ai-mini .k {
    color: var(--tc-subtle);
    font-size: 0.76em;
    margin-bottom: 0.25em;
}
.ai-mini .v {
    color: #f0f6fc;
    font-weight: 720;
}
@media (max-width: 900px) {
    .ai-small-grid { grid-template-columns: 1fr; }
}
</style>
""", unsafe_allow_html=True)


def render_ai_usage_panel(unlimited_ai, plan_name, quota_text, billing_rule_text):
    st.markdown(f"""
<div class="ai-panel hot">
    <div class="ai-panel-title">本次分析会做什么?</div>
    <div class="ai-panel-text">
        AI 会读取当前选择的数据范围,判断 FTP、骑手类型、训练量、疲劳抗性和待改善区间。
        <b>{'Pro / Coach 分析不扣次数' if unlimited_ai else '只有点击「🔬 开始 AI 分析」才会消耗 1 次额度'}</b>;切换数据范围、查看训练一致性不会扣次数。
    </div>
</div>
<div class="ai-small-grid">
    <div class="ai-mini"><div class="k">当前套餐</div><div class="v">{plan_name}</div></div>
    <div class="ai-mini"><div class="k">本月剩余额度</div><div class="v">{quota_text}</div></div>
    <div class="ai-mini"><div class="k">扣费规则</div><div class="v">{billing_rule_text}</div></div>
</div>
""", unsafe_allow_html=True)


def render_ai_cached_notice(cached_at, unlimited_ai):
    cache_note = f"|生成时间 {cached_at}" if cached_at else ""
    st.markdown(f"""
<div class="ai-panel good">
    <div class="ai-panel-title">诊断已保留</div>
    <div class="ai-panel-text">下方结果来自当前数据范围{cache_note}。切换页面回来不会重复扣次数;{'Pro / Coach 点击重新分析也不扣次数。' if unlimited_ai else '只有点击重新分析才会重新生成并消耗 1 次额度。'}</div>
</div>
""", unsafe_allow_html=True)



def render_plan_builder_styles():
    st.markdown("""
<style>
.plan-hero{padding:1.1em 1.15em;border-radius:16px;background:linear-gradient(135deg,rgba(255,107,53,.16),rgba(22,27,34,.96));border:1px solid rgba(255,107,53,.28);margin:.6em 0 1em}.plan-kicker{color:#ff9a68;font-size:.78em;font-weight:800;letter-spacing:.08em}.plan-title{color:#f0f6fc;font-size:1.45em;font-weight:850;margin:.25em 0}.plan-sub{color:#aab6c3;font-size:.9em;line-height:1.6}.plan-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.7em;margin:.8em 0 1em}.plan-card{background:var(--tc-surface);border:1px solid var(--tc-border);border-radius:13px;padding:.85em;min-height:5.6em}.plan-card .k{color:var(--tc-subtle);font-size:.72em}.plan-card .v{color:#f0f6fc;font-size:1.08em;font-weight:800;margin:.18em 0}.plan-card .d{color:var(--tc-subtle);font-size:.75em;line-height:1.35}.plan-day{background:var(--tc-surface);border:1px solid var(--tc-border);border-radius:10px;padding:.68em .66em;min-height:12em;margin:.15em 0}.plan-day .dow{color:var(--tc-subtle);font-size:.68em;font-weight:800}.plan-day .name{color:#f0f6fc;font-size:.82em;font-weight:800;margin-top:.28em;line-height:1.25}.plan-day .detail{color:var(--tc-subtle);font-size:.68em;margin-top:.35em;line-height:1.35;min-height:2.4em}.plan-pill{display:inline-block;background:var(--tc-surface-2);border-radius:5px;padding:.12em .42em;margin:.15em .16em .05em 0;font-size:.62em}.plan-warning{padding:.85em 1em;border-radius:12px;background:rgba(240,192,64,.1);border:1px solid rgba(240,192,64,.28);color:#d8c58a;font-size:.86em;line-height:1.55}@media(max-width:1050px){.plan-grid{grid-template-columns:1fr 1fr}}@media(max-width:720px){.plan-grid{grid-template-columns:1fr}}
</style>
""", unsafe_allow_html=True)


def render_plan_builder_intro():
    st.markdown("""
<div class="plan-hero">
  <div class="plan-kicker">TRAINING PLAN BUILDER</div>
  <div class="plan-title">先判断这周该怎么练,再生成可执行课表</div>
  <div class="plan-sub">根据 FIT 推算 FTP / 功体比,并结合训练负荷、睡眠/反馈、目标、可训练天数和周总量,动态生成本周重点、周期递进和 Zwift .ZWO 文件。</div>
</div>
""", unsafe_allow_html=True)


def render_plan_summary_cards(pm, ftp, wkg, weight, first, key_text, load_note):
    st.markdown(f"""
<div class="plan-grid">
  <div class="plan-card"><div class="k">当前阶段</div><div class="v">{pm['icon']} {pm['name']}</div><div class="d">{pm['desc']}</div></div>
  <div class="plan-card"><div class="k">功率基础</div><div class="v">FTP {ftp}W</div><div class="d">{wkg} W/kg · {weight}kg</div></div>
  <div class="plan-card"><div class="k">本周主题</div><div class="v" style="font-size:.96em;">{first['theme']}</div><div class="d">{first['theme_desc']}</div></div>
  <div class="plan-card"><div class="k">关键训练</div><div class="v" style="font-size:.96em;">{key_text}</div><div class="d">{load_note}</div></div>
</div>
""", unsafe_allow_html=True)



def render_goal_phase_path(phase_rows):
    st.subheader("阶段路径")
    st.dataframe(pd.DataFrame(phase_rows).astype(str), use_container_width=True, hide_index=True)


def render_goal_action_and_risk(actions, risk_flags, feasible, ftp, ftp_gap, target_ftp):
    c_left, c_right = st.columns([1.05, 1])
    with c_left:
        st.subheader("本周动作")
        for a_item in actions:
            st.markdown(f"- {a_item}")
    with c_right:
        st.subheader("风险与调整")
        if risk_flags:
            for r in risk_flags:
                st.warning(r)
        else:
            st.success("当前目标没有明显红旗。")
        if not feasible:
            mid = round(ftp + max(0, ftp_gap) / 2)
            st.info(f"建议中间目标:先到 **{mid}W**,稳定 2-3 周后再冲 **{target_ftp}W**。")
        st.caption("目标估算不是承诺值。真正决定进度的是连续性、恢复、补给和训练执行质量。")


def render_goal_reassessment_notes():
    st.subheader("什么时候重新评估")
    st.markdown("""
- **每 4 周**:重新看 FTP、CTL/ATL/TSB 和最近反馈。
- **连续两周疲劳高或睡眠差**:目标不一定错,但推进速度要降。
- **比赛前 7-10 天**:不再追训练量,改为保持状态和降低疲劳。
- **疼痛重复出现**:先处理身体/装备/姿势,不要继续用训练计划硬压。
""")
