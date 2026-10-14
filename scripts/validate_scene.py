"""Valida una escena contra la especificacion de docs/BEATS.md.

Existe por dos motivos:

  1. Renderizar tarda minutos; validar tarda milisegundos. Descubrir que una linea se
     desborda despues de esperar el video completo es caro.
  2. Un agente puede correr esto y corregirse solo. Los mensajes estan escritos para que
     un LLM los lea y sepa exactamente que cambiar, sin tener que adivinar.

Uso:
    python scripts/validate_scene.py motion/scenes/mi-escena.json
    python scripts/validate_scene.py mi-escena.json --json   # salida para maquinas

Sale con codigo 0 si la escena es valida, 1 si no.
"""
import argparse
import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

EPS = 1e-6  # tolerancia de coma flotante al comparar segundos
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

# Limite de caracteres por campo, medido contra la plantilla real (ver docs/BEATS.md).
# El valor es el maximo en MAYUSCULAS, que es el caso habitual en titulares y el mas chico.
# Los campos de `list` no estan: son los unicos que parten en varias lineas.
LIMITS = {
    "hook.lines": 12,
    "tasks.title": 15,
    "tasks.tasks": 23,
    "tasks.times": 15,
    "tasks.stamp": 23,
    "steps.title": 15,
    "steps.sub": 43,
    "tags.lines": 15,
    "tags.tags": 24,
    "swap.from": 8,
    "swap.to": 8,
    "swap.kicker": 37,
    "swap.sub": 37,
    "result.from": 11,
    "result.to": 11,
    "result.sub": 37,
    "end.headline": 18,
    "end.cta": 25,
    "end.handle": 37,
    "end.wordmark": 10.5,  # unidades: minuscula 1, mayuscula 1,4, espacio 0,5: es el unico campo serif y mixto (ver _wordmark_len)
    "end.studio": 22,
    "chip": 37,
}

# Duracion minima por tipo. Las marcadas como "duras" rompen la animacion si no se cumplen;
# el resto solo hacen que algo no llegue a verse.
MIN_DURATION = {
    "hook": (3.0, False),
    "tags": (3.2, False),
    "steps": (2.61, True),   # el reparto interno es (dur - 2.6) / n: por debajo sale negativo
    "list": (1.81, True),    # idem con (dur - 1.8) / n
    "tasks": (4.4, True),    # el sello cae en el segundo 3.9, fijo
    "result": (3.3, False),
    "swap": (3.5, False),
    "end": (2.5, False),
}

# Campos obligatorios por tipo: nombre -> tipo esperado.
SCHEMA = {
    "hook":   {"chip": str, "lines": list, "accent": list},
    "tags":   {"chip": str, "lines": list, "tags": list, "accent": int},
    "steps":  {"chip": str, "steps": list},
    "list":   {"chip": str, "items": list},
    "tasks":  {"chip": str, "title": str, "tasks": list, "times": str, "stamp": str},
    "result": {"from": str, "to": str, "count_to": int, "sub": str},
    "swap":   {"kicker": str, "from": str, "to": str, "sub": str},
    "end":    {"wordmark": str, "studio": str, "headline": list, "cta": str, "handle": str},
}

# Campos que son listas de objetos, con las claves que debe traer cada objeto.
NESTED = {"steps": ("steps", ("title", "sub")), "list": ("items", ("title", "sub"))}

# Listas de texto que si hay que medir (las demas listas son de numeros o de objetos).
TEXT_LISTS = {"lines", "tasks", "tags", "headline"}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def _wordmark_len(text: str) -> float:
    """Ancho efectivo del logotipo, el unico campo serif y en mayusculas y minusculas.

    Medido con Fraunces a 170 px sobre los 900 px disponibles: 10 minusculas = 850 px y
    11 = 952; 7 mayusculas = 837 y 8 = 980; "Nutri Laura" = 949, "Sintergia" = 736.
    Una mayuscula ocupa ~1,4 minusculas y un espacio ~media.
    """
    return round(sum(1.4 if c.isupper() else 0.5 if c == " " else 1 for c in text), 1)


def _check_text(r: Report, where: str, btype: str, key: str, value: object) -> None:
    """Un campo de texto: que sea texto y que entre en pantalla."""
    if not isinstance(value, str):
        r.error(f"{where}: '{key}' debe ser texto, no {type(value).__name__}.")
        return
    limit = LIMITS.get("chip" if key == "chip" else f"{btype}.{key}")
    if limit and btype == "end" and key == "wordmark" and _wordmark_len(value) > limit:
        r.error(
            f"{where}: 'wordmark' es demasiado ancho ({_wordmark_len(value):g} de {limit} unidades; "
            "mayuscula = 1,4, espacio = 0,5). Se sale de la pantalla. Usa un nombre mas corto o "
            "minusculas (\"Laura\" en vez de \"Nutri Laura\"), y pasa el resto a 'studio'.\n"
            f'    valor: "{value}"'
        )
        return
    if limit and len(value) > limit:
        r.error(
            f"{where}: '{key}' tiene {len(value)} caracteres y el maximo es {limit}. "
            f"El texto NO se parte solo: se sale de la pantalla. Acortalo.\n"
            f'    valor: "{value}"'
        )


