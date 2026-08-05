"""
ساخت تصویر گزارش قیمت بر روی قالب از پیش طراحی‌شده
"""

import io
from datetime import datetime, timedelta

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont
import jdatetime

FONT_BOLD    = "fonts/Vazirmatn-Bold.ttf"
FONT_REGULAR = "fonts/Vazirmatn-Regular.ttf"

GOLD  = (212, 175, 55)

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

# مرکز دقیق هر کادر - cy رو پایین‌تر آوردم تا وسط کادر باشه
FIELDS = {
    "time":     {"cx": 355, "cy": 163, "max_w": 260},
    "date":     {"cx": 793, "cy": 163, "max_w": 290},
    "usdt_usd": {"cx": 533, "cy": 490, "max_w": 330},
    "usdt_irt": {"cx": 533, "cy": 678, "max_w": 330},
    "gold18":   {"cx": 533, "cy": 868, "max_w": 330},
    "ounce":    {"cx": 533, "cy": 1057,"max_w": 330},
}


def fa(text):
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)


def to_fa(text):
    return str(text).translate(PERSIAN_DIGITS)


def get_font(size, bold=True):
    path = FONT_BOLD if bold else FONT_REGULAR
    return ImageFont.truetype(path, size)


def fit_and_draw(draw, key, text, start_size=46):
    """متن رو با بزرگ‌ترین سایز ممکن دقیقاً وسط کادر رسم می‌کنه"""
    f = FIELDS[key]
    size = start_size
    while size >= 18:
        fnt = get_font(size)
        bbox = draw.textbbox((0, 0), text, font=fnt)
        w = bbox[2] - bbox[0]
        if w <= f["max_w"]:
            break
        size -= 2
    draw.text((f["cx"], f["cy"]), text, font=fnt, fill=GOLD, anchor="mm")


def build_report_image(usd_price, toman_price, gold18_price, ounce_price):
    img = Image.open("template.png").copy()
    draw = ImageDraw.Draw(img)

    # ساعت و تاریخ
    now_iran = datetime.utcnow() + timedelta(hours=3, minutes=30)
    time_str = to_fa(now_iran.strftime("%H:%M"))
    jd = jdatetime.datetime.fromgregorian(datetime=now_iran)
    date_str = to_fa(jd.strftime("%Y/%m/%d"))

    fit_and_draw(draw, "time", time_str)
    fit_and_draw(draw, "date", date_str)

    # تتر به دلار (فقط عدد، بدون "تومان")
    val = f"$ {usd_price:.2f}" if usd_price is not None else fa("دریافت نشد")
    fit_and_draw(draw, "usdt_usd", val)

    # تتر به تومان (فقط عدد، بدون "تومان")
    val = to_fa(f"{toman_price:,}") if toman_price is not None else fa("دریافت نشد")
    fit_and_draw(draw, "usdt_irt", val)

    # طلای ۱۸ عیار (فقط عدد، بدون "تومان")
    val = to_fa(f"{gold18_price:,}") if gold18_price is not None else fa("دریافت نشد")
    fit_and_draw(draw, "gold18", val)

    # انس جهانی (فقط عدد)
    val = f"$ {ounce_price:,.2f}" if ounce_price is not None else fa("دریافت نشد")
    fit_and_draw(draw, "ounce", val)

    return img


def image_to_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
