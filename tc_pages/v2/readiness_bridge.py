from __future__ import annotations

from typing import Callable

from services.training_readiness import TrainingReadiness, build_training_readiness
from services.training_calendar import local_today


def _safe_call(func: Callable | None, default):
    if not func:
        return default
    try:
        return func()
    except Exception:
        return default


def v2_readiness_context(*, load_feedback=None, load_profile=None, load_rides=None, load_sleep=None, compute_daily_pmc_func=None) -> TrainingReadiness:
    return build_training_readiness(
        rides=_safe_call(load_rides, []),
        feedback=_safe_call(load_feedback, []),
        sleep_records=_safe_call(load_sleep, []),
        profile=_safe_call(load_profile, {}),
        compute_daily_pmc_func=compute_daily_pmc_func,
        today=local_today(),
    )


def readiness_label_class(level: str) -> str:
    if level == "恢复优先":
        return "rose"
    if level == "谨慎推进":
        return "warn"
    return "green"
