# Escenas de ejemplo

Estas son escenas **reales**, publicadas en Instagram por Sintergia Studio. No son demos
armadas para el repositorio: son el material con el que se desarrolló la herramienta, con
sus decisiones y sus compromisos a la vista.

Para renderizar cualquiera:

```bash
python -m motion.compose_text examples/diagnostico-gratis.json --stills 3,12,22   # revisar
python -m motion.compose_text examples/diagnostico-gratis.json                    # video completo
```

> **El código es libre; la marca no.** `Sintergia`, el usuario `@sintergiastudio` y los
> textos comerciales de estas escenas son de su autor (ver [NOTICE](../NOTICE)). Usalas para
> entender el formato, no las publiques tal cual. Para tu propia marca: [docs/MARCA.md](../docs/MARCA.md).

---

## Video animado de texto

Sin video de origen, sin voz, sin clave de API. Es el pipeline por el que conviene empezar.

| archivo | dur. | tema | beats |
|---|--:|---|---|
| [`primer-video.json`](primer-video.json) | 29,6 s | oscuro · **neutral, CC0** | `hook → tags → steps → end` |
| [`diagnostico-gratis-reel-test.json`](diagnostico-gratis-reel-test.json) | 29,6 s | oscuro | `hook → tags → steps → end` |
| [`diagnostico-gratis.json`](diagnostico-gratis.json) | 44 s | oscuro | `hook → tasks → steps → list → tags → swap → end` |
| [`diagnostico-gratis-light.json`](diagnostico-gratis-light.json) | 44 s | **claro** | igual que el anterior |
| [`ia-hogar.json`](ia-hogar.json) | 44 s | oscuro | igual |
| [`agente-contenido.json`](agente-contenido.json) | 49 s | oscuro | los 8 tipos de beat |

**Por dónde empezar, según qué quieras ver:**

- **`primer-video.json`** — **la única libre de copiar** (CC0) y sin marca. Es la que copia
  `reel init`. Si vas a partir de una escena para tu video, partí de esta.
- **`diagnostico-gratis-reel-test.json`** — el más corto y el más fácil de leer. Cuatro beats,
  una idea. Tiene la misma estructura que `primer-video.json`, con textos reales.
- **`agente-contenido.json`** — usa **los ocho tipos de beat**. Sirve de catálogo visual:
  renderizá stills a lo largo de los 49 s y vas a ver cada tipo en acción.
- **`diagnostico-gratis.json` vs `diagnostico-gratis-light.json`** — el **mismo contenido** en
  tema oscuro y claro. La única diferencia en el JSON es `"theme": "light"`. Útil para
  entender qué cambia un tema y qué no (las pastillas de color sólido no cambian: ya llevan
  texto oscuro sobre fondo de color, y eso funciona con cualquier fondo de página).

> Nota honesta sobre `diagnostico-gratis-reel-test.json`: salió de reescribir la versión
> larga para que entrara en 30 s, y en el proceso aparecieron los dos desbordes de texto que
> hoy están documentados en [BEATS.md](../docs/BEATS.md) y los detecta el validador.
> El límite de caracteres no es teoría: viene de acá.

## Pipeline híbrido (video + animación superpuesta)

| archivo | dur. | notas |
|---|--:|---|
| [`seo-cuentas.json`](seo-cuentas.json) | 40,1 s | Única escena de este pipeline. |

Formato **distinto** al de los otros: no tiene `beats` sino `source`, `split_windows`, `zoom`
y `face`. [BEATS.md](../docs/BEATS.md) no la cubre y el validador la saltea a propósito.

No la vas a poder renderizar: necesita `largos/01/seo.mp4`, que no se versiona (son cientos
de megas y no es material redistribuible). Está acá como **referencia del formato**, para
quien quiera adaptar el pipeline híbrido a su propio video.

---

## Validarlas

Todas pasan el validador. Es una buena forma de comprobar que tu instalación está sana:

```bash
for f in examples/*.json; do python scripts/validate_scene.py "$f"; done
```
