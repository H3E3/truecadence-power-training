from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from services.plan_preferences import DAY_ORDER, load_current_plan_prefs, normalize_plan_prefs

CN_TZ = ZoneInfo("Asia/Shanghai")
WEEKDAY_CN = DAY_ORDER


@dataclass(frozen=True)
class FuelingAdvice:
    headline: str
    before: str
    during: str
    hydration: str
    caffeine: str
    after: str


@dataclass(frozen=True)
class WeekSession:
    index: int
    date: date
    title: str
    kind: str
    badge: str
    power: str
    feel: str
    purpose: str
    downgrade: str
    detail: str
    is_rest: bool = False

    @property
    def weekday_label(self) -> str:
        return WEEKDAY_CN[self.date.weekday()]

    def date_label(self, today: date | None = None) -> str:
        today = today or local_today()
        prefix = "今天" if self.date == today else self.weekday_label
        return f"{self.date.month}月{self.date.day}日 {prefix}"

    def status(self, today: date | None = None) -> str:
        today = today or local_today()
        if self.date == today:
            return "rest_today" if self.is_rest else "today"
        if self.date < today:
            return "rest_past" if self.is_rest else "past"
        return "rest_future" if self.is_rest else "future"

    def status_label(self, today: date | None = None) -> str:
        status = self.status(today)
        if status == "today":
            return "今日建议执行"
        if status == "rest_today":
            return "今日休息"
        if status == "past":
            return "已过"
        if status == "rest_past":
            return "休息已过"
        if status == "rest_future":
            return "休息日"
        return "待确认"


def local_today(now: datetime | None = None) -> date:
    """Return the product-local date used by TrueCadence pages.

    Local development and current China-facing production should roll by
    Asia/Shanghai calendar days, not by hard-coded demo dates.
    """
    if now is None:
        return datetime.now(CN_TZ).date()
    if now.tzinfo is None:
        return now.date()
    return now.astimezone(CN_TZ).date()


def week_start_for(day: date) -> date:
    return day - timedelta(days=day.weekday())


def fmt_day_label(day: date) -> str:
    return f"{day.month}月{day.day}日 {WEEKDAY_CN[day.weekday()]}"


def fmt_week_range(start: date) -> str:
    end = start + timedelta(days=6)
    if start.month == end.month:
        return f"{start.month}月{start.day}日–{end.day}日"
    return f"{start.month}月{start.day}日–{end.month}月{end.day}日"


