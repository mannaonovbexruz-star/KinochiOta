from aiogram.fsm.state import State, StatesGroup


class AddMovie(StatesGroup):
    """Kino qo'shish ketma-ketligi.

    Admin video tashlaydi -> file_id saqlanadi -> kod so'raladi ->
    nom so'raladi -> Supabase'ga yoziladi.
    """

    waiting_for_code = State()
    waiting_for_title = State()


class DeleteMovie(StatesGroup):
    """/delete buyrug'i uchun: qaysi kodni o'chirish kerakligini so'raydi."""

    waiting_for_code = State()


class AddChannel(StatesGroup):
    """Majburiy obuna kanalini qo'shish (faqat egasi)."""

    waiting_for_channel = State()


class AddAdmin(StatesGroup):
    """Paneldan user_id orqali admin qo'shish (faqat egasi)."""

    waiting_for_id = State()
