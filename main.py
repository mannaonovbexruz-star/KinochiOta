import json
import asyncio
import atexit
import os
import sys
import logging
import threading
import socket

from aiogram import Bot, Dispatcher, F

from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BotCommand
)

from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import TOKEN, PORT, DATA_DIR


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# =========================
# SINGLE INSTANCE LOCK
# =========================

# Lock fayl: bitta kompyuterda faqat bitta bot instansiyasi
# ishlashini ta'minlaydi (ikkinchi instansiya ishga tushmaydi)
LOCK_FILE = os.path.join(DATA_DIR, "bot.lock")


def _windows_process_image_name(pid):
    """Windows: berilgan PID ga tegishli jarayon nomini qaytaradi (yoki None).

    Misol: _windows_process_image_name(1234) -> "python.exe"
    Jarayon topilmasa yoki nomini aniqlab bo'lmasa -> None
    """
    import subprocess

    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    stdout = result.stdout.strip()
    if not stdout:
        return None

    # CSV formati: "image.exe","PID","Session Name","Session#","Mem Usage"
    # Mos jarayon bo'lmasa tasklist xabar chiqaradi ("INFO: No tasks...")
    try:
        first_field = stdout.splitlines()[0].split(",")[0].strip('"')
    except IndexError:
        return None

    if not first_field or not first_field.lower().endswith(".exe"):
        return None

    return first_field


def _is_python_process_name(image_name):
    """Jarayon nomi Python botiga tegishlimi?"""
    if not image_name:
        return False
    base = image_name.lower()
    return (
        base.startswith("python")
        or base in ("py.exe", "pyw.exe")
    )


def _pid_is_alive(pid):
    """Berilgan PID jonli Python jarayoniga tegishlimi?

    Windows PID-larni qayta ishlatadi: eski lock fayldagi PID boshqa
    jarayonga (masalan svchost.exe) o'tib qolishi mumkin. Shuning uchun
    Windows'da PID jonli bo'lsa ham, u aynan Python jarayoni ekanini
    tekshiramiz — aks holda o'lik (stale) lock fayl botni bloklab qo'yardi.
    Linux/Mac'da esa har qanday jonli jarayon yetarli (PID qayta
    ishlatilish ehtimoli ancha past).
    """

    if pid <= 0:
        return False

    try:
        if os.name == "nt":
            # Windows: PID + jarayon nomini birgalikda tekshiramiz
            return _is_python_process_name(
                _windows_process_image_name(pid)
            )

        # Linux/Mac: signal 0 yuborib jarayon mavjudligini tekshiramiz
        os.kill(pid, 0)
        return True

    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # jarayon bor, lekin bizga tegishli emas
    except OSError:
        return True  # noaniq — jonli deb hisoblaymiz


def acquire_single_instance_lock():
    """Bitta kompyuterda faqat bitta bot instansiyasi ishlashini ta'minlaydi.

    Lock fayl (DATA_DIR/bot.lock) ichiga joriy PID yoziladi.
    Agar boshqa jonli instansiya mavjud bo'lsa — False qaytaradi.
    O'lik (stale) lock fayl avtomatik tozalanadi.
    """
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except OSError as e:
        logger.warning(f"⚠️ DATA_DIR yaratib bo'lmadi ({DATA_DIR}): {e}")

    # Lock faylni atomik yaratishga harakat qilamiz (O_EXCL)
    for attempt in range(2):
        try:
            fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except (FileNotFoundError, PermissionError) as e:
            # DATA_DIR mavjud emas yoki yozib bo'lmaydi — app ishdan chiqmaydi
            logger.warning(f"⚠️ Lock fayl yaratib bo'lmadi ({LOCK_FILE}): {e}")
            return False
        except FileExistsError:
            old_pid = 0
            try:
                with open(LOCK_FILE, "r", encoding="utf-8") as f:
                    old_pid = int(f.read().strip() or "0")
            except (OSError, ValueError):
                old_pid = 0

            if old_pid > 0 and _pid_is_alive(old_pid):
                owner = ""
                if os.name == "nt":
                    img = _windows_process_image_name(old_pid)
                    if img:
                        owner = f", {img}"
                logger.error(
                    f"🚫 Bot allaqachon ishlamoqda (PID {old_pid}{owner})!\n"
                    f"   Ikkinchi instansiya ishga tushirilmaydi.\n"
                    f"   Avval eski jarayonni to'xtating yoki {LOCK_FILE} faylini o'chiring."
                )
                return False

            # O'lik lock fayl — tozalab qayta urinamiz
            try:
                os.remove(LOCK_FILE)
                logger.info(f"🗑 Eski (o'lik) lock fayl tozalandi: {LOCK_FILE}")
            except OSError as e:
                logger.error(f"🚫 Lock faylni o'chirib bo'lmadi: {e}")
                return False
        else:
            try:
                # PID ni darhol yozamiz (bo'sh fayl orqali lock o'g'irlanishining oldini olish)
                os.write(fd, str(os.getpid()).encode("utf-8"))
                os.close(fd)
                logger.info(f"🔒 Single-instance lock olindi: {LOCK_FILE} (PID {os.getpid()})")
                return True
            except OSError as e:
                logger.error(f"🚫 Lock faylga PID yozib bo'lmadi: {e}")
                return False

    logger.error(
        f"🚫 Lock fayl olishda muammo: {LOCK_FILE}\n"
        f"   Faylni qo'lda o'chirib qayta urinib ko'ring."
    )
    return False


