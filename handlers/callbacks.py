"""Admin panel tugmalari (inline klaviatura bosishlari).

Router butunligicha IsAdmin bilan himoyalangan — begona odam eski
tugmani bossa, bu yerga umuman tushmaydi.

Har bir handler avval `callback.answer()` chaqiradi: Telegram tugmada
aylanayotgan indikatorni shu javob bilan to'xtatadi.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

import config
from database import admins as admins_db
from database import channels as channels_db
from database import movies as movies_db
from handlers.filters import IsAdmin
from handlers.keyboards import (
    CB_ADD,
    CB_ADMINS,
    CB_BACK,
    CB_CHANNEL_ADD,
    CB_CHANNEL_CLEAR,
    CB_CHANNEL_REMOVE_PREFIX,
    CB_CHANNELS,
    CB_DELETE,
    CB_LIST,
    CB_REMOVE_PREFIX,
    CB_STATS,
    admins_menu,
    back_menu,
    channels_menu,
)
from handlers.panel import render_panel
from handlers.states import AddChannel, DeleteMovie

logger = logging.getLogger(__name__)

router = Router(name="callbacks")
router.callback_query.filter(IsAdmin())


async def _edit(callback: CallbackQuery, text: str, markup=None) -> None:
    """Xabarni yangilaydi. Matn o'zgarmagan bo'lsa Telegram xato beradi —
    bu holat foydalanuvchi uchun muhim emas, shuning uchun yutamiz."""
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except Exception as exc:  # noqa: BLE001
        logger.debug("edit_text o'tmadi: %s", exc)


@router.callback_query(F.data == CB_BACK)
async def cb_back(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    text, markup = await render_panel(callback.from_user.id)
    await _edit(callback, text, markup)


@router.callback_query(F.data == CB_ADD)
async def cb_add(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await _edit(
        callback,
        "🎬 <b>Kino qo'shish</b>\n\nVideoni shu chatga yuboring — "
        "keyin kod va nom so'rayman.",
        back_menu(),
    )


@router.callback_query(F.data == CB_DELETE)
async def cb_delete(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(DeleteMovie.waiting_for_code)
    await _edit(
        callback,
        "🗑 <b>Kino o'chirish</b>\n\nO'chiriladigan kino <b>kodini</b> yuboring.",
        back_menu(),
    )


@router.callback_query(F.data == CB_STATS)
async def cb_stats(callback: CallbackQuery) -> None:
    await callback.answer()
    total = await movies_db.count_movies()
    await _edit(
        callback,
        f"📊 <b>Statistika</b>\n\nBazadagi kinolar soni: <b>{total}</b> ta",
        back_menu(),
    )


@router.callback_query(F.data == CB_LIST)
async def cb_list(callback: CallbackQuery) -> None:
    await callback.answer()
    items = await movies_db.list_movies(limit=20)
    if not items:
        body = "📭 Baza hozircha bo'sh."
    else:
        rows = "\n".join(f"<code>{m['movie_code']}</code> — {m['title']}" for m in items)
        body = f"📋 <b>Oxirgi 20 ta kino:</b>\n\n{rows}"
    await _edit(callback, body, back_menu())


# =========================
# ADMINLAR (faqat egasi)
# =========================


@router.callback_query(F.data == CB_ADMINS)
async def cb_admins(callback: CallbackQuery) -> None:
    if not config.is_owner(callback.from_user.id):
        await callback.answer("❌ Bu bo'lim faqat egasi uchun.", show_alert=True)
        return

    await callback.answer()
    items = await admins_db.list_admins()
    if not items:
        body = (
            "👥 <b>Adminlar</b>\n\n"
            "Hozircha parol bilan kirgan admin yo'q.\n"
            "Yangi odam <code>/admin parol</code> yozsa shu yerda paydo bo'ladi."
        )
    else:
        rows = "\n".join(
            f"• <code>{a['user_id']}</code>" + (f" — @{a['username']}" if a.get("username") else "")
            for a in items
        )
        body = f"👥 <b>Adminlar ({len(items)} ta):</b>\n\n{rows}"

    await _edit(callback, body, admins_menu(items))


# =========================
# MAJBURIY OBUNA KANALLARI (faqat egasi)
# =========================


async def _render_channels(callback: CallbackQuery) -> None:
    items = await channels_db.list_channels(force=True)
    if not items:
        body = (
            "📢 <b>Majburiy obuna</b>\n\n"
            "Hozircha kanal yo'q — majburiy obuna <b>o'chiq</b>, "
            "hamma botdan erkin foydalanadi."
        )
    else:
        rows = "\n".join(
            f"• <code>{c['chat_id']}</code>" + (f" — {c['title']}" if c.get("title") else "")
            for c in items
        )
        body = f"📢 <b>Majburiy obuna ({len(items)} ta):</b>\n\n{rows}"

    await _edit(callback, body, channels_menu(items))


@router.callback_query(F.data == CB_CHANNELS)
async def cb_channels(callback: CallbackQuery) -> None:
    if not config.is_owner(callback.from_user.id):
        await callback.answer("❌ Bu bo'lim faqat egasi uchun.", show_alert=True)
        return
    await callback.answer()
    await _render_channels(callback)


@router.callback_query(F.data == CB_CHANNEL_ADD)
async def cb_channel_add(callback: CallbackQuery, state: FSMContext) -> None:
    if not config.is_owner(callback.from_user.id):
        await callback.answer("❌ Bu amal faqat egasi uchun.", show_alert=True)
        return

    await callback.answer()
    await state.set_state(AddChannel.waiting_for_channel)
    await _edit(
        callback,
        "➕ <b>Kanal qo'shish</b>\n\n"
        "Kanal manzilini yuboring: <code>@KanalNomi</code>\n"
        "yoki ID: <code>-1001234567890</code>\n\n"
        "⚠️ Bot o'sha kanalda <b>admin</b> bo'lishi shart, aks holda "
        "obunani tekshira olmaydi.\n\n"
        "❌ Bekor qilish: /cancel",
        back_menu(),
    )


@router.callback_query(F.data.startswith(CB_CHANNEL_REMOVE_PREFIX))
async def cb_channel_remove(callback: CallbackQuery) -> None:
    if not config.is_owner(callback.from_user.id):
        await callback.answer("❌ Bu amal faqat egasi uchun.", show_alert=True)
        return

    chat_id = callback.data[len(CB_CHANNEL_REMOVE_PREFIX):]
    removed = await channels_db.remove_channel(chat_id)
    await callback.answer("🗑 O'chirildi" if removed else "🔍 Topilmadi")
    logger.info("Kanal o'chirildi: %s (egasi: %s)", chat_id, callback.from_user.id)
    await _render_channels(callback)


@router.callback_query(F.data == CB_CHANNEL_CLEAR)
async def cb_channel_clear(callback: CallbackQuery) -> None:
    if not config.is_owner(callback.from_user.id):
        await callback.answer("❌ Bu amal faqat egasi uchun.", show_alert=True)
        return

    count = await channels_db.clear_channels()
    await callback.answer(f"⏮️ {count} ta kanal o'chirildi — majburiy obuna o'chdi", show_alert=True)
    logger.info("Majburiy obuna o'chirildi (egasi: %s)", callback.from_user.id)
    await _render_channels(callback)


@router.callback_query(F.data.startswith(CB_REMOVE_PREFIX))
async def cb_remove_admin(callback: CallbackQuery) -> None:
    if not config.is_owner(callback.from_user.id):
        await callback.answer("❌ Bu amal faqat egasi uchun.", show_alert=True)
        return

    raw = callback.data[len(CB_REMOVE_PREFIX):]
    if not raw.isdigit():
        await callback.answer("⚠️ Noto'g'ri ma'lumot.", show_alert=True)
        return

    target_id = int(raw)

    # Egasi ADMIN_ID env'da — bazadan o'chirib bo'lmaydi, urinishni ham to'xtatamiz
    if config.is_owner(target_id):
        await callback.answer(
            "⚠️ Egasini o'chirib bo'lmaydi (u ADMIN_ID env'da).", show_alert=True
        )
        return

    removed = await admins_db.remove_admin(target_id)
    await callback.answer("🗑 O'chirildi" if removed else "🔍 Topilmadi")
    logger.info("Admin o'chirildi: %s (egasi: %s)", target_id, callback.from_user.id)

    items = await admins_db.list_admins()
    body = (
        f"👥 <b>Adminlar ({len(items)} ta):</b>\n\n"
        + ("\n".join(f"• <code>{a['user_id']}</code>" for a in items) or "Ro'yxat bo'sh.")
    )
    await _edit(callback, body, admins_menu(items))
