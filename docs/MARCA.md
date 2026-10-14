# MARCA.md — poner tu marca

Todos los colores y tipografías viven en **un solo archivo**: `themes/<nombre>.json`. Ese
archivo lo leen las dos mitades del proyecto —el Python que genera subtítulos y gráficos, y
el HTML que anima— así que no hay nada que sincronizar a mano.

```
themes/mi-marca.json
        │
        ├──► config/brand.py ──► FFmpeg · libass · Pillow
        └──► timeline.json ──► text_overlay.html (variables CSS)
```

## En dos minutos

```bash
cp themes/neutral.json themes/mi-marca.json
# editá los colores
```

Y después, una de estas dos:

```bash
# A) por defecto para todo, incluido el pipeline de video largo
echo "REEL_BRAND=mi-marca" >> .env

# B) por escena, agregando un campo al JSON
#    { "name": "...", "brand": "mi-marca", ... }
```

Comprobá el resultado sin renderizar un video entero:

```bash
python -m motion.compose_text examples/agente-contenido.json --stills 3,12,22
```

Esa escena usa los ocho tipos de beat, así que en tres capturas ves casi toda tu paleta
aplicada.

---

## Qué hace cada color

El tema tiene nueve colores. Los nombres son **históricos**, no descriptivos: `navy` no tiene
que ser azul y `lime` no tiene que ser verde. Lo que importa es el papel que cumple cada uno.

```json
{
  "palette": {
    "navy":    "#0B1220",   // fondo principal. El color que más se ve.
    "surface": "#161F2E",   // superficies elevadas (marcos, teléfonos)
    "deep":    "#0E1724",   // variante más oscura, solo en el pipeline híbrido
    "white":   "#F7F9FC",   // el texto. Tiene que contrastar fuerte con `navy`.
    "muted":   "#9AA6B8",   // texto secundario (los campos `sub`)
    "dot":     "#22304A",   // bordes apagados y la retícula del fondo
    "cyan":    "#38BDF8",   // ACENTO. Las pastillas `chip` y los detalles.
    "lime":    "#A3E635",   // RESALTADO. Lo más importante de cada pantalla.
    "orange":  "#FB923C"    // ALERTA. Sellos, tachados, la última línea del cierre.
  }
}
```

**Las tres que definen el carácter del video son `cyan`, `lime` y `orange`.** Las otras seis
son la escenografía.

### La regla que no podés romper

`cyan`, `lime` y `orange` se usan **como fondo con texto `navy` encima** (en las pastillas
`chip`, los sellos, el `cta` y los checks). Si elegís un acento oscuro, ese texto se vuelve
ilegible.

> Los tres acentos tienen que ser **claros**. Si tu marca es azul oscuro, no lo pongas en
> `cyan`: ponelo en `navy` y buscá una versión luminosa para el acento.

El resto del contraste importa menos, pero apuntá a que `white` sobre `navy` supere 7:1
(cualquier verificador de contraste en línea te lo dice). El texto de un Reel se lee en un
teléfono, a veces al sol, en movimiento.

---

## El tema claro

Cada tema trae un bloque `light` con lo que cambia cuando una escena lleva `"theme": "light"`:

```json
{
  "light": {
    "bg":         "#FAFAFA",   // el fondo pasa a claro
    "muted":      "#4B5563",   // el texto secundario se oscurece
    "cyan-ink":   "#0369A1",   // versiones OSCURAS de los acentos,
    "lime-ink":   "#4D7C0F",   // para cuando el acento es TEXTO
    "orange-ink": "#C2410C"    // sobre fondo claro
  }
}
```

La distinción entre `lime` y `lime-ink` es la clave de todo el sistema de temas:

- **`lime`** se usa como **fondo** (la pastilla del `cta`). No cambia entre temas: lleva texto
  oscuro encima y eso funciona igual sobre fondo blanco o negro.
- **`lime-ink`** se usa como **texto**. Sí cambia: un lima brillante es perfectamente legible
  sobre navy e ilegible sobre blanco.

