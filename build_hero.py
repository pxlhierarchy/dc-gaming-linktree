"""Build the home-page hero: the DC logo set into the gap between the Kongs.

Regenerates two files from the two source images. Re-run after replacing
either source.

    static/images/logo-gold.png  - the logo recoloured to the site accent
    static/images/hero.png       - Kongs art with that logo composited in

Usage:  venv/Scripts/python.exe build_hero.py
"""
from PIL import Image
import os
import numpy as np

KONGS = 'static/images/kongs.png'
LOGO = 'static/images/logo.png'
OUT_LOGO = 'static/images/logo-gold.png'
OUT_HERO = 'static/images/hero.png'

GOLD = (245, 185, 33)          # --accent, banana yellow
SHADOW_OFFSET = 5              # matches the site's hard blurless shadows


def recolour(path, rgb):
    """Recolour the logo's red fill, keeping its black outline and alpha.

    The source is a flat red fill (255,49,49) with a flat black outline, so
    the red channel alone says how far a pixel is from outline to fill:
    r=0 is outline, r=255 is fill, and the values between are the antialiased
    edge. Interpolating black -> gold by r/255 therefore recolours the fill
    and keeps every edge pixel smooth, with no halo.
    """
    img = Image.open(path).convert('RGBA')
    a = np.array(img).astype(np.float32)
    t = (a[..., 0] / 255.0)[..., None]              # redness, 0..1
    a[..., :3] = t * np.array(rgb, dtype=np.float32)
    out = Image.fromarray(a.astype(np.uint8), 'RGBA')
    return out.crop(out.getbbox())                  # trim transparent margin


def clear_box(alpha, x_lo=90, x_hi=440, y_hi=260):
    """Largest fully-transparent rectangle in the upper-centre of the art."""
    occupied = np.array(alpha) > 40
    best = None
    for x0 in range(x_lo, 270, 5):
        for x1 in range(x0 + 130, x_hi, 5):
            for y0 in range(0, 100, 5):
                for y1 in range(y0 + 110, y_hi, 5):
                    if not occupied[y0:y1, x0:x1].any():
                        area = (x1 - x0) * (y1 - y0)
                        if best is None or area > best[0]:
                            best = (area, x0, y0, x1, y1)
    return best[1:]


def build():
    logo = recolour(LOGO, GOLD)
    logo.save(OUT_LOGO)
    print(f'{OUT_LOGO}: {logo.size[0]}x{logo.size[1]}')

    kongs = Image.open(KONGS).convert('RGBA')
    x0, y0, x1, y1 = clear_box(kongs.getchannel('A'))
    print(f'clear gap: x {x0}-{x1}, y {y0}-{y1}')

    # Fit the logo inside the gap with a margin, leaving room for the shadow.
    pad = 12
    box_w, box_h = (x1 - x0) - pad * 2, (y1 - y0) - pad * 2
    scale = min(box_w / logo.width, box_h / logo.height)
    new = (max(1, int(logo.width * scale)), max(1, int(logo.height * scale)))
    logo = logo.resize(new, Image.LANCZOS)

    # Centre horizontally in the gap; sit just below the top edge.
    px = x0 + (x1 - x0 - logo.width) // 2
    py = y0 + max(6, (y1 - y0 - logo.height) // 2)

    hero = kongs.copy()

    # Hard offset shadow: the logo's own silhouette in translucent black.
    silhouette = Image.new('RGBA', logo.size, (0, 0, 0, 0))
    silhouette.putalpha(logo.getchannel('A').point(lambda v: int(v * 0.45)))
    hero.alpha_composite(silhouette, (px + SHADOW_OFFSET, py + SHADOW_OFFSET))

    hero.alpha_composite(logo, (px, py))

    # Quantise the colour channels only, and put the original 8-bit alpha back.
    # Quantising RGBA directly folds alpha into the palette and leaves a grey
    # halo of banding around the characters' soft cut-out edges.
    alpha = hero.getchannel('A')
    hero = hero.convert('RGB') \
               .quantize(colors=256, method=Image.FASTOCTREE) \
               .convert('RGB').convert('RGBA')
    hero.putalpha(alpha)
    hero.save(OUT_HERO, optimize=True)

    kb = os.path.getsize(OUT_HERO) / 1024
    print(f'{OUT_HERO}: {hero.size[0]}x{hero.size[1]}, logo at {px},{py} '
          f'@ {new[0]}x{new[1]}, {kb:.0f}KB')


if __name__ == '__main__':
    build()
