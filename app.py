# TrueCadence - 个人版
# 部署:streamlit run app.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
from plotly.subplots import make_subplots
import json, os, sys, tempfile, datetime, math, hashlib, base64
from pathlib import Path

pio.templates.default = "plotly_dark"

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))
from fitparse import FitFile
from auth import (
    load_users, save_users, register_user, login_user,
    add_rider, delete_rider, add_subscription_days, redeem_code, PLANS,
    gen_invite_code, redeem_invite, consume_invite,
    get_ai_usage, increment_ai_usage, get_ai_limit,
    load_rider_rides, load_rider_profile, save_rider_profile, save_rider_data,
    get_user_dir, get_rider_data_path, DATA_DIR,
)

st.set_page_config(
    page_title="TrueCadence",
    page_icon="🚴",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Fixed Dark Theme ───
pio.templates.default = "plotly_dark"

# ─── App Paths / Brand Logo ───
ASSET_DIR = Path(os.environ.get("TRUECADENCE_ASSET_DIR", APP_DIR / "assets"))
TC_LOGO_PATH = Path(os.environ.get("TRUECADENCE_LOGO_PATH", ASSET_DIR / "truecadence_mark_cutout.png"))

def load_tc_logo_svg():
    try:
        raw = TC_LOGO_PATH.read_bytes()
        ext = TC_LOGO_PATH.suffix.lower()
        mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png" if ext == ".png" else "image/svg+xml"
        return f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")
    except Exception:
        return ""

# ─── Global CSS ───
st.markdown("""
<style>

:root {
    --tc-bg:#0d1117; --tc-bg-soft:#111827; --tc-surface:#161b22; --tc-surface-2:#21262d;
    --tc-card:#161b22; --tc-card-2:#1b2430; --tc-border:#30363d;
    --tc-text:#e6edf3; --tc-muted:#c9d1d9; --tc-subtle:#8b949e;
    --tc-shadow:rgba(0,0,0,.28); --tc-accent:#ff7a12; --tc-accent-soft:rgba(255,107,53,.12);
}
/* Base typography */
html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
}
html, body, .stApp, [data-testid="stAppViewContainer"] {
    background: var(--tc-bg) !important;
    color: var(--tc-text) !important;
}
[data-testid="stHeader"] {
    background: color-mix(in srgb, var(--tc-bg) 78%, transparent) !important;
}
.block-container {
    background: transparent !important;
}
h1, h2, h3, h4 { font-weight: 600; letter-spacing: -0.02em; }
h1 { font-size: 2em !important; }
h2 { font-size: 1.4em !important; color: var(--tc-text) !important; }
h3 { font-size: 1.15em !important; color: var(--tc-muted) !important; }

/* Left-align ALL tables globally */
[data-testid="stDataFrameResizable"] table td,
[data-testid="stDataFrameResizable"] table th,
table td, table th {
    text-align: left !important;
}

/* Cards: wrap metrics and dataframes */
[data-testid="stMetric"] {
    background: var(--tc-surface);
    border: 1px solid var(--tc-surface-2);
    border-radius: 10px;
    padding: 1em !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}
[data-testid="stMetric"] label {
    color: var(--tc-subtle) !important;
    font-size: 0.78em;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 1.8em !important;
    font-weight: 700;
    color: #ffa25c !important;
}
[data-testid="stMetric"] [data-testid="stMetricDelta"] {
    color: var(--tc-subtle) !important;
    font-size: 0.82em;
}

/* Dataframe tables */
[data-testid="stDataFrame"] {
    background: var(--tc-surface);
    border: 1px solid var(--tc-surface-2);
    border-radius: 10px;
    overflow: hidden;
}
[data-testid="stDataFrame"] th {
    background: var(--tc-surface-2) !important;
    color: var(--tc-muted) !important;
    font-weight: 600;
    font-size: 0.8em;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
[data-testid="stDataFrame"] td {
    background: var(--tc-surface) !important;
    color: var(--tc-text) !important;
}

/* Inputs */
[data-testid="stNumberInput"] input, [data-testid="stTextInput"] input {
    background: var(--tc-surface) !important;
    border: 1px solid var(--tc-border) !important;
    border-radius: 8px !important;
    color: var(--tc-text) !important;
}
.stSelectbox [data-baseweb="select"] > div {
    background: var(--tc-surface) !important;
    border: 1px solid var(--tc-border) !important;
    border-radius: 8px !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #ff6b35 0%, #e85d2c 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em;
    transition: all 0.2s;
}
.stButton > button:hover {
    box-shadow: 0 0 16px rgba(255,107,53,0.3);
    transform: translateY(-1px);
}

/* Expander / tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: var(--tc-surface);
    border-radius: 10px 10px 0 0;
    padding: 0 4px;
}
.stTabs [data-baseweb="tab"] {
    color: var(--tc-subtle) !important;
    font-weight: 500;
    padding: 0.6em 1.2em;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    color: #ff6b35 !important;
    border-bottom: 2px solid #ff6b35 !important;
}

/* Success / Info / Warning boxes */
[data-testid="stSuccess"], [data-testid="stInfo"], [data-testid="stWarning"], [data-testid="stError"] {
    border-radius: 10px !important;
}

/* Progress bar */
[data-testid="stProgress"] > div > div {
    background: linear-gradient(90deg, #ff6b35, #ffa25c) !important;
    border-radius: 4px;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--tc-bg);
    border-right: 1px solid var(--tc-surface-2);
}
[data-testid="stSidebar"] label, [data-testid="stSidebar"] span {
    color: var(--tc-muted) !important;
}
[data-testid="stSidebar"] .stRadio label {
    color: var(--tc-subtle) !important;
}
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] [aria-checked="true"] {
    color: #ff6b35 !important;
}

/* Captions */
.stCaption { color: #6e7681 !important; font-size: 0.85em; }

/* Divider */
hr {
    border-color: var(--tc-surface-2) !important;
}

/* Markdown table */
[data-testid="stMarkdown"] table {
    background: var(--tc-surface);
    border-radius: 10px;
    overflow: hidden;
}
[data-testid="stMarkdown"] table th {
    background: var(--tc-surface-2) !important;
    color: var(--tc-muted) !important;
    font-weight: 600;
}
[data-testid="stMarkdown"] table td {
    background: var(--tc-surface) !important;
    color: var(--tc-text) !important;
}

/* Plotly toolbar bg */
.js-plotly-plot .plotly .modebar {
    background: transparent !important;
}
</style>
""", unsafe_allow_html=True)

# ─── Auth / Login ───
if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.rider = "默认骑手"

if st.session_state.user is None:
    logo_uri = load_tc_logo_svg()
    st.markdown("""
<style>
.block-container {
    padding-top: 2.6rem !important;
    max-width: 1180px !important;
}
.tc-auth-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.18fr) 340px;
    gap: 3.2rem;
    align-items: center;
    min-height: calc(100vh - 7.5rem);
}
.tc-clean-hero {
    position: relative;
    padding: 0.6rem 0 1rem;
}
.tc-clean-hero::before {
    content:"";
    position:absolute;
    left:-8%; top:-16%;
    width: 520px; height: 520px;
    border-radius:999px;
    background: radial-gradient(circle, rgba(255,107,53,0.16), rgba(255,107,53,0.045) 42%, transparent 68%);
    filter: blur(1px);
    z-index:0;
}
.tc-brand-line {
    position:relative;
    z-index:1;
    display:flex;
    align-items:center;
    gap:0.82rem;
    margin-bottom:2.1rem;
}
.tc-brand-line img {
    width:70px;
    height:46px;
    object-fit:contain;
    filter: drop-shadow(0 0 10px rgba(255,107,53,0.45));
}
.tc-brand-word {
    font-size:2.08rem;
    font-weight:800;
    letter-spacing:0.055em;
    line-height:1;
    background: linear-gradient(110deg, #ff7a12 0%, #ff7a12 32%, #ffe0cf 48%, #ff7a12 68%, #ff7a12 100%);
    background-size:260% 100%;
    -webkit-background-clip:text;
    background-clip:text;
    -webkit-text-fill-color:transparent;
    animation: tcCleanShine 7s linear infinite;
}
.tc-auth-title span {
    position:relative;
    display:inline-block;
    color:#ff7a12;
    -webkit-text-fill-color:#ff7a12;
    text-shadow: 0 0 6px rgba(255,107,53,0.72), 0 0 18px rgba(255,107,53,0.32), 0 0 30px rgba(255,107,53,0.16);
    animation: tcLetterPulse 4.8s ease-in-out infinite;
    overflow:visible;
}
.tc-auth-title span::after {
    content: attr(data-letter);
    position:absolute;
    inset:0;
    color:#fff7ee;
    -webkit-text-fill-color:#fff7ee;
    text-shadow:0 0 8px rgba(255,255,255,0.82), 0 0 16px rgba(255,206,170,0.46);
    opacity:0;
    animation: tcLetterSweep 4.6s linear infinite;
}
.tc-auth-title span:nth-child(2n) { animation-delay: .16s; }
.tc-auth-title span:nth-child(3n) { animation-delay: .31s; }
.tc-auth-title span:nth-child(5n) { animation-delay: .47s; }
.tc-auth-title span:nth-child(1)::after { animation-delay: 0.00s; }
.tc-auth-title span:nth-child(2)::after { animation-delay: 0.10s; }
.tc-auth-title span:nth-child(3)::after { animation-delay: 0.20s; }
.tc-auth-title span:nth-child(4)::after { animation-delay: 0.30s; }
.tc-auth-title span:nth-child(5)::after { animation-delay: 0.40s; }
.tc-auth-title span:nth-child(6)::after { animation-delay: 0.50s; }
.tc-auth-title span:nth-child(7)::after { animation-delay: 0.60s; }
.tc-auth-title span:nth-child(8)::after { animation-delay: 0.70s; }
.tc-auth-title span:nth-child(9)::after { animation-delay: 0.80s; }
.tc-auth-title span:nth-child(10)::after { animation-delay: 0.90s; }
.tc-auth-title span:nth-child(11)::after { animation-delay: 1.00s; }
@keyframes tcLetterPulse {
    0%, 100% { transform: translateY(0) scaleY(0.92); filter: brightness(1); }
    45% { transform: translateY(-3.2px) scaleY(1.03); filter: brightness(1.18); }
    62% { transform: translateY(1.2px) scaleY(0.89); filter: brightness(0.98); }
}
@keyframes tcLetterSweep {
    0%, 8% { opacity:0; }
    10%, 15% { opacity:0.92; }
    19%, 100% { opacity:0; }
}
.tc-brand-caption {
    color:var(--tc-subtle);
    font-size:0.72rem;
    letter-spacing:0.18em;
    margin-top:0.35rem;
}
.tc-main-title {
    position:relative;
    z-index:1;
    color:#f0f6fc;
    font-size: clamp(2.45rem, 5.5vw, 4.55rem);
    line-height:1.04;
    font-weight:840;
    letter-spacing:-0.06em;
    max-width:760px;
    margin:0 0 1.15rem;
}
.tc-main-title span { color:#ff7a12; }
.tc-main-copy {
    position:relative;
    z-index:1;
    max-width:710px;
    color:#aab6c3;
    font-size:.92rem;
    line-height:1.85;
    margin-bottom:1.65rem;
}
.tc-main-copy b { color:#f0f6fc; }
.tc-pill-row {
    position:relative;
    z-index:1;
    display:flex;
    flex-wrap:wrap;
    gap:0.62rem;
    margin-bottom:1.55rem;
}
.tc-pill {
    padding:0.45rem 0.72rem;
    border-radius:999px;
    color:#d8dee9;
    background:rgba(255,255,255,0.045);
    border:1px solid rgba(255,255,255,0.075);
    font-size:0.82rem;
}
.tc-philosophy-line {
    position:relative;
    z-index:1;
    color:#ffb088;
    font-size:0.92rem;
    letter-spacing:0.10em;
    margin-top:2.3rem;
}
.tc-login-brand {
    display:block;
    margin:0 0 1.16rem;
    padding:0.08rem 0 0.58rem;
    border-bottom:1px solid rgba(255,107,53,0.14);
}
.tc-login-brand .word {
    font-size:2.16rem;
    font-weight:840;
    line-height:1;
    letter-spacing:-0.02em;
    background: linear-gradient(110deg, #ff7a12 0%, #ff7a12 34%, #ffe0cf 50%, #ff7a12 70%, #ff7a12 100%);
    background-size:260% 100%;
    -webkit-background-clip:text;
    background-clip:text;
    -webkit-text-fill-color:transparent;
    animation: tcCleanShine 7s linear infinite;
}
.tc-login-brand .cap {
    color:var(--tc-subtle);
    font-size:0.72rem;
    letter-spacing:0.15em;
    margin-top:0.28rem;
}
.tc-login-panel {
    padding:1.05rem 1.0rem 0.95rem;
    border-radius:20px;
    background:rgba(22,27,34,0.72);
    border:1px solid rgba(255,107,53,0.18);
    box-shadow:0 18px 48px rgba(0,0,0,0.26), inset 0 1px 0 rgba(255,255,255,0.04);
    backdrop-filter: blur(8px);
}
.tc-login-panel [data-testid="stForm"] { border:0 !important; padding:0 !important; }
.tc-login-panel [data-testid="stTextInput"] { margin-bottom:-0.36rem; }
.tc-login-panel [data-testid="stTextInput"] label { font-size:0.78rem !important; }
.tc-login-panel [data-testid="stTextInput"] input {
    min-height:2.25rem !important;
    height:2.25rem !important;
    padding:0.32rem 0.62rem !important;
    font-size:0.86rem !important;
    border-radius:10px !important;
}
.tc-login-panel button[kind="primaryFormSubmit"] {
    min-height:2.28rem !important;
    height:2.28rem !important;
    border-radius:10px !important;
    font-size:0.88rem !important;
}
.tc-login-panel [data-baseweb="tab-list"] { margin-bottom:-0.18rem !important; }
.tc-login-panel [data-baseweb="tab"] { height:2.15rem !important; padding:0.38rem 0.64rem !important; }
.tc-login-panel [data-testid="stCaptionContainer"] { font-size:0.74rem !important; }
.tc-auth-center {
    max-width: 620px;
    margin: 4.0vh auto 0;
    text-align: center;
}
.tc-auth-title {
    font-family: 'Aptos Display', 'Segoe UI Variable Display', 'Inter', system-ui, sans-serif;
    font-size: clamp(2.34rem, 4.0vw, 3.38rem);
    font-weight: 500;
    letter-spacing: 0.035em;
    line-height: 0.9;
    margin: 0 0 1.64rem;
    background: linear-gradient(112deg, #ff6b35 0%, #ff8a2a 30%, #ffd0b6 50%, #ff7a12 68%, #ff6b35 100%);
    background-size:260% 100%;
    -webkit-background-clip:text;
    background-clip:text;
    -webkit-text-fill-color:transparent;
    filter: drop-shadow(0 0 8px rgba(255,107,53,0.60)) drop-shadow(0 0 22px rgba(255,107,53,0.26));
    animation: tcCleanShine 7s linear infinite;
}
.tc-philosophy-card {
    max-width: 500px;
    margin: 0 auto 1.45rem;
    padding: 0.82rem 1.08rem 0.88rem;
    border-radius: 16px;
    background: rgba(22,27,34,0.62);
    border: 1px solid rgba(255,107,53,0.16);
    box-shadow: 0 14px 38px rgba(0,0,0,0.20), inset 0 1px 0 rgba(255,255,255,0.035);
    backdrop-filter: blur(8px);
}
.tc-philosophy-card .eyebrow {
    color:#ff7a12;
    font-size:0.68rem;
    font-weight:780;
    letter-spacing:0.24em;
    margin-bottom:0.58rem;
}
.tc-philosophy-card .main {
    color:#f0f6fc;
    font-size:1.14rem;
    font-weight:680;
    letter-spacing:0.11em;
    margin-bottom:0.68rem;
    text-shadow:
        0 0 1px rgba(255,122,18,0.95),
        0 0 6px rgba(255,107,53,0.62),
        0 0 16px rgba(255,107,53,0.30),
        0 0 28px rgba(255,107,53,0.14);
}
.tc-philosophy-card .copy {
    color:#d8dee9;
    font-size:0.88rem;
    line-height:1.72;
    max-width:440px;
    margin:0 auto;
    text-shadow:
        0 0 1px rgba(255,255,255,0.82),
        0 0 7px rgba(255,255,255,0.24),
        0 0 14px rgba(255,206,170,0.12);
}
.tc-auth-center [data-baseweb="tab-list"] { justify-content:center; }
@keyframes tcCleanShine { 0% { background-position:220% 0; } 100% { background-position:-80% 0; } }
@media (max-width: 900px) {
    .tc-auth-grid { grid-template-columns:1fr; gap:1.6rem; min-height:auto; }
    .tc-login-panel { max-width:360px; }
    .tc-auth-title { font-size:3.15rem; }
}
</style>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="tc-auth-center">
  <div class="tc-auth-title"><span data-letter="T">T</span><span data-letter="r">r</span><span data-letter="u">u</span><span data-letter="e">e</span><span data-letter="C">C</span><span data-letter="a">a</span><span data-letter="d">d</span><span data-letter="e">e</span><span data-letter="n">n</span><span data-letter="c">c</span><span data-letter="e">e</span></div>
  <div class="tc-philosophy-card">
    <div class="eyebrow">TRUE CADENCE PHILOSOPHY</div>
    <div class="main">慢下来 · 成为自己的节奏</div>
    <div class="copy">不是追求别人的速度，而是在训练、生活和选择里，找到真正属于自己的节奏</div>
  </div>
</div>
""", unsafe_allow_html=True)

    _spacer_l, center, _spacer_r = st.columns([0.68, 1.36, 0.68], gap="large")
    with center:
        tab1, tab2 = st.tabs(["🔑 登录", "📝 注册"])

        with tab1:
            with st.form("login_form"):
                login_phone = st.text_input("手机号", placeholder="输入手机号", key="login_phone")
                login_pw = st.text_input("密码", type="password", placeholder="输入密码", key="login_pw")
                st.caption("安全提示：建议使用浏览器/手机密码管理器保存密码；TrueCadence 不会在链接中保存登录凭证。")
                login_submit = st.form_submit_button("登录", type="primary", use_container_width=True)
            if login_submit:
                if not login_phone or not login_pw:
                    st.error("请填写手机号和密码")
                else:
                    ok, msg, user_data = login_user(login_phone.strip(), login_pw)
                    if ok and user_data:
                        st.session_state.user = user_data
                        st.session_state.rider = user_data.get("active_rider", "默认骑手")
                        st.rerun()
                    else:
                        st.error(msg)

        with tab2:
            with st.form("register_form"):
                reg_invite = st.text_input("内测邀请码 *", placeholder="输入内测邀请码（必填）", key="reg_invite")
                reg_phone = st.text_input("手机号", placeholder="输入手机号", key="reg_phone")
                reg_pw = st.text_input("设置密码", type="password", placeholder="大小写字母+数字/符号, 6位以上", key="reg_pw")
                if reg_pw:
                    checks = []
                    checks.append("✅ ≥6位" if len(reg_pw) >= 6 else "❌ ≥6位")
                    import re as _re
                    checks.append("✅ 大写" if _re.search(r'[A-Z]', reg_pw) else "❌ 大写")
                    checks.append("✅ 小写" if _re.search(r'[a-z]', reg_pw) else "❌ 小写")
                    has_sym = _re.search(r'[0-9!@#$%^&*(),.?' + '"' + r':{}|<>_\-+=]', reg_pw)
                    checks.append("✅ 数字/符号" if has_sym else "❌ 数字/符号")
                    st.caption(" | ".join(checks))
                st.caption("需内测邀请码方可注册")
                reg_submit = st.form_submit_button("注册", type="primary", use_container_width=True)
            if reg_submit:
                if not reg_invite.strip():
                    st.error("请输入内测邀请码")
                elif not reg_phone:
                    st.error("请输入手机号")
                else:
                    ok, msg = register_user(reg_phone.strip(), reg_pw, reg_invite)
                    if ok:
                        st.success("注册成功！正在登录...")
                        _, _, user_data = login_user(reg_phone.strip(), reg_pw)
                        if user_data:
                            st.session_state.user = user_data
                            st.session_state.rider = user_data.get("active_rider", "默认骑手")
                            st.rerun()
                    else:
                        st.error(msg)
    st.stop()




# ─── Sidebar ───
side_logo_uri = load_tc_logo_svg()
st.sidebar.markdown("""
<style>
.tc-side-brand-wrap {
    text-align:center;
    padding:0.48em 0.5em 0.6em;
    margin-bottom:0.5em;
    background:transparent;
    border:0;
}
.tc-side-symbol {
    position: relative;
    width: 92px;
    height: 56px;
    margin: 0 auto 0.24em;
    border-radius: 14px;
    overflow: visible;
    filter: drop-shadow(0 0 6px rgba(255,107,53,0.72)) drop-shadow(0 0 18px rgba(255,107,53,0.32)) drop-shadow(0 0 30px rgba(255,107,53,0.16));
    animation: tcSideLogoPulse 4.8s ease-in-out infinite;
}
.tc-side-symbol img { width:100%; height:100%; object-fit:contain; display:block; }
.tc-side-shine-word {
    display: inline-block;
    font-family: 'Aptos Display', 'Segoe UI Variable Display', 'Inter', system-ui, sans-serif;
    font-size: 1.75em;
    letter-spacing: 0.035em;
    font-weight: 500;
    line-height: 0.9;
    filter: drop-shadow(0 0 8px rgba(255,107,53,0.60)) drop-shadow(0 0 22px rgba(255,107,53,0.26));
}
.tc-side-shine-word span {
    position:relative;
    display:inline-block;
    color:#ff7a12;
    -webkit-text-fill-color:#ff7a12;
    text-shadow: 0 0 6px rgba(255,107,53,0.72), 0 0 18px rgba(255,107,53,0.32), 0 0 30px rgba(255,107,53,0.16);
    animation: tcSideLetterPulse 4.8s ease-in-out infinite;
    overflow:visible;
}
.tc-side-shine-word span::after {
    content: attr(data-letter);
    position:absolute;
    inset:0;
    color:#fff7ee;
    -webkit-text-fill-color:#fff7ee;
    text-shadow:0 0 8px rgba(255,255,255,0.82), 0 0 16px rgba(255,206,170,0.46);
    opacity:0;
    animation: tcSideLetterSweep 4.6s linear infinite;
}
.tc-side-shine-word span:nth-child(2n) { animation-delay: .16s; }
.tc-side-shine-word span:nth-child(3n) { animation-delay: .31s; }
.tc-side-shine-word span:nth-child(5n) { animation-delay: .47s; }
.tc-side-shine-word span:nth-child(1)::after { animation-delay: 0.00s; }
.tc-side-shine-word span:nth-child(2)::after { animation-delay: 0.10s; }
.tc-side-shine-word span:nth-child(3)::after { animation-delay: 0.20s; }
.tc-side-shine-word span:nth-child(4)::after { animation-delay: 0.30s; }
.tc-side-shine-word span:nth-child(5)::after { animation-delay: 0.40s; }
.tc-side-shine-word span:nth-child(6)::after { animation-delay: 0.50s; }
.tc-side-shine-word span:nth-child(7)::after { animation-delay: 0.60s; }
.tc-side-shine-word span:nth-child(8)::after { animation-delay: 0.70s; }
.tc-side-shine-word span:nth-child(9)::after { animation-delay: 0.80s; }
.tc-side-shine-word span:nth-child(10)::after { animation-delay: 0.90s; }
.tc-side-shine-word span:nth-child(11)::after { animation-delay: 1.00s; }
@keyframes tcSideLogoPulse {
    0%, 100% {
        transform: translateY(0) scaleY(0.92);
        filter: brightness(1) drop-shadow(0 0 6px rgba(255,107,53,0.72)) drop-shadow(0 0 18px rgba(255,107,53,0.32)) drop-shadow(0 0 30px rgba(255,107,53,0.16));
    }
    45% {
        transform: translateY(-3.2px) scaleY(1.03);
        filter: brightness(1.18) drop-shadow(0 0 8px rgba(255,255,255,0.34)) drop-shadow(0 0 16px rgba(255,206,170,0.46)) drop-shadow(0 0 26px rgba(255,107,53,0.34));
    }
    62% {
        transform: translateY(1.2px) scaleY(0.89);
        filter: brightness(0.98) drop-shadow(0 0 6px rgba(255,107,53,0.72)) drop-shadow(0 0 18px rgba(255,107,53,0.32)) drop-shadow(0 0 30px rgba(255,107,53,0.16));
    }
}
@keyframes tcSideLetterPulse { 0%, 100% { transform: translateY(0) scaleY(0.92); filter: brightness(1); } 45% { transform: translateY(-3.2px) scaleY(1.03); filter: brightness(1.18); } 62% { transform: translateY(1.2px) scaleY(0.89); filter: brightness(0.98); } }
@keyframes tcSideLetterSweep { 0%, 8% { opacity:0; } 10%, 15% { opacity:0.92; } 19%, 100% { opacity:0; } }
.tc-side-slogan {
    margin-top:0.4em;
    font-size:0.7em;
    letter-spacing:0.15em;
    color:#d8c7bb;
    text-shadow:0 0 5px rgba(255,122,18,0.66), 0 0 13px rgba(255,107,53,0.40), 0 0 24px rgba(255,107,53,0.18);
    filter: drop-shadow(0 0 6px rgba(255,107,53,0.26));
}
</style>
<div class="tc-side-brand-wrap">
    <div class="tc-side-symbol"><img src=""" + side_logo_uri + """ alt="TrueCadence symbol" /></div>
    <div class="tc-side-shine-word"><span data-letter="T">T</span><span data-letter="r">r</span><span data-letter="u">u</span><span data-letter="e">e</span><span data-letter="C">C</span><span data-letter="a">a</span><span data-letter="d">d</span><span data-letter="e">e</span><span data-letter="n">n</span><span data-letter="c">c</span><span data-letter="e">e</span></div>
    <div class="tc-side-slogan">慢下来 · 成为自己的节奏</div>
</div>
""", unsafe_allow_html=True)

# ─── Rider Selector ───
user = st.session_state.user
plan_info = PLANS.get(user["plan"], PLANS["free"])
riders = list(user.get("riders", {}).keys())
user_level = plan_info.get("level", 0)

# Calculate remaining days
expires_str = user.get("expires", "")
remaining = 0
if expires_str:
    from datetime import date
    remaining = (date.fromisoformat(expires_str) - date.today()).days

st.sidebar.caption(f"👤 {user['phone'][:3]}****{user['phone'][-4:]}")
st.sidebar.caption(f"📦 {plan_info['name']} · {len(riders)}/{plan_info['riders']}骑手")
if remaining > 0 and remaining < 9999:
    if remaining <= 7:
        st.sidebar.warning(f"⏰ 剩余 {remaining} 天 (即将到期)")
    else:
        st.sidebar.caption(f"⏳ 剩余 {remaining} 天")

if len(riders) > 1:
    current = st.session_state.get("rider", riders[0])
    if current not in riders:
        current = riders[0]
    idx = riders.index(current)
    selected = st.sidebar.selectbox("🏍️ 当前骑手", riders, index=idx, key="rider_select")
    if selected != st.session_state.get("rider"):
        st.session_state.rider = selected
        st.cache_data.clear()
        st.rerun()
else:
    st.sidebar.caption("🏍️ 默认骑手")

try:
    _sidebar_history_count = len(load_rider_rides(user["user_id"], st.session_state.get("rider", "默认骑手")))
except Exception:
    _sidebar_history_count = 0
st.sidebar.caption(f"📁 训练存档 {_sidebar_history_count} 条")

with st.sidebar.expander("⚙️ 管理骑手"):
    new_name = st.text_input("新骑手名称", placeholder="输入名称", key="new_rider_name")
    if st.button("添加骑手", key="add_rider_btn", use_container_width=True):
        if new_name.strip():
            ok, msg = add_rider(user["user_id"], new_name.strip())
            if ok:
                users = load_users()
                st.session_state.user = {"user_id": user["user_id"], **users[user["user_id"]]}
                st.rerun()
            else:
                st.error(msg)
        else:
            st.error("请输入骑手名称")
    if len(riders) > 1:
        st.divider()
        del_name = st.selectbox("删除骑手", ["-- 选择 --"] + [r for r in riders if r != st.session_state.get("rider", riders[0])], key="del_rider")
        if st.button("🗑️ 删除选中骑手", key="del_rider_btn", use_container_width=True):
            if del_name != "-- 选择 --":
                ok, msg = delete_rider(user["user_id"], del_name)
                if ok:
                    users = load_users()
                    st.session_state.user = {"user_id": user["user_id"], **users[user["user_id"]]}
                    st.session_state.rider = users[user["user_id"]].get("active_rider", riders[0])
                    st.success(msg)
                    st.cache_data.clear()
                else:
                    st.error(msg)
            else:
                st.error("请选择要删除的骑手")

with st.sidebar.expander("⬆️ 升级套餐"):
    current_plan = user.get("plan", "free")
    plan_order = ["free", "core", "pro", "coach"]
    upgrades = [k for k in plan_order if plan_order.index(k) > plan_order.index(current_plan)]
    if upgrades:
        st.caption(f"当前：{PLANS[current_plan]['name']}")
        for plan_key in upgrades:
            plan_d = PLANS[plan_key]
            dur_labels = " · ".join([f"{d}{p['price']}" for d, p in plan_d["durations"].items()])
            if st.button(f"{plan_d['name']}  ({dur_labels})", key=f"up_{plan_key}", use_container_width=True):
                st.session_state["upgrade_to"] = plan_key
                st.session_state.pop("upgrade_dur", None)
        if st.session_state.get("upgrade_to"):
            target = st.session_state["upgrade_to"]
            st.info(f"升级到 {PLANS[target]['name']}")
            # Show duration options
            dur_opts = PLANS[target]["durations"]
            dur_choice = st.selectbox("付费周期", list(dur_opts.keys()),
                                      format_func=lambda d: f"{d} · {dur_opts[d]['price']} · {dur_opts[d]['days']}天",
                                      key="upgrade_dur")
            st.caption(f"价格：{dur_opts[dur_choice]['price']} / {dur_opts[dur_choice]['days']}天")
            code = st.text_input("输入内测邀请码", placeholder="联系客服获取", key="activate_code")
            if st.button("确认升级", key="confirm_upgrade", use_container_width=True):
                if code.strip():
                    ok, msg = redeem_code(user["user_id"], code.strip().upper())
                    if ok:
                        users = load_users()
                        st.session_state.user = {"user_id": user["user_id"], **users[user["user_id"]]}
                        st.session_state.pop("upgrade_to", None)
                        st.success(msg)
                        st.cache_data.clear()
                    else:
                        st.error(msg)
                else:
                    st.error("请输入内测邀请码")
    else:
        st.success(f"已是最高套餐：{PLANS[current_plan]['name']}")

if st.sidebar.button("🚪 退出登录", use_container_width=True):
    st.session_state.user = None
    st.session_state.rider = "默认骑手"
    st.cache_data.clear()
    st.rerun()

st.sidebar.divider()

page = st.sidebar.radio("导航", [
    "🏠 功能说明",
    "👤 骑手档案",
    "📤 上传分析",
    "📊 功率仪表盘",
    "📈 训练负荷",
    "📝 训练反馈",
    "🛌 恢复与睡眠",
    "🧠 AI 功率分析",
    "📋 训练课表",
    "🍝 营养与补给",
    "🎯 目标追踪",
    "🔐 数据隐私",
    "🐞 内测反馈",
    "💎 套餐对比",
])

DATA_FILE = str(APP_DIR / "self_data.json")
PROFILE_FILE = str(APP_DIR / "profile.json")
BETA_FEEDBACK_FILE = DATA_DIR / "beta_feedback.json"


def load_beta_feedback():
    try:
        if BETA_FEEDBACK_FILE.exists():
            with open(BETA_FEEDBACK_FILE, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
    except Exception:
        return []
    return []


def save_beta_feedback(items):
    BETA_FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = BETA_FEEDBACK_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp, BETA_FEEDBACK_FILE)


def load_profile():
    """Load saved client profile for current rider, fallback to defaults"""
    defaults = {'weight': 69, 'height': 175, 'age': 30, 'gender': '男',
                'ftp_test': 0, 'max_hr': 190, 'rest_hr': 60,
                'cycle_enabled': False, 'cycle_last_start': '', 'cycle_length': 28,
                'period_days': 5, 'cycle_sensitivity': '正常'}
    try:
        user = st.session_state.get("user")
        rider = st.session_state.get("rider", "默认骑手")
        if user:
            # Try rider-specific profile first
            p = load_rider_profile(user["user_id"], rider)
            if p:
                for k, v in defaults.items():
                    if k not in p or not p[k]:
                        p[k] = v
                return p
        # Fallback to legacy profile file
        if os.path.exists(PROFILE_FILE):
            with open(PROFILE_FILE, encoding='utf-8') as f:
                p = json.load(f)
            for k, v in defaults.items():
                if k not in p or not p[k]:
                    p[k] = v
            return p
    except:
        pass
    return defaults


def require_plan(min_level: int, page_name: str = ""):
    """Block access if user plan level is below min_level, with upgrade CTA"""
    user = st.session_state.get("user")
    plan = user.get("plan", "free") if user else "free"
    level = PLANS.get(plan, PLANS["free"]).get("level", 0)
    if level < min_level:
        plan_name = PLANS[plan]["name"]
        needed = [PLANS[k]["name"] for k in ["core", "pro", "coach"] if PLANS[k]["level"] >= min_level]
        
        # Feature preview cards
        previews = {
            "📋 训练课表": ("AI根据你的FIT数据自动生成周期化训练计划", "📋", [
                "基于FTP自动计算训练区间",
                "周度课表 + 每日训练内容",
                "一键导出 .ZWO 文件，导入 Zwift",
            ]),
            "🛌 恢复与睡眠": ("实时追踪CTL/ATL/TSB，自动提醒恢复状态", "🛌", [
                "训练负荷 PMC 曲线",
                "疲劳/体能/状态三指标",
                "自动恢复建议 + 睡眠优化",
            ]),
            "🍝 营养与补给": ("根据训练强度和体重，自动计算每日营养需求", "🍝", [
                "训练日/休息日分区营养方案",
                "车上补给时间×强度双维度建议",
                "碳水/蛋白质/脂肪精确到克",
            ]),
            "🎯 目标追踪": ("设定目标FTP，根据可投入时间预估到达路径", "🎯", [
                "目标FTP每周预估增幅",
                "里程碑时间线（每4周）",
                "过度训练风险预警",
            ]),
        }
        
        st.warning(f"🔒 {plan_name} 不支持此功能")
        
        if page_name in previews:
            desc, icon, features = previews[page_name]
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, var(--tc-surface) 0%, var(--tc-bg) 100%); border:1px solid var(--tc-border); border-radius:12px; padding:1.5em; margin:1em 0;">
                <div style="font-size:1.2em; color:#ff6b35; margin-bottom:0.5em;">{icon} <b>{page_name}</b></div>
                <div style="color:var(--tc-muted); font-size:0.95em; margin-bottom:1em;">{desc}</div>
                <div style="color:var(--tc-subtle); font-size:0.85em;">
                    {"<br>".join(f"✦ {f}" for f in features)}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.info(f"💡 升级到 **{'/'.join(needed)}** 即可解锁")
        st.caption("在侧边栏「⬆️ 升级套餐」中使用内测邀请码升级，或联系客服")
        st.stop()


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
    st.caption(f"建议路径：{secondary} → {primary} → 回来看本页结果。")


