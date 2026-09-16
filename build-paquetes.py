#!/usr/bin/env python3
"""
build-paquetes.py
Genera la grilla de paquetes de paquetes/index.html a partir de data/paquetes.json.

- Los paquetes viven como DATOS. El HTML se genera. NUNCA editar las cards a mano.
- Solo reemplaza el bloque entre <!-- PAQUETES:START --> y <!-- PAQUETES:END -->.
  El resto de la pagina no se toca jamas.
- Excluye automaticamente lo inactivo y lo vencido: nada vencido llega a la web.

Uso: python build-paquetes.py
"""
import sys, json, html, re, datetime, urllib.parse
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "paquetes.json"
PAGE = ROOT / "paquetes" / "index.html"
IMGDIR = ROOT / "img" / "paquetes"
PLACEHOLDER = "img/paquetes/placeholder.svg"

WA_NUMERO = "5491127489446"
WA_TEXTO = "Hola Legend Travel, quiero información sobre el paquete: {titulo}"

START = "<!-- PAQUETES:START -->"
END = "<!-- PAQUETES:END -->"

OBLIGATORIOS = ["id", "titulo", "destino", "region", "precio_desde", "moneda",
                "salida", "noches", "regimen", "incluye", "vigencia", "imagen"]

# Etiquetas de los chips. Mismos nombres que usa la migaja del sitio.
REGIONES = {
    "caribe": "Caribe", "brasil": "Brasil", "europa": "Europa", "usa": "EE. UU.",
    "argentina": "Argentina", "asia": "Asia", "africa": "África", "oceania": "Oceanía",
    "latinoamerica": "Latinoamérica", "medio-oriente": "Medio Oriente",
    "cruceros": "Cruceros", "disney": "Disney", "lunas-de-miel": "Lunas de miel",
    "viajes-deportivos": "Viajes deportivos",
}

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
         "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
         "noviembre": 11, "diciembre": 12}

# --- iconos (SVG inline, sin dependencias) ---
IC_CAL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 11h18"/></svg>'
IC_CAMA = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M3 18v-6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v6M3 18h18M3 18v2M21 18v2M6 10V7a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v3"/></svg>'
IC_PLATO = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M4 20h16M6 16h12M7 16a5 5 0 0 1 10 0M12 4v3M10.5 5.5h3"/></svg>'
IC_CHECK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"><path d="m4 12 5.5 5.5L20 7"/></svg>'
IC_RELOJ = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/></svg>'
IC_ESTRELLA = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="m12 2 2.9 6.3 6.9.8-5.1 4.7 1.4 6.8L12 17.3 5.9 20.6l1.4-6.8L2.2 9.1l6.9-.8z"/></svg>'
IC_WA = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm5.5 14.2c-.2.7-1.3 1.3-1.9 1.4-.5.1-1.1.1-1.8-.1a16 16 0 0 1-6.9-6.1c-.8-1.3-1.2-2.4-1.1-3 0-.6.5-1.6 1.1-1.9.3-.2.7-.2 1-.1.2 0 .5 0 .7.6l.9 2.1c.1.2.1.5 0 .7l-.5.8c-.2.2-.3.4-.1.7.5.9 1.2 1.7 2 2.4.8.7 1.6 1.2 2.6 1.6.3.1.5.1.7-.1l.7-.7c.2-.3.4-.3.7-.2l2.1 1c.5.3.6.4.6.8Z"/></svg>'
IC_BRUJULA = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5.5-5.5 2 2-5.5z"/></svg>'

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
    """'2026-10-20' -> date. Devuelve None si no parsea."""
    try:
        return datetime.date.fromisoformat(str(v).strip())
    except (ValueError, TypeError):
        return None


def parse_salida(s):
    """'12 de noviembre 2026' / 'noviembre 2026' / '12/11/2026' -> date, o None."""
    if not s:
        return None
    t = str(s).strip().lower()

    m = re.match(r'^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$', t)
    if m:
        d, mo, y = (int(x) for x in m.groups())
        try:
            return datetime.date(y, mo, d)
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
    """1450 -> '1.450' | 1180000 -> '1.180.000' (formato argentino)."""
    try:
        v = float(n)
    except (TypeError, ValueError):
        return html.escape(str(n))
    if v == int(v):
        return f"{int(v):,}".replace(",", ".")
    return f"{v:,.2f}".replace(",", "~").replace(".", ",").replace("~", ".")


def fmt_fecha_ar(d):
    """date -> '20/10/2026'."""
    return d.strftime("%d/%m/%Y")


def es_url(x):
    return str(x).lower().startswith(("http://", "https://", "//"))


