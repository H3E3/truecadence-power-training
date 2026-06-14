# TrueCadence V2 训练逻辑接入计划：简洁页面版（更新）

> 日期：2026-06-11
> 状态：上午已补「今日补给」V2 小模块；下午进入训练逻辑闭环接入。
> 目标：把旧版训练大脑压缩进新版 V2，但不把旧版复杂后台搬回主界面。

---

## 0. 总原则

新版不是把旧版所有表单、参数、图表原样搬回来。
新版要保留用户能理解的产品体验：

```text
目标 → 当前状态 → 本周策略 → 本周课表 → 单日执行 → 反馈回流
```

用户看到的应该是：

```text
我现在练什么？
我现在能不能练？
这周为什么这样排？
今天怎么执行？
今天吃什么？
练完反馈会不会影响后面？
```

后台可以复杂，但前台只给结论、依据和可执行动作。

### 页面控制原则

- 主页面不增加大量新卡片。
- 不恢复旧版大表、大参数、大控件。
- 复杂逻辑放到服务层、弹窗、依据入口里。
- 每个主页面只回答一个核心问题。
- 用户不需要懂 CTL / ATL / TSB 才能使用。
- 专业数据可以存在，但不能压到普通用户主路径。
- 训练、恢复、补给必须联动，而不是各说各话。

---

## 1. 当前新版状态

### 1.1 已完成：V2 页面骨架

新版 V2 已具备：

```text
骑手档案
上传与诊断
专业数据
今日训练建议
训练计划
状态与恢复
今日补给
帮助 / 隐私 / 更新
```

页面视觉和信息结构已经基本进入正式产品形态。

### 1.2 已完成：训练计划基础能力

当前已有：

```text
训练目标
可训练日
长距离日
不安排高强度日
本周 7 天课表
单日训练详情
导出课表
4 周方向基础文案
```

但训练计划仍主要按目标和训练日生成，尚未完整接入 readiness / 反馈 / 睡眠 / 负荷门控。

### 1.3 已完成：今日补给 V2 小模块（2026-06-11 上午新增）

新增独立 V2 小模块：

```text
今日补给
```

访问入口：

```text
状态与恢复 → 营养补给
左侧导航 → 今日补给
训练驾驶舱 → 今天吃什么
```

当前逻辑读取：

```text
今天课程强度
预计训练时长
最近 3 天训练反馈
补给反馈：吃少了 / 喝少了 / 胃不舒服 / 低血糖感
睡眠 / 腿疲劳 / 特殊情况
骑手体重
```

输出：

```text
骑前吃什么
骑中碳水 g/h
预计总碳水
喝水 ml/h
钠 mg/h
骑后恢复
根据上一条训练反馈的修正建议
```

涉及文件：

```text
services/fueling_recommendation.py
tc_pages/v2/fueling.py
app.py
tc_pages/v2/router.py
tc_pages/v2/shell.py
tc_pages/v2/dashboard.py
```

验证：

```text
.venv-mac/bin/python -m py_compile app.py tc_pages/*.py tc_pages/v2/*.py services/*.py rules/*.py
.venv-mac/bin/python verify_recovery_nutrition_rules.py
页面级浏览器验证：今日补给正常渲染
```

备注：当前 Streamlit 日志有既有 `st.components.v1.html` 未来移除提醒，来自旧弹窗组件，不影响本次补给模块运行；暂不扩大范围处理。

---

## 2. 新版和旧版核心差距

旧版逻辑链更完整：

```text
目标
→ 周期长度 / 周训练小时
→ 训练经验 / 历史 FTP / W/kg / 停训时间
→ 比赛类型 / 比赛日期 / 优先级
→ 可训练日 / 长距离日 / 不高强日
→ FIT / PMC / CTL / ATL / TSB
→ 训练反馈 / 睡眠 / 疼痛 / 特殊情况
→ readiness
→ phase
→ 本周训练重点
→ 周计划
→ 导出
```

新版当前更接近：

```text
目标
→ 可训练日
→ 本周小卡
→ 单日详情
→ 今日补给
→ 导出
```

所以接下来要补的是：

> 训练大脑的逻辑闭环，而不是继续堆页面。

---

## 3. 下午开始的逻辑闭环目标

下午优先完成核心闭环，不追求一次接完整个旧版系统。

### 目标闭环

