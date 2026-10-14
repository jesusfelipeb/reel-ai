# PROMPT.md — que tu agente escriba las escenas

Este es el documento que hace que reel-ai sirva **con cualquier agente y cualquier modelo**.

No hay integración que hacer. El proyecto no se conecta a tu IA: vos le das a tu modelo la
especificación, él escribe un archivo JSON, y lo renderizás. Funciona igual con Claude, con
ChatGPT, con Gemini, con un modelo local en Ollama o con un becario atento.

El ciclo es siempre el mismo:

```
   tu idea  →  [ el LLM escribe la escena ]  →  escena.json
                                                    │
                                 ┌──────────────────┤
                                 ▼                  ▼
                     validate_scene.py      compose_text.py --stills
                     (milisegundos)         (segundos)
                                 │                  │
                      ¿errores? ─┘        ¿se ve bien? ─┘
                      vuelven al LLM      lo mirás vos
```

El validador es la pieza clave: le devuelve al modelo errores concretos y accionables, así
que **el modelo se corrige solo** sin que vos tengas que revisar JSON a mano.

---

## Antes del prompt: tu brief

El prompt de abajo termina en *"describí acá tu tema"*. Si ahí ponés dos líneas, vas a
recibir una escena correcta y genérica — pasa el validador, renderiza, y no la mira nadie.

Lo que cambia el resultado es anteponer un **brief de marca**: quién sos, a quién le hablás,
cómo escribís y qué ganchos tuyos ya funcionaron. Se escribe una vez y se reutiliza siempre.

```
brief.md  +  este prompt  +  tu tema  ──►  el modelo
   │
   una vez         cada video
```

La plantilla y un ejemplo lleno están en **[BRIEF.md](BRIEF.md)**. Son diez minutos y es la
diferencia entre un video que existe y uno que alguien mira.

---

## El prompt

Copiá todo lo que está entre las líneas. Es autosuficiente: no hace falta que el modelo haya
visto el repositorio. Si tenés brief, pegalo **antes**.

---

````text
Vas a escribir una ESCENA para reel-ai: un archivo JSON que describe un video vertical
animado de 1080x1920 para Reels/TikTok/Shorts. No escribas código ni explicaciones: tu
salida es un único objeto JSON válido.

## Estructura

{
  "name": "nombre-del-archivo",
  "duration": 29.6,
  "beats": [
    { "type": "hook", "in": 0.0, "out": 5.2,
      "chip": "KINESIOLOGOS CON CONSULTORIO",
      "lines": ["TE ESCRIBEN", "A LAS 11 PM"],
      "accent": [1] },
    { "type": "end", "in": 5.2, "out": 29.6,
      "wordmark": "Tu Marca", "studio": "STUDIO",
      "headline": ["¿CUANTOS TURNOS", "PERDISTE HOY?"],
      "cta": "ESCRIBI AGENDA", "handle": "@tumarca" }
  ]
}

  - "name": letras, numeros, - y _ ; sin espacios ni barras.
  - "duration": IGUAL al "out" del ultimo beat.
  - "in" y "out": segundos absolutos desde el inicio del video. NUMEROS, sin comillas:
    "in": 5.2 esta bien; "in": "5.2" ROMPE la escena.
  - El "out" de un beat es EXACTAMENTE el "in" del siguiente: ni hueco ni superposicion.
  - "count_to" tambien es numero sin comillas.

No controlás las animaciones: se calculan solas a partir de in/out.

## Los 8 tipos de beat

TODOS los campos son TEXTO QUE SE VE EN PANTALLA, no nombres de estilo ni categorias.
  "chip" es la etiqueta chica dentro de la pastilla de color, arriba del titular: deci
  QUE ES ESTO o PARA QUIEN ES. Ejemplo bueno: "KINESIOLOGOS CON CONSULTORIO".
  Ejemplos MALOS: "alert", "highlight", "info", "kine" — no son texto para un lector.
Los titulares van en MAYUSCULAS; los campos "sub" y "kicker", en minuscula.

hook   — apertura.          {chip, lines[], accent[]}
         accent es una LISTA de indices (base 0) de lines[] que van resaltadas.
tags   — a quien le hablas. {chip, lines[], tags[], accent}
         accent es UN NUMERO (un solo indice de tags[]). Esta asimetria con hook es real.
