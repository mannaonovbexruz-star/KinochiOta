import json
import asyncio
import os

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


# =========================
# Health check server (Railway/Render health check uchun)
# =========================

from aiohttp import web

async def health(request):
    return web.Response(text="OK", status=200)

async def start_health_server():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🏥 Health check server running on port {PORT}")



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
# PREMIUM FILE
# =========================

PREMIUM_FILE = os.path.join(DATA_DIR, "premium_users.json")



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


    except:

        return []




def add_premium_user(user_id):

    users = get_premium_users()


    if user_id not in users:

        users.append(user_id)


        with open(
            PREMIUM_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                users,
                f
            )


        return True


    return False





def remove_premium_user(user_id):

    users = get_premium_users()


    if user_id in users:

        users.remove(user_id)


        with open(
            PREMIUM_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                users,
                f
            )


        return True


    return False




# =========================
# DATABASE
# =========================

DB_PATH = os.path.join(DATA_DIR, "database.json")

if not os.path.exists(DB_PATH):
    DB_PATH = "database.json"

with open(
    DB_PATH,
    "r",
    encoding="utf-8"
) as f:

    movies = json.load(f)


keyboard = InlineKeyboardMarkup(
    inline_keyboard=[

        [
            InlineKeyboardButton(
                text="📢 1-kanalga a'zo bo'lish",
                url="https://t.me/Pubbucfreefirealmaz"
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



        except Exception:

            return True



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


            except:

                pass



        else:


            await message.answer(

                "⚠️ Bu foydalanuvchi allaqachon Premium."

            )



    except:


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



    except:


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



        share = InlineKeyboardMarkup(

            inline_keyboard=[

                [

                    InlineKeyboardButton(

                        text="📤 Do'stlarga ulashish",

                        url=
                        f"https://t.me/share/url?"
                        f"url=https://t.me/{(await bot.get_me()).username}"
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
                                f"url=https://t.me/{(await bot.get_me()).username}"
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

async def set_menu():


    await bot.set_my_commands(

        [

            BotCommand(

                command="start",

                description="🏠 Botni ishga tushirish"

            ),


            BotCommand(

                command="buy",

                description="⭐ Premium sotib olish"

            )

        ]

    )








# =========================
# MAIN
# =========================

async def main():


    await set_menu()


    # Health check serverini ishga tushiramiz (Render uchun)

    await start_health_server()


    print("✅ Bot ishga tushdi...")


    await dp.start_polling(bot)





if __name__ == "__main__":

    asyncio.run(main())