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
    render_ai_analysis_styles,
    render_ai_cached_notice,
    render_ai_context_summary,
    render_ai_usage_panel,
    render_beta_feedback_intro,
    render_empty_data_state,
    render_goal_action_and_risk,
    render_goal_phase_path,
    render_goal_reassessment_notes,
    render_goal_styles,
    render_goal_verdict_summary,
    render_icp_footer as render_icp_footer_widget,
    render_intervals_manual_import_note,
    render_intervals_oauth_import_note,
    render_mini_metric_card,
    render_nutrition_feedback_adjustments,
    render_nutrition_intro,
    render_nutrition_quick_reference,
    render_nutrition_supplement_guidance,
    render_nutrition_target,
    render_nutrition_timing_guidance,
    render_plan_builder_intro,
    render_plan_builder_styles,
    render_plan_source_scope,
    render_plan_summary_cards,
    render_power_dashboard_top_metrics,
    render_power_ftp_reference,
    render_power_profile_and_durability,
    render_recovery_action_and_feedback,
    render_recovery_advice_summary,
    render_recovery_intro,
    render_danger_note,
    render_pricing_intro,
    render_profile_help,
    render_profile_intro,
    render_profile_section_title,
    render_training_feedback_intro,
    render_training_feedback_section,
    render_strava_export_note,
    render_training_load_guidance,
    render_training_load_styles,
    render_training_load_summary,
    render_upgrade_note,
    render_upload_cta_note,
    render_upload_intro,
    render_upload_next_steps,
    render_upload_quick_diagnosis_card,
    render_vertical_spacer,
    select_ride_scope as select_ride_scope_widget,
)
from tc_pages.account_pages import (
    render_beta_feedback_page,
    render_pricing_page,
)
from tc_pages.import_pages import (
    render_data_import_page,
    render_upload_analysis_page,
)
from tc_pages.profile_feedback_pages import (
    render_rider_profile_page,
    render_training_feedback_page,
)
from tc_pages.training_overview_pages import (
    render_power_dashboard_page,
    render_training_load_page,
)
from tc_pages.recovery_nutrition_goal_pages import (
    render_goal_tracking_page,
    render_nutrition_page,
    render_recovery_sleep_page,
)
from tc_pages.ai_analysis_page import render_ai_power_analysis_page
from tc_pages.training_plan_page import render_training_plan_page
from tc_pages.static_pages import (
    render_changelog_page,
    render_english_review_page,
    render_home_page,
    render_privacy_page,
)
from rules.recovery import (
    build_recovery_advice,
    summarize_diagnosis_sleep_recovery,
    summarize_recovery_inputs,
)
from rules.nutrition import (
    calculate_nutrition_targets,
    feedback_sets_from_recent_feedback,
    rank_supplements,
    score_supplement,
    supplement_card_context,
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
ADMIN_PHONE_ALLOWLIST = {x.strip() for x in os.environ.get("TRUECADENCE_ADMIN_PHONES", "").split(",") if x.strip()}


def is_admin_account(user_data: dict | None) -> bool:
    user_data = user_data or {}
    return bool(
        user_data.get("is_admin")
        or user_data.get("role") in ("admin", "super_admin")
        or (ADMIN_PHONE_ALLOWLIST and str(user_data.get("phone", "")) in ADMIN_PHONE_ALLOWLIST)
    )


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
is_admin_user = is_admin_account(_nav_user)

nav_groups = {
    "首页": {"desc": "", "pages": [("功能说明", "🏠 功能说明")]},
    "我的档案": {"desc": "身体、目标、骑手", "pages": [("骑手档案", "👤 骑手档案"), ("目标追踪", "🎯 目标追踪")]},
    "导入数据": {"desc": "FIT 与平台数据", "pages": [("FIT 上传", "📤 上传分析"), ("平台导入", "🔗 数据导入")]},
    "AI 分析": {"desc": "核心诊断", "pages": [("AI 分析", "🧠 AI 功率分析")]},
    "我的分析": {"desc": "能力、恢复", "pages": [("功率仪表盘", "📊 功率仪表盘"), ("恢复睡眠", "🛌 恢复与睡眠"), ("营养补给", "🍝 营养与补给")]},
    "训练建议": {"desc": "负荷、反馈", "pages": [("训练负荷", "📈 训练负荷"), ("训练反馈", "📝 训练反馈")]}, 
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
    if st.sidebar.button(name, key=f"nav_btn_{name}", use_container_width=True, type=("primary" if is_active else "secondary")):
        first_label = nav_groups[name]["pages"][0][0]
        _set_nav(name, first_label)
        st.rerun()

visible_subs = [(lbl, emoji) for lbl, emoji in sub_pages if lbl != "训练课表"]
if len(visible_subs) > 1:
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
is_admin_user = is_admin_account(user)
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


PLAN_PREF_DEFAULTS = {
    "goal": "恢复体能 / 重建基础",
    "weeks": 4,
    "hours": 8,
    "training_experience": "未填写",
    "historical_best_ftp": 0,
    "detraining_duration": "未填写",
    "historical_best_wkg": 0.0,
    "progression_preference": "标准",
    "event_type": "无比赛",
    "event_date": "",
    "event_priority": "B",
    "training_days": ['周二','周三','周五','周六','周日'],
    "preferred_long_day": "周日",
    "no_hard_days": [],
}


def get_plan_prefs_path():
    user = st.session_state.get("user")
    rider = st.session_state.get("rider", "默认骑手")
    if not user:
        return None
    return get_rider_data_path(user["user_id"], rider, "plan_prefs")


def load_plan_prefs():
    path = get_plan_prefs_path()
    if path and path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return {**PLAN_PREF_DEFAULTS, **data}
        except Exception:
            pass
    return dict(PLAN_PREF_DEFAULTS)


def save_plan_prefs(data):
    user = st.session_state.get("user")
    rider = st.session_state.get("rider", "默认骑手")
    if user:
        save_rider_data(user["user_id"], rider, "plan_prefs", data)


def clamp_number(value, default, min_value, max_value, as_float=False):
    try:
        v = float(value) if as_float else int(value)
    except Exception:
        v = default
    return max(min_value, min(max_value, v))



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

    render_upload_quick_diagnosis_card(
        state=state,
        state_desc=state_desc,
        state_color=state_color,
        range_text=range_text,
        ride_count=len(rides),
        ftp=ftp,
        ftp_source=ftp_source,
        wkg=wkg,
        ctl=ctl,
        atl=atl,
        tsb=tsb,
        recent7_tss=recent7_tss,
        recent28_tss=recent28_tss,
        traits=traits,
        suggestions=suggestions,
    )







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

    # Subjective feedback and wearable sleep / recovery interpretation
    feedback_summary = summarize_recent_feedback(feedback or [])
    recovery_diagnosis = summarize_diagnosis_sleep_recovery(feedback_summary, sleep_records or [])
    feedback_lines = recovery_diagnosis["feedback_lines"]
    sleep_lines = recovery_diagnosis["sleep_lines"]
    combined_recovery_flags = recovery_diagnosis["combined_recovery_flags"]

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

    feedback_badge = recovery_diagnosis["feedback_badge"]
    sleep_badge = recovery_diagnosis["sleep_badge"]

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
    render_beta_feedback_page(load_beta_feedback, save_beta_feedback)
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
    render_pricing_page(
        PLANS=PLANS,
        create_order=create_order,
        get_user_orders=get_user_orders,
        hide_order_for_user=hide_order_for_user,
        PAYMENT_WECHAT_QR_PATH=PAYMENT_WECHAT_QR_PATH,
        PAYMENT_ALIPAY_QR_PATH=PAYMENT_ALIPAY_QR_PATH,
        user=user,
    )
elif page == "📝 训练反馈":
    render_training_feedback_page(load_feedback=load_feedback, save_feedback=save_feedback, load_profile=load_profile)
elif page == "📤 上传分析":
    render_upload_analysis_page(
        parse_fit_files=parse_fit_files,
        enrich_rides=enrich_rides,
        load_historical=load_historical,
        merge_rides=merge_rides,
        save_current_rides=save_current_rides,
        render_upload_quick_diagnosis=render_upload_quick_diagnosis,
        load_profile=load_profile,
    )
elif page == "🔗 数据导入":
    render_data_import_page(
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
        set_nav=_set_nav,
    )
elif page == "👤 骑手档案":
    render_rider_profile_page(
        load_profile=load_profile,
        load_rider_profile=load_rider_profile,
        save_rider_profile=save_rider_profile,
        load_rider_rides=load_rider_rides,
        load_users=load_users,
        add_rider=add_rider,
        delete_rider=delete_rider,
        PROFILE_FILE=PROFILE_FILE,
        plan_info=plan_info,
        hr_zones_by_max=hr_zones_by_max,
        hr_zones_by_lthr=hr_zones_by_lthr,
        load_plan_prefs=load_plan_prefs,
        save_plan_prefs=save_plan_prefs,
    )
elif page == "📊 功率仪表盘":
    render_power_dashboard_page(
        select_ride_scope=select_ride_scope,
        merge_rides=merge_rides,
        load_historical=load_historical,
        enrich_rides=enrich_rides,
        load_profile=load_profile,
        estimate_ftp=estimate_ftp,
        calculate_power_zones=calculate_power_zones,
        hr_zones_by_max=hr_zones_by_max,
        hr_zones_by_lthr=hr_zones_by_lthr,
        plot_power_curve=plot_power_curve,
        estimate_best_powers=estimate_best_powers,
        calculate_fatigue_resistance=calculate_fatigue_resistance,
        summarize_durability=summarize_durability,
        ftp_wkg_bucket=ftp_wkg_bucket,
        peer_samples_for_bucket=peer_samples_for_bucket,
        record_power_profile_sample=record_power_profile_sample,
        power_profile_rating_rows=power_profile_rating_rows,
        apply_power_exclusions_to_rides=apply_power_exclusions_to_rides,
        render_power_exclusion_manager=render_power_exclusion_manager,
        estimate_ftp_explain=estimate_ftp_explain,
        data_scope_caption=data_scope_caption,
        POWER_PROFILE_MIN_PEER_SAMPLES=POWER_PROFILE_MIN_PEER_SAMPLES,
    )
elif page == "📈 训练负荷":
    render_training_load_page(
        select_ride_scope=select_ride_scope,
        merge_rides=merge_rides,
        load_historical=load_historical,
        enrich_rides=enrich_rides,
        load_profile=load_profile,
        compute_daily_pmc=compute_daily_pmc,
        plot_pmc=plot_pmc,
        tsb_zone_text=tsb_zone_text,
        load_feedback=load_feedback,
        data_scope_caption=data_scope_caption,
    )
elif page == "🧠 AI 功率分析":
    render_ai_power_analysis_page(
        PLANS=PLANS,
        DATA_DIR=DATA_DIR,
        get_ai_usage=get_ai_usage,
        get_ai_limit=get_ai_limit,
        increment_ai_usage=increment_ai_usage,
        load_historical=load_historical,
        select_ride_scope=select_ride_scope,
        enrich_rides=enrich_rides,
        data_scope_caption=data_scope_caption,
        load_profile=load_profile,
        estimate_ftp=estimate_ftp,
        load_feedback=load_feedback,
        summarize_recent_feedback=summarize_recent_feedback,
        load_wearable_sleep=load_wearable_sleep,
        infer_cycle_status_for_date=infer_cycle_status_for_date,
        estimate_best_powers=estimate_best_powers,
        generate_diagnosis=generate_diagnosis,
    )
elif page == "📋 训练课表":
    render_training_plan_page(
        select_ride_scope=select_ride_scope,
        merge_rides=merge_rides,
        load_historical=load_historical,
        enrich_rides=enrich_rides,
        data_scope_caption=data_scope_caption,
        load_profile=load_profile,
        save_rider_profile=save_rider_profile,
        estimate_ftp=estimate_ftp,
        estimate_best_powers=estimate_best_powers,
        infer_cycle_status_for_date=infer_cycle_status_for_date,
        load_plan_prefs=load_plan_prefs,
        save_plan_prefs=save_plan_prefs,
        PLAN_PREF_DEFAULTS=PLAN_PREF_DEFAULTS,
        compute_daily_pmc=compute_daily_pmc,
        load_feedback=load_feedback,
        summarize_recent_feedback=summarize_recent_feedback,
        load_wearable_sleep=load_wearable_sleep,
        rules_build_rider_state_v1=rules_build_rider_state_v1,
        rules_build_cadence_torque_state=rules_build_cadence_torque_state,
        rules_build_progression_state_v1=rules_build_progression_state_v1,
        rules_build_event_context=rules_build_event_context,
        rules_detect_phase=rules_detect_phase,
        rules_refined_readiness_cap=rules_refined_readiness_cap,
        rules_choose_mmp_training_focus=rules_choose_mmp_training_focus,
        rules_build_week_plan=rules_build_week_plan,
        rules_validate_week_plan=rules_validate_week_plan,
        rules_phase_meta=rules_phase_meta,
        rules_tss=rules_tss,
        rules_week_factor=rules_week_factor,
        rules_zone_style=rules_zone_style,
        estimate_tss_from_blocks=estimate_tss_from_blocks,
        workout_blocks_for_item=workout_blocks_for_item,
        workout_exports_for_item=workout_exports_for_item,
        require_plan=require_plan,
        clamp_number=clamp_number,
        DATA_DIR=DATA_DIR,
        PLAN_HARD_KINDS=PLAN_HARD_KINDS,
    )
elif page == "🛌 恢复与睡眠":
    render_recovery_sleep_page(
        require_plan=require_plan,
        select_ride_scope=select_ride_scope,
        merge_rides=merge_rides,
        load_historical=load_historical,
        enrich_rides=enrich_rides,
        compute_daily_pmc=compute_daily_pmc,
        load_feedback=load_feedback,
        summarize_recent_feedback=summarize_recent_feedback,
        save_wearable_sleep=save_wearable_sleep,
        data_scope_caption=data_scope_caption,
        load_wearable_sleep=load_wearable_sleep,
        load_profile=load_profile,
        get_effective_ftp=get_effective_ftp,
        infer_cycle_status_for_date=infer_cycle_status_for_date,
        summarize_recovery_inputs=summarize_recovery_inputs,
        build_recovery_advice=build_recovery_advice,
    )
elif page == "🍝 营养与补给":
    render_nutrition_page(
        require_plan=require_plan,
        load_profile=load_profile,
        select_ride_scope=select_ride_scope,
        merge_rides=merge_rides,
        load_historical=load_historical,
        enrich_rides=enrich_rides,
        data_scope_caption=data_scope_caption,
        get_effective_ftp=get_effective_ftp,
        load_feedback=load_feedback,
        summarize_recent_feedback=summarize_recent_feedback,
        feedback_sets_from_recent_feedback=feedback_sets_from_recent_feedback,
        calculate_nutrition_targets=calculate_nutrition_targets,
        rank_supplements=rank_supplements,
        supplement_card_context=supplement_card_context,
        APP_DIR=APP_DIR,
    )
elif page == "🎯 目标追踪":
    render_goal_tracking_page(
        require_plan=require_plan,
        select_ride_scope=select_ride_scope,
        merge_rides=merge_rides,
        load_historical=load_historical,
        enrich_rides=enrich_rides,
        load_profile=load_profile,
        get_effective_ftp=get_effective_ftp,
        compute_daily_pmc=compute_daily_pmc,
        data_scope_caption=data_scope_caption,
        load_feedback=load_feedback,
        render_footer=render_icp_footer,
    )