steps  — proceso numerado.  {chip, steps:[{title, sub}, ...]}
list   — puntos con tilde.  {chip, items:[{title, sub}, ...]}
tasks  — lista + sello.     {chip, title, tasks[], times, stamp}
result — transformacion.    {from, to, count_to, sub}
         Los digitos iniciales de "to" se reemplazan por un contador en vivo:
         "5 SHORTS" muestra el 5 subiendo. count_to debe ser de 1 a 6.
swap   — cambiar palabra.   {kicker, from, to, sub}
end    — cierre. SIEMPRE el ultimo. {wordmark, studio, headline[], cta, handle}
         headline tiene 1 o 2 lineas; la ultima sale en color de alerta.

## LARGO DEL TEXTO (lo que mas se rompe)

El texto NO se parte en dos lineas: si no entra, se sale de la pantalla y queda cortado.
Guiate por las PALABRAS, que es mas facil de respetar que contar letras. El maximo en
caracteres (MAYUSCULAS) esta al lado como tope duro:

  swap.from / swap.to ........  1 palabra corta ........  max  8
  result.from / result.to ....  1-2 palabras ...........  max 11
  hook.lines[] ...............  1-2 palabras por linea .  max 12
  tasks.title, steps[].title .  1-2 palabras ...........  max 15
  end.headline[] .............  2-3 palabras por linea .  max 18
  tasks.tasks[] ..............  2-4 palabras ...........  max 23
  tags.tags[] ................  1-2 palabras ...........  max 24
  end.cta ....................  2-3 palabras ...........  max 25
  end.studio .................  1-3 palabras ...........  max 22
  end.wordmark ...............  1 nombre corto .........  max 10 minusculas / 7 mayusculas
  chip .......................  3-5 palabras ...........  max 37
  steps[].sub ................  5-7 palabras ...........  max 43
  list.items[] ...............  parten solos, sin tope

Las lineas del hook son MUY cortas: "NO NECESITAS", "TE ESCRIBEN", "QUE PIERDES".
Si una frase no entra, partila en dos lineas del array en vez de acortarla a la fuerza.
Antes de devolver el JSON, repasa cada campo y conta: si una linea del hook tiene tres
palabras, casi seguro se pasa.

## DURACIONES MINIMAS (por debajo, la animacion se rompe o no llega a verse)

  list ....... > 1.8 s     hook ....... 3.0 s     result ..... 3.3 s
  steps ...... > 2.6 s     tags ....... 3.2 s     swap ....... 3.5 s
  tasks ...... 4.4 s (el sello cae en el segundo 3.9, fijo)
  end ........ 2.5 s (recomendado 4-5 s para que se lea el cta)

Recomendado: ~3 s por paso en steps, ~2.5 s por item en list.

## Como armar un buen video

- Duracion total entre 25 y 45 segundos.
- Empeza con hook. Termina con end. En el medio, 1 a 3 beats.
- El gancho decide todo: en los primeros 3 segundos tiene que quedar claro para quien es
  y que problema concreto resuelve. Nada de frases genericas.
- Usa tasks UNA sola vez como maximo: su sello sacude la pantalla y es el golpe del video.
- Varia los tipos. Dos beats del mismo tipo seguidos se ven repetitivos.
- Escribi los titulares en MAYUSCULAS y los campos "sub" en minusculas.
- El cta tiene que ser una accion concreta ("ESCRIBI DIAGNOSTICO"), no "seguime".

## Tu tarea

[DESCRIBI ACA TU TEMA, A QUIEN LE HABLAS Y QUE QUERES QUE HAGA EL ESPECTADOR]

Devolve solo el JSON.
````

---

## Ejemplo de resultado

Esto es una escena real y válida, de 29,6 s:

```json
{
  "name": "diagnostico-gratis",
  "duration": 29.6,
  "beats": [
    { "type": "hook", "in": 0.0, "out": 5.2,
      "chip": "PROFESIONALES INDEPENDIENTES",
      "lines": ["NO NECESITAS", "UNA WEB", "SINO SABER", "QUÉ PIERDES"],
      "accent": [2, 3] },
    { "type": "tags", "in": 5.2, "out": 8.8,
      "chip": "SEGURO TE PREGUNTASTE ESTO",
      "lines": ["ESTO ES PARA", "TI SI ERES"],
      "tags": ["MÉDICO", "ABOGADO", "CONTADOR", "TERAPEUTA"],
      "accent": 0 },
    { "type": "steps", "in": 8.8, "out": 24.4,
      "chip": "DIAGNÓSTICO GRATIS · 15 MIN",
      "steps": [
        {"title": "REVISO",  "sub": "cómo consigues pacientes o clientes"},
        {"title": "TE DIGO", "sub": "si necesitas web, agente IA o nada aún"},
        {"title": "SALES",   "sub": "con un plan claro, sin compromiso"}
      ] },
    { "type": "end", "in": 24.4, "out": 29.6,
      "wordmark": "Sintergia", "studio": "STUDIO",
      "headline": ["¿DE VERDAD", "NECESITAS WEB?"],
      "cta": "ESCRIBE DIAGNÓSTICO", "handle": "@sintergiastudio" }
  ]
}
```

