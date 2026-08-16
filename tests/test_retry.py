"""`with_retry` testi — Supabase'ning uzilib qoladigan ulanishi uchun.

Supabase server har javobdan keyin HTTP/2 GOAWAY yuboradi. httpx o'sha
ulanishni qayta ishlatmoqchi bo'lganda RemoteProtocolError chiqadi, keyingi
urinishda esa yangi ulanish ochilib, so'rov muvaffaqiyatli o'tadi.

Ishga tushirish:
    python tests/test_retry.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")

import httpx  # noqa: E402

from database.client import with_retry  # noqa: E402

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"   PASS  {name}")
    else:
        print(f"   FAIL  {name}  -> {detail}")
        FAILURES.append(name)


def main() -> None:
    print("\n[1] Bir marta uzilib, keyin o'tadigan so'rov:")
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise httpx.RemoteProtocolError("<ConnectionTerminated error_code:0>")
        return "natija"

    result = with_retry(flaky)
    check("natija qaytdi", result == "natija", str(result))
    check("2 marta chaqirildi", len(calls) == 2, f"{len(calls)} marta")

    print("\n[2] Har safar uzilsa — xato ko'tariladi (jimgina yutilmaydi):")
    always_calls = []

    def always_fails():
        always_calls.append(1)
        raise httpx.RemoteProtocolError("<ConnectionTerminated>")

    try:
        with_retry(always_fails)
        check("xato ko'tarildi", False, "xato chiqmadi")
    except httpx.RemoteProtocolError:
        check("xato ko'tarildi", True)
    check("3 marta urindi", len(always_calls) == 3, f"{len(always_calls)} marta")

    print("\n[3] Boshqa xatolar qayta urinilmaydi (darrov ko'tariladi):")
    other_calls = []

    def bad_request():
        other_calls.append(1)
        raise ValueError("noto'g'ri so'rov")

    try:
        with_retry(bad_request)
        check("darrov ko'tarildi", False, "xato chiqmadi")
    except ValueError:
        check("darrov ko'tarildi", True)
    check("1 marta urindi", len(other_calls) == 1, f"{len(other_calls)} marta")

    print("\n[4] Argumentlar uzatiladi:")
    check("argumentlar", with_retry(lambda a, b=0: a + b, 2, b=3) == 5)

    print()
    if FAILURES:
        print(f"XATO: {len(FAILURES)} ta test yiqildi: {FAILURES}")
        sys.exit(1)
    print("HAMMA TEST O'TDI")


if __name__ == "__main__":
    main()
