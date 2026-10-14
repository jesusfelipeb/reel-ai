"""Validacion de rutas que se derivan de datos de escena.

Una escena (`motion/scenes/*.json`) es **dato no confiable**: la escribe un LLM, o
llega compartida por un tercero. Eso obliga a validar cualquier campo que termine
formando parte de una ruta.

El riesgo no es obvio: `pathlib` descarta el lado izquierdo de un `/` cuando el
lado derecho es absoluto, asi que un campo hostil escapa del directorio base sin
necesidad de usar `..`:

    Path("/proyecto/.tmp") / "motion" / "/tmp/pwned"   ->  Path("/tmp/pwned")

Con `mkdir(parents=True)` y una escritura despues, eso es creacion de directorios
y escritura de archivos en cualquier ruta donde el usuario tenga permiso.
"""
import re
from pathlib import Path

# Un unico componente de ruta: sin separadores, sin "..", sin nombres ocultos.
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def safe_name(value: object, field: str = "name") -> str:
    """Devuelve `value` si sirve como un solo componente de ruta; si no, falla.

    Rechaza rutas absolutas, separadores, `..` y nombres que empiecen con punto,
    porque todos ellos permiten salir del directorio previsto.
    """
    if not isinstance(value, str):
        raise ValueError(f"El campo '{field}' de la escena debe ser texto, no {type(value).__name__}.")
    if not _SAFE_NAME.match(value):
        raise ValueError(
            f"El campo '{field}' de la escena vale {value!r}, que no es un nombre valido.\n"
            "Se permiten letras, numeros, punto, guion y guion bajo (1-64 caracteres), "
            "empezando por una letra o un numero. Sin barras ni '..'."
        )
    return value


def resolve_inside(base: Path, relative: object, field: str) -> Path:
    """Resuelve `relative` dentro de `base` y falla si se sale de ahi.

    Para campos que si pueden llevar subdirectorios (p. ej. `source`:
    "largos/1/video.mp4") pero que igual tienen que quedar dentro del proyecto.
    """
    if not isinstance(relative, str):
        raise ValueError(f"El campo '{field}' de la escena debe ser texto, no {type(relative).__name__}.")

    base = base.resolve()
    candidate = (base / relative).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError(
            f"El campo '{field}' de la escena apunta a {relative!r}, que queda fuera del proyecto.\n"
            f"Tiene que ser una ruta relativa dentro de {base}."
        )
    return candidate
