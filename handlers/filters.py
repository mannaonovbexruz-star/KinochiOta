from aiogram.filters import BaseFilter
from aiogram.types import Message

import config


class IsAdmin(BaseFilter):
    """Xabar ADMIN_ID ro'yxatidagi foydalanuvchidan kelganini tekshiradi.

    aiogram 3 da filtr — bu `__call__` metodli oddiy klass. Router'ga
    `router.message.filter(IsAdmin())` deb biriktirsak, o'sha routerdagi
    BARCHA handlerlar avtomatik himoyalanadi (har biriga alohida yozish shart emas).
    """

    async def __call__(self, message: Message) -> bool:
        return message.from_user is not None and config.is_admin(message.from_user.id)
