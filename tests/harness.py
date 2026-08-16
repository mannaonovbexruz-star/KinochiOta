"""Testlar uchun umumiy asboblar: soxta Telegram sessiyasi va Update yasash.

Tarmoqqa umuman chiqilmaydi — barcha Telegram API chaqiruvlari ushlab qolinadi.
"""

import datetime
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault("BOT_TOKEN", "111111:TEST-TOKEN-NOT-REAL")
os.environ.setdefault("ADMIN_ID", "7116299492")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("ADMIN_PASSWORD", "kino2026")

from aiogram import Bot  # noqa: E402
from aiogram.client.default import DefaultBotProperties  # noqa: E402
from aiogram.client.session.base import BaseSession  # noqa: E402
from aiogram.enums import ParseMode  # noqa: E402
from aiogram.types import (  # noqa: E402
    CallbackQuery,
    Chat,
    Message,
    Update,
    User,
    Video,
)

TEST_TOKEN = "111111:TEST-TOKEN-NOT-REAL"

# Yuborilgan har bir API chaqiruvi:
# (metod nomi, matn, tugmalar ro'yxati, klaviatura turi)
SENT: list[tuple[str, str, list[str], str]] = []


def _buttons(method) -> list[str]:
    """Inline ham, reply klaviatura ham bir xil o'qiladi."""
    markup = getattr(method, "reply_markup", None)
    rows = getattr(markup, "inline_keyboard", None) or getattr(markup, "keyboard", None) or []
    return [getattr(btn, "text", str(btn)) for row in rows for btn in row]


def _markup_type(method) -> str:
    markup = getattr(method, "reply_markup", None)
    return type(markup).__name__ if markup is not None else ""


class FakeSession(BaseSession):
    async def close(self): ...

    async def stream_content(self, *a, **kw):
        yield b""

    async def make_request(self, bot, method, timeout=None):
        name = type(method).__name__
        text = getattr(method, "text", None) or getattr(method, "caption", "") or ""
        SENT.append((name, text, _buttons(method), _markup_type(method)))

        if name in ("SendMessage", "EditMessageText"):
            return Message(
                message_id=1,
                date=datetime.datetime.now(),
                chat=Chat(id=getattr(method, "chat_id", 0) or 0, type="private"),
                text=getattr(method, "text", ""),
            )
        if name == "GetMe":
            return User(id=1, is_bot=True, first_name="Bot", username="test_bot")
        return True


def make_bot() -> Bot:
    return Bot(
        TEST_TOKEN,
        session=FakeSession(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


_seq = [1000]


def _next_id() -> int:
    _seq[0] += 1
    return _seq[0]


def message_update(user_id: int, text: str | None = None, *, video: bool = False,
                   username: str | None = None) -> Update:
    return Update(
        update_id=_next_id(),
        message=Message(
            message_id=_next_id(),
            date=datetime.datetime.now(),
            chat=Chat(id=user_id, type="private"),
            from_user=User(id=user_id, is_bot=False, first_name="X", username=username),
            text=text,
            video=Video(file_id="FILE_ID", file_unique_id="u", width=1, height=1, duration=1)
            if video
            else None,
        ),
    )


def callback_update(user_id: int, data: str) -> Update:
    return Update(
        update_id=_next_id(),
        callback_query=CallbackQuery(
            id=str(_next_id()),
            from_user=User(id=user_id, is_bot=False, first_name="X"),
            chat_instance="ci",
            data=data,
            message=Message(
                message_id=_next_id(),
                date=datetime.datetime.now(),
                chat=Chat(id=user_id, type="private"),
                text="panel",
            ),
        ),
    )


def last(index: int = -1) -> tuple[str, str, list[str], str]:
    return SENT[index] if SENT else ("", "", [], "")


def last_markup(index: int = -1) -> str:
    """Oxirgi xabardagi klaviatura turi: ReplyKeyboardMarkup / InlineKeyboardMarkup /
    ReplyKeyboardRemove / '' (klaviatura yo'q)."""
    return last(index)[3]


def last_text(index: int = -1) -> str:
    return last(index)[1]


def last_buttons(index: int = -1) -> list[str]:
    return last(index)[2]


def methods_since(marker: int) -> list[str]:
    return [row[0] for row in SENT[marker:]]


def mark() -> int:
    return len(SENT)


# =========================
# Natijalarni sanash
# =========================

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"   PASS  {name}")
    else:
        print(f"   FAIL  {name}  -> {detail}")
        FAILURES.append(name)


def report() -> None:
    print()
    if FAILURES:
        print(f"XATO: {len(FAILURES)} ta test yiqildi: {FAILURES}")
        sys.exit(1)
    print("HAMMA TEST O'TDI")
