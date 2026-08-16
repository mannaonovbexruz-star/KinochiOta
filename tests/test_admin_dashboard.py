"""Admin dashboard + parol bilan kirish testlari.

Ishga tushirish:
    python tests/test_admin_dashboard.py
"""

import asyncio

from harness import (  # noqa: E402  (harness sys.path ni sozlaydi)
    callback_update,
    check,
    last_buttons,
    last_text,
    make_bot,
    mark,
    message_update,
    methods_since,
    report,
)

from aiogram import Dispatcher  # noqa: E402
from aiogram.fsm.storage.memory import MemoryStorage  # noqa: E402

import config  # noqa: E402
from database import admins as admins_db  # noqa: E402
from database import movies as movies_db  # noqa: E402
from handlers import auth as auth_handlers  # noqa: E402
from handlers import register_routers  # noqa: E402

OWNER_ID = 7116299492      # ADMIN_ID env — egasi
NEWCOMER_ID = 5551234567   # parol bilan kiradigan odam
STRANGER_ID = 4440000000   # begona

PASSWORD = "kino2026"

# --- Soxta bazalar ---
FAKE_ADMINS: dict[int, dict] = {}
FAKE_MOVIES: dict[str, dict] = {}


async def fake_get_admin_ids(force: bool = False) -> set[int]:
    return set(FAKE_ADMINS)


async def fake_add_admin(user_id: int, username: str | None = None) -> dict:
    FAKE_ADMINS[user_id] = {"user_id": user_id, "username": username}
    return FAKE_ADMINS[user_id]


async def fake_remove_admin(user_id: int) -> bool:
    return FAKE_ADMINS.pop(user_id, None) is not None


async def fake_list_admins() -> list[dict]:
    return list(FAKE_ADMINS.values())


admins_db.get_admin_ids = fake_get_admin_ids
admins_db.add_admin = fake_add_admin
admins_db.remove_admin = fake_remove_admin
admins_db.list_admins = fake_list_admins

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


async def press(user_id: int, data: str) -> str:
    await dp.feed_update(bot, callback_update(user_id, data))
    return last_text()