```text
1. 目标
用户选择：提升 FTP / 减脂 / 比赛备赛 / 恢复体能 / 长距离耐力

2. 当前状态
系统判断：可推进 / 谨慎推进 / 恢复优先

3. 本周策略
系统输出：本周保留几次强度课、是否降级、长距离是否保留

4. 本周课表
页面展示：7 天小卡 + 完整周计划

5. 单日执行
弹窗展示：怎么练、怎么降级、怎么吃、怎么喝

6. 反馈回流
用户记录今日反馈，系统影响后续训练安排和今日补给
```

前台只显示这 6 步结论，不显示全部中间参数。

---

## 4. 下午开发顺序

## 第 1 刀：训练状态摘要服务

新增：

```text
services/training_readiness.py
```

输入：

```text
rides
feedback
sleep_records
profile
```

输出轻量对象：

```python
{
  "level": "可推进 / 谨慎推进 / 恢复优先",
  "headline": "本周可以推进，但不要加码",
  "reason": "近期反馈未见明显红旗",
  "intensity_cap": "normal / caution / recovery",
  "flags": ["腿部疲劳偏高", "TSB 偏低"],
  "source": {
    "feedback_count": 3,
    "sleep_count": 2,
    "pmc_available": True
  }
}
```

接入数据：

```text
CTL / ATL / TSB（可用则读）
最近 7 天 TSS
最近 28 天训练量
ramp rate
睡眠质量
腿部疲劳
精神状态
RPE
完成度
疼痛
感冒 / 发烧 / 睡眠不足 / 出差 / 天气过热
```

前台展示：

```text
本周策略：谨慎推进。
保留 1 次强度课，其余以 Z2 和恢复为主。
```

不在主页面展示：

```text
CTL 52 / ATL 68 / TSB -16 / ramp +7
```

这些进入「查看计划依据」。

---

## 第 2 刀：训练计划接入 readiness

修改：

```text
services/training_calendar.py
```

让 readiness 影响：

```text
强度课是否保留
强度课是否降级
长距离是否缩短
今日建议是否提示恢复优先
```

规则示例：

| readiness | 训练计划影响 |
|---|---|
| 可推进 | 保留目标刺激，正常安排长距离 |
| 谨慎推进 | 最多 1 次质量课；长距离不加码 |
| 恢复优先 | 暂停质量课，改 Z1/Z2 / 恢复骑 / 休息 |

---

## 第 3 刀：计划依据真实化

当前「查看计划依据」已有基础版，下一步把固定说明改成真实决策解释：

```text
目标依据
当前状态门控
训练日约束
反馈影响
补给影响
本周策略
```

用户看到：

```text
为什么这周只保留 1 次强度课？
为什么今天不是阈值？
为什么长距离没有加到 3 小时？
为什么今天补给提高了碳水下限？
```

---

## 第 4 刀：今日反馈回流训练计划

当前 V2 已有今日反馈弹窗；下一步让反馈真正影响计划。

反馈触发：

| 反馈 | 计划影响 |
|---|---|
| 睡眠 ≤ 2 | 下一节强度课降级 |
| 腿部疲劳 ≥ 4 | 下一节质量课降级 |
| 疼痛不为空 | 避开冲刺、高强度、过长低踏频 |
| 感冒 / 发烧 | 恢复优先，不安排结构化训练 |
| RPE 高 + 没完成 | 下一节强度课降一级 |
| 吃少 / 喝少 | 单日详情和今日补给强化提示 |
| 胃不舒服 | 补给改小口分次，避免一次性猛吃 |

---

## 第 5 刀：4 周方向接入 readiness

4 周方向不只是按目标变化，也按状态变化。

示例：

```text
恢复优先：第 1 周恢复连续性，第 2 周再轻微加量
谨慎推进：第 1 周控制强度，第 2 周视反馈恢复目标刺激
可推进：第 2/3 周逐步增加目标刺激
```

不做：

```text
28 天每天详细训练
每周 TSS 详细表
完整周期化参数
```

---

## 第 6 刀：AI 分析结果 V2 化

不是当前第一优先级，但后续需要做。

拆成短卡片：

```text
能力结论
风险提醒
训练建议
恢复建议
下一步
```

不搬旧版长报告，不跳回旧版页面。

---

## 第 7 刀：比赛日期轻量接入

仅当用户选择「比赛备赛」时，弹窗里显示可选项：

```text
比赛日期
比赛类型
```

默认折叠，不影响其他目标用户。

---

## 5. 页面结构保持简洁

训练计划主页面只保留：

