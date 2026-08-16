from aiogram import Dispatcher

from handlers import admin, auth, callbacks, subscription, user
from handlers.subscription import SubscriptionMiddleware


def register_routers(dp: Dispatcher) -> None:
    """Routerlarni dispatcherga ulaydi.

    TARTIB MUHIM:
      1. auth         — `/admin` hamma uchun ochiq (parol bilan kirish)
      2. callbacks    — panel tugmalari (IsAdmin bilan himoyalangan)
      3. admin        — admin buyruqlari va FSM (IsAdmin)
      4. subscription — "✅ Tekshirish" tugmasi (middleware'siz bo'lishi SHART,
                        aks holda obuna bo'lmagan odam o'zini tekshira olmasdi)
      5. user         — oxirida, chunki "har qanday matn = kino kodi"
                        handleri qolgan hamma narsani yutib yuboradi
    """
    dp.include_router(auth.router)
    dp.include_router(callbacks.router)
    dp.include_router(admin.router)
    dp.include_router(subscription.router)

    # Majburiy obuna faqat oddiy foydalanuvchilarga tegishli —
    # shuning uchun middleware faqat shu routerga ulanadi.
    user.router.message.middleware(SubscriptionMiddleware())
    user.router.callback_query.middleware(SubscriptionMiddleware())
    dp.include_router(user.router)
