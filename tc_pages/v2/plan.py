from __future__ import annotations

import html
import os
from pathlib import Path

import streamlit as st

from services.plan_preferences import DAY_ORDER, load_current_plan_prefs, save_current_plan_prefs
from services.training_calendar import fueling_advice_for_session, week_plan_context
from services.workout_export import workout_exports_for_item

from .modal_window import render_mac_modal_window
from .shell import _wrap, _url
from .readiness_bridge import readiness_label_class, v2_readiness_context




def _param_values(name: str) -> list[str]:
    if hasattr(st.query_params, "get_all"):
        values = st.query_params.get_all(name)
    else:
        value = st.query_params.get(name)
        values = value if isinstance(value, list) else ([value] if value is not None else [])
    expanded: list[str] = []
    for item in values:
        expanded.extend([part for part in str(item).split(',') if part])
    return expanded


def _handle_plan_settings_save() -> None:
    action = st.query_params.get("action")
    plan_action = st.query_params.get("plan_action")
    if isinstance(action, list):
        action = action[0] if action else None
    if isinstance(plan_action, list):
        plan_action = plan_action[0] if plan_action else None
    if plan_action == "export-week":
        _export_current_week_workouts()
        return
    if action != "save-settings" and plan_action != "save-settings":
        return
    training_days = [d for d in DAY_ORDER if d in _param_values("training_days")]
    no_hard_days = [d for d in DAY_ORDER if d in _param_values("no_hard_days") and d in training_days]
    preferred_long_day = str(st.query_params.get("preferred_long_day") or "")
    goal = str(st.query_params.get("goal") or "提升 FTP / 阈值能力")
    event_type = str(st.query_params.get("event_type") or "无比赛")
    event_date = str(st.query_params.get("event_date") or "").strip()
    event_priority = str(st.query_params.get("event_priority") or "B")
    if len(training_days) >= 3:
        current = load_current_plan_prefs()
        if preferred_long_day not in training_days:
            preferred_long_day = "周日" if "周日" in training_days else training_days[-1]
        save_current_plan_prefs({
            **current,
            "training_days": training_days,
            "preferred_long_day": preferred_long_day,
            "no_hard_days": no_hard_days,
            "goal": goal,
            "event_type": event_type,
            "event_date": event_date,
            "event_priority": event_priority,
        })
        st.toast("训练日设置已保存")
        st.query_params.clear()
        st.query_params["nav"] = "训练计划"
        st.query_params["sub"] = "本周课表"
        st.query_params["saved"] = "plan-settings"
        st.rerun()
    else:
        st.toast("请至少选择 3 个可训练日")

def _event_summary_text(ctx_or_prefs: dict) -> str:
    event_type = str(ctx_or_prefs.get("event_type") or "无比赛")
    event_date = str(ctx_or_prefs.get("event_date") or "").strip()
    priority = str(ctx_or_prefs.get("event_priority") or "B")
    if not event_date or event_type in ("无比赛", "未设置", ""):
        return "近期无明确比赛日期"
    try:
        import datetime as _dt
        target = _dt.date.fromisoformat(event_date)
        today = ctx_or_prefs.get("today") or _dt.datetime.now().date()
        if hasattr(today, "date") and not isinstance(today, _dt.date):
            today = today.date()
        days = (target - today).days
        if days > 0:
            timing = f"还有 {days} 天"
        elif days == 0:
            timing = "就是今天"
        else:
            timing = f"已过去 {abs(days)} 天"
    except Exception:
        timing = "日期待确认"
    return f"{event_type} · {event_date} · {priority} 级 · {timing}"


def _session_intensity_label(session) -> str:
    if session.is_rest:
        return "休息"
    title = session.title or ""
    if session.kind == "质量课" or "甜区" in title or "比赛模拟" in title:
        return "强度课"
    if session.kind == "耐力" or "长距离" in title:
        return "耐力课"
    if session.kind == "低强度" or "恢复" in title or "技术骑" in title:
        return "低强度"
    return "有氧课"


def _session_intensity_class(session) -> str:
    label = _session_intensity_label(session)
    if label == "强度课":
        return " intensity-hard"
    if label == "耐力课":
        return " intensity-long"
    if label == "低强度":
        return " intensity-easy"
    if label == "休息":
        return " intensity-rest"
    return " intensity-aerobic"


def _session_export_kind(session) -> str:
    title = session.title or ""
    if session.is_rest:
        return "rest"
    if "甜区" in title or session.kind == "质量课":
        return "sweet"
    if "长距离" in title or session.kind == "耐力":
        return "long"
    if "恢复" in title:
        return "recovery"
    return "z2"


def _session_export_duration_h(session) -> float:
    title = session.title or ""
    if session.is_rest:
        return 0.0
    if "2 小时" in title or "2小时" in title:
        return 2.0
    if "75–90" in title or "75-90" in title:
        return 1.35
    if "45–75" in title or "45-75" in title:
        return 1.0
    if "3×12" in title or "3x12" in title:
        return 1.25
    return 1.0


def _session_export_item(session) -> dict:
    return {
        "day": session.weekday_label,
        "name": session.title,
        "kind": _session_export_kind(session),
        "detail": session.detail,
        "dur_h": _session_export_duration_h(session),
        "rest": session.is_rest,
    }


def _export_current_week_workouts() -> None:
    ctx = week_plan_context(readiness=st.session_state.get("tc_v2_last_readiness"))
    export_dir = Path(os.path.expanduser("~/Documents/TrueCadence/Workouts/V2_Week"))
    export_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for session in ctx["sessions"]:
        item = _session_export_item(session)
        export_item = workout_exports_for_item(1, item, 250)
        if not export_item:
            continue
        fname, content = export_item["zwo"]
        path = export_dir / fname
        path.write_text(content, encoding="utf-8")
        written.append(path)
    st.session_state["tc_v2_export_notice"] = {
        "count": len(written),
        "path": str(export_dir),
    }
    st.query_params.clear()
    st.query_params["nav"] = "训练计划"
    st.query_params["sub"] = "本周课表"
    st.query_params["saved"] = "export-week"
    st.rerun()


def _plan_day_class(session, today) -> str:
    status = session.status(today)
    if status in ("today", "rest_today"):
        return " today"
    if status in ("past", "rest_past"):
        return " past"
    if session.is_rest:
        return " rest"
    return ""


