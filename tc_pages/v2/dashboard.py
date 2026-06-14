from __future__ import annotations

import html

from services.training_calendar import fueling_advice_for_session, week_plan_context

from .shell import _wrap, _url
from .modal_window import render_mac_modal_window
from .readiness_bridge import readiness_label_class, v2_readiness_context


def render_dashboard_page(*, load_feedback=None, load_profile=None, load_rides=None, load_sleep=None, compute_daily_pmc_func=None):
    readiness = v2_readiness_context(load_feedback=load_feedback, load_profile=load_profile, load_rides=load_rides, load_sleep=load_sleep, compute_daily_pmc_func=compute_daily_pmc_func)
    ctx = week_plan_context(readiness=readiness)
    today_ctx = ctx["today_context"]
    session = today_ctx["session"]
    readiness_label = readiness_label_class(readiness.level)
    body = f'''
        <style>
        .tc-today-hero-card .label{{height:32px;padding:0 15px;border-radius:16px;font-size:16px;margin-bottom:12px}}
        .tc-today-hero-card .h1{{font-size:40px;line-height:1.04;margin:0 0 10px}}
        .tc-today-hero-card .txt{{max-width:840px;padding-right:430px;line-height:1.55}}
        .tc-today-hero-card .actions{{position:absolute;right:32px;bottom:28px;margin:0;gap:10px}}
        .tc-today-hero-card .btn{{height:48px;font-size:19px;padding:0 19px}}
        </style>
        <section class="panel hot tc-today-hero-card"><div class="code">TODAY · {html.escape(ctx["today"].strftime("%Y-%m-%d"))}</div><div class="label green">{html.escape(today_ctx["hero_label"])}</div><div class="h1">{html.escape(today_ctx["hero_title"])}</div><p class="txt">{html.escape(today_ctx["hero_text"])}</p><div class="actions"><a target="_self" class="btn primary" href="#tc-today-training-detail-modal-layer">查看训练详情</a><a target="_self" class="btn primary" href="{_url('状态与恢复', '恢复睡眠')}">记录反馈</a></div></section>
        <div class="grid-3 mt"><section class="panel"><div class="code">WHY</div><div class="label purple">为什么这样安排</div><div class="h2">{html.escape(today_ctx["why_title"])}</div><p class="txt">{html.escape(today_ctx["why_text"])}</p></section><section class="panel"><div class="code">DOWN</div><div class="label warn">降级规则</div><div class="h2">按当天状态降级</div><p class="txt">{html.escape(session.downgrade)}</p></section><section class="panel"><div class="code">NO</div><div class="label rose">今天别做</div><div class="h2">{html.escape(today_ctx["avoid_title"])}</div><p class="txt">{html.escape(today_ctx["avoid_text"])}</p></section></div>
        <div class="grid-2 mt"><section class="panel hot"><div class="label {readiness_label}">本周状态 · {html.escape(readiness.level)}</div><div class="h2">{html.escape(readiness.headline)}</div><p class="txt">{html.escape(readiness.reason)}。{html.escape(readiness.actions[0] if readiness.actions else today_ctx["impact_text"])}</p></section><section class="panel"><div class="label cyan">本周周期</div><div class="h2">{html.escape(ctx["week_range"])} · 每日自动滚动</div><p class="txt">本周课表按电脑当前日期计算；今天是 {html.escape(ctx["today_label"])}，页面每天打开会自动更新。</p></section></div>
        <div class="grid-3 mt"><a target="_self" class="accordion blue" href="{_url('状态与恢复', '营养补给')}">今天吃什么</a><a target="_self" class="accordion" href="{_url('训练计划', '本周课表')}">查看计划依据</a><a target="_self" class="accordion" href="#tc-week-plan-preview-modal-layer">查看完整课表</a></div>
        '''
    _wrap('训练驾驶舱', '今日训练建议', body)
    _render_today_training_detail_modal(ctx)
    _render_week_plan_preview_modal(ctx)


