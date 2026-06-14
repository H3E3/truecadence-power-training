from __future__ import annotations

import html
import math
from pathlib import Path

import streamlit as st

from auth import load_rider_profile, load_rider_rides
from rules.power_analysis import estimate_best_powers
from services.rider_store import load_historical_for_context, load_profile_for_context
from services.training_metrics import estimate_ftp, estimate_ftp_explain

from .shell import _wrap
from .modal_window import render_mac_modal_window

APP_DIR = Path(__file__).resolve().parents[2]
PROFILE_FILE = APP_DIR / "profile.json"
DATA_FILE = APP_DIR / "data" / "rides.json"


def _fmt_w(value) -> str:
    try:
        v = float(value or 0)
    except Exception:
        v = 0
    return f"{round(v)}W" if v > 0 else "暂无"


def _pct(power, ftp) -> str:
    try:
        if power and ftp:
            return f"{round(float(power) / float(ftp) * 100)}% FTP"
    except Exception:
        pass
    return "等待数据"


def _load_power_context():
    user = st.session_state.get("user") or {}
    rider = st.session_state.get("rider", "默认骑手")
    rides = load_historical_for_context(user, rider, DATA_FILE, load_rider_rides)
    profile = load_profile_for_context(user, rider, PROFILE_FILE, load_rider_profile)
    weight = profile.get("weight", 69) or 69
    ftp_detail = estimate_ftp_explain(rides)
    est_ftp = ftp_detail.get("ftp") or estimate_ftp(rides)
    actual_ftp = profile.get("ftp_test", 0) or profile.get("ftp", 0) or 0
    ftp = actual_ftp if actual_ftp > 0 else est_ftp
    best = estimate_best_powers(rides, ftp)
    return {
        "user": user,
        "rider": rider,
        "rides": rides,
        "profile": profile,
        "weight": weight,
        "ftp": ftp,
        "actual_ftp": actual_ftp,
        "est_ftp": est_ftp,
        "ftp_detail": ftp_detail,
        "best": best,
    }


def _ability_title(best, ftp) -> str:
    p5 = best.get("5s", 0) or 0
    p20 = best.get("20min", 0) or 0
    p60 = best.get("60min", 0) or 0
    if ftp and p20 and p20 / ftp >= 0.95:
        return "阈值支撑不错，继续看后程稳定性。"
    if p5 and ftp and p5 / ftp >= 2.6 and p20 and p20 / ftp < 0.9:
        return "短时能力可用，阈值持续是重点。"
    if p60 and ftp and p60 / ftp >= 0.88:
        return "持续输出较稳，可以逐步做专项强化。"
    return "先看能力结构，再决定训练重点。"


def _ability_text(best, ftp, ride_count) -> str:
    p5 = best.get("5s", 0) or 0
    p1 = best.get("1min", 0) or 0
    p5m = best.get("5min", 0) or 0
    p20 = best.get("20min", 0) or 0
    if not ride_count:
        return "还没有读取到当前骑手的 FIT 历史。先上传 FIT 后，系统会把 5s / 1min / 5min / 20min 变成真实能力画像。"
    parts = [f"已读取 {ride_count} 条训练记录。"]
    if p5 and p1:
        parts.append(f"短时窗口 {round(p5)}W / {round(p1)}W 用来看冲刺、短坡和跟加速。")
    if p5m:
        parts.append(f"5min {round(p5m)}W 反映 VO2 和 3–6 分钟高强支撑。")
    if p20 and ftp:
        parts.append(f"20min {round(p20)}W，约 {_pct(p20, ftp)}，更接近 FTP 和长坡巡航能力。")
    return "".join(parts)