def _plan_feedback_impact_html() -> str:
    notice = st.session_state.get("tc_v2_feedback_impact") or {}
    if not notice:
        return ""
    level = html.escape(str(notice.get("level") or "已更新"))
    headline = html.escape(str(notice.get("headline") or "最新反馈已回流到训练计划"))
    entry = html.escape(str(notice.get("entry_summary") or "已记录今日状态"))
    impact = html.escape(str(notice.get("impact") or "本周课表暂未触发自动降级。"))
    change_count = int(notice.get("change_count") or 0)
    change_label = f"影响 {change_count} 天训练" if change_count else "未触发自动降级"
    actions = notice.get("actions") or []
    action_text = "；".join(str(x) for x in actions[:2]) or "继续按当前计划执行，并记录下一次反馈。"
    return f'''
    <section class="tc-plan-feedback-impact">
      <div><span>反馈已回流</span><b>{html.escape(change_label)}</b></div>
      <h3>{headline} · {level}</h3>
      <p><strong>刚才反馈：</strong>{entry}</p>
      <p><strong>计划变化：</strong>{impact}</p>
      <p><strong>接下来：</strong>{html.escape(action_text)}</p>
      <div class="actions"><a target="_self" class="btn secondary" href="{_url('状态与恢复', '恢复睡眠')}">回看反馈</a><a target="_self" class="btn primary" href="#tc-plan-rationale-modal-layer">查看计划依据</a></div>
    </section>
    '''


