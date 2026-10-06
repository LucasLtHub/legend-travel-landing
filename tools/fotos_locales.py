#!/usr/bin/env python3
"""
tools/fotos_locales.py — trae al sitio todas las fotos que se cargaban desde
images.pexels.com, para que no dependan de un servidor externo.

    python tools/fotos_locales.py            # descarga, optimiza y reemplaza
    python tools/fotos_locales.py --solo-ver # lista qué haría

- Recorre todos los .html de la fuente (no legend-tanda1), data/paquetes.json
  y data/_template-detalle.html.
- Cada URL de images.pexels.com se baja una sola vez, se recomprime (JPEG
  progresivo, calidad 72, ancho máximo 1800) y se guarda en
  assets/img/pexels/<id>-<ancho>.jpg. El mapa queda en tools/fotos-map.json.
- Se reemplaza la URL por la ruta local en el cuerpo, en el <style> propio de
  cada página y en la fuente de los paquetes. Las metas del <head> (og:image)
  no se tocan: son URLs absolutas para redes sociales.
- A cada página con hero de foto se le suma un <link rel="preload"> de esa
  foto (asset compartido) para que el navegador la pida primero.
"""
import re, sys, json, io, hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / 'assets' / 'img' / 'pexels'
MAPA = ROOT / 'tools' / 'fotos-map.json'
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')
URL_RE = re.compile(r'https://images\.pexels\.com/[^"\' )<>]+')
MAX_W = 1800
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120'

def archivos():
    out = []
    for p in ROOT.rglob('*.html'):
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith(('.git/', '.venv/', 'dist-tanda1/', '_')) or rel.split('/')[-1] in ('head-block.html', 'schema-block.html', 'gtm-noscript-body.html'): continue
        if re.match(r'index-(v\d|destinos)', rel): continue
        out.append(p)
    out += [ROOT / 'data' / 'paquetes.json']
    return out

def nombre(url):
    u = url.replace('&amp;', '&')
    m = re.search(r'/(?:photos|videos)/(\d+)/', u); pid = m.group(1) if m else hashlib.md5(u.encode()).hexdigest()[:10]
    w = re.search(r'[?&]w=(\d+)', u); w = min(int(w.group(1)), MAX_W) if w else 1200
    return '%s-%d.jpg' % (pid, w), u, w

def bajar(url):
    fn, u, w = nombre(url); dst = DEST / fn
    if dst.exists(): return url, fn, 'ya'
    try:
        req = urllib.request.Request(u, headers={'User-Agent': UA})
        data = urllib.request.urlopen(req, timeout=120).read()
        from PIL import Image
        im = Image.open(io.BytesIO(data)).convert('RGB')
        if im.width > w: im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
        im.save(dst, 'JPEG', quality=72, optimize=True, progressive=True)
        return url, fn, 'ok %dx%d %dKB' % (im.width, im.height, dst.stat().st_size // 1024)
    except Exception as e:
        return url, None, 'ERROR ' + str(e)[:80]

def main():
    solo_ver = '--solo-ver' in sys.argv
    DEST.mkdir(parents=True, exist_ok=True)
    files = archivos(); textos = {p: p.read_bytes().decode('utf-8') for p in files}
    urls = {u for t in textos.values() for u in URL_RE.findall(t)}
    # las fotos de los paquetes se ven a pantalla completa en el detalle: también se baja la variante grande
    import re as _re
    for u in URL_RE.findall(textos[ROOT / 'data' / 'paquetes.json']):
        urls.add(_re.sub(r'([?&]w=)\d+', r'\g<1>2200', u))
    urls = sorted(urls)
    print('archivos:', len(files), '| URLs únicas:', len(urls))
    if solo_ver:
        for u in urls[:20]: print(' ', nombre(u)[0], '<-', u[:90])
        return
    mapa = json.loads(MAPA.read_text(encoding='utf-8')) if MAPA.exists() else {}
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(bajar, urls))
    errores = [(u, s) for u, fn, s in res if fn is None]
    for u, fn, s in res:
        if fn: mapa[u] = 'assets/img/pexels/' + fn
    MAPA.write_text(json.dumps(mapa, ensure_ascii=False, indent=1), encoding='utf-8')
    print('descargadas/optimizadas:', sum(1 for _, fn, s in res if fn and s.startswith('ok')), '| ya estaban:', sum(1 for _, fn, s in res if s == 'ya'), '| errores:', len(errores))
    for u, s in errores[:10]: print('  ', s, u[:90])
    # reemplazo: solo fuera del <head> salvo el <style> propio de la página
    cambios = 0
    for p, t in textos.items():
        crlf = '\r\n' in t; t2 = t.replace('\r\n', '\n')
        if p.suffix == '.html' and '</head>' in t2:
            i = t2.index('</head>'); head, body = t2[:i], t2[i:]
            def rep_style(m): return URL_RE.sub(lambda u: mapa.get(u.group(0), u.group(0)), m.group(0))
            head = re.sub(r'<style>.*?</style>', rep_style, head, flags=re.S)
            body = URL_RE.sub(lambda u: mapa.get(u.group(0), u.group(0)), body)
            # preload de la foto del hero (asset compartido) si todavía no está
            m = re.search(r"\.hero-media \.scene\{background-image:url\('([^']+)'\)", head)
            if m and 'rel="preload" as="image"' not in head:
                head = head.rstrip('\n') + '\n<link rel="preload" as="image" href="%s" fetchpriority="high">\n' % m.group(1)
            t2 = head + body
        else:
            t2 = URL_RE.sub(lambda u: mapa.get(u.group(0), u.group(0)), t2)
        if t2 != t.replace('\r\n', '\n'):
            p.write_bytes((t2.replace('\n', '\r\n') if crlf else t2).encode('utf-8')); cambios += 1
    print('archivos modificados:', cambios, '| carpeta:', DEST.relative_to(ROOT), '| total:', sum(f.stat().st_size for f in DEST.glob('*.jpg')) // (1024 * 1024), 'MB')

if __name__ == '__main__':
    main()
