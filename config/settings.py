import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Carpeta de trabajo del usuario: de ahi se leen `.env`, `themes/` y los videos de entrada,
# y ahi se escribe `output/`. Por defecto es el propio repo; en Docker es el volumen
# montado (`/work`), porque el codigo vive aparte, en `/app`.
PROJECT_DIR = Path(os.getenv("REEL_PROJECT_DIR") or BASE_DIR).resolve()
load_dotenv(PROJECT_DIR / ".env")
load_dotenv(BASE_DIR / ".env")  # no pisa lo ya cargado: el .env del usuario manda


def _first(*names: str, default: str = "") -> str:
    """Primera variable de entorno con valor. Permite nombres nuevos sin romper los viejos."""
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


# --- Proveedor del LLM (seleccion de fragmentos) ----------------------------
# Sirve cualquier API compatible con OpenAI: solo cambian URL, clave y modelo.
#   Groq        https://api.groq.com/openai/v1        openai/gpt-oss-120b
#   OpenAI      https://api.openai.com/v1             gpt-4.1-mini
#   OpenRouter  https://openrouter.ai/api/v1          anthropic/claude-sonnet-4.5
#   Ollama      http://localhost:11434/v1             llama3.1  (clave: cualquier cosa)
LLM_BASE_URL = _first("LLM_BASE_URL", default="https://api.groq.com/openai/v1")
LLM_API_KEY = _first("LLM_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY")
LLM_MODEL = _first("LLM_MODEL", "GROQ_LLM_MODEL", default="openai/gpt-oss-120b")

# Los modelos de razonamiento (gpt-oss, o-series) devuelven JSON cortado si no se baja el
# esfuerzo, porque el presupuesto de tokens se va en razonar. Vacio = no se manda el
# parametro; los proveedores que no lo soportan lo rechazan con 400.
LLM_REASONING_EFFORT = os.getenv("LLM_REASONING_EFFORT", "low")

# --- Proveedor de transcripcion (Whisper) -----------------------------------
# Por defecto el mismo proveedor que el LLM. Groq y OpenAI exponen /audio/transcriptions
# con la misma forma, asi que el cliente es el mismo.
STT_BASE_URL = _first("STT_BASE_URL", default=LLM_BASE_URL)
STT_API_KEY = _first("STT_API_KEY", default=LLM_API_KEY)
STT_MODEL = _first("STT_MODEL", "GROQ_WHISPER_MODEL", default="whisper-large-v3")

INPUT_DIR = PROJECT_DIR / "input"
OUTPUT_DIR = PROJECT_DIR / "output"
# Los ~900 cuadros PNG de un render. En Docker van a /tmp del contenedor para no llenar
# la carpeta del usuario de archivos intermedios.
TMP_DIR = Path(os.getenv("REEL_TMP_DIR") or PROJECT_DIR / ".tmp")

FRAGMENT_COUNT = 5
FRAGMENT_MIN_SECONDS = 30
FRAGMENT_MAX_SECONDS = 60

# Formato de salida vertical (Reels/Shorts)
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