def _curve_svg(best, ftp) -> str:
    labels = ["5s", "30s", "1min", "5min", "20min", "40min", "60min", "2h", "3h"]
    seconds = [5, 30, 60, 300, 1200, 2400, 3600, 7200, 10800]
    values = [float(best.get(k, 0) or 0) for k in labels]
    real_values = [v for v in values if v > 0]
    if not real_values:
        return '<div class="tc-power-empty-curve">暂无足够功率窗口数据。上传带功率的 FIT 后会显示曲线。</div>'

    width, height = 920, 260
    left, right, top, bottom = 56, 22, 24, 42
    plot_w = width - left - right
    plot_h = height - top - bottom
    min_x = math.log10(min(seconds))
    max_x = math.log10(max(seconds))
    max_y = max(max(real_values), float(ftp or 0)) * 1.12
    min_y = 0

    def xy(sec, val):
        x = left + (math.log10(sec) - min_x) / (max_x - min_x) * plot_w
        y = top + (max_y - val) / (max_y - min_y) * plot_h
        return x, y

    points = []
    circles = []
    texts = []
    for lab, sec, val in zip(labels, seconds, values):
        if val <= 0:
            continue
        x, y = xy(sec, val)
        points.append(f"{x:.1f},{y:.1f}")
        safe_lab = html.escape(lab)
        safe_power = round(val)
        tooltip = f"{safe_lab} · {safe_power}W"
        tooltip_x = min(max(x - 48, left + 4), width - right - 116)
        tooltip_y = max(y - 42, top + 6)
        circles.append(
            f'<g class="point">'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="#f06f32" stroke="#fff3e8" stroke-width="1.4" />'
            f'<g class="tip" transform="translate({tooltip_x:.1f},{tooltip_y:.1f})">'
            f'<rect x="0" y="0" width="112" height="30" rx="10" fill="#15100c" stroke="#f06f32" stroke-width="1.2" opacity=".98" />'
            f'<text x="56" y="20" text-anchor="middle" fill="#f4f0ea" font-size="14" font-weight="780">{tooltip}</text>'
            f'</g>'
            f'</g>'
        )
        texts.append(f'<text x="{x:.1f}" y="{height - 16}" text-anchor="middle" class="axis">{safe_lab}</text>')

    ftp_line = ""
    if ftp:
        _, y = xy(seconds[0], float(ftp))
        ftp_line = f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#5ee7df" stroke-width="1.4" stroke-dasharray="7 7" opacity=".78"/><text x="{width-right-4}" y="{y-8:.1f}" text-anchor="end" class="ftp">FTP {round(ftp)}W</text>'

    y_ticks = []
    for ratio in [0, .25, .5, .75, 1]:
        val = min_y + (max_y - min_y) * ratio
        y = top + (1 - ratio) * plot_h
        y_ticks.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#211b16" stroke-width="1"/><text x="{left-12}" y="{y+4:.1f}" text-anchor="end" class="axis">{round(val)}</text>')

    return f'''
    <div class="tc-power-curve-card">
      <svg viewBox="0 0 {width} {height}" role="img" aria-label="真实 FIT 功率曲线">
        <style>.axis{{fill:#67645f;font-size:13px;font-weight:650}}.ftp{{fill:#5ee7df;font-size:14px;font-weight:760}}.point circle{{cursor:pointer;transition:r .16s ease,filter .16s ease}}.point:hover circle{{r:10;filter:drop-shadow(0 0 8px #f06f32)}}.point .tip{{opacity:0;pointer-events:none;transition:opacity .12s ease}}.point:hover .tip{{opacity:1}}</style>
        <rect x="0" y="0" width="{width}" height="{height}" rx="22" fill="#080a0d" stroke="#211b16" />
        {''.join(y_ticks)}
        {ftp_line}
        <polyline points="{' '.join(points)}" fill="none" stroke="#f06f32" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
        {''.join(circles)}
        {''.join(texts)}
      </svg>
    </div>
    '''


