from __future__ import annotations

import html

import streamlit as st

from auth import PLANS
from tc_pages.v2.modal_window import render_mac_modal_window


ACCOUNT_MODAL_CSS = """
.tc-account-cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.tc-account-card {
  min-height: 142px;
  border: 1px solid #211b16;
  border-radius: 22px;
  background: #080a0d;
  padding: 18px;
  box-sizing: border-box;
}
.tc-account-card.hot { background: #15100c; border-color: #4a2b1c; }
.tc-account-card .k {
  color: #f06f32;
  font-size: 12px;
  font-weight: 850;
  letter-spacing: .07em;
  margin-bottom: 12px;
}
.tc-account-card .v {
  color: #f4f0ea;
  font-size: 22px;
  line-height: 1.16;
  font-weight: 820;
  letter-spacing: -.025em;
  margin-bottom: 8px;
}
.tc-account-card .d { color: #a7a19a; font-size: 14px; line-height: 1.55; }
.tc-account-actions { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 18px; }
.tc-account-actions a {
  min-height: 46px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 15px;
  padding: 0 18px;
  text-decoration: none !important;
  font-size: 16px;
  font-weight: 780;
}
.tc-account-actions .primary { background: #f06f32; color: #11151b !important; border: 1px solid #f06f32; }
.tc-account-actions .secondary { background: #0d1219; color: #f4f0ea !important; border: 1px solid #253244; }
.tc-plan-version-cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.tc-plan-version-card {
  min-height: 312px;
  border: 1px solid #211b16;
  border-radius: 24px;
  background: #080a0d;
  padding: 20px;
  box-sizing: border-box;
  position: relative;
  display: flex;
  flex-direction: column;
}
.tc-plan-version-card.current { background: #15100c; border-color: #f06f32; box-shadow: 0 0 0 1px rgba(240,111,50,.14) inset; }
.tc-plan-version-card .badge {
  position: absolute;
  right: 16px;
  top: 16px;
  min-height: 24px;
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0 10px;
  background: rgba(240,111,50,.14);
  color: #f06f32;
  font-size: 12px;
  font-weight: 820;
}
.tc-plan-version-card .name { color: #f4f0ea; font-size: 24px; font-weight: 840; letter-spacing: -.035em; margin-bottom: 8px; }
.tc-plan-version-card .price { color: #f06f32; font-size: 18px; font-weight: 820; margin-bottom: 12px; }
.tc-plan-version-card .meta { color: #a7a19a; font-size: 14px; line-height: 1.5; margin-bottom: 14px; }
.tc-plan-version-card ul { margin: 0; padding: 0; list-style: none; display: grid; gap: 8px; }
.tc-plan-version-card ul { flex: 1; }
.tc-plan-version-card li { color: #d8c7bb; font-size: 13px; line-height: 1.42; }
.tc-plan-version-card li::before { content: ""; display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #f5b84b; margin-right: 8px; transform: translateY(-1px); }
.tc-plan-version-card.selected { border-color: #f5b84b; box-shadow: 0 0 0 1px rgba(245,184,75,.20) inset, 0 18px 36px rgba(0,0,0,.26); }
.tc-plan-choice {
  width: 100%;
  min-height: 44px;
  margin-top: auto;
  border: 1px solid #253244;
  border-radius: 15px;
  background: #0d1219;
  color: #f4f0ea!important;
  font-size: 15px;
  font-weight: 820;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none!important;
  box-sizing: border-box;
}
.tc-plan-choice.primary { background: #f06f32; border-color: #f06f32; color: #11151b!important; }
.tc-plan-choice.disabled { cursor: default; opacity: .78; background: rgba(240,111,50,.14); border-color: rgba(240,111,50,.40); color: #f06f32!important; pointer-events: none; }
.tc-plan-selected-note { margin-top: 16px; color: #f5b84b; font-size: 14px; font-weight: 780; min-height: 20px; }
.tc-order-summary { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.tc-order-box { border:1px solid #211b16; border-radius:22px; background:#080a0d; padding:18px; }
.tc-order-box.hot { background:#15100c; border-color:#4a2b1c; }
.tc-order-k { color:#f06f32; font-size:12px; font-weight:850; letter-spacing:.07em; margin-bottom:10px; }
.tc-order-v { color:#f4f0ea; font-size:24px; font-weight:840; letter-spacing:-.03em; margin-bottom:8px; }
.tc-order-d { color:#a7a19a; font-size:14px; line-height:1.55; }
.tc-duration-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; margin-top:16px; }
.tc-duration-choice { min-height:76px; text-align:left; border:1px solid #253244; border-radius:18px; background:#0d1219; color:#f4f0ea; padding:14px 16px; cursor:pointer; }
.tc-duration-choice.active { border-color:#f06f32; background:rgba(240,111,50,.13); box-shadow:0 0 0 1px rgba(240,111,50,.18) inset; }
.tc-duration-choice .t { display:block; font-size:16px; font-weight:840; margin-bottom:6px; }
.tc-duration-choice .p { display:block; color:#f5b84b; font-size:14px; font-weight:800; }
.tc-order-actions { display:flex; gap:12px; justify-content:flex-end; margin-top:18px; }
.tc-order-actions a, .tc-order-actions button { min-height:46px; border-radius:15px; padding:0 18px; font-size:16px; font-weight:820; text-decoration:none!important; }
.tc-order-actions .secondary { display:inline-flex; align-items:center; justify-content:center; background:#0d1219; color:#f4f0ea!important; border:1px solid #253244; }
.tc-order-actions .primary { background:#f06f32; color:#11151b; border:1px solid #f06f32; cursor:pointer; }
.tc-order-note { color:#a7a19a; font-size:13px; line-height:1.6; margin-top:12px; }
@media (max-width: 1100px) { .tc-plan-version-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 760px) { .tc-order-summary, .tc-duration-grid { grid-template-columns:1fr; } }
@media (max-width: 980px) { .tc-account-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 620px) { .tc-account-cards, .tc-plan-version-cards { grid-template-columns: 1fr; } }
"""


