"""Kino bot — kirish nuqtasi (entrypoint).

Ishga tushirish:
    python bot.py
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from aiohttp import web

import config
from database.admins import ping as admins_ping
from database.client import ping as db_ping
from handlers import register_routers

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def set_commands(bot: Bot) -> None:
    """Telegram menyusidagi buyruqlar ro'yxati."""
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="🎬 Botni ishga tushirish"),
            BotCommand(command="help", description="ℹ️ Yordam"),
            BotCommand(command="id", description="🆔 ID va admin holatim"),
        ]
    )


async def start_health_server() -> web.AppRunner:
    """Railway/Render healthcheck uchun minimal HTTP server.

    railway.json da `healthcheckPath: /health` bor — bu endpoint javob
    bermasa, deploy "unhealthy" deb belgilanadi va restart bo'laveradi.
    """
    app = web.Application()
    app.router.add_get("/", lambda _: web.json_response({"status": "ok"}))
    app.router.add_get("/health", lambda _: web.json_response({"status": "ok"}))

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=config.PORT)
    await site.start()
    logger.info("Health server ishga tushdi: 0.0.0.0:%s", config.PORT)
    return runner


async def main() -> None:
    config.validate()

    # Supabase'ga ulanishni startda tekshiramiz — noto'g'ri kalit/jadval
    # bo'lsa, buni birinchi foydalanuvchidan emas, loglardan bilib olamiz
    if not await asyncio.to_thread(db_ping):
        logger.error("Supabase'ga ulanib bo'lmadi. SUPABASE_URL/SUPABASE_KEY va jadvalni tekshiring.")
        sys.exit(1)

    # `admins` jadvali bo'lmasa bot ishlayveradi (egasi env'dan olinadi),
    # lekin parol bilan kirish ishlamaydi — buni logda aniq aytamiz
    if not await asyncio.to_thread(admins_ping):
        logger.warning(
            "⚠️ `admins` jadvali topilmadi — Supabase SQL Editor'da "
            "sql/002_admins.sql ni ishga tushiring. "
            "Hozircha faqat ADMIN_ID dagi egasi admin bo'la oladi."
        )
    elif not config.ADMIN_PASSWORD:
        logger.warning(
            "⚠️ ADMIN_PASSWORD sozlanmagan — parol bilan admin bo'lish o'chiq."
        )

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # MemoryStorage — FSM holatlari RAM da. Restart bo'lsa yarim qolgan
    # jarayon o'chadi (kino qo'shish uchun bu yetarli). Bir nechta instansiya
    # kerak bo'lsa RedisStorage ga o'ting.
    dp = Dispatcher(storage=MemoryStorage())
    register_routers(dp)

    runner = await start_health_server() if config.ENABLE_HEALTH_SERVER else None

    try:
        # Eski webhook qolib ketgan bo'lsa polling ishlamaydi — tozalaymiz
        await bot.delete_webhook(drop_pending_updates=True)
        await set_commands(bot)

        me = await bot.get_me()
        logger.info("Bot ishga tushdi: @%s (adminlar: %s)", me.username, config.ADMIN_IDS)

        await dp.start_polling(bot)
    finally:
        if runner is not None:
            await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
