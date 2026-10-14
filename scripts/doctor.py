"""Verifica que el entorno tenga todo lo necesario, y dice como arreglar lo que falte.

El objetivo es que alguien que acaba de clonar el repo sepa en 5 segundos que le falta,
en vez de descubrirlo con un stack trace a mitad de un render.

Uso:  python scripts/doctor.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

OK, WARN, FAIL = "ok  ", "aviso", "FALTA"
FONTS = ["InterTight-Black.woff", "JetBrainsMono-Bold.woff", "Fraunces-Medium.woff"]

results: list[tuple[str, str, str]] = []


def check(level: str, what: str, detail: str = "") -> None:
    results.append((level, what, detail))


def _version(cmd: list[str]) -> str | None:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return (out.stdout or out.stderr).splitlines()[0] if out.returncode == 0 else None


# Varias comprobaciones importan `config.settings`, que necesita python-dotenv. Sin las
# dependencias instaladas fallarian todas con "No module named 'dotenv'", escondiendo la
# causa real detras de errores que no son. Si faltan, se saltean y se dice por que.
deps_ok = True


def check_python() -> None:
    global deps_ok
    v = sys.version_info
    if v >= (3, 10):
        check(OK, f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        check(FAIL, f"Python {v.major}.{v.minor}", "Hace falta 3.10 o mas (el codigo usa `str | None`).")

    missing = [m for m in ("openai", "dotenv", "PIL") if not _importable(m)]
    if missing:
        deps_ok = False
        names = {"dotenv": "python-dotenv", "PIL": "Pillow"}
        pretty = ", ".join(names.get(m, m) for m in missing)
        check(FAIL, f"Paquetes de Python: faltan {pretty}", "pip install -r requirements.txt")
    else:
        check(OK, "Paquetes de Python (openai, python-dotenv, Pillow)")


def _importable(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def check_ffmpeg() -> None:
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool):
            check(OK, f"{tool}: {_version([tool, '-version']) or 'presente'}")
        else:
            check(FAIL, f"{tool} no esta en el PATH",
                  "Debian/Ubuntu: sudo apt install ffmpeg  ·  macOS: brew install ffmpeg")


def check_node() -> None:
    if not shutil.which("node"):
        check(FAIL, "node no esta en el PATH", "Instala Node 20 o mas: https://nodejs.org")
        return
    check(OK, f"node {_version(['node', '-v'])}")

    if not deps_ok:
        check(WARN, "Playwright: sin comprobar", "Instalá primero las dependencias de Python.")
        return

    try:
        from motion.node import node_env
        env = node_env()
    except Exception as err:
        check(FAIL, "Playwright no esta instalado", str(err).replace("\n", "\n        "))
        return
    check(OK, f"Playwright en {env['NODE_PATH']}")

    probe = "const {chromium}=require('playwright');chromium.executablePath()"
    try:
        run = subprocess.run(["node", "-e", probe], env=env, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as err:
        check(WARN, "No pude comprobar Chromium", str(err))
        return
    if run.returncode == 0:
        check(OK, "Chromium descargado")
    else:
        check(FAIL, "Falta el navegador de Playwright", "npx playwright install chromium")


def check_fonts() -> None:
    missing = [f for f in FONTS if not (BASE_DIR / "fonts" / f).is_file()]
    if missing:
        check(FAIL, f"Faltan tipografias: {', '.join(missing)}", "Deberian venir en el repo (ver NOTICE).")
    else:
        check(OK, f"Tipografias ({len(FONTS)} archivos en fonts/)")


def check_provider() -> None:
    """La clave es opcional: el pipeline de solo texto no la usa."""
    if not deps_ok:
        check(WARN, "Proveedor de IA: sin comprobar", "Instalá primero las dependencias de Python.")
        return
    try:
        from config.settings import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
    except Exception as err:
        check(FAIL, "No pude leer la configuracion", str(err))
        return

    if LLM_API_KEY:
        check(OK, f"Proveedor de IA: {LLM_MODEL} en {LLM_BASE_URL}")
    else:
        check(WARN, "Sin clave de API (LLM_API_KEY)",
              "Solo hace falta para el pipeline de video largo. El de texto anda igual.\n"
              "        Para configurarla: cp .env.example .env")


def main() -> int:
    print("\nreel-ai · revision del entorno")
    print("=" * 64)
    for fn in (check_python, check_ffmpeg, check_node, check_fonts, check_provider):
        fn()

    for level, what, detail in results:
        print(f"  [{level}] {what}")
        if detail:
            print(f"        {detail}")

    failed = sum(1 for level, _, _ in results if level == FAIL)
    warned = sum(1 for level, _, _ in results if level == WARN)
    print("-" * 64)
    if failed:
        print(f"  {failed} cosa(s) por resolver antes de renderizar.\n")
        return 1
    # Se prefieren los ejemplos que vienen con el repo; si no, lo que haya escrito el usuario.
    preferred = BASE_DIR / "examples/diagnostico-gratis-reel-test.json"
    scenes = [preferred] if preferred.is_file() else sorted((BASE_DIR / "examples").glob("*.json"))
    from config.settings import PROJECT_DIR

    # Fuera de Docker los ejemplos estan en el proyecto; en Docker, en /app (ruta absoluta).
    if not scenes:
        example = "<escena>.json"
    elif PROJECT_DIR == BASE_DIR:
        example = scenes[0].relative_to(BASE_DIR)
    else:
        example = scenes[0]
    print(f"  Todo listo{f' ({warned} aviso)' if warned else ''}. Proba:")
    print(f"    python reel.py stills {example}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
