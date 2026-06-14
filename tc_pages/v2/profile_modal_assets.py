from __future__ import annotations


PROFILE_MODAL_CSS = """
.tc-profile-modal-form { display: grid; gap: 14px; }
.tc-profile-manager { padding:16px; border:1px solid #211b16; border-radius:20px; background:#080a0d; }
.tc-profile-form-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
.tc-profile-field { display: grid; gap: 8px; }
.tc-profile-field label { color: #a7a19a; font-size: 14px; font-weight: 680; }
.tc-profile-field input,
.tc-profile-field select,
.tc-profile-field textarea {
  width: 100%;
  min-height: 48px;
  box-sizing: border-box;
  border-radius: 15px;
  border: 1px solid #253244;
  background: #0d1219;
  color: #f4f0ea;
  padding: 0 15px;
  font: 600 16px/1.2 -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'PingFang SC', Arial, sans-serif;
  outline: none;
}
.tc-profile-field textarea { min-height: 72px; padding: 11px 15px; resize: vertical; line-height: 1.45; }
.tc-profile-field input:focus,
.tc-profile-field select:focus,
.tc-profile-field textarea:focus {
  border-color: rgba(240,111,50,.82);
  box-shadow: 0 0 0 3px rgba(240,111,50,.14);
}
.tc-profile-field.full { grid-column: 1 / -1; }
.tc-profile-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 0; }
.tc-profile-save {
  min-width: 190px;
  height: 52px;
  border: 0;
  border-radius: 16px;
  background: #f06f32;
  color: #11151b;
  font-size: 17px;
  font-weight: 820;
  cursor: pointer;
  box-shadow: 0 10px 24px rgba(240,111,50,.20);
}
.tc-profile-save:hover { filter: brightness(1.05); }
@media (max-width: 860px) {
  .tc-profile-form-grid { grid-template-columns: 1fr; }
}
"""


