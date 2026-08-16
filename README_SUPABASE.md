# 🎬 Kino Bot — Supabase versiyasi (`bot.py`)

Modulli arxitektura: aiogram 3.x + Supabase (PostgreSQL). Eski `main.py` (JSON baza)
teginilmagan — bu versiya `bot.py` orqali ishga tushadi.

## 📁 Struktura

```
.
├── bot.py                  # entrypoint: Dispatcher, health server, polling
├── config.py               # env o'zgaruvchilar + validate()
├── requirements.txt
├── Procfile                # web: python bot.py
├── railway.json            # Railway build/deploy sozlamasi
├── .env.example
│
├── database/
│   ├── __init__.py
│   ├── client.py           # Supabase klienti (singleton) + ping()
│   └── movies.py           # CRUD: add / get / list / count / delete
│
├── handlers/
│   ├── __init__.py         # register_routers(dp) — router tartibi
│   ├── filters.py          # IsAdmin filtri
│   ├── states.py           # FSM state'lar (AddMovie, DeleteMovie)
│   ├── admin.py            # video -> kod -> nom -> Supabase
│   └── user.py             # /start, kod bo'yicha qidiruv
│
├── sql/
│   └── schema.sql          # movies jadvali + indeks + RLS
│
└── scripts/
    └── migrate_json_to_supabase.py   # eski database.json -> Supabase
```

## 🚀 Mahalliy ishga tushirish

```bash
pip install -r requirements.txt

cp .env.example .env       # Windows: copy .env.example .env
# .env ni to'ldiring: BOT_TOKEN, ADMIN_ID, SUPABASE_URL, SUPABASE_KEY

# Supabase Dashboard -> SQL Editor -> sql/schema.sql ni Run qiling

python bot.py
```

## 🗄 Supabase sozlash

1. [supabase.com](https://supabase.com) → **New project**
2. **SQL Editor** → `sql/schema.sql` mazmunini qo'yib **Run**
3. **Project Settings → API** dan quyidagilarni oling:
   - `Project URL` → `SUPABASE_URL`
   - `service_role` kaliti → `SUPABASE_KEY` (⚠️ hech qachon frontendga qo'ymang)

## ☁️ Railway deploy

1. Railway → **New Project → Deploy from GitHub repo** → shu repo
2. **Variables** bo'limiga quyidagilarni qo'shing:

| O'zgaruvchi | Qiymat | Izoh |
|---|---|---|
| `BOT_TOKEN` | `123456:AA...` | @BotFather dan |
| `ADMIN_ID` | `4423253818` | @userinfobot dan; bir nechta: `id1,id2` |
| `SUPABASE_URL` | `https://xxx.supabase.co` | Supabase API sahifasidan |
| `SUPABASE_KEY` | `eyJhbGci...` | **service_role** kaliti |
| `MOVIES_TABLE` | `movies` | ixtiyoriy (default: `movies`) |
| `LOG_LEVEL` | `INFO` | ixtiyoriy |

3. `PORT` ni **qo'lda qo'shmang** — Railway o'zi beradi.
4. Deploy: `railway.json` dagi `startCommand: python bot.py` avtomatik ishlaydi.
   Healthcheck `/health` manzilini tekshiradi (bot ichidagi aiohttp server javob beradi).

> ⚠️ Bitta bot tokeni bilan **ikkita** instansiya polling qilsa Telegram
> `409 Conflict` beradi. Yangi `bot.py` ni deploy qilishdan oldin eski
> `main.py` servisini to'xtating.

## 📦 Eski ma'lumotlarni ko'chirish

```bash
python scripts/migrate_json_to_supabase.py           # dry-run: nima ko'chishini ko'rsatadi
python scripts/migrate_json_to_supabase.py --apply   # haqiqatan yozadi (upsert, dublikatsiz)
```

## 📋 Buyruqlar

| Buyruq | Kim | Tavsif |
|---|---|---|
| `/start`, `/help` | hamma | Botni ishga tushirish |
| *(kod matni)* | hamma | Kino kodini yuborish → video keladi |
| *(video yuborish)* | admin | Kino qo'shish jarayonini boshlaydi |
| `/admin` | admin | Admin panel yordami |
| `/list` | admin | Oxirgi 20 ta kino |
| `/stats` | admin | Kinolar soni |
| `/delete` | admin | Kod bo'yicha o'chirish |
| `/cancel` | admin | FSM jarayonini bekor qilish |
