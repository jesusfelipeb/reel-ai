# BRIEF.md — el contexto de tu marca, escrito una sola vez

[PROMPT.md](PROMPT.md) te da un prompt que termina en *"describí acá tu tema"*. Si lo único
que ponés ahí son dos líneas, el modelo te va a devolver una escena **válida y sosa**: va a
pasar el validador, va a renderizar, y no la va a mirar nadie.

El brief es la diferencia. Lo escribís una vez, lo pegás antes del prompt siempre, y a partir
de ahí el modelo deja de escribir para "profesionales en general" y empieza a escribir para
tu gente.

```
brief.md  +  docs/PROMPT.md  +  tu tema  ──►  el modelo  ──►  escena.json
   │
   una vez          cada video
```

**Cómo usarlo:** copiá la plantilla de abajo a `brief.md` en la raíz del proyecto, llenala, y
pegá su contenido antes del prompt. Si usás un agente con acceso a archivos, alcanza con
decirle una vez en tu `AGENTS.md`:

```markdown
Antes de escribir una escena, leé brief.md y docs/BEATS.md.
Validá con scripts/validate_scene.py y corregí hasta que pase.
```

---

## La plantilla

Copiala tal cual. Las instrucciones en cursiva son para vos, borralas al llenar.

```markdown
# Brief de marca

## Qué vendo
*Concreto y con precio o rango si podés. "Ayudo a crecer" no sirve.*

## A quién le hablo
*Incómodamente específico. No "profesionales": "kinesiólogos con consultorio propio
que atienden solos y no tienen secretaria".*

## Qué ya sabe esa persona
*Define cuánto hay que explicar. Si ya sabe que necesita presencia digital, no se lo
expliques: andá directo a qué está perdiendo.*

## Qué le duele de verdad
*El problema como lo vive, no como lo nombra un consultor. No "falta de digitalización":
"le escriben a las 11 de la noche y contesta al otro día".*

## Cómo hablo
*Tuteo o voseo. Formal o directo. Con jerga técnica o sin nada de jerga.
Frases cortas o desarrolladas.*

## Palabras que uso
*5 a 10 términos que son tuyos.*

## Palabras que no uso nunca
*Las que te suenan a otro. "Sinergia", "potenciar", "revolucionario", lo que sea.*

## Promesas que no hago
*Lo que no vas a afirmar aunque venda. Marca el límite ético y además evita que el
modelo invente números.*

## Ganchos míos que funcionaron
*Lo más valioso del brief. Dos o tres, textuales, con el dato de cómo les fue.
Si todavía no tenés, dejalo vacío y volvé cuando tengas.*

## Mi llamada a la acción
*La acción concreta, con la palabra exacta.*
```

---

## Las dos secciones que hacen casi todo el trabajo

Si vas con poco tiempo, llená bien estas dos y dejá el resto a medias.

### «Qué le duele de verdad»

Es de donde sale el gancho. La trampa es escribir el problema en el idioma del que vende en
vez del que compra:

| El idioma del consultor | El idioma del cliente |
|---|---|
| Falta de digitalización | Le escriben a las 11 PM y contesta al otro día |
| Baja conversión de leads | Pidieron presupuesto y nunca volvieron a escribir |
| Ausencia de presencia online | Lo buscaron en Google y encontraron a otro |

La columna derecha produce ganchos. La izquierda produce folletos. Si lo que escribiste en
esa sección podría estar en la web de cualquier agencia, todavía no está listo.

### «Ganchos míos que funcionaron»

Dos o tres ejemplos textuales le enseñan al modelo tu registro mejor que cualquier
descripción. Y si les ponés el número al lado, mejor:

```markdown
## Ganchos míos que funcionaron
- "No necesitas una web. Necesitas saber qué te hace perder clientes."
  (retención 42 %, 11 comentarios con la keyword)
- "Te escriben a las 11 PM y contestas al otro día."
  (el de mejor alcance del mes)
```

**Si no tenés métricas, no inventes.** Poné los que te gustaron y anotá que son intuición.
Un brief honesto con tres ganchos reales sirve; uno con números inventados entrena al modelo
en una mentira.

> Escribí los ganchos **como aparecen en pantalla**. Si tus titulares van en mayúsculas,
> ponelos en mayúsculas acá. El modelo copia el formato de tus ejemplos antes que cualquier
> instrucción del prompt — es la señal más fuerte que le estás dando.

---

## Ejemplo lleno

Este es el brief detrás de las escenas de [`examples/`](../examples/). Sirve para ver el
nivel de concreción que hace falta — no para copiarlo.

```markdown
# Brief de marca

## Qué vendo
Sitios web simples (USD 80-500) y agentes de IA que atienden WhatsApp (USD 600-3000).
Entrada: un diagnóstico gratuito de 15 minutos.

## A quién le hablo
Profesionales que prestan servicios por su cuenta y necesitan más clientes: médicos,
kinesiólogos, abogados, contadores, terapeutas. Con consultorio o estudio propio,
sin equipo de marketing, atendiendo ellos mismos los mensajes.

## Qué ya sabe esa persona
Que "tendría que estar en internet". Ya se lo dijeron mil veces y le da culpa.
Lo que NO sabe es si una web le sirve para algo o si el problema es otro.

## Qué le duele de verdad
Le escriben por WhatsApp fuera de hora y contesta tarde. Cuando contesta, el paciente
ya sacó turno con otro. No sabe cuántos perdió porque nunca los contó.

## Cómo hablo
Castellano neutro, de tú. Directo, sin vueltas. Frases cortas. Cero jerga técnica:
nada de "stack", "funnel" ni "engagement". Hablo del negocio, no de la tecnología.

## Palabras que uso
Pacientes, clientes, turnos, consultorio, perder, recuperar, diagnóstico, claro, sin
compromiso.

## Palabras que no uso nunca
Sinergia, potenciar, disruptivo, solución integral, transformación digital, ecosistema.

## Promesas que no hago
No prometo cantidad de clientes ni plazos de resultados. No digo "garantizado".
No invento estadísticas del rubro.

## Ganchos míos que funcionaron
- "NO NECESITAS / UNA WEB / SINO SABER / QUÉ PIERDES"
- "TE ESCRIBEN / A LAS 11 PM / CONTESTAS / AL OTRO DÍA"

## Mi llamada a la acción
Que escriban una palabra por mensaje directo. Siempre una sola, en mayúsculas:
DIAGNÓSTICO, AGENDA.
```

---

## Qué esperar

El brief no escribe el video por vos. Lo que hace es subir el piso: el modelo deja de
producir genéricos y empieza a producir algo que al menos **suena a vos** y le habla a
alguien concreto.

La última decisión sigue siendo tuya. Mirá siempre los stills antes de renderizar entero, y
si el gancho no te haría frenar el pulgar a vos, no lo va a hacer frenar a nadie.

**Volvé al brief cada tanto.** Es el archivo más barato de mejorar del proyecto: cada gancho
que te funcione y agregues ahí mejora todos los videos que vengan después.