def _session_for_training_day(index: int, day: date, weekday: str, prefs: dict) -> WeekSession:
    preferred_long_day = prefs.get("preferred_long_day")
    no_hard_days = set(prefs.get("no_hard_days") or [])
    training_days = list(prefs.get("training_days") or [])
    goal = str(prefs.get("goal") or "提升 FTP / 阈值能力")

    hard_candidates = [d for d in training_days if d != preferred_long_day and d not in no_hard_days]
    quality_day = hard_candidates[0] if hard_candidates else None

    if weekday == preferred_long_day:
        long_title = "长距离 Z2 2.5 小时" if "长距离" in goal or "比赛" in goal else "长距离 Z2 2 小时"
        long_purpose = "建立长距离耐力和补给耐受" if "长距离" in goal else "积累耐力与疲劳抗性"
        return WeekSession(
            index=index,
            date=day,
            title=long_title,
            kind="耐力",
            badge="purple",
            power="Z2 中下段，别追均速",
            feel="稳定骑行，能说完整句子，不喘到说不出话；后半程不明显崩",
            purpose=long_purpose,
            downgrade="疲劳明显就缩短，不临时拉成超长距离",
            detail=f"目标：{goal}。提前补给，按 Z2 稳定完成，不临时硬加时长。",
        )
    if weekday == quality_day:
        if "减脂" in goal:
            return WeekSession(index=index, date=day, title="Tempo / Z2 燃脂 75–90 分钟", kind="有氧", badge="cyan", power="Z2 上沿到 Tempo 下沿，不进阈值", feel="出汗但可控，不追爆发", purpose="提高消耗和有氧效率，避免高强度拉高恢复成本", downgrade="腿沉 → 改 Z2 45–60 分钟", detail=f"目标：{goal}。以可持续消耗为主，不做阈值硬顶。")
        if "比赛" in goal:
            return WeekSession(index=index, date=day, title="比赛模拟 4×8 分钟", kind="质量课", badge="rose", power="阈值下沿到阈值，组间充分恢复", feel="接近比赛节奏，但不做 FTP 测试", purpose="建立比赛节奏和持续输出能力", downgrade="睡眠差 / 腿沉 → 改甜区 2×12 或 Z2", detail=f"目标：{goal}。保留比赛专项刺激，但不把训练骑成测试。")
        if "恢复" in goal:
            return WeekSession(index=index, date=day, title="Z2 恢复有氧 60 分钟", kind="低强度", badge="green", power="Z2 下到中段", feel="轻松顺畅，结束后更清醒", purpose="恢复体能和训练节奏，不堆高强度疲劳", downgrade="腿沉 → 30–45 分钟恢复骑或休息", detail=f"目标：{goal}。先重建连续性，再考虑强度。")
        if "长距离" in goal:
            return WeekSession(index=index, date=day, title="Z2 耐力 90 分钟", kind="耐力", badge="purple", power="Z2 中段，稳定踩踏", feel="可持续、不喘爆", purpose="补长距离所需的有氧底座", downgrade="腿沉 → 60 分钟 Z2 下沿", detail=f"目标：{goal}。优先堆可恢复的耐力时间。")
        return WeekSession(
            index=index,
            date=day,
            title="轻甜区 3×12 分钟",
            kind="质量课",
            badge="rose",
            power="甜区下沿，不做阈值硬顶",
            feel="组间轻松骑，能稳定完成比顶满更重要",
            purpose="给阈值基础一点刺激，但不硬顶",
            downgrade="睡眠差 / 腿沉 → 改 Z2 60 分钟",
            detail=f"目标：{goal}。给阈值基础一点刺激，但不做硬顶。睡眠差或腿沉时，直接降级成 Z2。",
        )
    if weekday in no_hard_days:
        return WeekSession(
            index=index,
            date=day,
            title="Z2 / 技术骑 45–75 分钟",
            kind="低强度",
            badge="green",
            power="Z2 下到中段，不做阈值",
            feel="轻松、顺畅、可控",
            purpose="保留训练频率，不堆高强度疲劳",
            downgrade="腿沉或睡眠差 → 30–45 分钟恢复骑或休息",
            detail="这是你设置的不安排高强度日：保留 Z2、技术骑或恢复，不放阈值 / VO2 / 冲刺。",
        )
    return WeekSession(
        index=index,
        date=day,
        title="Z2 有氧 75–90 分钟",
        kind="有氧",
        badge="cyan",
        power="158–184W",
        feel="RPE 3–4，能完整说话",
        purpose="恢复节奏，积累稳定有氧时间",
        downgrade="20 分钟后仍腿沉 → 45–60 分钟恢复骑",
        detail="目的：建立稳定有氧时间。体感能完整说话，不追均速，不顶上限。",
    )


def _rest_session(index: int, day: date) -> WeekSession:
    return WeekSession(
        index=index,
        date=day,
        title="休息日",
        kind="休息",
        badge="slate",
        power="不安排结构化训练",
        feel="恢复、睡眠、补给优先",
        purpose="给身体吸收训练刺激，避免连续堆疲劳",
        downgrade="如果很想动，只做 20–30 分钟轻松转腿或散步",
        detail="你在训练计划里没有选择这一天，所以系统把它固定为休息日；不要补做强度。",
        is_rest=True,
    )


