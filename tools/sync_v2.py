#!/usr/bin/env python3
"""
tools/sync_v2.py — lleva una subpágina al rediseño v2 (el de la home final).

    python tools/sync_v2.py aplicar  quienes-somos/index.html ...
    python tools/sync_v2.py auditar  quienes-somos/index.html ... [--contra REF]

QUÉ HACE "aplicar" (y nada más):
  1. Cambia las dos líneas de assets (design.css / design.js) de ?v=1 a ?v=2.
  2. Pie: el logo deja de estar dentro de la grilla y pasa, junto con el claim
     "Tu viaje, tu historia." (que ya estaba al pie), a un bloque superior
     .ftop idéntico al de la home. Mismos textos y links.
  3. Hero: cada línea del H1 (separadas por <br>) se envuelve en un span para
     la animación de entrada. El texto y la jerarquía no cambian.
  4. quienes-somos: su <style> propio pierde el "hero partido" (ya no existe en
     el v2); conserva la foto del hero.
  Todo lo demás es CSS/JS compartido. No toca textos, links, schemas, GTM ni
  marcadores.

"auditar" compara contra git (HEAD) con los mismos controles que
tools/rediseno.py (texto visible idéntico, head intacto salvo las líneas de
assets, schemas, GTM, wa.me, links internos, marcadores, fotos).
"""
import re, sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import rediseno as R1

if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')

V_OLD, V_NEW = '?v=1', '?v=2'
CSS_LINK = R1.CSS_LINK.replace(V_OLD, V_NEW)
JS_TAG = R1.JS_TAG.replace(V_OLD, V_NEW)

BRAND_RE = re.compile(r'\s*<div style="display:flex;align-items:center">\s*<a href="\." class="brand">\s*(<img[^>]*>)\s*</a>\s*</div>\n', re.S)
CLAIM_RE = re.compile(r'\s*<span class="claim">Tu viaje, tu historia\.</span>')
H1_RE = re.compile(r'(<h1\b[^>]*>)(.*?)(</h1>)', re.S)


def lineas_h1(inner: str) -> str:
    """Envuelve cada línea del H1 en <span class="ln"><span>…</span></span>, cerrando y
    reabriendo <em> si una itálica cruza un <br>."""
    partes = re.split(r'<br\s*/?>', inner)
    out = []; em = False
    for p in partes:
        p = p.strip()
        if not p: continue
        abre = em
        em_open = p.count('<em>'); em_close = p.count('</em>')
        s = ('<em>' if abre else '') + p + ('</em>' if abre + em_open > em_close else '')
        em = (abre + em_open - em_close) > 0
        out.append('<span class="ln"><span>%s</span></span>' % s)
    return ''.join(out)