def release_single_instance_lock():
    """Bot to'xtaganda lock faylni o'chiradi (faqat o'zimizniki bo'lsa)."""
    try:
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE, "r", encoding="utf-8") as f:
                pid = int(f.read().strip() or "0")
            if pid == os.getpid():
                os.remove(LOCK_FILE)
                logger.info("🔓 Single-instance lock bo'shatildi")
    except (OSError, ValueError):
        pass


atexit.register(release_single_instance_lock)

# =========================
# SOZLAMALAR
# =========================

# Ish rejimi: "polling" (Railway) yoki "webhook" (Render)
MODE = os.getenv("MODE", "polling")

# Serverning tashqi URL manzili (Render/Platformaga qarab)
SELF_URL = os.getenv("SELF_URL", "")

# Maxfiy kalit (webhook va aktivatsiya endpointi uchun)
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-to-secret")

# =========================
# WATCHDOG SOZLAMALARI (faqat webhook mode)
# =========================

# Asosiy serverning health check URL manzili (Railway)
# Watchdog shu URL ni tekshirib turadi. Misol: https://railway-app.railway.app/health
PRIMARY_URL = os.getenv("PRIMARY_URL", "")

# Watchdog qancha vaqt oralig'ida (sekund) tekshiradi
WATCHDOG_INTERVAL = int(os.getenv("WATCHDOG_INTERVAL", "30"))

# Necha marta ketma-ket xato bo'lsa, backup faollashsin
WATCHDOG_FAILURES = int(os.getenv("WATCHDOG_FAILURES", "3"))


# =========================
# Health check server (Railway/Render health check uchun)
# =========================

from aiohttp import web
import aiohttp

async def health(request):
    return web.Response(text="OK", status=200)

WEBHOOK_PATH = f"/webhook/{SECRET_KEY}"


async def set_webhook():
    """Telegram webhook-ni ushbu serverga o'rnatadi"""
    webhook_url = f"{SELF_URL}{WEBHOOK_PATH}"
    await bot.set_webhook(
        url=webhook_url,
        secret_token=SECRET_KEY,
        max_connections=40
    )
    logger.info(f"✅ Webhook o'rnatildi: {webhook_url}")
    return webhook_url


async def delete_webhook():
    """Telegram webhook-ni o'chiradi"""
    await bot.delete_webhook()
    logger.info("✅ Webhook o'chirildi")


async def get_webhook_info():
    """Webhook holatini qaytaradi"""
    return await bot.get_webhook_info()


async def handle_http_activate(request):
    """HTTP orqali webhook-ni faollashtirish (server tushib qolganda ishlatiladi)"""
    key = request.match_info.get("key", "")
    if key != SECRET_KEY:
        return web.Response(text="❌ Noto'g'ri kalit!", status=403)
    
    if MODE != "webhook":
        return web.Response(
            text="❌ Bu server polling rejimida. Webhook faqat webhook rejimidagi serverda o'rnatiladi!",
            status=400
        )
    
    try:
        url = await set_webhook()
        info = await get_webhook_info()
        return web.Response(
            text=f"✅ Webhook o\'rnatildi!\n📍 URL: {url}\n✅ Xatolik: {info.last_error_message or 'Mavjud emas'}",
            status=200
        )
    except Exception as e:
        logger.error(f"HTTP activate xatolik: {e}")
        return web.Response(text=f"❌ Xatolik: {e}", status=500)


async def handle_http_deactivate(request):
    """HTTP orqali webhook-ni o'chirish (faqat webhook rejimidagi serverda)"""
    key = request.match_info.get("key", "")
    if key != SECRET_KEY:
        return web.Response(text="❌ Noto'g'ri kalit!", status=403)
    
    if MODE != "webhook":
        return web.Response(
            text="❌ Webhook faqat webhook rejimidagi serverda o'chiriladi!",
            status=400
        )
    
    try:
        info = await get_webhook_info()
        old_url = info.url or "O'rnatilmagan"
        await delete_webhook()
        return web.Response(
            text=f"✅ Webhook o'chirildi!\n📍 Eski URL: {old_url}\n💡 Endi asosiy server (Railway) polling orqali ishlaydi.",
            status=200
        )
    except Exception as e:
        logger.error(f"HTTP deactivate xatolik: {e}")
        return web.Response(text=f"❌ Xatolik: {e}", status=500)