def render_plan_page(*, load_feedback=None, load_profile=None, load_rides=None, load_sleep=None, compute_daily_pmc_func=None):
    readiness = v2_readiness_context(load_feedback=load_feedback, load_profile=load_profile, load_rides=load_rides, load_sleep=load_sleep, compute_daily_pmc_func=compute_daily_pmc_func)
    st.session_state["tc_v2_last_readiness"] = readiness.as_dict()
    _handle_plan_settings_save()
    ctx = week_plan_context(readiness=readiness)
    today_ctx = ctx["today_context"]
    event_text = _event_summary_text(ctx)
    readiness_label = readiness_label_class(readiness.level)

    day_items = []
    for session in ctx["sessions"]:
        simple_title = "休息" if session.is_rest else session.title
        day_items.append(
            f'''<a target="_self" class="tc-plan-day{_plan_day_class(session, ctx["today"])}" href="#tc-plan-day-{session.date.weekday()}-modal-layer">
              <span class="d">{html.escape(session.weekday_label)}</span>
              <strong>{html.escape(simple_title)}</strong>
            </a>'''
        )
    day_strip_html = "\n              ".join(day_items)

    next_training = next((s for s in ctx["training_sessions"] if s.date >= ctx["today"]), None)
    next_training_text = (
        f"{next_training.date_label(ctx['today'])} · {next_training.title}"
        if next_training
        else "本周训练已结束，准备进入下周滚动计划"
    )

    saved_notice = _plan_feedback_impact_html()
    if st.query_params.get('saved') == 'plan-settings':
        saved_notice += '<div class="tc-plan-saved"><span>已保存</span>训练日设置已同步更新：本周概览、今日建议和完整周计划使用同一份设置。</div>'
    elif st.query_params.get('saved') == 'export-week':
        export_notice = st.session_state.get('tc_v2_export_notice') or {}
        saved_notice += f'<div class="tc-plan-saved"><span>已导出</span>已生成 {int(export_notice.get("count") or 0)} 个 ZWO 训练文件：{html.escape(str(export_notice.get("path") or "~/Documents/TrueCadence/Workouts/V2_Week"))}</div>'
    body = f'''
        <style>
        .tc-plan-top{{display:grid;grid-template-columns:.9fr 1.1fr;gap:20px;align-items:stretch}}
        .tc-plan-settings{{min-height:300px;height:300px}}
        .tc-plan-settings .txt{{max-width:760px}}
        .tc-plan-settings .actions{{gap:10px}}
        .tc-plan-today{{min-height:300px;height:300px}}
        .tc-week-strip-panel{{margin-top:20px;min-height:260px;height:auto;padding:24px 24px 26px!important;overflow:hidden!important}}
        .tc-week-strip-head{{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;margin-bottom:16px}}
        .tc-week-strip-head .h2{{margin:0}}
        .tc-week-strip-head .txt{{max-width:520px;font-size:14px}}
        .tc-plan-strip{{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:8px;width:100%;box-sizing:border-box}}
        .tc-plan-day{{min-height:86px;border:1px solid rgba(244,240,234,.055);background:rgba(255,255,255,.02);border-radius:16px;padding:12px 10px;text-decoration:none!important;color:#f4f0ea!important;display:flex;flex-direction:column;justify-content:space-between;gap:8px;box-sizing:border-box;box-shadow:none!important;min-width:0}}
        .tc-plan-day:hover{{border-color:rgba(240,111,50,.24);background:rgba(240,111,50,.045)}}
        .tc-plan-day.today{{border-color:rgba(240,111,50,.48);background:linear-gradient(145deg,rgba(240,111,50,.15),rgba(255,255,255,.02) 62%)}}
        .tc-plan-day.rest{{background:rgba(255,255,255,.01);border-color:rgba(244,240,234,.04)}}
        .tc-plan-day.past{{opacity:.56}}
        .tc-plan-day .d{{color:#f06f32;font-size:12px;font-weight:850;letter-spacing:.04em}}
        .tc-plan-day strong{{font-size:14px;line-height:1.22;font-weight:760;letter-spacing:-.02em;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
        .tc-plan-day.rest strong{{color:#8d8881}}
        .tc-plan-accordions{{margin-top:20px}}
        .tc-plan-saved{{margin-bottom:12px;border:1px solid rgba(66,211,146,.22);background:rgba(66,211,146,.07);color:#b9d8c9;border-radius:14px;padding:9px 13px;font-size:13px;line-height:1.35}}
        .tc-plan-saved span{{display:inline-flex;margin-right:8px;color:#42d392;font-weight:820}}
        .tc-plan-feedback-impact{{margin-bottom:16px;border:1px solid rgba(240,111,50,.24);background:linear-gradient(145deg,rgba(240,111,50,.11),rgba(255,255,255,.025));border-radius:24px;padding:18px 22px;color:#f4f0ea}}
        .tc-plan-feedback-impact>div:first-child{{display:flex;align-items:center;gap:10px;margin-bottom:8px}}
        .tc-plan-feedback-impact span{{color:#f06f32;font-size:12px;font-weight:900;letter-spacing:.07em;text-transform:uppercase}}
        .tc-plan-feedback-impact b{{color:#f0d9c8;font-size:12px;font-weight:820;border:1px solid rgba(240,111,50,.22);border-radius:999px;padding:4px 9px;background:rgba(240,111,50,.07)}}
        .tc-plan-feedback-impact h3{{margin:0 0 8px;font-size:22px;letter-spacing:-.03em}}
        .tc-plan-feedback-impact p{{margin:5px 0;color:#bdb6ad;font-size:14px;line-height:1.55}}
        .tc-plan-feedback-impact p strong{{color:#f4f0ea}}
        .tc-plan-feedback-impact .actions{{margin-top:12px;gap:10px}}
        .tc-plan-mini{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px;margin-top:20px}}
        .tc-plan-mini .panel{{min-height:240px;height:auto}}
        .tc-plan-mini .panel .actions{{margin-top:14px}}
        </style>

        {saved_notice}
        <div class="tc-plan-top">
          <section class="panel hot tc-plan-settings">
            <div class="code">SETTINGS</div><div class="label lime">训练日设置</div>
            <div class="h1">客户自己决定哪天训练</div>
            <p class="txt">目标：{html.escape(ctx.get("goal") or '提升 FTP / 阈值能力')}。比赛：{html.escape(event_text)}。可训练日：{html.escape('、'.join(ctx["training_days"]))}。休息日：{html.escape('、'.join(ctx["rest_days"]) or '无')}。</p>
            <div class="actions"><a target="_self" class="btn primary" href="#tc-plan-settings-modal-layer">调整训练日</a><a target="_self" class="btn primary" href="#tc-week-plan-preview-modal-layer">查看完整周计划</a></div>
          </section>
          <section class="panel tc-plan-today">
            <div class="code">PLAN DETAIL · {html.escape(ctx["today"].strftime("%Y-%m-%d"))}</div><div class="label {readiness_label}">今日 / 本周安排 · {html.escape(readiness.level)}</div>
            <div class="h2">{html.escape(today_ctx["hero_title"])}</div>
            <p class="txt"><b>{html.escape(today_ctx["hero_label"])}</b>：{html.escape(today_ctx["hero_text"])}<br>依据：{html.escape(readiness.reason)}。本周策略已同步到下方 7 天课表。</p>
            <div class="actions"><a target="_self" class="btn primary" href="#tc-plan-day-{ctx['today'].weekday()}-modal-layer">查看今日详情</a><a target="_self" class="btn primary" href="#tc-plan-rationale-modal-layer">查看计划依据</a></div>
          </section>
        </div>

        <section class="panel tc-week-strip-panel">
          <div class="tc-week-strip-head">
            <div><div class="label green">{html.escape(ctx["week_range"])} 本周概览</div><div class="h2">7 天小卡，只看今天和大概安排</div></div>
            <p class="txt">点某一天查看单日训练详情；完整周计划在底部入口查看。</p>
          </div>
          <div class="tc-plan-strip">
              {day_strip_html}
          </div>
        </section>

        <div class="tc-plan-mini">
          <section class="panel hot"><div class="code">LONG</div><div class="label purple">长距离日</div><div class="h2">{html.escape(ctx["preferred_long_day"] or '未设置')}</div><p class="txt">长距离 / Z2 容量 / 模拟课优先放在这一天，客户可以在训练日设置里改。</p></section>
          <section class="panel"><div class="code">NO HARD</div><div class="label warn">不安排高强度日</div><div class="h2">{html.escape('、'.join(ctx["no_hard_days"]) or '未设置')}</div><p class="txt">这些天仍可安排 Z2、恢复、技术骑，但尽量避开阈值、VO2、冲刺。</p></section>
          <section class="panel"><div class="code">EXPORT</div><div class="label rose">导出课表</div><div class="h2">确认后再导出</div><p class="txt">页面展示和导出的课表应使用同一份训练日配置，避免看到一套、导出另一套。</p><div class="actions"><a target="_self" class="btn primary" href="?nav=%E8%AE%AD%E7%BB%83%E8%AE%A1%E5%88%92&sub=%E6%9C%AC%E5%91%A8%E8%AF%BE%E8%A1%A8&plan_action=export-week">导出课表</a></div></section>
        </div>

        <div class="grid-3 tc-plan-accordions">
          <a target="_self" class="accordion" href="#tc-plan-rationale-modal-layer">查看计划依据</a>
          <a target="_self" class="accordion" href="#tc-plan-settings-modal-layer">查看训练日设置</a>
          <a target="_self" class="accordion" href="#tc-four-week-direction-modal-layer">查看 4 周方向</a>
        </div>
        '''
    _wrap('训练计划', '训练计划', body)
    _render_plan_settings_modal(ctx)
    _render_plan_day_detail_modals(ctx)
    _render_plan_rationale_modal(ctx, readiness)
    _render_four_week_direction_modal(ctx, readiness)
    _render_week_plan_preview_modal(ctx)

