"""HTTP-server: /api/auth для Mini App + раздача статики Mini App.
Работает параллельно с aiogram polling в одном процессе."""
import json
import logging
import os
from pathlib import Path
from urllib.parse import parse_qsl

from aiohttp import web

from services.supabase_client import issue_jwt, register_user
from services.webapp_auth import validate_init_data

log = logging.getLogger("oasis.server")

WEB_DIR = Path(__file__).parent / "web"


async def health(_request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "service": "oasis-bot"})


async def debug(_request: web.Request) -> web.Response:
    """Не палит секреты — только сообщает какие переменные присутствуют.
    Используется для быстрой проверки что Railway правильно прокинул env."""
    keys = [
        "BOT_TOKEN", "BOT_USERNAME", "SUPABASE_URL",
        "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_JWT_SECRET", "PUBLIC_URL", "PORT",
    ]
    present = {k: bool(os.environ.get(k)) for k in keys}
    lengths = {k: len(os.environ.get(k, "")) for k in keys if os.environ.get(k)}
    return web.json_response({
        "env_present": present,
        "env_lengths": lengths,
        "public_url": os.environ.get("PUBLIC_URL", "<not set>"),
        "supabase_url": os.environ.get("SUPABASE_URL", "<not set>"),
    })


async def auth(request: web.Request) -> web.Response:
    """
    POST /api/auth
    body: {"initData": "<raw initData from window.Telegram.WebApp.initData>",
           "ref_code": "OPTIONAL_REF_CODE"}
    response: {"jwt": "...", "user_id": "...", "ref_code": "...", "new_user": bool}
    """
    try:
        payload = await request.json()
    except Exception:
        raise web.HTTPBadRequest(text="invalid json")

    init_data = payload.get("initData")
    if not init_data:
        raise web.HTTPBadRequest(text="initData required")

    parsed = validate_init_data(init_data)
    if not parsed:
        log.warning("invalid initData signature from %s", request.remote)
        raise web.HTTPUnauthorized(text="invalid initData signature")

    user_blob = parsed.get("user")
    if not user_blob:
        raise web.HTTPBadRequest(text="user missing in initData")
    try:
        tg_user = json.loads(user_blob)
    except Exception:
        raise web.HTTPBadRequest(text="bad user json in initData")

    tg_id = int(tg_user["id"])
    ref_code = payload.get("ref_code")
    # ref-код может прийти и из start_param (deeplink)
    if not ref_code:
        start_param = parsed.get("start_param") or ""
        if start_param.startswith("ref_"):
            ref_code = start_param[4:]

    reg = await register_user(
        telegram_id=tg_id,
        username=tg_user.get("username"),
        first_name=tg_user.get("first_name"),
        last_name=tg_user.get("last_name"),
        photo_url=tg_user.get("photo_url"),
        language_code=tg_user.get("language_code") or "ru",
        ref_code=ref_code,
    )

    jwt_token = issue_jwt(tg_id)

    return web.json_response({
        "jwt": jwt_token,
        "user_id": reg["user_id"],
        "new_user": not reg.get("already_exists", False),
        "welcome_bonus": reg.get("welcome_bonus") if not reg.get("already_exists") else 0,
        "slot_filled": reg.get("slot_filled", False),
        "supabase_url": os.environ["SUPABASE_URL"],
        "supabase_anon_key": os.environ["SUPABASE_ANON_KEY"],
        "bot_username": os.environ.get("BOT_USERNAME", "RSroom_bot"),
    })


async def index(_request: web.Request) -> web.FileResponse:
    return web.FileResponse(WEB_DIR / "index.html")


async def admin_page(_request: web.Request) -> web.FileResponse:
    return web.FileResponse(WEB_DIR / "admin.html")


async def admin_config(_request: web.Request) -> web.Response:
    """Возвращает supabase_url + anon_key для админки (только публичные данные)."""
    return web.json_response({
        "supabase_url": os.environ["SUPABASE_URL"],
        "supabase_anon_key": os.environ["SUPABASE_ANON_KEY"],
        "bot_username": os.environ.get("BOT_USERNAME", "RSroom_bot"),
    })


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/api/debug", debug)
    app.router.add_get("/api/admin/config", admin_config)
    app.router.add_post("/api/auth", auth)
    app.router.add_get("/", index)
    app.router.add_get("/admin", admin_page)
    app.router.add_static("/assets/", path=WEB_DIR / "assets", show_index=False)
    return app
