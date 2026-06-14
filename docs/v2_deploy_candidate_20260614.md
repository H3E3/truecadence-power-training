# TrueCadence V2 部署候选清单（2026-06-14）

## 当前结论

本地验证通过，当前代码可作为 V2 部署候选。生产部署仍需显式确认后执行。

## 已完成门禁

- `py_compile`：通过
- V2 训练一致性：通过
- 训练日历/恢复门控：通过
- 反馈影响训练计划：通过
- 4 周方向：通过
- V2 上传边界：通过
- V2 AI 摘要：通过
- 训练恢复状态：通过
- workout export：通过
- 本地 HTTP smoke：`http://127.0.0.1:8502/` 返回 200
- 用户本地浏览器验证：正常
- `git diff --check`：通过

## 本次部署范围

### V2 页面与路由
- `tc_pages/v2/`
- `tc_pages/static_pages.py`：首页切到 V2 dashboard；更新日志/英文评审/隐私页与 HEAD 一致。
- `tc_pages/training_plan_page.py`
- `tc_pages/import_pages.py`
- `tc_pages/profile_feedback_pages.py`
- `tc_pages/recovery_nutrition_goal_pages.py`
- `tc_pages/training_overview_pages.py`
- `ui_components.py`

### V2 服务层
- `services/training_calendar.py`
- `services/training_readiness.py`
- `services/plan_preferences.py`
- `services/feedback_impact.py`
- `services/fueling_recommendation.py`
- `services/rider_profile_service.py`
- `services/v2_ai_summary.py`
- `services/workout_export.py`

### 认证边界
- 登录页/注册页保持旧版，不做 V2 视觉改造。
- `auth.py` 仅新增 active rider 逻辑。
- `auth_bridge.py` 新增 `/api/rider-profile/save`，供 V2 骑手档案 modal 保存资料。

### 验证脚本
- `verify_v2_training_consistency.py`
- `verify_training_calendar_readiness.py`
- `verify_feedback_impact.py`
- `verify_four_week_direction.py`
- `verify_v2_upload_boundary.py`
- `verify_v2_ai_summary.py`
- `verify_training_readiness.py`
- `verify_workout_exports.py`

## 不纳入部署/提交的本地文件

- `.learnings/`
- `logs/`
- `backups/code_cleanup_*/`
- 已隔离旧 V2 原型与设计资产：`tc_pages/v2_real.py`、`tc_pages/v2_shell.py`、`assets/v2_dashboard_strict.html`、`assets/v2_effects/`

## 生产部署前必须执行

1. 备份生产 `/opt/truecadence` 相关文件。
2. 同步候选文件，避免携带本地日志/备份/原型资产。
3. 服务器上运行 `py_compile` 与关键 verifier。
4. 重启 `truecadence` 与必要服务。
5. 检查：
   - `systemctl is-active truecadence truecadence-auth-bridge nginx`
   - local HTTP 200
   - public `https://truecadence.cn/` HTTP 200
   - 最近日志无 Traceback / PermissionError / ImportError / NameError
6. 浏览器线上 smoke：登录旧页、首页 V2、训练计划、上传与诊断、骑手档案、状态恢复。
