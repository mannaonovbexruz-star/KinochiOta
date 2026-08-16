"""Majburiy obuna testlari.

Ishga tushirish:
    python tests/test_subscription.py
"""

import asyncio

from harness import (  # noqa: E402
    SUBSCRIPTIONS,
    callback_update,
    check,
    last_buttons,
    last_text,
    make_bot,
    mark,
    message_update,
    report,
)
from harness import SENT  # noqa: E402

from aiogram import Dispatcher  # noqa: E402
from aiogram.fsm.storage.memory import MemoryStorage  # noqa: E402

from database import admins as admins_db  # noqa: E402
from database import channels as channels_db  # noqa: E402
from database import movies as movies_db  # noqa: E402
from handlers import register_routers  # noqa: E402

OWNER_ID = 7116299492
USER_ID = 4440000000

CH1 = "@ACIYNPUBG_UC"
CH2 = "@KinochiOka2025"

FAKE_MOVIES = {"1": {"movie_code": "1", "file_id": "F1", "title": "Labirint"}}
FAKE_CHANNELS: list[dict] = []

admins_db.get_admin_ids = lambda force=False: asyncio.sleep(0, result=set())
movies_db.get_movie_by_code = lambda code: asyncio.sleep(0, result=FAKE_MOVIES.get(code))
movies_db.count_movies = lambda: asyncio.sleep(0, result=len(FAKE_MOVIES))
movies_db.list_movies = lambda limit=20, offset=0: asyncio.sleep(0, result=list(FAKE_MOVIES.values()))


async def fake_list_channels(force: bool = False):
    return list(FAKE_CHANNELS)


async def fake_add_channel(chat_id, title=None, url=None):
    item = {"chat_id": chat_id, "title": title, "url": url}
    FAKE_CHANNELS.append(item)
    return item


async def fake_remove_channel(chat_id):
    before = len(FAKE_CHANNELS)
    FAKE_CHANNELS[:] = [c for c in FAKE_CHANNELS if c["chat_id"] != chat_id]
    return len(FAKE_CHANNELS) < before


async def fake_clear_channels():
    n = len(FAKE_CHANNELS)
    FAKE_CHANNELS.clear()
    return n


channels_db.list_channels = fake_list_channels
channels_db.add_channel = fake_add_channel
channels_db.remove_channel = fake_remove_channel
channels_db.clear_channels = fake_clear_channels

bot = make_bot()
dp = Dispatcher(storage=MemoryStorage())
register_routers(dp)


async def send(user_id: int, text: str | None = None, **kw) -> str:
    await dp.feed_update(bot, message_update(user_id, text, **kw))
    return last_text()


async def press(user_id: int, data: str) -> str:
    await dp.feed_update(bot, callback_update(user_id, data))
    return last_text()


def subscribe(user_id: int, *channels: str) -> None:
    for ch in channels:
        SUBSCRIPTIONS[(ch, user_id)] = "member"


def unsubscribe(user_id: int, *channels: str) -> None:
    for ch in channels:
        SUBSCRIPTIONS[(ch, user_id)] = "left"


