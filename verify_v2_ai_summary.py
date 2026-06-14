from __future__ import annotations

from pathlib import Path

from services.v2_ai_summary import build_v2_ai_summary

ROOT = Path(__file__).resolve().parent


def assert_true(name: str, cond: bool, value=None) -> None:
    if not cond:
        raise AssertionError(f"{name}: failed {value!r}")
    print(f"PASS {name}")


def read_rel(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_summary_has_five_short_cards() -> None:
    summary = build_v2_ai_summary(
        rides=[{"date": "2026-06-10", "dur": 160, "tss": 92}],
        profile={"ftp_test": 250, "weight": 68},
        feedback=[{"date": "2026-06-11", "sleep_quality": 2, "energy": 2, "leg_fatigue": 4, "pains": ["膝盖"]}],
        sleep_records=[],
        readiness={"level": "谨慎推进", "reason": "腿部疲劳偏高", "intensity_cap": "caution"},
    )
    for key in ["ability", "risk", "training", "recovery", "next_step", "data_basis"]:
        assert_true(f"summary_key:{key}", bool(summary.get(key)), summary)
    assert_true("summary_training_caution", "谨慎推进" in summary["training"], summary["training"])
    assert_true("summary_risk_mentions_fatigue", "腿部疲劳" in summary["risk"] or "睡眠" in summary["risk"], summary["risk"])


def test_upload_page_v2_ai_brief_not_legacy_long_report() -> None:
    upload_py = read_rel("tc_pages/v2/upload.py")
    router_py = read_rel("tc_pages/v2/router.py")
    assert_true("upload_accepts_context_loaders", "def render_upload_page(*, load_feedback" in upload_py)
    assert_true("upload_builds_v2_ai_summary", "build_v2_ai_summary" in upload_py)
    for label in ["能力结论", "风险提醒", "训练建议", "恢复建议", "下一步"]:
        assert_true(f"upload_short_card:{label}", label in upload_py)
    assert_true("upload_not_old_intro", "不搬旧版长报告" in upload_py)
    assert_true("upload_no_duplicate_ai_nav", "mini-nav" not in upload_py and "看训练计划" not in upload_py and "href=\"{_url(" not in upload_py)
    assert_true("router_passes_loaders", "render_upload_page(load_feedback=load_feedback" in router_py)


if __name__ == "__main__":
    test_summary_has_five_short_cards()
    test_upload_page_v2_ai_brief_not_legacy_long_report()
    print("OK V2 AI summary checks passed")