def _power_modal_curve(best, ftp) -> str:
    return f'''
    <div class="tc-power-note-grid one">
      <section class="tc-power-note-card hot"><div class="k">真实功率曲线</div><p>这张曲线来自当前骑手已保存的 FIT 历史，不是静态样例。横轴是时间窗口，纵轴是该窗口最佳平均功率。</p></section>
    </div>
    {_curve_svg(best, ftp)}
    '''


def render_power_page():
    ctx = _load_power_context()
    rides = ctx["rides"]
    best = ctx["best"]
    ftp = ctx["ftp"]
    weight = ctx["weight"]
    ride_count = len(rides)
    p5 = best.get("5s", 0) or 0
    p1 = best.get("1min", 0) or 0
    p5m = best.get("5min", 0) or 0
    p20 = best.get("20min", 0) or 0
    p60 = best.get("60min", 0) or 0
    wkg = round(float(ftp) / float(weight), 1) if ftp and weight else 0
    ftp_source = "实测 FTP" if ctx["actual_ftp"] else "自动估算 FTP"

    body = f'''
        <section class="panel hot"><div class="code">POWER</div><div class="label cyan">能力结论</div><div class="h1">{html.escape(_ability_title(best, ftp))}</div><p class="txt">{html.escape(_ability_text(best, ftp, ride_count))}</p></section>
        <div class="grid-4 mt"><section class="panel"><div class="code">5S / 1MIN</div><div class="label rose">冲刺 / 短坡</div><div class="h2">{_fmt_w(p5)} / {_fmt_w(p1)}</div><p class="txt">看起步、冲刺、短坡顶一下和跟加速。强不等于 FTP 高，但能说明短时发动机。</p></section><section class="panel"><div class="code">5MIN</div><div class="label warn">VO2 / 高强支撑</div><div class="h2">{_fmt_w(p5m)}</div><p class="txt">对应 3–6 分钟爬坡、追击和 VO2max 课。决定你能不能反复吃高强度。</p></section><section class="panel"><div class="code">20MIN</div><div class="label lime">阈值 / FTP 支撑</div><div class="h2">{_fmt_w(p20)}</div><p class="txt">{_pct(p20, ftp)}。比短时峰值更能体现长坡、巡航和持续输出能力。</p></section><section class="panel"><div class="code">FTP</div><div class="label slate">当前基准</div><div class="h2">{_fmt_w(ftp)}</div><p class="txt">{html.escape(ftp_source)} · {wkg or '-'} W/kg · 当前骑手历史 {ride_count} 条。训练区间和课表以这个 FTP 为准。</p></section></div>
        <div class="grid-2 mt"><section class="panel hot"><div class="label lime">训练指向</div><div class="h2">先看 20–60min 掉得快不快</div><p class="txt">60min 当前 {_fmt_w(p60)}。如果短时窗口强但 20–60min 明显低，下一阶段优先补 Z2、甜区、阈值和疲劳后稳定输出。</p></section><section class="panel"><div class="label slate">数据可信度</div><div class="h2">来自已上传 FIT</div><p class="txt">如果近期没有专门做过 5s、1min、5min 或 20min 全力测试，画像仍可能低估真实能力；异常峰值会高估短时窗口。</p><div class="actions"><a target="_self" class="btn primary" href="#tc-power-exclusion-note-modal-layer">异常数据说明</a></div></section></div>
        <div class="mt">{_curve_svg(best, ftp)}</div>
        <div class="grid-2 mt"><a target="_self" class="accordion" href="#tc-power-curve-note-modal-layer">展开功率曲线</a><a target="_self" class="accordion" href="#tc-power-percentile-note-modal-layer">查看分位数说明</a></div>
        '''
    _wrap('专业数据', '功率能力数据', body)
    _render_power_curve_note_modal(best, ftp)
    _render_power_percentile_note_modal()
    _render_power_exclusion_note_modal()


