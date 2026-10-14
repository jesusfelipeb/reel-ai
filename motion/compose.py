"""Compone un short animado a partir de una escena de motion/scenes/*.json.

Pipeline:
  1. timeline.json = escena + palabras de la transcripcion (relativas al inicio del fragmento)
  2. motion/render_overlay.cjs renderiza motion/overlay.html cuadro por cuadro (PNG con alpha)
  3. ffmpeg arma el video base por segmentos (layout completo / dividido) con zoom animado,
     superpone el overlay y normaliza el audio.

Uso: python -m motion.compose examples/seo-cuentas.json [--reuse-frames]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from config.brand import hex_ffmpeg, load_theme, rgb
from config.settings import BASE_DIR, OUTPUT_DIR, PROJECT_DIR, TMP_DIR
from motion.node import node_env
from services.video_renderer import _loudnorm_filter
from utils.paths import resolve_inside, safe_name
from utils.subtitles import _clean

FPS = 30
PANEL_MOVE = 0.45  # igual que en overlay.html: el corte de camara ocurre cuando el panel aterriza
SRC_W, SRC_H = 1920, 1080


def _relative_words(scene: dict) -> list[dict]:
    cache_path = resolve_inside(PROJECT_DIR, scene.get("transcription"), "transcription")
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    words = cache["transcription"]["words"]
    start, end = scene["start"], scene["end"]
    rel = [
        {"text": _clean(w["word"]), "start": round(w["start"] - start, 3), "end": round(w["end"] - start, 3)}
        for w in words
        if w["start"] >= start and w["end"] <= end + 0.2
    ]
    return sorted((w for w in rel if w["text"]), key=lambda w: w["start"])


def _segments(scene: dict) -> list[tuple[float, float, str]]:
    """Tramos del video base: 'full' (hablante 9:16) o 'split' (hablante en la mitad inferior).

    El ultimo tramo se extiende durante la tarjeta de cierre: el hablante sigue en movimiento
    mientras el panel crece y lo tapa (tpad despues de zoompan+concat no extendia el video).
    """
    total = scene["end"] - scene["start"] + scene["end_card_seconds"]
    cuts = []
    for a, b in scene["split_windows"]:
        cuts.append((a + PANEL_MOVE, "split"))
        if b < scene["end"] - scene["start"] - 0.01:
            cuts.append((b, "full"))
    segs, t, layout = [], 0.0, "full"
    for at, nxt in sorted(cuts):
        segs.append((t, at, layout))
        t, layout = at, nxt
    segs.append((t, total, layout))
    return [s for s in segs if s[1] - s[0] > 1 / FPS]


_EASE = {
    "linear": "(P)",
    "outCubic": "(1-pow(1-(P),3))",
    "inOutCubic": "if(lt(P,0.5),4*pow(P,3),1-pow(-2*(P)+2,3)/2)",
}


def _zoom_expr(keys: list[list], time_expr: str) -> str:
    """Keyframes [[t, zoom, ease]] -> expresion ffmpeg. 'cut' = salto; otra ease interpola desde el anterior."""
    expr = str(keys[-1][1])
    for i in range(len(keys) - 1, 0, -1):
        t0, z0 = keys[i - 1][0], keys[i - 1][1]
        t1, z1 = keys[i][0], keys[i][1]
        ease = keys[i][2] if len(keys[i]) > 2 else "cut"
        if ease == "cut":
            seg = str(z0)
        else:
            p = f"clip(({time_expr}-{t0})/{t1 - t0},0,1)"
            seg = f"({z0}+({z1 - z0})*{_EASE[ease].replace('P', p)})"
        expr = f"if(lt({time_expr},{t1}),{seg},{expr})"
    return f"if(lt({time_expr},{keys[0][0]}),{keys[0][1]},{expr})"


def _shake_expr(times: list[float], time_expr: str, amp_px: float) -> str:
    parts = [
        f"if(between({time_expr},{ts},{ts + 0.45}),{amp_px}*exp(-({time_expr}-{ts})*9)*sin(({time_expr}-{ts})*70),0)"
        for ts in times
    ]
    return "+".join(parts) if parts else "0"


def _segment_chain(idx: int, seg: tuple[float, float, str], scene: dict, pad_color: str) -> str:
    t0, t1, layout = seg
    face_x = scene["face"]["x"] * SRC_W
    fy = scene["face"]["y"]
    t_expr = f"({t0}+on/{FPS})"
    zoom = _zoom_expr(scene["zoom"][layout], t_expr)
    shake = _shake_expr(scene.get("shake_at", []), t_expr, 24)

    if layout == "full":
        cw = round(SRC_H * 9 / 16)
        up_w, up_h, out = 2160, 3840, "1080x1920"
        tail = "setsar=1"
    else:
        cw = round(SRC_H * 1080 / 960)
        up_w, up_h, out = 2160, 1920, "1080x960"
        tail = f"pad=1080:1920:0:960:color={pad_color},setsar=1"
    # min_x deja afuera elementos quemados en el borde del video original (ej. badge de redes)
    min_x = scene["face"].get("min_x", 0)
    cx = int(min(max(face_x - cw / 2, min_x), SRC_W - cw))

    return (
        f"[v{idx}]trim=start={t0}:end={t1},setpts=PTS-STARTPTS,"
        f"crop={cw}:{SRC_H}:{cx}:0,scale={up_w}:{up_h}:flags=lanczos,"
        f"zoompan=z='{zoom}':x='0.5*(iw-iw/zoom)+{shake}':y='{fy}*(ih-ih/zoom)':d=1:s={out}:fps={FPS},"
        f"{tail}[s{idx}]"
    )


def render_overlay(timeline_path: Path, frames_dir: Path) -> None:
    env = node_env()
    subprocess.run(
        ["node", str(BASE_DIR / "motion/render_overlay.cjs"), str(timeline_path), str(frames_dir), str(FPS), "6"],
        check=True,
        env=env,
    )


def compose(scene_path: Path, reuse_frames: bool) -> Path:
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    # `name` y `source` acaban formando rutas de disco y la escena es dato no confiable.
    name = safe_name(scene.get("name"), "name")
    work = TMP_DIR / "motion" / name
    frames_dir = work / "frames"
    work.mkdir(parents=True, exist_ok=True)

    theme = load_theme(scene.get("brand"))
    # El relleno del layout dividido tiene que ser el mismo fondo que usa el panel del overlay.
    pad_color = hex_ffmpeg(rgb(theme["palette"]["navy"]))

    timeline_path = work / "timeline.json"
    timeline_path.write_text(
        json.dumps({"scene": scene, "words": _relative_words(scene), "theme": theme}, ensure_ascii=False),
        encoding="utf-8",
    )

    if not (reuse_frames and any(frames_dir.glob("f*.png"))):
        print("[1/2] Renderizando overlay animado (Playwright)...")
        render_overlay(timeline_path, frames_dir)
    else:
        print("[1/2] Reutilizando frames del overlay")

    total = scene["end"] - scene["start"]
    end_card = scene["end_card_seconds"]
    segs = _segments(scene)
    source = resolve_inside(PROJECT_DIR, scene.get("source"), "source")

    chains = [f"[0:v]split={len(segs)}" + "".join(f"[v{i}]" for i in range(len(segs)))]
    chains += [_segment_chain(i, seg, scene, pad_color) for i, seg in enumerate(segs)]
    chains.append(
        "".join(f"[s{i}]" for i in range(len(segs)))
        + f"concat=n={len(segs)}:v=1:a=0[base]"
    )
    chains.append("[base][1:v]overlay=0:0:format=auto,format=yuv420p[vout]")
    loudnorm = _loudnorm_filter(source, scene["start"], scene["end"])
    chains.append(
        f"[0:a]atrim=end={total},asetpts=PTS-STARTPTS,{loudnorm},afade=t=out:st={total - 0.25}:d=0.25,apad=whole_dur={total + end_card}[aout]"
    )

    out_dir = OUTPUT_DIR / "motion"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{name}.mp4"

    print("[2/2] Componiendo video final (ffmpeg)...")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-ss", str(scene["start"]), "-to", str(scene["end"] + end_card), "-i", str(source),
            "-framerate", str(FPS), "-i", str(frames_dir / "f%05d.png"),
            "-filter_complex", ";".join(chains),
            "-map", "[vout]", "-map", "[aout]",
            "-t", str(total + end_card), "-r", str(FPS),
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
            "-movflags", "+faststart",
            str(out_path),
        ],
        check=True,
        capture_output=True,
    )
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compone un short animado desde una escena JSON")
    parser.add_argument("scene", type=Path)
    parser.add_argument("--reuse-frames", action="store_true", help="no re-renderizar el overlay")
    args = parser.parse_args()
    try:
        print(f"Listo: {compose(args.scene, args.reuse_frames)}")
    except ValueError as err:
        sys.exit(f"Escena invalida: {err}")
    except subprocess.CalledProcessError as err:
        stderr = err.stderr.decode(errors="replace") if isinstance(err.stderr, bytes) else (err.stderr or "")
        sys.exit(f"Fallo {err.cmd[0]}:\n{stderr[-3000:]}")
