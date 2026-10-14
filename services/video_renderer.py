import json
import subprocess
from pathlib import Path

from config import brand
from config.settings import OUTPUT_HEIGHT, OUTPUT_WIDTH
from utils.graphics import render_split, render_stamp


def _escape_ffmpeg_path(path: Path) -> str:
    return str(path).replace(":", r"\:").replace("'", r"\'")


def _escape_drawtext(text: str) -> str:
    return text.replace("\\", r"\\").replace(":", r"\:").replace("'", r"\'")


def _build_image_overlay(graphic: dict, src: str, dst: str) -> str:
    """Anima el PNG de [1:v] (stamp/split) y lo superpone sobre `src`, saliendo en `dst`."""
    offset = float(graphic["offset"])
    duration = float(graphic["duration"])

    if graphic["type"] == "stamp":
        prep = (
            f"[1:v]scale=w='iw*(0.8+0.2*min(max((t-{offset})/0.2\\,0)\\,1))"
            f"*(1+0.035*sin(2*PI*(t-{offset})*2))':h=-1:eval=frame[gfx]"
        )
    else:  # split
        fade_in_end = offset + 0.25
        fade_out_start = max(offset + duration - 0.25, fade_in_end)
        prep = (
            f"[1:v]scale={brand.GFX_SPLIT_WIDTH}:-1,format=rgba,"
            f"fade=t=in:st={offset}:d=0.25:alpha=1,"
            f"fade=t=out:st={fade_out_start}:d=0.25:alpha=1[gfx]"
        )

    enable = f"enable='between(t,{offset},{offset + duration})'"
    overlay = f"[{src}][gfx]overlay=x=(W-w)/2:y={brand.GFX_TOP}:{enable}[{dst}]"
    return f"{prep};{overlay}"


def _build_counter_drawtext(graphic: dict, src: str, dst: str) -> str:
    offset = float(graphic["offset"])
    duration = float(graphic["duration"])
    end = offset + duration
    prefix = _escape_drawtext(graphic["prefix"])
    label = _escape_drawtext(graphic["label"])
    target = int(graphic["target"])
    font_display = _escape_ffmpeg_path(brand.FONT_DISPLAY)
    font_mono = _escape_ffmpeg_path(brand.FONT_MONO)
    enable = f"enable='between(t,{offset},{end})'"

    label_draw = (
        f"drawtext=fontfile='{font_mono}':text='{label}':fontsize=34:"
        f"fontcolor={brand.hex_ffmpeg(brand.WHITE)}:x=(w-text_w)/2:y={brand.GFX_TOP}:"
        f"box=1:boxcolor={brand.hex_ffmpeg(brand.NAVY)}@0.85:boxborderw=16:{enable}"
    )
    counter_draw = (
        f"drawtext=fontfile='{font_display}':"
        f"text='{prefix}%{{eif\\:min({target}\\,(t-{offset})/{duration}*{target})\\:d}}':"
        f"fontsize=96:fontcolor={brand.hex_ffmpeg(brand.LIME)}:"
        f"borderw=6:bordercolor={brand.hex_ffmpeg(brand.NAVY)}:"
        f"x=(w-text_w)/2:y={brand.GFX_TOP + 80}:{enable}"
    )
    return f"[{src}]{label_draw},{counter_draw}[{dst}]"


def _build_progress_bar(duration: float, src: str, dst: str) -> str:
    # drawbox (ffmpeg 6) no acepta `t` en el ancho: se usa una barra de color que
    # entra desde la izquierda con overlay evaluado por frame.
    return (
        f"color=c={brand.hex_ffmpeg(brand.LIME)}:s={OUTPUT_WIDTH}x{brand.PROGRESS_HEIGHT}"
        f":d={duration}[bar];"
        f"[{src}][bar]overlay=x='-w+w*t/{duration}':y=0:eval=frame[{dst}]"
    )


