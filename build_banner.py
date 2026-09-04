"""Generate the DC Gaming YouTube channel banner.

    venv/Scripts/python.exe build_banner.py

Writes brand/dc-gaming-youtube-banner*.png. The -guides copies mark YouTube's
crop regions and exist for checking only - never upload one.

Two directions were tried and dropped:

- The DKC wallpaper full-bleed. The source is already exactly 16:9, so there
  is no overflow for a crop to remove and the game's own logo cannot be moved
  out of frame; and any scrim heavy enough to make the wordmark legible turned
  the sunset to sludge, with DK's head landing behind the word SPEEDRUNS.
- Cropping kongs.png down to just the DK/Diddy pair. Every crop tight enough
  to exclude Dixie's hand and Kiddy's foot also clipped DK's head.
"""
import os
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter

REPO = os.path.dirname(os.path.abspath(__file__))
IMAGES = os.path.join(REPO, "static", "images")
OUT = os.path.join(REPO, "brand")

W, H = 2048, 1152

# YouTube crops one upload three ways. Only the first is guaranteed anywhere;
# the 423-tall band is what desktop and tablet actually show, and it is much
# shorter than the canvas - art parked near the bottom edge is seen by nobody
# except TV viewers.
SAFE_W, SAFE_H = 1235, 338          # every device, including phones
BAND_H = 423                        # desktop (full width) and tablet (1855)
TABLET_W = 1855

SAFE_X, SAFE_Y = (W - SAFE_W) // 2, (H - SAFE_H) // 2
BAND_Y = (H - BAND_H) // 2
BAND_B = BAND_Y + BAND_H

# Tracks the site palette in static/styles.css - the banner exists to match
# it, so these move together. WASH is --wood, replacing the vine green that
# went with the old jungle ground.
BG, ACCENT, TEXT, WASH = (21, 17, 12), (245, 185, 33), (247, 241, 228), (138, 83, 37)
DISPLAY = r"C:\Windows\Fonts\ariblk.ttf"
BODY = r"C:\Windows\Fonts\segoeuib.ttf"

WORD = "DC GAMING"
SUB = "DONKEY KONG COUNTRY SPEEDRUNS"


def font(p, s):
    return ImageFont.truetype(p, s)


def tracked_width(d, s, f, tr):
    return sum(d.textlength(c, font=f) for c in s) + tr * (len(s) - 1)


def draw_tracked(d, xy, s, f, fill, tr, shadow=None, off=0):
    x, y = xy
    for ch in s:
        if shadow:
            d.text((x + off, y + off), ch, font=f, fill=shadow)
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + tr


def cover(im, w, h, focus=0.5):
    """Fill w*h, cropping horizontally around `focus` (0=left, 1=right)."""
    sc = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * sc), round(im.height * sc)), Image.LANCZOS)
    left = round((im.width - w) * focus)
    top = (im.height - h) // 2
    return im.crop((left, top, left + w, top + h))


def hgrad(size, a, b):
    g = Image.new("RGBA", (size[0], 1))
    px = g.load()
    for x in range(size[0]):
        t = x / max(size[0] - 1, 1)
        px[x, 0] = tuple(round(p + (q - p) * t) for p, q in zip(a, b))
    return g.resize(size, Image.BILINEAR)


def vgrad(size, a, b):
    g = Image.new("RGBA", (1, size[1]))
    px = g.load()
    for y in range(size[1]):
        t = y / max(size[1] - 1, 1)
        px[0, y] = tuple(round(p + (q - p) * t) for p, q in zip(a, b))
    return g.resize(size, Image.BILINEAR)