def _render_plan_day_detail_modals(ctx: dict) -> None:
    day_css = '''
.tc-plan-day-detail { display:grid; gap:12px; }
.tc-plan-day-hero { border:1px solid rgba(240,111,50,.25); background:rgba(240,111,50,.085); border-radius:18px; padding:16px 18px; }
.tc-plan-day-hero .k { color:#f06f32; font-size:13px; font-weight:850; letter-spacing:.08em; margin-bottom:5px; }
.tc-plan-day-hero .v { color:#f4f0ea; font-size:22px; font-weight:830; letter-spacing:-.03em; margin-bottom:5px; }
.tc-plan-day-hero p { color:#f0d9c8; font-size:14px; line-height:1.55; margin:0; }
.tc-plan-day-detail-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }
.tc-plan-day-detail-card { border:1px solid rgba(255,255,255,.07); background:rgba(255,255,255,.035); border-radius:16px; padding:14px 16px; }
.tc-plan-day-detail-card .k { color:#f4f0ea; font-size:15px; font-weight:800; margin-bottom:6px; }
.tc-plan-day-detail-card p { color:#a7a19a; font-size:13.5px; line-height:1.55; margin:0; }
'''
    for session in ctx["sessions"]:
        fuel = fueling_advice_for_session(session)
        if session.is_rest:
            plan_text = "不安排结构化训练；如果想动，只做 20–30 分钟轻松转腿或散步。"
        else:
            plan_text = f"功率：{html.escape(session.power)}。体感：{html.escape(session.feel)}。"
        detail_html = f'''
        <div class="tc-plan-day-detail">
          <section class="tc-plan-day-hero"><div class="k">{html.escape(session.date_label(ctx['today']))} · {html.escape(session.status_label(ctx['today']))}</div><div class="v">{html.escape(session.title)}</div><p>{html.escape(session.purpose)}</p></section>
          <div class="tc-plan-day-detail-grid">
            <section class="tc-plan-day-detail-card"><div class="k">怎么练</div><p>{plan_text}</p></section>
            <section class="tc-plan-day-detail-card"><div class="k">降级规则</div><p>{html.escape(session.downgrade)}</p></section>
            <section class="tc-plan-day-detail-card"><div class="k">骑前 / 骑中</div><p>{html.escape(fuel.before)} {html.escape(fuel.during)}</p></section>
            <section class="tc-plan-day-detail-card"><div class="k">喝水 / 骑后</div><p>{html.escape(fuel.hydration)} {html.escape(fuel.after)}</p></section>
          </div>
        </div>
        '''
        render_mac_modal_window(
            title=f'{session.weekday_label}详情',
            intro='单日训练详情：只保留今天怎么练、怎么降级、怎么吃，避免做成大报告。',
            form_html=detail_html,
            close_url='?nav=%E8%AE%AD%E7%BB%83%E8%AE%A1%E5%88%92&sub=%E6%9C%AC%E5%91%A8%E8%AF%BE%E8%A1%A8',
            submit_label='关闭',
            window_id=f'tc-plan-day-{session.date.weekday()}-modal',
            extra_css=day_css,
        )


def _readiness_payload(readiness) -> dict:
    if readiness is None:
        return {}
    if isinstance(readiness, dict):
        return readiness
    if hasattr(readiness, "as_dict"):
        return readiness.as_dict()
    return {
        "level": getattr(readiness, "level", ""),
        "headline": getattr(readiness, "headline", ""),
        "reason": getattr(readiness, "reason", ""),
        "intensity_cap": getattr(readiness, "intensity_cap", "normal"),
        "actions": getattr(readiness, "actions", []) or [],
        "source": getattr(readiness, "source", {}) or {},
    }


def _plan_gate_changes(ctx: dict) -> str:
    prefs = {
        "training_days": list(ctx.get("training_days") or []),
        "preferred_long_day": ctx.get("preferred_long_day"),
        "no_hard_days": list(ctx.get("no_hard_days") or []),
        "goal": ctx.get("goal") or "提升 FTP / 阈值能力",
    }
    baseline = week_plan_context(ctx.get("today"), prefs, readiness=None)
    changes = []
    for before, after in zip(baseline["sessions"], ctx["sessions"]):
        if before.title != after.title or before.kind != after.kind:
            changes.append(f"{after.weekday_label}：{before.title} → {after.title}")
    return "；".join(changes) or "本周课表未触发自动降级，按原计划推进。"


def _readiness_source_text(source: dict) -> str:
    if not source:
        return "暂无可展示来源。"
    parts = []
    feedback_count = int(source.get("feedback_count") or 0)
    sleep_count = int(source.get("sleep_count") or 0)
    parts.append(f"近期反馈 {feedback_count} 条")
    parts.append(f"睡眠记录 {sleep_count} 条")
    if source.get("pmc_available"):
        parts.append(
            f"PMC：CTL {source.get('ctl', 0)} / ATL {source.get('atl', 0)} / TSB {source.get('tsb', 0)}；"
            f"近 7 天 {source.get('tss_7', 0)} TSS / {source.get('hours_7', 0)}h；"
            f"近 28 天 {source.get('tss_28', 0)} TSS / {source.get('hours_28', 0)}h"
        )
        if source.get("latest_ride_date"):
            parts.append(f"最新骑行：{source.get('latest_ride_date')}")
    else:
        parts.append("缺少近期 FIT/PMC，负荷判断按保守规则处理")
    return "；".join(parts)


