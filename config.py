import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN", "")

# Ma'lumotlar saqlanadigan papka (Railway persistent volume)
DATA_DIR = os.getenv("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))

PORT = int(os.getenv("PORT", 8080))