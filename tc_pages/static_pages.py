from __future__ import annotations

import streamlit as st
from tc_pages.v2.router import render_v2_page


def render_home_page():
    render_v2_page("dashboard")


def render_changelog_page():
    st.title("📌 更新日志")
    st.caption("内测阶段的修复、优化和计划。这里不展示具体用户昵称,只记录来自内测反馈的产品改进。")

    st.markdown("""
<style>
.log-card { background:var(--tc-surface); border:1px solid var(--tc-border); border-radius:14px; padding:1em 1.05em; margin:.8em 0; }
.log-card .date { color:#ff9a68; font-size:.82em; font-weight:850; letter-spacing:.08em; margin-bottom:.4em; }
.log-card .title { color:#f0f6fc; font-size:1.08em; font-weight:800; margin-bottom:.45em; }
.log-card .text { color:#aab6c3; font-size:.9em; line-height:1.75; }
.log-pill { display:inline-block; border:1px solid rgba(255,107,53,.35); color:#ffb088; border-radius:999px; padding:.12em .55em; margin:.1em .25em .1em 0; font-size:.78em; }
</style>
<div class="log-card">
  <div class="date">下一阶段计划</div>
  <div class="title">正式版 UI 全面设计与平台同步</div>
  <div class="text">
    <span class="log-pill">正式 UI</span> 全面整理首页、导入、分析、课表、恢复、营养和套餐页面,让用户一眼知道现在状态、问题原因和下一步该做什么。<br>
    <span class="log-pill">更易懂</span> 减少内测感和技术表达,把复杂指标翻译成更简单的训练结论、风险提示和操作按钮。<br>
    <span class="log-pill">课程同步</span> 推进 Intervals.icu 课程同步,让 TrueCadence 生成的训练课可以更方便地进入日常训练平台。<br>
    <span class="log-pill">基础信息同步</span> 推进骑手基础信息同步,减少 FTP、体重、心率区间、训练目标等信息在多个平台重复填写。<br>
    <span class="log-pill">稳定上线</span> 正式版 UI 和同步能力会分批上线,每一批都先验证数据保存、训练判断和导出/同步稳定性。
  </div>
</div>
<div class="log-card">
  <div class="date">2026-06-02</div>
  <div class="title">代码拆分上线、功率曲线修正与套餐订单门禁</div>
  <div class="text">
    <span class="log-pill">架构</span> 完成一轮核心代码拆分上线,将训练指标、FIT 解析、功率分析、页面模块、数据导入和 UI 组件进一步拆开,降低后续维护和线上修复风险。<br>
    <span class="log-pill">修复</span> 修正数据导入后分析流程中部分解析结果未能继续进入训练指标计算的问题,上传 / 导入后的功率、TSS 和训练负荷会更稳定地衔接到后续页面。<br>
    <span class="log-pill">修复</span> 功率持续时间曲线增加单调性保护:更长时间窗口的最佳功率不会再高于更短时间窗口,避免 60min 高于 40min 等不符合训练常识的显示。<br>
    <span class="log-pill">修复</span> Coach 当前套餐用户不再能重复选择 Core / Pro / Coach 生成开通订单;当前套餐和低等级套餐会禁用,避免误下单。<br>
    <span class="log-pill">验证</span> 上线前后完成本地编译、训练指标/训练规则/导出回归、线上服务状态、HTTP、公网页面和近期日志检查。
  </div>
</div>
<div class="log-card">
  <div class="date">2026-06-01</div>
  <div class="title">自动课表稳定推进、TSS口径统一与训练反馈删除修复</div>
  <div class="text">
    <span class="log-pill">新增</span> 自动课表新增「训练背景与稳定推进」设置,可填写训练经验、停训时间、历史最佳 FTP / W/kg 和推进偏好;系统会优先保证稳定完成,不会把“略进阶”当成盲目加难。<br>
    <span class="log-pill">优化</span> 有结构化训练经验或比赛经验的骑手,在恢复、FTP可信度、疼痛风险和比赛倒计时都允许时,课表会小幅调整 Z2 / Tempo / Sweet Spot 容量,让复训更贴近真实背景。<br>
    <span class="log-pill">修复</span> 训练课表 TSS 显示改为按导出训练文件的真实功率段估算,减少 TrueCadence 页面 TSS 与 Intervals.icu 导入后 TSS 的差异。<br>
    <span class="log-pill">修复</span> 删除训练反馈和清空全部训练反馈后,旧反馈不再从历史/错骑手文件中重新出现。<br>
    <span class="log-pill">验证</span> 自动课表 A/B/C/D、E1 回归、阶段F和训练文件导出验证均已通过后上线。
  </div>
</div>
<div class="log-card">
  <div class="date">2026-05-30</div>
  <div class="title">功率画像升级、异常功率修正与数据稳定性优化</div>
  <div class="text">
    <span class="log-pill">新增</span> 功率仪表盘新增「功率画像 - 固定参考线 / 同水平分位数」,展示 5s、30s、1min、5min、20min、60min 的功率、W/kg、占 FTP、当前评级和评级来源。<br>
    <span class="log-pill">新增</span> 功率仪表盘新增「异常功率排除」,可将功率计飘值、断连重连等造成的异常 5s/30s/1min 等峰值从功率画像中排除;只影响分析结果,不删除原始 FIT。<br>
    <span class="log-pill">修复</span> 修正 session 最大功率单点飘值污染 5s 冲刺的问题:有逐秒 record 数据时优先使用 rolling 5s,不再让单个 max_power 覆盖真实 5s。<br>
    <span class="log-pill">修复</span> 上传解析预览中的最大功率增加异常修正:当原始最大功率明显高于 rolling 5s 时,显示「最大功率(修正)」并保留「原始最大功率」供排查设备问题。<br>
    <span class="log-pill">优化</span> 5s 短冲参考线从偏低的旧口径上调,当前以 400% FTP 作为卓越参考线,更适合区分真实短时爆发能力。<br>
    <span class="log-pill">新增</span> 后续将根据同水平用户样本自动切换为分位数评价;当前样本不足时先使用 TrueCadence 内测固定参考线。<br>
    <span class="log-pill">优化</span> 疲劳抗性模块将「可分析骑行」改为「后程可分析骑行」,并显示总记录数量,说明短骑或数据不足记录不会计入后程保持分析。<br>
    <span class="log-pill">优化</span> 后程保持评分、平均后半程衰减、最佳单次评级、后程可分析骑行四个卡片统一高度,减少页面错位。<br>
    <span class="log-pill">修复</span> 时长 38-45 分钟的骑行,如果采样点略少于 40 分钟窗口,不再把 40 分钟功率判为 0,改用平均功率和 NP 合理估算。适用于 FTP 测试 / 阈值区间测试等接近窗口的骑行。<br>
    <span class="log-pill">修复</span> Intervals.icu 导入只拿到摘要时不会再误删同一天已上传的 FIT 数据,避免训练负荷和功率仪表盘异常显示"未上传"。
  </div>
</div>
<div class="log-card">
  <div class="date">2026-05-29</div>
  <div class="title">平台接入、数据稳定性与内测体验收口</div>
  <div class="text">
    <span class="log-pill">新增</span> Intervals.icu OAuth 授权接入,支持一键连接 Intervals 账号导入活动数据,不再需要手动 API Key。<br>
    <span class="log-pill">新增</span> COROS / 高驰 FIT 文件兼容,解决部分码表导出 FIT 解析失败的问题。<br>
    <span class="log-pill">新增</span> FIT 解析缓存与耗时显示,同一文件再次上传速度大幅提升。<br>
    <span class="log-pill">新增</span> 训练课表"生成课表"独立入口,Core/Pro/Coach 用户可在侧边栏一键直达。<br>
    <span class="log-pill">新增</span> 内测反馈增加"最喜欢的功能、最不满意的点、愿意付费的功能"三个核心问题,帮助更快收口产品方向。<br>
    <span class="log-pill">修复</span> 上传 FIT 时侧边栏清除数据按钮被锁定,避免解析中途误删数据。<br>
    <span class="log-pill">修复</span> nginx 静态路由拦截 Streamlit 前端 JS 资源导致页面加载失败的问题。<br>
    <span class="log-pill">优化</span> Intervals 导入说明更清晰:当前 API Key 手动导入为内测临时方案,正式多用户版将通过 OAuth 授权。<br>
    <span class="log-pill">优化</span> 套餐对比卡片 UI 收口为用户确认的"完美"版本,不再调整功能行为。
  </div>
</div>
<div class="log-card">
  <div class="date">2026-05-28</div>
  <div class="title">平台导入、导航结构与正式版体验收口</div>
  <div class="text">
    <span class="log-pill">新增</span> 数据导入页新增 Intervals.icu 平台导入,支持读取活动列表、手动选择、最近10条、全选当前列表和摘要兜底导入。<br>
    <span class="log-pill">新增</span> 导入范围支持最近30天、最近90天、今年以来、最近12个月、全部历史和自定义日期。<br>
    <span class="log-pill">优化</span> 历史训练摘要改为长期保存;训练分析仍会按用途优先参考最近 4-12 周,避免导入历史被误删。<br>
    <span class="log-pill">优化</span> Intervals / Strava 来源说明更清晰:Strava API 同步活动可能无法下载原始 FIT,系统会使用 Intervals 摘要继续完成基础分析。<br>
    <span class="log-pill">优化</span> 左侧数据状态增加本次/历史数量、清除本次、确认后清除历史,并在导入中锁定清除操作,避免中断导入。<br>
    <span class="log-pill">优化</span> 导航结构调整:AI 分析归入「我的分析」,训练负荷归入「训练建议」,更贴近"先看结果,再决定怎么练"的流程。<br>
    <span class="log-pill">优化</span> Pro / Coach 版本 AI 分析显示为 ♾️,不再显示 999 次,也不会扣除分析次数。<br>
    <span class="log-pill">修复</span> 隐藏普通用户不需要看到的 endpoint、外部 ID 和 API 调试信息,减少页面噪音。<br>
    <span class="log-pill">修复</span> 修正侧边栏数据状态刷新、导入去重、同批导入提示和按钮颜色/文案一致性问题。
  </div>
</div>
<div class="log-card">
  <div class="date">2026-05-27</div>
  <div class="title">登录保持、备案展示与训练判断口径修复</div>
  <div class="text">
    <span class="log-pill">上线</span> 登录保持机制已上线,刷新或重新打开页面后可自动恢复登录状态,并支持退出登录撤销会话。<br>
    <span class="log-pill">上线</span> 页面底部已补充 ICP 备案号与公安备案号展示。<br>
    <span class="log-pill">修复</span> 恢复与睡眠页的"今天建议"只读取今天的主观反馈和手表睡眠/午睡记录,旧记录只作为历史展示,不再当作今天状态。<br>
    <span class="log-pill">修复</span> 训练负荷页的今日风险判断只读取今天的主观反馈;旧 FIT 会按休息日自然衰减到今天,但不会被当作今天刚训练。<br>
    <span class="log-pill">优化</span> 各页面"合并全历史数据"开关统一口径:没有本次上传时会禁用并提示;有本次上传时,关闭后只作为单批 FIT 临时预览,不作为正式训练安排依据。
  </div>
</div>
<div class="log-card">
  <div class="date">2026-05-26</div>
  <div class="title">训练负荷与 FTP 估算优化</div>
  <div class="text">
    <span class="log-pill">优化</span> 训练负荷页默认合并历史数据,单次训练会作为历史负荷的一部分参与 CTL / ATL / TSB 判断。<br>
    <span class="log-pill">新增</span> 近 42 天训练负荷视角,并补充历史 / 本次上传 TSS 贡献说明。<br>
    <span class="log-pill">优化</span> FTP 估算参考逻辑增加 20 / 40 / 60 分钟多窗口说明,用于减少单一 20 分钟数据带来的偏差。
  </div>
</div>
<div class="log-card">
  <div class="date">2026-05-25</div>
  <div class="title">内测体验修复与训练课导出增强</div>
  <div class="text">
    <span class="log-pill">修复</span> AI 功率分析结果会自动保留,切换页面或刷新后仍可查看;只有主动重新分析才会再次消耗 AI 次数。<br>
    <span class="log-pill">修复</span> 训练负荷页 TSS 正常但近 7 天/28 天时长显示异常的问题。<br>
    <span class="log-pill">新增</span> 训练课支持选择导出 ZWO / ERG / MRC 文件,并打包为 ZIP 下载。<br>
    <span class="log-pill">新增</span> 骑手档案支持按最大心率或乳酸阈值心率 LTHR 预览心率区间。<br>
    <span class="log-pill">优化</span> 训练负荷页增加当前 TSB 解读和状态区间说明。<br>
    <span class="log-pill">上线</span> truecadence.cn / www.truecadence.cn 已支持 HTTPS 安全访问。
  </div>
</div>


<div class="log-card">
  <div class="date">反馈入口</div>
  <div class="title">你的反馈会影响优先级</div>
  <div class="text">如果发现 Bug、数据异常或功能不好用,请在「🐞 内测反馈」提交。内测阶段会优先处理影响训练判断、数据可信度和使用体验的问题。</div>
</div>
""", unsafe_allow_html=True)