def load_feedback():
    """Load subjective training feedback for current rider.

    Prefer current rider-specific file. If rider name/session state changed,
    fall back to all feedback_*.json files under current user dir so saved
    feedback is still visible to AI analysis.
    """
    user = st.session_state.get("user")
    rider = st.session_state.get("rider", "默认骑手")
    if not user:
        return []

    def _read_list(path):
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
        except Exception:
            return []
        return []

    try:
        p = get_rider_data_path(user["user_id"], rider, "feedback")
        data = _read_list(p)
        if data:
            return trim_rides_to_recent_weeks(data)
    except Exception:
        pass

    # Fallback: collect all feedback files for this user. This prevents a
    # rider-id mismatch from making AI analysis think there is no feedback.
    merged = []
    try:
        user_dir = get_user_dir(user["user_id"])
        for fp in Path(user_dir).glob("feedback_*.json"):
            merged.extend(_read_list(fp))
        if merged:
            by_date = {}
            for item in merged:
                key = item.get("date") or item.get("created_at") or str(len(by_date))
                by_date[key] = item
            return sorted(by_date.values(), key=lambda x: (x.get("date", ""), x.get("created_at", "")), reverse=True)
    except Exception:
        pass
    return []


def save_feedback(data):
    """Save subjective training feedback for current rider."""
    user = st.session_state.get("user")
    rider = st.session_state.get("rider", "默认骑手")
    if not user:
        return
    save_rider_data(user["user_id"], rider, "feedback", data)


def load_wearable_sleep():
    """Load wearable sleep records for current rider."""
    user = st.session_state.get("user")
    rider = st.session_state.get("rider", "默认骑手")
    if not user:
        return []
    try:
        p = get_rider_data_path(user["user_id"], rider, "wearable_sleep")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
    except Exception:
        pass
    return []


def save_wearable_sleep(data):
    """Save wearable sleep records for current rider."""
    user = st.session_state.get("user")
    rider = st.session_state.get("rider", "默认骑手")
    if not user:
        return
    save_rider_data(user["user_id"], rider, "wearable_sleep", data)

def infer_cycle_status_for_date(item, profile=None):
    """Return explicit or profile-inferred female cycle status.
    item can be: a feedback dict (with cycle_status/date keys) or a datetime.date."""
    if isinstance(item, datetime.date):
        target_date = item
        explicit = None
    else:
        explicit = item.get("cycle_status")
        if explicit and explicit != "不记录":
            return explicit
        target_date = pd.to_datetime(item.get("date"), errors="coerce")
        if pd.isna(target_date):
            return ""
    profile = profile or load_profile()
    if not profile.get("cycle_enabled"):
        return ""
    last_start = profile.get("cycle_last_start") or ""
    if not last_start:
        return ""
    try:
        target_dt = pd.Timestamp(target_date)
        start = pd.to_datetime(last_start, errors="coerce")
        if pd.isna(target_dt) or pd.isna(start):
            return ""
        cycle_len = int(profile.get("cycle_length") or 28)
        period_days = int(profile.get("period_days") or 5)
        day = ((target_dt.normalize() - start.normalize()).days % cycle_len) + 1
        if day <= 2:
            return "经期第1-2天"
        if day <= period_days:
            return f"经期第3-{period_days}天"
        if day <= period_days + 3:
            return "经期后恢复期"
        if abs(day - round(cycle_len / 2)) <= 2:
            return "排卵期附近"
        if day >= cycle_len - 5:
            return "经前期/PMS"
        return "周期正常，无明显影响"
    except Exception:
        return ""


def summarize_recent_feedback(feedback, days=14):
    """Summarize recent subjective feedback for AI diagnosis."""
    if not feedback:
        return {"count": 0, "lines": ["最近没有训练反馈记录；恢复、疼痛和生病风险只能根据功率数据间接判断。"], "risk_flags": [], "last_date": ""}

    today = pd.Timestamp.today().normalize()
    profile = load_profile()
    recent = []
    for item in feedback:
        try:
            d = pd.to_datetime(item.get("date"), errors="coerce")
        except Exception:
            d = pd.NaT
        if pd.notna(d) and (today - d.normalize()).days <= days:
            recent.append(item)
    if not recent:
        recent = sorted(feedback, key=lambda x: x.get("date", ""), reverse=True)[:5]

    def avg(key):
        vals = [x.get(key) for x in recent if isinstance(x.get(key), (int, float))]
        return round(sum(vals) / len(vals), 1) if vals else 0

    pain_counts, special_counts, cycle_counts = {}, {}, {}
    for item in recent:
        for pain in item.get("pains", []) or []:
            pain_counts[pain] = pain_counts.get(pain, 0) + 1
        for special in item.get("specials", []) or []:
            special_counts[special] = special_counts.get(special, 0) + 1
        cycle_status = infer_cycle_status_for_date(item, profile)
        if cycle_status:
            cycle_counts[cycle_status] = cycle_counts.get(cycle_status, 0) + 1

    risk_flags = []
    avg_sleep = avg("sleep_quality")
    avg_fatigue = avg("leg_fatigue")
    avg_rpe = avg("rpe")
    avg_stress = avg("stress")
    if avg_sleep and avg_sleep <= 2.5:
        risk_flags.append("近期睡眠偏差，建议降低高强度密度。")
    if avg_fatigue and avg_fatigue >= 4:
        risk_flags.append("腿部疲劳偏高，下一次质量课前应优先恢复。")
    if avg_rpe and avg_rpe >= 8:
        risk_flags.append("主观强度偏高，注意不要把每次训练都骑成比赛。")
    if avg_stress and avg_stress >= 4:
        risk_flags.append("生活/工作压力偏高，训练恢复储备可能不足。")
    if any(k in special_counts for k in ["感冒", "发烧"]):
        risk_flags.append("近期记录过感冒/发烧，恢复前不建议做 VO2max 或阈值课。")
    if any(k in cycle_counts for k in ["经期第1-2天", "经前期/PMS"]):
        risk_flags.append("近期处在经期前段或经前期，建议结合腹痛、睡眠和腿疲劳调整强度。")
    for pain, n in pain_counts.items():
        if n >= 2:
            risk_flags.append(f"{pain} 不适重复出现 {n} 次，需关注训练量、姿势设定或装备因素。")

    top_pains = "、".join(f"{k}×{v}" for k, v in sorted(pain_counts.items(), key=lambda kv: kv[1], reverse=True)[:4]) or "无明显疼痛记录"
    top_specials = "、".join(f"{k}×{v}" for k, v in sorted(special_counts.items(), key=lambda kv: kv[1], reverse=True)[:4]) or "无特殊情况记录"
    top_cycles = "、".join(f"{k}×{v}" for k, v in sorted(cycle_counts.items(), key=lambda kv: kv[1], reverse=True)[:4]) or "未记录"
    last_date = max((x.get("date", "") for x in recent), default="")
    lines = [
        f"最近反馈：**{len(recent)}** 条，最新记录 **{last_date or '未知日期'}**。",
        f"平均睡眠/精神/腿疲劳/压力/RPE：**{avg_sleep or '-'} / {avg('energy') or '-'} / {avg_fatigue or '-'} / {avg_stress or '-'} / {avg_rpe or '-'}**。",
        f"不适记录：{top_pains}。",
        f"特殊情况：{top_specials}。",
        f"女性周期：{top_cycles}。",
    ]
    if risk_flags:
        lines.append("主观风险：" + "；".join(risk_flags[:5]))
    else:
        lines.append("主观风险：近期没有明显红旗，但仍建议关键强度课后持续记录。")
    return {"count": len(recent), "lines": lines, "risk_flags": risk_flags, "last_date": last_date}

FIT_DIR = str(APP_DIR / "fit")

# ─── Session state init ───
if 'uploaded_rides' not in st.session_state:
    st.session_state.uploaded_rides = []
if 'historical_loaded' not in st.session_state:
    st.session_state.historical = None

# ─── Data loading ───
HISTORY_RETENTION_DAYS = 84


def parse_ride_date(value):
    try:
        dt = pd.to_datetime(value, errors="coerce")
        if pd.notna(dt):
            return dt.normalize()
    except Exception:
        pass
    return pd.NaT


def ride_date_key(r):
    dt = parse_ride_date((r or {}).get("date", ""))
    return dt.strftime("%Y-%m-%d") if pd.notna(dt) else ""


def trim_rides_to_recent_weeks(rides, days=HISTORY_RETENTION_DAYS):
    """Keep at most the latest rolling 12 weeks of ride summaries."""
    valid_dates = [parse_ride_date((r or {}).get("date", "")) for r in (rides or []) if isinstance(r, dict)]
    valid_dates = [d for d in valid_dates if pd.notna(d)]
    if not valid_dates:
        return rides or []
    latest = max(valid_dates)
    cutoff = latest - pd.Timedelta(days=days - 1)
    kept = []
    for r in rides or []:
        if not isinstance(r, dict):
            continue
        dt = parse_ride_date(r.get("date", ""))
        if pd.isna(dt) or dt >= cutoff:
            kept.append(r)
    return sorted(kept, key=lambda x: str(x.get("date", "")))


@st.cache_data(ttl=10)
def load_historical():
    """Load historical session data for current rider"""
    user = st.session_state.get("user")
    rider = st.session_state.get("rider", "默认骑手")
    if user:
        data = load_rider_rides(user["user_id"], rider)
        if data:
            return trim_rides_to_recent_weeks(data)
    # Fallback to legacy
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding='utf-8-sig') as f:
            data = json.load(f)
        if data:
            return data
    return []


def cleanup_old_fit_uploads(temp_dir, hours=48):
    """Keep uploaded FIT originals only for a short testing retention window."""
    cutoff = datetime.datetime.now().timestamp() - hours * 3600
    try:
        for fp in Path(temp_dir).glob("*.fit"):
            try:
                if fp.stat().st_mtime < cutoff:
                    fp.unlink()
            except Exception:
                pass
    except Exception:
        pass



def rolling_best_average(values, window):
    """Return best rolling average over a fixed sample window. Assumes ~1 Hz FIT record samples."""
    if not values or window <= 0 or len(values) < window:
        return 0
    vals = [float(v or 0) for v in values]
    cur = sum(vals[:window])
    best = cur
    for i in range(window, len(vals)):
        cur += vals[i] - vals[i-window]
        if cur > best:
            best = cur
    return round(best / window)

def extract_fit_power_series(fit):
    """Extract ~1Hz power series from FIT record messages."""
    powers = []
    try:
        for msg in fit.get_messages('record'):
            v = msg.get_values()
            pw = v.get('power')
            if pw is None:
                continue
            try:
                pw = float(pw)
            except Exception:
                continue
            if pw < 0 or pw > 2500:
                continue
            powers.append(pw)
    except Exception:
        return []
    return powers

def compute_power_curve_from_series(powers):
    """Compute best rolling powers from a record-level power series."""
    if not powers:
        return {}
    windows = {
        '5s': 5,
        '30s': 30,
        '1min': 60,
        '5min': 300,
        '20min': 1200,
        '60min': 3600,
    }
    curve = {}
    for key, sec in windows.items():
        curve[key] = rolling_best_average(powers, sec)
    return curve

def compute_power_curve_from_fit(fit):
    """Compute best rolling powers from FIT record messages."""
    return compute_power_curve_from_series(extract_fit_power_series(fit))

def best_rolling_after_index(powers, window, start_idx):
    """Best rolling average after a given sample index."""
    if not powers or window <= 0 or len(powers) - start_idx < window:
        return 0
    segment = powers[max(0, start_idx):]
    return rolling_best_average(segment, window)