```text
1. 当前策略摘要
2. 本周 7 天课表
3. 次级入口
```

复杂信息放进：

```text
调整训练日
查看计划依据
查看 4 周方向
今日补给
单日训练详情
专业数据
```

单日详情只服务执行：

```text
今天练什么
怎么练
为什么今天这样安排
降级规则
骑前 / 骑中吃什么
喝水 / 电解质
骑后恢复
```

---

## 6. 已接入 / 待接入清单

| 模块 | 状态 | 说明 |
|---|---|---|
| 训练目标 | 已有基础版 | 需继续作为策略输入 |
| 可训练日 / 长距离日 / 不高强日 | 已有基础版 | 需继续作为约束输入 |
| 今日补给 | 已接入 V2 小模块 | 已联动课程强度 + 最近反馈 |
| readiness 状态门控 | 已接入 | 第 1 刀完成：三档状态 + V2 摘要 |
| 训练计划接入 readiness | 已接入 | 第 2 刀完成：normal 保留，caution 降质量课/长距离，recovery 转恢复 |
| 计划依据真实化 | 已接入 | 第 3 刀完成：显示目标/约束/数据来源/readiness/实际降级变化 |
| 反馈回流训练计划 | 已接入基础版 | 第 4 刀完成：保存反馈后生成后续训练影响摘要 |
| 4 周方向接入 readiness | 已接入 | 第 6 刀完成：normal/caution/recovery 三档周期方向 |
| AI 分析 V2 化 | 待接入 | 后续增强 |
| 比赛日期轻量接入 | 待接入 | 后续增强 |
| 12 周详细课表 | 暂不接入主界面 | 未来 Pro / Coach 高级入口 |
| 旧版完整 PMC 图表 | 不进训练计划主界面 | 留在专业数据 |
| 管理后台 / 订单 / 套餐 | 不进训练计划页 | 保持账号/管理模块 |

---

## 7. 下午最小验收标准

如果下午先做核心闭环，最小完成标准是：

```text
1. services/training_readiness.py 存在且可单独测试
2. readiness 能输出 3 档：可推进 / 谨慎推进 / 恢复优先
3. 训练计划顶部显示真实策略摘要
4. 本周课表会根据 readiness 降级或保留强度
5. 计划依据能解释至少 3 个来源：目标、反馈、负荷/睡眠
6. 保存今日反馈后，重新进入页面能影响建议
7. py_compile 通过
8. 相关 verify 脚本通过
9. 本地 8502 页面 HTTP 200，浏览器不出现 Traceback
```

---

## 8. 当前本地状态

本地服务：

```text
http://127.0.0.1:8502
```

当前运行命令：

```text
TRUECADENCE_DEPLOY_MODE=local .venv-mac/bin/python -m streamlit run app.py --server.port 8502 --server.address 127.0.0.1 --server.headless true --server.fileWatcherType none
```

当前说明：

- 本次只改本地，未动生产。
- 今日补给页面已浏览器验证正常。
- 下午开始做 readiness 和训练计划闭环时，仍遵循：先诊断、再小步改、每刀验证。

---

## 9. 一句话结论

新版接下来不是继续加页面，而是把旧版训练大脑压缩成用户能懂的闭环：

```text
本周能不能推进？
为什么这样排？
今天怎么练？
今天怎么吃？
练后反馈会怎么影响后面？
```

上午已经补上「今天怎么吃」。
下午从 `services/training_readiness.py` 开始，把「本周能不能推进」和「为什么这样排」接起来。


---

## 10. 下午进展：第 1-2 刀完成（2026-06-11 14:41）

已完成：

```text
第 1 刀：services/training_readiness.py
第 2 刀：training_calendar.py 消费 readiness 做课表门控
```

当前门控规则：

```text
normal / 可推进：课表不变
caution / 谨慎推进：质量课降为 Z2 45–60 分钟，长距离缩短为 Z2 75–90 分钟
recovery / 恢复优先：训练日全部改为恢复骑 30–45 分钟 / 休息，休息日不变
```

新增验证：

```text
verify_training_readiness.py
verify_training_calendar_readiness.py
```

已通过验证：

```bash
.venv-mac/bin/python -m py_compile app.py tc_pages/*.py tc_pages/v2/*.py services/*.py rules/*.py
.venv-mac/bin/python verify_training_readiness.py
.venv-mac/bin/python verify_training_calendar_readiness.py
.venv-mac/bin/python verify_recovery_nutrition_rules.py
.venv-mac/bin/python verify_workout_exports.py
```

