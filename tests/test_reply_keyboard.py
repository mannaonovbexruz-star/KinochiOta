"""Doimiy (reply) klaviatura testlari — yozish maydoni ostidagi tugmalar.

Ishga tushirish:
    python tests/test_reply_keyboard.py
"""

import asyncio

from harness import (  # noqa: E402
    check,
    last_buttons,
    last_markup,
    last_text,
    make_bot,
    message_update,
    report,
)

from aiogram import Dispatcher  # noqa: E402
from aiogram.fsm.storage.memory import MemoryStorage  # noqa: E402

from database import admins as admins_db  # noqa: E402
from database import movies as movies_db  # noqa: E402
from handlers import register_routers  # noqa: E402

OWNER_ID = 7116299492
STRANGER_ID = 4440000000

FAKE_MOVIES: dict[str, dict] = {}

admins_db.get_admin_ids = lambda force=False: asyncio.sleep(0, result=set())
admins_db.list_admins = lambda: asyncio.sleep(0, result=[])
movies_db.get_movie_by_code = lambda code: asyncio.sleep(0, result=FAKE_MOVIES.get(code))
movies_db.count_movies = lambda: asyncio.sleep(0, result=len(FAKE_MOVIES))
movies_db.list_movies = lambda limit=20, offset=0: asyncio.sleep(0, result=list(FAKE_MOVIES.values()))
movies_db.delete_movie = lambda code: asyncio.sleep(0, result=FAKE_MOVIES.pop(code, None) is not None)


async def fake_add_movie(movie_code, file_id, title):
    FAKE_MOVIES[movie_code] = {"movie_code": movie_code, "file_id": file_id, "title": title}
    return FAKE_MOVIES[movie_code]


movies_db.add_movie = fake_add_movie

bot = make_bot()
dp = Dispatcher(storage=MemoryStorage())
register_routers(dp)


async def send(user_id: int, text: str | None = None, **kw) -> str:
    await dp.feed_update(bot, message_update(user_id, text, **kw))
    return last_text()


# Tugma matnlari — kod bilan bir xil bo'lishi shart
BTN_ADD = "🎬 Kino qo'shish"
BTN_DELETE = "🗑 Kino o'chirish"
BTN_LIST = "📋 Ro'yxat"
BTN_STATS = "📊 Statistika"


async def main() -> None:
    print("\n[1] Admin /start bosganda doimiy klaviatura keladi:")
    await send(OWNER_ID, "/start")
    check("reply klaviatura", last_markup() == "ReplyKeyboardMarkup", last_markup())
    buttons = last_buttons()
    for label in (BTN_ADD, BTN_DELETE, BTN_LIST, BTN_STATS):
        check(f"tugma bor: {label}", label in buttons, str(buttons))

    print("\n[2] Tugmalar ishlaydi (kino kodi deb qidirilmaydi):")
    reply = await send(OWNER_ID, BTN_STATS)
    check("statistika", "kinolar soni" in reply.lower(), reply[:60])
    check("kod deb qidirmadi", "topilmadi" not in reply, reply[:60])

    reply = await send(OWNER_ID, BTN_LIST)
    check("ro'yxat", "bo'sh" in reply.lower() or "Oxirgi" in reply, reply[:60])

    reply = await send(OWNER_ID, BTN_ADD)
    check("video so'radi", "video" in reply.lower(), reply[:60])

    reply = await send(OWNER_ID, BTN_DELETE)
    check("kod so'radi", "kod" in reply.lower(), reply[:60])
    await send(OWNER_ID, "/cancel")

    print("\n[3] Tugma orqali kino qo'shish to'liq ishlaydi:")
    await send(OWNER_ID, BTN_ADD)
    await send(OWNER_ID, video=True)
    await send(OWNER_ID, "500")
    await send(OWNER_ID, "Tugma orqali kino")
    check("saqlandi", FAKE_MOVIES.get("500", {}).get("title") == "Tugma orqali kino",
          str(FAKE_MOVIES.get("500")))

    print("\n[4] Oddiy foydalanuvchida admin klaviaturasi yo'q:")
    await send(STRANGER_ID, "/start")
    check("admin tugmalari yo'q", BTN_ADD not in last_buttons(), str(last_buttons()))

    print("\n[5] Begona odam tugma matnini qo'lda yozsa — admin amali bajarilmaydi:")
    reply = await send(STRANGER_ID, BTN_STATS)
    check("statistika berilmadi", "kinolar soni" not in reply.lower(), reply[:60])
    check("kod deb qaraldi", "topilmadi" in reply, reply[:60])

    reply = await send(STRANGER_ID, BTN_ADD)
    check("video so'ramadi", "Videoni shu chatga" not in reply, reply[:60])

    report()


if __name__ == "__main__":
    asyncio.run(main())
