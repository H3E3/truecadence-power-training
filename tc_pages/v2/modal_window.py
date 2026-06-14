from __future__ import annotations

import html

import streamlit as st
import streamlit.components.v1 as components


BASE_MODAL_CSS = """
.tc-mac-modal-layer {
  position: fixed;
  inset: 0;
  z-index: -1;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 54px;
  box-sizing: border-box;
  pointer-events: none;
  opacity: 0;
  background: rgba(3, 4, 7, .52);
  backdrop-filter: blur(10px) saturate(1.04);
  -webkit-backdrop-filter: blur(10px) saturate(1.04);
}
.tc-mac-modal-layer:target,
.tc-mac-modal-layer.tc-force-open {
  z-index: 80;
  pointer-events: auto;
  animation: tcModalVeilIn .24s cubic-bezier(.22, 1, .36, 1) both;
}
.tc-mac-modal-layer.tc-saved-closed {
  z-index: -1 !important;
  pointer-events: none !important;
  opacity: 0 !important;
  animation: none !important;
}
.tc-mac-modal-window {
  width: min(980px, calc(100vw - 88px));
  max-height: min(760px, calc(100vh - 82px));
  overflow: auto;
  position: relative;
  color: #f4f0ea;
  background: linear-gradient(180deg, rgba(15, 18, 24, .98), rgba(8, 10, 13, .985));
  border: 1.4px solid rgba(240, 111, 50, .40);
  border-radius: 28px;
  box-shadow: 0 26px 70px rgba(0, 0, 0, .46), 0 0 0 1px rgba(255, 255, 255, .035) inset, 0 0 44px rgba(240, 111, 50, .10);
  transform-origin: 16% 37%;
  opacity: 0;
  transform: translate(-390px, -145px) scale(.16);
}
.tc-mac-modal-layer:target .tc-mac-modal-window,
.tc-mac-modal-layer.tc-force-open .tc-mac-modal-window {
  animation: tcModalOpenFromButton .42s cubic-bezier(.16, 1, .3, 1) both;
}
.tc-mac-modal-window.tc-closing {
  pointer-events: none;
  animation: tcModalReturnToButton .82s cubic-bezier(.55, 0, .18, 1) both;
}
.tc-mac-modal-layer:has(.tc-closing) {
  animation: tcModalVeilOut .82s cubic-bezier(.55, 0, .18, 1) both;
}
.tc-mac-modal-topbar {
  position: sticky;
  top: 0;
  z-index: 2;
  min-height: 72px;
  display: grid;
  grid-template-columns: 1fr 48px;
  align-items: center;
  padding: 18px 24px 14px;
  box-sizing: border-box;
  background: linear-gradient(180deg, rgba(15, 18, 24, .98), rgba(15, 18, 24, .88));
  border-bottom: 1px solid rgba(255, 255, 255, .06);
}
.tc-mac-modal-title {
  text-align: left;
  font-size: 19px;
  font-weight: 760;
  letter-spacing: -.02em;
  color: #f4f0ea;
}
.tc-mac-close {
  width: 36px;
  height: 36px;
  justify-self: end;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 13px;
  color: #bdb4aa !important;
  text-decoration: none !important;
  border: 1px solid rgba(255,255,255,.07);
  background: rgba(255,255,255,.035);
  font-size: 22px;
  line-height: 1;
}
.tc-mac-close:hover { color: #fff4ea !important; background: rgba(240,111,50,.13); border-color: rgba(240,111,50,.30); }
.tc-mac-modal-body { padding: 24px 34px 28px; }
.tc-mac-intro {
  color: #a7a19a;
  font-size: 15px;
  line-height: 1.65;
  margin: 0 0 24px;
}
@keyframes tcModalVeilIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes tcModalVeilOut { from { opacity: 1; } to { opacity: 0; } }
@keyframes tcModalOpenFromButton {
  0% { opacity: 0; transform: translate(-390px, -145px) scale(.16); filter: blur(10px); border-radius: 16px; }
  58% { opacity: 1; transform: translate(8px, 4px) scale(1.012); filter: blur(0); }
  100% { opacity: 1; transform: translate(0, 0) scale(1); filter: blur(0); border-radius: 28px; }
}
@keyframes tcModalReturnToButton {
  0% { opacity: 1; transform: translate(0, 0) scale(1); filter: blur(0); border-radius: 28px; }
  28% { opacity: .98; transform: translate(-34px, -10px) scale(.94); filter: blur(0); border-radius: 25px; }
  62% { opacity: .88; transform: translate(-190px, -66px) scale(.56); filter: blur(1.2px); border-radius: 20px; }
  100% { opacity: 0; transform: translate(-455px, -170px) scale(.10); filter: blur(10px); border-radius: 15px; }
}
@media (max-width: 860px) {
  .tc-mac-modal-window { width: calc(100vw - 28px); max-height: calc(100vh - 28px); }
  .tc-mac-modal-body { padding: 22px 18px 24px; }
}
@media (prefers-reduced-motion: reduce) {
  .tc-mac-modal-layer,
  .tc-mac-modal-window,
  .tc-mac-modal-window.tc-closing,
  .tc-mac-modal-layer:has(.tc-closing) { animation-duration: .01ms !important; animation-iteration-count: 1 !important; }
}
"""


