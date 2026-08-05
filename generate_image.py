import io
from datetime import datetime, timedelta

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont
import jdatetime

FONT_BOLD    = "fonts/Vazirmatn-Bold.ttf"
FONT_REGULAR = "fonts/Vazirmatn-Regular.ttf"

GOLD = (212, 175, 55)

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

FIELDS = {
    "time":     {"cx": 375, "cy": 200, "max_w": 140},
    "date":     {"cx": 825, "cy": 200, "max_w": 145},
    "usdt_usd": {"cx": 575, "cy": 525, "max_w": 145},
    "usdt_irt": {"cx": 575, "cy": 700, "max_w": 145},
    "gold18":   {"cx": 575, "cy": 900, "max_w": 145},
    "ounce":    {"cx": 575, "cy": 1075, "max_w": 145},
}


def fa(text):
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)


def to_fa(text):
    return str(text).translate(PERSIAN_DIGITS)


def get_font(size, bold=True):
    path = FONT_BOLD if bold else FONT_REGULAR
    return ImageFont.truetype(path, size)


def fit_and_draw(draw, key, text, start_size=44):
    f = FIELDS[key]
    size = start_size
    while size >= 16:
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

    now_iran = datetime.utcnow() + timedelta(hours=3, minutes=30)
    time_str = to_fa(now_iran.strftime("%H:%M"))
    jd = jdatetime.datetime.fromgregorian(datetime=now_iran)
    date_str = to_fa(jd.strftime("%Y/%m/%d"))

    fit_and_draw(draw, "time", time_str)
    fit_and_draw(draw, "date", date_str)

    val = f"$ {usd_price:.2f}" if usd_price is not None else fa("دریافت نشد")
    fit_and_draw(draw, "usdt_usd", val)

    val = to_fa(f"{toman_price:,}") if toman_price is not None else fa("دریافت نشد")
    fit_and_draw(draw, "usdt_irt", val)

    val = to_fa(f"{gold18_price:,}") if gold18_price is not None else fa("دریافت نشد")
    fit_and_draw(draw, "gold18", val)

    val = f"$ {ounce_price:,.2f}" if ounce_price is not None else fa("دریافت نشد")
    fit_and_draw(draw, "ounce", val)

    return img


def image_to_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
