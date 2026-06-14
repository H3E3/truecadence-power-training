from __future__ import annotations

import datetime
import html

import streamlit as st

from services.training_calendar import fueling_advice_for_session, week_plan_context

from .modal_window import render_mac_modal_window
from .shell import _wrap, _url
from .readiness_bridge import readiness_label_class, v2_readiness_context


def _feedback_impact_notice_html() -> str:
    if st.query_params.get('saved') != 'v2-feedback':
        return ''
    notice = st.session_state.get('tc_v2_feedback_impact') or {}
    level = html.escape(str(notice.get('level') or '已保存'))
    headline = html.escape(str(notice.get('headline') or '今日反馈已记录'))
    entry = html.escape(str(notice.get('entry_summary') or '已记录今日状态'))
    reason = html.escape(str(notice.get('reason') or '页面会重新读取状态。'))
    impact = html.escape(str(notice.get('impact') or '本周课表暂未触发自动降级。'))
    actions = notice.get('actions') or []
    actions_html = ''.join(f'<li>{html.escape(str(x))}</li>' for x in actions[:3]) or '<li>继续记录反馈，下一次进入页面会按最新状态计算。</li>'
    return f'''
    <section class="tc-feedback-impact">
      <div class="tag">已保存 · {level}</div>
      <div class="title">{headline}</div>
      <p><b>这条反馈：</b>{entry}</p>
      <p><b>为什么：</b>{reason}</p>
      <p><b>影响后续：</b>{impact}</p>
      <ul>{actions_html}</ul>
    </section>
    '''


def render_recovery_page(*, load_feedback=None, load_profile=None, load_rides=None, load_sleep=None, compute_daily_pmc_func=None):
    readiness = v2_readiness_context(load_feedback=load_feedback, load_profile=load_profile, load_rides=load_rides, load_sleep=load_sleep, compute_daily_pmc_func=compute_daily_pmc_func)
    ctx = week_plan_context(readiness=readiness)
    session = ctx["today_context"]["session"]
    fuel = fueling_advice_for_session(session)
    readiness_label = readiness_label_class(readiness.level)
    saved_notice = _feedback_impact_notice_html()
    body = f'''
        <style>
        .tc-feedback-impact{{margin-bottom:18px;border:1px solid rgba(66,211,146,.24);background:linear-gradient(145deg,rgba(66,211,146,.11),rgba(255,255,255,.025));border-radius:24px;padding:18px 22px;color:#f4f0ea}}
        .tc-feedback-impact .tag{{display:inline-flex;color:#42d392;font-size:12px;font-weight:880;letter-spacing:.06em;text-transform:uppercase;margin-bottom:8px}}
        .tc-feedback-impact .title{{font-size:22px;font-weight:860;letter-spacing:-.03em;margin-bottom:8px}}
        .tc-feedback-impact p{{margin:6px 0;color:#bdb6ad;line-height:1.55;font-size:14px}}
        .tc-feedback-impact p b{{color:#f4f0ea;font-weight:850}}
        .tc-feedback-impact ul{{margin:9px 0 0 18px;color:#d6ccc0;line-height:1.55;font-size:14px}}
        </style>
        {saved_notice}
        <div class="grid-2 tc-upload-top">
          <section class="panel hot">
            <div class="code">READINESS</div><div class="label {readiness_label}">今日恢复判断 · {html.escape(readiness.level)}</div>
            <div class="h1">{html.escape(readiness.headline)}</div>
            <p class="txt">今天对应：{session.title}。{html.escape(readiness.actions[0] if readiness.actions else '状态一般时先按计划下沿执行')}；补给按这堂课的强度和时长来，不是简单多吃胶或硬加咖啡因。</p>
            <div class="actions"><a target="_self" class="btn primary" href="#tc-recovery-feedback-modal-layer">记录今日反馈</a></div>
          </section>
          <section class="panel">
            <div class="code">WHY</div><div class="label warn">为什么这样判断</div>
            <div class="h2">{html.escape(readiness.reason)}</div>
            <p class="txt">{fuel.headline}。该补碳水就补碳水，该喝水和电解质就补，不用靠刺激物硬顶。</p>
          </section>
        </div>

        <div class="grid-3 mt">
          <section class="panel"><div class="code">DO</div><div class="label cyan">今天可以做</div><div class="h2">{session.title} · {fuel.headline}</div><p class="txt">{fuel.before} {fuel.during}</p></section>
          <section class="panel"><div class="code">AVOID</div><div class="label rose">今天先别做</div><div class="h2">不临时加码 · 不靠补剂硬顶</div><p class="txt">{ctx["today_context"]["avoid_text"]} {fuel.caffeine} 如果热身后功率上不去、心率偏高，直接降级，而不是再补一包胶继续顶。</p></section>
          <section class="panel hot"><div class="code">IF TIRED</div><div class="label lime">如果仍然腿沉</div><div class="h2">按降级规则处理 · 骑后补正餐</div><p class="txt">{session.downgrade}。如果缩短到 60 分钟以内，骑中以水为主；如果仍超过 60 分钟，保留对应碳水。{fuel.after}</p></section>
        </div>

        <div class="grid-2 mt">
          <section class="panel hot">
            <div class="code">RECOVERY INPUTS</div><div class="label green">需要关注的信号</div>
            <div class="h2">补水、电解质跟出汗量走</div>
            <p class="txt">睡眠、腿感、心率、胃口和出汗量一起看。{fuel.hydration} 胃口差、空腹或低血糖感明显时，先按骑前建议补碳水再谈训练。</p>
          </section>
          <section class="panel">
            <div class="code">NEXT PLAN</div><div class="label cyan">对训练计划的影响</div>
            <div class="h2">今天的目标：训练完成 + 补给匹配</div>
            <p class="txt">今天不是统一“吃胶模板”，而是按 {session.kind} / {session.title} 来补。补给跟上，后面训练才有质量；如果今天硬顶又吃不够，下一节质量课大概率需要降级。</p>
          </section>
        </div>

        <div class="grid-2 mt">
          <a target="_self" class="accordion blue" href="{_url('状态与恢复', '营养补给')}">今天吃什么</a>
          <a target="_self" class="accordion" href="{_url('训练计划', '本周课表')}">查看计划依据</a>
        </div>
        '''
    _wrap('状态与恢复', '状态与恢复', body)
    _render_feedback_modal()


