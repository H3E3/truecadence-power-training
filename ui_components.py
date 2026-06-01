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