浏览器烟测：

```text
训练计划：已显示实际课表门控
今日训练建议：正常
今日补给：正常
状态与恢复：正常
```

当前本地服务：

```text
http://127.0.0.1:8502
session: faint-sage
```

下一刀建议：

```text
第 3 刀：计划依据真实化
- 把目标、训练日设置、readiness 原因、反馈、睡眠、PMC 来源写进“查看计划依据” modal
- 让用户能看懂：为什么本周这样排 / 为什么被降级 / 哪些反馈影响了后面
```


---

## 11. 下午进展：第 3 刀完成（2026-06-11 14:52）

已完成：

```text
第 3 刀：计划依据真实化
```

`训练计划 > 查看计划依据` 现在展示真实依据：

```text
1. 本周结论：readiness level + headline + reason
2. 目标与约束：目标、可训练日、休息日、长距离日、不高强日
3. 数据来源：近期反馈数、睡眠记录数、PMC/缺少 PMC 状态
4. 门控规则：normal / caution / recovery 对课表的影响
5. 实际变化：对比无门控课表与当前课表，例如质量课 → Z2
6. 执行动作：readiness actions + 今日建议结果
```

验证通过：

```bash
.venv-mac/bin/python -m py_compile app.py tc_pages/*.py tc_pages/v2/*.py services/*.py rules/*.py
.venv-mac/bin/python verify_training_readiness.py
.venv-mac/bin/python verify_training_calendar_readiness.py
.venv-mac/bin/python verify_recovery_nutrition_rules.py
.venv-mac/bin/python verify_workout_exports.py
```

浏览器/DOM smoke：

```text
计划依据内容已渲染
包含“实际变化”
包含“周一：轻甜区 3×12 分钟 → Z2 有氧 45–60 分钟”
无 Traceback
```

当前本地服务：

```text
http://127.0.0.1:8502
session: amber-falcon
```

下一刀建议：

```text
第 4 刀：反馈回流闭环
- 保存今日反馈后，readiness 立即重新计算
- 页面明确提示“这条反馈影响了后面哪几天”
- 验证睡眠差/腿疲劳/发烧等反馈能触发对应降级
```


---

## 12. 下午进展：第 4 刀完成（2026-06-11 14:59）

已完成：

```text
第 4 刀：反馈回流影响摘要
```

新增：

```text
services/feedback_impact.py
verify_feedback_impact.py
```

保存 V2 今日反馈后，现在会：

```text
1. 保存反馈
2. 重新读取 rides / profile / sleep / feedback
3. 重新计算 training_readiness
4. 生成无门控 baseline week plan
5. 生成 readiness 门控后的 gated week plan
6. 对比两者变化
7. 在状态与恢复页显示“这条反馈影响后续哪几天”
```

状态页保存后提示包含：

```text
这条反馈：睡眠/腿疲劳/RPE/完成度/补给/疼痛/特殊情况摘要
为什么：readiness reason
影响后续：例如 周一 轻甜区 → Z2；周日 长距离 → 缩短
执行动作：readiness actions
```

验证通过：

```bash
.venv-mac/bin/python -m py_compile app.py tc_pages/*.py tc_pages/v2/*.py services/*.py rules/*.py verify_feedback_impact.py
.venv-mac/bin/python verify_feedback_impact.py
.venv-mac/bin/python verify_training_readiness.py
.venv-mac/bin/python verify_training_calendar_readiness.py
.venv-mac/bin/python verify_recovery_nutrition_rules.py
```

浏览器 smoke：

```text
状态与恢复页正常渲染
无 Traceback
```

备注：

```text
未做真实表单提交烟测，避免向本地真实骑手数据写入测试反馈。
影响摘要逻辑已由 verify_feedback_impact.py 覆盖。
```

当前本地服务：

```text
http://127.0.0.1:8502
session: tide-meadow
```

下一刀建议：

```text
第 5 刀：反馈后的计划页联动提示
- 训练计划页读取 tc_v2_feedback_impact
- 顶部提示“刚才反馈导致这些训练变化”
- 让用户从状态页跳到计划页后仍然看得懂闭环
```


---

## 13. 下午进展：第 5 刀完成（2026-06-11 15:00）

已完成：

```text
第 5 刀：反馈后的计划页联动提示
```

训练计划页现在会读取：

```text
st.session_state["tc_v2_feedback_impact"]
```

