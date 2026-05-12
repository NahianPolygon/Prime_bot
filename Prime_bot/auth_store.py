from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path


AUTH_STORE_PATH = Path(os.getenv("PRIMEBOT_AUTH_STORE_PATH", "kb_users.json"))
AUTH_SECRET = os.getenv("PRIMEBOT_AUTH_SECRET", "primebot-local-auth-secret-change-me")
SUPER_ADMIN_ROLE = "super_admin"
BANK_ADMIN_ROLE = "bank_admin"
TOKEN_TTL_SECONDS = 60 * 60 * 12
PASSWORD_ITERATIONS = 200_000


def _urlsafe_b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _urlsafe_b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def _password_hash(password: str, salt: bytes | None = None) -> str:
    salt_bytes = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        PASSWORD_ITERATIONS,
    )
    return "pbkdf2_sha256${iterations}${salt}${digest}".format(
        iterations=PASSWORD_ITERATIONS,
        salt=_urlsafe_b64encode(salt_bytes),
        digest=_urlsafe_b64encode(digest),
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iterations, salt_b64, digest_b64 = encoded_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = _urlsafe_b64decode(salt_b64)
        expected = _urlsafe_b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
        )
    except Exception:
        return False
    return secrets.compare_digest(actual, expected)


def _default_store() -> dict:
    return {"users": []}


def _read_store() -> dict:
    if not AUTH_STORE_PATH.exists():
        return _default_store()
    try:
        data = json.loads(AUTH_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return _default_store()
    if not isinstance(data, dict):
        return _default_store()
    users = data.get("users")
    if not isinstance(users, list):
        data["users"] = []
    return data


def _write_store(store: dict) -> dict:
    AUTH_STORE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")
    return store


def ensure_default_super_admin(username: str, password: str) -> None:
    store = _read_store()
    for user in store["users"]:
        if user.get("role") == SUPER_ADMIN_ROLE:
            return
    store["users"].append({
        "username": username,
        "password_hash": _password_hash(password),
        "role": SUPER_ADMIN_ROLE,
        "bank_slug": None,
        "active": True,
        "updated_at": int(time.time()),
    })
    _write_store(store)


def _active_users() -> list[dict]:
    return [user for user in _read_store()["users"] if user.get("active", True)]


def authenticate_user(username: str, password: str, role: str) -> dict | None:
    username_norm = (username or "").strip()
    for user in _active_users():
        if user.get("role") != role:
            continue
        if not secrets.compare_digest(str(user.get("username", "")), username_norm):
            continue
        if verify_password(password or "", str(user.get("password_hash", ""))):
            return {
                "username": str(user["username"]),
                "role": str(user["role"]),
                "bank_slug": user.get("bank_slug"),
            }
    return None


def list_bank_admins() -> list[dict]:
    admins = []
    for user in _active_users():
        if user.get("role") != BANK_ADMIN_ROLE:
            continue
        admins.append({
            "bank_slug": str(user.get("bank_slug") or ""),
            "username": str(user.get("username") or ""),
            "active": bool(user.get("active", True)),
            "updated_at": int(user.get("updated_at") or 0),
        })
    return sorted(admins, key=lambda item: (item["bank_slug"], item["username"]))


def upsert_bank_admin(bank_slug: str, username: str, password: str) -> dict:
    bank_slug = (bank_slug or "").strip()
    username = (username or "").strip()
    password = password or ""
    if not bank_slug:
        raise ValueError("Bank name is required.")
    if not username:
        raise ValueError("Username is required.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    store = _read_store()
    existing_for_bank = None
    for user in store["users"]:
        if user.get("role") == BANK_ADMIN_ROLE and user.get("bank_slug") == bank_slug:
            existing_for_bank = user
        if str(user.get("username") or "") == username and user is not existing_for_bank:
            raise ValueError("Username is already in use.")

    target = existing_for_bank
    if target is None:
        target = {
            "role": BANK_ADMIN_ROLE,
            "bank_slug": bank_slug,
            "active": True,
        }
        store["users"].append(target)

    target["username"] = username
    target["password_hash"] = _password_hash(password)
    target["updated_at"] = int(time.time())
    target["active"] = True
    _write_store(store)
    return {
        "bank_slug": bank_slug,
        "username": username,
        "active": True,
        "updated_at": target["updated_at"],
    }


def issue_token(user: dict, ttl_seconds: int = TOKEN_TTL_SECONDS) -> str:
    payload = {
        "sub": str(user.get("username") or ""),
        "role": str(user.get("role") or ""),
        "bank_slug": user.get("bank_slug"),
        "exp": int(time.time()) + int(ttl_seconds),
    }
    payload_b64 = _urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(AUTH_SECRET.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    return f"{payload_b64}.{_urlsafe_b64encode(signature)}"


def read_token(token: str) -> dict | None:
    try:
        payload_b64, signature_b64 = (token or "").split(".", 1)
        expected = hmac.new(AUTH_SECRET.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
        if not secrets.compare_digest(expected, _urlsafe_b64decode(signature_b64)):
            return None
        payload = json.loads(_urlsafe_b64decode(payload_b64).decode("utf-8"))
        if int(payload.get("exp") or 0) < int(time.time()):
            return None
        role = str(payload.get("role") or "")
        if role not in {SUPER_ADMIN_ROLE, BANK_ADMIN_ROLE}:
            return None
        return payload
    except Exception:
        return None
