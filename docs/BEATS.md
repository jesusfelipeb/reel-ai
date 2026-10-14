# BEATS.md — especificación del formato de escena

Una **escena** es un archivo JSON que describe un video vertical completo. Es el único
contrato del proyecto: lo escribe una persona o un LLM, y lo consume el renderizador.

Si estás generando escenas con un agente, dale [PROMPT.md](PROMPT.md) — es esta misma
especificación comprimida para que entre en un prompt.

---

## Estructura

```json
{
  "name": "mi-primer-video",
  "duration": 29.6,
  "brand": "neutral",
  "theme": "dark",
  "beats": [
    { "type": "hook", "in": 0.0, "out": 5.2, "...": "campos del tipo" },
    { "type": "end",  "in": 24.4, "out": 29.6, "...": "..." }
  ]
}
```

### Campos de la escena

| campo | tipo | req. | qué hace |
|---|---|:--:|---|
| `name` | string | sí | Nombre del archivo de salida (`output/motion/<name>.mp4`). Solo letras, números, `.`, `-`, `_`; de 1 a 64 caracteres; empieza con letra o número. **Sin barras ni `..`** — se valida y se rechaza, porque forma una ruta de disco. |
| `duration` | number | sí | Duración total en segundos. Debe coincidir con el `out` del último beat. |
| `brand` | string | no | Qué tema de `themes/` usar. Por defecto, `REEL_BRAND` del entorno o `neutral`. |
| `theme` | string | no | `"dark"` (por defecto) o `"light"`. |
| `beats` | array | sí | Los bloques, en orden. |

### Campos comunes a todos los beats

| campo | tipo | qué hace |
|---|---|---|
| `type` | string | Uno de los 8 tipos de abajo. |
| `in` | number | Segundo en que aparece, **absoluto** desde el inicio del video. |
| `out` | number | Segundo en que desaparece. |

**Reglas de tiempo:**

- Los beats **no se superponen**: el `out` de uno es el `in` del siguiente.
- Los tiempos son absolutos. Las animaciones internas se calculan solas a partir de
  `in`/`out` — vos no las controlás, y ese es el punto: así un LLM puede escribir escenas sin
  saber nada de animación.
- Todos los beats salen con una animación de 0,35 s al final de su ventana. El `end` es la
  excepción: no sale nunca, porque es el último.

---

## Lo que más rompe: el texto no se parte solo

La mayoría de los campos se renderizan con `white-space: nowrap`. **Si el texto no entra, no
se parte en dos líneas: se sale de la pantalla y queda cortado.** Es el error número uno al
escribir escenas.

Límites medidos en el render real (1080 px de ancho). Usá la columna de MAYÚSCULAS si tu
texto va en mayúsculas, que es lo habitual en los titulares:

| campo | MAYÚSCULAS | minúsculas |
|---|:--:|:--:|
| `swap.from` / `swap.to` | **8** | 9 |
| `result.from` / `result.to` | **11** | 13 |
| `hook.lines[]` | **12** | 14 |
| `tasks.title` · `steps[].title` | **15** | 18 |
| `end.headline[]` | **18** | 20 |
| `tasks.tasks[]` | **23** | 27 |
| `tags.tags[]` | **24** | 28 |
| `end.cta` | **25** | 30 |
| `end.studio` | **22** | 22 (monoespaciada) |
| `end.wordmark` | **10** minúsculas · **7** mayúsculas | es serif y mixto: `Sintergia` entra, `Nutri Laura` no |
| `chip` (en cualquier beat) | **37** | 37 |
| `steps[].sub` | **43** | 43 |

> Los campos `chip` y `steps[].sub` van en tipografía monoespaciada, así que mayúsculas y
> minúsculas ocupan lo mismo.
>
> **La excepción son los `list.items[]`**: ni `title` ni `sub` llevan `nowrap`, así que sí se
> parten en varias líneas dentro de sus 760 px. No se te va a salir por el costado, pero si te
> excedés mucho el ítem crece hacia abajo y puede pisar al siguiente (están cada 290 px).
> Como referencia, `title` entra en una línea hasta ~19 caracteres en mayúsculas.

Estos números no son estimaciones: están medidos contra la plantilla y predicen los dos
desbordes reales que tuvimos. `"PERDER CLIENTES?"` son 16 caracteres en una línea de `hook`
cuyo límite es 12 → se cortó en pantalla. `"si necesitas web, agente de WhatsApp, o nada aún"`
son 48 en un `steps[].sub` de 43 → se salió por la derecha.

**Dejá un margen.** Apuntá a un 80 % del límite. Un titular corto además se lee mejor.

---

## Los 8 tipos de beat

### `hook` — la apertura

Una pastilla arriba y hasta 4 líneas grandes que suben una tras otra. Es con lo que
empieza casi todo video.

