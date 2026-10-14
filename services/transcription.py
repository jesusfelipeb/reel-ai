import json
import subprocess
from pathlib import Path

from services.llm import transcribe_audio


def extract_audio(video_path: Path, audio_path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k",
            str(audio_path),
        ],
        check=True,
        capture_output=True,
    )


def transcribe(audio_path: Path) -> dict:
    """Transcribe con timestamps por palabra y por segmento."""
    return transcribe_audio(audio_path.name, audio_path.read_bytes())


def _video_fingerprint(video_path: Path) -> str:
    stat = video_path.stat()
    return f"{stat.st_size}-{int(stat.st_mtime)}"


def load_cached_transcription(video_path: Path, cache_path: Path) -> dict | None:
    """Devuelve la transcripcion guardada si corresponde al mismo archivo de video."""
    if not cache_path.exists():
        return None
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if data.get("fingerprint") != _video_fingerprint(video_path):
        return None
    return data["transcription"]


def save_transcription(video_path: Path, cache_path: Path, transcription: dict) -> None:
    payload = {"fingerprint": _video_fingerprint(video_path), "transcription": transcription}
    cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
