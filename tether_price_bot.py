"""
ربات تلگرام اعلام قیمت تتر (USDT)
این نسخه برای اجرا با GitHub Actions هست: هر بار که اجرا می‌شه،
یک پیام می‌فرسته و تموم می‌شه. زمان‌بندی (هر ۴ ساعت) رو خود
GitHub Actions (فایل .github/workflows/tether-price.yml) انجام می‌ده.

توکن و chat id از "GitHub Secrets" خونده می‌شن، نه از خود فایل،
چون این ریپازیتوری Public هست و نباید توکن واقعی توش دیده بشه.

نکته: چون سرورهای GitHub Actions نمی‌تونن به Nobitex وصل بشن،
قیمت تومانی به‌صورت تقریبی از نرخ جهانی دلار/ریال محاسبه می‌شه
(ممکنه با قیمت واقعی بازار آزاد ایران کمی فرق داشته باشه).
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


def get_toman_price(usd_price):
    """
    محاسبه‌ی تقریبی قیمت تتر به تومان، با استفاده از نرخ جهانی دلار/ریال
    (چون Nobitex از سرورهای GitHub Actions در دسترس نیست)
    """
    if usd_price is None:
        return None
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        response = requests.get(url, timeout=10)
        data = response.json()
        usd_to_rial = data["rates"]["IRR"]
        usd_to_toman = usd_to_rial / 10  # تبدیل ریال به تومان
        return round(usd_price * usd_to_toman)
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
    toman_price = get_toman_price(usd_price)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    message = f"📊 <b>گزارش قیمت تتر</b>\n🕒 {now}\n\n"

    if usd_price is not None:
        message += f"💵 قیمت دلاری: <b>{usd_price}$</b>\n"
    else:
        message += "💵 قیمت دلاری: دریافت نشد\n"

    if toman_price is not None:
        message += f"💰 قیمت تومانی (تقریبی): <b>{toman_price:,} تومان</b>\n"
    else:
        message += "💰 قیمت تومانی: دریافت نشد\n"

    send_telegram_message(message)
    print(f"[{now}] پیام ارسال شد.")


if __name__ == "__main__":
    build_and_send_report()
