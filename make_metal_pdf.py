# -*- coding: utf-8 -*-
"""
make_metal_pdf.py — كتالوج PDF لمنتجات المعدن (الشافعي)

التشغيل (من جوه فولدر المشروع، جنب index.html):
    pip install reportlab arabic-reshaper python-bidi pillow
    python make_metal_pdf.py

الناتج: metal_catalog.pdf
"""
import io
import json
import os
import re
import sys

from PIL import Image
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import arabic_reshaper
from bidi.algorithm import get_display

# =====================================================================
#                           الإعدادات
# =====================================================================
BRAND = "الشافعي"
PRODUCTS_JSON = "data/products.json"
OUTPUT_PDF = "metal_catalog.pdf"

# الكفر: حطي صورة اسمها cover (jpg / png / webp) جنب السكريبت
COVER_NAME = "cover"

# ---- استثناءات الصور ----
# المنتجات اللي مش عايزة أول صورة منها: حطي الـ id بتاعها هنا
# وهياخد الصورة التانية بدالها. مثال:
#   SKIP_FIRST_IMAGE = {"p-qahwa", "p-moon-21"}
SKIP_FIRST_IMAGE = set()

# ---- التحكم اليدوي في المنتجات ----
FORCE_INCLUDE = set()   # ids تتضاف حتى لو الكود شافها مش معدن
FORCE_EXCLUDE = set()   # ids تتشال حتى لو الكود شافها معدن

# ---- منطق تحديد "معدن" ----
# المنتج يتحسب معدن لو العنوان أو التاج فيه واحدة من دول:
METAL_WORDS = ["معدن", "زنك"]
# ولو ظهر في أي مكان (عنوان/تاج/وصف/خامة) واحدة من دول يتشال:
# (الخشب زي ما طلبتي + خامات تانية بتخلي المنتج مش معدن صافي)
WOOD_WORDS = ["خشب", "mdf", "ام دي اف", "إم دي إف", "الزان"]
OTHER_MATERIAL_WORDS = ["كرتون", "قماش", "جوت", "بالون", "ورق"]
EXCLUDE_WORDS = WOOD_WORDS + OTHER_MATERIAL_WORDS

# ---- الألوان ----
IVORY = HexColor("#FAF6EE")
INK = HexColor("#1A150F")
GOLD = HexColor("#B8924A")
GOLD_SOFT = HexColor("#D9BE86")
CARD = white
HAIR = HexColor("#E6DCC8")

PAGE_W, PAGE_H = A4
MARGIN = 34


# =====================================================================
#                              الخطوط
# =====================================================================
def register_fonts():
    here = os.path.dirname(os.path.abspath(__file__))
    win = os.environ.get("WINDIR", r"C:\Windows") + r"\Fonts"
    candidates = [
        # (regular, bold)
        (os.path.join(here, "Cairo-Regular.ttf"), os.path.join(here, "Cairo-Bold.ttf")),
        (os.path.join(win, "segoeui.ttf"), os.path.join(win, "segoeuib.ttf")),
        (os.path.join(win, "tahoma.ttf"), os.path.join(win, "tahomabd.ttf")),
        (os.path.join(win, "arial.ttf"), os.path.join(win, "arialbd.ttf")),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for reg, bold in candidates:
        if os.path.exists(reg):
            pdfmetrics.registerFont(TTFont("AR", reg))
            pdfmetrics.registerFont(TTFont("AR-B", bold if os.path.exists(bold) else reg))
            print("الخط المستخدم:", os.path.basename(reg))
            return
    sys.exit("مفيش خط عربي متاح. حطي Cairo-Regular.ttf و Cairo-Bold.ttf جنب السكريبت.")


def ar(text):
    """تشكيل الحروف العربية + ترتيب اليمين لليسار"""
    return get_display(arabic_reshaper.reshape(text))


def wrap_ar(text, font, size, max_w):
    """تقسيم النص لسطور حسب العرض (على النص المنطقي قبل التشكيل)"""
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if pdfmetrics.stringWidth(ar(trial), font, size) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# =====================================================================
#                              الصور
# =====================================================================
def load_image(path, max_side=1600):
    """يفتح الصورة (webp وغيرها) ويرجعها كـ RGB مصغّرة لتخفيف حجم الـ PDF"""
    im = Image.open(path)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90)
    buf.seek(0)
    return ImageReader(buf), im.size


def find_cover():
    here = os.path.dirname(os.path.abspath(__file__))
    for ext in ("jpg", "jpeg", "png", "webp"):
        p = os.path.join(here, f"{COVER_NAME}.{ext}")
        if os.path.exists(p):
            return p
    return None


# =====================================================================
#                          اختيار المنتجات
# =====================================================================
def is_metal(p):
    head = (p.get("title", "") + " " + p.get("tag", "")).lower()
    full = " ".join([p.get("title", ""), p.get("tag", ""),
                     p.get("description", ""), p.get("craftsmanship", "")]).lower()
    has_metal = any(w in head for w in METAL_WORDS)
    has_excluded = any(w.lower() in full for w in EXCLUDE_WORDS)
    return has_metal and not has_excluded


def pick_products(products):
    out = []
    for p in products:
        pid = p["id"]
        if pid in FORCE_EXCLUDE:
            continue
        if pid in FORCE_INCLUDE or is_metal(p):
            out.append(p)
    return out


def main_image_path(p):
    gallery = p.get("gallery") or [p["image"]]
    idx = 1 if (p["id"] in SKIP_FIRST_IMAGE and len(gallery) > 1) else 0
    return gallery[idx]


