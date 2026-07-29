import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token (majburiy)
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("❌ XATOLIK: BOT_TOKEN environment variable topilmadi!", file=sys.stderr)
    print("💡 .env faylida yoki Railway dashboardda BOT_TOKEN ni sozlang.", file=sys.stderr)
    sys.exit(1)

# Ma'lumotlar saqlanadigan papka
# Railwayda persistent volume mount qiling: /data
# Mahalliy kompyuterda loyiha papkasi ichida
DATA_DIR = os.getenv("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))

# Health check server porti (Railway avtomatik PORT beradi)
PORT = int(os.getenv("PORT", 8080))