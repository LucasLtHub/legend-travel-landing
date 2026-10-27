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
- ref, operador y operador_sigla son INTERNOS: no salen nunca al HTML (ni cards, ni detalle,
  ni schema, ni llms). El operador nunca se muestra al cliente.
- codigo_ref (KM-1145, JT-2187, GEA...) SI se muestra, solo en el detalle ("Cod. KM-1145" bajo el precio)
  y como variable paquete_codigo del dataLayer; nunca en cards, madres, home ni en el texto de WhatsApp.

Uso: python build-paquetes.py
"""
import sys, json, html, re, datetime, urllib.parse, shutil, unicodedata
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
#   nota_impuestos, motivo_inactivo, operador, operador_sigla, ref, destacado,
#   precios, vuelos, crucero, foto_portada (P1/P2, ver docs/planilla-paquetes.md)
#   fuente_detalle (interno: de donde salio el detalle; no se publica)
#   regiones_extra: lista de regiones secundarias SOLO para listados (madres y relacionados);
#   la region principal sigue mandando en URL, kicker, schema y chips.

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
# Leyenda fija de precio (pedido de Silvia): va junto a TODO precio "Desde", en cards, detalle y llms.
LEYENDA_PRECIO = "Sujeto a disponibilidad al momento de la reserva."
# Pedido de Silvia (19/10/2026): en Argentina, Brasil y Caribe hay muchas mas fechas que las publicadas
# (se cotizan al consultar). En exoticos (Asia, Africa, Medio Oriente) y Europa NO: son fechas fijas.
MAS_FECHAS_REGIONES = {"argentina", "brasil", "caribe"}
MAS_FECHAS_TXT = "Tenemos muchas más fechas disponibles: consultanos por la que te convenga."
MAS_FECHAS_CARD = "Más fechas disponibles: consultanos"   # version corta para las cards
ORG_ID = DOMINIO + "/#organization"   # el ÚNICO @id de la agencia en todo el sitio (declaración y referencias)
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


def alt_imagen(p):
    """alt de la foto del paquete (card y hero del detalle): "imagen_alt" del JSON,
    descriptivo y concreto. Si falta, "Foto de <primer destino>" para que nunca quede vacío."""
    propio = str(p.get("imagen_alt") or "").strip()
    if propio:
        return propio
    dests = lista(p, "destinos")
    return "Foto de {}".format(dests[0] if dests else txt(p, "titulo"))


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
# ============================================================
# Filtros y orden de /paquetes/ (2026-10-22). Los datos salen del JSON:
# - meses_salida (explicito) o el texto de "salida": fecha fija, rango "del dd/mm al dd/mm/aaaa",
#   "Fecha a eleccion, hasta <mes> <aaaa>" (desde el mes del build) o "<Mes> <aaaa>".
# - tipo: lista derivada por tools (grupal, crucero, todo-incluido).
# ============================================================
MESES_NOMBRE = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
                "Septiembre", "Octubre", "Noviembre", "Diciembre"]
TIPOS_LABEL = [("grupal", "Salida grupal acompa\u00f1ada"), ("crucero", "Crucero"), ("todo-incluido", "Todo incluido")]
DURACIONES = [("hasta-5", "Hasta 5 noches"), ("6-10", "6 a 10 noches"), ("mas-10", "M\u00e1s de 10 noches")]


def _meses_entre(y1, m1, y2, m2):
    out = []
    y, m = y1, m1
    while (y, m) <= (y2, m2) and len(out) < 36:
        out.append("{:04d}-{:02d}".format(y, m))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def meses_de(p, hoy=None):
    """Meses (YYYY-MM) en los que sale el paquete. Un rango o 'fecha a eleccion' cubre todos sus meses."""
    hoy = hoy or datetime.date.today()
    exp = [str(x) for x in lista(p, "meses_salida") if re.match(r"^\d{4}-\d{2}$", str(x))]
    if exp:
        return exp
    s = str(p.get("salida") or "").strip().lower()
    m = re.search(r"del\s+(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\s+al\s+(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        y2, m2 = int(m.group(6)), int(m.group(5))
        y1, m1 = int(m.group(3) or y2), int(m.group(2))
        return _meses_entre(y1, m1, y2, m2)
    m = re.search(r"hasta\s+([a-z\u00e1\u00e9\u00ed\u00f3\u00fa]+)\s+(?:de\s+)?(\d{4})", s)
    if m and m.group(1) in MESES:
        return _meses_entre(hoy.year, hoy.month, int(m.group(2)), MESES[m.group(1)])
    d = parse_salida(s)
    if d:
        return ["{:04d}-{:02d}".format(d.year, d.month)]
    v = parse_vigencia(p.get("vigencia"))
    return ["{:04d}-{:02d}".format(v.year, v.month)] if v else []


def duracion_rango(noches):
    try:
        n = int(noches)
    except (TypeError, ValueError):
        return ""
    return "hasta-5" if n <= 5 else ("6-10" if n <= 10 else "mas-10")


def mes_label(ym):
    y, m = ym.split("-")
    return "{} {}".format(MESES_NOMBRE[int(m)], y)


def render_filtros(publicados, hoy):
    """Barra de filtros y orden: selects (orden, mes, duracion, tipo), chips de region, Limpiar y contador.
    En mobile va dentro de un <details> (boton 'Filtrar y ordenar'); el JS lo abre en escritorio.
    Sin JS: el listado completo se ve igual, en el orden por defecto."""
    desde = "{:04d}-{:02d}".format(hoy.year, hoy.month)
    meses = sorted({m for p, v in publicados for m in meses_de(p, hoy) if m >= desde})   # meses pasados no se ofrecen
    tipos_pres = {t for p, v in publicados for t in lista(p, "tipo")}
    NL = chr(10)

    def opt(val, lbl):
        return '          <option value="{}">{}</option>'.format(e(val), lbl)
    sel_orden = [opt("", "Pr\u00f3ximas salidas"), opt("precio-asc", "Precio: menor a mayor"),
                 opt("precio-desc", "Precio: mayor a menor"), opt("duracion", "Duraci\u00f3n")]
    sel_mes = [opt("", "Todos los meses")] + [opt(m, mes_label(m)) for m in meses]
    sel_dur = [opt("", "Cualquier duraci\u00f3n")] + [opt(k, l) for k, l in DURACIONES]
    sel_tipo = [opt("", "Todos los tipos")] + [opt(k, l) for k, l in TIPOS_LABEL if k in tipos_pres]

    def campo(id_, label, opts, nombre):
        return NL.join([
            '      <div class="pk-fld">',
            '        <label class="pk-lbl" for="pk-{}">{}</label>'.format(id_, label),
            '        <select id="pk-{}" class="pk-sel" data-f="{}">'.format(id_, nombre),
            NL.join(opts),
            '        </select>',
            '      </div>'])
    chips = render_chips(publicados).replace('    <div class="pk-filters rv" role="group" aria-label="Filtrar por regi&oacute;n">',
                                             '        <div class="pk-filters" role="group" aria-labelledby="pk-reg-lbl">')
    n = len(publicados)
    return NL.join([
        '    <details class="pk-fbox rv">',
        '      <summary class="pk-fsum">{}Filtrar y ordenar</summary>'.format(IC_FILTRO),
        '      <div class="pk-bar">',
        '      <div class="pk-sels">',
        campo("orden", "Ordenar por", sel_orden, "orden"),
        campo("mes", "Mes de salida", sel_mes, "mes"),
        campo("duracion", "Duraci\u00f3n", sel_dur, "duracion"),
        campo("tipo", "Tipo de viaje", sel_tipo, "tipo"),
        '      </div>',
        '      <div class="pk-fld">',
        '        <span class="pk-lbl" id="pk-reg-lbl">Regi\u00f3n</span>',
        chips,
        '      </div>',
        '      <div class="pk-tools">',
        '        <button type="button" class="pk-clear" disabled>Limpiar filtros</button>',
        '      </div>',
        '      </div>',
        '    </details>',
        '    <p class="pk-count" role="status" aria-live="polite">{} {}</p>'.format(n, "salida" if n == 1 else "salidas"),
    ])


def render_nores():
    wa = "https://wa.me/{}?text={}".format(WA_NUMERO, urllib.parse.quote(
        "Hola Legend Travel, busqu\u00e9 en los paquetes y no encontr\u00e9 lo que quiero. \u00bfMe arman una propuesta a medida?", safe=''))
    return NL_.join([
        '    <div class="pk-nores" hidden>',
        '      <h3>No encontramos salidas con esos filtros.</h3>',
        '      <p>Prob\u00e1 con otro mes o regi\u00f3n, o contanos qu\u00e9 busc\u00e1s y te armamos un viaje a medida.</p>',
        '      <a class="pk-cta" style="max-width:340px;margin:16px auto 0" href="{}" target="_blank" rel="noopener noreferrer">{}Pedir una propuesta por WhatsApp</a>'.format(e(wa), IC_WA),
        '    </div>',
    ])


NL_ = chr(10)
IC_FILTRO = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 6h16M7 12h10M10 18h4"/></svg>'


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
    if p["region"] in MAS_FECHAS_REGIONES:
        metas.append('            <span class="masf">{}</span>'.format(e(MAS_FECHAS_CARD)))

    inc = lista(p, "incluye")
    inc_html = "\n".join('          <li>{}{}</li>'.format(IC_CHECK, e(i))
                         for i in inc[:MAX_INCLUYE_CARD])
    mas = ('\n          <p class="pk-mas">+{} &#237;tems m&#225;s en el detalle</p>'
           .format(len(inc) - MAX_INCLUYE_CARD) if len(inc) > MAX_INCLUYE_CARD else "")

    pd = p["precio_desde"]
    pnota = str(pd.get("nota") or "").strip()
    pnota_html = ('\n            <p class="pk-pnota">{}</p>'.format(e(pnota)) if pnota else "")

    fecha_orden = parse_salida(p["salida"]) or vig_date
    return '''      <article class="pk-card" data-r="{region}" data-moneda="{moneda}" data-precio="{precio_n}" data-noches="{noches}" data-meses="{meses}" data-tipo="{tipo}" data-base="{base}" data-fecha="{fecha}">
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
            <p class="pk-sujeto">{leyenda}</p>
            <div class="pk-acts">
              <a class="pk-cta" href="{wa}" target="_blank" rel="noopener noreferrer">{ic_wa}Consultar</a>
              <span class="pk-ver">Ver detalle{ic_fl}</span>
            </div>
          </div>
        </div>
      </article>'''.format(
        region=e(p["region"]), id=e(p["id"]), imagen=e(p["imagen"]),
        precio_n=int(pd.get("valor") or 0), noches=int(p.get("noches") or 0),
        meses=" ".join(meses_de(p)), tipo=" ".join(lista(p, "tipo")),
        base=e("doble" if "doble" in [str(x.get("base")) for x in (p.get("precios") or []) if isinstance(x, dict)] else (str(((p.get("precios") or [{}])[0] or {}).get("base") or "doble"))), fecha=fecha_orden.isoformat(),
        alt=e(alt_imagen(p)), badge=badge,
        kicker=kicker, titulo=e(p["titulo"]), resumen=e(txt(p, "resumen")),
        metas="\n".join(metas), incluye=inc_html, mas=mas,
        moneda=e(pd.get("moneda", "")), precio=fmt_precio(pd.get("valor")),
        pnota=pnota_html, leyenda=LEYENDA_PRECIO, wa=e(wa_link(p["titulo"])), ic_wa=IC_WA, ic_fl=IC_FLECHA,
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
        <span class="s">{salida} &middot; {noches}</span>{masf}
        <span class="p"><b><small>Desde</small> {moneda} {precio}</b><span>Ver detalle &rarr;</span></span>
        <span class="sujeto">{leyenda}</span>
      </a>'''.format(
        leyenda=LEYENDA_PRECIO,
        masf=(chr(10) + '        <span class="masf">{}</span>'.format(e(MAS_FECHAS_CARD)) if p["region"] in MAS_FECHAS_REGIONES else ""),
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
    # La region de la madre manda en el titulo (medio-oriente/ dice "Medio Oriente" aunque
    # el paquete sea de africa via regiones_extra). El ancla #region solo sirve si todos
    # los paquetes tienen esa region principal (el filtro de /paquetes/ es por principal).
    r_madre = next((reg for reg, c in REGION_MADRE.items() if c == carpeta and reg in REGIONES_TITULO), None)
    r = r_madre or (list(regs)[0] if len(regs) == 1 else None)
    if r:
        frase = REGIONES_FRASE.get(r, "a " + REGIONES.get(r, r))
        titulo = REGIONES_TITULO.get(r) or "Salidas {frase} <em>con fecha confirmada</em>.".format(frase=e(frase))
        ancla = "paquetes/#{}".format(e(r)) if regs == {r} else "paquetes/"
    else:
        titulo = "Pr&oacute;ximas <em>salidas</em>."
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
        ('    <p class="dnota rv">Todas las salidas {f}: '.format(f=e(frase) if r else "publicadas") + " &middot; ".join(
            '<a href="paquetes/{}/" style="text-decoration:underline;text-underline-offset:3px">{}</a>'.format(e(p["id"]), e(txt(p, "titulo"))) for p, v in items) + '</p>')
        if len(items) > len(muestra) else '',
        '  </div>',
        R_END,
    ])


# ============================================================
# Render — PAGINA DE DETALLE
# ============================================================
# P1/P2 — campos del detalle. Todos opcionales: lo que no esta cargado no se muestra.
BASES = {"single": "Base single", "doble": "Base doble", "triple": "Base triple",
         "cuadruple": "Base cu&aacute;druple"}
BASES_ORDEN = ["single", "doble", "triple", "cuadruple"]
HOTEL_CAMPOS = ["id", "ciudad", "nombre", "categoria", "noches", "regimen", "habitacion", "web",
                "mapa", "destacados", "foto_credito"]
# Ficha de hotel: "id" nombra la foto (assets/img/hoteles/<id>.jpg|webp|png), que se muestra solo si el
# archivo existe Y hay "foto_credito". "mapa" es el texto de busqueda en Google Maps (nombre + ciudad).
# "destacados" es una lista de {"texto", "fuente"}: se publica el texto; la fuente es interna.
HOTEL_FOTOS = ROOT / "assets" / "img" / "hoteles"
IC_EXT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M7 17 17 7M9 7h8v8"/></svg>'
IC_PIN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 21s-7-5.5-7-11a7 7 0 0 1 14 0c0 5.5-7 11-7 11Z"/><circle cx="12" cy="10" r="2.5"/></svg>' 
VUELO_CAMPOS = ["aerolinea", "ruta", "clase", "fecha", "horario", "numero", "equipaje"]
CRUCERO_CAMPOS = [("naviera", "Naviera"), ("barco", "Barco"), ("cabina", "Tipo de cabina"),
                  ("bebidas", "Bebidas"), ("propinas", "Propinas"), ("wifi", "Wi-Fi"),
                  ("asistencia", "Asistencia al viajero")]


def _v(d, k):
    """Valor de texto de un campo; vacio si no esta o es "a confirmar"."""
    x = d.get(k) if isinstance(d, dict) else None
    s = "" if x is None else str(x).strip()
    return "" if s.lower() in ("a confirmar", "-", "n/a") else s


def render_hotel(h):
    if not isinstance(h, dict):   # formato viejo: "Ciudad: Hotel 4*"
        return e(h)
    partes = []
    nombre = _v(h, "nombre")
    cab = "<b>{}</b>".format(e(nombre)) if nombre else ""
    cat = _v(h, "categoria")
    if cat:
        cat = re.sub(r'^(\d)\s*\*', lambda m: m.group(1) + "&#9733;", e(cat))
        cab += " " + cat
    if cab:
        partes.append(cab.strip())
    if _v(h, "ciudad"):
        partes.append(e(_v(h, "ciudad")))
    if _v(h, "noches"):
        n = int(_v(h, "noches"))
        partes.append("{} {}".format(n, "noche" if n == 1 else "noches"))
    for k in ("regimen", "habitacion"):   # regimen de comidas y tipo de habitacion, si estan cargados
        if _v(h, k):
            partes.append(e(_v(h, k)))
    out = " &middot; ".join(partes)
    if es_url(_v(h, "web")):
        out += (' &middot; <a href="{}" target="_blank" rel="noopener noreferrer" '
                'style="color:var(--red);font-weight:600">Web oficial</a>').format(e(_v(h, "web")))
    return out


def foto_hotel(h):
    """Ruta de la foto del hotel si el archivo existe y tiene credito; si no, ''."""
    hid = _v(h, "id")
    if not hid or not _v(h, "foto_credito"):
        return ""
    for ext in ("jpg", "jpeg", "webp", "png"):
        if (HOTEL_FOTOS / "{}.{}".format(hid, ext)).exists():
            return "assets/img/hoteles/{}.{}".format(hid, ext)
    return ""


def render_hotel_ficha(h):
    """Ficha de un hotel: nombre, estrellas, noches, regimen, destacados y botones.
    Cada parte se muestra solo si el dato esta cargado; sin foto, la ficha queda igual de prolija."""
    nombre = _v(h, "nombre")
    cat = _v(h, "categoria")
    m = re.match(r'^(\d)\s*\*\s*(.*)$', cat)
    estrellas = ""
    if m:
        estrellas = ('<span class="hcard-st" aria-label="{n} estrellas">{st}{sup}</span>'
                     .format(n=m.group(1), st="&#9733;" * int(m.group(1)),
                             sup=" " + e(m.group(2)) if m.group(2) else ""))
    elif cat:
        estrellas = '<span class="hcard-st">{}</span>'.format(e(cat))
    arriba = [e(_v(h, "ciudad"))] if _v(h, "ciudad") else []
    if _v(h, "noches"):
        n = int(_v(h, "noches"))
        arriba.append("{} {}".format(n, "noche" if n == 1 else "noches"))
    abajo = [e(_v(h, k)) for k in ("regimen", "habitacion") if _v(h, k)]
    dest = [d.get("texto") if isinstance(d, dict) else d for d in (h.get("destacados") or [])]
    dest = [str(x).strip() for x in dest if x and str(x).strip()]
    botones = []
    if es_url(_v(h, "web")):
        botones.append('<a class="hcard-btn" href="{}" target="_blank" rel="noopener noreferrer">Ver el hotel{}</a>'
                       .format(e(_v(h, "web")), IC_EXT))
    if _v(h, "mapa"):
        botones.append('<a class="hcard-lnk" href="https://www.google.com/maps/search/?api=1&amp;query={}" '
                       'target="_blank" rel="noopener noreferrer">{}Ver en el mapa</a>'
                       .format(urllib.parse.quote(_v(h, "mapa"), safe=''), IC_PIN))
    foto = foto_hotel(h)
    L = ['      <article class="hcard{}">'.format(" con-foto" if foto else "")]
    if foto:
        L.append('        <figure class="hcard-foto"><img src="/{}" alt="{}" loading="lazy" decoding="async">'
                 '<figcaption>Foto: {}</figcaption></figure>'.format(e(foto), e(nombre), e(_v(h, "foto_credito"))))
    L.append('        <div class="hcard-body">')
    if arriba:
        L.append('          <p class="hcard-k">{}</p>'.format(" &middot; ".join(arriba)))
    L.append('          <h3 class="hcard-t">{}{}</h3>'.format(e(nombre), " " + estrellas if estrellas else ""))
    if abajo:
        L.append('          <p class="hcard-m">{}</p>'.format(" &middot; ".join(abajo)))
    if dest:
        L.append('          <ul class="hcard-d">' + "".join(
            '<li>{}<span>{}</span></li>'.format(IC_CHECK, e(x)) for x in dest) + '</ul>')
    if botones:
        L.append('          <div class="hcard-a">' + "".join(botones) + '</div>')
    L.append('        </div>')
    L.append('      </article>')
    return "\n".join(L)


def render_vuelo(v):
    cab = " &middot; ".join(x for x in [
        "<b>{}</b>".format(e(_v(v, "aerolinea"))) if _v(v, "aerolinea") else "",
        e(_v(v, "ruta"))] if x)
    datos = [(lbl, _v(v, k)) for k, lbl in [("clase", "Clase"), ("fecha", "Fecha"),
             ("horario", "Horario"), ("numero", "Vuelo"), ("equipaje", "Equipaje")] if _v(v, k)]
    if datos:
        cab += ("<br>" if cab else "") + " &middot; ".join(
            "{} {}".format(lbl, e(x)) for lbl, x in datos)
    return cab


def _sec(titulo, cuerpo, extra=""):
    return '''
<section class="dsec px">
  <div class="dwrap rv">
    <h2 class="dh2">{t}</h2>
{c}{x}
  </div>
</section>'''.format(t=titulo, c=cuerpo, x=extra)


def regiones_de(p):
    """Region principal + regiones secundarias (regiones_extra) para listados: madres y relacionados.
    La principal manda en URL, kicker, schema y chips; las extra solo suman el paquete a otras madres."""
    regs = [p["region"]]
    for r in lista(p, "regiones_extra"):
        if isinstance(r, str) and r in REGIONES and r not in regs:
            regs.append(r)
    return regs


def render_relacionados(p, todos):
    """
    P3: hasta MAX_RELACIONADOS salidas de la MISMA región que el paquete abierto,
    nunca la actual. Si no hay otras de esa región, no se muestran cards: queda
    un link al listado completo.
    """
    NL = chr(10)
    mias = set(regiones_de(p))
    elegidos = [(q, v) for q, v in todos if q["id"] != p["id"] and mias & set(regiones_de(q))][:MAX_RELACIONADOS]
    sub = "Otras salidas {}".format(REGIONES_FRASE.get(p["region"], "")).strip()
    if not elegidos:
        return NL.join([
            '',
            '<section class="dsec px">',
            '  <div class="dwrap rv">',
            '    <h2 class="dh2">{} <em>que te pueden interesar</em></h2>'.format(e(sub)),
            '    <p class="dnota">Por ahora no hay otras salidas {} publicadas. '
            '<a href="paquetes/" style="color:var(--red);font-weight:600">Ver todos los paquetes</a></p>'.format(
                e(REGIONES_FRASE.get(p["region"], ""))).replace("salidas  publicadas", "salidas publicadas"),
            '  </div>',
            '</section>',
        ])
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


# ============================================================
# Diferenciales (2026-10-22): lo que distingue a cada paquete de los parecidos.
# Campos opcionales del JSON: seo_titulo, seo_descripcion, subtitulo, por_que (lista),
# ideal_para, ver_tambien (lista de {id, texto}). Nada se inventa: lo escribe el equipo
# a partir de la ficha. Las ciudades exclusivas de los circuitos de Europa se calculan
# contra los otros circuitos ACTIVOS de la misma region.
# ============================================================
_SEP_ITIN = re.compile(r"\s[–—-]\s|\s✈\s|,\s")
_CIUDAD_IGNORAR = {"buenos aires", "madrid", "navegacion", "navegación", "embarque", "desembarque"}
_NO_ES_CIUDAD = re.compile(r"(crucero|auroras|experiencia|abadía|safari|excursi|city tour|y |visita|tren |ferry|vuelo|llegada|salida)", re.I)


def _es_ciudad(c):
    """Token de itinerario que parece un nombre de lugar: empieza en mayuscula, hasta 4 palabras, sin descriptores."""
    return bool(c) and c[0].isupper() and len(c.split()) <= 4 and not _NO_ES_CIUDAD.search(c)


def _ciudades(p):
    """Lugares de un paquete: primero los destinos cargados, despues las paradas del itinerario."""
    out = []
    for c in lista(p, "destinos"):
        c = str(c).strip()
        if c and c.lower() not in _CIUDAD_IGNORAR and c not in out:
            out.append(c)
    for i in lista(p, "itinerario"):
        if not isinstance(i, dict):
            continue
        for c in _SEP_ITIN.split(str(i.get("titulo") or "")):
            c = c.strip(" .")
            if _es_ciudad(c) and c.lower() not in _CIUDAD_IGNORAR and c not in out:
                out.append(c)
    return out


def _mismo_lugar(a, b):
    """'Santiago' ~ 'Santiago de Compostela', 'Santillana' ~ 'Santillana del Mar', 'Venecia' ~ 'Venecia (Mestre)'."""
    a, b = a.lower(), b.lower()
    return a == b or a.startswith(b + " ") or b.startswith(a + " ") or a.startswith(b + " (") or b.startswith(a + " (")


def ciudades_exclusivas(p, todos):
    """Lugares de p que ningun otro paquete activo de su region recorre (destinos + itinerario)."""
    otras = []
    for q, _v in todos:
        if q is p or q.get("id") == p.get("id") or q.get("region") != p.get("region"):
            continue
        otras.extend(_ciudades(q))
    return [c for c in _ciudades(p) if not any(_mismo_lugar(c, o) for o in otras)]


def _enumerar(items):
    items = [str(x) for x in items]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " y " + items[-1]


def render_por_que(p, todos):
    """Seccion "Por que elegir este viaje" + "Ideal para" + comparativas con links a otros paquetes activos."""
    puntos = [str(x).strip() for x in lista(p, "por_que") if str(x).strip()]
    if p.get("region") == "europa" and lista(p, "itinerario"):
        excl = ciudades_exclusivas(p, todos)[:6]
        if excl:
            puntos.insert(0, "De nuestros circuitos por Europa, solo este pasa por {}.".format(_enumerar(excl)))
    ideal = txt(p, "ideal_para")
    activos = {q.get("id") for q, _v in todos}
    titulos = {q.get("id"): txt(q, "titulo") for q, _v in todos}
    links = []
    for v in lista(p, "ver_tambien"):
        if not isinstance(v, dict) or v.get("id") not in activos or v.get("id") == p.get("id"):
            continue
        links.append('    <p class="dnota">{} <a href="paquetes/{}/" style="text-decoration:underline;text-underline-offset:3px">{}</a>.</p>'.format(
            e(str(v.get("texto") or "Mir\u00e1 tambi\u00e9n").strip().rstrip(":.,")), e(v["id"]), e(titulos[v["id"]])))
    if not (puntos or ideal or links):
        return ""
    cuerpo = ('    <ul class="dlist si">\n' + "\n".join(
        '      <li>{}<span>{}</span></li>'.format(IC_CHECK, e(x)) for x in puntos) + '\n    </ul>') if puntos else ""
    extra = ""
    if ideal:
        extra += '\n    <p class="dnota"><strong>Ideal para:</strong> {}</p>'.format(e(ideal))
    if links:
        extra += "\n" + "\n".join(links)
    return _sec("Por qu&eacute; elegir <em>este viaje</em>", cuerpo, extra)


def render_subtitulo(p):
    sub = txt(p, "subtitulo")
    return ('\n      <p class="dhero-linea dhero-sub"><b>{}</b></p>'.format(e(sub))) if sub else ""


# ============================================================
# AEO (2026-10-26): preguntas frecuentes por paquete, schema con Offer, frescura,
# respuesta directa en las madres y guias como paginas (/guias/).
# ============================================================
GUIAS_JSON = ROOT / "data" / "guias.json"
GUIAS_DIR = ROOT / "guias"
PLANTILLA_GUIA = ROOT / "data" / "_template-guia.html"
RESP_START = "<!-- RESPUESTA:START -->"
RESP_END = "<!-- RESPUESTA:END -->"
HOY_BUILD = datetime.date.today()


def fmt_fecha_larga(d):
    return "{} de {} de {}".format(d.day, MESES_NOMBRE[d.month].lower(), d.year)


def _palabras(s):
    return len(re.findall(r"[\wáéíóúñü]+", str(s), flags=re.I))


def _recortar_frases(texto, maximo=60):
    """Deja frases enteras mientras no pase de `maximo` palabras (al menos una)."""
    frases = re.split(r"(?<=[.!?])\s+", texto.strip())
    out = []
    for f in frases:
        if out and _palabras(" ".join(out + [f])) > maximo:
            break
        out.append(f)
    return " ".join(out)


def _titulo_corto(p):
    t = txt(p, "titulo")
    for corte in (" \u2014 ", " \u00b7 "):
        if corte in t:
            t = t.split(corte)[0]
    return t.strip()


def _enum(items):
    items = [str(x).strip().rstrip(".") for x in items if str(x).strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " y " + items[-1]


LEYENDA_FAQ = "La tarifa es por persona en base doble y est\u00e1 sujeta a disponibilidad al momento de la reserva."

_COMUNES_INC = {"a\u00e9reo", "a\u00e9reos", "aereo", "aereos", "traslado", "traslados", "noche", "noches", "excursi\u00f3n", "excursiones", "asistencia",
                "equipaje", "crucero", "pensi\u00f3n", "tasas", "vuelo", "vuelos", "visita", "visitas", "gu\u00eda", "gu\u00edas", "entrada", "entradas",
                "bebidas", "propinas", "comidas", "comida", "circuito", "reuni\u00f3n", "coordinador", "coordinadores", "bolso", "valija", "ferry",
                "ferries", "billetes", "tren", "trenes", "almuerzos", "cenas", "cena", "almuerzo", "parques", "parque", "city", "d\u00eda", "alojamiento",
                "habitaci\u00f3n", "paquete", "seguro", "kit", "evento", "seguimiento", "reuniones", "acompa\u00f1ante", "tour", "salida", "salidas",
                "aut\u00f3car", "autocar", "late", "early", "gastos", "servicios", "cualquier", "todos", "todas", "otros", "el", "la", "los", "las", "un", "una",
                "impuesto", "impuestos", "cobertura", "visado", "visa", "cargos", "cargo", "wi-fi", "wifi", "cabina", "p\u00e9rdida", "pensi\u00f3n"}


def _minus(item):
    """Minuscula inicial para los items comunes ('Aéreos con LATAM' -> 'aéreos con LATAM'); respeta nombres propios y siglas."""
    item = str(item).strip()
    if not item:
        return item
    primera = item.split()[0].lower().strip(",.;:")
    if item[0].isdigit() or primera in _COMUNES_INC:
        return item[0].lower() + item[1:]
    return item


def _plural_noches(texto):
    return re.sub(r"\b1 noches\b", "1 noche", texto)


def _fecha_salida_limpia(p):
    """'8 de febrero 2027 — South African Airways vía San Pablo' -> ('el 8 de febrero de 2027', True).
    Rangos y fecha a eleccion devuelven el texto limpio sin la cola."""
    s_ = txt(p, "salida")
    d = parse_salida(s_)
    base = salida_corta(s_)
    if re.match(r"^\d{1,2} de [a-z\u00e1\u00e9\u00ed\u00f3\u00fa]+ \d{4}$", base.lower()) and d:
        return "el " + fmt_fecha_larga(d)
    if re.match(r"^[a-z\u00e1\u00e9\u00ed\u00f3\u00fa]+ \d{4}$", base.lower()) and d:
        return "en {} de {}".format(MESES_NOMBRE[d.month].lower(), d.year)
    b = base[0].lower() + base[1:]
    if b.startswith("salidas "):
        return "con " + b
    if b.startswith("fecha a elecci"):
        return "en la fecha que elijas" + (", " + b.split(",", 1)[1].strip() if "," in b else "")
    return "el " + b


def _var(p, n):
    """Indice estable 0..n-1 por paquete, para variar los arranques sin cambiar los datos."""
    return sum(ord(c) for c in str(p.get("id", ""))) % n



def faq_paquete(p):
    """4 o 5 preguntas con respuesta de 40 a 60 palabras, SOLO con datos del paquete y del bloque de pagos del sitio.
    Si un dato no existe, esa pregunta no se arma."""
    corto = _titulo_corto(p)
    pd = p["precio_desde"]
    mon = pd.get("moneda", "")
    precio = "{} {}".format(mon, fmt_precio(pd.get("valor")))
    cond = [str(c) for c in lista(p, "condiciones")]
    out = []

    # 1) que incluye y que no
    inc = [str(x) for x in lista(p, "incluye")]
    noinc = [str(x) for x in lista(p, "no_incluye")]
    if inc:
        sel = []
        arranques = ["El precio desde {pr} por persona incluye {it}.",
                     "Por {pr} por persona, {co} incluye {it}.",
                     "{co} incluye, desde {pr} por persona, {it}."]
        arr = arranques[_var(p, 3)]
        for it in inc:
            prueba = arr.format(pr=precio, co=corto, it=_enum([_minus(x) for x in sel + [it]]))
            if sel and _palabras(prueba) > 42:
                break
            sel.append(it)
        ans = arr.format(pr=precio, co=corto, it=_enum([_minus(x) for x in sel]))
        if len(sel) < len(inc):
            ans += [" En el detalle figura el resto de lo incluido.", " El resto de lo incluido est\u00e1 en el detalle.", " En esta p\u00e1gina figura todo lo incluido."][_var(p, 3)]
        if noinc:
            nsel = []
            for it in noinc:
                if nsel and _palabras(ans + " No incluye {}.".format(_enum(nsel + [it]))) > 60:
                    break
                nsel.append(it)
            ans += " No incluye {}.".format(_enum([_minus(x) for x in nsel]))
        if _palabras(ans) < 40:
            ans += " " + LEYENDA_FAQ
        out.append(("\u00bfQu\u00e9 incluye {} y qu\u00e9 no?".format(corto), ans))

    # 2) documentacion y requisitos (solo si la ficha lo dice)
    doc = [c.strip() for c in cond + noinc if re.search(r"\bvisa\b|\bETA\b|vacuna|pasaporte|e-?ticket|\bDNI\b|c\u00e9dula", c, re.I)]
    doc = [c if c.endswith((".", "!", "?")) else c + "." for c in doc]   # 'Visa de Vietnam (...)' sin punto: se separa bien
    if doc:
        ans = _recortar_frases(" ".join(doc), 60)
        if _palabras(ans) < 40:
            ans += " Es un tr\u00e1mite personal de cada pasajero: consultanos antes de reservar y te confirmamos los requisitos vigentes para tu documento."
        if _palabras(ans) < 40:
            ans += " Si ten\u00e9s dudas sobre tu documentaci\u00f3n, escribinos por WhatsApp antes de reservar y lo revisamos con vos."
        ans = _recortar_frases(ans, 60)
        out.append(("\u00bfQu\u00e9 documentaci\u00f3n o requisitos necesito para {}?".format(corto), ans))

    # 2b) cuando sale, cuanto dura y donde se duerme (siempre hay dato); entra solo si hacen falta preguntas para llegar a 4
    hot = [h for h in lista(p, "hoteles") if isinstance(h, dict) and _v(h, "nombre")]
    noches = p.get("noches")
    ans_sal = ["{co} sale {fe} y dura {n} noche{s}.", "La salida de {co} es {fe}; son {n} noche{s}.", "{co} parte {fe}, con {n} noche{s} de viaje."][_var(p, 3)].format(
        co=corto, fe=_fecha_salida_limpia(p), n=noches, s="" if str(noches) == "1" else "s")
    if hot:
        partes = []
        for h in hot:
            parte = "{}{}{}".format(_v(h, "nombre"), " en " + _v(h, "ciudad") if _v(h, "ciudad") else "",
                                    " ({} noche{}, {})".format(_v(h, "noches"), "" if str(_v(h, "noches")) == "1" else "s", _v(h, "regimen").lower()) if _v(h, "noches") and _v(h, "regimen") else "")
            if partes and _palabras(ans_sal + " El alojamiento previsto es {}.".format(_enum(partes + [parte]))) > 58:
                break
            partes.append(parte)
        ans_sal += " El alojamiento previsto es {}{}.".format(_enum(partes), ", entre otros" if len(partes) < len(hot) else "")
    elif isinstance(p.get("crucero"), dict) and p["crucero"]:
        ans_sal += " Se navega a bordo del {} y las escalas son {}.".format(_v(p["crucero"], "barco") or "barco", _enum(lista(p, "destinos")[:8]))
    elif lista(p, "destinos"):
        ans_sal += " Recorre {}.".format(_enum(lista(p, "destinos")[:7]))
    aer_sal = []
    for v in lista(p, "vuelos"):
        a_ = str(v.get("aerolinea") or "").strip() if isinstance(v, dict) else ""
        if a_ and a_ not in aer_sal:
            aer_sal.append(a_)
    if aer_sal and _palabras(ans_sal) < 40:
        ans_sal += " Los vuelos son con {}.".format(_enum(aer_sal))
    if _palabras(ans_sal) < 40:
        ans_sal += " " + LEYENDA_FAQ
    ans_sal = _recortar_frases(ans_sal, 60)
    q_salida = ("\u00bfCu\u00e1ndo sale {} y en qu\u00e9 hoteles se aloja?".format(corto) if hot else "\u00bfCu\u00e1ndo sale {} y qu\u00e9 recorre?".format(corto), _plural_noches(ans_sal))

    # 3) como se paga (bloque unico de medios de pago del sitio)
    if mon == "ARS":
        ans = ["Es un paquete nacional: se paga en efectivo en pesos, por transferencia en pesos o con tarjeta de cr\u00e9dito (consultar cuotas sin inter\u00e9s vigentes).",
               "Como es un viaje dentro de Argentina, pod\u00e9s pagar en efectivo en pesos, por transferencia en pesos o con tarjeta de cr\u00e9dito (consultar cuotas sin inter\u00e9s vigentes).",
               "{} se abona en pesos: efectivo, transferencia o tarjeta de cr\u00e9dito (consultar cuotas sin inter\u00e9s vigentes).".format(corto)][_var(p, 3)]
        ans += " Tu asesora te confirma las opciones de pago y el total final al momento de la reserva."
        nota = txt(p, "nota_impuestos")
        if nota and _palabras(ans + " " + nota) <= 60:
            ans = ans.replace(" Tu asesora", " {} Tu asesora".format(nota.rstrip(".") + "."), 1)
    else:
        ans = ["Es un paquete internacional: se paga en efectivo en d\u00f3lares billete (consultar percepciones) o por transferencia en d\u00f3lares.",
               "Como todos nuestros viajes internacionales, {} se paga en efectivo en d\u00f3lares billete (consultar percepciones) o por transferencia en d\u00f3lares.".format(corto),
               "El pago es en d\u00f3lares: efectivo billete (consultar percepciones) o transferencia en d\u00f3lares."][_var(p, 3)]
        ans += (" Por lo general se reserva con una se\u00f1a y el saldo se abona hasta un mes antes de la salida. "
                "Tu asesora te confirma las opciones de pago al momento de la reserva.")
    out.append(("\u00bfC\u00f3mo se paga {}?".format(corto), ans))

    # 4) equipaje (solo si figura en los vuelos)
    vuelos = [v for v in lista(p, "vuelos") if isinstance(v, dict)]
    eqs, aers = [], []
    for v in vuelos:
        e_ = str(v.get("equipaje") or "").strip()
        if e_ and e_ not in eqs:
            eqs.append(e_)
        a_ = str(v.get("aerolinea") or "").strip()
        if a_ and a_ not in aers:
            aers.append(a_)
    if eqs:
        if all(re.match(r"^equipaje incluido", x, re.I) for x in eqs):
            ans = "Los vuelos{} tienen el equipaje incluido; la ficha no detalla el peso.".format(" de " + _enum(aers) if aers else "")
        else:
            ans = ["Los vuelos{a} incluyen {e}.", "En los vuelos{a} viaj\u00e1s con {e}.", "El equipaje incluido en los vuelos{a} es {e}."][_var(p, 3)].format(
                a=" de " + _enum(aers) if aers else "", e=_enum(eqs).lower() if not eqs[0][:1].isdigit() else _enum(eqs))
        extra = [c for c in cond if re.search(r"equipaje|valija|bolso|mochila", c, re.I)]
        if extra:
            ans = _recortar_frases(ans + " " + " ".join(extra), 60)
        if _palabras(ans) < 40:
            ans += " Si necesit\u00e1s despachar m\u00e1s equipaje, consultanos antes de la emisi\u00f3n de los pasajes y te confirmamos el costo con la aerol\u00ednea."
            ans = _recortar_frases(ans, 60)
        out.append(("\u00bfQu\u00e9 equipaje incluyen los vuelos de {}?".format(corto), ans))

    # 5) como se reserva o confirma
    cupo = [c for c in cond if re.search(r"cupo|se\u00f1a|reserv|saldo|emiten|emisi\u00f3n", c, re.I)]
    ans = ["Escribinos por WhatsApp, llamanos o complet\u00e1 el formulario de contacto: una asesora te confirma disponibilidad, la tarifa final y las opciones de pago, sin compromiso.",
           "Para reservar {}, consultanos por WhatsApp, por tel\u00e9fono o con el formulario de contacto: una asesora te confirma disponibilidad, tarifa final y opciones de pago, sin compromiso.".format(corto),
           "La reserva empieza con una consulta por WhatsApp, tel\u00e9fono o formulario: una asesora revisa disponibilidad y te confirma la tarifa final y las opciones de pago, sin compromiso."][_var(p, 3)]
    if cupo:
        ans = _recortar_frases(ans + " " + cupo[0], 48)
    ans += " El precio es desde, por persona en base doble, y est\u00e1 sujeto a disponibilidad al momento de la reserva."
    ans = _recortar_frases(ans, 60)
    out.append(("\u00bfC\u00f3mo se reserva {}?".format(corto), ans))

    if len(out) < 4 and 40 <= _palabras(q_salida[1]) <= 60:
        out.insert(1, q_salida)

    # control: 40 a 60 palabras, sin inventar: lo que no entra se descarta
    final = []
    for q, a in out:
        a = _plural_noches(a)
        n = _palabras(a)
        if 40 <= n <= 60:
            final.append((q, a))
        elif n > 60:
            a2 = _recortar_frases(a, 60)
            if 40 <= _palabras(a2) <= 60:
                final.append((q, a2))
        else:
            a2 = a + " " + LEYENDA_FAQ
            if 40 <= _palabras(a2) <= 60:
                final.append((q, a2))
    return final[:5]


def render_faq(faqs):
    if not faqs:
        return ""
    NL = chr(10)
    cuerpo = NL.join(
        '    <details class="dfaq">' + NL +
        '      <summary>{}</summary>'.format(e(q)) + NL +
        '      <p>{}</p>'.format(e(a)) + NL +
        '    </details>' for q, a in faqs)
    return _sec("Preguntas <em>frecuentes</em>", cuerpo)


def schema_faq(faqs):
    return {"@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]}


def render_actualizado(hoy=None):
    return '<p class="dnota">Actualizado el {}.</p>'.format(fmt_fecha_larga(hoy or HOY_BUILD))


def render_respuesta(carpeta, items, hoy):
    """Parrafo de respuesta directa para la madre: cantidad de salidas, rango de precios Desde por moneda
    y destinos con mas salidas. Todo calculado en el build; sin superlativos."""
    r_madre = next((reg for reg, c in REGION_MADRE.items() if c == carpeta and reg in REGIONES_FRASE), None)
    frase = REGIONES_FRASE.get(r_madre or carpeta, "a " + carpeta.replace("-", " ").title())
    n = len(items)
    por_mon = {}
    for p, v in items:
        pd = p["precio_desde"]
        por_mon.setdefault(pd.get("moneda", ""), []).append(int(pd.get("valor") or 0))
    partes = []
    for mon in ("USD", "ARS"):
        vals = [x for x in por_mon.get(mon, []) if x > 0]
        if not vals:
            continue
        if len(vals) == 1 or min(vals) == max(vals):
            partes.append("{} {} por persona".format(mon, fmt_precio(min(vals))) if len(partes) == 0 else "{} {}".format(mon, fmt_precio(min(vals))))
        else:
            partes.append("{} {} hasta {} {} por persona".format(mon, fmt_precio(min(vals)), mon, fmt_precio(max(vals))))
    rango = " y ".join(partes)
    cont = {}
    for p, v in items:
        for d in lista(p, "destinos")[:3]:
            cont[d] = cont.get(d, 0) + 1
    top = sorted(cont.items(), key=lambda kv: (-kv[1], kv[0]))[:2]
    top = [kv for kv in top if kv[1] >= 2]
    frase_dest = ""
    if top:
        frase_dest = " Los destinos con m\u00e1s salidas son " + _enum(["{} ({})".format(d, c) for d, c in top]) + "."
    texto = "Viajes {}{}: hoy tenemos {} {} publicada{} con precio desde {}.{} Cada precio es \u00abdesde\u00bb, sujeto a disponibilidad, y una asesora lo confirma por WhatsApp antes de reservar.".format(
        e(frase), "" if carpeta == "argentina" else " desde Argentina", n, "salida" if n == 1 else "salidas", "" if n == 1 else "s", rango, frase_dest)
    url = "{}/{}/".format(DOMINIO, carpeta)
    schema = json.dumps({"@context": "https://schema.org", "@type": "WebPage", "@id": url + "#webpage", "url": url,
                         "dateModified": hoy.isoformat(), "publisher": {"@id": ORG_ID}}, ensure_ascii=False)
    return "\n".join([
        RESP_START,
        '<section class="px" style="padding-top:56px;padding-bottom:0">',
        '  <div class="mx">',
        '    <div class="rv" style="max-width:860px">',
        '      <p style="font-size:18px;line-height:1.8;color:var(--ink)">{}</p>'.format(texto),
        '      <p class="dnota" style="margin-top:10px">Actualizado el {}.</p>'.format(fmt_fecha_larga(hoy)),
        '    </div>',
        '  </div>',
        '</section>',
        '<script type="application/ld+json">{}</script>'.format(schema),
        RESP_END,
    ])


def _render_guia(g, guias, publicados, plantilla, hoy):
    url = "{}/guias/{}/".format(DOMINIO, g["slug"])
    titulo = g["titulo"]
    region = g.get("region")
    madre = REGION_MADRE.get(region, region)
    rel = [p for p, v in publicados if region in regiones_de(p)][:4]
    links = []
    if madre and (ROOT / madre / "index.html").exists():
        links.append('      <li>{}<span><a href="{}/">Viajes {}: todos los destinos y salidas</a></span></li>'.format(
            IC_CHECK, e(madre), e(REGIONES_FRASE.get(region) or REGIONES_FRASE.get(madre) or ("a " + REGIONES.get(region, region)))))
    for p in rel:
        links.append('      <li>{}<span><a href="paquetes/{}/">{}</a> &middot; desde {} {}</span></li>'.format(
            IC_CHECK, e(p["id"]), e(txt(p, "titulo")), e(p["precio_desde"].get("moneda", "")), fmt_precio(p["precio_desde"].get("valor"))))
    relacionados = ('    <div class="grel">\n      <h2>Te puede interesar</h2>\n      <ul class="dlist si">\n' + "\n".join(links) + "\n      </ul>\n    </div>") if links else ""
    pub = datetime.date.fromisoformat(g["fecha_publicacion"])
    meta = "Por <strong>Equipo de Legend Travel</strong> &middot; Publicado el {} &middot; Actualizado el {}".format(
        fmt_fecha_larga(pub), fmt_fecha_larga(hoy))
    img = g.get("imagen", "")
    figura = ('    <figure class="gfig"><img src="/{}" alt="{}" loading="eager" fetchpriority="high" decoding="async"></figure>'.format(e(img), e(g.get("imagen_alt", ""))) if img else "")
    desc = g.get("descripcion") or titulo
    wa = "https://wa.me/{}?text={}".format(WA_NUMERO, urllib.parse.quote("Hola Legend Travel, le\u00ed la gu\u00eda \u00ab{}\u00bb y quiero consultar".format(titulo), safe=''))
    schema = {"@context": "https://schema.org", "@graph": [
        {"@type": "Article", "@id": url + "#article", "headline": titulo, "description": desc, "url": url, "mainEntityOfPage": url,
         "image": "{}/{}".format(DOMINIO, img) if img else "{}/og-image.jpg".format(DOMINIO),
         "datePublished": g["fecha_publicacion"], "dateModified": hoy.isoformat(), "inLanguage": "es-AR",
         "articleSection": g.get("categoria", ""),
         "author": {"@type": "Organization", "name": "Equipo de Legend Travel", "@id": ORG_ID},
         "publisher": {"@id": ORG_ID}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Inicio", "item": DOMINIO + "/"},
            {"@type": "ListItem", "position": 2, "name": "Gu\u00edas", "item": DOMINIO + "/guias/"},
            {"@type": "ListItem", "position": 3, "name": titulo, "item": url}]},
    ]}
    vals = {
        "{{TITULO_TAG}}": e(titulo if len(titulo) > 50 else titulo + " | Legend Travel"),
        "{{DESC}}": e(recortar(desc, 158)), "{{CANONICAL}}": e(url), "{{OG_TITULO}}": e(titulo), "{{OG_DESC}}": e(recortar(desc, 200)),
        "{{OGIMAGE}}": e("{}/{}".format(DOMINIO, img) if img else "{}/og-image.jpg".format(DOMINIO)), "{{ALT}}": e(g.get("imagen_alt", "")),
        "{{OG_TYPE}}": "article", "{{WA}}": e(wa), "{{CRUMB_EXTRA}}": ' <span aria-hidden="true">&rsaquo;</span> <span>{}</span>'.format(e(titulo)),
        "{{CAT}}": e(g.get("categoria", "")), "{{TITULO}}": e(titulo), "{{META}}": meta, "{{FIGURA}}": figura,
        "{{CUERPO}}": g["cuerpo_html"], "{{RELACIONADOS}}": relacionados,
        "{{SCHEMA}}": json.dumps(schema, ensure_ascii=False, separators=(',', ':')),
    }
    out = plantilla
    for k, v in vals.items():
        out = out.replace(k, v)
    return out


def _render_guias_index(guias, plantilla, hoy):
    url = DOMINIO + "/guias/"
    cards = []
    for g in guias:
        cards.append('      <a class="gcard" href="guias/{slug}/">\n        <div class="im"><img src="/{img}" alt="{alt}" loading="lazy" decoding="async"></div>\n        <div class="b"><p class="cat">{cat}</p><h2>{t}</h2><p>{d}</p><p class="d">Actualizado el {f}</p></div>\n      </a>'.format(
            slug=e(g["slug"]), img=e(g.get("imagen", "")), alt=e(g.get("imagen_alt", "")), cat=e(g.get("categoria", "")), t=e(g["titulo"]),
            d=e(recortar(g.get("descripcion") or "", 150)), f=fmt_fecha_larga(hoy)))
    cuerpo = '    <div class="glist">\n' + "\n".join(cards) + "\n    </div>"
    schema = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "@id": url + "#webpage", "url": url, "name": "Gu\u00edas y art\u00edculos de viaje", "dateModified": hoy.isoformat(), "publisher": {"@id": ORG_ID}},
        {"@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "url": "{}/guias/{}/".format(DOMINIO, g["slug"]), "name": g["titulo"]} for i, g in enumerate(guias)]},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Inicio", "item": DOMINIO + "/"},
            {"@type": "ListItem", "position": 2, "name": "Gu\u00edas", "item": url}]},
    ]}
    wa = "https://wa.me/{}?text={}".format(WA_NUMERO, urllib.parse.quote("Hola Legend Travel, quiero consultar por un viaje", safe=''))
    desc = "Gu\u00edas y art\u00edculos de viaje escritos por el equipo de Legend Travel: cu\u00e1ndo viajar, qu\u00e9 destino elegir y c\u00f3mo planificar tu viaje desde Argentina."
    vals = {
        "{{TITULO_TAG}}": "Gu\u00edas y art\u00edculos de viaje | Legend Travel", "{{DESC}}": e(desc), "{{CANONICAL}}": e(url),
        "{{OG_TITULO}}": "Gu\u00edas y art\u00edculos de viaje | Legend Travel", "{{OG_DESC}}": e(desc), "{{OGIMAGE}}": DOMINIO + "/og-image.jpg",
        "{{ALT}}": "Legend Travel", "{{OG_TYPE}}": "website", "{{WA}}": e(wa), "{{CRUMB_EXTRA}}": "",
        "{{CAT}}": "Gu\u00edas y art\u00edculos", "{{TITULO}}": "Todo lo que necesit\u00e1s saber antes de viajar",
        "{{META}}": "Escritas por el equipo de Legend Travel con datos verificados. {} gu\u00edas publicadas.".format(len(guias)),
        "{{FIGURA}}": "", "{{CUERPO}}": cuerpo, "{{RELACIONADOS}}": "",
        "{{SCHEMA}}": json.dumps(schema, ensure_ascii=False, separators=(',', ':')),
    }
    out = plantilla
    for k, v in vals.items():
        out = out.replace(k, v)
    return out.replace('<div class="art-body">', '<div class="art-body" style="margin-top:0">', 1)


def generar_guias(publicados, hoy):
    """/guias/index.html y /guias/<slug>/index.html desde data/guias.json y data/_template-guia.html."""
    if not GUIAS_JSON.exists() or not PLANTILLA_GUIA.exists():
        print("   (sin data/guias.json o plantilla: no se generan guias)")
        return []
    guias = json.loads(GUIAS_JSON.read_text(encoding="utf-8")).get("guias") or []
    plantilla = PLANTILLA_GUIA.read_text(encoding="utf-8")
    GUIAS_DIR.mkdir(exist_ok=True)
    logo = ROOT / "logo-wordmark.png"
    cambios = 0
    for g in guias:
        d = GUIAS_DIR / g["slug"]
        d.mkdir(exist_ok=True)
        for carpeta in (GUIAS_DIR, d):
            if logo.exists() and not (carpeta / "logo-wordmark.png").exists():
                shutil.copy2(logo, carpeta / "logo-wordmark.png")
        out = _render_guia(g, guias, publicados, plantilla, hoy)
        f = d / "index.html"
        if not f.exists() or f.read_text(encoding="utf-8") != out:
            f.write_text(out, encoding="utf-8"); cambios += 1
    idx = _render_guias_index(guias, plantilla, hoy)
    f = GUIAS_DIR / "index.html"
    if not f.exists() or f.read_text(encoding="utf-8") != idx:
        f.write_text(idx, encoding="utf-8"); cambios += 1
    vivos = {g["slug"] for g in guias}
    for d in GUIAS_DIR.iterdir():
        if d.is_dir() and d.name not in vivos:
            shutil.rmtree(d)
    print("OK  guias/: {} guias + indice ({} archivo(s) escritos)".format(len(guias), cambios))
    return guias


def render_detalle(p, vig, plantilla, todos=()):
    pd = p["precio_desde"]
    dests = lista(p, "destinos")
    titulo_txt = txt(p, "titulo")
    resumen = txt(p, "resumen")
    relacionados = render_relacionados(p, todos)

    # --- barra de datos rapidos (solo lo que existe) ---
    salida_v = e(p["salida"])
    if p["region"] in MAS_FECHAS_REGIONES:
        salida_v += '<span class="mas">{}</span>'.format(e(MAS_FECHAS_TXT))
    facts = [("Salida", IC_CAL, salida_v, ""),
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

    # --- hoteles (opcional). P2: nombre, categoria, noches y web oficial ---
    hot = lista(p, "hoteles")
    if hot and all(isinstance(x, dict) for x in hot):
        cuerpo_hot = '    <div class="hcards">\n' + "\n".join(render_hotel_ficha(x) for x in hot) + '\n    </div>'
    else:   # formato viejo (texto): lista simple
        cuerpo_hot = ('    <ul class="dlist si">\n' + "\n".join(
            '      <li>{}<span>{}</span></li>'.format(IC_HOTEL, render_hotel(x)) for x in hot) + '\n    </ul>')
    hoteles_html = _sec(
        "Hoteles <em>previstos</em>",
        cuerpo_hot,
        '\n    <p class="dnota">Hoteles previstos o similares, sujetos a disponibilidad '
        'al momento de la reserva.</p>') if hot else ""

    # --- vuelos (opcional). P2: aerolinea, clase, fecha, horario, numero, equipaje ---
    vue = [v for v in lista(p, "vuelos") if isinstance(v, dict) and any(_v(v, k) for k in VUELO_CAMPOS)]
    vuelos_html = _sec(
        "Los <em>vuelos</em>",
        '    <ul class="dlist si">\n' + "\n".join(
            '      <li>{}<span>{}</span></li>'.format(IC_CHECK, render_vuelo(v)) for v in vue)
        + '\n    </ul>') if vue else ""

    # --- crucero (opcional). P2: naviera, barco, cabina, bebidas, propinas, wifi, asistencia, web ---
    cru = p.get("crucero") if isinstance(p.get("crucero"), dict) else {}
    filas_cru = [(lbl, _v(cru, k)) for k, lbl in CRUCERO_CAMPOS if _v(cru, k)]
    crucero_html = ""
    if filas_cru:
        web = _v(cru, "web")
        extra = ('\n    <p class="dnota"><a href="{}" target="_blank" rel="noopener noreferrer" '
                 'style="color:var(--red);font-weight:600">Web oficial de {}</a></p>'.format(
                     e(web), e(_v(cru, "naviera") or "la naviera"))) if es_url(web) else ""
        crucero_html = _sec("El <em>crucero</em>", '    <dl class="dtar dtar-info">\n' + "\n".join(
            '      <div><dt>{}</dt><dd>{}</dd></div>'.format(lbl, e(v)) for lbl, v in filas_cru)
            + '\n    </dl>', extra)

    # --- precios por base (P1) + otras tarifas que no son una base ---
    filas = []
    precios = [x for x in lista(p, "precios") if isinstance(x, dict) and x.get("base") in BASES]
    # single, doble, triple, cuadruple; en cruceros se respeta el orden de cabinas cargado
    if not any(x.get("cabina") for x in precios):
        precios.sort(key=lambda x: BASES_ORDEN.index(x["base"]))
    mon = e(pd.get("moneda", ""))
    for x in precios:
        etq = BASES[x["base"]]
        if x.get("cabina"):
            etq = "Cabina {} &middot; {}".format(e(str(x["cabina"]).lower()), etq.lower())
        # se resalta la fila del precio destacado (base doble, la cabina mas economica)
        on = ' class="on"' if x["base"] == "doble" and x["valor"] == pd.get("valor") else ""
        filas.append('      <div{}><dt>{}</dt><dd>Desde {} {}</dd></div>'.format(on, etq, mon, fmt_precio(x["valor"])))
    for t in lista(p, "tarifas"):
        if isinstance(t, dict):
            precio_t = str(t.get("precio") or "").strip()
            if re.match(r"^(USD|ARS|EUR)\s", precio_t):   # toda cifra de paquete va con "Desde"
                precio_t = "Desde " + precio_t
            filas.append('      <div><dt>{}</dt><dd>{}</dd></div>'.format(
                e(str(t.get("etiqueta") or "")), e(precio_t)))
    tarifas_html = ""
    if filas:
        nota = txt(p, "nota_impuestos")
        extra = '\n    <p class="dnota">{}</p>'.format(e(nota)) if nota else ""
        extra += '\n    <p class="dnota">Precios por persona. {}</p>'.format(LEYENDA_PRECIO)
        tarifas_html = _sec("Precios <em>por persona</em>" if precios else "Tarifas",
                            '    <dl class="dtar{}">\n'.format(" dtar-base" if precios else "")
                            + "\n".join(filas) + '\n    </dl>', extra)

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
    canonical = "{}/paquetes/{}/".format(DOMINIO, p["id"])
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
    pdv = p["precio_desde"]
    vig_iso = vig.isoformat() if hasattr(vig, "isoformat") else str(vig)
    trip["offers"] = {
        "@type": "Offer", "price": int(pdv.get("valor") or 0), "priceCurrency": pdv.get("moneda", ""),
        "validThrough": vig_iso, "availability": "https://schema.org/InStock", "url": canonical,
        "priceSpecification": {"@type": "PriceSpecification", "price": int(pdv.get("valor") or 0), "priceCurrency": pdv.get("moneda", ""),
                               "description": "Precio desde por persona en base doble. " + LEYENDA_PRECIO},
    }
    faqs = faq_paquete(p)
    grafo = [
        {"@type": "WebPage", "@id": canonical + "#webpage", "url": canonical, "name": titulo_txt,
         "dateModified": HOY_BUILD.isoformat(), "publisher": {"@id": ORG_ID}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Inicio", "item": DOMINIO + "/"},
            {"@type": "ListItem", "position": 2, "name": "Paquetes", "item": DOMINIO + "/paquetes/"},
            {"@type": "ListItem", "position": 3, "name": titulo_txt, "item": canonical},
        ]},
        trip,
    ]
    if faqs:
        grafo.append(schema_faq(faqs))
    schema = json.dumps({"@context": "https://schema.org", "@graph": grafo}, ensure_ascii=False, separators=(',', ':'))

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
    # P2: foto de portada propia del detalle (en cruceros, la oficial del barco) si esta cargada
    if txt(p, "foto_portada"):
        img_hero = txt(p, "foto_portada")
    if "images.pexels.com" in img_hero:
        img_hero = re.sub(r'([?&]w=)\d+', r'\g<1>2200', img_hero)
    elif img_hero.startswith("assets/img/pexels/"):
        # foto local (tools/fotos_locales.py): se usa la variante grande si existe
        grande = re.sub(r'-\d+\.jpg$', '-1800.jpg', img_hero)
        if (ROOT / grande).exists():
            img_hero = grande
        # ruta absoluta: el navegador pide esta foto antes de leer el <base> y una ruta relativa daba 404 en /paquetes/<id>/
        img_hero = "/" + img_hero
    elif not es_url(img_hero) and not img_hero.startswith("/"):
        img_hero = "/" + img_hero   # misma razon: se pide antes de leer el <base>

    vals = {
        "{{IMAGEN_HERO}}": e(img_hero),
        "{{TITULO_TAG}}": e(txt(p, "seo_titulo") or titulo_tag(titulo_txt)),
        "{{OG_TITULO}}": e(html.unescape(og_titulo)),
        "{{OG_DESC}}": e(resumen),
        "{{TITULO_TXT}}": e(titulo_txt),
        "{{TITULO}}": e(titulo_txt),
        "{{HERO_MADRE}}": hero_madre,
        "{{URGENCIA}}": urgencia,
        "{{RELACIONADOS}}": relacionados,
        "{{DESC}}": e(txt(p, "seo_descripcion") or desc),
        "{{SUBTITULO}}": render_subtitulo(p),
        "{{FAQ}}": render_faq(faqs),
        "{{ACTUALIZADO}}": render_actualizado(),
        "{{POR_QUE}}": render_por_que(p, todos),
        "{{ALT}}": e(alt_imagen(p)),
        "{{KICKER}}": e(REGIONES.get(p["region"], p["region"])),
        "{{CANONICAL}}": e(canonical),
        "{{OGIMAGE}}": e(ogimg),
        "{{IMAGEN}}": e(p["imagen"]),
        "{{HERO_LINEA}}": hero_linea,
        "{{MONEDA}}": e(pd.get("moneda", "")),
        "{{PRECIO}}": fmt_precio(pd.get("valor")),
        "{{PRECIO_NOTA}}": ('<span class="nota">{}</span>'.format(e(pnota)) if pnota else "")
                          + '<span class="sujeto">{}</span>'.format(LEYENDA_PRECIO),
        # codigo interno de referencia (KM-1145, GEA, ...): solo en el detalle, chiquito, nunca en cards ni en WhatsApp
        "{{CODIGO}}": ('<span class="cod">C&oacute;d. {}</span>'.format(e(txt(p, "codigo_ref")))
                       if txt(p, "codigo_ref") else ""),
        "{{CODIGO_REF}}": e(txt(p, "codigo_ref")),
        "{{NFACTS}}": str(len(facts)),
        "{{DATOS}}": datos,
        "{{RESUMEN}}": e(resumen),
        "{{ITINERARIO}}": itin_html,
        "{{INCLUYE}}": incluye_html,
        "{{NO_INCLUYE}}": noinc_html,
        "{{HOTELES}}": hoteles_html,
        "{{VUELOS}}": vuelos_html,
        "{{CRUCERO}}": crucero_html,
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
def validar_detalle(p):
    """Formato de los campos de P1/P2. Devuelve la lista de problemas."""
    err = []
    pr = p.get("precios", [])
    if not isinstance(pr, list):
        err.append('"precios" tiene que ser una lista')
    else:
        for x in pr:
            if not isinstance(x, dict) or x.get("base") not in BASES:
                err.append('precios: base "{}" no es single, doble, triple ni cuadruple'.format(
                    x.get("base") if isinstance(x, dict) else x))
            elif not isinstance(x.get("valor"), int) or x["valor"] <= 0:
                err.append('precios: el valor de la base {} tiene que ser un numero entero'.format(x["base"]))
    for campo, claves in (("hoteles", HOTEL_CAMPOS), ("vuelos", VUELO_CAMPOS)):
        val = p.get(campo, [])
        if not isinstance(val, list):
            err.append('"{}" tiene que ser una lista'.format(campo))
            continue
        for x in val:
            if isinstance(x, str) and campo == "hoteles":
                continue   # formato viejo, se sigue aceptando
            if not isinstance(x, dict) or set(x) - set(claves):
                err.append('{}: campos no reconocidos {}'.format(
                    campo, sorted(set(x) - set(claves)) if isinstance(x, dict) else x))
            elif campo == "hoteles" and _v(x, "id") and not re.match(r'^[a-z0-9-]+$', _v(x, "id")):
                err.append('hoteles: el id "{}" tiene que ser slug (a-z 0-9 -): nombra la foto'.format(_v(x, "id")))
            elif campo == "hoteles" and not isinstance(x.get("destacados", []), list):
                err.append('hoteles: "destacados" de {} tiene que ser una lista'.format(_v(x, "nombre")))
            elif campo == "hoteles" and _v(x, "noches") and not _v(x, "noches").isdigit():
                err.append('hoteles: noches "{}" tiene que ser un numero'.format(_v(x, "noches")))
            elif _v(x, "web") and not es_url(_v(x, "web")):
                err.append('{}: la web "{}" tiene que empezar con https://'.format(campo, _v(x, "web")))
    cru = p.get("crucero", {})
    if cru not in (None, {}) and not isinstance(cru, dict):
        err.append('"crucero" tiene que ser un objeto')
    elif cru and _v(cru, "web") and not es_url(_v(cru, "web")):
        err.append('crucero: la web "{}" tiene que empezar con https://'.format(_v(cru, "web")))
    foto = txt(p, "foto_portada")
    if foto and not es_url(foto) and not (ROOT / foto.lstrip("/")).exists():
        err.append('foto_portada "{}" no existe'.format(foto))
    return err


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
        err = validar_detalle(p)
        if err:
            errores.extend("{}: {}".format(ident, x) for x in err)
            continue
        # P1: el precio destacado es siempre el de base doble (en cruceros, la cabina mas economica)
        dobles = [x["valor"] for x in lista(p, "precios") if x.get("base") == "doble"]
        if dobles:
            p["precio_desde"]["valor"] = min(dobles)

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
        for r in lista(p, "regiones_extra"):
            if not isinstance(r, str) or r not in REGIONES:
                avisos.append('{}: regiones_extra "{}" no esta en el mapa de REGIONES (se ignora)'.format(ident, r))
        for h in lista(p, "hoteles"):   # foto de hotel sin credito: no se muestra y se avisa
            if isinstance(h, dict) and _v(h, "id") and not _v(h, "foto_credito") and any(
                    (HOTEL_FOTOS / "{}.{}".format(_v(h, "id"), x)).exists() for x in ("jpg", "jpeg", "webp", "png")):
                avisos.append('{}: la foto del hotel "{}" no se muestra porque falta "foto_credito"'.format(ident, _v(h, "nombre")))

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
LLMS_FULL = ROOT / "llms-full.txt"


def _texto_plano(frag):
    """Líneas de texto de un fragmento de HTML, sin scripts, estilos ni etiquetas."""
    s = re.sub(r"<(script|style|svg|nav)\b.*?</\1>", "", frag, flags=re.S)
    s = re.sub(r'<a\b[^>]*class="[^"]*\b(btn|tlink)\b[^"]*"[^>]*>.*?</a>', "", s, flags=re.S)   # botones/CTA
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"</?(h[1-6]|p|li|div|section|article|figcaption|dt|dd)\b[^>]*>", "\n", s)
    s = re.sub(r'<span\b[^>]*class="[^"]*\bchip\b[^"]*"[^>]*>', "\n", s)   # cada chip, una línea
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))   # inline (span, b, em, a…): un espacio, no se pegan palabras
    s = re.sub(r"[ \t\xa0]+", " ", s)
    s = re.sub(r" ([.,;:!?])", r"\1", s)
    return [l.strip() for l in s.split("\n") if l.strip()]


def _seccion(texto_html, id_):
    m = re.search(r'<section\b[^>]*\bid="' + re.escape(id_) + r'".*?</section>', texto_html, flags=re.S)
    return m.group(0) if m else ""


def _faqs_de(texto_html):
    """Preguntas y respuestas de una página: del FAQPage (JSON-LD) si lo declara;
    si no, de los desplegables .faq de la sección de preguntas."""
    out = []
    for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', texto_html, flags=re.S):
        try:
            d = json.loads(b)
        except ValueError:
            continue
        nodos = (d.get("@graph") or [d]) if isinstance(d, dict) else d
        for n in nodos:
            if isinstance(n, dict) and n.get("@type") == "FAQPage":
                for q in n.get("mainEntity") or []:
                    a = (q.get("acceptedAnswer") or {}).get("text", "")
                    if q.get("name") and a:
                        out.append((q["name"].strip(), " ".join(_texto_plano(a))))
    if out:
        return out
    for m in re.finditer(r'<div class="faq(?: [^"]*)?">\s*<button[^>]*>(.*?)<span class="pm".*?<div class="ans">(.*?)</div>\s*</div>',
                         texto_html, flags=re.S):
        q, a = _texto_plano(m.group(1)), _texto_plano(m.group(2))
        if q and a:
            out.append((" ".join(q), " ".join(a)))
    return out


def _paginas_publicadas():
    """Las páginas que build-tanda.py publica (misma configuración: servicios completos +
    madres), para que llms-full.txt describa solo lo que está online."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("build_tanda", ROOT / "build-tanda.py")
    bt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bt)
    paginas = [("", ROOT / "index.html")]
    for d in bt.FULL_DIRS:
        if d in bt.SITEMAP_EXCLUIR:
            continue
        for f in sorted((ROOT / d).rglob("index.html")):
            if f.stat().st_size and f.parent.name != "data":
                paginas.append((f.parent.relative_to(ROOT).as_posix() + "/", f))
    for d in bt.MADRE_DIRS:
        f = ROOT / d / "index.html"
        if f.exists():
            paginas.append((d + "/", f))
    return paginas


