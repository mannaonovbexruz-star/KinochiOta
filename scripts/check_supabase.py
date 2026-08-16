"""Supabase ulanishini tekshiradi: kalit turi, jadvallar, o'qish huquqi.

Botning o'zi qanday o'qisa, xuddi shunday o'qiydi — shuning uchun natija
"bot nimani ko'radi" degan savolga aniq javob beradi.

Ishlatish:
    python scripts/check_supabase.py
"""

import base64
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import config  # noqa: E402


def key_role(key: str) -> str:
    """Kalit turini aniqlaydi — KALITNING O'ZI hech qayerga chiqmaydi.

    Supabase'da ikki avlod kalit bor:
      eski (JWT):  eyJhbGci...  -> ichida "role": "anon" | "service_role"
      yangi:       sb_secret_...      (service_role o'rnini bosadi)
                   sb_publishable_... (anon o'rnini bosadi)
    """
    if key.startswith("sb_secret_"):
        return "service_role"
    if key.startswith("sb_publishable_"):
        return "anon"

    try:
        payload = key.split(".")[1]
        payload += "=" * (-len(payload) % 4)  # base64 padding
        data = json.loads(base64.urlsafe_b64decode(payload))
        return data.get("role", "noma'lum")
    except Exception:
        return "o'qib bo'lmadi (JWT ham, sb_ ham emas)"


def main() -> None:
    print("=" * 55)
    print("SUPABASE DIAGNOSTIKASI")
    print("=" * 55)

    if not config.SUPABASE_URL or not config.SUPABASE_KEY:
        print("\n❌ .env da SUPABASE_URL yoki SUPABASE_KEY yo'q.")
        sys.exit(1)

    print(f"\n🔗 URL:  {config.SUPABASE_URL}")

    role = key_role(config.SUPABASE_KEY)
    print(f"🔑 Kalit turi:  {role}")
    if role == "service_role":
        print("   ✅ To'g'ri — RLS'ni chetlab o'tadi")
    elif role == "anon":
        print("   ❌ NOTO'G'RI — RLS yoqilgan jadvallardan HECH NARSA o'qiy olmaydi")
    else:
        print("   ⚠️ Kutilmagan qiymat")

    # Botning o'zi qanday so'rasa — shunday: with_retry bilan
    from database.client import get_client, with_retry

    client = get_client()

    print("\n📊 Jadvallar (bot ko'rgan holicha):")
    for table in ("movies", "admins"):
        try:
            resp = with_retry(
                lambda: client.table(table).select("*", count="exact").limit(3).execute()
            )
            count = resp.count if resp.count is not None else len(resp.data or [])
            print(f"   {table:8} → {count} ta qator")
            for row in (resp.data or [])[:3]:
                if table == "movies":
                    print(f"              {row['movie_code']:>4} — {row['title'][:40]}")
                else:
                    print(f"              {row['user_id']} — {row.get('username')}")
        except Exception as exc:  # noqa: BLE001
            print(f"   {table:8} → ❌ XATO: {exc}")

    print("\n🎬 Bot kino qidirganda (kod '1'):")
    try:
        resp = with_retry(
            lambda: client.table("movies").select("*").eq("movie_code", "1").limit(1).execute()
        )
        rows = resp.data or []
        print(f"   {'✅ topildi: ' + rows[0]['title'] if rows else '❌ TOPILMADI'}")
    except Exception as exc:  # noqa: BLE001
        print(f"   ❌ XATO: {exc}")

    print("\n" + "=" * 55)
    if role == "anon":
        print("XULOSA: SUPABASE_KEY ni service_role kalitiga almashtiring")
        print("        (Supabase → Settings → API → service_role secret)")
        print("        .env da HAM, Railway Variables'da HAM.")
    print("=" * 55)


if __name__ == "__main__":
    main()
