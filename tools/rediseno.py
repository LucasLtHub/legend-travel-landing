#!/usr/bin/env python3
"""
tools/rediseno.py — aplica y audita el diseño nuevo en las páginas del sitio.

    python tools/rediseno.py aplicar  caribe/index.html quienes-somos/index.html ...
    python tools/rediseno.py auditar  caribe/index.html quienes-somos/index.html ...

QUÉ HACE "aplicar" (y nada más):
  1. En el <head>: reemplaza el <style> inline por el link a assets/design.css
     más un <style> mínimo con lo propio de la página (la foto del hero).
  2. En el <body>: reemplaza el script inline de comportamiento (menú, reveal,
     acordeón) por assets/design.js.
  El resto del archivo no se toca: ni textos, ni links, ni schemas, ni GTM,
  ni los marcadores PAQUETES-REGION, ni el script de migas (que además genera
  el schema BreadcrumbList).

"auditar" compara cada página contra su versión en git (HEAD por defecto) y
falla si cambió algo que no sea lo anterior.
"""
import sys, re, json, subprocess, html
from html.parser import HTMLParser
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).resolve().parent.parent
VER = '1'
# El sitio fija su <base> con document.write en la primera línea del head. El
# "preload scanner" del navegador no ve esa base y pediría assets/… relativo a
# la carpeta de la página (404). Por eso el CSS y el JS se cargan DESPUÉS de la
# base: el CSS con document.write (sigue bloqueando el render, sin parpadeo) y
# el JS creado por script. El <noscript> cubre a quien navega sin JavaScript.
CSS_LINK = ("<script>document.write('<link rel=\"stylesheet\" href=\"assets/design.css?v=" + VER + "\">')</script>\n"
            '<noscript><link rel="stylesheet" href="/assets/design.css?v=' + VER + '"></noscript>')
JS_TAG = ("<script>(function(){var s=document.createElement('script');"
          "s.src='assets/design.js?v=" + VER + "';document.body.appendChild(s)})()</script>")
WA = '5491176554362'
GTM = 'GTM-PMHNZSSJ'

# ---------------------------------------------------------------------------
# CSS propio de página
# ---------------------------------------------------------------------------
# Hero partido (texto sobre bordó + foto al lado). Lo usan las páginas cuyo CSS
# original convertía el hero en un flex de dos columnas (hoy: quienes-somos).
HERO_PARTIDO = """
.hero{flex-direction:column;align-items:stretch;min-height:0;padding-top:var(--nav-h)}
.hero-media{position:relative;inset:auto;height:44vh;flex:none}
.hero-media .ground{display:none}
.hero-inner{background:var(--bur);align-items:flex-start;text-align:left;padding-top:44px;padding-bottom:60px}
.hero h1{font-size:clamp(34px,4.6vw,68px);max-width:none}
.hero-inner .hero-sub{margin-left:0!important;margin-right:0!important}
#navcrumb{position:static!important;order:-1;text-align:left!important;padding:0 var(--gutter) 14px!important}
@media(min-width:900px){
  .hero{flex-direction:row;min-height:100vh;min-height:100svh;padding-top:0}
  .hero-media{height:auto;flex:1 1 50%;order:2}
  .hero-media::after{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(73,20,23,.82) 0%,rgba(73,20,23,0) 24%);pointer-events:none}
  .hero-inner{flex:1 1 50%;order:1;justify-content:center;padding-top:calc(var(--nav-h) + 56px);padding-bottom:72px}
  #navcrumb{position:absolute!important;order:0;padding:0 var(--gutter)!important}
}
"""

SCENE_RE = re.compile(r"\.hero-media\s+\.scene\s*\{([^}]*)\}")
URL_RE = re.compile(r"url\((['\"]?)([^'\")]+)\1\)\s*([^;/}]*)")


def css_de_pagina(css_viejo: str) -> str:
    """Devuelve el CSS mínimo que la página necesita conservar."""
    out = []
    escena = None
    for m in SCENE_RE.finditer(css_viejo):
        if 'url(' in m.group(1):
            escena = m.group(1)
    if escena:
        u = URL_RE.search(escena)
        url, pos = u.group(2), (u.group(3) or '').strip() or 'center'
        out.append(f".hero-media .scene{{background-image:url('{url}');background-position:{pos}}}")
    # otras fotos definidas en el CSS de la página (ej. el fondo del cierre)
    sin_coment = re.sub(r'/\*.*?\*/', '', css_viejo, flags=re.S)
    for m in re.finditer(r'([^{}]+)\{([^{}]*url\([^{}]*)\}', sin_coment):
        sel, cuerpo = m.group(1).strip(), m.group(2)
        if sel.startswith('@') or '.scene' in sel:
            continue
        u = URL_RE.search(cuerpo)
        if not u or u.group(2).startswith('data:'):
            continue
        pos = (u.group(3) or '').strip() or 'center'
        out.append(f"{sel}{{background-image:url('{u.group(2)}');background-position:{pos}}}")
    # hero compacto (páginas legales): sin foto y de poca altura
    mh = re.search(r"\.hero\{[^}]*min-height:(\d+)vh", css_viejo)
    if mh and int(mh.group(1)) <= 60 and not escena:
        out.append(f".hero{{min-height:{mh.group(1)}vh}}")
    # hero partido: el CSS original pasaba .hero a flex en fila
    if re.search(r"\.hero\{[^}]*flex-direction:row", css_viejo) or \
       re.search(r"\.hero\{display:flex;flex-direction:column", css_viejo):
        out.append(HERO_PARTIDO.strip())
    return '\n'.join(out)


