import logging
import time
from functools import lru_cache
from typing import Any, Callable, TypeVar

import httpx
from supabase import Client, create_client

import config

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Supabase serveri har javobdan keyin HTTP/2 GOAWAY yuboradi. httpx o'sha
# yopilgan ulanishni qayta ishlatmoqchi bo'lganda RemoteProtocolError chiqadi
# — amalda har ikkinchi so'rov yiqiladi. Keyingi urinishda httpx yangi ulanish
# ochadi va so'rov o'tadi, shuning uchun qisqa qayta urinish yetarli.
#
# supabase 2.31.0 da httpx sozlamalarini (http2=False) uzatib bo'lmaydi,
# shu sabab tuzatish shu qatlamda.
RETRY_EXCEPTIONS = (
    httpx.RemoteProtocolError,
    httpx.ConnectError,
    httpx.ReadError,
    httpx.WriteError,
    httpx.ReadTimeout,
)

MAX_ATTEMPTS = 3
RETRY_DELAY = 0.2  # soniya


def with_retry(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Ulanish uzilishida qayta uriniladi. Boshqa xatolar darrov ko'tariladi."""
    last_exc: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return func(*args, **kwargs)
        except RETRY_EXCEPTIONS as exc:
            last_exc = exc
            # Bu deyarli har so'rovda uchraydi va qayta urinish uni hal qiladi —
            # shuning uchun DEBUG. Loglar toshib ketmasin.
            logger.debug(
                "Supabase ulanishi uzildi (%s/%s): %s", attempt, MAX_ATTEMPTS, exc
            )
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_DELAY)

    # Bu yerga yetdik — hamma urinish tugadi, endi bu haqiqiy nosozlik
    logger.warning("Supabase %s urinishdan keyin ham javob bermadi: %s", MAX_ATTEMPTS, last_exc)
    assert last_exc is not None
    raise last_exc


@lru_cache(maxsize=1)
def get_client() -> Client:
    """Supabase klientini qaytaradi (singleton).

    lru_cache tufayli klient faqat bir marta yaratiladi — har bir so'rovda
    yangi HTTP sessiya ochilmaydi.
    """
    logger.info("Supabase klienti yaratilmoqda: %s", config.SUPABASE_URL)
    return create_client(config.SUPABASE_URL, config.SUPABASE_KEY)


def ping() -> bool:
    """Bazaga ulanishni tekshiradi (startupda healthcheck uchun)."""
    try:
        get_client().table(config.MOVIES_TABLE).select("id").limit(1).execute()
        return True
    except Exception as exc:  # noqa: BLE001 - startupda har qanday xatoni ko'rsatamiz
        logger.error("Supabase ulanishida xato: %s", exc)
        return False
