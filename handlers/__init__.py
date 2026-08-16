from aiogram import Dispatcher

from handlers import admin, user


def register_routers(dp: Dispatcher) -> None:
    """Routerlarni dispatcherga ulaydi.

    TARTIB MUHIM: admin birinchi bo'ladi, chunki user routeridagi
    "har qanday matn = kino kodi" handleri admin FSM javoblarini
    yutib yuborishi mumkin edi.
    """
    dp.include_router(admin.router)
    dp.include_router(user.router)
