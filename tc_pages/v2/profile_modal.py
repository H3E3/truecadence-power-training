from __future__ import annotations

import html
import json

from services.rider_profile_service import PROFILE_GOAL_OPTIONS, normalize_profile_goal
from tc_pages.v2.modal_window import render_mac_modal_window
from tc_pages.v2.profile_modal_assets import PROFILE_MODAL_CSS, profile_modal_script


def _goal_options(goal_value: str) -> str:
    return "".join(
        f'<option value="{html.escape(option, quote=True)}" {"selected" if option == goal_value else ""}>{html.escape(option)}</option>'
        for option in PROFILE_GOAL_OPTIONS
    )


def _rider_manager_html(*, user: dict | None, rider: str, load_rider_profile) -> str:
    if not user or user.get("plan") != "coach":
        return ""
    rider_names = list((user.get("riders") or {}).keys())
    if not rider_names:
        return ""
    rider_profiles = {name: (load_rider_profile(user["user_id"], name) or {}) for name in rider_names}
    rider_profiles_json = html.escape(json.dumps(rider_profiles, ensure_ascii=False), quote=True)
    rider_options = "".join(
        f'<option value="{html.escape(name, quote=True)}" {"selected" if name == rider else ""}>{html.escape(name)}</option>'
        for name in rider_names
    )
    if len(rider_names) < 20:
        rider_options += '<option value="__new__">＋ 添加新骑手</option>'
    return f"""
  <div class="tc-profile-manager" data-tc-rider-manager>
    <div class="tc-profile-field full"><label for="profile-target-rider">当前编辑骑手</label><select id="profile-target-rider" name="target_rider" data-rider-profiles="{rider_profiles_json}">{rider_options}</select></div>
  </div>
"""


def render_profile_edit_modal(*, profile: dict, user: dict | None, rider: str, load_rider_profile) -> None:
    goal_value = normalize_profile_goal(profile.get("goal"))
    form_html = f"""
<form class="tc-profile-modal-form" data-tc-fetch-submit>
  <input type="hidden" name="rider" value="{html.escape(str(rider), quote=True)}" />
  <input type="hidden" name="tc_profile_mode" value="current" />
  {_rider_manager_html(user=user, rider=rider, load_rider_profile=load_rider_profile)}
  <div class="tc-profile-form-grid">
    <div class="tc-profile-field"><label for="profile-name">姓名 / 编号</label><input id="profile-name" name="rider_name" value="{html.escape(str(profile.get('name') or ''), quote=True)}" /></div>
    <div class="tc-profile-field"><label for="profile-weight">体重 kg</label><input id="profile-weight" name="weight" type="number" min="0" max="200" step="0.1" value="{html.escape(str(profile.get('weight') or 0), quote=True)}" /></div>
    <div class="tc-profile-field"><label for="profile-ftp">实测 FTP W</label><input id="profile-ftp" name="ftp_test" type="number" min="0" max="600" step="1" value="{html.escape(str(profile.get('ftp_test') or profile.get('ftp') or 0), quote=True)}" /></div>
    <div class="tc-profile-field"><label for="profile-max-hr">最大心率</label><input id="profile-max-hr" name="max_hr" type="number" min="0" max="250" step="1" value="{html.escape(str(profile.get('max_hr') or 0), quote=True)}" /></div>
    <div class="tc-profile-field"><label for="profile-lthr">乳酸阈值心率</label><input id="profile-lthr" name="lthr" type="number" min="0" max="230" step="1" value="{html.escape(str(profile.get('lthr') or 0), quote=True)}" /></div>
    <div class="tc-profile-field"><label for="profile-height">身高 cm</label><input id="profile-height" name="height" type="number" min="0" max="250" step="1" value="{html.escape(str(profile.get('height') or 0), quote=True)}" /></div>
    <div class="tc-profile-field full"><label for="profile-goal">训练目标</label><select id="profile-goal" name="goal">{_goal_options(goal_value)}</select></div>
    <div class="tc-profile-field full"><label for="profile-notes">备注 / 限制 / 近期目标</label><textarea id="profile-notes" name="notes">{html.escape(str(profile.get('notes') or ''))}</textarea></div>
  </div>
  <div class="tc-profile-actions"><button class="tc-profile-save" type="submit" data-current-label="保存当前骑手" data-new-label="保存为新骑手">保存当前骑手</button></div>
</form>
"""
    render_mac_modal_window(
        title="编辑骑手档案",
        intro="独立编辑窗口：保存后同步影响训练区间、功体比、AI 分析和课表生成。",
        form_html=form_html,
        close_url="?nav=骑手档案&sub=骑手资料",
        submit_label="保存骑手档案",
        window_id="tc-profile-edit-modal",
        extra_css=PROFILE_MODAL_CSS,
        extra_script=profile_modal_script("tc-profile-edit-modal"),
    )