```json
{
  "type": "hook", "in": 0.0, "out": 5.2,
  "chip": "PROFESIONALES INDEPENDIENTES",
  "lines": ["NO NECESITAS", "UNA WEB", "SINO SABER", "QUÉ PIERDES"],
  "accent": [2, 3]
}
```

| campo | tipo | qué hace |
|---|---|---|
| `chip` | string | Etiqueta de contexto en la pastilla de color. |
| `lines` | string[] | Una entrada por línea. Recomendado 2-4; cada una ≤ 12 caracteres. |
| `accent` | number[] | Índices (desde 0) de las líneas que van en color de énfasis. |

Duración mínima práctica: **3 s**. Habitual: 4-6 s.

---

### `tags` — a quién le hablás

Un par de líneas y después pastillas que aparecen de a una. Sirve para calificar audiencia
("esto es para vos si sos…").

```json
{
  "type": "tags", "in": 5.2, "out": 8.8,
  "chip": "SEGURO TE PREGUNTASTE ESTO",
  "lines": ["ESTO ES PARA", "TI SI ERES"],
  "tags": ["MÉDICO", "ABOGADO", "CONTADOR", "TERAPEUTA"],
  "accent": 0
}
```

| campo | tipo | qué hace |
|---|---|---|
| `chip` | string | |
| `lines` | string[] | Líneas de introducción, ≤ 15 caracteres cada una. |
| `tags` | string[] | Las pastillas. 3-5 funciona bien. |
| `accent` | number | **Un solo índice**, no una lista. |

> ⚠️ Inconsistencia real de la plantilla: en `hook`, `accent` es un **array**; en `tags` es un
> **número**. Está así en el código; si pasás el tipo equivocado, el beat falla al construirse.

La última etiqueta aparece en `1,1 + 0,32 × (n−1) + 0,55` s. Con 4 etiquetas eso es ~2,6 s:
dale al beat al menos **3,2 s**.

---

### `steps` — un proceso numerado

Pasos conectados por una línea vertical que se dibuja sola. El paso activo se resalta y los
demás se atenúan.

```json
{
  "type": "steps", "in": 8.8, "out": 24.4,
  "chip": "DIAGNÓSTICO GRATIS · 15 MIN",
  "steps": [
    {"title": "REVISO",  "sub": "cómo consigues pacientes o clientes"},
    {"title": "TE DIGO", "sub": "si necesitas web, agente IA o nada aún"},
    {"title": "SALES",   "sub": "con un plan claro, sin compromiso"}
  ]
}
```

| campo | tipo | qué hace |
|---|---|---|
| `chip` | string | |
| `steps` | `{title, sub}[]` | 3-4 pasos. Se numeran solos (01, 02, 03). |

> 🔴 **`out − in` tiene que ser mayor que 2,6 s.** El reparto interno es
> `(duración − 2,6) / cantidad`; por debajo de eso sale negativo y la animación se rompe.
> Dale ~3 s por paso: con 3 pasos, unos 12-16 s.

---

### `list` — puntos con tilde

Ítems con un check que se dibuja. Más suelto que `steps`: no implica orden.

```json
{
  "type": "list", "in": 19.4, "out": 27.4,
  "chip": "ORGANIZACIÓN",
  "items": [
    {"title": "PRESUPUESTO MENSUAL", "sub": "te muestra dónde puedes ahorrar"},
    {"title": "LISTA DE COMPRAS",    "sub": "sin repetir lo que ya tienes"}
  ]
}
```

| campo | tipo | qué hace |
|---|---|---|
| `chip` | string | |
| `items` | `{title, sub}[]` | 2-3 ítems. A diferencia del resto de los beats, **acá el texto sí se parte en varias líneas** (ambos campos). |

> 🔴 **`out − in` tiene que ser mayor que 1,8 s.** Mismo motivo que `steps`.

---

### `tasks` — una lista que termina en un sello

Un título, tareas que entran desde la izquierda, un número grande y un sello que golpea la
pantalla con una sacudida.

```json
{
  "type": "tasks", "in": 0.0, "out": 8.0,
  "chip": "LO QUE HACÉS HOY",
  "title": "EDITAR UN REEL",
  "tasks": ["Recortar el video", "Escribir subtítulos", "Buscar música"],
  "times": "3 HORAS",
  "stamp": "CADA SEMANA"
}
```

| campo | tipo | qué hace |
|---|---|---|
| `chip` · `title` · `times` · `stamp` | string | |
| `tasks` | string[] | 3-4 entradas. |

> 🔴 **El sello cae en el segundo 3,9 del beat, fijo.** Si el beat dura menos de ~4,4 s, el
> sello no llega a verse. Dale al menos **5 s**.