En el tema oscuro, `lime-ink` es simplemente `lime`. En el claro, es la variante oscura que
definís vos. **Elegí los `-ink` apuntando a 4,5:1 contra tu `bg` claro.**

---

## Adorno de la tarjeta de cierre

```json
{ "end_ornament": "constellation" }
```

Opcional. Dibuja la constelación animada arriba del logotipo en el bloque `end`. Es parte de
la identidad de Sintergia, así que solo la trae `themes/sintergia.json`; sin este campo, el
cierre sale sin adorno.

---

## Tipografías

```json
{
  "fonts": {
    "display": "InterTight-Black.woff",      // titulares, números — muy pesada
    "mono": "JetBrainsMono-Bold.woff",       // pastillas y texto secundario
    "serif": "Fraunces-Medium.woff",         // solo el logotipo del cierre
    "display_family": "Inter Tight Black"    // el nombre que ve libass
  }
}
```

Para cambiarlas:

1. Poné los `.woff` en `fonts/`.
2. Actualizá los nombres de archivo en tu tema.
3. **Ajustá `display_family`**: tiene que ser el nombre de familia *interno* de la fuente, no
   el del archivo. Es lo que usa libass para los subtítulos quemados del pipeline de video
   largo; si no coincide, cae en una fuente por defecto sin avisar.

> ⚠️ Revisá la licencia antes de agregar una tipografía al repositorio. Las tres que vienen
> son SIL OFL, que permite redistribuirlas; muchas comerciales no (ver [NOTICE](../NOTICE)).
>
> Y si **reemplazás** una: borrá su `fonts/OFL-*.txt` y poné el archivo de licencia de la
> nueva. La OFL exige que el texto acompañe a la fuente, así que dejar la licencia vieja al
> lado de una fuente distinta es peor que no tener ninguna: afirma algo que no es cierto.

### Si cambiás la de titulares, revisá los límites de caracteres

Los máximos de [BEATS.md](BEATS.md) están medidos **contra Inter Tight Black**. Una fuente
más ancha hace que el texto se desborde antes, y una más angosta te deja escribir más.

Para volver a medirlos con tu tipografía, lo práctico es escribir una escena con el texto más
largo que pienses usar en cada campo y renderizar stills:

```bash
python -m motion.compose_text motion/scenes/prueba-tipografia.json --stills 2
```

Si algo se sale, ya sabés que ese campo tiene menos margen del que dice la tabla.

---

## Cosas que el tema **no** controla

Esto está en `config/brand.py` a propósito: no son decisiones de marca sino restricciones de
las plataformas y de la legibilidad. Cambiarlas rompe cosas.

| | valor | por qué |
|---|---|---|
| `SAFE_TOP` / `SAFE_BOTTOM` | 220 / 440 px | Lo que tapa la interfaz de Reels y TikTok. |
| `CAPTION_MARGIN_V` | 540 px | Subtítulos arriba de la zona tapada. Hay un `assert` que impide bajarlo de `SAFE_BOTTOM`. |
| `LOUDNESS_LUFS` | −14 | Estándar de las plataformas móviles. |
| `OUTPUT_WIDTH` × `HEIGHT` | 1080 × 1920 | Las posiciones de la plantilla están calculadas para este lienzo. |

Y las **posiciones** de cada elemento están escritas en el HTML, no en el tema. Mover cosas
es rediseñar la plantilla, no cambiar de marca. Si llegás a ese punto, abrí
`motion/text_overlay.html` directamente en un navegador: la paleta del `:root` es el tema
neutro y la plantilla funciona suelta, sin pasar por el pipeline.

---

## Comprobar que no te olvidaste de nada

```bash
# ¿se carga el tema y con qué colores?
python -c "
from config.brand import THEME, NAVY, CYAN, LIME
print(THEME['name'], NAVY, CYAN, LIME)"
```

Si el nombre del tema no existe, el error te lista los disponibles. Y si ves `neutral` cuando
esperabas el tuyo, es que `REEL_BRAND` no está llegando: revisá que esté en `.env` y no solo
exportado en otra terminal.
