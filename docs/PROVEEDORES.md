# PROVEEDORES.md — elegir tu IA

**Si solo vas a hacer videos animados de texto, saltéate este documento.** Ese pipeline no
usa ninguna IA: vos (o tu agente, por fuera) escribís el JSON y el renderizador hace el
video. No necesitás clave de API ni conexión.

Esto aplica al **pipeline de video largo → 5 shorts** (`main.py`), que sí llama a dos
servicios: uno que transcribe y otro que elige los fragmentos.

---

## Cómo funciona

El proyecto no está atado a ningún proveedor. Usa el SDK de OpenAI como **cliente genérico**,
porque su protocolo es el que más servicios implementan. Cambiar de proveedor es cambiar tres
variables en `.env`:

```bash
LLM_BASE_URL=...    # a dónde apuntar
LLM_API_KEY=...     # tu clave
LLM_MODEL=...       # qué modelo
```

> Usar el SDK de OpenAI **no implica usar modelos de OpenAI**. Es solo el protocolo.

## Configuraciones conocidas

### Groq — por defecto

Rápido y con capa gratis generosa. Es contra el que está probado el proyecto.

```bash
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=gsk_...
LLM_MODEL=openai/gpt-oss-120b
LLM_REASONING_EFFORT=low
```

Transcribe y razona, así que con una sola clave tenés las dos piezas.

> ⚠️ `LLM_REASONING_EFFORT=low` **no es opcional** con los modelos `gpt-oss`. Son modelos de
> razonamiento: sin bajarles el esfuerzo, se gastan el presupuesto de tokens razonando y
> devuelven el JSON cortado, que falla con `json_validate_failed`.

### OpenAI

```bash
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4.1-mini
LLM_REASONING_EFFORT=
```

Dejá `LLM_REASONING_EFFORT` vacío salvo que uses un modelo de razonamiento (serie `o`, `gpt-5`).
Transcribe con `whisper-1`.

### OpenRouter — una clave, muchos modelos

Útil si querés probar Claude, Gemini o Llama sin abrir cuenta en cada lado.

```bash
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-...
LLM_MODEL=anthropic/claude-sonnet-4.5
LLM_REASONING_EFFORT=
```

> OpenRouter **no transcribe**. Necesitás apuntar la transcripción a otro lado:
> ```bash
> STT_BASE_URL=https://api.groq.com/openai/v1
> STT_API_KEY=gsk_...
> ```

### Ollama — local y sin costo

```bash
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=lo-que-sea          # Ollama la ignora, pero el cliente exige que no esté vacía
LLM_MODEL=llama3.1
LLM_REASONING_EFFORT=
```

Honestamente: **no está probado**. Los modelos locales chicos suelen cumplir mal el modo JSON
y la selección de fragmentos devuelve estructuras inválidas. El reintento ayuda, pero no hace
magia. Y Ollama tampoco transcribe: necesitás `STT_BASE_URL` apuntando a otro servicio, o
correr `faster-whisper` por tu cuenta.

---

## Separar transcripción y razonamiento

Son dos trabajos distintos y podés mandarlos a servicios distintos. Si no configurás nada,
la transcripción usa el mismo proveedor que el LLM.

```bash
# razonar con Claude vía OpenRouter, transcribir con Groq
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-...
LLM_MODEL=anthropic/claude-sonnet-4.5

STT_BASE_URL=https://api.groq.com/openai/v1
STT_API_KEY=gsk_...
STT_MODEL=whisper-large-v3
```

El servicio de transcripción tiene que soportar `verbose_json` con
`timestamp_granularities: ["word", "segment"]`. **No es opcional**: los subtítulos palabra por
palabra dependen de los tiempos por palabra. Groq y OpenAI lo soportan.

---

## Lo único realmente incompatible

`reasoning_effort` es el parámetro que no todos aceptan: lo necesitan los modelos de
razonamiento y lo rechazan los demás con un 400.

`services/llm.py` lo resuelve solo: lo manda si está configurado y, **si el proveedor lo
rechaza, reintenta sin él y no lo vuelve a mandar en esa corrida**. Así que si configurás mal
esa variable, perdés una llamada y seguís andando, en vez de que todo falle.

---

## Comprobar que anda

```bash
python scripts/doctor.py
```

Te dice qué proveedor y qué modelo quedaron configurados, pero **no hace una llamada real**.
Para eso:

```bash
python -c "
from services.llm import complete_json
print(complete_json([{'role':'user','content':'Devolvé {\"ok\": true}'}], max_tokens=256))"
```

Si devuelve algo con `ok`, la cadena entera funciona.

### Errores frecuentes

| síntoma | causa casi segura |
|---|---|
| `Falta la clave de API` | No copiaste `.env.example` a `.env`, o la variable está vacía. |
| `404 model_not_found` | El modelo dejó de existir. Los proveedores dan de baja modelos sin aviso: pedí la lista actual a la API. |
| JSON cortado o `json_validate_failed` | Modelo de razonamiento sin `LLM_REASONING_EFFORT=low`. |
| `401` | La clave es de otro proveedor que el `LLM_BASE_URL` que pusiste. |
| Transcripción sin tiempos por palabra | El servicio no soporta `timestamp_granularities`. |

Para ver qué modelos existen hoy en tu proveedor:

```bash
curl -s -H "Authorization: Bearer $LLM_API_KEY" "$LLM_BASE_URL/models" | head -40
```

---

## Sobre el costo

El pipeline de video largo cobra dos veces por video: la transcripción (por minuto de audio)
y la selección (por tokens de la transcripción). Un video de una hora son unos pocos centavos
en Groq.

Dos cosas que ya están hechas para que no pagues de más:

- **La transcripción se cachea** en `.tmp/<video>.transcription.json`, con huella de tamaño y
  fecha del archivo. La segunda corrida sobre el mismo video no la vuelve a pagar.
- **La selección no se cachea**, a propósito: se llama en cada corrida y devuelve fragmentos
  distintos. Si uno no te gustó, volvé a correrlo.

Y el recordatorio que importa: **el pipeline de texto animado no cuesta nada**, porque no
llama a ninguna API.