def fueling_advice_for_session(session: WeekSession) -> FuelingAdvice:
    """Return practical fueling guidance matched to today's workout type.

    This is intentionally simple and conservative: it gives a rider-facing
    execution range without pretending to be a medical/nutrition prescription.
    """
    if session.is_rest:
        return FuelingAdvice(
            headline="休息日 · 正常吃饭，不用训练补给",
            before="不用特意吃胶。正常三餐，别长期低碳；如果只是散步/轻松转腿，空腹不舒服就先吃 20–30g 碳水。",
            during="不安排骑中补给；如果做 20–30 分钟轻松活动，喝水即可。",
            hydration="日常补水为主；出汗多或天气热，再补一点电解质。",
            caffeine="不需要为了休息日额外加咖啡因。",
            after="正常一餐：主食 + 蛋白质 + 蔬果，目标是把恢复补回来，而不是用能量胶代替正餐。",
        )
    if "长距离" in session.title or session.kind == "耐力":
        return FuelingAdvice(
            headline="长距离 Z2 · 60–90g/h 碳水",
            before="骑前 1–3 小时吃正常主食；出门前仍饿，可补 20–30g 碳水。",
            during="2 小时左右按 60–90g/h 碳水准备：普通 25g 胶约 2–3 包/小时，或运动饮料 + 胶 + 能量棒组合。",
            hydration="水 500–750ml/h；热天或出汗大提高到 750ml/h 左右，钠约 300–600mg/h。",
            caffeine="可选，不是必须；如果用咖啡因，放在后半程或关键路段前，不要用来硬压疲劳。",
            after="骑后 30–60 分钟补主食 + 20–30g 蛋白；长距离后晚餐继续补碳水。",
        )
    if session.kind == "质量课" or "甜区" in session.title:
        return FuelingAdvice(
            headline="甜区 / 质量课 · 45–60g/h 碳水",
            before="训练前 30–60 分钟补 30–50g 碳水，避免低碳上强度。",
            during="60–90 分钟训练按 45–60g/h 碳水：普通 25g 胶 1–2 包，或运动饮料 + 胶。",
            hydration="水 400–700ml/h；室内骑或出汗多时加电解质，钠约 300–600mg/h。",
            caffeine="状态正常时可选；睡眠差、腿沉时不要靠咖啡因硬顶，直接降级更稳。",
            after="骑后补 1–1.2g/kg 碳水 + 20–30g 蛋白，帮助接住质量课刺激。",
        )
    if session.kind == "低强度" or "Z2" in session.title:
        return FuelingAdvice(
            headline="Z2 / 低强度 · 30–45g/h 碳水",
            before="上一餐超过 3 小时或空腹不舒服，骑前补 20–30g 碳水；刚吃过正餐则不用额外加胶。",
            during="45–60 分钟通常水即可；60–75 分钟按 30–45g/h 碳水，普通 25g 胶约 1 包，也可用香蕉/运动饮料替代。",
            hydration="水 400–600ml/h；热天或出汗多加电解质。",
            caffeine="通常不需要咖啡因。低强度日的目标是恢复节奏，不是兴奋起来硬骑。",
            after="正常吃饭即可；如果当天总训练量超过 75 分钟，骑后补主食 + 20–30g 蛋白。",
        )
    return FuelingAdvice(
        headline="有氧训练 · 30–60g/h 碳水",
        before="骑前不要明显空腹；上一餐超过 3 小时，先补 20–30g 碳水。",
        during="60–90 分钟按 30–60g/h 碳水；强度越高越靠近 60g/h。",
        hydration="水 400–700ml/h；热天或出汗多加电解质。",
        caffeine="可选但不必要；疲劳明显时优先降级，不靠咖啡因硬顶。",
        after="骑后正常补主食和 20–30g 蛋白。",
    )


def _readiness_value(readiness: dict | object | None, key: str, default=None):
    if readiness is None:
        return default
    if isinstance(readiness, dict):
        return readiness.get(key, default)
    return getattr(readiness, key, default)


