"""Xavfsizlik testi: oddiy foydalanuvchi admin buyruqlariga kira olmasligi kerak.

Ishga tushirish (pytest kerak emas):
    python tests/test_admin_access.py
"""

import asyncio
import datetime
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Test uchun soxta muhit — haqiqiy Telegram/Supabase'ga chiqilmaydi
os.environ.update(
    BOT_TOKEN="111111:TEST-TOKEN-NOT-REAL",
    ADMIN_ID="7116299492",
    SUPABASE_URL="https://example.supabase.co",
    SUPABASE_KEY="test-key",
)

from aiogram import Bot, Dispatcher  # noqa: E402
from aiogram.client.default import DefaultBotProperties  # noqa: E402
from aiogram.client.session.base import BaseSession  # noqa: E402
from aiogram.enums import ParseMode  # noqa: E402
from aiogram.fsm.storage.memory import MemoryStorage  # noqa: E402
from aiogram.types import Chat, Message, Update, User, Video  # noqa: E402

from database import movies as movies_db  # noqa: E402
from handlers import register_routers  # noqa: E402

ADMIN_ID = 7116299492
STRANGER_ID = 5555555555  # begona odam

SENT: list[tuple[int, str, str]] = []  # (chat_id, method, text)
FAKE_DB: dict[str, dict] = {}


class FakeSession(BaseSession):
    """Telegram API o'rniga — hech qanday tarmoq so'rovi ketmaydi."""

    async def close(self): ...

    async def stream_content(self, *a, **kw):
        yield b""

    async def make_request(self, bot, method, timeout=None):
        name = type(method).__name__
        text = getattr(method, "text", None) or getattr(method, "caption", "") or ""
        SENT.append((getattr(method, "chat_id", 0), name, text))
        if name == "SendMessage":
            return Message(message_id=1, date=datetime.datetime.now(),
                           chat=Chat(id=method.chat_id, type="private"), text=method.text)
        if name == "GetMe":
            return User(id=1, is_bot=True, first_name="Bot", username="test_bot")
        return True


async def fake_get(code):
    return FAKE_DB.get(code)


async def fake_add(movie_code, file_id, title):
    FAKE_DB[movie_code] = {"movie_code": movie_code, "file_id": file_id, "title": title}
    return FAKE_DB[movie_code]


async def fake_count():
    return len(FAKE_DB)


async def fake_list(limit=20, offset=0):
    return list(FAKE_DB.values())


async def fake_delete(code):
    return FAKE_DB.pop(code, None) is not None


movies_db.get_movie_by_code = fake_get
movies_db.add_movie = fake_add
movies_db.count_movies = fake_count
movies_db.list_movies = fake_list
movies_db.delete_movie = fake_delete

bot = Bot("111111:TEST-TOKEN-NOT-REAL", session=FakeSession(),
          default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
register_routers(dp)

_seq = [0]


def make_update(user_id: int, text: str | None = None, video: bool = False) -> Update:
    _seq[0] += 1
    return Update(update_id=_seq[0], message=Message(
        message_id=_seq[0], date=datetime.datetime.now(),
        chat=Chat(id=user_id, type="private"),
        from_user=User(id=user_id, is_bot=False, first_name="X"),
        text=text,
        video=Video(file_id="F", file_unique_id="u", width=1, height=1, duration=1) if video else None,
    ))


async def send(user_id: int, text: str | None = None, video: bool = False) -> str:
    await dp.feed_update(bot, make_update(user_id, text, video))
    return SENT[-1][2] if SENT else ""


FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"   PASS  {name}")
    else:
        print(f"   FAIL  {name}  -> {detail}")
        FAILURES.append(name)


async def main() -> None:
    print("\n[1] Begona odam admin buyruqlarini bosadi (hech biri ishlamasligi kerak):")
    for cmd in ("/admin", "/list", "/stats", "/delete", "/cancel"):
        reply = await send(STRANGER_ID, cmd)
        # Admin javoblari: "Admin panel", "Oxirgi 20 ta", "Bazadagi kinolar soni", "o'chiriladigan"
        leaked = any(w in reply for w in ("Admin panel", "Oxirgi 20", "Bazadagi kinolar soni", "chiriladigan kino"))
        check(f"{cmd} bloklandi", not leaked, reply[:60])

    print("\n[2] Begona odam video tashladi (kino qo'shish boshlanmasligi kerak):")
    reply = await send(STRANGER_ID, video=True)
    check("video rad etildi", "Video qabul qilindi" not in reply, reply[:60])
    state = await dp.fsm.get_context(bot, STRANGER_ID, STRANGER_ID).get_state()
    check("FSM holati ochilmadi", state is None, f"state={state}")

    print("\n[3] Begona odam baza holatini o'zgartira olmaydi:")
    FAKE_DB["777"] = {"movie_code": "777", "file_id": "F", "title": "Bor kino"}
    await send(STRANGER_ID, "/delete")
    await send(STRANGER_ID, "777")
    check("kino o'chirilmadi", "777" in FAKE_DB, f"DB={list(FAKE_DB)}")

    print("\n[4] Haqiqiy admin uchun hammasi ishlaydi:")
    reply = await send(ADMIN_ID, "/admin")
    check("/admin ochildi", "Admin panel" in reply, reply[:60])
    reply = await send(ADMIN_ID, video=True)
    check("video qabul qilindi", "Video qabul qilindi" in reply, reply[:60])
    await send(ADMIN_ID, "125")
    reply = await send(ADMIN_ID, "Yangi kino")
    check("kino saqlandi", FAKE_DB.get("125", {}).get("title") == "Yangi kino", str(FAKE_DB.get("125")))

    print("\n[5] /id begona odamga admin ma'lumotini sizdirmaydi:")
    reply = await send(STRANGER_ID, "/id")
    check("oddiy user deb belgilandi", "oddiy foydalanuvchi" in reply, reply[:80])
    check("ADMIN_ID ro'yxati yashirilgan", str(ADMIN_ID) not in reply, reply[:80])

    reply = await send(ADMIN_ID, "/id")
    check("admin o'zi ro'yxatni ko'radi", str(ADMIN_ID) in reply, reply[:80])

    print()
    if FAILURES:
        print(f"XATO: {len(FAILURES)} ta test yiqildi: {FAILURES}")
        sys.exit(1)
    print("HAMMA TEST O'TDI — admin qismi himoyalangan.")


if __name__ == "__main__":
    asyncio.run(main())
