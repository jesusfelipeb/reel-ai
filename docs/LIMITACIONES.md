# LIMITACIONES.md — qué no se probó y qué no anda

Este documento existe porque un repositorio que declara sus límites es más útil que uno que
promete de más. Todo lo que sigue está verificado: o se probó y falla, o directamente nunca
se probó y lo decimos.

Resumen rápido:

| pipeline | estado | probado contra |
|---|---|---|
| **Texto animado** (`motion/compose_text.py`) | 🟢 Estable | 5 escenas, varios videos publicados |
| **Híbrido** (`motion/compose.py`) | 🟡 Funciona | **una** escena |
| **Video largo → 5 shorts** (`main.py`) | 🟡 Funciona | **un** video |

---

## Lo que vale para todo el proyecto

**No hay tests automatizados.** Toda la verificación fue mirar cuadros renderizados. Hay dos
herramientas que cubren parte del hueco —`scripts/doctor.py` para el entorno y
`scripts/validate_scene.py` para las escenas— pero nadie comprueba que una animación siga
viéndose bien después de un cambio. Si tocás `motion/*.html`, renderizá stills y mirálos.

**Solo se probó en Linux.** Nada del código es específico de Linux (Python, Node, FFmpeg y
Playwright son multiplataforma), pero nadie lo corrió en macOS ni en Windows. En Windows,
además, lo más probable es que necesites WSL por cómo se resuelve FFmpeg.

**El renderizado es intensivo.** Un video de 30 s son ~900 capturas de pantalla de Chromium.
Con 6 páginas en paralelo tarda ~70 s en una laptop moderna. En una máquina con poca RAM,
bajá `WORKERS` en `motion/compose_text.py`.

---

## Pipeline de texto animado

El más sólido de los tres. Las limitaciones son de diseño, no fallas.

**El texto no se parte solo.** Casi todos los campos van con `white-space: nowrap`: si no
entra, se sale de la pantalla. Por eso existen los límites de caracteres de
[BEATS.md](BEATS.md) y el validador. La única excepción son los `list.items[]`.

**No podés cambiar las animaciones desde la escena.** Las curvas y los tiempos internos están
en la plantilla. Es deliberado —es lo que permite que un LLM escriba escenas sin saber de
animación— pero significa que para un movimiento distinto hay que editar HTML.

**Ocho tipos de beat y nada más.** No hay forma de agregar uno desde el JSON; se agrega en el
objeto `BEATS` de `motion/text_overlay.html`.

**Sin imágenes ni video dentro de los beats.** Todo es texto, formas y color. Si necesitás
mostrar una captura de pantalla, este pipeline no es el camino.

**Sin voz ni música.** El video sale con una pista de audio **silenciosa** (está ahí porque
varias redes rechazan archivos sin audio). Si querés locución o música, agregala después con
FFmpeg o en el editor de la red.

**Límites duros poco intuitivos**, todos verificados y todos comprobados por el validador:

- `tasks` necesita más de 4,4 s: el sello cae en el segundo 3,9, fijo.
- `steps` necesita más de 2,6 s y `list` más de 1,8 s, o el reparto interno sale negativo y la
  animación se rompe.
- `result.count_to` no puede pasar de 6: dibuja un teléfono por unidad y el séptimo queda
  fuera de pantalla.
- `accent` es una **lista** en `hook` y un **número** en `tags`. Es una inconsistencia real de
  la plantilla, no un error de la documentación.

---

## Pipeline híbrido (video + animación superpuesta)

🟡 **Se probó con exactamente una escena**, `examples/seo-cuentas.json`, contra un video de
1920×1080. Funciona y el resultado está publicado, pero es el menos ejercitado.

- **Asume una fuente 16:9 de 1920×1080.** `SRC_W` y `SRC_H` están escritos en
  `motion/compose.py`. Con otra resolución, los recortes y el encuadre de la cara van a estar
  mal calculados.
- **La escena se escribe a mano, y es laboriosa.** Hay que indicar la posición de la cara,
  las ventanas de layout dividido y los fotogramas clave del zoom. No hay herramienta que
  ayude y el LLM no genera este formato.
- **Necesita una transcripción ya hecha**, con tiempos por palabra, en la ruta que diga el
  campo `transcription`.
