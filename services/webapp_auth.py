"""Init data validation for Telegram WebApp (HMAC по BOT_TOKEN).
Используется когда Mini App шлёт initData на наш бэк для верификации.
В текущем MVP бот сам выдаёт JWT по telegram_id из update, но helper лежит
готовый — пригодится когда добавим серверный API для Mini App.
"""
import hashlib
import hmac
import os
from urllib.parse import parse_qsl


def validate_init_data(init_data: str) -> dict | None:
    """Возвращает распарсенный dict если подпись валидна, иначе None."""
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", os.environ["BOT_TOKEN"].encode(), hashlib.sha256).digest()
    calc_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calc_hash, received_hash):
        return None
    return parsed
