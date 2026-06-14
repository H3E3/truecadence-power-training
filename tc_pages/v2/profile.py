from __future__ import annotations

import html

import streamlit as st

from services.plan_preferences import DAY_ORDER, load_current_plan_prefs
from services.rider_profile_service import goal_training_background, profile_completeness
from .shell import _wrap
from .modal_window import render_mac_modal_window
from .profile_modal import render_profile_edit_modal


def render_profile_page(profile: dict | None = None, load_rider_profile=None):
    profile = profile or {}
    rider_name = profile.get('name') or '默认骑手'
    ftp = profile.get('ftp_test') or profile.get('ftp') or 0
    weight = profile.get('weight') or 0
    goal = profile.get('goal') or '未设置训练目标'
    training_bg_title, training_bg_text = goal_training_background(goal)
    plan_prefs = load_current_plan_prefs()
    training_days = list(plan_prefs.get('training_days') or [])
    rest_days = [day for day in DAY_ORDER if day not in training_days]
    preferred_long_day = plan_prefs.get('preferred_long_day') or '未设置'
    no_hard_days = list(plan_prefs.get('no_hard_days') or [])
    training_days_text = '、'.join(training_days) or '未设置'
    rest_days_text = '、'.join(rest_days) or '无'
    no_hard_days_text = '、'.join(no_hard_days) or '未设置'
    safe_rider_name = html.escape(str(rider_name))
    safe_goal = html.escape(str(goal))
    safe_training_bg_title = html.escape(training_bg_title)
    safe_training_bg_text = html.escape(training_bg_text)
    completeness, missing_text = profile_completeness(profile)
    safe_missing_text = html.escape(str(missing_text))
    user = st.session_state.get('user') or {}
    riders = (user.get('riders') or {}) if isinstance(user, dict) else {}
    is_coach = user.get('plan') == 'coach'
    rider_count = len(riders) or 1
    rider_count_text = f"当前账号 {rider_count}/20 位骑手" if is_coach else "当前套餐支持 1 位骑手"
    body = f'''
        <style>
        .tc-profile-hero-card .label{{height:32px;padding:0 15px;border-radius:16px;font-size:16px;margin-bottom:12px}}
        .tc-profile-hero-card .h1{{font-size:38px;line-height:1.02;margin:0 0 10px}}
        .tc-profile-hero-card [data-tc-profile-summary]{{max-width:980px;padding-right:300px;line-height:1.55}}
        .tc-profile-hero-card .actions{{position:absolute;right:32px;bottom:28px;margin:0}}
        .tc-profile-hero-card .btn{{height:48px;font-size:19px;padding:0 20px}}
        </style>
        <section class="panel hot tc-profile-hero-card"><div class="code">PROFILE</div><div class="label slate">基础信息</div><div class="h1" data-tc-profile-name>{safe_rider_name}</div><p class="txt" data-tc-profile-summary>FTP {ftp or '未填'}W · {weight or '未填'}kg · 训练目标：{safe_goal}。资料完整度 {completeness}%{safe_missing_text}。</p><div class="actions"><a target="_self" class="btn primary" href="#tc-profile-edit-modal-layer">编辑骑手档案</a></div></section>
        <div class="grid-3 mt"><section class="panel"><div class="code">RIDER</div><div class="label cyan">骑手状态</div><div class="h2">当前档案</div><p class="txt" data-tc-rider-count>{html.escape(rider_count_text)}。当前骑手：正在编辑的档案。</p></section><section class="panel"><div class="code">BACKGROUND</div><div class="label purple">训练背景</div><div class="h2" data-tc-training-bg-title>{safe_training_bg_title}</div><p class="txt" data-tc-training-bg-text>{safe_training_bg_text}</p></section><section class="panel hot"><div class="code">NOTE</div><div class="label warn">注意事项</div><div class="h2">疼痛/生病未记录</div><p class="txt">若有不适，计划强度应先降级。</p></section></div>
        <div class="grid-2 mt"><section class="panel"><div class="label lime">可训练日</div><div class="h2">{html.escape(training_days_text)}</div><p class="txt">休息日：{html.escape(rest_days_text)}。长距离优先：{html.escape(str(preferred_long_day))}。不高强日：{html.escape(no_hard_days_text)}。此处与训练计划设置使用同一份数据。</p><div class="actions"><a target="_self" class="btn primary" href="?nav=%E8%AE%AD%E7%BB%83%E8%AE%A1%E5%88%92&sub=%E6%9C%AC%E5%91%A8%E8%AF%BE%E8%A1%A8#tc-plan-settings-modal-layer">调整训练日</a></div></section><section class="panel"><div class="label slate">数据来源</div><div class="h2">训练计划设置</div><p class="txt">训练日、长距离日和不高强日来自同一份计划偏好；保存训练计划设置后，骑手档案会同步显示。</p></section></div>
        <div class="grid-3 mt"><a target="_self" class="accordion" href="#tc-profile-history-modal-layer">查看历史资料变更</a><a target="_self" class="accordion" href="#tc-profile-privacy-modal-layer">隐私与数据说明</a><a target="_self" class="accordion" href="#tc-profile-data-source-modal-layer">数据接入说明</a></div>
        '''
    _wrap('骑手档案', '骑手档案', body)
    rider = st.session_state.get('rider') or '默认骑手'
    safe_load_rider_profile = load_rider_profile or (lambda user_id, rider_name: {})
    render_profile_edit_modal(profile=profile, user=user, rider=rider, load_rider_profile=safe_load_rider_profile)
    _render_profile_info_modals()