El golpe del sello sacude toda la escena y produce un destello. Es el momento más fuerte del
video: usalo una sola vez.

---

### `result` — una transformación con contador

Un marco 16:9, una flecha y teléfonos que van apareciendo mientras un número sube.

```json
{
  "type": "result", "in": 33.4, "out": 40.0,
  "from": "1 VIDEO LARGO",
  "to": "5 SHORTS",
  "count_to": 5,
  "sub": "EN MINUTOS, NO EN HORAS"
}
```

| campo | tipo | qué hace |
|---|---|---|
| `from` | string | Estado inicial. |
| `to` | string | Estado final. **Los dígitos del principio se eliminan** y los reemplaza el contador en vivo: escribí `"5 SHORTS"` y se ve el 5 subiendo. |
| `count_to` | number | Hasta cuánto cuenta **y cuántos teléfonos dibuja**. |
| `sub` | string | Pastilla de cierre. |

> ⚠️ `count_to` **no puede pasar de 6**. Los teléfonos miden 72 px y se colocan en
> `600 + i × 80`: el sexto termina en 1072 y entra justo; el séptimo arranca en 1080 y queda
> fuera de pantalla. Con 5 o menos vas cómodo.

Duración mínima: **3,3 s**.

---

### `swap` — cambiar una palabra por otra

Una palabra aparece, se tacha y la reemplaza otra. Muy fuerte visualmente, texto muy corto.

```json
{
  "type": "swap", "in": 12.0, "out": 16.5,
  "kicker": "EL CAMBIO REAL",
  "from": "GASTO",
  "to": "ACTIVO",
  "sub": "ASÍ LO VE TU CLIENTE"
}
```

| campo | tipo | qué hace |
|---|---|---|
| `kicker` | string | Línea chica de arriba. |
| `from` | string | Palabra tachada. **≤ 8 caracteres.** |
| `to` | string | Palabra nueva. **≤ 8 caracteres.** |
| `sub` | string | |

> La palabra nueva entra en el segundo 2,0 y el subtítulo en el 2,6. Duración mínima: **3,5 s**.

---

### `end` — la tarjeta de cierre

Constelación, logotipo, titular final, llamada a la acción y usuario. **Siempre el último
beat**, y el único sin animación de salida.

```json
{
  "type": "end", "in": 24.4, "out": 29.6,
  "wordmark": "Sintergia",
  "studio": "STUDIO",
  "headline": ["¿DE VERDAD", "NECESITAS WEB?"],
  "cta": "ESCRIBE DIAGNÓSTICO",
  "handle": "@sintergiastudio"
}
```

| campo | tipo | qué hace |
|---|---|---|
| `wordmark` | string | Tu nombre, en tipografía serif. Corto: hasta 10 letras en minúsculas o 7 en mayúsculas. |
| `studio` | string | Bajada chica. |
| `headline` | string[] | 1-2 líneas. **La última va en color de alerta.** |
| `cta` | string | La acción concreta. Late suavemente para llamar la atención. |
| `handle` | string | Tu usuario. |

La barra de progreso de arriba se apaga cuando entra este beat: el espectador ve que terminó.
Duración mínima: **2,5 s**. Recomendado 4-5 s, para que la llamada a la acción se alcance a leer.

---

## Reglas de duración, juntas

| tipo | mínimo duro | recomendado |
|---|:--:|:--:|
| `hook` | 3 s | 4-6 s |
| `tags` | 3,2 s | 3,5-5 s |
| `steps` | **> 2,6 s** | ~3 s por paso |
| `list` | **> 1,8 s** | ~2,5 s por ítem |
| `tasks` | **4,4 s** (el sello está en 3,9) | 6-8 s |
| `result` | 3,3 s | 5-7 s |
| `swap` | 3,5 s | 4-5 s |
| `end` | 2,5 s | 4-5 s |

Un video de Reel funciona bien entre 25 y 45 segundos.

---

## Lista de control antes de renderizar

1. `duration` es igual al `out` del último beat.
2. Los beats están en orden y no se superponen: `out[i] == in[i+1]`.
3. Ningún texto pasa su límite de caracteres (tabla de arriba).
4. `steps` dura más de 2,6 s; `list`, más de 1,8 s; `tasks`, más de 4,4 s.
5. `accent` es un **array** en `hook` y un **número** en `tags`.
6. `count_to` en `result` no pasa de 6.
7. El último beat es `end`.

Y después, lo único que de verdad confirma: renderizá cuadros sueltos y miralos.

```bash
python -m motion.compose_text motion/scenes/mi-escena.json --stills 3,12,22
# mirá los PNG en output/stills/mi-escena/
```

Tarda segundos y te ahorra renderizar un video entero para descubrir que una línea se salió.
