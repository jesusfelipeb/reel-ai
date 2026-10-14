"""Resolucion del Playwright que usan los renderizadores de cuadros.

Los renderizadores (`render_text.cjs`, `render_overlay.cjs`) corren bajo `node` y necesitan
`playwright`. Para que el proyecto sea clonable, la instalacion vive en el propio repo
(`npm install`) y no se toma prestada de otro proyecto del disco.
"""
import os
from pathlib import Path

from config.settings import BASE_DIR

INSTALL_HINT = (
    f"  1. Instalalo en el proyecto:   cd {BASE_DIR} && npm install\n"
    "  2. O reusa otra instalacion:   export PLAYWRIGHT_NODE_PATH=/ruta/a/node_modules"
)


def node_env() -> dict[str, str]:
    """Entorno para lanzar `node` con `NODE_PATH` apuntando a un Playwright valido.

    Orden de busqueda: `node_modules/` del proyecto (lo normal) y, si no esta,
    `PLAYWRIGHT_NODE_PATH` como escotilla para reusar la instalacion de otro proyecto.
    """
    env = dict(os.environ)
    candidates = [BASE_DIR / "node_modules"]

    override = env.get("PLAYWRIGHT_NODE_PATH")
    if override:
        candidates.append(Path(override))

    for path in candidates:
        if (path / "playwright").is_dir():
            env["NODE_PATH"] = str(path)
            return env

    raise RuntimeError("No encuentro Playwright. Opciones:\n" + INSTALL_HINT)