def _render_plan_rationale_modal(ctx: dict, readiness=None) -> None:
    goal = ctx.get('goal') or '提升 FTP / 阈值能力'
    event_text = _event_summary_text(ctx)
    payload = _readiness_payload(readiness)
    level = payload.get("level") or ctx.get("readiness_level") or "未计算"
    cap = payload.get("intensity_cap") or ctx.get("readiness_cap") or "normal"
    headline = payload.get("headline") or "按本周状态生成计划"
    reason = payload.get("reason") or "暂无状态原因"
    actions = payload.get("actions") or []
    action_text = "；".join(str(x) for x in actions[:3]) or "按当前课表执行，并继续记录反馈。"
    source_text = _readiness_source_text(payload.get("source") or {})
    gate_changes = _plan_gate_changes(ctx)
    hard_sessions = [s for s in ctx['sessions'] if _session_intensity_label(s) == '强度课']
    long_sessions = [s for s in ctx['sessions'] if _session_intensity_label(s) == '耐力课']
    hard_summary = '、'.join(f"{s.weekday_label} {s.title}" for s in hard_sessions) or '本周不安排明显强度课'
    long_summary = '、'.join(f"{s.weekday_label} {s.title}" for s in long_sessions) or '本周不安排长距离重点课'
    if cap == "recovery":
        gate_rule = "恢复优先：所有训练日转为恢复骑或休息，暂停结构化高强度。"
    elif cap == "caution":
        gate_rule = "谨慎推进：质量课降为 Z2 45–60 分钟，长距离缩短到 Z2 75–90 分钟，普通 Z2 和休息日保留。"
    else:
        gate_rule = "可推进：状态允许按原计划执行，不额外加码。"
    if '恢复' in goal:
        strategy = '恢复优先：降低强度，先恢复训练连续性。'
    elif '减脂' in goal:
        strategy = '可持续消耗：以 Z2、Tempo 和训练频率为主，不靠高强度硬顶制造疲劳。'
    elif '比赛' in goal:
        strategy = '专项推进：保留比赛节奏或阈值相关刺激，同时用长距离日维持耐力底座。'
    elif '长距离' in goal:
        strategy = '耐力优先：提高 Z2 连续时间和补给耐受，强度课从属于长距离能力建设。'
    else:
        strategy = 'FTP 推进：保留轻甜区 / 阈值基础刺激，其余训练用 Z2 和恢复支撑完成质量。'
    rationale_html = f'''
    <div class="tc-plan-rationale-grid">
      <section class="wide hot"><div>1. 本周结论：{html.escape(level)}</div><p><b>{html.escape(headline)}</b><br>{html.escape(reason)}</p></section>
      <section><div>2. 目标与约束</div><p>目标：<b>{html.escape(goal)}</b>。比赛：{html.escape(event_text)}。可训练日：{html.escape('、'.join(ctx['training_days']))}；休息日：{html.escape('、'.join(ctx['rest_days']) or '无')}。长距离优先：{html.escape(ctx['preferred_long_day'] or '未设置')}；不高强日：{html.escape('、'.join(ctx['no_hard_days']) or '未设置')}。</p></section>
      <section><div>3. 数据来源</div><p>{html.escape(source_text)}</p></section>
      <section class="wide"><div>4. 门控规则</div><p><b>{html.escape(gate_rule)}</b><br>实际变化：{html.escape(gate_changes)}</p></section>
      <section><div>5. 本周策略</div><p>{html.escape(strategy)} 当前强度课：{html.escape(hard_summary)}；耐力重点：{html.escape(long_summary)}。</p></section>
      <section><div>6. 执行动作</div><p>{html.escape(action_text)} 今日建议读取门控后的当天结果：{html.escape(ctx['today_context']['hero_label'])}：{html.escape(ctx['today_context']['hero_title'])}。</p></section>
    </div>
    '''
    rationale_css = '''
.tc-plan-rationale-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }
.tc-plan-rationale-grid section { border:1px solid rgba(255,255,255,.07); background:rgba(255,255,255,.035); border-radius:18px; padding:18px 20px; }
.tc-plan-rationale-grid section.wide { grid-column:1/-1; background:rgba(240,111,50,.075); border-color:rgba(240,111,50,.22); }
.tc-plan-rationale-grid section div { color:#f4f0ea; font-size:18px; font-weight:780; margin-bottom:8px; }
.tc-plan-rationale-grid section p { color:#a7a19a; font-size:15px; line-height:1.7; margin:0; }
.tc-plan-rationale-grid section p b { color:#f4f0ea; font-weight:850; }
.tc-plan-rationale-grid section.wide p { color:#f0d9c8; }
'''
    render_mac_modal_window(
        title='计划依据',
        intro='这里说明本周课表为什么这样排，不跳回旧页面。',
        form_html=rationale_html,
        close_url='?nav=%E8%AE%AD%E7%BB%83%E8%AE%A1%E5%88%92&sub=%E6%9C%AC%E5%91%A8%E8%AF%BE%E8%A1%A8',
        submit_label='关闭',
        window_id='tc-plan-rationale-modal',
        extra_css=rationale_css,
    )

def _four_week_focus(goal: str, readiness=None) -> list[tuple[str, str, str]]:
    payload = _readiness_payload(readiness)
    cap = payload.get("intensity_cap") or "normal"
    level = payload.get("level") or ""
    reason = payload.get("reason") or ""
    if cap == "recovery":
        return [
            ("第 1 周", "恢复优先", f"当前状态：{level or '恢复优先'}。先取消结构化高强度，用休息、恢复骑和稳定睡眠把身体拉回可训练状态。"),
            ("第 2 周", "恢复连续性", "如果睡眠、腿感和疼痛反馈好转，恢复 2–4 次低强度训练；仍不急着加甜区、阈值或 VO2。"),
            ("第 3 周", "轻刺激试探", "连续反馈稳定后，再加入 1 次很轻的 Tempo / 甜区下沿；一旦腿疲劳或疼痛反弹，立刻退回 Z2。"),
            ("第 4 周", "重新定方向", "根据 3 周反馈决定回到 FTP、长距离、减脂或比赛目标；如果仍恢复差，继续恢复周期而不是硬进阶。"),
        ]
    if cap == "caution":
        return [
            ("第 1 周", "谨慎承接", f"当前状态：{level or '谨慎推进'}。本周先把质量课和长距离降一点，核心是完成稳定，不追刺激。"),
            ("第 2 周", "看反馈再恢复强度", "如果本周反馈变好，下周恢复 1 次质量课；如果仍腿沉、睡眠差或补给失败，继续 Z2 与恢复骑。"),
            ("第 3 周", "目标刺激周", "只有在连续反馈稳定时，才把目标课加回原计划；否则保持保守推进，避免连续两周硬顶。"),
            ("第 4 周", "吸收调整", "降低总量，复盘哪类训练最容易触发疲劳；下一轮从可恢复的训练开始加。"),
        ]
    if reason and reason != "暂无状态原因":
        status_note = f"当前状态允许推进：{reason}。"
    else:
        status_note = "当前状态允许按目标推进。"
    if "减脂" in goal:
        return [
            ("第 1 周", "建立节奏", status_note + "先稳定训练频率，控制强度，把 Z2 和 Tempo 的可持续性找回来。"),
            ("第 2 周", "轻微加量", "有氧时间小幅增加，保持 1 次 Tempo / Z2 上沿训练，提高总消耗。"),
            ("第 3 周", "目标刺激", "围绕可持续消耗做重点周，不靠高强度硬顶，避免恢复成本过高。"),
            ("第 4 周", "吸收调整", "降低总量，保留轻刺激，根据体重、睡眠和腿感决定下个周期。"),
        ]
    if "比赛" in goal:
        return [
            ("第 1 周", "建立节奏", status_note + "恢复训练频率，确认身体能接住基础有氧和轻质量课。"),
            ("第 2 周", "专项推进", "保留 1 次比赛节奏训练，长距离日继续建立耐力底座。"),
            ("第 3 周", "比赛模拟", "加入更明确的比赛模拟或阈值节奏，但不把训练骑成测试。"),
            ("第 4 周", "吸收调整", "降低总量，保留短刺激，根据反馈决定是否进入下一轮专项。"),
        ]
    if "恢复" in goal:
        return [
            ("第 1 周", "恢复连续性", status_note + "先把训练频率恢复起来，强度压低，不急着证明能力。"),
            ("第 2 周", "轻微加量", "有氧时间小幅增加，观察睡眠、腿感和心率反应。"),
            ("第 3 周", "稳定基础", "如果恢复良好，加入很轻的节奏刺激；否则继续 Z2 和恢复骑。"),
            ("第 4 周", "吸收复盘", "降低总量，复盘哪些训练能接住，决定是否进入 FTP 或耐力目标。"),
        ]
    if "长距离" in goal:
        return [
            ("第 1 周", "建立节奏", status_note + "先保证 Z2 连续性和补给执行，不临时拉超长。"),
            ("第 2 周", "耐力加量", "长距离日略加时长，其他日用 Z2 支撑，不堆太多强度。"),
            ("第 3 周", "耐力重点", "重点看长距离后半程稳定性和补给耐受。"),
            ("第 4 周", "吸收调整", "降低总量，让身体吸收耐力刺激，再决定是否继续加长。"),
        ]
    return [
        ("第 1 周", "建立节奏", status_note + "恢复训练频率，先确认身体能接住本周安排。"),
        ("第 2 周", "轻微加量", "有氧时间小幅增加，保留 1 次轻甜区训练。"),
        ("第 3 周", "目标刺激", "根据 FTP 目标加强甜区 / 阈值基础，但不做硬测试。"),
        ("第 4 周", "吸收调整", "降低总量，保留轻刺激，根据反馈决定下一轮周期。"),
    ]