def validate(scene: dict) -> Report:
    r = Report()

    name = scene.get("name")
    if not isinstance(name, str) or not SAFE_NAME.match(name):
        r.error(
            f"'name' vale {name!r}. Tiene que ser de 1 a 64 caracteres (letras, numeros, "
            "'.', '-', '_'), empezando por letra o numero, sin barras ni '..'."
        )

    # Las escenas del pipeline hibrido (video + overlay) tienen otro formato: no llevan
    # `beats` sino `source`, `split_windows`, `zoom`... Este validador no las cubre.
    if "source" in scene and "beats" not in scene:
        r.warn(
            "Esto parece una escena del pipeline hibrido (tiene 'source' y no 'beats'). "
            "Este validador solo cubre las escenas de video animado de texto, que son las "
            "que describe docs/BEATS.md. No hay nada que revisar aca."
        )
        return r

    beats = scene.get("beats")
    if not isinstance(beats, list) or not beats:
        r.error("'beats' tiene que ser una lista con al menos un beat.")
        return r

    duration = scene.get("duration")
    if not isinstance(duration, (int, float)):
        r.error("'duration' tiene que ser un numero (segundos).")
        duration = None

    # --- cada beat --------------------------------------------------------
    for i, b in enumerate(beats):
        where = f"beat {i} ({b.get('type', '?')})"
        btype = b.get("type")
        if btype not in SCHEMA:
            r.error(f"{where}: tipo desconocido. Validos: {', '.join(sorted(SCHEMA))}.")
            continue

        t_in, t_out = b.get("in"), b.get("out")
        if not isinstance(t_in, (int, float)) or not isinstance(t_out, (int, float)):
            r.error(f"{where}: 'in' y 'out' tienen que ser numeros.")
            continue
        if t_out <= t_in:
            r.error(f"{where}: 'out' ({t_out}) tiene que ser mayor que 'in' ({t_in}).")
            continue

        dur = t_out - t_in
        minimum, hard = MIN_DURATION[btype]
        # EPS evita falsos positivos de coma flotante: 22.4 - 19.1 da 3.2999999999999972,
        # que compararia como menor a 3.3 aunque el usuario escribio los numeros justos.
        if dur < minimum - EPS:
            detail = (
                "la animacion se ROMPE por debajo de eso" if hard
                else "a esa velocidad el contenido no llega a verse"
            )
            r.error(f"{where}: dura {dur:.2f} s y el minimo es {minimum} s — {detail}.")

        # campos obligatorios y su tipo
        for key, expected in SCHEMA[btype].items():
            if key not in b:
                r.error(f"{where}: falta el campo obligatorio '{key}'.")
                continue
            value = b[key]
            if expected is int and isinstance(value, bool) or not isinstance(value, expected):
                article = {str: "texto", list: "una lista", int: "un numero entero"}[expected]
                r.error(
                    f"{where}: '{key}' debe ser {article}, no {type(value).__name__}."
                    + (
                        "  Ojo: 'accent' es una LISTA de indices en hook y un NUMERO en tags."
                        if key == "accent" else ""
                    )
                )
                continue

            if expected is str:
                _check_text(r, where, btype, key, value)
            elif expected is list and key in TEXT_LISTS:
                for item in value:
                    _check_text(r, where, btype, key, item)

        # listas de objetos (steps / list)
        if btype in NESTED:
            field, keys = NESTED[btype]
            for j, item in enumerate(b.get(field, [])):
                if not isinstance(item, dict):
                    r.error(f"{where}: {field}[{j}] deberia ser un objeto con {list(keys)}.")
                    continue
                for k in keys:
                    if k not in item:
                        r.error(f"{where}: {field}[{j}] no tiene '{k}'.")
                    elif btype == "steps":  # los de `list` parten en varias lineas, no se miden
                        _check_text(r, where, btype, k, item[k])

        # reglas propias de cada tipo
        # Ojo: estas reglas corren aunque un campo haya fallado la validacion de tipo mas
        # arriba, asi que cada una comprueba el tipo antes de usarlo.
        if btype == "hook":
            lines = b.get("lines") if isinstance(b.get("lines"), list) else []
            if isinstance(b.get("accent"), list):
                for idx in b["accent"]:
                    if not isinstance(idx, int) or not 0 <= idx < len(lines):
                        r.error(f"{where}: 'accent' tiene el indice {idx}, fuera de 'lines'.")
            if len(lines) > 4:
                r.warn(f"{where}: {len(lines)} lineas. Mas de 4 no entran bien en pantalla.")
        if btype == "tags":
            acc, tags = b.get("accent"), b.get("tags")
            if isinstance(acc, int) and isinstance(tags, list) and not 0 <= acc < len(tags):
                r.error(f"{where}: 'accent' es {acc}, fuera de 'tags'.")
        if btype == "result" and isinstance(b.get("count_to"), int):
            if not 1 <= b["count_to"] <= 6:
                r.error(
                    f"{where}: 'count_to' es {b['count_to']}. Tiene que estar entre 1 y 6: "
                    "dibuja un telefono por unidad y el septimo se sale de pantalla."
                )
        if btype in ("steps", "list"):
            field = NESTED[btype][0]
            n = len(b.get(field, []))
            if n and dur / n < 2.0:
                r.warn(f"{where}: {n} elementos en {dur:.1f} s ({dur/n:.1f} s cada uno). "
                       "Por debajo de 2 s se lee apurado.")

    # --- continuidad temporal --------------------------------------------
    for i in range(len(beats) - 1):
        a, b2 = beats[i], beats[i + 1]
        if not all(isinstance(x.get(k), (int, float)) for x in (a, b2) for k in ("in", "out")):
            continue
        if abs(a["out"] - b2["in"]) > 0.001:
            gap = b2["in"] - a["out"]
            kind = f"un hueco de {gap:.2f} s" if gap > 0 else f"una superposicion de {-gap:.2f} s"
            r.error(
                f"Entre el beat {i} y el {i + 1} hay {kind}. "
                f"El 'out' de uno tiene que ser igual al 'in' del siguiente "
                f"({a['out']} != {b2['in']})."
            )

    # --- juicio editorial: no son errores, pero casi siempre conviene corregirlos ----
    # Un modelo sin estas pistas tiende a dos extremos: videos de 13 s que no dicen nada,
    # o siete beats apretados en medio minuto.
    if isinstance(duration, (int, float)) and duration > 0:
        if duration < 20:
            r.warn(f"El video dura {duration:.0f} s. Por debajo de 20 s no entra una idea "
                   "completa con gancho y cierre; apunta a 25-45 s.")
        elif duration > 60:
            r.warn(f"El video dura {duration:.0f} s. Pasados los 45-60 s la retencion cae "
                   "fuerte en Reels.")
        ritmo = duration / len(beats)
        if ritmo < 4 and len(beats) > 3:
            r.warn(f"{len(beats)} beats en {duration:.0f} s ({ritmo:.1f} s cada uno). "
                   "Un beat cada menos de 4 s se siente apurado: suelen sobrar ideas. "
                   "Con 3 o 4 beats bien elegidos alcanza.")

    last = beats[-1]
    if last.get("type") != "end":
        r.warn(f"El ultimo beat es '{last.get('type')}'. Lo normal es cerrar con 'end' "
               "(llamada a la accion y usuario).")
    if duration is not None and isinstance(last.get("out"), (int, float)):
        if abs(duration - last["out"]) > 0.001:
            r.error(
                f"'duration' es {duration} pero el ultimo beat termina en {last['out']}. "
                "Tienen que coincidir, o el video se corta o se queda en negro."
            )

    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Valida una escena contra docs/BEATS.md")
    ap.add_argument("scene", type=Path)
    ap.add_argument("--json", action="store_true", help="salida legible por maquinas")
    args = ap.parse_args()

    try:
        scene = json.loads(args.scene.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"No existe el archivo: {args.scene}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as err:
        msg = f"El archivo no es JSON valido: linea {err.lineno}, columna {err.colno}: {err.msg}"
        print(json.dumps({"ok": False, "errors": [msg]}) if args.json else msg, file=sys.stderr)
        return 1

    r = validate(scene)

    if args.json:
        print(json.dumps({"ok": not r.errors, "errors": r.errors, "warnings": r.warnings},
                         ensure_ascii=False, indent=2))
        return 1 if r.errors else 0

    print(f"\nValidando {args.scene.name}")
    print("=" * 64)
    for e in r.errors:
        print(f"  [ERROR] {e}")
    for w in r.warnings:
        print(f"  [aviso] {w}")
    print("-" * 64)
    if r.errors:
        print(f"  {len(r.errors)} error(es). La escena no esta lista para renderizar.\n")
        return 1
    extra = f" ({len(r.warnings)} aviso(s))" if r.warnings else ""
    print(f"  Escena valida{extra}. Proba:")
    print(f"    python reel.py stills {args.scene}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
