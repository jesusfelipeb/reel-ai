"""reel — punto de entrada unico de reel-ai.

Pensado para que lo use un agente (Claude Code, Codex...) tanto como una persona: cada
comando termina con codigo 0 si salio bien y 1 si no, y con --json imprime un unico objeto
JSON en la salida estandar.

    python reel.py init                           prepara la carpeta para tu agente
    python reel.py doctor                         revisa el entorno
    python reel.py validate escena.json           valida sin renderizar (milisegundos)
    python reel.py stills escena.json             una captura por beat, para revisar el diseño
    python reel.py stills escena.json --at 3,12   capturas en esos segundos
    python reel.py render escena.json             valida y renderiza el video completo
    python reel.py shorts video.mp4               video horizontal largo -> 5 shorts (usa IA)

En Docker el mismo comando es el ENTRYPOINT de la imagen (ver Dockerfile).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Lo que `init` copia a la carpeta del usuario: con esto un agente sabe que hacer sin tener
# el repositorio. Las rutas son las mismas que en el repo, asi AGENTS.md sirve en los dos.
INIT_FILES = [
    "AGENTS.md",
    "docs/BEATS.md",
    "docs/BRIEF.md",
    "docs/MARCA.md",
    "docs/PROVEEDORES.md",
    "themes/neutral.json",
    "examples/primer-video.json",
]
# Claude Code lee CLAUDE.md, Codex lee AGENTS.md: el puente evita mantener dos copias.
CLAUDE_BRIDGE = "@AGENTS.md\n"

# Momento de cada beat que se captura por defecto: pasado el 65 % la animacion de entrada
# ya termino y la de salida todavia no empezo, asi que se ve el beat completo.
STILL_POINT = 0.65


class SceneError(Exception):
    """La escena no se puede usar. El mensaje esta escrito para quien tiene que corregirla."""


def _emit(as_json: bool, payload: dict, human: str) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2) if as_json else human)
    return 0 if payload.get("ok") else 1


def _load_scene(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SceneError(f"No existe el archivo: {path}") from None
    except json.JSONDecodeError as err:
        raise SceneError(
            f"{path} no es JSON valido: linea {err.lineno}, columna {err.colno}: {err.msg}"
        ) from None


def _check(scene: dict) -> tuple[list[str], list[str]]:
    from scripts.validate_scene import validate

    report = validate(scene)
    return report.errors, report.warnings


def _validation_text(errors: list[str], warnings: list[str]) -> str:
    lines = [f"  [ERROR] {e}" for e in errors] + [f"  [aviso] {w}" for w in warnings]
    return "\n".join(lines)


def _rel(path: Path) -> str:
    """Ruta relativa a la carpeta del usuario: en Docker `/work/...` no existe fuera del
    contenedor, pero `output/...` vale igual adentro y afuera."""
    from config.settings import PROJECT_DIR

    try:
        return str(path.resolve().relative_to(PROJECT_DIR))
    except ValueError:
        return str(path)


def _default_stills(scene: dict) -> str:
    """Un segundo por beat, en el punto en que el beat se ve entero."""
    times = []
    for beat in scene.get("beats", []):
        start, end = beat.get("in"), beat.get("out")
        if isinstance(start, (int, float)) and isinstance(end, (int, float)) and end > start:
            times.append(f"{start + (end - start) * STILL_POINT:.2f}")
    return ",".join(times)


def cmd_init(args: argparse.Namespace) -> int:
    """Copia instrucciones, especificacion y un ejemplo. Nunca pisa un archivo existente."""
    import shutil

    from config.settings import PROJECT_DIR

    created, kept = [], []

    def place(rel: str, write) -> None:
        target = PROJECT_DIR / rel
        if target.exists():
            kept.append(rel)
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        write(target)
        created.append(rel)

    for rel in INIT_FILES:
        place(rel, lambda t, rel=rel: shutil.copyfile(BASE_DIR / rel, t))
    place("CLAUDE.md", lambda t: t.write_text(CLAUDE_BRIDGE, encoding="utf-8"))
    (PROJECT_DIR / "escenas").mkdir(exist_ok=True)

    payload = {"ok": True, "created": created, "kept": kept}
    human = "\n".join(
        [f"  + {r}" for r in created] + [f"  = {r} (ya existia, no se toco)" for r in kept]
        + ["Carpeta lista. Abri tu agente aca y pedile un video."]
    )
    return _emit(args.json, payload, human)


def cmd_doctor(_: argparse.Namespace) -> int:
    from scripts.doctor import main

    return main()


def cmd_validate(args: argparse.Namespace) -> int:
    errors, warnings = _check(_load_scene(args.scene))
    payload = {"ok": not errors, "errors": errors, "warnings": warnings}
    verdict = f"{len(errors)} error(es): corregilos antes de renderizar." if errors else "Escena valida."
    human = "\n".join(filter(None, [_validation_text(errors, warnings), verdict]))
    return _emit(args.json, payload, human)


def cmd_stills(args: argparse.Namespace) -> int:
    from motion.compose_text import compose

    scene = _load_scene(args.scene)
    errors, warnings = _check(scene)
    if errors:
        # Con errores igual se capturan: ver el desborde ayuda a entender el error.
        print(_validation_text(errors, []), file=sys.stderr)
    at = args.at or _default_stills(scene)
    if not at:
        raise SceneError("La escena no tiene beats con 'in' y 'out': no se que capturar. Usá --at 2,5,8")

    folder = compose(args.scene, reuse_frames=False, stills=at)
    shots = sorted(folder.glob("still-*.png"), key=lambda p: float(p.stem.removeprefix("still-")))
    files = [_rel(p) for p in shots]
    payload = {"ok": True, "stills": files, "errors": errors, "warnings": warnings}
    return _emit(args.json, payload, "Capturas:\n" + "\n".join(f"  {f}" for f in files))


def cmd_render(args: argparse.Namespace) -> int:
    from motion.compose_text import compose

    scene = _load_scene(args.scene)
    errors, warnings = _check(scene)
    if errors and not args.force:
        payload = {"ok": False, "errors": errors, "warnings": warnings}
        human = (_validation_text(errors, warnings)
                 + f"\n{len(errors)} error(es): no se renderiza. Corregilos (o usá --force).")
        return _emit(args.json, payload, human)

    video = compose(args.scene, reuse_frames=args.reuse_frames, stills=None)
    payload = {"ok": True, "video": _rel(video), "warnings": warnings}
    return _emit(args.json, payload, f"Listo: {_rel(video)}")


def cmd_shorts(args: argparse.Namespace) -> int:
    from main import run

    run(args.video)
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="reel", description="Videos verticales animados a partir de una escena JSON.")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="prepara la carpeta para usarla con un agente (no pisa nada)")
    p.add_argument("--json", action="store_true", help="salida para maquinas")
    p.set_defaults(fn=cmd_init)

    sub.add_parser("doctor", help="revisa que el entorno tenga todo").set_defaults(fn=cmd_doctor)

    p = sub.add_parser("validate", help="valida una escena sin renderizar")
    p.add_argument("scene", type=Path)
    p.add_argument("--json", action="store_true", help="salida para maquinas")
    p.set_defaults(fn=cmd_validate)

    p = sub.add_parser("stills", help="capturas sueltas para revisar el diseño (segundos)")
    p.add_argument("scene", type=Path)
    p.add_argument("--at", help="segundos a capturar, ej. 3,12,22 (por defecto, uno por beat)")
    p.add_argument("--json", action="store_true", help="salida para maquinas")
    p.set_defaults(fn=cmd_stills)

    p = sub.add_parser("render", help="valida y renderiza el video completo (~1-2 min)")
    p.add_argument("scene", type=Path)
    p.add_argument("--reuse-frames", action="store_true", help="no re-renderizar la animacion")
    p.add_argument("--force", action="store_true", help="renderizar aunque la escena tenga errores")
    p.add_argument("--json", action="store_true", help="salida para maquinas")
    p.set_defaults(fn=cmd_render)

    p = sub.add_parser("shorts", help="video horizontal largo -> 5 shorts (necesita LLM_API_KEY)")
    p.add_argument("video", type=Path)
    p.set_defaults(fn=cmd_shorts)
    return ap


def main() -> int:
    args = build_parser().parse_args()
    as_json = getattr(args, "json", False)
    try:
        return args.fn(args)
    except (SceneError, ValueError) as err:
        return _emit(as_json, {"ok": False, "errors": [str(err)]}, f"Error: {err}")
    except subprocess.CalledProcessError as err:
        stderr = err.stderr.decode(errors="replace") if isinstance(err.stderr, bytes) else (err.stderr or "")
        return _emit(as_json, {"ok": False, "errors": [f"Fallo {err.cmd[0]}", stderr[-3000:]]},
                     f"Fallo {err.cmd[0]}:\n{stderr[-3000:]}")


if __name__ == "__main__":
    sys.exit(main())
