from __future__ import annotations

import datetime
import json

import pandas as pd
import streamlit as st

from ui_components import (
    render_danger_note,
    render_profile_help,
    render_profile_intro,
    render_profile_section_title,
    render_training_feedback_intro,
    render_training_feedback_section,
)


def render_training_feedback_page(*, load_feedback, save_feedback, load_profile):
    st.title("📝 训练反馈")
    st.caption("记录睡眠、疲劳、疼痛、不适和训练后感受。后续 AI 分析会结合这些主观信息,判断是否该降强度、恢复或调整课表。")

    render_training_feedback_intro()

    feedback = load_feedback()
    profile = load_profile()
    cycle_enabled_for_feedback = bool(profile.get('cycle_enabled')) or profile.get('gender') == '女'

    with st.form("feedback_form"):
        render_training_feedback_section("今日状态")
        c1, c2, c3 = st.columns(3)
        fb_date = c1.date_input("日期", value=datetime.date.today())
        sleep_quality = c2.slider("睡眠质量", 1, 5, 3, help="1=很差,5=很好")
        energy = c3.slider("精神状态", 1, 5, 3, help="1=很差,5=很好")
        c4, c5, c6 = st.columns(3)
        leg_fatigue = c4.slider("腿部疲劳", 1, 5, 3, help="1=很轻松,5=很沉很累")
        stress = c5.slider("生活/工作压力", 1, 5, 3)
        morning_hr = c6.number_input("晨脉/静息心率", 0, 160, 0, help="可选")

        render_training_feedback_section("训练后反馈")
        c7, c8, c9 = st.columns(3)
        rpe = c7.slider("RPE 主观强度", 1, 10, 5, help="1=非常轻松,10=极限")
        completion = c8.selectbox("完成度", ["未训练", "轻松完成", "正常完成", "勉强完成", "没完成"])
        leg_feel = c9.selectbox("腿感", ["正常", "轻松", "沉", "酸", "抽筋", "发软"])
        c10, c11 = st.columns(2)
        breathing = c10.selectbox("呼吸/心肺感受", ["正常", "喘不上来", "胸闷", "心率异常偏高", "心率异常偏低"])
        fueling = c11.selectbox("补给情况", ["正常", "吃少了", "喝少了", "胃不舒服", "低血糖感", "不适用"])

        render_training_feedback_section("不适与特殊情况")
        pain_options = ["膝盖", "腰", "颈肩", "手麻", "坐垫压迫", "脚麻/脚痛", "髋/臀", "跟腱/小腿"]
        pains = st.multiselect("哪里不舒服", pain_options, default=[], placeholder="无不适可留空")
        special_options = ["感冒", "发烧", "睡眠不足", "饮酒", "出差/旅行", "天气太热", "天气太冷", "工作压力大"]
        specials = st.multiselect("特殊情况", special_options, default=[], placeholder="无特殊情况可留空")
        cycle_status = '不记录'
        cycle_pain = '无'
        cycle_flow = '不记录'
        cycle_mood = '不记录'
        cycle_training_impact = '不记录'
        if cycle_enabled_for_feedback:
            render_training_feedback_section("女性周期状态")
            fc1, fc2, fc3 = st.columns(3)
            cycle_status = fc1.selectbox("今日周期状态", ["不记录", "经期第1-2天", "经期第3-5天", "经期后恢复期", "排卵期附近", "经前期/PMS", "周期正常,无明显影响"], key="fb_cycle_status")
            cycle_pain = fc2.selectbox("腹痛/腰酸", ["无", "轻", "中", "重"], key="fb_cycle_pain")
            cycle_flow = fc3.selectbox("出血量", ["不记录", "少", "中", "多"], key="fb_cycle_flow")
            fc4, fc5 = st.columns(2)
            cycle_mood = fc4.selectbox("情绪波动", ["不记录", "低", "中", "高"], key="fb_cycle_mood")
            cycle_training_impact = fc5.selectbox("是否影响训练", ["不记录", "不影响", "轻微", "明显"], key="fb_cycle_training_impact")

        notes = st.text_area("备注", placeholder="例如:今天鼻塞,没做完间歇;右膝外侧痛;补给没吃够后半程掉功率。")

        submitted = st.form_submit_button("💾 保存训练反馈", type="primary", use_container_width=True)

    if submitted:
        entry = {
            "date": fb_date.isoformat(), "sleep_quality": sleep_quality, "energy": energy,
            "leg_fatigue": leg_fatigue, "stress": stress, "morning_hr": morning_hr,
            "rpe": rpe, "completion": completion, "leg_feel": leg_feel,
            "breathing": breathing, "fueling": fueling,
            "pains": pains,
            "specials": specials,
            "notes": notes,
            "cycle_status": cycle_status, "cycle_pain": cycle_pain,
            "cycle_flow": cycle_flow, "cycle_mood": cycle_mood,
            "cycle_training_impact": cycle_training_impact,
            "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        feedback = [x for x in feedback if x.get("date") != entry["date"]]
        feedback.append(entry)
        feedback.sort(key=lambda x: x.get("date", ""), reverse=True)
        save_feedback(feedback)
        st.session_state.pop("ai_diagnosis", None)
        st.session_state.pop("ai_signature", None)
        st.session_state["feedback_saved_notice"] = f"✅ {entry['date']} 训练反馈已保存,AI 功率分析会自动纳入这条反馈"
        st.success(st.session_state["feedback_saved_notice"])

    if st.session_state.get("feedback_saved_notice"):
        st.success(st.session_state["feedback_saved_notice"])

    st.divider()
    st.subheader("最近反馈")
    if feedback:
        df_fb = pd.DataFrame(feedback[:14])
        show_cols = ["date", "sleep_quality", "energy", "leg_fatigue", "stress", "rpe", "completion", "leg_feel", "pains", "specials", "cycle_status", "cycle_pain", "cycle_training_impact", "notes"]
        df_fb = df_fb[[c for c in show_cols if c in df_fb.columns]].copy()
        for col in ["pains", "specials"]:
            if col in df_fb.columns:
                df_fb[col] = df_fb[col].apply(lambda x: "、".join(x) if isinstance(x, list) and x else "")
        st.dataframe(df_fb.astype(str), use_container_width=True, hide_index=True,
                     column_config={"date": "日期", "sleep_quality": "睡眠", "energy": "精神", "leg_fatigue": "腿疲劳", "stress": "压力", "rpe": "RPE", "completion": "完成度", "leg_feel": "腿感", "pains": "不适", "specials": "特殊情况", "cycle_status": "周期", "cycle_pain": "腹痛/腰酸", "cycle_training_impact": "周期影响", "notes": "备注"})

        with st.expander("🗑️ 删除训练反馈数据", expanded=bool(st.session_state.get("feedback_delete_area_open", False))):
            feedback_options = []
            for idx, item in enumerate(feedback):
                label = f"{item.get('date', '-')}|睡眠{item.get('sleep_quality', '-')}|腿疲劳{item.get('leg_fatigue', '-')}|RPE{item.get('rpe', '-')}|{item.get('completion', '-')}"
                feedback_options.append((idx, label))
            option_labels = [x[1] for x in feedback_options]
            selected_label = st.selectbox("选择要删除的反馈", option_labels, key="feedback_delete_select")
            selected_idx = next((idx for idx, label in feedback_options if label == selected_label), None)
            fc1, fc2 = st.columns([1, 1])
            if fc1.button("删除选中反馈", key="delete_feedback_one", use_container_width=True):
                if selected_idx is not None:
                    deleted_date = feedback[selected_idx].get("date", "-")
                    feedback = [x for i, x in enumerate(feedback) if i != selected_idx]
                    save_feedback(feedback)
                    st.session_state.pop("ai_diagnosis", None)
                    st.session_state.pop("ai_signature", None)
                    st.success(f"已删除 {deleted_date} 的训练反馈。剩余 {len(feedback)} 条。")
                    st.session_state["feedback_delete_area_open"] = bool(feedback)
                    st.rerun()
            st.session_state["feedback_delete_area_open"] = True
            confirm_clear_feedback = fc2.checkbox("确认清空全部", key="confirm_clear_feedback")
            if fc2.button("清空全部训练反馈", key="clear_feedback_all", use_container_width=True, disabled=not confirm_clear_feedback):
                save_feedback([])
                st.session_state.pop("ai_diagnosis", None)
                st.session_state.pop("ai_signature", None)
                st.success("已清空当前骑手全部训练反馈。")
                st.session_state["feedback_delete_area_open"] = False
                st.rerun()
    else:
        st.info("还没有训练反馈。建议每次关键训练后记录一次,尤其是强度课、长距离、感冒/睡眠差/疼痛时。")



def render_rider_profile_page(
    *,
    load_profile,
    load_rider_profile,
    save_rider_profile,
    load_rider_rides,
    load_users,
    add_rider,
    delete_rider,
    PROFILE_FILE,
    plan_info,
    hr_zones_by_max,
    hr_zones_by_lthr,
):
    st.title("👤 骑手档案")

    render_profile_intro()

    profile = load_profile()

    tab0, tab1, tab2 = st.tabs(["骑手管理", "基础档案", "Fitting 设定"])

    with tab0:
        user = st.session_state.get("user", {})
        riders = list(user.get("riders", {}).keys())
        active_rider = st.session_state.get("rider", riders[0] if riders else "默认骑手")
        try:
            history_count = len(load_rider_rides(user.get("user_id"), active_rider)) if user else 0
        except Exception:
            history_count = 0

        render_profile_section_title("当前骑手")
        c0a, c0b, c0c = st.columns(3)
        c0a.metric("当前骑手", active_rider)
        c0b.metric("骑手数量", f"{len(riders)}/{plan_info['riders']}")
        c0c.metric("训练存档", f"{history_count} 条")

        if len(riders) > 1:
            selected_profile_rider = st.selectbox("切换当前骑手", riders, index=riders.index(active_rider) if active_rider in riders else 0, key="profile_rider_select")
            if selected_profile_rider != st.session_state.get("rider"):
                st.session_state.rider = selected_profile_rider
                st.cache_data.clear()
                st.rerun()
        else:
            st.info("当前只有一个骑手档案。Coach 版可管理多个骑手。")

        render_profile_section_title("添加骑手")
        add_col, add_btn_col = st.columns([2, 1], vertical_alignment="bottom")
        new_name = add_col.text_input("新骑手名称", placeholder="例如:客户007 / 张三 / 默认骑手2", key="profile_new_rider_name")
        if add_btn_col.button("添加骑手", key="profile_add_rider_btn", use_container_width=True):
            if new_name.strip():
                ok, msg = add_rider(user["user_id"], new_name.strip())
                if ok:
                    users = load_users()
                    st.session_state.user = {"user_id": user["user_id"], **users[user["user_id"]]}
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.error("请输入骑手名称")

        if len(riders) > 1:
            render_profile_section_title("删除骑手")
            st.caption("只能删除非当前骑手。删除前请确认该骑手的数据不再需要。")
            del_options = [r for r in riders if r != active_rider]
            del_col, del_btn_col = st.columns([2, 1], vertical_alignment="bottom")
            del_name = del_col.selectbox("选择要删除的骑手", ["-- 选择 --"] + del_options, key="profile_del_rider")
            if del_btn_col.button("删除", key="profile_del_rider_btn", use_container_width=True):
                if del_name != "-- 选择 --":
                    ok, msg = delete_rider(user["user_id"], del_name)
                    if ok:
                        users = load_users()
                        st.session_state.user = {"user_id": user["user_id"], **users[user["user_id"]]}
                        st.session_state.rider = users[user["user_id"]].get("active_rider", riders[0])
                        st.success(msg)
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("请选择要删除的骑手")

    with tab1:
        render_profile_section_title("身体数据")
        render_profile_help("用于计算功体比、营养需求和训练负荷解释。")
        c1, c2 = st.columns(2)
        name = c1.text_input("姓名", value=profile.get('name') or '', help="可填客户姓名或编号")
        gender = c2.selectbox("性别", ["男", "女"], index=0 if profile.get('gender', '男') == '男' else 1)
        age = c1.number_input("年龄", 0, 99, value=profile.get('age') if profile.get('age') is not None else 0)
        weight = c2.number_input("体重 kg", 0, 200, value=profile.get('weight') if profile.get('weight') else 0, help="用于计算 W/kg 和营养建议")
        height = c1.number_input("身高 cm", 0, 250, value=profile.get('height') if profile.get('height') else 0)
        exp_years = c2.number_input("骑行年限", 0, 60, value=profile.get('exp_years') or 0)

        cycle_enabled = bool(profile.get('cycle_enabled', False))
        cycle_last_start = profile.get('cycle_last_start') or ''
        cycle_length = int(profile.get('cycle_length') or 28)
        period_days = int(profile.get('period_days') or 5)
        cycle_sensitivity = profile.get('cycle_sensitivity') or '正常'
        if gender == '女':
            render_profile_section_title("女性周期辅助")
            render_profile_help("可选填写。只用于训练恢复和补给建议,不作为医学判断。")
            cycle_enabled = st.toggle("启用女性周期辅助", value=cycle_enabled, key="profile_cycle_enabled")
            if cycle_enabled:
                cc1, cc2 = st.columns(2)
                try:
                    default_cycle_date = datetime.date.fromisoformat(cycle_last_start) if cycle_last_start else datetime.date.today()
                except Exception:
                    default_cycle_date = datetime.date.today()
                cycle_last_start_date = cc1.date_input("最近一次月经开始日期", value=default_cycle_date, key="profile_cycle_last_start")
                cycle_last_start = cycle_last_start_date.isoformat()
                cycle_length = cc2.number_input("平均周期长度 天", 20, 45, value=cycle_length, key="profile_cycle_length")
                period_days = cc1.number_input("平均经期天数", 2, 10, value=period_days, key="profile_period_days")
                cycle_sensitivity = cc2.selectbox("经期训练敏感度", ["保守", "正常", "激进"], index=["保守", "正常", "激进"].index(cycle_sensitivity) if cycle_sensitivity in ["保守", "正常", "激进"] else 1, key="profile_cycle_sensitivity")

        render_profile_section_title("训练数据")
        render_profile_help("FTP 和心率数据会直接影响功率区间、AI 诊断和课表生成。")
        c3, c4 = st.columns(2)
        ftp_test = c3.number_input("实测 FTP W", 0, 600, value=profile.get('ftp_test') if profile.get('ftp_test') else 0, key="ftp_input", help="如果不填,系统会根据 FIT 数据自动估算")
        max_hr = c4.number_input("最大心率", 0, 250, value=profile.get('max_hr') if profile.get('max_hr') else 0)
        rest_hr = c3.number_input("静息心率", 0, 120, value=profile.get('rest_hr') if profile.get('rest_hr') else 0)
        lthr = c4.number_input("乳酸阈值心率 LTHR", 0, 230, value=profile.get('lthr') if profile.get('lthr') else 0, help="可选。若做过阈值测试或知道骑行乳酸阈值心率,填写后可用 LTHR 划分心率区间。")
        hr_zone_method = c3.selectbox("心率区间算法", ["按最大心率", "按乳酸阈值心率 LTHR"], index=1 if profile.get('hr_zone_method') == "按乳酸阈值心率 LTHR" else 0, help="LTHR 通常更适合训练区间;没有 LTHR 时先用最大心率。")
        bike_type = c4.selectbox("主要车种", ["公路车", "山地车", "铁三车", "砾石车", "折叠车", "其他"], index=["公路车", "山地车", "铁三车", "砾石车", "折叠车", "其他"].index(profile.get('bike_type', '公路车')) if profile.get('bike_type', '公路车') in ["公路车", "山地车", "铁三车", "砾石车", "折叠车", "其他"] else 0)

        zone_rows = hr_zones_by_lthr(lthr) if hr_zone_method == "按乳酸阈值心率 LTHR" and lthr else hr_zones_by_max(max_hr)
        if zone_rows:
            render_profile_section_title("心率区间预览")
            st.dataframe(pd.DataFrame(zone_rows), use_container_width=True, hide_index=True)
            st.caption("心率区间用于训练强度解释,不作为医学判断;高温、疲劳、咖啡因、睡眠和补给都会影响心率反应。")
        else:
            st.info("填写最大心率或乳酸阈值心率后,会在这里显示心率区间。")

        render_profile_section_title("目标信息")
        render_profile_help("训练目标越清楚,AI 建议和课表方向越容易对准。")
        goal = st.text_input("训练目标", value=profile.get('goal') or '', placeholder="例如:提升 FTP、备战绕圈赛、减脂、恢复体能")
        notes = st.text_area("备注", value=profile.get('notes') or '', placeholder="可记录伤病、可训练时间、比赛日期、器材情况等")

        save_col, clear_col = st.columns([3, 1])
        if save_col.button("💾 保存骑手档案", type="primary", use_container_width=True):
            basics = dict(name=name, age=age, gender=gender, weight=weight, height=height,
                         exp_years=exp_years, ftp_test=ftp_test, max_hr=max_hr, rest_hr=rest_hr,
                         lthr=lthr, hr_zone_method=hr_zone_method,
                         bike_type=bike_type, goal=goal, notes=notes,
                         cycle_enabled=cycle_enabled if gender == '女' else False,
                         cycle_last_start=cycle_last_start if gender == '女' and cycle_enabled else '',
                         cycle_length=cycle_length, period_days=period_days,
                         cycle_sensitivity=cycle_sensitivity)
            user = st.session_state.get("user")
            rider = st.session_state.get("rider", "默认骑手")
            existing = load_rider_profile(user["user_id"], rider) if user else {}
            existing.update(basics)
            if user:
                save_rider_profile(user["user_id"], rider, existing)
            else:
                with open(PROFILE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(existing, f, ensure_ascii=False, indent=2)
            st.success("✅ 骑手档案已保存")
        if clear_col.button("清空", use_container_width=True, help="仅清空当前骑手的基础档案"):
            user = st.session_state.get("user")
            rider = st.session_state.get("rider", "默认骑手")
            empty = {"name": "", "age": 0, "gender": "男", "weight": 0, "height": 0,
                     "exp_years": 0, "ftp_test": 0, "max_hr": 0, "rest_hr": 0,
                     "lthr": 0, "hr_zone_method": "按最大心率",
                     "bike_type": "公路车", "goal": "", "notes": "", "cycle_enabled": False, "cycle_last_start": "", "cycle_length": 28, "period_days": 5, "cycle_sensitivity": "正常"}
            if user:
                existing = load_rider_profile(user["user_id"], rider)
                for k in empty:
                    existing[k] = empty[k]
                save_rider_profile(user["user_id"], rider, existing)
            st.cache_data.clear()
            st.rerun()
        render_danger_note("清空只影响当前骑手档案,不会删除 FIT 骑行记录。")

    with tab2:
        render_profile_section_title("Fitting 设定记录")
        render_profile_help("用于记录人车设定,后续可辅助判断姿势变化、舒适性和输出表现。这里不是医学诊断,只是长期跟踪档案。")
        c5, c6 = st.columns(2)
        saddle_h = c5.number_input("座垫高度 mm", 0, 900, value=profile.get('saddle_height') if profile.get('saddle_height') else 0)
        reach = c5.number_input("座垫-车把 mm", 0, 700, value=profile.get('reach') if profile.get('reach') else 0)
        drop = c5.number_input("落差 mm", -200, 150, value=profile.get('drop') if profile.get('drop') else 0)
        setback = c5.number_input("座垫后移 mm", -50, 150, value=profile.get('saddle_setback') if profile.get('saddle_setback') else 0)
        crank = c6.number_input("曲柄 mm", 0, 180, value=profile.get('crank_length') if profile.get('crank_length') else 0)
        bar_w = c6.number_input("弯把宽 mm", 0, 480, value=profile.get('handlebar_width') if profile.get('handlebar_width') else 0)
        stem = c6.number_input("把立 mm", 0, 160, value=profile.get('stem_length') if profile.get('stem_length') else 0)
        inseam = c6.number_input("跨高 mm", 0, 1000, value=profile.get('inseam') if profile.get('inseam') else 0)
        shoe = c6.number_input("锁鞋 EU", 0, 50, value=profile.get('shoe_size') if profile.get('shoe_size') else 0)

        save_col2, clear_col2 = st.columns([3, 1])
        if save_col2.button("💾 保存 Fitting 设定", type="primary", use_container_width=True):
            fitdata = dict(saddle_height=saddle_h, reach=reach, drop=drop, saddle_setback=setback,
                          crank_length=crank, handlebar_width=bar_w, stem_length=stem,
                          inseam=inseam, shoe_size=shoe)
            user = st.session_state.get("user")
            rider = st.session_state.get("rider", "默认骑手")
            existing = load_rider_profile(user["user_id"], rider) if user else {}
            existing.update(fitdata)
            if user:
                save_rider_profile(user["user_id"], rider, existing)
            else:
                with open(PROFILE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(existing, f, ensure_ascii=False, indent=2)
            st.success("✅ Fitting 设定已保存")
        if clear_col2.button("清空", use_container_width=True, help="仅清空当前骑手的 Fitting 设定"):
            user = st.session_state.get("user")
            rider = st.session_state.get("rider", "默认骑手")
            empty = {"saddle_height": 0, "reach": 0, "drop": 0, "saddle_setback": 0,
                     "crank_length": 0, "handlebar_width": 0, "stem_length": 0,
                     "inseam": 0, "shoe_size": 0}
            if user:
                existing = load_rider_profile(user["user_id"], rider)
                for k in empty:
                    existing[k] = empty[k]
                save_rider_profile(user["user_id"], rider, existing)
            st.cache_data.clear()
            st.rerun()
        render_danger_note("清空只影响当前骑手的 Fitting 设定,不会删除基础档案和骑行记录。")

