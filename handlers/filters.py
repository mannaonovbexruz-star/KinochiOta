from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message, TelegramObject

import config
from database import admins as admins_db


def _user_id(event: TelegramObject) -> int | None:
    """Message ham, CallbackQuery ham `from_user` ga ega."""
    user = getattr(event, "from_user", None)
    return user.id if user else None


class IsOwner(BaseFilter):
    """Faqat EGASI (ADMIN_ID env). Bazadan o'zgartirib bo'lmaydi."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user_id = _user_id(event)
        return user_id is not None and config.is_owner(user_id)


class IsAdmin(BaseFilter):
    """Egasi YOKI `admins` jadvalidagi admin.

    aiogram 3 da filtr — `__call__` metodli klass. Routerga
    `router.message.filter(IsAdmin())` deb biriktirilsa, o'sha routerdagi
    barcha handlerlar avtomatik himoyalanadi.
    """

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user_id = _user_id(event)
        if user_id is None:
            return False
        if config.is_owner(user_id):
            return True
        return user_id in await admins_db.get_admin_ids()
