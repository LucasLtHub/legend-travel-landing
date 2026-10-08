#!/usr/bin/env python3
"""
build-paquetes.py
Genera TODA la presencia de paquetes del sitio a partir de data/paquetes.json.

Escribe en tres lugares, y en ningun otro:

  1. paquetes/index.html   → entre <!-- PAQUETES:START --> y <!-- PAQUETES:END -->
     Chips de filtro + la grilla de cards. Cada card linkea a su detalle.

  2. paquetes/<id>/index.html
     Una pagina de detalle por paquete activo, armada con el molde
     data/_template-detalle.html (la ESTRUCTURA del detalle se toca solo
     ahi; vive en data/ porque no se publica). El DISENO —del detalle y
     de las cards— vive en assets/design.css, seccion "paquetes".
     Los detalles de paquetes que dejan de estar activos se BORRAN: nunca
     queda una pagina huerfana publicable.

  3. <region>/index.html   → entre <!-- PAQUETES-REGION:START/END -->
     Dentro de cada madre, un apartado con SOLO las salidas de esa region.
     Los marcadores se insertan solos la primera vez.

Reglas que no se negocian:
- Los paquetes viven como DATOS. El HTML se genera. Nunca editar a mano.
- activo:false O vigencia pasada  →  ni card, ni detalle, ni sitemap.
- Si un campo no esta en el JSON, el modulo no se dibuja. No se inventa nada.
- ref y operador son INTERNOS: no salen nunca al HTML.

Uso: python build-paquetes.py
"""
import sys, json, html, re, datetime, urllib.parse, shutil
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "paquetes.json"
TEMPLATE = ROOT / "data" / "_template-detalle.html"
PAGE = ROOT / "paquetes" / "index.html"
PAQDIR = ROOT / "paquetes"
IMGDIR = ROOT / "img" / "paquetes"
PLACEHOLDER = "img/paquetes/placeholder.svg"
DOMINIO = "https://www.legendtravel.com.ar"

WA_NUMERO = "5491176554362"
WA_TEXTO = "Hola Legend Travel, quiero información sobre el paquete: {titulo}"

START = "<!-- PAQUETES:START -->"
END = "<!-- PAQUETES:END -->"
# Titulos propios del apartado "Salidas destacadas" (AR5, AF4); el resto usa el generico.
REGIONES_TITULO = {
    "argentina": "Salidas por Argentina <em>listas para reservar</em>.",
    "africa": "Salidas a &Aacute;frica con <em>itinerarios pensados y fechas fijas</em>.",
}
R_START = "<!-- PAQUETES-REGION:START -->"
R_END = "<!-- PAQUETES-REGION:END -->"

# Obligatorios de verdad: sin esto la card no se puede dibujar.
OBLIGATORIOS = ["id", "titulo", "region", "destinos", "resumen",
                "precio_desde", "salida", "vigencia", "noches", "incluye", "imagen"]
# Todo lo demas es opcional y su modulo se omite si viene vacio:
#   regimen, tarifas, itinerario, hoteles, no_incluye, condiciones,
#   nota_impuestos, motivo_inactivo, operador, ref, destacado

REGIONES = {
    "caribe": "Caribe", "brasil": "Brasil", "europa": "Europa", "usa": "EE. UU.",
    "argentina": "Argentina", "asia": "Asia", "africa": "África", "oceania": "Oceanía",
    "latinoamerica": "Latinoamérica", "medio-oriente": "Medio Oriente",
    "cruceros": "Cruceros", "disney": "Disney", "lunas-de-miel": "Lunas de miel",
    "viajes-deportivos": "Viajes deportivos", "quinceaneras": "Quinceañeras",
}

REGIONES_FRASE = {
    "caribe": "al Caribe", "brasil": "a Brasil", "europa": "a Europa",
    "usa": "a Estados Unidos", "argentina": "por Argentina", "asia": "a Asia",
    "africa": "a África", "oceania": "a Oceanía", "latinoamerica": "a Latinoamérica",
    "medio-oriente": "a Medio Oriente", "cruceros": "en crucero",
    "disney": "a Disney", "lunas-de-miel": "de luna de miel",
    "viajes-deportivos": "a eventos deportivos", "quinceaneras": "de quinceañera",
}

# En que carpeta madre se muestran las salidas de cada region.
# quinceaneras -> disney/ : los viajes de XV viven ahi.
REGION_MADRE = {
    "argentina": "argentina", "caribe": "caribe", "europa": "europa",
    "asia": "asia", "africa": "africa", "medio-oriente": "medio-oriente",
    "cruceros": "cruceros", "quinceaneras": "disney", "disney": "disney",
    "usa": "usa", "brasil": "brasil", "oceania": "oceania",
    "latinoamerica": "latinoamerica", "lunas-de-miel": "lunas-de-miel",
    "viajes-deportivos": "viajes-deportivos",
}

# Titulo de cada bloque de la grilla. Descriptivos a proposito: no afirman
# nada que pueda quedar falso cuando cambien los paquetes de adentro.
REGIONES_TITULO = {
    "caribe": "Escapadas al Caribe",
    "cruceros": "Salidas en crucero",
    "europa": "Descubr&iacute; el continente europeo",
    "argentina": "Descubr&iacute; Argentina",
    "asia": "Grandes viajes por Asia",
    "africa": "Descubr&iacute; &Aacute;frica",
    "quinceaneras": "Viajes de Quincea&ntilde;eras",
    "brasil": "Descubr&iacute; Brasil",
    "usa": "Descubr&iacute; Estados Unidos",
    "medio-oriente": "Descubr&iacute; Medio Oriente",
    "latinoamerica": "Descubr&iacute; Latinoam&eacute;rica",
    "oceania": "Descubr&iacute; Ocean&iacute;a",
    "disney": "Disney y Orlando",
    "lunas-de-miel": "Lunas de miel",
    "viajes-deportivos": "Viajes deportivos",
}

# Orden de los bloques en /paquetes/. Editar aca para reordenar la pagina.
# Lo que no figure en la lista va al final, alfabetico.
ORDEN_REGIONES = ["caribe", "cruceros", "europa", "argentina", "asia", "africa",
                  "quinceaneras", "brasil", "usa", "medio-oriente",
                  "latinoamerica", "oceania", "disney", "lunas-de-miel",
                  "viajes-deportivos"]

MAX_REGION_CARDS = 3      # en la madre, hasta 3 salidas; el resto en /paquetes/
MAX_RELACIONADOS = 3      # al pie del detalle
ORG_ID = DOMINIO + "/#organization"   # la TravelAgency que ya declara el sitio
LLMS = ROOT / "llms.txt"
LLMS_START = "<!-- PAQUETES:START -->"
LLMS_END = "<!-- PAQUETES:END -->"

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
         "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
         "noviembre": 11, "diciembre": 12}

MAX_INCLUYE_CARD = 4      # la card muestra 4 items; el resto vive en el detalle
MAX_DESTINOS_CARD = 3