def _render_today_training_detail_modal(ctx: dict) -> None:
    today_ctx = ctx["today_context"]
    session = today_ctx["session"]
    fuel = fueling_advice_for_session(session)
    detail_html = f'''
    <div class="tc-today-detail-grid">
      <section class="tc-today-detail-card hot"><div class="k">今日对应</div><div class="v">{html.escape(session.date_label(ctx["today"]))}</div><p>{html.escape(today_ctx["hero_title"])} · {html.escape(today_ctx["hero_text"])}</p></section>
      <section class="tc-today-detail-card"><div class="k">执行方式</div><ul><li>前 10–15 分钟渐进热身。</li><li>{html.escape(session.feel)}。</li><li>{html.escape(fuel.during)}</li><li>{html.escape(fuel.hydration)}</li><li>最后 5–10 分钟轻松收操，记录反馈。</li></ul></section>
      <section class="tc-today-detail-card"><div class="k">降级规则</div><ul><li>{html.escape(session.downgrade)}。</li><li>心率明显异常高：降到 Z1/Z2 下沿。</li><li>降级后按实际时长补给：少于 60 分钟以水为主，超过 60 分钟保留碳水。</li><li>出现疼痛或不适：停止强度，记录反馈。</li></ul></section>
      <section class="tc-today-detail-card"><div class="k">今天怎么吃</div><ul><li>{html.escape(fuel.headline)}</li><li>{html.escape(fuel.before)}</li><li>{html.escape(fuel.caffeine)}</li><li>{html.escape(fuel.after)}</li></ul></section>
    </div>
    '''
    detail_css = '''
.tc-today-detail-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }
.tc-today-detail-card { border:1px solid rgba(255,255,255,.07); background:rgba(255,255,255,.035); border-radius:18px; padding:18px 20px; }
.tc-today-detail-card.hot { background:rgba(240,111,50,.10); border-color:rgba(240,111,50,.28); }
.tc-today-detail-card .k { color:#f06f32; font-size:14px; font-weight:820; letter-spacing:.04em; margin-bottom:8px; }
.tc-today-detail-card .v { color:#f4f0ea; font-size:22px; font-weight:820; letter-spacing:-.03em; margin-bottom:8px; }
.tc-today-detail-card p, .tc-today-detail-card li { color:#a7a19a; font-size:15px; line-height:1.7; margin:0; }
.tc-today-detail-card ul { margin:0; padding-left:18px; }
'''
    switch_script = '''
(() => {
  const doc = window.parent.document;
  doc.querySelectorAll('a[href="#tc-week-plan-preview-modal-layer"]').forEach((link) => {
    link.addEventListener('click', () => {
      const detailLayer = doc.getElementById('tc-today-training-detail-modal-layer');
      if (detailLayer) {
        detailLayer.classList.add('tc-saved-closed');
        detailLayer.classList.remove('tc-force-open');
        detailLayer.style.zIndex = '';
        detailLayer.style.pointerEvents = '';
        detailLayer.style.opacity = '';
      }
    });
  });
})();
'''
    render_mac_modal_window(
        title='今日训练详情',
        intro='这张卡只解释今天这一堂训练怎么执行；不跳走，不打断当前页面。',
        form_html=detail_html,
        close_url='?nav=%E8%AE%AD%E7%BB%83%E9%A9%BE%E9%A9%B6%E8%88%B1&sub=%E9%A6%96%E9%A1%B5%E7%AE%80%E6%8A%A5',
        submit_label='关闭',
        window_id='tc-today-training-detail-modal',
        extra_css=detail_css,
        extra_script=switch_script,
    )


