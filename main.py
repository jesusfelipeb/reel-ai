import argparse
import re
import sys
from pathlib import Path

from config.settings import INPUT_DIR, OUTPUT_DIR, TMP_DIR
from services.fragment_selector import select_fragments
from services.transcription import (
    extract_audio,
    load_cached_transcription,
    save_transcription,
    transcribe,
)
from services.video_renderer import build_graphic_asset, render_fragment
from utils.subtitles import build_ass


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug or "short"


def run(video_path: Path) -> None:
    if not video_path.exists():
        sys.exit(f"No existe el archivo: {video_path}")

    TMP_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    cache_path = TMP_DIR / f"{video_path.stem}.transcription.json"
    transcription = load_cached_transcription(video_path, cache_path)
    if transcription:
        print("[1-2/4] Transcripcion en cache, se omite Whisper")
    else:
        audio_path = TMP_DIR / f"{video_path.stem}.wav"
        print(f"[1/4] Extrayendo audio de {video_path.name}...")
        extract_audio(video_path, audio_path)

        print("[2/4] Transcribiendo con Groq Whisper...")
        transcription = transcribe(audio_path)
        save_transcription(video_path, cache_path, transcription)
    segments = transcription["segments"]
    words = transcription["words"]

    print("[3/4] Seleccionando los mejores 5 fragmentos...")
    fragments = select_fragments(segments)

    print("[4/4] Renderizando shorts verticales con subtitulos...")
    for i, frag in enumerate(fragments, start=1):
        start, end = float(frag["start"]), float(frag["end"])
        title = frag.get("title", f"short-{i}")
        slug = slugify(title)

        ass_path = TMP_DIR / f"{video_path.stem}-{i}-{slug}.ass"
        out_path = OUTPUT_DIR / f"{i}-{slug}.mp4"

        build_ass(words, start, end, ass_path)

        graphic = frag.get("graphic")
        graphic_asset_path = None
        if graphic:
            asset_path = TMP_DIR / f"{video_path.stem}-{i}-{slug}-gfx.png"
            graphic_asset_path = build_graphic_asset(graphic, asset_path)

        render_fragment(video_path, start, end, ass_path, out_path, graphic, graphic_asset_path)

        print(f"  - {out_path.name} ({end - start:.0f}s) — {title}")
        print(f"    razon: {frag.get('reason', '')}")
        if graphic:
            print(f"    grafico: {graphic['type']} en +{graphic['offset']}s")

    print(f"\nListo. {len(fragments)} shorts generados en {OUTPUT_DIR}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convierte un video horizontal largo en shorts verticales")
    parser.add_argument("video", type=Path, help="Ruta al video horizontal de entrada")
    args = parser.parse_args()
    run(args.video)