# --- iconos ---
IC_CAL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 11h18"/></svg>'
IC_CAMA = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M3 18v-6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v6M3 18h18M3 18v2M21 18v2M6 10V7a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v3"/></svg>'
IC_PLATO = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M4 20h16M6 16h12M7 16a5 5 0 0 1 10 0M12 4v3M10.5 5.5h3"/></svg>'
IC_CHECK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"><path d="m4 12 5.5 5.5L20 7"/></svg>'
IC_CRUZ = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M18 6 6 18M6 6l12 12"/></svg>'
IC_RELOJ = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/></svg>'
IC_ESTRELLA = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="m12 2 2.9 6.3 6.9.8-5.1 4.7 1.4 6.8L12 17.3 5.9 20.6l1.4-6.8L2.2 9.1l6.9-.8z"/></svg>'
IC_WA = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm5.5 14.2c-.2.7-1.3 1.3-1.9 1.4-.5.1-1.1.1-1.8-.1a16 16 0 0 1-6.9-6.1c-.8-1.3-1.2-2.4-1.1-3 0-.6.5-1.6 1.1-1.9.3-.2.7-.2 1-.1.2 0 .5 0 .7.6l.9 2.1c.1.2.1.5 0 .7l-.5.8c-.2.2-.3.4-.1.7.5.9 1.2 1.7 2 2.4.8.7 1.6 1.2 2.6 1.6.3.1.5.1.7-.1l.7-.7c.2-.3.4-.3.7-.2l2.1 1c.5.3.6.4.6.8Z"/></svg>'
IC_BRUJULA = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5.5-5.5 2 2-5.5z"/></svg>'
IC_FLECHA = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14m-6-6 6 6-6 6"/></svg>'
IC_HOTEL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M3 21h18M5 21V5a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v16M9 8h1m4 0h1M9 12h1m4 0h1M9 16h6v5H9z"/></svg>'
IC_MAS = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14"/><path class="v" d="M12 5v14"/></svg>'

# ============================================================
# CSS de las cards — la FUENTE UNICA es assets/design.css (seccion "paquetes").
# Antes se inyectaba un <style> en la pagina y en cada madre; ahora solo queda
# este comentario en el HTML generado, para que quien lo lea sepa donde mirar.
# ============================================================
CARD_CSS = ("<!-- El diseno de las cards (.pk-*, .pkc) vive en assets/design.css, "
            "seccion \"paquetes\". Aca no se inyecta CSS: una corrida no puede pisarlo. -->")

PLACEHOLDER_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" width="800" height="500" role="img" aria-label="Imagen no disponible">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#491417"/><stop offset="100%" stop-color="#0E232D"/>
  </linearGradient></defs>
  <rect width="800" height="500" fill="url(#g)"/>
  <g fill="none" stroke="#F2B33D" stroke-width="3" opacity=".65"
     transform="translate(400 235) scale(2.6) translate(-12 -12)">
    <circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5.5-5.5 2 2-5.5z"/>
  </g>
  <text x="400" y="330" text-anchor="middle" font-family="Inter,Segoe UI,sans-serif"
        font-size="20" letter-spacing="5" fill="#F8F8F8" opacity=".55">LEGEND TRAVEL</text>
