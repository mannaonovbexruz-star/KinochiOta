import os
import sys

from dotenv import load_dotenv

load_dotenv()


# =========================
# TELEGRAM
# =========================

# @BotFather dan olingan token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Eski main.py bilan moslik uchun alias (o'zgartirmang)
TOKEN = BOT_TOKEN

# EGASI (owner). Bitta raqam ham, vergul bilan ajratilgan ro'yxat ham bo'ladi:
#   ADMIN_ID=123456789
#   ADMIN_ID=123456789,987654321
#
# Egani bazadan o'chirib bo'lmaydi — u faqat shu env o'zgaruvchida turadi.
# Parol bilan kirgan oddiy adminlar esa `admins` jadvalida saqlanadi.
OWNER_IDS: set[int] = {
    int(part.strip())
    for part in os.getenv("ADMIN_ID", "").split(",")
    if part.strip().isdigit()
}

# Eski nom bilan moslik
ADMIN_IDS = OWNER_IDS

# Parol bilan admin bo'lish uchun. Bo'sh bo'lsa — parol bilan kirish O'CHIQ,
# faqat ADMIN_ID dagi egasi admin bo'ladi.
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()


# =========================
# SUPABASE
# =========================

# Supabase Dashboard -> Project Settings -> API
SUPABASE_URL = os.getenv("SUPABASE_URL")

# ⚠️ Serverda service_role kalitidan foydalaning (RLS'ni chetlab o'tadi).
# anon kaliti bilan ishlatsangiz, jadvalga RLS policy yozishingiz shart.
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Jadval nomi (SQL sxemasidagi bilan bir xil bo'lishi kerak)
MOVIES_TABLE = os.getenv("MOVIES_TABLE", "movies")


# =========================
# SERVER / DEPLOY
# =========================

# Railway/Render avtomatik PORT beradi
PORT = int(os.getenv("PORT", "8080"))

# railway.json dagi healthcheckPath ishlashi uchun kichik HTTP server
ENABLE_HEALTH_SERVER = os.getenv("ENABLE_HEALTH_SERVER", "1") == "1"

# Eski main.py fayl-bazasi uchun papka (Supabase versiyasida ishlatilmaydi)
DATA_DIR = os.getenv("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def is_owner(user_id: int) -> bool:
    """Foydalanuvchi EGASI ekanligini tekshiradi (ADMIN_ID env).

    Oddiy adminlik `admins` jadvalidan tekshiriladi — buning uchun
    `handlers.filters.IsAdmin` yoki `database.admins.get_admin_ids()`.
    """
    return user_id in OWNER_IDS


def validate() -> None:
    """Majburiy env o'zgaruvchilarni tekshiradi.

    Import paytida emas, bot.py startida chaqiriladi — shunda eski main.py
    ham shu configni Supabase o'zgaruvchilarisiz import qila oladi.
    """
    missing = [
        name
        for name, value in (
            ("BOT_TOKEN", BOT_TOKEN),
            ("SUPABASE_URL", SUPABASE_URL),
            ("SUPABASE_KEY", SUPABASE_KEY),
        )
        if not value
    ]
    if not OWNER_IDS:
        missing.append("ADMIN_ID")

    if missing:
        print(
            f"❌ XATOLIK: quyidagi environment variable'lar yo'q: {', '.join(missing)}",
            file=sys.stderr,
        )
        print("💡 .env faylida yoki Railway dashboardda sozlang.", file=sys.stderr)
        sys.exit(1)
