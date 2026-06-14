from __future__ import annotations

import html
from typing import Callable

from services.fueling_recommendation import build_v2_fueling_recommendation
from services.training_calendar import week_plan_context

from .shell import _wrap, _url
from .readiness_bridge import v2_readiness_context


def _safe_call(func: Callable | None, default):
    if not func:
        return default
    try:
        return func()
    except Exception:
        return default


def render_fueling_page(*, load_feedback: Callable | None = None, load_profile: Callable | None = None, load_rides: Callable | None = None, load_sleep: Callable | None = None, compute_daily_pmc_func: Callable | None = None):
    readiness = v2_readiness_context(load_feedback=load_feedback, load_profile=load_profile, load_rides=load_rides, load_sleep=load_sleep, compute_daily_pmc_func=compute_daily_pmc_func)
    ctx = week_plan_context(readiness=readiness)
    session = ctx["today_context"]["session"]
    feedback = _safe_call(load_feedback, [])
    profile = _safe_call(load_profile, {})
    rec = build_v2_fueling_recommendation(session, feedback=feedback, profile=profile, today=ctx["today"])
    basis_html = "".join(f"<li>{html.escape(item)}</li>" for item in rec.basis)
    body = f'''
        <section class="panel hot tc-fuel-hero">
          <div class="code">FUEL · {html.escape(ctx["today"].strftime("%Y-%m-%d"))}</div>
          <div class="label green">今日补给建议</div>
          <div class="h1">{html.escape(rec.headline)}</div>
          <p class="txt">{html.escape(rec.context_line)} {html.escape(rec.feedback_line)}</p>
          <div class="actions"><a target="_self" class="btn primary" href="#tc-fuel-detail-modal-layer">打开吃什么清单</a></div>
        </section>

        <div class="grid-4 mt tc-fuel-metrics">
          <section class="mini"><div class="k">碳水 / 小时</div><div class="v">{rec.carb_range[0]}–{rec.carb_range[1]}g</div><div class="d">按今天课程强度估算，不是一律多吃胶。</div></section>
          <section class="mini"><div class="k">预计总碳水</div><div class="v">{rec.total_carb_range[0]}–{rec.total_carb_range[1]}g</div><div class="d">随实际缩短/降级同步下调。</div></section>
          <section class="mini"><div class="k">水 / 小时</div><div class="v">{rec.water_range[0]}–{rec.water_range[1]}ml</div><div class="d">室内和热天优先补液。</div></section>
          <section class="mini"><div class="k">钠 / 小时</div><div class="v">{rec.sodium_range[0]}–{rec.sodium_range[1]}mg</div><div class="d">出汗大时不要只补糖。</div></section>
        </div>

        <div class="grid-2 mt">
          <section class="panel"><div class="code">BEFORE</div><div class="label cyan">骑前吃什么</div><div class="h2">先补够，再谈训练质量</div><p class="txt">{html.escape(rec.before)}</p></section>
          <section class="panel hot"><div class="code">DURING</div><div class="label purple">骑中怎么补</div><div class="h2">按小时拆，不等饿了再吃</div><p class="txt">{html.escape(rec.during)}</p></section>
        </div>

        <div class="grid-3 mt">
          <section class="panel"><div class="code">DRINK</div><div class="label blue">喝水 / 电解质</div><div class="h2">补水跟出汗量走</div><p class="txt">{html.escape(rec.hydration)}</p></section>
          <section class="panel"><div class="code">AFTER</div><div class="label green">骑后恢复</div><div class="h2">回到正餐，不靠胶代餐</div><p class="txt">{html.escape(rec.after)}</p></section>
          <section class="panel hot"><div class="code">ADJUST</div><div class="label warn">根据反馈修正</div><div class="h2">联动上一条训练反馈</div><p class="txt">{html.escape(rec.adjustment)}</p></section>
        </div>

        <div class="grid-3 mt">
          <a target="_self" class="accordion" href="#tc-fuel-detail-modal-layer">查看完整清单</a>
          <a target="_self" class="accordion" href="{_url('训练驾驶舱', '首页简报')}">回今日训练</a>
          <a target="_self" class="accordion" href="{_url('训练计划', '本周课表')}">看本周课表</a>
        </div>
        <style>
        .tc-fuel-hero .txt{{max-width:900px;padding-right:470px}}
        .tc-fuel-hero .actions{{gap:10px}}
        .tc-fuel-metrics .mini .v{{font-size:24px;color:#f4f0ea}}
        </style>
        '''
    _wrap('今日补给', '今日补给', body)
    _render_fuel_detail_modal(rec, basis_html)


def _render_fuel_detail_modal(rec, basis_html: str) -> None:
    from .modal_window import render_mac_modal_window

    detail_html = f'''
    <div class="tc-fuel-detail-grid">
      <section class="tc-fuel-card hot"><div class="k">今天先看这个</div><div class="v">{html.escape(rec.headline)}</div><p>{html.escape(rec.context_line)}</p></section>
      <section class="tc-fuel-card"><div class="k">骑前</div><p>{html.escape(rec.before)}</p></section>
      <section class="tc-fuel-card"><div class="k">骑中</div><p>{html.escape(rec.during)}</p></section>
      <section class="tc-fuel-card"><div class="k">喝水 / 电解质</div><p>{html.escape(rec.hydration)}</p></section>
      <section class="tc-fuel-card"><div class="k">骑后</div><p>{html.escape(rec.after)}</p></section>
      <section class="tc-fuel-card hot"><div class="k">反馈修正</div><p>{html.escape(rec.adjustment)}</p></section>
      <section class="tc-fuel-card wide"><div class="k">依据</div><ul>{basis_html}</ul><p>{html.escape(rec.warning)}</p></section>
    </div>
    '''
    css = '''
.tc-fuel-detail-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }
.tc-fuel-card { border:1px solid rgba(255,255,255,.07); background:rgba(255,255,255,.035); border-radius:18px; padding:18px 20px; }
.tc-fuel-card.hot { background:rgba(240,111,50,.10); border-color:rgba(240,111,50,.28); }
.tc-fuel-card.wide { grid-column:1/-1; }
.tc-fuel-card .k { color:#f06f32; font-size:14px; font-weight:820; letter-spacing:.04em; margin-bottom:8px; }
.tc-fuel-card .v { color:#f4f0ea; font-size:22px; font-weight:820; letter-spacing:-.03em; margin-bottom:8px; }
.tc-fuel-card p, .tc-fuel-card li { color:#a7a19a; font-size:15px; line-height:1.7; margin:0; }
.tc-fuel-card ul { margin:0 0 10px; padding-left:18px; }
'''
    render_mac_modal_window(
        title='今天吃什么',
        intro='按今天课程强度 + 最近训练反馈生成的轻量补给清单。',
        form_html=detail_html,
        close_url='?nav=%E7%8A%B6%E6%80%81%E4%B8%8E%E6%81%A2%E5%A4%8D&sub=%E8%90%A5%E5%85%BB%E8%A1%A5%E7%BB%99',
        submit_label='关闭',
        window_id='tc-fuel-detail-modal',
        extra_css=css,
    )