def _loudnorm_filter(source_video: Path, start: float, end: float) -> str:
    """loudnorm en dos pasadas: mide el fragmento y aplica una ganancia lineal.

    Una sola pasada (modo dinamico) no llega al objetivo en fragmentos con silencio
    o musica de intro (se midio -17.3 LUFS con objetivo -14).
    """
    target = f"I={brand.LOUDNESS_LUFS}:TP={brand.TRUE_PEAK_DB}:LRA=11"
    result = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-nostats",
            "-ss", str(start), "-to", str(end), "-i", str(source_video),
            "-vn", "-af", f"loudnorm={target}:print_format=json", "-f", "null", "-",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    # loudnorm imprime el JSON al final de stderr
    stats = json.loads(result.stderr[result.stderr.rindex("{"):])
    return (
        f"loudnorm={target}:linear=true"
        f":measured_I={stats['input_i']}:measured_TP={stats['input_tp']}"
        f":measured_LRA={stats['input_lra']}:measured_thresh={stats['input_thresh']}"
        f":offset={stats['target_offset']}"
    )


def render_fragment(
    source_video: Path,
    start: float,
    end: float,
    ass_path: Path,
    out_path: Path,
    graphic: dict | None = None,
    graphic_asset_path: Path | None = None,
) -> None:
    """Corta el fragmento a vertical 9:16 sin recortar nada del frame original:
    el video completo entra centrado, con fondo difuminado del mismo video
    rellenando arriba/abajo. Encima: subtitulos, grafico opcional (sello,
    comparacion o contador) y barra de progreso. Audio normalizado a -14 LUFS.
    """
    duration = end - start
    ass_escaped = _escape_ffmpeg_path(ass_path)
    fonts_escaped = _escape_ffmpeg_path(brand.FONTS_DIR)

    chains = [
        f"[0:v]split=2[bg][fg];"
        f"[bg]scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={OUTPUT_WIDTH}:{OUTPUT_HEIGHT},gblur=sigma=20[bgblur];"
        f"[fg]scale={OUTPUT_WIDTH}:-2:force_original_aspect_ratio=decrease[fgscaled];"
        f"[bgblur][fgscaled]overlay=(W-w)/2:(H-h)/2,"
        f"ass='{ass_escaped}':fontsdir='{fonts_escaped}'[vbase]"
    ]
    last = "vbase"

    extra_inputs: list[str] = []
    if graphic and graphic["type"] == "counter":
        chains.append(_build_counter_drawtext(graphic, last, "vgfx"))
        last = "vgfx"
    elif graphic and graphic["type"] in ("stamp", "split") and graphic_asset_path:
        # -loop 1: sin esto ffmpeg solo decodifica un frame estatico en t=0 y lo
        # congela; las expresiones de escala/fade (que dependen de t) quedarian
        # evaluadas una sola vez en t=0 en vez de animarse en tiempo real.
        # -t acota el loop infinito a la duracion del fragmento (si no, ffmpeg
        # nunca ve EOF en este input y el proceso no termina nunca).
        extra_inputs = ["-loop", "1", "-t", str(duration), "-i", str(graphic_asset_path)]
        chains.append(_build_image_overlay(graphic, last, "vgfx"))
        last = "vgfx"

    chains.append(_build_progress_bar(duration, last, "vout"))

    loudnorm = _loudnorm_filter(source_video, start, end)

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-ss", str(start), "-to", str(end), "-i", str(source_video),
            *extra_inputs,
            "-filter_complex", ";".join(chains),
            "-map", "[vout]", "-map", "0:a",
            "-af", loudnorm, "-ar", "48000",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart",
            str(out_path),
        ],
        check=True,
        capture_output=True,
    )


def build_graphic_asset(graphic: dict, out_path: Path) -> Path | None:
    """Genera el PNG del grafico (stamp/split) si corresponde. Counter no necesita asset."""
    gtype = graphic["type"]
    if gtype == "stamp":
        render_stamp(graphic["text"], out_path, subtext=graphic.get("subtext"))
        return out_path
    if gtype == "split":
        render_split(
            graphic["left_label"], graphic["left_value"],
            graphic["right_label"], graphic["right_value"],
            out_path,
        )
        return out_path
    return None
