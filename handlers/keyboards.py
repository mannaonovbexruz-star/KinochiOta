"""Inline klaviaturalar.

Callback data formati: `adm:<amal>` yoki `adm:rm:<user_id>`.
Telegram callback_data uchun 64 baytlik chegara bor — shuning uchun
qisqa prefikslar ishlatilgan.
"""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# =========================
# DOIMIY (REPLY) KLAVIATURA
# =========================
# Yozish maydoni ostida turadigan tugmalar. Inline tugmalardan farqi:
# bosilganda callback emas, TUGMA MATNI oddiy xabar sifatida yuboriladi.
# Shuning uchun har bir matnga alohida handler kerak (handlers/admin.py).

BTN_ADD = "🎬 Kino qo'shish"
BTN_DELETE = "🗑 Kino o'chirish"
BTN_LIST = "📋 Ro'yxat"
BTN_STATS = "📊 Statistika"


def admin_reply_keyboard() -> ReplyKeyboardMarkup:
    """Adminning doimiy klaviaturasi."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ADD), KeyboardButton(text=BTN_DELETE)],
            [KeyboardButton(text=BTN_LIST), KeyboardButton(text=BTN_STATS)],
        ],
        resize_keyboard=True,   # tugmalar balandligi ixcham bo'ladi
        is_persistent=True,     # foydalanuvchi yopsa ham qaytadi
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    """Adminlikdan chiqarilgan odamda eski tugmalar qolib ketmasin."""
    return ReplyKeyboardRemove()

CB_ADD = "adm:add"
CB_LIST = "adm:list"
CB_STATS = "adm:stats"
CB_DELETE = "adm:del"
CB_ADMINS = "adm:admins"
CB_CHANNELS = "adm:channels"
CB_BACK = "adm:back"
CB_REMOVE_PREFIX = "adm:rm:"
CB_ADMIN_ADD = "adm:addadmin"

# Kanal boshqaruvi
CB_CHANNEL_ADD = "ch:add"
CB_CHANNEL_REMOVE_PREFIX = "ch:rm:"
CB_CHANNEL_CLEAR = "ch:clear"


def admin_menu(is_owner: bool) -> InlineKeyboardMarkup:
    """Asosiy panel. 'Adminlar' tugmasi faqat egasiga ko'rinadi."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎬 Kino qo'shish", callback_data=CB_ADD),
        InlineKeyboardButton(text="🗑 Kino o'chirish", callback_data=CB_DELETE),
    )
    builder.row(
        InlineKeyboardButton(text="📋 Ro'yxat", callback_data=CB_LIST),
        InlineKeyboardButton(text="📊 Statistika", callback_data=CB_STATS),
    )
    if is_owner:
        builder.row(
            InlineKeyboardButton(text="👥 Adminlar", callback_data=CB_ADMINS),
            InlineKeyboardButton(text="📢 Kanallar", callback_data=CB_CHANNELS),
        )
    return builder.as_markup()


def channels_menu(channels: list[dict]) -> InlineKeyboardMarkup:
    """Majburiy obuna kanallarini boshqarish (faqat egasi)."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data=CB_CHANNEL_ADD))

    for channel in channels:
        chat_id = channel["chat_id"]
        builder.row(
            InlineKeyboardButton(
                text=f"❌ {chat_id} ni o'chirish",
                callback_data=f"{CB_CHANNEL_REMOVE_PREFIX}{chat_id}",
            )
        )

    if channels:
        builder.row(
            InlineKeyboardButton(
                text="⏮️ Obunani butunlay o'chirish", callback_data=CB_CHANNEL_CLEAR
            )
        )

    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data=CB_BACK))
    return builder.as_markup()


def back_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data=CB_BACK))
    return builder.as_markup()


def admins_menu(admins: list[dict]) -> InlineKeyboardMarkup:
    """➕ qo'shish + har bir admin uchun o'chirish tugmasi + orqaga."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Admin qo'shish", callback_data=CB_ADMIN_ADD))
    for item in admins:
        user_id = item["user_id"]
        label = item.get("username") or user_id
        builder.row(
            InlineKeyboardButton(
                text=f"❌ {label} ni o'chirish",
                callback_data=f"{CB_REMOVE_PREFIX}{user_id}",
            )
        )
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data=CB_BACK))
    return builder.as_markup()
