import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token (majburiy)
# Tokenni .env faylida BOT_TOKEN=... sifatida yoki platforma dashboardida saqlang
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("❌ XATOLIK: BOT_TOKEN environment variable topilmadi!", file=sys.stderr)
    print("💡 .env faylida yoki Railway dashboardda BOT_TOKEN ni sozlang.", file=sys.stderr)
    sys.exit(1)

# Ma'lumotlar saqlanadigan papka
# Railwayda persistent volume mount qiling: /data
# Mahalliy kompyuterda loyiha papkasi ichida
DATA_DIR = os.getenv("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))

# Agar sozlangan DATA_DIR yozib bo'lmaydigan bo'lsa (masalan Render free
# tier'da /data yaratib bo'lmasa), ishonchli joyga tushamiz. Aks holda
# lock/premium/database yozish xatosi app'ni ishdan chiqarib, healthcheck
# muvaffaqiyatsiz bo'lib qolardi.
_probe = None
try:
    os.makedirs(DATA_DIR, exist_ok=True)
    _probe = os.path.join(DATA_DIR, ".write_probe")
    with open(_probe, "w", encoding="utf-8") as _f:
        _f.write("ok")
except OSError:
    DATA_DIR = os.path.dirname(os.path.abspath(__file__))
    print(f"⚠️ DATA_DIR yozib bo'lmadi, fallback: {DATA_DIR}", file=sys.stderr)
finally:
    if _probe is not None:
        try:
            os.remove(_probe)
        except OSError:
            pass

# Health check server porti (Railway/Render avtomatik PORT beradi)
PORT = int(os.getenv("PORT", 8080))