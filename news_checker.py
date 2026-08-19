"""
news_checker.py
این اسکریپت هر بار که اجرا میشه (توسط GitHub Actions هر ۵ دقیقه):
1. چک می‌کنه آیا کاربر روی دکمه‌ی "ارسال اخبار روز" زده یا دستور /news فرستاده
2. اگر حالت اخبار "روشن" باشه، فیدهای رویترز و WSJ رو چک می‌کنه
   و خبرهای جدید (که قبلاً نفرستاده) رو به تلگرام می‌فرسته
"""

import os
import json
import time
import re
import requests
import xml.etree.ElementTree as ET
from html import unescape

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
STATE_FILE = "news_state.json"

RSS_FEEDS = {
    "رویترز": "https://news.google.com/rss/search?q=site:reuters.com&hl=en-US&gl=US&ceid=US:en",
    "وال استریت ژورنال": "https://news.google.com/rss/search?q=site:wsj.com&hl=en-US&gl=US&ceid=US:en",
}

# نام نمایشی: یوزرنیم کانال (بدون @)
TELEGRAM_CHANNELS = {
    "کانال Last News": "lastnews",
    "کانال کارگشا": "kargosha",
    "کانال News1Fori": "News1Fori",
    "کانال بهنام صمدی": "BehnamSamadi_ir",
    "کانال Update World News": "updateworlddnews",
    "کانال توییتر بورس": "twitter_bourse",
}

API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"news_mode": False, "sent_ids": [], "last_update_id": 0}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def send_message(text, reply_markup=None):
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": False,
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(f"{API}/sendMessage", data=payload, timeout=15)
    except Exception as e:
        print(f"خطا در ارسال پیام: {e}")


def send_photo(photo_url, caption):
    payload = {
        "chat_id": CHAT_ID,
        "photo": photo_url,
        "caption": caption[:1024],  # محدودیت تلگرام برای کپشن عکس
    }
    try:
        resp = requests.post(f"{API}/sendPhoto", data=payload, timeout=20)
        if not resp.json().get("ok"):
            # اگه ارسال با لینک عکس شکست خورد (مثلاً تلگرام نتونه لینک رو باز کنه)، پیام متنی بفرست
            print(f"خطا در ارسال عکس، برگشت به متن: {resp.text}")
            send_message(f"{caption}\n\n🖼 {photo_url}")
    except Exception as e:
        print(f"خطا در ارسال عکس: {e}")
        send_message(f"{caption}\n\n🖼 {photo_url}")


# دکمه‌ی ثابت پایین چت (کنار دکمه‌ی قیمت‌ها)
NEWS_BUTTON_TEXT = "📰 اخبار روز"
MAIN_KEYBOARD = {
    "keyboard": [
        [{"text": "📊 دریافت قیمت‌ها"}],
        [{"text": NEWS_BUTTON_TEXT}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}


def process_updates(state):
    """چک کردن پیام‌ها و دکمه‌های زده‌شده از آخرین باری که اسکریپت اجرا شد"""
    try:
        resp = requests.get(
            f"{API}/getUpdates",
            params={"offset": state["last_update_id"] + 1, "timeout": 0},
            timeout=15,
        )
        print(f"DEBUG status_code={resp.status_code}")
        print(f"DEBUG raw_response={resp.text}")
        updates = resp.json().get("result", [])
    except Exception as e:
        print(f"خطا در گرفتن آپدیت‌ها: {e}")
        return state

    for update in updates:
        state["last_update_id"] = update["update_id"]

        message = update.get("message")
        if not message:
            continue

        text = message.get("text", "").strip()

        if text == "/start":
            send_message("خوش اومدی! از دکمه‌های پایین استفاده کن:", MAIN_KEYBOARD)

        elif text in ("/news", NEWS_BUTTON_TEXT):
            state["news_mode"] = not state["news_mode"]
            if state["news_mode"]:
                send_message("🟢 اخبار روز روشن شد؛ در حال بررسی اخبار جدید...", MAIN_KEYBOARD)
            else:
                send_message("🔴 اخبار روز خاموش شد.", MAIN_KEYBOARD)

    return state


def strip_html(text):
    text = re.sub("<[^<]+?>", "", text or "")
    return unescape(text).strip()


def translate_text(text):
    """ترجمه‌ی متن انگلیسی به فارسی. اگه ترجمه شکست بخوره، خود متن اصلی رو برمی‌گردونه."""
    if not text:
        return text
    try:
        resp = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "en", "tl": "fa", "dt": "t", "q": text},
            timeout=10,
        )
        data = resp.json()
        return "".join(segment[0] for segment in data[0] if segment[0])
    except Exception as e:
        print(f"خطا در ترجمه: {e}")
        return text