def _render_power_curve_note_modal(best, ftp) -> None:
    _render_power_note_modal(
        title='功率曲线说明',
        intro='这不是静态样例：曲线来自当前骑手已上传/保存的 FIT 数据。',
        form_html=_power_modal_curve(best, ftp),
        window_id='tc-power-curve-note-modal',
    )


def _render_power_percentile_note_modal() -> None:
    form_html = '''
    <div class="tc-power-note-grid">
      <section class="tc-power-note-card hot"><div class="k">分位数是什么</div><p>分位数用来回答“在相近 FTP / 功体比水平的人里，这个窗口算强还是弱”，比只看绝对瓦数更公平。</p></section>
      <section class="tc-power-note-card"><div class="k">不同窗口含义不同</div><p>5s 更偏神经肌肉和冲刺；1min 偏无氧容量；5min 偏 VO2；20min 更接近阈值和 FTP 支撑。</p></section>
      <section class="tc-power-note-card"><div class="k">不要过度解读</div><p>如果没有做过对应时长的最大努力，分位数可能低估真实能力；如果有异常峰值，也可能高估短时能力。</p></section>
      <section class="tc-power-note-card"><div class="k">产品口径</div><p>TrueCadence 会优先把分位数翻译成强项、短板和训练方向，而不是让用户自己研究表格。</p></section>
    </div>
    '''
    _render_power_note_modal(
        title='分位数说明',
        intro='这里解释功率画像里的分位数口径，避免用户只盯一个瓦数做判断。',
        form_html=form_html,
        window_id='tc-power-percentile-note-modal',
    )


def _render_power_note_modal(*, title: str, intro: str, form_html: str, window_id: str) -> None:
    extra_css = '''
.tc-power-note-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.tc-power-note-grid.one{grid-template-columns:1fr}.tc-power-note-card{border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.035);border-radius:18px;padding:18px 20px}.tc-power-note-card.hot{background:rgba(240,111,50,.10);border-color:rgba(240,111,50,.28)}.tc-power-note-card .k{color:#f06f32;font-size:14px;font-weight:820;letter-spacing:.04em;margin-bottom:8px}.tc-power-note-card p{color:#a7a19a;font-size:15px;line-height:1.7;margin:0}.tc-power-curve-card{margin-top:16px}.tc-power-empty-curve{border:1px solid #211b16;background:#080a0d;border-radius:22px;padding:28px;color:#a7a19a}@media(max-width:860px){.tc-power-note-grid{grid-template-columns:1fr}}
'''
    render_mac_modal_window(
        title=title,
        intro=intro,
        form_html=form_html,
        close_url='?nav=%E4%B8%93%E4%B8%9A%E6%95%B0%E6%8D%AE&sub=%E5%8A%9F%E7%8E%87%E7%94%BB%E5%83%8F',
        submit_label='关闭',
        window_id=window_id,
        extra_css=extra_css,
    )


def _render_power_exclusion_note_modal() -> None:
    form_html = '''
    <div class="tc-power-note-grid">
      <section class="tc-power-note-card hot"><div class="k">什么时候算异常</div><p>比如功率计飘值、设备断连重连、室内台功率源异常，导致某个 5s / 30s / 1min 峰值明显不符合实际。</p></section>
      <section class="tc-power-note-card"><div class="k">会影响什么</div><p>异常峰值会把功率画像和峰值曲线抬高，让系统误以为短时能力更强，从而影响训练判断。</p></section>
      <section class="tc-power-note-card"><div class="k">不会删除原始数据</div><p>异常排除只应该影响分析层，不应该改写原始 FIT 或历史训练记录。</p></section>
      <section class="tc-power-note-card"><div class="k">当前新版状态</div><p>新版 V2 页面先保留说明入口；完整管理器会接入旧版已验证功能后再开放。</p></section>
    </div>
    '''
    _render_power_note_modal(
        title='异常数据说明',
        intro='这里先解释异常功率的处理边界。',
        form_html=form_html,
        window_id='tc-power-exclusion-note-modal',
    )
