"""`/admin` — panelga kirish va parol bilan admin bo'lish.

Bu router IsAdmin filtri bilan CHEKLANMAGAN, chunki hali admin bo'lmagan
odam ham `/admin <parol>` yozib kira olishi kerak. Himoya handler ichida.
"""

import logging
import secrets
import time

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

import config
from database import admins as admins_db
from handlers.keyboards import admin_reply_keyboard
from handlers.panel import render_panel

logger = logging.getLogger(__name__)

router = Router(name="auth")

# Brute-force himoyasi: parol endi zaif nuqta, shuning uchun urinishlar cheklanadi
MAX_ATTEMPTS = 5
BLOCK_SECONDS = 15 * 60

# {user_id: {"fails": int, "blocked_until": float}}
_login_attempts: dict[int, dict[str, float]] = {}


def reset_login_attempts() -> None:
    """Testlar va qo'lda tozalash uchun."""
    _login_attempts.clear()


def _blocked_for(user_id: int) -> int:
    """Bloklangan bo'lsa — necha soniya qolganini, aks holda 0 qaytaradi."""
    entry = _login_attempts.get(user_id)
    if not entry:
        return 0
    remaining = entry.get("blocked_until", 0) - time.monotonic()
    return int(remaining) if remaining > 0 else 0


def _register_failure(user_id: int) -> None:
    entry = _login_attempts.setdefault(user_id, {"fails": 0, "blocked_until": 0})
    entry["fails"] += 1
    if entry["fails"] >= MAX_ATTEMPTS:
        entry["blocked_until"] = time.monotonic() + BLOCK_SECONDS
        entry["fails"] = 0


async def _show_panel(message: Message) -> None:
    # Avval doimiy tugmalarni biriktiramiz (reply klaviatura), keyin panelni
    # inline tugmalari bilan chiqaramiz — ikkalasi bir vaqtda ishlayveradi.
    await message.answer("🛠 Boshqaruv tugmalari yoqildi.", reply_markup=admin_reply_keyboard())

    text, markup = await render_panel(message.from_user.id)
    await message.answer(text, reply_markup=markup)


@router.message(Command("admin"))
async def cmd_admin(message: Message, command: CommandObject) -> None:
    user = message.from_user
    password = (command.args or "").strip()

    # 1. Allaqachon admin bo'lsa — parol so'ralmaydi
    if await admins_db.is_admin(user.id):
        await _show_panel(message)
        return

    # 2. Bloklanganmi
    blocked = _blocked_for(user.id)
    if blocked:
        await message.answer(
            f"🚫 Bloklandingiz: juda ko'p noto'g'ri urinish.\n"
            f"⏳ {blocked // 60 + 1} daqiqadan keyin qayta urinib ko'ring."
        )
        return

    # 3. Parol berilmagan
    if not password:
        await message.answer(
            "🔒 Bu buyruq adminlar uchun.\n"
            "Parolingiz bo'lsa: <code>/admin parol</code>"
        )
        return

    # 4. Parol bilan kirish o'chirilganmi
    if not config.ADMIN_PASSWORD:
        logger.warning("ADMIN_PASSWORD sozlanmagan, kirish urinishi: %s", user.id)
        await message.answer("🔒 Parol bilan kirish o'chirilgan.")
        return

    # 5. Parolni tekshirish.
    # compare_digest — vaqt bo'yicha hujumdan himoya: taqqoslash har doim
    # bir xil vaqt oladi, shuning uchun parolni belgima-belgi topib bo'lmaydi.
    #
    # ⚠️ .encode() SHART: compare_digest str bilan faqat ASCII qabul qiladi.
    # Parolda ’ yoki ў bo'lsa TypeError chiqib, bot javob bermay qolardi.
    if secrets.compare_digest(password.encode("utf-8"), config.ADMIN_PASSWORD.encode("utf-8")):
        await admins_db.add_admin(user.id, user.username)
        logger.info("Yangi admin: %s (@%s)", user.id, user.username)

        # Parol yozilgan xabarni o'chiramiz — chat tarixida qolmasin
        try:
            await message.delete()
        except Exception as exc:  # noqa: BLE001 - o'chirib bo'lmasa ham davom etamiz
            logger.warning("Parol xabarini o'chirib bo'lmadi: %s", exc)

        await message.answer("✅ <b>Admin bo'ldingiz!</b>")
        await _show_panel(message)
        return

    # 6. Noto'g'ri parol
    _register_failure(user.id)
    logger.warning(
        "Noto'g'ri admin paroli: user_id=%s username=@%s", user.id, user.username
    )
    await message.answer("❌ Parol noto'g'ri.")