如果用户刚保存过今日反馈，训练计划页顶部会显示：

```text
反馈已回流
刚才反馈：睡眠/腿疲劳/RPE/完成度/补给/疼痛/特殊情况摘要
计划变化：后续哪些训练被降级或缩短
接下来：readiness actions
```

提供两个入口：

```text
回看反馈
查看计划依据
```

验证通过：

```bash
.venv-mac/bin/python -m py_compile app.py tc_pages/*.py tc_pages/v2/*.py services/*.py rules/*.py verify_feedback_impact.py
.venv-mac/bin/python verify_feedback_impact.py
.venv-mac/bin/python verify_training_readiness.py
.venv-mac/bin/python verify_training_calendar_readiness.py
.venv-mac/bin/python verify_recovery_nutrition_rules.py
```

浏览器 smoke：

```text
训练计划页正常渲染
无 Traceback
```

当前本地服务：

```text
http://127.0.0.1:8502
session: tender-cove
```

下一刀建议：

```text
第 6 刀：4 周方向接入 readiness
- 让“查看 4 周方向”不再只是静态文案
- 根据当前 readiness / 反馈 / 课表门控解释下周怎么变
```


---

## 14. 下午进展：第 6 刀完成（2026-06-11 15:06）

已完成：

```text
第 6 刀：4 周方向接入 readiness
```

`训练计划 > 查看 4 周方向` 现在不再只是静态目标文案，而是根据 readiness 分三档：

```text
normal / 可推进：保留目标方向，第 1 周加入当前状态原因
caution / 谨慎推进：先谨慎承接，再看反馈恢复 1 次质量课
recovery / 恢复优先：先恢复，再连续性，再轻刺激试探，最后重新定方向
```

新增验证：

```text
verify_four_week_direction.py
```

验证通过：

```bash
.venv-mac/bin/python -m py_compile app.py tc_pages/*.py tc_pages/v2/*.py services/*.py rules/*.py verify_four_week_direction.py
.venv-mac/bin/python verify_four_week_direction.py
.venv-mac/bin/python verify_feedback_impact.py
.venv-mac/bin/python verify_training_readiness.py
.venv-mac/bin/python verify_training_calendar_readiness.py
```

浏览器/DOM smoke：

```text
训练计划页正常渲染
DOM 包含：当前目标 · 谨慎推进
DOM 包含：谨慎承接 / 看反馈再恢复强度
无 Traceback
```

当前本地服务：

```text
http://127.0.0.1:8502
session: gentle-falcon
```

下一步建议：

```text
收口一次 V2 训练闭环总验收，或第 7 刀做“4 周方向与计划依据互链/文案压缩”。
```


---

## 15. 下午进展：第 7 刀完成（2026-06-11 15:29）

已完成：

```text
第 7 刀：V2 训练设置一致性总验收
```

本刀修复的关键不一致：

```text
今日训练建议 > 查看完整课表
```

旧问题：弹窗顶部仍写死：

```text
3 次训练 / 约 4.5–5 小时 / 1 次质量课
周四质量课优先降级
```

现在已改为从同一份 `week_plan_context(ctx)` 动态生成：

```text
训练天数
休息天数
质量/专项课数量
可训练日
休息日
自适应降级规则
```

新增一致性验证：

```text
verify_v2_training_consistency.py
```

覆盖：

```text
1. week_plan_context 与 plan_prefs 一致
2. profile 读取 plan_prefs
3. dashboard 周计划弹窗动态摘要
4. 禁止旧训练日占位 / 写死摘要回归
```

验证通过：

```bash
.venv-mac/bin/python -m py_compile app.py tc_pages/*.py tc_pages/v2/*.py services/*.py rules/*.py verify_v2_training_consistency.py
.venv-mac/bin/python verify_v2_training_consistency.py
.venv-mac/bin/python verify_training_calendar_readiness.py
.venv-mac/bin/python verify_training_readiness.py
.venv-mac/bin/python verify_feedback_impact.py
.venv-mac/bin/python verify_four_week_direction.py
```

浏览器 smoke：

```text
今日训练建议完整课表：显示同一组可训练日
今日训练建议完整课表：显示 6 天训练 / 1 天休息 / 无明显质量课
骑手档案：显示同一组可训练日
无旧占位：二 / 四 / 六
无 Traceback
```

当前本地服务：

```text
http://127.0.0.1:8502
session: mild-meadow
```
