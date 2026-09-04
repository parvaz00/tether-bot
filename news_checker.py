"""
news_checker.py
این اسکریپت هر بار که اجرا میشه (توسط GitHub Actions هر ۵ دقیقه):
1. چک می‌کنه آیا کاربر روی دکمه‌ی "ارسال اخبار روز" زده یا دستور /news فرستاده
2. اگر حالت اخبار "روشن" باشه، منابع RSS انگلیسی و کانال‌های تلگرام رو چک می‌کنه،
   با هوش مصنوعی (DeepSeek از طریق AvalAI) تگ‌گذاری و ترجمه می‌کنه،
   و فقط خبرهای مرتبط و جدید رو به تلگرام می‌فرسته
"""

import os
import json
import time
import re
import requests
import xml.etree.ElementTree as ET
from html import unescape, escape as html_escape

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
AVALAI_API_KEY = os.environ.get("AVALAI_API_KEY")
STATE_FILE = "news_state.json"

TAGS = [
    "اقتصادی",
    "جنگ",
    "بازار مالی داخلی",
    "توییت بزرگان بازار مالی و سیاستمداران و بیانیه سران",
    "ارز دیجیتال",
    "انس طلا و نقره و مس و روی",
]

TAG_PROMPT = (
    "تو یک تحلیلگر خبری حوزه‌ی بازار مالی هستی. متن خبر زیر رو بخون و مشخص کن "
    "دقیقاً به کدوم یک یا چندتا از این تگ‌ها مربوطه:\n"
    + "\n".join(f"- {t}" for t in TAGS)
    + "\n\nفقط اسم تگ‌های مرتبط رو با کاما (,) از هم جدا کن و بنویس، بدون هیچ توضیح اضافه. "
    "اگه خبر به هیچ‌کدوم از این تگ‌ها مربوط نبود، فقط بنویس: هیچکدام"
)

RSS_FEEDS = {
    "رویترز": "https://news.google.com/rss/search?q=site:reuters.com&hl=en-US&gl=US&ceid=US:en",
    "وال استریت ژورنال": "https://news.google.com/rss/search?q=site:wsj.com&hl=en-US&gl=US&ceid=US:en",
    "SEC": "https://www.sec.gov/news/pressreleases.rss",
    "یاهو فایننس": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC&region=US&lang=en-US",
    "کوین‌دسک": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "کریپتو نیوز": "https://crypto.news/feed/",
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
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(f"{API}/sendMessage", data=payload, timeout=15)
    except Exception as e:
        print(f"خطا در ارسال پیام: {e}")


def send_photo(photo_url, body_text, url=None):
    link_part = link_line(url)
    max_body = 1024 - len(link_part)
    caption = body_text[:max_body] + link_part
    payload = {
        "chat_id": CHAT_ID,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML",
    }
    try:
        resp = requests.post(f"{API}/sendPhoto", data=payload, timeout=20)
        if not resp.json().get("ok"):
            # اگه ارسال با لینک عکس شکست خورد (مثلاً تلگرام نتونه لینک رو باز کنه)، پیام متنی بفرست
            print(f"خطا در ارسال عکس، برگشت به متن: {resp.text}")
            send_message(f"{body_text}{link_part}")
    except Exception as e:
        print(f"خطا در ارسال عکس: {e}")
        send_message(f"{body_text}{link_part}")


def link_line(url):
    """یه خط با یه کلمه‌ی «لینک» که قابل کلیکه، برای انتهای پیام"""
    if not url:
        return ""
    return f'\n\n🔗 <a href="{html_escape(url)}">لینک</a>'


# هیچ دکمه‌ی ثابتی نداریم؛ فقط منوی دستورات بات (آیکون کنار جعبه‌ی پیام) استفاده میشه
NEWS_BUTTON_TEXT = "📰 اخبار روز"
REMOVE_KEYBOARD = {"remove_keyboard": True}


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
            send_message(
                "خوش اومدی! از آیکون منو کنار جعبه‌ی پیام، دستور /news رو بزن.",
                REMOVE_KEYBOARD,
            )

        elif text in ("/news", NEWS_BUTTON_TEXT):
            state["news_mode"] = not state["news_mode"]
            if state["news_mode"]:
                send_message("🟢 اخبار روز روشن شد؛ در حال بررسی اخبار جدید...", REMOVE_KEYBOARD)
            else:
                send_message("🔴 اخبار روز خاموش شد.", REMOVE_KEYBOARD)

    return state


def strip_html(text):
    text = re.sub("<[^<]+?>", "", text or "")
    return unescape(text).strip()


DEEPSEEK_MODEL = "deepseek-chat"

ANALYZE_PROMPT = (
    "تو یک تحلیلگر خبری حرفه‌ای حوزه‌ی بازار مالی هستی و به فارسی و انگلیسی مسلطی. "
    "متن خبر زیر (که به انگلیسیه) رو بخون و دو کار انجام بده:\n"
    "1. مشخص کن دقیقاً به کدوم یک یا چندتا از این تگ‌ها مربوطه:\n"
    + "\n".join(f"   - {t}" for t in TAGS)
    + "\n2. کل متن رو کامل، دقیق و روان به فارسی ترجمه کن (چیزی از متن رو کم یا خلاصه نکن).\n\n"
    "فقط یک خروجی JSON با همین ساختار دقیق برگردون، بدون هیچ توضیح یا متن اضافه:\n"
    '{"tags": ["تگ۱", "تگ۲"], "translation": "متن ترجمه‌شده"}\n'
    "اگه خبر به هیچ‌کدوم از تگ‌ها مربوط نبود:\n"
    '{"tags": [], "translation": ""}'
)


def _call_avalai(system_prompt, user_text):
    if not AVALAI_API_KEY or not user_text:
        return None
    try:
        resp = requests.post(
            "https://api.avalai.ir/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {AVALAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text[:3000]},
                ],
                "temperature": 0,
            },
            timeout=30,
        )
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"خطا در تماس با AvalAI: {e}")
        return None


