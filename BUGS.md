# BUGS.md — Legend Travel

Auditoría estática de 109 archivos HTML. Fecha: 2026-07-05.
No se modificó ningún archivo del proyecto.

---

## 1. Errores de JavaScript

| # | Archivo | Línea | Descripción |
|---|---------|-------|-------------|
| JS-1 | `schema-block.html` | 3 | `getElementById("navMobile")` — el ID no existe en este snippet (archivo parcial sin estructura nav). Copiar/pegar del template completo dejó JS huérfano. |

---

## 2. Links y botones rotos

### 2A. Sistémico: footer logo `href="#"` en todas las subpáginas (104 páginas)

El footer de todas las subpáginas tiene `<a href="#" class="brand">` como logo. En una subpágina, `href="#"` hace scroll al top de la página actual en lugar de navegar a la home. Debería ser `href="/"`.

**Ejemplo representativo:** `africa/index.html:577`
**Afecta:** todas las subpáginas (104 archivos).

---

### 2B. Sistémico: footer "La agencia" linkea a secciones solo de la home (~102 subpáginas)

La columna "La agencia" del footer tiene anchors que solo existen en `index.html`. Desde cualquier subpágina, los cuatro links siguientes no hacen nada:

| Anchor | Link visible | Existe en home | Existe en subpáginas |
|--------|-------------|----------------|----------------------|
| `#diferenciales` | "Por qué Legend" | ✓ | ✗ |
| `#historia` | "Nuestra historia" | ✓ | ✗ |
| `#equipo` | "El equipo" | ✓ | ✗ |
| `#guias` | "Guías y consejos" | ✓ | ✗ (subpáginas tienen `#guia` sin 's') |

**Línea en ejemplo:** `asia/japon/index.html:543`
**Afecta:** ~102 subpáginas (todas excepto index.html y quienes-somos).
**Fix:** cambiar a `href="/#diferenciales"`, `href="/#historia"`, etc.

---

### 2C. Sistémico: footer `<h4><a href="#destinos">` roto en 86 páginas child

Las páginas hijo (ej. `asia/japon/`, `caribe/aruba/`, `europa/central/alemania/`) tienen en el footer `<h4><a href="#destinos">Destinos</a></h4>`, pero esas páginas no tienen ninguna sección con `id="destinos"`. El link no hace nada.

**Ejemplo:** `asia/japon/index.html:521`
**Afecta:** 86 páginas child (todas menos las ~20 páginas madre que sí tienen `#destinos`).

---

### 2D. Europa (28 páginas): sección de contacto sin `id="contacto"`

Todas las páginas de Europa (madres y children) tienen `<section class="sec px contact">` como sección de contacto, pero esa sección **no tiene** `id="contacto"`. El footer tiene dos links a `#contacto` que no funcionan:
- `<h4><a href="#contacto">Contacto</a></h4>`
- `<a href="#contacto">Contacto</a>` en "La agencia"

**Páginas afectadas (28):**
- `europa/central/index.html:285`
- `europa/central/alemania/index.html:278`
- `europa/central/belgica/index.html:278`
- `europa/central/croacia/index.html` (sin id="contacto")
- `europa/central/eslovenia/index.html`
- `europa/central/paises-bajos/index.html`
- `europa/central/suiza/index.html:278`
- `europa/del-este/index.html`
- `europa/del-este/austria/index.html`
- `europa/del-este/hungria/index.html`
- `europa/del-este/polonia/index.html`
- `europa/del-este/republica-checa/index.html`
- `europa/escandinavia/index.html`
- `europa/escandinavia/dinamarca/index.html`
- `europa/escandinavia/finlandia/index.html`
- `europa/escandinavia/islandia/index.html`
- `europa/escandinavia/noruega/index.html`
- `europa/escandinavia/suecia/index.html`
- `europa/islas-britanicas/index.html`
- `europa/islas-britanicas/escocia/index.html`
- `europa/islas-britanicas/gales/index.html`
- `europa/islas-britanicas/inglaterra/index.html`
- `europa/islas-britanicas/irlanda/index.html`
- `europa/sur-occidental/index.html`
- `europa/sur-occidental/espana/index.html:309`
- `europa/sur-occidental/francia/index.html:303`
- `europa/sur-occidental/grecia/index.html:271`
- `europa/sur-occidental/italia/index.html:303`
- `europa/sur-occidental/portugal/index.html:277`