def _mask_phone(phone: str) -> str:
    phone = str(phone or "")
    if len(phone) >= 7:
        return f"{phone[:3]}****{phone[-4:]}"
    return phone or "未登录"


def _remaining_text(user: dict | None) -> str:
    if not user:
        return "-"
    expires = user.get("expires") or ""
    if not expires:
        return "永久 / 未设置"
    try:
        from datetime import date

        days = (date.fromisoformat(str(expires)) - date.today()).days
    except Exception:
        return str(expires)
    if days >= 9999:
        return "永久"
    if days < 0:
        return f"已到期 {abs(days)} 天"
    return f"剩余 {days} 天"


def _plan_price_text(plan_key: str, plan: dict) -> str:
    durations = plan.get("durations") or {}
    if plan_key == "free":
        return "¥0 / 永久"
    year = durations.get("年付") or {}
    month = durations.get("月付") or {}
    if year and month:
        return f"¥{month.get('price')} / 月 · ¥{year.get('price')} / 年"
    if year:
        return f"¥{year.get('price')} / 年"
    return "价格待确认"


def _plan_modal_script(window_id: str) -> str:
    return f"""
(() => {{
  const doc = window.parent.document;
  const modal = doc.getElementById("{window_id}");
  if (!modal || modal.dataset.tcPlanChoiceBridge === "1") return;
  modal.dataset.tcPlanChoiceBridge = "1";
  const note = modal.querySelector("[data-tc-plan-selected-note]");
  modal.querySelectorAll("a[data-tc-plan-choice]").forEach((button) => {{
    button.addEventListener("click", (event) => {{
      event.preventDefault();
      const plan = button.dataset.tcPlanChoice || "";
      const name = button.dataset.tcPlanName || plan;
      const monthPrice = button.dataset.tcMonthPrice || "";
      const monthDays = button.dataset.tcMonthDays || "";
      const yearPrice = button.dataset.tcYearPrice || "";
      const yearDays = button.dataset.tcYearDays || "";
      modal.querySelectorAll(".tc-plan-version-card").forEach((card) => card.classList.toggle("selected", card.dataset.tcPlanCard === plan));
      modal.querySelectorAll("a[data-tc-plan-choice]").forEach((item) => {{
        item.textContent = item.dataset.defaultLabel || item.textContent;
      }});
      button.textContent = "已选择 " + name;
      if (note) note.textContent = "已选择：" + name + "。正在打开周期选择 / 订单确认。";
      const orderModal = doc.getElementById("tc-plan-order-modal");
      if (orderModal) {{
        orderModal.querySelectorAll("[data-order-plan-name]").forEach((node) => node.textContent = name);
        orderModal.querySelectorAll("[data-order-plan-key]").forEach((node) => node.textContent = plan);
        orderModal.querySelectorAll("button[data-duration]").forEach((item) => {{
          const isYear = item.dataset.duration === "年付";
          const price = isYear ? yearPrice : monthPrice;
          const days = isYear ? yearDays : monthDays;
          const priceNode = item.querySelector(".p");
          if (priceNode) priceNode.textContent = "¥" + price + " · " + days + "天";
          item.dataset.price = price;
          item.dataset.days = days;
          item.dataset.plan = plan;
          item.dataset.planName = name;
        }});
        const month = orderModal.querySelector('button[data-duration="月付"]');
        if (month) month.click();
        const currentLayer = modal.closest(".tc-mac-modal-layer");
        if (currentLayer) currentLayer.classList.add("tc-saved-closed");
        const layer = doc.getElementById("tc-plan-order-modal-layer");
        if (layer) {{
          layer.classList.remove("tc-saved-closed");
          layer.classList.add("tc-force-open");
          layer.style.zIndex = "140";
          layer.style.pointerEvents = "auto";
          layer.style.opacity = "1";
        }}
        doc.defaultView.location.hash = "tc-plan-order-modal-layer";
      }}
    }});
  }});
}})();
"""


