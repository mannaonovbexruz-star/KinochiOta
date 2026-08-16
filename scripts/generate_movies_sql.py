"""`database.json` dan Supabase uchun tayyor INSERT SQL yasaydi.

Supabase kaliti kerak emas — natijani SQL Editor'ga paste qilasiz.

Ishlatish:
    python scripts/generate_movies_sql.py
    -> sql/003_movies_data.sql
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = ("database.json", "data/database.json")
OUTPUT = os.path.join(ROOT, "sql", "003_movies_data.sql")


def sql_escape(value: str) -> str:
    """Postgres literal: bitta tirnoq ikkilantiriladi ('O''zbek)."""
    return value.replace("'", "''")


def main() -> None:
    merged: dict[str, dict] = {}
    for name in SOURCES:
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Keyingi fayl oldingisini to'ldiradi, mavjudini o'zgartirmaydi
        for code, item in data.items():
            if isinstance(item, dict) and item.get("file_id") and code not in merged:
                merged[code] = item
        print(f"📂 {name}: {len(data)} ta")

    if not merged:
        print("❌ Hech qanday kino topilmadi.", file=sys.stderr)
        sys.exit(1)

    # Kodlarni raqam bo'yicha tartiblash (1, 2, 9, 11, ... 100)
    def sort_key(code: str):
        return (0, int(code)) if code.isdigit() else (1, code)

    rows = []
    for code in sorted(merged, key=sort_key):
        item = merged[code]
        title = (item.get("name") or f"Kino {code}").strip()
        rows.append(
            f"    ('{sql_escape(code.strip())}', "
            f"'{sql_escape(item['file_id'])}', "
            f"'{sql_escape(title)}')"
        )

    sql = f"""-- =====================================================
-- 003: ESKI database.json DAGI KINOLAR ({len(rows)} ta)
-- Supabase -> SQL Editor -> New query -> paste -> Run
--
-- `on conflict do nothing`: mavjud kodlar tegilmaydi, shuning uchun
-- bu faylni bir necha marta ishga tushirish xavfsiz (dublikat bo'lmaydi).
-- =====================================================

insert into public.movies (movie_code, file_id, title)
values
{",\n".join(rows)}
on conflict (movie_code) do nothing;

-- Tekshirish
select count(*) as jami_kinolar from public.movies;
"""

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(sql)

    print(f"✅ {len(rows)} ta kino yozildi: sql/003_movies_data.sql")


if __name__ == "__main__":
    main()
