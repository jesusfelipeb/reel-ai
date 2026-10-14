"""Cliente de IA agnostico del proveedor.

Este proyecto solo le pide dos cosas a un proveedor de IA: una respuesta de chat en JSON y
una transcripcion con timestamps. Las dos existen con la misma forma en cualquier API
compatible con OpenAI, asi que alcanza con cambiar `base_url` para pasar de Groq a OpenAI,
OpenRouter, Together u Ollama. Por eso el SDK que se usa es el de OpenAI y no el de un
proveedor concreto.

Lo unico que de verdad cambia entre proveedores es `reasoning_effort`: lo necesitan los
modelos de razonamiento y lo rechazan los demas. Se manda si esta configurado y, si el
proveedor lo rechaza, se reintenta sin el y no se vuelve a mandar en esa corrida.
"""
import functools

from openai import BadRequestError, OpenAI

from config.settings import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_REASONING_EFFORT,
    STT_API_KEY,
    STT_BASE_URL,
    STT_MODEL,
)

# Se apaga solo si el proveedor rechaza el parametro, para no pagar un 400 por llamada.
_reasoning_supported = bool(LLM_REASONING_EFFORT)


def _client(base_url: str, api_key: str, what: str) -> OpenAI:
    if not api_key:
        raise RuntimeError(
            f"Falta la clave de API para {what}.\n"
            "  Copiá .env.example a .env y completá LLM_API_KEY.\n"
            f"  Proveedor configurado: {base_url}"
        )
    return OpenAI(base_url=base_url, api_key=api_key)


@functools.lru_cache(maxsize=1)
def chat_client() -> OpenAI:
    return _client(LLM_BASE_URL, LLM_API_KEY, "el LLM")


@functools.lru_cache(maxsize=1)
def stt_client() -> OpenAI:
    return _client(STT_BASE_URL, STT_API_KEY, "la transcripcion")


def complete_json(messages: list[dict], *, temperature: float = 0.4, max_tokens: int = 4096) -> str:
    """Pide una respuesta en JSON mode y devuelve el texto crudo del modelo."""
    global _reasoning_supported

    kwargs = {
        "model": LLM_MODEL,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if _reasoning_supported:
        kwargs["reasoning_effort"] = LLM_REASONING_EFFORT

    try:
        response = chat_client().chat.completions.create(**kwargs)
    except BadRequestError:
        if not _reasoning_supported:
            raise
        # El proveedor no conoce reasoning_effort: se reintenta sin el una sola vez.
        _reasoning_supported = False
        kwargs.pop("reasoning_effort")
        response = chat_client().chat.completions.create(**kwargs)

    return response.choices[0].message.content


def transcribe_audio(filename: str, data: bytes) -> dict:
    """Transcribe con timestamps por palabra y por segmento."""
    result = stt_client().audio.transcriptions.create(
        file=(filename, data),
        model=STT_MODEL,
        response_format="verbose_json",
        timestamp_granularities=["word", "segment"],
    )
    return result.model_dump()