def _order_modal_script(window_id: str) -> str:
    return f"""
(() => {{
  const doc = window.parent.document;
  const modal = doc.getElementById("{window_id}");
  if (!modal || modal.dataset.tcOrderBridge === "1") return;
  modal.dataset.tcOrderBridge = "1";
  const setText = (selector, value) => modal.querySelectorAll(selector).forEach((node) => node.textContent = value || "");
  modal.querySelectorAll("button[data-duration]").forEach((button) => {{
    button.addEventListener("click", () => {{
      modal.querySelectorAll("button[data-duration]").forEach((item) => item.classList.toggle("active", item === button));
      const planName = button.dataset.planName || modal.querySelector("[data-order-plan-name]")?.textContent || "-";
      const duration = button.dataset.duration || "月付";
      const price = button.dataset.price || "-";
      const days = button.dataset.days || "-";
      setText("[data-order-duration]", duration);
      setText("[data-order-amount]", price === "-" ? "-" : "¥" + price);
      setText("[data-order-days]", days === "-" ? "-" : days + "天");
      setText("[data-order-confirm-text]", "确认 " + planName + " · " + duration + " · ¥" + price);
    }});
  }});
  modal.querySelectorAll("a[href='#tc-plan-cards-modal-layer']").forEach((link) => {{
    link.addEventListener("click", (event) => {{
      event.preventDefault();
      const orderLayer = modal.closest(".tc-mac-modal-layer");
      if (orderLayer) {{
        orderLayer.classList.add("tc-saved-closed");
        orderLayer.classList.remove("tc-force-open");
        orderLayer.style.zIndex = "";
        orderLayer.style.pointerEvents = "";
        orderLayer.style.opacity = "";
      }}
      const planLayer = doc.getElementById("tc-plan-cards-modal-layer");
      if (planLayer) {{
        planLayer.classList.remove("tc-saved-closed");
        planLayer.classList.add("tc-force-open");
        planLayer.style.zIndex = "140";
        planLayer.style.pointerEvents = "auto";
        planLayer.style.opacity = "1";
      }}
      doc.defaultView.location.hash = "tc-plan-cards-modal-layer";
    }});
  }});
  modal.querySelectorAll("button[data-order-confirm]").forEach((button) => {{
    button.addEventListener("click", () => {{
      const msg = modal.querySelector("[data-order-result]");
      if (msg) msg.textContent = "订单确认弹窗 UI 已就绪；下一步接后端 create_order 后会生成真实订单号。";
    }});
  }});
}})();
"""