# =========================
# WATCHDOG (faqat webhook mode / Render da ishlaydi)
# =========================

_watchdog_fail_count = 0


async def _is_self_webhook_active():
    """Webhook aynan shu serverga o'rnatilganmi?"""
    if not SELF_URL:
        return False
    try:
        info = await get_webhook_info()
        return info.url is not None and (info.url or "").startswith(SELF_URL.rstrip("/"))
    except Exception:
        return False


async def watchdog_check():
    """Watchdog: asosiy server (Railway) ni kuzatib, kerak bo'lsa avtomatik almashadi"""
    global _watchdog_fail_count

    if not PRIMARY_URL:
        logger.warning("⚠️ Watchdog: PRIMARY_URL sozlanmagan! Automatic failover ISHLAMAYDI.")
        return

    logger.info(f"👁 Watchdog ishga tushdi. Asosiy server: {PRIMARY_URL}")

    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        while True:
            railway_up = False

            try:
                async with session.get(PRIMARY_URL) as resp:
                    railway_up = resp.status == 200
            except (asyncio.TimeoutError, aiohttp.ClientError, OSError) as e:
                railway_up = False
                logger.debug(f"Watchdog: Railway check failed: {e}")

            # Webhook hozir shu serverda faolmi?
            is_self_active = await _is_self_webhook_active()

            if railway_up:
                _watchdog_fail_count = 0

                if is_self_active:
                    # Railway qaytdi, backup-ni o'chirish kerak
                    logger.info("✅ Watchdog: Railway qaytdi! Backup o'chirilmoqda...")
                    try:
                        await delete_webhook()
                        logger.info("✅ Watchdog: Webhook o'chirildi, Railway polling-ga qaytdi")
                    except Exception as e:
                        logger.error(f"❌ Watchdog: Webhook o'chirishda xatolik: {e}")
            else:
                _watchdog_fail_count += 1

                if _watchdog_fail_count == WATCHDOG_FAILURES:
                    logger.warning(f"⚠️ Watchdog: Railway ({_watchdog_fail_count}/{WATCHDOG_FAILURES}) javob bermadi")

                # Threshold ga yetdimi va webhook hali bu serverda emasmi?
                if (
                    _watchdog_fail_count >= WATCHDOG_FAILURES
                    and not is_self_active
                    and SELF_URL
                ):
                    logger.warning(
                        f"🚨 Watchdog: Railway ({WATCHDOG_FAILURES} marta) javob bermadi! "
                        "Backup faollashtirilmoqda..."
                    )
                    try:
                        await set_webhook()
                        logger.info("✅ Watchdog: Backup faollashtirildi!")
                    except Exception as e:
                        logger.error(f"❌ Watchdog: Backup faollashtirishda xatolik: {e}")

            await asyncio.sleep(WATCHDOG_INTERVAL)


# =========================
# PORT TEKSHIRISH
# =========================

