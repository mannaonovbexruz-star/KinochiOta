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
│   ├── filters.py          # IsAdmin (egasi yoki baza) + IsOwner
│   ├── auth.py             # /admin — panel + parol bilan kirish
│   ├── panel.py            # panel matni + klaviaturasi
│   ├── keyboards.py        # inline tugmalar
│   ├── callbacks.py        # tugma bosishlari (IsAdmin bilan himoyalangan)
│   ├── states.py           # FSM state'lar (AddMovie, DeleteMovie)
│   ├── admin.py            # video -> kod -> nom -> Supabase
│   └── user.py             # /start, /id, kod bo'yicha qidiruv
│
├── tests/
│   ├── harness.py               # soxta Telegram sessiyasi (tarmoqsiz)
│   ├── test_admin_access.py     # begona odam admin qismiga kira olmasligi
│   └── test_admin_dashboard.py  # parol bilan kirish, rollar, panel
│
├── sql/
│   ├── schema.sql          # movies jadvali + indeks + RLS
│   └── 002_admins.sql      # admins jadvali
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
2. **SQL Editor** → `sql/schema.sql` ni **Run**, keyin `sql/002_admins.sql` ni **Run**
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
| `ADMIN_PASSWORD` | `kino2026` | ixtiyoriy; boshqa odam admin bo'lishi uchun |
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

## 👑 Adminlar tizimi

Ikki daraja bor:

| | **Egasi** (`ADMIN_ID` env) | **Admin** (parol bilan kirgan) |
|---|:---:|:---:|
| Qayerda saqlanadi | Railway env o'zgaruvchisi | `admins` jadvali |
| Kino qo'shish / o'chirish | ✅ | ✅ |
| Statistika, ro'yxat | ✅ | ✅ |
| Adminlarni ko'rish / o'chirish | ✅ | ❌ |
| O'chirib bo'ladimi | ❌ hech qachon | ✅ egasi o'chiradi |

**Boshqa odamni admin qilish:**

```
1. ADMIN_PASSWORD ni Railway Variables'ga qo'shasiz (masalan: kino2026)
2. Parolni o'sha odamga OG'ZAKI aytasiz (Telegram orqali emas!)
3. U botga yozadi:  /admin kino2026
   → "✅ Admin bo'ldingiz" + panel ochiladi
   → parol yozilgan xabar avtomatik o'chiriladi
4. Keyin u shunchaki /admin yozsa panel ochilaveradi (parolsiz)
```

**Adminni chiqarib yuborish:** `/admin` → 👥 Adminlar → ❌ o'chirish.

Brute-force himoyasi: 5 marta noto'g'ri parol → 15 daqiqa blok. Har bir urinish
Railway logiga `user_id` bilan yoziladi.

## 📋 Buyruqlar

| Buyruq | Kim | Tavsif |
|---|---|---|
| `/start`, `/help` | hamma | Botni ishga tushirish |
| `/id` | hamma | O'z ID'ingiz va admin holatingiz |
| *(kod matni)* | hamma | Kino kodini yuborish → video keladi |
| `/admin` | hamma | Admin bo'lsangiz panel, bo'lmasangiz parol so'raydi |
| `/admin <parol>` | hamma | Parol bilan admin bo'lish |
| *(video yuborish)* | admin | Kino qo'shish jarayonini boshlaydi |
| `/list`, `/stats` | admin | Ro'yxat va statistika |
| `/delete` | admin | Kod bo'yicha o'chirish |
| `/cancel` | admin | FSM jarayonini bekor qilish |

## 🧪 Testlar

```bash
python tests/test_admin_access.py      # begona odam kira olmasligi
python tests/test_admin_dashboard.py   # parol, rollar, panel tugmalari
```

Testlar tarmoqqa chiqmaydi — Telegram sessiyasi va Supabase to'liq soxta.