def _render_four_week_direction_modal(ctx: dict, readiness=None) -> None:
    goal = ctx.get('goal') or '提升 FTP / 阈值能力'
    payload = _readiness_payload(readiness)
    level = payload.get("level") or ctx.get("readiness_level") or "未计算"
    reason = payload.get("reason") or "暂无状态原因"
    cards = []
    for week, title, text in _four_week_focus(goal, readiness):
        cards.append(f'<section><div class="k">{html.escape(week)}</div><div class="v">{html.escape(title)}</div><p>{html.escape(text)}</p></section>')
    direction_html = f'''
    <div class="tc-four-week-summary"><div class="k">当前目标 · {html.escape(level)}</div><div class="v">{html.escape(goal)}</div><p>{html.escape(reason)}。这里不是 12 周大课表，只说明接下来 4 周训练方向；每天怎么练仍以本周计划滚动更新。</p></div>
    <div class="tc-four-week-grid">{''.join(cards)}</div>
    '''
    direction_css = '''
.tc-four-week-summary { border:1px solid rgba(240,111,50,.28); background:rgba(240,111,50,.09); border-radius:18px; padding:16px 18px; margin-bottom:14px; }
.tc-four-week-summary .k, .tc-four-week-grid .k { color:#f06f32; font-size:13px; font-weight:850; letter-spacing:.08em; margin-bottom:5px; }
.tc-four-week-summary .v { color:#f4f0ea; font-size:22px; font-weight:830; letter-spacing:-.03em; margin-bottom:6px; }
.tc-four-week-summary p { color:#f0d9c8; font-size:14px; line-height:1.6; margin:0; }
.tc-four-week-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }
.tc-four-week-grid section { border:1px solid rgba(255,255,255,.07); background:rgba(255,255,255,.035); border-radius:16px; padding:14px 16px; }
.tc-four-week-grid .v { color:#f4f0ea; font-size:17px; font-weight:820; margin-bottom:6px; }
.tc-four-week-grid p { color:#a7a19a; font-size:13.5px; line-height:1.58; margin:0; }
'''
    render_mac_modal_window(
        title='4 周方向',
        intro='只看周期方向，不展开 12 周大课表，避免主页面变重。',
        form_html=direction_html,
        close_url='?nav=%E8%AE%AD%E7%BB%83%E8%AE%A1%E5%88%92&sub=%E6%9C%AC%E5%91%A8%E8%AF%BE%E8%A1%A8',
        submit_label='关闭',
        window_id='tc-four-week-direction-modal',
        extra_css=direction_css,
    )


