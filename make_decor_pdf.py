# -*- coding: utf-8 -*-
"""
make_decor_pdf.py — كتالوج PDF للزينة والمنتجات الأخرى (كرتون / ورق / قماش / بلاستيك / ميلامين...)
    أي منتج مش معدن ومش خشب. كل صفحة فيها 3 أو 4 صور: واحدة كبيرة والباقي أصغر وواضحين

التشغيل (من جوه فولدر المشروع، جنب index.html):
    pip install reportlab arabic-reshaper python-bidi pillow
    python make_decor_pdf.py

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

# ترتيب الأقسام في الـ PDF بس (مش بيأثر على الموقع).
# غيّري الترتيب زي ما تحبي، وأي قسم مش مكتوب هنا بيتحط في الآخر:
CATEGORY_ORDER = [
    "hospitality",   # قطع التقديم والضيافة
    "lighting",      # فوانيس وإضاءة
    "storage",       # علب وحافظات الضيافة
    "decor",         # ديكور ومفارش مائدة
]
OUTPUT_PDF = "decor_catalog.pdf"

# الكفر: حطي صورة اسمها cover3 (jpg / png / webp) جنب السكريبت
COVER_NAME = "cover3"

# ---- تصميم الصفحة ----
# عدد الصور الصغيرة تحت الصورة الكبيرة (3 = يعني 4 صور في الصفحة، 2 = 3 صور)
MAX_EXTRA = 3

# لو عايزة تقصري الكتالوج على أقسام معينة، اكتبي أسماءها هنا. مثال: {"decor"}
# None = كل الأقسام
ONLY_CATEGORIES = None

# ---- استثناءات الصور ----
# المنتجات اللي مش عايزة أول صورة منها: حطي الـ id بتاعها هنا
# وهتتشال من الصفحة خالص، والصورة التانية هتبقى هي الكبيرة. مثال:
#   SKIP_FIRST_IMAGE = {"p-qahwa", "p-moon-21"}
SKIP_FIRST_IMAGE = set()

# ---- التحكم اليدوي في المنتجات ----
FORCE_INCLUDE = set()   # ids تتضاف حتى لو الكود شافها معدن أو خشب
FORCE_EXCLUDE = {       # ids تتشال من الكتالوج ده
    # صواني الميلامين
    "p-melamine-trays", "p-melamine-trays-rect", "p-melamine-rect-set",
    "p-melamine-trays-white", "p-white-melamine-rect-set", "p-white-melamine-trays",
    # حافظات الطعام الحرارية
    "p-insulated-food-carrier-set", "p-insulated-food-carrier-set-brown",
}

# ---- منطق التحديد ----
# الكتالوج ده فيه أي منتج مش معدن ومش خشب (بنفس قواعد سكريبتات المعدن والخشب)،
# فكده كل منتج في الموقع بيظهر في واحد من التلات كتالوجات ومفيش منتج بيتكرر.
#
# قواعد المعدن:
# المنتج يتحسب معدن لو العنوان أو التاج فيه واحدة من دول:
METAL_WORDS = ["معدن", "زنك"]
# لو ظهر خشب في أي مكان (عنوان/تاج/وصف/خامة) المنتج يتشال (زي ما طلبتي):
WOOD_WORDS = ["خشب", "mdf", "ام دي اف", "إم دي إف", "الزان"]
# خامات تانية بتخلي المنتج مش معدن؛ بتتدور عليها في العنوان والتاج بس:
OTHER_MATERIAL_WORDS = ["كرتون", "جوت", "بالون"]

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
    has_wood = any(w.lower() in full for w in WOOD_WORDS)
    has_other = any(w.lower() in head for w in OTHER_MATERIAL_WORDS)
    return has_metal and not has_wood and not has_other


def is_wood(p):
    full = " ".join([p.get("title", ""), p.get("tag", ""),
                     p.get("description", ""), p.get("craftsmanship", "")]).lower()
    return any(w.lower() in full for w in WOOD_WORDS)


def is_other(p):
    if ONLY_CATEGORIES and p.get("categorySlug") not in ONLY_CATEGORIES:
        return False
    return not is_metal(p) and not is_wood(p)


def sort_by_category(items):
    """ترتيب المنتجات كل قسم ورا بعض حسب CATEGORY_ORDER،
    وجوه كل قسم بيفضل ترتيب المنتجات زي ما هو في products.json"""
    order = {slug: i for i, slug in enumerate(CATEGORY_ORDER)}
    return sorted(items, key=lambda p: order.get(p.get("categorySlug"), 999))


def pick_products(products):
    out = []
    for p in products:
        pid = p["id"]
        if pid in FORCE_EXCLUDE:
            continue
        if pid in FORCE_INCLUDE or is_other(p):
            out.append(p)
    return sort_by_category(out)


def pick_images(p):
    """يرجع (الصورة الكبيرة، [الصور الصغيرة])"""
    gallery = p.get("gallery") or [p["image"]]
    if p["id"] in SKIP_FIRST_IMAGE and len(gallery) > 1:
        gallery = gallery[1:]          # تجاهل أول صورة تماماً
    main = gallery[0]
    extras = [g for g in gallery[1:] if os.path.exists(g)][:MAX_EXTRA]
    return main, extras


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
        c.drawCentredString(PAGE_W / 2, PAGE_H / 2 - 20, ar("كتالوج الزينة والمنتجات الأخرى"))
    c.showPage()


def draw_image_card(c, path, x, y, w, h, radius=16, pad=12):
    """كارت أبيض بظل خفيف والصورة جواه (contain) بحواف دائرية"""
    c.setFillColor(HexColor("#EFE6D4"))
    c.roundRect(x + 1.5, y - 2.5, w, h, radius, stroke=0, fill=1)
    c.setFillColor(CARD)
    c.roundRect(x, y, w, h, radius, stroke=0, fill=1)

    bx, by, bw, bh = x + pad, y + pad, w - 2 * pad, h - 2 * pad
    try:
        img, (iw, ih) = load_image(path)
        scale = min(bw / iw, bh / ih)
        dw, dh = iw * scale, ih * scale
        c.saveState()
        clip = c.beginPath()
        clip.roundRect(bx, by, bw, bh, radius - 4)
        c.clipPath(clip, stroke=0, fill=0)
        c.drawImage(img, bx + (bw - dw) / 2, by + (bh - dh) / 2, dw, dh)
        c.restoreState()
    except Exception as e:
        print(f"  ⚠ تعذر فتح الصورة: {path} ({e})")
        c.setFillColor(HAIR)
        c.roundRect(bx, by, bw, bh, radius - 4, stroke=0, fill=1)


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

    # ---------- منطقة الصور ----------
    main_path, extras = pick_images(p)
    area_x, area_w = MARGIN, PAGE_W - 2 * MARGIN
    area_top = PAGE_H - 74
    area_h = 612
    gap = 12
    k = len(extras)

    if k == 0:
        main_h = area_h
        row_h = 0
    else:
        row_h = {1: 240, 2: 215, 3: 195}.get(k, 195)
        main_h = area_h - row_h - gap
    main_y = area_top - main_h

    # الصورة الكبيرة
    draw_image_card(c, main_path, area_x, main_y, area_w, main_h, radius=18, pad=14)

    # الصور الأصغر (تحتها في صف واحد)
    if k:
        if k == 1:
            cw = area_w * 0.62
            xs = [area_x + (area_w - cw) / 2]
        else:
            cw = (area_w - (k - 1) * gap) / k
            xs = [area_x + i * (cw + gap) for i in range(k)]
        row_y = main_y - gap - row_h
        for x, path in zip(xs, extras):
            draw_image_card(c, path, x, row_y, cw, row_h, radius=14, pad=8 if k >= 3 else 10)
        img_bottom = row_y
    else:
        img_bottom = main_y

    # ---------- اسم المنتج ----------
    title = p["title"]
    max_w = PAGE_W - 2 * MARGIN - 30
    size = 19
    lines = wrap_ar(title, "AR-B", size, max_w)
    if len(lines) > 3:
        size = 15
        lines = wrap_ar(title, "AR-B", size, max_w)
    lines = lines[:3]

    leading = size + 8
    block_h = leading * (len(lines) - 1) + size + 20   # الاسم + الفاصل
    t_top = img_bottom - 8
    t_bottom = 40
    first_y = t_top - (t_top - t_bottom - block_h) / 2 - size

    c.setFillColor(INK)
    c.setFont("AR-B", size)
    y = first_y
    for ln in lines:
        c.drawCentredString(PAGE_W / 2, y, ar(ln))
        y -= leading
    last_y = y + leading

    div_y = last_y - 16
    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.line(PAGE_W / 2 - 26, div_y, PAGE_W / 2 - 5, div_y)
    c.line(PAGE_W / 2 + 5, div_y, PAGE_W / 2 + 26, div_y)
    c.setFillColor(GOLD)
    c.circle(PAGE_W / 2, div_y, 2.2, stroke=0, fill=1)

    # رقم الصفحة
    c.setFillColor(GOLD)
    c.setFont("AR", 9)
    c.drawCentredString(PAGE_W / 2, 24, f"{page_no} / {total}")
    c.showPage()


def main():
    register_fonts()
    with open(PRODUCTS_JSON, encoding="utf-8") as f:
        products = json.load(f)

    chosen = pick_products(products)
    print(f"عدد المنتجات: {len(chosen)} من {len(products)}")

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
