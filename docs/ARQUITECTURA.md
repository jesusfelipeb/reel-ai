# Arquitectura — cómo funciona reel-ai

Este documento explica **cómo está construido y por qué**. Si lo que querés es escribir una
escena, andá directo a [BEATS.md](BEATS.md). Si querés que tu agente las escriba por vos,
[PROMPT.md](PROMPT.md).

---

## La idea en una página

Casi todas las herramientas de "video con IA" le piden al modelo que produzca el video.
Acá no. **El modelo produce un archivo JSON y el video lo hace código determinista.**

```
   guion / transcripción
            │
            ▼
   ┌─────────────────┐
   │   un LLM        │   ← la parte creativa: qué decir y cuándo
   │  (cualquiera)   │
   └────────┬────────┘
            │   escena.json  ← el contrato
            ▼
   ┌─────────────────┐
   │  renderizador   │   ← la parte determinista: cómo se ve
   │ HTML + Chromium │      no sabe que existe un LLM
   └────────┬────────┘
            │   1080×1920 PNG × N
            ▼
   ┌─────────────────┐
   │     FFmpeg      │
   └────────┬────────┘
            ▼
        video .mp4
```

La consecuencia importante: **lo portable de este proyecto no es el Python, es el contrato
JSON**. El renderizador es una dependencia que instalás una vez. El JSON lo puede escribir
Claude, GPT, Gemini, un modelo local con Ollama, o vos a mano en un editor de texto. Por eso
el repositorio sirve con cualquier agente y con cualquier modelo: nadie tiene que integrarse
con nada, solo tiene que emitir un archivo que cumpla [la especificación](BEATS.md).

Y el reverso: **el LLM nunca piensa en animación**. No decide curvas de easing ni duraciones
de transición. Dice "este beat va de 5,2 s a 8,8 s y dice esto"; los tiempos internos los
calcula la plantilla. Un modelo chico puede escribir una escena válida.

---

## Por qué el render es determinista (y por qué importa)

La animación vive en [`motion/text_overlay.html`](../motion/text_overlay.html), pero **no usa
animaciones de CSS ni `requestAnimationFrame`**. Expone una función:

```js
window.renderAt(t)   // coloca TODO el documento en el estado exacto del segundo t
```

Todo lo que se mueve es una función pura del tiempo. Para dibujar el cuadro 450 de un video
a 30 fps, el renderizador llama `renderAt(15.0)` y saca una captura. Nada depende de qué
cuadro se dibujó antes.

Eso compra cuatro cosas que con animaciones de CSS no tenés:

1. **Reproducibilidad.** El mismo JSON da el mismo video, bit a bit. Podés versionar escenas
   en git y comparar resultados.
2. **Paralelismo.** Seis pestañas de Chromium renderizan cuadros alternados a la vez, porque
   ninguna necesita el estado de la otra. Un video de 30 s sale en ~70 s.
3. **Independencia del reloj.** Una máquina lenta no produce un video distinto, solo tarda más.
   Con animaciones de CSS, capturar cuadro a cuadro te deja a merced de cuándo el navegador
   decidió avanzar la animación.
4. **Revisión barata.** `--stills 3,12,22` renderiza tres cuadros sueltos en segundos. Podés
   iterar el diseño sin esperar un video entero.

Si vas a agregar un tipo de beat, esta es **la regla que no se puede romper**: tu `render(b, lt)`
tiene que poder llamarse con cualquier `lt` en cualquier orden y dar siempre el mismo resultado.
Nada de contadores que se incrementan, nada de `setTimeout`, nada de leer el estado anterior.

---

## Los tres pipelines

El repositorio tiene tres caminos distintos. Comparten la marca y el renderizador, pero
resuelven problemas diferentes y **no están igual de probados**.

| | Entrada | ¿Necesita IA? | Estado real |
|---|---|---|---|
| **1. Texto animado**<br>`motion/compose_text.py` | una escena JSON | No | 🟢 Estable. Es el que produjo todos los videos publicados. Empezá por acá. |
| **2. Híbrido**<br>`motion/compose.py` | video + transcripción + escena | No (la escena se escribe a mano) | 🟡 Funciona, probado con **una** escena. |
| **3. Video largo → 5 shorts**<br>`main.py` | un video horizontal | Sí (Whisper + LLM) | 🟡 Funciona, probado con **un** video de 11 min en 16:9. |

Las limitaciones concretas de cada uno están en [LIMITACIONES.md](LIMITACIONES.md). No las
escondemos: si le vas a tirar un video de 40 minutos al pipeline 3, conviene que sepas de
antemano qué no se probó nunca.

---

## Pipeline 1: texto animado (empezá por acá)

```bash
python -m motion.compose_text motion/scenes/mi-escena.json
```

No necesita video de origen, ni voz, ni clave de API. Es 100 % determinista y es el camino
que recomendamos para el primer video.

**Qué pasa adentro**, en orden:

1. **[`motion/compose_text.py`](../motion/compose_text.py)** lee la escena, valida el campo
   `name` (es dato no confiable: forma rutas de disco) y carga el tema de marca.
