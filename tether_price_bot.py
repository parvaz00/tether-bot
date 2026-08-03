"""
ربات تلگرام اعلام قیمت تتر + طلای ۱۸ عیار + انس جهانی طلا
این نسخه برای اجرا با GitHub Actions هست: هر بار که اجرا می‌شه،
یک پیام می‌فرسته و تموم می‌شه. زمان‌بندی رو خود GitHub Actions
(فایل .github/workflows/tether-price.yml) انجام می‌ده.

توکن، chat id و کلید BrsApi از "GitHub Secrets" خونده می‌شن.
"""

import os
import requests
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
BRSAPI_KEY = os.environ.get("BRSAPI_KEY")

BRSAPI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}

_brsapi_cache = None  # برای اینکه فقط یک‌بار درخواست به BrsApi بزنیم


def get_usd_price():
    """گرفتن قیمت جهانی تتر به دلار از CoinGecko"""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": "tether", "vs_currencies": "usd"}
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        return data["tether"]["usd"]
    except Exception as e:
        print(f"خطا در گرفتن قیمت دلاری: {e}")
        return None


def get_brsapi_data():
    """گرفتن و کش کردن کل پاسخ BrsApi (شامل ارز، طلا و رمزارز)"""
    global _brsapi_cache
    if _brsapi_cache is not None:
        return _brsapi_cache
    if not BRSAPI_KEY:
        print("خطا: BRSAPI_KEY تنظیم نشده")
        return None
    try:
        url = "https://Api.BrsApi.ir/Market/Gold_Currency.php"
        params = {"key": BRSAPI_KEY}
        response = requests.get(url, params=params, headers=BRSAPI_HEADERS, timeout=15)
        data = response.json()
        print("پاسخ خام BrsApi:", data)

        candidates = []
        if isinstance(data, dict):
            for value in data.values():
                if isinstance(value, list):
                    candidates.extend(value)
        elif isinstance(data, list):
            candidates = data

        _brsapi_cache = candidates
        return candidates
    except Exception as e:
        print(f"خطا در گرفتن اطلاعات از BrsApi: {e}")
        return None


def find_price(candidates, symbol_keywords=None, name_keywords=None):
    """پیدا کردن قیمت یک آیتم بر اساس نماد یا اسم، تو لیست داده‌های BrsApi"""
    if not candidates:
        return None
    symbol_keywords = [s.upper() for s in (symbol_keywords or [])]
    name_keywords = name_keywords or []

    for item in candidates:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol", "")).upper()
        name = str(item.get("name", ""))
        name_en = str(item.get("name_en", "")).lower()

        symbol_match = any(k in symbol for k in symbol_keywords)
        name_match = any(k in name or k.lower() in name_en for k in name_keywords)

        if symbol_match or name_match:
            price = item.get("price") or item.get("price_toman") or item.get("close")
            if price:
                try:
                    return round(float(price))
                except (TypeError, ValueError):
                    continue
    return None


def get_toman_price(usd_price):
    """قیمت تومانی تتر"""
    if usd_price is None:
        return None
    candidates = get_brsapi_data()
    return find_price(candidates, symbol_keywords=["USDT"], name_keywords=["تتر", "Tether"])


def get_gold_18k_price():
    """قیمت طلای ۱۸ عیار (هر گرم، به تومان)"""
    candidates = get_brsapi_data()
    return find_price(
        candidates,
        symbol_keywords=["IR_GOLD_18K", "GERAM18", "GOLD18"],
        name_keywords=["طلای 18 عیار", "طلا 18 عیار", "18 عیار", "18K Gold"],
    )


def get_gold_ounce_price():
    """قیمت انس جهانی طلا (به دلار)"""
    candidates = get_brsapi_data()
    return find_price(
        candidates,
        symbol_keywords=["XAUUSD", "XAU", "ONS"],
        name_keywords=["انس طلا", "انس جهانی", "Gold Ounce"],
    )


def send_telegram_message(text):
    """ارسال پیام به تلگرام"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code != 200:
            print(f"خطا در ارسال پیام: {response.text}")
    except Exception as e:
        print(f"خطا در ارسال پیام: {e}")


def build_and_send_report():
    if not BOT_TOKEN or not CHAT_ID:
        print("خطا: BOT_TOKEN یا CHAT_ID تنظیم نشده (باید تو GitHub Secrets اضافه بشن)")
        return

    usd_price = get_usd_price()
    toman_price = get_toman_price(usd_price)
    gold18_price = get_gold_18k_price()
    ounce_price = get_gold_ounce_price()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    message = f"📊 <b>گزارش بازار</b>\n🕒 {now}\n\n"

    message += "💠 <b>تتر (USDT)</b>\n"
    if usd_price is not None:
        message += f"💵 دلاری: <b>{usd_price}$</b>\n"
    else:
        message += "💵 دلاری: دریافت نشد\n"
    if toman_price is not None:
        message += f"💰 تومانی: <b>{toman_price:,} تومان</b>\n"
    else:
        message += "💰 تومانی: دریافت نشد\n"

    message += "\n🥇 <b>طلا</b>\n"
    if gold18_price is not None:
        message += f"🔸 هر گرم طلای ۱۸ عیار: <b>{gold18_price:,} تومان</b>\n"
    else:
        message += "🔸 طلای ۱۸ عیار: دریافت نشد\n"
    if ounce_price is not None:
        message += f"🔸 انس جهانی طلا: <b>{ounce_price:,}$</b>\n"
    else:
        message += "🔸 انس جهانی طلا: دریافت نشد\n"

    send_telegram_message(message)
    print(f"[{now}] پیام ارسال شد.")


if __name__ == "__main__":
    build_and_send_report()
