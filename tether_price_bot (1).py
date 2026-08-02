"""
ربات تلگرام اعلام قیمت تتر (USDT)
این نسخه برای اجرا با GitHub Actions هست: هر بار که اجرا می‌شه،
یک پیام می‌فرسته و تموم می‌شه. زمان‌بندی (هر ۴ ساعت) رو خود
GitHub Actions (فایل .github/workflows/tether-price.yml) انجام می‌ده.

توکن و chat id از "GitHub Secrets" خونده می‌شن، نه از خود فایل،
چون این ریپازیتوری Public هست و نباید توکن واقعی توش دیده بشه.
"""

import os
import requests
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")


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


def get_toman_price():
    """گرفتن قیمت تومانی تتر از نوبیتکس"""
    try:
        url = "https://api.nobitex.ir/market/stats"
        params = {"srcCurrency": "usdt", "dstCurrency": "rls"}
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        rial_price = float(data["stats"]["usdt-rls"]["latest"])
        toman_price = rial_price / 10  # تبدیل ریال به تومان
        return round(toman_price)
    except Exception as e:
        print(f"خطا در گرفتن قیمت تومانی: {e}")
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
    toman_price = get_toman_price()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    message = f"📊 <b>گزارش قیمت تتر</b>\n🕒 {now}\n\n"

    if usd_price is not None:
        message += f"💵 قیمت دلاری: <b>{usd_price}$</b>\n"
    else:
        message += "💵 قیمت دلاری: دریافت نشد\n"

    if toman_price is not None:
        message += f"💰 قیمت تومانی (نوبیتکس): <b>{toman_price:,} تومان</b>\n"
    else:
        message += "💰 قیمت تومانی: دریافت نشد\n"

    send_telegram_message(message)
    print(f"[{now}] پیام ارسال شد.")


if __name__ == "__main__":
    build_and_send_report()
