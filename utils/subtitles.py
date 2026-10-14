import re
from pathlib import Path

from config.brand import (
    CAPTION_ACTIVE_SCALE,
    CAPTION_FONT_SIZE,
    CAPTION_MARGIN_H,
    CAPTION_MARGIN_V,
    CAPTION_OUTLINE,
    FONT_DISPLAY_NAME,
    LIME,
    NAVY,
    WHITE,
    hex_ass,
)
from config.settings import OUTPUT_HEIGHT, OUTPUT_WIDTH

# Bold=0: la fuente ya es Black; con Bold=-1 libass le aplicaria negrita sintetica encima.
# Alignment 2 (abajo-centro) + MarginV: con Alignment 5 libass ignora MarginV.
ASS_HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {OUTPUT_WIDTH}
PlayResY: {OUTPUT_HEIGHT}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{FONT_DISPLAY_NAME},{CAPTION_FONT_SIZE},{hex_ass(WHITE)},{hex_ass(WHITE)},{hex_ass(NAVY)},{hex_ass(NAVY)},0,0,0,0,100,100,0,0,1,{CAPTION_OUTLINE},0,2,{CAPTION_MARGIN_H},{CAPTION_MARGIN_H},{CAPTION_MARGIN_V},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

# Reglas de agrupacion: una frase corta por pantalla, no bloques fijos de N palabras.
MAX_WORDS_PER_CAPTION = 4
MAX_CHARS_PER_CAPTION = 18
PAUSE_BREAK_SECONDS = 0.35
# Si entre dos grupos hay menos que esto, el anterior se estira para evitar parpadeo.
BRIDGE_GAP_SECONDS = 0.3

_PHRASE_END = re.compile(r"[.,;:?!…]$")
# Override inline: \c usa &HBBGGRR& (sin canal alpha, a diferencia del bloque Style)
_ACTIVE_TAG = (
    f"{{\\c&H{LIME[2]:02X}{LIME[1]:02X}{LIME[0]:02X}&"
    f"\\fscx{CAPTION_ACTIVE_SCALE}\\fscy{CAPTION_ACTIVE_SCALE}}}"
)


def _format_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def _clean(word: str) -> str:
    # Llaves y barras invertidas romperian los override tags de ASS
    return re.sub(r"[{}\\]", "", word.strip()).upper()


def _group_words(words: list[dict]) -> list[list[dict]]:
    groups: list[list[dict]] = []
    current: list[dict] = []
    for word in words:
        if current:
            text_len = len(" ".join(w["text"] for w in current + [word]))
            pause = word["start"] - current[-1]["end"]
            if (
                len(current) >= MAX_WORDS_PER_CAPTION
                or text_len > MAX_CHARS_PER_CAPTION
                or pause > PAUSE_BREAK_SECONDS
                or _PHRASE_END.search(current[-1]["text"])
            ):
                groups.append(current)
                current = []
        current.append(word)
    if current:
        groups.append(current)
    return groups


def _render_group(group: list[dict], active: int) -> str:
    parts = []
    for i, w in enumerate(group):
        parts.append(f"{_ACTIVE_TAG}{w['text']}{{\\r}}" if i == active else w["text"])
    return " ".join(parts)


def build_ass(words: list[dict], fragment_start: float, fragment_end: float, out_path: Path) -> None:
    """Genera un .ass con captions agrupados por frase y la palabra activa resaltada.

    Cada grupo produce un evento por palabra: el texto del grupo es el mismo, solo cambia
    cual palabra va en color de acento. Timestamps relativos al inicio del fragmento.
    """
    relevant = [
        {
            "text": _clean(w["word"]),
            "start": w["start"] - fragment_start,
            "end": w["end"] - fragment_start,
        }
        for w in words
        if w["start"] >= fragment_start and w["end"] <= fragment_end
    ]
    relevant = [w for w in relevant if w["text"]]
    groups = _group_words(relevant)

    lines = [ASS_HEADER]
    for g_idx, group in enumerate(groups):
        group_end = group[-1]["end"]
        if g_idx + 1 < len(groups):
            next_start = groups[g_idx + 1][0]["start"]
            if next_start - group_end < BRIDGE_GAP_SECONDS:
                group_end = next_start

        for i, word in enumerate(group):
            start = max(word["start"], 0)
            end = group[i + 1]["start"] if i + 1 < len(group) else group_end
            if end <= start:
                continue
            lines.append(
                f"Dialogue: 0,{_format_time(start)},{_format_time(end)},Caption,,0,0,0,,"
                f"{_render_group(group, i)}\n"
            )

    out_path.write_text("".join(lines), encoding="utf-8")
