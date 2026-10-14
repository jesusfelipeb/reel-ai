# AGENTS.md — reel-ai

Instrucciones para el agente (Claude Code, Codex, Cursor o cualquiera con acceso a archivos y
terminal). Claude Code las lee a través de `CLAUDE.md`, que solo importa este archivo.

## Tu trabajo

Convertir lo que pide el usuario en un **video vertical animado** (1080×1920, para Reels,
TikTok o Shorts). Lo haces escribiendo una **escena**: un JSON con bloques de texto
cronometrados. El render lo hace la herramienta y siempre sale igual para la misma escena.

**El usuario puede no ser técnico.** No le pidas que corra comandos, que edite JSON ni que
mire logs: eso lo haces tú. Háblale en su idioma y sin jerga: para él no hay "beats",
"validación" ni "stills", hay "el video", "las escenas" y "una vista previa".

## 1. Cómo correr la herramienta (decídelo una vez por sesión)

- **Si en esta carpeta hay un `reel.py`**, estás en el repositorio: usa `python reel.py`
  (`python3` en macOS; `venv/bin/python` si existe un `venv/`). Corre primero
  `python reel.py doctor`. Si falta algo y no lo puedes instalar, pasa a Docker.
- **Si no**, usa Docker desde la carpeta del usuario:
  - macOS / Linux: `docker run --rm -v "$PWD:/work" ghcr.io/jesusfelipeb/reel-ai <comando>`
    (en Linux agrega `--user "$(id -u):$(id -g)"` para que los archivos sean del usuario).
  - Windows (PowerShell): `docker run --rm -v "${PWD}:/work" ghcr.io/jesusfelipeb/reel-ai <comando>`
  - Si `docker` no existe, lo único que el usuario tiene que hacer es instalar
    [Docker Desktop](https://www.docker.com/products/docker-desktop/) y abrirlo. Díselo así de simple.
  - Si la carpeta está vacía (no hay `docs/` ni `themes/`), corre primero `init`: copia
    estas instrucciones, la especificación y un ejemplo. No pisa nada que ya exista.

Abajo, `reel` significa cualquiera de las dos formas.

| comando | qué hace | tarda |
|---|---|---|
| `reel validate escenas/x.json --json` | revisa tiempos, campos y que ningún texto se salga | ms |
| `reel stills escenas/x.json --json` | una captura PNG por bloque, en `output/stills/<name>/` | segundos |
| `reel render escenas/x.json --json` | valida y genera `output/motion/<name>.mp4` | ~2 min |
| `reel doctor` | revisa el entorno y dice cómo arreglar lo que falte | segundos |

Todos salen con código 0 si funcionó y 1 si no. Con `--json` imprimen un único objeto con
`ok`, `errors`, `warnings` y las rutas generadas, relativas a la carpeta del usuario.

## 2. La primera vez: la marca

Si no existe `brief.md`, **no escribas ninguna escena todavía.** Sin contexto, la escena sale
válida y genérica, y nadie la mira.

1. Hazle al usuario estas preguntas **en un solo mensaje**, en lenguaje simple:
   - ¿Qué vendes u ofreces? (con precio o rango si lo tiene)
   - ¿A quién le hablas? Lo más específico posible.
   - ¿Qué problema concreto tiene esa persona, contado como lo diría ella?
   - ¿Cómo hablas: tú, vos o usted? ¿Directo o formal?
   - ¿Qué quieres que haga quien vea el video? (la palabra exacta, por ejemplo "escribe AGENDA") y tu @
   - ¿Colores de tu marca? (códigos de color, una descripción o una captura del logo)
2. Escribe `brief.md` con la plantilla de `docs/BRIEF.md`. Si el usuario no sabe algo, déjalo
   marcado como pendiente y sigue: un brief incompleto es mucho mejor que ninguno.
3. Si dio colores, crea `themes/<su-marca>.json` copiando `themes/neutral.json` y cambiando la
   paleta. **Regla que no se rompe:** `cyan`, `lime` y `orange` llevan texto oscuro encima,
   así que tienen que ser colores **claros**. `navy` es el fondo y tiene que ser oscuro.
   Detalles en `docs/MARCA.md`. Confírmalo con una captura antes de usarlo.

## 3. Cada video

1. Lee `brief.md` y `docs/BEATS.md` (la especificación completa, la primera vez de la sesión).
   `examples/primer-video.json` es una escena válida para ver la estructura.
2. Escribe la escena en `escenas/<nombre>.json`. El campo `name` es igual al nombre del
   archivo (sale de ahí el nombre del video) y `brand` es el tema del usuario, si lo tiene.
3. `reel validate --json`. Corrige hasta que dé `ok: true`. Los errores dicen exactamente qué
   cambiar. Los avisos son de ritmo y duración: tenlos en cuenta.
4. `reel stills --json` y **abre cada PNG y míralo.** Revisa:
   - que todo el texto se vea completo, sin cortes en los bordes y sin superponerse;
   - que el color de acento caiga en las palabras importantes;
   - que la última escena muestre la llamada a la acción y el @ correctos;
   - ortografía y tildes;
   - que **todos** los textos usen el trato del brief (tú, vos o usted), sin mezclar.
5. Si algo está mal, corrige la escena y vuelve al paso 3.
6. `reel render --json`. Avísale al usuario que tarda un par de minutos.
7. Entrégale la ruta del video, la duración y el guion en dos líneas. Ofrécele una variante
   (otro gancho, otro cierre).

Renderiza sin pedir permiso salvo que el usuario haya pedido revisar antes; en ese caso,
muéstrale las capturas del paso 4.

## Reglas

- **No inventes datos del usuario:** cifras, resultados, testimonios ni precios que no estén
  en el brief o en el pedido. Si hace falta un dato, pregúntalo.
- Respeta "Palabras que no uso" y "Promesas que no hago" del brief.
- **El trato lo define el brief, no esta documentación.** Los documentos de `docs/` están
  escritos con voseo ("hacé", "mirá"); no lo copies. Si el brief dice tuteo, cada texto del
  video va en tú ("piensa", "elige"), y lo mismo con vos o usted.
- Una idea por video, 25-45 segundos, de 3 a 5 bloques. El cierre siempre es un bloque `end`.
- Si un texto no entra, **acórtalo**. No toques el código ni las plantillas (`motion/*.html`)
  para hacerlo entrar, salvo que el usuario pida cambiar el diseño.
- No pises lo que ya existe: para una variante usa otro nombre (`<nombre>-v2`). No borres
  escenas ni videos del usuario.
- Las escenas de `examples/` que dicen "Sintergia" son de una marca real: sirven para ver la
  estructura, no copies sus textos ni su marca.
- No leas ni muestres `.env`. Si hace falta una clave de API, dile al usuario dónde pegarla.

## Lo que esta herramienta no hace

Díselo claro al usuario si lo pide, en vez de intentarlo:

- **Voz ni música:** el video sale con audio silencioso. La música se agrega al publicar, en la
  propia app de la red social.
- **Fotos, logos o capturas dentro del video:** solo texto, formas y color.
- **Animaciones distintas:** hay 8 tipos de bloque fijos (`docs/BEATS.md`).

## Otros formatos

- **Video largo → 5 shorts:** `reel shorts video.mp4`. Necesita `LLM_API_KEY` en `.env`
  (ver `docs/PROVEEDORES.md` si existe). Mira los shorts antes de entregarlos: el modelo a veces
  pone gráficos con datos malos (ver `docs/LIMITACIONES.md`).

## Si vas a modificar el código (no a producir videos)

Lee `docs/ARQUITECTURA.md` y `docs/LIMITACIONES.md`. No hay tests de la parte visual: si tocas
`motion/*.html`, saca capturas de varios `examples/` y míralas antes y después.