DOCS_VUELOS = ROOT / "docs" / "vuelos-faltantes.md"


def generar_vuelos_faltantes(publicados, hoy):
    """
    P5: docs/vuelos-faltantes.md (no se publica). Un bloque por paquete activo
    al que le falte algún dato de vuelos (aerolínea, ida, vuelta o equipaje),
    listo para pegar en WhatsApp y que el operador lo complete. Lo que ya está
    cargado va precargado; lo que falta queda en blanco. Los cruceros con
    embarque en Buenos Aires no llevan vuelos y no entran.
    """
    NL = chr(10)

    def tramo(v):
        return " · ".join(x for x in (_v(v, "fecha"), _v(v, "horario"), _v(v, "numero")) if x)

    bloques, completos = [], []
    for p, vig in publicados:
        if p.get("region") == "cruceros":
            continue
        vue = [v for v in lista(p, "vuelos") if isinstance(v, dict)]
        con_datos = [v for v in vue if tramo(v)]
        campos = [
            ("Aerolínea", ", ".join(sorted({_v(v, "aerolinea") for v in vue if _v(v, "aerolinea")}))),
            ("Vuelo de ida (fecha, horario, número)", tramo(con_datos[0]) if con_datos else ""),
            ("Vuelo de vuelta (fecha, horario, número)", tramo(con_datos[1]) if len(con_datos) > 1 else ""),
            ("Equipaje incluido (valija en bodega / carry on / solo mochila)",
             ", ".join(sorted({_v(v, "equipaje") for v in vue if _v(v, "equipaje")}))),
        ]
        if all(val for _, val in campos):
            completos.append(txt(p, "titulo"))
            continue
        contexto = [("{} {}".format(_v(v, "aerolinea"), _v(v, "ruta"))).strip() for v in vue if _v(v, "ruta")]
        bloques.append(NL.join(
            ["### {}".format(txt(p, "titulo")), ""]
            + (["Cargado hoy: " + " / ".join(contexto), ""] if contexto else [])
            + ["```", "*{} — salida {}*".format(txt(p, "titulo"), salida_corta(p["salida"]))]
            + ["{}: {}".format(k, val).rstrip() for k, val in campos]
            + ["```", ""]))
    t = NL.join([
        "# Vuelos faltantes por paquete",
        "",
        "Generado el {} por build-paquetes.py desde data/paquetes.json (se rehace en cada build; no editar a mano).".format(hoy.isoformat()),
        "Copiar el bloque de cada paquete y pegarlo en WhatsApp para que el operador lo complete.",
        "Después, cargar la respuesta en `vuelos` del paquete (aerolinea, fecha, horario, numero, equipaje) y correr el build.",
        "Los cruceros con embarque en Buenos Aires no llevan vuelos y no figuran.",
        "",
    ] + bloques + (["Con los vuelos completos: " + "; ".join(completos), ""] if completos else [])) + NL
    DOCS_VUELOS.parent.mkdir(exist_ok=True)
    if not DOCS_VUELOS.exists() or DOCS_VUELOS.read_text(encoding="utf-8") != t:
        DOCS_VUELOS.write_text(t, encoding="utf-8")
        print("OK  docs/vuelos-faltantes.md ({} paquetes con datos de vuelo por completar)".format(len(bloques)))
    else:
        print("=   docs/vuelos-faltantes.md sin cambios")


