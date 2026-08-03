"""
ربات تلگرام اعلام قیمت تتر (USDT)
این نسخه برای اجرا با GitHub Actions هست: هر بار که اجرا می‌شه،
یک پیام می‌فرسته و تموم می‌شه. زمان‌بندی (هر ۴ ساعت) رو خود
GitHub Actions (فایل .github/workflows/tether-price.yml) انجام می‌ده.

توکن، chat id و کلید BrsApi از "GitHub Secrets" خونده می‌شن، نه از
خود فایل، چون این ریپازیتوری Public هست.

منبع قیمت تومانی: BrsApi.ir (یک سرویس اطلاع‌رسانی عمومی قیمت طلا/ارز/
رمزارز، نه یک صرافی) که باید از سرورهای GitHub Actions در دسترس باشه.
اگه به هر دلیلی این منبع کار نکرد، به‌صورت خودکار قیمت تومانی خالی
گذاشته می‌شه ولی قیمت دلاری همچنان ارسال می‌شه.
"""

import os
import requests
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
BRSAPI_KEY = os.environ.get("BRSAPI_KEY")


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


def get_toman_price_from_brsapi():
    """
    گرفتن قیمت تومانی تتر از BrsApi.ir
    این تابع چند حالت مختلف از ساختار JSON رو امتحان می‌کنه، چون
    ساختار دقیق پاسخ ممکنه کمی متفاوت باشه.
    """
    if not BRSAPI_KEY:
        print("خطا: BRSAPI_KEY تنظیم نشده")
        return None
    try:
        url = "https://Api.BrsApi.ir/Market/Gold_Currency.php"
        params = {"key": BRSAPI_KEY}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }
        response = requests.get(url, params=params, headers=headers, timeout=15)
        data = response.json()

        # چاپ کامل پاسخ خام تو لاگ، تا در صورت خطا بشه ساختار دقیق رو دید
        print("پاسخ خام BrsApi:", data)

        # ممکنه دیتا به شکل یه دیکشنری با کلید cryptocurrency باشه یا یه لیست ساده
        candidates = []
        if isinstance(data, dict):
            for value in data.values():
                if isinstance(value, list):
                    candidates.extend(value)
        elif isinstance(data, list):
            candidates = data

        for item in candidates:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("symbol", "")).upper()
            name = str(item.get("name", "")).lower()
            name_en = str(item.get("name_en", "")).lower()
            if "USDT" in symbol or "تتر" in name or "tether" in name_en:
                price = item.get("price") or item.get("price_toman") or item.get("close")
                if price:
                    return round(float(price))

        print("تتر تو پاسخ BrsApi پیدا نشد.")
        return None
    except Exception as e:
        print(f"خطا در گرفتن قیمت تومانی از BrsApi: {e}")
        return None


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
    toman_price = get_toman_price_from_brsapi()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    message = f"📊 <b>گزارش قیمت تتر</b>\n🕒 {now}\n\n"

    if usd_price is not None:
        message += f"💵 قیمت دلاری: <b>{usd_price}$</b>\n"
    else:
        message += "💵 قیمت دلاری: دریافت نشد\n"

    if toman_price is not None:
        message += f"💰 قیمت تومانی: <b>{toman_price:,} تومان</b>\n"
    else:
        message += "💰 قیمت تومانی: دریافت نشد\n"

    send_telegram_message(message)
    print(f"[{now}] پیام ارسال شد.")


if __name__ == "__main__":
    build_and_send_report()