def _is_port_free(port):
    """Port hozir band emasligini tekshiradi."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("0.0.0.0", port))
        return True
    except OSError:
        return False


def _log_port_busy(port):
    logger.error(
        f"🚫 {port}-port band! Server ishga tushmadi.\n"
        f"   Bu portni boshqa jarayon egallab turibdi (masalan, eski bot nusxasi).\n"
        f"   Qaysi jarayon ekanini tekshirish:\n"
        f"     Windows:  netstat -ano | findstr :{port}\n"
        f"     Linux:    sudo lsof -i :{port}\n"
        f"   Jarayonni to'xtatish (yuqoridagi natijadagi PID bilan):\n"
        f"     Windows:  taskkill /PID <PID> /F\n"
        f"     Linux:    kill <PID>\n"
        f"   Yoki boshqa port tanlang: PORT=<boshqa port> python main.py"
    )


async def start_health_server():
    """Health check + activation/deactivation serverini ishga tushiradi"""
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    
    # HTTP orqali aktivatsiya endpointi
    # Masalan: https://railway-app.railway.app/activate/your-secret-key
    app.router.add_get("/activate/{key}", handle_http_activate)
    app.router.add_post("/activate/{key}", handle_http_activate)
    
    # HTTP orqali deaktivatsiya endpointi
    # Masalan: https://render-app.onrender.com/deactivate/your-secret-key
    app.router.add_get("/deactivate/{key}", handle_http_deactivate)
    app.router.add_post("/deactivate/{key}", handle_http_deactivate)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    try:
        await site.start()
    except OSError as e:
        if getattr(e, "errno", None) in (10048, 98, 48):  # Windows / Linux / Mac band port
            _log_port_busy(PORT)
        else:
            logger.error(f"Health check serverni ishga tushirishda xatolik: {e}")
        sys.exit(1)
    logger.info(f"Health check server running on port {PORT}")


# =========================
# ADMINLAR
# =========================

ADMIN_IDS = [
    4423253818,
    7116299492
]


# =========================
# BOT
# =========================

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher()


# =========================
# KANALLAR
# =========================

CHANNELS = [
    -1004423253818,
    -1004374605592
]


# =========================
# BOT USERNAME CACHE
# =========================

_bot_username = None
_bot_username_lock = threading.Lock()

async def get_bot_username():
    global _bot_username
    if _bot_username is None:
        with _bot_username_lock:
            if _bot_username is None:
                me = await bot.get_me()
                _bot_username = me.username
    return _bot_username


# =========================
# PREMIUM FILE
# =========================

PREMIUM_FILE = os.path.join(DATA_DIR, "premium_users.json")
_premium_lock = threading.Lock()


def get_premium_users():

    if not os.path.exists(PREMIUM_FILE):
        return []

    try:
        with open(
            PREMIUM_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except Exception as e:
        logger.error(f"premium_users.json o'qishda xatolik: {e}")
        return []


def add_premium_user(user_id):
    with _premium_lock:
        users = get_premium_users()

        if user_id not in users:
            users.append(user_id)

            try:
                with open(
                    PREMIUM_FILE,
                    "w",
                    encoding="utf-8"
                ) as f:
                    json.dump(users, f)
                return True

            except Exception as e:
                logger.error(f"premium_users.json yozishda xatolik: {e}")
                return False

    return False


def remove_premium_user(user_id):
    with _premium_lock:
        users = get_premium_users()

        if user_id in users:
            users.remove(user_id)

            try:
                with open(
                    PREMIUM_FILE,
                    "w",
                    encoding="utf-8"
                ) as f:
                    json.dump(users, f)
                return True

            except Exception as e:
                logger.error(f"premium_users.json yozishda xatolik: {e}")
                return False

    return False


# =========================
# DATABASE
# =========================

DB_PATH = os.path.join(DATA_DIR, "database.json")
LOCAL_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.json")


def _sync_database():
    """Lokal (repo)dagi database.json ni volume dagi nusxa bilan birlashtiradi.

    Railway/Render da DATA_DIR volume ga qaratilgan bo'ladi. Avvalgi
    kod faqat volume da fayl bo'lmasagina ko'chirardi — shuning uchun
    yangi qo'shilgan kinolar volume ga o'tmas, bot eski bazani o'qib
    qolaverardi.

    Endi har ishga tushishda:
    - volume fayli yo'q bo'lsa, lokal fayl nusxalanadi;
    - volume fayli bor bo'lsa, ikkisi birlashtiriladi (lokal
      ma'lumotlar ustun turadi, lekin volume ga to'g'ridan-to'g'ri
      qo'shilgan kinolar ham saqlanib qoladi).
    """
    if not os.path.exists(LOCAL_DB):
        return

    try:
        with open(LOCAL_DB, "r", encoding="utf-8") as src:
            local_data = json.load(src)
    except Exception as e:
        logger.warning(f"Lokal database.json o'qishda xatolik: {e}")
        return

    volume_data = {}
    try:
        with open(DB_PATH, "r", encoding="utf-8") as dst:
            volume_data = json.load(dst)
    except FileNotFoundError:
        pass  # Yangi volume — hech qanday muammo emas
    except Exception as e:
        logger.warning(f"Volume database.json o'qishda xatolik: {e}")

    # Lokal ma'lumotlar ustun, volume dagi qo'shimchalar saqlanadi
    volume_data.update(local_data)

    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(DB_PATH, "w", encoding="utf-8") as dst:
            json.dump(volume_data, dst, ensure_ascii=False, indent=4)
        logger.info(f"Database birlashtirildi: {len(volume_data)} ta kino -> {DB_PATH}")
    except Exception as e:
        logger.warning(f"Database yozishda xatolik: {e}")


def load_movies():
    """Database faylini diskdan har safar yangidan o'qib qaytaradi.

    Shu tufayli yangi kino qo'shilsa, botni qayta ishga tushirmasdan
    ham darhol ko'rinaveradi.
    """
    path = DB_PATH if os.path.exists(DB_PATH) else LOCAL_DB
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Database yuklanmadi ({path}): {e}")
        return {}


_sync_database()

movies = load_movies()
logger.info(f"Database yuklandi: {len(movies)} ta kino")


keyboard = InlineKeyboardMarkup(
    inline_keyboard=[

        [
            InlineKeyboardButton(
                text="📢 1-kanalga a'zo bo'lish",
                url="https://t.me/ACIYNPUBG_UC"
            )
        ],

        [
            InlineKeyboardButton(
                text="📢 2-kanalga a'zo bo'lish",
                url="https://t.me/KinochiOka2025"
            )
        ],

        [
            InlineKeyboardButton(
                text="✅ Tasdiqlash",
                callback_data="check"
            )
        ],

        [
            InlineKeyboardButton(
                text="⭐ Premium sotib olish",
                callback_data="premium"
            )
        ]

    ]
)


back_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[

        [

            InlineKeyboardButton(
                text="⬅️ Orqaga",
                callback_data="back_to_sub"
            )

        ]

    ]
)


async def check_sub(user_id):

    if (
        user_id in ADMIN_IDS
        or user_id in get_premium_users()
    ):
        return True

    for channel in CHANNELS:

        try:

            member = await bot.get_chat_member(
                chat_id=channel,
                user_id=user_id
            )

            if member.status in [
                "left",
                "kicked"
            ]:
                return False

        except Exception as e:
            logger.warning(f"check_sub xatosi (user {user_id}, kanal {channel}): {e}")
            return False

    return True


@dp.message(Command("start"))
async def start(message: Message):

    user_id = message.from_user.id

    if await check_sub(user_id):

        await message.answer(

            "🎉 <b>Xush kelibsiz!</b>\n\n"

            "🎬 Kino kodini yuboring.\n\n"

            "⭐ Premium foydalanuvchilar "
            "kino nomidan ham qidira oladi."

        )

    else:

        await message.answer(

            "❌ Botdan foydalanish uchun "
            "kanallarga obuna bo'ling.\n\n"

            f"🆔 Sizning ID: "
            f"<code>{user_id}</code>",

            reply_markup=keyboard

        )


# =========================
# BUY
# =========================

@dp.message(Command("buy"))
async def buy(message: Message):

    await message.answer(

        "⭐ Premium sotib olish:",

        reply_markup=InlineKeyboardMarkup(

            inline_keyboard=[

                [

                    InlineKeyboardButton(

                        text="⭐ Premium olish",

                        callback_data="premium"

                    )

                ]

            ]

        )

    )


# =========================
# OBUNA TASDIQLASH
# =========================

@dp.callback_query(F.data=="check")
async def check(callback: CallbackQuery):

    if await check_sub(callback.from_user.id):

        await callback.answer()

        await callback.message.edit_text(

            "✅ Obuna tasdiqlandi!\n\n"

            "🎬 Kino kodini yuboring."

        )

    else:

        await callback.answer(

            "❌ Hali kanallarga obuna bo'lmagansiz!",

            show_alert=True

        )


# =========================
# ADMIN PREMIUM BERISH
# =========================

@dp.message(Command("premium"))
async def make_premium(message: Message):

    if message.from_user.id not in ADMIN_IDS:
        return

    try:

        args = message.text.split()

        if len(args) < 2:

            await message.answer(
                "❌ Foydalanish:\n"
                "<code>/premium user_id</code>"
            )

            return

        user_id = int(args[1])

        if add_premium_user(user_id):

            await message.answer(

                f"✅ {user_id} Premium qilindi!"

            )

            try:

                await bot.send_message(

                    chat_id=user_id,

                    text=

                    "🎉 Tabriklaymiz!\n\n"

                    "⭐ Sizga Premium berildi.\n"

                    "Endi kanallarga obuna shart emas."

                )

            except Exception as e:
                logger.warning(f"Premium xabarini yuborib bo'lmadi (user {user_id}): {e}")

        else:

            await message.answer(

                "⚠️ Bu foydalanuvchi allaqachon Premium."

            )

    except Exception as e:
        logger.error(f"/premium xatolik: {e}")

        await message.answer(

            "❌ ID xato!"

        )


# =========================
# ADMIN PREMIUM O'CHIRISH
# =========================

@dp.message(Command("unpremium"))
async def del_premium(message: Message):

    if message.from_user.id not in ADMIN_IDS:

        return

    try:

        args = message.text.split()

        if len(args) < 2:

            await message.answer(

                "❌ Foydalanish:\n"
                "<code>/unpremium user_id</code>"

            )

            return

        user_id = int(args[1])

        if remove_premium_user(user_id):

            await message.answer(

                f"❌ {user_id} Premiumdan chiqarildi."

            )

        else:

            await message.answer(

                "⚠️ Bu user Premium emas."

            )

    except Exception as e:
        logger.error(f"/unpremium xatolik: {e}")

        await message.answer(

            "❌ ID xato!"

        )


# =========================
# PREMIUM TUGMASI
# =========================

@dp.callback_query(F.data=="premium")
async def show_premium(callback: CallbackQuery):

    user_id = callback.from_user.id

    text = (

        "💎 <b>PREMIUM OBUNA</b>\n\n"

        "✨ Afzalliklar:\n"

        "✅ Majburiy obuna yo'q\n"

        "✅ Kino nomidan qidirish\n"

        "✅ Tezkor foydalanish\n\n"

        "💰 Narxi: <b>15000 so'm / 1 oy</b>\n\n"

        "💳 Karta:\n"

        "<code>4916 9903 1746 8368</code>\n\n"

        "👤 Karta egasi:\n"

        "Dildora Yuldosheva\n\n"

        "To'lovdan keyin chek va ID yuboring:\n"

        f"🆔 <code>{user_id}</code>"

    )

    await callback.message.edit_text(

        text,

        reply_markup=back_keyboard

    )


# =========================
# ORQAGA
# =========================

@dp.callback_query(F.data=="back_to_sub")
async def back_to_sub(callback: CallbackQuery):

    user_id = callback.from_user.id

    await callback.message.edit_text(

        "❌ Botdan foydalanish uchun "
        "kanallarga obuna bo'ling.\n\n"

        f"🆔 ID: <code>{user_id}</code>",

        reply_markup=keyboard

    )


# =========================
# KINO QIDIRISH
# =========================

@dp.message()
async def movie(message: Message):

    user_id = message.from_user.id

    # Obuna tekshirish

    if not await check_sub(user_id):

        await message.answer(
            "❌ Avval kanallarga obuna bo'ling:",
            reply_markup=keyboard
        )

        return

    # File_id olish (admin uchun)

    if (
        message.video
        or message.document
        or message.animation
    ):

        if message.video:

            file_id = message.video.file_id

        elif message.document:

            file_id = message.document.file_id

        else:

            file_id = message.animation.file_id

        await message.answer(

            "📄 File ID:\n\n"
            f"<code>{file_id}</code>"

        )

        return

    if not message.text:

        return

    # Bazani har safar yangidan o'qiymiz —
    # yangi qo'shilgan kinolar darhol ko'rinadi
    movies = load_movies()

    query = message.text.strip()

    is_premium = (

        user_id in ADMIN_IDS

        or user_id in get_premium_users()

    )

    # =========================
    # KOD BILAN QIDIRISH
    # =========================

    if query in movies:

        movie = movies[query]

        caption = (

            f"{movie['name']}\n\n"

            f"{movie['country']}\n"

            f"{movie['language']}\n"

            f"{movie['format']}\n\n"

            f"{movie['thanks']}"

        )

        bot_username = await get_bot_username()

        share = InlineKeyboardMarkup(

            inline_keyboard=[

                [

                    InlineKeyboardButton(

                        text="📤 Do'stlarga ulashish",

                        url=
                        f"https://t.me/share/url?"
                        f"url=https://t.me/{bot_username}"
                        f"&text=🎬 Kino kodi: {query}"

                    )

                ]

            ]

        )

        try:

            await message.answer(

                "🔍 Kino topildi!\n"
                "⏳ Yuklanmoqda..."

            )

            await message.answer_video(

                video=movie["file_id"],

                caption=caption,

                protect_content=True,

                supports_streaming=True,

                reply_markup=share

            )

        except Exception as e:

            logger.error(f"Video yuborishda xatolik (kod: {query}): {e}")

            await message.answer(

                f"❌ Xatolik:\n{e}"

            )

        return

    # =========================
    # PREMIUM NOM BO'YICHA
    # =========================

    if is_premium:

        found = []

        for code, item in movies.items():

            if query.lower() in item["name"].lower():

                found.append(item)

        if found:

            await message.answer(

                f"🔎 {len(found)} ta kino topildi!"

            )

            bot_username = await get_bot_username()

            for item in found[:3]:

                caption = (

                    f"{item['name']}\n\n"

                    f"{item['country']}\n"

                    f"{item['language']}\n"

                    f"{item['format']}\n\n"

                    f"{item['thanks']}"

                )

                share = InlineKeyboardMarkup(

                    inline_keyboard=[

                        [

                            InlineKeyboardButton(

                                text="📤 Do'stlarga ulashish",

                                url=
                                f"https://t.me/share/url?"
                                f"url=https://t.me/{bot_username}"
                                f"&text=🎬 Kino kodi: {item['name']}"

                            )

                        ]

                    ]

                )

                await message.answer_video(

                    video=item["file_id"],

                    caption=caption,

                    protect_content=True,

                    supports_streaming=True,

                    reply_markup=share

                )

        else:

            await message.answer(

                "❌ Kino topilmadi."

            )

    else:

        await message.answer(

            "❌ Bunday kodli kino topilmadi.\n\n"

            "⭐ Premium bo'lsangiz kino nomidan qidira olasiz."

        )


# =========================
# BOT MENU
# =========================

# =========================
# ADMIN: WEBHOOK FAQAT ADMINLAR UCHUN
# =========================

@dp.message(Command("activate"))
async def cmd_activate(message: Message):

    """Webhook-ni ushbu serverga o'rnatish"""

    if message.from_user.id not in ADMIN_IDS:
        return

    if not SELF_URL:
        await message.answer(
            "❌ <b>SELF_URL</b> sozlanmagan!\n\n"
            "Environment variable ga SELF_URL qo'shing.\n"
            "Masalan: https://my-app.onrender.com"
        )
        return

    if MODE != "webhook":
        await message.answer(
            "❌ Bu server <b>polling</b> rejimida.\n\n"
            "Webhook faqat <b>webhook</b> rejimidagi serverda o'rnatiladi.\n"
            "💡 Backup serverni faollashtirish uchun uning URL manziliga\n"
            "<code>/activate/SECRET_KEY</code> qo'shib oching."
        )
        return

    try:
        url = await set_webhook()
        info = await get_webhook_info()

        await message.answer(
            f"✅ <b>Webhook o'rnatildi!</b>\n\n"
            f"📍 URL: <code>{url}</code>\n"
            f"✅ Xatolik: {info.last_error_message or 'Mavjud emas'}\n"
            f"⏳ Kutilayotgan: {info.pending_update_count} ta"
        )

        logger.info(f"Admin {message.from_user.id} webhook-ni faollashtirdi")

    except Exception as e:
        logger.error(f"/activate xatolik: {e}")
        await message.answer(f"❌ Xatolik: {e}")


