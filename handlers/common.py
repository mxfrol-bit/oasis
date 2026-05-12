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

router = Router(name="common")
MINIAPP_URL = os.environ.get("PUBLIC_URL", "https://example.com")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>OASIS — путь от Хостела до Оазиса.</b>\n\n"
        "🔑 За приглашение каждого жителя место в твоей комнате заполняется.\n"
        "🏠 Когда заполнены все 5 мест — закрываешь уровень и открываешь следующую жизнь.\n"
        "💎 KEY можно перевести в основную игру — на стиль, апгрейд и косметику.\n\n"
        "Команды:\n"
        "/start — начать или продолжить\n"
        "/me — твой профиль\n"
        "/help — это сообщение",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🌴 Открыть игру", web_app=WebAppInfo(url=MINIAPP_URL))
        ]])
    )
