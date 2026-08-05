import io
from datetime import datetime, timedelta

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont
import jdatetime

FONT_BOLD    = "fonts/Vazirmatn-Bold.ttf"
FONT_REGULAR = "fonts/Vazirmatn-Regular.ttf"

SILVER = (200, 200, 210)  # سفید خاکستری
FIXED_FONT_SIZE = 48      # بزرگ‌تر از قبل

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

FIELDS = {
    "time":     {"cx": 375, "cy": 200},
    "date":     {"cx": 825, "cy": 200},
    "usdt_usd": {"cx": 575, "cy": 525},
    "usdt_irt": {"cx": 575, "cy": 720},
    "gold18":   {"cx": 575, "cy": 900},
    "ounce":    {"cx": 575, "cy": 1095},
}


def fa(text):
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)


def to_fa(text):
    return str(text).translate(PERSIAN_DIGITS)


def get_font(bold=True):
    path = FONT_BOLD if bold else FONT_REGULAR
    return ImageFont.truetype(path, FIXED_FONT_SIZE)


def draw_field(draw, key, text):
    f = FIELDS[key]
    fnt = get_font()
    draw.text((f["cx"], f["cy"]), text, font=fnt, fill=SILVER, anchor="mm")


def build_report_image(usd_price, toman_price, gold18_price, ounce_price):
    img = Image.open("template.png").copy()
    draw = ImageDraw.Draw(img)

    now_iran = datetime.utcnow() + timedelta(hours=3, minutes=30)
    time_str = to_fa(now_iran.strftime("%H:%M"))
    jd = jdatetime.datetime.fromgregorian(datetime=now_iran)
    date_str = to_fa(jd.strftime("%Y/%m/%d"))

    draw_field(draw, "time", time_str)
    draw_field(draw, "date", date_str)

    val = f"{usd_price:.2f}" if usd_price is not None else fa("دریافت نشد")
    draw_field(draw, "usdt_usd", val)

    val = to_fa(f"{toman_price:,}") if toman_price is not None else fa("دریافت نشد")
    draw_field(draw, "usdt_irt", val)

    val = to_fa(f"{gold18_price:,}") if gold18_price is not None else fa("دریافت نشد")
    draw_field(draw, "gold18", val)

    val = f"{ounce_price:,.2f}" if ounce_price is not None else fa("دریافت نشد")
    draw_field(draw, "ounce", val)

    return img


def image_to_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
