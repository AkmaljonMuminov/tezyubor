#!/usr/bin/env python3
"""ORVEX PAY: foydalanuvchi bergan ikonka rasmi (brand/app_icon_v2.png, 1254x1254, RGB, burchaklari qora)
dan Android launcher PNG'larini yasaydi.

Ishlatish: python3 render_launcher_from_png.py <app_icon_v2.png> <mobile_papka>
Chiqadi: mobile/launcher_res/mipmap-*/ic_launcher{,_background,_foreground}.png

- Eski (API<26) ikonka: rasm to'liq, burchaklari shaffof (squircle maska).
- Adaptive (API26+): fon = rasmning to'q yashil rangi, foreground = rasm (burchaklari shaffof) markazda 62% hajmda,
  shunda doira/skvirkl maskada ham butun rasm ko'rinadi (matn kesilmaydi).
"""
import sys, os
import numpy as np
from PIL import Image

SRC, MOBILE = sys.argv[1], sys.argv[2]
# Rasm chetidagi squircle: burchak o'lchami ~225px (1254 da), ko'rsatkich ~2.2 (ribbon chetini kesmaydi, qora soyani kesadi). 4px ichkariga olinadi (qora hoshiya qolmasin).
CORNER, EXP, INSET = 225.0, 2.2, 4.0

def squircle_alpha(n, supersample=4):
    """n x n, burchaklari yumaloq maska (0..1), anti-alias supersampling bilan."""
    N = n * supersample
    c = (N - 1) / 2.0
    half = N / 2.0 - INSET * supersample * (N / (1254.0 * supersample))
    s = CORNER * (N / 1254.0)
    ys, xs = np.mgrid[0:N, 0:N]
    dx, dy = np.abs(xs - c), np.abs(ys - c)
    inner = half - s  # to'g'ri chiziqli qism yarim kengligi
    ux = np.clip(dx - inner, 0, None) / s
    uy = np.clip(dy - inner, 0, None) / s
    inside = (ux ** EXP + uy ** EXP) <= 1.0
    inside &= (dx <= half) & (dy <= half)
    m = inside.astype(np.float32).reshape(n, supersample, n, supersample).mean(axis=(1, 3))
    return m

src = Image.open(SRC).convert("RGB")
assert src.size == (1254, 1254), src.size
full_alpha = squircle_alpha(1254, supersample=2)
rgba_full = np.dstack([np.asarray(src), (full_alpha * 255).round().astype(np.uint8)])
art = Image.fromarray(rgba_full, "RGBA")  # burchaklari shaffof 1254x1254

# Adaptive fon rangi: rasmning chet atrofidagi to'q yashil (maska ichida, burchaklardan uzoqda)
a = np.asarray(src).astype(int)
samples = np.concatenate([a[620:640, 6:16].reshape(-1, 3), a[6:16, 600:650].reshape(-1, 3)])
BG = tuple(int(v) for v in np.median(samples, axis=0))
print("adaptive fon rangi (median):", BG)

legacy = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
adaptive = {"mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432}
SCALE = 0.62

def save(img, rel):
    p = os.path.join(MOBILE, "launcher_res", rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    img.save(p, optimize=True)
    print("yozildi", rel, img.size, os.path.getsize(p))

for d, px in legacy.items():
    save(art.resize((px, px), Image.LANCZOS), f"mipmap-{d}/ic_launcher.png")
for d, px in adaptive.items():
    save(Image.new("RGB", (px, px), BG), f"mipmap-{d}/ic_launcher_background.png")
    side = round(px * SCALE)
    fg = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    fg.paste(art.resize((side, side), Image.LANCZOS), ((px - side) // 2, (px - side) // 2))
    save(fg, f"mipmap-{d}/ic_launcher_foreground.png")