def _render_plan_order_modal() -> None:
    selected_plan = st.query_params.get("order_plan")
    if isinstance(selected_plan, list):
        selected_plan = selected_plan[0] if selected_plan else None
    if selected_plan not in ("core", "pro", "coach"):
        selected_plan = "core"
    selected = PLANS[selected_plan]
    selected_name = selected.get("name", selected_plan)
    durations = selected.get("durations") or {}
    month = durations.get("月付") or {}
    year = durations.get("年付") or {}
    month_price = html.escape(str(month.get("price", "-")))
    month_days = html.escape(str(month.get("days", "-")))
    year_price = html.escape(str(year.get("price", "-")))
    year_days = html.escape(str(year.get("days", "-")))
    form_html = f"""
<div class="tc-order-summary">
  <section class="tc-order-box hot"><div class="tc-order-k">已选套餐</div><div class="tc-order-v" data-order-plan-name>{html.escape(str(selected_name))}</div><div class="tc-order-d">套餐代码：<span data-order-plan-key>{html.escape(str(selected_plan))}</span></div></section>
  <section class="tc-order-box"><div class="tc-order-k">订单预览</div><div class="tc-order-v" data-order-amount>¥{month_price}</div><div class="tc-order-d"><span data-order-duration>月付</span> · 有效期 <span data-order-days>{month_days}天</span></div></section>
</div>
<div class="tc-duration-grid">
  <button class="tc-duration-choice active" type="button" data-duration="月付" data-plan="{html.escape(str(selected_plan), quote=True)}" data-plan-name="{html.escape(str(selected_name), quote=True)}" data-price="{month_price}" data-days="{month_days}"><span class="t">月付</span><span class="p">¥{month_price} · {month_days}天</span></button>
  <button class="tc-duration-choice" type="button" data-duration="年付" data-plan="{html.escape(str(selected_plan), quote=True)}" data-plan-name="{html.escape(str(selected_name), quote=True)}" data-price="{year_price}" data-days="{year_days}"><span class="t">年付</span><span class="p">¥{year_price} · {year_days}天</span></button>
</div>
<div class="tc-order-actions">
  <a target="_self" class="secondary" href="#tc-plan-cards-modal-layer">返回套餐</a>
  <button class="primary" type="button" data-order-confirm><span data-order-confirm-text>确认订单</span></button>
</div>
<div class="tc-order-note" data-order-result>内测阶段订单仍需人工确认收款；这里先做新版弹窗流程，不跳回旧版页面。</div>
"""
    render_mac_modal_window(
        title="周期选择 / 订单确认",
        intro="选择付费周期，确认套餐金额和有效期。",
        form_html=form_html,
        close_url=f"?{_current_page_query()}",
        submit_label="确认订单",
        window_id="tc-plan-order-modal",
        extra_css=ACCOUNT_MODAL_CSS,
        extra_script=_order_modal_script("tc-plan-order-modal"),
    )


def _current_page_query() -> str:
    nav = st.query_params.get("nav") or "训练驾驶舱"
    sub = st.query_params.get("sub") or "首页简报"
    if isinstance(nav, list):
        nav = nav[0] if nav else "训练驾驶舱"
    if isinstance(sub, list):
        sub = sub[0] if sub else "首页简报"
    from urllib.parse import quote
    return f"nav={quote(str(nav))}&sub={quote(str(sub))}"