# ---------------------------------------------------------------------------
# aplicar
# ---------------------------------------------------------------------------
HEAD_STYLE_RE = re.compile(r'<style\b[^>]*>(.*?)</style>', re.S)
OLD_JS_RE = re.compile(r'<script>\s*\(function\(\)\{\s*document\.querySelectorAll\(\'\.fade\'\).*?</script>', re.S)


def aplicar(rel: str) -> str:
    f = ROOT / rel
    raw = f.read_bytes()
    crlf = b'\r\n' in raw
    t = raw.decode('utf-8').replace('\r\n', '\n')
    if 'assets/design.css' in t:
        return 'ya aplicado'
    fin_head = t.index('</head>')
    head, resto = t[:fin_head], t[fin_head:]

    estilos = list(HEAD_STYLE_RE.finditer(head))
    if len(estilos) != 1:
        return f'ERROR: se esperaba 1 <style> en el head, hay {len(estilos)}'
    m = estilos[0]
    propio = css_de_pagina(m.group(1))
    nuevo = CSS_LINK + ('\n<style>\n' + propio + '\n</style>' if propio else '')
    head = head[:m.start()] + nuevo + head[m.end():]

    resto, n = OLD_JS_RE.subn(JS_TAG, resto, count=1)
    nota = ''
    if n != 1:
        if ".fade'" in resto or 'class="rv' in resto or ' rv"' in resto:
            return 'ERROR: usa .fade/.rv pero no encontré su script inline'
        i = resto.rindex('</body>')
        resto = resto[:i] + JS_TAG + '\n' + resto[i:]
        nota = ' (sin script previo: design.js agregado al final)'

    t = head + resto
    f.write_bytes((t.replace('\n', '\r\n') if crlf else t).encode('utf-8'))
    return 'ok' + (' (hero partido)' if 'flex-direction:row' in propio else '') + nota


