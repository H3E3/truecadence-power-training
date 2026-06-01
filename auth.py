"""
TrueCadence Auth Module
User registration, login, subscription management
"""

import json, os, hashlib, datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("TRUECADENCE_DATA_DIR", APP_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
ORDERS_FILE = DATA_DIR / "orders.json"

# Plan definitions
# Tiers: free → core → pro → coach
# Feature gating based on plan level

PLANS = {
    "free": {
        "name": "免费版",
        "riders": 1,
        "level": 0,
        "features": ["上传FIT", "基础功率分析", "基础PMC", "训练概览", "AI点评(限8次/月)"],
        "durations": {"永久": {"days": 9999, "price": 0}},
    },
    "core": {
        "name": "Core版",
        "riders": 1,
        "level": 1,
        "recommended": True,
        "features": ["AI训练分析(30次/月)", "周训练建议", "恢复建议", "睡眠/营养", "目标追踪", "AI生成课表", "自动调整负荷"],
        "durations": {
            "月付": {"days": 31, "price": 19},
            "年付": {"days": 370, "price": 169},
        },
    },
    "pro": {
        "name": "Pro版",
        "riders": 1,
        "level": 2,
        "features": ["周期化训练", "比赛目标", "Taper策略", "AI动态调整", "FTP预测", "历史趋势", "高级训练结构"],
        "durations": {
            "月付": {"days": 31, "price": 49},
            "年付": {"days": 370, "price": 449},
        },
    },
    "coach": {
        "name": "Coach版",
        "riders": 20,
        "level": 3,
        "features": ["20位骑手管理", "教练后台", "骑手分组", "AI辅助教练", "批量生成课表", "骑手恢复监控"],
        "durations": {
            "月付": {"days": 31, "price": 149},
            "年付": {"days": 370, "price": 1349},
        },
    },
}


def load_users() -> dict:
    if USERS_FILE.exists():
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_users(users: dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def hash_pw(phone: str, pw: str) -> str:
    return hashlib.sha256(f"{phone}:{pw}:truecadence".encode()).hexdigest()[:32]


def generate_uid() -> str:
    import uuid
    return uuid.uuid4().hex[:8]


def register_user(phone: str, password: str, invite_code: str = "") -> tuple:
    """Register with invitation code. Returns (success, message).
    Requires invitation code. Password must have uppercase, lowercase, digit/symbol, length > 6."""
    users = load_users()

    for uid, u in users.items():
        if u.get("phone") == phone:
            return False, "该手机号已注册"

    # Validate invitation code (required)
    plan = "free"
    days = 9999
    invite_ok = False
    if not invite_code.strip():
        return False, "需要内测邀请码才能注册"
    ok, plan_from_code, days_from_code, msg = redeem_invite(invite_code.strip().upper())
    if not ok:
        return False, msg
    plan = plan_from_code
    days = days_from_code
    invite_ok = True

    # Validate password complexity
    if len(password) < 6:
        return False, "密码至少6位"
    import re
    if not re.search(r'[A-Z]', password):
        return False, "密码需包含大写字母"
    if not re.search(r'[a-z]', password):
        return False, "密码需包含小写字母"
    if not re.search(r'[0-9!@#$%^&*(),.?":{}|<>_\-+=]', password):
        return False, "密码需包含数字或符号"

    uid = generate_uid()
    now = datetime.date.today().isoformat()
    expire_date = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()

    users[uid] = {
        "phone": phone,
        "password": hash_pw(phone, password),
        "plan": plan,
        "duration": f"{days}天",
        "created": now,
        "expires": expire_date,
        "riders": {
            "默认骑手": {"id": f"r_{uid}_0", "created": now}
        },
        "active_rider": "默认骑手",
    }
    save_users(users)

    # Consume invitation code
    if invite_ok:
        consume_invite(invite_code.strip().upper(), uid)

    return True, uid


def login_user(phone: str, password: str) -> tuple[bool, str, dict | None]:
    """Returns (success, message, user_data_or_None)."""
    users = load_users()
    for uid, u in users.items():
        if u.get("phone") == phone and u.get("password") == hash_pw(phone, password):
            # Check expiration (skip for free plan)
            expires = u.get("expires", "")
            if u.get("plan") != "free" and expires and expires < datetime.date.today().isoformat():
                return False, "会员已过期，请联系续费", None
            return True, "登录成功", {"user_id": uid, **u}
    return False, "手机号或密码错误", None


def add_rider(user_id: str, rider_name: str) -> tuple[bool, str]:
    """Add a new rider to user's account."""
    users = load_users()
    if user_id not in users:
        return False, "用户不存在"

    u = users[user_id]
    max_riders = PLANS[u["plan"]]["riders"]

    if len(u.get("riders", {})) >= max_riders:
        return False, f"当前套餐最多 {max_riders} 位骑手，请升级套餐"

    if rider_name in u.get("riders", {}):
        return False, "骑手名称已存在"

    u.setdefault("riders", {})
    u["riders"][rider_name] = {
        "id": f"r_{user_id}_{abs(hash(rider_name)) % 1000000:06d}",
        "created": datetime.date.today().isoformat(),
    }
    save_users(users)
    return True, "添加成功"


def delete_rider(user_id: str, rider_name: str) -> tuple[bool, str]:
    """Delete a rider and all their data."""
    users = load_users()
    if user_id not in users:
        return False, "用户不存在"
    u = users[user_id]
    riders = u.get("riders", {})
    if rider_name not in riders:
        return False, "骑手不存在"
    if len(riders) <= 1:
        return False, "至少保留一位骑手"

    # Get rider_id to delete data files
    rider_info = riders[rider_name]
    rider_id = rider_info.get("id", "")
    user_dir = get_user_dir(user_id)
    for f_type in ["profile", "rides", "backup"]:
        f_path = user_dir / f"{f_type}_{rider_id}.json"
        if f_path.exists():
            f_path.unlink()

    del riders[rider_name]
    # If deleted the active rider, switch to first remaining
    if u.get("active_rider") == rider_name:
        u["active_rider"] = next(iter(riders.keys()))
    save_users(users)
    return True, f"已删除骑手「{rider_name}」及其全部数据"


def add_subscription_days(user_id: str, days: int, plan: str = "basic"):
    """Admin/payment: add days to a user's subscription."""
    users = load_users()
    if user_id not in users:
        return False
    u = users[user_id]
    # If upgrading to a different plan, reset from today.
    # If renewing same plan, extend from current expiry.
    old_plan = u.get("plan", "")
    if old_plan != plan:
        expire_date = datetime.date.today()
    else:
        current = u.get("expires", datetime.date.today().isoformat())
        expire_date = datetime.date.fromisoformat(current)
        if expire_date < datetime.date.today():
            expire_date = datetime.date.today()
    expire_date += datetime.timedelta(days=days)
    u["expires"] = expire_date.isoformat()
    u["plan"] = plan
    u["duration"] = f"{days}天"
    save_users(users)
    return True


# ─── Orders / Manual Payment MVP ───

def load_orders() -> dict:
    if ORDERS_FILE.exists():
        with open(ORDERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    return {}


def save_orders(orders: dict):
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)


def generate_order_id() -> str:
    import random
    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    return "TC" + now + f"{random.randint(0, 999):03d}"


def create_order(user_id: str, plan: str, duration_label: str, payment_method: str = "manual_wechat") -> tuple[bool, str, dict | None]:
    """Create a pending manual-payment order. Returns (ok, message/order_id, order).

    Price/days are always read from server-side PLANS at creation time. The UI never sends
    trusted amount fields, preventing a stale widget state from buying a higher plan at a lower price.
    """
    users = load_users()
    plan = str(plan or "").strip().lower()
    duration_label = str(duration_label or "").strip()
    if user_id not in users:
        return False, "用户不存在", None
    if plan not in PLANS or plan == "free":
        return False, "无效套餐", None
    duration = PLANS[plan].get("durations", {}).get(duration_label)
    if not duration:
        return False, "无效付费周期", None

    orders = load_orders()
    order_id = generate_order_id()
    while order_id in orders:
        order_id = generate_order_id()

    now = datetime.datetime.now().isoformat(timespec="seconds")
    user = users[user_id]
    order = {
        "order_id": order_id,
        "user_id": user_id,
        "phone": user.get("phone", ""),
        "plan": plan,
        "plan_name": PLANS[plan]["name"],
        "duration_label": duration_label,
        "days": int(duration.get("days", 0)),
        "amount": float(duration.get("price", 0)),
        "currency": "CNY",
        "status": "pending",
        "payment_method": payment_method,
        "created_at": now,
        "paid_at": None,
        "confirmed_by": None,
        "confirmed_at": None,
        "expires_at_after_paid": None,
        "note": "人工收款确认后开通",
    }
    orders[order_id] = order
    save_orders(orders)
    return True, order_id, order


def get_user_orders(user_id: str, include_hidden: bool = False) -> list:
    orders = load_orders()
    rows = [o for o in orders.values() if o.get("user_id") == user_id]
    if not include_hidden:
        rows = [o for o in rows if not o.get("hidden_by_user")]
    rows.sort(key=lambda o: o.get("created_at", ""), reverse=True)
    return rows


def update_order_status(order_id: str, status: str, admin_id: str = "", note: str = "") -> tuple[bool, str]:
    orders = load_orders()
    if order_id not in orders:
        return False, "订单不存在"
    if status not in ("pending", "paid", "cancelled", "refunded", "expired"):
        return False, "无效订单状态"
    order = orders[order_id]
    order["status"] = status
    order["updated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    if note:
        order["admin_note"] = note
    if admin_id:
        order["updated_by"] = admin_id
    save_orders(orders)
    return True, "订单状态已更新"


def hide_order_for_user(order_id: str, user_id: str) -> tuple[bool, str]:
    """User-side delete: hide the order from user's order list while keeping admin audit record."""
    orders = load_orders()
    if order_id not in orders:
        return False, "订单不存在"
    order = orders[order_id]
    if order.get("user_id") != user_id:
        return False, "无权操作该订单"
    now = datetime.datetime.now().isoformat(timespec="seconds")
    if order.get("status") == "pending":
        order["status"] = "cancelled"
        order["cancelled_at"] = now
        order["cancelled_by"] = user_id
    order["hidden_by_user"] = True
    order["hidden_by_user_at"] = now
    save_orders(orders)
    return True, "订单已从你的订单列表移除"


def confirm_order_paid(order_id: str, admin_id: str = "") -> tuple[bool, str]:
    """Mark order paid and grant subscription days. Idempotent for already-paid orders."""
    orders = load_orders()
    if order_id not in orders:
        return False, "订单不存在"
    order = orders[order_id]
    if order.get("status") == "paid":
        return True, "订单已是已支付状态"
    if order.get("status") not in ("pending", "expired"):
        return False, f"当前状态不能确认付款：{order.get('status')}"

    ok = add_subscription_days(order.get("user_id", ""), int(order.get("days", 0)), order.get("plan", ""))
    if not ok:
        return False, "用户不存在，无法开通套餐"

    users = load_users()
    user = users.get(order.get("user_id", ""), {})
    now = datetime.datetime.now().isoformat(timespec="seconds")
    order["status"] = "paid"
    order["paid_at"] = now
    order["confirmed_at"] = now
    order["confirmed_by"] = admin_id
    order["expires_at_after_paid"] = user.get("expires")
    save_orders(orders)
    return True, f"已确认收款并开通 {order.get('plan_name')}，有效期至 {user.get('expires', '-')}"


# ─── Invitation Codes ───

INVITE_FILE = DATA_DIR / "invitation_codes.json"


def gen_invite_code(plan: str = "basic", days: int = 31, note: str = "") -> str:
    """Generate an invitation code. Used at registration to set plan."""
    import random, string
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    codes = {}
    if INVITE_FILE.exists():
        with open(INVITE_FILE, "r", encoding="utf-8") as f:
            codes = json.load(f)
    codes[code] = {
        "plan": plan,
        "days": days,
        "used_by": None,
        "used_at": None,
        "created": datetime.date.today().isoformat(),
        "note": note
    }
    with open(INVITE_FILE, "w", encoding="utf-8") as f:
        json.dump(codes, f, ensure_ascii=False, indent=2)
    return code


def redeem_invite(code: str) -> tuple:
    """Validate invitation code. Returns (ok, plan, days, msg)."""
    if not INVITE_FILE.exists():
        return False, None, 0, "无效内测邀请码"
    with open(INVITE_FILE, "r", encoding="utf-8") as f:
        codes = json.load(f)
    if code not in codes:
        return False, None, 0, "无效内测邀请码"
    c = codes[code]
    if c.get("used_by"):
        return False, None, 0, "该内测邀请码已被使用"
    return True, c["plan"], c["days"], ""


def consume_invite(code: str, user_id: str):
    """Mark invitation code as used."""
    if not INVITE_FILE.exists():
        return
    with open(INVITE_FILE, "r", encoding="utf-8") as f:
        codes = json.load(f)
    if code in codes and not codes[code].get("used_by"):
        codes[code]["used_by"] = user_id
        codes[code]["used_at"] = datetime.date.today().isoformat()
        with open(INVITE_FILE, "w", encoding="utf-8") as f:
            json.dump(codes, f, ensure_ascii=False, indent=2)


# ─── Activation Codes ───

ACTIVATION_FILE = DATA_DIR / "activation_codes.json"


def gen_activation_code(plan: str = "basic", days: int = 30, note: str = "") -> str:
    """Generate a one-time activation code."""
    import random, string
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    codes = {}
    if ACTIVATION_FILE.exists():
        with open(ACTIVATION_FILE, "r", encoding="utf-8") as f:
            codes = json.load(f)
    codes[code] = {
        "plan": plan,
        "days": days,
        "used_by": None,
        "used_at": None,
        "created": datetime.date.today().isoformat(),
        "note": note
    }
    with open(ACTIVATION_FILE, "w", encoding="utf-8") as f:
        json.dump(codes, f, ensure_ascii=False, indent=2)
    return code


def redeem_code(user_id: str, code: str) -> tuple:
    """Redeem a one-time inner beta invite code for an existing account.

    During beta we expose one user-facing concept: 内测邀请码. For backward
    compatibility this accepts legacy activation_codes first, then falls back
    to invitation_codes so the same type of code can be used for registration
    or existing-account upgrade/extension.
    """
    code = (code or "").strip().upper()
    if not code:
        return False, "请输入内测邀请码"

    # 1) Legacy activation codes, kept for admin/backward compatibility.
    if ACTIVATION_FILE.exists():
        with open(ACTIVATION_FILE, "r", encoding="utf-8") as f:
            codes = json.load(f)
        if code in codes:
            c = codes[code]
            if c.get("used_by"):
                return False, "该内测邀请码已被使用"
            ok = add_subscription_days(user_id, c["days"], c["plan"])
            if not ok:
                return False, "用户不存在"
            c["used_by"] = user_id
            c["used_at"] = datetime.date.today().isoformat()
            with open(ACTIVATION_FILE, "w", encoding="utf-8") as f:
                json.dump(codes, f, ensure_ascii=False, indent=2)
            return True, f"开通成功！{PLANS[c['plan']]['name']}，有效期 {c['days']} 天"

    # 2) Unified beta invite codes.
    if INVITE_FILE.exists():
        with open(INVITE_FILE, "r", encoding="utf-8") as f:
            invites = json.load(f)
        if code in invites:
            c = invites[code]
            if c.get("used_by"):
                return False, "该内测邀请码已被使用"
            ok = add_subscription_days(user_id, c["days"], c["plan"])
            if not ok:
                return False, "用户不存在"
            c["used_by"] = user_id
            c["used_at"] = datetime.date.today().isoformat()
            with open(INVITE_FILE, "w", encoding="utf-8") as f:
                json.dump(invites, f, ensure_ascii=False, indent=2)
            return True, f"开通成功！{PLANS[c['plan']]['name']}，有效期 {c['days']} 天"

    return False, "无效内测邀请码"


# ─── AI Usage Tracking ───

def get_ai_usage(user_id: str) -> int:
    """Get AI usage count for current month."""
    users = load_users()
    u = users.get(user_id, {})
    ai = u.get("ai_usage", {})
    month_key = datetime.date.today().strftime("%Y-%m")
    return ai.get(month_key, 0)


def is_ai_unlimited(user_id: str) -> bool:
    """Return whether the user's plan has unlimited AI analysis."""
    users = load_users()
    u = users.get(user_id, {})
    return u.get("plan", "free") in ("pro", "coach")


def increment_ai_usage(user_id: str) -> int:
    """Increment AI usage for current month. Pro/Coach are unlimited and do not consume quota."""
    users = load_users()
    if user_id not in users:
        return 0
    if users[user_id].get("plan", "free") in ("pro", "coach"):
        return get_ai_usage(user_id)
    ai = users[user_id].get("ai_usage", {})
    month_key = datetime.date.today().strftime("%Y-%m")
    ai[month_key] = ai.get(month_key, 0) + 1
    users[user_id]["ai_usage"] = ai
    save_users(users)
    return ai[month_key]


def get_ai_limit(user_id: str):
    """Get AI usage limit based on plan. Pro/Coach are unlimited."""
    users = load_users()
    u = users.get(user_id, {})
    plan = u.get("plan", "free")
    if plan == "free":
        return 8
    elif plan == "core":
        return 30
    else:
        return None  # pro/coach: unlimited


def get_user_dir(user_id: str) -> Path:
    """Get data directory for a user."""
    d = DATA_DIR / user_id
    d.mkdir(exist_ok=True)
    return d


def get_rider_data_path(user_id: str, rider_name: str, file_type: str) -> Path:
    """Get path for rider-specific data file.
    file_type: 'profile' or 'rides' or 'backup'
    """
    users = load_users()
    user_data = users.get(user_id, {})
    riders = user_data.get("riders") if isinstance(user_data, dict) else {}
    if not isinstance(riders, dict):
        riders = {}
    rider = riders.get(rider_name, {})
    rider_id = rider.get("id", f"r_{user_id}_{abs(hash(rider_name)) % 1000000:06d}")
    return get_user_dir(user_id) / f"{file_type}_{rider_id}.json"


def load_rider_rides(user_id: str, rider_name: str) -> list:
    """Load FIT rides for a specific rider."""
    p = get_rider_data_path(user_id, rider_name, "rides")
    if p.exists():
        with open(p, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    # Fall back to local legacy file when present
    legacy = APP_DIR / "self_data.json"
    if legacy.exists():
        with open(legacy, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return []


def load_rider_profile(user_id: str, rider_name: str) -> dict:
    """Load profile for a specific rider."""
    p = get_rider_data_path(user_id, rider_name, "profile")
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    # Fall back to local legacy file when present
    legacy = APP_DIR / "profile.json"
    if legacy.exists():
        with open(legacy, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_rider_data(user_id: str, rider_name: str, file_type: str, data):
    """Save data for a specific rider. file_type: 'profile' or 'rides' or 'backup'."""
    p = get_rider_data_path(user_id, rider_name, file_type)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_rider_profile(user_id: str, rider_name: str, profile: dict):
    """Save rider profile."""
    save_rider_data(user_id, rider_name, "profile", profile)
