"""`sql/schema.sql` ni Supabase bazasiga tushiradi.

Kerak: .env faylida SUPABASE_DB_URL (Supabase -> Connect -> Session pooler URI).

Ishlatish:
    python scripts/apply_schema.py
"""

import os
import sys

import psycopg2
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"))

SCHEMA_PATH = os.path.join(ROOT, "sql", "schema.sql")


def main() -> None:
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        print("❌ .env faylida SUPABASE_DB_URL yo'q.", file=sys.stderr)
        print("💡 Supabase -> Connect -> Session pooler -> URI ni nusxalang.", file=sys.stderr)
        sys.exit(1)

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    print(f"🔌 Ulanmoqda: {db_url.split('@')[-1]}")  # parolni logga chiqarmaymiz
    conn = psycopg2.connect(db_url)
    try:
        # schema.sql butunligicha bitta tranzaksiyada — xato bo'lsa hech narsa qolmaydi
        with conn, conn.cursor() as cur:
            cur.execute(schema_sql)

            cur.execute("""
                select column_name, data_type
                from information_schema.columns
                where table_schema = 'public' and table_name = 'movies'
                order by ordinal_position
            """)
            columns = cur.fetchall()

            cur.execute("select count(*) from public.movies")
            total = cur.fetchone()[0]
    finally:
        conn.close()

    if not columns:
        print("❌ `movies` jadvali yaratilmadi.", file=sys.stderr)
        sys.exit(1)

    print("✅ `movies` jadvali tayyor:")
    for name, dtype in columns:
        print(f"   {name:<12} {dtype}")
    print(f"📊 Hozirgi qatorlar soni: {total}")


if __name__ == "__main__":
    main()
