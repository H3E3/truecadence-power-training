from __future__ import annotations

import html

import streamlit as st

from .shell import _wrap


def render_help_page():
    body = '''
        <div class="grid-2 tc-upload-top">
          <section class="panel hot">
            <div class="code">SUPPORT</div><div class="label lime">帮助 · 隐私 · 更新</div>
            <div class="h1">先让用户知道数据怎么用。</div>
            <p class="txt">这里集中解释 TrueCadence 的数据边界、隐私原则、FIT / Intervals.icu 接入方式，以及内测版本更新。避免用户跳到旧版页面。</p>
          </section>
          <section class="panel">
            <div class="code">BETA</div><div class="label cyan">内测说明</div>
            <div class="h2">训练建议来自数据，但不替代教练判断</div>
            <p class="txt">TrueCadence 会根据上传 FIT、历史摘要、恢复反馈和骑手档案生成训练建议。数据不足时会保守提示，不强行下结论。</p>
          </section>
        </div>

        <div class="grid-3 mt">
          <section class="panel"><div class="code">PRIVACY</div><div class="label purple">隐私与数据</div><div class="h2">只用于当前骑手分析</div><p class="txt">FIT 和平台导入数据用于训练负荷、功率画像、恢复判断和课表建议。页面不展示密码、token、邀请码等敏感信息。</p></section>
          <section class="panel"><div class="code">IMPORT</div><div class="label cyan">数据接入</div><div class="h2">FIT 上传 + Intervals.icu</div><p class="txt">当前支持 FIT 上传和 Intervals.icu 导入。上传后的训练摘要会保存到当前骑手历史；同日期新记录会覆盖旧摘要并去重。</p></section>
          <section class="panel hot"><div class="code">CHANGELOG</div><div class="label rose">版本更新</div><div class="h2">正式版 UI 正在收口</div><p class="txt">近期重点是统一新版页面、降低认知负担，把专业训练逻辑翻译成普通骑友能看懂的结论和下一步动作。</p></section>
        </div>

        <div class="grid-2 mt">
          <section class="panel hot">
            <div class="code">USER CONTROL</div><div class="label green">用户可控</div>
            <div class="h2">可以继续上传，也可以清除历史</div>
            <p class="txt">上传与诊断页会显示历史训练数量。测试脏数据或重新建档时，可以在数据状态里确认后清除当前骑手历史。</p>
          </section>
          <section class="panel">
            <div class="code">BOUNDARY</div><div class="label warn">安全边界</div>
            <div class="h2">不做医学诊断</div>
            <p class="txt">如果出现持续疼痛、明显不适、异常心率、头晕或生病状态，应优先停止强度训练，并寻求线下教练、康复或医疗支持。</p>
          </section>
        </div>

        <div class="grid-2 mt">
          <section class="panel hot">
            <div class="code">FEEDBACK</div><div class="label cyan">问题反馈</div>
            <div class="h2">看不懂、数据不对、页面不好用，都从这里说。</div>
            <p class="txt">内测阶段反馈会记录问题页面、影响程度、复现步骤和期望表现。越具体，越容易优先修到关键体验。</p>
          </section>
          <section class="panel">
            <div class="code">FAST PATH</div><div class="label lime">反馈入口</div>
            <div class="h2">提交后会进入内测问题记录</div>
            <p class="txt">如果是训练建议看不懂、FIT 数据异常、手机端显示问题或套餐/权限问题，请直接提交反馈。</p>
          </section>
        </div>

        <div class="grid-4 mt">
          <a target="_self" class="accordion" href="?nav=帮助%20·%20隐私%20·%20更新&sub=反馈">提交问题反馈</a>
          <a target="_self" class="accordion" href="?nav=帮助%20·%20隐私%20·%20更新&sub=隐私">隐私与数据说明</a>
          <a target="_self" class="accordion" href="?nav=帮助%20·%20隐私%20·%20更新&sub=FIT说明">FIT / ICU 接入说明</a>
          <a target="_self" class="accordion" href="?nav=帮助%20·%20隐私%20·%20更新&sub=updates">查看版本更新</a>
        </div>
        '''
    _wrap('帮助 · 隐私 · 更新', '帮助 · 隐私 · 更新', body)


