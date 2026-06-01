# TrueCadence - 个人版
# 部署:streamlit run app.py

import streamlit as st
import pandas as pd
import plotly.io as pio
import json, os, sys, datetime, math, hashlib, secrets, time, importlib
from pathlib import Path
pio.templates.default = "plotly_dark"

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))
from auth import (
    load_users, save_users, register_user, login_user,
    add_rider, delete_rider, add_subscription_days, redeem_code, PLANS,
    load_orders, create_order, get_user_orders, confirm_order_paid, update_order_status, hide_order_for_user,
    gen_invite_code, redeem_invite, consume_invite,
    get_ai_usage, increment_ai_usage, get_ai_limit,
    load_rider_rides, load_rider_profile, save_rider_profile, save_rider_data,
    get_user_dir, get_rider_data_path, DATA_DIR,
)
from training_plan_rules import (
    HARD_KINDS as PLAN_HARD_KINDS,
    build_cadence_torque_state as rules_build_cadence_torque_state,
    build_event_context as rules_build_event_context,
    build_progression_state_v1 as rules_build_progression_state_v1,
    build_rider_state_v1 as rules_build_rider_state_v1,
    choose_mmp_training_focus as rules_choose_mmp_training_focus,
    build_week_plan as rules_build_week_plan,
    detect_phase as rules_detect_phase,
    phase_meta as rules_phase_meta,
    refined_readiness_cap as rules_refined_readiness_cap,
    rules_summary as training_rules_summary,
    tss_for_kind as rules_tss,
    validate_week_plan as rules_validate_week_plan,
    week_factor as rules_week_factor,
    zone_style as rules_zone_style,
)

