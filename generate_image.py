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

GOLD       = (201, 162, 87)
WHITE      = (240, 240, 240)
GREEN      = (70, 200, 140)

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

# مختصات دقیق جعبه‌های متن روی قالب
BOXES = {
    "time": (220, 135, 500, 195),
    "date": (640, 135, 950, 195),
    "usdt_usd": (355, 450, 715, 510),
    "usdt_irt": (355, 638, 715, 698),
    "gold18":   (355, 828, 715, 888),
    "ounce":    (355, 1015, 715, 1075),
}


def fa(text):
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)


def to_fa(text):
    return str(text).translate(PERSIAN_DIGITS)


def font(size, bold=False):
    path = FONT_BOLD if bold else FONT_REGULAR
    return ImageFont.truetype(path, size)


def draw_centered_text(draw, box, text, fnt, color):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    draw.text((cx, cy), text, font=fnt, fill=color, anchor="mm")


def build_report_image(usd_price, toman_price, gold18_price, ounce_price):
    img = Image.open("template.png").copy()
    draw = ImageDraw.Draw(img)

    # --- ساعت و تاریخ (به وقت ایران UTC+3:30) ---
    now_iran = datetime.utcnow() + timedelta(hours=3, minutes=30)
    time_str = to_fa(now_iran.strftime("%H:%M"))
    jd = jdatetime.datetime.fromgregorian(datetime=now_iran)
    date_str = to_fa(jd.strftime("%Y/%m/%d"))

    draw_centered_text(draw, BOXES["time"], time_str,  font(34, bold=True), WHITE)
    draw_centered_text(draw, BOXES["date"], date_str,  font(30, bold=True), WHITE)

    # --- تتر به دلار ---
    if usd_price is not None:
        val = f"$ {usd_price:.2f}"
        draw_centered_text(draw, BOXES["usdt_usd"], val, font(36, bold=True), GREEN)
    else:
        draw_centered_text(draw, BOXES["usdt_usd"], fa("دریافت نشد"), font(28), WHITE)

    # --- تتر به تومان ---
    if toman_price is not None:
        val = fa(to_fa(f"{toman_price:,}") + " تومان")
        draw_centered_text(draw, BOXES["usdt_irt"], val, font(33, bold=True), GREEN)
    else:
        draw_centered_text(draw, BOXES["usdt_irt"], fa("دریافت نشد"), font(28), WHITE)

    # --- طلای ۱۸ عیار ---
    if gold18_price is not None:
        val = fa(to_fa(f"{gold18_price:,}") + " تومان")
        draw_centered_text(draw, BOXES["gold18"], val, font(33, bold=True), GOLD)
    else:
        draw_centered_text(draw, BOXES["gold18"], fa("دریافت نشد"), font(28), WHITE)

    # --- انس جهانی ---
    if ounce_price is not None:
        val = f"$ {ounce_price:,.2f}"
        draw_centered_text(draw, BOXES["ounce"], val, font(36, bold=True), GOLD)
    else:
        draw_centered_text(draw, BOXES["ounce"], fa("دریافت نشد"), font(28), WHITE)

    return img


def image_to_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