def _render_week_plan_preview_modal(ctx: dict) -> None:
    rows = []
    hard_sessions = [s for s in ctx['sessions'] if _session_intensity_label(s) == '强度课']
    hard_summary = '、'.join(f"{s.weekday_label} {s.title}" for s in hard_sessions) or '本周不安排明显强度课'
    for session in ctx['sessions']:
        row_class = ' today' if session.status(ctx['today']) in ('today', 'rest_today') else ' past' if session.status(ctx['today']) in ('past', 'rest_past') else ''
        intensity_label = _session_intensity_label(session)
        rows.append(f'''<section class="tc-plan-full-row{row_class}{_session_intensity_class(session)}"><div class="head"><div><div class="day">{html.escape(session.date_label(ctx['today']))} · {html.escape(session.status_label(ctx['today']))}</div><div class="title">{html.escape(session.title)}</div></div><span>{html.escape(intensity_label)}</span></div><div class="detail-grid"><p><b>功率</b>{html.escape(session.power)}</p><p><b>体感</b>{html.escape(session.feel)}</p><p><b>目的</b>{html.escape(session.purpose)}</p><p><b>降级</b>{html.escape(session.downgrade)}</p></div></section>''')
    rows_html = '\n      '.join(rows)
    week_html = f'''
    <div class="tc-plan-full-summary">
      <div><div class="k">本周课表 · {html.escape(ctx['week_range'])}</div><div class="v">{len(ctx['training_sessions'])} 天训练 · {len(ctx['rest_days'])} 天休息</div><p>目标：{html.escape(ctx.get('goal') or '提升 FTP / 阈值能力')}。强度课：{html.escape(hard_summary)}。</p></div>
      <div class="meta"><span>长距离：{html.escape(ctx['preferred_long_day'] or '未设置')}</span><span>不高强：{html.escape('、'.join(ctx['no_hard_days']) or '未设置')}</span></div>
    </div>
    <div class="tc-plan-full-list">
      {rows_html}
    </div>
    '''
    week_css = '''
#tc-week-plan-preview-modal { width:min(1120px, calc(100vw - 88px)); max-height:min(840px, calc(100vh - 72px)); }
.tc-plan-full-summary { display:grid; grid-template-columns:1fr auto; gap:18px; align-items:center; border:1px solid rgba(240,111,50,.30); background:rgba(240,111,50,.10); border-radius:20px; padding:18px 20px; margin-bottom:14px; }
.tc-plan-full-summary .k { color:#f06f32; font-size:13px; font-weight:850; letter-spacing:.08em; margin-bottom:6px; }
.tc-plan-full-summary .v { color:#f4f0ea; font-size:22px; font-weight:830; letter-spacing:-.03em; margin-bottom:6px; }
.tc-plan-full-summary p { color:#a7a19a; font-size:15px; line-height:1.6; margin:0; }
.tc-plan-full-summary .meta { display:grid; gap:8px; justify-items:end; }
.tc-plan-full-summary .meta span { color:#f5b84b; border:1px solid rgba(245,184,75,.30); background:rgba(245,184,75,.08); border-radius:999px; padding:7px 12px; font-size:13px; font-weight:760; white-space:nowrap; }
.tc-plan-full-list { display:grid; gap:13px; }
.tc-plan-full-row { border:1px solid rgba(255,255,255,.07); background:rgba(255,255,255,.035); border-radius:18px; padding:16px 18px; }
.tc-plan-full-row.today { background:rgba(66,211,146,.07); border-color:rgba(66,211,146,.24); }
.tc-plan-full-row.intensity-hard { border-left:4px solid #f06f32; background:rgba(240,111,50,.055); }
.tc-plan-full-row.intensity-long { border-left:4px solid #a78bfa; }
.tc-plan-full-row.intensity-easy { border-left:4px solid #42d392; }
.tc-plan-full-row.intensity-aerobic { border-left:4px solid #58a6ff; }
.tc-plan-full-row.intensity-rest { border-left:4px solid rgba(244,240,234,.18); }
.tc-plan-full-row.past { opacity:.62; }
.tc-plan-full-row .head { display:grid; grid-template-columns:1fr auto; gap:14px; align-items:start; margin-bottom:12px; }
.tc-plan-full-row .day { color:#f06f32; font-size:13px; font-weight:850; letter-spacing:.08em; margin-bottom:5px; }
.tc-plan-full-row .title { color:#f4f0ea; font-size:20px; font-weight:820; letter-spacing:-.025em; }
.tc-plan-full-row .head span { color:#58a6ff; border:1px solid rgba(88,166,255,.30); background:rgba(88,166,255,.08); border-radius:999px; padding:7px 12px; font-size:13px; font-weight:760; white-space:nowrap; }
.tc-plan-full-row.intensity-hard .head span { color:#f06f32; border-color:rgba(240,111,50,.38); background:rgba(240,111,50,.10); }
.tc-plan-full-row.intensity-long .head span { color:#a78bfa; border-color:rgba(167,139,250,.36); background:rgba(167,139,250,.09); }
.tc-plan-full-row.intensity-easy .head span { color:#42d392; border-color:rgba(66,211,146,.34); background:rgba(66,211,146,.08); }
.tc-plan-full-row.intensity-rest .head span { color:#8d8881; border-color:rgba(244,240,234,.12); background:rgba(255,255,255,.025); }
.tc-plan-full-row .detail-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px 14px; }
.tc-plan-full-row p { color:#a7a19a; font-size:14px; line-height:1.55; margin:0; }
.tc-plan-full-row p b { color:#f4f0ea; margin-right:8px; }
'''
    render_mac_modal_window(
        title='完整周计划',
        intro='这里查看本周 7 天完整安排，不跳回旧页面。',
        form_html=week_html,
        close_url='?nav=%E8%AE%AD%E7%BB%83%E8%AE%A1%E5%88%92&sub=%E6%9C%AC%E5%91%A8%E8%AF%BE%E8%A1%A8',
        submit_label='关闭',
        window_id='tc-week-plan-preview-modal',
        extra_css=week_css,
    )


def _plan_settings_link_script() -> str:
    return """
(() => {
  const doc = window.parent.document;
  const form = doc.querySelector('.tc-plan-settings-form');
  if (!form || form.dataset.tcPlanLinked === '1') return;
  form.dataset.tcPlanLinked = '1';
  const trainChecks = () => Array.from(form.querySelectorAll('input[name="training_days"]'));
  const noHardChecks = () => Array.from(form.querySelectorAll('input[name="no_hard_days"]'));
  const longSelect = form.querySelector('select[name="preferred_long_day"]');
  const dayOrder = ['周一','周二','周三','周四','周五','周六','周日'];
  const sync = () => {
    const selected = new Set(trainChecks().filter(x => x.checked).map(x => x.value));
    if (longSelect) {
      Array.from(longSelect.options).forEach(opt => {
        const enabled = selected.has(opt.value);
        opt.disabled = !enabled;
        opt.hidden = !enabled;
      });
      if (!selected.has(longSelect.value)) {
        const next = Array.from(longSelect.options).find(opt => selected.has(opt.value));
        if (next) longSelect.value = next.value;
      }
    }
    noHardChecks().forEach(input => {
      const enabled = selected.has(input.value);
      input.disabled = !enabled;
      if (!enabled) input.checked = false;
      const label = input.closest('label');
      if (label) label.classList.toggle('tc-disabled-day', !enabled);
    });
    const summary = form.querySelector('[data-tc-plan-live-summary]');
    if (summary) {
      const training = dayOrder.filter(day => selected.has(day));
      const rest = dayOrder.filter(day => !selected.has(day));
      const longDay = longSelect ? longSelect.value : '';
      summary.innerHTML = `
        <div><b>当前可训练日</b><span>${training.length ? training.join('、') : '未选择'}</span></div>
        <div><b>当前休息日</b><span>${rest.length ? rest.join('、') : '无'}</span></div>
        <div><b>长距离日</b><span>${longDay || '未设置'}</span></div>
      `;
    }
    form.dataset.trainingCount = String(selected.size);
  };
  trainChecks().forEach(input => input.addEventListener('change', sync));
  sync();
})();
"""