</svg>
'''


# ============================================================
# Helpers
# ============================================================
def parse_vigencia(v):
    try:
        return datetime.date.fromisoformat(str(v).strip())
    except (ValueError, TypeError):
        return None


def parse_salida(s):
    """
    Primera fecha de salida, para ordenar. Acepta lo que mandan los operadores:
      "12 de noviembre 2026"                      -> 2026-11-12
      "5 de marzo 2027 - Ethiopian ET507"         -> 2027-03-05  (ignora la cola)
      "Septiembre 2027 - desde Buenos Aires"      -> 2027-09-01  (sin dia -> dia 1)
      "Salidas del 16/09 al 30/12/2026"           -> 2026-09-16  (la PRIMERA)
    None si no hay fecha reconocible (ej. "enero-febrero de 2027 y 2028"):
    el que llama ordena por vigencia.
    """
    if not s:
        return None
    t = str(s).strip().lower()

    # Fechas con barra: gana la que aparece PRIMERO en el texto, aunque el
    # anio solo figure al final del rango.
    m = re.search(r'\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{4}))?\b', t)
    if m:
        d, mo, y = m.group(1), m.group(2), m.group(3)
        if not y:
            ym = re.search(r'\b(20\d{2})\b', t)
            y = ym.group(1) if ym else None
        if y:
            try:
                return datetime.date(int(y), int(mo), int(d))
            except ValueError:
                return None

    m = re.search(r'(?:(\d{1,2})\s*(?:de\s+)?)?([a-záéíóú]+)\s*(?:de\s+)?(\d{4})', t)
    if m:
        dia, mes, anio = m.group(1), m.group(2), m.group(3)
        if mes in MESES:
            try:
                return datetime.date(int(anio), MESES[mes], int(dia) if dia else 1)
            except ValueError:
                return None
    return None


def fmt_precio(n):
    """1741290 -> '1.741.290' (formato argentino)."""
    try:
        v = float(n)
    except (TypeError, ValueError):
        return html.escape(str(n))
    if v == int(v):
        return "{:,}".format(int(v)).replace(",", ".")
    return "{:,.2f}".format(v).replace(",", "~").replace(".", ",").replace("~", ".")


def fmt_fecha_ar(d):
    return d.strftime("%d/%m/%Y")


def es_url(x):
    return str(x).lower().startswith(("http://", "https://", "//"))


def wa_link(titulo):
    txt_ = WA_TEXTO.format(titulo=titulo)
    return "https://wa.me/{}?text={}".format(WA_NUMERO, urllib.parse.quote(txt_, safe=''))


def e(x):
    return html.escape(str(x), quote=True)


def lista(p, campo):
    v = p.get(campo) or []
    return [x for x in v if str(x).strip()] if isinstance(v, list) else []


def txt(p, campo):
    return str(p.get(campo) or "").strip()


def noches_txt(n):
    return "{} {}".format(n, "noche" if str(n) == "1" else "noches")


def salida_corta(s):
    """"5 de marzo 2027 - Ethiopian ET507" -> "5 de marzo 2027" (para metas)."""
    s = str(s or "").strip()
    for corte in (" \u2014 ", " - ", " \u00b7 ", " ("):
        if corte in s:
            s = s.split(corte)[0].strip()
    return s.rstrip(" .,")


def titulo_tag(titulo):
    """
    "<Titulo> desde Buenos Aires | Legend Travel", y si pasa de ~65 caracteres
    cae a la version corta. No se recorta el titulo del paquete: mutilarlo es
    peor que un title largo.
    """
    largo = "{} desde Buenos Aires | Legend Travel".format(titulo)
    return largo if len(largo) <= 65 else "{} | Legend Travel".format(titulo)


# Palabras que no pueden quedar al final de una frase recortada.
COLGADAS = {"el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del",
            "y", "e", "o", "u", "en", "con", "sin", "por", "para", "a", "al",
            "que", "su", "sus", "mas", "m\u00e1s", "entre", "sobre", "desde", "hasta"}


def recortar(texto, limite):
    """
    Recorta a `limite` cortando en la ultima coma o punto si hay uno razonable;
    si no, en el ultimo espacio, y descarta las palabras funcionales que queden
    colgando al final ("...Capri, el" -> "...Capri").
    """
    if len(texto) <= limite:
        return texto
    trozo = texto[:limite]
    corte = max(trozo.rfind(","), trozo.rfind(";"), trozo.rfind("."))
    if corte >= limite * 0.6:
        trozo = trozo[:corte]
    else:
        trozo = trozo.rsplit(" ", 1)[0]
    palabras = trozo.rstrip(" .,;:").split(" ")
    while len(palabras) > 1 and palabras[-1].lower().strip(",.;:") in COLGADAS:
        palabras.pop()
    return " ".join(palabras).rstrip(" .,;:")


def meta_desc(p, limite=158):
    """
    Descripcion armada SOLO con datos del JSON: salida, duracion, resumen,
    precio y CTA. Si no entra todo, lo primero que se recorta es el resumen.
    """
    pd = p["precio_desde"]
    sal = salida_corta(p["salida"])
    # Varios paquetes traen "Salidas del ... al ...": no anteponer "Salida".
    cabeza = ("{}. {}." if sal.lower().startswith("salida")
              else "Salida {}. {}.").format(sal, noches_txt(p["noches"]))
    cola = "Desde {} {}. Consult\u00e1 por WhatsApp.".format(
        pd.get("moneda", ""), fmt_precio(pd.get("valor")))
    hueco = limite - len(cabeza) - len(cola) - 2
    resumen = txt(p, "resumen")
    if resumen and hueco >= 45:
        return "{} {}. {}".format(cabeza, recortar(resumen.rstrip(" ."), hueco - 1), cola)
    return "{} {}".format(cabeza, cola)


def reemplazar_bloque(texto, ini, fin, bloque):
    return re.sub(re.escape(ini) + r".*?" + re.escape(fin),
                  lambda _: bloque, texto, count=1, flags=re.S)


# ============================================================
# Render — CARD
# ============================================================
def render_card(p, vig_date):
    badge = ('\n        <span class="pk-badge">{}Destacado</span>'.format(IC_ESTRELLA)
             if p.get("destacado") else "")

    dests = lista(p, "destinos")
    kicker = " &middot; ".join(e(d) for d in dests[:MAX_DESTINOS_CARD])
    if len(dests) > MAX_DESTINOS_CARD:
        kicker += " &middot; +{}".format(len(dests) - MAX_DESTINOS_CARD)

    metas = ['            <span>{}{}</span>'.format(IC_CAL, e(p["salida"])),
             '            <span>{}{}</span>'.format(IC_CAMA, e(noches_txt(p["noches"])))]
    if txt(p, "regimen"):
        metas.append('            <span>{}{}</span>'.format(IC_PLATO, e(txt(p, "regimen"))))

    inc = lista(p, "incluye")
    inc_html = "\n".join('          <li>{}{}</li>'.format(IC_CHECK, e(i))
                         for i in inc[:MAX_INCLUYE_CARD])
    mas = ('\n          <p class="pk-mas">+{} &#237;tems m&#225;s en el detalle</p>'
           .format(len(inc) - MAX_INCLUYE_CARD) if len(inc) > MAX_INCLUYE_CARD else "")

    pd = p["precio_desde"]
    pnota = str(pd.get("nota") or "").strip()
    pnota_html = ('\n            <p class="pk-pnota">{}</p>'.format(e(pnota)) if pnota else "")

    return '''      <article class="pk-card" data-r="{region}">
        <a class="pk-stretch" href="paquetes/{id}/" aria-label="Ver detalle: {titulo}"></a>
        <div class="pk-media">
          <img src="{imagen}" alt="{alt}" loading="lazy">{badge}
        </div>
        <div class="pk-body">
          <p class="pk-dest">{kicker}</p>
          <h3 class="pk-t">{titulo}</h3>
          <p class="pk-resumen">{resumen}</p>
          <div class="pk-meta">
{metas}
          </div>
          <ul class="pk-inc">
{incluye}
          </ul>{mas}
          <div class="pk-foot">
            <div class="pk-price"><span class="lbl">Desde</span><span class="cur">{moneda}</span><span class="amt">{precio}</span></div>{pnota}
            <div class="pk-acts">
              <a class="pk-cta" href="{wa}" target="_blank" rel="noopener noreferrer">{ic_wa}Consultar</a>
              <span class="pk-ver">Ver detalle{ic_fl}</span>
            </div>
          </div>
        </div>
      </article>'''.format(
        region=e(p["region"]), id=e(p["id"]), imagen=e(p["imagen"]),
        alt=e(dests[0] if dests else p["titulo"]), badge=badge,
        kicker=kicker, titulo=e(p["titulo"]), resumen=e(txt(p, "resumen")),
        metas="\n".join(metas), incluye=inc_html, mas=mas,
        moneda=e(pd.get("moneda", "")), precio=fmt_precio(pd.get("valor")),
        pnota=pnota_html, wa=e(wa_link(p["titulo"])), ic_wa=IC_WA, ic_fl=IC_FLECHA,
        ic_reloj=IC_RELOJ, vigencia=fmt_fecha_ar(vig_date),
    )


def render_chips(publicados):
    # Mismo orden que los bloques de la grilla: el chip N-esimo corresponde al
    # bloque N-esimo. Si no coinciden, la pagina se lee desprolija.
    chips = ['      <button class="pk-chip on" data-r="all" aria-pressed="true">'
             'Todos <span class="n">{}</span></button>'.format(len(publicados))]
    for r, items in agrupar(publicados):
        chips.append('      <button class="pk-chip" data-r="{r}" aria-pressed="false">'
                     '{lbl} <span class="n">{n}</span></button>'.format(
                         r=e(r), lbl=e(REGIONES.get(r, r.replace("-", " ").title())),
                         n=len(items)))
    return ('    <div class="pk-filters rv" role="group" aria-label="Filtrar por regi&oacute;n">\n'
            + "\n".join(chips) + "\n    </div>")


def agrupar(publicados):
    """
    Agrupa las salidas por region y devuelve [(region, [(p, vig), ...]), ...]
    en el orden de ORDEN_REGIONES. Dentro de cada grupo se conserva el orden
    que ya traia: destacados primero y despues por fecha de salida.
    """
    grupos = {}
    for p, v in publicados:
        grupos.setdefault(p["region"], []).append((p, v))
    def clave(r):
        return (ORDEN_REGIONES.index(r) if r in ORDEN_REGIONES else len(ORDEN_REGIONES), r)
    return [(r, grupos[r]) for r in sorted(grupos, key=clave)]


def render_grupos(publicados):
    """La grilla dividida en bloques con titulo, uno por region."""
    NL = chr(10)
    bloques = []
    for region, items in agrupar(publicados):
        titulo = REGIONES_TITULO.get(
            region, "Descubr&iacute; " + e(REGIONES.get(region, region)))
        n = len(items)
        bloques.append(NL.join([
            '    <section class="pk-group" data-r="{}">'.format(e(region)),
            '      <div class="pk-ghead">',
            '        <h3>{}</h3>'.format(titulo),
            '        <span class="n">{} {}</span>'.format(n, "salida" if n == 1 else "salidas"),
            '      </div>',
            '      <div class="pk-grid">',
            NL.join(render_card(p, v) for p, v in items),
            '      </div>',
            '    </section>',
        ]))
    return NL.join(bloques)


def render_vacio():
    return '''    <div class="pk-empty rv">
      {ic}
      <h3>Estamos renovando nuestras salidas</h3>
      <p>En este momento no tenemos paquetes publicados. Escribinos y armamos una propuesta con tu destino, tus fechas y tu presupuesto.</p>
      <a class="pk-cta" style="max-width:320px;margin:0 auto" href="{wa}" target="_blank" rel="noopener noreferrer">
        {ic_wa}
        Consultanos por WhatsApp
      </a>
    </div>'''.format(
        ic=IC_BRUJULA, ic_wa=IC_WA,
        wa=e("https://wa.me/{}?text={}".format(
            WA_NUMERO,
            urllib.parse.quote("Hola Legend Travel, quiero consultar por una salida", safe=''))))


def render_card_compacta(p, vig):
    """Card chica para las madres y para 'otros paquetes': lo minimo que
    hace falta para decidir un click (titulo, salida, duracion, precio)."""
    pd = p["precio_desde"]
    dests = lista(p, "destinos")
    return '''      <a class="pkc" href="paquetes/{id}/">
        <span class="k">{ic}{dest}</span>
        <span class="t">{titulo}</span>
        <span class="s">{salida} &middot; {noches}</span>
        <span class="p"><b><small>Desde</small> {moneda} {precio}</b><span>Ver detalle &rarr;</span></span>
      </a>'''.format(
        id=e(p["id"]), ic=IC_BRUJULA,
        dest=e(dests[0] if dests else REGIONES.get(p["region"], p["region"])),
        titulo=e(p["titulo"]), salida=e(salida_corta(p["salida"])),
        noches=e(noches_txt(p["noches"])),
        moneda=e(pd.get("moneda", "")), precio=fmt_precio(pd.get("valor")))


def grid_style(n):
    if n == 1:
        return ' style="max-width:400px"'
    if n == 2:
        return ' style="max-width:820px"'
    return ''


def render_region_block(carpeta, items, hoy):
    """
    Modulo "Salidas destacadas" de una madre: hasta MAX_REGION_CARDS cards
    compactas + link a /paquetes/. Si la carpeta junta mas de una region
    (disney/ recibe quinceaneras), el titulo cae a una version neutra.
    """
    muestra = items[:MAX_REGION_CARDS]
    regs = {p["region"] for p, _ in items}
    if len(regs) == 1:
        r = list(regs)[0]
        frase = REGIONES_FRASE.get(r, "a " + REGIONES.get(r, r))
        titulo = REGIONES_TITULO.get(r) or "Salidas {frase} con <em>fecha y precio cerrado</em>.".format(frase=e(frase))
        ancla = "paquetes/#{}".format(e(r))
    else:
        titulo = "Salidas con <em>fecha y precio cerrado</em>."
        ancla = "paquetes/"

    if len(items) > len(muestra):
        ver = "Ver las {} salidas".format(len(items))
    else:
        ver = "Ver todos los paquetes"

    NL = chr(10)
    return NL.join([
        R_START,
        "<!-- Generado por build-paquetes.py el {}. NO editar a mano: se pisa. -->".format(hoy.isoformat()),
        CARD_CSS,
        '  <hr class="pk-rsep">',
        '  <div class="mx" style="margin-top:64px">',
        '    <div class="pk-rhead rv">',
        '      <div>',
        '        <p class="kicker">Salidas destacadas</p>',
        '        <h3>{}</h3>'.format(titulo),
        '      </div>',
        '      <a class="pk-rall" href="{a}">{v}{ic}</a>'.format(a=ancla, v=ver, ic=IC_FLECHA),
        '    </div>',
        '    <div class="pkc-grid rv">',
        NL.join(render_card_compacta(p, v) for p, v in muestra),
        '    </div>',
        '  </div>',
        R_END,
    ])


# ============================================================
# Render — PAGINA DE DETALLE
# ============================================================
def _sec(titulo, cuerpo, extra=""):
    return '''