# ---------------------------------------------------------------------------
# auditar
# ---------------------------------------------------------------------------
class _Texto(HTMLParser):
    """Texto visible del body, sin scripts ni estilos."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0; self.out = []; self.h1 = 0; self.err = None
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.skip += 1
        if tag == 'h1' and not self.skip: self.h1 += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.skip: self.skip -= 1
    def handle_data(self, data):
        if not self.skip and data.strip(): self.out.append(' '.join(data.split()))


def _visible(t: str):
    p = _Texto(); p.feed(t[t.index('<body'):]); p.close()
    return p.out, p.h1


def _git(rel: str, ref: str) -> str:
    r = subprocess.run(['git', 'show', f'{ref}:{rel}'], cwd=ROOT, capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f'git show {ref}:{rel} falló: {r.stderr.decode()[:200]}')
    return r.stdout.decode('utf-8').replace('\r\n', '\n')


def _head_sin_estilo(t: str) -> list:
    h = t[:t.index('</head>')]
    h = HEAD_STYLE_RE.sub('', h)
    propias = set(CSS_LINK.split('\n'))
    return [l.strip() for l in h.split('\n') if l.strip() and l.strip() not in propias]


def _links_internos(t: str) -> set:
    out = set()
    for m in re.finditer(r'<a\b[^>]*\bhref="([^"]+)"', t):
        h = m.group(1)
        if h.startswith(('http://', 'https://', '//', 'mailto:', 'tel:', '#', 'javascript:', 'data:')) or "'" in h or '+' in h:
            continue
        out.add(h)
    return out


def _existe(href: str) -> bool:
    ruta = href.split('#')[0].split('?')[0].lstrip('/')
    if ruta in ('', '.', './'):
        return (ROOT / 'index.html').exists()
    if ruta.startswith('./'): ruta = ruta[2:]
    p = ROOT / ruta
    return p.is_file() or (p / 'index.html').is_file()


def auditar(rel: str, ref: str) -> list:
    """Lista de problemas (vacía = página aprobada)."""
    prob = []
    nuevo = (ROOT / rel).read_bytes().decode('utf-8').replace('\r\n', '\n')
    viejo = _git(rel, ref)

    # 1. el HTML parsea y hay un solo H1
    try:
        vis_n, h1 = _visible(nuevo)
    except Exception as e:
        return [f'HTML no parsea: {e}']
    vis_v, _ = _visible(viejo)
    if h1 != 1: prob.append(f'H1: hay {h1}')

    # 2. contenido visible idéntico
    if vis_n != vis_v:
        dif = next((i for i, (a, b) in enumerate(zip(vis_v, vis_n)) if a != b), min(len(vis_v), len(vis_n)))
        prob.append(f'texto visible cambió (bloque {dif}): '
                    f'{(vis_v[dif] if dif < len(vis_v) else "∅")[:60]!r} → {(vis_n[dif] if dif < len(vis_n) else "∅")[:60]!r}')

    # 3. head intacto salvo el <style> y el link nuevo
    if _head_sin_estilo(nuevo) != _head_sin_estilo(viejo):
        a, b = _head_sin_estilo(viejo), _head_sin_estilo(nuevo)
        prob.append('head cambió: ' + '; '.join(sorted(set(a) ^ set(b)))[:200])
    if CSS_LINK not in nuevo[:nuevo.index('</head>')]: prob.append('falta el link a design.css')
    if JS_TAG not in nuevo: prob.append('falta design.js')

    # 4. schemas JSON-LD: parsean y son los mismos
    sch = lambda t: re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S)
    for i, x in enumerate(sch(nuevo)):
        try: json.loads(x)
        except Exception as e: prob.append(f'schema {i} no parsea: {e}')
    if sch(nuevo) != sch(viejo): prob.append('los schemas JSON-LD cambiaron')
    if 'BreadcrumbList' in viejo and 'BreadcrumbList' not in nuevo: prob.append('se perdió el schema de migas')

    # 5. GTM, WhatsApp, links, marcadores
    if nuevo.count(GTM) != viejo.count(GTM) or nuevo.count(GTM) < 2: prob.append('GTM cambió o falta')
    wa = lambda t: re.findall(r'https://wa\.me/(\d+)(\?text=[^"\']*)?', t)
    if wa(nuevo) != wa(viejo): prob.append('los links de WhatsApp cambiaron')
    if any(n != WA for n, _ in wa(nuevo)): prob.append('hay un wa.me con otro número')
    if _links_internos(nuevo) != _links_internos(viejo): prob.append('los links internos cambiaron')
    rotos = sorted(h for h in _links_internos(nuevo) if not _existe(h))
    if rotos: prob.append('links internos que no resuelven: ' + ', '.join(rotos[:6]))
    marc = lambda t: re.findall(r'<!-- PAQUETES-REGION:START -->.*?<!-- PAQUETES-REGION:END -->', t, re.S)
    if marc(nuevo) != marc(viejo): prob.append('el bloque PAQUETES-REGION cambió')
    img = lambda t: re.findall(r'<img\b[^>]*\bsrc="([^"]+)"', t) + re.findall(r"background-image:url\('([^']+)'\)", t[t.index('<body'):])
    if img(nuevo) != img(viejo): prob.append('las fotos del cuerpo cambiaron')
    # las fotos que vivían en el CSS viejo tienen que seguir en el <style> nuevo
    css_v = ''.join(HEAD_STYLE_RE.findall(viejo[:viejo.index('</head>')]))
    head_n = nuevo[:nuevo.index('</head>')]
    for u in sorted(set(re.findall(r"url\(['\"]?([^'\")]+)", re.sub(r'/\*.*?\*/', '', css_v, flags=re.S)))):
        if not u.startswith('data:') and u not in head_n:
            prob.append(f'se perdió una foto del CSS: {u[:70]}')
    return prob


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ('aplicar', 'auditar'):
        print(__doc__); return 2
    modo, args = sys.argv[1], sys.argv[2:]
    ref = 'HEAD'
    if '--contra' in args:
        i = args.index('--contra'); ref = args[i + 1]; args = args[:i] + args[i + 2:]
    fallas = 0
    for rel in args:
        rel = rel.replace('\\', '/')
        if modo == 'aplicar':
            r = aplicar(rel); print(f'  {rel:<62} {r}')
            fallas += r.startswith('ERROR')
        else:
            p = auditar(rel, ref)
            print(f'  {rel:<62} ' + ('✓' if not p else '✗'))
            for x in p: print(f'      - {x}')
            fallas += bool(p)
    print(f'\n{len(args)} páginas, {fallas} con problemas' if modo == 'auditar' else f'\n{len(args)} páginas procesadas, {fallas} errores')
    return 1 if fallas else 0


if __name__ == '__main__':
    sys.exit(main())