def _render_plan_settings_modal(ctx: dict) -> None:
    prefs = load_current_plan_prefs()
    training_days = set(prefs.get('training_days') or [])
    no_hard_days = set(prefs.get('no_hard_days') or [])
    preferred_long_day = prefs.get('preferred_long_day') or ctx.get('preferred_long_day') or '周日'
    current_goal = prefs.get('goal') or '提升 FTP / 阈值能力'
    current_event_type = prefs.get('event_type') or '无比赛'
    current_event_date = prefs.get('event_date') or ''
    current_event_priority = prefs.get('event_priority') or 'B'
    goal_options = ['提升 FTP / 阈值能力', '减脂 / 体重管理', '比赛备赛', '恢复体能 / 重建基础', '长距离耐力']
    goal_options_html = ''.join(f'<option value="{html.escape(goal)}"{" selected" if goal == current_goal else ""}>{html.escape(goal)}</option>' for goal in goal_options)
    event_options = ['无比赛', '公路赛', '绕圈赛', '爬坡赛', '个人计时赛', '长距离骑行', '其他']
    event_options_html = ''.join(f'<option value="{html.escape(item)}"{" selected" if item == current_event_type else ""}>{html.escape(item)}</option>' for item in event_options)
    priority_options_html = ''.join(f'<option value="{item}"{" selected" if item == current_event_priority else ""}>{item} 级</option>' for item in ['A', 'B', 'C'])
    day_checks = []
    long_options = []
    no_hard_checks = []
    for day in DAY_ORDER:
        checked = ' checked' if day in training_days else ''
        no_hard_checked = ' checked' if day in no_hard_days else ''
        selected = ' selected' if day == preferred_long_day else ''
        safe_day = html.escape(day)
        day_checks.append(f'<label><input type="checkbox" name="training_days" value="{safe_day}"{checked}> <span>{safe_day}</span></label>')
        no_hard_checks.append(f'<label><input type="checkbox" name="no_hard_days" value="{safe_day}"{no_hard_checked}> <span>{safe_day}</span></label>')
        long_options.append(f'<option value="{safe_day}"{selected}>{safe_day}</option>')
    settings_html = f'''
    <form class="tc-plan-settings-form" method="get" action="">
      <input type="hidden" name="nav" value="训练计划">
      <input type="hidden" name="sub" value="本周课表">
      <input type="hidden" name="plan_action" value="save-settings">
      <section class="wide"><div>训练目标</div><p>先决定这一阶段练什么，再决定哪几天能练。</p><select name="goal">{goal_options_html}</select></section>
      <section><div>比赛类型</div><p>轻量记录，只影响计划说明和后续周期方向，不生成完整备赛大课表。</p><select name="event_type">{event_options_html}</select></section>
      <section><div>比赛日期</div><p>如果没有明确日期可以留空；有日期时计划依据会显示倒计时。</p><input type="date" name="event_date" value="{html.escape(str(current_event_date), quote=True)}"></section>
      <section class="wide"><div>赛事优先级</div><p>A 是年度重点，B 是重要目标，C 是练习赛 / 体验赛。</p><select name="event_priority">{priority_options_html}</select></section>
      <section class="wide"><div>可训练日</div><p>选择客户通常可以训练的日期；没选的日期就是休息日。这里会实时更新，点击保存后主页面才会刷新。</p><div class="day-grid">{''.join(day_checks)}</div><div class="tc-plan-live-summary" data-tc-plan-live-summary></div></section>
      <section><div>长距离日</div><p>长距离 / Z2 容量 / 模拟课优先放在这一天。</p><select name="preferred_long_day">{''.join(long_options)}</select></section>
      <section><div>不安排高强度日</div><p>这些天仍可安排 Z2、恢复、技术骑，但避开阈值、VO2 和冲刺。</p><div class="day-grid compact">{''.join(no_hard_checks)}</div></section>
      <button class="tc-plan-save-btn" type="submit">保存训练日设置</button>
    </form>
    '''
    settings_css = '''
.tc-plan-settings-form { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }
.tc-plan-settings-form section { border:1px solid rgba(255,255,255,.07); background:rgba(255,255,255,.035); border-radius:18px; padding:18px 20px; }
.tc-plan-settings-form section.wide { grid-column:1/-1; background:rgba(240,111,50,.075); border-color:rgba(240,111,50,.22); }
.tc-plan-settings-form section div { color:#f4f0ea; font-size:18px; font-weight:780; margin-bottom:8px; }
.tc-plan-settings-form section p { color:#a7a19a; font-size:15px; line-height:1.7; margin:0 0 12px; }
.tc-plan-settings-form .day-grid { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:8px; }
.tc-plan-settings-form .day-grid.compact { grid-template-columns:repeat(4,minmax(0,1fr)); }
.tc-plan-settings-form label { min-height:42px; border:1px solid rgba(255,255,255,.08); background:rgba(255,255,255,.035); border-radius:13px; display:flex; align-items:center; justify-content:center; gap:7px; color:#f4f0ea; font-size:14px; font-weight:760; transition:background .16s ease,border-color .16s ease,color .16s ease,opacity .16s ease; }
.tc-plan-live-summary { margin-top:12px; display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; }
.tc-plan-live-summary div { border:1px solid rgba(240,111,50,.24); background:rgba(240,111,50,.09); border-radius:13px; padding:10px 12px; margin:0 !important; }
.tc-plan-live-summary b { display:block; color:#f06f32; font-size:12px; letter-spacing:.05em; margin-bottom:4px; }
.tc-plan-live-summary span { display:block; color:#fff4ea; font-size:14px; line-height:1.45; font-weight:760; }
.tc-plan-settings-form label:has(input:checked) { background:rgba(240,111,50,.16); border-color:rgba(240,111,50,.48); color:#fff4ea; box-shadow:0 0 0 1px rgba(240,111,50,.10) inset; }
.tc-plan-settings-form label.tc-disabled-day { opacity:.36; filter:saturate(.55); }
.tc-plan-settings-form input[type="checkbox"] { accent-color:#f06f32; }
.tc-plan-settings-form select option:disabled { color:#6f6860; }
.tc-plan-settings-form select, .tc-plan-settings-form input[type="date"] { width:100%; height:44px; border-radius:14px; border:1px solid rgba(255,255,255,.12); background:#0d1219; color:#f4f0ea; padding:0 12px; font-weight:760; box-sizing:border-box; }
.tc-plan-save-btn { grid-column:1/-1; height:46px; border:0; border-radius:15px; background:#f06f32; color:#11151b; font-weight:820; font-size:15px; cursor:pointer; }
'''
    render_mac_modal_window(
        title='调整训练日',
        intro='在当前新版页面里设置训练日；未选择的日期就是休息日。',
        form_html=settings_html,
        close_url='?nav=%E8%AE%AD%E7%BB%83%E8%AE%A1%E5%88%92&sub=%E6%9C%AC%E5%91%A8%E8%AF%BE%E8%A1%A8',
        submit_label='关闭',
        window_id='tc-plan-settings-modal',
        extra_css=settings_css,
        extra_script=_plan_settings_link_script(),
    )
