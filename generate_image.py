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

GOLD  = (201, 162, 87)
WHITE = (240, 240, 240)
GREEN = (70, 200, 140)

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

# مختصات دقیق مرکز هر کادر روی قالب (cx, cy) و عرض کادر برای تنظیم فونت
FIELDS = {
    "time":     {"cx": 355,  "cy": 163, "max_w": 265, "color": WHITE},
    "date":     {"cx": 793,  "cy": 163, "max_w": 295, "color": WHITE},
    "usdt_usd": {"cx": 533,  "cy": 467, "max_w": 340, "color": GREEN},
    "usdt_irt": {"cx": 533,  "cy": 656, "max_w": 340, "color": GREEN},
    "gold18":   {"cx": 533,  "cy": 846, "max_w": 340, "color": GOLD},
    "ounce":    {"cx": 533,  "cy": 1035,"max_w": 340, "color": GOLD},
}


def fa(text):
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)


def to_fa(text):
    return str(text).translate(PERSIAN_DIGITS)


def get_font(size, bold=False):
    path = FONT_BOLD if bold else FONT_REGULAR
    return ImageFont.truetype(path, size)


def fit_text(draw, text, max_w, start_size=44, bold=True):
    """پیدا کردن بزرگ‌ترین سایز فونتی که متن داخل عرض کادر جا بشه"""
    size = start_size
    while size > 16:
        fnt = get_font(size, bold=bold)
        bbox = draw.textbbox((0, 0), text, font=fnt)
        w = bbox[2] - bbox[0]
        if w <= max_w:
            return fnt
        size -= 2
    return get_font(16, bold=bold)


def draw_field(draw, key, text):
    f = FIELDS[key]
    fnt = fit_text(draw, text, f["max_w"])
    draw.text((f["cx"], f["cy"]), text, font=fnt, fill=f["color"], anchor="mm")


def build_report_image(usd_price, toman_price, gold18_price, ounce_price):
    img = Image.open("template.png").copy()
    draw = ImageDraw.Draw(img)

    # ساعت و تاریخ (به وقت ایران UTC+3:30)
    now_iran = datetime.utcnow() + timedelta(hours=3, minutes=30)
    time_str = to_fa(now_iran.strftime("%H:%M"))
    jd = jdatetime.datetime.fromgregorian(datetime=now_iran)
    date_str = to_fa(jd.strftime("%Y/%m/%d"))

    draw_field(draw, "time", time_str)
    draw_field(draw, "date", date_str)

    # تتر به دلار
    val = f"$ {usd_price:.2f}" if usd_price is not None else fa("دریافت نشد")
    draw_field(draw, "usdt_usd", val)

    # تتر به تومان
    val = fa(to_fa(f"{toman_price:,}") + " تومان") if toman_price is not None else fa("دریافت نشد")
    draw_field(draw, "usdt_irt", val)

    # طلای ۱۸ عیار
    val = fa(to_fa(f"{gold18_price:,}") + " تومان") if gold18_price is not None else fa("دریافت نشد")
    draw_field(draw, "gold18", val)

    # انس جهانی
    val = f"$ {ounce_price:,.2f}" if ounce_price is not None else fa("دریافت نشد")
    draw_field(draw, "ounce", val)

    return img


def image_to_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
