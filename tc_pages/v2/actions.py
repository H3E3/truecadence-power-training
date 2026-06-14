from __future__ import annotations

from urllib.parse import quote


V2_SECONDARY_MENUS: dict[str, list[str]] = {
    "profile": ["编辑骑手档案", "训练目标设置", "Fitting 设定", "历史资料变更", "数据与隐私说明"],
    "upload": ["上传 FIT", "查看本次解析", "数据可信度", "为什么这样判断", "专业诊断详情"],
    "plan": ["训练详情", "生成/重新生成", "导出课表", "调整训练目标", "训练反馈"],
    "recovery": ["填写恢复反馈", "睡眠记录", "疼痛/生病记录", "恢复依据", "调整今日建议"],
    "power": ["功率曲线", "Power Profile", "异常功率排除", "PMC/训练负荷", "数据明细"],
}


def second_level_url(nav: str, sub: str, action: str) -> str:
    return f"?nav={quote(nav)}&sub={quote(sub)}&action={quote(action)}"


def normalize_action(value) -> str | None:
    if isinstance(value, list):
        return value[0] if value else None
    return value or None