- **Su formato no está documentado ni validado.** [BEATS.md](BEATS.md) solo cubre el pipeline
  de texto, y `validate_scene.py` saltea estas escenas a propósito.
- **`face.min_x` es un parche.** Existe para dejar fuera del recorte un elemento quemado en el
  borde del video original (un distintivo de redes). Es específico de aquel video.

---

## Pipeline de video largo → 5 shorts

🟡 **Se probó con exactamente un video**: `seo.mp4`, 11,2 minutos, 1920×1080, en español.
Generó 5 shorts correctos, verificados cuadro por cuadro. Todo lo demás es terreno sin pisar.

### No probado

- **Otra relación de aspecto.** Solo 16:9. Un video vertical o 4:3 no se probó nunca.
- **Más de ~15 minutos.** Groq limita el audio a 25 MB. A 16 kHz y 64 kbps, una hora de video
  da unos 28 MB: **por encima del límite**. Habría que trocear el audio, y eso no está
  implementado. Si tu video pasa de ~50 minutos, este pipeline va a fallar.
- **Audio en más de un idioma**, o con mucho ruido de fondo.
- **Varios hablantes.** El encuadre asume una sola persona a cámara.

### Problemas conocidos y reales

**El LLM a veces devuelve datos malos para el gráfico.** Observado en corridas reales:

- un contador salió como «s0» (puso la unidad en el campo del prefijo),
- un gráfico quedó en el último segundo del fragmento, sin tiempo de verse,
- un sello decía «CALL TO ACTION» — texto sobre el guion, no del contenido.

No hay validación de que `offset + duration` entre dentro del fragmento. **Revisá los shorts
antes de publicarlos.**

**El contador no separa miles.** Muestra `$500000`, no `$500.000`. Es una limitación de
`drawtext`: la expresión `%{eif:...}` de FFmpeg no tiene separador de miles.

**Un gráfico por fragmento, como máximo.** No está soportado tener varios.

**Los resultados cambian entre corridas.** El LLM se llama de nuevo cada vez y elige
fragmentos distintos. Es a propósito, pero significa que no podés reproducir un resultado
exacto. (La transcripción sí se cachea.)

**Si un fragmento no cumple la duración, se descarta.** El selector valida 30-60 s y
reintenta hasta 3 veces. Si tras eso alguno sigue mal, lo tira: podés terminar con 4 shorts
en vez de 5. Es deliberado — mejor 4 coherentes que uno de 15 segundos.

---

## Proveedores de IA

Lo probado es **Groq** con `openai/gpt-oss-120b` y `whisper-large-v3`. El resto de las
configuraciones de [PROVEEDORES.md](PROVEEDORES.md) deberían funcionar porque usan el mismo
protocolo, pero no se ejercitaron una por una.

**Ollama y los modelos locales chicos son el caso dudoso.** Suelen cumplir mal el modo JSON y
la selección de fragmentos devuelve estructuras inválidas. El reintento ayuda y no resuelve.

---

## Seguridad

Dos vulnerabilidades reales se encontraron y se cerraron antes de publicar, las dos por
tratar la escena como dato de confianza:

1. **Ejecución de código**: el texto de la escena se interpolaba sin escapar en `innerHTML`,
   así que un campo con `<img src=x onerror=...>` ejecutaba JavaScript en el renderizador.
   Hoy se escapa todo con una *tagged template*.
2. **Escritura fuera del proyecto**: `scene["name"]` formaba rutas sin validar, y `pathlib`
   descarta el lado izquierdo de un `/` si el derecho es absoluto. Hoy se valida en
   `utils/paths.py`.

**Lo que sigue siendo cierto:** una escena es código de otra persona. El renderizador abre
Chromium y lo alimenta con ese contenido. Las dos vías conocidas están cerradas, pero no hubo
auditoría externa. **Mirá una escena antes de renderizarla**, igual que mirarías un script.

---

## Cómo reportar algo

Si chocás con un límite que no está acá, abrí un issue con la escena (o el video) y lo que
esperabas. Especialmente valioso: cualquier cosa de la lista de **no probado**. Si corriste
el pipeline largo contra un video que no es 16:9 de 11 minutos, sos la primera persona en
hacerlo y nos sirve saber qué pasó.
