"""Supabase wrapper:
- service-role операции (register_user, поиск юзеров)
- генерация короткоживущих JWT с claim tg_id для Mini App
"""
import os
import time
from typing import Any

import httpx
import jwt as pyjwt

_url: str | None = None
_service_key: str | None = None
_jwt_secret: str | None = None
_client: httpx.AsyncClient | None = None


def init_supabase(url: str, service_key: str) -> None:
    global _url, _service_key, _jwt_secret, _client
    _url = url.rstrip("/")
    _service_key = service_key
    # JWT_SECRET — для подписи токенов, которые мы выдаём Mini App.
    # В Supabase это тот же ключ что в Settings → API → JWT Keys (Legacy JWT secret).
    jwt_secret = os.environ.get("SUPABASE_JWT_SECRET")
    if not jwt_secret:
        raise RuntimeError(
            "SUPABASE_JWT_SECRET env var is missing. "
            "Get it from Supabase Settings → API → JWT Keys → Legacy JWT secret."
        )
    _jwt_secret = jwt_secret
    _client = httpx.AsyncClient(
        timeout=15.0,
        headers={
            "apikey": _service_key,
            "Authorization": f"Bearer {_service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
    )


async def rpc(name: str, params: dict[str, Any]) -> Any:
    assert _client and _url
    r = await _client.post(f"{_url}/rest/v1/rpc/{name}", json=params)
    r.raise_for_status()
    return r.json()


async def register_user(
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
    photo_url: str | None,
    language_code: str,
    ref_code: str | None,
    target_level_id: int | None = None,
) -> dict[str, Any]:
    return await rpc(
        "register_user",
        {
            "p_telegram_id": telegram_id,
            "p_username": username,
            "p_first_name": first_name,
            "p_last_name": last_name,
            "p_photo_url": photo_url,
            "p_language_code": language_code,
            "p_ref_code": ref_code,
            "p_target_level_id": target_level_id,
        },
    )


async def get_user_by_tg(telegram_id: int) -> dict | None:
    """Достаём юзера + профиль по telegram_id (service-role, в обход RLS)."""
    assert _client and _url
    r = await _client.get(
        f"{_url}/rest/v1/users",
        params={
            "select": "id,telegram_id,username,first_name,ref_code,is_gm,"
                      "profiles(key_balance,total_referrals,current_level_id,highest_level_reached)",
            "telegram_id": f"eq.{telegram_id}",
            "limit": 1,
        },
    )
    r.raise_for_status()
    data = r.json()
    return data[0] if data else None


async def find_user_by_username(username: str) -> dict | None:
    """Для GM-команд: найти юзера по @username."""
    assert _client and _url
    r = await _client.get(
        f"{_url}/rest/v1/users",
        params={"select": "id,telegram_id,username,first_name", "username": f"eq.{username.lstrip('@')}", "limit": 1},
    )
    r.raise_for_status()
    data = r.json()
    return data[0] if data else None


async def gm_grant_via_service(gm_telegram_id: int, target_user_id: str, amount: int, reason: str, comment: str | None = None) -> str:
    """Вызов gm_grant_key от имени GM (через JWT с его tg_id, чтобы RLS отработала)."""
    assert _client and _url
    token = issue_jwt(gm_telegram_id)
    r = await _client.post(
        f"{_url}/rest/v1/rpc/gm_grant_key",
        json={"p_target_user_id": target_user_id, "p_amount": amount, "p_reason": reason, "p_comment": comment},
        headers={"Authorization": f"Bearer {token}", "apikey": _service_key},
    )
    r.raise_for_status()
    return r.text.strip('"')


def issue_jwt(telegram_id: int, ttl_seconds: int = 3600) -> str:
    """Короткоживущий JWT для Mini App — с claim tg_id и role=authenticated."""
    assert _jwt_secret
    now = int(time.time())
    payload = {
        "role": "authenticated",
        "tg_id": str(telegram_id),
        "iat": now,
        "exp": now + ttl_seconds,
    }
    return pyjwt.encode(payload, _jwt_secret, algorithm="HS256")
