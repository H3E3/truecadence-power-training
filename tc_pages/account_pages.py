from __future__ import annotations

import datetime

import pandas as pd
import streamlit as st

from ui_components import (
    render_beta_feedback_intro,
    render_pricing_intro,
    render_upgrade_note,
)


def render_beta_feedback_page(load_beta_feedback, save_beta_feedback):
    st.title("🐞 内测反馈")
    st.caption("这里用于收集内测问题、体验建议和你希望 TrueCadence 优先改进的地方。")

    user = st.session_state.get("user", {})
    rider = st.session_state.get("rider", "默认骑手")

    render_beta_feedback_intro()

    with st.form("beta_feedback_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            contact = st.text_input("联系方式 / 微信 / 手机", placeholder="方便回访时填写,可留空")
            feedback_page = st.selectbox("问题页面", [
                "首页/功能说明", "注册/登录/内测邀请码", "骑手档案", "上传分析", "功率仪表盘",
                "训练负荷", "训练反馈", "恢复与睡眠", "AI 功率分析", "训练课表/ZWO",
                "营养与补给", "目标追踪", "套餐/权限", "手机端显示", "其他"
            ])
        with c2:
            issue_type = st.selectbox("反馈类型", ["Bug/报错", "看不懂/需要解释", "数据不符合预期", "体验建议", "功能建议", "视觉/手机端", "其他"])
            severity = st.selectbox("影响程度", ["一般建议", "影响理解", "影响使用", "阻塞无法继续"])

        description = st.text_area("问题描述", height=120, placeholder="请描述你看到的问题,或者希望改进的地方。")
        steps = st.text_area("操作步骤 / 复现方式", height=100, placeholder="例如:登录 → 上传 FIT → 进入训练负荷 → 点击合并历史 → 出现......")
        st.markdown("#### 快速三问(可选,但很重要)")
        favorite_feature = st.text_area("1. 你最喜欢 TrueCadence 的哪个功能?为什么?", height=80, placeholder="例如:AI 功率分析,因为能直接看懂自己哪里弱。")
        disliked_feature = st.text_area("2. 你最不喜欢、最想吐槽的地方是什么?", height=80, placeholder="例如:某个页面看不懂 / 手机端不好点 / 上传流程不顺。")
        paid_feature = st.text_area("3. 如果以后付费,你觉得哪个功能最值得付费?多少钱能接受?", height=80, placeholder="例如:训练课表 / Intervals 导入 / AI 分析;月付 XX 元或年付 XX 元。")
        expected = st.text_area("你期望它怎么表现", height=80, placeholder="例如:希望显示更明确的解释 / 希望按钮位置更明显 / 希望能导出......")
        allow_contact = st.checkbox("允许后续联系我确认细节", value=True)
        submitted = st.form_submit_button("提交内测反馈", use_container_width=True)

    if submitted:
        if not any(x.strip() for x in [description, steps, expected, favorite_feature, disliked_feature, paid_feature]):
            st.error("请至少填写一段问题描述、操作步骤、期望改进,或回答快速三问。")
        else:
            item = {
                "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "user_id": user.get("user_id", ""),
                "username": user.get("username", ""),
                "plan": user.get("plan", "free"),
                "rider": rider,
                "contact": contact.strip(),
                "page": feedback_page,
                "type": issue_type,
                "severity": severity,
                "description": description.strip(),
                "steps": steps.strip(),
                "expected": expected.strip(),
                "favorite_feature": favorite_feature.strip(),
                "disliked_feature": disliked_feature.strip(),
                "paid_feature": paid_feature.strip(),
                "allow_contact": bool(allow_contact),
            }
            try:
                data = load_beta_feedback()
                data.insert(0, item)
                save_beta_feedback(data)
                st.success("已收到,感谢。这个反馈会进入内测问题记录。")
            except Exception as e:
                st.error(f"保存失败:{e}")

    st.divider()
    my_items = [x for x in load_beta_feedback() if x.get("user_id") == user.get("user_id")]
    st.subheader("我的反馈记录")
    if not my_items:
        st.info("你还没有提交过反馈。遇到问题时直接在上面填写即可。")
    else:
        st.caption(f"已提交 {len(my_items)} 条。")
        show = []
        for x in my_items[:8]:
            show.append({
                "时间": x.get("created_at", ""),
                "页面": x.get("page", ""),
                "类型": x.get("type", ""),
                "影响": x.get("severity", ""),
                "描述": (x.get("description", "") or x.get("favorite_feature", "") or x.get("expected", ""))[:80],
            })
        st.dataframe(pd.DataFrame(show).astype(str), use_container_width=True, hide_index=True)




def render_pricing_page(
    *,
    PLANS,
    create_order,
    get_user_orders,
    hide_order_for_user,
    PAYMENT_WECHAT_QR_PATH,
    PAYMENT_ALIPAY_QR_PATH,
    user,
):
    st.title("💎 套餐与升级路径")
    st.caption("先免费看懂数据,再用 Core 开始系统训练;如果你有比赛和提升目标,Pro 会把训练、恢复、营养和目标追踪连成闭环。")

    current_plan = st.session_state.user.get("plan", "free")
    current_level = int(PLANS.get(current_plan, PLANS.get("free", {})).get("level", 0) or 0)
    paid_plan_keys = ("core", "pro", "coach")
    available_paid_plan_keys = [
        plan_key for plan_key in paid_plan_keys
        if int(PLANS.get(plan_key, {}).get("level", 0) or 0) > current_level
    ]

    render_pricing_intro()

    import html as _html
    plan_from_url = st.query_params.get("plan")
    if isinstance(plan_from_url, list):
        plan_from_url = plan_from_url[0] if plan_from_url else None
    if plan_from_url in paid_plan_keys:
        if plan_from_url in available_paid_plan_keys:
            st.session_state["selected_paid_plan"] = plan_from_url
            if st.session_state.get("last_plan_from_url") != plan_from_url:
                st.session_state["force_plan_sku"] = plan_from_url
                st.session_state["last_plan_from_url"] = plan_from_url
        else:
            st.session_state.pop("selected_paid_plan", None)
            st.session_state.pop("buy_sku", None)

    plans_data = [
        ("free", "免费版", "¥0", "适合:先试试看,了解自己数据", "结果:看懂基础功率数据,不再只看平均速度", ["上传 FIT 文件,查看基础功率分析", "基础 PMC 训练负荷曲线", "最近训练概览", "AI 点评每月 8 次"]),
        ("core", "Core版", "¥19/月 · ¥169/年", "适合:想开始系统训练的骑友", "结果:每周拿到可执行训练课表", ["AI 训练分析每月 30 次", "自动生成训练课表,导出 .ZWO 文件", "功率仪表盘与疲劳抗性分析", "训练负荷 PMC 曲线"]),
        ("pro", "Pro版", "¥49/月 · ¥449/年", "适合:有比赛、FTP 或体重管理目标", "结果:训练、恢复、营养、目标完整闭环", ["包含 Core 全部功能", "营养补给建议与比赛日策略", "恢复监督与睡眠优化", "目标追踪与周期化训练计划", "AI 动态分析无限次数"]),
        ("coach", "Coach版", "¥149/月 · ¥1349/年", "适合:教练、工作室或管理多位骑手", "结果:最多 20 位骑手档案、批量分析和长期跟踪", ["最多 20 位骑手管理", "AI 辅助教练分析与批量生成课表", "骑手分组与恢复监控", "包含 Pro 全部功能"]),
    ]
    icons = {"free":"🟦", "core":"🔥", "pro":"🏆", "coach":"👥"}
    colors = {"free":"var(--tc-subtle)", "core":"#ff6b35", "pro":"#f0c040", "coach":"#f85149"}
    bgs = {
        "free":"linear-gradient(180deg, rgba(139,148,158,0.10), var(--tc-surface))",
        "core":"linear-gradient(180deg, rgba(255,107,53,0.13), var(--tc-surface))",
        "pro":"linear-gradient(180deg, rgba(240,192,64,0.10), var(--tc-surface))",
        "coach":"linear-gradient(180deg, rgba(248,81,73,0.10), var(--tc-surface))",
    }
    card_cols = st.columns(4)
    for idx, (plan_key, name, price, fit, result, features) in enumerate(plans_data):
        with card_cols[idx]:
            color = colors[plan_key]
            version_tags = {"free":"体验", "core":"入门训练", "pro":"完整闭环", "coach":"多骑手"}
            with st.container(border=True):
                st.markdown('<div style="height:5px;border-radius:999px;background:rgba(255,255,255,0.05);margin:-.35em 0 .55em 0;"></div>', unsafe_allow_html=True)
                badge_lines = []
                if plan_key == current_plan:
                    badge_lines.append('<span class="plan-badge" style="margin-top:0;">当前套餐</span>')
                if st.session_state.get("selected_paid_plan") == plan_key:
                    badge_lines.append('<span class="plan-badge" style="background:#ff6b35;margin-top:.28em;">已选</span>')
                right_badges = '<div style="position:absolute;right:.85em;top:.75em;display:flex;flex-direction:column;align-items:flex-end;gap:.18em;white-space:nowrap;">' + ''.join(badge_lines) + '</div>' if badge_lines else ''
                st.markdown('<div style="position:relative;min-height:2.45em;margin-bottom:.2em;"><div style="color:' + color + ';font-size:.68em;font-weight:850;letter-spacing:.08em;padding-right:5.4em;">' + version_tags.get(plan_key, '') + '</div>' + right_badges + '</div>', unsafe_allow_html=True)
                if plan_key == "core":
                    st.markdown('<div style="height:34px;display:flex;align-items:flex-start;"><span class="plan-rec">🔥 推荐</span></div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div style="height:34px;display:flex;align-items:flex-start;"><span class="plan-rec" style="visibility:hidden;">占位</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="plan-name" style="color:{color};">{icons[plan_key]} {_html.escape(name)}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="plan-price">{_html.escape(price)}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="plan-fit">{_html.escape(fit)}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="plan-result">{_html.escape(result)}</div>', unsafe_allow_html=True)
                st.markdown('<div style="color:var(--tc-subtle);font-size:0.76em;font-weight:700;margin-bottom:0.35em;">包含</div>', unsafe_allow_html=True)
                feature_lines = list(features)[:5]
                while len(feature_lines) < 5:
                    feature_lines.append('')
                for f in feature_lines:
                    if f:
                        st.markdown('<div class="plan-feature">✦ ' + _html.escape(f) + '</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="plan-feature">&nbsp;</div>', unsafe_allow_html=True)
                st.markdown('<div style="height:.35em"></div>', unsafe_allow_html=True)
                if plan_key == "free":
                    st.button("免费体验", key="choose_card_free", disabled=True, use_container_width=True)
                else:
                    plan_level = int(PLANS.get(plan_key, {}).get("level", 0) or 0)
                    can_choose_plan = plan_level > current_level
                    btn_type = "primary" if st.session_state.get("selected_paid_plan") == plan_key else "secondary"
                    if st.button(f"选择 {name}" if can_choose_plan else ("当前套餐" if plan_key == current_plan else "不可降级/重复开通"), key=f"choose_card_{plan_key}", type=btn_type, use_container_width=True, disabled=not can_choose_plan):
                        st.session_state["selected_paid_plan"] = plan_key
                        st.session_state["buy_sku"] = (plan_key, "月付", PLANS[plan_key]["durations"]["月付"]["price"], PLANS[plan_key]["durations"]["月付"]["days"])
                        st.rerun()
    render_upgrade_note()

    st.subheader("开通 / 续费")
    selected_plan_for_order = st.session_state.get("selected_paid_plan") if st.session_state.get("selected_paid_plan") in available_paid_plan_keys else (available_paid_plan_keys[0] if available_paid_plan_keys else None)

    if not selected_plan_for_order:
        st.success(f"当前已经是 {PLANS.get(current_plan, PLANS['free'])['name']},无需再生成开通订单。")
        st.caption("如需续费、企业/工作室定制或人工调整到期时间,请通过内测反馈联系管理员处理。")
        orders = get_user_orders(user["user_id"])
        if orders:
            order_rows = []
            for o in sorted(orders, key=lambda x: x.get("created_at", ""), reverse=True)[:8]:
                order_rows.append({
                    "订单号": o.get("order_id"),
                    "套餐": o.get("plan_name"),
                    "周期": o.get("duration_label"),
                    "金额": o.get("amount"),
                    "状态": o.get("status"),
                    "创建时间": o.get("created_at", "")[:19],
                    "开通后到期": o.get("expires_at_after_paid") or "-",
                })
            st.dataframe(order_rows, use_container_width=True, hide_index=True)
        return

    sku_options = []
    for duration_label, duration in PLANS[selected_plan_for_order]["durations"].items():
        sku_options.append((selected_plan_for_order, duration_label, duration["price"], duration["days"]))

    default_index = next((i for i, x in enumerate(sku_options) if x[1] == "月付"), 0)
    current_sku = st.session_state.get("buy_sku")
    if current_sku not in sku_options:
        st.session_state["buy_sku"] = sku_options[default_index]

    selected_sku = st.radio(
        "选择付费周期",
        sku_options,
        format_func=lambda x: f"{PLANS[x[0]]['name']} · {x[1]} · ¥{x[2]} · {x[3]}天",
        key="buy_sku",
    )
    buy_plan, buy_duration, amount, days = selected_sku
    pay_method = st.selectbox(
        "支付方式",
        ["manual_wechat", "manual_alipay"],
        format_func=lambda x: "微信人工收款" if x == "manual_wechat" else "支付宝人工收款",
        key="buy_pay_method",
    )

    st.caption(f"将生成待支付订单:{PLANS[buy_plan]['name']} · {buy_duration} · ¥{amount} · {days}天")
    if st.button("生成开通订单", type="primary", use_container_width=True):
        checked = PLANS.get(buy_plan, {}).get("durations", {}).get(buy_duration)
        if not checked or checked.get("price") != amount or checked.get("days") != days:
            st.error("套餐价格校验失败,请刷新页面后重试。")
            st.stop()
        ok, msg, order = create_order(user["user_id"], buy_plan, buy_duration, pay_method)
        if ok:
            st.session_state["latest_order_id"] = msg
            st.success(f"订单已生成:{msg}")
            st.rerun()
        else:
            st.error(msg)

    latest_order_id = st.session_state.get("latest_order_id")
    orders = get_user_orders(user["user_id"])
    if latest_order_id:
        latest = next((o for o in orders if o.get("order_id") == latest_order_id), None)
        if latest:
            pay_label = "微信" if latest.get("payment_method") == "manual_wechat" else "支付宝"
            qr_path = PAYMENT_WECHAT_QR_PATH if latest.get("payment_method") == "manual_wechat" else PAYMENT_ALIPAY_QR_PATH
            st.markdown("### 待支付订单")
            p1, p2 = st.columns([1.05, 1])
            with p1:
                st.info(
                    f"订单号:{latest['order_id']}\n\n"
                    f"套餐:{latest['plan_name']} · {latest['duration_label']}\n\n"
                    f"金额:¥{float(latest['amount']):.0f}\n\n"
                    f"支付方式:{pay_label}\n\n"
                    f"付款备注请填写:{latest['order_id']} 或注册手机号"
                )
                st.code(latest["order_id"], language=None)
                st.caption("内测阶段采用人工确认收款。付款后管理员会在后台确认并开通套餐;如长时间未开通,可在「内测反馈」里提交订单号。")
            with p2:
                if qr_path.exists():
                    st.image(str(qr_path), caption=f"{pay_label}收款码|请支付 ¥{float(latest['amount']):.0f}", width=280)
                else:
                    st.warning(f"未找到{pay_label}收款码图片,请联系管理员人工付款。")
    if orders:
        st.subheader("我的订单")
        status_map = {"pending":"待支付", "paid":"已支付", "cancelled":"已取消", "refunded":"已退款", "expired":"已过期"}
        rows = []
        for o in orders[:10]:
            rows.append({
                "订单号": o.get("order_id"),
                "套餐": o.get("plan_name"),
                "周期": o.get("duration_label"),
                "金额": f"¥{float(o.get('amount', 0)):.0f}",
                "状态": status_map.get(o.get("status"), o.get("status")),
                "创建时间": o.get("created_at", "")[:19].replace("T", " "),
                "开通后到期": o.get("expires_at_after_paid") or "-",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        deletable_orders = [o for o in orders if o.get("status") in ("pending", "cancelled", "paid", "expired", "refunded")]
        if deletable_orders:
            with st.expander("删除我的订单记录", expanded=False):
                del_order_id = st.selectbox(
                    "选择要从列表移除的订单",
                    [o["order_id"] for o in deletable_orders],
                    format_func=lambda oid: next((f"{x['order_id']}|{x.get('plan_name','')}|{status_map.get(x.get('status'), x.get('status'))}" for x in deletable_orders if x["order_id"] == oid), oid),
                    key="user_hide_order_select",
                )
                st.caption("删除后只是不在你的订单列表显示;后台仍会保留必要记录,方便核对付款和售后。待支付订单会同时标记为已取消。")
                confirm_user_hide = st.checkbox(f"确认删除我的订单记录 {del_order_id}", key="confirm_user_hide_order")
                if st.button("删除我的订单记录", disabled=not confirm_user_hide, use_container_width=True):
                    ok, msg = hide_order_for_user(del_order_id, user["user_id"])
                    if ok:
                        if del_order_id == st.session_state.get("latest_order_id"):
                            st.session_state.pop("latest_order_id", None)
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