<section class="dsec px">
  <div class="dwrap rv">
    <h2 class="dh2">{t}</h2>
{c}{x}
  </div>
</section>'''.format(t=titulo, c=cuerpo, x=extra)


def render_relacionados(p, todos):
    """
    C2: hasta MAX_RELACIONADOS salidas para seguir mirando. Primero las de la
    misma region; si no alcanzan, se completa con otras. Nunca la actual.
    """
    otros = [(q, v) for q, v in todos if q["id"] != p["id"]]
    if not otros:
        return ""
    misma = [x for x in otros if x[0]["region"] == p["region"]]
    resto = [x for x in otros if x[0]["region"] != p["region"]]
    elegidos = (misma + resto)[:MAX_RELACIONADOS]

    if len(misma) >= 1:
        sub = "Otras salidas {}".format(REGIONES_FRASE.get(p["region"], ""))
    else:
        sub = "Otras salidas"
    NL = chr(10)
    return NL.join([
        '',
        '<section class="dsec px">',
        '  <div class="dwrap rv">',
        '    <h2 class="dh2">{} <em>que te pueden interesar</em></h2>'.format(e(sub.strip())),
        '    <div class="drel">',
        NL.join(render_card_compacta(q, v) for q, v in elegidos),
        '    </div>',
        '  </div>',
        '</section>',
    ])


def render_detalle(p, vig, plantilla, todos=()):
    pd = p["precio_desde"]
    dests = lista(p, "destinos")
    titulo_txt = txt(p, "titulo")
    resumen = txt(p, "resumen")
    relacionados = render_relacionados(p, todos)

    # --- barra de datos rapidos (solo lo que existe) ---
    facts = [("Salida", IC_CAL, e(p["salida"]), ""),
             ("Duraci&oacute;n", IC_CAMA, e(noches_txt(p["noches"])), "")]
    if txt(p, "regimen"):
        facts.append(("R&eacute;gimen", IC_PLATO, e(txt(p, "regimen")), ""))
    datos = "\n".join(
        '    <div class="dfact{cls}"><span class="k">{ic}{k}</span><span class="v">{v}</span></div>'
        .format(cls=cls, ic=ic, k=k, v=v) for k, ic, v, cls in facts)

    # --- itinerario (opcional) ---
    itin = [i for i in lista(p, "itinerario") if isinstance(i, dict)]
    itin_html = ""
    if itin:
        filas = []
        for i in itin:
            cuerpo = str(i.get("texto") or "").strip()
            pm = ('<span class="pm">{}</span>'.format(IC_MAS) if cuerpo
                  else '<span class="pm" style="visibility:hidden"></span>')
            body = ('\n        <div class="cuerpo"><p>{}</p></div>'.format(e(cuerpo))
                    if cuerpo else "")
            filas.append(
                '      <div class="ditem{tiene}">\n'
                '        <div class="head"{aria}>'
                '<span class="dia">{dia}</span>'
                '<span class="tit">{tit}</span>{pm}</div>{body}\n'
                '      </div>'.format(
                    tiene=" tiene" if cuerpo else "",
                    aria=' role="button" tabindex="0" aria-expanded="false"' if cuerpo else '',
                    dia=e(str(i.get("dia") or "")), tit=e(str(i.get("titulo") or "")),
                    pm=pm, body=body))
        itin_html = _sec("Itinerario <em>d&iacute;a a d&iacute;a</em>",
                         '    <div class="ditin">\n' + "\n".join(filas) + '\n    </div>')

    # --- incluye ---
    incluye_html = _sec(
        "El viaje <em>incluye</em>",
        '    <ul class="dlist si">\n' + "\n".join(
            '      <li>{}<span>{}</span></li>'.format(IC_CHECK, e(x))
            for x in lista(p, "incluye")) + '\n    </ul>')

    # --- no incluye (opcional) ---
    noinc = lista(p, "no_incluye")
    noinc_html = _sec(
        "No <em>incluye</em>",
        '    <ul class="dlist no">\n' + "\n".join(
            '      <li>{}<span>{}</span></li>'.format(IC_CRUZ, e(x)) for x in noinc)
        + '\n    </ul>') if noinc else ""

    # --- hoteles (opcional) ---
    hot = lista(p, "hoteles")
    hoteles_html = _sec(
        "Hoteles <em>previstos</em>",
        '    <ul class="dlist si">\n' + "\n".join(
            '      <li>{}<span>{}</span></li>'.format(IC_HOTEL, e(x)) for x in hot)
        + '\n    </ul>',
        '\n    <p class="dnota">Hoteles previstos o similares, sujetos a disponibilidad '
        'al momento de la reserva.</p>') if hot else ""

    # --- tarifas (opcional) ---
    tar = [t for t in lista(p, "tarifas") if isinstance(t, dict)]
    tarifas_html = ""
    if tar:
        filas = "\n".join(
            '      <div><dt>{}</dt><dd>{}</dd></div>'.format(
                e(str(t.get("etiqueta") or "")), e(str(t.get("precio") or "")))
            for t in tar)
        nota = txt(p, "nota_impuestos")
        extra = '\n    <p class="dnota">{}</p>'.format(e(nota)) if nota else ""
        extra += ('\n    <p class="dnota">Precios por persona, sujetos a disponibilidad '
                  'y a confirmaci&oacute;n al momento de la reserva.</p>')
        tarifas_html = _sec("Tarifas <em>por base</em>",
                            '    <dl class="dtar">\n' + filas + '\n    </dl>', extra)

    # --- condiciones (opcional) ---
    cond = lista(p, "condiciones")
    cond_html = _sec(
        "Condiciones",
        '    <ul class="dlist no">\n' + "\n".join(
            '      <li>{}<span>{}</span></li>'.format(IC_CHECK, e(x)) for x in cond)
        + '\n    </ul>') if cond else ""

    # --- linea del hero ---
    partes = []
    if dests:
        # se escapa cada destino por separado: escapar la cadena ya unida
        # convertia el separador en texto literal ("&middot;")
        partes.append("<b>{}</b>".format(" &middot; ".join(e(d) for d in dests[:4])))
    partes.append(e(noches_txt(p["noches"])))
    partes.append(e(p["salida"]))
    hero_linea = '<span class="sep">|</span>'.join(
        "<span>{}</span>".format(x) for x in partes)

    # --- C3: link a la madre de la region ---
    carpeta = REGION_MADRE.get(p["region"])
    hero_madre = ""
    if carpeta and (ROOT / carpeta / "index.html").exists():
        hero_madre = (
            '\n      <p style="margin-top:14px">'
            '<a href="{c}/" style="display:inline-flex;align-items:center;gap:7px;'
            'font-size:13.5px;font-weight:600;color:rgba(255,255,255,.8);'
            'border-bottom:1px solid rgba(255,255,255,.25);padding-bottom:2px">'
            'Ver m&aacute;s viajes a {n} {ic}</a></p>'
        ).format(c=e(carpeta), n=e(REGIONES.get(p["region"], p["region"])), ic=IC_FLECHA)

    # --- E: urgencia, solo con datos reales (vigencia y fecha de salida) ---
    urg = []   # P2: la vigencia de tarifa no se muestra (sigue retirando vencidos)
    if "salida única" in str(p["salida"]).lower() or "salida unica" in str(p["salida"]).lower():
        urg.append('<span>{}Salida &uacute;nica &mdash; {}</span>'.format(
            IC_CAL, e(salida_corta(p["salida"]))))
    urgencia = ('    <div class="durg">' + "".join(urg) + '</div>') if urg else ''

    # --- B: schema. BreadcrumbList + TouristTrip, SIN precios (rotan) ---
    canonical = "{}/paquetes/{}".format(DOMINIO, p["id"])
    trip = {
        "@type": "TouristTrip",
        "@id": canonical + "#trip",
        "name": titulo_txt,
        "description": resumen,
        "url": canonical,
        "provider": {"@id": ORG_ID},
    }
    if dests:
        trip["touristType"] = (REGIONES["quinceaneras"] if p["region"] == "quinceaneras"
                               else "Viajeros desde Argentina")
        trip["itinerary"] = {
            "@type": "ItemList",
            "numberOfItems": len(dests),
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1,
                 "item": {"@type": "Place", "name": d}}
                for i, d in enumerate(dests)],
        }
    dias = [i for i in lista(p, "itinerario") if isinstance(i, dict)]
    if dias:
        trip["subjectOf"] = {
            "@type": "ItemList", "name": "Itinerario dia a dia",
            "numberOfItems": len(dias),
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1,
                 "name": " - ".join(x for x in [str(d.get("dia") or "").strip(),
                                                str(d.get("titulo") or "").strip()] if x)}
                for i, d in enumerate(dias)],
        }
    schema = json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Inicio", "item": DOMINIO + "/"},
                {"@type": "ListItem", "position": 2, "name": "Paquetes", "item": DOMINIO + "/paquetes"},
                {"@type": "ListItem", "position": 3, "name": titulo_txt, "item": canonical},
            ]},
            trip,
        ]}, ensure_ascii=False, separators=(',', ':'))

    # --- A: metas. og:image absoluta; con placeholder cae a la del sitio ---
    desc = meta_desc(p)
    if es_url(p["imagen"]):
        ogimg = p["imagen"]
    elif p["imagen"] == PLACEHOLDER:
        ogimg = DOMINIO + "/og-image.jpg"
    else:
        ogimg = DOMINIO + "/" + p["imagen"].lstrip("/")
    pnota = str(pd.get("nota") or "").strip()
    og_titulo = "{} &mdash; desde {} {}".format(
        titulo_txt, pd.get("moneda", ""), fmt_precio(pd.get("valor")))

    # El hero se ve a pantalla completa: si la foto es de Pexels se pide una
    # variante mas grande. La card sigue con la chica (no hace falta mas).
    img_hero = p["imagen"]
    if "images.pexels.com" in img_hero:
        img_hero = re.sub(r'([?&]w=)\d+', r'\g<1>2200', img_hero)
    elif img_hero.startswith("assets/img/pexels/"):
        # foto local (tools/fotos_locales.py): se usa la variante grande si existe
        grande = re.sub(r'-\d+\.jpg$', '-1800.jpg', img_hero)
        if (ROOT / grande).exists():
            img_hero = grande
        # ruta absoluta: el navegador pide esta foto antes de leer el <base> y una ruta relativa daba 404 en /paquetes/<id>/
        img_hero = "/" + img_hero

    vals = {
        "{{IMAGEN_HERO}}": e(img_hero),
        "{{TITULO_TAG}}": e(titulo_tag(titulo_txt)),
        "{{OG_TITULO}}": e(html.unescape(og_titulo)),
        "{{OG_DESC}}": e(resumen),
        "{{TITULO_TXT}}": e(titulo_txt),
        "{{TITULO}}": e(titulo_txt),
        "{{HERO_MADRE}}": hero_madre,
        "{{URGENCIA}}": urgencia,
        "{{RELACIONADOS}}": relacionados,
        "{{DESC}}": e(desc),
        "{{ALT}}": e(dests[0] if dests else titulo_txt),
        "{{KICKER}}": e(REGIONES.get(p["region"], p["region"])),
        "{{CANONICAL}}": e(canonical),
        "{{OGIMAGE}}": e(ogimg),
        "{{IMAGEN}}": e(p["imagen"]),
        "{{HERO_LINEA}}": hero_linea,
        "{{MONEDA}}": e(pd.get("moneda", "")),
        "{{PRECIO}}": fmt_precio(pd.get("valor")),
        "{{PRECIO_NOTA}}": '<span class="nota">{}</span>'.format(e(pnota)) if pnota else "",
        "{{NFACTS}}": str(len(facts)),
        "{{DATOS}}": datos,
        "{{RESUMEN}}": e(resumen),
        "{{ITINERARIO}}": itin_html,
        "{{INCLUYE}}": incluye_html,
        "{{NO_INCLUYE}}": noinc_html,
        "{{HOTELES}}": hoteles_html,
        "{{TARIFAS}}": tarifas_html,
        "{{CONDICIONES}}": cond_html,
        "{{WA}}": e(wa_link(p["titulo"])),
        "{{SCHEMA}}": schema,
    }
    out = plantilla
    for k, v in vals.items():
        out = out.replace(k, v)
    sobran = set(re.findall(r'\{\{[A-Z_]+\}\}', out))
    if sobran:
        raise ValueError("{}: placeholders sin reemplazar: {}".format(p["id"], sobran))
    return out


# ============================================================
# Marcadores en las madres
# ============================================================
def asegurar_marcadores(texto):
    if R_START in texto and R_END in texto:
        return texto, False
    m = re.search(r'<section\b[^>]*\bid="paquetes"[^>]*>', texto)
    if not m:
        return texto, None
    cierre = texto.find("</section>", m.end())
    if cierre == -1:
        return texto, None
    return texto[:cierre] + "\n{}\n{}\n".format(R_START, R_END) + texto[cierre:], True


# ============================================================
# Carga y validacion
# ============================================================
def cargar(hoy):
    """Devuelve (publicados, vencidos, inactivos, avisos, fotos). Corta si hay errores."""
    raw = json.loads(DATA.read_text(encoding="utf-8"))
    paquetes = raw.get("paquetes") if isinstance(raw, dict) else raw
    if not isinstance(paquetes, list):
        sys.exit('ERROR: se esperaba una lista en la clave "paquetes".')

    publicados, vencidos, inactivos, avisos, errores, fotos = [], [], [], [], [], []
    vistos = set()

    for idx, p in enumerate(paquetes):
        ident = p.get("id") or "#{} (sin id)".format(idx + 1)

        faltan = [c for c in OBLIGATORIOS if c not in p or p[c] in (None, "", [], {})]
        if faltan:
            errores.append("{}: faltan campos {}".format(ident, ", ".join(faltan)))
            continue
        if ident in vistos:
            errores.append("{}: id duplicado".format(ident))
            continue
        vistos.add(ident)
        if not re.match(r'^[a-z0-9-]+$', str(ident)):
            errores.append("{}: el id tiene que ser slug (a-z 0-9 -): se usa de carpeta web".format(ident))
            continue
        if not isinstance(p.get("incluye"), list) or not isinstance(p.get("destinos"), list):
            errores.append('{}: "incluye" y "destinos" tienen que ser listas'.format(ident))
            continue
        if not isinstance(p.get("precio_desde"), dict) or "valor" not in p["precio_desde"]:
            errores.append('{}: "precio_desde" tiene que ser un objeto con valor y moneda'.format(ident))
            continue

        vig = parse_vigencia(p["vigencia"])
        if vig is None:
            errores.append('{}: vigencia "{}" no se entiende (formato AAAA-MM-DD)'
                           .format(ident, p["vigencia"]))
            continue

        if not p.get("activo", False):
            inactivos.append((ident, txt(p, "motivo_inactivo")))
            continue
        if vig < hoy:
            vencidos.append((ident, vig))
            continue

        if not es_url(p["imagen"]) and not (ROOT / p["imagen"]).exists():
            fotos.append((ident, p["imagen"]))
            p["imagen"] = PLACEHOLDER

        if vig - hoy <= datetime.timedelta(days=7):
            avisos.append("{}: la tarifa vence en {} dias ({})"
                          .format(ident, (vig - hoy).days, fmt_fecha_ar(vig)))
        if str(p["titulo"]).strip().upper().startswith("[EJEMPLO]"):
            avisos.append("{}: sigue marcado [EJEMPLO] — no publicar asi".format(ident))
        if p["region"] not in REGIONES:
            avisos.append('{}: region "{}" no esta en el mapa de REGIONES'.format(ident, p["region"]))

        publicados.append((p, vig))

    if errores:
        print("\nERRORES — no se genero nada:")
        for x in errores:
            print("  x  {}".format(x))
        sys.exit(1)

    publicados.sort(key=lambda t: (
        not bool(t[0].get("destacado")),
        parse_salida(t[0]["salida"]) or t[1],
    ))
    return publicados, vencidos, inactivos, avisos, fotos


# ============================================================
# D — GEO: llms.txt con la oferta viva
# ============================================================
def actualizar_llms(publicados, hoy):
    """
    Reescribe SOLO el bloque entre marcadores de llms.txt con las salidas
    vigentes. Lo que lee una IA es siempre la oferta de hoy, nunca una
    tarifa muerta. El resto del archivo no se toca.
    """
    if not LLMS.exists():
        print("\n!  no existe llms.txt — salteado")
        return

    original = LLMS.read_text(encoding="utf-8")
    t = original

    NL = chr(10)
    filas = []
    for p, vig in publicados:
        pd = p["precio_desde"]
        filas.append("- {titulo} — desde {mon} {val} — Salida: {sal} — {url}".format(
            titulo=txt(p, "titulo"), mon=pd.get("moneda", ""),
            val=fmt_precio(pd.get("valor")), sal=salida_corta(p["salida"]),
            url="{}/paquetes/{}".format(DOMINIO, p["id"])))

    bloque = NL.join([
        LLMS_START,
        "## Salidas y paquetes actuales",
        "Generado el {} desde data/paquetes.json. Solo salidas vigentes:".format(hoy.isoformat()),
        "lo inactivo o vencido se retira de esta lista automáticamente.",
        "Precios por persona en base doble, sujetos a confirmación al reservar.",
        "",
    ] + filas + [
        "",
        "Listado completo: {}/paquetes".format(DOMINIO),
        LLMS_END,
    ]) if filas else NL.join([
        LLMS_START,
        "## Salidas y paquetes actuales",
        "En este momento no hay salidas publicadas. Consultar por WhatsApp.",
        LLMS_END,
    ])

    if LLMS_START in t and LLMS_END in t:
        t = reemplazar_bloque(t, LLMS_START, LLMS_END, bloque)
    elif "## Contacto" in t:
        t = t.replace("## Contacto", bloque + NL + NL + "## Contacto", 1)
    else:
        t = t.rstrip() + NL + NL + bloque + NL

    # Correccion de una linea que describia el buscador de GEA, ya dado de baja.
    viejo = "- Buscador de paquetes con precios en tiempo real"
    if viejo in t:
        t = t.replace(
            viejo,
            "- Salidas y paquetes con precio y fecha publicados en /paquetes",
            1)
        print("\n!  llms.txt: corregida la linea del buscador de GEA (ya no existe)")

    if t != original:
        LLMS.write_text(t, encoding="utf-8")
        print("OK  llms.txt actualizado ({} salidas)".format(len(filas)))
    else:
        print("=   llms.txt sin cambios")


# ============================================================
# Main
# ============================================================
# ============================================================
# E — Reseñas de Google en la home (data/resenas-google.json)
# ============================================================
RES_JSON = ROOT / "data" / "resenas-google.json"
RS_START = "<!-- RESENAS:START -->"
RS_END = "<!-- RESENAS:END -->"
RSS_START = "<!-- RESENAS-SCHEMA:START -->"
RSS_END = "<!-- RESENAS-SCHEMA:END -->"
RS_STAR = ('<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 17.27 18.18 21l-1.64-7.03'
           'L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></svg>')
RS_CSS = """<style>
.rsG{background:var(--white)}
.rsG-grid{display:grid;gap:18px;margin-top:48px}
@media(min-width:720px){.rsG-grid{grid-template-columns:1fr 1fr}}
@media(min-width:1100px){.rsG-grid{grid-template-columns:repeat(3,1fr);gap:22px}}
.rsG-card{display:flex;flex-direction:column;gap:16px;padding:clamp(22px,2.4vw,30px);border-radius:var(--r-lg);background:#fff;box-shadow:0 0 0 1px var(--line),0 30px 60px -48px rgba(14,35,45,.35)}
.rsG-top{display:flex;align-items:center;gap:14px}
.rsG-av{flex:none;width:48px;height:48px;border-radius:50%;background:var(--red);color:#fff;display:grid;place-items:center;font-weight:700;font-size:16px;letter-spacing:.04em}
.rsG-top b{display:block;font-size:16px;color:var(--ink);line-height:1.2}
.rsG-stars{display:inline-flex;gap:2px;margin-top:5px;color:var(--gold)}
.rsG-stars svg{width:15px;height:15px}
.rsG-card p{margin:0;font-size:15.5px;line-height:1.6;color:var(--ink-2)}
.rsG-more{margin-top:40px}
</style>"""


def actualizar_resenas():
    """
    Reescribe en index.html la sección "Nuestros pasajeros" (entre RS_START y
    RS_END) y el schema Review (entre RSS_START y RSS_END) con las reseñas de
    data/resenas-google.json. Para sumar una reseña alcanza con editar el JSON
    y volver a correr este script: no se toca HTML a mano.
    """
    if not RES_JSON.exists():
        print("\n!  no existe data/resenas-google.json — salteado")
        return
    data = json.loads(RES_JSON.read_text(encoding="utf-8"))
    rs = [r for r in data.get("resenas", []) if str(r.get("nombre", "")).strip() and str(r.get("texto", "")).strip()]
    url = str(data.get("url_google") or "").strip()
    home = ROOT / "index.html"
    t = home.read_text(encoding="utf-8")
    original = t
    if RS_START not in t or RS_END not in t or RSS_START not in t or RSS_END not in t:
        print("\n!  index.html no tiene los marcadores RESENAS — salteado")
        return

    def iniciales(nombre):
        partes = [p for p in nombre.replace("-", " ").split() if p]
        return (partes[0][0] + (partes[1][0] if len(partes) > 1 else "")).upper()

    cards = []
    for i, r in enumerate(rs):
        n = max(1, min(5, int(r.get("estrellas", 5) or 5)))
        cards.append(
            '      <article class="rsG-card rv" style="--d:{d}ms">\n'
            '        <div class="rsG-top"><span class="rsG-av" aria-hidden="true">{ini}</span>'
            '<div><b>{nombre}</b><span class="rsG-stars" role="img" aria-label="{n} de 5 estrellas">{stars}</span></div></div>\n'
            '        <p>{texto}</p>\n'
            '      </article>'.format(d=min(i, 8) * 70, ini=e(iniciales(r["nombre"])), nombre=e(r["nombre"]),
                                      n=n, stars=RS_STAR * n, texto=e(r["texto"])))
    link = ""
    if url:
        link = ('\n    <div class="rsG-more rv"><a class="btn" data-magnet href="{u}" target="_blank" rel="noopener noreferrer">'
                'Ver todas las rese&ntilde;as en Google <span class="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14m-6-6 6 6-6 6"/></svg></span></a></div>'
                ).format(u=e(url))
    bloque = "\n".join([
        RS_START,
        "<!-- Generado por build-paquetes.py desde data/resenas-google.json. NO editar a mano: se pisa. -->",
        '<section class="sec rsG" id="pasajeros">',
        RS_CSS,
        '  <div class="wrap">',
        '    <div class="rv"><p class="kicker">Nuestros pasajeros</p><h2 class="h2">Lo que dicen <em>quienes ya viajaron.</em></h2></div>',
        '    <div class="rsG-grid">',
        "\n".join(cards),
        '    </div>' + link,
        '  </div>',
        '</section>',
        RS_END,
    ])
    schema = {
        "@context": "https://schema.org",
        "@type": "TravelAgency",
        "@id": DOMINIO + "/#agencia",
        "review": [{
            "@type": "Review",
            "reviewRating": {"@type": "Rating", "ratingValue": str(max(1, min(5, int(r.get("estrellas", 5) or 5)))), "bestRating": "5"},
            "author": {"@type": "Person", "name": r["nombre"]},
            "reviewBody": r["texto"],
        } for r in rs],
    }
    bloque_schema = "\n".join([
        RSS_START,
        "<!-- Generado por build-paquetes.py desde data/resenas-google.json. NO editar a mano: se pisa. -->",
        '<script type="application/ld+json">',
        json.dumps(schema, ensure_ascii=False, indent=2),
        '</script>',
        RSS_END,
    ])
    t = reemplazar_bloque(t, RS_START, RS_END, bloque)
    t = reemplazar_bloque(t, RSS_START, RSS_END, bloque_schema)
    if t != original:
        home.write_text(t, encoding="utf-8")
        print("OK  index.html: seccion 'Nuestros pasajeros' ({} resenas{})".format(
            len(rs), "" if url else "; sin link a Google porque url_google esta vacio"))
    else:
        print("=   index.html: resenas sin cambios")


def main():
    hoy = datetime.date.today()
    print("build-paquetes.py  —  {}".format(hoy.isoformat()))
    print("=" * 66)

    for f in (DATA, PAGE, TEMPLATE):
        if not f.exists():
            sys.exit("ERROR: no existe {}".format(f))
    plantilla = TEMPLATE.read_text(encoding="utf-8")

    IMGDIR.mkdir(parents=True, exist_ok=True)
    ph = ROOT / PLACEHOLDER
    if not ph.exists():
        ph.write_text(PLACEHOLDER_SVG, encoding="utf-8")
        print("  + creado {}".format(PLACEHOLDER))

    publicados, vencidos, inactivos, avisos, fotos = cargar(hoy)

    # ---------- 1. paquetes/index.html ----------
    if publicados:
        bloque = "\n".join([
            START,
            "<!-- Generado por build-paquetes.py el {}. NO editar a mano: se pisa. -->".format(hoy.isoformat()),
            CARD_CSS,
            render_chips(publicados),
            render_grupos(publicados),
            '    <p class="pk-nores">No hay salidas en esa regi&oacute;n por ahora.</p>',
            END,
        ])
    else:
        bloque = "\n".join([START, render_vacio(), END])

    pagina = PAGE.read_text(encoding="utf-8")
    if START not in pagina or END not in pagina:
        sys.exit("ERROR: faltan los marcadores en {}".format(PAGE))
    nueva = reemplazar_bloque(pagina, START, END, bloque)
    if nueva != pagina:
        PAGE.write_text(nueva, encoding="utf-8")
        print("\nOK  paquetes/index.html  ({} salidas)".format(len(publicados)))
    else:
        print("\n=   paquetes/index.html sin cambios")

    # ---------- 2. paginas de detalle ----------
    activos_ids = {p["id"] for p, _ in publicados}
    nuevas = act = 0
    for p, v in publicados:
        d = PAQDIR / p["id"]
        d.mkdir(parents=True, exist_ok=True)
        # copia del logo en cada carpeta: el navegador lo pide relativo a la carpeta antes de leer el <base> (404 si no está)
        logo_src = ROOT / "logo-wordmark.png"
        for carpeta in (PAQDIR, d):
            if logo_src.exists() and not (carpeta / "logo-wordmark.png").exists():
                shutil.copy2(logo_src, carpeta / "logo-wordmark.png")
        f = d / "index.html"
        existia = f.exists()
        out = render_detalle(p, v, plantilla, publicados)
        if not existia or f.read_text(encoding="utf-8") != out:
            f.write_text(out, encoding="utf-8")
            if existia:
                act += 1
            else:
                nuevas += 1
    print("\n→  Paginas de detalle: {} ({} nuevas, {} actualizadas, {} sin cambios)".format(
        len(publicados), nuevas, act, len(publicados) - nuevas - act))

    borradas = []
    for d in sorted(PAQDIR.iterdir()):
        if d.is_dir() and d.name not in activos_ids:
            shutil.rmtree(d)
            borradas.append(d.name)
    if borradas:
        print("   borradas (ya no activas): {}".format(", ".join(borradas)))

    # ---------- 3. modulo "Salidas destacadas" en las madres ----------
    # Se agrupa por CARPETA, no por region: disney/ recibe las de quinceaneras.
    por_carpeta = {}
    for p, v in publicados:
        carpeta = REGION_MADRE.get(p["region"])
        if carpeta:
            por_carpeta.setdefault(carpeta, []).append((p, v))

    candidatas = sorted(set(list(REGION_MADRE.values()) + list(por_carpeta.keys())))

    print("\n→  Salidas destacadas en las madres:")
    tocadas, vaciadas, sin_seccion, sin_pagina = [], [], [], []
    for carpeta in candidatas:
        f = ROOT / carpeta / "index.html"
        if not f.exists():
            if carpeta in por_carpeta:
                sin_pagina.append(carpeta)
            continue
        texto = f.read_text(encoding="utf-8")
        texto, insertados = asegurar_marcadores(texto)
        if insertados is None:
            if carpeta in por_carpeta:
                sin_seccion.append(carpeta)
            continue
        items = por_carpeta.get(carpeta, [])
        bloque_r = (render_region_block(carpeta, items, hoy) if items
                    else R_START + "\n" + R_END)
        nuevo = reemplazar_bloque(texto, R_START, R_END, bloque_r)
        if nuevo != f.read_text(encoding="utf-8"):
            f.write_text(nuevo, encoding="utf-8")
            if items:
                tocadas.append(carpeta)
            else:
                vaciadas.append(carpeta)
        if items:
            print("   {:<18} {} de {} salida(s)".format(
                carpeta + "/", min(len(items), MAX_REGION_CARDS), len(items)))
    for r in vaciadas:
        print("   {:<18} sin salidas — modulo vaciado".format(r + "/"))
    if not tocadas and not vaciadas:
        print("   (sin cambios)")

    # ---------- 4. llms.txt (GEO) ----------
    actualizar_llms(publicados, hoy)

    # ---------- 5. resenas de Google en la home ----------
    actualizar_resenas()

    # ---------- resumen ----------
    print("\n" + "=" * 66)
    print("RESUMEN")
    print("=" * 66)
    print("  Publicados            : {}  (card + pagina de detalle)".format(len(publicados)))
    for p, v in publicados:
        print("      {} {:<34} {:<14} vence {}".format(
            "*" if p.get("destacado") else " ", p["id"], p["region"], fmt_fecha_ar(v)))

    print("\n  Excluidos por vencidos: {}".format(len(vencidos)))
    for ident, v in vencidos:
        print("      - {}  vencido el {} — no publicado".format(ident, fmt_fecha_ar(v)))

    print("\n  Inactivos             : {}".format(len(inactivos)))
    for ident, motivo in inactivos:
        print("      - {}".format(ident))
        if motivo:
            print("            {}".format(motivo))

    print("\n  Advertencias          : {}".format(len(avisos)))
    for a in avisos:
        print("      !  {}".format(a))
    for r in sin_pagina:
        print("      !  region '{}' tiene salidas pero no existe {}/index.html".format(r, r))
    for r in sin_seccion:
        print("      !  {}/index.html no tiene <section id=\"paquetes\"> — sin apartado".format(r))

    if fotos:
        print("\n" + "-" * 66)
        print("  FOTOS PENDIENTES ({}) — mientras tanto usan el placeholder".format(len(fotos)))
        print("-" * 66)
        for ident, ruta in fotos:
            print("      {:<34} {}".format(ident, ruta))

    if publicados:
        regs = []
        for p, _ in publicados:
            if p["region"] not in regs:
                regs.append(p["region"])
        print("\n  Chips                 : Todos, {}".format(
            ", ".join(REGIONES.get(r, r) for r in regs)))
    print()


if __name__ == "__main__":
    main()