def _selected(value: str, current: str) -> str:
    return ' selected' if value == current else ''


def _help_nav_buttons(active: str = '') -> str:
    items = [
        ('帮助首页', '?nav=帮助%20·%20隐私%20·%20更新&sub=首页'),
        ('问题反馈', '?nav=帮助%20·%20隐私%20·%20更新&sub=反馈'),
        ('隐私与数据说明', '?nav=帮助%20·%20隐私%20·%20更新&sub=隐私'),
        ('FIT / ICU 接入说明', '?nav=帮助%20·%20隐私%20·%20更新&sub=FIT说明'),
        ('查看版本更新', '?nav=帮助%20·%20隐私%20·%20更新&sub=updates'),
    ]
    links = ''.join(f'<a target="_self" class="accordion" href="{href}">{html.escape(label)}</a>' for label, href in items if label != active)
    return f'<div class="grid-4 mt">{links}</div>'


def render_help_privacy_page():
    body = f'''
        <div class="grid-2 tc-upload-top">
          <section class="panel hot"><div class="code">PRIVACY</div><div class="label purple">隐私与数据说明</div><div class="h1">数据只为当前骑手分析服务。</div><p class="txt">TrueCadence 使用 FIT、平台导入数据、骑手档案、训练反馈和睡眠记录生成训练负荷、功率画像、恢复判断和课表建议。</p></section>
          <section class="panel"><div class="code">BOUNDARY</div><div class="label warn">边界</div><div class="h2">不展示敏感凭证，不做医学诊断</div><p class="txt">页面不展示密码、token、邀请码等敏感信息。持续疼痛、异常心率、头晕或生病状态，应优先停止强度训练并寻求线下专业支持。</p></section>
        </div>
        <div class="grid-3 mt">
          <section class="panel"><div class="code">FIT</div><div class="label cyan">训练数据</div><div class="h2">用于计算负荷和能力</div><p class="txt">上传或导入的训练摘要会保存到当前骑手历史，用于 PMC、功率曲线、训练建议、补给建议和 AI 分析。</p></section>
          <section class="panel"><div class="code">PROFILE</div><div class="label green">骑手档案</div><div class="h2">用于个性化判断</div><p class="txt">FTP、体重、训练目标、可训练日等会影响课表强度、周计划结构和恢复建议。</p></section>
          <section class="panel hot"><div class="code">CONTROL</div><div class="label lime">用户可控</div><div class="h2">可继续上传，也可清除历史</div><p class="txt">测试脏数据或重新建档时，可在上传与诊断页的数据状态里确认后清除当前骑手历史。</p></section>
        </div>
        {_help_nav_buttons('隐私与数据说明')}
    '''
    _wrap('隐私与数据说明', '帮助 · 隐私 · 更新', body)


def render_help_import_page():
    body = f'''
        <div class="grid-2 tc-upload-top">
          <section class="panel hot"><div class="code">IMPORT</div><div class="label cyan">FIT / ICU 接入说明</div><div class="h1">先把训练数据接进来，再谈分析。</div><p class="txt">当前支持 FIT 上传和 Intervals.icu 导入。系统会把训练摘要归到当前骑手历史里，同日期新记录会覆盖旧摘要并去重。</p></section>
          <section class="panel"><div class="code">TRUST</div><div class="label lime">数据可信度</div><div class="h2">优先看来源、时间和字段完整度</div><p class="txt">功率、心率、踏频、时间戳、暂停和采样缺失都会影响判断。数据不足时系统应保守提示，不强行下结论。</p></section>
        </div>
        <div class="grid-3 mt">
          <section class="panel"><div class="code">FIT</div><div class="label green">FIT 上传</div><div class="h2">适合码表/平台导出的原始活动</div><p class="txt">上传后可用于功率曲线、训练负荷、AI 诊断、训练计划和补给建议。</p></section>
          <section class="panel"><div class="code">ICU</div><div class="label blue">Intervals.icu</div><div class="h2">适合批量导入历史活动</div><p class="txt">连接后可读取平台活动摘要，减少手动上传成本。导入结果仍以当前骑手为单位保存。</p></section>
          <section class="panel hot"><div class="code">NEXT</div><div class="label rose">下一步</div><div class="h2">导入后看训练计划和专业数据</div><p class="txt">如果数据已经进入历史，优先查看今日训练建议、训练计划、功率能力数据和今日补给。</p></section>
        </div>
        {_help_nav_buttons('FIT / ICU 接入说明')}
    '''
    _wrap('FIT / ICU 接入说明', '帮助 · 隐私 · 更新', body)