def _options(options, selected):
    return ''.join(f'<option value="{html.escape(str(opt))}"{" selected" if str(opt) == str(selected) else ""}>{html.escape(str(opt))}</option>' for opt in options)


def _render_feedback_modal() -> None:
    today = datetime.date.today().isoformat()
    pain_options = ["膝盖", "腰", "颈肩", "手麻", "坐垫压迫", "脚麻/脚痛", "髋/臀", "跟腱/小腿"]
    special_options = ["感冒", "发烧", "睡眠不足", "饮酒", "出差/旅行", "天气太热", "天气太冷", "工作压力大"]
    pain_checks = ''.join(f'<label><input type="checkbox" name="pains" value="{html.escape(x)}"> <span>{html.escape(x)}</span></label>' for x in pain_options)
    special_checks = ''.join(f'<label><input type="checkbox" name="specials" value="{html.escape(x)}"> <span>{html.escape(x)}</span></label>' for x in special_options)
    form_html = f'''
    <form class="tc-v2-feedback-form" method="get" action="">
      <input type="hidden" name="nav" value="状态与恢复">
      <input type="hidden" name="sub" value="恢复睡眠">
      <input type="hidden" name="action" value="save-v2-feedback">
      <section class="wide"><div>今日状态</div><p>反馈会用于恢复判断、AI 分析和后续训练计划降级逻辑。</p></section>
      <label>日期<input type="date" name="date" value="{today}"></label>
      <label>睡眠质量<select name="sleep_quality">{_options([1,2,3,4,5], 3)}</select></label>
      <label>精神状态<select name="energy">{_options([1,2,3,4,5], 3)}</select></label>
      <label>腿部疲劳<select name="leg_fatigue">{_options([1,2,3,4,5], 3)}</select></label>
      <label>完成度<select name="completion">{_options(["未训练", "轻松完成", "正常完成", "勉强完成", "没完成"], "正常完成")}</select></label>
      <label>RPE 主观强度<select name="rpe">{_options([1,2,3,4,5,6,7,8,9,10], 5)}</select></label>
      <label>腿感<select name="leg_feel">{_options(["正常", "轻松", "沉", "酸", "抽筋", "发软"], "正常")}</select></label>
      <label>补给情况<select name="fueling">{_options(["正常", "吃少了", "喝少了", "胃不舒服", "低血糖感", "不适用"], "正常")}</select></label>
      <section><div>不适</div><div class="check-grid">{pain_checks}</div></section>
      <section><div>特殊情况</div><div class="check-grid">{special_checks}</div></section>
      <label class="wide">备注<textarea name="notes" rows="3" placeholder="例如：今天腿沉、没做完间歇、补给吃少了、右膝外侧不舒服。"></textarea></label>
      <button class="tc-v2-feedback-save" type="submit">保存今日反馈</button>
    </form>
    '''
    css = '''
.tc-v2-feedback-form { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }
.tc-v2-feedback-form .wide { grid-column:1/-1; }
.tc-v2-feedback-form section, .tc-v2-feedback-form label { border:1px solid rgba(255,255,255,.07); background:rgba(255,255,255,.035); border-radius:16px; padding:13px 15px; color:#f4f0ea; font-size:14px; font-weight:760; display:grid; gap:8px; }
.tc-v2-feedback-form section.wide { background:rgba(240,111,50,.075); border-color:rgba(240,111,50,.22); }
.tc-v2-feedback-form section div:first-child { color:#f4f0ea; font-size:16px; font-weight:820; }
.tc-v2-feedback-form section p { color:#f0d9c8; font-size:14px; line-height:1.55; margin:0; }
.tc-v2-feedback-form input, .tc-v2-feedback-form select, .tc-v2-feedback-form textarea { width:100%; border-radius:12px; border:1px solid rgba(255,255,255,.12); background:#0d1219; color:#f4f0ea; padding:9px 10px; font-weight:700; box-sizing:border-box; }
.tc-v2-feedback-form .check-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:7px; }
.tc-v2-feedback-form .check-grid label { min-height:34px; padding:7px 8px; display:flex; align-items:center; justify-content:center; gap:6px; font-size:12px; }
.tc-v2-feedback-form input[type="checkbox"] { width:auto; accent-color:#f06f32; }
.tc-v2-feedback-save { grid-column:1/-1; height:44px; border:0; border-radius:14px; background:#f06f32; color:#11151b; font-weight:850; font-size:15px; cursor:pointer; }
'''
    render_mac_modal_window(
        title='记录今日反馈',
        intro='轻量记录今天状态和训练反馈，不跳回旧版页面。',
        form_html=form_html,
        close_url='?nav=%E7%8A%B6%E6%80%81%E4%B8%8E%E6%81%A2%E5%A4%8D&sub=%E6%81%A2%E5%A4%8D%E7%9D%A1%E7%9C%A0',
        submit_label='关闭',
        window_id='tc-recovery-feedback-modal',
        extra_css=css,
    )
