import logging

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import config
from database import channels as channels_db
from database import movies as movies_db
from database.movies import MovieAlreadyExistsError
from handlers.filters import IsAdmin
from handlers.keyboards import BTN_ADD, BTN_DELETE, BTN_LIST, BTN_STATS
from handlers.states import AddChannel, AddMovie, DeleteMovie

logger = logging.getLogger(__name__)

router = Router(name="admin")

# Butun routerni admin bilan cheklaymiz — oddiy foydalanuvchi bu handlerlarga
# umuman tushmaydi va xabari keyingi routerga (user) o'tib ketadi.
router.message.filter(IsAdmin())

MAX_CODE_LENGTH = 32
MAX_TITLE_LENGTH = 200


# =========================
# UMUMIY BUYRUQLAR
# =========================


@router.message(StateFilter("*"), Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Istalgan FSM jarayonini bekor qiladi."""
    if await state.get_state() is None:
        await message.answer("ℹ️ Hozir bekor qiladigan jarayon yo'q.")
        return

    await state.clear()
    await message.answer("❌ Bekor qilindi.")


# =========================
# DOIMIY KLAVIATURA TUGMALARI
# =========================
# MUHIM: bu handlerlar FSM handlerlaridan OLDIN turishi kerak. aiogram
# handlerlarni ro'yxatga olish tartibida tekshiradi — pastda tursa, kino
# qo'shish jarayonida bosilgan tugma "kino kodi" deb qabul qilinardi.
#
# StateFilter("*") + state.clear(): tugma qaysi bosqichda bosilsa ham
# joriy jarayonni bekor qilib, o'z amalini bajaradi.


@router.message(StateFilter("*"), F.text == BTN_ADD)
async def btn_add(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "🎬 <b>Kino qo'shish</b>\n\nVideoni shu chatga yuboring — "
        "keyin kod va nom so'rayman."
    )


@router.message(StateFilter("*"), F.text == BTN_STATS)
async def btn_stats(message: Message, state: FSMContext) -> None:
    await state.clear()
    total = await movies_db.count_movies()
    await message.answer(f"📊 Bazadagi kinolar soni: <b>{total}</b> ta")


@router.message(StateFilter("*"), F.text == BTN_LIST)
async def btn_list(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _send_movie_list(message)


@router.message(StateFilter("*"), F.text == BTN_DELETE)
async def btn_delete(message: Message, state: FSMContext) -> None:
    await state.set_state(DeleteMovie.waiting_for_code)
    await message.answer(
        "🗑 O'chiriladigan kino <b>kodini</b> yuboring:\n❌ Bekor qilish: /cancel"
    )


# ℹ️ `/admin` bu yerda EMAS — u handlers/auth.py da, chunki hali admin
# bo'lmagan odam ham parol bilan kira olishi kerak.


@router.message(Command("help_admin"))
async def cmd_help_admin(message: Message) -> None:
    await message.answer(
        "🛠 <b>Admin buyruqlari</b>\n\n"
        "/admin — panelni ochish\n"
        "🎬 Kino qo'shish: videoni shu chatga tashlang\n"
        "📋 /list — oxirgi qo'shilgan kinolar\n"
        "📊 /stats — statistika\n"
        "🗑 /delete — kino o'chirish\n"
        "❌ /cancel — jarayonni bekor qilish"
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    total = await movies_db.count_movies()
    await message.answer(f"📊 Bazadagi kinolar soni: <b>{total}</b> ta")


async def _send_movie_list(message: Message) -> None:
    """`/list` va 📋 tugmasi uchun umumiy."""
    items = await movies_db.list_movies(limit=20)
    if not items:
        await message.answer("📭 Baza hozircha bo'sh.")
        return

    lines = [f"<code>{m['movie_code']}</code> — {m['title']}" for m in items]
    await message.answer("📋 <b>Oxirgi 20 ta kino:</b>\n\n" + "\n".join(lines))


@router.message(Command("list"))
async def cmd_list(message: Message) -> None:
    await _send_movie_list(message)


# =========================
# KINO QO'SHISH (FSM)
# =========================


@router.message(StateFilter(None), F.video)
async def catch_video(message: Message, state: FSMContext) -> None:
    """Admin video tashladi — file_id ni ushlab olamiz va kod so'raymiz."""
    file_id = message.video.file_id

    # FSM storage — bu vaqtinchalik "savat": jarayon tugaguncha ma'lumot
    # shu yerda turadi, tugagach state.clear() bilan tozalanadi.
    await state.update_data(file_id=file_id)
    await state.set_state(AddMovie.waiting_for_code)

    await message.answer(
        "✅ Video qabul qilindi!\n\n"
        f"<code>file_id</code>: <code>{file_id}</code>\n\n"
        "🔢 Endi shu kino uchun <b>kod</b> yuboring (masalan: <code>125</code>)\n"
        "❌ Bekor qilish: /cancel"
    )


@router.message(StateFilter(None), F.document)
async def catch_video_document(message: Message, state: FSMContext) -> None:
    """Video "document" sifatida (siqilmagan holda) yuborilgan holat."""
    mime = message.document.mime_type or ""
    if not mime.startswith("video/"):
        await message.answer("⚠️ Faqat video fayl yuboring.")
        return

    await state.update_data(file_id=message.document.file_id)
    await state.set_state(AddMovie.waiting_for_code)
    await message.answer(
        "✅ Video (document) qabul qilindi!\n\n"
        "🔢 Kino uchun <b>kod</b> yuboring (masalan: <code>125</code>)\n"
        "❌ Bekor qilish: /cancel"
    )


@router.message(AddMovie.waiting_for_code, F.text)
async def process_code(message: Message, state: FSMContext) -> None:
    code = message.text.strip()

    if len(code) > MAX_CODE_LENGTH:
        await message.answer(f"⚠️ Kod juda uzun (max {MAX_CODE_LENGTH} belgi). Qayta yuboring.")
        return

    if not code.replace("_", "").replace("-", "").isalnum():
        await message.answer(
            "⚠️ Kodda faqat harf, raqam, <code>-</code> va <code>_</code> bo'lishi mumkin.\n"
            "Qayta yuboring:"
        )
        return

    # Bazaga yozishdan oldin tekshiramiz — admin xatosini darrov ko'rsatamiz
    existing = await movies_db.get_movie_by_code(code)
    if existing:
        await message.answer(
            f"⚠️ <code>{code}</code> kodi band: <b>{existing['title']}</b>\n"
            "Boshqa kod yuboring yoki /cancel:"
        )
        return

    await state.update_data(movie_code=code)
    await state.set_state(AddMovie.waiting_for_title)
    await message.answer("🎬 Endi kino <b>nomini</b> yuboring:")


@router.message(AddMovie.waiting_for_code)
async def process_code_invalid(message: Message) -> None:
    await message.answer("⚠️ Kodni <b>matn</b> ko'rinishida yuboring (masalan: 125).")


@router.message(AddMovie.waiting_for_title, F.text)
async def process_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()

    if len(title) > MAX_TITLE_LENGTH:
        await message.answer(f"⚠️ Nom juda uzun (max {MAX_TITLE_LENGTH} belgi). Qayta yuboring.")
        return

    data = await state.get_data()
    file_id = data["file_id"]
    movie_code = data["movie_code"]

    try:
        await movies_db.add_movie(movie_code=movie_code, file_id=file_id, title=title)
    except MovieAlreadyExistsError:
        await state.clear()
        await message.answer(f"⚠️ <code>{movie_code}</code> kodi endigina band bo'ldi. Qaytadan urinib ko'ring.")
        return
    except Exception as exc:  # noqa: BLE001 - adminga aniq xabar berish uchun
        logger.exception("Kino saqlashda xato")
        await state.clear()
        await message.answer(f"❌ Bazaga saqlashda xato:\n<code>{exc}</code>")
        return

    await state.clear()
    await message.answer(
        "✅ <b>Kino saqlandi!</b>\n\n"
        f"🔢 Kod: <code>{movie_code}</code>\n"
        f"🎬 Nomi: <b>{title}</b>\n\n"
        f"Tekshirish uchun botga <code>{movie_code}</code> deb yozing."
    )


@router.message(AddMovie.waiting_for_title)
async def process_title_invalid(message: Message) -> None:
    await message.answer("⚠️ Kino nomini <b>matn</b> ko'rinishida yuboring.")


# =========================
# KANAL QO'SHISH (FSM, faqat egasi)
# =========================


@router.message(AddChannel.waiting_for_channel, F.text)
async def process_channel(message: Message, state: FSMContext) -> None:
    if not config.is_owner(message.from_user.id):
        await state.clear()
        await message.answer("❌ Bu amal faqat egasi uchun.")
        return

    chat_id = message.text.strip()
    if not (chat_id.startswith("@") or chat_id.lstrip("-").isdigit()):
        await message.answer(
            "⚠️ Noto'g'ri format. <code>@KanalNomi</code> yoki "
            "<code>-1001234567890</code> ko'rinishida yuboring."
        )
        return

    # Kanalni tekshiramiz: bot u yerda admin bo'lmasa obunani tekshira olmaydi
    title, url, warning = chat_id, None, ""
    try:
        chat = await message.bot.get_chat(chat_id)
        title = chat.title or chat_id
        url = f"https://t.me/{chat.username}" if chat.username else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Kanalni tekshirib bo'lmadi (%s): %s", chat_id, exc)
        warning = (
            "\n\n⚠️ <b>Diqqat:</b> kanalga ulanib bo'lmadi. Botni o'sha kanalga "
            "<b>admin</b> qiling, aks holda obuna tekshirilmaydi."
        )

    await channels_db.add_channel(chat_id, title, url)
    await state.clear()
    await message.answer(
        f"✅ Kanal qo'shildi: <code>{chat_id}</code>\n"
        f"📢 {title}{warning}\n\n"
        "Panelni ochish: /admin"
    )


# =========================
# KINO O'CHIRISH (FSM)
# =========================


@router.message(Command("delete"))
async def cmd_delete(message: Message, state: FSMContext) -> None:
    await state.set_state(DeleteMovie.waiting_for_code)
    await message.answer("🗑 O'chiriladigan kino <b>kodini</b> yuboring:\n❌ Bekor qilish: /cancel")


@router.message(DeleteMovie.waiting_for_code, F.text)
async def process_delete_code(message: Message, state: FSMContext) -> None:
    code = message.text.strip()
    deleted = await movies_db.delete_movie(code)
    await state.clear()

    if deleted:
        await message.answer(f"🗑 <code>{code}</code> kodli kino o'chirildi.")
    else:
        await message.answer(f"🔍 <code>{code}</code> kodli kino topilmadi.")
