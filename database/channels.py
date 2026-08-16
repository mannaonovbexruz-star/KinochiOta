"""Majburiy obuna kanallari (`channels` jadvali).

Jadval bo'sh bo'lsa — majburiy obuna o'chiq.

Kesh: ro'yxat har bir xabarda kerak bo'ladi, shuning uchun 60 soniya
xotirada saqlanadi va o'zgartirilganda darrov yangilanadi.
"""

import asyncio
import logging
import time
from typing import Any

from database.client import get_client, with_retry

logger = logging.getLogger(__name__)

Channel = dict[str, Any]

TABLE = "channels"
CACHE_TTL = 60.0

_cached: list[Channel] = []
_cached_at: float = 0.0
_cache_loaded: bool = False


def _table():
    return get_client().table(TABLE)


def invalidate_cache() -> None:
    global _cached_at
    _cached_at = 0.0


def ping() -> bool:
    try:
        with_retry(lambda: _table().select("chat_id").limit(1).execute())
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("`%s` jadvaliga ulanib bo'lmadi: %s", TABLE, exc)
        return False


# =========================
# O'QISH
# =========================


def _list_sync() -> list[Channel]:
    response = _table().select("*").order("added_at").execute()
    return response.data or []


async def list_channels(force: bool = False) -> list[Channel]:
    """Kanallar ro'yxati (keshlangan).

    Baza javob bermasa oxirgi ma'lum ro'yxat qaytariladi — obuna tekshiruvi
    tufayli butun bot to'xtab qolmasin.
    """
    global _cached, _cached_at, _cache_loaded

    if not force and _cache_loaded and (time.monotonic() - _cached_at) < CACHE_TTL:
        return _cached

    try:
        _cached = await asyncio.to_thread(with_retry, _list_sync)
        _cached_at = time.monotonic()
        _cache_loaded = True
    except Exception as exc:  # noqa: BLE001
        logger.error("Kanallar ro'yxatini o'qib bo'lmadi: %s", exc)

    return _cached


# =========================
# YOZISH
# =========================


def _add_sync(chat_id: str, title: str | None, url: str | None) -> Channel:
    payload = {"chat_id": chat_id, "title": title, "url": url}
    response = _table().upsert(payload, on_conflict="chat_id").execute()
    return (response.data or [payload])[0]


async def add_channel(chat_id: str, title: str | None = None, url: str | None = None) -> Channel:
    result = await asyncio.to_thread(with_retry, _add_sync, chat_id.strip(), title, url)
    invalidate_cache()
    return result


def _remove_sync(chat_id: str) -> bool:
    response = _table().delete().eq("chat_id", chat_id).execute()
    return bool(response.data)


async def remove_channel(chat_id: str) -> bool:
    result = await asyncio.to_thread(with_retry, _remove_sync, chat_id.strip())
    invalidate_cache()
    return result


def _clear_sync() -> int:
    rows = _table().select("id").execute().data or []
    if rows:
        # `neq id -1` — hamma qatorga mos keladi (Supabase filtrsiz delete'ni rad etadi)
        _table().delete().neq("id", -1).execute()
    return len(rows)


async def clear_channels() -> int:
    """Barcha kanallarni o'chiradi — majburiy obuna butunlay o'chadi."""
    result = await asyncio.to_thread(with_retry, _clear_sync)
    invalidate_cache()
    return result