@dp.message(Command("deactivate"))
async def cmd_deactivate(message: Message):

    """Webhook-ni o'chirish"""

    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        info = await get_webhook_info()
        old_url = info.url or "O\'rnatilmagan"

        await delete_webhook()

        await message.answer(
            f"✅ <b>Webhook o\'chirildi!</b>\n\n"
            f"📍 Eski URL: <code>{old_url}</code>\n"
            f"💡 Endi boshqa serverda /activate qiling."
        )

        logger.info(f"Admin {message.from_user.id} webhook-ni o'chirdi")

    except Exception as e:
        logger.error(f"/deactivate xatolik: {e}")
        await message.answer(f"❌ Xatolik: {e}")


@dp.message(Command("status"))
async def cmd_status(message: Message):

    """Bot va webhook holatini ko'rish"""

    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        info = await get_webhook_info()

        is_this_server = (
            SELF_URL
            and info.url
            and SELF_URL in info.url
        )

        server_name = os.getenv("RAILWAY_SERVICE_NAME", os.getenv("RENDER_SERVICE_NAME", "Noma'lum server"))

        text = (
            f"🤖 <b>Bot holati</b>\n\n"
            f"📋 <b>Rejim:</b> {MODE.upper()}\n"
            f"🖥 <b>Server:</b> {server_name}\n"
            f"🌐 <b>URL:</b> <code>{SELF_URL or 'Sozlanmagan'}</code>\n\n"
            f"📌 <b>Webhook:</b>\n"
            f"📍 <code>{info.url or 'O\'rnatilmagan'}</code>\n"
            f"✅ Xatolik: {info.last_error_message or 'Mavjud emas'}\n"
            f"⏳ Kutilayotgan: {info.pending_update_count} ta\n"
            f"🔗 Max connection: {info.max_connections}\n\n"
        )

        if is_this_server:
            text += "✅ <b>Bu server faol!</b>"
        elif info.url:
            text += "❌ <b>Bu server faol EMAS.</b>"
            text += f"\n💡 Boshqa serverda /activate qiling yoki \n"
            text += f"🌐 <code>{SELF_URL}/activate/{SECRET_KEY}</code>"
        else:
            text += "💡 Webhook o\'rnatilmagan. /activate yozing."

        await message.answer(text)

    except Exception as e:
        logger.error(f"/status xatolik: {e}")
        await message.answer(f"❌ Xatolik: {e}")


