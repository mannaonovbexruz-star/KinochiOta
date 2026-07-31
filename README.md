# 🎬 KinochiOta Bot

Telegram'da kino tarqatuvchi bot. Foydalanuvchi kino kodini yuboradi, bot esa o'sha kodga mos kinoni qaytaradi.

## ✨ Xususiyatlar

- 🔍 **Kino kod orqali qidirish** — har bir kinoning o'z kodi bor
- ⭐ **Premium tizimi** — obuna shartsiz + kino nomidan qidirish
- 📢 **Majburiy obuna** — 2 ta kanalga a'zo bo'lish talab qilinadi
- 📤 **Do'stlarga ulashish** — bir tugma bilan kino ulashish
- 🖥 **Webhook + Polling** — Railway va Render'da ishlaydi
- 👁 **Watchdog** — Render backup server avtomatik almashinish

## 🛠 Texnologiyalar

- Python 3.12
- aiogram 3.x
- aiohttp

## 🚀 Ishga tushirish (mahalliy)

```bash
# 1. Kutubxonalarni o'rnatish
pip install -r requirements.txt

# 2. .env faylini yaratish
cp .env.example .env        # Linux/Mac
# yoki
copy .env.example .env      # Windows
# .env ichida BOT_TOKEN ni o'z tokeningizga almashtiring

# 3. Botni ishga tushirish
python main.py
```

## ☁️ Deploy

### Railway (asosiy server, polling)
1. Repo'ni Railway'ga ulang
2. Environment o'zgaruvchilarga `BOT_TOKEN` ni qo'shing
3. `PORT` va `DATA_DIR` (persistent volume: `/data`) ni sozlang

### Render (backup server, webhook)
1. Repo'ni GitHub'ga push qiling (Render GitHub orqali deploy qiladi)
2. Render dashboard → **New +** → **Blueprint** → GitHub reponi tanlang
3. `render.yaml` avtomatik aniqlanadi → **Apply** tugmasini bosing
4. Dashboardda quyidagi environment o'zgaruvchilarni sozlang:
   - `BOT_TOKEN` — bot tokeningiz
   - `SELF_URL` — Render servis URL'i (masalan `https://kinochi-ota-bot.onrender.com`)
   - `PRIMARY_URL` — asosiy Railway server URL'i (watchdog kuzatadi)
5. Deploy tugagach **Environment** bo'limidan avtomatik yaratilgan `SECRET_KEY` qiymatini nusxalang
6. Webhook'ni qo'lda faollashtirish: brauzerda oching
   `https://<SELF_URL>/activate/<SECRET_KEY>` (yoki botga admin sifatida `/activate` yozing)

> 💡 **Watchdog qanday ishlaydi**: Render'dagi watchdog `PRIMARY_URL` (Railway) ni kuzatib turadi.
> Railway tushib qolsa (3 marta ketma-ket javob bermasa), Render avtomatik webhook'ni oladi;
> Railway qaytsa, webhook o'z-o'zidan o'chirilib polling-ga qaytadi.
> ⚠️ Agar Railway sog'lom bo'lsa, webhook faol turmaydi — bu normal holat.

> ⚠️ **Free tier eslatmasi**: Render free rejasida `/data` papkasi har bir redeploy'da tozalanadi.
> `database.json` repodan avtomatik tiklanadi, lekin `premium_users.json` qayta deploy'da yo'qoladi.
> Premium ma'lumotlar muhim bo'lsa, paid rejaga o'tishni o'ylab ko'ring.

## 📋 Buyruqlar

| Buyruq | Tavsif |
|---|---|
| `/start` | Botni ishga tushirish |
| `/buy` | Premium sotib olish |
| `/premium <id>` | Foydalanuvchiga Premium berish (admin) |
| `/unpremium <id>` | Premium'ni o'chirish (admin) |
| `/status` | Bot va webhook holati (admin) |
| `/activate` | Webhook'ni o'rnatish (admin) |
| `/deactivate` | Webhook'ni o'chirish (admin) |

## 🔧 Sozlash (config)

Asosiy sozlamalar `main.py` boshida:

```python
ADMIN_IDS = [4423253818, 7116299492]   # Admin ID lar
CHANNELS  = [-1004423253818, -1004374605592]  # Majburiy kanallar
```

Kino ma'lumotlari `database.json` da saqlanadi:

```json
{
  "100": {
    "name": "Kino nomi",
    "country": "Mamlakat",
    "language": "Til",
    "format": "Sifat",
    "thanks": "Rahmat",
    "file_id": "Telegram file_id"
  }
}
```

## 🤝 Kredit

- Bot: [@KinochiOta_bot](https://t.me/KinochiOta_bot)
- Kanal: [@KinochiOka2025](https://t.me/KinochiOka2025)

---
© 2026 KinochiOta — Barcha huquqlar himoyalangan.
