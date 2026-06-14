#!/usr/bin/env python3
"""TrueCadence local auth bridge.

A tiny localhost-only HTTP bridge used by the Streamlit app to set and clear
HttpOnly session cookies. Streamlit cannot reliably attach Set-Cookie headers
from the app script itself, and frontend JS cookies are not HttpOnly.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import http.server
import json
import os
from pathlib import Path
from http import HTTPStatus
from urllib.parse import parse_qs, urlparse

from auth import load_users
from services.rider_profile_service import save_rider_profile_from_payload

HOST = "127.0.0.1"
DEFAULT_PORT = int(os.environ.get("TC_AUTH_BRIDGE_PORT", "8503"))
APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("TRUECADENCE_DATA_DIR", APP_DIR / "data"))
SESSION_FILE = DATA_DIR / "login_sessions.json"
SESSION_HANDOFF_FILE = DATA_DIR / "login_session_handoffs.json"
SESSION_COOKIE_NAME = "tc_session"
SESSION_DAYS = 30
MAX_AGE = SESSION_DAYS * 24 * 60 * 60
REDIRECT_TO = os.environ.get("TC_AUTH_BRIDGE_REDIRECT", "https://truecadence.cn/")
LOCAL_APP_URL = os.environ.get("TC_APP_URL", "http://127.0.0.1:8502/")
COOKIE_SECURE = os.environ.get("TC_AUTH_BRIDGE_SECURE_COOKIE", "0").strip().lower() in ("1", "true", "yes", "on")
BASE_PATH = os.environ.get("TC_AUTH_BRIDGE_BASE_PATH", "").strip().rstrip("/")


def _safe_redirect(target: str | None) -> str:
    if not target:
        return REDIRECT_TO
    parsed = urlparse(target)
    redirect_parsed = urlparse(REDIRECT_TO)
    allowed_hosts = {"127.0.0.1", "localhost"}
    if redirect_parsed.hostname:
        allowed_hosts.add(redirect_parsed.hostname)
    if parsed.scheme in ("http", "https") and parsed.hostname in allowed_hosts:
        return target
    if target.startswith("/") and not target.startswith("//"):
        return target
    return REDIRECT_TO


def _route_path(path: str) -> str:
    if BASE_PATH and path.startswith(BASE_PATH + "/"):
        return path[len(BASE_PATH):]
    if BASE_PATH and path == BASE_PATH:
        return "/"
    return path


def _session_cookie(value: str, max_age: int) -> str:
    parts = [
        f"{SESSION_COOKIE_NAME}={value}",
        f"Max-Age={max_age}",
        "Path=/",
        "HttpOnly",
        "SameSite=Lax",
    ]
    if COOKIE_SECURE:
        parts.append("Secure")
    return "; ".join(parts)


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _parse_iso(value: str) -> datetime.datetime | None:
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _hash_token(token: str) -> str:
    return hashlib.sha256(f"{token}:truecadence-session".encode("utf-8")).hexdigest()


def _cors_origin() -> str:
    return os.environ.get("TC_APP_URL", "http://127.0.0.1:8502/").rstrip("/")


def _public_user_from_token(token: str) -> dict | None:
    if not token:
        return None
    sessions = _load_json(SESSION_FILE)
    row = sessions.get(_hash_token(token))
    if not isinstance(row, dict) or row.get("revoked_at"):
        return None
    expires_at = _parse_iso(row.get("expires_at", ""))
    if not expires_at or expires_at <= _utc_now():
        return None
    user_id = row.get("user_id", "")
    users = load_users()
    user_data = users.get(user_id)
    if not isinstance(user_data, dict):
        return None
    return {"user_id": user_id, **user_data}


def _load_json(path: Path) -> dict:
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def _save_json(path: Path, data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _consume_handoff(code: str) -> str:
    if not code:
        return ""
    now = _utc_now()
    handoffs = _load_json(SESSION_HANDOFF_FILE)
    row = handoffs.get(code)
    fresh = {}
    for k, item in handoffs.items():
        if not isinstance(item, dict):
            continue
        expires_at = _parse_iso(item.get("expires_at", ""))
        if expires_at and expires_at > now and not item.get("used_at") and k != code:
            fresh[k] = item
    token = ""
    if isinstance(row, dict) and not row.get("used_at"):
        expires_at = _parse_iso(row.get("expires_at", ""))
        candidate = row.get("token", "")
        sessions = _load_json(SESSION_FILE)
        session_row = sessions.get(_hash_token(candidate)) if candidate else None
        session_expires = _parse_iso(session_row.get("expires_at", "")) if isinstance(session_row, dict) else None
        if expires_at and expires_at > now and isinstance(session_row, dict) and not session_row.get("revoked_at") and session_expires and session_expires > now:
            token = candidate
    _save_json(SESSION_HANDOFF_FILE, fresh)
    return token


class AuthBridgeHandler(http.server.BaseHTTPRequestHandler):
    server_version = "TrueCadenceAuthBridge/1.0"

    def log_message(self, fmt: str, *args) -> None:  # avoid logging query token
        path = urlparse(self.path).path
        self.log_request_line(path, *args)

    def log_request_line(self, path: str, *_args) -> None:
        print(f"{self.address_string()} - {self.command} {path}")

    def _redirect(self, location: str, cookie_header: str | None = None) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", _safe_redirect(location))
        self.send_header("Cache-Control", "no-store")
        if cookie_header:
            self.send_header("Set-Cookie", cookie_header)
        self.end_headers()

    def _html_response(self, html: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json_response(self, data: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", _cors_origin())
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", _cors_origin())
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()

    def _cookie_value(self, name: str) -> str:
        cookie_header = self.headers.get("Cookie", "")
        for part in cookie_header.split(";"):
            if "=" not in part:
                continue
            key, value = part.strip().split("=", 1)
            if key == name:
                return value
        return ""

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        route_path = _route_path(parsed.path)
        if route_path != "/api/rider-profile/save":
            self.send_error(HTTPStatus.NOT_FOUND, "not found")
            return
        user = _public_user_from_token(self._cookie_value(SESSION_COOKIE_NAME))
        if not user:
            self._json_response({"ok": False, "error": "not_authenticated"}, HTTPStatus.UNAUTHORIZED)
            return
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(min(length, 1024 * 64))
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            self._json_response({"ok": False, "error": "invalid_json"}, HTTPStatus.BAD_REQUEST)
            return
        ok, result, status_code = save_rider_profile_from_payload(user, payload)
        if not ok:
            self._json_response({"ok": False, **result}, HTTPStatus(status_code))
            return
        self._json_response({"ok": True, **result})

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        route_path = _route_path(parsed.path)
        params = parse_qs(parsed.query, keep_blank_values=False)
        next_url = params.get("next", [REDIRECT_TO])[0]

        if route_path == "/set-session":
            code = params.get("code", [""])[0]
            token = _consume_handoff(code)
            if not token:
                self.send_error(HTTPStatus.BAD_REQUEST, "invalid or expired session handoff")
                return
            cookie = _session_cookie(token, MAX_AGE)
            self._redirect(next_url, cookie)
            return

        if route_path == "/clear-session":
            cookie = _session_cookie("", 0)
            self._redirect(next_url, cookie)
            return

        if route_path == "/intervals/callback":
            code = params.get("code", [""])[0]
            state_val = params.get("state", [""])[0]
            success_html = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>授权完成</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#0d1117;color:#c9d1d9;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}}</style>
</head><body><div style="text-align:center"><h1>{icon}</h1><p>{message}</p><p style="color:#8b949e;font-size:.85em">即将返回 TrueCadence…</p></div>
<script>setTimeout(function(){{window.location.href='{return_url}'}},1500);</script>
</body></html>"""
            if not code or not state_val:
                html = success_html.format(icon="❌", message="缺少授权参数", return_url=LOCAL_APP_URL)
                self._html_response(html, HTTPStatus.BAD_REQUEST)
                return
            # Inline token exchange using urllib (no external deps)
            try:
                import urllib.request
                import base64 as b64_oauth
                client_id = os.environ.get("TC_INTERVALS_CLIENT_ID", "428")
                client_secret = os.environ.get("TC_INTERVALS_CLIENT_SECRET", "")
                redirect_uri = os.environ.get(
                    "TC_INTERVALS_REDIRECT_URI",
                    "https://truecadence.cn/auth-bridge/intervals/callback",
                )
                token_data = urllib.parse.urlencode({
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": client_id,
                    "client_secret": client_secret,
                }).encode("ascii")
                import urllib.error
                req = urllib.request.Request(
                    "https://intervals.icu/api/oauth/token",
                    data=token_data,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                        "User-Agent": "TrueCadence/1.0",
                    },
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        payload = json.loads(resp.read())
                except urllib.error.HTTPError as he:
                    detail_body = he.read().decode("utf-8", "replace")[:500]
                    print(f"Intervals token exchange HTTPError {he.code}: {detail_body}")
                    html = success_html.format(icon="⚠️", message=f"Token 交换失败 ({he.code}): {detail_body}", return_url=LOCAL_APP_URL)
                    self._html_response(html, HTTPStatus.BAD_REQUEST)
                    return
                    access_token = payload.get("access_token", "")
                    refresh_token = payload.get("refresh_token", "")
                    expires_in = int(payload.get("expires_in", 0) or 0)
                    if not access_token:
                        html = success_html.format(icon="⚠️", message=f"Token 交换失败: {payload}", return_url=LOCAL_APP_URL)
                        self._html_response(html, HTTPStatus.BAD_REQUEST)
                        return
                    # Store token
                    import hashlib, datetime
                    from pathlib import Path
                    tokens_dir = Path(os.environ.get("TRUECADENCE_DATA_DIR", Path(__file__).resolve().parent / "data"))
                    tokens_file = tokens_dir / "intervals_oauth_tokens.json"
                    tokens_dir.mkdir(parents=True, exist_ok=True)
                    tokens = {}
                    if tokens_file.exists():
                        with open(tokens_file, "r") as f:
                            tokens = json.load(f)
                    # Resolve user_id from pending states
                    import hashlib
                    state_hash = hashlib.sha256(f"intervals-oauth:{state_val}".encode()).hexdigest()
                    pending = tokens.get("_pending_states", {})
                    entry = pending.pop(state_hash, {})
                    uid = entry.get("user_id", "unknown")
                    tokens["_pending_states"] = pending
                    tokens[uid] = {
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "scope": "ACTIVITY:READ",
                        "created_at": datetime.datetime.utcnow().isoformat(),
                        "expires_at": (datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)).isoformat() if expires_in > 0 else None,
                    }
                    with open(tokens_file, "w") as f:
                        json.dump(tokens, f, ensure_ascii=False, indent=2)
                    html = success_html.format(icon="✅", message="Intervals.icu 授权成功！", return_url=LOCAL_APP_URL)
                    self._html_response(html)
            except Exception as e:
                import traceback
                print("Intervals OAuth callback error:", repr(e))
                traceback.print_exc()
                html = success_html.format(icon="❌", message=f"服务器错误: {e}", return_url=LOCAL_APP_URL)
                self._html_response(html, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if route_path == "/healthz":
            body = b"ok\n"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "not found")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    server = http.server.ThreadingHTTPServer((args.host, args.port), AuthBridgeHandler)
    print(f"TrueCadence auth bridge listening on http://{args.host}:{args.port}{BASE_PATH or ''} secure_cookie={COOKIE_SECURE}")
    server.serve_forever()


if __name__ == "__main__":
    main()