**Fix:** agregar `id="contacto"` a `<section class="sec px contact"...>` en cada una.

---

### 2E. Footer `href="#financiacion"` roto en 14 páginas

Estas páginas tienen `href="#financiacion"` en el footer pero no tienen sección con `id="financiacion"`:

| Archivo | Línea |
|---------|-------|
| `blog/index.html` | 344 |
| `caribe/cancun-riviera-maya/index.html` | 316 |
| `caribe/republica-dominicana/index.html` | 512 |
| `caribe/republica-dominicana/miches/index.html` | 493 |
| `caribe/republica-dominicana/samana/index.html` | 492 |
| `europa/central/index.html` | 318 |
| `europa/del-este/index.html` | 479 |
| `europa/escandinavia/index.html` | 466 |
| `europa/index.html` | 382 |
| `europa/islas-britanicas/index.html` | 369 |
| `europa/sur-occidental/index.html` | 320 |
| `financiacion/index.html` | 456 |
| `quienes-somos/index.html` | 497 |
| `usa/costa-oeste/index.html` | 497 |

---

### 2F. Footer `href="#testimonios"` roto en 3 páginas

| Archivo | Línea | Detalle |
|---------|-------|---------|
| `index.html` | 932 | La home no tiene `id="testimonios"` (su sección de testimonios usa un id diferente) |
| `blog/index.html` | 344 | La página de blog no tiene sección de testimonios |
| `financiacion/index.html` | 456 | La página de financiación no tiene sección de testimonios |

---

## 3. Referencias a IDs que no existen en el HTML

*(Además de los casos ya listados en la sección 2)*

| # | Archivo | Línea | ID referenciado | Descripción |
|---|---------|-------|-----------------|-------------|
| ID-1 | `schema-block.html` | 3 | `navMobile` | Ver JS-1 — snippet parcial |
| ID-2 | `index.html` | 932 | `#testimonios` | Ver 2F — home no tiene esta sección |
| ID-3 | `europa/central/alemania/index.html` | 311/314 | `#contacto` | Ver 2D |

---

## 4. Errores de lógica

| # | Descripción | Impacto |
|---|-------------|---------|
| L-1 | **Footer usa anchors relativos para secciones de la home.** Los links `#diferenciales`, `#historia`, `#equipo`, `#guias` del footer solo funcionan cuando el usuario ya está en `index.html`. Desde cualquier subpágina, los anchors resuelven al ID en la página actual (que no existe) → el click no hace nada. El diseño asume que el usuario navega siempre desde la home, pero en la práctica usuarios pueden llegar directo a subpáginas. | Alto — links muertos en toda la navegación del footer |
| L-2 | **`href="#"` en el logo del footer.** El patrón estándar de `<a href="#" class="brand">` hace scroll-to-top. En la home es aceptable; en subpáginas, el logo debería llevar a la home. El logo es un elemento de orientación importante. | Medio — el usuario no puede ir a la home desde el footer de ninguna subpágina |
| L-3 | **Europa: sección `.contact` sin ID.** El template de Europa no asignó `id="contacto"` a la sección de cierre. Esto no solo rompe el footer sino que además impide el smooth-scroll si en alguna versión futura se agrega "Contacto" al navbar. | Medio — 28 páginas con link de cierre roto |
| L-4 | **Footer h4 `#destinos` linkea a sección que no existe en páginas hijo.** La navegación del footer no está contextualizada: usa `#destinos` (sección de "ver todos los destinos") que solo existe en páginas madre o en la home, no en páginas de destino individual. | Bajo — el h4 del footer como link es decorativo pero confunde cuando no hace nada |

---

## Resumen de archivos revisados (109)