2. Escribe `.tmp/motion/<nombre>/timeline.json` = `{scene, theme}`.
3. **[`motion/render_text.cjs`](../motion/render_text.cjs)** levanta Chromium con Playwright,
   abre `text_overlay.html` en un viewport de 1080×1920, llama `setScene(timeline)` una vez y
   después `renderAt(t)` + captura, para cada cuadro. Reparte los cuadros entre 6 páginas en
   paralelo.
4. **FFmpeg** encadena los PNG a 30 fps con `libx264 -crf 18`, le pega una pista de audio
   silenciosa y escribe `output/motion/<nombre>.mp4`.

El paso 4 tiene un detalle que cuesta descubrir solo: **el video lleva audio silencioso a
propósito**. Varias redes rechazan o procesan mal un archivo sin pista de audio. `anullsrc`
genera el silencio.

### Atajos útiles

```bash
# solo tres cuadros sueltos, para revisar el diseño sin renderizar todo
python -m motion.compose_text motion/scenes/mi-escena.json --stills 3,12,22

# recomponer con ffmpeg sin volver a renderizar los cuadros
python -m motion.compose_text motion/scenes/mi-escena.json --reuse-frames
```

---

## Pipeline 3: de un video largo a 5 shorts

```bash
python main.py largos/01/charla.mp4
```

Este sí usa IA, y es el único que necesita una clave de API.

1. **Audio** — `services/transcription.py::extract_audio` saca WAV mono a 16 kHz con FFmpeg.
2. **Transcripción** — Whisper con timestamps por palabra y por segmento. Se cachea en
   `.tmp/<video>.transcription.json`, con huella de tamaño + fecha de modificación, así que
   la segunda corrida no vuelve a pagarla.
3. **Selección** — `services/fragment_selector.py` le pasa la transcripción a un LLM en modo
   JSON y le pide los 5 mejores fragmentos de 30-60 s. **Valida la duración y reintenta hasta
   3 veces** devolviéndole el error al modelo. Si después de eso algún fragmento sigue mal, lo
   descarta: mejor 4 shorts coherentes que uno de 15 s.
4. **Subtítulos** — `utils/subtitles.py` genera un `.ass` por fragmento, agrupado por frases,
   con la palabra que se está diciendo resaltada.
5. **Gráficos** — el LLM elige por fragmento entre `stamp`, `split` y `counter`; Pillow genera
   el PNG (o, para `counter`, se dibuja con `drawtext` en vivo).
6. **Render** — FFmpeg: fondo difuminado + cuadro completo centrado, subtítulos quemados,
   gráfico superpuesto, barra de progreso y audio normalizado a −14 LUFS.

A diferencia del pipeline 1, acá **los resultados cambian entre corridas**: el LLM se llama de
nuevo cada vez y elige fragmentos distintos. Es esperado, no un error.

---

## El proveedor de IA es intercambiable

Todo lo que el proyecto le pide a una IA son dos cosas —un chat con salida JSON y una
transcripción— y las dos existen con la misma forma en cualquier API compatible con OpenAI.
Por eso [`services/llm.py`](../services/llm.py) usa el SDK de OpenAI como **cliente genérico**,
con `base_url` configurable:

```bash
LLM_BASE_URL=https://api.groq.com/openai/v1     LLM_MODEL=openai/gpt-oss-120b
LLM_BASE_URL=https://api.openai.com/v1          LLM_MODEL=gpt-4.1-mini
LLM_BASE_URL=https://openrouter.ai/api/v1       LLM_MODEL=anthropic/claude-sonnet-4.5
LLM_BASE_URL=http://localhost:11434/v1          LLM_MODEL=llama3.1
```

Usar el SDK de OpenAI **no implica usar modelos de OpenAI**. Es el protocolo que más
proveedores implementan, nada más.

La única incompatibilidad real entre proveedores es `reasoning_effort`: lo necesitan los
modelos de razonamiento (sin él devuelven el JSON cortado, porque el presupuesto de tokens se
va en razonar) y lo rechazan los demás con un 400. La capa lo manda si está configurado y, si
el proveedor lo rechaza, **reintenta sin él y no lo vuelve a mandar en esa corrida**.

---

## La marca vive en un solo archivo

La paleta y las tipografías están en `themes/<nombre>.json`. Ese archivo lo leen los dos
mundos:

- **Python** (`config/brand.py`) lo convierte a RGB para FFmpeg, libass y Pillow.
- **El HTML** lo recibe dentro del timeline y lo aplica como variables CSS.

```
themes/sintergia.json
        │
        ├──► config/brand.py ──► ffmpeg / libass / Pillow
        └──► timeline.json ──► text_overlay.html (variables CSS)
```

Las plantillas tienen la paleta del tema `neutral` escrita en su `:root`, pero **solo como
respaldo**: sirve para abrir el HTML suelto en un navegador mientras diseñás. En el render
siempre la pisa el tema.

Dentro del CSS hay dos capas y conviene no confundirlas:

- **Paleta** (`--navy`, `--cyan`, `--lime`…): los colores crudos. Vienen del tema.
- **Roles** (`--bg`, `--ink`, `--lime-ink`…): para qué se usa cada color. Viven en el CSS
  porque son decisiones de diseño, no de marca. El tema claro redefine los roles, no la paleta.

Cómo cambiarlo por tu marca: [MARCA.md](MARCA.md).

---

## Decisiones no obvias

Esto es lo que costó descubrir. Si vas a modificar el proyecto, leelo: casi todo acá es una
cicatriz de algo que se rompió.

**`WrapStyle: 0` en los subtítulos ASS es obligatorio.** Con `WrapStyle: 2` el texto largo se
desborda de la pantalla en vez de partirse en dos líneas.

**Las zonas seguras son reales.** La interfaz de Reels/TikTok tapa los 440 px de abajo y los
220 de arriba. Los subtítulos van con `Alignment 2` + `MarginV 540`. Con `Alignment 5` libass
ignora `MarginV` por completo.

**El color inline en ASS se escribe `\c&HBBGGRR&`** —sin alpha y con `&` al final—. El formato
del bloque `Style` (`&HAABBGGRR`) no funciona dentro de llaves.

**`loudnorm` en dos pasadas.** En una sola pasada, un fragmento con intro musical quedó en
−17,3 LUFS en vez de −14. Midiendo primero y aplicando con `linear=true`, todos caen en −14,0.

**Fondo difuminado en vez de recorte centrado.** La primera versión recortaba al centro.
Quedaba bien con una persona hablando a cámara, pero cortaba la mitad de cualquier pantalla
compartida. Ahora el cuadro completo entra entero sobre un fondo borroso de sí mismo: encuadre
menos cinematográfico, cero pérdida de información.

**`-loop 1 -t <duración>` en las imágenes de FFmpeg, los dos juntos.** Sin `-loop 1`, FFmpeg
decodifica un solo cuadro en t=0 y lo congela: cualquier expresión temporal se evalúa una vez
en t≈0. Un `stamp` "funcionaba" de casualidad (en t=0 ya estaba casi en su tamaño final), pero
un `split` con fade-in a los 3 s se evaluaba en t=0 → alpha 0 congelado, invisible todo el
video. Y sin el `-t` que acota el loop, FFmpeg se cuelga para siempre esperando un EOF que
nunca llega.

**`tpad` después de `zoompan`+`concat` no extiende el video** (salían 40,1 s de 43,1). En el
pipeline híbrido, el último tramo lee 3 s extra de la fuente durante la tarjeta de cierre.

**El corte de cámara coincide con el aterrizaje del panel (0,45 s)** para que no se note.

**El texto de la escena se escapa antes de entrar al DOM.** Las plantillas construyen HTML con
una *tagged template* `` html`...` `` que escapa todo lo interpolado. Lo que de verdad es
marcado hay que declararlo con `raw()`. No es decorativo: antes de eso, una escena con
`chip: "<img src=x onerror=...>"` ejecutaba JavaScript en el renderizador — y el caso de uso
normal del proyecto es que una escena la escriba un LLM o te la pase otra persona.

**Los campos de la escena que forman rutas se validan.** `pathlib` descarta el lado izquierdo
de un `/` si el derecho es absoluto, así que `TMP_DIR / scene["name"]` con
`name: "/tmp/algo"` escribe en `/tmp/algo`. `utils/paths.py` lo bloquea.

---

## Dónde tocar qué

| Querés… | Archivo |
|---|---|
| Escribir una escena | `motion/scenes/*.json` — ver [BEATS.md](BEATS.md) |
| Que tu agente escriba con tu voz | `brief.md` — ver [BRIEF.md](BRIEF.md) |
| Cambiar colores o tipografías | `themes/*.json` — ver [MARCA.md](MARCA.md) |
| Agregar un tipo de beat | `motion/text_overlay.html`, objeto `BEATS` |
| Cambiar cómo se eligen los fragmentos | `services/fragment_selector.py`, `SYSTEM_PROMPT` |
| Cambiar de proveedor de IA | `.env` — ver [PROVEEDORES.md](PROVEEDORES.md) |
| Ajustar zonas seguras, subtítulos, loudness | `config/brand.py` |
| Saber por qué algo no anda | `python scripts/doctor.py` |

## Estructura

```
config/     settings.py (entorno) · brand.py (tokens, carga themes/)
themes/     neutral.json (default) · sintergia.json (ejemplo real)
motion/     compose_text.py · compose.py · node.py
            text_overlay.html · overlay.html   ← la animación
            render_text.cjs · render_overlay.cjs   ← Playwright
            scenes/*.json   ← las escenas
services/   llm.py (proveedor) · transcription.py · fragment_selector.py · video_renderer.py
utils/      subtitles.py (.ass) · graphics.py (Pillow) · paths.py (validación)
scripts/    doctor.py
fonts/      tipografías OFL (ver NOTICE)
largos/     videos de entrada (ignorado por git)
output/     videos generados (ignorado por git)
.tmp/       cuadros, timelines, cachés — se puede borrar sin miedo
```
