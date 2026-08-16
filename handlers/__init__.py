from aiogram import Dispatcher

from handlers import admin, auth, callbacks, user


def register_routers(dp: Dispatcher) -> None:
    """Routerlarni dispatcherga ulaydi.

    TARTIB MUHIM:
      1. auth      — `/admin` hamma uchun ochiq (parol bilan kirish)
      2. callbacks — panel tugmalari (IsAdmin bilan himoyalangan)
      3. admin     — admin buyruqlari va FSM (IsAdmin)
      4. user      — oxirida, chunki "har qanday matn = kino kodi"
                     handleri qolgan hamma narsani yutib yuboradi
    """
    dp.include_router(auth.router)
    dp.include_router(callbacks.router)
    dp.include_router(admin.router)
    dp.include_router(user.router)