def _apply_readiness_gate(session: WeekSession, readiness: dict | object | None) -> WeekSession:
    cap = str(_readiness_value(readiness, "intensity_cap", "normal") or "normal")
    level = str(_readiness_value(readiness, "level", "") or "")
    if session.is_rest or cap == "normal":
        return session

    if cap == "recovery":
        return replace(
            session,
            title="恢复骑 30–45 分钟 / 休息",
            kind="低强度",
            badge="green",
            power="Z1–Z2 下沿，能轻松说话",
            feel="越骑越松，不追均速、不追功率",
            purpose=f"状态门控：{level or '恢复优先'}。先恢复，再谈训练刺激。",
            downgrade="如果热身后仍腿沉、疼痛或身体不适，直接休息",
            detail="今日状态不适合承接结构化训练：取消阈值、甜区、VO2、冲刺和长距离加码，只保留恢复骑或休息。",
        )

    if cap == "caution":
        if session.kind == "质量课" or "甜区" in session.title or "比赛模拟" in session.title:
            return replace(
                session,
                title="Z2 有氧 45–60 分钟",
                kind="低强度",
                badge="green",
                power="Z2 下到中段，不进甜区/阈值",
                feel="轻松、顺畅、可控，结束后不更累",
                purpose=f"状态门控：{level or '谨慎推进'}。保留训练频率，暂时不做质量课。",
                downgrade="腿沉或睡眠差 → 30–45 分钟恢复骑或休息",
                detail="本周状态允许训练，但不建议加码；原质量课降为 Z2，等反馈恢复后再保留强度刺激。",
            )
        if session.kind == "耐力" or "长距离" in session.title:
            return replace(
                session,
                title="Z2 耐力 75–90 分钟",
                badge="purple",
                power="Z2 中下段，别追均速",
                feel="稳定、有余量，后半程不硬顶",
                purpose=f"状态门控：{level or '谨慎推进'}。长距离保留有氧目的，但缩短时长。",
                downgrade="腿沉 → 45–60 分钟 Z2 或恢复骑",
                detail="本周状态谨慎推进：长距离不取消，但从超长耐力改成可恢复的 Z2 训练。",
            )
    return session


def build_week_sessions(today: date | None = None, prefs: dict | None = None, readiness: dict | object | None = None) -> list[WeekSession]:
    today = today or local_today()
    prefs = normalize_plan_prefs(prefs if prefs is not None else load_current_plan_prefs())
    start = week_start_for(today)
    sessions: list[WeekSession] = []
    workout_index = 1
    for i, weekday in enumerate(WEEKDAY_CN):
        day = start + timedelta(days=i)
        if weekday in prefs["training_days"]:
            session = _session_for_training_day(workout_index, day, weekday, prefs)
            sessions.append(_apply_readiness_gate(session, readiness))
            workout_index += 1
        else:
            sessions.append(_rest_session(i + 1, day))
    return sessions


