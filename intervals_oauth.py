"""Intervals.icu OAuth integration for TrueCadence.

Flow:
  1. User clicks "连接 Intervals.icu" → redirect to Intervals authorize page.
  2. User authorizes → Intervals redirects to our callback.
  3. Callback exchanges code for tokens, stores them server-side per user.
  4. API calls use stored access token with Bearer auth.

Credentials are NOT hardcoded; read from env with safe fallback.
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import json
import os
import secrets
from pathlib import Path
from urllib.parse import urlencode

import requests

# ─── Env config ───
CLIENT_ID = os.environ.get("TC_INTERVALS_CLIENT_ID", "428")
CLIENT_SECRET = os.environ.get("TC_INTERVALS_CLIENT_SECRET", "")
AUTHORIZE_URL = "https://intervals.icu/oauth/authorize"
TOKEN_URL = "https://intervals.icu/api/oauth/token"
REDIRECT_URI = os.environ.get(
    "TC_INTERVALS_REDIRECT_URI",
    "https://truecadence.cn/auth-bridge/intervals/callback",
)
SCOPE = "ACTIVITY:READ"

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("TRUECADENCE_DATA_DIR", APP_DIR / "data"))
TOKENS_FILE = DATA_DIR / "intervals_oauth_tokens.json"


# ─── Helpers ───

def _load_tokens() -> dict:
    if TOKENS_FILE.exists():
        try:
            with open(TOKENS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def _save_tokens(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = TOKENS_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, TOKENS_FILE)


def _generate_state() -> str:
    return secrets.token_urlsafe(32)


def _hash_state(state: str) -> str:
    return hashlib.sha256(f"intervals-oauth:{state}".encode()).hexdigest()


# ─── Public API ───

def get_authorize_url(user_id: str) -> tuple[str, str]:
    """Build Intervals authorize URL + return raw state for callback verification."""
    state = _generate_state()
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "state": state,
    }
    # Store state → user_id mapping (hashed for storage)
    tokens = _load_tokens()
    tokens.setdefault("_pending_states", {})
    tokens["_pending_states"][_hash_state(state)] = {
        "user_id": user_id,
        "created_at": datetime.datetime.utcnow().isoformat(),
    }
    _save_tokens(tokens)
    return f"{AUTHORIZE_URL}?{urlencode(params)}", state


def exchange_code(code: str, state: str) -> tuple[bool, str, dict | None]:
    """Exchange authorization code for tokens. Returns (ok, message, token_data)."""
    if not CLIENT_SECRET:
        return False, "Intervals OAuth Client Secret 未配置", None

    # Verify state → user_id
    tokens = _load_tokens()
    pending = tokens.get("_pending_states", {})
    state_key = _hash_state(state)
    entry = pending.pop(state_key, None)
    if not entry:
        return False, "OAuth state 无效或已过期", None
    user_id = entry.get("user_id", "")

    # Exchange code for tokens
    try:
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
            timeout=15,
        )
    except Exception as e:
        return False, f"Token 请求失败: {e}", None

    if resp.status_code != 200:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text[:300]
        return False, f"Token 交换失败 ({resp.status_code}): {detail}", None

    payload = resp.json()
    access_token = payload.get("access_token", "")
    refresh_token = payload.get("refresh_token", "")
    expires_in = int(payload.get("expires_in", 0) or 0)

    # Store token per user
    tokens["_pending_states"] = pending
    tokens[user_id] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": (
            (datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)).isoformat()
            if expires_in > 0
            else None
        ),
        "created_at": datetime.datetime.utcnow().isoformat(),
        "scope": SCOPE,
    }
    _save_tokens(tokens)
    return True, "授权成功", {"user_id": user_id, "expires_in": expires_in}


def get_auth_header(user_id: str) -> dict | None:
    """Return Bearer auth header for Intervals API calls, refreshing if needed."""
    token = get_token(user_id)
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"} if token else None


def get_token(user_id: str) -> str | None:
    """Get a valid access token for the user, refreshing if needed."""
    tokens = _load_tokens()
    entry = tokens.get(user_id)
    if not entry:
        return None

    access_token = entry.get("access_token")
    expires_at = entry.get("expires_at")

    # Check expiry with 60s buffer
    if expires_at:
        try:
            expiry = datetime.datetime.fromisoformat(expires_at)
            if datetime.datetime.utcnow() + datetime.timedelta(seconds=60) >= expiry:
                # Try refresh
                refresh_token = entry.get("refresh_token")
                if refresh_token and CLIENT_SECRET:
                    ok, _, new_entry = exchange_refresh(user_id, refresh_token)
                    if ok and new_entry:
                        return new_entry.get("access_token")
                return None
        except Exception:
            pass

    return access_token if access_token else None


def exchange_refresh(user_id: str, refresh_token: str) -> tuple[bool, str, dict | None]:
    """Refresh an expired access token."""
    if not CLIENT_SECRET:
        return False, "Client Secret 未配置", None
    try:
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
            timeout=15,
        )
    except Exception as e:
        return False, f"Refresh 请求失败: {e}", None

    if resp.status_code != 200:
        return False, f"Token 刷新失败 ({resp.status_code})", None

    payload = resp.json()
    access_token = payload.get("access_token", "")
    new_refresh_token = payload.get("refresh_token", refresh_token)
    expires_in = int(payload.get("expires_in", 0) or 0)

    tokens = _load_tokens()
    tokens[user_id] = {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "expires_at": (
            (datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)).isoformat()
            if expires_in > 0
            else None
        ),
        "created_at": datetime.datetime.utcnow().isoformat(),
        "scope": SCOPE,
    }
    _save_tokens(tokens)
    return True, "刷新成功", tokens[user_id]


def disconnect_user(user_id: str) -> bool:
    """Remove stored tokens for a user."""
    tokens = _load_tokens()
    if user_id in tokens:
        del tokens[user_id]
        _save_tokens(tokens)
        return True
    return False


def is_connected(user_id: str) -> bool:
    """Check if user has a valid token."""
    return get_token(user_id) is not None


def get_athlete_id(user_id: str) -> str:
    """Athlete ID for API calls. Use 0 for self."""
    return "0"
