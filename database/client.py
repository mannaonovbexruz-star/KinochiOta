import logging
from functools import lru_cache

from supabase import Client, create_client

import config

logger = logging.getLogger(__name__)


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
