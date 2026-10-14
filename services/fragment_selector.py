import json

from config.settings import (
    FRAGMENT_COUNT,
    FRAGMENT_MAX_SECONDS,
    FRAGMENT_MIN_SECONDS,
)
from services.llm import complete_json

SYSTEM_PROMPT = f"""Sos un editor experto en contenido viral para Reels e Instagram/TikTok/YouTube Shorts.
Vas a recibir la transcripcion de un video horizontal largo, con segmentos y sus timestamps (en segundos).

Tu tarea: elegir los {FRAGMENT_COUNT} mejores fragmentos para convertir en shorts verticales independientes.

Criterios:
- Cada fragmento debe tener sentido por si solo (inicio y cierre claros, sin frases cortadas a la mitad).
- Duracion entre {FRAGMENT_MIN_SECONDS} y {FRAGMENT_MAX_SECONDS} segundos.
- Priorizar ganchos fuertes al inicio (primeros 3 segundos), momentos de alto valor, humor, dato sorprendente o consejo accionable.
- Los {FRAGMENT_COUNT} fragmentos no deben superponerse entre si.
- Usar los timestamps reales de los segmentos provistos, ajustando a un inicio/fin de segmento cercano.

Ademas, para cada fragmento elegis UN grafico animado que va a aparecer superpuesto sobre el video
para reforzar visualmente lo que se dice en ese momento. Elegis el tipo segun el contenido del fragmento:

- "stamp": sello grande rotado con una palabra/frase corta (ideal para ganchos, errores, alertas).
  Campos: text (2-4 palabras, ej "ERROR #1"), subtext (opcional, breve).
- "split": tarjeta comparativa de dos mitades verde/rojo con un valor cada una (ideal cuando se comparan
  dos casos, dos resultados, antes/despues).
  Campos: left_label, left_value, right_label, right_value (valores cortos, ej "3", "+40", "Si", "No").
- "counter": contador que sube en vivo hasta un numero (ideal para cifras de dinero, tiempo perdido,
  porcentajes grandes que se mencionan en el fragmento).
  Campos: prefix (ej "$"), target (numero entero), label (breve, ej "PERDIDO AL ANO").

Reglas del grafico:
- "offset": segundos desde el INICIO del fragmento (no del video completo) donde debe aparecer. Tiene
  que coincidir con el momento en que se menciona ese dato/idea en el audio.
- "duration": cuantos segundos permanece en pantalla (2 a 3.5 segundos).
- Usa datos reales mencionados en la transcripcion del fragmento, no inventes cifras.
- Si ningun tipo encaja bien con el fragmento, omitir el campo "graphic" (puede ser null).

Respondes UNICAMENTE en JSON con este formato exacto:
{{"fragments": [
  {{"start": 12.3, "end": 45.6, "title": "titulo corto y atractivo", "reason": "por que funciona como short",
    "graphic": {{"type": "stamp", "offset": 1.5, "duration": 2.5, "text": "ERROR #1", "subtext": "sin visitas"}}}}
]}}

Ejemplo para "split": {{"type": "split", "offset": 8.0, "duration": 3.0, "left_label": "Clinica A", "left_value": "+40", "right_label": "Clinica B", "right_value": "3"}}
Ejemplo para "counter": {{"type": "counter", "offset": 20.0, "duration": 3.0, "prefix": "$", "target": 500000, "label": "PERDIDO AL ANO"}}
"""


# Margen de redondeo: los cortes se ajustan a bordes de segmento de Whisper
DURATION_TOLERANCE_SECONDS = 1.0
MAX_ATTEMPTS = 3


def _request_fragments(messages: list[dict]) -> tuple[list[dict], str]:
    content = complete_json(messages, temperature=0.4, max_tokens=4096)
    return json.loads(content).get("fragments", []), content


def _has_valid_duration(frag: dict) -> bool:
    duration = float(frag["end"]) - float(frag["start"])
    return (
        FRAGMENT_MIN_SECONDS - DURATION_TOLERANCE_SECONDS
        <= duration
        <= FRAGMENT_MAX_SECONDS + DURATION_TOLERANCE_SECONDS
    )


def _feedback(fragments: list[dict]) -> str:
    problems = []
    if len(fragments) < FRAGMENT_COUNT:
        problems.append(f"Devolviste {len(fragments)} fragmentos, se necesitan {FRAGMENT_COUNT}.")
    for i, frag in enumerate(fragments, start=1):
        if not _has_valid_duration(frag):
            duration = float(frag["end"]) - float(frag["start"])
            problems.append(
                f"El fragmento {i} dura {duration:.1f}s: tiene que durar entre "
                f"{FRAGMENT_MIN_SECONDS} y {FRAGMENT_MAX_SECONDS}s."
            )
    return " ".join(problems)


def select_fragments(segments: list[dict]) -> list[dict]:
    """Pide los fragmentos al LLM y reintenta si alguno no cumple la duracion 30-60s.

    Si tras MAX_ATTEMPTS sigue habiendo fragmentos fuera de rango, se descartan
    (mejor 4 shorts coherentes que uno de 15s que rompe la serie).
    """
    transcript_lines = "\n".join(
        f"[{seg['start']:.1f}-{seg['end']:.1f}] {seg['text'].strip()}"
        for seg in segments
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": transcript_lines},
    ]

    fragments: list[dict] = []
    for _ in range(MAX_ATTEMPTS):
        fragments, raw = _request_fragments(messages)
        fragments = fragments[:FRAGMENT_COUNT]
        feedback = _feedback(fragments)
        if not feedback:
            break
        messages += [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": f"{feedback} Corregilo y devolve el JSON completo otra vez."},
        ]

    valid = [frag for frag in fragments if _has_valid_duration(frag)]
    if not valid:
        raise ValueError("El LLM no devolvio ningun fragmento con duracion valida")
    if len(valid) < len(fragments) or len(valid) < FRAGMENT_COUNT:
        print(f"  aviso: solo {len(valid)} fragmentos cumplen {FRAGMENT_MIN_SECONDS}-{FRAGMENT_MAX_SECONDS}s")

    for frag in valid:
        if not _is_valid_graphic(frag.get("graphic")):
            frag["graphic"] = None

    return valid


_REQUIRED_GRAPHIC_FIELDS = {
    "stamp": {"text"},
    "split": {"left_label", "left_value", "right_label", "right_value"},
    "counter": {"prefix", "target", "label"},
}


def _is_valid_graphic(graphic: dict | None) -> bool:
    if not graphic or not isinstance(graphic, dict):
        return False
    gtype = graphic.get("type")
    if gtype not in _REQUIRED_GRAPHIC_FIELDS:
        return False
    if not _REQUIRED_GRAPHIC_FIELDS[gtype].issubset(graphic.keys()):
        return False
    return "offset" in graphic and "duration" in graphic