def compute_durability_from_series(powers, ftp=None):
    """Durability 2.0: evaluate late-ride power retention from record-level power.

    This is different from the classic power curve: it asks whether the rider can still
    produce useful 5/20min power after the ride has already accumulated fatigue.
    """
    if not powers or len(powers) < 1800:  # need at least 30min to say anything useful
        return {}
    total = len(powers)
    first_half = powers[:max(1, total // 2)]
    second_half = powers[total // 2:]
    first_avg = round(sum(first_half) / len(first_half)) if first_half else 0
    second_avg = round(sum(second_half) / len(second_half)) if second_half else 0
    half_drop_pct = round((first_avg - second_avg) / first_avg * 100, 1) if first_avg > 0 else 0

    whole_5m = rolling_best_average(powers, 300)
    whole_20m = rolling_best_average(powers, 1200)
    late_5m = best_rolling_after_index(powers, 300, total // 2)
    late_20m = best_rolling_after_index(powers, 1200, total // 2)
    late_5m_retention = round(late_5m / whole_5m * 100, 1) if whole_5m else 0
    late_20m_retention = round(late_20m / whole_20m * 100, 1) if whole_20m else 0

    after_60_5m = best_rolling_after_index(powers, 300, 3600) if total >= 3900 else 0
    after_60_20m = best_rolling_after_index(powers, 1200, 3600) if total >= 4800 else 0
    after_60_5m_pct_ftp = round(after_60_5m / ftp * 100, 1) if ftp and after_60_5m else 0
    after_60_20m_pct_ftp = round(after_60_20m / ftp * 100, 1) if ftp and after_60_20m else 0

    score_parts = []
    if late_5m_retention:
        score_parts.append(late_5m_retention)
    if late_20m_retention:
        score_parts.append(late_20m_retention)
    if first_avg and second_avg:
        score_parts.append(max(0, 100 - half_drop_pct))
    score = round(sum(score_parts) / len(score_parts), 1) if score_parts else 0
    if score >= 92 and half_drop_pct <= 8:
        rating = "卓越"
    elif score >= 86 and half_drop_pct <= 12:
        rating = "优秀"
    elif score >= 78 and half_drop_pct <= 18:
        rating = "良好"
    elif score >= 68:
        rating = "一般"
    else:
        rating = "待提升"

    return {
        "duration_min": round(total / 60, 1),
        "first_half_avg": first_avg,
        "second_half_avg": second_avg,
        "half_drop_pct": half_drop_pct,
        "whole_5m": whole_5m,
        "late_5m": late_5m,
        "late_5m_retention": late_5m_retention,
        "whole_20m": whole_20m,
        "late_20m": late_20m,
        "late_20m_retention": late_20m_retention,
        "after_60_5m": after_60_5m,
        "after_60_20m": after_60_20m,
        "after_60_5m_pct_ftp": after_60_5m_pct_ftp,
        "after_60_20m_pct_ftp": after_60_20m_pct_ftp,
        "score": score,
        "rating": rating,
    }

@st.cache_data(ttl=600)
def parse_fit_files(files):
    """Parse uploaded FIT files for session data"""
    results = []
    temp_dir = Path(os.environ.get("TRUECADENCE_TMP_DIR", APP_DIR / "tmp_uploads"))
    temp_dir.mkdir(parents=True, exist_ok=True)
    cleanup_old_fit_uploads(temp_dir, hours=48)
    for f in files:
        tmp_path = None
        try:
            raw = f.read()
            file_hash = hashlib.sha256(raw).hexdigest()[:16]
            with tempfile.NamedTemporaryFile(delete=False, suffix='.fit', dir=temp_dir) as tmp:
                tmp.write(raw)
                tmp_path = tmp.name

            fit = FitFile(tmp_path)
            power_series = extract_fit_power_series(fit)
            power_curve = compute_power_curve_from_series(power_series)
            durability = compute_durability_from_series(power_series)
            sessions = list(fit.get_messages('session'))
            if sessions:
                s = sessions[0].get_values()
                start = s.get('start_time')
                results.append({
                    'date': start.strftime('%Y-%m-%d') if start else 'unknown',
                    'dur': round(s.get('total_timer_time', 0) / 60, 1),
                    'dist': round(s.get('total_distance', 0) / 1000, 1),
                    'avg_p': s.get('avg_power', 0) or 0,
                    'np': s.get('normalized_power', 0) or 0,
                    'max_p': s.get('max_power', 0) or 0,
                    'hr_avg': s.get('avg_heart_rate', 0) or 0,
                    'hr_max': s.get('max_heart_rate', 0) or 0,
                    'tss': s.get('training_stress_score', 0) or 0,
                    'cal': s.get('total_calories', 0) or 0,
                    'power_curve': power_curve,
                    'durability': durability,
                    'best_5s': power_curve.get('5s', 0),
                    'best_30s': power_curve.get('30s', 0),
                    'best_1min': power_curve.get('1min', 0),
                    'best_5min': power_curve.get('5min', 0),
                    'best_20min': power_curve.get('20min', 0),
                    'best_60min': power_curve.get('60min', 0),
                    'file_hash': file_hash,
                    'file_name': getattr(f, 'name', ''),
                })
        except Exception as e:
            st.warning(f"解析失败: {f.name} - {e}")
        finally:
            # Testing-stage retention: keep uploaded FIT originals for up to 48h for debugging,
            # then cleanup_old_fit_uploads(...) removes them automatically on later uploads.
            pass
    return results

# ─── FTP estimation ───
def get_effective_ftp(rides):
    p = load_profile()
    if p.get('ftp_test', 0) > 0:
        return p['ftp_test']
    return estimate_ftp(rides)

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

    # 1) Best rolling powers from FIT record data — primary evidence.
    curve_20 = []
    curve_60 = []
    for r in rides or []:
        pc = r.get('power_curve') or {}
        p20 = valid_power(pc.get('20min') or r.get('best_20min'))
        p60 = valid_power(pc.get('60min') or r.get('best_60min'))
        if p20:
            curve_20.append(p20)
        if p60:
            curve_60.append(p60)
    if curve_20:
        candidates.append(max(curve_20) * 0.95)
    if curve_60:
        candidates.append(max(curve_60) * 0.97)

    # 2) Session summary fallback: useful for old data without record-level power curve.
    best_60_avg = max([valid_power(r.get('avg_p')) for r in rides or [] if (r.get('dur', 0) or 0) >= 55], default=0)
    if best_60_avg:
        candidates.append(best_60_avg * 0.97)

    best_20_avg = max([valid_power(r.get('avg_p')) for r in rides or [] if (r.get('dur', 0) or 0) >= 20], default=0)
    if best_20_avg:
        candidates.append(best_20_avg * 0.95)

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
    best_60_curve = 0
    best_20_avg = 0
    best_60_avg = 0
    best_np = 0

    for r in rides or []:
        pc = r.get('power_curve') or {}
        p20 = valid_power(pc.get('20min') or r.get('best_20min'))
        p60 = valid_power(pc.get('60min') or r.get('best_60min'))
        best_20_curve = max(best_20_curve, p20)
        best_60_curve = max(best_60_curve, p60)

        if (r.get('dur', 0) or 0) >= 20:
            best_20_avg = max(best_20_avg, valid_power(r.get('avg_p')))
        if (r.get('dur', 0) or 0) >= 55:
            best_60_avg = max(best_60_avg, valid_power(r.get('avg_p')))
        if (r.get('dur', 0) or 0) >= 30:
            best_np = max(best_np, valid_power(r.get('np')))

    if best_20_curve:
        candidates.append((best_20_curve * 0.95, f"20min 最佳滑动功率 {round(best_20_curve)}W × 0.95", "高"))
    if best_60_curve:
        candidates.append((best_60_curve * 0.97, f"60min 最佳滑动功率 {round(best_60_curve)}W × 0.97", "高"))
    if best_60_avg:
        candidates.append((best_60_avg * 0.97, f"≥55min 整场平均功率 {round(best_60_avg)}W × 0.97", "中"))
    if best_20_avg:
        candidates.append((best_20_avg * 0.95, f"≥20min 整场平均功率 {round(best_20_avg)}W × 0.95", "中低"))
    if best_np:
        candidates.append((best_np * 0.85, f"长时间训练 NP {round(best_np)}W 保守折算", "低"))

    if not candidates:
        return {"ftp": 160, "basis": "缺少有效功率数据，使用默认值", "confidence": "低", "best_20": 0, "best_60": 0}

    val, basis, confidence = max(candidates, key=lambda x: x[0])
    return {"ftp": round(val), "basis": basis, "confidence": confidence, "best_20": round(best_20_curve or best_20_avg), "best_60": round(best_60_curve or best_60_avg)}

def data_scope_caption(rides, historical, uploaded_rides, source_label):
    return f"当前分析：{len(rides)} 条骑行记录｜{source_label}｜本次上传 {len(uploaded_rides)} 条｜历史存档 {len(historical)} 条"


def compute_daily_pmc(rides, ctl_tau=42, atl_tau=7, end_date=None):
    """Compute PMC by natural calendar day, filling rest days with TSS=0.

    Returns a DataFrame with date, tss, ctl, atl, tsb. Multiple rides on the same
    day are summed. By default the timeline extends to today, so CTL/ATL/TSB keep
    decaying naturally after the last uploaded ride, similar to Intervals.icu / PMC.
    """
    cols = ["date", "tss", "ctl", "atl", "tsb"]
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
    daily = df.groupby("date_dt", as_index=True)["tss"].sum().sort_index()
    if end_date is None:
        end_dt = pd.Timestamp.today().normalize()
    else:
        end_dt = pd.to_datetime(end_date, errors="coerce")
        end_dt = end_dt.normalize() if pd.notna(end_dt) else pd.Timestamp.today().normalize()
    end_dt = max(daily.index.max(), end_dt)
    full_index = pd.date_range(daily.index.min(), end_dt, freq="D")
    daily = daily.reindex(full_index, fill_value=0)

    c, a = 0.0, 0.0
    rows = []
    for dt, tss_val in daily.items():
        tss_val = float(tss_val or 0)
        c = c + (tss_val - c) / ctl_tau
        a = a + (tss_val - a) / atl_tau
        rows.append({
            "date": dt.strftime("%Y-%m-%d"),
            "date_dt": dt,
            "tss": round(tss_val, 1),
            "ctl": round(c),
            "atl": round(a),
            "tsb": round(c - a),
        })
    return pd.DataFrame(rows)

def ride_identity(r):
    """Stable-ish key for de-duplicating FIT session summaries."""
    if r.get("file_hash"):
        return f"hash:{r.get('file_hash')}"
    return "|".join(str(r.get(k, "")) for k in ("date", "dur", "dist", "avg_p", "np", "max_p", "hr_avg", "hr_max", "tss"))

def merge_rides(existing, incoming):
    """Merge ride summaries with beta retention rules.

    Rules:
    - Incoming dates replace existing records on the same calendar date.
    - Remaining duplicates are de-duplicated by file_hash/session identity; newest wins.
    - Stored history is capped to the latest 12 weeks.
    """
    incoming = [r for r in (incoming or []) if isinstance(r, dict)]
    existing = [r for r in (existing or []) if isinstance(r, dict)]
    incoming_dates = {ride_date_key(r) for r in incoming if ride_date_key(r)}

    merged = {}
    for r in existing:
        if ride_date_key(r) in incoming_dates:
            continue
        merged[ride_identity(r)] = r
    for r in incoming:
        merged[ride_identity(r)] = r
    return trim_rides_to_recent_weeks(list(merged.values()))

def save_current_rides(rides):
    """Persist current rider history and clear cached historical reads."""
    rides = trim_rides_to_recent_weeks(rides)
    user = st.session_state.get("user")
    rider = st.session_state.get("rider", "默认骑手")
    if user:
        save_rider_data(user["user_id"], rider, "rides", rides)
    else:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(rides, f, ensure_ascii=False, indent=2)
    load_historical.clear()

def render_upload_quick_diagnosis(rides, profile=None):
    """Rule-based first impression after FIT upload; no AI call/cost."""
    if not rides:
        return
    profile = profile or load_profile()
    weight = profile.get("weight", 69) or 69
    actual_ftp = profile.get("ftp_test", 0) or 0
    ftp_detail = estimate_ftp_explain(rides)
    est_ftp = ftp_detail.get("ftp") or estimate_ftp(rides)
    ftp = actual_ftp if actual_ftp > 0 else est_ftp
    best = estimate_best_powers(rides, ftp)
    pmc = compute_daily_pmc(enrich_rides([dict(r) for r in rides], ftp))

    ctl = atl = tsb = None
    if not pmc.empty:
        last = pmc.iloc[-1]
        ctl, atl, tsb = int(last.get("ctl", 0)), int(last.get("atl", 0)), int(last.get("tsb", 0))

    recent_dates = []
    for r in rides:
        dt = parse_ride_date(r.get("date", ""))
        if pd.notna(dt):
            recent_dates.append(dt)
    latest_dt = max(recent_dates) if recent_dates else None
    recent7_tss = 0
    recent28_tss = 0
    if latest_dt is not None:
        start7 = latest_dt - pd.Timedelta(days=6)
        start28 = latest_dt - pd.Timedelta(days=27)
        for r in rides:
            dt = parse_ride_date(r.get("date", ""))
            if pd.isna(dt):
                continue
            tss = float(r.get("tss", 0) or 0)
            if dt >= start7:
                recent7_tss += tss
            if dt >= start28:
                recent28_tss += tss

    wkg = round(ftp / weight, 1) if ftp and weight else 0
    p20 = best.get("20min", 0) or 0
    p60 = best.get("60min", 0) or 0
    p5s = best.get("5s", 0) or 0

    if tsb is None:
        state = "数据已读取"
        state_desc = "已解析 FIT 数据，可以继续查看功率仪表盘和训练负荷。"
        state_color = "#8b949e"
    elif tsb <= -30:
        state = "疲劳偏高"
        state_desc = "短期负荷明显高于长期负荷，近期不建议连续堆高强度。"
        state_color = "#ff6b35"
    elif tsb <= -15:
        state = "负荷偏紧"
        state_desc = "训练刺激充足，但恢复余量有限，适合控制强度密度。"
        state_color = "#ffb020"
    elif tsb >= 12:
        state = "恢复较好"
        state_desc = "当前状态相对清爽，可以安排质量课，但仍要看睡眠和主观疲劳。"
        state_color = "#3fb950"
    else:
        state = "状态相对平衡"
        state_desc = "训练负荷和恢复大致平衡，适合按计划推进。"
        state_color = "#58a6ff"

    traits = []
    if ftp and p20:
        ratio20 = p20 / ftp
        if ratio20 >= 1.03:
            traits.append("20min 功率证据较强，FTP 可能有上调空间")
        elif ratio20 >= 0.95:
            traits.append("20min 功率接近 FTP，阈值能力较扎实")
    if ftp and p60:
        ratio60 = p60 / ftp
        if ratio60 >= 0.92:
            traits.append("60min 保持能力较好，耐力/疲劳抗性不错")
        elif ratio60 and ratio60 < 0.82:
            traits.append("60min 保持能力偏弱，后续可补耐力和甜区")
    if p5s and ftp and p5s / ftp >= 4.5:
        traits.append("短时爆发相对突出")
    if not traits:
        traits.append("已建立基础功率画像，建议继续补充 4-12 周数据让判断更稳定")

    suggestions = []
    if tsb is not None and tsb <= -20:
        suggestions.extend(["接下来 2-3 天优先恢复或 Z1/Z2", "暂时减少 VO2max / 阈值连续刺激"])
    elif tsb is not None and tsb >= 12:
        suggestions.extend(["可以安排 1 次质量课", "质量课后注意补碳水和睡眠"])
    else:
        suggestions.extend(["先查看训练负荷确认 CTL/ATL/TSB", "再进入 AI 功率分析生成更完整建议"])
    if actual_ftp <= 0:
        suggestions.append("如果知道实测 FTP，请到骑手档案填写，区间和课表会更准")
    suggestions.append("建议补一条训练反馈，让恢复判断更贴近真实体感")

    ftp_source = "实测 FTP" if actual_ftp > 0 else f"自动估算 FTP · {ftp_detail.get('basis', '依据不足')}"
    range_text = "-"
    if latest_dt is not None:
        earliest = min(recent_dates)
        range_text = f"{earliest.strftime('%Y-%m-%d')} 至 {latest_dt.strftime('%Y-%m-%d')}"

    st.markdown(f"""
<style>
.upload-diagnosis {{
    border: 1px solid rgba(255,107,53,0.34);
    border-radius: 18px;
    padding: 1.05em 1.15em;
    margin: 1.0em 0 1.15em;
    background: linear-gradient(135deg, rgba(255,107,53,0.16), rgba(22,27,34,0.96));
    box-shadow: 0 0 24px rgba(255,107,53,0.08);
}}
.upload-diagnosis .eyebrow {{ color:#ff9a68; font-size:0.76em; font-weight:850; letter-spacing:0.12em; margin-bottom:0.35em; }}
.upload-diagnosis .title {{ color:#f0f6fc; font-size:1.24em; font-weight:840; margin-bottom:0.45em; }}
.upload-diagnosis .status {{ color:{state_color}; font-size:1.02em; font-weight:800; margin:0.35em 0; }}
.upload-diagnosis .body {{ color:#aab6c3; font-size:0.90em; line-height:1.72; }}
.upload-diagnosis b {{ color:#ffb088; }}
</style>
<div class="upload-diagnosis">
  <div class="eyebrow">TRUECADENCE QUICK READ</div>
  <div class="title">上传后初步诊断</div>
  <div class="status">当前状态：{state}</div>
  <div class="body">
    数据范围：<b>{range_text}</b>｜记录：<b>{len(rides)} 条</b>｜FTP：<b>{ftp}W</b>（{ftp_source}）｜功体比：<b>{wkg} W/kg</b><br>
    训练负荷：CTL <b>{ctl if ctl is not None else '-'}</b> / ATL <b>{atl if atl is not None else '-'}</b> / TSB <b>{tsb if tsb is not None else '-'}</b>｜近7天 TSS <b>{round(recent7_tss)}</b>｜近28天 TSS <b>{round(recent28_tss)}</b><br>
    {state_desc}
  </div>
</div>
""", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**能力特点**")
        for t in traits[:4]:
            st.markdown(f"- {t}")
    with c2:
        st.markdown("**下一步建议**")
        for sug in suggestions[:5]:
            st.markdown(f"- {sug}")


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

def estimate_best_powers(rides, ftp=None):
    """Estimate best powers at various durations, preferring FIT record-level power_curve."""
    best = {'5s': 0, '30s': 0, '1min': 0, '5min': 0, '20min': 0, '60min': 0}
    keys = ['5s', '30s', '1min', '5min', '20min', '60min']

    for r in rides or []:
        pc = r.get('power_curve') or {}
        for key in keys:
            val = pc.get(key) or r.get(f"best_{key}") or 0
            try:
                val = float(val or 0)
            except Exception:
                val = 0
            if val > best[key]:
                best[key] = round(val)

        # Legacy summary fallback for old rows without power_curve.
        if not pc and r.get('np', 0) > 0:
            if r.get('dur', 0) >= 60 and r['np'] > best['60min']:
                best['60min'] = r['np']
            if r.get('dur', 0) >= 20 and r['np'] > best['20min']:
                best['20min'] = r['np']
        if r.get('max_p', 0) > best['5s']:
            best['5s'] = r['max_p']

    # Fill gaps with FTP-based estimates so charts remain usable for incomplete legacy data.
    if ftp is None:
        ftp = 160
    if best['60min'] == 0:
        best['60min'] = ftp
    if best['20min'] == 0:
        best['20min'] = round(ftp * 1.05)
    if best['5min'] == 0:
        best['5min'] = round(ftp * 1.20)
    if best['1min'] == 0:
        best['1min'] = round(ftp * 1.60)
    if best['30s'] == 0:
        best['30s'] = round(best['5s'] * 0.80) if best['5s'] > 0 else round(ftp * 2.0)
    return best

def calculate_power_zones(ftp):
    """Coggan power zones"""
    return {
        'Z1 Active Recovery': (0, round(ftp * 0.55)),
        'Z2 Endurance': (round(ftp * 0.55), round(ftp * 0.75)),
        'Z3 Tempo': (round(ftp * 0.75), round(ftp * 0.90)),
        'Z4 Sweet Spot': (round(ftp * 0.88), round(ftp * 0.95)),
        'Z5 Threshold': (round(ftp * 0.95), round(ftp * 1.05)),
        'Z6 VO2max': (round(ftp * 1.05), round(ftp * 1.20)),
        'Z7 Anaerobic': (round(ftp * 1.20), 999),
    }

def rider_type_profile(best, ftp, weight=69):
    """Determine rider type based on power profile"""
    if not ftp:
        return "Unknown"

    wkg_5s = best['5s'] / weight if best['5s'] else 0
    wkg_1min = best.get('1min', best['30s']) / weight if best.get('1min', best['30s']) else 0
    wkg_5min = best['5min'] / weight if best['5min'] else 0
    wkg_20min = best['20min'] / weight if best['20min'] else 0
    wkg_60min = best['60min'] / weight if best['60min'] else 0
    wkg_ftp = ftp / weight

    # Relative to FTP
    r_5s = wkg_5s / wkg_ftp if wkg_ftp else 0
    r_1min = wkg_1min / wkg_ftp if wkg_ftp else 0
    r_5min = wkg_5min / wkg_ftp if wkg_5min else 0

    if r_5s > 7.5 and wkg_5s > 14:
        return "冲刺手 Sprinter — 爆发力极强，擅长终点冲刺和短时攻击"
    elif r_1min > 3.5 and wkg_1min > 7:
        return "攻击手 Puncheur — 短陡坡和起伏路段优势明显，擅长反复进攻"
    elif r_5min > 1.5 and wkg_5min > 5:
        return "爬坡手 Climber — 长时间爬坡为王，功体比高是核心优势"
    elif wkg_60min > wkg_ftp * 0.92:
        return "计时赛手 TT — 稳定持续输出，适合平路和单人计时"
    else:
        return "全能型 All-Rounder — 各方面均衡，无明显短板也暂无突出长板"

def calculate_fatigue_resistance(rides, ftp, best):
    """Calculate fatigue resistance - power drop at each duration"""
    if not ftp:
        return None
    durations = [
        ('5s', best.get('5s', 0) or 0, [140, 160, 180, 200, 220]),
        ('30s', best.get('30s', 0) or 0, [130, 145, 160, 175, 190]),
        ('1min', best.get('1min', 0) or 0, [120, 130, 140, 150, 160]),
        ('5min', best.get('5min', 0) or 0, [105, 110, 115, 120, 128]),
        ('20min', best.get('20min', 0) or 0, [98, 100, 102, 105, 108]),
        ('60min', best.get('60min', 0) or 0, [92, 95, 98, 100, 102]),
    ]
    results = {}
    for name, power, thresholds in durations:
        if power <= 0:
            continue
        pct = round(power / ftp * 100)
        if pct >= thresholds[3]:
            rating = "卓越"
        elif pct >= thresholds[2]:
            rating = "优秀"
        elif pct >= thresholds[1]:
            rating = "良好"
        elif pct >= thresholds[0]:
            rating = "一般"
        else:
            rating = "待提升"
        results[name] = {'power': power, '%FTP': pct, 'rating': rating}
    return results


def summarize_durability(rides):
    """Aggregate ride-level durability metrics and keep the best/most informative records."""
    items = []
    for r in rides or []:
        d = r.get('durability') or {}
        if not d or not d.get('score'):
            continue
        x = dict(d)
        x['date'] = r.get('date', '')
        x['file_name'] = r.get('file_name', '')
        items.append(x)
    if not items:
        return None
    best_score = max(items, key=lambda x: x.get('score', 0))
    longest = max(items, key=lambda x: x.get('duration_min', 0))
    recent = sorted(items, key=lambda x: x.get('date', ''))[-1]
    avg_score = round(sum(x.get('score', 0) for x in items) / len(items), 1)
    avg_drop = round(sum(x.get('half_drop_pct', 0) for x in items) / len(items), 1)
    return {
        'count': len(items),
        'avg_score': avg_score,
        'avg_drop': avg_drop,
        'best_score': best_score,
        'longest': longest,
        'recent': recent,
        'items': sorted(items, key=lambda x: (x.get('score', 0), x.get('duration_min', 0)), reverse=True),
    }



# ─── Plot helpers ───
def plot_power_curve(best_powers, ftp):
    """Power duration curve"""
    dur_labels = ['5s', '30s', '1min', '5min', '20min', '60min']
    dur_seconds = [5, 30, 60, 300, 1200, 3600]
    values = [best_powers.get(d, 0) for d in dur_labels]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dur_seconds, y=values, mode='lines+markers',
        line=dict(color='#FF6B35', width=3),
        marker=dict(size=10),
        name='Best Power',
    ))
    if ftp:
        fig.add_hline(y=ftp, line_dash="dash", line_color="#4ECDC4",
                      annotation_text=f"FTP: {ftp}W")
    fig.update_xaxes(type="log", title="Duration", tickvals=dur_seconds, ticktext=dur_labels)
    fig.update_yaxes(title="Watts")
    fig.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20),
                      template="plotly_dark")
    return fig

def plot_pmc(rides):
    """PMC chart: CTL/ATL/TSB over natural calendar days."""
    if not rides:
        return go.Figure()

    df = compute_daily_pmc(rides)
    if df.empty:
        return go.Figure()

    hovertpl = '<b>%{x}</b><br>%{y:,.0f}<extra></extra>'

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=df['date'], y=df['ctl'], name='体能CTL', hovertemplate=hovertpl, line=dict(color='#4ECDC4', width=3)))
    fig.add_trace(go.Scatter(x=df['date'], y=df['atl'], name='疲劳ATL', hovertemplate=hovertpl, line=dict(color='#FF6B35', width=3)))
    fig.add_trace(go.Bar(x=df['date'], y=df['tsb'], name='状态TSB', hovertemplate=hovertpl, marker_color='#45B7D1', opacity=0.7, showlegend=True), secondary_y=True)

    fig.update_layout(
        height=400, margin=dict(l=30, r=30, t=30, b=30),
        template="plotly_dark",
        hovermode='x unified',
        hoverlabel=dict(font_size=16, font_family="Arial"),
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center", font=dict(size=14)),
    )
    fig.update_yaxes(title_text="体能/疲劳", secondary_y=False, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(title_text="状态", secondary_y=True, gridcolor='rgba(255,255,255,0.05)')
    fig.update_xaxes(showgrid=False)
    return fig

def plot_monthly_volume(rides):
    """Monthly training volume"""
    df = pd.DataFrame(rides)
    df['month'] = df['date'].str[:7]
    monthly = df.groupby('month').agg(
        rides=('date', 'count'),
        hours=('dur', lambda x: round(x.sum() / 60, 1)),
        km=('dist', 'sum'),
        tss=('tss', 'sum'),
    ).reset_index()

    fig = make_subplots(rows=2, cols=2, subplot_titles=('Hours', 'Rides', 'KM', 'TSS'))
    fig.add_trace(go.Bar(x=monthly['month'], y=monthly['hours'], marker_color='#FF6B35', name='Hours'), row=1, col=1)
    fig.add_trace(go.Bar(x=monthly['month'], y=monthly['rides'], marker_color='#4ECDC4', name='Rides'), row=1, col=2)
    fig.add_trace(go.Bar(x=monthly['month'], y=monthly['km'], marker_color='#45B7D1', name='KM'), row=2, col=1)
    fig.add_trace(go.Bar(x=monthly['month'], y=monthly['tss'], marker_color='#96CEB4', name='TSS'), row=2, col=2)
    fig.update_layout(height=500, template="plotly_dark", showlegend=False)
    return fig

# ─── AI diagnosis ───

def generate_zwo_week(wk, phase, ftp, h_per_ride, days):
    """Generate ZWO files for a week"""
    zwo_files = []
    z2_lo = round(ftp * 0.55)
    z2_hi = round(ftp * 0.75)
    sweet = round(ftp * 0.90)
    thresh = round(ftp * 0.97)
    vo2 = round(ftp * 1.10)
    sprint = round(ftp * 1.50)

    def make_zwo(name, desc, segments):
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<workout_file>\n'
        xml += '  <author>TrueCadence</author>\n'
        xml += f'  <name>{name}</name>\n'
        xml += f'  <description>{desc}</description>\n'
        xml += '  <sportType>bike</sportType>\n'
        xml += '  <tags/>\n'
        xml += '  <workout>\n'
        xml += segments + '\n'
        xml += '  </workout>\n'
        xml += '</workout_file>'
        return xml

    def steady(dur_sec, frac):
        return f'    <SteadyState Duration="{dur_sec}" Power="{frac:.3f}"/>'

    def intervals(rep, on_sec, off_sec, on_frac, off_frac):
        return f'    <IntervalsT Repeat="{rep}" OnDuration="{on_sec}" OffDuration="{off_sec}" OnPower="{on_frac:.3f}" OffPower="{off_frac:.3f}"/>'

    z2_pct = 0.65
    z1_pct = 0.45

    if phase == "rebuild":
        workouts = [
            ("D2_Z2", f"Week{wk} Z2耐力", steady(round(h_per_ride*3600), z2_pct)),
            ("D3_Z2_Sprints", f"Week{wk} Z2+冲刺",
             steady(900, z2_pct) + "\n" + intervals(3, 15, 165, 1.5, z2_pct) + "\n" + steady(round(h_per_ride*3600-900-3*180), z2_pct)),
            ("D5_Z2", f"Week{wk} Z2耐力", steady(round(h_per_ride*3600), z2_pct)),
            ("D6_LongZ2", f"Week{wk} 长距离Z2", steady(round(h_per_ride*1.5*3600), z2_pct)),
            ("D7_Recovery", f"Week{wk} 恢复骑", steady(1800, z1_pct)),
        ]
    elif phase == "build":
        workouts = [
            ("D2_SweetSpot", f"Week{wk} 甜区3x15min",
             steady(600, z2_pct) + "\n" + intervals(3, 900, 300, 0.90, z2_pct) + "\n" + steady(600, z2_pct)),
            ("D3_Z2", f"Week{wk} Z2耐力", steady(round(h_per_ride*1.3*3600), z2_pct)),
            ("D5_Threshold", f"Week{wk} 阈值4x8min",
             steady(600, z2_pct) + "\n" + intervals(4, 480, 240, 0.97, z2_pct) + "\n" + steady(600, z2_pct)),
            ("D6_Z1", f"Week{wk} Z1晃腿", steady(2700, z1_pct)),
            ("D7_LongZ2", f"Week{wk} 长距离Z2+爬坡", steady(round(h_per_ride*2*3600), z2_pct)),
        ]
    elif phase == "crit":
        workouts = [
            ("D2_Threshold", f"Week{wk} 阈值4x8min",
             steady(600, z2_pct) + "\n" + intervals(4, 480, 240, 0.97, z2_pct) + "\n" + steady(600, z2_pct)),
            ("D3_Z2", f"Week{wk} Z2耐力", steady(round(h_per_ride*1.3*3600), z2_pct)),
            ("D5_VO2", f"Week{wk} VO2max+冲刺",
             steady(600, z2_pct) + "\n" + intervals(6, 180, 180, 1.10, z2_pct) + "\n" + intervals(8, 15, 45, 1.50, z2_pct) + "\n" + steady(600, z2_pct)),
            ("D6_Z1", f"Week{wk} Z1+起跳", steady(2700, z1_pct)),
            ("D7_CritSim", f"Week{wk} 绕圈模拟", steady(round(h_per_ride*2*3600), z2_pct)),
        ]
    elif phase == "climb":
        workouts = [
            ("D2_SweetClimb", f"Week{wk} 甜区爬坡3x20min",
             steady(600, z2_pct) + "\n" + intervals(3, 1200, 300, 0.90, z2_pct) + "\n" + steady(600, z2_pct)),
            ("D3_Z2Climb", f"Week{wk} Z2+爬坡", steady(round(h_per_ride*1.5*3600), z2_pct)),
            ("D5_ThreshClimb", f"Week{wk} 阈值爬坡4x10min",
             steady(600, z2_pct) + "\n" + intervals(4, 600, 300, 0.97, z2_pct) + "\n" + steady(600, z2_pct)),
            ("D6_Z1", f"Week{wk} Z1晃腿", steady(2700, z1_pct)),
            ("D7_LongClimb", f"Week{wk} 长距离爬坡", steady(round(h_per_ride*2.5*3600), z2_pct)),
        ]
    elif phase == "taper":
        workouts = [
            ("D2_Activate", f"Week{wk} 赛前激活",
             steady(600, z2_pct) + "\n" + intervals(3, 300, 300, 0.95, z2_pct) + "\n" + steady(600, z2_pct)),
            ("D3_Z1", f"Week{wk} 轻松晃腿", steady(2700, z1_pct)),
            ("D5_PreCheck", f"Week{wk} 赛前预检",
             steady(600, z2_pct) + "\n" + intervals(2, 180, 300, 0.95, z2_pct) + "\n" + steady(600, z2_pct)),
            ("D6_Z1", f"Week{wk} 碳水加载", steady(1800, z1_pct)),
        ]
    else:
        workouts = [
            ("D2_Mix", f"Week{wk} 灵活骑", steady(round(h_per_ride*3600), z2_pct)),
            ("D3_Z2", f"Week{wk} Z2+爬坡", steady(round(h_per_ride*1.3*3600), z2_pct)),
            ("D5_ThreshM", f"Week{wk} 阈值维持",
             steady(600, z2_pct) + "\n" + intervals(3, 600, 300, 0.95, z2_pct) + "\n" + steady(600, z2_pct)),
            ("D7_Long", f"Week{wk} 长距离", steady(round(h_per_ride*2*3600), z2_pct)),
        ]

    for short, name, segments in workouts:
        xml = make_zwo(name, f"TC Week{wk} - {name}", segments)
        filename = f"TC_W{wk}_{short}.zwo"
        zwo_files.append((f"W{wk} {short}", xml, filename))

    return zwo_files

def generate_diagnosis(rides, ftp, best, weight=69, feedback=None, sleep_records=None):
    """Generate a richer rider diagnosis report from available ride summaries."""
    if not ftp:
        return "数据不足，请上传更多带功率数据的 FIT 文件。"

    weight = weight or 69
    wkg = round(ftp / weight, 1) if weight else 0
    rides_sorted = sorted(rides, key=lambda x: x.get('date', ''))
    total_rides = len(rides_sorted)
    total_h = round(sum(r.get('dur', 0) or 0 for r in rides_sorted) / 60, 1)
    total_km = round(sum(r.get('dist', 0) or 0 for r in rides_sorted), 1)
    total_tss = round(sum(r.get('tss', 0) or 0 for r in rides_sorted))

    dates = [r.get('date', '')[:10] for r in rides_sorted if r.get('date') and r.get('date') != 'unknown']
    span_days = 0
    if dates:
        try:
            d0 = pd.to_datetime(min(dates))
            d1 = pd.to_datetime(max(dates))
            span_days = max((d1 - d0).days + 1, 1)
        except Exception:
            span_days = 0
    span_weeks = max(round(span_days / 7, 1), 1) if span_days else max(total_rides / 3, 1)
    avg_week_h = round(total_h / span_weeks, 1)
    avg_week_rides = round(total_rides / span_weeks, 1)
    avg_tss_week = round(total_tss / span_weeks) if total_tss else 0

    rider = rider_type_profile(best, ftp, weight)
    fatigue = calculate_fatigue_resistance(rides_sorted, ftp, best)

    def pct(power):
        return round(power / ftp * 100) if ftp and power else 0

    p5 = best.get('5s', 0) or 0
    p60s = best.get('1min', 0) or 0
    p5m = best.get('5min', 0) or 0
    p20 = best.get('20min', 0) or 0
    p60 = best.get('60min', 0) or 0

    # Ability interpretation
    if wkg < 2.3:
        level = "入门/重建基础阶段"
        core_focus = "先把 Z2 有氧基础和训练连续性建立起来"
    elif wkg < 3.0:
        level = "大众进阶阶段"
        core_focus = "在稳定有氧基础上加入甜区和阈值训练"
    elif wkg < 3.8:
        level = "较强业余阶段"
        core_focus = "围绕专项目标优化阈值、VO2max 和疲劳抗性"
    else:
        level = "高水平业余/竞技阶段"
        core_focus = "维持高水平能力，重点做专项化和恢复管理"

    # Detect strengths and weaknesses from duration ratios
    ability_rows = []
    if p5:
        ability_rows.append(("5秒冲刺", p5, pct(p5), "爆发力 / 神经肌肉能力"))
    if p60s:
        ability_rows.append(("1分钟", p60s, pct(p60s), "无氧容量 / 短坡攻击"))
    if p5m:
        ability_rows.append(("5分钟", p5m, pct(p5m), "VO2max / 长坡与追击"))
    if p20:
        ability_rows.append(("20分钟", p20, pct(p20), "阈值能力 / FTP 支撑"))
    if p60:
        ability_rows.append(("60分钟", p60, pct(p60), "耐力与阈值维持"))

    strengths, weaknesses = [], []
    if p5 and p5 / ftp >= 4.8:
        strengths.append("短时爆发力不错，适合冲刺、跟攻和短坡变化")
    elif p5 and p5 / ftp < 3.5:
        weaknesses.append("5秒爆发偏弱，冲刺和快速变速能力需要补强")
    if p5m and p5m / ftp >= 1.18:
        strengths.append("5分钟能力较好，VO2max 和追击能力有优势")
    elif p5m and p5m / ftp < 1.08:
        weaknesses.append("5分钟功率偏弱，高强度爬坡和追击能力需要训练")
    if p20 and p20 / ftp >= 0.98:
        strengths.append("20分钟阈值支撑较好，FTP 估算可信度较高")
    elif p20 and p20 / ftp < 0.90:
        weaknesses.append("20分钟能力相对不足，甜区/阈值连续输出需要加强")
    if p60 and p60 / ftp >= 0.90:
        strengths.append("60分钟耐力保持较好，长时间输出不容易崩")
    elif p60 and p60 / ftp < 0.82:
        weaknesses.append("60分钟维持能力偏弱，疲劳抗性和长时间 Z2 需要加强")

    if not strengths:
        strengths.append("目前数据更适合先建立稳定训练画像，优势区间还需要更多高质量记录确认")
    if not weaknesses:
        weaknesses.append("当前数据没有暴露明显单点短板，下一阶段可优先关注训练连续性、恢复质量和专项目标匹配")

    # Training volume interpretation
    if avg_week_h < 3:
        volume_comment = "训练量明显偏少，当前最优先不是堆强度，而是把每周规律骑行建立起来。"
        volume_target = "先稳定到每周 3-4 次、4-6 小时。"
    elif avg_week_h < 6:
        volume_comment = "训练量偏基础，可以开始建立结构化训练，但强度不要太密。"
        volume_target = "逐步稳定到每周 6-8 小时。"
    elif avg_week_h < 10:
        volume_comment = "训练量适中，已经具备做系统周期训练的基础。"
        volume_target = "保持每周 2 次质量课 + 2-3 次 Z2/恢复。"
    else:
        volume_comment = "训练量较高，提升空间更多来自恢复质量、强弱分配和专项化。"
        volume_target = "控制强度密度，避免每次都骑成中高强度。"

    # Fatigue interpretation
    fatigue_lines = []
    if fatigue:
        for dur, val in fatigue.items():
            power = val.get('power', 0)
            rating = val.get('rating', '')
            fatigue_lines.append(f"- **{dur}**：{power}W（{val.get('%FTP', 0)}% FTP）→ **{rating}**")
        weak_zones = [z for z, v in fatigue.items() if v.get('rating') in ('一般', '待提升')]
        strong_zones = [z for z, v in fatigue.items() if v.get('rating') in ('优秀', '卓越')]
    else:
        weak_zones, strong_zones = [], []
        fatigue_lines.append("- 暂无足够数据判断疲劳抗性，建议上传更长时间或更多历史骑行记录。")

    # Weekly prescription
    z2_lo, z2_hi = round(ftp * 0.55), round(ftp * 0.75)
    tempo_lo, tempo_hi = round(ftp * 0.76), round(ftp * 0.87)
    ss_lo, ss_hi = round(ftp * 0.88), round(ftp * 0.94)
    th_lo, th_hi = round(ftp * 0.95), round(ftp * 1.02)
    vo2_lo, vo2_hi = round(ftp * 1.05), round(ftp * 1.18)

    if avg_week_h < 4 or wkg < 2.5:
        week_plan = [
            f"2-3 次 Z2 有氧：每次 60-120 分钟，功率约 **{z2_lo}-{z2_hi}W**。",
            f"1 次轻甜区入门：2-3 组 × 8-12 分钟，功率约 **{ss_lo}-{ss_hi}W**，组间轻松骑 5 分钟。",
            "其余时间做恢复骑或休息，不建议连续两天高强度。",
        ]
    elif weak_zones:
        week_plan = [
            f"1 次甜区/阈值课：3×12-15 分钟甜区 **{ss_lo}-{ss_hi}W**，或 4×8 分钟阈值 **{th_lo}-{th_hi}W**。",
            f"1 次 VO2max 维护：4-5×3 分钟 **{vo2_lo}-{vo2_hi}W**，不要做到力竭。",
            f"2-3 次 Z2 有氧：每次 90-150 分钟，功率约 **{z2_lo}-{z2_hi}W**。",
        ]
    else:
        week_plan = [
            f"1 次专项质量课：根据目标选择阈值 **{th_lo}-{th_hi}W** 或 VO2max **{vo2_lo}-{vo2_hi}W**。",
            f"1 次长距离 Z2：2-4 小时，功率约 **{z2_lo}-{z2_hi}W**，后段保持稳定不要掉功率。",
            f"1 次节奏/甜区：Tempo **{tempo_lo}-{tempo_hi}W** 或甜区 **{ss_lo}-{ss_hi}W**，用于提高有氧效率。",
        ]

    # Subjective feedback interpretation
    feedback_summary = summarize_recent_feedback(feedback or [])
    feedback_lines = feedback_summary.get("lines", [])
    feedback_risk_flags = feedback_summary.get("risk_flags", [])

    # Wearable sleep / recovery interpretation
    sleep_records = sleep_records or []
    sleep_sorted = sorted(sleep_records, key=lambda x: x.get("date", ""), reverse=True)
    recent_sleep = []
    today_ts = pd.Timestamp.today().normalize()
    for item in sleep_sorted:
        d = pd.to_datetime(item.get("date"), errors="coerce")
        if pd.notna(d) and (today_ts - d.normalize()).days <= 14:
            recent_sleep.append(item)
    if not recent_sleep:
        recent_sleep = sleep_sorted[:5]

    def sleep_avg(key):
        vals = [x.get(key) for x in recent_sleep if isinstance(x.get(key), (int, float)) and x.get(key) > 0]
        return round(sum(vals) / len(vals), 1) if vals else 0

    sleep_avg_hours = sleep_avg("sleep_hours")
    sleep_avg_score = sleep_avg("sleep_score")
    sleep_avg_hrv = sleep_avg("hrv")
    sleep_avg_rest_hr = sleep_avg("rest_hr")
    sleep_avg_stress = sleep_avg("stress_score")
    sleep_avg_body_battery = sleep_avg("body_battery")
    latest_sleep = sleep_sorted[0] if sleep_sorted else {}
    sleep_lines = []
    sleep_risk_flags = []
    if recent_sleep:
        nap_items = [x for x in recent_sleep if x.get("nap_minutes", 0)]
        avg_nap = round(sum(float(x.get("nap_minutes", 0) or 0) for x in nap_items) / len(nap_items), 1) if nap_items else 0
        nap_refresh = sum(1 for x in nap_items if x.get("nap_after") == "更清醒")
        nap_sluggish = sum(1 for x in nap_items if x.get("nap_after") == "更困")
        nap_phrase = f"，午睡 {len(nap_items)} 次，平均 **{avg_nap}min**，更清醒 {nap_refresh} 次，更困 {nap_sluggish} 次" if nap_items else ""
        sleep_lines.append(f"最近 {len(recent_sleep)} 条手表睡眠：平均夜间睡眠 **{sleep_avg_hours or '-'}h**，评分 **{sleep_avg_score or '-'}**，HRV **{sleep_avg_hrv or '-'}**，静息心率 **{sleep_avg_rest_hr or '-'}**，压力 **{sleep_avg_stress or '-'}**，Body Battery/恢复分 **{sleep_avg_body_battery or '-'}**{nap_phrase}。")
        if nap_items:
            if nap_sluggish:
                sleep_risk_flags.append("午睡后仍昏沉，下午训练不宜直接上高强度。")
            elif nap_refresh and 15 <= avg_nap <= 45:
                sleep_lines.append("短午睡且醒后更清醒，可作为下午训练准备度的小幅加成，但不能完全抵消夜间睡眠债。")
        if sleep_avg_hours and sleep_avg_hours < 5.5:
            sleep_risk_flags.append(f"平均睡眠 {sleep_avg_hours}h，明显不足，质量课建议下调或取消。")
        elif sleep_avg_hours and sleep_avg_hours < 6.5:
            sleep_risk_flags.append(f"平均睡眠 {sleep_avg_hours}h，偏少，高强度训练需谨慎。")
        if sleep_avg_score and sleep_avg_score < 55:
            sleep_risk_flags.append(f"睡眠评分 {sleep_avg_score}，恢复很差，优先恢复而非加训练量。")
        elif sleep_avg_score and sleep_avg_score < 70:
            sleep_risk_flags.append(f"睡眠评分 {sleep_avg_score}，恢复一般，避免连续高强度。")
        if sleep_avg_stress and sleep_avg_stress >= 70:
            sleep_risk_flags.append(f"压力分 {sleep_avg_stress}，自主神经压力偏高，训练日应保守。")
        if sleep_avg_body_battery and sleep_avg_body_battery < 35:
            sleep_risk_flags.append(f"恢复分 {sleep_avg_body_battery}，恢复储备偏低。")
        if not sleep_risk_flags:
            sleep_lines.append("手表睡眠未见明显红旗，可作为正常训练的辅助确认。")
    else:
        sleep_lines.append("暂未录入手表睡眠数据；AI 恢复判断主要依赖训练反馈和训练负荷。")

    # Risks and data quality
    risk_lines = []
    if total_rides < 5:
        risk_lines.append("当前记录数偏少，诊断更像初筛；建议至少上传 10-20 条记录后再做正式判断。")
    if not p20 or not p60:
        risk_lines.append("缺少 20min/60min 级别有效记录，FTP 和耐力判断可能偏保守。")
    if avg_tss_week == 0:
        risk_lines.append("多数记录缺少 TSS，训练负荷和恢复风险判断会受限。")
    if not any(r.get('hr_avg', 0) for r in rides_sorted):
        risk_lines.append("缺少心率数据，无法判断同功率下的心肺压力和恢复状态。")
    if not risk_lines:
        risk_lines.append("当前数据质量可以支撑基础训练判断；后续继续积累近期记录，诊断会更稳定。")

    feedback_badge = ""
    if feedback_summary.get("count", 0):
        feedback_badge = f"\n> ✅ 本报告已纳入最近 **{feedback_summary.get('count', 0)}** 条训练反馈，最新记录：**{feedback_summary.get('last_date', '未知')}**。\n"
    else:
        feedback_badge = "\n> ⚠️ 本报告暂未读取到训练反馈，恢复和疼痛判断主要来自功率数据。\n"

    sleep_badge = f"> ✅ 本报告已纳入 **{len(recent_sleep)}** 条手表睡眠/恢复记录，最新记录：**{latest_sleep.get('date', '未知')}**。\n" if recent_sleep else "> ⚠️ 本报告暂未读取到手表睡眠/恢复记录。\n"

    diagnosis = f"""## 🔍 TrueCadence 骑手诊断报告
{feedback_badge}{sleep_badge}
### 1. 一句话结论
你当前处于 **{level}**，骑手画像为 **{rider}**。下一阶段可优先关注：**{core_focus}**。

### 2. 判断依据说明
以下判断主要基于 FIT 文件中的最佳功率曲线、FTP、训练频率、训练负荷、近期反馈和睡眠/恢复记录。如果没有专门做过冲刺、5分钟、20分钟或60分钟测试，相关结论更适合作为参考方向，不等于能力定论。

### 3. 当前能力概览
- FTP：**{ftp}W**
- 功体比：**{wkg} W/kg**（体重 {weight}kg）
- 数据范围：**{total_rides}** 条记录 / **{total_h}** 小时 / **{total_km}** km
- 周均训练：约 **{avg_week_h}h/周**、**{avg_week_rides} 次/周**、TSS **{avg_tss_week}/周**
- 骑手类型：**{rider}**

### 4. 功率能力画像
| 区间 | 最佳功率 | 占 FTP | 代表能力 |
|---|---:|---:|---|
"""
    for name, power, percent, meaning in ability_rows:
        diagnosis += f"| {name} | {power}W | {percent}% | {meaning} |\n"

    diagnosis += "\n### 5. 优势与关注方向\n"
    diagnosis += "**相对优势**\n"
    for s in strengths[:4]:
        diagnosis += f"- {s}\n"
    diagnosis += "\n**下一阶段建议优先关注**\n"
    for w in weaknesses[:4]:
        diagnosis += f"- {w}\n"

    diagnosis += f"\n### 6. 训练量与一致性判断\n- {volume_comment}\n- 建议目标：{volume_target}\n"

    diagnosis += "\n### 7. 疲劳抗性\n"
    diagnosis += "\n".join(fatigue_lines) + "\n"
    if strong_zones:
        diagnosis += f"- 优势维持区间：**{', '.join(strong_zones)}**\n"
    if weak_zones:
        diagnosis += f"- 优先补强区间：**{', '.join(weak_zones)}**\n"

    diagnosis += "\n### 8. 接下来 2-4 周训练建议\n"
    for i, item in enumerate(week_plan, 1):
        diagnosis += f"{i}. {item}\n"
    diagnosis += "4. 每周至少安排 1 天完全休息或只做 30-45 分钟 Z1 恢复骑。\n"

    diagnosis += "\n### 9. 主观状态、手表睡眠与恢复风险\n"
    diagnosis += "**训练反馈**\n"
    if feedback_lines:
        for line in feedback_lines:
            diagnosis += f"- {line}\n"
    else:
        diagnosis += "- 暂无训练反馈记录。\n"
    diagnosis += "\n**手表睡眠 / 恢复数据**\n"
    for line in sleep_lines:
        diagnosis += f"- {line}\n"
    combined_recovery_flags = (feedback_risk_flags or []) + (sleep_risk_flags or [])
    if combined_recovery_flags:
        diagnosis += "\n**训练调整建议**\n"
        for flag in combined_recovery_flags[:7]:
            diagnosis += f"- {flag}\n"
    else:
        diagnosis += "- 暂无明显主观/睡眠恢复红旗；如果近期有睡眠差、疼痛或感冒，请先补记。\n"

    diagnosis += "\n### 10. 风险与数据质量提醒\n"
    for r in risk_lines:
        diagnosis += f"- {r}\n"

    diagnosis += "\n### 11. 下一步操作\n"
    diagnosis += "- 去 **📊 功率仪表盘** 看功率曲线和区间细节。\n"
    diagnosis += "- 如果已解锁 Core，进入 **📋 训练课表** 生成可执行课表。\n"
    diagnosis += "- 在 **👤 骑手档案** 中补充真实 FTP、体重、最大心率和训练目标，后续判断会更准。\n"

    return diagnosis

# ─── Pages ───

if page == "🏠 功能说明":
    st.markdown("""
<style>
.tc-hero {
    padding: 2.1em 1.4em 1.9em;
    border-radius: 18px;
    margin-bottom: 1.2em;
    background:
        radial-gradient(circle at 18% 20%, rgba(255,107,53,0.18), transparent 32%),
        linear-gradient(135deg, #111827 0%, var(--tc-bg) 52%, #101820 100%);
    border: 1px solid rgba(255,107,53,0.22);
    box-shadow: 0 10px 34px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.04);
}
.tc-eyebrow {
    display: inline-block;
    padding: 0.28em 0.9em;
    border: 1px solid rgba(255,107,53,0.35);
    border-radius: 999px;
    color: #ff9a68;
    background: rgba(255,107,53,0.08);
    font-size: 0.76em;
    letter-spacing: 0.12em;
    margin-bottom: 0.8em;
}
.tc-hero-title {
    font-size: 2.45em;
    line-height: 1.12;
    font-weight: 720;
    letter-spacing: -0.035em;
    color: #f0f6fc;
    margin: 0 0 0.42em;
}
.tc-hero-title span { color: #ff6b35; }
.tc-hero-sub {
    max-width: 860px;
    color: #aab6c3;
    font-size: 1.02em;
    line-height: 1.75;
    margin-bottom: 1.2em;
}
 .tc-hero-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75em;
    margin-top: 0.5em;
}
.tc-flow-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.45em;
    padding: 0.78em 1.08em;
    border-radius: 999px;
    font-weight: 720;
    letter-spacing: 0.02em;
    color: #f0f6fc !important;
    border: 1px solid rgba(255,107,53,0.38);
    background: linear-gradient(180deg, rgba(255,107,53,0.16), rgba(22,27,34,0.82));
    box-shadow: 0 8px 22px rgba(255,107,53,0.10);
    cursor: default;
}
.tc-flow-chip strong {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.55em;
    height: 1.55em;
    border-radius: 50%;
    color: #fff;
    background: #ff6b35;
    font-family: 'Courier New', monospace;
    font-size: 0.86em;
}
.tc-grid-3 {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.9em;
    margin: 1em 0 1.2em;
}
.tc-grid-4 {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.8em;
    margin: 0.8em 0 1.2em;
}
.tc-card {
    background: var(--tc-surface);
    border: 1px solid var(--tc-surface-2);
    border-radius: 14px;
    padding: 1em;
    min-height: 128px;
}
.tc-card .icon {
    font-size: 1.25em;
    margin-bottom: 0.45em;
}
.tc-card .title {
    color: #f0f6fc;
    font-size: 1.02em;
    font-weight: 700;
    margin-bottom: 0.35em;
}
.tc-card .text {
    color: var(--tc-subtle);
    font-size: 0.86em;
    line-height: 1.62;
}
.tc-step {
    position: relative;
    background: linear-gradient(180deg, rgba(255,107,53,0.06), rgba(22,27,34,0.85));
    border: 1px solid rgba(255,107,53,0.18);
}
.tc-step-num {
    color: #ff6b35;
    font-family: 'Courier New', monospace;
    font-size: 0.82em;
    letter-spacing: 0.08em;
    margin-bottom: 0.45em;
}
.tc-section-title {
    margin-top: 1.2em;
    color: #f0f6fc;
    font-size: 1.15em;
    font-weight: 720;
}
.tc-muted {
    color: var(--tc-subtle);
    font-size: 0.88em;
    line-height: 1.65;
}
@media (max-width: 900px) {
    .tc-grid-3, .tc-grid-4 { grid-template-columns: 1fr; }
    .tc-hero-title { font-size: 1.9em; }
}
</style>

<div class="tc-hero">
    <div class="tc-eyebrow">TRUECADENCE · AI CYCLING COACH</div>
    <div class="tc-hero-title">上传骑行数据，知道你<span>下一步该怎么练</span></div>
    <div class="tc-hero-sub">
        TrueCadence 会读取你的 FIT 文件，自动判断 FTP、功率短板、疲劳抗性和训练方向，
        把功率分析、AI 诊断、训练课表、恢复、营养和目标管理变成一条可执行路径。
    </div>
    <div class="tc-hero-actions">
        <span class="tc-flow-chip"><strong>1</strong> 填骑手档案</span>
        <span class="tc-flow-chip"><strong>2</strong> 上传 FIT 文件</span>
        <span class="tc-flow-chip"><strong>3</strong> 看分析并生成课表</span>
    </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="tc-section-title">首次使用路径</div>
<div class="tc-grid-3">
    <div class="tc-card tc-step">
        <div class="tc-step-num">STEP 01</div>
        <div class="title">先填骑手档案</div>
        <div class="text">优先填写体重、实测 FTP、最大心率和训练目标。它们会影响区间、营养、AI 分析和训练计划。</div>
    </div>
    <div class="tc-card tc-step">
        <div class="tc-step-num">STEP 02</div>
        <div class="title">上传最近 4-12 周 FIT</div>
        <div class="text">从码表、骑行台或平台导出 FIT，系统自动解析功率、心率、时长和训练负荷。</div>
    </div>
    <div class="tc-card tc-step">
        <div class="tc-step-num">STEP 03</div>
        <div class="title">按顺序看结果</div>
        <div class="text">先看功率仪表盘，再看训练负荷和恢复状态，最后生成 AI 分析、训练课表和 ZWO。</div>
    </div>
</div>

<div class="tc-section-title">建议浏览顺序</div>
<div class="tc-grid-4">
    <div class="tc-card tc-step"><div class="tc-step-num">01</div><div class="title">👤 骑手档案</div><div class="text">先校准体重、FTP、心率和目标。</div></div>
    <div class="tc-card tc-step"><div class="tc-step-num">02</div><div class="title">📤 上传分析</div><div class="text">上传 FIT，建立数据基础。</div></div>
    <div class="tc-card tc-step"><div class="tc-step-num">03</div><div class="title">📊/📈 数据判断</div><div class="text">查看能力结构、训练负荷和恢复风险。</div></div>
    <div class="tc-card tc-step"><div class="tc-step-num">04</div><div class="title">🧠/📋 执行</div><div class="text">生成 AI 分析、课表和 Zwift 文件。</div></div>
</div>

<div class="tc-section-title">开始前你需要准备什么</div>
<div class="tc-grid-4">
    <div class="tc-card">
        <div class="icon">📁</div>
        <div class="title">最近 4-12 周 FIT</div>
        <div class="text">优先上传有功率数据的骑行记录；历史最多保留最近 12 周。</div>
    </div>
    <div class="tc-card">
        <div class="icon">⚖️</div>
        <div class="title">体重</div>
        <div class="text">用于计算功体比和营养建议，建议填写当前真实体重。</div>
    </div>
    <div class="tc-card">
        <div class="icon">⚡</div>
        <div class="title">实测 FTP</div>
        <div class="text">如果知道 FTP，请优先填写；没有也可以先用自动估算作为参考。</div>
    </div>
    <div class="tc-card">
        <div class="icon">❤️</div>
        <div class="title">最大心率/训练目标</div>
        <div class="text">用于判断强度反应、恢复压力和后续训练方向。</div>
    </div>
</div>

<div class="tc-section-title">你能得到什么</div>
<div class="tc-grid-4">
    <div class="tc-card">
        <div class="icon">📊</div>
        <div class="title">功率驾驶舱</div>
        <div class="text">FTP、功体比、功率曲线、训练区间和疲劳抗性集中展示。</div>
    </div>
    <div class="tc-card">
        <div class="icon">🧠</div>
        <div class="title">AI 训练判断</div>
        <div class="text">告诉你现在该堆有氧、练甜区、冲 FTP，还是优先恢复。</div>
    </div>
    <div class="tc-card">
        <div class="icon">📋</div>
        <div class="title">可执行课表</div>
        <div class="text">把诊断结果变成每周训练安排，不停留在“建议你多练”。</div>
    </div>
    <div class="tc-card">
        <div class="icon">🍝</div>
        <div class="title">训练闭环</div>
        <div class="text">恢复、睡眠、营养、目标追踪接入同一个训练系统。</div>
    </div>
</div>
""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("支持数据", "FIT", "功率 / 心率 / TSS")
    c2.metric("核心输出", "诊断 + 课表", "从分析到执行")
    c3.metric("适用对象", "骑友 / 教练", "个人训练或多骑手管理")

    st.divider()

    with st.expander("⚙️ 展开：TrueCadence 的知识来源与能力边界", expanded=False):
        st.markdown("""
TrueCadence 不是只把数据画成图，而是把功率训练、Bike Fitting、运动营养和恢复管理整合到同一个判断框架里。

**功率训练**
- FTP 测试与校准、七区训练、PMC 训练负荷、疲劳抗性、周期化课表与比赛前减量。

**Bike Fitting**
- 座垫、弯把、把立、锁片、骑行伤痛排查与动态踩踏分析，用于理解姿势和输出能力之间的关系。

**运动营养**
- 训练日/休息日碳水、蛋白质恢复、赛中补给、比赛日策略和补剂循证分级。

**恢复与身体**
- 睡眠、晨脉、疲劳信号、主动恢复、功能动作筛查和过度训练风险识别。

**边界说明**
- 系统用于训练辅助和数据分析，不替代医学诊断；疼痛、损伤或异常身体反应应咨询专业人士。
""")

elif page == "🔐 数据隐私":
    st.title("🔐 数据隐私与内测说明")
    st.caption("TrueCadence 需要读取训练数据才能给出功率、负荷、恢复和课表建议。这里说明数据会怎么被使用。")

    st.markdown("""
<style>
.privacy-hero {
    padding: 1.12em 1.18em;
    border-radius: 17px;
    background: linear-gradient(135deg, rgba(255,107,53,0.15), rgba(22,27,34,0.96));
    border: 1px solid rgba(255,107,53,0.30);
    margin: 0.85em 0 1.05em;
}
.privacy-hero .k { color:#ff9a68; font-size:.78em; font-weight:850; letter-spacing:.11em; margin-bottom:.35em; }
.privacy-hero .t { color:#f0f6fc; font-size:1.28em; font-weight:850; margin-bottom:.35em; }
.privacy-hero .d { color:#aab6c3; font-size:.92em; line-height:1.75; }
.privacy-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.8em; margin:.9em 0 1.1em; }
.privacy-card { background:var(--tc-surface); border:1px solid var(--tc-border); border-radius:14px; padding:1em; min-height:132px; }
.privacy-card .title { color:#f0f6fc; font-size:1.02em; font-weight:780; margin-bottom:.38em; }
.privacy-card .text { color:#aab6c3; font-size:.88em; line-height:1.68; }
.privacy-note { border-radius:14px; padding:1em 1.08em; background:rgba(88,166,255,.09); border:1px solid rgba(88,166,255,.22); color:#aab6c3; font-size:.90em; line-height:1.72; margin:1em 0; }
@media(max-width:900px){.privacy-grid{grid-template-columns:1fr}}
</style>
<div class="privacy-hero">
  <div class="k">DATA & PRIVACY</div>
  <div class="t">你的训练数据只用于训练分析与内测改进</div>
  <div class="d">内测阶段，我们会尽量少保存原始文件，只保留完成分析所需的训练摘要。系统不会公开展示你的个人数据，也不会把你的 FIT、睡眠、反馈或女性周期信息用于医疗判断。</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="privacy-grid">
  <div class="privacy-card"><div class="title">📁 FIT 原始文件</div><div class="text">上传的 .fit 原始文件仅用于解析功率、心率、时长、TSS 和功率曲线。内测阶段原始 FIT 最多保留 48 小时，后续上传时会自动清理旧文件。</div></div>
  <div class="privacy-card"><div class="title">📊 训练摘要</div><div class="text">系统会保存解析后的训练摘要，例如日期、时长、距离、功率、心率、TSS、功率曲线等，用于历史趋势、训练负荷、AI 分析和训练课表。</div></div>
  <div class="privacy-card"><div class="title">📝 主观反馈 / 睡眠</div><div class="text">训练反馈、睡眠、HRV、压力、疲劳、疼痛等信息只用于判断恢复状态和调整训练建议。你可以在对应页面删除单条记录或清空记录。</div></div>
  <div class="privacy-card"><div class="title">🩸 女性周期信息</div><div class="text">女性周期、腹痛、情绪和训练影响只用于训练恢复建议，不用于医学诊断，也不会公开展示。你可以选择不记录。</div></div>
  <div class="privacy-card"><div class="title">🐞 内测反馈</div><div class="text">内测反馈会记录问题页面、反馈类型、描述和联系方式。联系方式只用于必要时回访确认问题，不会显示给其他用户。</div></div>
  <div class="privacy-card"><div class="title">🔒 账号与登录</div><div class="text">TrueCadence 不会在分享链接里保存登录凭证。建议使用浏览器或手机系统密码管理器保存密码，不要把账号密码发给他人。</div></div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="privacy-note">
<b>重要边界：</b>TrueCadence 是训练辅助工具，不替代医生、康复师或专业医疗建议。出现胸痛、晕厥、持续异常心率、严重疼痛、感染发烧或疑似损伤时，应停止训练并咨询专业人士。
</div>
""", unsafe_allow_html=True)

    with st.expander("查看内测阶段数据保留规则", expanded=True):
        st.markdown("""
- **FIT 原始文件**：最多保留 48 小时，用于测试和排查解析问题，之后自动清理。
- **训练历史摘要**：最多保留最近 12 周；同日期新上传会覆盖旧记录，避免重复和脏数据。
- **训练反馈 / 睡眠记录**：由用户主动填写，可单条删除或确认后清空。
- **AI 分析上下文**：用于训练计划读取最近一次分析结果；如果训练数据、反馈或睡眠变更，会重新生成上下文。
- **内测反馈**：用于产品改进和问题追踪。
""")

    with st.expander("我应该怎么保护自己的数据？", expanded=False):
        st.markdown("""
- 不要把登录后的页面截图里暴露手机号、邀请码或个人敏感信息。
- 如果要在抖音/朋友圈分享分析截图，建议遮挡姓名、手机号和具体个人备注。
- 不要把完整登录链接、账号密码、邀请码公开发到评论区。
- 如果只是想试功能，优先上传最近 4-12 周训练数据，不需要上传多年历史。
""")

elif page == "🐞 内测反馈":
    st.title("🐞 内测反馈")
    st.caption("这里用于收集内测问题、体验建议和你希望 TrueCadence 优先改进的地方。")

    user = st.session_state.get("user", {})
    rider = st.session_state.get("rider", "默认骑手")

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
  <div class="d">越具体越好：在哪个页面、点了什么、看到什么异常、你原本期待它怎么工作。反馈会保存到内测记录里，方便后续集中修复。</div>
</div>
<div class="feedback-tip">
  <b>建议反馈格式：</b>页面 + 操作步骤 + 看到的问题 + 期望结果。比如：“训练负荷页，上传 5 个 FIT 后，切到合并历史，图表没有变化，希望能提示是否已合并。”
</div>
""", unsafe_allow_html=True)

    with st.form("beta_feedback_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            contact = st.text_input("联系方式 / 微信 / 手机", placeholder="方便回访时填写，可留空")
            feedback_page = st.selectbox("问题页面", [
                "首页/功能说明", "注册/登录/内测邀请码", "骑手档案", "上传分析", "功率仪表盘",
                "训练负荷", "训练反馈", "恢复与睡眠", "AI 功率分析", "训练课表/ZWO",
                "营养与补给", "目标追踪", "套餐/权限", "手机端显示", "其他"
            ])
        with c2:
            issue_type = st.selectbox("反馈类型", ["Bug/报错", "看不懂/需要解释", "数据不符合预期", "体验建议", "功能建议", "视觉/手机端", "其他"])
            severity = st.selectbox("影响程度", ["一般建议", "影响理解", "影响使用", "阻塞无法继续"])

        description = st.text_area("问题描述", height=120, placeholder="请描述你看到的问题，或者希望改进的地方。")
        steps = st.text_area("操作步骤 / 复现方式", height=100, placeholder="例如：登录 → 上传 FIT → 进入训练负荷 → 点击合并历史 → 出现……")
        expected = st.text_area("你期望它怎么表现", height=80, placeholder="例如：希望显示更明确的解释 / 希望按钮位置更明显 / 希望能导出……")
        allow_contact = st.checkbox("允许后续联系我确认细节", value=True)
        submitted = st.form_submit_button("提交内测反馈", use_container_width=True)

    if submitted:
        if not description.strip() and not steps.strip() and not expected.strip():
            st.error("请至少填写一段问题描述、操作步骤或期望改进。")
        else:
            item = {
                "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "user_id": user.get("user_id", ""),
                "username": user.get("username", ""),
                "plan": user.get("plan", "free"),
                "rider": rider,
                "contact": contact.strip(),
                "page": feedback_page,
                "type": issue_type,
                "severity": severity,
                "description": description.strip(),
                "steps": steps.strip(),
                "expected": expected.strip(),
                "allow_contact": bool(allow_contact),
            }
            try:
                data = load_beta_feedback()
                data.insert(0, item)
                save_beta_feedback(data)
                st.success("已收到，感谢。这个反馈会进入内测问题记录。")
            except Exception as e:
                st.error(f"保存失败：{e}")

    st.divider()
    my_items = [x for x in load_beta_feedback() if x.get("user_id") == user.get("user_id")]
    st.subheader("我的反馈记录")
    if not my_items:
        st.info("你还没有提交过反馈。遇到问题时直接在上面填写即可。")
    else:
        st.caption(f"已提交 {len(my_items)} 条。")
        show = []
        for x in my_items[:8]:
            show.append({
                "时间": x.get("created_at", ""),
                "页面": x.get("page", ""),
                "类型": x.get("type", ""),
                "影响": x.get("severity", ""),
                "描述": (x.get("description", "") or x.get("expected", ""))[:80],
            })
        st.dataframe(pd.DataFrame(show).astype(str), use_container_width=True, hide_index=True)

    if user.get("is_admin") or user.get("role") in ("admin", "super_admin"):
        st.divider()
        st.subheader("🛠️ 管理员：全部内测反馈")
        all_items = load_beta_feedback()
        st.caption(f"当前共 {len(all_items)} 条反馈。")
        if not all_items:
            st.info("暂无内测反馈。")
        else:
            df_all = pd.DataFrame(all_items).copy()
            for col in ["created_at", "user_id", "username", "plan", "rider", "contact", "page", "type", "severity", "description", "steps", "expected", "allow_contact"]:
                if col not in df_all.columns:
                    df_all[col] = ""
            f1, f2, f3 = st.columns(3)
            page_opts = ["全部"] + sorted([x for x in df_all["page"].dropna().astype(str).unique().tolist() if x])
            type_opts = ["全部"] + sorted([x for x in df_all["type"].dropna().astype(str).unique().tolist() if x])
            sev_order = ["全部", "阻塞无法继续", "影响使用", "影响理解", "一般建议"]
            page_filter = f1.selectbox("页面筛选", page_opts, key="admin_fb_page")
            type_filter = f2.selectbox("类型筛选", type_opts, key="admin_fb_type")
            severity_filter = f3.selectbox("影响程度", sev_order, key="admin_fb_severity")
            filtered = df_all.copy()
            if page_filter != "全部":
                filtered = filtered[filtered["page"].astype(str) == page_filter]
            if type_filter != "全部":
                filtered = filtered[filtered["type"].astype(str) == type_filter]
            if severity_filter != "全部":
                filtered = filtered[filtered["severity"].astype(str) == severity_filter]
            st.caption(f"筛选后 {len(filtered)} 条。")
            if len(filtered):
                show_cols = ["created_at", "page", "type", "severity", "contact", "plan", "rider", "description", "steps", "expected", "allow_contact", "user_id"]
                rename = {
                    "created_at": "时间", "page": "页面", "type": "类型", "severity": "影响", "contact": "联系方式",
                    "plan": "套餐", "rider": "骑手", "description": "描述", "steps": "步骤", "expected": "期望",
                    "allow_contact": "可回访", "user_id": "用户ID"
                }
                display = filtered[show_cols].rename(columns=rename).astype(str)
                st.dataframe(display, use_container_width=True, hide_index=True)
                csv = display.to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    "下载筛选结果 CSV",
                    data=csv.encode("utf-8-sig"),
                    file_name=f"truecadence_beta_feedback_{datetime.date.today().isoformat()}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
                with st.expander("查看反馈全文", expanded=False):
                    for _, row in filtered.head(20).iterrows():
                        st.markdown(f"""
**{row.get('created_at','')}｜{row.get('page','')}｜{row.get('type','')}｜{row.get('severity','')}**  
用户：`{row.get('user_id','')}`｜套餐：{row.get('plan','')}｜联系方式：{row.get('contact','') or '-'}  
描述：{row.get('description','') or '-'}  
步骤：{row.get('steps','') or '-'}  
期望：{row.get('expected','') or '-'}
---
""")

elif page == "💎 套餐对比":
    st.title("💎 套餐与升级路径")
    st.caption("先免费看懂数据，再用 Core 开始系统训练；如果你有比赛和提升目标，Pro 会把训练、恢复、营养和目标追踪连成闭环。")

    current_plan = st.session_state.user.get("plan", "free")

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
.upgrade-note {
    background: rgba(35,134,54,0.08); border: 1px solid rgba(35,134,54,0.28);
    border-radius: 12px; padding: 0.95em 1em; margin-top: 1em;
    color: var(--tc-muted); line-height: 1.65; font-size: 0.9em;
}
@media (max-width: 900px) { .plan-path, .plans-grid { grid-template-columns: 1fr; } }
</style>
<div class="pricing-hero">
    <div class="pricing-hero-title">选择的不是功能，是训练方式</div>
    <div class="pricing-hero-text">Free 让你先看懂数据；Core 让你开始每周按课表训练；Pro 把训练、恢复、营养、目标追踪连起来；Coach 用来管理多个骑手。</div>
</div>
<div class="plan-path">
    <div class="path-step"><div class="k">Free</div><div class="v">体验数据<br>先看懂自己</div></div>
    <div class="path-step"><div class="k">Core</div><div class="v">开始训练<br>每周有课表</div></div>
    <div class="path-step"><div class="k">Pro</div><div class="v">完整闭环<br>训练+恢复+营养</div></div>
    <div class="path-step"><div class="k">Coach</div><div class="v">多骑手管理<br>教练/工作室</div></div>
</div>
""", unsafe_allow_html=True)

    import html as _html
    plans_data = [
        ("free", "免费版", "¥0", "适合：先试试看，了解自己数据", "结果：看懂基础功率数据，不再只看平均速度", ["上传 FIT 文件，查看基础功率分析", "基础 PMC 训练负荷曲线", "最近训练概览", "AI 点评每月 8 次"]),
        ("core", "Core版", "¥19/月 · ¥169/年", "适合：想开始系统训练的骑友", "结果：每周拿到可执行训练课表", ["AI 训练分析每月 30 次", "自动生成训练课表，导出 .ZWO 文件", "功率仪表盘与疲劳抗性分析", "训练负荷 PMC 曲线"]),
        ("pro", "Pro版", "¥49/月 · ¥449/年", "适合：有比赛、FTP 或体重管理目标", "结果：训练、恢复、营养、目标完整闭环", ["包含 Core 全部功能", "营养补给建议与比赛日策略", "恢复监督与睡眠优化", "目标追踪与周期化训练计划", "AI 动态分析无限次数"]),
        ("coach", "Coach版", "¥149/月 · ¥1349/年", "适合：教练、工作室或管理多位骑手", "结果：最多 20 位骑手档案、批量分析和长期跟踪", ["最多 20 位骑手管理", "AI 辅助教练分析与批量生成课表", "骑手分组与恢复监控", "包含 Pro 全部功能"]),
    ]
    icons = {"free":"🟦", "core":"🔥", "pro":"🏆", "coach":"👥"}
    colors = {"free":"var(--tc-subtle)", "core":"#ff6b35", "pro":"#f0c040", "coach":"#f85149"}
    bgs = {
        "free":"linear-gradient(180deg, rgba(139,148,158,0.10), var(--tc-surface))",
        "core":"linear-gradient(180deg, rgba(255,107,53,0.13), var(--tc-surface))",
        "pro":"linear-gradient(180deg, rgba(240,192,64,0.10), var(--tc-surface))",
        "coach":"linear-gradient(180deg, rgba(248,81,73,0.10), var(--tc-surface))",
    }
    card_html = ['<div class="plans-grid">']
    for plan_key, name, price, fit, result, features in plans_data:
        color = colors[plan_key]
        rec = '<div class="plan-rec">🔥 推荐</div>' if plan_key == 'core' else '<div style="height:28px"></div>'
        badge = '<div class="plan-badge">当前套餐</div>' if plan_key == current_plan else ''
        feature_html = ''.join('<div class="plan-feature">✦ ' + _html.escape(f) + '</div>' for f in features)
        card = (
            '<div class="plan-card" style="border:2px solid ' + color + '; background:' + bgs[plan_key] + ';">'
            + rec
            + '<div class="plan-name" style="color:' + color + ';">' + icons[plan_key] + ' ' + _html.escape(name) + '</div>'
            + '<div class="plan-price">' + _html.escape(price) + '</div>'
            + '<div class="plan-fit">' + _html.escape(fit) + '</div>'
            + '<div class="plan-result">' + _html.escape(result) + '</div>'
            + '<div style="color:var(--tc-subtle);font-size:0.76em;font-weight:700;margin-bottom:0.35em;">包含</div>'
            + '<div style="flex:1;">' + feature_html + '</div>'
            + badge
            + '</div>'
        )
        card_html.append(card)
    card_html.append('</div>')
    st.markdown('\n'.join(card_html), unsafe_allow_html=True)

    st.markdown("""
<div class="upgrade-note">
    <b>怎么升级：</b>在左侧边栏「⬆️ 升级套餐」输入内测邀请码即可升级，升级后立即解锁对应功能。<br>
    如果你只是想体验，Free 足够；如果你想真正开始按计划训练，建议从 Core 开始。
</div>
""", unsafe_allow_html=True)

elif page == "📝 训练反馈":
    st.title("📝 训练反馈")
    st.caption("记录睡眠、疲劳、疼痛、不适和训练后感受。后续 AI 分析会结合这些主观信息，判断是否该降强度、恢复或调整课表。")

    st.markdown("""
<style>
.feedback-note {
    background: linear-gradient(135deg, rgba(255,107,53,0.10), rgba(22,27,34,0.92));
    border: 1px solid rgba(255,107,53,0.22);
    border-radius: 14px;
    padding: 0.95em 1em;
    margin: 0.7em 0 1em;
    color: #aab6c3;
    font-size: 0.9em;
    line-height: 1.65;
}
.feedback-section { color: #f0f6fc; font-size: 1.02em; font-weight: 720; margin: 0.9em 0 0.45em; }
</style>
<div class="feedback-note">
    <b>为什么要记录：</b>功率只能告诉你做了多少，反馈能告诉你身体承受得怎么样。感冒、睡眠差、腿沉、膝盖痛、补给不足，都会影响今天该不该继续上强度。
</div>
""", unsafe_allow_html=True)

    feedback = load_feedback()
    profile = load_profile()
    cycle_enabled_for_feedback = bool(profile.get('cycle_enabled')) or profile.get('gender') == '女'

    with st.form("feedback_form"):
        st.markdown('<div class="feedback-section">今日状态</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        fb_date = c1.date_input("日期", value=datetime.date.today())
        sleep_quality = c2.slider("睡眠质量", 1, 5, 3, help="1=很差，5=很好")
        energy = c3.slider("精神状态", 1, 5, 3, help="1=很差，5=很好")
        c4, c5, c6 = st.columns(3)
        leg_fatigue = c4.slider("腿部疲劳", 1, 5, 3, help="1=很轻松，5=很沉很累")
        stress = c5.slider("生活/工作压力", 1, 5, 3)
        morning_hr = c6.number_input("晨脉/静息心率", 0, 160, 0, help="可选")

        st.markdown('<div class="feedback-section">训练后反馈</div>', unsafe_allow_html=True)
        c7, c8, c9 = st.columns(3)
        rpe = c7.slider("RPE 主观强度", 1, 10, 5, help="1=非常轻松，10=极限")
        completion = c8.selectbox("完成度", ["未训练", "轻松完成", "正常完成", "勉强完成", "没完成"])
        leg_feel = c9.selectbox("腿感", ["正常", "轻松", "沉", "酸", "抽筋", "发软"])
        c10, c11 = st.columns(2)
        breathing = c10.selectbox("呼吸/心肺感受", ["正常", "喘不上来", "胸闷", "心率异常偏高", "心率异常偏低"])
        fueling = c11.selectbox("补给情况", ["正常", "吃少了", "喝少了", "胃不舒服", "低血糖感", "不适用"])

        st.markdown('<div class="feedback-section">不适与特殊情况</div>', unsafe_allow_html=True)
        pain_options = ["膝盖", "腰", "颈肩", "手麻", "坐垫压迫", "脚麻/脚痛", "髋/臀", "跟腱/小腿"]
        pains = st.multiselect("哪里不舒服", pain_options, default=[], placeholder="无不适可留空")
        special_options = ["感冒", "发烧", "睡眠不足", "饮酒", "出差/旅行", "天气太热", "天气太冷", "工作压力大"]
        specials = st.multiselect("特殊情况", special_options, default=[], placeholder="无特殊情况可留空")
        cycle_status = '不记录'
        cycle_pain = '无'
        cycle_flow = '不记录'
        cycle_mood = '不记录'
        cycle_training_impact = '不记录'
        if cycle_enabled_for_feedback:
            st.markdown('<div class="feedback-section">女性周期状态</div>', unsafe_allow_html=True)
            fc1, fc2, fc3 = st.columns(3)
            cycle_status = fc1.selectbox("今日周期状态", ["不记录", "经期第1-2天", "经期第3-5天", "经期后恢复期", "排卵期附近", "经前期/PMS", "周期正常，无明显影响"], key="fb_cycle_status")
            cycle_pain = fc2.selectbox("腹痛/腰酸", ["无", "轻", "中", "重"], key="fb_cycle_pain")
            cycle_flow = fc3.selectbox("出血量", ["不记录", "少", "中", "多"], key="fb_cycle_flow")
            fc4, fc5 = st.columns(2)
            cycle_mood = fc4.selectbox("情绪波动", ["不记录", "低", "中", "高"], key="fb_cycle_mood")
            cycle_training_impact = fc5.selectbox("是否影响训练", ["不记录", "不影响", "轻微", "明显"], key="fb_cycle_training_impact")

        notes = st.text_area("备注", placeholder="例如：今天鼻塞，没做完间歇；右膝外侧痛；补给没吃够后半程掉功率。")

        submitted = st.form_submit_button("💾 保存训练反馈", type="primary", use_container_width=True)

    if submitted:
        entry = {
            "date": fb_date.isoformat(), "sleep_quality": sleep_quality, "energy": energy,
            "leg_fatigue": leg_fatigue, "stress": stress, "morning_hr": morning_hr,
            "rpe": rpe, "completion": completion, "leg_feel": leg_feel,
            "breathing": breathing, "fueling": fueling,
            "pains": pains,
            "specials": specials,
            "notes": notes,
            "cycle_status": cycle_status, "cycle_pain": cycle_pain,
            "cycle_flow": cycle_flow, "cycle_mood": cycle_mood,
            "cycle_training_impact": cycle_training_impact,
            "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        feedback = [x for x in feedback if x.get("date") != entry["date"]]
        feedback.append(entry)
        feedback.sort(key=lambda x: x.get("date", ""), reverse=True)
        save_feedback(feedback)
        st.session_state.pop("ai_diagnosis", None)
        st.session_state.pop("ai_signature", None)
        st.session_state["feedback_saved_notice"] = f"✅ {entry['date']} 训练反馈已保存，AI 功率分析会自动纳入这条反馈"
        st.success(st.session_state["feedback_saved_notice"])

    if st.session_state.get("feedback_saved_notice"):
        st.success(st.session_state["feedback_saved_notice"])

    st.divider()
    st.subheader("最近反馈")
    if feedback:
        df_fb = pd.DataFrame(feedback[:14])
        show_cols = ["date", "sleep_quality", "energy", "leg_fatigue", "stress", "rpe", "completion", "leg_feel", "pains", "specials", "cycle_status", "cycle_pain", "cycle_training_impact", "notes"]
        df_fb = df_fb[[c for c in show_cols if c in df_fb.columns]].copy()
        for col in ["pains", "specials"]:
            if col in df_fb.columns:
                df_fb[col] = df_fb[col].apply(lambda x: "、".join(x) if isinstance(x, list) and x else "")
        st.dataframe(df_fb.astype(str), use_container_width=True, hide_index=True,
                     column_config={"date": "日期", "sleep_quality": "睡眠", "energy": "精神", "leg_fatigue": "腿疲劳", "stress": "压力", "rpe": "RPE", "completion": "完成度", "leg_feel": "腿感", "pains": "不适", "specials": "特殊情况", "cycle_status": "周期", "cycle_pain": "腹痛/腰酸", "cycle_training_impact": "周期影响", "notes": "备注"})

        with st.expander("🗑️ 删除训练反馈数据", expanded=False):
            feedback_options = []
            for idx, item in enumerate(feedback):
                label = f"{item.get('date', '-')}｜睡眠{item.get('sleep_quality', '-')}｜腿疲劳{item.get('leg_fatigue', '-')}｜RPE{item.get('rpe', '-')}｜{item.get('completion', '-')}"
                feedback_options.append((idx, label))
            option_labels = [x[1] for x in feedback_options]
            selected_label = st.selectbox("选择要删除的反馈", option_labels, key="feedback_delete_select")
            selected_idx = next((idx for idx, label in feedback_options if label == selected_label), None)
            fc1, fc2 = st.columns([1, 1])
            if fc1.button("删除选中反馈", key="delete_feedback_one", use_container_width=True):
                if selected_idx is not None:
                    deleted_date = feedback[selected_idx].get("date", "-")
                    feedback = [x for i, x in enumerate(feedback) if i != selected_idx]
                    save_feedback(feedback)
                    st.session_state.pop("ai_diagnosis", None)
                    st.session_state.pop("ai_signature", None)
                    st.success(f"已删除 {deleted_date} 的训练反馈。剩余 {len(feedback)} 条。")
                    st.rerun()
            confirm_clear_feedback = fc2.checkbox("确认清空全部", key="confirm_clear_feedback")
            if fc2.button("清空全部训练反馈", key="clear_feedback_all", use_container_width=True, disabled=not confirm_clear_feedback):
                save_feedback([])
                st.session_state.pop("ai_diagnosis", None)
                st.session_state.pop("ai_signature", None)
                st.success("已清空当前骑手全部训练反馈。")
                st.rerun()
    else:
        st.info("还没有训练反馈。建议每次关键训练后记录一次，尤其是强度课、长距离、感冒/睡眠差/疼痛时。")

elif page == "📤 上传分析":
    st.title("📤 上传分析")
    st.caption("上传码表、骑行台或训练平台导出的 FIT 文件，系统会自动解析功率、心率和训练负荷。")

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
    <div class="upload-hero-title">第一步：把你的真实骑行数据放进来</div>
    <div class="upload-hero-text">
        建议一次上传最近 4-12 周的 FIT 文件。数据越完整，FTP 估算、功率曲线、疲劳抗性和后续 AI 诊断会越稳定。
        如果只有 1-3 次骑行，也可以先上传体验基础分析。
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
        <div class="text">用于生成 TSS、PMC、周训练量趋势，并为训练课表提供依据。</div>
    </div>
</div>
""", unsafe_allow_html=True)

    with st.expander("📁 从哪里导出 FIT 文件？", expanded=True):
        st.markdown("""
**推荐准备：**最近 4-12 周、有功率数据的 FIT 文件。一次最多上传 28 个；历史最多保留最近 12 周；同日期新上传会覆盖旧记录。

**常见导出方式：**
- **Garmin Connect / 佳明：**进入一次骑行活动 → 右上角更多/齿轮 → 导出原始数据 / Export Original → 得到 `.fit` 文件。
- **Zwift：**登录 Zwift 活动页面 → 选择对应骑行 → 下载 FIT 文件；也可从本机 `Documents/Zwift/Activities` 找到 `.fit`。
- **Wahoo / ELEMNT：**活动详情里选择分享/导出，优先选择 FIT 原始文件。
- **COROS / 其他码表：**活动详情 → 导出数据 → 选择 FIT。若只有 `.tcx/.gpx`，功率和 TSS 可能不完整。
- **骑行台平台：**优先从训练平台活动详情下载 FIT，而不是截图或 CSV。

**上传建议：**先上传最近 28 个 FIT 看结果；如果需要补更早的数据，再分批上传。系统会自动去重合并。
""")

    st.info("🔐 数据说明：内测阶段上传的 FIT 原始文件最多保留 48 小时；系统会保存解析后的训练摘要用于分析、课表和历史趋势。你的数据不会公开展示。")

    st.markdown("""
<div class="upload-cta-note">
    <b>👇 从这里开始：</b>点击下方按钮选择 FIT 文件，或直接把 FIT 文件拖到上传框里。一次最多 28 个，单次总大小最多 50MB；网络不稳定或使用代理时，建议每批 5-10 个 FIT，更稳。
</div>
""", unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "📂 选择或拖拽 FIT 文件",
        type=['fit'],
        accept_multiple_files=True,
        help="从码表、骑行台或训练平台导出的 .fit 文件。历史最多保留最近 12 周；为保证稳定，一次最多上传 28 个，单次总大小最多 50MB。网络不稳定或使用代理时，建议每批 5-10 个。"
    )

    MAX_FIT_UPLOADS = 28
    MAX_TOTAL_UPLOAD_MB = 50
    if uploaded and len(uploaded) > MAX_FIT_UPLOADS:
        st.error(f"一次最多上传 {MAX_FIT_UPLOADS} 个 FIT 文件。你当前选择了 {len(uploaded)} 个，请分批上传。")
        st.info("建议按时间顺序分批上传：网络不稳定时每批 5-10 个更稳；例如先传最近一批，保存后再上传更早的数据。历史最多保留最近 12 周；同日期新上传会覆盖旧记录，系统也会按文件指纹/记录去重。")
        st.stop()
    if uploaded:
        total_bytes = sum(getattr(f, "size", 0) or 0 for f in uploaded)
        total_mb = total_bytes / 1024 / 1024
        if total_mb > MAX_TOTAL_UPLOAD_MB:
            st.error(f"本次文件总大小约 {total_mb:.1f}MB，超过单次 {MAX_TOTAL_UPLOAD_MB}MB 限制。请分批上传。")
            st.info("建议先上传最近 4-12 周内最关键的一批 FIT；如果文件很多，可按月份或按最近/更早分批上传。网络不稳定时每批 5-10 个更稳。")
            st.stop()

    if not uploaded:
        render_empty_data_state(
            "选择 FIT 文件开始建立训练画像",
            "建议一次上传最近 4-12 周的 FIT 文件。数据越完整，FTP 估算、训练负荷、疲劳抗性和 AI 诊断越稳定。",
            ["展开上方说明，从码表 / Zwift / 训练平台导出 .fit 文件", "一次最多选择 28 个；网络不稳定时建议每批 5-10 个，系统会自动去重合并", "上传后先看功率仪表盘和训练负荷"]
        )
        st.stop()

    with st.spinner(f"正在解析 {len(uploaded)} 个文件..."):
        new_rides = parse_fit_files(uploaded)

    if new_rides:
        # Fill missing NP and TSS from available data
        new_rides = enrich_rides(new_rides)
        st.success(f"✅ 解析完成：获取 {len(new_rides)} 条骑行记录")

        # Preview table - cast to text so Streamlit does not right-align numeric cells.
        df = pd.DataFrame(new_rides)
        cols = ['date', 'dur', 'dist', 'avg_p', 'np', 'max_p', 'hr_avg', 'hr_max', 'tss']
        rename_cols = {
            'date': '日期', 'dur': '时长(min)', 'dist': '距离(km)',
            'avg_p': '平均功率', 'np': 'NP', 'max_p': '最大功率',
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
        st.success(f"✅ 已合并保存到历史：本次新增 {added_count} 条，当前历史保留最近 12 周共 {len(merged_rides)} 条")
        st.caption("历史规则：最多保留最近 12 周；新上传中出现的日期会覆盖历史中同日期旧记录，避免重复和旧数据残留。")

        render_upload_quick_diagnosis(merged_rides, load_profile())

        st.markdown(f"""
<div class="upload-next">
    <div class="title">下一步建议</div>
    <div class="text">
        这 {len(new_rides)} 条新解析数据已经并入历史。建议先看 <b>📊 功率仪表盘</b> 理解当前能力结构，
        再进入 <b>🧠 AI 功率分析</b> 获取训练判断；如果你已解锁 Core，可继续生成 <b>📋 训练课表</b>。
    </div>
</div>
""", unsafe_allow_html=True)
    else:
        st.warning("未找到有效骑行数据。请确认文件为 .fit 格式，并包含骑行记录；如果没有功率数据，部分分析会受限。")

elif page == "👤 骑手档案":
    st.title("👤 骑手档案")

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
    <div class="main">这些信息会直接影响 <b>FTP、功体比、训练区间、营养建议和 AI 分析</b>。建议优先填写：<b>体重、实测 FTP、最大心率、训练目标</b>。</div>
</div>
<div class="profile-note">
    <b>为什么要填：</b>体重决定 W/kg 和营养建议；FTP 决定功率区间、AI 分析和训练课表；心率用于判断强度反应和恢复压力；训练目标会影响后续建议方向。
</div>
""", unsafe_allow_html=True)

    profile = load_profile()

    tab1, tab2 = st.tabs(["基础档案", "Fitting 设定"])

    with tab1:
        st.markdown('<div class="profile-section-title">身体数据</div>', unsafe_allow_html=True)
        st.markdown('<div class="profile-help">用于计算功体比、营养需求和训练负荷解释。</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        name = c1.text_input("姓名", value=profile.get('name') or '', help="可填客户姓名或编号")
        gender = c2.selectbox("性别", ["男", "女"], index=0 if profile.get('gender', '男') == '男' else 1)
        age = c1.number_input("年龄", 0, 99, value=profile.get('age') if profile.get('age') is not None else 0)
        weight = c2.number_input("体重 kg", 0, 200, value=profile.get('weight') if profile.get('weight') else 0, help="用于计算 W/kg 和营养建议")
        height = c1.number_input("身高 cm", 0, 250, value=profile.get('height') if profile.get('height') else 0)
        exp_years = c2.number_input("骑行年限", 0, 60, value=profile.get('exp_years') or 0)

        cycle_enabled = bool(profile.get('cycle_enabled', False))
        cycle_last_start = profile.get('cycle_last_start') or ''
        cycle_length = int(profile.get('cycle_length') or 28)
        period_days = int(profile.get('period_days') or 5)
        cycle_sensitivity = profile.get('cycle_sensitivity') or '正常'
        if gender == '女':
            st.markdown('<div class="profile-section-title">女性周期辅助</div>', unsafe_allow_html=True)
            st.markdown('<div class="profile-help">可选填写。只用于训练恢复和补给建议，不作为医学判断。</div>', unsafe_allow_html=True)
            cycle_enabled = st.toggle("启用女性周期辅助", value=cycle_enabled, key="profile_cycle_enabled")
            if cycle_enabled:
                cc1, cc2 = st.columns(2)
                try:
                    default_cycle_date = datetime.date.fromisoformat(cycle_last_start) if cycle_last_start else datetime.date.today()
                except Exception:
                    default_cycle_date = datetime.date.today()
                cycle_last_start_date = cc1.date_input("最近一次月经开始日期", value=default_cycle_date, key="profile_cycle_last_start")
                cycle_last_start = cycle_last_start_date.isoformat()
                cycle_length = cc2.number_input("平均周期长度 天", 20, 45, value=cycle_length, key="profile_cycle_length")
                period_days = cc1.number_input("平均经期天数", 2, 10, value=period_days, key="profile_period_days")
                cycle_sensitivity = cc2.selectbox("经期训练敏感度", ["保守", "正常", "激进"], index=["保守", "正常", "激进"].index(cycle_sensitivity) if cycle_sensitivity in ["保守", "正常", "激进"] else 1, key="profile_cycle_sensitivity")

        st.markdown('<div class="profile-section-title">训练数据</div>', unsafe_allow_html=True)
        st.markdown('<div class="profile-help">FTP 和心率数据会直接影响功率区间、AI 诊断和课表生成。</div>', unsafe_allow_html=True)
        c3, c4 = st.columns(2)
        ftp_test = c3.number_input("实测 FTP W", 0, 600, value=profile.get('ftp_test') if profile.get('ftp_test') else 0, key="ftp_input", help="如果不填，系统会根据 FIT 数据自动估算")
        max_hr = c4.number_input("最大心率", 0, 250, value=profile.get('max_hr') if profile.get('max_hr') else 0)
        rest_hr = c3.number_input("静息心率", 0, 120, value=profile.get('rest_hr') if profile.get('rest_hr') else 0)
        bike_type = c4.selectbox("主要车种", ["公路车", "山地车", "铁三车", "砾石车", "折叠车", "其他"], index=["公路车", "山地车", "铁三车", "砾石车", "折叠车", "其他"].index(profile.get('bike_type', '公路车')) if profile.get('bike_type', '公路车') in ["公路车", "山地车", "铁三车", "砾石车", "折叠车", "其他"] else 0)

        st.markdown('<div class="profile-section-title">目标信息</div>', unsafe_allow_html=True)
        st.markdown('<div class="profile-help">训练目标越清楚，AI 建议和课表方向越容易对准。</div>', unsafe_allow_html=True)
        goal = st.text_input("训练目标", value=profile.get('goal') or '', placeholder="例如：提升 FTP、备战绕圈赛、减脂、恢复体能")
        notes = st.text_area("备注", value=profile.get('notes') or '', placeholder="可记录伤病、可训练时间、比赛日期、器材情况等")

        save_col, clear_col = st.columns([3, 1])
        if save_col.button("💾 保存骑手档案", type="primary", use_container_width=True):
            basics = dict(name=name, age=age, gender=gender, weight=weight, height=height,
                         exp_years=exp_years, ftp_test=ftp_test, max_hr=max_hr, rest_hr=rest_hr,
                         bike_type=bike_type, goal=goal, notes=notes,
                         cycle_enabled=cycle_enabled if gender == '女' else False,
                         cycle_last_start=cycle_last_start if gender == '女' and cycle_enabled else '',
                         cycle_length=cycle_length, period_days=period_days,
                         cycle_sensitivity=cycle_sensitivity)
            user = st.session_state.get("user")
            rider = st.session_state.get("rider", "默认骑手")
            existing = load_rider_profile(user["user_id"], rider) if user else {}
            existing.update(basics)
            if user:
                save_rider_profile(user["user_id"], rider, existing)
            else:
                with open(PROFILE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(existing, f, ensure_ascii=False, indent=2)
            st.success("✅ 骑手档案已保存")
        if clear_col.button("清空", use_container_width=True, help="仅清空当前骑手的基础档案"):
            user = st.session_state.get("user")
            rider = st.session_state.get("rider", "默认骑手")
            empty = {"name": "", "age": 0, "gender": "男", "weight": 0, "height": 0,
                     "exp_years": 0, "ftp_test": 0, "max_hr": 0, "rest_hr": 0,
                     "bike_type": "公路车", "goal": "", "notes": "", "cycle_enabled": False, "cycle_last_start": "", "cycle_length": 28, "period_days": 5, "cycle_sensitivity": "正常"}
            if user:
                existing = load_rider_profile(user["user_id"], rider)
                for k in empty:
                    existing[k] = empty[k]
                save_rider_profile(user["user_id"], rider, existing)
            st.cache_data.clear()
            st.rerun()
        st.markdown('<div class="danger-note">清空只影响当前骑手档案，不会删除 FIT 骑行记录。</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="profile-section-title">Fitting 设定记录</div>', unsafe_allow_html=True)
        st.markdown('<div class="profile-help">用于记录人车设定，后续可辅助判断姿势变化、舒适性和输出表现。这里不是医学诊断，只是长期跟踪档案。</div>', unsafe_allow_html=True)
        c5, c6 = st.columns(2)
        saddle_h = c5.number_input("座垫高度 mm", 0, 900, value=profile.get('saddle_height') if profile.get('saddle_height') else 0)
        reach = c5.number_input("座垫-车把 mm", 0, 700, value=profile.get('reach') if profile.get('reach') else 0)
        drop = c5.number_input("落差 mm", -200, 150, value=profile.get('drop') if profile.get('drop') else 0)
        setback = c5.number_input("座垫后移 mm", -50, 150, value=profile.get('saddle_setback') if profile.get('saddle_setback') else 0)
        crank = c6.number_input("曲柄 mm", 0, 180, value=profile.get('crank_length') if profile.get('crank_length') else 0)
        bar_w = c6.number_input("弯把宽 mm", 0, 480, value=profile.get('handlebar_width') if profile.get('handlebar_width') else 0)
        stem = c6.number_input("把立 mm", 0, 160, value=profile.get('stem_length') if profile.get('stem_length') else 0)
        inseam = c6.number_input("跨高 mm", 0, 1000, value=profile.get('inseam') if profile.get('inseam') else 0)
        shoe = c6.number_input("锁鞋 EU", 0, 50, value=profile.get('shoe_size') if profile.get('shoe_size') else 0)

        save_col2, clear_col2 = st.columns([3, 1])
        if save_col2.button("💾 保存 Fitting 设定", type="primary", use_container_width=True):
            fitdata = dict(saddle_height=saddle_h, reach=reach, drop=drop, saddle_setback=setback,
                          crank_length=crank, handlebar_width=bar_w, stem_length=stem,
                          inseam=inseam, shoe_size=shoe)
            user = st.session_state.get("user")
            rider = st.session_state.get("rider", "默认骑手")
            existing = load_rider_profile(user["user_id"], rider) if user else {}
            existing.update(fitdata)
            if user:
                save_rider_profile(user["user_id"], rider, existing)
            else:
                with open(PROFILE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(existing, f, ensure_ascii=False, indent=2)
            st.success("✅ Fitting 设定已保存")
        if clear_col2.button("清空", use_container_width=True, help="仅清空当前骑手的 Fitting 设定"):
            user = st.session_state.get("user")
            rider = st.session_state.get("rider", "默认骑手")
            empty = {"saddle_height": 0, "reach": 0, "drop": 0, "saddle_setback": 0,
                     "crank_length": 0, "handlebar_width": 0, "stem_length": 0,
                     "inseam": 0, "shoe_size": 0}
            if user:
                existing = load_rider_profile(user["user_id"], rider)
                for k in empty:
                    existing[k] = empty[k]
                save_rider_profile(user["user_id"], rider, existing)
            st.cache_data.clear()
            st.rerun()
        st.markdown('<div class="danger-note">清空只影响当前骑手的 Fitting 设定，不会删除基础档案和骑行记录。</div>', unsafe_allow_html=True)

elif page == "📊 功率仪表盘":
    st.title("📊 功率仪表盘")
    st.caption("功率曲线、区间、疲劳抗性一览")

    uploaded_rides = st.session_state.get('uploaded_rides', [])
    historical = load_historical()

    use_all = st.toggle("合并全历史数据", value=False if uploaded_rides else True,
                        help="开启=上传文件+历史数据一起分析;关闭=只看上传的文件")

    if use_all:
        rides = merge_rides(historical, uploaded_rides)
        source_label = "合并历史数据"
    elif uploaded_rides:
        rides = uploaded_rides
        source_label = "仅本次上传"
    else:
        rides = historical
        source_label = "历史数据"

    rides.sort(key=lambda x: x['date'])
    rides = enrich_rides(rides)

    if not rides:
        render_empty_data_state(
            "还没有可分析的骑行数据",
            "功率仪表盘需要 FIT 数据才能计算 FTP、功率曲线、功率区间和疲劳抗性。建议先上传最近 4-12 周的 FIT 文件；如果你已经知道实测 FTP，也先在骑手档案里填好。",
            ["填写骑手档案里的体重、实测 FTP 和最大心率", "上传最近 4-12 周 FIT 文件", "回到功率仪表盘查看 FTP、功率曲线和区间"]
        )
        st.stop()

    st.caption(data_scope_caption(rides, historical, uploaded_rides, source_label))

    profile = load_profile()
    pweight = profile.get('weight', 69)

    ftp_detail = estimate_ftp_explain(rides)
    est_ftp = ftp_detail.get("ftp") or estimate_ftp(rides)
    actual_ftp = profile.get('ftp_test', 0)
    ftp = actual_ftp if actual_ftp > 0 else est_ftp

    best = estimate_best_powers(rides, ftp)

    # Show FTP source. Training calculations always prefer manually tested FTP when available.
    if actual_ftp > 0:
        st.success(f"当前使用 FTP: **{actual_ftp}W**（来源：用户实测）· 功体比: **{round(actual_ftp/pweight, 1)} W/kg**")
        st.caption(f"自动估算 FTP：{est_ftp}W，仅作参考；依据：{ftp_detail.get('basis', '-')}；可信度：{ftp_detail.get('confidence', '-') }。训练区间、AI 分析和课表优先使用实测 FTP。")
    else:
        st.info(f"当前使用自动估算 FTP: **{est_ftp}W** · 功体比: **{round(est_ftp/pweight, 1)} W/kg**")
        st.caption(f"估算依据：{ftp_detail.get('basis', '-')}；可信度：{ftp_detail.get('confidence', '-') }。如有正式 FTP 测试，请在骑手档案页填写实测 FTP。")

    if actual_ftp > 0 and est_ftp > 0 and abs(actual_ftp - est_ftp) / actual_ftp > 0.12:
        st.warning(f"自动估算 ({est_ftp}W) 与实测 FTP ({actual_ftp}W) 差异较大。当前训练建议以实测 FTP 为准；自动值仅说明已上传数据里的可见证据。")
    elif actual_ftp > 0 and best.get('20min', 0) >= actual_ftp * 0.98:
        st.info(f"已上传数据中存在接近/达到当前 FTP 的 20min 记录（20min {best.get('20min', 0)}W），当前实测 FTP 可信度较高。")

    # Top metrics - uniform cards
    col1, col2, col3, col4, col5 = st.columns(5)
    wkg = round(ftp/pweight, 1)
    col1.metric("FTP", f"{ftp}W", f"{wkg} W/kg")
    s5_wkg = round(best['5s']/pweight, 1) if best['5s'] and pweight else ""
    col2.metric("5s 冲刺", f"{best['5s']}W", f"{s5_wkg} W/kg" if s5_wkg else "")
    p20 = best.get('20min', 0)
    col3.metric("20min 功率", f"{p20}W", f"{round(p20/ftp*100)}% FTP" if ftp and p20 else "")
    p60 = best.get('60min', 0)
    col4.metric("60min 功率", f"{p60}W", f"{round(p60/ftp*100)}% FTP" if ftp and p60 else "")
    col5.metric("总骑行次数", len(rides), f"{len(rides)} 条记录")

    # Power curve
    st.subheader("功率持续时间曲线")
    st.plotly_chart(plot_power_curve(best, ftp), use_container_width=True)

    # Power zones table
    if ftp:
        st.subheader("🏷️ 功率区间 - 练什么功率代表练什么能力")
        zone_data = []
        zone_desc = {
            'Z1 Active Recovery': '恢复骑,排乳酸',
            'Z2 Endurance': '有氧耐力,燃烧脂肪,堆量靠这个',
            'Z3 Tempo': '节奏骑,提升有氧效率',
            'Z4 Sweet Spot': '甜区,性价比最高的强度',
            'Z5 Threshold': '阈值,提升FTP的核心区间',
            'Z6 VO2max': '最大摄氧量,很累但有效',
            'Z7 Anaerobic': '无氧冲刺,练爆发力',
        }
        zones = calculate_power_zones(ftp)
        for i, (name, (lo, hi)) in enumerate(zones.items()):
            zone_data.append({
                '区间': name,
                '功率': f"{lo}-{hi}W",
                '练什么': zone_desc.get(name, ''),
                '建议时长': '任意' if i <= 1 else '1-3h' if i == 2 else '20-60min×2-3组' if i <= 4 else '3-8min×3-5组' if i == 5 else '30s-3min×4-8组',
            })
        _zone_df = pd.DataFrame(zone_data).astype(str)
        st.dataframe(_zone_df, use_container_width=True, hide_index=True,
                     column_config={'区间': '区间', '功率': '功率', '练什么': '练什么', '建议时长': '建议时长'})

    # Fatigue resistance / Durability 2.0
    fatigue = calculate_fatigue_resistance(rides, ftp, best)
    durability_summary = summarize_durability(rides)
    if fatigue:
        st.subheader("🔋 疲劳抗性 2.0 - 后程还能不能输出")
        st.caption("上半部分看功率曲线持续能力；下半部分在新上传 FIT 有逐点功率时，会进一步判断后半程保持能力。")
        fat_data = []
        for dur, val in fatigue.items():
            fat_data.append({'时长': dur, '功率(W)': str(val.get('power', 0)), '占FTP': f"{val['%FTP']}%", '评级': val['rating']})
        _fat_df = pd.DataFrame(fat_data).astype(str)
        st.dataframe(_fat_df, use_container_width=True, hide_index=True)
        st.caption("功率曲线评分：数值越高越好。比如60min能保持FTP的95%以上=耐力不错；短时项目则反映爆发和无氧能力。")

        if durability_summary:
            b = durability_summary['best_score']
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("后程保持评分", f"{durability_summary['avg_score']}", "多次骑行平均")
            c2.metric("平均后半程衰减", f"{durability_summary['avg_drop']}%")
            c3.metric("最佳单次评级", b.get('rating', '-'), f"{b.get('score', 0)} 分")
            c4.metric("可分析骑行", f"{durability_summary['count']} 条")
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
                st.success("后程保持能力较好：长距离或训练后段仍能保留较高输出，可以逐步加入更专项的后段质量刺激。")
            elif durability_summary['avg_score'] >= 78:
                st.info("后程保持能力中等：基础耐力可以，但长骑后段的甜区/阈值保持仍有提升空间。")
            else:
                st.warning("后程保持能力偏弱：建议先补 Z2 长距离、甜区耐力和补给策略，不要过早堆高强度。")
        else:
            st.info("疲劳抗性 2.0 需要新上传的 FIT 包含逐点功率数据。旧历史摘要仍可显示功率曲线评分；重新上传最近 4-12 周 FIT 后会更准。")

elif page == "📈 训练负荷":
    st.title("📈 训练负荷")
    st.caption("判断最近练得是太少、刚好，还是太猛。")

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

    uploaded_rides = st.session_state.get('uploaded_rides', [])
    historical = load_historical()
    use_all = st.toggle("合并全历史数据", value=False if uploaded_rides else True, key="load_use_all", help="开启=上传文件+历史数据一起看；关闭=只看本次上传文件")
    if use_all:
        rides = merge_rides(historical, uploaded_rides)
        source_label = "合并历史数据"
    elif uploaded_rides:
        rides = uploaded_rides
        source_label = "仅本次上传"
    else:
        rides = historical
        source_label = "历史数据"

    rides.sort(key=lambda x: x.get('date', ''))
    rides = enrich_rides(rides)

    if not rides:
        render_empty_data_state(
            "训练负荷需要先有 FIT 历史",
            "CTL、ATL、TSB 都基于 TSS 计算。上传 FIT 后，系统会按自然日计算 PMC；即使后面几天没有训练，也会按 TSS=0 自然回落到今天。",
            ["上传至少 1 条带训练负荷的 FIT", "建议上传最近 4-12 周，让 CTL/ATL 更稳定", "回到训练负荷页查看疲劳、状态和风险提示"]
        )
        st.stop()

    st.caption(data_scope_caption(rides, historical, uploaded_rides, source_label))

    df_raw = pd.DataFrame(rides).sort_values('date')
    df_raw['date_dt'] = pd.to_datetime(df_raw['date'], errors='coerce')
    df_pmc = compute_daily_pmc(rides)
    latest_date = df_pmc['date_dt'].max() if not df_pmc.empty else pd.NaT

    current_ctl = int(df_pmc.iloc[-1]['ctl']) if not df_pmc.empty else 0
    current_atl = int(df_pmc.iloc[-1]['atl']) if not df_pmc.empty else 0
    current_tsb = int(df_pmc.iloc[-1]['tsb']) if not df_pmc.empty else 0
    ctl_series = df_pmc['ctl'].tolist() if not df_pmc.empty else [0]

    if pd.isna(latest_date):
        recent_7 = df_raw.tail(7)
        recent_28 = df_raw.tail(28)
    else:
        recent_7 = df_raw[df_raw['date_dt'] >= latest_date - pd.Timedelta(days=6)]
        recent_28 = df_raw[df_raw['date_dt'] >= latest_date - pd.Timedelta(days=27)]

    tss_7 = round(recent_7.get('tss', pd.Series(dtype=float)).fillna(0).sum()) if len(recent_7) else 0
    tss_28 = round(recent_28.get('tss', pd.Series(dtype=float)).fillna(0).sum()) if len(recent_28) else 0
    hours_7 = round(recent_7.get('duration_h', pd.Series(dtype=float)).fillna(0).sum(), 1) if len(recent_7) else 0
    hours_28 = round(recent_28.get('duration_h', pd.Series(dtype=float)).fillna(0).sum(), 1) if len(recent_28) else 0
    avg_weekly_hours = round(hours_28 / 4, 1)
    ctl_7_days_ago = df_pmc.iloc[-8]['ctl'] if len(df_pmc) >= 8 else df_pmc.iloc[0]['ctl'] if not df_pmc.empty else 0
    ramp_rate = current_ctl - ctl_7_days_ago

    feedback = load_feedback()
    recent_feedback = sorted(feedback, key=lambda x: (x.get('date', ''), x.get('created_at', '')), reverse=True)[:5]
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
        risk_desc = '新手/恢复/减脂目标，提前提醒，优先安全。'
        thresholds = dict(tsb_red=-25, tsb_caution=-12, fresh=15,
                          atl_red=20, atl_caution=10, ramp_fast=8, ramp_drop=-5,
                          fatigue_red=4.0, fatigue_caution=3.3, sleep_red=2.5)
    elif any(k in intent_text for k in performance_keywords) or exp_years >= 3:
        risk_mode = '进阶'
        risk_desc = '规律训练/备赛目标，允许一定负荷积累。'
        thresholds = dict(tsb_red=-35, tsb_caution=-18, fresh=20,
                          atl_red=30, atl_caution=15, ramp_fast=12, ramp_drop=-7,
                          fatigue_red=4.3, fatigue_caution=3.7, sleep_red=2.2)
    else:
        risk_mode = '标准'
        risk_desc = '普通规律训练，兼顾训练刺激和恢复风险。'
        thresholds = dict(tsb_red=-30, tsb_caution=-15, fresh=18,
                          atl_red=25, atl_caution=12, ramp_fast=10, ramp_drop=-6,
                          fatigue_red=4.2, fatigue_caution=3.5, sleep_red=2.3)

    red_flags = []
    caution_flags = []
    good_flags = []
    good_flags.append(f"风险档位：{risk_mode}（{risk_desc}）")

    if current_tsb < thresholds['tsb_red']:
        red_flags.append(f"TSB {current_tsb}，近期疲劳明显压过体能")
    elif current_tsb < thresholds['tsb_caution']:
        caution_flags.append(f"TSB {current_tsb}，适合降一点强度")
    elif current_tsb > thresholds['fresh']:
        caution_flags.append(f"TSB {current_tsb}，状态很新鲜；如果不是比赛/测试期，可能训练刺激偏少")
    else:
        good_flags.append("TSB 在可训练区间，整体状态可控")

    atl_gap = current_atl - current_ctl
    if atl_gap > thresholds['atl_red']:
        red_flags.append(f"ATL 高于 CTL {round(atl_gap)}，最近训练冲得比较猛")
    elif atl_gap > thresholds['atl_caution']:
        caution_flags.append(f"ATL 高于 CTL {round(atl_gap)}，近期疲劳正在累积")

    if ramp_rate > thresholds['ramp_fast']:
        caution_flags.append(f"CTL 近 7 天约 +{round(ramp_rate)}，加量速度偏快")
    elif ramp_rate < thresholds['ramp_drop']:
        caution_flags.append(f"CTL 近 7 天约 {round(ramp_rate)}，训练连续性有下滑")
    else:
        good_flags.append("近期训练负荷变化比较平稳")

    if avg_fatigue and avg_fatigue >= thresholds['fatigue_red']:
        red_flags.append(f"主观腿疲劳 {avg_fatigue}/5 偏高")
    elif avg_fatigue and avg_fatigue >= thresholds['fatigue_caution']:
        caution_flags.append(f"主观腿疲劳 {avg_fatigue}/5，强度课要谨慎")
    if avg_sleep and avg_sleep <= thresholds['sleep_red']:
        red_flags.append(f"睡眠评分 {avg_sleep}/5 偏低")
    if '感冒/发烧' in special_items or '生病' in special_items:
        red_flags.append("反馈里出现感冒/发烧/生病，暂停高强度")
    if pain_items:
        caution_flags.append("近期有不适记录：" + "、".join(sorted(set(pain_items))[:5]))

    if red_flags:
        status_label = "恢复优先，别硬顶"
        status_tone = "当前训练负荷和主观反馈提示风险偏高。"
        action_items = ["今天优先 Z1/Z2 或完全休息", "暂停 VO2、阈值、冲刺等高强度", "先把睡眠、补水、碳水和疼痛处理好", "连续 2-3 天观察腿疲劳和晨脉变化"]
    elif caution_flags:
        status_label = "适度疲劳，控制强度"
        status_tone = "可以训练，但不适合连续堆强度。"
        action_items = ["保留 1 个关键训练，其余用 Z2/恢复骑承接", "如果腿沉或睡眠差，把强度课改成耐力骑", "下一次关键课前至少留 24-48 小时恢复窗口"]
    elif current_ctl < 25 and tss_7 < 250:
        status_label = "刺激不足，需要建立规律"
        status_tone = "当前训练压力不高，更重要的是稳定频率。"
        action_items = ["先做到每周 3-4 次规律骑行", "以 Z2 为主，逐步增加单次时长", "不要急着堆 VO2，先把基础做起来"]
    else:
        status_label = "负荷合理，可以正常推进"
        status_tone = "体能、疲劳和状态处在相对健康的训练区间。"
        action_items = ["可以按计划进行关键训练", "高强度后安排 1-2 天低强度承接", "继续记录训练反馈，用主观状态校准 PMC"]

    reasons = red_flags + caution_flags + good_flags
    reason_text = "；".join(reasons[:4]) if reasons else "训练负荷数据没有明显异常。"

    st.markdown(f"""
<div class="load-hero">
    <div class="load-eyebrow">TRAINING LOAD VERDICT</div>
    <div class="load-main">{status_label}</div>
    <div class="load-why">{status_tone}<br><b>判断依据：</b>{reason_text}</div>
</div>
<div class="load-grid">
    <div class="load-card"><div class="k">体能 CTL</div><div class="v">{current_ctl}</div><div class="d">约 6 周训练积累</div></div>
    <div class="load-card"><div class="k">疲劳 ATL</div><div class="v">{current_atl}</div><div class="d">约 1 周近期疲劳</div></div>
    <div class="load-card"><div class="k">状态 TSB</div><div class="v">{current_tsb}</div><div class="d">CTL - ATL，新鲜度</div></div>
    <div class="load-card"><div class="k">近 7 天</div><div class="v">{tss_7} TSS</div><div class="d">{hours_7} 小时训练</div></div>
</div>
<div class="load-grid">
    <div class="load-card"><div class="k">近 28 天</div><div class="v">{tss_28} TSS</div><div class="d">{hours_28} 小时训练</div></div>
    <div class="load-card"><div class="k">周均训练</div><div class="v">{avg_weekly_hours}h</div><div class="d">近 28 天折算</div></div>
    <div class="load-card"><div class="k">CTL 变化</div><div class="v">{round(ramp_rate)}</div><div class="d">近 7 天变化</div></div>
    <div class="load-card"><div class="k">风险档位</div><div class="v">{risk_mode}</div><div class="d">{risk_desc}</div></div>
</div>
<div class="load-grid">
    <div class="load-card"><div class="k">主观反馈</div><div class="v">{len(recent_feedback)} 条</div><div class="d">睡眠 {avg_sleep or '-'} / 腿疲劳 {avg_fatigue or '-'}</div></div>
    <div class="load-card"><div class="k">TSB 阈值</div><div class="v">{thresholds['tsb_caution']} / {thresholds['tsb_red']}</div><div class="d">黄色 / 红色提醒线</div></div>
    <div class="load-card"><div class="k">ATL-CTL 阈值</div><div class="v">+{thresholds['atl_caution']} / +{thresholds['atl_red']}</div><div class="d">黄色 / 红色提醒线</div></div>
    <div class="load-card"><div class="k">主观疲劳阈值</div><div class="v">{thresholds['fatigue_caution']} / {thresholds['fatigue_red']}</div><div class="d">黄色 / 红色提醒线</div></div>
</div>
""", unsafe_allow_html=True)

    c1, c2 = st.columns([1.05, 1])
    with c1:
        st.subheader("接下来怎么练")
        for item in action_items:
            st.markdown(f"- {item}")
        st.markdown("""
<div class="load-panel">
    <div class="load-panel-title">怎么理解 CTL / ATL / TSB</div>
    <div class="load-panel-text">
        <b>CTL</b> 是长期训练积累，代表你目前能承受多少训练；<br>
        <b>ATL</b> 是短期疲劳，最近一周练得越猛越高，休息日会按 TSS=0 自然回落，并会从最后一次骑行持续衰减到今天；<br>
        <b>TSB</b> 是当前新鲜度，太低说明疲劳压住了状态，太高则可能训练刺激不足或正在减量。
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
        if recent_feedback:
            st.caption("最近训练反馈已接入负荷判断。")
        else:
            st.info("还没有训练反馈。去「📝 训练反馈」记录后，负荷判断会更贴近真实状态。")

    st.subheader("PMC 曲线")
    st.plotly_chart(plot_pmc(rides), use_container_width=True)
    st.caption("蓝线=体能 CTL · 橙线=疲劳 ATL · 柱状=状态 TSB。TSB 不是越高越好，关键看是否匹配训练阶段。")

    with st.expander("查看训练记录明细", expanded=False):
        show_cols = [c for c in ['date', 'duration_h', 'avg_power', 'normalized_power', 'tss'] if c in df_pmc.columns]
        if show_cols:
            st.dataframe(df_pmc[show_cols].tail(30).astype(str), use_container_width=True, hide_index=True)
        else:
            st.info("当前记录缺少可展示字段。")

elif page == "🧠 AI 功率分析":
    st.title("🧠 AI 功率分析")
    st.caption("把骑行数据转成训练判断：当前强弱项、该练什么、什么时候该恢复。")

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

    # AI usage tracking
    uid = st.session_state.user["user_id"]
    used = get_ai_usage(uid)
    limit = get_ai_limit(uid)
    remaining = limit - used
    plan_name = PLANS[st.session_state.user.get("plan", "free")]["name"]

    if remaining <= 0:
        st.error(f"🔒 本月 AI 分析次数已用完（{used}/{limit}）。升级套餐解锁更多次数。")
        st.caption("在侧边栏「⬆️ 升级套餐」中使用内测邀请码升级")
        st.stop()

    uploaded_rides = st.session_state.get('uploaded_rides', [])
    historical = load_historical()

    st.markdown(f"""
<div class="ai-panel hot">
    <div class="ai-panel-title">本次分析会做什么？</div>
    <div class="ai-panel-text">
        AI 会读取当前选择的数据范围，判断 FTP、骑手类型、训练量、疲劳抗性和待改善区间。
        <b>只有点击「🔬 开始 AI 分析」才会消耗 1 次额度</b>；切换数据范围、查看训练一致性不会扣次数。
    </div>
</div>
<div class="ai-small-grid">
    <div class="ai-mini"><div class="k">当前套餐</div><div class="v">{plan_name}</div></div>
    <div class="ai-mini"><div class="k">本月剩余额度</div><div class="v">{remaining}/{limit} 次</div></div>
    <div class="ai-mini"><div class="k">扣费规则</div><div class="v">按钮触发扣除1次</div></div>
</div>
""", unsafe_allow_html=True)

    st.subheader("1. 选择分析数据")
    use_all = st.toggle("合并全历史数据", value=False if uploaded_rides else True,
                        key="ai_use_all",
                        help="开启=上传文件+历史数据一起分析；关闭=只看本次上传文件")
    if use_all:
        rides = merge_rides(historical, uploaded_rides)
        source_label = "合并历史数据"
    elif uploaded_rides:
        rides = uploaded_rides
        source_label = "仅本次上传"
    else:
        rides = historical
        source_label = "历史数据"
    rides.sort(key=lambda x: x['date'])
    rides = enrich_rides(rides)

    if not rides:
        render_empty_data_state(
            "AI 分析需要先有骑行数据",
            "AI 会综合 FIT、FTP、训练反馈、睡眠和恢复记录。没有 FIT 时，系统无法判断能力结构和训练负荷。",
            ["先在骑手档案填写基础信息", "上传最近 4-12 周 FIT 文件", "补一条训练反馈后再生成 AI 分析"]
        )
        st.stop()

    st.caption(data_scope_caption(rides, historical, uploaded_rides, source_label))

    profile = load_profile()
    pweight = profile.get('weight', 69)
    actual_ftp = profile.get('ftp_test', 0)
    est_ftp = estimate_ftp(rides)
    effective_ftp = actual_ftp if actual_ftp > 0 else est_ftp

    c1, c2, c3 = st.columns(3)
    c1.metric("数据范围", source_label, f"{len(rides)} 条记录")
    c2.metric("FTP来源", "手动填写" if actual_ftp > 0 else "自动估算", f"{effective_ftp}W")
    c3.metric("体重", f"{pweight}kg", f"{round(effective_ftp/pweight, 1)} W/kg" if pweight and effective_ftp else "")

    feedback = load_feedback()
    feedback_latest = max((x.get("date", "") for x in feedback), default="")
    feedback_stamp = max((x.get("created_at", "") for x in feedback), default="")
    feedback_summary = summarize_recent_feedback(feedback)
    sleep_records = load_wearable_sleep()
    sleep_latest = max((x.get("date", "") for x in sleep_records), default="")
    sleep_stamp = max((x.get("created_at", "") for x in sleep_records), default="")
    st.caption(f"已接入训练反馈：最近记录 {feedback_summary.get('count', 0)} 条" + (f"｜最新 {feedback_latest}" if feedback_latest else "｜暂无反馈"))
    st.caption(f"已接入手表睡眠：最近记录 {len(sleep_records)} 条" + (f"｜最新 {sleep_latest}" if sleep_latest else "｜暂无睡眠记录"))
    if feedback:
        latest_fb = feedback[0]
        fb_pains = "、".join(latest_fb.get("pains", []) or []) or "无"
        fb_specials = "、".join(latest_fb.get("specials", []) or []) or "无"
        st.success(
            f"✅ AI 已读取训练反馈：{latest_fb.get('date', '-')}｜睡眠 {latest_fb.get('sleep_quality', '-')}｜"
            f"腿疲劳 {latest_fb.get('leg_fatigue', '-')}｜RPE {latest_fb.get('rpe', '-')}｜"
            f"不适：{fb_pains}｜特殊：{fb_specials}"
        )
        with st.expander("查看已接入的训练反馈", expanded=True):
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
            st.dataframe(df_ai_fb.astype(str), use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ AI 暂未读取到训练反馈。请先到「📝 训练反馈」保存一条记录。")

    if sleep_records:
        latest_sleep = sorted(sleep_records, key=lambda x: x.get("date", ""), reverse=True)[0]
        nap_txt = f"｜午睡 {latest_sleep.get('nap_minutes', 0)}min｜醒后{latest_sleep.get('nap_after', '未记录')}" if latest_sleep.get('nap_minutes', 0) else ""
        st.success(
            f"✅ AI 已读取手表睡眠：{latest_sleep.get('date', '-')}｜夜间睡眠 {latest_sleep.get('sleep_hours', '-')}h｜"
            f"评分 {latest_sleep.get('sleep_score', '-')}｜HRV {latest_sleep.get('hrv', '-')}｜"
            f"静息心率 {latest_sleep.get('rest_hr', '-')}｜压力 {latest_sleep.get('stress_score', '-')}｜"
            f"恢复分 {latest_sleep.get('body_battery', '-')}{nap_txt}"
        )
        with st.expander("查看已接入的手表睡眠", expanded=False):
            df_sleep = pd.DataFrame(sleep_records[:7]).rename(columns={
                "date": "日期", "source": "来源", "sleep_hours": "夜间睡眠h", "sleep_score": "评分",
                "rest_hr": "静息心率", "hrv": "HRV", "stress_score": "压力", "body_battery": "恢复分",
                "nap_minutes": "午睡min", "nap_quality": "午睡质量", "nap_after": "醒后状态", "nap_to_training": "到训练间隔", "note": "备注"
            })
            sleep_cols = [c for c in ["日期", "来源", "夜间睡眠h", "评分", "静息心率", "HRV", "压力", "恢复分", "午睡min", "午睡质量", "醒后状态", "到训练间隔", "备注"] if c in df_sleep.columns]
            st.dataframe(df_sleep[sleep_cols].astype(str), use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ AI 暂未读取到手表睡眠数据。可在「🛌 恢复与睡眠」录入一条记录。")

    # Clear stale diagnosis when data source, feedback, or sleep changes
    ai_signature = f"{len(rides)}|{feedback_latest}|{feedback_stamp}|{len(feedback)}|{sleep_latest}|{sleep_stamp}|{len(sleep_records)}|{actual_ftp}|{pweight}"
    if st.session_state.get("ai_signature") != ai_signature:
        st.session_state.pop("ai_diagnosis", None)
        st.session_state.ai_signature = ai_signature

    st.subheader("2. 生成 AI 诊断")

    # Show persisted diagnosis if available
    if "ai_diagnosis" in st.session_state:
        st.markdown("""
<div class="ai-panel good">
    <div class="ai-panel-title">诊断已生成</div>
    <div class="ai-panel-text">下方结果来自当前数据范围。若你上传了新数据或修改了 FTP，可点击重新分析。</div>
</div>
""", unsafe_allow_html=True)
        st.markdown(st.session_state.ai_diagnosis)
        if st.button("🔄 重新分析", key="ai_reanalyze",
                     help="清除当前诊断，下一次点击开始分析会重新扣 1 次"):
            st.session_state.pop("ai_diagnosis", None)
            st.rerun()

    # Only analyze on button click - disable after analysis
    already_analyzed = bool(st.session_state.get("ai_diagnosis"))
    if not already_analyzed:
        st.caption("点击后将消耗 1 次 AI 分析额度。页面刷新、切换数据范围、查看训练一致性不会自动扣费。")
    if st.button("🔬 开始 AI 分析", type="primary", use_container_width=True,
                 key="ai_analyze_btn", disabled=already_analyzed,
                 help="已分析完成" if already_analyzed else "点击开始分析，会消耗 1 次 AI 额度"):
        try:
            ftp = effective_ftp
            best = estimate_best_powers(rides, ftp)

            if actual_ftp > 0:
                st.info(f"FTP: **{actual_ftp}W**" + (f"（估算: {est_ftp}W）" if abs(actual_ftp - est_ftp) > 10 else ""))
            else:
                st.info(f"估算 FTP: **{est_ftp}W**")

            result = generate_diagnosis(rides, ftp, best, pweight, feedback, sleep_records)
            st.session_state.ai_diagnosis = result
            # Persist a structured AI context so the training-plan page can actually read it.
            try:
                ai_ctx = {
                    "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
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
    st.caption("这部分只根据数据统计，不消耗 AI 次数。")
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

elif page == "📋 训练课表":
    require_plan(1, "📋 训练课表")

    uploaded_rides = st.session_state.get('uploaded_rides', [])
    historical = load_historical()
    with st.expander("⚙️ 数据来源设置", expanded=False):
        use_all = st.toggle("合并全历史数据", value=False if uploaded_rides else True, help="通常不用改。打开后会把历史存档和本次上传一起用于估算 FTP / 功率区间。")
        st.caption(f"本次上传 {len(uploaded_rides)} 条｜历史存档 {len(historical)} 条｜合并后 {len(merge_rides(historical, uploaded_rides))} 条")

    source_label = "合并历史数据" if use_all else ("仅本次上传" if uploaded_rides else "历史数据")
    rides = merge_rides(historical, uploaded_rides) if use_all else (uploaded_rides or historical)
    rides.sort(key=lambda x: x['date'])
    rides = enrich_rides(rides)
    if not rides:
        render_empty_data_state(
            "训练课表需要先建立功率基准",
            "课表会根据 FTP、训练负荷、恢复状态和训练目标生成。请先上传 FIT；如果有实测 FTP，先在骑手档案填写，课表会更准确。",
            ["填写体重、实测 FTP、最大心率和训练目标", "上传 FIT 建立功率和负荷数据", "再回来生成本周训练课表和 ZWO"]
        )
        st.stop()

    st.caption(data_scope_caption(rides, historical, uploaded_rides, source_label))

    profile = load_profile()
    est_ftp = estimate_ftp(rides)
    actual_ftp = profile.get('ftp_test', 0) or 0
    ftp = actual_ftp if actual_ftp > 0 else est_ftp
    ftp_source = f"客户填写 FTP {actual_ftp}W" if actual_ftp > 0 else f"FIT 自动估算 FTP {est_ftp}W"
    cycle_status = infer_cycle_status_for_date(datetime.date.today(), profile)
    weight = profile.get('weight', 69) or 69
    wkg = round(ftp / weight, 1) if ftp and weight else 0

    st.markdown("""
<style>
.plan-hero{padding:1.1em 1.15em;border-radius:16px;background:linear-gradient(135deg,rgba(255,107,53,.16),rgba(22,27,34,.96));border:1px solid rgba(255,107,53,.28);margin:.6em 0 1em}.plan-kicker{color:#ff9a68;font-size:.78em;font-weight:800;letter-spacing:.08em}.plan-title{color:#f0f6fc;font-size:1.45em;font-weight:850;margin:.25em 0}.plan-sub{color:#aab6c3;font-size:.9em;line-height:1.6}.plan-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.7em;margin:.8em 0 1em}.plan-card{background:var(--tc-surface);border:1px solid var(--tc-border);border-radius:13px;padding:.85em;min-height:5.6em}.plan-card .k{color:var(--tc-subtle);font-size:.72em}.plan-card .v{color:#f0f6fc;font-size:1.08em;font-weight:800;margin:.18em 0}.plan-card .d{color:var(--tc-subtle);font-size:.75em;line-height:1.35}.plan-day{background:var(--tc-surface);border:1px solid var(--tc-border);border-radius:10px;padding:.68em .66em;min-height:12em;margin:.15em 0}.plan-day .dow{color:var(--tc-subtle);font-size:.68em;font-weight:800}.plan-day .name{color:#f0f6fc;font-size:.82em;font-weight:800;margin-top:.28em;line-height:1.25}.plan-day .detail{color:var(--tc-subtle);font-size:.68em;margin-top:.35em;line-height:1.35;min-height:2.4em}.plan-pill{display:inline-block;background:var(--tc-surface-2);border-radius:5px;padding:.12em .42em;margin:.15em .16em .05em 0;font-size:.62em}.plan-warning{padding:.85em 1em;border-radius:12px;background:rgba(240,192,64,.1);border:1px solid rgba(240,192,64,.28);color:#d8c58a;font-size:.86em;line-height:1.55}@media(max-width:1050px){.plan-grid{grid-template-columns:1fr 1fr}}@media(max-width:720px){.plan-grid{grid-template-columns:1fr}}
</style>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="plan-hero">
  <div class="plan-kicker">TRAINING PLAN BUILDER</div>
  <div class="plan-title">先判断这周该怎么练，再生成可执行课表</div>
  <div class="plan-sub">根据 FIT 推算 FTP / 功体比，并结合训练负荷、睡眠/反馈、目标、可训练天数和周总量，动态生成本周重点、周期递进和 Zwift .ZWO 文件。</div>
</div>
""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        goal = st.selectbox("训练目标", ["恢复体能 / 重建基础", "减脂减重 / 燃脂骑", "提升 FTP / 功体比", "备战绕圈赛 / 平路冲刺", "备战爬坡 / 长距离", "赛前减量 / 巅峰", "维持现状 / 休闲骑"])
    with c2:
        days = st.slider("每周训练日", 3, 7, 5)
    with c3:
        weeks = st.slider("计划周期", 1, 12, 4)
    with c4:
        hours = st.slider("每周总时长 h", 4, 20, 8)

    # ── dynamic readiness inputs: training load + feedback + sleep ──
    df_plan = pd.DataFrame(rides).sort_values('date')
    df_plan['date_dt'] = pd.to_datetime(df_plan['date'], errors='coerce')
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
        readiness_reasons.append("负荷/反馈提示风险偏高，本周自动降量并替换高强度课")
    elif current_tsb < -12 or current_atl > current_ctl + 10 or (avg_sleep and avg_sleep <= 3) or (avg_fatigue and avg_fatigue >= 3.5) or pain_items:
        readiness_label = "谨慎推进"
        readiness_factor = 0.82
        intensity_cap = "caution"
        readiness_reasons.append("近期疲劳或主观反馈偏紧，本周保留少量质量课，其余降为 Z2/恢复")
    else:
        readiness_reasons.append("训练负荷和主观反馈未见明显红旗，可按目标推进")
    if ramp_rate > 8:
        readiness_factor = min(readiness_factor, 0.9)
        readiness_reasons.append(f"CTL 近 7 次约 +{round(ramp_rate)}，加量偏快")
    if cycle_status and isinstance(cycle_status, str) and '经期' in cycle_status:
        readiness_factor = min(readiness_factor, 0.85)
        intensity_cap = "caution" if intensity_cap == "normal" else intensity_cap
        readiness_reasons.append("本周经期：高强度课可后移或降一级")
    if hours >= 16:
        readiness_reasons.append("用户设置周总量偏高，系统会优先保护质量课并限制过长训练")

    ai_plan_hint = "AI 未参与本次排课；当前已基于 FIT、训练负荷、睡眠/反馈动态生成，不影响使用。"
    ai_plan_ctx = {}
    try:
        user = st.session_state.get("user")
        if user:
            user_dir = DATA_DIR / user.get("user_id", "")
            ai_ctx_file = user_dir / "ai_training_plan_context.json"
            if ai_ctx_file.exists():
                with open(ai_ctx_file, "r", encoding="utf-8") as f:
                    ai_plan_ctx = json.load(f)
                ai_plan_hint = f"已接入 AI 分析（{ai_plan_ctx.get('generated_at', '-') }）：{ai_plan_ctx.get('ftp_source', '-') } FTP {ai_plan_ctx.get('ftp', '-')}W，反馈 {ai_plan_ctx.get('feedback_count', 0)} 条"
                ai_risks = ai_plan_ctx.get("feedback_risk_flags", []) or []
                if ai_risks:
                    readiness_factor = min(readiness_factor, 0.9)
                    readiness_reasons.append("AI 分析提示主观恢复风险：" + "；".join(ai_risks[:2]))
            elif st.session_state.get("ai_diagnosis"):
                ai_plan_hint = "已读取本次会话 AI 报告；未落盘结构化结论，但不影响当前动态排课。"
    except Exception:
        pass


    if '减脂' in goal or '燃脂' in goal or '减重' in goal:
        phase = "fatloss"
    elif wkg < 2.5 or '恢复' in goal:
        phase = "rebuild"
    elif '绕圈' in goal:
        phase = "crit"
    elif '爬坡' in goal:
        phase = "climb"
    elif '减量' in goal:
        phase = "taper"
    elif wkg < 3 or 'FTP' in goal:
        phase = "build"
    else:
        phase = "maintain"

    phase_meta = {
        'rebuild': {'name': '基础重建', 'icon': '🧱', 'desc': '低强度高频次，重建有氧引擎', 'color': '#3fb950'},
        'fatloss': {'name': '减脂燃脂', 'icon': '🔥', 'desc': 'Z2 为主，稳定消耗，保护恢复和力量感', 'color': '#ff9a3d'},
        'build': {'name': '提升期', 'icon': '📈', 'desc': '甜区+阈值，稳健提升 FTP', 'color': '#d29922'},

        'crit': {'name': '绕圈赛专项', 'icon': '🔥', 'desc': '阈值、VO2max、反复冲刺与比赛节奏', 'color': '#f85149'},
        'climb': {'name': '爬坡专项', 'icon': '⛰️', 'desc': '甜区爬坡、阈值爬坡与长距离耐力', 'color': '#bc8cff'},
        'taper': {'name': '赛前减量', 'icon': '🎯', 'desc': '降低总量，保留神经与比赛强度', 'color': '#ff6b35'},
        'maintain': {'name': '巩固期', 'icon': '🔄', 'desc': '维持功体比和骑行习惯', 'color': '#58a6ff'},
    }
    pm = phase_meta[phase]

    def training_days(n):
        return {3:['周二','周四','周日'],4:['周二','周四','周六','周日'],5:['周二','周三','周五','周六','周日'],6:['周二','周三','周四','周五','周六','周日'],7:['周一','周二','周三','周四','周五','周六','周日']}[n]

    def zone_style(kind):
        m = {'rest':('var(--tc-surface-2)','#484f58','休息'),'recovery':('#1a2332','#58a6ff','Z1'),'z2':('#1a2e1a','#3fb950','Z2'),'fatloss':('#2e2416','#ff9a3d','燃脂'),'long':('#1a2e1a','#3fb950','Z2'),'tempo':('#2e2416','#d29922','Tempo'),'sweet':('#2e2016','#db6d28','甜区'),'threshold':('#2e1616','#f85149','阈值'),'vo2':('#261a2e','#bc8cff','VO2max'),'crit':('#2e1a16','#ff6b35','冲刺'),'climb':('#261a2e','#bc8cff','爬坡'),'openers':('#2e1616','#ff6b35','激活'),'race':('#2e1616','#ff6b35','比赛')}
        return m.get(kind, ('var(--tc-surface-2)','var(--tc-subtle)','混合'))

    def tss(kind, h):
        return int((h or 0) * {'recovery':30,'z2':50,'fatloss':48,'long':52,'tempo':65,'sweet':75,'threshold':85,'vo2':95,'crit':90,'climb':82,'openers':60,'race':100}.get(kind,50))

    def session_pool(phase):
        z2_lo, z2_hi = round(ftp*.55), round(ftp*.75)
        sweet, thresh, vo2, sprint = round(ftp*.90), round(ftp*.97), round(ftp*1.10), round(ftp*1.50)
        pools = {
            'rebuild': [('z2','Z2 有氧耐力',f'{z2_lo}-{z2_hi}W，能完整说短句',1.0,.8,3.0),('z2','Z2 + 轻微变速','Z2 为主，每 30min 来 15s 轻冲刺',1.0,.8,2.5),('long','长距离 Z2','全程可控，不追均速',1.6,1.4,5.0),('recovery','恢复骑 / 晃腿',f'≤{z2_lo}W，越轻松越好',.45,.4,1.0),('z2','Z2 技术骑','踏频、转弯、补给节奏练习',.8,.7,2.0),('recovery','核心力量 20min + 轻松骑','不做力竭训练',.35,.3,.8),('recovery','主动恢复','散步/拉伸/超轻松骑',.3,.2,.7)],
            'fatloss': [('fatloss','燃脂 Z2 稳态',f'{z2_lo}-{z2_hi}W，能说短句，优先稳定时长',1.35,1.0,3.0),('recovery','Z1 恢复骑',f'≤{z2_lo}W，降低压力，保留训练习惯',.55,.4,1.0),('fatloss','Z2 + 高踏频唤醒','Z2 为主，每 12-15min 加 1min 高踏频，不冲功率',1.05,.8,2.0),('long','长距离燃脂骑','Z2 下沿为主，补水电解质，避免空腹硬撑',1.75,1.3,4.5),('tempo','Tempo 短维持',f'{round(ftp*.78)}-{round(ftp*.84)}W，2×10min，保持力量感',.75,.6,1.2),('fatloss','通勤/轻松有氧','轻松可持续，累计消耗，不追均速',.8,.6,2.0),('recovery','完全休息或散步','睡眠和饮食执行优先',.3,.0,.6)],
            'build': [('sweet','甜区 3×15min',f'{sweet}W，间隔 5min Z1',1.25,1.1,1.7),('z2','Z2 耐力',f'{z2_lo}-{z2_hi}W，稳定踩踏',1.35,1.0,4.0),('threshold','阈值 4×8min',f'{thresh}W，间隔 4min Z1',1.25,1.1,1.7),('long','长距离 Z2 + 爬坡','Z2 为主，含 2-3 段自然爬坡',2.0,1.5,5.5),('recovery','Z1 晃腿',f'≤{z2_lo}W，促进恢复',.55,.45,1.0),('tempo','Tempo 稳态',f'{round(ftp*.82)}W 左右，别顶爆',1.0,.8,2.0),('recovery','主动恢复','轻松骑或完全休息',.4,.3,.8)],
            'crit': [('threshold','阈值 4×8min',f'{thresh}W，建立可重复输出',1.2,1.1,1.6),('z2','Z2 耐力',f'{z2_lo}-{z2_hi}W，低压积累',1.2,1.0,3.5),('vo2','VO2max 6×3min + 冲刺',f'{vo2}W + 8×15s {sprint}W',1.25,1.0,1.6),('crit','绕圈模拟 / 团体骑','随机进攻、追击、出弯加速',1.8,1.3,4.0),('recovery','Z1 晃腿 + 起跳练习',f'≤{z2_lo}W，少量神经刺激',.55,.45,1.0),('tempo','Tempo + 小冲刺','节奏骑中加入 6-8 次短冲',1.0,.8,2.0),('recovery','主动恢复','保持新鲜感',.35,.3,.7)],
            'climb': [('sweet','甜区爬坡 3×20min',f'{sweet}W，坡度 3-5%',1.35,1.2,1.8),('z2','Z2 + 爬坡',f'{z2_lo}-{z2_hi}W，低踏频可控',1.4,1.1,3.8),('climb','阈值爬坡 4×10min',f'{thresh}W，坡度 3-5%',1.35,1.2,1.8),('long','长距离爬坡','总爬升优先，强度别失控',2.2,1.6,5.8),('recovery','Z1 晃腿',f'≤{z2_lo}W',.55,.45,1.0),('tempo','爬坡 Tempo',f'{round(ftp*.82)}W 左右，稳定输出',1.0,.8,2.0),('recovery','主动恢复','拉伸/轻松骑',.35,.3,.7)],
            'taper': [('openers','赛前激活 3×5min',f'{round(ftp*.95)}W，保感觉不堆疲劳',.7,.6,1.0),('recovery','Z1 轻松晃腿',f'≤{z2_lo}W',.5,.4,.8),('openers','赛前预检 2×3min','比赛强度，检查装备和补给',.6,.5,.8),('race','比赛日 / 模拟测试','热身充分，执行策略',1.0,.8,2.5),('recovery','完全休息或散步','睡眠和碳水优先',.25,.0,.5),('recovery','轻松转腿','只唤醒，不训练',.35,.3,.6),('recovery','休息','装备检查',.2,.0,.4)],
            'maintain': [('z2','Z2 或甜区维持','按当天状态二选一',1.0,.8,2.5),('z2','Z2 + 爬坡','享受骑行，不堆疲劳',1.2,1.0,3.0),('threshold','阈值维持 3×10min',f'{round(ftp*.95)}W',1.1,1.0,1.5),('long','长距离探险骑','新路线、美景、稳定补给',1.8,1.4,4.5),('recovery','轻松骑 / 团体骑','社交节奏，别拼',.6,.5,1.2),('tempo','Tempo 维持','中等强度，不做力竭',.9,.8,1.8),('recovery','主动恢复','轻松活动',.3,.2,.7)]
        }
        return [{'kind':k,'name':n,'detail':d,'share':sh,'min':mn,'max':mx} for k,n,d,sh,mn,mx in pools[phase]]

    def week_factor(wk):
        if phase == 'taper':
            base = max(.45, .75 - .08*((wk-1)%4))
        else:
            base = [.92, 1.00, 1.08, .68][(wk-1)%4]
        return round(base * (readiness_factor if wk == 1 else 1.0), 2)

    def allocate(items, target_h):
        total_share = sum(x['share'] for x in items) or 1
        for x in items:
            raw = target_h * x['share'] / total_share
            x['dur_h'] = round(max(x['min'], min(x['max'], raw)), 1)
        diff = round(target_h - sum(x['dur_h'] for x in items), 1)
        flex = [x for x in items if x['kind'] in ('long','z2','fatloss','tempo')]
        if diff > 0:
            for x in flex:
                add = min(round(x['max']-x['dur_h'],1), diff)
                x['dur_h'] = round(x['dur_h'] + add, 1); diff = round(diff-add,1)
                if diff <= 0: break
        elif diff < 0:
            for x in reversed(flex or items):
                sub = min(round(x['dur_h']-x['min'],1), -diff)
                x['dur_h'] = round(x['dur_h'] - sub, 1); diff = round(diff+sub,1)
                if diff >= 0: break
        return items

    def build_week_plan(wk):
        active_days = training_days(days)
        items = [dict(x) for x in session_pool(phase)[:days]]
        if wk == 1 and intensity_cap in ('recovery', 'caution'):
            hard_seen = 0
            for x in items:
                if x['kind'] in ('sweet','threshold','vo2','crit','climb','openers','race'):
                    hard_seen += 1
                    original = x['name']
                    if intensity_cap == 'recovery' or hard_seen > 1:
                        x.update({'kind':'recovery','name':f'恢复替代（原：{original}）','detail':'因训练负荷/睡眠/反馈风险，本周改为 Z1-Z2 恢复。','share':0.55,'min':0.4,'max':1.2})
                    else:
                        x.update({'kind':'z2','name':f'降级执行（原：{original}）','detail':'保留训练节奏，但强度降为 Z2，不做力竭。','share':0.9,'min':0.8,'max':2.0})
        items = allocate(items, round(hours*week_factor(wk),1))
        by_day = {d: item for d, item in zip(active_days, items)}
        rows = []
        for day in ['周一','周二','周三','周四','周五','周六','周日']:
            if day in by_day:
                item = by_day[day]; item.update({'day':day,'rest':False})
            else:
                item = {'day':day,'kind':'rest','name':'休息 / 恢复','detail':'不安排结构化训练','dur_h':0,'rest':True}
            rows.append(item)
        return rows

    all_weeks = []
    for wk in range(1, weeks+1):
        rows = build_week_plan(wk)
        actual_h = round(sum(x.get('dur_h',0) for x in rows), 1)
        actual_tss = sum(tss(x['kind'], x.get('dur_h',0)) for x in rows)
        all_weeks.append({'wk':wk,'rows':rows,'target_h':round(hours*week_factor(wk),1),'actual_h':actual_h,'tss':actual_tss})

    first = all_weeks[0]
    active_count = sum(1 for x in first['rows'] if not x.get('rest'))
    key_sessions = [x['name'] for x in first['rows'] if x['kind'] in ('sweet','threshold','vo2','crit','climb','openers')][:2]
    key_text = '、'.join(key_sessions) if key_sessions else '以 Z2 耐力和恢复为主'
    load_note = readiness_label
    if hours >= 16: load_note += '｜高周量设置'
    elif hours <= 5: load_note += '｜先建立连续性'
    if intensity_cap == 'recovery':
        key_text = '本周高强度自动替换为恢复/Z2'
    elif intensity_cap == 'caution' and key_sessions:
        key_text = '保留 1 个关键课，其余降级'

    evidence_text = '；'.join(readiness_reasons[:4])
    st.markdown(f"""
<div class="plan-grid">
  <div class="plan-card"><div class="k">当前阶段</div><div class="v">{pm['icon']} {pm['name']}</div><div class="d">{pm['desc']}</div></div>
  <div class="plan-card"><div class="k">功率基础</div><div class="v">FTP {ftp}W</div><div class="d">{wkg} W/kg · {weight}kg</div></div>
  <div class="plan-card"><div class="k">本周安排</div><div class="v">{active_count} 天 / {first['actual_h']:.1f}h</div><div class="d">约 {first['tss']} TSS｜校正系数 {readiness_factor}</div></div>
  <div class="plan-card"><div class="k">关键训练</div><div class="v" style="font-size:.96em;">{key_text}</div><div class="d">{load_note}</div></div>
</div>
""", unsafe_allow_html=True)

    # Explain why this week is arranged this way, like a coach briefing before the table.
    if intensity_cap == "recovery":
        plan_logic_title = "为什么本周偏恢复？"
        plan_logic_main = "当前负荷或主观反馈提示恢复风险，系统优先降低强度密度，把高强度课替换成恢复骑 / Z2。"
    elif intensity_cap == "caution":
        plan_logic_title = "为什么本周谨慎推进？"
        plan_logic_main = "当前可以训练，但恢复余量不算宽。系统保留少量关键课，其余用 Z2 / Tempo 承接，避免继续堆疲劳。"
    elif phase == "fatloss":
        plan_logic_title = "为什么本周以 Z2 燃脂为主？"
        plan_logic_main = "你的目标偏减脂/燃脂，系统优先安排稳定可持续的 Z2 和少量 Tempo，让消耗可持续，同时保护恢复。"
    elif phase in ("build", "climb", "crit"):
        plan_logic_title = "为什么本周有质量课？"
        plan_logic_main = "训练负荷和反馈没有明显红旗，目标需要能力提升，系统安排关键质量课，同时用 Z2/恢复日保证吸收。"
    elif phase == "taper":
        plan_logic_title = "为什么本周降量保强度？"
        plan_logic_main = "当前目标是赛前减量/巅峰，系统降低总量，只保留少量激活强度，重点是新鲜感和比赛状态。"
    else:
        plan_logic_title = "为什么本周这样安排？"
        plan_logic_main = "系统按当前 FTP、目标、周时长和训练负荷生成一个稳健方案，优先保持连续性而不是盲目加量。"

    plan_logic_points = [
        f"目标：{goal} → 当前阶段判定为 {pm['name']}。",
        f"负荷：CTL {current_ctl} / ATL {current_atl} / TSB {current_tsb}，近 7 天 {tss_7} TSS。",
        f"反馈：睡眠 {avg_sleep or '-'} / 腿疲劳 {avg_fatigue or '-'} / 能量 {avg_energy or '-'}。",
        f"本周：{active_count} 天、{first['actual_h']:.1f} 小时、约 {first['tss']} TSS，关键训练：{key_text}。",
    ]
    if ai_plan_hint and "未参与" not in ai_plan_hint:
        plan_logic_points.append(f"AI 上下文：{ai_plan_hint}")
    if evidence_text:
        plan_logic_points.append(f"调整依据：{evidence_text}")

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
        st.markdown("""
**读法：**如果 TSB 偏低、ATL 明显高于 CTL、睡眠差、腿疲劳高或有疼痛/生病记录，课表会自动降级；如果状态较好，才会保留阈值、VO2、绕圈赛或爬坡专项质量课。
""")

    if hours >= 16:
        st.markdown('<div class="plan-warning">⚠️ 你设置的周总量偏高。系统会优先保护强度课质量，并把额外时间放进 Z2 / 长距离；如果睡眠、腿疲劳或经期状态不好，建议下调 10-25%。</div>', unsafe_allow_html=True)

    for week in all_weeks:
        title = f"第 {week['wk']} 周｜目标 {week['target_h']:.1f}h｜实际 {week['actual_h']:.1f}h｜约 {week['tss']} TSS"
        with st.expander(title, expanded=(week['wk']==1)):
            bars = ''.join(f'<span style="display:inline-block;width:{max(7,int((x.get("dur_h",0)/max(week["actual_h"],0.1))*100))}%;height:6px;background:{zone_style(x["kind"])[1]};border-radius:2px;margin:0 1px;" title="{x["day"]}: {x["name"]}"></span>' for x in week['rows'] if not x.get('rest'))
            st.markdown(f'<div style="display:flex;gap:2px;margin:.2em 0 .8em;">{bars}</div>', unsafe_allow_html=True)
            cols = st.columns(7)
            for i, item in enumerate(week['rows']):
                bg, border, zone = zone_style(item['kind'])
                dur = item.get('dur_h',0)
                dur_display = f"{dur:.1f}h" if dur > 0 else "休息"
                tss_str = '—' if dur <= 0 else f"~{tss(item['kind'], dur)}"
                with cols[i]:
                    st.markdown(f"""
<div class="plan-day" style="background:{bg}; border-top:3px solid {border};">
  <div class="dow">{item['day']}</div><div class="name">{item['name']}</div><div class="detail">{item['detail']}</div>
  <div style="margin-top:.55em;"><span class="plan-pill" style="color:var(--tc-subtle);">⏱ {dur_display}</span><span class="plan-pill" style="color:{border};">{zone}</span><span class="plan-pill" style="color:var(--tc-subtle);">TSS {tss_str}</span></div>
</div>
""", unsafe_allow_html=True)
            if week['wk'] % 4 == 0 and phase != 'taper':
                st.info("第 4 周为减量/吸收周：总量下降，保留轻刺激。状态好可安排 FTP 小测试；状态差就只做恢复和 Z2。")
            if week['wk'] == 1 and cycle_status and isinstance(cycle_status, str) and '经期' in cycle_status:
                st.info("🩸 本周正值经期：可以练，但建议把高强度课后移或降一级执行。恢复优先。")

    def make_zwo_xml(name, desc, segments):
        return f'''<?xml version="1.0" encoding="UTF-8"?>\n<workout_file>\n  <author>TrueCadence</author>\n  <name>{name}</name>\n  <description>{desc}</description>\n  <sportType>bike</sportType>\n  <workout>\n{segments}\n  </workout>\n</workout_file>\n'''
    def steady(sec, frac): return f'    <SteadyState Duration="{max(60,int(sec))}" Power="{frac:.3f}"/>'
    def intervals(rep,on,off,onp,offp): return f'    <IntervalsT Repeat="{rep}" OnDuration="{int(on)}" OffDuration="{int(off)}" OnPower="{onp:.3f}" OffPower="{offp:.3f}"/>'
    def zwo_for_item(wk, item):
        if item.get('rest') or item.get('dur_h',0) <= 0: return None
        total = int(item['dur_h']*3600); kind = item['kind']; z2 = .65; z1 = .45
        if kind in ('z2','fatloss','long','tempo'):
            seg = steady(total, .78 if kind == 'tempo' else (.62 if kind == 'fatloss' else z2))
        elif kind == 'recovery':
            seg = steady(total, z1)
        elif kind == 'sweet':
            seg = steady(600,z2)+"\n"+intervals(3,900,300,.90,z2)+"\n"+steady(max(300,total-4200),z2)
        elif kind in ('threshold','climb'):
            seg = steady(600,z2)+"\n"+intervals(4,480,240,.97 if kind=='threshold' else .95,z2)+"\n"+steady(max(300,total-3480),z2)
        elif kind == 'vo2':
            seg = steady(600,z2)+"\n"+intervals(6,180,180,1.10,z2)+"\n"+intervals(8,15,45,1.50,z2)+"\n"+steady(max(300,total-3240),z2)
        elif kind == 'crit':
            seg = steady(600,z2)+"\n"+intervals(5,240,180,.95,z2)+"\n"+intervals(10,20,100,1.35,z2)+"\n"+steady(max(300,total-3900),z2)
        elif kind == 'openers':
            seg = steady(600,z2)+"\n"+intervals(3,300,300,.95,z1)+"\n"+steady(max(180,total-2400),z1)
        elif kind == 'race':
            seg = steady(max(900,total), z2)
        else:
            seg = steady(total, z2)
        safe_day = item['day'].replace('周','D')
        fname = f"TC_W{wk}_{safe_day}_{kind}.zwo"
        title = f"W{wk} {item['day']} {item['name']}"
        return fname, make_zwo_xml(title, item['detail'], seg)

    st.divider()
    st.subheader("📥 生成 Zwift .ZWO 文件")
    import os as _os, io as _io, zipfile as _zipfile
    DEPLOY_MODE = os.environ.get("TRUECADENCE_DEPLOY_MODE", "local").lower()
    all_zwo = []
    for week in all_weeks:
        for item in week['rows']:
            z = zwo_for_item(week['wk'], item)
            if z: all_zwo.append((week['wk'], item['day'], item['name'], z[0], z[1]))

    if DEPLOY_MODE == "server":
        zip_buf = _io.BytesIO()
        with _zipfile.ZipFile(zip_buf, "w", compression=_zipfile.ZIP_DEFLATED) as zf:
            for wk, day, name, fname, xml in all_zwo:
                zf.writestr(fname, xml)
        st.download_button(
            f"📦 下载 {len(all_zwo)} 个 ZWO 训练文件 ZIP",
            data=zip_buf.getvalue(),
            file_name="TrueCadence_ZWO_Workouts.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True,
            key="zwo_zip_download_server_v1",
        )
        st.caption("服务器内测版：ZWO 会打包成 ZIP 下载；解压后复制到 Zwift Workouts 文件夹。")
    else:
        zwift_dir = _os.path.expanduser("~/Documents/Zwift/Workouts/TrueCadence")
        _os.makedirs(zwift_dir, exist_ok=True)
        col_export, col_path = st.columns([1,2])
        with col_export:
            if st.button(f"📥 一键生成 {len(all_zwo)} 个 ZWO", type="primary", key="zwo_export_all_v2"):
                for wk, day, name, fname, xml in all_zwo:
                    with open(_os.path.join(zwift_dir, fname), "w", encoding="utf-8") as f: f.write(xml)
                st.success(f"已生成 {len(all_zwo)} 个 .zwo 文件")
                if hasattr(_os, "startfile"):
                    _os.startfile(zwift_dir)
        with col_path:
            st.caption(f"文件会直接写入：`{zwift_dir}`")
            st.caption("页面显示的课表和生成的 ZWO 使用同一份数据；不会再出现显示和导出不一致。")
    with st.expander("查看将生成的 ZWO 文件", expanded=False):
        for wk, day, name, fname, _xml in all_zwo:
            st.caption(f"Week {wk}｜{day}｜{name} → {fname}")

    st.divider()
    st.caption("补给方案 →「🍝 营养与补给」| 恢复 →「🛌 恢复与睡眠」| 每 4 周更新 FTP")
elif page == "🛌 恢复与睡眠":
    require_plan(2, "🛌 恢复与睡眠")
    st.title("🛌 恢复与睡眠")
    st.caption("把训练负荷和主观反馈合在一起，判断今天该正常训练、降强度、恢复骑，还是完全休息。")

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
    <div class="recovery-title">今天不是问“能不能练”，而是问“练多重才值得”</div>
    <div class="recovery-text">系统会综合 TSB/训练负荷、最近训练反馈、睡眠、腿疲劳、RPE、感冒发烧和疼痛记录，给出当天训练建议。</div>
</div>
""", unsafe_allow_html=True)

    uploaded_rides = st.session_state.get('uploaded_rides', [])
    historical = load_historical()
    use_all = st.toggle("合并全历史数据", value=False if uploaded_rides else True, key="recovery_use_all")
    source_label = "合并历史数据" if use_all else ("仅本次上传" if uploaded_rides else "历史数据")
    rides = merge_rides(historical, uploaded_rides) if use_all else (uploaded_rides or historical)
    rides.sort(key=lambda x: x.get('date', ''))
    rides = enrich_rides(rides)
    st.caption(data_scope_caption(rides, historical, uploaded_rides, source_label))

    feedback = load_feedback()
    sleep_records = load_wearable_sleep()
    feedback_summary = summarize_recent_feedback(feedback)
    recent_feedback = []
    today = pd.Timestamp.today().normalize()
    for item in feedback:
        d = pd.to_datetime(item.get("date"), errors="coerce")
        if pd.notna(d) and (today - d.normalize()).days <= 14:
            recent_feedback.append(item)
    if not recent_feedback:
        recent_feedback = sorted(feedback, key=lambda x: x.get("date", ""), reverse=True)[:5]

    def avg_fb(key):
        vals = [x.get(key) for x in recent_feedback if isinstance(x.get(key), (int, float))]
        return round(sum(vals) / len(vals), 1) if vals else 0

    profile = load_profile()
    pweight = profile.get('weight', 69)
    ftp = get_effective_ftp(rides) if rides else (profile.get('ftp_test') or 0)

    if rides:
        df = pd.DataFrame(rides).sort_values('date')
        df['date_dt'] = pd.to_datetime(df['date'], errors='coerce')
        pmc_recovery = compute_daily_pmc(rides)
        ctl = int(pmc_recovery.iloc[-1]['ctl']) if not pmc_recovery.empty else 0
        atl = int(pmc_recovery.iloc[-1]['atl']) if not pmc_recovery.empty else 0
        tsb = int(pmc_recovery.iloc[-1]['tsb']) if not pmc_recovery.empty else 0
        latest_date_recovery = pmc_recovery['date_dt'].max() if not pmc_recovery.empty else df['date_dt'].max()
        recent14 = df[df['date_dt'] >= latest_date_recovery - pd.Timedelta(days=13)] if pd.notna(latest_date_recovery) else df.tail(14)
        recent_h = sum(r.get('dur', 0) for r in recent14.to_dict('records')) / 60
        weekly_h = round(recent_h / 2, 1)
    else:
        ctl = atl = tsb = 0
        weekly_h = 0

    avg_sleep = avg_fb('sleep_quality')
    avg_energy = avg_fb('energy')
    avg_fatigue = avg_fb('leg_fatigue')
    avg_stress = avg_fb('stress')
    avg_rpe = avg_fb('rpe')

    recent_sleep_records = []
    for item in sleep_records:
        d = pd.to_datetime(item.get("date"), errors="coerce")
        if pd.notna(d) and (today - d.normalize()).days <= 14:
            recent_sleep_records.append(item)
    if not recent_sleep_records:
        recent_sleep_records = sorted(sleep_records, key=lambda x: x.get("date", ""), reverse=True)[:5]

    def avg_sleep_metric(key):
        vals = [x.get(key) for x in recent_sleep_records if isinstance(x.get(key), (int, float)) and x.get(key) > 0]
        return round(sum(vals) / len(vals), 1) if vals else 0

    watch_sleep_hours = avg_sleep_metric("sleep_hours")
    watch_sleep_score = avg_sleep_metric("sleep_score")
    watch_hrv = avg_sleep_metric("hrv")
    watch_rest_hr = avg_sleep_metric("rest_hr")
    watch_stress = avg_sleep_metric("stress_score")
    nap_records = [x for x in recent_sleep_records if x.get("nap_minutes", 0)]
    avg_nap_min = round(sum(float(x.get("nap_minutes", 0) or 0) for x in nap_records) / len(nap_records), 1) if nap_records else 0
    nap_refresh_count = sum(1 for x in nap_records if x.get("nap_after") == "更清醒")
    nap_sluggish_count = sum(1 for x in nap_records if x.get("nap_after") == "更困")
    nap_good_count = sum(1 for x in nap_records if (x.get("nap_quality", 0) or 0) >= 4)

    pain_counts, special_counts, cycle_counts = {}, {}, {}
    for item in recent_feedback:
        for pain in item.get('pains', []) or []:
            pain_counts[pain] = pain_counts.get(pain, 0) + 1
        for special in item.get('specials', []) or []:
            special_counts[special] = special_counts.get(special, 0) + 1
        cycle_status = infer_cycle_status_for_date(item, profile)
        if cycle_status:
            cycle_counts[cycle_status] = cycle_counts.get(cycle_status, 0) + 1

    red_flags = []
    caution_flags = []
    if any(k in special_counts for k in ["发烧"]):
        red_flags.append("近期记录过发烧")
    if any(k in cycle_counts for k in ["经期第1-2天"]):
        latest_cycle = next((x for x in recent_feedback if infer_cycle_status_for_date(x, profile) == '经期第1-2天'), {})
        if latest_cycle.get('cycle_pain') in ['中', '重'] or latest_cycle.get('cycle_training_impact') == '明显':
            red_flags.append("经期前段且身体反应明显")
        else:
            caution_flags.append("经期前段，建议降低训练强度")
    if any(k in cycle_counts for k in ["经前期/PMS"]):
        caution_flags.append("经前期/PMS，注意睡眠、情绪和腿感波动")
    if any(k in special_counts for k in ["感冒"]):
        caution_flags.append("近期感冒/身体不适")
    if avg_sleep and avg_sleep <= 2:
        red_flags.append("睡眠质量很差")
    elif avg_sleep and avg_sleep <= 3:
        caution_flags.append("睡眠质量一般")
    if watch_sleep_hours and watch_sleep_hours < 5.5:
        red_flags.append(f"手表睡眠 {watch_sleep_hours}h，明显不足")
    elif watch_sleep_hours and watch_sleep_hours < 6.5:
        caution_flags.append(f"手表睡眠 {watch_sleep_hours}h，偏少")
    if watch_sleep_score and watch_sleep_score < 55:
        red_flags.append(f"睡眠评分 {watch_sleep_score}，恢复很差")
    elif watch_sleep_score and watch_sleep_score < 70:
        caution_flags.append(f"睡眠评分 {watch_sleep_score}，恢复一般")
    if watch_stress and watch_stress >= 70:
        caution_flags.append(f"手表压力 {watch_stress}，自主神经压力偏高")
    if nap_records:
        if nap_sluggish_count:
            caution_flags.append("午睡后仍昏沉，下午高强度需谨慎")
        elif nap_refresh_count and 15 <= avg_nap_min <= 45 and nap_good_count:
            caution_flags.append("午睡对下午训练有小幅恢复加成，但不等同于夜间睡眠")
        elif avg_nap_min > 90:
            caution_flags.append("午睡时间较长，注意睡眠惯性和夜间睡眠节律")
    if avg_fatigue and avg_fatigue >= 5:
        red_flags.append("腿部疲劳很高")
    elif avg_fatigue and avg_fatigue >= 4:
        caution_flags.append("腿部疲劳偏高")
    if avg_rpe and avg_rpe >= 8:
        caution_flags.append("最近训练主观强度偏高")
    if avg_stress and avg_stress >= 4:
        caution_flags.append("生活/工作压力偏高")
    for pain, n in pain_counts.items():
        if n >= 2:
            caution_flags.append(f"{pain} 不适重复出现")
    if tsb < -20:
        red_flags.append(f"TSB {tsb}，深度疲劳")
    elif tsb < -10:
        caution_flags.append(f"TSB {tsb}，疲劳偏高")
    if weekly_h > 12:
        caution_flags.append(f"近两周周均 {weekly_h}h，训练量偏高")

    if red_flags:
        advice_class = "recovery-red"
        advice_tag = "RED FLAG"
        advice_main = "今天建议完全休息，或只做非常轻松恢复活动"
        next_action = ["取消 VO2max、阈值、冲刺和大扭矩爬坡。", "优先睡眠、补水、正常进食；发烧/明显感染时不要训练。", "如果疼痛或症状持续，先处理身体问题，不要硬顶课表。"]
    elif caution_flags:
        advice_class = "recovery-yellow"
        advice_tag = "CAUTION"
        advice_main = "今天建议降强度：Z1-Z2 恢复骑或缩短训练"
        next_action = [f"恢复骑 30-60 分钟，功率控制在 <{round(ftp*0.55) if ftp else 90}W。", "如果必须训练，把质量课改成短 Z2，不做力竭间歇。", "今晚优先睡眠，明天根据腿感和精神再决定是否恢复强度。"]
    elif tsb > 10 and avg_energy and avg_energy >= 4:
        advice_class = "recovery-blue"
        advice_tag = "READY"
        advice_main = "状态较好，可以安排关键训练或测试"
        next_action = ["适合做阈值、VO2max、FTP测试或比赛模拟。", "热身要充分，训练后及时补碳水和蛋白。", "不要因为状态好连续多天堆高强度。"]
    else:
        advice_class = "recovery-green"
        advice_tag = "NORMAL"
        advice_main = "今天可以正常训练，但保持计划内强度"
        next_action = ["按原计划训练，不额外加码。", "强度课后记录 RPE、腿感、睡眠和疼痛。", "如果热身中感觉异常疲劳，主动降为 Z2。"]

    reasons = red_flags + caution_flags
    if not reasons:
        reasons = ["训练负荷和主观反馈没有明显红旗"]

    st.markdown(f"""
<div class="recovery-advice {advice_class}">
    <div class="tag">{advice_tag}</div>
    <div class="main">{advice_main}</div>
    <div class="why"><b>主要依据：</b>{'；'.join(reasons[:6])}</div>
</div>
<div class="recovery-grid">
    <div class="recovery-card"><div class="k">TSB 状态</div><div class="v">{tsb}</div><div class="d">CTL {ctl} / ATL {atl}</div></div>
    <div class="recovery-card"><div class="k">近两周周均</div><div class="v">{weekly_h}h</div><div class="d">来自 FIT 训练记录</div></div>
    <div class="recovery-card"><div class="k">训练反馈</div><div class="v">{feedback_summary.get('count', 0)} 条</div><div class="d">最近主观状态</div></div>
    <div class="recovery-card"><div class="k">手表睡眠</div><div class="v">{watch_sleep_hours or '-'}h</div><div class="d">评分 {watch_sleep_score or '-'} / HRV {watch_hrv or '-'}</div></div>
    <div class="recovery-card"><div class="k">午睡修正</div><div class="v">{str(avg_nap_min) + 'min' if avg_nap_min else '-'}</div><div class="d">更清醒 {nap_refresh_count} 次 / 更困 {nap_sluggish_count} 次</div></div>
</div>
""", unsafe_allow_html=True)

    c1, c2 = st.columns([1.1, 1])
    with c1:
        st.subheader("今天怎么做")
        for item in next_action:
            st.markdown(f"- {item}")
        if ftp:
            z1 = round(ftp * 0.55)
            z2_hi = round(ftp * 0.75)
            st.info(f"恢复/有氧参考：Z1 < **{z1}W**；Z2 约 **{z1}-{z2_hi}W**。")
        if nap_records:
            st.caption("午睡说明：午睡只作为当日训练准备度修正，不直接等同于夜间睡眠。15-45 分钟且醒后更清醒，通常对下午训练有帮助；>90 分钟或醒后更困，则要注意睡眠惯性。")
        st.subheader("恢复优先级")
        st.markdown(f"""
1. **睡眠**：目标 7.5-9 小时；睡眠差时训练收益会明显下降。  
2. **补水和碳水**：长距离/强度课后先补碳水，再补蛋白。  
3. **低强度活动**：疲劳高时，30-45 分钟 Z1 比硬上间歇更有价值。  
4. **疼痛处理**：重复疼痛优先查训练量、锁片/座垫/把位，不要只靠忍。
""")
    with c2:
        st.subheader("最近反馈摘要")
        for line in feedback_summary.get('lines', []):
            st.markdown(f"- {line}")
        if pain_counts:
            pain_txt = "、".join(f"{k}×{v}" for k, v in sorted(pain_counts.items(), key=lambda kv: kv[1], reverse=True))
            st.warning(f"不适记录：{pain_txt}")
        if special_counts:
            special_txt = "、".join(f"{k}×{v}" for k, v in sorted(special_counts.items(), key=lambda kv: kv[1], reverse=True))
            st.warning(f"特殊情况：{special_txt}")
        if cycle_counts:
            cycle_txt = "、".join(f"{k}×{v}" for k, v in sorted(cycle_counts.items(), key=lambda kv: kv[1], reverse=True))
            st.info(f"女性周期：{cycle_txt}")
        if not feedback:
            st.info("还没有训练反馈。去「📝 训练反馈」记录一次，恢复判断会更准。")

    st.divider()
    st.subheader("⌚ 手表睡眠数据")
    st.caption("先用手动录入打通字段；后续佳明/Apple/华为/COROS 的截图 OCR、CSV 或 API 都落到这套数据里。")

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
        st.markdown("**午睡 / 小睡（可选）**")
        nc1, nc2, nc3, nc4 = st.columns(4)
        with nc1:
            nap_minutes = st.number_input("午睡时长 min", 0, 180, int(latest_sleep.get("nap_minutes", 0) or 0), 5, key="wear_nap_minutes")
        with nc2:
            nap_quality = st.slider("午睡质量", 1, 5, int(latest_sleep.get("nap_quality", 3) or 3), key="wear_nap_quality", help="1=很差，5=很好；0分钟午睡时可忽略")
        with nc3:
            nap_after = st.selectbox("醒后状态", ["未午睡", "更困", "无变化", "更清醒"], index=["未午睡", "更困", "无变化", "更清醒"].index(latest_sleep.get("nap_after", "未午睡") if latest_sleep.get("nap_after", "未午睡") in ["未午睡", "更困", "无变化", "更清醒"] else "未午睡"), key="wear_nap_after")
        with nc4:
            nap_to_training = st.selectbox("到训练间隔", ["不训练/未知", "<30分钟", "30-90分钟", ">90分钟"], index=["不训练/未知", "<30分钟", "30-90分钟", ">90分钟"].index(latest_sleep.get("nap_to_training", "不训练/未知") if latest_sleep.get("nap_to_training", "不训练/未知") in ["不训练/未知", "<30分钟", "30-90分钟", ">90分钟"] else "不训练/未知"), key="wear_nap_to_training")
        sleep_note = st.text_input("备注", value=str(latest_sleep.get("note", "") or ""), placeholder="例如：夜醒多、午睡后清醒、饮酒、晚训、出差、戴表不准等", key="wear_sleep_note")
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
        st.info("还没有手表睡眠记录。先手动录入 1 条，后面可以升级为截图识别或官方 API 自动同步。")

    st.divider()
    st.subheader("数据依据")
    st.caption(f"FIT 记录 {len(rides)} 条；训练反馈 {len(feedback)} 条；睡眠/午睡记录 {len(sleep_records)} 条。午睡只作为当日准备度修正，不直接等同夜间睡眠；CTL/ATL/TSB 基于 TSS 指数加权估算，不替代医学诊断。")
    col1, col2, col3 = st.columns(3)
    col1.metric("体能 CTL", ctl, "长期积累" if ctl < 40 else "中等" if ctl < 70 else "高")
    col2.metric("疲劳 ATL", atl, "轻" if atl < 40 else "适中" if atl < 65 else "高")
    col3.metric("状态 TSB", tsb, "好" if tsb > 10 else "正常" if tsb > -10 else "疲劳")

elif page == "🍝 营养与补给":
    require_plan(2, "🍝 营养与补给")
    st.title("🍝 营养与补给")
    st.caption("不是泛泛说多吃碳水，而是按今天的训练、体重、强度和反馈，算出怎么吃、怎么喝、怎么补。")

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
    <div class="nutrition-title">补给不是吃得越多越好，而是刚好支持今天的输出</div>
    <div class="nutrition-text">系统会根据体重、训练时长、强度、天气和训练反馈，给出每小时碳水、水、钠，以及训练前/中/后的执行建议。</div>
</div>
""", unsafe_allow_html=True)

    uploaded_rides = st.session_state.get('uploaded_rides', [])
    historical = load_historical()
    use_all = st.toggle("合并全历史数据", value=False if uploaded_rides else True, key="nutrition_use_all")
    source_label = "合并历史数据" if use_all else ("仅本次上传" if uploaded_rides else "历史数据")
    rides = merge_rides(historical, uploaded_rides) if use_all else (uploaded_rides or historical)
    rides.sort(key=lambda x: x.get('date', ''))
    rides = enrich_rides(rides) if rides else []
    st.caption(data_scope_caption(rides, historical, uploaded_rides, source_label))

    profile = load_profile()
    ftp = get_effective_ftp(rides) if rides else (profile.get('ftp_test') or 0)
    pweight = profile.get('weight', 69)
    feedback = load_feedback()
    feedback_summary = summarize_recent_feedback(feedback)
    recent_feedback = sorted(feedback, key=lambda x: (x.get('date', ''), x.get('created_at', '')), reverse=True)[:5]

    special_set = set()
    fueling_set = set()
    for item in recent_feedback:
        for s_item in item.get('specials', []) or []:
            special_set.add(s_item)
        if item.get('fueling') and item.get('fueling') != '正常':
            fueling_set.add(item.get('fueling'))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        weight = st.number_input("体重 kg", min_value=40, max_value=120, value=int(pweight or 69), key="nut_weight_v2")
    with c2:
        ride_hours = st.slider("今天骑多久 h", 0.5, 6.0, 2.0, 0.5, key="nut_ride_hours")
    with c3:
        workout_type = st.selectbox("训练类型", ["恢复骑", "Z2 长距离", "甜区/阈值", "VO2max/间歇", "比赛/绕圈赛"], key="nut_workout_type")
    with c4:
        environment = st.selectbox("环境", ["正常", "天气太热", "天气太冷", "室内骑行"], index=1 if "天气太热" in special_set else 0, key="nut_environment")

    if workout_type == "恢复骑":
        carb_lo, carb_hi = 0, 20
        water_lo, water_hi = 400, 600
        sodium_lo, sodium_hi = 0, 300
        intensity_note = "恢复骑主要目标是促进血液循环，不需要强行补很多糖。"
    elif workout_type == "Z2 长距离":
        carb_lo, carb_hi = (30, 50) if ride_hours <= 2 else (50, 70)
        water_lo, water_hi = 500, 750
        sodium_lo, sodium_hi = 300, 600
        intensity_note = "Z2 长距离要从前 20 分钟就开始少量多次补，不要等饿了再吃。"
    elif workout_type == "甜区/阈值":
        carb_lo, carb_hi = 60, 80
        water_lo, water_hi = 600, 850
        sodium_lo, sodium_hi = 500, 800
        intensity_note = "甜区/阈值会明显消耗糖原，训练前和训练中都要有碳水支持。"
    elif workout_type == "VO2max/间歇":
        carb_lo, carb_hi = 50, 70
        water_lo, water_hi = 600, 850
        sodium_lo, sodium_hi = 500, 800
        intensity_note = "VO2max 更怕胃里太撑，训练前吃够，训练中小口补。"
    else:
        carb_lo, carb_hi = 80, 100
        water_lo, water_hi = 750, 1000
        sodium_lo, sodium_hi = 700, 1000
        intensity_note = "比赛日目标是稳定供能，不要尝试没测试过的新补给。"

    if environment in ["天气太热", "室内骑行"]:
        water_lo += 150; water_hi += 250
        sodium_lo += 200; sodium_hi += 300
    if "低血糖感" in fueling_set or "吃少了" in fueling_set:
        carb_lo += 10; carb_hi += 10
    if "胃不舒服" in fueling_set:
        carb_hi = min(carb_hi, 70)

    total_carb_lo = round(carb_lo * ride_hours)
    total_carb_hi = round(carb_hi * ride_hours)
    total_water_lo = round(water_lo * ride_hours)
    total_water_hi = round(water_hi * ride_hours)
    total_sodium_lo = round(sodium_lo * ride_hours)
    total_sodium_hi = round(sodium_hi * ride_hours)

    st.markdown(f"""
<div class="nutrition-advice">
    <div class="tag">TODAY FUELING TARGET</div>
    <div class="main">每小时 {carb_lo}-{carb_hi}g 碳水 · {water_lo}-{water_hi}ml 水 · {sodium_lo}-{sodium_hi}mg 钠</div>
    <div class="why"><b>依据：</b>{workout_type}｜{ride_hours}h｜{environment}｜体重 {weight}kg。{intensity_note}</div>
</div>
<div class="nutrition-grid">
    <div class="nutrition-card"><div class="k">本次总碳水</div><div class="v">{total_carb_lo}-{total_carb_hi}g</div><div class="d">约 {max(0, round(total_carb_lo/25))}-{max(1, round(total_carb_hi/25))} 根能量胶</div></div>
    <div class="nutrition-card"><div class="k">本次总饮水</div><div class="v">{total_water_lo}-{total_water_hi}ml</div><div class="d">分 15-20 分钟小口喝</div></div>
    <div class="nutrition-card"><div class="k">本次总钠</div><div class="v">{total_sodium_lo}-{total_sodium_hi}mg</div><div class="d">热天/室内优先补足</div></div>
    <div class="nutrition-card"><div class="k">反馈接入</div><div class="v">{feedback_summary.get('count', 0)} 条</div><div class="d">低血糖/胃不适/高温会修正建议</div></div>
</div>
""", unsafe_allow_html=True)

    st.subheader("训练前 / 训练中 / 训练后")
    pre_carb = round(weight * (1.5 if ride_hours <= 2 else 2.0))
    pre_protein = round(weight * 0.3)
    post_carb = round(weight * (0.8 if workout_type == "恢复骑" else 1.2))
    post_protein = round(weight * 0.35)
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown(f"""
**训练前 2-3 小时**
- 碳水：**{pre_carb}g**
- 蛋白：**{pre_protein}g**
- 低脂、低纤维，别吃太撑
""")
    with col_b:
        st.markdown(f"""
**训练中**
- 每 15-20 分钟吃/喝一次
- 不要等饿了再补
- >60g/h 建议葡萄糖+果糖组合
""")
    with col_c:
        st.markdown(f"""
**训练后 30 分钟内**
- 碳水：**{post_carb}g**
- 蛋白：**{post_protein}g**
- 强度课后优先补碳水
""")

    st.subheader("按训练类型快速参考")
    rows = [
        ["恢复骑", "0-20g/h", "400-600ml/h", "0-300mg/h", "不饿不硬吃，重点恢复"],
        ["Z2 长距离", "50-70g/h", "500-750ml/h", "300-600mg/h", "从前 20 分钟开始补"],
        ["甜区/阈值", "60-80g/h", "600-850ml/h", "500-800mg/h", "训练前必须吃够"],
        ["VO2max/间歇", "50-70g/h", "600-850ml/h", "500-800mg/h", "别让胃太撑，小口补"],
        ["比赛/绕圈赛", "80-100g/h", "750-1000ml/h", "700-1000mg/h", "只用训练中测试过的补给"],
    ]
    st.dataframe(pd.DataFrame(rows, columns=["训练类型", "碳水", "水", "钠", "重点"]).astype(str), use_container_width=True, hide_index=True)

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
        def sup_score(sup):
            sc = 0
            if sup["carbs_g"] >= 40: sc += 1
            if environment in ["天气太热", "室内骑行"] and sup["electrolytes_mg"] >= 200: sc += 2
            if "胃不舒服" in fueling_set and sup["type"] == "软糖": sc += 2
            if workout_type in ["比赛/绕圈赛", "VO2max/间歇"] and sup.get("caffeine"): sc += 1
            if workout_type == "恢复骑" and sup.get("caffeine"): sc -= 1
            if workout_type == "比赛/绕圈赛" and "电解质" in sup.get("tags", []): sc += 1
            if environment in ["天气太热", "室内骑行"] and sup.get("electrolytes_mg", 0) < 100: sc -= 1
            return sc

        ranked = sorted(supplements, key=sup_score, reverse=True)
        top = ranked[:3]

        sup_cols = st.columns(len(top))
        for i, sup in enumerate(top):
            with sup_cols[i]:
                servings_needed = max(1, round(carb_hi / sup["carbs_g"], 1)) if sup["carbs_g"] else 0
                badge = "⭐ 首选" if i == 0 else ("👍 备选" if i == 1 else "💡 调剂")
                tags_text = " · ".join(sup.get("tags", [])[:3])
                score = sup_score(sup)
                card_tone = "normal"
                reason_parts = []
                if environment in ["天气太热", "室内骑行"] and sup.get("electrolytes_mg", 0) >= 200:
                    card_tone = "heat"
                    reason_parts.append("高温/室内：补钠优先")
                if "胃不舒服" in fueling_set and sup.get("type") == "软糖":
                    card_tone = "gut"
                    reason_parts.append("胃不适：软糖更温和")
                if workout_type in ["比赛/绕圈赛", "VO2max/间歇"] and sup.get("caffeine"):
                    card_tone = "caffeine"
                    reason_parts.append("高强度：咖啡因加成")
                if workout_type == "恢复骑" and sup.get("caffeine"):
                    card_tone = "caution"
                    reason_parts.append("恢复骑：咖啡因谨慎")
                if i == 0 and card_tone == "normal":
                    card_tone = "primary"
                    reason_parts.append("当前最匹配")

                tone_styles = {
                    "primary": ("rgba(255,107,53,0.72)", "rgba(255,107,53,0.15)", "rgba(255,107,53,0.20)", "#ff9a68"),
                    "heat": ("rgba(88,166,255,0.72)", "rgba(88,166,255,0.13)", "rgba(88,166,255,0.20)", "#79c0ff"),
                    "gut": ("rgba(35,134,54,0.72)", "rgba(35,134,54,0.13)", "rgba(35,134,54,0.20)", "#7ee787"),
                    "caffeine": ("rgba(210,168,255,0.72)", "rgba(210,168,255,0.13)", "rgba(210,168,255,0.20)", "#d2a8ff"),
                    "caution": ("rgba(240,192,64,0.72)", "rgba(240,192,64,0.12)", "rgba(240,192,64,0.20)", "#f0c040"),
                    "normal": ("rgba(139,148,158,0.42)", "rgba(48,54,61,0.32)", "rgba(48,54,61,0.26)", "var(--tc-subtle)"),
                }
                border_color, bg_glow, shadow_glow, accent_color = tone_styles[card_tone]
                reason_text = " · ".join(reason_parts) if reason_parts else f"匹配分 {score}"
                st.markdown(f"""<div style="background:linear-gradient(135deg, {bg_glow}, var(--tc-surface) 72%); border:1.5px solid {border_color}; box-shadow:0 0 0 1px {shadow_glow}, 0 10px 26px rgba(0,0,0,0.16); border-radius:13px; padding:0.85em; margin:0.3em 0;">
<div style="color:{accent_color}; font-size:0.72em; font-weight:780; letter-spacing:0.08em; margin-bottom:0.3em;">{badge}</div>
<div style="color:#f0f6fc; font-size:1.02em; font-weight:760;">{sup['name']}</div>
<div style="color:var(--tc-subtle); font-size:0.76em; margin-top:0.15em;">{sup['type']} · {sup['flavor']} · {sup['serving_g']}g/份</div>
<div style="color:#aab6c3; font-size:0.82em; margin-top:0.5em; line-height:1.5;">碳水 <b>{sup['carbs_g']}g</b> · 钠 <b>{sup['sodium_mg']}mg</b> · {sup['kcal']}kcal</div>
<div style="color:#6e7681; font-size:0.74em; margin-top:0.35em;">{tags_text}</div>
<div style="color:{accent_color}; font-size:0.72em; margin-top:0.42em;">{reason_text}</div>
<div style="color:var(--tc-subtle); font-size:0.74em; margin-top:0.5em; border-top:1px solid var(--tc-surface-2); padding-top:0.4em;">约需 <b>{servings_needed}</b> 份/小时</div>
</div>""", unsafe_allow_html=True)

        if environment in ["天气太热", "室内骑行"] and "胃不舒服" in fueling_set:
            st.info("高温+胃不适：优先碳水软糖做碳水主力，搭配电解质胶少量多次补盐。赛前 30min 不要吃太多胶。")
        elif environment in ["天气太热", "室内骑行"]:
            st.info("高温环境：推荐以电解质胶为主，碳水软糖作为口味调剂。不要只靠碳水密度高的产品而忽略钠。")
        elif "胃不舒服" in fueling_set:
            st.info("胃不适记录：优先碳水软糖→果胶基质更温和；能量胶分小口摄入，不要一次吃完一根。")
        elif workout_type == "比赛/绕圈赛":
            st.info("比赛日：赛前可用咖啡胶，赛中主力用电解质胶。不要用训练中没测试过的产品。")
    else:
        st.caption("补剂产品库未加载，请确认 supplement_db.json 存在。")

    st.subheader("根据最近反馈的修正")
    if fueling_set or special_set:
        if "低血糖感" in fueling_set or "吃少了" in fueling_set:
            st.warning("你最近记录过低血糖感/吃少了：下次训练前 2-3 小时必须吃正餐，训练中碳水提前到前 15-20 分钟开始。")
        if "胃不舒服" in fueling_set:
            st.warning("你最近记录过胃不舒服：不要一下冲到 90g/h，先从 40-60g/h 做肠胃训练，并分小口摄入。")
        if "喝少了" in fueling_set:
            st.warning("你最近记录过喝少了：把水壶按时间喝，不要只凭口渴。")
        if "天气太热" in special_set:
            st.warning("近期有高温记录：饮水和钠已上调；热天强度课更容易心率漂移。")
        if "睡眠不足" in special_set or "工作压力大" in special_set:
            st.info("近期睡眠/压力不理想：不要用咖啡因硬顶长期疲劳，优先保证晚间恢复。")
    else:
        st.info("最近反馈没有明显补给风险。建议关键训练后继续记录：吃少了、胃不舒服、低血糖感、喝少了。")

    st.caption(f"数据依据：体重 {weight}kg；FTP {ftp or '-'}W；训练反馈 {len(feedback)} 条。补给建议用于训练辅助，不替代医学或营养师建议。")

elif page == "🎯 目标追踪":
    require_plan(2, "🎯 目标追踪")
    st.title("🎯 目标追踪")
    st.caption("把目标拆成路径、阶段和本周动作：不是许愿，而是知道下一步怎么走。")

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

    uploaded_rides = st.session_state.get('uploaded_rides', [])
    historical = load_historical()
    use_all = st.toggle("合并全历史数据", value=False if uploaded_rides else True, key="goal_use_all", help="开启=上传文件+历史数据一起分析；关闭=只看上传的文件")
    source_label = "合并历史数据" if use_all else ("仅本次上传" if uploaded_rides else "历史数据")
    rides = merge_rides(historical, uploaded_rides) if use_all else (uploaded_rides or historical)
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
        weekly_gain = 6.0; capacity = "高投入，但恢复要求高"

    if current_wkg >= 4.0:
        weekly_gain = max(1.0, weekly_gain - 2.5)
        capacity += "｜高阶涨功更慢"
    if goal_type == "恢复体能":
        weekly_gain = max(weekly_gain, 3.0)
    if goal_type == "减脂不掉功率":
        weekly_gain = max(1.0, weekly_gain - 1.5)

    needed_weeks = max(1, math.ceil(max(0, ftp_gap) / weekly_gain)) if ftp_gap > 0 else 1
    feasible = needed_weeks <= target_weeks_n
    risk_flags = []
    if weekly_h < 5 and ftp_gap > 25:
        risk_flags.append("每周训练时间偏少，目标涨幅较大")
    if tsb < -15:
        risk_flags.append("当前 TSB 偏低，疲劳较高")
    if avg_fatigue and avg_fatigue >= 4:
        risk_flags.append("最近腿疲劳偏高")
    if avg_sleep and avg_sleep <= 2.5:
        risk_flags.append("最近睡眠偏差")
    if goal_type == "减脂不掉功率" and weekly_h >= 10:
        risk_flags.append("减脂期训练量较高，注意能量可用性不足")

    if feasible and not risk_flags:
        verdict = "目标合理，可以推进"
        verdict_text = "以当前训练时间和状态，目标具备可执行性。关键是稳定执行，不要每周都临时改方向。"
    elif feasible and risk_flags:
        verdict = "目标可行，但要管理风险"
        verdict_text = "时间上够，但恢复、睡眠或疲劳会影响完成质量。目标不是问题，节奏管理是关键。"
    else:
        verdict = "目标偏激进，建议拆成两段"
        verdict_text = f"按当前投入估算约需 {needed_weeks} 周，而你设定的是 {target_weeks_n} 周。建议先设中间目标，再冲最终目标。"

    st.markdown(f"""
<div class="goal-hero">
    <div class="goal-tag">GOAL VERDICT</div>
    <div class="goal-main">{verdict}</div>
    <div class="goal-why">{verdict_text}</div>
</div>
<div class="goal-grid">
    <div class="goal-card"><div class="k">当前 FTP</div><div class="v">{ftp}W</div><div class="d">{current_wkg} W/kg</div></div>
    <div class="goal-card"><div class="k">目标</div><div class="v">{target_ftp}W</div><div class="d">{target_wkg} W/kg｜差 {ftp_gap:+}W</div></div>
    <div class="goal-card"><div class="k">预计需要</div><div class="v">{needed_weeks}周</div><div class="d">设定周期 {target_weeks_n}周</div></div>
    <div class="goal-card"><div class="k">训练承载</div><div class="v">{weekly_h}h/周</div><div class="d">{capacity}</div></div>
</div>
<div class="goal-grid">
    <div class="goal-card"><div class="k">体能 CTL</div><div class="v">{ctl}</div><div class="d">长期训练积累</div></div>
    <div class="goal-card"><div class="k">状态 TSB</div><div class="v">{tsb}</div><div class="d">当前新鲜度</div></div>
    <div class="goal-card"><div class="k">反馈接入</div><div class="v">{len(recent_feedback)} 条</div><div class="d">睡眠 {avg_sleep or '-'} / 腿疲劳 {avg_fatigue or '-'}</div></div>
    <div class="goal-card"><div class="k">目标日期</div><div class="v">{event_date}</div><div class="d">用于阶段倒推</div></div>
</div>
""", unsafe_allow_html=True)

    progress = min(max(ftp / target_ftp, 0), 1) if target_ftp else 0
    st.progress(progress, f"当前进度：{round(progress*100)}%｜还差 {max(0, ftp_gap)}W / {max(0, wkg_gap)} W/kg")

    st.subheader("阶段路径")
    phase_rows = []
    phase_count = max(1, target_weeks_n // 4)
    for i in range(1, phase_count + 1):
        wk = i * 4
        phase_target = min(target_ftp, round(ftp + weekly_gain * wk)) if ftp_gap > 0 else ftp
        if i == 1:
            focus = "建立节奏：Z2 连续性 + 1 次轻强度"
            risk = "别一开始就堆 VO2"
        elif i == phase_count:
            focus = "专项收束：接近目标强度，减少无效疲劳"
            risk = "避免最后阶段练过头"
        else:
            focus = "主要提升：阈值/甜区 + 长耐力"
            risk = "每周保留恢复窗口"
        if goal_type == "比赛备战":
            focus = "比赛专项：节奏变化、冲刺、补给演练"
        elif goal_type == "长距离耐力":
            focus = "长耐力：逐步拉长 Z2，练补给和姿势稳定"
        elif goal_type == "减脂不掉功率":
            focus = "控体重：Z2 稳定输出，强度课前后不缺碳水"
        phase_rows.append({"阶段": f"第 {max(1, wk-3)}-{wk} 周", "目标": f"FTP ~{phase_target}W / {round(phase_target/weight,1)} W/kg", "训练重点": focus, "风险提醒": risk})
    st.dataframe(pd.DataFrame(phase_rows).astype(str), use_container_width=True, hide_index=True)

    c_left, c_right = st.columns([1.05, 1])
    with c_left:
        st.subheader("本周动作")
        if weekly_h <= 4:
            actions = ["完成 3 次骑行，比单次骑很猛更重要", "全部以 Z2/轻松骑为主", "本周不要追 FTP 测试"]
        elif goal_type in ["提升 FTP", "提升 W/kg"]:
            actions = ["安排 1 次阈值/甜区质量课", "安排 1 次 2h 左右 Z2", "其余训练保持低强度，不要把恢复骑骑成强度课"]
        elif goal_type == "比赛备战":
            actions = ["安排 1 次比赛模拟或节奏变化训练", "至少 1 次补给演练", "保留 1-2 天恢复窗口"]
        elif goal_type == "长距离耐力":
            actions = ["最长单次比上周增加不超过 10-15%", "从前 20 分钟开始补给", "关注后半程功率是否明显掉"]
        elif goal_type == "减脂不掉功率":
            actions = ["不要在质量课前低碳", "用 Z2 增加能量消耗", "每周体重下降不宜过快"]
        else:
            actions = ["先恢复规律训练频率", "只做轻到中等强度", "连续 2 周稳定后再提高目标"]
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
            st.info(f"建议中间目标：先到 **{mid}W**，稳定 2-3 周后再冲 **{target_ftp}W**。")
        st.caption("目标估算不是承诺值。真正决定进度的是连续性、恢复、补给和训练执行质量。")

    st.subheader("什么时候重新评估")
    st.markdown("""
- **每 4 周**：重新看 FTP、CTL/ATL/TSB 和最近反馈。  
- **连续两周疲劳高或睡眠差**：目标不一定错，但推进速度要降。  
- **比赛前 7-10 天**：不再追训练量，改为保持状态和降低疲劳。  
- **疼痛重复出现**：先处理身体/装备/姿势，不要继续用训练计划硬压。
""")

st.sidebar.divider()
up_count = len(st.session_state.get('uploaded_rides', []))
hi_count = len(load_historical())
st.sidebar.caption(f"📤 本次上传: {up_count}条 | 📚 历史存档: {hi_count}条")
if st.sidebar.button("🧹 清除本次上传", help="只清除当前会话里的本次上传缓存，不删除历史存档", use_container_width=True):
    st.cache_data.clear()
    st.session_state.uploaded_rides = []
    st.rerun()

with st.sidebar.expander("⚠️ 清除历史上传", expanded=False):
    st.caption("危险操作：会删除当前骑手已保存的全部 FIT 解析历史，不影响账号和骑手档案。")
    confirm_clear_history = st.checkbox("我确认清除当前骑手历史存档", key="confirm_clear_ride_history")
    if st.button("删除历史存档", disabled=not confirm_clear_history, use_container_width=True):
        save_current_rides([])
        st.cache_data.clear()
        st.session_state.uploaded_rides = []
        st.success("已清除当前骑手历史上传记录")
        st.rerun()
st.sidebar.divider()
st.sidebar.caption("TrueCadence v1.0")
st.sidebar.caption(f"{datetime.date.today()}")