def _render_week_plan_preview_modal(ctx: dict) -> None:
    rows = []
    training_sessions = ctx.get("training_sessions") or []
    rest_days = ctx.get("rest_days") or []
    quality_sessions = [s for s in training_sessions if "质量" in s.kind or "甜区" in s.title or "阈值" in s.title or "比赛" in s.title]
    total_training_text = f"{len(training_sessions)} 天训练"
    rest_text = f"{len(rest_days)} 天休息"
    quality_text = f"{len(quality_sessions)} 次质量/专项" if quality_sessions else "无明显质量课"
    first_quality = quality_sessions[0] if quality_sessions else None
    if first_quality:
        adaptive_rule = f"如果反馈变差，{first_quality.weekday_label}的{first_quality.title}优先按降级规则执行；如果反馈稳定，保留但不临时加量。"
    else:
        adaptive_rule = "如果反馈变差，下一堂训练优先缩短或改恢复骑；如果反馈稳定，维持当前低强度连续性。"
    for session in ctx["sessions"]:
        row_class = " today" if session.status(ctx["today"]) == "today" else " past" if session.status(ctx["today"]) == "past" else ""
        rows.append(f'''<section class="tc-week-plan-row{row_class}"><div class="head"><div><div class="day">{html.escape(session.date_label(ctx["today"]))} · {html.escape(session.status_label(ctx["today"]))}</div><div class="title">{html.escape(session.title)}</div></div><span>{html.escape(session.kind)}</span></div><div class="detail-grid"><p><b>功率</b>{html.escape(session.power)}</p><p><b>体感</b>{html.escape(session.feel)}</p><p><b>目的</b>{html.escape(session.purpose)}</p><p><b>降级</b>{html.escape(session.downgrade)}</p></div></section>''')
    week_rows_html = "\n      ".join(rows)
    week_html = f'''
    <div class="tc-week-summary">
      <div><div class="k">本周目标 · {html.escape(ctx["week_range"])}</div><div class="v">{html.escape(ctx.get("goal") or '提升 FTP / 阈值能力')}</div><p>可训练日：{html.escape('、'.join(ctx.get("training_days") or []))}；休息日：{html.escape('、'.join(rest_days) or '无')}。本周日期按当前电脑日期滚动；今天是 {html.escape(ctx["today"].strftime("%Y-%m-%d"))}，课表会自动标记今日、已过和待确认。</p></div>
      <div class="meta"><span>{html.escape(total_training_text)}</span><span>{html.escape(rest_text)}</span><span>{html.escape(quality_text)}</span></div>
    </div>
    <div class="tc-week-plan-list">
{week_rows_html}
    </div>
    <div class="tc-week-rule"><b>调整规则：</b>{html.escape(adaptive_rule)}</div>
    <div class="tc-week-plan-actions"><a target="_self" class="tc-week-btn primary" href="?nav=%E8%AE%AD%E7%BB%83%E8%AE%A1%E5%88%92&sub=%E6%9C%AC%E5%91%A8%E8%AF%BE%E8%A1%A8&action=export-week">导出课表</a><a target="_self" class="tc-week-btn" href="#tc-today-training-detail-modal-layer">返回今日详情</a></div>
    '''
    week_css = '''
#tc-week-plan-preview-modal { width:min(1120px, calc(100vw - 88px)); max-height:min(840px, calc(100vh - 72px)); }
.tc-week-summary { display:grid; grid-template-columns:1fr auto; gap:18px; align-items:center; border:1px solid rgba(240,111,50,.30); background:rgba(240,111,50,.10); border-radius:20px; padding:18px 20px; margin-bottom:14px; }
.tc-week-summary .k { color:#f06f32; font-size:13px; font-weight:850; letter-spacing:.08em; margin-bottom:6px; }
.tc-week-summary .v { color:#f4f0ea; font-size:22px; font-weight:830; letter-spacing:-.03em; margin-bottom:6px; }
.tc-week-summary p { color:#a7a19a; font-size:15px; line-height:1.6; margin:0; }
.tc-week-summary .meta { display:grid; gap:8px; justify-items:end; }
.tc-week-summary .meta span { color:#f5b84b; border:1px solid rgba(245,184,75,.30); background:rgba(245,184,75,.08); border-radius:999px; padding:7px 12px; font-size:13px; font-weight:760; white-space:nowrap; }
.tc-week-plan-list { display:grid; gap:13px; }
.tc-week-plan-row { border:1px solid rgba(255,255,255,.07); background:rgba(255,255,255,.035); border-radius:18px; padding:16px 18px; }
.tc-week-plan-row.today { background:rgba(66,211,146,.07); border-color:rgba(66,211,146,.24); }
.tc-week-plan-row .head { display:grid; grid-template-columns:1fr auto; gap:14px; align-items:start; margin-bottom:12px; }
.tc-week-plan-row .day { color:#f06f32; font-size:13px; font-weight:850; letter-spacing:.08em; margin-bottom:5px; }
.tc-week-plan-row .title { color:#f4f0ea; font-size:20px; font-weight:820; letter-spacing:-.025em; }
.tc-week-plan-row .head span { color:#58a6ff; border:1px solid rgba(88,166,255,.30); background:rgba(88,166,255,.08); border-radius:999px; padding:7px 12px; font-size:13px; font-weight:760; white-space:nowrap; }
.tc-week-plan-row .detail-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px 14px; }
.tc-week-plan-row p { color:#a7a19a; font-size:14px; line-height:1.55; margin:0; }
.tc-week-plan-row p b { color:#f4f0ea; margin-right:8px; }
.tc-week-rule { margin-top:14px; border:1px solid rgba(245,184,75,.22); background:rgba(245,184,75,.07); color:#c9b9a7; border-radius:16px; padding:13px 16px; font-size:14px; line-height:1.6; }
.tc-week-rule b { color:#f5b84b; }
.tc-week-plan-actions { display:flex; justify-content:flex-end; gap:12px; margin-top:18px; }
.tc-week-btn { height:44px; display:inline-flex; align-items:center; justify-content:center; border-radius:14px; padding:0 18px; text-decoration:none!important; color:#f4f0ea!important; background:#0d1219; border:1px solid #253244; font-weight:760; }
.tc-week-btn.primary { background:#f06f32; color:#11151b!important; border-color:#f06f32; }
'''
    week_script = '''
(() => {
  const doc = window.parent.document;
  doc.querySelectorAll('a[href="#tc-today-training-detail-modal-layer"]').forEach((link) => {
    link.addEventListener('click', () => {
      const weekLayer = doc.getElementById('tc-week-plan-preview-modal-layer');
      if (weekLayer) {
        weekLayer.classList.add('tc-saved-closed');
        weekLayer.classList.remove('tc-force-open');
        weekLayer.style.zIndex = '';
        weekLayer.style.pointerEvents = '';
        weekLayer.style.opacity = '';
      }
    });
  });
})();
'''
    render_mac_modal_window(
        title='本周课表预览',
        intro='这里先给你看本周训练安排的核心卡片，不直接跳走；确认后可以直接导出本周训练。',
        form_html=week_html,
        close_url='?nav=%E8%AE%AD%E7%BB%83%E9%A9%BE%E9%A9%B6%E8%88%B1&sub=%E9%A6%96%E9%A1%B5%E7%AE%80%E6%8A%A5',
        submit_label='关闭',
        window_id='tc-week-plan-preview-modal',
        extra_css=week_css,
        extra_script=week_script,
    )