async def main() -> None:
    print("\n[1] Kanal sozlanmagan — hamma erkin o'tadi:")
    FAKE_CHANNELS.clear()
    channels_db.invalidate_cache()
    m = mark()
    await send(USER_ID, "1")
    check("video keldi", any(r[0] == "SendVideo" for r in SENT[m:]), str([r[0] for r in SENT[m:]]))

    print("\n[2] Kanal bor, obuna yo'q — kino berilmaydi:")
    await fake_add_channel(CH1, "1-kanal", f"https://t.me/{CH1.lstrip('@')}")
    await fake_add_channel(CH2, "2-kanal", f"https://t.me/{CH2.lstrip('@')}")
    channels_db.invalidate_cache()
    unsubscribe(USER_ID, CH1, CH2)

    m = mark()
    reply = await send(USER_ID, "1")
    check("video berilmadi", not any(r[0] == "SendVideo" for r in SENT[m:]), str([r[0] for r in SENT[m:]]))
    check("obuna so'raldi", "obuna" in reply.lower(), reply[:60])
    buttons = last_buttons()
    check("kanal tugmalari bor", len(buttons) >= 2, str(buttons))
    check("tekshirish tugmasi bor", any("ekshir" in b for b in buttons), str(buttons))

    print("\n[3] Bitta kanalga obuna bo'lsa ham yetarli emas:")
    subscribe(USER_ID, CH1)
    m = mark()
    await send(USER_ID, "1")
    check("video berilmadi", not any(r[0] == "SendVideo" for r in SENT[m:]), str([r[0] for r in SENT[m:]]))

    print("\n[4] Ikkalasiga obuna — kino keladi:")
    subscribe(USER_ID, CH1, CH2)
    m = mark()
    await send(USER_ID, "1")
    check("video keldi", any(r[0] == "SendVideo" for r in SENT[m:]), str([r[0] for r in SENT[m:]]))

    print("\n[5] '✅ Tekshirish' tugmasi:")
    unsubscribe(USER_ID, CH2)
    await send(USER_ID, "1")
    reply = await press(USER_ID, "sub:check")
    check("hali obuna emas deydi", "obuna" in reply.lower(), reply[:60])

    subscribe(USER_ID, CH1, CH2)
    reply = await press(USER_ID, "sub:check")
    check("obuna tasdiqlandi", "rahmat" in reply.lower() or "✅" in reply, reply[:60])

    print("\n[6] Admin obunadan ozod:")
    unsubscribe(OWNER_ID, CH1, CH2)
    m = mark()
    await send(OWNER_ID, "1")
    check("adminga video keldi", any(r[0] == "SendVideo" for r in SENT[m:]),
          str([r[0] for r in SENT[m:]]))

    print("\n[7] Bot kanalda admin bo'lmasa — foydalanuvchi bloklanmaydi:")
    SUBSCRIPTIONS[(CH1, USER_ID)] = "error"
    SUBSCRIPTIONS[(CH2, USER_ID)] = "member"
    m = mark()
    await send(USER_ID, "1")
    check("video keldi (bloklanmadi)", any(r[0] == "SendVideo" for r in SENT[m:]),
          str([r[0] for r in SENT[m:]]))

    print("\n[8] Panelda '📢 Kanallar' faqat egasida:")
    SUBSCRIPTIONS.clear()
    subscribe(OWNER_ID, CH1, CH2)
    await send(OWNER_ID, "/admin")
    check("Kanallar tugmasi bor", any("Kanallar" in b for b in last_buttons()), str(last_buttons()))

    print("\n[9] Egasi kanal qo'sha va o'chira oladi:")
    reply = await press(OWNER_ID, "adm:channels")
    check("ro'yxat ochildi", CH1 in reply or "Kanallar" in reply, reply[:80])

    reply = await press(OWNER_ID, f"ch:rm:{CH1}")
    check("kanal o'chirildi", all(c["chat_id"] != CH1 for c in FAKE_CHANNELS),
          str([c["chat_id"] for c in FAKE_CHANNELS]))

    await press(OWNER_ID, "ch:add")
    reply = await send(OWNER_ID, "@YangiKanal")
    check("kanal qo'shildi", any(c["chat_id"] == "@YangiKanal" for c in FAKE_CHANNELS),
          str([c["chat_id"] for c in FAKE_CHANNELS]))

    print("\n[10] Oddiy foydalanuvchi kanal boshqara olmaydi:")
    before = [c["chat_id"] for c in FAKE_CHANNELS]
    await press(USER_ID, f"ch:rm:{CH2}")
    check("o'chira olmadi", [c["chat_id"] for c in FAKE_CHANNELS] == before,
          str([c["chat_id"] for c in FAKE_CHANNELS]))

    report()


if __name__ == "__main__":
    asyncio.run(main())
