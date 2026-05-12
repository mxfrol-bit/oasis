"""OASIS Telegram Bot — entry point.
Запускает параллельно aiogram polling + aiohttp HTTP server (auth + static)."""
import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web

from handlers import common, gm, start
from server import create_app
from services.supabase_client import init_supabase

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("oasis.bot")


async def run_http(port: int) -> None:
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    log.info("HTTP server listening on 0.0.0.0:%s", port)
    await asyncio.Event().wait()


async def run_polling(bot: Bot, dp: Dispatcher) -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


async def main() -> None:
    # Fail fast если переменных нет
    required = ["BOT_TOKEN", "SUPABASE_URL", "SUPABASE_ANON_KEY",
                "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_JWT_SECRET"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        log.error("Missing required env vars: %s", ", ".join(missing))
        log.error("Set them in Railway → Settings → Variables and redeploy")
        sys.exit(1)

    bot_token = os.environ["BOT_TOKEN"]
    init_supabase(
        url=os.environ["SUPABASE_URL"],
        service_key=os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )

    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    me = await bot.get_me()
    log.info("Bot started: @%s (id=%s)", me.username, me.id)

    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(gm.router)
    dp.include_router(common.router)

    port = int(os.environ.get("PORT", 8080))

    try:
        await asyncio.gather(run_http(port), run_polling(bot, dp))
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
