from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent


def assert_true(name: str, cond: bool, value=None) -> None:
    if not cond:
        raise AssertionError(f"{name}: failed {value!r}")
    print(f"PASS {name}")


def read_rel(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a)
    return text[a:b]


def test_upload_page_boundaries() -> None:
    upload_py = read_rel("tc_pages/v2/upload.py")
    modal_block = _between(upload_py, "ai_modal_html = f'''", "    body = f'''")

    assert_true("upload_no_unused_url_import", "from .shell import _wrap, _url" not in upload_py)
    assert_true("upload_single_ai_entry", upload_py.count('href="#tc-upload-ai-modal-layer"') == 1, upload_py.count('href="#tc-upload-ai-modal-layer"'))
    assert_true("modal_no_duplicate_nav_to_plan", "看训练计划" not in modal_block and "训练计划" not in modal_block, modal_block)
    assert_true("modal_no_duplicate_nav_to_today", "看今日建议" not in modal_block and "训练驾驶舱" not in modal_block, modal_block)
    assert_true("modal_no_button_actions", "<button" not in modal_block and "class=\"btn" not in modal_block and "mini-nav" not in modal_block, modal_block)
    for label in ["能力结论", "风险提醒", "训练建议", "恢复建议", "下一步"]:
        assert_true(f"modal_keeps_short_card:{label}", label in modal_block)
    assert_true("upload_primary_scope_data", "上传 FIT" in upload_py and "连接 ICU" in upload_py and "AI 分析" in upload_py)
    assert_true("upload_snapshot_renamed", "状态初筛" in upload_py and "数据线索" in upload_py and "只提示，不替代训练计划" in upload_py)
    assert_true("upload_no_main_duplicate_labels", '<div class="label rose">今日建议</div>' not in upload_py and '<div class="label purple">功率画像</div>' not in upload_py)
    assert_true("upload_main_no_full_training_advice", "今天怎么骑更划算" not in upload_py and "把专业曲线翻译成人话" not in upload_py)
    assert_true("upload_explains_page_boundary", "具体今天怎么练、能力短板和本周安排，分别回到对应页面看" in upload_py)
    assert_true("upload_status_points_to_plan", "详细安排去训练计划看" in upload_py and "具体怎么练到训练计划里看" in upload_py)


if __name__ == "__main__":
    test_upload_page_boundaries()
    print("OK V2 upload boundary checks passed")
