"""
ربات تلگرام - دکمه دستی قیمت بازار
وقتی دکمه "📊 قیمت بازار" زده می‌شه، GitHub Actions workflow رو trigger می‌کنه
که قیمت‌ها رو از BrsApi می‌گیره و عکس می‌فرسته.
"""

import os
import time
import requests

BOT_TOKEN  = os.environ.get("BOT_TOKEN")
GH_TOKEN   = os.environ.get("GH_TOKEN")
GH_REPO    = "parvaz00/tether-bot"

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def trigger_price_workflow():
    """trigger کردن workflow قیمت از گیت‌هاب"""
    url = f"https://api.github.com/repos/{GH_REPO}/actions/workflows/tether-price.yml/dispatches"
    headers = {
        "Authorization": f"token {GH_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {"ref": "main"}
    r = requests.post(url, json=data, headers=headers, timeout=10)
    return r.status_code == 204


def send_message(chat_id, text, reply_markup=None):
    import json
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{BASE_URL}/sendMessage", data=payload, timeout=10)


def get_keyboard():
    return {
        "keyboard": [[{"text": "📊 قیمت بازار"}]],
        "resize_keyboard": True,
        "persistent": True
    }


def handle_update(update):
    msg = update.get("message", {})
    if not msg:
        return
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "")

    if text in ["/start", "start"]:
        send_message(chat_id,
            "سلام! 👋\nبرای دریافت قیمت‌های لحظه‌ای روی دکمه زیر بزن 👇",
            reply_markup=get_keyboard())

    elif text == "📊 قیمت بازار":
        send_message(chat_id, "⏳ در حال دریافت قیمت‌ها، لطفاً ۳۰ ثانیه صبر کن...")
        ok = trigger_price_workflow()
        if not ok:
            send_message(chat_id, "❌ خطا در دریافت قیمت‌ها. دوباره امتحان کن.")


def get_updates(offset=None):
    params = {"timeout": 30, "allowed_updates": ["message"]}
    if offset:
        params["offset"] = offset
    try:
        r = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=35)
        return r.json().get("result", [])
    except:
        return []


def main():
    print("ربات روشن شد...")
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates:
            handle_update(update)
            offset = update["update_id"] + 1
        time.sleep(1)


if __name__ == "__main__":
    main()
