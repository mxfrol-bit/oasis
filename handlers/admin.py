"""/admin — выдать GM ссылку на десктоп-админку с JWT в URL."""
import logging
import os

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from services.supabase_client import get_user_by_tg, issue_jwt

router = Router(name="admin")
log = logging.getLogger("oasis.admin")


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not message.from_user:
        return
    u = await get_user_by_tg(message.from_user.id)
    if not u or not u.get("is_gm"):
        return  # silent — не палим админ-фичу обычным юзерам

    public_url = os.environ.get("PUBLIC_URL", "https://example.com").rstrip("/")
    # JWT на 7 дней — десктоп-сессия должна жить дольше чем Mini App
    token = issue_jwt(message.from_user.id, ttl_seconds=7 * 24 * 3600)
    admin_url = f"{public_url}/admin#token={token}"

    await message.answer(
        f"🛠 <b>Админ-панель OASIS</b>\n\n"
        f"Открой эту ссылку на ПК (живёт 7 дней):\n"
        f"<code>{admin_url}</code>\n\n"
        f"⚠️ Не пересылай — кто откроет, получит твои права GM.",
        disable_web_page_preview=True,
    )
