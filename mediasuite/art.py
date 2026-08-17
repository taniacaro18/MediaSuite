"""Ilustraciones dibujadas con Pillow (sin archivos externos)."""

from __future__ import annotations

from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter

ROSE = (244, 160, 192, 255)
ROSE_D = (216, 112, 160, 255)
BLUSH = (253, 230, 241, 255)
CREAM = (255, 252, 255, 255)
GOLD = (183, 148, 244, 255)
SAGE = (158, 196, 245, 255)
COCOA = (50, 38, 74, 230)
LILAC = (201, 176, 232, 255)
PEACH = (232, 220, 255, 255)
BLUE = (158, 196, 245, 255)


def _canvas(size: int, scale: int = 3) -> tuple[Image.Image, ImageDraw.ImageDraw, int]:
    side = size * scale
    img = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img), scale


def _down(img: Image.Image, size: int) -> Image.Image:
    return img.resize((size, size), Image.Resampling.LANCZOS)


def _circle(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, fill) -> None:
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill)


def _round_rect(draw: ImageDraw.ImageDraw, box, radius: int, fill) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def logo(size: int = 96) -> Image.Image:
    img, draw, s = _canvas(size)
    c = img.width // 2
    _round_rect(draw, (6 * s, 6 * s, img.width - 6 * s, img.height - 6 * s), 28 * s, BLUSH)
    _circle(draw, c, c, 28 * s, ROSE)
    for dx, dy in ((-22, -8), (22, -8), (0, -24), (-16, 18), (16, 18)):
        _circle(draw, c + dx * s, c + dy * s, 9 * s, GOLD)
    _circle(draw, c, c, 11 * s, CREAM)
    _circle(draw, c - 4 * s, c - 4 * s, 3 * s, (255, 255, 255, 200))
    return _down(img, size)


def icon_home(size: int = 96) -> Image.Image:
    img, draw, s = _canvas(size)
    c = img.width // 2
    _circle(draw, c, c, 46 * s, BLUSH)
    # heart
    _circle(draw, c - 12 * s, c - 6 * s, 14 * s, ROSE)
    _circle(draw, c + 12 * s, c - 6 * s, 14 * s, ROSE)
    draw.polygon(
        [(c - 24 * s, c - 2 * s), (c + 24 * s, c - 2 * s), (c, c + 26 * s)],
        fill=ROSE,
    )
    _circle(draw, c + 18 * s, c - 22 * s, 4 * s, GOLD)
    _circle(draw, c - 26 * s, c + 16 * s, 3 * s, GOLD)
    return _down(img, size)


def icon_silence(size: int = 96) -> Image.Image:
    img, draw, s = _canvas(size)
    c = img.width // 2
    _circle(draw, c, c, 46 * s, BLUSH)
    bars = [10, 18, 28, 38, 24, 16, 12]
    x0 = c - 28 * s
    for i, h in enumerate(bars):
        x = x0 + i * 8 * s
        _round_rect(draw, (x, c - h * s, x + 5 * s, c + h * s), 3 * s, ROSE if i % 2 else GOLD)
    # scissors
    _circle(draw, c + 18 * s, c + 20 * s, 8 * s, CREAM)
    _circle(draw, c + 30 * s, c + 12 * s, 8 * s, CREAM)
    draw.line((c + 18 * s, c + 20 * s, c + 4 * s, c - 8 * s), fill=ROSE_D, width=3 * s)
    draw.line((c + 30 * s, c + 12 * s, c + 8 * s, c - 18 * s), fill=ROSE_D, width=3 * s)
    return _down(img, size)


def icon_watermark(size: int = 96) -> Image.Image:
    img, draw, s = _canvas(size)
    c = img.width // 2
    _circle(draw, c, c, 46 * s, PEACH)
    _round_rect(draw, (c - 28 * s, c - 22 * s, c + 28 * s, c + 22 * s), 8 * s, CREAM)
    _round_rect(draw, (c - 22 * s, c - 14 * s, c + 22 * s, c + 14 * s), 5 * s, LILAC)
    # sparkle stamp
    _circle(draw, c + 16 * s, c + 16 * s, 12 * s, ROSE)
    draw.polygon(
        [(c + 16 * s, c + 6 * s), (c + 19 * s, c + 14 * s), (c + 27 * s, c + 16 * s),
         (c + 19 * s, c + 18 * s), (c + 16 * s, c + 26 * s), (c + 13 * s, c + 18 * s),
         (c + 5 * s, c + 16 * s), (c + 13 * s, c + 14 * s)],
        fill=GOLD,
    )
    return _down(img, size)