```
africa/index.html
africa/seychelles/index.html
africa/zanzibar/index.html
argentina/bariloche/index.html
argentina/cataratas-iguazu/index.html
argentina/el-calafate/index.html
argentina/index.html
argentina/mendoza/index.html
argentina/salta-jujuy/index.html
argentina/ushuaia/index.html
asia/china/index.html
asia/corea/index.html
asia/dubai/index.html
asia/filipinas/index.html
asia/index.html
asia/india/index.html
asia/japon/index.html
asia/malasia/index.html
asia/maldivas/index.html
asia/singapur/index.html
asia/tailandia/index.html
asia/vietnam/index.html
blog/index.html
brasil/index.html
caribe/aruba/index.html
caribe/bahamas/index.html
caribe/cancun-riviera-maya/index.html
caribe/cuba/index.html
caribe/curazao/index.html
caribe/index.html
caribe/jamaica/index.html
caribe/republica-dominicana/bayahibe/index.html
caribe/republica-dominicana/index.html
caribe/republica-dominicana/miches/index.html
caribe/republica-dominicana/punta-cana/index.html
caribe/republica-dominicana/samana/index.html
caribe/saint-maarten/index.html
caribe/san-andres/index.html
caribe/turks-caicos/index.html
cruceros/index.html
disney/index.html
europa/central/alemania/index.html
europa/central/belgica/index.html
europa/central/croacia/index.html
europa/central/eslovenia/index.html
europa/central/index.html
europa/central/paises-bajos/index.html
europa/central/suiza/index.html
europa/del-este/austria/index.html
europa/del-este/hungria/index.html
europa/del-este/index.html
europa/del-este/polonia/index.html
europa/del-este/republica-checa/index.html
europa/escandinavia/dinamarca/index.html
europa/escandinavia/finlandia/index.html
europa/escandinavia/index.html
europa/escandinavia/islandia/index.html
europa/escandinavia/noruega/index.html
europa/escandinavia/suecia/index.html
europa/index.html
europa/islas-britanicas/escocia/index.html
europa/islas-britanicas/gales/index.html
europa/islas-britanicas/index.html
europa/islas-britanicas/inglaterra/index.html
europa/islas-britanicas/irlanda/index.html
europa/sur-occidental/espana/index.html
europa/sur-occidental/francia/index.html
europa/sur-occidental/grecia/index.html
europa/sur-occidental/index.html
europa/sur-occidental/italia/index.html
europa/sur-occidental/portugal/index.html
financiacion/index.html
gtm-noscript-body.html
head-block.html
index.html
latinoamerica/chile/index.html
latinoamerica/colombia/index.html
latinoamerica/costa-rica/index.html
latinoamerica/guatemala/index.html
latinoamerica/index.html
latinoamerica/panama/index.html
latinoamerica/peru/index.html
lunas-de-miel/index.html
medio-oriente/dubai-emiratos/index.html
medio-oriente/index.html
medio-oriente/jordania/index.html
medio-oriente/turquia/index.html
oceania/australia/index.html
oceania/bora-bora/index.html
oceania/index.html
oceania/nueva-zelanda/index.html
quienes-somos/index.html
schema-block.html
usa/costa-oeste/index.html
usa/costa-oeste/las-vegas/index.html
usa/costa-oeste/los-angeles/index.html
usa/costa-oeste/san-francisco/index.html
usa/disney-universal/index.html
usa/hawaii/index.html
usa/index.html
usa/miami/index.html
usa/nueva-york/index.html
viajes-a-medida/index.html
viajes-deportivos/formula-1/index.html
viajes-deportivos/grand-slams-tenis/index.html
viajes-deportivos/index.html
viajes-deportivos/mundial-futbol/index.html
viajes-deportivos/rugby/index.html
```

*(Se excluyeron archivos legacy de redirección: brasil/buzios.html, brasil/florianopolis.html, brasil/maceio.html, brasil/maragogi.html, brasil/natal-pipa.html, brasil/porto-de-galinhas.html, brasil/porto-seguro.html, brasil/recife.html, brasil/rio.html, brasil/salvador-de-bahia.html, caribe/aruba.html, caribe/cancun.html, caribe/punta-cana.html, caribe/riviera-maya.html, e index-backup.html)*