---

## El ciclo de corrección

Guardá lo que devolvió el modelo y validalo:

```bash
python scripts/validate_scene.py motion/scenes/mi-escena.json
```

Si hay errores, **pegáselos de vuelta al modelo tal cual**. Están escritos para que los
entienda sin contexto adicional:

```
[ERROR] beat 0 (hook): 'lines' tiene 21 caracteres y el maximo es 12.
        El texto NO se parte solo: se sale de la pantalla. Acortalo.
    valor: "SINO PERDER CLIENTES?"
[ERROR] beat 2 (steps): dura 1.70 s y el minimo es 2.61 s — la animacion se ROMPE.
```

Una o dos vueltas suelen alcanzar. Después, lo único que confirma de verdad:

```bash
python -m motion.compose_text motion/scenes/mi-escena.json --stills 3,12,22
```

Tarda segundos y te deja tres PNG en `output/stills/mi-escena/`. **Miralos.** El
validador atrapa lo medible; que el texto *diga* algo que valga la pena solo lo juzgás vos.

---

## Conectarlo a tu agente

### Agentes con acceso a archivos (Claude Code, Cursor, Codex, Copilot…)

Son los que mejor cierran el ciclo, porque pueden validar y corregirse sin vos. Una sola
instrucción alcanza:

> Leé `brief.md` y `docs/BEATS.md`. Escribí una escena sobre [tema] en
> `motion/scenes/<nombre>.json`. Validala con `python scripts/validate_scene.py` y corregí
> hasta que pase. Después renderizá los stills y mostrámelos.

Si el agente soporta instrucciones permanentes (`CLAUDE.md`, `.cursorrules`, `AGENTS.md`),
poné ahí la regla y no la repetís nunca más:

```markdown
Al escribir escenas en motion/scenes/, leé primero brief.md (la voz de la marca) y
docs/BEATS.md (el formato). Validá con scripts/validate_scene.py y corregí hasta que
pase antes de dar nada por terminado.
```

Ese archivo lo escribe cada usuario para su agente — el repositorio no trae ninguno, así que
no hay nada que pisar.

### Chat sin acceso a archivos (ChatGPT, Claude.ai, Gemini…)

Pegá el prompt de arriba, copiá el JSON que devuelve a un archivo, y corré el validador vos.
Si falla, pegale los errores de vuelta.

### Por API

El proyecto ya trae un cliente que habla con cualquier proveedor compatible con OpenAI
(ver [PROVEEDORES.md](PROVEEDORES.md)):

```python
from pathlib import Path
from services.llm import complete_json

spec = Path("docs/PROMPT.md").read_text(encoding="utf-8")
brief = Path("brief.md").read_text(encoding="utf-8")   # ver BRIEF.md

escena = complete_json([
    {"role": "system", "content": brief + "\n\n" + spec},
    {"role": "user", "content": "Un video sobre por qué un kinesiólogo pierde turnos "
                                "por no responder WhatsApp a tiempo."},
])
Path("motion/scenes/kine.json").write_text(escena, encoding="utf-8")
```

Y para cerrar el ciclo sin intervención, el validador tiene salida para máquinas:

```bash
python scripts/validate_scene.py motion/scenes/kine.json --json
# {"ok": false, "errors": [...], "warnings": [...]}
```

Leés ese JSON, y si `ok` es `false` le mandás `errors` al modelo en otro turno.

---

## Qué modelo usar

Escribir una escena **no es una tarea difícil**: el modelo no razona sobre animación, solo
llena campos respetando límites. Un modelo chico y barato alcanza.

Donde sí se nota un modelo mejor es en **el guion**: el gancho, qué dejar afuera, que la
promesa sea concreta. Esa parte no la resuelve la especificación, y es exactamente la que
más impacto tiene en si el video funciona o no.

Dicho de otro modo: el modelo te da una escena *válida* fácil. Una escena *buena* depende de
lo que vos le pidas.