from services.workout_export import (
    estimate_tss_from_blocks,
    workout_blocks_for_item,
    workout_exports_for_item,
)
from services.training_metrics import (
    compute_daily_pmc,
    enrich_rides,
    estimate_ftp,
    estimate_ftp_explain,
    hr_zones_by_lthr,
    hr_zones_by_max,
    tsb_zone_text,
)
from services.charts import (
    plot_pmc as plot_pmc_chart,
    plot_power_curve,
)
from services.feedback_store import (
    infer_cycle_status_for_date as feedback_infer_cycle_status_for_date,
    load_beta_feedback_from_file,
    load_feedback_for_rider,
    load_wearable_sleep_for_rider,
    save_beta_feedback_to_file,
    save_feedback_for_rider,
    save_wearable_sleep_for_rider,
    summarize_recent_feedback as feedback_summarize_recent_feedback,
)
from services.fit_processing import (
    NamedBytesFile,
    download_intervals_activity_fit,
    parse_fit_files,
    summarize_durability,
)
from services.power_exclusions import (
    apply_power_exclusions_to_rides,
    current_rider_power_exclusions_path as power_exclusions_path_for_context,
    render_power_exclusion_manager as render_power_exclusion_manager_widget,
)
from services.rider_store import (
    load_historical_for_context,
    load_profile_for_context,
    merge_rides,
    parse_ride_date,
    ride_date_key,
    ride_identity,
    save_current_rides_for_context,
    sort_rides_by_date,
    trim_rides_to_recent_weeks,
)
import ui_components as _ui_components
_ui_components = importlib.reload(_ui_components)
from ui_components import (
    data_scope_caption,
    load_tc_logo_svg as load_tc_logo_svg_from_path,
    render_empty_data_state,
    render_icp_footer as render_icp_footer_widget,
    render_mini_metric_card,
    render_pricing_intro,
    render_upgrade_note,
    select_ride_scope as select_ride_scope_widget,
)
from pages.static_pages import (
    render_changelog_page,
    render_english_review_page,
    render_home_page,
    render_privacy_page,
)
from rules.power_analysis import (
    POWER_PROFILE_MIN_PEER_SAMPLES,
    POWER_PROFILE_SAMPLES_FILE,
    anonymize_power_profile_user_id,
    build_power_profile_metrics,
    build_power_profile_sample,
    calculate_fatigue_resistance,
    calculate_power_zones,
    choose_percentile_metric,
    evaluate_power_profile,
    estimate_best_powers,
    ftp_wkg_bucket,
    get_peer_samples,
    load_power_profile_samples,
    peer_samples_for_bucket,
    percentile_rank,
    power_profile_rating_rows,
    power_profile_sample_key,
    rating_from_percentile,
    rating_from_thresholds,
    record_power_profile_sample,
    rider_type_profile,
    save_power_profile_samples,
    upsert_power_profile_sample,
)
from integrations.intervals_icu import (
    clear_intervals_pref,
    extract_intervals_activity_id,
    extract_intervals_rows,
    fetch_intervals_activities,
    fetch_intervals_activities_csv,
    get_intervals_pref_path_for_context,
    intervals_activity_date,
    intervals_activity_name,
    intervals_activity_summary_rows,
    intervals_get_bytes,
    intervals_get_field,
    intervals_get_json,
    load_intervals_pref,
    normalize_intervals_athlete_id,
    ride_from_intervals_summary,
    save_intervals_pref,
    summarize_intervals_csv_dates,
    summarize_intervals_response,
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
ICP_RECORD_NO = "冀ICP备2026017484号"
ICP_RECORD_URL = "https://beian.miit.gov.cn/"
MPS_RECORD_NO = "冀公网安备13082502000150号"
MPS_RECORD_URL = "https://beian.mps.gov.cn/#/query/webSearch?code=13082502000150"
MPS_RECORD_ICON_PATH = Path(os.environ.get("TRUECADENCE_MPS_RECORD_ICON_PATH", ASSET_DIR / "mps_beian_icon.png"))
PAYMENT_WECHAT_QR_PATH = Path(os.environ.get("TRUECADENCE_PAYMENT_WECHAT_QR_PATH", ASSET_DIR / "payment_wechat.jpg"))
PAYMENT_ALIPAY_QR_PATH = Path(os.environ.get("TRUECADENCE_PAYMENT_ALIPAY_QR_PATH", ASSET_DIR / "payment_alipay.jpg"))


def load_tc_logo_svg():
    return load_tc_logo_svg_from_path(TC_LOGO_PATH)


def render_icp_footer():
    return render_icp_footer_widget(ICP_RECORD_NO, ICP_RECORD_URL, MPS_RECORD_NO, MPS_RECORD_URL, MPS_RECORD_ICON_PATH)

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
    min-height: 7.2rem;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
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
[data-testid="stSidebar"] [data-testid="stMetric"] {
    padding: .55rem .5rem !important;
    border-radius: 9px;
    min-height: auto;
}
[data-testid="stSidebar"] [data-testid="stMetric"] label {
    font-size: .62rem !important;
    letter-spacing: .02em;
    white-space: nowrap;
}
[data-testid="stSidebar"] [data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 1.05rem !important;
    line-height: 1.1 !important;
    white-space: nowrap;
}
.tc-mini-metric-card {
    background: var(--tc-surface);
    border: 1px solid var(--tc-surface-2);
    border-radius: 10px;
    padding: 1rem;
    min-height: 7.4rem;
    height: 7.4rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    display: flex;
    flex-direction: column;
    justify-content: center;
    overflow: hidden;
}
.tc-mini-metric-card .tc-mm-label {
    color: var(--tc-subtle);
    font-size: .76rem;
    line-height: 1.2;
    text-transform: uppercase;
    letter-spacing: .06em;
    margin-bottom: .45rem;
    white-space: nowrap;
}
.tc-mini-metric-card .tc-mm-value {
    color: #ffa25c;
    font-size: 1.65rem;
    line-height: 1.08;
    font-weight: 700;
    white-space: nowrap;
}
.tc-mini-metric-card .tc-mm-delta {
    color: var(--tc-subtle);
    font-size: .82rem;
    line-height: 1.2;
    margin-top: .35rem;
    min-height: 1rem;
    white-space: nowrap;
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

/* Sidebar / TrueCadence navigation */
[data-testid="stSidebar"] {
    background:
        radial-gradient(circle at 14% 8%, rgba(255,122,18,.12), transparent 30%),
        linear-gradient(180deg, #0b0f16 0%, #0d1117 46%, #090c11 100%) !important;
    border-right: 1px solid rgba(255,122,18,.13);
}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
}
[data-testid="stSidebar"] label, [data-testid="stSidebar"] span {
    color: var(--tc-muted) !important;
}
[data-testid="stSidebar"] .stCaption {
    color: #717b88 !important;
    line-height: 1.55;
}
.tc-nav-kicker {
    margin: .72rem 0 .42rem;
    font-size: .66rem;
    letter-spacing: .18em;
    color: #7d8590;
    text-transform: uppercase;
}
.tc-nav-card {
    display:flex;
    align-items:center;
    justify-content:center;
    text-align:center;
    text-decoration:none !important;
    margin:.02rem 0 .16rem;
    min-height:1.85rem;
    height:1.85rem;
    padding:0 .72rem;
    border-radius:14px;
    border:1px solid transparent;
    background:transparent;
    transition:transform .16s ease, border-color .16s ease, background .16s ease, box-shadow .16s ease;
}
.tc-nav-card:hover {
    transform:translateX(2px);
    border-color:rgba(255,122,18,.24);
    background:linear-gradient(90deg, rgba(255,122,18,.105), rgba(255,255,255,.014));
}
.tc-nav-card.active {
    border-color:rgba(255,122,18,.36);
    background:linear-gradient(90deg, rgba(255,122,18,.24), rgba(255,122,18,.065) 62%, rgba(255,255,255,.012));
    box-shadow:inset 2px 0 0 #ff7a12, 0 10px 24px rgba(255,107,53,.12);
}
.tc-nav-card.active.solo {
    border-color:transparent;
    background:transparent;
    box-shadow:none;
}
.tc-nav-card .tc-nav-title {
    width:100%;
    color:#aab6c3;
    font-size:.90rem;
    font-weight:680;
    letter-spacing:.018em;
    line-height:1.15;
    text-align:center;
}
.tc-nav-card.active .tc-nav-title { color:#fff2e8; }
.tc-nav-card .tc-nav-desc {
    display:none;
}
.tc-nav-card.active .tc-nav-desc { display:none; }
.tc-subnav-panel {
    margin:.28rem 0 .44rem;
    padding:.42rem;
    border-radius:18px;
    border:1px solid rgba(255,122,18,.16);
    background:rgba(255,122,18,.045);
}
.tc-subnav-grid {
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:.38rem;
}
.tc-subnav-chip {
    display:flex;
    align-items:center;
    justify-content:center;
    text-decoration:none !important;
    text-align:center;
    min-height:1.70rem;
    height:1.70rem;
    padding:0 .32rem;
    border-radius:12px;
    color:#9eaab7 !important;
    font-size:.78rem;
    font-weight:620;
    letter-spacing:.016em;
    border:1px solid rgba(255,255,255,.035);
    background:rgba(255,255,255,.018);
}
.tc-subnav-chip:hover {
    color:#f0d9c8 !important;
    border-color:rgba(255,122,18,.24);
    background:rgba(255,122,18,.075);
}
.tc-subnav-chip.active {
    color:#fff7ef !important;
    border-color:rgba(255,122,18,.38);
    background:linear-gradient(180deg, rgba(255,122,18,.24), rgba(255,122,18,.09));
    box-shadow:0 5px 14px rgba(255,107,53,.10);
}
[data-testid="stSidebar"] .stButton > button[kind="secondary"],
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    width:100% !important;
    min-height:1.85rem !important;
    height:1.85rem !important;
    padding:0 !important;
    margin:.02rem 0 .16rem !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    text-align:center !important;
    border-radius:14px !important;
    font-size:.86rem !important;
    font-weight:620 !important;
    opacity:1 !important;
}
[data-testid="stSidebar"] .stButton > button[kind="secondary"] {
    border:1px solid rgba(255,255,255,.045) !important;
    background:rgba(255,255,255,.012) !important;
    color:#aab6c3 !important;
    box-shadow:none !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    border:1px solid rgba(255,122,18,.36) !important;
    background:linear-gradient(90deg, rgba(255,122,18,.24), rgba(255,122,18,.065) 62%, rgba(255,255,255,.012)) !important;
    color:#fff2e8 !important;
    font-weight:680 !important;
    box-shadow:inset 2px 0 0 #ff7a12, 0 10px 24px rgba(255,107,53,.12) !important;
}
[data-testid="stSidebar"] .stButton > button[kind="secondary"] p,
[data-testid="stSidebar"] .stButton > button[kind="primary"] p {
    width:100% !important;
    text-align:center !important;
}
[data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
    border-color:rgba(255,122,18,.24) !important;
    background:rgba(255,122,18,.075) !important;
    color:#fff2e8 !important;
}
[data-testid="stSidebar"] .stHorizontalBlock .stButton > button[kind="secondary"],
[data-testid="stSidebar"] .stHorizontalBlock .stButton > button[kind="primary"] {
    min-height:1.70rem !important;
    height:1.70rem !important;
    margin:.06rem 0 .10rem !important;
    border-radius:12px !important;
    font-size:.78rem !important;
    box-shadow:none !important;
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
.tc-icp-footer {
    margin: 2.4rem auto 0.4rem;
    padding: 1rem 0 0.2rem;
    text-align: center;
    color: #8b949e;
    font-size: 0.78rem;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.32rem;
    flex-wrap: wrap;
}
.tc-icp-footer a {
    color: #8b949e !important;
    text-decoration: none;
}
.tc-icp-footer a:hover {
    color: #ffa25c !important;
    text-decoration: underline;
}
.tc-icp-separator {
    color: #57606a;
}
.tc-mps-record {
    display: inline-flex;
    align-items: center;
    gap: 0.28rem;
}
.tc-mps-record img {
    width: 18px;
    height: 20px;
    object-fit: contain;
    vertical-align: middle;
}
</style>
""", unsafe_allow_html=True)

# ─── Auth / Login ───
if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.rider = "默认骑手"

# ─── Persistent Login Sessions ───
SESSION_FILE = DATA_DIR / "login_sessions.json"
SESSION_HANDOFF_FILE = DATA_DIR / "login_session_handoffs.json"
SESSION_COOKIE_NAME = "tc_session"
SESSION_DAYS = 30
SESSION_HANDOFF_TTL_SECONDS = 60
AUTH_BRIDGE_URL = os.environ.get("TC_AUTH_BRIDGE_URL", "http://127.0.0.1:8503")
APP_URL = os.environ.get("TC_APP_URL", "http://127.0.0.1:8502/")


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _session_expiry() -> datetime.datetime:
    return _utc_now() + datetime.timedelta(days=SESSION_DAYS)


def _iso(dt: datetime.datetime) -> str:
    return dt.astimezone(datetime.timezone.utc).isoformat(timespec="seconds")


def _parse_iso(value: str) -> datetime.datetime | None:
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _hash_token(token: str) -> str:
    return hashlib.sha256(f"{token}:truecadence-session".encode("utf-8")).hexdigest()


def _load_sessions() -> dict:
    if SESSION_FILE.exists():
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def _save_sessions(sessions: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = SESSION_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)
    os.replace(tmp, SESSION_FILE)


def _public_user(uid: str, user_data: dict) -> dict:
    return {"user_id": uid, **user_data}


def create_login_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    sessions = _load_sessions()
    sessions[_hash_token(token)] = {
        "user_id": user_id,
        "created_at": _iso(_utc_now()),
        "expires_at": _iso(_session_expiry()),
        "revoked_at": None,
    }
    _save_sessions(sessions)
    return token


def _load_handoffs() -> dict:
    if SESSION_HANDOFF_FILE.exists():
        try:
            with open(SESSION_HANDOFF_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def _save_handoffs(handoffs: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = SESSION_HANDOFF_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(handoffs, f, ensure_ascii=False, indent=2)
    os.replace(tmp, SESSION_HANDOFF_FILE)


def create_session_handoff(token: str) -> str:
    code = secrets.token_urlsafe(24)
    now = _utc_now()
    handoffs = _load_handoffs()
    fresh = {}
    for k, row in handoffs.items():
        if not isinstance(row, dict):
            continue
        expires_at = _parse_iso(row.get("expires_at", ""))
        if expires_at and expires_at > now and not row.get("used_at"):
            fresh[k] = row
    fresh[code] = {
        "token": token,
        "created_at": _iso(now),
        "expires_at": _iso(now + datetime.timedelta(seconds=SESSION_HANDOFF_TTL_SECONDS)),
        "used_at": None,
    }
    _save_handoffs(fresh)
    return code


def validate_login_session(token: str) -> tuple[bool, dict | None]:
    if not token:
        return False, None
    sessions = _load_sessions()
    row = sessions.get(_hash_token(token))
    if not isinstance(row, dict) or row.get("revoked_at"):
        return False, None
    expires_at = _parse_iso(row.get("expires_at", ""))
    if not expires_at or expires_at <= _utc_now():
        return False, None
    user_id = row.get("user_id", "")
    users = load_users()
    user_data = users.get(user_id)
    if not isinstance(user_data, dict):
        return False, None
    if user_data.get("plan") != "free":
        expires = user_data.get("expires", "")
        if expires and expires < datetime.date.today().isoformat():
            return False, None
    row["last_seen_at"] = _iso(_utc_now())
    sessions[_hash_token(token)] = row
    _save_sessions(sessions)
    return True, _public_user(user_id, user_data)


def revoke_login_session(token: str):
    if not token:
        return
    sessions = _load_sessions()
    key = _hash_token(token)
    if isinstance(sessions.get(key), dict):
        sessions[key]["revoked_at"] = _iso(_utc_now())
        _save_sessions(sessions)


def _session_token_from_browser() -> str:
    try:
        return st.context.cookies.get(SESSION_COOKIE_NAME, "") or ""
    except Exception:
        return ""


def _clear_session_query_param():
    try:
        st.query_params.pop(SESSION_COOKIE_NAME, None)
    except Exception:
        pass


def _auth_bridge_set_url(token: str) -> str:
    from urllib.parse import quote
    code = create_session_handoff(token)
    return f"{AUTH_BRIDGE_URL}/set-session?code={quote(code)}&next={quote(APP_URL, safe='')}"


def _auth_bridge_clear_url() -> str:
    from urllib.parse import quote
    return f"{AUTH_BRIDGE_URL}/clear-session?next={quote(APP_URL, safe='')}"


def restore_login_from_session():
    if st.session_state.get("user") is not None:
        return
    token = _session_token_from_browser()
    ok, user_data = validate_login_session(token)
    if ok and user_data:
        st.session_state.user = user_data
        st.session_state.rider = user_data.get("active_rider", "默认骑手")
        st.session_state["session_token"] = token
        _clear_session_query_param()
    elif token:
        revoke_login_session(token)
        st.session_state.pop("session_token", None)
        _clear_session_query_param()


def remember_login(user_id: str):
    # Create a server-side session for future backend-cookie support, but the
    # current login state is carried by Streamlit session_state.
    token = create_login_session(user_id)
    st.session_state["session_token"] = token
    return token


def finish_login_and_redirect(user_id: str):
    token = remember_login(user_id)
    target = _auth_bridge_set_url(token)
    st.markdown(f"""
<meta http-equiv="refresh" content="0; url={target}">
<div style="padding:1rem;border:1px solid rgba(255,107,53,.28);border-radius:12px;background:rgba(255,107,53,.08);color:#e6edf3;">
  登录成功,正在进入 TrueCadence...<br>
  <span style="color:#8b949e;font-size:.9em;">如果没有自动跳转,请点击下方按钮。</span>
</div>
""", unsafe_allow_html=True)
    st.link_button("进入 TrueCadence", target, type="primary")
    st.stop()


def logout_current_session():
    token = st.session_state.get("session_token") or _session_token_from_browser()
    revoke_login_session(token)
    st.session_state.pop("session_token", None)
    _clear_session_query_param()


restore_login_from_session()
if st.session_state.user is not None:
    _clear_session_query_param()

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
    <div class="copy">不是追求别人的速度,而是在训练、生活和选择里,找到真正属于自己的节奏</div>
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
                st.caption("安全提示:建议使用浏览器/手机密码管理器保存密码;TrueCadence 不会在链接中保存登录凭证。")
                login_submit = st.form_submit_button("登录", type="primary", use_container_width=True)
            if login_submit:
                if not login_phone or not login_pw:
                    st.error("请填写手机号和密码")
                else:
                    ok, msg, user_data = login_user(login_phone.strip(), login_pw)
                    if ok and user_data:
                        st.session_state.user = user_data
                        st.session_state.rider = user_data.get("active_rider", "默认骑手")
                        finish_login_and_redirect(user_data["user_id"])
                    else:
                        st.error(msg)

        with tab2:
            with st.form("register_form"):
                reg_invite = st.text_input("内测邀请码 *", placeholder="输入内测邀请码(必填)", key="reg_invite")
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
                        st.success("注册成功!正在登录...")
                        _, _, user_data = login_user(reg_phone.strip(), reg_pw)
                        if user_data:
                            st.session_state.user = user_data
                            st.session_state.rider = user_data.get("active_rider", "默认骑手")
                            finish_login_and_redirect(user_data["user_id"])
                    else:
                        st.error(msg)
    render_icp_footer()
    st.stop()




# ─── Sidebar ───
side_logo_uri = load_tc_logo_svg()
st.sidebar.markdown("""
<style>
.tc-side-brand-wrap {
    text-align:center;
    padding:0 0.35em 0.62em;
    margin-top:-2.05rem;
    margin-bottom:0.34em;
    background:transparent;
    border-bottom:1px solid rgba(255,122,18,.13);
    pointer-events:none;
}
.tc-side-brand-wrap img { pointer-events:none; }
.tc-side-symbol {
    position: relative;
    width: 76px;
    height: 46px;
    margin: 0 auto 0.18em;
    border-radius: 14px;
    overflow: visible;
    filter: drop-shadow(0 0 6px rgba(255,107,53,0.72)) drop-shadow(0 0 18px rgba(255,107,53,0.32)) drop-shadow(0 0 30px rgba(255,107,53,0.16));
    animation: tcSideLogoPulse 4.8s ease-in-out infinite;
}
.tc-side-symbol img { width:100%; height:100%; object-fit:contain; display:block; }
.tc-side-shine-word {
    display: inline-block;
    font-family: 'Aptos Display', 'Segoe UI Variable Display', 'Inter', system-ui, sans-serif;
    font-size: 1.42em;
    letter-spacing: 0.055em;
    font-weight: 520;
    line-height: 0.95;
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
    margin-top:0.38em;
    font-size:0.68em;
    letter-spacing:0.17em;
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

_nav_user = st.session_state.get("user", {}) or {}
is_admin_user = bool(_nav_user.get("is_admin") or _nav_user.get("role") in ("admin", "super_admin") or str(_nav_user.get("phone", "")) == "18503146826")

nav_groups = {
    "首页": {"desc": "", "pages": [("功能说明", "🏠 功能说明")]},
    "我的档案": {"desc": "身体、目标、骑手", "pages": [("骑手档案", "👤 骑手档案"), ("目标追踪", "🎯 目标追踪")]},
    "导入数据": {"desc": "FIT 与平台数据", "pages": [("FIT 上传", "📤 上传分析"), ("平台导入", "🔗 数据导入")]},
    "AI 分析": {"desc": "核心诊断", "pages": [("AI 分析", "🧠 AI 功率分析")]},
    "我的分析": {"desc": "能力、恢复", "pages": [("功率仪表盘", "📊 功率仪表盘"), ("恢复睡眠", "🛌 恢复与睡眠"), ("营养补给", "🍝 营养与补给")]},
    "训练建议": {"desc": "负荷、课表、反馈", "pages": [("训练负荷", "📈 训练负荷"), ("训练课表", "📋 训练课表"), ("训练反馈", "📝 训练反馈")]},
    "数据与支持": {"desc": "隐私、反馈、版本", "pages": [("数据隐私", "🔐 数据隐私"), ("内测反馈", "🐞 内测反馈"), ("套餐对比", "💎 套餐对比"), ("更新日志", "📌 更新日志")]},
    "English / Review": {"desc": "Platform review", "pages": [("Review", "🌐 English / Review")]},
}
if is_admin_user:
    nav_groups["管理后台"] = {"desc": "订单与反馈", "pages": [("管理后台", "🛠️ 管理后台")]}

query_nav = st.query_params.get("nav")
query_page = st.query_params.get("sub")
if isinstance(query_nav, list):
    query_nav = query_nav[0] if query_nav else None
if isinstance(query_page, list):
    query_page = query_page[0] if query_page else None
if query_nav not in nav_groups:
    query_nav = "首页"
section_names = list(nav_groups.keys())
nav_section = query_nav
sub_pages = nav_groups[nav_section]["pages"]
page_labels = [label for label, _ in sub_pages]
if query_page not in page_labels:
    query_page = page_labels[0]
page = dict(sub_pages)[query_page]

def _set_nav(target_nav, target_sub=None):
    st.query_params["nav"] = target_nav
    if target_sub:
        st.query_params["sub"] = target_sub
    elif "sub" in st.query_params:
        del st.query_params["sub"]

st.sidebar.markdown('<div class="tc-nav-kicker">Flow</div>', unsafe_allow_html=True)
plan_for_nav = PLANS.get(st.session_state.get("user", {}).get("plan", "free"), PLANS["free"]).get("level", 0)
for name in section_names:
    is_active = name == nav_section
    if name == "训练建议" and plan_for_nav >= 1:
        on_training_plan = page == "📋 训练课表"
        parent_active = is_active and not on_training_plan
        if st.sidebar.button("训练建议", key=f"nav_btn_{name}", use_container_width=True, type=("primary" if parent_active else "secondary")):
            _set_nav(name)
            st.rerun()
        if st.sidebar.button("生成课表", key="btn_quick_training_plan", use_container_width=True, type=("primary" if on_training_plan else "secondary")):
            _set_nav("训练建议", "训练课表")
            st.rerun()
        continue
    if st.sidebar.button(name, key=f"nav_btn_{name}", use_container_width=True, type=("primary" if is_active else "secondary")):
        first_label = nav_groups[name]["pages"][0][0]
        _set_nav(name, first_label)
        st.rerun()

visible_subs = sub_pages if nav_section == "训练建议" else [(lbl, emoji) for lbl, emoji in sub_pages if lbl != "训练课表"]
if len(visible_subs) > 1 and not (nav_section == "训练建议" and page == "📋 训练课表"):
    st.sidebar.markdown('<div class="tc-nav-kicker">Detail</div>', unsafe_allow_html=True)
    cols = st.sidebar.columns(2)
    for i, (label, _) in enumerate(visible_subs):
        active = label == query_page
        if cols[i % len(cols)].button(label, key=f"sub_btn_{nav_section}_{label}", use_container_width=True, type=("primary" if active else "secondary")):
            _set_nav(nav_section, label)
            st.rerun()


st.sidebar.caption("FLOW 01 · 档案 → 导入 → 分析 → 建议")

if nav_section == "导入数据":
    st.sidebar.divider()
    up_count = len(st.session_state.get('last_import_rides') or st.session_state.get('uploaded_rides', []))
    try:
        hi_count = len(load_rider_rides(st.session_state.user["user_id"], st.session_state.get("rider", "默认骑手")))
    except Exception:
        hi_count = 0
    import_busy = bool(st.session_state.get("intervals_import_busy"))
    pending_fit_files = st.session_state.get("fit_file_uploader") if page == "📤 上传分析" else None
    pending_fit_sig = tuple((getattr(f, "name", ""), getattr(f, "size", 0) or 0) for f in (pending_fit_files or []))
    last_fit_sig = st.session_state.get("last_fit_upload_sig")
    fit_upload_busy = bool(st.session_state.get("fit_upload_busy") or (pending_fit_sig and pending_fit_sig != last_fit_sig))
    clear_disabled = import_busy or fit_upload_busy
    with st.sidebar.expander("数据状态", expanded=True):
        c_up, c_hi = st.columns(2)
        c_up.metric("本次", f"{up_count}条")
        c_hi.metric("历史", f"{hi_count}条")
        if import_busy:
            st.warning("正在导入,暂时不能清除数据。")
        if fit_upload_busy:
            st.warning("正在上传/解析 FIT,暂时不能清除数据。")
        if st.button("清除本次", disabled=clear_disabled, help="只清除当前会话里的本次上传/导入缓存,不删除历史存档", use_container_width=True):
            st.cache_data.clear()
            st.session_state.uploaded_rides = []
            st.session_state.pop("last_import_rides", None)
            st.session_state.pop("last_import_count", None)
            st.session_state.pop("last_import_message", None)
            st.session_state.pop("last_import_table", None)
            st.rerun()
        confirm_sidebar_clear = st.checkbox("确认清除历史", disabled=clear_disabled, key="sidebar_confirm_clear_history", help="会删除当前骑手已保存的历史训练摘要,账号和骑手档案不受影响。")
        if st.button("清除历史", disabled=clear_disabled or not confirm_sidebar_clear, help="删除当前骑手历史存档;不可撤销,建议只在测试脏数据或重新建档时使用。", use_container_width=True):
            save_rider_data(st.session_state.user["user_id"], st.session_state.get("rider", "默认骑手"), "rides", [])
            st.cache_data.clear()
            st.session_state.uploaded_rides = []
            st.session_state.pop("last_import_rides", None)
            st.session_state.pop("last_import_count", None)
            st.session_state.pop("last_import_message", None)
            st.session_state.pop("last_import_table", None)
            st.success("已清除当前骑手历史存档。")
            st.rerun()

st.sidebar.divider()

# ─── Rider Selector ───
user = st.session_state.user
is_admin_user = bool(user.get("is_admin") or user.get("role") in ("admin", "super_admin") or str(user.get("phone", "")) == "18503146826")
if is_admin_user and not user.get("is_admin"):
    st.session_state.user["is_admin"] = True
    st.session_state.user["role"] = user.get("role") or "admin"
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

try:
    _sidebar_history_count = len(load_rider_rides(user["user_id"], st.session_state.get("rider", "默认骑手")))
except Exception:
    _sidebar_history_count = 0

if len(riders) > 1:
    current = st.session_state.get("rider", riders[0])
    if current not in riders:
        current = riders[0]
    idx = riders.index(current)
    selected = st.sidebar.selectbox("当前骑手", riders, index=idx, key="rider_select")
    if selected != st.session_state.get("rider"):
        st.session_state.rider = selected
        st.cache_data.clear()
        st.rerun()
else:
    st.sidebar.caption(f"当前骑手 · {st.session_state.get('rider', '默认骑手')}")

with st.sidebar.expander("账户", expanded=False):
    st.caption(f"{user['phone'][:3]}****{user['phone'][-4:]}")
    st.caption(f"{plan_info['name']} · {len(riders)}/{plan_info['riders']}骑手")
    if remaining > 0 and remaining < 9999:
        if remaining <= 7:
            st.warning(f"剩余 {remaining} 天,即将到期")
        else:
            st.caption(f"剩余 {remaining} 天")
    st.caption(f"当前骑手:{st.session_state.get('rider', '默认骑手')}")
    st.caption(f"训练存档:{_sidebar_history_count} 条")

    current_plan = user.get("plan", "free")
    plan_order = ["free", "core", "pro", "coach"]
    upgrades = [k for k in plan_order if plan_order.index(k) > plan_order.index(current_plan)]
    if upgrades:
        st.divider()
        st.caption("升级套餐")
        for plan_key in upgrades:
            plan_d = PLANS[plan_key]
            dur_labels = " · ".join([f"{d}{p['price']}" for d, p in plan_d["durations"].items()])
            if st.button(f"{plan_d['name']}  ({dur_labels})", key=f"up_{plan_key}", use_container_width=True):
                st.session_state["upgrade_to"] = plan_key
                st.session_state.pop("upgrade_dur", None)
        if st.session_state.get("upgrade_to"):
            target = st.session_state["upgrade_to"]
            st.info(f"升级到 {PLANS[target]['name']}")
            dur_opts = PLANS[target]["durations"]
            dur_choice = st.selectbox("付费周期", list(dur_opts.keys()),
                                      format_func=lambda d: f"{d} · {dur_opts[d]['price']} · {dur_opts[d]['days']}天",
                                      key="upgrade_dur")
            st.caption(f"价格:{dur_opts[dur_choice]['price']} / {dur_opts[dur_choice]['days']}天")
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
        st.caption(f"已是最高套餐:{PLANS[current_plan]['name']}")

if st.sidebar.button("退出登录", use_container_width=True):
    logout_current_session()
    st.session_state.user = None
    st.session_state.rider = "默认骑手"
    st.cache_data.clear()
    target = _auth_bridge_clear_url()
    st.markdown(f"""
<meta http-equiv="refresh" content="0; url={target}">
<div style="padding:1rem;border:1px solid rgba(255,107,53,.28);border-radius:12px;background:rgba(255,107,53,.08);color:#e6edf3;">
  已退出,正在清除本设备登录状态...<br>
  <span style="color:#8b949e;font-size:.9em;">如果没有自动跳转,请点击下方按钮。</span>
</div>
""", unsafe_allow_html=True)
    st.link_button("完成退出", target, type="primary")
    st.stop()


DATA_FILE = str(APP_DIR / "self_data.json")
PROFILE_FILE = str(APP_DIR / "profile.json")
BETA_FEEDBACK_FILE = DATA_DIR / "beta_feedback.json"


def load_beta_feedback():
    return load_beta_feedback_from_file(BETA_FEEDBACK_FILE)



def save_beta_feedback(items):
    return save_beta_feedback_to_file(items, BETA_FEEDBACK_FILE)



def current_rider_power_exclusions_path():
    user = st.session_state.get("user")
    rider = st.session_state.get("rider", "默认骑手")
    return power_exclusions_path_for_context(user, rider, APP_DIR, get_rider_data_path)


def render_power_exclusion_manager(rides):
    return render_power_exclusion_manager_widget(rides, current_rider_power_exclusions_path())


def load_profile():
    """Load saved client profile for current rider, fallback to defaults."""
    user = st.session_state.get("user")
    rider = st.session_state.get("rider", "默认骑手")
    return load_profile_for_context(user, rider, PROFILE_FILE, load_rider_profile)


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
                "一键导出 .ZWO 文件,导入 Zwift",
            ]),
            "🛌 恢复与睡眠": ("实时追踪CTL/ATL/TSB,自动提醒恢复状态", "🛌", [
                "训练负荷 PMC 曲线",
                "疲劳/体能/状态三指标",
                "自动恢复建议 + 睡眠优化",
            ]),
            "🍝 营养与补给": ("根据训练强度和体重,自动计算每日营养需求", "🍝", [
                "训练日/休息日分区营养方案",
                "车上补给时间×强度双维度建议",
                "碳水/蛋白质/脂肪精确到克",
            ]),
            "🎯 目标追踪": ("设定目标FTP,根据可投入时间预估到达路径", "🎯", [
                "目标FTP每周预估增幅",
                "里程碑时间线(每4周)",
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
        st.caption("在侧边栏「账户」中选择套餐并输入内测邀请码升级,或联系客服")
        st.stop()






def get_intervals_pref_path():
    user = st.session_state.get("user")
    rider = st.session_state.get("rider", "默认骑手")
    return get_intervals_pref_path_for_context(user, rider, get_rider_data_path)

def load_feedback():
    user = st.session_state.get("user")
    rider = st.session_state.get("rider", "默认骑手")
    return load_feedback_for_rider(user, rider, get_rider_data_path, get_user_dir, trim_rides_to_recent_weeks)



def save_feedback(data):
    user = st.session_state.get("user")
    rider = st.session_state.get("rider", "默认骑手")
    return save_feedback_for_rider(data, user, rider, save_rider_data)



def load_wearable_sleep():
    user = st.session_state.get("user")
    rider = st.session_state.get("rider", "默认骑手")
    return load_wearable_sleep_for_rider(user, rider, get_rider_data_path)



def save_wearable_sleep(data):
    user = st.session_state.get("user")
    rider = st.session_state.get("rider", "默认骑手")
    return save_wearable_sleep_for_rider(data, user, rider, save_rider_data)


def infer_cycle_status_for_date(item, profile=None):
    return feedback_infer_cycle_status_for_date(item, profile or load_profile())



def summarize_recent_feedback(feedback, days=14):
    return feedback_summarize_recent_feedback(feedback, load_profile(), days)


FIT_DIR = str(APP_DIR / "fit")

# ─── Session state init ───
if 'uploaded_rides' not in st.session_state:
    st.session_state.uploaded_rides = []
if 'historical_loaded' not in st.session_state:
    st.session_state.historical = None

# ─── Data loading ───
HISTORY_RETENTION_DAYS = 84


@st.cache_data(ttl=10)
def load_historical():
    user = st.session_state.get("user")
    rider = st.session_state.get("rider", "默认骑手")
    return load_historical_for_context(user, rider, DATA_FILE, load_rider_rides)




























































# ─── FTP estimation ───
def get_effective_ftp(rides):
    p = load_profile()
    if p.get('ftp_test', 0) > 0:
        return p['ftp_test']
    return estimate_ftp(rides)



def select_ride_scope(toggle_label="合并全历史数据", key=None, help_text=None, recommended=False):
    return select_ride_scope_widget(load_historical, merge_rides, toggle_label, key, help_text, recommended)









def save_current_rides(rides):
    """Persist current rider history and clear cached historical reads."""
    user = st.session_state.get("user")
    rider = st.session_state.get("rider", "默认骑手")
    save_current_rides_for_context(rides, user, rider, DATA_FILE, save_rider_data)
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
        state_desc = "已解析 FIT 数据,可以继续查看功率仪表盘和训练负荷。"
        state_color = "#8b949e"
    elif tsb <= -30:
        state = "疲劳偏高"
        state_desc = "短期负荷明显高于长期负荷,近期不建议连续堆高强度。"
        state_color = "#ff6b35"
    elif tsb <= -15:
        state = "负荷偏紧"
        state_desc = "训练刺激充足,但恢复余量有限,适合控制强度密度。"
        state_color = "#ffb020"
    elif tsb >= 12:
        state = "恢复较好"
        state_desc = "当前状态相对清爽,可以安排质量课,但仍要看睡眠和主观疲劳。"
        state_color = "#3fb950"
    else:
        state = "状态相对平衡"
        state_desc = "训练负荷和恢复大致平衡,适合按计划推进。"
        state_color = "#58a6ff"

    traits = []
    if ftp and p20:
        ratio20 = p20 / ftp
        if ratio20 >= 1.03:
            traits.append("20min 功率证据较强,FTP 可能有上调空间")
        elif ratio20 >= 0.95:
            traits.append("20min 功率接近 FTP,阈值能力较扎实")
    if ftp and p60:
        ratio60 = p60 / ftp
        if ratio60 >= 0.92:
            traits.append("60min 保持能力较好,耐力/疲劳抗性不错")
        elif ratio60 and ratio60 < 0.82:
            traits.append("60min 保持能力偏弱,后续可补耐力和甜区")
    if p5s and ftp and p5s / ftp >= 4.5:
        traits.append("短时爆发相对突出")
    if not traits:
        traits.append("已建立基础功率画像,建议继续补充 4-12 周数据让判断更稳定")

    suggestions = []
    if tsb is not None and tsb <= -20:
        suggestions.extend(["接下来 2-3 天优先恢复或 Z1/Z2", "暂时减少 VO2max / 阈值连续刺激"])
    elif tsb is not None and tsb >= 12:
        suggestions.extend(["可以安排 1 次质量课", "质量课后注意补碳水和睡眠"])
    else:
        suggestions.extend(["先查看训练负荷确认 CTL/ATL/TSB", "再进入 AI 功率分析生成更完整建议"])
    if actual_ftp <= 0:
        suggestions.append("如果知道实测 FTP,请到骑手档案填写,区间和课表会更准")
    suggestions.append("建议补一条训练反馈,让恢复判断更贴近真实体感")

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
  <div class="status">当前状态:{state}</div>
  <div class="body">
    数据范围:<b>{range_text}</b>|记录:<b>{len(rides)} 条</b>|FTP:<b>{ftp}W</b>({ftp_source})|功体比:<b>{wkg} W/kg</b><br>
    训练负荷:CTL <b>{ctl if ctl is not None else '-'}</b> / ATL <b>{atl if atl is not None else '-'}</b> / TSB <b>{tsb if tsb is not None else '-'}</b>|近7天 TSS <b>{round(recent7_tss)}</b>|近28天 TSS <b>{round(recent28_tss)}</b><br>
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






POWER_PROFILE_DURATIONS = ['5s', '30s', '1min', '5min', '20min', '60min']
POWER_PROFILE_FIXED_THRESHOLDS = {
    # Thresholds are pct_ftp cutoffs for: 一般 / 良好 / 优秀 / 卓越.
    # This is the fixed-reference fallback; later peer percentile ratings can override it.
    '5s': [250, 300, 350, 400],
    '30s': [140, 160, 180, 200],
    '1min': [130, 145, 160, 175],
    '5min': [105, 112, 120, 128],
    '20min': [95, 98, 100, 105],
    '60min': [88, 92, 95, 100],
}




POWER_PROFILE_MIN_PEER_SAMPLES = 30
POWER_PROFILE_SAMPLES_FILE = DATA_DIR / "power_profile_samples.json"
POWER_PROFILE_SAMPLE_SCHEMA_VERSION = 1









































# ─── Plot helpers ───
def plot_pmc(rides):
    return plot_pmc_chart(rides, compute_daily_pmc)


# ─── AI diagnosis ───

def generate_diagnosis(rides, ftp, best, weight=69, feedback=None, sleep_records=None):
    """Generate a richer rider diagnosis report from available ride summaries."""
    if not ftp:
        return "数据不足,请上传更多带功率数据的 FIT 文件。"

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
    fatigue = calculate_fatigue_resistance(rides_sorted, ftp, best, weight)

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
        core_focus = "维持高水平能力,重点做专项化和恢复管理"

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
        strengths.append("短时爆发力不错,适合冲刺、跟攻和短坡变化")
    elif p5 and p5 / ftp < 3.5:
        weaknesses.append("5秒爆发偏弱,冲刺和快速变速能力需要补强")
    if p5m and p5m / ftp >= 1.18:
        strengths.append("5分钟能力较好,VO2max 和追击能力有优势")
    elif p5m and p5m / ftp < 1.08:
        weaknesses.append("5分钟功率偏弱,高强度爬坡和追击能力需要训练")
    if p20 and p20 / ftp >= 0.98:
        strengths.append("20分钟阈值支撑较好,FTP 估算可信度较高")
    elif p20 and p20 / ftp < 0.90:
        weaknesses.append("20分钟能力相对不足,甜区/阈值连续输出需要加强")
    if p60 and p60 / ftp >= 0.90:
        strengths.append("60分钟耐力保持较好,长时间输出不容易崩")
    elif p60 and p60 / ftp < 0.82:
        weaknesses.append("60分钟维持能力偏弱,疲劳抗性和长时间 Z2 需要加强")

    if not strengths:
        strengths.append("目前数据更适合先建立稳定训练画像,优势区间还需要更多高质量记录确认")
    if not weaknesses:
        weaknesses.append("当前数据没有暴露明显单点短板,下一阶段可优先关注训练连续性、恢复质量和专项目标匹配")

    # Training volume interpretation
    if avg_week_h < 3:
        volume_comment = "训练量明显偏少,当前最优先不是堆强度,而是把每周规律骑行建立起来。"
        volume_target = "先稳定到每周 3-4 次、4-6 小时。"
    elif avg_week_h < 6:
        volume_comment = "训练量偏基础,可以开始建立结构化训练,但强度不要太密。"
        volume_target = "逐步稳定到每周 6-8 小时。"
    elif avg_week_h < 10:
        volume_comment = "训练量适中,已经具备做系统周期训练的基础。"
        volume_target = "保持每周 2 次质量课 + 2-3 次 Z2/恢复。"
    else:
        volume_comment = "训练量较高,提升空间更多来自恢复质量、强弱分配和专项化。"
        volume_target = "控制强度密度,避免每次都骑成中高强度。"

    # Fatigue interpretation
    fatigue_lines = []
    if fatigue:
        for dur, val in fatigue.items():
            power = val.get('power', 0)
            rating = val.get('rating', '')
            fatigue_lines.append(f"- **{dur}**:{power}W({val.get('%FTP', 0)}% FTP)→ **{rating}**")
        weak_zones = [z for z, v in fatigue.items() if v.get('rating') in ('一般', '待提升')]
        strong_zones = [z for z, v in fatigue.items() if v.get('rating') in ('优秀', '卓越')]
    else:
        weak_zones, strong_zones = [], []
        fatigue_lines.append("- 暂无足够数据判断疲劳抗性,建议上传更长时间或更多历史骑行记录。")

    # Weekly prescription
    z2_lo, z2_hi = round(ftp * 0.55), round(ftp * 0.75)
    tempo_lo, tempo_hi = round(ftp * 0.76), round(ftp * 0.87)
    ss_lo, ss_hi = round(ftp * 0.88), round(ftp * 0.94)
    th_lo, th_hi = round(ftp * 0.95), round(ftp * 1.02)
    vo2_lo, vo2_hi = round(ftp * 1.05), round(ftp * 1.18)

    if avg_week_h < 4 or wkg < 2.5:
        week_plan = [
            f"2-3 次 Z2 有氧:每次 60-120 分钟,功率约 **{z2_lo}-{z2_hi}W**。",
            f"1 次轻甜区入门:2-3 组 × 8-12 分钟,功率约 **{ss_lo}-{ss_hi}W**,组间轻松骑 5 分钟。",
            "其余时间做恢复骑或休息,不建议连续两天高强度。",
        ]
    elif weak_zones:
        week_plan = [
            f"1 次甜区/阈值课:3×12-15 分钟甜区 **{ss_lo}-{ss_hi}W**,或 4×8 分钟阈值 **{th_lo}-{th_hi}W**。",
            f"1 次 VO2max 维护:4-5×3 分钟 **{vo2_lo}-{vo2_hi}W**,不要做到力竭。",
            f"2-3 次 Z2 有氧:每次 90-150 分钟,功率约 **{z2_lo}-{z2_hi}W**。",
        ]
    else:
        week_plan = [
            f"1 次专项质量课:根据目标选择阈值 **{th_lo}-{th_hi}W** 或 VO2max **{vo2_lo}-{vo2_hi}W**。",
            f"1 次长距离 Z2:2-4 小时,功率约 **{z2_lo}-{z2_hi}W**,后段保持稳定不要掉功率。",
            f"1 次节奏/甜区:Tempo **{tempo_lo}-{tempo_hi}W** 或甜区 **{ss_lo}-{ss_hi}W**,用于提高有氧效率。",
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
        nap_phrase = f",午睡 {len(nap_items)} 次,平均 **{avg_nap}min**,更清醒 {nap_refresh} 次,更困 {nap_sluggish} 次" if nap_items else ""
        sleep_lines.append(f"最近 {len(recent_sleep)} 条手表睡眠:平均夜间睡眠 **{sleep_avg_hours or '-'}h**,评分 **{sleep_avg_score or '-'}**,HRV **{sleep_avg_hrv or '-'}**,静息心率 **{sleep_avg_rest_hr or '-'}**,压力 **{sleep_avg_stress or '-'}**,Body Battery/恢复分 **{sleep_avg_body_battery or '-'}**{nap_phrase}。")
        if nap_items:
            if nap_sluggish:
                sleep_risk_flags.append("午睡后仍昏沉,下午训练不宜直接上高强度。")
            elif nap_refresh and 15 <= avg_nap <= 45:
                sleep_lines.append("短午睡且醒后更清醒,可作为下午训练准备度的小幅加成,但不能完全抵消夜间睡眠债。")
        if sleep_avg_hours and sleep_avg_hours < 5.5:
            sleep_risk_flags.append(f"平均睡眠 {sleep_avg_hours}h,明显不足,质量课建议下调或取消。")
        elif sleep_avg_hours and sleep_avg_hours < 6.5:
            sleep_risk_flags.append(f"平均睡眠 {sleep_avg_hours}h,偏少,高强度训练需谨慎。")
        if sleep_avg_score and sleep_avg_score < 55:
            sleep_risk_flags.append(f"睡眠评分 {sleep_avg_score},恢复很差,优先恢复而非加训练量。")
        elif sleep_avg_score and sleep_avg_score < 70:
            sleep_risk_flags.append(f"睡眠评分 {sleep_avg_score},恢复一般,避免连续高强度。")
        if sleep_avg_stress and sleep_avg_stress >= 70:
            sleep_risk_flags.append(f"压力分 {sleep_avg_stress},自主神经压力偏高,训练日应保守。")
        if sleep_avg_body_battery and sleep_avg_body_battery < 35:
            sleep_risk_flags.append(f"恢复分 {sleep_avg_body_battery},恢复储备偏低。")
        if not sleep_risk_flags:
            sleep_lines.append("手表睡眠未见明显红旗,可作为正常训练的辅助确认。")
    else:
        sleep_lines.append("暂未录入手表睡眠数据;AI 恢复判断主要依赖训练反馈和训练负荷。")

    # Risks and data quality
    risk_lines = []
    if total_rides < 5:
        risk_lines.append("当前记录数偏少,诊断更像初筛;建议至少上传 10-20 条记录后再做正式判断。")
    if not p20 or not p60:
        risk_lines.append("缺少 20min/60min 级别有效记录,FTP 和耐力判断可能偏保守。")
    if avg_tss_week == 0:
        risk_lines.append("多数记录缺少 TSS,训练负荷和恢复风险判断会受限。")
    if not any(r.get('hr_avg', 0) for r in rides_sorted):
        risk_lines.append("缺少心率数据,无法判断同功率下的心肺压力和恢复状态。")
    if not risk_lines:
        risk_lines.append("当前数据质量可以支撑基础训练判断;后续继续积累近期记录,诊断会更稳定。")

    feedback_badge = ""
    if feedback_summary.get("count", 0):
        feedback_badge = f"\n> ✅ 本报告已纳入最近 **{feedback_summary.get('count', 0)}** 条训练反馈,最新记录:**{feedback_summary.get('last_date', '未知')}**。\n"
    else:
        feedback_badge = "\n> ⚠️ 本报告暂未读取到训练反馈,恢复和疼痛判断主要来自功率数据。\n"

    sleep_badge = f"> ✅ 本报告已纳入 **{len(recent_sleep)}** 条手表睡眠/恢复记录,最新记录:**{latest_sleep.get('date', '未知')}**。\n" if recent_sleep else "> ⚠️ 本报告暂未读取到手表睡眠/恢复记录。\n"

    diagnosis = f"""## 🔍 TrueCadence 骑手诊断报告
{feedback_badge}{sleep_badge}
### 1. 一句话结论
你当前处于 **{level}**,骑手画像为 **{rider}**。下一阶段可优先关注:**{core_focus}**。

### 2. 判断依据说明
以下判断主要基于 FIT 文件中的最佳功率曲线、FTP、训练频率、训练负荷、近期反馈和睡眠/恢复记录。如果没有专门做过冲刺、5分钟、20分钟或60分钟测试,相关结论更适合作为参考方向,不等于能力定论。

### 3. 当前能力概览
- FTP:**{ftp}W**
- 功体比:**{wkg} W/kg**(体重 {weight}kg)
- 数据范围:**{total_rides}** 条记录 / **{total_h}** 小时 / **{total_km}** km
- 周均训练:约 **{avg_week_h}h/周**、**{avg_week_rides} 次/周**、TSS **{avg_tss_week}/周**
- 骑手类型:**{rider}**

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

    diagnosis += f"\n### 6. 训练量与一致性判断\n- {volume_comment}\n- 建议目标:{volume_target}\n"

    diagnosis += "\n### 7. 疲劳抗性\n"
    diagnosis += "\n".join(fatigue_lines) + "\n"
    if strong_zones:
        diagnosis += f"- 优势维持区间:**{', '.join(strong_zones)}**\n"
    if weak_zones:
        diagnosis += f"- 优先补强区间:**{', '.join(weak_zones)}**\n"

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
        diagnosis += "- 暂无明显主观/睡眠恢复红旗;如果近期有睡眠差、疼痛或感冒,请先补记。\n"

    diagnosis += "\n### 10. 风险与数据质量提醒\n"
    for r in risk_lines:
        diagnosis += f"- {r}\n"

    diagnosis += "\n### 11. 下一步操作\n"
    diagnosis += "- 去 **📊 功率仪表盘** 看功率曲线和区间细节。\n"
    diagnosis += "- 如果已解锁 Core,进入 **📋 训练课表** 生成可执行课表。\n"
    diagnosis += "- 在 **👤 骑手档案** 中补充真实 FTP、体重、最大心率和训练目标,后续判断会更准。\n"

    return diagnosis

# ─── Pages ───

if page == "🏠 功能说明":
    render_home_page()

elif page == "📌 更新日志":
    render_changelog_page()

elif page == "🌐 English / Review":
    render_english_review_page()

elif page == "🔐 数据隐私":
    render_privacy_page(save_current_rides_func=save_current_rides)
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

    with st.form("beta_feedback_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            contact = st.text_input("联系方式 / 微信 / 手机", placeholder="方便回访时填写,可留空")
            feedback_page = st.selectbox("问题页面", [
                "首页/功能说明", "注册/登录/内测邀请码", "骑手档案", "上传分析", "功率仪表盘",
                "训练负荷", "训练反馈", "恢复与睡眠", "AI 功率分析", "训练课表/ZWO",
                "营养与补给", "目标追踪", "套餐/权限", "手机端显示", "其他"
            ])
        with c2:
            issue_type = st.selectbox("反馈类型", ["Bug/报错", "看不懂/需要解释", "数据不符合预期", "体验建议", "功能建议", "视觉/手机端", "其他"])
            severity = st.selectbox("影响程度", ["一般建议", "影响理解", "影响使用", "阻塞无法继续"])

        description = st.text_area("问题描述", height=120, placeholder="请描述你看到的问题,或者希望改进的地方。")
        steps = st.text_area("操作步骤 / 复现方式", height=100, placeholder="例如:登录 → 上传 FIT → 进入训练负荷 → 点击合并历史 → 出现......")
        st.markdown("#### 快速三问(可选,但很重要)")
        favorite_feature = st.text_area("1. 你最喜欢 TrueCadence 的哪个功能?为什么?", height=80, placeholder="例如:AI 功率分析,因为能直接看懂自己哪里弱。")
        disliked_feature = st.text_area("2. 你最不喜欢、最想吐槽的地方是什么?", height=80, placeholder="例如:某个页面看不懂 / 手机端不好点 / 上传流程不顺。")
        paid_feature = st.text_area("3. 如果以后付费,你觉得哪个功能最值得付费?多少钱能接受?", height=80, placeholder="例如:训练课表 / Intervals 导入 / AI 分析;月付 XX 元或年付 XX 元。")
        expected = st.text_area("你期望它怎么表现", height=80, placeholder="例如:希望显示更明确的解释 / 希望按钮位置更明显 / 希望能导出......")
        allow_contact = st.checkbox("允许后续联系我确认细节", value=True)
        submitted = st.form_submit_button("提交内测反馈", use_container_width=True)

    if submitted:
        if not any(x.strip() for x in [description, steps, expected, favorite_feature, disliked_feature, paid_feature]):
            st.error("请至少填写一段问题描述、操作步骤、期望改进,或回答快速三问。")
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
                "favorite_feature": favorite_feature.strip(),
                "disliked_feature": disliked_feature.strip(),
                "paid_feature": paid_feature.strip(),
                "allow_contact": bool(allow_contact),
            }
            try:
                data = load_beta_feedback()
                data.insert(0, item)
                save_beta_feedback(data)
                st.success("已收到,感谢。这个反馈会进入内测问题记录。")
            except Exception as e:
                st.error(f"保存失败:{e}")

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
                "描述": (x.get("description", "") or x.get("favorite_feature", "") or x.get("expected", ""))[:80],
            })
        st.dataframe(pd.DataFrame(show).astype(str), use_container_width=True, hide_index=True)


elif page == "🛠️ 管理后台":
    st.title("🛠️ 管理后台")
    st.caption("仅管理员可见:订单确认、订单清理和内测反馈查看。")
    if not is_admin_user:
        st.error("当前账号没有管理员权限。")
        st.stop()

    if user.get("is_admin") or user.get("role") in ("admin", "super_admin"):
        st.divider()
        st.subheader("🛠️ 管理员")
        admin_tab_feedback, admin_tab_orders = st.tabs(["内测反馈", "订单确认"])

        with admin_tab_orders:
            orders = load_orders()
            order_rows = sorted(orders.values(), key=lambda o: o.get("created_at", ""), reverse=True)
            if not order_rows:
                st.info("暂无订单。")
            else:
                status_map = {"pending":"待支付", "paid":"已支付", "cancelled":"已取消", "refunded":"已退款", "expired":"已过期"}
                table_rows = []
                for o in order_rows[:100]:
                    table_rows.append({
                        "订单号": o.get("order_id"),
                        "用户": o.get("phone") or o.get("user_id"),
                        "套餐": o.get("plan_name"),
                        "周期": o.get("duration_label"),
                        "金额": f"¥{float(o.get('amount', 0)):.0f}",
                        "状态": status_map.get(o.get("status"), o.get("status")),
                        "创建时间": o.get("created_at", "")[:19].replace("T", " "),
                        "确认时间": (o.get("confirmed_at") or "")[:19].replace("T", " ") or "-",
                        "到期": o.get("expires_at_after_paid") or "-",
                    })
                st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
                selected_order_id = st.selectbox(
                    "选择订单",
                    [o["order_id"] for o in order_rows],
                    format_func=lambda oid: next((f"{x['order_id']}|{x.get('phone','')}|{x.get('plan_name','')}|¥{float(x.get('amount',0)):.0f}|{status_map.get(x.get('status'), x.get('status'))}" for x in order_rows if x["order_id"] == oid), oid),
                    key="admin_order_select",
                )
                selected_order = next((o for o in order_rows if o.get("order_id") == selected_order_id), {})
                col_ok, col_cancel = st.columns(2)
                if col_ok.button("确认已收款并开通", type="primary", use_container_width=True, disabled=selected_order.get("status") != "pending"):
                    ok, msg = confirm_order_paid(selected_order_id, user.get("user_id", "admin"))
                    if ok:
                        if selected_order_id == st.session_state.get("latest_order_id"):
                            st.session_state.pop("latest_order_id", None)
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                if col_cancel.button("取消订单", use_container_width=True, disabled=selected_order.get("status") != "pending"):
                    ok, msg = update_order_status(selected_order_id, "cancelled", user.get("user_id", "admin"))
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                st.caption("用户侧可自行删除/隐藏订单记录;管理员后台保留订单记录用于核对付款、售后和审计。")

        with admin_tab_feedback:
            st.subheader("全部内测反馈")
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
                    show_cols = ["created_at", "page", "type", "severity", "contact", "plan", "rider", "description", "favorite_feature", "disliked_feature", "paid_feature", "steps", "expected", "allow_contact", "user_id"]
                    for col in show_cols:
                        if col not in filtered.columns:
                            filtered[col] = ""
                    rename = {
                        "created_at": "时间", "page": "页面", "type": "类型", "severity": "影响", "contact": "联系方式",
                        "plan": "套餐", "rider": "骑手", "description": "描述", "favorite_feature": "最喜欢", "disliked_feature": "最讨厌", "paid_feature": "付费意愿", "steps": "步骤", "expected": "期望",
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
    **{row.get('created_at','')}|{row.get('page','')}|{row.get('type','')}|{row.get('severity','')}**
    用户:`{row.get('user_id','')}`|套餐:{row.get('plan','')}|联系方式:{row.get('contact','') or '-'}
    描述:{row.get('description','') or '-'}
    最喜欢:{row.get('favorite_feature','') or '-'}
    最讨厌:{row.get('disliked_feature','') or '-'}
    付费意愿:{row.get('paid_feature','') or '-'}
    步骤:{row.get('steps','') or '-'}
    期望:{row.get('expected','') or '-'}
    ---
    """)

elif page == "💎 套餐对比":
    st.title("💎 套餐与升级路径")
    st.caption("先免费看懂数据,再用 Core 开始系统训练;如果你有比赛和提升目标,Pro 会把训练、恢复、营养和目标追踪连成闭环。")

    current_plan = st.session_state.user.get("plan", "free")

    render_pricing_intro()

    import html as _html
    plan_from_url = st.query_params.get("plan")
    if isinstance(plan_from_url, list):
        plan_from_url = plan_from_url[0] if plan_from_url else None
    if plan_from_url in ("core", "pro", "coach"):
        st.session_state["selected_paid_plan"] = plan_from_url
        if st.session_state.get("last_plan_from_url") != plan_from_url:
            st.session_state["force_plan_sku"] = plan_from_url
            st.session_state["last_plan_from_url"] = plan_from_url

    plans_data = [
        ("free", "免费版", "¥0", "适合:先试试看,了解自己数据", "结果:看懂基础功率数据,不再只看平均速度", ["上传 FIT 文件,查看基础功率分析", "基础 PMC 训练负荷曲线", "最近训练概览", "AI 点评每月 8 次"]),
        ("core", "Core版", "¥19/月 · ¥169/年", "适合:想开始系统训练的骑友", "结果:每周拿到可执行训练课表", ["AI 训练分析每月 30 次", "自动生成训练课表,导出 .ZWO 文件", "功率仪表盘与疲劳抗性分析", "训练负荷 PMC 曲线"]),
        ("pro", "Pro版", "¥49/月 · ¥449/年", "适合:有比赛、FTP 或体重管理目标", "结果:训练、恢复、营养、目标完整闭环", ["包含 Core 全部功能", "营养补给建议与比赛日策略", "恢复监督与睡眠优化", "目标追踪与周期化训练计划", "AI 动态分析无限次数"]),
        ("coach", "Coach版", "¥149/月 · ¥1349/年", "适合:教练、工作室或管理多位骑手", "结果:最多 20 位骑手档案、批量分析和长期跟踪", ["最多 20 位骑手管理", "AI 辅助教练分析与批量生成课表", "骑手分组与恢复监控", "包含 Pro 全部功能"]),
    ]
    icons = {"free":"🟦", "core":"🔥", "pro":"🏆", "coach":"👥"}
    colors = {"free":"var(--tc-subtle)", "core":"#ff6b35", "pro":"#f0c040", "coach":"#f85149"}
    bgs = {
        "free":"linear-gradient(180deg, rgba(139,148,158,0.10), var(--tc-surface))",
        "core":"linear-gradient(180deg, rgba(255,107,53,0.13), var(--tc-surface))",
        "pro":"linear-gradient(180deg, rgba(240,192,64,0.10), var(--tc-surface))",
        "coach":"linear-gradient(180deg, rgba(248,81,73,0.10), var(--tc-surface))",
    }
    card_cols = st.columns(4)
    for idx, (plan_key, name, price, fit, result, features) in enumerate(plans_data):
        with card_cols[idx]:
            color = colors[plan_key]
            version_tags = {"free":"体验", "core":"入门训练", "pro":"完整闭环", "coach":"多骑手"}
            with st.container(border=True):
                st.markdown('<div style="height:5px;border-radius:999px;background:rgba(255,255,255,0.05);margin:-.35em 0 .55em 0;"></div>', unsafe_allow_html=True)
                badge_lines = []
                if plan_key == current_plan:
                    badge_lines.append('<span class="plan-badge" style="margin-top:0;">当前套餐</span>')
                if st.session_state.get("selected_paid_plan") == plan_key:
                    badge_lines.append('<span class="plan-badge" style="background:#ff6b35;margin-top:.28em;">已选</span>')
                right_badges = '<div style="position:absolute;right:.85em;top:.75em;display:flex;flex-direction:column;align-items:flex-end;gap:.18em;white-space:nowrap;">' + ''.join(badge_lines) + '</div>' if badge_lines else ''
                st.markdown('<div style="position:relative;min-height:2.45em;margin-bottom:.2em;"><div style="color:' + color + ';font-size:.68em;font-weight:850;letter-spacing:.08em;padding-right:5.4em;">' + version_tags.get(plan_key, '') + '</div>' + right_badges + '</div>', unsafe_allow_html=True)
                if plan_key == "core":
                    st.markdown('<div style="height:34px;display:flex;align-items:flex-start;"><span class="plan-rec">🔥 推荐</span></div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div style="height:34px;display:flex;align-items:flex-start;"><span class="plan-rec" style="visibility:hidden;">占位</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="plan-name" style="color:{color};">{icons[plan_key]} {_html.escape(name)}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="plan-price">{_html.escape(price)}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="plan-fit">{_html.escape(fit)}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="plan-result">{_html.escape(result)}</div>', unsafe_allow_html=True)
                st.markdown('<div style="color:var(--tc-subtle);font-size:0.76em;font-weight:700;margin-bottom:0.35em;">包含</div>', unsafe_allow_html=True)
                feature_lines = list(features)[:5]
                while len(feature_lines) < 5:
                    feature_lines.append('')
                for f in feature_lines:
                    if f:
                        st.markdown('<div class="plan-feature">✦ ' + _html.escape(f) + '</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="plan-feature">&nbsp;</div>', unsafe_allow_html=True)
                st.markdown('<div style="height:.35em"></div>', unsafe_allow_html=True)
                if plan_key == "free":
                    st.button("免费体验", key="choose_card_free", disabled=True, use_container_width=True)
                else:
                    btn_type = "primary" if st.session_state.get("selected_paid_plan") == plan_key else "secondary"
                    if st.button(f"选择 {name}", key=f"choose_card_{plan_key}", type=btn_type, use_container_width=True):
                        st.session_state["selected_paid_plan"] = plan_key
                        st.session_state["buy_sku"] = (plan_key, "月付", PLANS[plan_key]["durations"]["月付"]["price"], PLANS[plan_key]["durations"]["月付"]["days"])
                        st.rerun()
    render_upgrade_note()

    st.subheader("开通 / 续费")
    selected_plan_for_order = st.session_state.get("selected_paid_plan") if st.session_state.get("selected_paid_plan") in ("core", "pro", "coach") else "core"

    sku_options = []
    for duration_label, duration in PLANS[selected_plan_for_order]["durations"].items():
        sku_options.append((selected_plan_for_order, duration_label, duration["price"], duration["days"]))

    default_index = next((i for i, x in enumerate(sku_options) if x[1] == "月付"), 0)
    current_sku = st.session_state.get("buy_sku")
    if current_sku not in sku_options:
        st.session_state["buy_sku"] = sku_options[default_index]

    selected_sku = st.radio(
        "选择付费周期",
        sku_options,
        format_func=lambda x: f"{PLANS[x[0]]['name']} · {x[1]} · ¥{x[2]} · {x[3]}天",
        key="buy_sku",
    )
    buy_plan, buy_duration, amount, days = selected_sku
    pay_method = st.selectbox(
        "支付方式",
        ["manual_wechat", "manual_alipay"],
        format_func=lambda x: "微信人工收款" if x == "manual_wechat" else "支付宝人工收款",
        key="buy_pay_method",
    )

    st.caption(f"将生成待支付订单:{PLANS[buy_plan]['name']} · {buy_duration} · ¥{amount} · {days}天")
    if st.button("生成开通订单", type="primary", use_container_width=True):
        checked = PLANS.get(buy_plan, {}).get("durations", {}).get(buy_duration)
        if not checked or checked.get("price") != amount or checked.get("days") != days:
            st.error("套餐价格校验失败,请刷新页面后重试。")
            st.stop()
        ok, msg, order = create_order(user["user_id"], buy_plan, buy_duration, pay_method)
        if ok:
            st.session_state["latest_order_id"] = msg
            st.success(f"订单已生成:{msg}")
            st.rerun()
        else:
            st.error(msg)

    latest_order_id = st.session_state.get("latest_order_id")
    orders = get_user_orders(user["user_id"])
    if latest_order_id:
        latest = next((o for o in orders if o.get("order_id") == latest_order_id), None)
        if latest:
            pay_label = "微信" if latest.get("payment_method") == "manual_wechat" else "支付宝"
            qr_path = PAYMENT_WECHAT_QR_PATH if latest.get("payment_method") == "manual_wechat" else PAYMENT_ALIPAY_QR_PATH
            st.markdown("### 待支付订单")
            p1, p2 = st.columns([1.05, 1])
            with p1:
                st.info(
                    f"订单号:{latest['order_id']}\n\n"
                    f"套餐:{latest['plan_name']} · {latest['duration_label']}\n\n"
                    f"金额:¥{float(latest['amount']):.0f}\n\n"
                    f"支付方式:{pay_label}\n\n"
                    f"付款备注请填写:{latest['order_id']} 或注册手机号"
                )
                st.code(latest["order_id"], language=None)
                st.caption("内测阶段采用人工确认收款。付款后管理员会在后台确认并开通套餐;如长时间未开通,可在「内测反馈」里提交订单号。")
            with p2:
                if qr_path.exists():
                    st.image(str(qr_path), caption=f"{pay_label}收款码|请支付 ¥{float(latest['amount']):.0f}", width=280)
                else:
                    st.warning(f"未找到{pay_label}收款码图片,请联系管理员人工付款。")
    if orders:
        st.subheader("我的订单")
        status_map = {"pending":"待支付", "paid":"已支付", "cancelled":"已取消", "refunded":"已退款", "expired":"已过期"}
        rows = []
        for o in orders[:10]:
            rows.append({
                "订单号": o.get("order_id"),
                "套餐": o.get("plan_name"),
                "周期": o.get("duration_label"),
                "金额": f"¥{float(o.get('amount', 0)):.0f}",
                "状态": status_map.get(o.get("status"), o.get("status")),
                "创建时间": o.get("created_at", "")[:19].replace("T", " "),
                "开通后到期": o.get("expires_at_after_paid") or "-",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        deletable_orders = [o for o in orders if o.get("status") in ("pending", "cancelled", "paid", "expired", "refunded")]
        if deletable_orders:
            with st.expander("删除我的订单记录", expanded=False):
                del_order_id = st.selectbox(
                    "选择要从列表移除的订单",
                    [o["order_id"] for o in deletable_orders],
                    format_func=lambda oid: next((f"{x['order_id']}|{x.get('plan_name','')}|{status_map.get(x.get('status'), x.get('status'))}" for x in deletable_orders if x["order_id"] == oid), oid),
                    key="user_hide_order_select",
                )
                st.caption("删除后只是不在你的订单列表显示;后台仍会保留必要记录,方便核对付款和售后。待支付订单会同时标记为已取消。")
                confirm_user_hide = st.checkbox(f"确认删除我的订单记录 {del_order_id}", key="confirm_user_hide_order")
                if st.button("删除我的订单记录", disabled=not confirm_user_hide, use_container_width=True):
                    ok, msg = hide_order_for_user(del_order_id, user["user_id"])
                    if ok:
                        if del_order_id == st.session_state.get("latest_order_id"):
                            st.session_state.pop("latest_order_id", None)
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

elif page == "📝 训练反馈":
    st.title("📝 训练反馈")
    st.caption("记录睡眠、疲劳、疼痛、不适和训练后感受。后续 AI 分析会结合这些主观信息,判断是否该降强度、恢复或调整课表。")

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
    <b>为什么要记录:</b>功率只能告诉你做了多少,反馈能告诉你身体承受得怎么样。感冒、睡眠差、腿沉、膝盖痛、补给不足,都会影响今天该不该继续上强度。
</div>
""", unsafe_allow_html=True)

    feedback = load_feedback()
    profile = load_profile()
    cycle_enabled_for_feedback = bool(profile.get('cycle_enabled')) or profile.get('gender') == '女'

    with st.form("feedback_form"):
        st.markdown('<div class="feedback-section">今日状态</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        fb_date = c1.date_input("日期", value=datetime.date.today())
        sleep_quality = c2.slider("睡眠质量", 1, 5, 3, help="1=很差,5=很好")
        energy = c3.slider("精神状态", 1, 5, 3, help="1=很差,5=很好")
        c4, c5, c6 = st.columns(3)
        leg_fatigue = c4.slider("腿部疲劳", 1, 5, 3, help="1=很轻松,5=很沉很累")
        stress = c5.slider("生活/工作压力", 1, 5, 3)
        morning_hr = c6.number_input("晨脉/静息心率", 0, 160, 0, help="可选")

        st.markdown('<div class="feedback-section">训练后反馈</div>', unsafe_allow_html=True)
        c7, c8, c9 = st.columns(3)
        rpe = c7.slider("RPE 主观强度", 1, 10, 5, help="1=非常轻松,10=极限")
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
            cycle_status = fc1.selectbox("今日周期状态", ["不记录", "经期第1-2天", "经期第3-5天", "经期后恢复期", "排卵期附近", "经前期/PMS", "周期正常,无明显影响"], key="fb_cycle_status")
            cycle_pain = fc2.selectbox("腹痛/腰酸", ["无", "轻", "中", "重"], key="fb_cycle_pain")
            cycle_flow = fc3.selectbox("出血量", ["不记录", "少", "中", "多"], key="fb_cycle_flow")
            fc4, fc5 = st.columns(2)
            cycle_mood = fc4.selectbox("情绪波动", ["不记录", "低", "中", "高"], key="fb_cycle_mood")
            cycle_training_impact = fc5.selectbox("是否影响训练", ["不记录", "不影响", "轻微", "明显"], key="fb_cycle_training_impact")

        notes = st.text_area("备注", placeholder="例如:今天鼻塞,没做完间歇;右膝外侧痛;补给没吃够后半程掉功率。")

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
        st.session_state["feedback_saved_notice"] = f"✅ {entry['date']} 训练反馈已保存,AI 功率分析会自动纳入这条反馈"
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

        with st.expander("🗑️ 删除训练反馈数据", expanded=bool(st.session_state.get("feedback_delete_area_open", False))):
            feedback_options = []
            for idx, item in enumerate(feedback):
                label = f"{item.get('date', '-')}|睡眠{item.get('sleep_quality', '-')}|腿疲劳{item.get('leg_fatigue', '-')}|RPE{item.get('rpe', '-')}|{item.get('completion', '-')}"
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
                    st.session_state["feedback_delete_area_open"] = bool(feedback)
                    st.rerun()
            st.session_state["feedback_delete_area_open"] = True
            confirm_clear_feedback = fc2.checkbox("确认清空全部", key="confirm_clear_feedback")
            if fc2.button("清空全部训练反馈", key="clear_feedback_all", use_container_width=True, disabled=not confirm_clear_feedback):
                save_feedback([])
                st.session_state.pop("ai_diagnosis", None)
                st.session_state.pop("ai_signature", None)
                st.success("已清空当前骑手全部训练反馈。")
                st.session_state["feedback_delete_area_open"] = False
                st.rerun()
    else:
        st.info("还没有训练反馈。建议每次关键训练后记录一次,尤其是强度课、长距离、感冒/睡眠差/疼痛时。")

elif page == "📤 上传分析":
    st.title("📤 上传分析")
    st.caption("上传码表、骑行台或训练平台导出的 FIT 文件,系统会自动解析功率、心率和训练负荷。")

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

    st.markdown("""
<div class="upload-cta-note">
    <b>👇 从这里开始:</b>点击下方按钮选择 FIT 文件,或直接把 FIT 文件拖到上传框里。一次最多 28 个,单次总大小最多 50MB;网络不稳定或使用代理时,建议每批 5-10 个 FIT,更稳。
</div>
""", unsafe_allow_html=True)

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

        st.markdown(f"""
<div class="upload-next">
    <div class="title">下一步建议</div>
    <div class="text">
        这 {len(new_rides)} 条新解析数据已经并入历史。建议先看 <b>📊 功率仪表盘</b> 理解当前能力结构,
        再进入 <b>🧠 AI 功率分析</b> 获取训练判断;如果你已解锁 Core,可继续生成 <b>📋 训练课表</b>。
    </div>
</div>
""", unsafe_allow_html=True)
    else:
        st.warning("未找到有效骑行数据。请确认文件为 .fit 格式,并包含骑行记录;如果没有功率数据,部分分析会受限。")

elif page == "🔗 数据导入":
    st.title("🔗 数据导入")
    st.caption("从训练平台或文件导入骑行数据。当前已支持 Intervals.icu 手动导入;Strava / Garmin 授权导入后续接入。")

    import_source = st.selectbox("选择导入来源", ["Intervals.icu", "Strava(正在申请中...)"], key="data_import_source")

    if import_source == "Intervals.icu":
        st.markdown("""
<div class="upload-cta-note">
<b>Intervals.icu 外部入口:</b>当前为内测临时手动导入方式。如果你还没打开 Intervals.icu,请先登录并进入设置页复制 Athlete ID 与 Personal API Key,然后回到本页导入。正式多用户版本会优先改为 OAuth 授权,不长期要求用户手动填写 API Key。
</div>
""", unsafe_allow_html=True)
        icu_jump_1, icu_jump_2 = st.columns([1, 1])
        with icu_jump_1:
            st.link_button("打开 Intervals.icu", "https://intervals.icu/", type="primary", use_container_width=True)
        with icu_jump_2:
            st.link_button("打开 Intervals 设置", "https://intervals.icu/settings", type="primary", use_container_width=True)

    if import_source == "Strava(正在申请中...)":
        st.markdown("""
<div class="upload-cta-note">
<b>Strava 外部入口:</b>Strava OAuth 正在申请接入。当前可先打开 Strava 导出 FIT,再回到 TrueCadence 的 FIT 上传页面分析。
</div>
""", unsafe_allow_html=True)
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
    st.markdown("""
<div class="upload-cta-note">
<b>Intervals.icu 外部入口：</b>现在支持一键 OAuth 授权导入，点击下方按钮授权后即可自动导入活动，不再需要手动填写 API Key。
</div>
""", unsafe_allow_html=True)

    # ─── OAuth connect / disconnect ───
    from intervals_oauth import get_token, is_connected, get_authorize_url, disconnect_user
    user_id_oauth = st.session_state.get("user", {}).get("user_id", "")
    oauth_token = get_token(user_id_oauth) if user_id_oauth else None
    oauth_connected = bool(oauth_token)

    if oauth_connected:
        st.success("✅ 已连接 Intervals.icu（OAuth 授权）")
        if st.button("断开 Intervals.icu 连接", key="intervals_oauth_disconnect", use_container_width=True):
            disconnect_user(user_id_oauth)
            st.success("已断开 Intervals.icu 连接。")
            st.rerun()
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
                st.rerun()
            else:
                st.session_state.pop("intervals_import_busy", None)
                st.session_state.pop("intervals_pending_ids", None)
                if failures:
                    st.error("导入失败:无法下载 FIT,也无法生成活动摘要。请确认这些活动在 Intervals 中有日期、时长、距离或训练负荷等摘要字段。")
                else:
                    st.error("导入失败:没有生成有效活动。")

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
    <div class="main">这些信息会直接影响 <b>FTP、功体比、训练区间、营养建议和 AI 分析</b>。建议优先填写:<b>体重、实测 FTP、最大心率、训练目标</b>。</div>
</div>
<div class="profile-note">
    <b>为什么要填:</b>体重决定 W/kg 和营养建议;FTP 决定功率区间、AI 分析和训练课表;心率用于判断强度反应和恢复压力;训练目标会影响后续建议方向。
</div>
""", unsafe_allow_html=True)

    profile = load_profile()

    tab0, tab1, tab2 = st.tabs(["骑手管理", "基础档案", "Fitting 设定"])

    with tab0:
        user = st.session_state.get("user", {})
        riders = list(user.get("riders", {}).keys())
        active_rider = st.session_state.get("rider", riders[0] if riders else "默认骑手")
        try:
            history_count = len(load_rider_rides(user.get("user_id"), active_rider)) if user else 0
        except Exception:
            history_count = 0

        st.markdown('<div class="profile-section-title">当前骑手</div>', unsafe_allow_html=True)
        c0a, c0b, c0c = st.columns(3)
        c0a.metric("当前骑手", active_rider)
        c0b.metric("骑手数量", f"{len(riders)}/{plan_info['riders']}")
        c0c.metric("训练存档", f"{history_count} 条")

        if len(riders) > 1:
            selected_profile_rider = st.selectbox("切换当前骑手", riders, index=riders.index(active_rider) if active_rider in riders else 0, key="profile_rider_select")
            if selected_profile_rider != st.session_state.get("rider"):
                st.session_state.rider = selected_profile_rider
                st.cache_data.clear()
                st.rerun()
        else:
            st.info("当前只有一个骑手档案。Coach 版可管理多个骑手。")

        st.markdown('<div class="profile-section-title">添加骑手</div>', unsafe_allow_html=True)
        add_col, add_btn_col = st.columns([2, 1], vertical_alignment="bottom")
        new_name = add_col.text_input("新骑手名称", placeholder="例如:客户007 / 张三 / 默认骑手2", key="profile_new_rider_name")
        if add_btn_col.button("添加骑手", key="profile_add_rider_btn", use_container_width=True):
            if new_name.strip():
                ok, msg = add_rider(user["user_id"], new_name.strip())
                if ok:
                    users = load_users()
                    st.session_state.user = {"user_id": user["user_id"], **users[user["user_id"]]}
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.error("请输入骑手名称")

        if len(riders) > 1:
            st.markdown('<div class="profile-section-title">删除骑手</div>', unsafe_allow_html=True)
            st.caption("只能删除非当前骑手。删除前请确认该骑手的数据不再需要。")
            del_options = [r for r in riders if r != active_rider]
            del_col, del_btn_col = st.columns([2, 1], vertical_alignment="bottom")
            del_name = del_col.selectbox("选择要删除的骑手", ["-- 选择 --"] + del_options, key="profile_del_rider")
            if del_btn_col.button("删除", key="profile_del_rider_btn", use_container_width=True):
                if del_name != "-- 选择 --":
                    ok, msg = delete_rider(user["user_id"], del_name)
                    if ok:
                        users = load_users()
                        st.session_state.user = {"user_id": user["user_id"], **users[user["user_id"]]}
                        st.session_state.rider = users[user["user_id"]].get("active_rider", riders[0])
                        st.success(msg)
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("请选择要删除的骑手")

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
            st.markdown('<div class="profile-help">可选填写。只用于训练恢复和补给建议,不作为医学判断。</div>', unsafe_allow_html=True)
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
        ftp_test = c3.number_input("实测 FTP W", 0, 600, value=profile.get('ftp_test') if profile.get('ftp_test') else 0, key="ftp_input", help="如果不填,系统会根据 FIT 数据自动估算")
        max_hr = c4.number_input("最大心率", 0, 250, value=profile.get('max_hr') if profile.get('max_hr') else 0)
        rest_hr = c3.number_input("静息心率", 0, 120, value=profile.get('rest_hr') if profile.get('rest_hr') else 0)
        lthr = c4.number_input("乳酸阈值心率 LTHR", 0, 230, value=profile.get('lthr') if profile.get('lthr') else 0, help="可选。若做过阈值测试或知道骑行乳酸阈值心率,填写后可用 LTHR 划分心率区间。")
        hr_zone_method = c3.selectbox("心率区间算法", ["按最大心率", "按乳酸阈值心率 LTHR"], index=1 if profile.get('hr_zone_method') == "按乳酸阈值心率 LTHR" else 0, help="LTHR 通常更适合训练区间;没有 LTHR 时先用最大心率。")
        bike_type = c4.selectbox("主要车种", ["公路车", "山地车", "铁三车", "砾石车", "折叠车", "其他"], index=["公路车", "山地车", "铁三车", "砾石车", "折叠车", "其他"].index(profile.get('bike_type', '公路车')) if profile.get('bike_type', '公路车') in ["公路车", "山地车", "铁三车", "砾石车", "折叠车", "其他"] else 0)

        zone_rows = hr_zones_by_lthr(lthr) if hr_zone_method == "按乳酸阈值心率 LTHR" and lthr else hr_zones_by_max(max_hr)
        if zone_rows:
            st.markdown('<div class="profile-section-title">心率区间预览</div>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(zone_rows), use_container_width=True, hide_index=True)
            st.caption("心率区间用于训练强度解释,不作为医学判断;高温、疲劳、咖啡因、睡眠和补给都会影响心率反应。")
        else:
            st.info("填写最大心率或乳酸阈值心率后,会在这里显示心率区间。")

        st.markdown('<div class="profile-section-title">目标信息</div>', unsafe_allow_html=True)
        st.markdown('<div class="profile-help">训练目标越清楚,AI 建议和课表方向越容易对准。</div>', unsafe_allow_html=True)
        goal = st.text_input("训练目标", value=profile.get('goal') or '', placeholder="例如:提升 FTP、备战绕圈赛、减脂、恢复体能")
        notes = st.text_area("备注", value=profile.get('notes') or '', placeholder="可记录伤病、可训练时间、比赛日期、器材情况等")

        save_col, clear_col = st.columns([3, 1])
        if save_col.button("💾 保存骑手档案", type="primary", use_container_width=True):
            basics = dict(name=name, age=age, gender=gender, weight=weight, height=height,
                         exp_years=exp_years, ftp_test=ftp_test, max_hr=max_hr, rest_hr=rest_hr,
                         lthr=lthr, hr_zone_method=hr_zone_method,
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
                     "lthr": 0, "hr_zone_method": "按最大心率",
                     "bike_type": "公路车", "goal": "", "notes": "", "cycle_enabled": False, "cycle_last_start": "", "cycle_length": 28, "period_days": 5, "cycle_sensitivity": "正常"}
            if user:
                existing = load_rider_profile(user["user_id"], rider)
                for k in empty:
                    existing[k] = empty[k]
                save_rider_profile(user["user_id"], rider, existing)
            st.cache_data.clear()
            st.rerun()
        st.markdown('<div class="danger-note">清空只影响当前骑手档案,不会删除 FIT 骑行记录。</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="profile-section-title">Fitting 设定记录</div>', unsafe_allow_html=True)
        st.markdown('<div class="profile-help">用于记录人车设定,后续可辅助判断姿势变化、舒适性和输出表现。这里不是医学诊断,只是长期跟踪档案。</div>', unsafe_allow_html=True)
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
        st.markdown('<div class="danger-note">清空只影响当前骑手的 Fitting 设定,不会删除基础档案和骑行记录。</div>', unsafe_allow_html=True)

elif page == "📊 功率仪表盘":
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

    # Top metrics - uniform cards
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    wkg = round(ftp/pweight, 1)
    col1.metric("FTP", f"{ftp}W", f"{wkg} W/kg")
    s5_wkg = round(best['5s']/pweight, 1) if best['5s'] and pweight else ""
    col2.metric("5s 冲刺", f"{best['5s']}W", f"{s5_wkg} W/kg" if s5_wkg else "")
    p20 = best.get('20min', 0)
    col3.metric("20min 功率", f"{p20}W", f"{round(p20/ftp*100)}% FTP" if ftp and p20 else "")
    p40 = best.get('40min', 0)
    col4.metric("40min 功率", f"{p40}W", f"{round(p40/ftp*100)}% FTP" if ftp and p40 else "")
    p60 = best.get('60min', 0)
    col5.metric("60min 功率", f"{p60}W", f"{round(p60/ftp*100)}% FTP" if ftp and p60 else "")
    col6.metric("总骑行次数", len(rides), f"{len(rides)} 条记录")

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
        st.subheader("⚡ 功率画像 - 固定参考线 / 同水平分位数")
        if any(v.get('rating_source') == 'peer_percentile' for v in fatigue.values()):
            st.caption("当前评级优先采用同 FTP W/kg 水平用户分位数;固定参考线保留为解释和兜底。")
        else:
            st.caption(f"当前同水平样本量不足({len(peer_samples)}/{POWER_PROFILE_MIN_PEER_SAMPLES}),评级暂用 TrueCadence 内测固定参考线;样本积累后会自动切换为同水平用户分位数。")
        profile_rows = power_profile_rating_rows(fatigue)
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
                render_mini_metric_card("后程可分析骑行", f"{durability_summary['count']} 条", f"总记录 {len(rides)} 条")
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

elif page == "📈 训练负荷":
    st.title("📈 训练负荷")
    st.caption("判断最近练得是太少、刚好,还是太猛。")

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
    <div class="load-card"><div class="k">主观反馈</div><div class="v">{len(recent_feedback)} 条</div><div class="d">睡眠 {avg_sleep or '-'} / 腿疲劳 {avg_fatigue or '-'}</div></div>
    <div class="load-card"><div class="k">TSB 阈值</div><div class="v">{thresholds['tsb_caution']} / {thresholds['tsb_red']}</div><div class="d">黄色 / 红色提醒线</div></div>
    <div class="load-card"><div class="k">ATL-CTL 阈值</div><div class="v">+{thresholds['atl_caution']} / +{thresholds['atl_red']}</div><div class="d">黄色 / 红色提醒线</div></div>
    <div class="load-card"><div class="k">主观疲劳阈值</div><div class="v">{thresholds['fatigue_caution']} / {thresholds['fatigue_red']}</div><div class="d">黄色 / 红色提醒线</div></div>
</div>
""", unsafe_allow_html=True)

    c1, c2 = st.columns([1.05, 1])
    if stale_notes:
        st.info(";".join(stale_notes))

    with c1:
        st.subheader("接下来怎么练")
        for item in action_items:
            st.markdown(f"- {item}")
        st.markdown("""
<div class="load-panel">
    <div class="load-panel-title">怎么理解 CTL / ATL / TSB</div>
    <div class="load-panel-text">
        <b>CTL</b> 是长期训练积累,代表你目前能承受多少训练;<br>
        <b>ATL</b> 是短期疲劳,最近一周练得越猛越高,休息日会按 TSS=0 自然回落,并会从最后一次骑行持续衰减到今天;<br>
        <b>TSB</b> 是当前新鲜度,太低说明疲劳压住了状态,太高则可能训练刺激不足或正在减量。<br><br>
        <b>当前 TSB 解读:</b>{tsb_zone_text(current_tsb)}<br><br>
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
        if not use_all and uploaded_rides:
            st.info("当前关闭合并历史:风险提示只用于本批上传文件排查,正式训练建议请打开合并历史数据。")
        if recent_feedback:
            st.caption("最近训练反馈已接入负荷判断。")
        else:
            st.info("还没有训练反馈。去「📝 训练反馈」记录后,负荷判断会更贴近真实状态。")

    st.subheader("PMC 曲线")
    st.plotly_chart(plot_pmc(rides), use_container_width=True)
    st.caption("蓝线=体能 CTL · 橙线=疲劳 ATL · 柱状=状态 TSB。TSB 不是越高越好,关键看是否匹配训练阶段。")

    with st.expander("查看训练记录明细", expanded=False):
        show_cols = [c for c in ['date', 'duration_h', 'avg_power', 'normalized_power', 'tss'] if c in df_pmc.columns]
        if show_cols:
            st.dataframe(df_pmc[show_cols].tail(30).astype(str), use_container_width=True, hide_index=True)
        else:
            st.info("当前记录缺少可展示字段。")

elif page == "🧠 AI 功率分析":
    st.title("🧠 AI 功率分析")
    st.caption("把骑行数据转成训练判断:当前强弱项、该练什么、什么时候该恢复。")

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
    st.caption(f"已接入训练反馈:最近记录 {feedback_summary.get('count', 0)} 条" + (f"|最新 {feedback_latest}" if feedback_latest else "|暂无反馈"))
    st.caption(f"已接入手表睡眠:最近记录 {len(sleep_records)} 条" + (f"|最新 {sleep_latest}" if sleep_latest else "|暂无睡眠记录"))
    if feedback:
        latest_fb = feedback[0]
        fb_pains = "、".join(latest_fb.get("pains", []) or []) or "无"
        fb_specials = "、".join(latest_fb.get("specials", []) or []) or "无"
        st.success(
            f"✅ AI 已读取训练反馈:{latest_fb.get('date', '-')}|睡眠 {latest_fb.get('sleep_quality', '-')}|"
            f"腿疲劳 {latest_fb.get('leg_fatigue', '-')}|RPE {latest_fb.get('rpe', '-')}|"
            f"不适:{fb_pains}|特殊:{fb_specials}"
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
        nap_txt = f"|午睡 {latest_sleep.get('nap_minutes', 0)}min|醒后{latest_sleep.get('nap_after', '未记录')}" if latest_sleep.get('nap_minutes', 0) else ""
        st.success(
            f"✅ AI 已读取手表睡眠:{latest_sleep.get('date', '-')}|夜间睡眠 {latest_sleep.get('sleep_hours', '-')}h|"
            f"评分 {latest_sleep.get('sleep_score', '-')}|HRV {latest_sleep.get('hrv', '-')}|"
            f"静息心率 {latest_sleep.get('rest_hr', '-')}|压力 {latest_sleep.get('stress_score', '-')}|"
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
        cache_note = f"|生成时间 {cached_at}" if cached_at else ""
        st.markdown(f"""
<div class="ai-panel good">
    <div class="ai-panel-title">诊断已保留</div>
    <div class="ai-panel-text">下方结果来自当前数据范围{cache_note}。切换页面回来不会重复扣次数;{'Pro / Coach 点击重新分析也不扣次数。' if unlimited_ai else '只有点击重新分析才会重新生成并消耗 1 次额度。'}</div>
</div>
""", unsafe_allow_html=True)
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

elif page == "📋 训练课表":
    require_plan(1, "📋 训练课表")

    with st.expander("⚙️ 数据来源设置", expanded=False):
        uploaded_rides, historical, use_all, rides, source_label = select_ride_scope(
            "合并全历史数据",
            key="plan_use_all",
            help_text="通常不用改。打开后会把历史存档和本次上传一起用于估算 FTP / 功率区间。",
        )
        st.caption(f"本次上传 {len(uploaded_rides)} 条|历史存档 {len(historical)} 条|合并后 {len(merge_rides(historical, uploaded_rides))} 条")
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

    st.markdown("""
<style>
.plan-hero{padding:1.1em 1.15em;border-radius:16px;background:linear-gradient(135deg,rgba(255,107,53,.16),rgba(22,27,34,.96));border:1px solid rgba(255,107,53,.28);margin:.6em 0 1em}.plan-kicker{color:#ff9a68;font-size:.78em;font-weight:800;letter-spacing:.08em}.plan-title{color:#f0f6fc;font-size:1.45em;font-weight:850;margin:.25em 0}.plan-sub{color:#aab6c3;font-size:.9em;line-height:1.6}.plan-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.7em;margin:.8em 0 1em}.plan-card{background:var(--tc-surface);border:1px solid var(--tc-border);border-radius:13px;padding:.85em;min-height:5.6em}.plan-card .k{color:var(--tc-subtle);font-size:.72em}.plan-card .v{color:#f0f6fc;font-size:1.08em;font-weight:800;margin:.18em 0}.plan-card .d{color:var(--tc-subtle);font-size:.75em;line-height:1.35}.plan-day{background:var(--tc-surface);border:1px solid var(--tc-border);border-radius:10px;padding:.68em .66em;min-height:12em;margin:.15em 0}.plan-day .dow{color:var(--tc-subtle);font-size:.68em;font-weight:800}.plan-day .name{color:#f0f6fc;font-size:.82em;font-weight:800;margin-top:.28em;line-height:1.25}.plan-day .detail{color:var(--tc-subtle);font-size:.68em;margin-top:.35em;line-height:1.35;min-height:2.4em}.plan-pill{display:inline-block;background:var(--tc-surface-2);border-radius:5px;padding:.12em .42em;margin:.15em .16em .05em 0;font-size:.62em}.plan-warning{padding:.85em 1em;border-radius:12px;background:rgba(240,192,64,.1);border:1px solid rgba(240,192,64,.28);color:#d8c58a;font-size:.86em;line-height:1.55}@media(max-width:1050px){.plan-grid{grid-template-columns:1fr 1fr}}@media(max-width:720px){.plan-grid{grid-template-columns:1fr}}
</style>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="plan-hero">
  <div class="plan-kicker">TRAINING PLAN BUILDER</div>
  <div class="plan-title">先判断这周该怎么练,再生成可执行课表</div>
  <div class="plan-sub">根据 FIT 推算 FTP / 功体比,并结合训练负荷、睡眠/反馈、目标、可训练天数和周总量,动态生成本周重点、周期递进和 Zwift .ZWO 文件。</div>
</div>
""", unsafe_allow_html=True)

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

    c1, c2, c3 = st.columns(3)
    with c1:
        goal = st.selectbox("训练目标", PLAN_GOAL_OPTIONS)
    with c2:
        weeks = st.slider("计划周期", 1, 12, 4)
    with c3:
        hours = st.slider("每周总时长 h", 4, 20, 8)
        st.caption("新手/刚恢复建议 3–5h；有基础 5–8h；进阶 8–12h；12h+ 适合训练基础和恢复都较稳定的人。TrueCadence 不按固定死档排课，会结合训练背景、FTP可信度、恢复/疼痛反馈和比赛时间自动调整。")

    suggested_event_type = GOAL_TO_EVENT_TYPE.get(goal, "无比赛")
    if st.session_state.get("plan_last_goal_for_event_sync") != goal:
        st.session_state["plan_last_goal_for_event_sync"] = goal
        # 训练目标是课表主意图。非比赛目标必须清空比赛类型,避免阶段D倒计时污染普通训练课表。
        st.session_state["plan_event_type_v2"] = suggested_event_type

    with st.expander("🧱 训练背景与稳定推进（阶段F，可选）", expanded=False):
        bg1, bg2, bg3 = st.columns(3)
        with bg1:
            training_experience = st.selectbox("训练经验", ["未填写", "新手", "普通骑行者", "有结构化训练经验", "有比赛经验"], key="plan_training_experience_v1")
            historical_best_ftp = st.number_input("历史最佳FTP W（可选）", min_value=0, max_value=600, value=0, step=5, key="plan_historical_best_ftp_v1")
        with bg2:
            detraining_duration = st.selectbox("停训时间", ["未填写", "无停训", "2-4周", "1-3月", "3月以上", "伤病后恢复"], key="plan_detraining_duration_v1")
            historical_best_wkg = st.number_input("历史最佳W/kg（可选）", min_value=0.0, max_value=8.0, value=0.0, step=0.1, key="plan_historical_best_wkg_v1")
        with bg3:
            progression_preference = st.selectbox("训练推进偏好", ["保守", "标准", "略进阶"], index=1, key="plan_progression_preference_v1")
        st.caption("阶段F不是更难模式。它只在恢复、疼痛、FTP可信度和比赛倒计时都允许时,根据训练背景小幅调整推进速度。")

    with st.expander("🎯 比赛倒计时 / 专项设置（阶段D，可选）", expanded=False):
        ev1, ev2, ev3 = st.columns([1.2, 1.2, .8])
        with ev1:
            event_type = st.selectbox("比赛类型", EVENT_TYPE_OPTIONS, key="plan_event_type_v2")
        with ev2:
            default_event_date = datetime.date.today() + datetime.timedelta(days=28)
            event_date = st.date_input("比赛日期", value=default_event_date, key="plan_event_date_v1")
        with ev3:
            event_priority = st.selectbox("优先级", ["A", "B", "C"], index=1, help="A=主要目标;B=重要训练赛;C=普通参与", key="plan_event_priority_v1")
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

    day_order = ['周一','周二','周三','周四','周五','周六','周日']
    default_training_days = ['周二','周三','周五','周六','周日']
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
        preferred_long_day = st.selectbox(
            "长距离日",
            selected_training_days,
            index=(selected_training_days.index('周日') if '周日' in selected_training_days else len(selected_training_days)-1),
            help="长距离/Z2容量/模拟课会优先放在这一天。",
            key="plan_long_day_select_v2",
        )
    with sc3:
        no_hard_days = st.multiselect(
            "不安排高强度日",
            selected_training_days,
            default=[],
            help="这些天仍可安排 Z2、恢复、技术骑,但会尽量避开阈值、VO2、冲刺等质量课。",
            key="plan_no_hard_days_select_v2",
        )
    fixed_rest_days = [d for d in day_order if d not in selected_training_days]
    if fixed_rest_days:
        st.caption(f"实际训练日:{days} 天 | 固定休息日:" + "、".join(fixed_rest_days) + f" | 长距离优先:{preferred_long_day}")
    else:
        st.caption(f"实际训练日:7 天 | 长距离优先:{preferred_long_day}。系统仍会安排恢复/轻松日,不建议每天都高强度。")

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
    st.markdown(f"""
<div class="plan-grid">
  <div class="plan-card"><div class="k">当前阶段</div><div class="v">{pm['icon']} {pm['name']}</div><div class="d">{pm['desc']}</div></div>
  <div class="plan-card"><div class="k">功率基础</div><div class="v">FTP {ftp}W</div><div class="d">{wkg} W/kg · {weight}kg</div></div>
  <div class="plan-card"><div class="k">本周主题</div><div class="v" style="font-size:.96em;">{first['theme']}</div><div class="d">{first['theme_desc']}</div></div>
  <div class="plan-card"><div class="k">关键训练</div><div class="v" style="font-size:.96em;">{key_text}</div><div class="d">{load_note}</div></div>
</div>
""", unsafe_allow_html=True)

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
elif page == "🛌 恢复与睡眠":
    require_plan(2, "🛌 恢复与睡眠")
    st.title("🛌 恢复与睡眠")
    st.caption("把训练负荷和主观反馈合在一起,判断今天该正常训练、降强度、恢复骑,还是完全休息。")

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
    today = pd.Timestamp.today().normalize()
    today_str = today.strftime("%Y-%m-%d")
    todays_feedback = []
    stale_feedback = []
    for item in feedback:
        d = pd.to_datetime(item.get("date"), errors="coerce")
        if pd.notna(d) and d.normalize() == today:
            todays_feedback.append(item)
        elif pd.notna(d) and d.normalize() < today:
            stale_feedback.append(item)
    recent_feedback = sorted(todays_feedback, key=lambda x: (x.get("date", ""), x.get("created_at", "")), reverse=True)
    stale_feedback = sorted(stale_feedback, key=lambda x: (x.get("date", ""), x.get("created_at", "")), reverse=True)

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

    todays_sleep_records = []
    stale_sleep_records = []
    for item in sleep_records:
        d = pd.to_datetime(item.get("date"), errors="coerce")
        if pd.notna(d) and d.normalize() == today:
            todays_sleep_records.append(item)
        elif pd.notna(d) and d.normalize() < today:
            stale_sleep_records.append(item)
    recent_sleep_records = sorted(todays_sleep_records, key=lambda x: (x.get("date", ""), x.get("created_at", "")), reverse=True)
    stale_sleep_records = sorted(stale_sleep_records, key=lambda x: (x.get("date", ""), x.get("created_at", "")), reverse=True)

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
            caution_flags.append("经期前段,建议降低训练强度")
    if any(k in cycle_counts for k in ["经前期/PMS"]):
        caution_flags.append("经前期/PMS,注意睡眠、情绪和腿感波动")
    if any(k in special_counts for k in ["感冒"]):
        caution_flags.append("近期感冒/身体不适")
    if avg_sleep and avg_sleep <= 2:
        red_flags.append("睡眠质量很差")
    elif avg_sleep and avg_sleep <= 3:
        caution_flags.append("睡眠质量一般")
    if watch_sleep_hours and watch_sleep_hours < 5.5:
        red_flags.append(f"手表睡眠 {watch_sleep_hours}h,明显不足")
    elif watch_sleep_hours and watch_sleep_hours < 6.5:
        caution_flags.append(f"手表睡眠 {watch_sleep_hours}h,偏少")
    if watch_sleep_score and watch_sleep_score < 55:
        red_flags.append(f"睡眠评分 {watch_sleep_score},恢复很差")
    elif watch_sleep_score and watch_sleep_score < 70:
        caution_flags.append(f"睡眠评分 {watch_sleep_score},恢复一般")
    if watch_stress and watch_stress >= 70:
        caution_flags.append(f"手表压力 {watch_stress},自主神经压力偏高")
    if nap_records:
        if nap_sluggish_count:
            caution_flags.append("午睡后仍昏沉,下午高强度需谨慎")
        elif nap_refresh_count and 15 <= avg_nap_min <= 45 and nap_good_count:
            caution_flags.append("午睡对下午训练有小幅恢复加成,但不等同于夜间睡眠")
        elif avg_nap_min > 90:
            caution_flags.append("午睡时间较长,注意睡眠惯性和夜间睡眠节律")
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
        red_flags.append(f"TSB {tsb},深度疲劳")
    elif tsb < -10:
        caution_flags.append(f"TSB {tsb},疲劳偏高")
    if weekly_h > 12:
        caution_flags.append(f"近两周周均 {weekly_h}h,训练量偏高")

    if red_flags:
        advice_class = "recovery-red"
        advice_tag = "RED FLAG"
        advice_main = "今天建议完全休息,或只做非常轻松恢复活动"
        next_action = ["取消 VO2max、阈值、冲刺和大扭矩爬坡。", "优先睡眠、补水、正常进食;发烧/明显感染时不要训练。", "如果疼痛或症状持续,先处理身体问题,不要硬顶课表。"]
    elif caution_flags:
        advice_class = "recovery-yellow"
        advice_tag = "CAUTION"
        advice_main = "今天建议降强度:Z1-Z2 恢复骑或缩短训练"
        next_action = [f"恢复骑 30-60 分钟,功率控制在 <{round(ftp*0.55) if ftp else 90}W。", "如果必须训练,把质量课改成短 Z2,不做力竭间歇。", "今晚优先睡眠,明天根据腿感和精神再决定是否恢复强度。"]
    elif tsb > 10 and avg_energy and avg_energy >= 4:
        advice_class = "recovery-blue"
        advice_tag = "READY"
        advice_main = "状态较好,可以安排关键训练或测试"
        next_action = ["适合做阈值、VO2max、FTP测试或比赛模拟。", "热身要充分,训练后及时补碳水和蛋白。", "不要因为状态好连续多天堆高强度。"]
    else:
        advice_class = "recovery-green"
        advice_tag = "NORMAL"
        advice_main = "今天可以正常训练,但保持计划内强度"
        next_action = ["按原计划训练,不额外加码。", "强度课后记录 RPE、腿感、睡眠和疼痛。", "如果热身中感觉异常疲劳,主动降为 Z2。"]

    reasons = red_flags + caution_flags
    stale_notes = []
    if not recent_feedback and stale_feedback:
        latest_feedback_date = stale_feedback[0].get("date", "")
        stale_notes.append(f"今天({today_str})没有新的主观反馈;旧反馈最新为 {latest_feedback_date},只展示历史,不参与今天建议")
    if not recent_sleep_records and stale_sleep_records:
        latest_sleep_date = stale_sleep_records[0].get("date", "")
        stale_notes.append(f"今天({today_str})没有新的手表睡眠/午睡记录;旧记录最新为 {latest_sleep_date},只展示历史,不参与今天建议")
    if not reasons:
        reasons = ["训练负荷和今天记录没有明显红旗"]

    st.markdown(f"""
<div class="recovery-advice {advice_class}">
    <div class="tag">{advice_tag}</div>
    <div class="main">{advice_main}</div>
    <div class="why"><b>主要依据:</b>{';'.join(reasons[:6])}</div>
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
    if stale_notes:
        st.info(";".join(stale_notes))

    with c1:
        st.subheader("今天怎么做")
        for item in next_action:
            st.markdown(f"- {item}")
        if ftp:
            z1 = round(ftp * 0.55)
            z2_hi = round(ftp * 0.75)
            st.info(f"恢复/有氧参考:Z1 < **{z1}W**;Z2 约 **{z1}-{z2_hi}W**。")
        if nap_records:
            st.caption("午睡说明:午睡只作为当日训练准备度修正,不直接等同于夜间睡眠。15-45 分钟且醒后更清醒,通常对下午训练有帮助;>90 分钟或醒后更困,则要注意睡眠惯性。")
        st.subheader("恢复优先级")
        st.markdown(f"""
1. **睡眠**:目标 7.5-9 小时;睡眠差时训练收益会明显下降。
2. **补水和碳水**:长距离/强度课后先补碳水,再补蛋白。
3. **低强度活动**:疲劳高时,30-45 分钟 Z1 比硬上间歇更有价值。
4. **疼痛处理**:重复疼痛优先查训练量、锁片/座垫/把位,不要只靠忍。
""")
    with c2:
        st.subheader("最近反馈摘要")
        for line in feedback_summary.get('lines', []):
            st.markdown(f"- {line}")
        if pain_counts:
            pain_txt = "、".join(f"{k}×{v}" for k, v in sorted(pain_counts.items(), key=lambda kv: kv[1], reverse=True))
            st.warning(f"不适记录:{pain_txt}")
        if special_counts:
            special_txt = "、".join(f"{k}×{v}" for k, v in sorted(special_counts.items(), key=lambda kv: kv[1], reverse=True))
            st.warning(f"特殊情况:{special_txt}")
        if cycle_counts:
            cycle_txt = "、".join(f"{k}×{v}" for k, v in sorted(cycle_counts.items(), key=lambda kv: kv[1], reverse=True))
            st.info(f"女性周期:{cycle_txt}")
        if not feedback:
            st.info("还没有训练反馈。去「📝 训练反馈」记录一次,恢复判断会更准。")

    st.divider()
    st.subheader("⌚ 手表睡眠数据")
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

elif page == "🍝 营养与补给":
    require_plan(2, "🍝 营养与补给")
    st.title("🍝 营养与补给")
    st.caption("不是泛泛说多吃碳水,而是按今天的训练、体重、强度和反馈,算出怎么吃、怎么喝、怎么补。")

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
        ride_hours = st.slider("今天骑多久 h", 0.5, 24.0, 2.0, 0.5, key="nut_ride_hours")
    with c3:
        workout_type = st.selectbox("训练类型", ["恢复骑", "Z2 长距离", "甜区/阈值", "VO2max/间歇", "比赛/绕圈赛"], key="nut_workout_type")
    with c4:
        environment = st.selectbox("环境", ["正常", "天气太热", "天气太冷", "室内骑行"], index=1 if "天气太热" in special_set else 0, key="nut_environment")

    if workout_type == "恢复骑":
        carb_lo, carb_hi = 0, 20
        water_lo, water_hi = 400, 600
        sodium_lo, sodium_hi = 0, 300
        intensity_note = "恢复骑主要目标是促进血液循环,不需要强行补很多糖。"
    elif workout_type == "Z2 长距离":
        carb_lo, carb_hi = (30, 50) if ride_hours <= 2 else (50, 70)
        water_lo, water_hi = 500, 750
        sodium_lo, sodium_hi = 300, 600
        intensity_note = "Z2 长距离要从前 20 分钟就开始少量多次补,不要等饿了再吃。"
    elif workout_type == "甜区/阈值":
        carb_lo, carb_hi = 60, 80
        water_lo, water_hi = 600, 850
        sodium_lo, sodium_hi = 500, 800
        intensity_note = "甜区/阈值会明显消耗糖原,训练前和训练中都要有碳水支持。"
    elif workout_type == "VO2max/间歇":
        carb_lo, carb_hi = 50, 70
        water_lo, water_hi = 600, 850
        sodium_lo, sodium_hi = 500, 800
        intensity_note = "VO2max 更怕胃里太撑,训练前吃够,训练中小口补。"
    else:
        carb_lo, carb_hi = 80, 100
        water_lo, water_hi = 750, 1000
        sodium_lo, sodium_hi = 700, 1000
        intensity_note = "比赛日目标是稳定供能,不要尝试没测试过的新补给。"

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
    <div class="why"><b>依据:</b>{workout_type}|{ride_hours}h|{environment}|体重 {weight}kg。{intensity_note}</div>
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
- 碳水:**{pre_carb}g**
- 蛋白:**{pre_protein}g**
- 低脂、低纤维,别吃太撑
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
- 碳水:**{post_carb}g**
- 蛋白:**{post_protein}g**
- 强度课后优先补碳水
""")

    st.subheader("按训练类型快速参考")
    rows = [
        ["恢复骑", "0-20g/h", "400-600ml/h", "0-300mg/h", "不饿不硬吃,重点恢复"],
        ["Z2 长距离", "50-70g/h", "500-750ml/h", "300-600mg/h", "从前 20 分钟开始补"],
        ["甜区/阈值", "60-80g/h", "600-850ml/h", "500-800mg/h", "训练前必须吃够"],
        ["VO2max/间歇", "50-70g/h", "600-850ml/h", "500-800mg/h", "别让胃太撑,小口补"],
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
                    reason_parts.append("高温/室内:补钠优先")
                if "胃不舒服" in fueling_set and sup.get("type") == "软糖":
                    card_tone = "gut"
                    reason_parts.append("胃不适:软糖更温和")
                if workout_type in ["比赛/绕圈赛", "VO2max/间歇"] and sup.get("caffeine"):
                    card_tone = "caffeine"
                    reason_parts.append("高强度:咖啡因加成")
                if workout_type == "恢复骑" and sup.get("caffeine"):
                    card_tone = "caution"
                    reason_parts.append("恢复骑:咖啡因谨慎")
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
            st.info("高温+胃不适:优先碳水软糖做碳水主力,搭配电解质胶少量多次补盐。赛前 30min 不要吃太多胶。")
        elif environment in ["天气太热", "室内骑行"]:
            st.info("高温环境:推荐以电解质胶为主,碳水软糖作为口味调剂。不要只靠碳水密度高的产品而忽略钠。")
        elif "胃不舒服" in fueling_set:
            st.info("胃不适记录:优先碳水软糖→果胶基质更温和;能量胶分小口摄入,不要一次吃完一根。")
        elif workout_type == "比赛/绕圈赛":
            st.info("比赛日:赛前可用咖啡胶,赛中主力用电解质胶。不要用训练中没测试过的产品。")
    else:
        st.caption("补剂产品库未加载,请确认 supplement_db.json 存在。")

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

    st.caption(f"数据依据:体重 {weight}kg;FTP {ftp or '-'}W;训练反馈 {len(feedback)} 条。补给建议用于训练辅助,不替代医学或营养师建议。")

elif page == "🎯 目标追踪":
    require_plan(2, "🎯 目标追踪")
    st.title("🎯 目标追踪")
    st.caption("把目标拆成路径、阶段和本周动作:不是许愿,而是知道下一步怎么走。")

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
    <div class="goal-card"><div class="k">反馈接入</div><div class="v">{len(recent_feedback)} 条</div><div class="d">睡眠 {avg_sleep or '-'} / 腿疲劳 {avg_fatigue or '-'}</div></div>
    <div class="goal-card"><div class="k">目标日期</div><div class="v">{event_date}</div><div class="d">用于阶段倒推</div></div>
</div>
""", unsafe_allow_html=True)

    progress = min(max(ftp / target_ftp, 0), 1) if target_ftp else 0
    st.progress(progress, f"当前进度:{round(progress*100)}%|还差 {max(0, ftp_gap)}W / {max(0, wkg_gap)} W/kg")

    st.subheader("阶段路径")
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
    st.dataframe(pd.DataFrame(phase_rows).astype(str), use_container_width=True, hide_index=True)

    c_left, c_right = st.columns([1.05, 1])
    with c_left:
        st.subheader("本周动作")
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

    st.subheader("什么时候重新评估")
    st.markdown("""
- **每 4 周**:重新看 FTP、CTL/ATL/TSB 和最近反馈。
- **连续两周疲劳高或睡眠差**:目标不一定错,但推进速度要降。
- **比赛前 7-10 天**:不再追训练量,改为保持状态和降低疲劳。
- **疼痛重复出现**:先处理身体/装备/姿势,不要继续用训练计划硬压。
""")

st.sidebar.caption("TrueCadence v1.0")
st.sidebar.caption(f"{datetime.date.today()}")
render_icp_footer()


