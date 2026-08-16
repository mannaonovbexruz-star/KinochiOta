"""Majburiy obuna: tekshiruv, to'siq (middleware) va "✅ Tekshirish" tugmasi.

Tekshiruv middleware ko'rinishida faqat USER routeriga ulanadi — admin
handlerlariga umuman tegmaydi.
"""

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    TelegramObject,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import admins as admins_db
from database import channels as channels_db

logger = logging.getLogger(__name__)

router = Router(name="subscription")

CB_CHECK = "sub:check"


async def unsubscribed_channels(bot, user_id: int) -> list[dict]:
    """Foydalanuvchi obuna BO'LMAGAN kanallar ro'yxati.

    ⚠️ Kanalni tekshirib bo'lmasa (bot u yerda admin emas, kanal o'chirilgan
    va h.k.) — o'sha kanal HISOBGA OLINMAYDI. Aks holda bitta noto'g'ri
    sozlamadan butun bot ishlamay qolardi.
    """
    channels = await channels_db.list_channels()
    if not channels:
        return []

    missing = []
    for channel in channels:
        chat_id = channel["chat_id"]
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Obunani tekshirib bo'lmadi (%s): %s", chat_id, exc)
            continue

        if member.status in ("left", "kicked"):
            missing.append(channel)

    return missing


def subscription_keyboard(channels: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for index, channel in enumerate(channels, start=1):
        chat_id = channel["chat_id"]
        url = channel.get("url") or (
            f"https://t.me/{chat_id.lstrip('@')}" if chat_id.startswith("@") else None
        )
        title = channel.get("title") or chat_id
        if url:
            builder.row(InlineKeyboardButton(text=f"📢 {title}", url=url))
        else:
            builder.row(InlineKeyboardButton(text=f"📢 {title}", callback_data="sub:noop"))

    builder.row(InlineKeyboardButton(text="✅ Tekshirish", callback_data=CB_CHECK))
    return builder.as_markup()


def subscription_text(count: int) -> str:
    return (
        "❌ <b>Botdan foydalanish uchun avval kanallarga obuna bo'ling</b>\n\n"
        f"📢 Quyidagi {count} ta kanalga a'zo bo'ling, "
        "so'ng <b>✅ Tekshirish</b> tugmasini bosing."
    )


class SubscriptionMiddleware(BaseMiddleware):
    """Obuna bo'lmagan foydalanuvchini handlergacha o'tkazmaydi."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        bot = data["bot"]

        if user is None:
            return await handler(event, data)

        # Adminlar tekshiruvdan ozod
        if await admins_db.is_admin(user.id):
            return await handler(event, data)

        missing = await unsubscribed_channels(bot, user.id)
        if not missing:
            return await handler(event, data)

        markup = subscription_keyboard(missing)
        text = subscription_text(len(missing))

        if isinstance(event, Message):
            await event.answer(text, reply_markup=markup)
        elif isinstance(event, CallbackQuery):
            await event.answer("❌ Avval kanallarga obuna bo'ling.", show_alert=True)

        return None  # handler CHAQIRILMAYDI


@router.callback_query(F.data == CB_CHECK)
async def cb_check(callback: CallbackQuery) -> None:
    """"✅ Tekshirish" tugmasi. Bu router middleware'siz — aks holda
    obuna bo'lmagan odam o'z holatini tekshira olmasdi."""
    missing = await unsubscribed_channels(callback.bot, callback.from_user.id)

    if missing:
        await callback.answer("❌ Hali hamma kanalga obuna bo'lmagansiz.", show_alert=True)
        try:
            await callback.message.edit_text(
                subscription_text(len(missing)),
                reply_markup=subscription_keyboard(missing),
            )
        except Exception as exc:  # noqa: BLE001 - matn o'zgarmasa Telegram xato beradi
            logger.debug("edit_text o'tmadi: %s", exc)
        return

    await callback.answer("✅ Rahmat!")
    try:
        await callback.message.edit_text(
            "✅ <b>Rahmat, obuna tasdiqlandi!</b>\n\n"
            "🔢 Endi kino <b>kodini</b> yuboring."
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("edit_text o'tmadi: %s", exc)


@router.callback_query(F.data == "sub:noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer("Bu kanalga havola sozlanmagan.", show_alert=True)
