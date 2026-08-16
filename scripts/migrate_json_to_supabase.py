"""Eski `database.json` dagi kinolarni Supabase'ga ko'chiradi.

Ishlatish:
    python scripts/migrate_json_to_supabase.py            # ko'rib chiqish (dry-run)
    python scripts/migrate_json_to_supabase.py --apply    # haqiqatan yozish

Eski format:
    {"1": {"file_id": "...", "name": "🎬 Labirint", ...}, ...}
Yangi jadval: movies(movie_code, file_id, title)
"""

import json
import os
import sys

# Loyiha ildizini import yo'liga qo'shamiz (scripts/ ichidan ishga tushirilganda)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from database.client import get_client  # noqa: E402

JSON_CANDIDATES = ("data/database.json", "database.json")


def load_movies() -> dict:
    for path in JSON_CANDIDATES:
        if os.path.exists(path):
            print(f"📂 Manba: {path}")
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    print("❌ database.json topilmadi.", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    apply_changes = "--apply" in sys.argv
    config.validate()

    data = load_movies()
    rows = []
    skipped = []

    for code, item in data.items():
        if not isinstance(item, dict) or not item.get("file_id"):
            skipped.append(code)
            continue
        rows.append(
            {
                "movie_code": str(code).strip(),
                "file_id": item["file_id"],
                "title": (item.get("name") or f"Kino {code}").strip(),
            }
        )

    print(f"✅ Ko'chirishga tayyor: {len(rows)} ta")
    if skipped:
        print(f"⚠️ O'tkazib yuborildi (file_id yo'q): {skipped}")

    if not apply_changes:
        for row in rows[:5]:
            print(f"   {row['movie_code']:>4} | {row['title']}")
        print("\nℹ️ Bu dry-run edi. Yozish uchun: --apply flagi bilan qayta ishga tushiring.")
        return

    table = get_client().table(config.MOVIES_TABLE)

    # upsert: mavjud movie_code bo'lsa yangilaydi, yo'q bo'lsa qo'shadi.
    # Skriptni bir necha marta ishga tushirsa ham dublikat bo'lmaydi.
    inserted = 0
    for start in range(0, len(rows), 100):  # partiyalarga bo'lib yuboramiz
        chunk = rows[start : start + 100]
        table.upsert(chunk, on_conflict="movie_code").execute()
        inserted += len(chunk)
        print(f"   ⬆️ {inserted}/{len(rows)}")

    print(f"🎉 Tayyor! {inserted} ta kino Supabase'ga ko'chirildi.")


if __name__ == "__main__":
    main()
