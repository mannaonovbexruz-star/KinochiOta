"""Admin panelining ko'rinishi (matn + klaviatura).

Alohida modulda, chunki panelni ikki joydan chizamiz: `/admin` buyrug'i
(auth.py) va "⬅️ Orqaga" tugmasi (callbacks.py).
"""

import config
from handlers.keyboards import admin_menu
from database import movies as movies_db


async def render_panel(user_id: int) -> tuple[str, object]:
    """Panel matni va klaviaturasini qaytaradi."""
    owner = config.is_owner(user_id)

    try:
        total = await movies_db.count_movies()
        total_text = f"{total} ta kino"
    except Exception:  # noqa: BLE001 - baza tushsa ham panel ochilaversin
        total_text = "kinolar soni noma'lum"

    role = "👑 Egasi" if owner else "🛡 Admin"
    text = (
        "🛠 <b>Admin panel</b>\n\n"
        f"{role} · 🎬 {total_text}\n\n"
        "Kerakli amalni tanlang:"
    )
    return text, admin_menu(is_owner=owner)