def render_english_review_page():
    st.title("🌐 English / Platform Review")
    st.caption("English summary for Strava / Intervals.icu / future platform review. TrueCadence remains Chinese-first for current beta users.")

    st.markdown("""
<style>
.review-hero {
    padding: 1.18em 1.22em;
    border-radius: 17px;
    background: linear-gradient(135deg, rgba(255,107,53,0.16), rgba(22,27,34,0.96));
    border: 1px solid rgba(255,107,53,0.30);
    margin: 0.85em 0 1.05em;
}
.review-hero .k { color:#ff9a68; font-size:.78em; font-weight:850; letter-spacing:.11em; margin-bottom:.35em; }
.review-hero .t { color:#f0f6fc; font-size:1.35em; font-weight:860; margin-bottom:.35em; }
.review-hero .d { color:#aab6c3; font-size:.94em; line-height:1.75; }
.review-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.82em; margin:.9em 0 1.12em; }
.review-card { background:var(--tc-surface); border:1px solid var(--tc-border); border-radius:14px; padding:1em; min-height:138px; }
.review-card .title { color:#f0f6fc; font-size:1.02em; font-weight:780; margin-bottom:.38em; }
.review-card .text { color:#aab6c3; font-size:.89em; line-height:1.68; }
.review-note { border-radius:14px; padding:1em 1.08em; background:rgba(88,166,255,.09); border:1px solid rgba(88,166,255,.22); color:#aab6c3; font-size:.91em; line-height:1.74; margin:1em 0; }
@media(max-width:900px){.review-grid{grid-template-columns:1fr}}
</style>
<div class="review-hero">
  <div class="k">TRUECADENCE REVIEW SUMMARY</div>
  <div class="t">A cycling training analysis tool for Chinese-speaking cyclists</div>
  <div class="d">TrueCadence helps athletes understand their own cycling training data, including training load, power profile, endurance trends, heart-rate/cadence context, nutrition and recovery-related insights. The product is currently Chinese-first, with English review information provided for integration partners.</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="review-grid">
  <div class="review-card"><div class="title">🚴 Product purpose</div><div class="text">TrueCadence is a personal training-analysis dashboard. It is not a social network, route platform, segment platform, leaderboard platform, or replacement for Strava / Intervals.icu / Garmin.</div></div>
  <div class="review-card"><div class="title">🔗 Data import sources</div><div class="text">Current beta supports FIT upload and Intervals.icu manual import. Strava OAuth import is planned as an optional read-only source after developer review and athlete-capacity approval.</div></div>
  <div class="review-card"><div class="title">👤 User-only display</div><div class="text">Imported activity data is displayed only to the authorized user inside their own TrueCadence dashboard. One athlete's platform data is not shown to other users.</div></div>
  <div class="review-card"><div class="title">🔒 Read-only integration</div><div class="text">For Strava, the planned first version is read-only. TrueCadence will not write, modify, delete, publish, or upload activities to Strava.</div></div>
  <div class="review-card"><div class="title">🤖 AI / ML boundary</div><div class="text">TrueCadence will not use Strava data to train, fine-tune, benchmark, or build AI/ML models. User-authorized data is used only to generate analysis for that same user.</div></div>
  <div class="review-card"><div class="title">🗑️ Deletion and disconnect</div><div class="text">Users can disconnect platform integrations and request deletion of imported data. Raw activity files or stream data, if temporarily downloaded for parsing, are retained only for a limited period.</div></div>
</div>
""", unsafe_allow_html=True)

    st.subheader("Planned Strava integration")
    st.markdown("""
- **Authorization:** OAuth-based user authorization.
- **Default range:** recent 30 days; maximum 90 days for manual import.
- **Requested scopes:** `read`, `activity:read`; `activity:read_all` only when a user explicitly authorizes private activities.
- **Callback domain:** `truecadence.cn`.
- **Proposed redirect URI:** `https://truecadence.cn/auth-bridge/strava/callback`.
- **No automatic background sync in the first version:** users manually start an import to control server load and privacy.
""")

    st.subheader("Data handling summary")
    st.markdown("""
- TrueCadence does not sell, redistribute, or disclose platform data to third parties.
- TrueCadence does not expose imported platform data in public leaderboards, feeds, route pages, or social features.
- Raw FIT / stream-like files are temporary parsing inputs, not long-term product content.
- Training summaries are used for the authorized user's dashboard, training-load view, power profile, recovery context, and workout suggestions.
- Support / deletion requests can be handled through the TrueCadence site during the beta period.
""")

    st.markdown("""
<div class="review-note">
<b>Beta note:</b> TrueCadence is currently validating data quality and user value with a small Chinese-speaking cycling community. Platform integrations are intentionally limited, manual and conservative before public scale-up.
</div>
""", unsafe_allow_html=True)



