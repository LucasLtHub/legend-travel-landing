#!/usr/bin/env python3
"""
tools/revision_extract.py — extrae TODOS los textos visibles de las páginas de
la tanda 1 para el documento de revisión de contenido.

Salida:
  tools/revision-map.json   → cada código mapeado a archivo + ubicación exacta
  (scratch) revision.json   → estructura para armar el .docx (páginas/secciones/bloques)

    python tools/revision_extract.py <salida.json>
"""
import re, sys, json
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parent.parent
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# páginas de la tanda 1, en el orden del documento: (código, título, archivo)
PAGINAS = [
    ('HOME', 'Home', 'index.html'),
    ('QSOMOS', 'Quiénes somos', 'quienes-somos/index.html'),
    ('AMEDIDA', 'Viajes a medida', 'viajes-a-medida/index.html'),
    ('FINAN', 'Financiación', 'financiacion/index.html'),
    ('LUNAS', 'Lunas de miel', 'lunas-de-miel/index.html'),
    ('USA', 'USA', 'usa/index.html'),
    ('CARIBE', 'Caribe', 'caribe/index.html'),
    ('EUROPA', 'Europa', 'europa/index.html'),
    ('BRASIL', 'Brasil', 'brasil/index.html'),
    ('ARG', 'Argentina', 'argentina/index.html'),
    ('LATAM', 'Latinoamérica', 'latinoamerica/index.html'),
    ('DEPORT', 'Viajes deportivos', 'viajes-deportivos/index.html'),
    ('ASIA', 'Asia', 'asia/index.html'),
    ('AFRICA', 'África', 'africa/index.html'),
    ('MEDIO', 'Medio Oriente', 'medio-oriente/index.html'),
    ('OCEANIA', 'Oceanía', 'oceania/index.html'),
    ('CRUCEROS', 'Cruceros', 'cruceros/index.html'),
    ('PAQ', 'Paquetes (página general)', 'paquetes/index.html'),
    ('PAQDET', 'Paquetes: detalle de ejemplo (textos fijos del molde)', 'data/_template-detalle.html'),
    ('SORTEO', 'Sorteo Río', 'sorteo/index.html'),
]
TAGS = ['h1', 'h2', 'h3', 'h4', 'h5', 'p', 'li', 'button', 'a', 'b', 'span', 'i', 'cite', 'dt', 'dd', 'summary', 'label', 'option', 'small', 'figcaption', 'blockquote', 'td', 'th', 'strong']
# textos que no se revisan en la tabla: datos a verificar aparte
RE_DATO = re.compile(r'(\+?54\s?9?\s?11|\b11\s?\d{4}[\s-]?\d{4}\b|\b4717-0344\b|\blegajo\b|\bcuit\b|paran[aá] 3745|\b10 a 20 ?h|lunes a s[aá]bado|@legendtravel|/LegendTravel|wa\.me|\bU\$S|\bUSD\b|\$\s?\d|\bARS\b|©\s?20\d\d)', re.I)
RE_PRECIO = re.compile(r'(U\$S|USD|\$)\s?\d')

def norm(t): return ' '.join(t.split())

def seccion_titulo(sec):
    h = sec.find(['h1', 'h2'])
    if h: return norm(h.get_text(' '))
    k = sec.find(class_='kicker') or sec.find(['h3', 'p'])
    return norm(k.get_text(' '))[:60] if k else 'Bloque'

def seccion_codigo(sec, usados):
    sid = sec.get('id') or ('HERO' if 'hero' in (sec.get('class') or []) else ('FOOTER' if sec.name == 'footer' else 'INTRO'))
    base = re.sub(r'[^A-Z]', '', sid.upper().replace('-', ''))[:6] or 'SEC'
    c, n = base, 2
    while c in usados: c = base + str(n); n += 1
    usados.add(c); return c

def css_path(el):
    parts = []
    while isinstance(el, Tag) and el.name != 'body':
        sib = [s for s in el.parent.find_all(el.name, recursive=False)] if el.parent else [el]
        idx = sib.index(el) + 1 if el in sib else 1
        parts.append('%s:nth-of-type(%d)' % (el.name, idx))
        el = el.parent
    return ' > '.join(reversed(parts))

