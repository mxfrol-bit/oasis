"""GM-команды: /grant, /find, /stats. Доступ только юзерам с is_gm=true."""
import logging
import re

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from services.supabase_client import (
    find_user_by_username,
    get_user_by_tg,
    gm_grant_via_service,
)

router = Router(name="gm")
log = logging.getLogger("oasis.gm")


async def _is_gm(telegram_id: int) -> bool:
    u = await get_user_by_tg(telegram_id)
    return bool(u and u.get("is_gm"))


@router.message(Command("grant"))
async def cmd_grant(message: Message, command: CommandObject) -> None:
    """/grant @username <amount> [причина...]"""
    if not message.from_user or not await _is_gm(message.from_user.id):
        return  # silent — GM-команды не должны палить себя
    args = (command.args or "").strip()
    m = re.match(r"^(@?\S+)\s+(-?\d+)(?:\s+(.+))?$", args)
    if not m:
        await message.answer("Формат: <code>/grant @username 500 [причина]</code>")
        return
    target_username, amount_str, reason = m.groups()
    amount = int(amount_str)
    target = await find_user_by_username(target_username)
    if not target:
        await message.answer(f"Юзер {target_username} не найден.")
        return
    try:
        action_id = await gm_grant_via_service(
            gm_telegram_id=message.from_user.id,
            target_user_id=target["id"],
            amount=amount,
            reason=reason or "manual",
            comment=f"by @{message.from_user.username or message.from_user.id}",
        )
    except Exception as e:
        log.exception("grant failed")
        await message.answer(f"❌ Ошибка: {e}")
        return
    sign = "+" if amount >= 0 else ""
    await message.answer(
        f"✅ {sign}{amount} KEY → <b>{target.get('first_name') or target_username}</b>\n"
        f"<code>action_id: {action_id[:8]}…</code>"
    )


@router.message(Command("find"))
async def cmd_find(message: Message, command: CommandObject) -> None:
    """/find @username — карточка юзера для GM."""
    if not message.from_user or not await _is_gm(message.from_user.id):
        return
    username = (command.args or "").strip().lstrip("@")
    if not username:
        await message.answer("Формат: <code>/find username</code>")
        return
    u = await find_user_by_username(username)
    if not u:
        await message.answer(f"Не нашёл @{username}.")
        return
    full = await get_user_by_tg(u["telegram_id"])
    p = (full or {}).get("profiles", [{}])[0] if full else {}
    await message.answer(
        f"👤 <b>{u.get('first_name') or '—'}</b> @{u.get('username') or '—'}\n"
        f"tg_id: <code>{u['telegram_id']}</code>\n"
        f"user_id: <code>{u['id']}</code>\n"
        f"Баланс: <b>{p.get('key_balance', 0)} KEY</b>\n"
        f"Уровень: <b>{p.get('current_level_id') or '—'}/12</b>  "
        f"(достиг: {p.get('highest_level_reached', 0)})\n"
        f"Рефералов: <b>{p.get('total_referrals', 0)}</b>"
    )


@router.message(Command("me"))
async def cmd_me(message: Message) -> None:
    """Дебаг: свой telegram_id и статус GM."""
    if not message.from_user:
        return
    u = await get_user_by_tg(message.from_user.id)
    if not u:
        await message.answer(f"tg_id: <code>{message.from_user.id}</code>\nНе зарегистрирован — отправь /start.")
        return
    p = u.get("profiles", [{}])[0] if u.get("profiles") else {}
    await message.answer(
        f"tg_id: <code>{message.from_user.id}</code>\n"
        f"user_id: <code>{u['id']}</code>\n"
        f"ref_code: <code>{u['ref_code']}</code>\n"
        f"GM: <b>{'да' if u.get('is_gm') else 'нет'}</b>\n"
        f"Баланс: <b>{p.get('key_balance', 0)} KEY</b>"
    )