def profile_modal_script(window_id: str) -> str:
    return f"""
(() => {{
  const doc = window.parent.document;
  const modal = doc.getElementById("{window_id}");
  if (!modal || modal.dataset.tcProfileBridge === "1") return;
  modal.dataset.tcProfileBridge = "1";
  const setText = (selector, value) => {{
    const node = doc.querySelector(selector);
    if (node) node.textContent = value || "";
  }};
  modal.querySelectorAll("form[data-tc-fetch-submit]").forEach((form) => {{
    const modeInput = form.querySelector('input[name="tc_profile_mode"]');
    const saveButton = form.querySelector(".tc-profile-save");
    const setFormProfile = (profile, mode) => {{
      if (modeInput) modeInput.value = mode;
      const setValue = (selector, value) => {{
        const field = form.querySelector(selector);
        if (field) field.value = value ?? "";
      }};
      setValue("#profile-name", profile.name || "");
      setValue("#profile-weight", profile.weight || "");
      setValue("#profile-ftp", profile.ftp_test || profile.ftp || "");
      setValue("#profile-max-hr", profile.max_hr || "");
      setValue("#profile-lthr", profile.lthr || "");
      setValue("#profile-height", profile.height || "");
      setValue("#profile-notes", profile.notes || "");
      const goal = form.querySelector("#profile-goal");
      if (goal) goal.value = profile.goal || "恢复体能 / 重建基础";
      if (saveButton) saveButton.textContent = mode === "new" ? (saveButton.dataset.newLabel || "保存为新骑手") : (saveButton.dataset.currentLabel || "保存当前骑手");
    }};
    const riderSelector = form.querySelector("#profile-target-rider");
    let riderProfiles = {{}};
    if (riderSelector) {{
      try {{ riderProfiles = JSON.parse(riderSelector.dataset.riderProfiles || "{{}}"); }} catch (error) {{}}
      riderSelector.addEventListener("change", () => {{
        if (riderSelector.value === "__new__") {{
          setFormProfile({{}}, "new");
        }} else {{
          setFormProfile(riderProfiles[riderSelector.value] || {{}}, "current");
          const hiddenRider = form.querySelector('input[name="rider"]');
          if (hiddenRider) hiddenRider.value = riderSelector.value;
        }}
      }});
    }}

    form.addEventListener("submit", async (event) => {{
      event.preventDefault();
      if (form.dataset.tcSubmitting === "1") return;
      form.dataset.tcSubmitting = "1";
      if (saveButton) {{
        saveButton.disabled = true;
        saveButton.textContent = "保存中…";
      }}
      const payload = Object.fromEntries(new FormData(form).entries());
      try {{
        const response = await fetch("http://127.0.0.1:8503/api/rider-profile/save", {{
          method: "POST",
          credentials: "include",
          headers: {{"Content-Type": "application/json"}},
          body: JSON.stringify(payload),
        }});
        const data = await response.json().catch(() => ({{}}));
        if (!response.ok || !data.ok) throw new Error(data.error || "保存失败");
        const ui = data.ui || {{}};
        setText("[data-tc-profile-name]", ui.name);
        setText("[data-tc-profile-summary]", ui.summary);
        setText("[data-tc-training-bg-title]", ui.training_bg_title);
        setText("[data-tc-training-bg-text]", ui.training_bg_text);
        setText("[data-tc-current-rider]", ui.rider);
        setText("[data-tc-rider-count]", ui.rider_count_text);
        const hiddenRider = form.querySelector('input[name="rider"]');
        if (hiddenRider && ui.rider) hiddenRider.value = ui.rider;
        if (modeInput) modeInput.value = "current";
        if (ui.rider && riderSelector) {{
          let option = Array.from(riderSelector.options).find((item) => item.value === ui.rider);
          if (!option) {{
            option = doc.createElement("option");
            option.value = ui.rider;
            option.textContent = ui.rider;
            const newOption = Array.from(riderSelector.options).find((item) => item.value === "__new__");
            riderSelector.insertBefore(option, newOption || null);
          }}
          riderSelector.value = ui.rider;
        }}
        if (ui.rider) {{
          doc.querySelectorAll(".tc-rider-dropdown a").forEach((item) => item.classList.toggle("active", item.textContent === ui.rider));
          const dropdown = doc.querySelector(".tc-rider-dropdown");
          if (dropdown && !Array.from(dropdown.querySelectorAll("a")).some((item) => item.textContent === ui.rider)) {{
            const item = doc.createElement("a");
            item.textContent = ui.rider;
            item.className = "active";
            item.href = "?nav=" + encodeURIComponent("骑手档案") + "&sub=" + encodeURIComponent("骑手资料") + "&tc_rider=" + encodeURIComponent(ui.rider);
            item.target = "_self";
            dropdown.appendChild(item);
          }}
        }}
        if (data.profile) {{
          const p = data.profile;
          if (ui.rider && riderSelector) {{
            riderProfiles[ui.rider] = p;
            riderSelector.dataset.riderProfiles = JSON.stringify(riderProfiles);
          }}
          setFormProfile(p, "current");
        }}
        if (window.tcCloseModal) window.tcCloseModal(modal);
        window.setTimeout(() => {{
          form.dataset.tcSubmitting = "0";
          if (saveButton) {{
            saveButton.disabled = false;
            saveButton.textContent = saveButton.dataset.currentLabel || "保存当前骑手";
          }}
        }}, 860);
      }} catch (error) {{
        form.dataset.tcSubmitting = "0";
        if (saveButton) {{
          const mode = form.querySelector('input[name="tc_profile_mode"]')?.value || "current";
          saveButton.disabled = false;
          saveButton.textContent = mode === "new" ? (saveButton.dataset.newLabel || "保存为新骑手") : (saveButton.dataset.currentLabel || "保存当前骑手");
        }}
        const msg = doc.createElement("div");
        msg.textContent = "保存失败，请稍后重试";
        msg.style.cssText = "margin-top:10px;color:#ffb4a2;font-weight:700;";
        const actions = form.querySelector(".tc-profile-actions");
        if (actions && !form.querySelector(".tc-profile-save-error")) {{
          msg.className = "tc-profile-save-error";
          actions.prepend(msg);
        }}
      }}
    }});
  }});
}})();
"""