def wa_link(titulo):
    txt = WA_TEXTO.format(titulo=titulo)
    return "https://wa.me/{}?text={}".format(WA_NUMERO, urllib.parse.quote(txt, safe=''))


def e(x):
    """Escape para HTML (incluye comillas, sirve en atributos)."""
    return html.escape(str(x), quote=True)


# ============================================================
# Render
# ============================================================
def render_card(p, vig_date):
    destacado = bool(p.get("destacado"))
    nota = str(p.get("nota") or "").strip()
    pnota = str(p.get("precio_nota") or "").strip()

    badge = ('\n        <span class="pk-badge">{}Destacado</span>'.format(IC_ESTRELLA)
             if destacado else "")
    nota_html = ('\n        <span class="pk-nota">{}</span>'.format(e(nota))
                 if nota else "")

    noches = p["noches"]
    noches_txt = "{} {}".format(noches, "noche" if str(noches) == "1" else "noches")

    incluye = "\n".join(
        '          <li>{}{}</li>'.format(IC_CHECK, e(i))
        for i in p["incluye"]
    )

    pnota_html = ('\n          <p class="pk-pnota">{}</p>'.format(e(pnota))
                  if pnota else "")

    return '''      <article class="pk-card" data-r="{region}">
        <div class="pk-media">
          <img src="{imagen}" alt="{destino}" loading="lazy">{badge}{nota}
        </div>
        <div class="pk-body">
          <p class="pk-dest">{destino}</p>
          <h3 class="pk-t">{titulo}</h3>
          <div class="pk-meta">
            <span>{ic_cal}{salida}</span>
            <span>{ic_cama}{noches}</span>
            <span>{ic_plato}{regimen}</span>
          </div>
          <ul class="pk-inc">
{incluye}
          </ul>
          <div class="pk-foot">
            <div class="pk-price"><span class="lbl">Desde</span><span class="cur">{moneda}</span><span class="amt">{precio}</span></div>{pnota}
            <a class="pk-cta" href="{wa}" target="_blank" rel="noopener noreferrer">
              {ic_wa}
              Consultar por WhatsApp
            </a>
            <p class="pk-vig">{ic_reloj}Tarifa v&aacute;lida hasta <b>{vigencia}</b></p>
          </div>
        </div>
      </article>'''.format(
        region=e(p["region"]), imagen=e(p["imagen"]), destino=e(p["destino"]),
        badge=badge, nota=nota_html, titulo=e(p["titulo"]),
        ic_cal=IC_CAL, salida=e(p["salida"]),
        ic_cama=IC_CAMA, noches=e(noches_txt),
        ic_plato=IC_PLATO, regimen=e(p["regimen"]),
        incluye=incluye,
        moneda=e(p["moneda"]), precio=fmt_precio(p["precio_desde"]), pnota=pnota_html,
        wa=e(wa_link(p["titulo"])), ic_wa=IC_WA,
        ic_reloj=IC_RELOJ, vigencia=fmt_fecha_ar(vig_date),
    )


def render_chips(publicados):
    """Chips solo de las regiones que tienen paquetes publicados."""
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
        ic=IC_BRUJULA,
        wa=e("https://wa.me/{}?text={}".format(
            WA_NUMERO,
            urllib.parse.quote("Hola Legend Travel, quiero consultar por una salida", safe=''))),
        ic_wa=IC_WA)