def analyze_and_translate(text):
    """
    برای متن‌های انگلیسی: هم تگ‌ها رو تشخیص می‌ده هم دقیق ترجمه می‌کنه (با DeepSeek).
    خروجی: (tags, translation) یا (None, None) اگه خطا خورد.
    """
    content = _call_avalai(ANALYZE_PROMPT, text)
    if content is None:
        return None, None
    try:
        cleaned = re.sub(r"^```json|^```|```$", "", content.strip(), flags=re.MULTILINE).strip()
        data = json.loads(cleaned)
        tags = [t for t in data.get("tags", []) if t in TAGS]
        translation = data.get("translation", "")
        return tags, translation
    except Exception as e:
        print(f"خطا در خوندن خروجی JSON هوش مصنوعی: {e} | content={content}")
        return None, None


def classify_news(text):
    """
    برای متن‌های فارسی (کانال‌های تلگرام): فقط تگ‌گذاری، بدون ترجمه.
    خروجی: لیست تگ‌ها، [] اگه به هیچی مربوط نبود، یا None اگه خطا خورد.
    """
    content = _call_avalai(TAG_PROMPT, text)
    if content is None:
        return None
    if "هیچکدام" in content:
        return []
    return [t for t in TAGS if t in content]


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

            full_text = f"{item['title']}\n{item['desc']}"
            tags, translation = analyze_and_translate(full_text)

            if tags is None:
                # خطای موقت هوش مصنوعی؛ این خبر رو فعلاً رد می‌کنیم و دفعه‌ی بعد دوباره امتحان می‌کنیم
                continue

            if tags == []:
                # به هیچ تگی مربوط نیست
                new_sent.append(item["id"])
                sent.add(item["id"])
                continue

            tag_line = f"🏷 {html_escape(', '.join(tags))}\n\n"
            text = f"📰 {source_name}\n\n{tag_line}{html_escape(translation)}{link_line(item['link'])}"
            send_message(text)
            new_sent.append(item["id"])
            sent.add(item["id"])
            time.sleep(1)

    for source_name, username in TELEGRAM_CHANNELS.items():
        for item in fetch_telegram_channel_items(username):
            if item["id"] in sent:
                continue

            tags = classify_news(item["desc"])
            if tags is None:
                continue
            if tags == []:
                new_sent.append(item["id"])
                sent.add(item["id"])
                continue

            tag_line = f"🏷 {html_escape(', '.join(tags))}\n\n"
            body = f"📰 {source_name}\n\n{tag_line}{html_escape(item['desc'])}"
            if item.get("photo_url"):
                send_photo(item["photo_url"], body, item["link"])
            else:
                send_message(body + link_line(item["link"]))
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