def aplicar(rel: str) -> str:
    f = ROOT / rel
    raw = f.read_bytes(); crlf = b'\r\n' in raw
    t = raw.decode('utf-8').replace('\r\n', '\n')
    if 'assets/design.css' not in t:
        return 'ERROR: la página no tiene el rediseño v1 (corré antes tools/rediseno.py aplicar)'
    if V_NEW in t:
        return 'ya aplicado'
    if t.count(R1.CSS_LINK) != 1 or t.count(R1.JS_TAG) != 1:
        return 'ERROR: no encontré las líneas de assets v1 tal cual'
    t = t.replace(R1.CSS_LINK, CSS_LINK, 1).replace(R1.JS_TAG, JS_TAG, 1)
    notas = []

    # pie: logo + claim arriba
    m = BRAND_RE.search(t)
    if m:
        img = re.sub(r'\s*style="[^"]*"', '', m.group(1)).replace('class="brand-logo"', '').replace('  ', ' ')
        img = re.sub(r'\s+>', '>', img)
        if 'loading=' not in img: img = img.replace('<img ', '<img loading="lazy" ')
        t = t[:m.start()] + '\n' + t[m.end():]
        ftop = ('    <div class="ftop">\n'
                '      <a href="." class="flogo" aria-label="Legend Travel">%s</a>\n'
                '      <p class="fclaim">Tu viaje, <em>tu historia.</em></p>\n'
                '    </div>\n') % img
        i = t.index('<div class="fgrid">')
        t = t[:i] + ftop + '    ' + t[i:]
        t, n = CLAIM_RE.subn('', t, count=1)
        if n != 1: notas.append('AVISO: el pie no tenía el claim')
    else:
        notas.append('AVISO: el pie no tiene el bloque de marca esperado; se dejó como estaba')

    # hero: líneas del H1
    hero = re.search(r'<section class="hero">.*?</section>', t, re.S)
    if hero and '<h1' in hero.group(0) and 'class="ln"' not in hero.group(0) and 'hero-kicker' not in hero.group(0) and 'class="code"' not in hero.group(0):
        h = H1_RE.sub(lambda m: m.group(1) + lineas_h1(m.group(2)) + m.group(3), hero.group(0), count=1)
        t = t.replace(hero.group(0), h, 1)
    elif not hero:
        notas.append('sin <section class="hero">')

    # quienes-somos: sin hero partido
    if 'flex-direction:row' in t[:t.index('</head>')]:
        head = t[:t.index('</head>')]
        st = re.search(r'<style>(.*?)</style>', head, re.S)
        keep = [l for l in st.group(1).split('\n') if 'background-image' in l]
        nuevo = ('<style>\n' + '\n'.join(keep) + '\n</style>') if keep else ''
        t = t[:st.start()] + nuevo + t[st.end():]
        notas.append('hero partido quitado')

    f.write_bytes((t.replace('\n', '\r\n') if crlf else t).encode('utf-8'))
    return 'ok' + (' (' + '; '.join(notas) + ')' if notas else '')


def auditar(rel: str, ref: str) -> list:
    """Mismos controles que rediseno.auditar, tolerando el cambio de versión de los assets."""
    R1.CSS_LINK, R1.JS_TAG = CSS_LINK, JS_TAG
    nuevo = (ROOT / rel).read_bytes().decode('utf-8').replace('\r\n', '\n')
    viejo = R1._git(rel, ref)
    # el head puede diferir solo en la versión de los assets y en el <style> propio
    viejo_norm = viejo.replace(V_OLD, V_NEW)
    orig = R1._git
    R1._git = lambda r, rf: viejo_norm
    try:
        prob = R1.auditar(rel, ref)
    finally:
        R1._git = orig
    # el claim del pie sube al bloque superior: el texto es el mismo, solo cambia de lugar
    vis_n, _ = R1._visible(nuevo); vis_v, _ = R1._visible(viejo)
    palabras = lambda vis: sorted(' '.join(vis).split())
    if palabras(vis_n) == palabras(vis_v):
        prob = [p for p in prob if not p.startswith('texto visible cambió')]
    # controles propios del v2
    if 'class="ftop"' not in nuevo: prob.append('el pie no tiene el bloque .ftop')
    if nuevo.count('class="fclaim"') != 1 or 'class="claim"' in nuevo: prob.append('el claim del pie no quedó una sola vez arriba')
    hero = re.search(r'<section class="hero">.*?</section>', nuevo, re.S)
    if hero and '<h1' in hero.group(0) and 'hero-kicker' not in hero.group(0) and 'class="code"' not in hero.group(0) and 'class="ln"' not in hero.group(0):
        prob.append('el H1 del hero no tiene las líneas envueltas')
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
            r = aplicar(rel); print(f'{rel}: {r}'); fallas += r.startswith('ERROR')
        else:
            p = auditar(rel, ref)
            print(f'{rel}: ' + ('OK' if not p else '\n  - ' + '\n  - '.join(p)))
            fallas += any(not x.startswith('AVISO') for x in p)
    return 1 if fallas else 0

if __name__ == '__main__':
    sys.exit(main())