# =====================================================================
#                              الرسم
# =====================================================================
def draw_cover(c, cover_path, count):
    if cover_path:
        img, (w, h) = load_image(cover_path, 2400)
        # تغطية الصفحة كاملة (crop من الأطراف)
        scale = max(PAGE_W / w, PAGE_H / h)
        dw, dh = w * scale, h * scale
        c.drawImage(img, (PAGE_W - dw) / 2, (PAGE_H - dh) / 2, dw, dh)
    else:
        c.setFillColor(INK)
        c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
        c.setFillColor(GOLD_SOFT)
        c.setFont("AR-B", 54)
        c.drawCentredString(PAGE_W / 2, PAGE_H / 2 + 20, ar(BRAND))
        c.setFont("AR", 18)
        c.setFillColor(white)
        c.drawCentredString(PAGE_W / 2, PAGE_H / 2 - 20, ar("كتالوج المنتجات المعدنية"))
    c.showPage()


def draw_product_page(c, p, page_no, total):
    # الخلفية
    c.setFillColor(IVORY)
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)

    # إطار ذهبي رفيع
    c.setStrokeColor(GOLD_SOFT)
    c.setLineWidth(0.8)
    c.roundRect(14, 14, PAGE_W - 28, PAGE_H - 28, 10, stroke=1, fill=0)

    # الهيدر: اسم البراند
    c.setFillColor(GOLD)
    c.setFont("AR-B", 15)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 48, ar(BRAND))
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.6)
    c.line(PAGE_W / 2 - 22, PAGE_H - 56, PAGE_W / 2 + 22, PAGE_H - 56)

    # كارت الصورة
    card_x, card_w = MARGIN, PAGE_W - 2 * MARGIN
    card_top = PAGE_H - 74
    card_h = 560
    card_y = card_top - card_h

    c.setFillColor(HexColor("#EFE6D4"))          # ظل خفيف
    c.roundRect(card_x + 2, card_y - 3, card_w, card_h, 18, stroke=0, fill=1)
    c.setFillColor(CARD)
    c.roundRect(card_x, card_y, card_w, card_h, 18, stroke=0, fill=1)

    # الصورة داخل الكارت (contain مع padding) ومقصوصة بحواف دائرية
    path = main_image_path(p)
    pad = 16
    box_x, box_y = card_x + pad, card_y + pad
    box_w, box_h = card_w - 2 * pad, card_h - 2 * pad
    try:
        img, (w, h) = load_image(path)
        scale = min(box_w / w, box_h / h)
        dw, dh = w * scale, h * scale
        c.saveState()
        clip = c.beginPath()
        clip.roundRect(box_x, box_y, box_w, box_h, 12)
        c.clipPath(clip, stroke=0, fill=0)
        c.drawImage(img, box_x + (box_w - dw) / 2, box_y + (box_h - dh) / 2, dw, dh)
        c.restoreState()
    except Exception as e:
        print(f"  ⚠ تعذر فتح الصورة: {path} ({e})")
        c.setFillColor(HAIR)
        c.roundRect(box_x, box_y, box_w, box_h, 12, stroke=0, fill=1)

    # اسم المنتج
    title = p["title"]
    max_w = PAGE_W - 2 * MARGIN - 30
    size = 20
    lines = wrap_ar(title, "AR-B", size, max_w)
    if len(lines) > 3:
        size = 16
        lines = wrap_ar(title, "AR-B", size, max_w)
    lines = lines[:3]

    leading = size + 9
    block_h = leading * (len(lines) - 1) + size + 22   # الاسم + الفاصل
    area_top = card_y - 10
    area_bottom = 44
    first_y = area_top - (area_top - area_bottom - block_h) / 2 - size

    c.setFillColor(INK)
    c.setFont("AR-B", size)
    y = first_y
    for ln in lines:
        c.drawCentredString(PAGE_W / 2, y, ar(ln))
        y -= leading
    last_y = y + leading

    # فاصل ذهبي صغير تحت الاسم
    div_y = last_y - 18
    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.line(PAGE_W / 2 - 26, div_y, PAGE_W / 2 - 5, div_y)
    c.line(PAGE_W / 2 + 5, div_y, PAGE_W / 2 + 26, div_y)
    c.setFillColor(GOLD)
    c.circle(PAGE_W / 2, div_y, 2.2, stroke=0, fill=1)

    # رقم الصفحة
    c.setFillColor(GOLD)
    c.setFont("AR", 9)
    c.drawCentredString(PAGE_W / 2, 26, f"{page_no} / {total}")
    c.showPage()


def main():
    register_fonts()
    with open(PRODUCTS_JSON, encoding="utf-8") as f:
        products = json.load(f)

    chosen = pick_products(products)
    print(f"عدد المنتجات المعدنية: {len(chosen)} من {len(products)}")

    c = canvas.Canvas(OUTPUT_PDF, pagesize=A4)
    c.setTitle(f"{BRAND} - كتالوج المنتجات المعدنية")
    c.setAuthor(BRAND)

    cover = find_cover()
    if not cover:
        print(f"⚠ مفيش صورة اسمها {COVER_NAME}.jpg/png/webp — هعمل كفر بسيط مؤقت")
    draw_cover(c, cover, len(chosen))

    for i, p in enumerate(chosen, 1):
        draw_product_page(c, p, i, len(chosen))

    c.save()
    print("تم إنشاء:", OUTPUT_PDF)


if __name__ == "__main__":
    main()
