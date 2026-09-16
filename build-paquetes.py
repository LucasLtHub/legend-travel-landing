#!/usr/bin/env python3
"""
build-paquetes.py
Genera TODA la presencia de paquetes del sitio a partir de data/paquetes.json.

Escribe en tres lugares, y en ningun otro:

  1. paquetes/index.html   → entre <!-- PAQUETES:START --> y <!-- PAQUETES:END -->
     Chips de filtro + la grilla de cards. Cada card linkea a su detalle.

  2. paquetes/<id>/index.html
     Una pagina de detalle por paquete activo, armada con el molde
     data/_template-detalle.html (ese archivo es el UNICO lugar donde se
     toca el diseno del detalle; vive en data/ porque no se publica).
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

# Regiones sin pagina madre propia: no se reportan como faltante.
SIN_MADRE = {"quinceaneras"}

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
# CSS de las cards — FUENTE UNICA (se inyecta en la pagina y en las madres)
# ============================================================
CARD_CSS = """<style>
.pk-grid{display:grid;grid-template-columns:1fr;gap:28px}
@media(min-width:680px){.pk-grid{grid-template-columns:1fr 1fr}}
@media(min-width:1080px){.pk-grid{grid-template-columns:1fr 1fr 1fr}}
.pk-card{position:relative;display:flex;flex-direction:column;background:#fff;border:1px solid rgba(14,35,45,.09);border-radius:18px;overflow:hidden;transition:transform .35s ease,box-shadow .35s ease,border-color .35s ease}
.pk-card:hover{transform:translateY(-4px);border-color:rgba(14,35,45,.14);box-shadow:0 18px 40px -18px rgba(14,35,45,.28)}
/* la card entera es un link; el boton de WhatsApp va por encima (z-index) */
.pk-stretch{position:absolute;inset:0;z-index:1}
.pk-card:focus-within{border-color:rgba(172,10,16,.45);box-shadow:0 0 0 3px rgba(172,10,16,.12)}
.pk-media{position:relative;aspect-ratio:16/10;overflow:hidden;background:rgba(14,35,45,.06)}
.pk-media img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .7s cubic-bezier(.2,.6,.2,1)}
.pk-card:hover .pk-media img{transform:scale(1.06)}
.pk-media::after{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(14,35,45,.3) 0%,rgba(14,35,45,0) 42%);pointer-events:none}
.pk-badge{position:absolute;top:14px;left:14px;z-index:2;display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,.94);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);color:var(--bur);font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.14em;padding:6px 12px;border-radius:100px;box-shadow:0 2px 10px rgba(14,35,45,.14);pointer-events:none}
.pk-badge svg{width:11px;height:11px;color:var(--gold)}
.pk-body{display:flex;flex-direction:column;flex:1;padding:24px 24px 22px}
.pk-dest{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.18em;color:var(--red);margin-bottom:9px;line-height:1.45}
.pk-t{font-size:19px;font-weight:700;letter-spacing:-.015em;line-height:1.28;color:var(--black);margin-bottom:12px}
.pk-resumen{font-size:14px;color:rgba(14,35,45,.62);line-height:1.6;margin-bottom:16px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;line-clamp:2;overflow:hidden}
.pk-meta{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:18px}
.pk-meta span{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;font-weight:600;color:rgba(14,35,45,.62);background:rgba(14,35,45,.04);border:1px solid rgba(14,35,45,.07);border-radius:8px;padding:5px 11px}
.pk-meta svg{width:13px;height:13px;color:var(--red);flex:none}
.pk-inc{list-style:none;margin:0 0 8px;padding:0;display:grid;gap:7px}
.pk-inc li{display:flex;align-items:flex-start;gap:9px;font-size:13.5px;color:rgba(14,35,45,.72);line-height:1.5}
.pk-inc svg{width:13px;height:13px;color:var(--red);flex:none;margin-top:4px}
.pk-mas{font-size:12.5px;color:rgba(14,35,45,.45);margin-bottom:20px;padding-left:22px}
.pk-foot{margin-top:auto;padding-top:18px;border-top:1px solid rgba(14,35,45,.08)}
.pk-price{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.pk-price .lbl{font-size:12px;font-weight:600;color:rgba(14,35,45,.5);text-transform:uppercase;letter-spacing:.1em}
.pk-price .amt{font-size:27px;font-weight:700;letter-spacing:-.03em;color:var(--black);line-height:1}
.pk-price .cur{font-size:15px;font-weight:700;color:rgba(14,35,45,.55);letter-spacing:-.01em}
.pk-pnota{font-size:12px;color:rgba(14,35,45,.5);margin-top:5px;line-height:1.5}
.pk-acts{display:flex;align-items:center;gap:12px;margin-top:16px}
.pk-cta{position:relative;z-index:2;display:flex;align-items:center;justify-content:center;gap:9px;flex:1;background:var(--red);color:#fff;padding:12px 16px;border-radius:9px;font-size:14.5px;font-weight:600;transition:background .3s,transform .3s}
.pk-cta:hover{background:var(--bur);transform:translateY(-1px)}
.pk-cta svg{width:17px;height:17px;flex:none}
.pk-ver{flex:none;display:inline-flex;align-items:center;gap:6px;font-size:13.5px;font-weight:700;color:var(--red);white-space:nowrap}
.pk-card:hover .pk-ver{color:var(--bur)}
.pk-ver svg{width:14px;height:14px;transition:transform .3s}
.pk-card:hover .pk-ver svg{transform:translateX(3px)}
.pk-vig{display:flex;align-items:center;gap:7px;margin-top:13px;font-size:11.5px;color:rgba(14,35,45,.45)}
.pk-vig svg{width:12px;height:12px;flex:none}
.pk-vig b{font-weight:600;color:rgba(14,35,45,.62)}
.pk-rhead{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;flex-wrap:wrap;margin-bottom:34px}
.pk-rhead h3{font-size:27px;font-weight:700;letter-spacing:-.022em;line-height:1.15;color:var(--black);max-width:620px}
.pk-rhead h3 em{font-style:normal;color:var(--red)}
.pk-rall{display:inline-flex;align-items:center;gap:9px;font-size:14px;font-weight:700;color:var(--red);border-bottom:1.5px solid rgba(172,10,16,.25);padding-bottom:3px;white-space:nowrap;transition:color .25s,border-color .25s}
.pk-rall:hover{color:var(--bur);border-color:var(--bur)}
.pk-rall svg{width:15px;height:15px}
.pk-rsep{border:0;border-top:1px solid rgba(14,35,45,.09);margin:72px 0 0}
</style>"""

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
            <p class="pk-vig">{ic_reloj}Tarifa v&aacute;lida hasta <b>{vigencia}</b></p>
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
    orden, cuenta = [], {}
    for p, _ in publicados:
        r = p["region"]
        if r not in cuenta:
            orden.append(r)
            cuenta[r] = 0
        cuenta[r] += 1
    chips = ['      <button class="pk-chip on" data-r="all" aria-pressed="true">'
             'Todos <span class="n">{}</span></button>'.format(len(publicados))]
    for r in orden:
        chips.append('      <button class="pk-chip" data-r="{r}" aria-pressed="false">'
                     '{lbl} <span class="n">{n}</span></button>'.format(
                         r=e(r), lbl=e(REGIONES.get(r, r.replace("-", " ").title())),
                         n=cuenta[r]))
    return ('    <div class="pk-filters rv" role="group" aria-label="Filtrar por regi&oacute;n">\n'
            + "\n".join(chips) + "\n    </div>")


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


def grid_style(n):
    if n == 1:
        return ' style="max-width:400px"'
    if n == 2:
        return ' style="max-width:820px"'
    return ''


def render_region_block(region, items, hoy):
    n = len(items)
    frase = REGIONES_FRASE.get(region, "a " + REGIONES.get(region, region))
    titulo = "{n} {sal} {frase} con <em>fecha y precio cerrado</em>.".format(
        n=n, sal="salida" if n == 1 else "salidas", frase=e(frase))
    return "\n".join([
        R_START,
        "<!-- Generado por build-paquetes.py el {}. NO editar a mano: se pisa. -->".format(hoy.isoformat()),
        CARD_CSS,
        '  <hr class="pk-rsep">',
        '  <div class="mx" style="margin-top:72px">',
        '    <div class="pk-rhead rv">',
        '      <div>',
        '        <p class="kicker">Salidas confirmadas</p>',
        '        <h3>{}</h3>'.format(titulo),
        '      </div>',
        '      <a class="pk-rall" href="paquetes/#{r}">Ver todas las salidas{ic}</a>'.format(
            r=e(region), ic=IC_FLECHA),
        '    </div>',
        '    <div class="pk-grid rv"{}>'.format(grid_style(n)),
        "\n".join(render_card(p, v) for p, v in items),
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


def render_detalle(p, vig, plantilla):
    pd = p["precio_desde"]
    dests = lista(p, "destinos")
    titulo_txt = txt(p, "titulo")
    resumen = txt(p, "resumen")

    # --- barra de datos rapidos (solo lo que existe) ---
    facts = [("Salida", IC_CAL, e(p["salida"]), ""),
             ("Duraci&oacute;n", IC_CAMA, e(noches_txt(p["noches"])), "")]
    if txt(p, "regimen"):
        facts.append(("R&eacute;gimen", IC_PLATO, e(txt(p, "regimen")), ""))
    facts.append(("Vigencia de tarifa", IC_RELOJ,
                  "Tarifa v&aacute;lida hasta " + fmt_fecha_ar(vig), " vig"))
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
        partes.append("<b>{}</b>".format(e(" &middot; ".join(dests[:4]))))
    partes.append(e(noches_txt(p["noches"])))
    partes.append(e(p["salida"]))
    hero_linea = '<span class="sep">|</span>'.join(
        "<span>{}</span>".format(x) for x in partes)

    canonical = "{}/paquetes/{}".format(DOMINIO, p["id"])
    schema = json.dumps({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Inicio", "item": DOMINIO + "/"},
            {"@type": "ListItem", "position": 2, "name": "Paquetes", "item": DOMINIO + "/paquetes"},
            {"@type": "ListItem", "position": 3, "name": titulo_txt, "item": canonical},
        ]}, ensure_ascii=False, separators=(',', ':'))

    desc = resumen if len(resumen) <= 160 else resumen[:157].rsplit(" ", 1)[0] + "…"
    ogimg = p["imagen"] if es_url(p["imagen"]) else DOMINIO + "/" + p["imagen"].lstrip("/")
    pnota = str(pd.get("nota") or "").strip()

    vals = {
        "{{TITULO_TXT}}": e(titulo_txt),
        "{{TITULO}}": e(titulo_txt),
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
# Main
# ============================================================
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
            '    <div class="pk-grid rv">',
            "\n".join(render_card(p, v) for p, v in publicados),
            "    </div>",
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
        f = d / "index.html"
        existia = f.exists()
        out = render_detalle(p, v, plantilla)
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

    # ---------- 3. apartados por region ----------
    por_region = {}
    for p, v in publicados:
        por_region.setdefault(p["region"], []).append((p, v))
    madres = sorted(set(list(REGIONES.keys()) + list(por_region.keys())))

    print("\n→  Apartados por region:")
    tocadas, vaciadas, sin_seccion, sin_pagina = [], [], [], []
    for region in madres:
        f = ROOT / region / "index.html"
        if not f.exists():
            if region in por_region and region not in SIN_MADRE:
                sin_pagina.append(region)
            continue
        texto = f.read_text(encoding="utf-8")
        texto, insertados = asegurar_marcadores(texto)
        if insertados is None:
            if region in por_region:
                sin_seccion.append(region)
            continue
        items = por_region.get(region, [])
        bloque_r = (render_region_block(region, items, hoy) if items
                    else R_START + "\n" + R_END)
        nuevo = reemplazar_bloque(texto, R_START, R_END, bloque_r)
        if nuevo != f.read_text(encoding="utf-8"):
            f.write_text(nuevo, encoding="utf-8")
            if items:
                tocadas.append(region)
                print("   {:<18} {} salida(s)".format(region + "/", len(items)))
            else:
                vaciadas.append(region)
    for r in vaciadas:
        print("   {:<18} sin salidas — apartado vacio".format(r + "/"))
    if not tocadas and not vaciadas:
        print("   (sin cambios)")

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