# ============================================================
# Main
# ============================================================
def main():
    hoy = datetime.date.today()
    print("build-paquetes.py  —  {}".format(hoy.isoformat()))
    print("=" * 62)

    if not DATA.exists():
        sys.exit("ERROR: no existe {}".format(DATA))
    if not PAGE.exists():
        sys.exit("ERROR: no existe {}".format(PAGE))

    try:
        raw = json.loads(DATA.read_text(encoding="utf-8"))
    except json.JSONDecodeError as ex:
        sys.exit("ERROR: {} no es JSON valido -> {}".format(DATA.name, ex))

    paquetes = raw.get("paquetes") if isinstance(raw, dict) else raw
    if not isinstance(paquetes, list):
        sys.exit('ERROR: se esperaba una lista en la clave "paquetes".')

    # placeholder e img/paquetes/
    IMGDIR.mkdir(parents=True, exist_ok=True)
    ph = ROOT / PLACEHOLDER
    if not ph.exists():
        ph.write_text(PLACEHOLDER_SVG, encoding="utf-8")
        print("  + creado {}".format(PLACEHOLDER))

    publicados, vencidos, inactivos, avisos, errores = [], [], [], [], []
    vistos = set()

    for idx, p in enumerate(paquetes):
        ident = p.get("id") or "#{} (sin id)".format(idx + 1)

        faltan = [c for c in OBLIGATORIOS if c not in p or p[c] in (None, "", [])]
        if faltan:
            errores.append("{}: faltan campos {}".format(ident, ", ".join(faltan)))
            continue
        if ident in vistos:
            errores.append("{}: id duplicado".format(ident))
            continue
        vistos.add(ident)

        if not isinstance(p["incluye"], list):
            errores.append('{}: "incluye" tiene que ser una lista'.format(ident))
            continue

        vig = parse_vigencia(p["vigencia"])
        if vig is None:
            errores.append('{}: vigencia "{}" no se entiende (formato AAAA-MM-DD)'
                           .format(ident, p["vigencia"]))
            continue

        if not p.get("activo", False):
            inactivos.append(ident)
            continue

        if vig < hoy:
            vencidos.append((ident, vig))
            continue

        # imagen: URL se usa tal cual; ruta local tiene que existir
        if not es_url(p["imagen"]):
            if not (ROOT / p["imagen"]).exists():
                avisos.append("{}: no existe la imagen {} -> uso placeholder"
                              .format(ident, p["imagen"]))
                p["imagen"] = PLACEHOLDER

        if parse_salida(p["salida"]) is None:
            avisos.append('{}: no pude leer la fecha de salida "{}" -> ordeno por vigencia'
                          .format(ident, p["salida"]))

        if vig - hoy <= datetime.timedelta(days=7):
            avisos.append("{}: la tarifa vence en {} dias ({})"
                          .format(ident, (vig - hoy).days, fmt_fecha_ar(vig)))

        if str(p["titulo"]).strip().upper().startswith("[EJEMPLO]"):
            avisos.append("{}: sigue marcado [EJEMPLO] — no publicar asi".format(ident))

        publicados.append((p, vig))

    if errores:
        print("\nERRORES — no se genero nada:")
        for x in errores:
            print("  x  {}".format(x))
        sys.exit(1)

    # destacados primero, despues por fecha de salida
    publicados.sort(key=lambda t: (
        not bool(t[0].get("destacado")),
        parse_salida(t[0]["salida"]) or t[1],
    ))

    # armar el bloque
    if publicados:
        bloque = "\n".join([
            START,
            "<!-- Generado por build-paquetes.py el {}. NO editar a mano: se pisa. -->".format(hoy.isoformat()),
            render_chips(publicados),
            '    <div class="pk-grid rv">',
            "\n".join(render_card(p, v) for p, v in publicados),
            "    </div>",
            '    <p class="pk-nores">No hay salidas en esa regi&oacute;n por ahora.</p>',
            END,
        ])
    else:
        bloque = "\n".join([
            START,
            "<!-- Generado por build-paquetes.py el {}. Sin paquetes publicables. -->".format(hoy.isoformat()),
            render_vacio(),
            END,
        ])

    pagina = PAGE.read_text(encoding="utf-8")
    if START not in pagina or END not in pagina:
        sys.exit("ERROR: faltan los marcadores {} / {} en {}".format(START, END, PAGE))

    nuevo = re.sub(
        re.escape(START) + r".*?" + re.escape(END),
        lambda _: bloque,
        pagina, count=1, flags=re.S,
    )
    if nuevo == pagina:
        print("\n=  sin cambios en paquetes/index.html")
    else:
        PAGE.write_text(nuevo, encoding="utf-8")
        print("\nOK  paquetes/index.html actualizado")

    # ---- resumen ----
    print("\n" + "=" * 62)
    print("RESUMEN")
    print("=" * 62)
    print("  Publicados            : {}".format(len(publicados)))
    for p, v in publicados:
        print("      - {}{}  ({}, vence {})".format(
            p["id"], "  [destacado]" if p.get("destacado") else "",
            p["region"], fmt_fecha_ar(v)))

    print("  Excluidos por vencidos: {}".format(len(vencidos)))
    for ident, v in vencidos:
        print("      - {}  vencido el {} — no publicado".format(ident, fmt_fecha_ar(v)))

    print("  Inactivos             : {}".format(len(inactivos)))
    for ident in inactivos:
        print("      - {}  (activo: false)".format(ident))

    print("  Advertencias          : {}".format(len(avisos)))
    for a in avisos:
        print("      !  {}".format(a))

    if publicados:
        regs = []
        for p, _ in publicados:
            if p["region"] not in regs:
                regs.append(p["region"])
        print("\n  Regiones con chip     : Todos, {}".format(
            ", ".join(REGIONES.get(r, r) for r in regs)))
    print()


if __name__ == "__main__":
    main()
