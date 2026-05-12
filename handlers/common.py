"""Общие команды и fallback."""
import os

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from services.supabase_client import get_user_by_tg

router = Router(name="common")
MINIAPP_URL = os.environ.get("PUBLIC_URL", "https://example.com")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    is_gm = False
    if message.from_user:
        u = await get_user_by_tg(message.from_user.id)
        is_gm = bool(u and u.get("is_gm"))

    gm_lines = ""
    if is_gm:
        gm_lines = (
            "\n\n<b>Команды GM:</b>\n"
            "/admin — ссылка на десктоп-админку\n"
            "/find @user — карточка юзера\n"
            "/grant @user 500 [причина] — начислить KEY\n"
        )

    await message.answer(
        "<b>OASIS — путь от Хостела до Оазиса.</b>\n\n"
        "🔑 За приглашение каждого жителя место в твоей комнате заполняется.\n"
        "🏠 Когда заполнены все 5 мест — закрываешь уровень и открываешь следующую жизнь.\n"
        "💎 KEY можно перевести в основную игру — на стиль, апгрейд и косметику.\n\n"
        "Команды:\n"
        "/start — начать или продолжить\n"
        "/me — твой профиль\n"
        "/help — это сообщение"
        + gm_lines,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🌴 Открыть игру", web_app=WebAppInfo(url=MINIAPP_URL))
        ]])
    )