def render_privacy_page(save_current_rides_func):
    st.title("🔐 数据隐私与内测说明")
    st.caption("TrueCadence 需要读取训练数据才能给出功率、负荷、恢复和课表建议。这里说明数据会怎么被使用。")

    st.markdown("""
<style>
.privacy-hero {
    padding: 1.12em 1.18em;
    border-radius: 17px;
    background: linear-gradient(135deg, rgba(255,107,53,0.15), rgba(22,27,34,0.96));
    border: 1px solid rgba(255,107,53,0.30);
    margin: 0.85em 0 1.05em;
}
.privacy-hero .k { color:#ff9a68; font-size:.78em; font-weight:850; letter-spacing:.11em; margin-bottom:.35em; }
.privacy-hero .t { color:#f0f6fc; font-size:1.28em; font-weight:850; margin-bottom:.35em; }
.privacy-hero .d { color:#aab6c3; font-size:.92em; line-height:1.75; }
.privacy-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.8em; margin:.9em 0 1.1em; }
.privacy-card { background:var(--tc-surface); border:1px solid var(--tc-border); border-radius:14px; padding:1em; min-height:132px; }
.privacy-card .title { color:#f0f6fc; font-size:1.02em; font-weight:780; margin-bottom:.38em; }
.privacy-card .text { color:#aab6c3; font-size:.88em; line-height:1.68; }
.privacy-note { border-radius:14px; padding:1em 1.08em; background:rgba(88,166,255,.09); border:1px solid rgba(88,166,255,.22); color:#aab6c3; font-size:.90em; line-height:1.72; margin:1em 0; }
@media(max-width:900px){.privacy-grid{grid-template-columns:1fr}}
</style>
<div class="privacy-hero">
  <div class="k">DATA & PRIVACY</div>
  <div class="t">你的训练数据只用于训练分析与内测改进</div>
  <div class="d">内测阶段,我们会尽量少保存原始文件,只保留完成分析所需的训练摘要。系统不会公开展示你的个人数据,也不会把你的 FIT、睡眠、反馈或女性周期信息用于医疗判断。</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="privacy-grid">
  <div class="privacy-card"><div class="title">📁 FIT 原始文件</div><div class="text">上传的 .fit 原始文件仅用于解析功率、心率、时长、TSS 和功率曲线。内测阶段原始 FIT 最多保留 48 小时,后续上传时会自动清理旧文件。</div></div>
  <div class="privacy-card"><div class="title">📊 训练摘要</div><div class="text">系统会保存解析后的训练摘要,例如日期、时长、距离、功率、心率、TSS、功率曲线等,用于历史趋势、训练负荷、AI 分析和训练课表。</div></div>
  <div class="privacy-card"><div class="title">📝 主观反馈 / 睡眠</div><div class="text">训练反馈、睡眠、HRV、压力、疲劳、疼痛等信息只用于判断恢复状态和调整训练建议。你可以在对应页面删除单条记录或清空记录。</div></div>
  <div class="privacy-card"><div class="title">🩸 女性周期信息</div><div class="text">女性周期、腹痛、情绪和训练影响只用于训练恢复建议,不用于医学诊断,也不会公开展示。你可以选择不记录。</div></div>
  <div class="privacy-card"><div class="title">🐞 内测反馈</div><div class="text">内测反馈会记录问题页面、反馈类型、描述和联系方式。联系方式只用于必要时回访确认问题,不会显示给其他用户。</div></div>
  <div class="privacy-card"><div class="title">🔒 账号与登录</div><div class="text">TrueCadence 不会在分享链接里保存登录凭证。建议使用浏览器或手机系统密码管理器保存密码,不要把账号密码发给他人。</div></div>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="privacy-note">
<b>重要边界:</b>TrueCadence 是训练辅助工具,不替代医生、康复师或专业医疗建议。出现胸痛、晕厥、持续异常心率、严重疼痛、感染发烧或疑似损伤时,应停止训练并咨询专业人士。
</div>
""", unsafe_allow_html=True)

    with st.expander("查看内测阶段数据保留规则", expanded=True):
        st.markdown("""
- **FIT 原始文件**:最多保留 48 小时,用于测试和排查解析问题,之后自动清理。
- **训练历史摘要**:长期保存已解析摘要;同日期新上传会覆盖旧记录,避免重复和脏数据。分析页面会按训练用途优先查看最近 4-12 周。
- **训练反馈 / 睡眠记录**:由用户主动填写,可单条删除或确认后清空。
- **AI 分析上下文**:用于训练计划读取最近一次分析结果;如果训练数据、反馈或睡眠变更,会重新生成上下文。
- **内测反馈**:用于产品改进和问题追踪。
""")

    with st.expander("我应该怎么保护自己的数据?", expanded=False):
        st.markdown("""
- 不要把登录后的页面截图里暴露手机号、邀请码或个人敏感信息。
- 如果要在抖音/朋友圈分享分析截图,建议遮挡姓名、手机号和具体个人备注。
- 不要把完整登录链接、账号密码、邀请码公开发到评论区。
- 如果只是想试功能,优先上传最近 4-12 周训练数据,不需要上传多年历史。
""")

    with st.expander("危险操作:清除当前骑手历史上传", expanded=False):
        st.warning("这会删除当前骑手已保存的全部 FIT 解析历史,不影响账号和骑手档案。一般只在测试脏数据或重新建档时使用。")
        confirm_clear_history = st.checkbox("我确认清除当前骑手历史存档", key="confirm_clear_ride_history")
        if st.button("删除历史存档", disabled=not confirm_clear_history, use_container_width=True):
            save_current_rides_func([])
            st.cache_data.clear()
            st.session_state.uploaded_rides = []
            st.success("已清除当前骑手历史上传记录")
            st.rerun()



