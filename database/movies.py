"""`movies` jadvali bilan ishlash (repository qatlami).

supabase-py SINXRON kutubxona — uning `.execute()` chaqiruvi HTTP so'rov
yuborib, javob kelguncha threadni bloklaydi. Aiogram esa asyncio ustida
ishlaydi, shuning uchun har bir DB chaqiruvi `asyncio.to_thread()` ichida
alohida threadda bajariladi. Aks holda bitta sekin so'rov butun botni
(barcha foydalanuvchilar uchun) muzlatib qo'yadi.
"""

import asyncio
import logging
from typing import Any

import config
from database.client import get_client, with_retry

logger = logging.getLogger(__name__)

Movie = dict[str, Any]


class MovieAlreadyExistsError(Exception):
    """Bunday movie_code bazada allaqachon bor."""


def _table():
    return get_client().table(config.MOVIES_TABLE)


# =========================
# READ
# =========================


def _get_movie_by_code_sync(movie_code: str) -> Movie | None:
    response = (
        _table()
        .select("*")
        .eq("movie_code", movie_code)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


async def get_movie_by_code(movie_code: str) -> Movie | None:
    """Kod bo'yicha kinoni qaytaradi, topilmasa None."""
    return await asyncio.to_thread(with_retry, _get_movie_by_code_sync, movie_code.strip())


def _list_movies_sync(limit: int, offset: int) -> list[Movie]:
    response = (
        _table()
        .select("*")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return response.data or []


async def list_movies(limit: int = 20, offset: int = 0) -> list[Movie]:
    """Oxirgi qo'shilgan kinolar ro'yxati (admin panel uchun)."""
    return await asyncio.to_thread(with_retry, _list_movies_sync, limit, offset)


def _count_movies_sync() -> int:
    # count="exact" + head=True: qatorlar tanasini yuklamay, faqat sonini oladi
    response = _table().select("id", count="exact").limit(1).execute()
    return response.count or 0


async def count_movies() -> int:
    """Bazadagi kinolar umumiy soni."""
    return await asyncio.to_thread(with_retry, _count_movies_sync)


# =========================
# WRITE
# =========================


def _add_movie_sync(movie_code: str, file_id: str, title: str) -> Movie:
    payload = {"movie_code": movie_code, "file_id": file_id, "title": title}
    try:
        response = _table().insert(payload).execute()
    except Exception as exc:  # noqa: BLE001
        # Postgres unique violation kodi 23505 — movie_code takrorlangan
        message = str(exc)
        if "23505" in message or "duplicate key" in message.lower():
            raise MovieAlreadyExistsError(movie_code) from exc
        raise
    return (response.data or [payload])[0]


async def add_movie(movie_code: str, file_id: str, title: str) -> Movie:
    """Yangi kino qo'shadi.

    Raises:
        MovieAlreadyExistsError: bunday movie_code allaqachon mavjud.
    """
    return await asyncio.to_thread(
        _add_movie_sync, movie_code.strip(), file_id, title.strip()
    )


def _delete_movie_sync(movie_code: str) -> bool:
    response = _table().delete().eq("movie_code", movie_code).execute()
    return bool(response.data)


async def delete_movie(movie_code: str) -> bool:
    """Kinoni o'chiradi. O'chirilgan bo'lsa True, topilmasa False."""
    return await asyncio.to_thread(with_retry, _delete_movie_sync, movie_code.strip())
