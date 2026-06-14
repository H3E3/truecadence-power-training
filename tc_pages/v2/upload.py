from __future__ import annotations

import html

import streamlit as st

from .shell import _wrap
from .modal_window import render_mac_modal_window
from .readiness_bridge import readiness_label_class, v2_readiness_context
from services.v2_ai_summary import build_v2_ai_summary


def _safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _fmt(value, suffix="", digits=0):
    v = _safe_float(value, None)
    if v is None:
        return "暂无"
    if digits == 0:
        return f"{v:.0f}{suffix}"
    return f"{v:.{digits}f}{suffix}"


def _history_rides():
    rides = []
    try:
        rides = list(st.session_state.get("last_import_rides") or st.session_state.get("uploaded_rides") or [])
    except Exception:
        rides = []
    try:
        from auth import load_rider_rides

        user = st.session_state.get("user") or {}
        rider = st.session_state.get("rider", "默认骑手")
        if user.get("user_id"):
            saved = load_rider_rides(user["user_id"], rider) or []
            if saved:
                rides = saved
    except Exception:
        pass
    return rides


def _latest_ride(rides):
    if not rides:
        return {}
    return sorted(rides, key=lambda r: str(r.get("date", "")), reverse=True)[0]


def _today_advice(rides):
    if not rides:
        return "暂无历史训练。先上传 1-2 次 FIT，再给今日状态提示。"
    r = _latest_ride(rides)
    dur = _safe_float(r.get("dur"))
    tss = _safe_float(r.get("tss"))
    if tss >= 85 or dur >= 150:
        return "上一骑负荷偏高：今天先保守，详细安排去训练计划看。"
    if tss >= 45 or dur >= 70:
        return "上一骑有训练刺激：今天以稳住节奏为主，不在上传页展开计划。"
    return "上一骑负担不重：状态判断先给初筛，具体怎么练到训练计划里看。"


def _power_summary(rides):
    if not rides:
        return "暂无功率历史。上传后只做初筛，完整能力分析放在功率能力数据页。"
    power_rides = [r for r in rides if _safe_float(r.get("avg_p")) or _safe_float(r.get("np")) or _safe_float(r.get("max_p"))]
    long_count = sum(1 for r in rides if _safe_float(r.get("dur")) >= 90)
    if len(power_rides) < 3:
        return f"{len(power_rides)} 条功率记录：先作为初筛，不急着判断强弱项。"
    if long_count < 2:
        return "已有功率记录，但长时间稳定性样本偏少；完整画像去功率能力数据页看。"
    return "数据已能支持初步判断；这里给入口级提示，完整能力结构不在上传页展开。"


def _escape(text: str) -> str:
    return html.escape(str(text or ""))


def _ai_quota_info():
    user = st.session_state.get("user") or {}
    uid = str(user.get("user_id") or "")
    plan_key = str(user.get("plan") or "free")
    plan_names = {"free": "免费版", "core": "Core版", "pro": "Pro版", "coach": "Coach版"}
    plan_name = plan_names.get(plan_key, plan_key or "免费版")
    unlimited = plan_key in ("pro", "coach")
    used = 0
    limit = 0
    try:
        from auth import get_ai_usage, get_ai_limit
        if uid:
            used = int(get_ai_usage(uid) or 0)
            limit = int(get_ai_limit(uid) or 0)
    except Exception:
        pass
    remaining = None if unlimited else max(0, limit - used)
    quota_text = "♾️ 不限次数" if unlimited else f"本月剩余 {remaining}/{limit} 次"
    billing_text = "Pro / Coach 生成 AI 分析不扣次数。" if unlimited else "点击正式生成 AI 分析会消耗 1 次额度；只查看当前说明不扣次数。"
    status_text = "额度充足" if unlimited or (remaining or 0) > 0 else "本月额度已用完"
    return {
        "plan_name": plan_name,
        "quota_text": quota_text,
        "billing_text": billing_text,
        "status_text": status_text,
        "unlimited": unlimited,
        "remaining": remaining,
        "limit": limit,
        "used": used,
    }