def generar_llms_full(publicados, hoy):
    """
    Escribe llms-full.txt completo a partir de los MISMOS datos que llms.txt:
    la parte fija de llms.txt (agencia, destinos, servicios, guías, contacto),
    historia/valores/local de /quienes-somos/, medios de pago de la home, el
    detalle de cada paquete activo (data/paquetes.json) y las FAQ de cada página
    publicada. Se regenera entero en cada build: nunca se edita a mano.
    """
    NL = chr(10)
    base = LLMS.read_text(encoding="utf-8") if LLMS.exists() else "# Legend Travel" + NL
    fijo = re.sub(re.escape(LLMS_START) + r".*?" + re.escape(LLMS_END) + r"\s*", "", base, flags=re.S)
    fijo = re.sub(r"\nVersión completa \([^\n]*llms-full\.txt\n", "\n", fijo)   # el link a este mismo archivo no va acá
    fijo = fijo.replace("# Legend Travel", "# Legend Travel — versión completa (llms-full.txt)", 1).rstrip()
    L = [fijo, "",
         "Generado el {} por build-paquetes.py. Resumen corto: {}/llms.txt".format(hoy.isoformat(), DOMINIO), ""]

    qs = ROOT / "quienes-somos" / "index.html"
    qs_html = qs.read_text(encoding="utf-8") if qs.exists() else ""
    for id_, titulo in (("historia", "Historia"), ("valores", "Valores"), ("local", "Dónde estamos")):
        lineas = _texto_plano(_seccion(qs_html, id_))
        if lineas:
            L += ["## " + titulo] + ["- " + l for l in lineas[1:] if l not in ("Ver en Google Maps",)] + [""]
    home_html = (ROOT / "index.html").read_text(encoding="utf-8")
    pago = _texto_plano(_seccion(home_html, "financiacion"))
    if pago:
        L += ["## Medios de pago"] + ["- " + l for l in pago[1:]] + [""]

    L += ["## Paquetes y salidas vigentes (detalle)",
          "Precios por persona. " + LEYENDA_PRECIO + " Solo salidas vigentes al {}.".format(fmt_fecha_ar(hoy)), ""]
    for p, vig in publicados:
        pd = p.get("precio_desde") or {}
        mon = pd.get("moneda", "")
        precios = {str(x.get("base", "")).lower(): x.get("valor") for x in (p.get("precios") or []) if isinstance(x, dict)}
        doble = precios.get("doble", pd.get("valor"))
        L.append("### " + txt(p, "titulo"))
        L.append("- URL: {}/paquetes/{}/".format(DOMINIO, p["id"]))
        if lista(p, "destinos"):
            L.append("- Destinos: " + ", ".join(lista(p, "destinos")))
        L.append("- Salida: {}{}{}".format(p.get("salida", ""), " · {} noches".format(p["noches"]) if p.get("noches") else "",
                 " · Otras fechas: consultar (" + MAS_FECHAS_TXT.rstrip(".").lower() + ")" if p["region"] in MAS_FECHAS_REGIONES else "")
                 + (" · Régimen: " + txt(p, "regimen") if txt(p, "regimen") else ""))
        base_ppal = "doble" if ("doble" in precios or not precios) else next(iter(precios))
        if base_ppal != "doble":
            doble = precios[base_ppal]
        L.append("- Precio: desde {} {} por persona en base {}{}".format(mon, fmt_precio(doble), base_ppal,
                 " ({})".format(pd["nota"]) if pd.get("nota") else ""))
        if lista(p, "por_que"):
            L.append("- Por qu\u00e9 elegirlo: " + "; ".join(str(x).strip().rstrip(".") for x in lista(p, "por_que")) + ".")
        if txt(p, "ideal_para"):
            L.append("- Ideal para: " + txt(p, "ideal_para"))
        for base_, val in precios.items():
            if base_ != base_ppal and val:
                L.append("- Precio: desde {} {} por persona en base {}".format(mon, fmt_precio(val), base_))
        if txt(p, "nota_impuestos"):
            L.append("- Impuestos: " + txt(p, "nota_impuestos"))
        if lista(p, "incluye"):
            L.append("- Incluye: " + "; ".join(lista(p, "incluye")))
        if lista(p, "no_incluye"):
            L.append("- No incluye: " + "; ".join(lista(p, "no_incluye")))
        for h in p.get("hoteles") or []:
            if not isinstance(h, dict) or not _v(h, "nombre"):
                continue
            datos = [x for x in (_v(h, "ciudad"), _v(h, "categoria"),
                                 "{} noches".format(h["noches"]) if h.get("noches") else "",
                                 _v(h, "regimen"), _v(h, "habitacion")) if x]
            dest = [_v(x, "texto") if isinstance(x, dict) else str(x) for x in (h.get("destacados") or [])]
            L.append("- Hotel: {}{}{}".format(_v(h, "nombre"), " (" + ", ".join(datos) + ")" if datos else "",
                                               " — " + "; ".join(d for d in dest if d) if dest else ""))
        if txt(p, "resumen"):
            L.append("- Resumen: " + txt(p, "resumen"))
        L.append("- Vigente hasta: " + fmt_fecha_ar(vig))
        L.append("")
    if not publicados:
        L += ["En este momento no hay salidas publicadas. Consultar por WhatsApp.", ""]
    L.append("Listado completo: {}/paquetes/".format(DOMINIO))
    L.append("")

    L += ["## Preguntas frecuentes por página", ""]
    n_faq = 0
    for ruta, f in _paginas_publicadas():
        texto = f.read_text(encoding="utf-8")
        faqs = _faqs_de(texto)
        if not faqs:
            continue
        m = re.search(r"<title>(.*?)</title>", texto, flags=re.S)
        titulo = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip() if m else ruta or "Inicio"
        L.append("### {} — {}/{}".format(titulo, DOMINIO, (ruta.rstrip("/") + "/") if ruta else ""))
        for q, a in faqs:
            L.append("- P: {}".format(q))
            L.append("  R: {}".format(a))
            n_faq += 1
        L.append("")

    nuevo = NL.join(L).rstrip() + NL
    if not LLMS_FULL.exists() or LLMS_FULL.read_text(encoding="utf-8") != nuevo:
        LLMS_FULL.write_text(nuevo, encoding="utf-8")
        print("OK  llms-full.txt generado ({} paquetes, {} preguntas)".format(len(publicados), n_faq))
    else:
        print("=   llms-full.txt sin cambios")


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
        bases = [x["base"] for x in lista(p, "precios") if isinstance(x, dict)]
        base_txt = "" if ("doble" in bases or not bases) else " (base {})".format(bases[0])
        filas.append("- {titulo} — desde {mon} {val}{base} — Salida: {sal} — {url}".format(
            titulo=txt(p, "titulo"), mon=pd.get("moneda", ""), base=base_txt,
            val=fmt_precio(pd.get("valor")), sal=salida_corta(p["salida"]),
            url="{}/paquetes/{}/".format(DOMINIO, p["id"])))

    bloque = NL.join([
        LLMS_START,
        "## Salidas y paquetes actuales",
        "Generado el {} desde data/paquetes.json. Solo salidas vigentes:".format(hoy.isoformat()),
        "lo inactivo o vencido se retira de esta lista automáticamente.",
        "Precios por persona en base doble, salvo que el paquete indique otra base. " + LEYENDA_PRECIO,
        "",
    ] + filas + [
        "",
        "Listado completo: {}/paquetes/".format(DOMINIO),
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

    # Páginas de destino publicadas (tanda 2): entre marcadores, antes de "## Servicios". Salen de
    # data/destinos-paises.json ("publicar": true); llms-full.txt las hereda con la parte fija.
    D_START, D_END = "<!-- DESTINOS:START -->", "<!-- DESTINOS:END -->"
    pubs = [(r, c) for r, c in cargar_paises().items() if c.get("publicar")]
    if pubs:
        bloque_d = NL.join([D_START, "## Páginas de destino",
                            "Páginas propias con guía de viaje, requisitos y las salidas publicadas de cada destino:"] +
                           ["- {}: {}/{}/".format(c["nombre"], DOMINIO, r) for r, c in pubs] + [D_END])
        if D_START in t and D_END in t:
            t = reemplazar_bloque(t, D_START, D_END, bloque_d)
        elif "## Servicios" in t:
            t = t.replace("## Servicios", bloque_d + NL + NL + "## Servicios", 1)

    # Link a la versión completa (llms-full.txt), una sola vez, antes de "## Destinos".
    if "llms-full.txt" not in t and "## Destinos" in t:
        t = t.replace("## Destinos", "Versión completa (historia, medios de pago, detalle de cada paquete con hoteles y las FAQ de cada página): {}/llms-full.txt".format(DOMINIO) + NL + NL + "## Destinos", 1)

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
.rsG-more{margin-top:40px;display:flex;flex-wrap:wrap;align-items:center;gap:18px 28px}
</style>"""
# Carrusel de la home: mismo carril con scroll-snap que .bento (Destinos) en mobile,
# flechas desde 1024 px, teclado (←/→, Inicio/Fin) y sin autoplay.
RS_CAR_CSS = """<style>
#pasajeros .kicker{font-size:12px;font-weight:700;letter-spacing:.26em;text-transform:uppercase;color:var(--red);margin-bottom:16px}
#pasajeros .kicker::before{content:'// '}
.rsC-head{display:flex;align-items:flex-end;justify-content:space-between;gap:24px}
.rsC-nav{display:none;gap:10px;flex:none}
.rsC-btn{width:52px;height:52px;border-radius:50%;border:0;background:#fff;color:var(--ink);box-shadow:inset 0 0 0 1px var(--line);display:grid;place-items:center;cursor:pointer;transition:background .4s var(--ease),color .3s,box-shadow .3s,opacity .3s}
.rsC-btn svg{width:18px;height:18px}
.rsC-btn:hover:not([aria-disabled="true"]){background:var(--red);color:#fff;box-shadow:none}
.rsC-btn:focus-visible{outline:2px solid var(--gold);outline-offset:3px}
.rsC-btn[aria-disabled="true"]{opacity:.35;cursor:default}
.rsC-track{display:flex;align-items:stretch;gap:14px;margin:42px calc(-1*var(--gutter)) -34px;padding:6px var(--gutter) 34px;overflow-x:auto;scroll-snap-type:x mandatory;scroll-padding-inline:var(--gutter);scrollbar-width:none;-webkit-overflow-scrolling:touch;overscroll-behavior-x:contain}
.rsC-track::-webkit-scrollbar{display:none}
.rsC-track:focus-visible{outline:2px solid var(--gold);outline-offset:-2px;border-radius:var(--r-lg)}
.rsC-slide{flex:0 0 86%;scroll-snap-align:start}
.rsC-bar{position:relative;height:2px;margin-top:30px;border-radius:2px;background:var(--line);overflow:hidden}
.rsC-bar i{position:absolute;left:0;top:0;bottom:0;width:33%;border-radius:2px;background:var(--red)}
@media(min-width:720px){.rsC-track{gap:18px}.rsC-slide{flex-basis:calc((100% - 18px)/2)}}
@media(min-width:1024px){.rsC-nav{display:flex}.rsC-track{margin-left:-2px;margin-right:-2px;padding-left:2px;padding-right:2px;scroll-padding-inline:2px}}
@media(min-width:1100px){.rsC-track{gap:22px}.rsC-slide{flex-basis:calc((100% - 44px)/3)}}
/* Escritorio (>=1280): la seccion entra completa en una pantalla (zoom 100%) */
@media(min-width:1280px) and (min-height:560px){
  #pasajeros{--pt:clamp(12px,2.6vh,44px);--pb:clamp(16px,3.4vh,56px);min-height:100vh;min-height:100svh;padding:calc(var(--nav-h) + var(--pt)) 0 var(--pb);display:flex;align-items:center}
  #pasajeros>.wrap{width:100%}
  #pasajeros .kicker{margin-bottom:clamp(8px,1.8vh,16px)}
  #pasajeros .h2{font-size:clamp(34px,min(5vw,8.5vh),72px)}
  #pasajeros .rsC-track{margin-top:clamp(14px,3.2vh,42px)}
  #pasajeros .rsG-card{padding:clamp(18px,2.6vh,30px) clamp(20px,2.2vw,30px);gap:clamp(10px,1.6vh,16px)}
  #pasajeros .rsG-card p{font-size:clamp(13.5px,1.8vh,15.5px);line-height:1.5;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:9;overflow:hidden}
  #pasajeros .rsC-bar{margin-top:clamp(14px,2.6vh,30px)}
  #pasajeros .rsG-more{margin-top:clamp(14px,3vh,40px)}
}
</style>"""
RS_CAR_JS = """<script>
(function(){
  var tr=document.getElementById('rsC-track');if(!tr)return;
  var prev=document.querySelector('.rsC-btn[data-dir="-1"]'),next=document.querySelector('.rsC-btn[data-dir="1"]');
  var bar=document.querySelector('.rsC-bar i'),slides=tr.querySelectorAll('.rsC-slide');
  var reduce=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function paso(){var g=parseFloat(getComputedStyle(tr).columnGap)||0;return slides.length?slides[0].getBoundingClientRect().width+g:tr.clientWidth}
  function ir(x){tr.scrollTo({left:x,behavior:reduce?'auto':'smooth'})}
  function mover(dir){ir(tr.scrollLeft+dir*paso())}
  function estado(){
    var max=tr.scrollWidth-tr.clientWidth;
    prev.setAttribute('aria-disabled',tr.scrollLeft<=2?'true':'false');
    next.setAttribute('aria-disabled',tr.scrollLeft>=max-2?'true':'false');
    var r=max>0?tr.clientWidth/tr.scrollWidth:1;   /* barra de avance: ancho = parte visible, posición = scroll */
    bar.style.width=(r*100)+'%';
    bar.style.transform='translateX('+(max>0?tr.scrollLeft/max*(1-r)/r*100:0)+'%)';
  }
  prev.addEventListener('click',function(){mover(-1)});
  next.addEventListener('click',function(){mover(1)});
  tr.addEventListener('keydown',function(e){
    var k=e.key;
    if(k==='ArrowRight'||k==='ArrowLeft'){e.preventDefault();mover(k==='ArrowRight'?1:-1)}
    else if(k==='Home'||k==='End'){e.preventDefault();ir(k==='Home'?0:tr.scrollWidth)}
  });
  tr.addEventListener('scroll',estado,{passive:true});
  window.addEventListener('resize',estado);
  estado();
})();
</script>"""
RS_FLECHA_IZQ = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" '
                 'stroke-linejoin="round" aria-hidden="true"><path d="M19 12H5m6-6-6 6 6 6"/></svg>')
RS_FLECHA_DER = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" '
                 'stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6"/></svg>')


def actualizar_resenas():
    """
    Reescribe "Nuestros pasajeros" con las reseñas de data/resenas-google.json:
    en index.html todas, en un carrusel (entre RS_START y RS_END: lo visible coincide con el schema),
    y en quienes-somos/index.html todas, en grilla.
    El schema va siempre en UNA sola entidad TravelAgency por página (entre RSS_START y RSS_END), con
    aggregateRating ("calificacion") y review (todas): separarlos dispara "Varias reseñas sin el objeto
    aggregateRating" en Search Console. Para sumar una reseña alcanza con editar el JSON
    y volver a correr este script: no se toca HTML a mano.
    """
    if not RES_JSON.exists():
        print("\n!  no existe data/resenas-google.json — salteado")
        return
    data = json.loads(RES_JSON.read_text(encoding="utf-8"))
    rs = [r for r in data.get("resenas", []) if str(r.get("nombre", "")).strip() and str(r.get("texto", "")).strip()]
    url = str(data.get("url_google") or "").strip()
    FLECHA = ('<span class="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" '
              'stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14m-6-6 6 6-6 6"/></svg></span>')
    GEN = "<!-- Generado por build-paquetes.py desde data/resenas-google.json. NO editar a mano: se pisa. -->"

    def iniciales(nombre):
        partes = [p for p in nombre.replace("-", " ").split() if p]
        return (partes[0][0] + (partes[1][0] if len(partes) > 1 else "")).upper()

    def estrellas(r):
        return max(1, min(5, int(r.get("estrellas", 5) or 5)))

    def cards(lista, carrusel=False):
        out = []
        for i, r in enumerate(lista):
            n = estrellas(r)
            # en el carrusel las tarjetas no llevan .rv: las que arrancan fuera de pantalla
            # (a la derecha) nunca dispararían el IntersectionObserver y quedarían invisibles
            abre = ('<article class="rsG-card rsC-slide" role="group" aria-roledescription="reseña" '
                    'aria-label="{} de {}">'.format(i + 1, len(lista)) if carrusel
                    else '<article class="rsG-card rv" style="--d:{}ms">'.format(min(i, 8) * 70))
            out.append(
                '      ' + abre + '\n'
                '        <div class="rsG-top"><span class="rsG-av" aria-hidden="true">{ini}</span>'
                '<div><b>{nombre}</b><span class="rsG-stars" role="img" aria-label="{n} de 5 estrellas">{stars}</span></div></div>\n'
                '        <p>{texto}</p>\n'
                '      </article>'.format(ini=e(iniciales(r["nombre"])), nombre=e(r["nombre"]),
                                          n=n, stars=RS_STAR * n, texto=e(r["texto"])))
        return "\n".join(out)

    cal = data.get("calificacion") or {}
    if not str(cal.get("valor") or "").strip() or not str(cal.get("total") or "").strip():
        # review sin aggregateRating en la misma entidad = error en Search Console
        raise SystemExit("ERROR data/resenas-google.json: falta 'calificacion' (valor y total de Google)")
    rating = {"@type": "AggregateRating", "ratingValue": str(cal["valor"]).replace(",", "."),
              "reviewCount": str(cal["total"]), "bestRating": "5"}

    def fusionar_schema(texto, archivo, org_id):
        """
        Una sola entidad TravelAgency por página: busca, entre RSS_START y RSS_END,
        el nodo TravelAgency con @id org_id (suelto o dentro de @graph) y le pisa
        aggregateRating + review. El resto de sus campos queda como está.
        """
        m = re.search(re.escape(RSS_START) + r".*?<script type=\"application/ld\+json\">\n(.*?)\n</script>.*?"
                      + re.escape(RSS_END), texto, flags=re.S)
        if not m:
            raise SystemExit("ERROR {}: no tiene los marcadores RESENAS-SCHEMA con el JSON-LD de la agencia".format(archivo))
        ld = json.loads(m.group(1))
        nodos = [n for n in (ld.get("@graph") or [ld])
                 if n.get("@type") == "TravelAgency" and n.get("@id") == org_id]
        if len(nodos) != 1:
            raise SystemExit("ERROR {}: no encuentro un único TravelAgency {} entre los marcadores".format(archivo, org_id))
        nodos[0]["aggregateRating"] = rating
        nodos[0]["review"] = [{
            "@type": "Review",
            "reviewRating": {"@type": "Rating", "ratingValue": str(estrellas(r)), "bestRating": "5"},
            "author": {"@type": "Person", "name": r["nombre"]},
            "reviewBody": r["texto"],
        } for r in rs]
        nuevo = json.dumps(ld, ensure_ascii=False, indent=2)
        return texto[:m.start(1)] + nuevo + texto[m.end(1):]

    google = ('<a class="{cls}" href="{u}" target="_blank" rel="noopener noreferrer">'
              'Ver todas las rese&ntilde;as en Google {fl}</a>')

    # ---------- home: todas, en carrusel (lo visible = el schema) ----------
    home = ROOT / "index.html"
    t = home.read_text(encoding="utf-8")
    original = t
    if RS_START not in t or RS_END not in t or RSS_START not in t or RSS_END not in t:
        print("\n!  index.html no tiene los marcadores RESENAS — salteado")
        return
    mas = ('\n    <div class="rsG-more rv">' + google.format(cls="btn", u=e(url), fl=FLECHA) + '</div>') if url else ""
    bloque = "\n".join([
        RS_START, GEN,
        '<section class="sec rsG" id="pasajeros">',
        RS_CSS,
        RS_CAR_CSS,
        '  <div class="wrap">',
        '    <div class="rsC-head rv">',
        '      <div><p class="kicker">Nuestros pasajeros</p><h2 class="h2">Lo que dicen <em>quienes ya viajaron.</em></h2></div>',
        '      <div class="rsC-nav">'
        '<button type="button" class="rsC-btn" data-dir="-1" aria-controls="rsC-track" aria-label="Reseña anterior">' + RS_FLECHA_IZQ + '</button>'
        '<button type="button" class="rsC-btn" data-dir="1" aria-controls="rsC-track" aria-label="Reseña siguiente">' + RS_FLECHA_DER + '</button></div>',
        '    </div>',
        '    <div class="rsC-track" id="rsC-track" tabindex="0" role="region" aria-roledescription="carrusel" '
        'aria-label="Reseñas de pasajeros">',
        cards(rs, carrusel=True),
        '    </div>',
        '    <div class="rsC-bar" aria-hidden="true"><i></i></div>' + mas,
        '  </div>',
        '</section>',
        RS_CAR_JS,
        RS_END,
    ])
    t = reemplazar_bloque(t, RS_START, RS_END, bloque)
    t = fusionar_schema(t, "index.html", ORG_ID)
    if t != original:
        home.write_text(t, encoding="utf-8")
        print("OK  index.html: 'Nuestros pasajeros' en carrusel con las {} resenas".format(len(rs)))
    else:
        print("=   index.html: resenas sin cambios")

    # ---------- schema-block.html: el snippet de referencia, mismo bloque que la home ----------
    sb = ROOT / "schema-block.html"
    if sb.exists():
        t = sb.read_text(encoding="utf-8")
        nuevo = fusionar_schema(t, "schema-block.html", ORG_ID)
        if nuevo != t:
            sb.write_text(nuevo, encoding="utf-8")
            print("OK  schema-block.html: TravelAgency con aggregateRating + {} review".format(len(rs)))
        else:
            print("=   schema-block.html sin cambios")

    # ---------- /quienes-somos/: todas las reseñas ----------
    qs = ROOT / "quienes-somos" / "index.html"
    if not qs.exists():
        return
    t = qs.read_text(encoding="utf-8")
    original = t
    if RS_START not in t or RS_END not in t:
        print("!  quienes-somos/index.html no tiene los marcadores RESENAS — salteado")
        return
    link = ('\n    <div class="rsG-more rv">' + google.format(cls="btn", u=e(url), fl=FLECHA) + '</div>') if url else ""
    bloque = "\n".join([
        RS_START, GEN,
        '<section class="sec px rsG" id="pasajeros">',
        RS_CSS,
        '  <div class="mx">',
        '    <div class="rv" style="max-width:720px"><p class="kicker">Nuestros pasajeros</p><h2 class="h2">Lo que dicen <em>quienes ya viajaron.</em></h2></div>',
        '    <div class="rsG-grid">',
        cards(rs),
        '    </div>' + link,
        '  </div>',
        '</section>',
        RS_END,
    ])
    t = reemplazar_bloque(t, RS_START, RS_END, bloque)
    t = fusionar_schema(t, "quienes-somos/index.html", ORG_ID)
    if t != original:
        qs.write_text(t, encoding="utf-8")
        print("OK  quienes-somos/index.html: las {} resenas".format(len(rs)))
    else:
        print("=   quienes-somos/index.html: resenas sin cambios")



# ============================================================
# Paquetes retirados: registro persistente + 301 en .htaccess
# ============================================================
RETIRADOS = ROOT / "data" / "paquetes-retirados.json"
HTACCESS = ROOT / ".htaccess"
RET_START = "# PAQUETES-RETIRADOS:START (lo genera build-paquetes.py desde data/paquetes-retirados.json; no editar a mano)"
RET_END = "# PAQUETES-RETIRADOS:END"


def actualizar_retirados(publicados, hoy):
    """Regla fija (2026-10-22): cuando un paquete vence o pasa a activo=false su pagina
    desaparece, pero la URL /paquetes/<slug>/ NO puede quedar en 404. Se lleva un registro
    persistente de todo slug que alguna vez se publico (data/paquetes-retirados.json, nunca
    se borra nada) y en cada build se escribe en .htaccess, entre marcadores y antes del
    ErrorDocument, una 301 por cada slug retirado hacia la madre de su region (o /paquetes/
    si la region no tiene pagina). Si el paquete vuelve a activarse, su regla se quita sola
    porque solo se generan reglas para slugs que NO estan publicados: nunca se redirige
    una URL activa, asi no hay bucles."""
    reg = json.loads(RETIRADOS.read_text(encoding="utf-8")) if RETIRADOS.exists() else {"paquetes": {}}
    items = reg.setdefault("paquetes", {})
    cambios = 0
    for p, _v in publicados:
        slug = p["id"]
        if slug not in items:
            items[slug] = {"region": p["region"], "fuente": "publicado el " + hoy.isoformat()}
            cambios += 1
        elif items[slug].get("region") != p["region"]:
            items[slug]["region"] = p["region"]
            cambios += 1
    if cambios or not RETIRADOS.exists():
        reg["paquetes"] = dict(sorted(items.items()))
        RETIRADOS.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    activos = {p["id"] for p, _v in publicados}
    reglas = []
    for slug, info in sorted(items.items()):
        if slug in activos:
            continue
        if not re.match(r"^[a-z0-9-]+$", slug):
            continue
        region = str(info.get("region") or "").strip("/")
        destino = "/{}/".format(region) if region and (ROOT / region / "index.html").exists() else "/paquetes/"
        if (ROOT / "paquetes" / slug / "index.html").exists():
            print("   AVISO: {} sigue con pagina en paquetes/ aunque no esta publicado: no se redirige".format(slug))
            continue
        reglas.append("RewriteRule ^paquetes/{}/?$ {} [L,R=301]".format(slug, destino))   # slug ya validado: solo [a-z0-9-]

    bloque = "\n".join([RET_START,
                        "# {} paquete(s) retirado(s) -> madre de su region. Con y sin barra final.".format(len(reglas))]
                       + reglas + [RET_END])
    txt = HTACCESS.read_text(encoding="utf-8")
    if RET_START in txt and RET_END in txt:
        nuevo = re.sub(re.escape(RET_START) + r".*?" + re.escape(RET_END), lambda m: bloque, txt, count=1, flags=re.S)
    elif "ErrorDocument 404" in txt:
        nuevo = txt.replace("ErrorDocument 404", bloque + "\n\nErrorDocument 404", 1)
    else:
        nuevo = txt.rstrip("\n") + "\n\n" + bloque + "\n"
    if nuevo != txt:
        HTACCESS.write_text(nuevo, encoding="utf-8", newline="\n")
        print("OK  .htaccess: bloque PAQUETES-RETIRADOS con {} regla(s) 301 ({} slug(s) en el registro)".format(len(reglas), len(items)))
    else:
        print("=   .htaccess: bloque PAQUETES-RETIRADOS sin cambios ({} regla(s))".format(len(reglas)))
    return reglas

# ============================================================
# Modulo "Salidas por destino" en las paginas de pais (tanda 2, 27/10/2026)
# ============================================================
# data/destinos-paises.json lista cada pagina de pais con sus terminos de match. Un paquete
# entra en una pagina solo si tiene al menos una noche de hotel (hoteles[].ciudad) o un tramo
# de recorrido terrestre ("destinos" de un paquete que no es crucero) en ese pais; las escalas
# de crucero no cuentan y los viajes de quinceaneras no entran en ninguna. Match sin acentos y
# por palabra completa, nunca contra palabras sueltas del titulo. Las cards son las compactas
# de las madres y el ItemList del schema replica EXACTAMENTE las cards visibles, en el
# mismo orden. Si la pagina queda sin paquetes (porque vencen), muestra las salidas activas
# de su region bajo "Otras salidas en <region>" con su propio ItemList. Se recalcula en
# cada build. "publicar": true marca las paginas que build-tanda.py copia a la tanda.
PAISES_JSON = ROOT / "data" / "destinos-paises.json"
PAIS_START = "<!-- PAQUETES-PAIS:START -->"
PAIS_END = "<!-- PAQUETES-PAIS:END -->"
REGION_EN = {"caribe": "el Caribe", "europa": "Europa", "usa": "Estados Unidos", "argentina": "Argentina",
             "asia": "Asia", "africa": "\u00c1frica", "oceania": "Ocean\u00eda", "latinoamerica": "Latinoam\u00e9rica",
             "medio-oriente": "Medio Oriente", "brasil": "Brasil", "cruceros": "crucero",
             "viajes-deportivos": "viajes deportivos", "quinceaneras": "viajes de quincea\u00f1eras", "disney": "Disney"}
_SECCION_PAQ_RE = re.compile(r'(?:<!-- PAQUETES -->\s*)?<section\b[^>]*\bid="paquetes"[^>]*>.*?</section>\s*', re.S)


def _norm_lugar(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().strip()


def es_crucero(p):
    return p.get("region") == "cruceros" or "crucero" in lista(p, "tipo")


def lugares_de(p):
    """Lugares donde el paquete tiene al menos una noche de hotel o un tramo de recorrido terrestre:
    las ciudades de hoteles[] siempre, y "destinos" solo si NO es crucero (en un crucero "destinos"
    son escalas, que no cuentan; un crucero con noches de hotel pre/post entra por esas ciudades)."""
    out = set()
    if not es_crucero(p):
        out.update(_norm_lugar(d) for d in lista(p, "destinos"))
    for h in lista(p, "hoteles"):
        if isinstance(h, dict) and _v(h, "ciudad"):
            out.add(_norm_lugar(_v(h, "ciudad")))
    return out


def coincide_pais(p, terminos):
    lug = lugares_de(p)
    for t in terminos:
        pat = re.compile(r"(?<![a-z0-9])" + re.escape(_norm_lugar(t)) + r"(?![a-z0-9])")
        if any(pat.search(l) for l in lug):
            return True
    return False


def cargar_paises():
    if not PAISES_JSON.exists():
        return {}
    return json.loads(PAISES_JSON.read_text(encoding="utf-8")).get("paginas", {})


def schema_itemlist(nombre, items):
    return json.dumps({"@context": "https://schema.org", "@type": "ItemList", "name": nombre, "numberOfItems": len(items),
                       "itemListElement": [{"@type": "ListItem", "position": i + 1,
                                            "url": "{}/paquetes/{}/".format(DOMINIO, p["id"]), "name": txt(p, "titulo")}
                                           for i, (p, v) in enumerate(items)]}, ensure_ascii=False)


def render_modulo_pais(cfg, items, otros, hoy):
    nombre = cfg["nombre"]
    frase = cfg.get("frase") or ("a " + nombre)
    region = cfg.get("region")
    reg_en = REGION_EN.get(region, REGIONES.get(region, region))
    NL = chr(10)
    if items:
        n = len(items)
        kicker = "Salidas {}".format(e(frase))
        h2 = "{} {} {} <em>con fecha y precio publicados.</em>".format(n, "salida" if n == 1 else "salidas", e(frase))
        cards, nombre_lista = items, "Salidas {}".format(frase)
    elif otros:
        kicker = "Otras salidas en {}".format(e(reg_en))
        h2 = "Por ahora no hay salidas publicadas {}. <em>Estas son otras salidas en {}.</em>".format(e(frase), e(reg_en))
        cards, nombre_lista = otros, "Otras salidas en {}".format(reg_en)
    else:
        kicker = "Salidas {}".format(e(frase))
        h2 = "Por ahora no hay salidas publicadas {}. <em>Te cotizamos el viaje a medida.</em>".format(e(frase))
        cards, nombre_lista = [], None
    wa = "https://wa.me/{}?text={}".format(WA_NUMERO, urllib.parse.quote("Hola Legend Travel, quiero consultar sobre un viaje " + frase, safe=''))
    partes = [
        PAIS_START,
        "<!-- Generado por build-paquetes.py el {}. NO editar a mano: se pisa. -->".format(hoy.isoformat()),
        CARD_CSS,
        '<section class="sec px" id="paquetes" style="background:#fff">',
        '  <div class="mx">',
        '    <div class="pk-rhead rv">',
        '      <div>',
        '        <p class="kicker">{}</p>'.format(kicker),
        '        <h2 class="h2" style="font-size:clamp(28px,3vw,40px)">{}</h2>'.format(h2),
        '      </div>',
        '      <a class="pk-rall" href="paquetes/">Ver todos los paquetes{}</a>'.format(IC_FLECHA),
        '    </div>',
    ]
    if cards:
        partes += [
            '    <div class="pkc-grid rv">',
            NL.join(render_card_compacta(p, v) for p, v in cards),
            '    </div>',
            '    <p class="dnota rv" style="margin-top:20px">Actualizado el {}. Precios por persona en base doble, \u00abdesde\u00bb y sujetos a disponibilidad; una asesora los confirma por WhatsApp antes de reservar.</p>'.format(fmt_fecha_larga(hoy)),
        ]
    else:
        partes.append('    <p class="dnota rv">Actualizado el {}. <a href="{}" target="_blank" rel="noopener noreferrer" style="color:var(--red);font-weight:600">Consultanos por WhatsApp</a> y armamos el viaje con tus fechas.</p>'.format(fmt_fecha_larga(hoy), e(wa)))
    partes += ['  </div>', '</section>']
    if cards:
        partes.append('<script type="application/ld+json">{}</script>'.format(schema_itemlist(nombre_lista, cards)))
    partes.append(PAIS_END)
    return NL.join(partes)


def asegurar_marcadores_pais(texto):
    """(texto, True) si inserto los marcadores: reemplaza la seccion estatica #paquetes o, si la pagina
    no la tiene, los pone antes del contacto (o del footer). (texto, None) si no hay donde."""
    if PAIS_START in texto and PAIS_END in texto:
        return texto, False
    bloque = PAIS_START + "\n" + PAIS_END + "\n"
    m = _SECCION_PAQ_RE.search(texto)
    if m:
        return texto[:m.start()] + bloque + texto[m.end():], True
    for pat in (r'<section\b[^>]*\bid="contacto"', r'<section\b[^>]*\bclass="[^"]*\bcontact\b', r'<footer\b'):
        m = re.search(pat, texto)
        if m:
            return texto[:m.start()] + bloque + texto[m.start():], True
    return texto, None


def generar_modulos_pais(publicados, hoy):
    """Escribe el modulo en TODAS las paginas de data/destinos-paises.json (esten o no publicadas:
    asi cada grupo de la tanda 2 ya tiene su modulo listo). Devuelve {ruta: (ids, ids_region)}."""
    paginas = cargar_paises()
    if not paginas:
        return {}
    resultado = {}
    print("\n\u2192  Salidas por destino en las p\u00e1ginas de pa\u00eds (se listan las marcadas publicar):")
    for ruta, cfg in paginas.items():
        f = ROOT / ruta / "index.html"
        if not f.exists():
            print("   !  {}/index.html no existe".format(ruta))
            continue
        # Los viajes de quinceaneras (XV) no entran en ninguna pagina de pais.
        candidatos = [(p, v) for p, v in publicados if p.get("region") != "quinceaneras"]
        items = [(p, v) for p, v in candidatos if coincide_pais(p, cfg.get("match", []))]
        region = cfg.get("region")
        otros = [] if items else [(p, v) for p, v in candidatos if region in regiones_de(p)]
        original = f.read_text(encoding="utf-8")
        texto, ins = asegurar_marcadores_pais(original)
        if ins is None:
            print("   !  {}: sin lugar para el m\u00f3dulo (ni #paquetes, ni contacto, ni footer)".format(ruta))
            continue
        nuevo = reemplazar_bloque(texto, PAIS_START, PAIS_END, render_modulo_pais(cfg, items, otros, hoy))
        if nuevo != original:
            f.write_text(nuevo, encoding="utf-8")
        resultado[ruta] = ([p["id"] for p, _ in items], [p["id"] for p, _ in otros])
        if cfg.get("publicar"):
            print("   {:<40} {} salida(s){}".format(ruta + "/", len(items), "" if items else "  \u2192 {} de la regi\u00f3n".format(len(otros))))
    print("   ({} p\u00e1ginas con m\u00f3dulo)".format(len(resultado)))
    return resultado


def _plano_inline(frag):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", frag))).strip()


def faqs_visibles(texto_html):
    """Pares (pregunta, respuesta) de los desplegables .faq (button + .ans) de una pagina, en orden."""
    out = []
    for m in re.finditer(r'<div class="faq(?: [^"]*)?">\s*<button[^>]*>(.*?)<span class="pm".*?<div class="ans">(.*?)</div>\s*</div>',
                         texto_html, flags=re.S):
        q, a = _plano_inline(m.group(1)), _plano_inline(m.group(2))
        if q and a:
            out.append((q, a))
    return out


def sincronizar_faqpage(texto_html):
    """Reescribe el nodo FAQPage del JSON-LD de la pagina con EXACTAMENTE las preguntas visibles
    (regla AEO: FAQPage = lo visible). Si la pagina tiene .faq pero ningun FAQPage, lo agrega al
    @graph del primer JSON-LD. Conserva el formato (compacto o indentado). Sin .faq, no toca nada."""
    faqs = faqs_visibles(texto_html)
    if not faqs:
        return texto_html
    nodo = {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]}
    scripts = list(re.finditer(r'<script type="application/ld\+json">\s*(\{(?:(?!</script>).)*\})\s*</script>', texto_html, flags=re.S))
    elegido = next((m for m in scripts if '"FAQPage"' in m.group(1)), None) or next((m for m in scripts if '"@graph"' in m.group(1)), None)
    if not elegido:
        return texto_html
    try:
        d = json.loads(elegido.group(1))
    except ValueError:
        return texto_html
    if isinstance(d, dict) and d.get("@type") == "FAQPage":
        d = {"@context": d.get("@context", "https://schema.org"), **nodo}
    elif isinstance(d, dict) and isinstance(d.get("@graph"), list):
        if any(isinstance(n, dict) and n.get("@type") == "FAQPage" for n in d["@graph"]):
            d["@graph"] = [nodo if isinstance(n, dict) and n.get("@type") == "FAQPage" else n for n in d["@graph"]]
        else:
            d["@graph"].append(nodo)
    else:
        return texto_html
    indentado = "\n" in elegido.group(1).strip()
    out = json.dumps(d, ensure_ascii=False, indent=2) if indentado else json.dumps(d, ensure_ascii=False, separators=(",", ":"))
    return texto_html[:elegido.start(1)] + out + texto_html[elegido.end(1):]


def sincronizar_faqs_estaticas():
    """FAQPage = visible tambien en las paginas estaticas (home, servicios, madres y paginas de pais
    publicadas). Los detalles de paquetes y las guias ya salen sincronizados del generador."""
    rutas = [ROOT / "index.html"] + sorted(ROOT.glob("*/index.html"))
    rutas += [ROOT / r / "index.html" for r, c in cargar_paises().items() if c.get("publicar")]
    tocadas = []
    for f in rutas:
        if not f.exists():
            continue
        t = f.read_text(encoding="utf-8")
        n = sincronizar_faqpage(t)
        if n != t:
            f.write_text(n, encoding="utf-8", newline="\n")
            tocadas.append(f.relative_to(ROOT).as_posix())
    if tocadas:
        print("OK  FAQPage sincronizado con lo visible en: " + ", ".join(tocadas))
    else:
        print("=   FAQPage = visible en todas las paginas estaticas")


# ============================================================
# Paginas de pais que no estan en el build -> 301 a su ancestro publicado (28/10/2026)
# ============================================================
# Hostinger no borra lo subido en builds anteriores (Overwrite no elimina archivos) y el sitemap
# viejo (julio 2026) anunciaba todas las paginas de pais. Por eso cada pagina de
# data/destinos-paises.json con publicar: false (y cada ruta extra de "retiradas") redirige al
# ancestro publicado mas cercano, en el mismo formato que PAQUETES-RETIRADOS. Si una pagina pasa
# a publicar: true, su regla desaparece sola: nunca se redirige una URL publicada.
PAGRET_START = "# PAGINAS-RETIRADAS:START (lo genera build-paquetes.py desde data/destinos-paises.json; no editar a mano)"
PAGRET_END = "# PAGINAS-RETIRADAS:END"


def actualizar_paginas_retiradas():
    datos = json.loads(PAISES_JSON.read_text(encoding="utf-8")) if PAISES_JSON.exists() else {}
    paginas = datos.get("paginas", {})
    publicadas = {r for r, c in paginas.items() if c.get("publicar")}

    def ancestro(ruta):
        partes = ruta.strip("/").split("/")
        for corte in range(len(partes) - 1, 0, -1):
            cand = "/".join(partes[:corte])
            if cand in publicadas or (corte == 1 and (ROOT / cand / "index.html").exists()):
                return "/{}/".format(cand)
        return "/"

    reglas = []
    fuentes = [(r, None) for r, c in sorted(paginas.items()) if not c.get("publicar")]
    fuentes += [(r, d) for r, d in sorted((datos.get("retiradas") or {}).items())]
    for ruta, destino in fuentes:
        ruta = ruta.strip("/")
        if not re.match(r"^[a-z0-9-]+(/[a-z0-9-]+)*$", ruta) or ruta in publicadas:
            continue
        destino = destino or ancestro(ruta)
        if not re.match(r"^/([a-z0-9-]+/)*$", destino):
            continue
        reglas.append("RewriteRule ^{}/?$ {} [L,R=301]".format(ruta, destino))
    bloque = "\n".join([PAGRET_START, "# {} pagina(s) fuera del build -> ancestro publicado. Con y sin barra final.".format(len(reglas))]
                       + reglas + [PAGRET_END])
    txt = HTACCESS.read_text(encoding="utf-8")
    if PAGRET_START in txt and PAGRET_END in txt:
        nuevo = re.sub(re.escape(PAGRET_START) + r".*?" + re.escape(PAGRET_END), lambda m: bloque, txt, count=1, flags=re.S)
    elif RET_END in txt:
        nuevo = txt.replace(RET_END, RET_END + "\n\n" + bloque, 1)
    elif "ErrorDocument 404" in txt:
        nuevo = txt.replace("ErrorDocument 404", bloque + "\n\nErrorDocument 404", 1)
    else:
        nuevo = txt.rstrip("\n") + "\n\n" + bloque + "\n"
    if nuevo != txt:
        HTACCESS.write_text(nuevo, encoding="utf-8", newline="\n")
        print("OK  .htaccess: bloque PAGINAS-RETIRADAS con {} regla(s) 301".format(len(reglas)))
    else:
        print("=   .htaccess: bloque PAGINAS-RETIRADAS sin cambios ({} regla(s))".format(len(reglas)))
    return reglas


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
            render_filtros(publicados, hoy),
            render_grupos(publicados),
            '    <div class="pk-flat" hidden></div>',
            render_nores(),
            END,
        ])
    else:
        bloque = "\n".join([START, render_vacio(), END])

    pagina = PAGE.read_text(encoding="utf-8")
    if START not in pagina or END not in pagina:
        sys.exit("ERROR: faltan los marcadores en {}".format(PAGE))
    nueva = sincronizar_faqpage(reemplazar_bloque(pagina, START, END, bloque))   # FAQPage = preguntas visibles
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
    # Un paquete con regiones_extra entra tambien en esas madres (ej. Egipto & Jordania en africa/ y medio-oriente/).
    por_carpeta = {}
    for p, v in publicados:
        for r in regiones_de(p):
            carpeta = REGION_MADRE.get(r)
            if carpeta and all(x["id"] != p["id"] for x, _ in por_carpeta.get(carpeta, [])):
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
        if RESP_START in nuevo and RESP_END in nuevo:
            bloque_resp = render_respuesta(carpeta, items, hoy) if items else RESP_START + "\n" + RESP_END
            nuevo = reemplazar_bloque(nuevo, RESP_START, RESP_END, bloque_resp)
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

    # ---------- 3b. guias como paginas ----------
    generar_guias(publicados, hoy)

    # ---------- 3c. salidas por destino en las paginas de pais ----------
    generar_modulos_pais(publicados, hoy)

    # ---------- 4. llms.txt (GEO) ----------
    actualizar_llms(publicados, hoy)
    generar_llms_full(publicados, hoy)
    generar_vuelos_faltantes(publicados, hoy)
    actualizar_retirados(publicados, hoy)
    actualizar_paginas_retiradas()
    sincronizar_faqs_estaticas()

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