def today_training_context(today: date | None = None, prefs: dict | None = None, readiness: dict | object | None = None) -> dict:
    today = today or local_today()
    prefs = normalize_plan_prefs(prefs if prefs is not None else load_current_plan_prefs())
    sessions = build_week_sessions(today, prefs, readiness)
    todays = [s for s in sessions if s.date == today]
    training_sessions = [s for s in sessions if not s.is_rest]
    upcoming = [s for s in training_sessions if s.date > today]
    past = [s for s in training_sessions if s.date < today]

    if todays:
        session = todays[0]
        if session.is_rest:
            next_training = upcoming[0] if upcoming else None
            next_text = f"下一堂训练是 {next_training.date_label(today)}：{next_training.title}。" if next_training else "本周训练已结束，准备进入下周滚动计划。"
            return {
                "mode": "rest",
                "session": session,
                "hero_title": "休息日",
                "hero_label": "今天不安排训练",
                "hero_text": f"今天是 {session.date_label(today)}，你在训练计划里没有选择这一天训练。{next_text}今天不要补强度。",
                "why_title": "休息日也是计划的一部分",
                "why_text": "未选择训练的日期就是休息/恢复日，用来吸收前面训练刺激，而不是临时补课。",
                "impact_title": "休息到位，下一堂更稳",
                "impact_text": next_text,
                "avoid_title": "不补做强度",
                "avoid_text": "不要把休息日改成阈值、VO2、FTP 测试或超长骑；最多轻松活动。",
            }
        return {
            "mode": "workout",
            "session": session,
            "hero_title": session.title,
            "hero_label": "今日该怎么骑",
            "hero_text": f"目标功率 {session.power}，{session.feel}。不追均速，先把完成质量做稳。",
            "why_title": "今天收益最高的是按计划骑稳",
            "why_text": "今日建议直接来自本周课表的当天训练。恢复反馈正常时执行原计划；腿沉或睡眠差时按降级规则处理。",
            "impact_title": "今天完成质量决定后续安排",
            "impact_text": "如果今天按目标完成，本周后续训练保留；如果今天硬顶或明显疲劳，下一堂质量课优先降级。",
            "avoid_title": "不临时加码",
            "avoid_text": "不要把计划课临时骑成 FTP 测试、冲刺课或灰区堆量。",
        }

    if upcoming:
        next_session = upcoming[0]
        return {
            "mode": "support",
            "session": next_session,
            "hero_title": "恢复 / 激活 30–45 分钟",
            "hero_label": "今天不是主课日",
            "hero_text": f"本周下一堂主课是 {next_session.date_label(today)}：{next_session.title}。今天更适合恢复、轻松转腿或完全休息。",
            "why_title": "今天的价值是给下一堂课留状态",
            "why_text": "非主课日不要硬塞强度。睡眠、腿感和心率稳定，比临时多练一小时更重要。",
            "impact_title": "今天收住，下一堂才有质量",
            "impact_text": f"如果今天恢复做好，{next_session.weekday_label} 的 {next_session.title} 更容易高质量完成。",
            "avoid_title": "不补做错过的强度",
            "avoid_text": "不要把休息日临时改成阈值、VO2 或 FTP 测试；缺课优先顺延或降级，不硬补。",
        }

    last_session = past[-1] if past else training_sessions[-1]
    return {
        "mode": "wrap",
        "session": last_session,
        "hero_title": "恢复 / 复盘 30–45 分钟",
        "hero_label": "本周收尾日",
        "hero_text": "本周计划课已到尾声。今天更适合恢复、轻松转腿、记录反馈，为下周滚动计划做准备。",
        "why_title": "今天收益最高的是恢复和复盘",
        "why_text": "周末收尾不要临时补强度。记录本周完成情况、睡眠和腿感，下一周计划会更准确。",
        "impact_title": "复盘越清楚，下周越好排",
        "impact_text": "如果本周质量课完成吃力，下周先稳有氧；如果恢复良好，再保留轻甜区刺激。",
        "avoid_title": "不在收尾日硬补课",
        "avoid_text": "不要因为本周少骑就把今天堆成高强度长骑，避免影响下周第一堂课。",
    }


def week_plan_context(today: date | None = None, prefs: dict | None = None, readiness: dict | object | None = None) -> dict:
    today = today or local_today()
    prefs = normalize_plan_prefs(prefs if prefs is not None else load_current_plan_prefs())
    start = week_start_for(today)
    sessions = build_week_sessions(today, prefs, readiness)
    training_sessions = [s for s in sessions if not s.is_rest]
    rest_days = [s.weekday_label for s in sessions if s.is_rest]
    return {
        "today": today,
        "today_label": fmt_day_label(today),
        "week_start": start,
        "week_end": start + timedelta(days=6),
        "week_range": fmt_week_range(start),
        "sessions": sessions,
        "training_sessions": training_sessions,
        "training_days": list(prefs["training_days"]),
        "rest_days": rest_days,
        "preferred_long_day": prefs.get("preferred_long_day"),
        "no_hard_days": list(prefs.get("no_hard_days") or []),
        "goal": prefs.get("goal") or "提升 FTP / 阈值能力",
        "event_type": prefs.get("event_type") or "无比赛",
        "event_date": prefs.get("event_date") or "",
        "event_priority": prefs.get("event_priority") or "B",
        "today_context": today_training_context(today, prefs, readiness),
        "readiness_cap": _readiness_value(readiness, "intensity_cap", "normal"),
        "readiness_level": _readiness_value(readiness, "level", ""),
    }
