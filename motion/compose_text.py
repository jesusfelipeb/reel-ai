"""Compone un short 100 % animado a partir de un guion de beats (sin video de fuente ni voz).

Pipeline:
  1. timeline.json = escena (beats con tiempos absolutos)
  2. motion/render_text.cjs renderiza motion/text_overlay.html cuadro por cuadro (PNG opaco)
  3. ffmpeg encadena los cuadros y agrega una pista de audio silenciosa (compatibilidad con redes)

Uso: python -m motion.compose_text examples/agente-contenido.json [--reuse-frames] [--stills 1,5,12]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from config.brand import load_theme
from config.settings import BASE_DIR, OUTPUT_DIR, TMP_DIR
from motion.node import node_env
from utils.paths import safe_name

FPS = 30
WORKERS = 6


def render_frames(timeline_path: Path, frames_dir: Path, only: str | None = None) -> None:
    env = node_env()
    cmd = ["node", str(BASE_DIR / "motion/render_text.cjs"), str(timeline_path), str(frames_dir), str(FPS), str(WORKERS)]
    if only:
        cmd.append(only)
    # El progreso va a stderr: stdout queda libre para la salida --json de reel.py.
    # El stderr de node se captura para que, si falla, el error llegue a quien llamo
    # (antes el JSON decia solo "Fallo node" y la causa quedaba suelta en la consola).
    subprocess.run(cmd, check=True, env=env, stdout=sys.stderr, stderr=subprocess.PIPE)


def compose(scene_path: Path, reuse_frames: bool, stills: str | None) -> Path:
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    # `name` acaba formando rutas de disco y la escena es dato no confiable.
    name = safe_name(scene.get("name"), "name")
    work = TMP_DIR / "motion" / name
    frames_dir = work / "frames"
    work.mkdir(parents=True, exist_ok=True)

    timeline_path = work / "timeline.json"
    timeline = {"scene": scene, "theme": load_theme(scene.get("brand"))}
    timeline_path.write_text(json.dumps(timeline, ensure_ascii=False), encoding="utf-8")

    if stills:
        # En output/ y no en .tmp/: en Docker .tmp/ queda dentro del contenedor y nadie
        # podria mirarlas. Se vacia antes para no mezclar capturas de una version anterior.
        stills_dir = OUTPUT_DIR / "stills" / name
        for old in stills_dir.glob("still-*.png"):
            old.unlink()
        render_frames(timeline_path, stills_dir, stills)
        return stills_dir

    if not (reuse_frames and any(frames_dir.glob("f*.png"))):
        print("[1/2] Renderizando animacion (Playwright)...", file=sys.stderr)
        render_frames(timeline_path, frames_dir)
    else:
        print("[1/2] Reutilizando frames", file=sys.stderr)

    out_dir = OUTPUT_DIR / "motion"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{name}.mp4"
    duration = scene["duration"]

    print("[2/2] Componiendo video final (ffmpeg)...", file=sys.stderr)
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-framerate", str(FPS), "-i", str(frames_dir / "f%05d.png"),
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-map", "0:v", "-map", "1:a",
            "-t", str(duration), "-r", str(FPS),
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            str(out_path),
        ],
        check=True,
        capture_output=True,
    )
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compone un short animado solo con texto desde un guion JSON")
    parser.add_argument("scene", type=Path)
    parser.add_argument("--reuse-frames", action="store_true", help="no re-renderizar la animacion")
    parser.add_argument("--stills", help="solo capturas en estos segundos (ej. 2,7,15) para revisar el diseño")
    args = parser.parse_args()
    try:
        print(f"Listo: {compose(args.scene, args.reuse_frames, args.stills)}")
    except ValueError as err:
        sys.exit(f"Escena invalida: {err}")
    except subprocess.CalledProcessError as err:
        stderr = err.stderr.decode(errors="replace") if isinstance(err.stderr, bytes) else (err.stderr or "")
        sys.exit(f"Fallo {err.cmd[0]}:\n{stderr[-3000:]}")