def render_help_update_page():
    body = f'''
        <div class="grid-2 tc-upload-top">
          <section class="panel hot"><div class="code">CHANGELOG</div><div class="label rose">查看版本更新</div><div class="h1">近期重点：新版 UI 和训练闭环收口。</div><p class="txt">目标不是堆更多复杂功能，而是把专业训练逻辑压缩成普通骑友能看懂、能执行、能反馈的路径。</p></section>
          <section class="panel"><div class="code">V2</div><div class="label cyan">新版方向</div><div class="h2">简报 → 诊断 → 计划 → 恢复</div><p class="txt">训练驾驶舱、上传与诊断、训练计划、状态恢复、今日补给和帮助页正在统一到 V2 体验。</p></section>
        </div>
        <div class="grid-3 mt">
          <section class="panel"><div class="code">DONE</div><div class="label green">已接入</div><div class="h2">训练状态与课表门控</div><p class="txt">readiness、反馈回流、计划依据、4 周方向和今日补给已接入新版训练链路。</p></section>
          <section class="panel"><div class="code">FOCUS</div><div class="label lime">当前重点</div><div class="h2">减少跳旧版和无效入口</div><p class="txt">帮助、隐私、更新、反馈都应留在新版体系内，避免用户体验断层。</p></section>
          <section class="panel hot"><div class="code">NEXT</div><div class="label warn">后续</div><div class="h2">真实用户反馈驱动优化</div><p class="txt">优先处理影响理解、影响训练判断、手机端操作和数据可信度的问题。</p></section>
        </div>
        {_help_nav_buttons('查看版本更新')}
    '''
    _wrap('查看版本更新', '帮助 · 隐私 · 更新', body)


