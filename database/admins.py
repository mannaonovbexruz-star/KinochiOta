"""`admins` jadvali bilan ishlash (parol orqali kirgan adminlar).

⚠️ EGASI bu yerda saqlanmaydi — u `config.OWNER_IDS` (ADMIN_ID env) da.

KESH HAQIDA: `IsAdmin` filtri botga kelgan HAR BIR xabarda ishlaydi.
Har safar Supabase'ga so'rov yuborilsa, oddiy foydalanuvchi kino kodi
yozganda ham ortiqcha kechikish paydo bo'lardi. Shuning uchun adminlar
ro'yxati 60 soniya xotirada saqlanadi va admin qo'shilganda/o'chirilganda
darrov yangilanadi.
"""

import asyncio
import logging
import time
from typing import Any

import config
from database.client import get_client

logger = logging.getLogger(__name__)

Admin = dict[str, Any]

TABLE = "admins"
CACHE_TTL = 60.0  # soniya

_cached_ids: set[int] = set()
_cached_at: float = 0.0
_cache_loaded: bool = False


def _table():
    return get_client().table(TABLE)


def ping() -> bool:
    """Jadval mavjudligini tekshiradi (startupda ogohlantirish uchun)."""
    try:
        _table().select("user_id").limit(1).execute()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("`%s` jadvaliga ulanib bo'lmadi: %s", TABLE, exc)
        return False


def invalidate_cache() -> None:
    """Keshni bekor qiladi — keyingi so'rovda bazadan qayta o'qiladi."""
    global _cached_at
    _cached_at = 0.0


# =========================
# O'QISH
# =========================


def _fetch_admin_ids_sync() -> set[int]:
    response = _table().select("user_id").execute()
    return {int(row["user_id"]) for row in (response.data or [])}


async def get_admin_ids(force: bool = False) -> set[int]:
    """Bazadagi adminlar user_id to'plami (keshlangan).

    Baza javob bermasa — oxirgi ma'lum ro'yxat qaytariladi. Bu holda ham
    egasi (OWNER_IDS) baribir ishlayveradi, chunki u env'dan olinadi.
    """
    global _cached_ids, _cached_at, _cache_loaded

    if not force and _cache_loaded and (time.monotonic() - _cached_at) < CACHE_TTL:
        return _cached_ids

    try:
        _cached_ids = await asyncio.to_thread(_fetch_admin_ids_sync)
        _cached_at = time.monotonic()
        _cache_loaded = True
    except Exception as exc:  # noqa: BLE001 - baza tushsa bot ishlashda davom etsin
        logger.error("Adminlar ro'yxatini o'qib bo'lmadi: %s", exc)

    return _cached_ids


def _list_admins_sync() -> list[Admin]:
    response = _table().select("*").order("added_at", desc=True).execute()
    return response.data or []


async def list_admins() -> list[Admin]:
    """To'liq ro'yxat (username, qo'shilgan sana bilan) — panel uchun."""
    return await asyncio.to_thread(_list_admins_sync)


async def is_admin(user_id: int) -> bool:
    """Egasi YOKI bazadagi admin."""
    if config.is_owner(user_id):
        return True
    return user_id in await get_admin_ids()


# =========================
# YOZISH
# =========================


def _add_admin_sync(user_id: int, username: str | None) -> Admin:
    payload = {"user_id": user_id, "username": username}
    # upsert: allaqachon admin bo'lsa xato bermaydi, username yangilanadi
    response = _table().upsert(payload, on_conflict="user_id").execute()
    return (response.data or [payload])[0]


async def add_admin(user_id: int, username: str | None = None) -> Admin:
    """Adminlar ro'yxatiga qo'shadi va keshni darrov yangilaydi."""
    result = await asyncio.to_thread(_add_admin_sync, user_id, username)
    invalidate_cache()
    return result


def _remove_admin_sync(user_id: int) -> bool:
    response = _table().delete().eq("user_id", user_id).execute()
    return bool(response.data)


async def remove_admin(user_id: int) -> bool:
    """Adminlikdan chiqaradi. Egasiga ta'sir qilmaydi (u bazada yo'q)."""
    result = await asyncio.to_thread(_remove_admin_sync, user_id)
    invalidate_cache()
    return result