def _profile_modal_content(items: list[tuple[str, str]]) -> str:
    rows = ''.join(
        f'<section class="tc-profile-info-row"><div class="tc-profile-info-title">{html.escape(title)}</div><p>{html.escape(text)}</p></section>'
        for title, text in items
    )
    return f'<div class="tc-profile-info-list">{rows}</div>'


def _render_profile_info_modals() -> None:
    close_url = '?nav=%E9%AA%91%E6%89%8B%E6%A1%A3%E6%A1%88&sub=%E9%AA%91%E6%89%8B%E8%B5%84%E6%96%99'
    info_css = '''
.tc-profile-info-list { display:grid; gap:14px; }
.tc-profile-info-row { border:1px solid rgba(255,255,255,.07); background:rgba(255,255,255,.035); border-radius:18px; padding:18px 20px; }
.tc-profile-info-title { color:#f4f0ea; font-size:18px; font-weight:780; margin-bottom:8px; }
.tc-profile-info-row p { color:#a7a19a; font-size:15px; line-height:1.7; margin:0; }
'''
    render_mac_modal_window(
        title='历史资料变更',
        intro='这里先作为新版档案页的资料变更入口。后续接入真实档案版本记录后，会展示每次保存的时间、字段和变更摘要。',
        form_html=_profile_modal_content([
            ('当前状态', '新版骑手档案页已基本完成，暂不继续深接数据。'),
            ('后续接入', '等待其他页面完成后，再统一接入真实资料版本、训练设置和反馈记录。'),
            ('展示规则', '只展示和骑手档案相关的变更摘要，不暴露敏感登录信息。'),
        ]),
        close_url=close_url,
        submit_label='关闭',
        window_id='tc-profile-history-modal',
        extra_css=info_css,
    )
    render_mac_modal_window(
        title='隐私与数据说明',
        intro='说明骑手档案页展示的数据边界。当前页面以本地账号和当前骑手资料为主，不在此处外发数据。',
        form_html=_profile_modal_content([
            ('本页数据', '基础信息来自当前骑手档案；套餐与骑手数量来自当前登录账号。'),
            ('训练设置', '可训练日、长距离日和不高强日来自训练计划设置；保存后骑手档案同步展示。'),
            ('隐私原则', '不在页面展示密码、token、邀请码等敏感信息；客户/骑手数据只用于当前功能展示。'),
        ]),
        close_url=close_url,
        submit_label='关闭',
        window_id='tc-profile-privacy-modal',
        extra_css=info_css,
    )
    render_mac_modal_window(
        title='数据接入说明',
        intro='说明这些卡片未来会从哪里取真实数据，避免把当前占位内容误认为最终计算结果。',
        form_html=_profile_modal_content([
            ('训练背景', '来自骑手档案里的训练目标，并通过目标映射成训练背景说明。'),
            ('可训练日', '已接入训练计划设置里的 training_days / preferred_long_day / no_hard_days 字段。'),
            ('注意事项', '后续应接入训练反馈里的 pains、specials、notes，以及恢复/睡眠风险提示。'),
        ]),
        close_url=close_url,
        submit_label='关闭',
        window_id='tc-profile-data-source-modal',
        extra_css=info_css,
    )