def icon_convert(size: int = 96) -> Image.Image:
    img, draw, s = _canvas(size)
    c = img.width // 2
    _circle(draw, c, c, 46 * s, BLUE)
    _round_rect(draw, (c - 30 * s, c - 18 * s, c + 8 * s, c + 10 * s), 8 * s, GOLD)
    _round_rect(draw, (c - 8 * s, c - 8 * s, c + 30 * s, c + 20 * s), 8 * s, ROSE)
    _circle(draw, c + 22 * s, c - 20 * s, 10 * s, CREAM)
    draw.arc((c + 14 * s, c - 28 * s, c + 30 * s, c - 12 * s), 40, 300, fill=SAGE, width=3 * s)
    return _down(img, size)


def icon_images(size: int = 96) -> Image.Image:
    img, draw, s = _canvas(size)
    c = img.width // 2
    _circle(draw, c, c, 46 * s, PEACH)
    _round_rect(draw, (c - 26 * s, c - 28 * s, c + 26 * s, c + 30 * s), 6 * s, CREAM)
    _round_rect(draw, (c - 20 * s, c - 22 * s, c + 20 * s, c + 12 * s), 4 * s, ROSE)
    _circle(draw, c - 6 * s, c - 8 * s, 6 * s, GOLD)
    draw.polygon([(c - 18 * s, c + 12 * s), (c - 2 * s, c - 4 * s), (c + 20 * s, c + 12 * s)], fill=LILAC)
    _circle(draw, c, c + 22 * s, 4 * s, ROSE)
    return _down(img, size)


def icon_audio(size: int = 96) -> Image.Image:
    img, draw, s = _canvas(size)
    c = img.width // 2
    _circle(draw, c, c, 46 * s, SAGE)
    _circle(draw, c, c + 4 * s, 28 * s, COCOA)
    _circle(draw, c, c + 4 * s, 18 * s, ROSE)
    _circle(draw, c, c + 4 * s, 7 * s, CREAM)
    # notes
    _circle(draw, c + 22 * s, c - 22 * s, 5 * s, GOLD)
    draw.line((c + 26 * s, c - 22 * s, c + 26 * s, c - 38 * s), fill=GOLD, width=3 * s)
    _circle(draw, c + 32 * s, c - 16 * s, 5 * s, GOLD)
    draw.line((c + 36 * s, c - 16 * s, c + 36 * s, c - 32 * s), fill=GOLD, width=3 * s)
    return _down(img, size)


def banner(kind: str, width: int = 920, height: int = 128) -> Image.Image:
    scale = 2
    img = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    w, h = img.size
    draw.rounded_rectangle((0, 0, w - 1, h - 1), radius=40, fill=BLUSH)
    draw.ellipse((int(w * 0.55), -40, w + 80, int(h * 0.9)), fill=PEACH)
    draw.ellipse((int(w * 0.72), int(h * 0.15), w + 40, h + 60), fill=(255, 252, 251, 140))
    draw.ellipse((-40, int(h * 0.4), int(w * 0.28), h + 50), fill=(201, 162, 122, 70))
    icon = ICONS.get(kind, logo)(96)
    icon = icon.resize((96 * scale, 96 * scale), Image.Resampling.LANCZOS)
    img.paste(icon, (28 * scale, (h - icon.height) // 2), icon)
    img = img.filter(ImageFilter.GaussianBlur(radius=0.2))
    return img.resize((width, height), Image.Resampling.LANCZOS)


ICONS = {
    "inicio": icon_home,
    "silencios": icon_silence,
    "marcas": icon_watermark,
    "convertir": icon_convert,
    "imagenes": icon_images,
    "audio": icon_audio,
}


@lru_cache(maxsize=64)
def pil_icon(kind: str, size: int = 96) -> Image.Image:
    fn = ICONS.get(kind, logo)
    if kind == "logo":
        return logo(size)
    return fn(size)