def extraer(codigo, titulo, rel):
    raw = (ROOT / rel).read_text(encoding='utf-8')
    # bloques generados por build-paquetes.py: no se revisan acá
    raw = re.sub(r'<!-- PAQUETES-REGION:START -->.*?<!-- PAQUETES-REGION:END -->', '', raw, flags=re.S)
    raw = re.sub(r'<!-- PAQUETES:START -->.*?<!-- PAQUETES:END -->', '', raw, flags=re.S)
    soup = BeautifulSoup(raw, 'lxml')
    body = soup.body
    for sel in ['script', 'style', 'noscript', 'svg', '.navwrap', '#navMobile', '.waf', '.thread', '#art-overlay', '.srt-hp', '.sr-only', '[data-dup]', '[aria-hidden="true"]', '.hero-clips', '.dsticky']:
        for el in body.select(sel): el.decompose()
    # contenedores de primer nivel: secciones y pie (y lo que quede suelto)
    tops = [el for el in body.find_all(['section', 'footer'], recursive=True) if not el.find_parent(['section', 'footer'])]
    paginas = {'codigo': codigo, 'titulo': titulo, 'archivo': rel, 'secciones': []}
    usados = set(); mapa = {}; n_total = 0; datos = []
    for sec in tops:
        scode = seccion_codigo(sec, usados)
        stitle = seccion_titulo(sec) if sec.name == 'section' else 'Pie de página'
        bloques = []; capturados = []; k = 0
        for el in sec.find_all(TAGS):
            if any(el is c or c in el.parents for c in capturados): continue
            if el.name == 'a' and el.find_parent(['p', 'li', 'h1', 'h2', 'h3', 'h4']): continue
            if el.name in ('b', 'strong', 'i', 'em', 'span', 'small') and el.find_parent(['p', 'li', 'h1', 'h2', 'h3', 'h4', 'a', 'button', 'summary', 'label']): continue
            # un link, ítem o botón que contiene títulos o párrafos (una card) no se captura entero: se revisan sus partes
            if el.name in ('a', 'li', 'button', 'label', 'summary', 'td') and el.find(['h1', 'h2', 'h3', 'h4', 'h5', 'p']): continue
            txt = norm(el.get_text(' '))
            if not txt or len(txt) < 2: continue
            if re.fullmatch(r'[\d\W]+', txt): continue   # números sueltos de pasos/listas
            capturados.append(el)
            tipo = {'h1': 'Título principal', 'h2': 'Título de sección', 'h3': 'Subtítulo', 'h4': 'Subtítulo', 'h5': 'Subtítulo',
                    'a': 'Botón / link', 'button': 'Botón', 'li': 'Ítem de lista', 'option': 'Opción del formulario', 'label': 'Etiqueta del formulario',
                    'summary': 'Desplegable', 'cite': 'Firma del testimonio'}.get(el.name, 'Texto')
            if el.name == 'p' and ('kicker' in (el.get('class') or []) or 'eyebrow' in (el.get('class') or []) or 'cat' in (el.get('class') or [])): tipo = 'Antetítulo'
            if el.name == 'span' and 'chip' in (el.get('class') or []): tipo = 'Chip'
            if el.name == 'b': tipo = 'Título corto'
            es_dato = len(txt) < 140 and (bool(RE_DATO.search(txt)) or bool(RE_PRECIO.search(txt)))
            # en el pie, los links de navegación (Destinos, La agencia) no se revisan: son nombres de páginas
            if sec.name == 'footer' and el.name == 'a' and not RE_DATO.search(txt): continue
            if sec.name == 'footer' and el.name == 'h4': continue
            k += 1
            code = '%s-%s-%02d' % (codigo, scode, k)
            entrada = {'codigo': code, 'tipo': tipo, 'texto': txt, 'html': el.decode_contents().strip(), 'ruta': css_path(el), 'tag': el.name,
                       'seccion': sec.get('id') or scode, 'archivo': rel}
            mapa[code] = entrada
            if es_dato: datos.append({'codigo': code, 'texto': txt, 'pagina': titulo})
            else: bloques.append({'codigo': code, 'tipo': tipo, 'texto': txt})
        if bloques:
            paginas['secciones'].append({'codigo': scode, 'titulo': stitle, 'bloques': bloques}); n_total += len(bloques)
    return paginas, mapa, datos, n_total

def main():
    salida = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'tools' / 'revision.json'
    doc = {'paginas': [], 'datos': []}; mapa = {}; total = 0
    for codigo, titulo, rel in PAGINAS:
        if not (ROOT / rel).exists(): print('falta', rel); continue
        pag, m, datos, n = extraer(codigo, titulo, rel)
        doc['paginas'].append(pag); mapa.update(m); doc['datos'] += datos; total += n
        print('%-8s %3d bloques  %2d datos  %s' % (codigo, n, len(datos), rel))
    # dedup de datos a verificar por texto
    vistos = set(); dd = []
    for d in doc['datos']:
        if d['texto'] in vistos: continue
        vistos.add(d['texto']); dd.append(d)
    doc['datos'] = dd
    salida.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')
    (ROOT / 'tools' / 'revision-map.json').write_text(json.dumps(mapa, ensure_ascii=False, indent=1), encoding='utf-8')
    print('páginas:', len(doc['paginas']), '| bloques:', total, '| datos a verificar:', len(dd))
    print('mapa:', ROOT / 'tools' / 'revision-map.json')

if __name__ == '__main__':
    main()