def _render_plan_versions_modal(current_plan: str) -> None:
    cards = []
    base_query = _current_page_query()
    current_level = int(PLANS.get(current_plan, PLANS["free"]).get("level", 0) or 0)
    for plan_key in ["free", "core", "pro", "coach"]:
        plan = PLANS[plan_key]
        plan_name = str(plan.get("name", plan_key))
        plan_level = int(plan.get("level", 0) or 0)
        features = plan.get("features") or []
        feature_html = "".join(f"<li>{html.escape(str(item))}</li>" for item in features[:5])
        current_cls = " current" if plan_key == current_plan else ""
        badge = '<span class="badge">当前套餐</span>' if plan_key == current_plan else ""
        if plan_key == current_plan:
            button_html = '<span class="tc-plan-choice disabled">当前套餐</span>'
        elif plan_level <= current_level:
            button_html = '<span class="tc-plan-choice disabled">不可降级/重复开通</span>'
        else:
            safe_label = html.escape(f"选择 {plan_name}")
            month = (plan.get("durations") or {}).get("月付") or {}
            year = (plan.get("durations") or {}).get("年付") or {}
            button_html = (
                f'<a target="_self" class="tc-plan-choice primary" href="#tc-plan-order-modal-layer" '
                f'data-tc-plan-choice="{html.escape(plan_key, quote=True)}" data-tc-plan-name="{html.escape(plan_name, quote=True)}" data-default-label="{safe_label}" '
                f'data-tc-month-price="{html.escape(str(month.get("price", "")), quote=True)}" data-tc-month-days="{html.escape(str(month.get("days", "")), quote=True)}" '
                f'data-tc-year-price="{html.escape(str(year.get("price", "")), quote=True)}" data-tc-year-days="{html.escape(str(year.get("days", "")), quote=True)}">{safe_label}</a>'
            )
        cards.append(
            f"""
<section class="tc-plan-version-card{current_cls}" data-tc-plan-card="{html.escape(plan_key, quote=True)}">
  {badge}
  <div class="name">{html.escape(plan_name)}</div>
  <div class="price">{html.escape(_plan_price_text(plan_key, plan))}</div>
  <div class="meta">支持 {html.escape(str(plan.get('riders', 1)))} 位骑手 · 等级 {html.escape(str(plan.get('level', 0)))}</div>
  <ul>{feature_html}</ul>
  {button_html}
</section>
"""
        )
    render_mac_modal_window(
        title="套餐版本",
        intro="四个版本只在这里横向对比；不跳回旧版页面。具体开通仍按内测邀请码 / 人工确认流程处理。",
        form_html=f'<div class="tc-plan-version-cards">{"".join(cards)}</div><div class="tc-plan-selected-note" data-tc-plan-selected-note></div>',
        close_url=f"?{base_query}",
        submit_label="关闭",
        window_id="tc-plan-cards-modal",
        extra_css=ACCOUNT_MODAL_CSS,
        extra_script=_plan_modal_script("tc-plan-cards-modal"),
    )


def render_account_plan_modal() -> None:
    user = st.session_state.get("user") or {}
    riders = (user.get("riders") or {}) if isinstance(user, dict) else {}
    plan_key = user.get("plan", "free") if isinstance(user, dict) else "free"
    plan_info = PLANS.get(plan_key, PLANS["free"])
    rider_count = len(riders) or 1
    rider_limit = plan_info.get("riders", 1)
    current_rider = st.session_state.get("rider", "默认骑手")
    history_count = st.session_state.get("tc_sidebar_history_count", 0)
    phone = _mask_phone(user.get("phone") or user.get("username") or "")
    plan_name = plan_info.get("name", "免费版")
    remaining = _remaining_text(user)

    cards = [
        ("账号", phone, "当前登录账号，仅在本设备保持登录状态。", "hot"),
        ("当前套餐", plan_name, f"支持 {rider_limit} 位骑手 · {remaining}", ""),
        ("骑手", f"{rider_count}/{rider_limit}", f"当前骑手：{html.escape(str(current_rider))}", ""),
        ("训练存档", f"{history_count} 条", "当前骑手已导入/解析的训练摘要。", ""),
    ]
    card_html = "".join(
        f'<section class="tc-account-card {cls}"><div class="k">{html.escape(k)}</div><div class="v">{html.escape(str(v))}</div><div class="d">{d}</div></section>'
        for k, v, d, cls in cards
    )
    form_html = f"""
<div class="tc-account-cards">{card_html}</div>
<div class="tc-account-actions">
  <a target="_self" class="primary" href="#tc-plan-cards-modal-layer">查看 / 升级套餐</a>
</div>
"""
    render_mac_modal_window(
        title="账号与套餐",
        intro="旧版四张卡片信息归位到独立弹窗：账号、当前套餐、骑手数量和训练存档。",
        form_html=form_html,
        close_url=f"?{_current_page_query()}",
        submit_label="关闭",
        window_id="tc-account-plan-modal",
        extra_css=ACCOUNT_MODAL_CSS,
    )
    _render_plan_versions_modal(plan_key)
    _render_plan_order_modal()