def fetch_feed_items(url):
    items = []
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(resp.content)
        for item in root.findall(".//item")[:10]:
            title = strip_html(item.findtext("title", ""))
            link = item.findtext("link", "") or ""
            desc = strip_html(item.findtext("description", ""))[:220]
            guid = item.findtext("guid", link) or link
            if title and link:
                items.append({"id": guid, "title": title, "link": link, "desc": desc})
    except Exception as e:
        print(f"خطا در خوندن فید {url}: {e}")
    return items


def fetch_telegram_channel_items(username):
    """خوندن مستقیم آخرین پست‌های عمومی یک کانال تلگرام از t.me/s/username"""
    items = []
    try:
        resp = requests.get(
            f"https://t.me/s/{username}",
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        html = resp.text

        # هر پست رو از جایی که data-post شروع میشه تا شروع پست بعدی جدا می‌کنیم
        blocks = re.split(r'(?=data-post="' + re.escape(username) + r'/\d+")', html)
        print(f"DEBUG telegram {username}: found {len(blocks)} raw blocks")

        posts = []
        for block in blocks:
            id_match = re.search(r'data-post="' + re.escape(username) + r'/(\d+)"', block)
            if not id_match:
                continue
            post_id = id_match.group(1)

            text_match = re.search(
                r'tgme_widget_message_text[^>]*>(.*?)</div>', block, flags=re.DOTALL
            )
            raw_text = text_match.group(1) if text_match else ""
            text = strip_html(raw_text).replace("<br>", "\n")[:900]

            photo_match = re.search(
                r'tgme_widget_message_photo_wrap[^"]*"\s+style="[^"]*background-image:\s*url\([\'"]?([^\'")]+)[\'"]?\)',
                block,
            )
            photo_url = unescape(photo_match.group(1)) if photo_match else None

            posts.append((post_id, text, photo_url))

        for post_id, text, photo_url in posts[-5:]:
            if not text and not photo_url:
                continue
            items.append(
                {
                    "id": f"tg-{username}-{post_id}",
                    "title": "",
                    "link": f"https://t.me/{username}/{post_id}",
                    "desc": text,
                    "photo_url": photo_url,
                }
            )
    except Exception as e:
        print(f"خطا در خوندن کانال {username}: {e}")
    return items


def check_and_send_news(state):
    if not state["news_mode"]:
        return state

    sent = set(state["sent_ids"])
    new_sent = list(state["sent_ids"])

    for source_name, feed_url in RSS_FEEDS.items():
        for item in fetch_feed_items(feed_url):
            if item["id"] in sent:
                continue
            title_fa = translate_text(item["title"])
            desc_fa = translate_text(item["desc"])
            text = f"📰 {source_name}\n\n{title_fa}\n\n{desc_fa}"
            send_message(text)
            new_sent.append(item["id"])
            sent.add(item["id"])
            time.sleep(1)

    for source_name, username in TELEGRAM_CHANNELS.items():
        for item in fetch_telegram_channel_items(username):
            if item["id"] in sent:
                continue
            text = f"📰 {source_name}\n\n{item['desc']}"
            if item.get("photo_url"):
                send_photo(item["photo_url"], text)
            else:
                send_message(text)
            new_sent.append(item["id"])
            sent.add(item["id"])
            time.sleep(1)

    # فقط ۳۰۰ تای آخر رو نگه دار تا فایل بزرگ نشه
    state["sent_ids"] = new_sent[-300:]
    return state


def main():
    state = load_state()
    state = process_updates(state)
    state = check_and_send_news(state)
    save_state(state)


if __name__ == "__main__":
    main()