def glow(size, colour, alpha, box, blur):
    """One ellipse, heavily blurred. Stacked ellipses banded in v1."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse(box, fill=colour + (alpha,))
    return layer.filter(ImageFilter.GaussianBlur(blur))


def lockup(canvas, logo_px, word_px, sub_px, gap, sub_gap, tr, left=None,
           word=WORD, show_logo=True):
    """Logo + wordmark + rule + subline. Centred in the safe strip unless
    `left` is given, which left-aligns the group at that x.

    The monogram already reads as the letters D and C, so pairing it with the
    word "DC GAMING" says DC twice. Either the mark carries the DC and the
    wordmark is just GAMING, or the wordmark carries it and the mark is
    dropped - never both.
    """
    d = ImageDraw.Draw(canvas)
    fw, fs = font(DISPLAY, word_px), font(BODY, sub_px)

    if show_logo:
        logo = Image.open(os.path.join(IMAGES, "logo-gold.png")).convert("RGBA")
        logo = logo.resize((logo_px, logo_px), Image.LANCZOS)
    else:
        logo_px, gap = 0, 0

    wb = d.textbbox((0, 0), word, font=fw)
    word_w, word_h = wb[2] - wb[0], wb[3] - wb[1]
    # tracked_width returns a float; paste boxes must be integral.
    text_w = round(max(word_w, tracked_width(d, SUB, fs, tr)))

    total_w = logo_px + gap + text_w
    x0 = int(left if left is not None else SAFE_X + (SAFE_W - total_w) // 2)
    text_h = word_h + sub_gap + sub_px
    group_h = max(logo_px, text_h)
    y0 = SAFE_Y + (SAFE_H - group_h) // 2

    if show_logo:
        canvas.alpha_composite(logo, (x0, y0 + (group_h - logo_px) // 2))
    tx, ty = x0 + logo_px + gap, y0 + (group_h - text_h) // 2

    off = max(3, word_px // 18)          # the site's blurless 4px offset shadow
    d.text((tx - wb[0] + off, ty - wb[1] + off), word, font=fw, fill=(0, 0, 0, 200))
    d.text((tx - wb[0], ty - wb[1]), word, font=fw, fill=ACCENT + (255,))

    ry = ty + word_h + sub_gap // 2
    d.rectangle([tx, ry - 3, tx + text_w, ry], fill=ACCENT + (210,))
    draw_tracked(d, (tx, ry + sub_gap // 2), SUB, fs, TEXT + (255,), tr,
                 shadow=(0, 0, 0, 180), off=2)
    return x0 + total_w


def kong_layer(height, opacity=255, knee=60, floor=12):
    """The Kong art, re-keyed.

    kongs.png is not the clean cut-out it looks like: roughly half its pixels
    are semi-transparent and a band around the characters is near-black at
    alpha 150-177. On the site that never shows, because the page behind it is
    almost black. On any lighter ground it composites as a dark rectangle.

    Thresholding alpha does not fix it - those pixels are nearly opaque. What
    separates veil from character is luminance, so alpha is multiplied by a
    ramp on brightness: near-black goes transparent, anything with real colour
    is untouched. `floor` then clears the last few counts of residue.
    """
    k = Image.open(os.path.join(IMAGES, "kongs.png")).convert("RGBA")
    r, g, b, a = k.split()
    lum = Image.merge("RGB", (r, g, b)).convert("L")
    ramp = lum.point(lambda v: min(255, round(255 * v / knee)))
    a = ImageChops.multiply(a, ramp).point(lambda v: 0 if v < floor else v)
    if opacity < 255:
        a = a.point(lambda v: v * opacity // 255)
    k = Image.merge("RGBA", (r, g, b, a))
    sc = height / k.height
    return k.resize((round(k.width * sc), height), Image.LANCZOS)


# ---------------------------------------------------------------- variants
def flat_kongs():
    """Palette + type, with the Kong group framed whole on the right.

    v2 bled the group past the right edge and Kiddy ended up bisected with no
    clean cut line. Fitting the group entirely inside the canvas reads as a
    deliberate composition instead of a crop accident.
    """
    c = Image.new("RGBA", (W, H), BG + (255,))
    c.alpha_composite(glow((W, H), WASH, 46, [-200, 40, W * 0.72, H - 40], 190))
    c.alpha_composite(glow((W, H), (28, 20, 12), 120, [W * 0.55, -200, W + 300, H + 200], 220))

    # Rules sit between the phone strip and the desktop band: cropped away on
    # a phone, present on desktop. Drawn before the art so nothing is ruled
    # through.
    d = ImageDraw.Draw(c)
    d.rectangle([0, BAND_Y + 20, W, BAND_Y + 23], fill=ACCENT + (70,))
    d.rectangle([0, BAND_B - 23, W, BAND_B - 20], fill=ACCENT + (70,))

    # Sized and placed to sit inside the 423-tall band, so desktop and tablet
    # viewers actually see the whole group.
    k = kong_layer(392)
    c.alpha_composite(k, (W - k.width - 96, BAND_Y + (BAND_H - k.height) // 2 + 6))

    lockup(c, 216, 112, 30, 40, 24, 3.4, left=SAFE_X + 18, word="GAMING")
    return c


def plain_mark():
    """The monogram carries the DC; the wordmark is just GAMING."""
    c = Image.new("RGBA", (W, H), BG + (255,))
    c.alpha_composite(glow((W, H), WASH, 44, [-200, 40, W * 0.78, H - 40], 200))
    d = ImageDraw.Draw(c)
    d.rectangle([0, BAND_Y + 20, W, BAND_Y + 23], fill=ACCENT + (70,))
    d.rectangle([0, BAND_B - 23, W, BAND_B - 20], fill=ACCENT + (70,))
    lockup(c, 224, 132, 30, 44, 24, 3.4, word="GAMING")
    return c


def plain_word():
    """No mark; the wordmark carries the whole name."""
    c = Image.new("RGBA", (W, H), BG + (255,))
    c.alpha_composite(glow((W, H), WASH, 44, [-200, 40, W * 0.78, H - 40], 200))
    d = ImageDraw.Draw(c)
    d.rectangle([0, BAND_Y + 20, W, BAND_Y + 23], fill=ACCENT + (70,))
    d.rectangle([0, BAND_B - 23, W, BAND_B - 20], fill=ACCENT + (70,))
    lockup(c, 0, 150, 32, 0, 26, 3.8, show_logo=False)
    return c


def guides(im):
    g = im.copy()
    d = ImageDraw.Draw(g)
    f = font(BODY, 26)
    d.rectangle([0, BAND_Y, W - 1, BAND_B], outline=(90, 170, 255), width=3)
    d.text((14, BAND_Y + 10), "2048 x 423  desktop", font=f, fill=(120, 190, 255))
    tx = (W - TABLET_W) // 2
    d.rectangle([tx, BAND_Y, tx + TABLET_W, BAND_B], outline=(150, 130, 255), width=2)
    d.text((tx + 12, BAND_B - 38), "1855 x 423  tablet", font=f, fill=(170, 150, 255))
    d.rectangle([SAFE_X, SAFE_Y, SAFE_X + SAFE_W, SAFE_Y + SAFE_H], outline=(255, 60, 60), width=4)
    d.text((SAFE_X + 12, SAFE_Y - 40), "1235 x 338  safe on ALL devices", font=f, fill=(255, 90, 90))
    return g


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, im in [("dc-gaming-youtube-banner", plain_mark()),
                     ("dc-gaming-youtube-banner-wordmark", plain_word()),
                     ("dc-gaming-youtube-banner-kongs", flat_kongs())]:
        p = os.path.join(OUT, name + ".png")
        im.convert("RGB").save(p, "PNG", optimize=True)
        guides(im).convert("RGB").save(os.path.join(OUT, name + "-guides.png"), "PNG", optimize=True)
        print("%-18s %.2f MB" % (name, os.path.getsize(p) / 1048576))
