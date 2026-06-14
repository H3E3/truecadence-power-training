from __future__ import annotations

from typing import Any


def _as_dict(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "as_dict"):
        return obj.as_dict()
    return {
        "level": getattr(obj, "level", ""),
        "headline": getattr(obj, "headline", ""),
        "reason": getattr(obj, "reason", ""),
        "intensity_cap": getattr(obj, "intensity_cap", "normal"),
        "actions": getattr(obj, "actions", []) or [],
    }


def _session_changes(baseline_ctx: dict[str, Any], gated_ctx: dict[str, Any]) -> list[str]:
    before_sessions = baseline_ctx.get("sessions") or []
    after_sessions = gated_ctx.get("sessions") or []
    changes: list[str] = []
    for before, after in zip(before_sessions, after_sessions):
        if getattr(before, "is_rest", False):
            continue
        if getattr(before, "title", "") != getattr(after, "title", "") or getattr(before, "kind", "") != getattr(after, "kind", ""):
            changes.append(f"{after.weekday_label}：{before.title} → {after.title}")
    return changes


def describe_feedback_entry(entry: dict[str, Any]) -> str:
    parts: list[str] = []
    if entry.get("sleep_quality") is not None:
        parts.append(f"睡眠 {entry.get('sleep_quality')}/5")
    if entry.get("leg_fatigue") is not None:
        parts.append(f"腿疲劳 {entry.get('leg_fatigue')}/5")
    if entry.get("rpe") is not None:
        parts.append(f"RPE {entry.get('rpe')}/10")
    completion = entry.get("completion")
    if completion:
        parts.append(str(completion))
    fueling = entry.get("fueling")
    if fueling and fueling != "正常":
        parts.append(f"补给：{fueling}")
    pains = entry.get("pains") or []
    if pains:
        parts.append("不适：" + "、".join(str(x) for x in pains[:3]))
    specials = entry.get("specials") or []
    if specials:
        parts.append("特殊：" + "、".join(str(x) for x in specials[:3]))
    return "；".join(parts) or "已记录今日状态"


def build_feedback_impact_notice(*, entry: dict[str, Any], readiness: Any, baseline_ctx: dict[str, Any], gated_ctx: dict[str, Any]) -> dict[str, Any]:
    payload = _as_dict(readiness)
    changes = _session_changes(baseline_ctx, gated_ctx)
    level = payload.get("level") or gated_ctx.get("readiness_level") or "未计算"
    headline = payload.get("headline") or "已更新训练状态"
    reason = payload.get("reason") or "已根据最新反馈重新计算训练建议。"
    actions = payload.get("actions") or []
    if changes:
        impact = "；".join(changes[:4])
        if len(changes) > 4:
            impact += f"；另有 {len(changes) - 4} 天同步调整"
    else:
        impact = "本周课表暂未触发自动降级；继续按当前计划执行，并观察下一条反馈。"
    return {
        "level": level,
        "headline": headline,
        "entry_summary": describe_feedback_entry(entry),
        "reason": reason,
        "impact": impact,
        "actions": list(actions[:3]),
        "change_count": len(changes),
    }