def _modal_bridge_script(window_id: str) -> str:
    return f"""
(() => {{
  const doc = window.parent.document;
  const modal = doc.getElementById("{window_id}");
  if (!modal || modal.dataset.tcModalBridge === "1") return;
  modal.dataset.tcModalBridge = "1";
  const layer = modal.closest(".tc-mac-modal-layer");
  const openLayer = () => {{
    if (layer) {{
      layer.classList.remove("tc-saved-closed");
      layer.classList.add("tc-force-open");
      layer.style.zIndex = "140";
      layer.style.pointerEvents = "auto";
      layer.style.opacity = "1";
    }}
    modal.classList.remove("tc-closing");
  }};
  if (doc.defaultView.location.hash === "#" + modal.id + "-layer") openLayer();
  window.tcCloseModal = (targetModal) => {{
    const m = targetModal || modal;
    const l = m.closest(".tc-mac-modal-layer");
    m.classList.add("tc-closing");
    window.setTimeout(() => {{
      try {{
        if (l) {{
          l.classList.add("tc-saved-closed");
          l.classList.remove("tc-force-open");
          l.style.zIndex = "";
          l.style.pointerEvents = "";
          l.style.opacity = "";
        }}
        const parentWindow = doc.defaultView;
        if (parentWindow && parentWindow.history) {{
          parentWindow.history.replaceState(null, "", parentWindow.location.pathname + parentWindow.location.search);
        }}
      }} catch (error) {{}}
      m.classList.remove("tc-closing");
    }}, 860);
  }};
  doc.querySelectorAll('a[href="#' + modal.id + '-layer"]').forEach((link) => {{
    link.addEventListener("click", () => {{
      openLayer();
    }});
  }});
  modal.querySelectorAll("[data-tc-modal-close]").forEach((link) => {{
    link.addEventListener("click", (event) => {{
      event.preventDefault();
      window.tcCloseModal(modal);
    }});
  }});
}})();
"""


def render_mac_modal_window(
    *,
    title: str,
    intro: str,
    form_html: str,
    close_url: str,
    submit_label: str = "保存",
    window_id: str = "tc-mac-modal",
    closing: bool = False,
    redirect_url: str | None = None,
    extra_css: str = "",
    extra_script: str = "",
) -> None:
    """Render a reusable animated modal shell.

    Business-specific form markup, CSS, and JS should be supplied by the caller.
    """
    safe_title = html.escape(title)
    safe_intro = html.escape(intro)
    safe_close_url = html.escape(close_url, quote=True)
    safe_window_id = html.escape(window_id, quote=True)
    safe_redirect_url = html.escape(redirect_url or close_url, quote=True)
    closing_class = " tc-closing" if closing else ""
    refresh_html = f'<meta http-equiv="refresh" content="0.36;url={safe_redirect_url}">' if closing else ""

    st.html(
        f"""
<style>
{BASE_MODAL_CSS}
{extra_css}
</style>
{refresh_html}
<div class="tc-mac-modal-layer{' tc-force-open' if closing else ''}" id="{safe_window_id}-layer">
  <section class="tc-mac-modal-window{closing_class}" id="{safe_window_id}" role="dialog" aria-modal="true" aria-label="{safe_title}">
    <div class="tc-mac-modal-topbar">
      <div class="tc-mac-modal-title">{safe_title}</div>
      <a class="tc-mac-close" href="{safe_close_url}" target="_self" data-tc-modal-close aria-label="关闭">×</a>
    </div>
    <div class="tc-mac-modal-body">
      <p class="tc-mac-intro">{safe_intro}</p>
      {form_html}
    </div>
  </section>
</div>
"""
    )
    components.html(
        f"""
<script>
{_modal_bridge_script(safe_window_id)}
{extra_script}
</script>
""",
        height=0,
    )