def render_feedback_page():

    saved = st.query_params.get('saved') == 'v2-beta-feedback'
    saved_html = '''
        <section class="panel hot mt">
          <div class="code">SAVED</div><div class="label green">已收到</div>
          <div class="h2">反馈已进入内测问题记录。</div>
          <p class="txt">谢谢，越具体的反馈越能帮助我们优先修到关键体验。如果需要回访，会按你留下的联系方式确认。</p>
        </section>
    ''' if saved else ''
    page_options = ["首页/功能说明", "注册/登录/内测邀请码", "骑手档案", "上传分析", "功率仪表盘", "训练负荷", "训练反馈", "恢复与睡眠", "AI 功率分析", "训练课表/ZWO", "营养与补给", "目标追踪", "套餐/权限", "手机端显示", "其他"]
    type_options = ["Bug/报错", "看不懂/需要解释", "数据不符合预期", "体验建议", "功能建议", "视觉/手机端", "其他"]
    severity_options = ["一般建议", "影响理解", "影响使用", "阻塞无法继续"]
    page_html = ''.join(f'<option value="{html.escape(x)}">{html.escape(x)}</option>' for x in page_options)
    type_html = ''.join(f'<option value="{html.escape(x)}">{html.escape(x)}</option>' for x in type_options)
    severity_html = ''.join(f'<option value="{html.escape(x)}">{html.escape(x)}</option>' for x in severity_options)
    body = f'''
        <div class="grid-2 tc-upload-top">
          <section class="panel hot">
            <div class="code">FEEDBACK</div><div class="label cyan">问题反馈</div>
            <div class="h1">问题、建议、看不懂，都从这里说。</div>
            <p class="txt">这个页面保持新版 V2 风格，不再跳回旧表单。反馈会保存到内测问题记录里，方便后续集中修复。</p>
          </section>
          <section class="panel">
            <div class="code">HOW TO</div><div class="label lime">越具体越好</div>
            <div class="h2">页面 + 操作步骤 + 看到的问题 + 期望结果</div>
            <p class="txt">例如：训练计划页，点击查看计划依据后看不懂为什么降级，希望用更直白的话解释。</p>
          </section>
        </div>
        {saved_html}
        <form class="tc-v2-beta-feedback-form mt" method="get" action="">
          <input type="hidden" name="nav" value="帮助 · 隐私 · 更新">
          <input type="hidden" name="sub" value="反馈">
          <input type="hidden" name="action" value="save-v2-beta-feedback">
          <section class="panel hot">
            <div class="code">FORM</div><div class="label cyan">提交反馈</div>
            <div class="tc-v2-form-grid">
              <label>联系方式 / 微信 / 手机<input name="contact" placeholder="方便回访时填写，可留空"></label>
              <label>问题页面<select name="feedback_page">{page_html}</select></label>
              <label>反馈类型<select name="issue_type">{type_html}</select></label>
              <label>影响程度<select name="severity">{severity_html}</select></label>
              <label class="wide">问题描述<textarea name="description" rows="4" placeholder="请描述你看到的问题，或者希望改进的地方。"></textarea></label>
              <label class="wide">操作步骤 / 复现方式<textarea name="steps" rows="3" placeholder="例如：登录 → 上传 FIT → 进入训练计划 → 点击某个按钮 → 出现……"></textarea></label>
              <label class="wide">你期望它怎么表现<textarea name="expected" rows="3" placeholder="例如：希望显示更明确的解释 / 希望按钮位置更明显 / 希望能导出……"></textarea></label>
              <label class="wide">快速三问：喜欢什么 / 吐槽什么 / 哪个功能值得付费<textarea name="quick_answers" rows="4" placeholder="可选，但很重要。"></textarea></label>
            </div>
            <button class="tc-v2-submit-feedback" type="submit">提交反馈</button>
          </section>
        </form>
        <div class="grid-4 mt">
          <a target="_self" class="accordion" href="?nav=帮助%20·%20隐私%20·%20更新&sub=首页">返回帮助首页</a>
          <a target="_self" class="accordion" href="?nav=帮助%20·%20隐私%20·%20更新&sub=隐私">隐私与数据说明</a>
          <a target="_self" class="accordion" href="?nav=帮助%20·%20隐私%20·%20更新&sub=FIT说明">FIT / ICU 接入说明</a>
          <a target="_self" class="accordion" href="?nav=帮助%20·%20隐私%20·%20更新&sub=updates">查看版本更新</a>
        </div>
        <style>
        .tc-v2-beta-feedback-form .panel {{ min-height:auto; height:auto; overflow:visible; }}
        .tc-v2-form-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; margin-top:8px; }}
        .tc-v2-form-grid label {{ display:grid; gap:8px; color:#f4f0ea; font-size:15px; font-weight:760; }}
        .tc-v2-form-grid label.wide {{ grid-column:1/-1; }}
        .tc-v2-form-grid input,.tc-v2-form-grid select,.tc-v2-form-grid textarea {{ width:100%; box-sizing:border-box; border-radius:16px; border:1px solid #2a211b; background:#090b0f; color:#f4f0ea; padding:13px 14px; font-size:15px; font-family:inherit; }}
        .tc-v2-form-grid textarea {{ resize:vertical; line-height:1.55; }}
        .tc-v2-submit-feedback {{ margin-top:18px; height:54px; min-width:180px; border-radius:16px; border:1px solid #253244; background:#0d1219; color:#f4f0ea; font-size:18px; font-weight:800; cursor:pointer; }}
        .tc-v2-submit-feedback:hover {{ border-color:#f06f32; box-shadow:0 0 14px rgba(240,111,50,.20); }}
        </style>
    '''
    _wrap('问题反馈', '帮助 · 隐私 · 更新', body)
