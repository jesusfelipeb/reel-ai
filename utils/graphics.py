from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from config import brand

# Alerta = naranja, positivo = cian (se distinguen tambien por luminosidad, no solo por tono)
RED = (*brand.ORANGE, 255)
GREEN = (*brand.CYAN, 255)
WHITE = (*brand.WHITE, 255)
NAVY = (*brand.NAVY, 255)


def _font(size: int, mono: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(brand.FONT_MONO if mono else brand.FONT_DISPLAY), size)


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def render_stamp(text: str, out_path: Path, subtext: str | None = None) -> None:
    """Sello tipo 'grunge stamp' rotado, fondo transparente."""
    w, h = 520, 200
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_main = _font(46)
    border_margin = 14
    draw.rounded_rectangle(
        [border_margin, border_margin, w - border_margin, h - border_margin],
        radius=10,
        fill=(*brand.NAVY, 215),  # fondo para que el texto se lea sobre cualquier imagen
        outline=RED,
        width=6,
    )

    tw, th = _text_size(draw, text.upper(), font_main)
    draw.text(((w - tw) / 2, (h - th) / 2 - (14 if subtext else 0)), text.upper(), font=font_main, fill=RED)

    if subtext:
        font_sub = _font(22, mono=True)
        sw, sh = _text_size(draw, subtext.upper(), font_sub)
        draw.text(((w - sw) / 2, h / 2 + 24), subtext.upper(), font=font_sub, fill=RED)

    img = img.rotate(-8, expand=True, resample=Image.BICUBIC)
    img.save(out_path)


def render_split(
    left_label: str,
    left_value: str,
    right_label: str,
    right_value: str,
    out_path: Path,
) -> None:
    """Tarjeta comparativa de dos mitades (verde/rojo) con check/cruz."""
    w, h = 950, 480
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle([0, 0, w, h], radius=28, fill=(*brand.NAVY, 235))

    half = w // 2
    pad = 18
    draw.rounded_rectangle([pad, pad, half - pad // 2, h - pad], radius=20, fill=(8, 46, 64, 255))
    draw.rounded_rectangle([half + pad // 2, pad, w - pad, h - pad], radius=20, fill=(64, 34, 16, 255))

    icon_size = 90
    cx_left, cy = half // 2, h // 2 - 70
    draw.line([cx_left - 36, cy, cx_left - 8, cy + 32], fill=GREEN, width=14, joint="curve")
    draw.line([cx_left - 8, cy + 32, cx_left + 44, cy - 30], fill=GREEN, width=14, joint="curve")

    cx_right = half + half // 2
    draw.line([cx_right - 32, cy - 32, cx_right + 32, cy + 32], fill=RED, width=14)
    draw.line([cx_right - 32, cy + 32, cx_right + 32, cy - 32], fill=RED, width=14)

    font_value = _font(96)
    font_label = _font(30, mono=True)

    vw, vh = _text_size(draw, left_value, font_value)
    draw.text((cx_left - vw / 2, cy + 40), left_value, font=font_value, fill=GREEN)
    lw, lh = _text_size(draw, left_label, font_label)
    draw.text((cx_left - lw / 2, cy + 40 + vh + 16), left_label, font=font_label, fill=WHITE)

    vw, vh = _text_size(draw, right_value, font_value)
    draw.text((cx_right - vw / 2, cy + 40), right_value, font=font_value, fill=RED)
    lw, lh = _text_size(draw, right_label, font_label)
    draw.text((cx_right - lw / 2, cy + 40 + vh + 16), right_label, font=font_label, fill=WHITE)

    badge_r = 42
    bx, by = w // 2, h // 2
    draw.ellipse([bx - badge_r, by - badge_r, bx + badge_r, by + badge_r], fill=WHITE)
    font_vs = _font(30)
    vsw, vsh = _text_size(draw, "VS", font_vs)
    draw.text((bx - vsw / 2, by - vsh / 2 - 4), "VS", font=font_vs, fill=NAVY)

    card.save(out_path)