# =========================
# BOT MENU
# =========================

async def set_menu():

    commands = [

        BotCommand(
            command="start",
            description="🏠 Botni ishga tushirish"
        ),

        BotCommand(
            command="buy",
            description="⭐ Premium sotib olish"
        ),

        BotCommand(
            command="status",
            description="📊 Bot holati"
        ),

        BotCommand(
            command="activate",
            description="✅ Webhook-ni faollashtirish"
        ),

        BotCommand(
            command="deactivate",
            description="❌ Webhook-ni o'chirish"
        )

    ]

    await bot.set_my_commands(commands)


# =========================
# MAIN
# =========================

# Container muhitini aniqlash (Render / Railway)
# Container ichida har bir instansiya alohida bo'ladi — single-instance
# lock shart emas. Aks holda eski bot.lock fayli yoki PID takrorlanishi
# tufayli app chiqib ketib, healthcheck muvaffaqiyatsiz bo'lishi mumkin.
IS_CONTAINER = bool(
    os.getenv("RENDER")
    or os.getenv("RENDER_SERVICE_ID")
    or os.getenv("RAILWAY_SERVICE_ID")
    or os.getenv("RAILWAY_SERVICE_NAME")
)


async def main():

    # 1) Single-instance lock — faqat mahalliy (containersiz) rejimda
    if not IS_CONTAINER:
        try:
            if not acquire_single_instance_lock():
                logger.error("🚫 Single-instance lock olinmadi!")
                sys.exit(1)
        except Exception as e:
            logger.warning(f"⚠️ Single-instance lock xatosi (davom etiladi): {e}")
    else:
        logger.info("📦 Container muhiti aniqlandi — single-instance lock o'tkazib yuboriladi")

    # 2) Port band bo'lsa — ogohlantiramiz, lekin chiqib ketmaymiz.
    #    Aslida server o'zi EADDRINUSE bilan aniq xatolik chiqaradi.
    if not _is_port_free(PORT):
        logger.warning(f"⚠️ {PORT}-port band ko'rinmoqda, lekin davom etilmoqda...")

    # MUHIM: set_menu() (Telegram API) faqat server bind bo'lgandan KEYIN
    # chaqiriladi. Aks holda Telegram sekin bo'lsa, port ochilmay qolib,
    # platforma healthcheck'ni muvaffaqiyatsiz deb topardi.

    if MODE == "webhook":

        # ========== WEBHOOK MODE (Render) ==========

        logger.info(f"🌐 Webhook mode: {SELF_URL}")

        # Webhook uchun aiohttp app (health check + webhook birgalikda)
        app = web.Application()

        # Health check
        app.router.add_get("/", health)
        app.router.add_get("/health", health)

        # HTTP activation endpoint
        app.router.add_get("/activate/{key}", handle_http_activate)
        app.router.add_post("/activate/{key}", handle_http_activate)
        
        # HTTP deactivation endpoint
        app.router.add_get("/deactivate/{key}", handle_http_deactivate)
        app.router.add_post("/deactivate/{key}", handle_http_deactivate)

        # Webhook handler (aiogram)
        from aiogram.webhook.aiohttp_server import (
            SimpleRequestHandler,
            setup_application
        )

        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
            secret_token=SECRET_KEY,
        )
        webhook_requests_handler.register(app, path=WEBHOOK_PATH)

        # Aiogram lifecycle-ni aiohttp app ga bog'lash
        setup_application(app, dp, bot=bot)

        # Watchdog-ni ishga tushiramiz (asosiy serverni kuzatish)
        watchdog_task = None
        if PRIMARY_URL:
            watchdog_task = asyncio.create_task(watchdog_check())
            logger.info(f"👁 Watchdog: {PRIMARY_URL} har {WATCHDOG_INTERVAL}s tekshiriladi")
        else:
            logger.info("👁 Watchdog o'chirilgan. PRIMARY_URL sozlanmagan.")

        logger.info("🚀 Webhook server ishga tushdi...")
        logger.info(f"📌 Aktivatsiya: {SELF_URL}/activate/{SECRET_KEY}")

        # web.run_app o'rniga AppRunner — hammasi bitta event loop'da ishlaydi,
        # shuning uchun watchdog ham to'g'ri ishlaydi va healthcheck o'tadi.
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        try:
            await site.start()
        except OSError as e:
            if getattr(e, "errno", None) in (10048, 98, 48):
                _log_port_busy(PORT)
            else:
                logger.error(f"Webhook serverni ishga tushirishda xatolik: {e}")
            await runner.cleanup()
            sys.exit(1)

        logger.info(f"✅ Health check: http://0.0.0.0:{PORT}/health")

        # Server bind bo'ldi — endi bot menyusini o'rnatamiz (xato bo'lsa ham davom)
        try:
            await set_menu()
        except Exception as e:
            logger.warning(f"⚠️ Bot menyusini o'rnatishda xatolik (davom etiladi): {e}")

        # Serverni ochiq ushlab turamiz
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass
        finally:
            if watchdog_task:
                watchdog_task.cancel()
            await runner.cleanup()

    else:

        # ========== POLLING MODE (Railway) ==========

        # Avval health check serverni ishga tushiramiz — healthcheck
        # Telegram API'ga bog'liq bo'lmasligi kerak.
        await start_health_server()

        logger.info("🚀 Bot ishga tushdi (polling)...")
        logger.info(f"📌 Aktivatsiya: {SELF_URL}/activate/{SECRET_KEY}")

        # Server bind bo'ldi — endi bot menyusini o'rnatamiz (xato bo'lsa ham davom)
        try:
            await set_menu()
        except Exception as e:
            logger.warning(f"⚠️ Bot menyusini o'rnatishda xatolik (davom etiladi): {e}")

        try:
            await dp.start_polling(bot)
        except Exception as e:
            logger.error(f"🚫 Polling to'xtadi: {e}")
            sys.exit(1)


if __name__ == "__main__":

    asyncio.run(main())
