"""Tokens visuales de marca: una sola fuente de verdad para Python y para el HTML.

La paleta y las tipografias viven en `themes/<nombre>.json`. Este modulo las carga y las
expone como constantes de Python (para ffmpeg, libass y Pillow); las plantillas HTML reciben
el mismo JSON y lo aplican como variables CSS. Antes la paleta estaba escrita tres veces
—aca, en `motion/overlay.html` y en `motion/text_overlay.html`— y se desincronizaba.

Que tema se usa:
  1. el campo `brand` de la escena, si lo trae
  2. la variable de entorno REEL_BRAND
  3. "neutral"

Las medidas (zonas seguras, tamanos, loudness) NO son de marca: son restricciones de las
plataformas y de la legibilidad, asi que viven aca y no en el tema.
"""
import json
import os

from config.settings import BASE_DIR, PROJECT_DIR
from utils.paths import safe_name

THEMES_DIR = BASE_DIR / "themes"
# Un tema en la carpeta del usuario tiene prioridad sobre uno del proyecto con el mismo nombre.
THEME_DIRS = list(dict.fromkeys([PROJECT_DIR / "themes", THEMES_DIR]))
DEFAULT_BRAND = os.getenv("REEL_BRAND", "neutral")


def load_theme(name: str | None = None) -> dict:
    """Carga `themes/<name>.json`. El nombre puede venir de una escena, asi que se valida."""
    name = safe_name(name or DEFAULT_BRAND, "brand")
    for folder in THEME_DIRS:
        path = folder / f"{name}.json"
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    available = ", ".join(sorted({p.stem for d in THEME_DIRS for p in d.glob("*.json")})) or "ninguno"
    raise ValueError(f"No existe el tema '{name}'. Disponibles: {available}")


def rgb(hex_color: str) -> tuple[int, int, int]:
    """'#RRGGBB' -> (r, g, b)."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


THEME = load_theme()
_P = THEME["palette"]

FONTS_DIR = BASE_DIR / "fonts"
FONT_DISPLAY = FONTS_DIR / THEME["fonts"]["display"]  # titulares, subtitulos, numeros
FONT_MONO = FONTS_DIR / THEME["fonts"]["mono"]  # etiquetas cortas
FONT_DISPLAY_NAME = THEME["fonts"]["display_family"]  # nombre de familia que ve libass

# Paleta (RGB). Cian vs naranja se distinguen tambien por luminosidad, no solo por tono.
NAVY = rgb(_P["navy"])
WHITE = rgb(_P["white"])
CYAN = rgb(_P["cyan"])
LIME = rgb(_P["lime"])
ORANGE = rgb(_P["orange"])


def hex_ffmpeg(rgb_color: tuple[int, int, int]) -> str:
    """(r,g,b) -> '0xRRGGBB' para filtros de ffmpeg."""
    return "0x{:02X}{:02X}{:02X}".format(*rgb_color)


def hex_ass(rgb_color: tuple[int, int, int], alpha: int = 0) -> str:
    """(r,g,b) -> '&HAABBGGRR' (ASS usa orden BGR y alpha invertido: 00 = opaco)."""
    r, g, b = rgb_color
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"


# Zonas seguras (lo que tapa la interfaz de Reels/TikTok/Shorts)
SAFE_TOP = 220
SAFE_BOTTOM = 440

# Subtitulos: la base del texto queda en y = OUTPUT_HEIGHT - CAPTION_MARGIN_V (~1380)
CAPTION_FONT_SIZE = 76
CAPTION_OUTLINE = 8
CAPTION_MARGIN_V = 540
CAPTION_MARGIN_H = 90
CAPTION_ACTIVE_SCALE = 108  # % de escala de la palabra que se esta diciendo

# Graficos: franja superior libre (entre la zona segura y el borde de arriba del video)
GFX_TOP = SAFE_TOP + 30
GFX_SPLIT_WIDTH = 780  # alto ~394 px: entra entre GFX_TOP y el borde superior del video (y=656)

# Barra de progreso
PROGRESS_HEIGHT = 8

# Audio (estandar de plataformas moviles)
LOUDNESS_LUFS = -14
TRUE_PEAK_DB = -1.5

assert CAPTION_MARGIN_V >= SAFE_BOTTOM, "los subtitulos no pueden caer en la zona tapada"
