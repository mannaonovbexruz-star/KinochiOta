"""Xavfsizlik testi: oddiy foydalanuvchi admin qismiga kira olmasligi kerak.

Ishga tushirish:
    python tests/test_admin_access.py
"""

import asyncio

from harness import check, last_text, mark, message_update, make_bot, report  # noqa: E402

from aiogram import Dispatcher  # noqa: E402
from aiogram.fsm.storage.memory import MemoryStorage  # noqa: E402

from database import admins as admins_db  # noqa: E402
from database import movies as movies_db  # noqa: E402
from handlers import register_routers  # noqa: E402

OWNER_ID = 7116299492
STRANGER_ID = 5555555555

FAKE_MOVIES: dict[str, dict] = {}

# Baza o'rniga xotira — hech qanday tarmoq so'rovi ketmaydi
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


async def main() -> None:
    print("\n[1] Begona odam admin buyruqlarini bosadi:")
    for cmd in ("/admin", "/list", "/stats", "/delete", "/cancel", "/help_admin"):
        reply = await send(STRANGER_ID, cmd)
        leaked = any(
            w in reply
            for w in ("Admin panel", "Oxirgi 20", "Bazadagi kinolar soni",
                      "chiriladigan kino", "Admin buyruqlari")
        )
        check(f"{cmd} bloklandi", not leaked, reply[:60])

    print("\n[2] Begona odam video tashladi:")
    reply = await send(STRANGER_ID, video=True)
    check("video rad etildi", "Video qabul qilindi" not in reply, reply[:60])
    state = await dp.fsm.get_context(bot, STRANGER_ID, STRANGER_ID).get_state()
    check("FSM holati ochilmadi", state is None, f"state={state}")

    print("\n[3] Begona odam bazani o'zgartira olmaydi:")
    FAKE_MOVIES["777"] = {"movie_code": "777", "file_id": "F", "title": "Bor kino"}
    await send(STRANGER_ID, "/delete")
    await send(STRANGER_ID, "777")
    check("kino o'chirilmadi", "777" in FAKE_MOVIES, f"DB={list(FAKE_MOVIES)}")

    print("\n[4] Egasi uchun hammasi ishlaydi:")
    reply = await send(OWNER_ID, "/admin")
    check("/admin ochildi", "Admin panel" in reply, reply[:60])
    reply = await send(OWNER_ID, video=True)
    check("video qabul qilindi", "Video qabul qilindi" in reply, reply[:60])
    await send(OWNER_ID, "125")
    await send(OWNER_ID, "Yangi kino")
    check("kino saqlandi", FAKE_MOVIES.get("125", {}).get("title") == "Yangi kino",
          str(FAKE_MOVIES.get("125")))

    print("\n[5] /id begona odamga admin ma'lumotini sizdirmaydi:")
    reply = await send(STRANGER_ID, "/id")
    check("oddiy user deb belgilandi", "oddiy foydalanuvchi" in reply, reply[:80])
    check("ADMIN_ID ro'yxati yashirilgan", str(OWNER_ID) not in reply, reply[:80])

    reply = await send(OWNER_ID, "/id")
    check("egasi o'zi ro'yxatni ko'radi", str(OWNER_ID) in reply, reply[:80])

    print("\n[6] Oddiy foydalanuvchi kino ola oladi:")
    m = mark()
    await send(STRANGER_ID, "125")
    from harness import SENT  # noqa: E402
    check("video yuborildi", any(row[0] == "SendVideo" for row in SENT[m:]),
          str([row[0] for row in SENT[m:]]))

    reply = await send(STRANGER_ID, "888")
    check("topilmagan kod", "topilmadi" in reply, reply[:60])

    report()


if __name__ == "__main__":
    asyncio.run(main())