def render_upload_page(*, load_feedback=None, load_profile=None, load_sleep=None, compute_daily_pmc_func=None):
    rides = _history_rides()
    latest = _latest_ride(rides)
    history_count = len(rides)
    latest_line = "暂无历史记录"
    if latest:
        latest_line = f"最近一次：{_escape(latest.get('date', '未知日期'))} · {_fmt(latest.get('dur'), '分钟')} · 平均功率 {_fmt(latest.get('avg_p'), 'W')} · TSS {_fmt(latest.get('tss'))}"
    status_title = "已有历史记录" if history_count else "还没有历史记录"
    status_text = (
        f"当前骑手已保存 {history_count} 条训练摘要。关闭上传窗口后，这些记录仍会留在这里，不需要重复上传。"
        if history_count
        else "先上传 FIT 或连接 Intervals.icu。上传后系统会保存摘要，关闭窗口后仍能基于历史继续查看建议。"
    )
    today_text = _today_advice(rides)
    power_text = _power_summary(rides)
    ai_quota = _ai_quota_info()
    def _safe_call(loader, default):
        if not callable(loader):
            return default
        try:
            return loader()
        except Exception:
            return default

    def _safe_profile():
        return _safe_call(load_profile, {})

    def _safe_feedback():
        return _safe_call(load_feedback, [])

    def _safe_sleep():
        return _safe_call(load_sleep, [])

    readiness = v2_readiness_context(load_feedback=_safe_feedback, load_profile=_safe_profile, load_rides=lambda: rides, load_sleep=_safe_sleep, compute_daily_pmc_func=compute_daily_pmc_func)
    profile = _safe_profile()
    feedback = _safe_feedback()
    sleep_records = _safe_sleep()
    ai_summary = build_v2_ai_summary(rides=rides, profile=profile, feedback=feedback, sleep_records=sleep_records, readiness=readiness.as_dict())
    ai_label = readiness_label_class(ai_summary.get("readiness_level"))
    ai_modal_html = f'''
      <div class="tc-upload-ai-brief">
        <section class="wide quota"><div>套餐与 AI 次数</div><p>当前套餐：{_escape(ai_quota['plan_name'])}。{_escape(ai_quota['quota_text'])}。{_escape(ai_quota['billing_text'])} 状态：{_escape(ai_quota['status_text'])}。</p></section>
        <section class="wide hot"><div>AI 短结论 · {_escape(ai_summary.get('readiness_level'))}</div><p>{_escape(ai_summary.get('data_basis'))}</p></section>
        <section><span class="badge cyan">能力结论</span><div>现在强弱项怎么看</div><p>{_escape(ai_summary.get('ability'))}</p></section>
        <section><span class="badge warn">风险提醒</span><div>今天别硬顶什么</div><p>{_escape(ai_summary.get('risk'))}</p></section>
        <section><span class="badge rose">训练建议</span><div>接下来怎么练</div><p>{_escape(ai_summary.get('training'))}</p></section>
        <section><span class="badge green">恢复建议</span><div>怎么接住训练</div><p>{_escape(ai_summary.get('recovery'))}</p></section>
        <section class="wide next"><span class="badge {ai_label}">下一步</span><div>把分析落到行动</div><p>{_escape(ai_summary.get('next_step'))}</p></section>
      </div>
    '''

    body = f'''
        <div class="grid-2 tc-upload-top">
          <section class="panel hot">
            <div class="code">DATA IN</div><div class="label lime">导入训练数据</div>
            <div class="h1">先补齐最近骑行。</div>
            <p class="txt">上传 FIT 或连接 Intervals.icu。数据进来后，会保存到当前骑手历史；关闭窗口后不用重传。</p>
            <div class="actions"><a target="_self" class="btn primary" href="?nav=%E4%B8%8A%E4%BC%A0%E4%B8%8E%E8%AF%8A%E6%96%AD&sub=%E4%B8%8A%E4%BC%A0%20FIT&action=upload-fit">上传 FIT</a><a target="_self" class="btn primary" href="?nav=%E4%B8%8A%E4%BC%A0%E4%B8%8E%E8%AF%8A%E6%96%AD&sub=%E5%B9%B3%E5%8F%B0%E5%AF%BC%E5%85%A5&action=connect-icu">连接 ICU</a></div>
          </section>
          <section class="panel">
            <div class="code">HISTORY</div><div class="label cyan">{_escape(status_title)}</div>
            <div class="h2">{history_count} 条训练摘要</div>
            <p class="txt">{_escape(status_text)}</p>
            <p class="txt" style="margin-top:14px;color:#f0d9c8">{latest_line}</p>
            <p class="txt" style="margin-top:10px;color:#58a6ff">AI：{_escape(ai_quota['quota_text'])}</p>
            <div class="actions" style="margin-top:16px"><a target="_self" class="btn primary" href="#tc-upload-ai-modal-layer">AI 分析</a></div>
          </section>
        </div>
        <div class="grid-2 mt tc-upload-snapshot">
          <section id="tc-upload-status-card" class="panel hot">
            <div class="label rose">状态初筛</div>
            <div class="h2">只提示，不替代训练计划</div>
            <p class="txt">{_escape(today_text)}</p>
          </section>
          <section id="tc-upload-data-card" class="panel">
            <div class="label purple">数据线索</div>
            <div class="h2">只看够不够判断</div>
            <p class="txt">{_escape(power_text)}</p>
          </section>
        </div>
        <div class="grid-3 mt">
          <section class="panel">
            <div class="code">HOW TO READ</div><div class="label lime">上传后先确认什么</div>
            <div class="h2">先确认数据，再看结论</div>
            <p class="txt">上传完成后先确认数据是否进来、判断是否可信；具体今天怎么练、能力短板和本周安排，分别回到对应页面看。</p>
          </section>
          <section class="panel">
            <div class="code">CONFIDENCE</div><div class="label cyan">数据可信度</div>
            <div class="h2">记录越连续，判断越稳</div>
            <p class="txt">单次 FIT 可以做初判；连续 4-12 周数据更适合看趋势。数据不足时，系统会保守提示，不强行下结论。</p>
          </section>
          <section class="panel hot">
            <div class="code">HISTORY</div><div class="label rose">历史会保留</div>
            <div class="h2">不用每次重新上传</div>
            <p class="txt">FIT 解析后会合并进当前骑手历史。关闭窗口后仍能查看记录；后续上传同日期训练，会自动覆盖旧摘要并去重。</p>
          </section>
        </div>
        '''
    _wrap('上传与诊断', '上传与诊断', body)
    render_mac_modal_window(
        title='AI 分析短报告',
        intro='不搬旧版长报告；这里只保留能力、风险、训练、恢复和下一步 5 张短卡。',
        form_html=ai_modal_html,
        close_url='?nav=%E4%B8%8A%E4%BC%A0%E4%B8%8E%E8%AF%8A%E6%96%AD&sub=%E4%B8%8A%E4%BC%A0%20FIT',
        submit_label='关闭',
        window_id='tc-upload-ai-modal',
        extra_css='''
.tc-upload-ai-brief { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }
.tc-upload-ai-brief section { border:1px solid rgba(255,255,255,.07); background:rgba(255,255,255,.035); border-radius:18px; padding:18px 20px; }
.tc-upload-ai-brief section.wide { grid-column:1/-1; }
.tc-upload-ai-brief section.hot { background:rgba(240,111,50,.075); border-color:rgba(240,111,50,.22); }
.tc-upload-ai-brief section.quota { background:rgba(88,166,255,.075); border-color:rgba(88,166,255,.24); }
.tc-upload-ai-brief section.next { background:rgba(66,211,146,.055); border-color:rgba(66,211,146,.22); }
.tc-upload-ai-brief section div { color:#f4f0ea; font-size:18px; font-weight:780; margin:8px 0; }
.tc-upload-ai-brief section p { color:#a7a19a; font-size:15px; line-height:1.7; margin:0; }
.tc-upload-ai-brief section.wide p { color:#f0d9c8; }
.tc-upload-ai-brief .badge { display:inline-flex; align-items:center; height:26px; border-radius:999px; padding:0 10px; font-size:12px; font-weight:840; }
.tc-upload-ai-brief .badge.cyan { color:#58a6ff; background:rgba(88,166,255,.10); border:1px solid rgba(88,166,255,.24); }
.tc-upload-ai-brief .badge.warn { color:#f5b84b; background:rgba(245,184,75,.10); border:1px solid rgba(245,184,75,.24); }
.tc-upload-ai-brief .badge.rose { color:#ff7a90; background:rgba(255,122,144,.10); border:1px solid rgba(255,122,144,.24); }
.tc-upload-ai-brief .badge.green { color:#42d392; background:rgba(66,211,146,.10); border:1px solid rgba(66,211,146,.24); }


''',
    )
