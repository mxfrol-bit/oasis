"""/start handler: регистрация юзера, обработка реф-кода из deeplink."""
import logging
import os
import re

from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from services.supabase_client import register_user, get_user_by_tg

router = Router(name="start")
log = logging.getLogger("oasis.start")

REF_PREFIX = "ref_"
MINIAPP_URL = os.environ.get("PUBLIC_URL", "https://example.com")


def parse_ref_payload(payload: str | None) -> tuple[str | None, int | None]:
    """Парсит start_param. Формат: 'ref_XXXXXXX' или 'XXXXXXX'.
    Возвращает (ref_code, None). target_level_id остаётся None — уровень
    выбирается реферралом в Mini App после регистрации.
    """
    if not payload:
        return (None, None)
    payload = payload.strip()
    if payload.startswith(REF_PREFIX):
        payload = payload[len(REF_PREFIX):]
    payload = payload.upper()
    if re.fullmatch(r"[A-Z2-9]{4,12}", payload):
        return (payload, None)
    return (None, None)


def parse_ref_code(payload: str | None) -> str | None:
    code, _ = parse_ref_payload(payload)
    return code


def play_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌴 Открыть игру", web_app=WebAppInfo(url=MINIAPP_URL))],
        ]
    )


@router.message(CommandStart(deep_link=True))
@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject) -> None:
    user = message.from_user
    if not user:
        return

    ref_code, target_level_id = parse_ref_payload(command.args)

    result = await register_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        photo_url=None,
        language_code=user.language_code or "ru",
        ref_code=ref_code,
        target_level_id=target_level_id,
    )

    if result.get("already_exists"):
        existing = await get_user_by_tg(user.id)
        balance = (existing or {}).get("profiles", [{}])[0].get("key_balance", 0) if existing else 0
        await message.answer(
            f"С возвращением, <b>{user.first_name or 'друг'}</b>.\n\n"
            f"Баланс: <b>{balance} KEY</b>\n"
            f"Открой приложение, чтобы продолжить путь 👇",
            reply_markup=play_keyboard(),
        )
        return

    # Новый юзер
    fresh = await get_user_by_tg(user.id)
    my_ref = fresh["ref_code"] if fresh else "??????"
    welcome = result.get("welcome_bonus", 500)

    ref_line = ""
    if result.get("has_referrer"):
        ref_line = (
            "\n🤝 Тебя пригласил <b>житель</b> — ты занял место в его комнате.\n"
            if result.get("slot_filled")
            else "\n🤝 Тебя пригласил <b>житель</b>, твоё место зарезервировано.\n"
        )

    await message.answer(
        f"Добро пожаловать в <b>OASIS</b>, {user.first_name or 'друг'}.\n\n"
        f"Ты получил <b>{welcome} KEY</b> — стартовый бонус для входа в Хостел I.\n"
        f"{ref_line}\n"
        f"Твой путь — 12 ступеней: Хостел → Квартира → Дом → Оазис.\n"
        f"Заполни 5 мест в комнате — открой следующую жизнь.\n\n"
        f"🔗 Твоя ссылка для приглашений:\n<code>https://t.me/{(await message.bot.get_me()).username}?start={REF_PREFIX}{my_ref}</code>",
        reply_markup=play_keyboard(),
    )
