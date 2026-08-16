import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import Message
from aiogram.utils.markdown import hbold

import config
from database import movies as movies_db

logger = logging.getLogger(__name__)

router = Router(name="user")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        f"👋 Assalomu alaykum, {hbold(message.from_user.full_name)}!\n\n"
        "🎬 Men kino botman.\n"
        "🔢 Kino <b>kodini</b> yuboring — men uni sizga jo'nataman.\n\n"
        "Masalan: <code>125</code>"
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "ℹ️ <b>Yordam</b>\n\n"
        "Kino olish uchun shunchaki kino <b>kodini</b> yozing (masalan: <code>125</code>).\n"
        "Kodlarni kanalimizdagi postlardan olasiz."
    )


@router.message(Command("id"))
async def cmd_id(message: Message) -> None:
    """Diagnostika: bot xabarda KIMNI ko'rayotganini aynan ko'rsatadi.

    IsAdmin filtri `from_user.id` ni tekshiradi — shu buyruq o'sha raqamni
    qaytaradi. ADMIN_ID bilan solishtirish uchun ishlatiladi.
    """
    me = await message.bot.get_me()
    user_id = message.from_user.id
    admin = config.is_admin(user_id)

    lines = [
        f"🤖 Bot: @{me.username}",
        f"👤 Sizning user_id: <code>{user_id}</code>",
        f"💬 chat_id: <code>{message.chat.id}</code>",
    ]
    # ADMIN_ID ro'yxatini faqat adminning o'ziga ko'rsatamiz — begona odamga
    # admin ID'sini berish uni nishonga olishni osonlashtiradi (spam, fishing).
    if admin:
        lines.append(f"🔑 ADMIN_ID ro'yxati: <code>{sorted(config.ADMIN_IDS)}</code>")
        lines.append("✅ Siz ADMINSIZ")
    else:
        lines.append("👥 Siz oddiy foydalanuvchisiz")

    await message.answer("\n".join(lines))


@router.message(StateFilter(None), F.text)
async def search_movie(message: Message) -> None:
    """Har qanday matn = kino kodi deb qaraladi.

    StateFilter(None) muhim: agar foydalanuvchi (masalan admin) biror FSM
    jarayonida bo'lsa, uning javobi bu handlerga tushib ketmaydi.
    """
    code = message.text.strip()

    try:
        movie = await movies_db.get_movie_by_code(code)
    except Exception:  # noqa: BLE001 - baza tushib qolsa bot yiqilmasin
        logger.exception("Kino qidirishda xato: %s", code)
        await message.answer("⚠️ Texnik nosozlik. Birozdan so'ng qayta urinib ko'ring.")
        return

    if movie is None:
        await message.answer(
            f"🔍 <code>{code}</code> kodli kino topilmadi.\n"
            "Kodni tekshirib, qaytadan yuboring."
        )
        return

    await message.answer_video(
        video=movie["file_id"],
        caption=(
            f"🎬 <b>{movie['title']}</b>\n"
            f"🔢 Kod: <code>{movie['movie_code']}</code>\n\n"
            "❤️ Botimizni tanlaganingiz uchun rahmat!"
        ),
    )


@router.message()
async def fallback(message: Message) -> None:
    """Matn ham, buyruq ham bo'lmagan xabarlar (stiker, rasm va h.k.)."""
    await message.answer("🔢 Iltimos, kino <b>kodini</b> matn ko'rinishida yuboring.")