async def main() -> None:
    print("\n[1] Parol bilan kirish:")
    auth_handlers.reset_login_attempts()
    FAKE_ADMINS.clear()

    m = mark()
    reply = await send(NEWCOMER_ID, f"/admin {PASSWORD}", username="yangi")
    check("admin bo'ldi", NEWCOMER_ID in FAKE_ADMINS, f"admins={list(FAKE_ADMINS)}")
    check("dashboard ochildi", "Admin panel" in reply, reply[:60])
    check("parol xabari o'chirildi", "DeleteMessage" in methods_since(m), str(methods_since(m)))

    print("\n[2] Noto'g'ri parol:")
    auth_handlers.reset_login_attempts()
    reply = await send(STRANGER_ID, "/admin xato-parol")
    check("kirita olmadi", STRANGER_ID not in FAKE_ADMINS, f"admins={list(FAKE_ADMINS)}")
    check("xato xabari keldi", "noto'g'ri" in reply.lower(), reply[:60])

    print("\n[3] 5 marta xato -> bloklanadi:")
    auth_handlers.reset_login_attempts()
    for _ in range(5):
        await send(STRANGER_ID, "/admin xato")
    reply = await send(STRANGER_ID, f"/admin {PASSWORD}")  # endi TO'G'RI parol
    check("blok ishladi", STRANGER_ID not in FAKE_ADMINS, f"admins={list(FAKE_ADMINS)}")
    check("blok xabari keldi", "blok" in reply.lower(), reply[:60])

    print("\n[4] Egasi dashboardida 'Adminlar' tugmasi bor:")
    buttons = []
    await send(OWNER_ID, "/admin")
    buttons = last_buttons()
    check("panel ochildi", any("Kino qo'sh" in b for b in buttons), str(buttons))
    check("Adminlar tugmasi bor", any("Adminlar" in b for b in buttons), str(buttons))

    print("\n[5] Oddiy adminda 'Adminlar' tugmasi yo'q:")
    await send(NEWCOMER_ID, "/admin")
    buttons = last_buttons()
    check("panel ochildi", any("Kino qo'sh" in b for b in buttons), str(buttons))
    check("Adminlar tugmasi yo'q", not any("Adminlar" in b for b in buttons), str(buttons))

    print("\n[6] Oddiy admin adminlar ro'yxatiga kira olmaydi:")
    reply = await press(NEWCOMER_ID, "adm:admins")
    check("rad etildi", "egasi" in reply.lower(), reply[:60])

    print("\n[7] Egasini o'chirib bo'lmaydi:")
    reply = await press(OWNER_ID, f"adm:rm:{OWNER_ID}")
    check("o'chirilmadi", config.is_owner(OWNER_ID), "egasi env'da, o'chmasligi kerak")
    check("ogohlantirish keldi", "egasi" in reply.lower(), reply[:60])

    print("\n[8] Egasi oddiy adminni o'chira oladi:")
    reply = await press(OWNER_ID, f"adm:rm:{NEWCOMER_ID}")
    check("admin o'chirildi", NEWCOMER_ID not in FAKE_ADMINS, f"admins={list(FAKE_ADMINS)}")

    print("\n[9] O'chirilgan admin endi kira olmaydi:")
    reply = await send(NEWCOMER_ID, "/admin")
    check("panel ochilmadi", "Admin panel" not in reply, reply[:60])

    print("\n[10] Admin tugma orqali kino qo'sha oladi:")
    await fake_add_admin(NEWCOMER_ID, "yangi")
    reply = await press(NEWCOMER_ID, "adm:add")
    check("video so'radi", "video" in reply.lower(), reply[:60])
    await send(NEWCOMER_ID, video=True)
    await send(NEWCOMER_ID, "300")
    await send(NEWCOMER_ID, "Test kino")
    check("kino saqlandi", FAKE_MOVIES.get("300", {}).get("title") == "Test kino", str(FAKE_MOVIES))

    print("\n[11] Begona odam tugmalarni bosa olmaydi:")
    FAKE_MOVIES["999"] = {"movie_code": "999", "file_id": "F", "title": "Maxfiy"}
    reply = await press(STRANGER_ID, "adm:stats")
    check("statistika berilmadi", "Bazadagi kinolar soni" not in reply, reply[:60])
    check("rad javobi keldi", "siz uchun emas" in reply.lower(), reply[:60])

    reply = await press(STRANGER_ID, "adm:list")
    check("ro'yxat berilmadi", "Maxfiy" not in reply, reply[:60])

    reply = await press(STRANGER_ID, f"adm:rm:{OWNER_ID}")
    check("egani o'chira olmadi", config.is_owner(OWNER_ID), "egasi o'chmasligi kerak")

    print("\n[12] Parol o'chirilgan bo'lsa hech kim kira olmaydi:")
    auth_handlers.reset_login_attempts()
    saved = config.ADMIN_PASSWORD
    config.ADMIN_PASSWORD = ""
    try:
        reply = await send(STRANGER_ID, "/admin kino2026")
        check("kirita olmadi", STRANGER_ID not in FAKE_ADMINS, f"admins={list(FAKE_ADMINS)}")
        check("o'chiq deb javob berdi", "o'chirilgan" in reply.lower(), reply[:60])
    finally:
        config.ADMIN_PASSWORD = saved

    print("\n[14] Egasi paneldan ID orqali admin qo'sha oladi:")
    FAKE_ADMINS.clear()
    await press(OWNER_ID, "adm:admins")
    check("➕ tugmasi bor", any("Admin qo'shish" in b for b in last_buttons()), str(last_buttons()))

    reply = await press(OWNER_ID, "adm:addadmin")
    check("ID so'radi", "id" in reply.lower(), reply[:60])

    reply = await send(OWNER_ID, "8363001073")
    check("admin qo'shildi", 8363001073 in FAKE_ADMINS, f"admins={list(FAKE_ADMINS)}")

    print("\n[15] Noto'g'ri ID qabul qilinmaydi:")
    await press(OWNER_ID, "adm:addadmin")
    reply = await send(OWNER_ID, "-1004423253818")  # kanal ID'si
    check("kanal ID rad etildi", -1004423253818 not in FAKE_ADMINS, f"admins={list(FAKE_ADMINS)}")
    check("ogohlantirish", "kanal" in reply.lower() or "raqam" in reply.lower(), reply[:60])

    print("\n[16] Oddiy admin ➕ tugmasini bosa olmaydi:")
    await fake_add_admin(NEWCOMER_ID, "oddiy")
    reply = await press(NEWCOMER_ID, "adm:addadmin")
    check("rad etildi", "egasi" in reply.lower(), reply[:60])

    print("\n[13] Parolda ASCII bo'lmagan harf bo'lsa ham ishlaydi:")
    auth_handlers.reset_login_attempts()
    FAKE_ADMINS.clear()
    saved = config.ADMIN_PASSWORD
    config.ADMIN_PASSWORD = "Behruz’2026ў"  # tipografik apostrof + kirill
    try:
        reply = await send(STRANGER_ID, "/admin Behruz’2026ў")
        check("admin bo'ldi", STRANGER_ID in FAKE_ADMINS, f"admins={list(FAKE_ADMINS)}")
        check("panel ochildi", "Admin panel" in reply, reply[:60])
    finally:
        config.ADMIN_PASSWORD = saved
        FAKE_ADMINS.clear()

    report()


if __name__ == "__main__":
    asyncio.run(main())
