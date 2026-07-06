#!/usr/bin/env python3
"""
build-tanda.py
Genera la carpeta de publicación para una tanda de páginas.
- Copia desde el proyecto original (solo lectura).
- Transforma cards que apuntan a páginas NO incluidas → badge "Próximamente".
- Genera un sitemap acotado solo con las páginas de la tanda.
NUNCA modifica el proyecto original.

Uso: python build-tanda.py
"""
import os, sys, shutil, re, datetime
from pathlib import Path

# Forzar UTF-8 en stdout (Windows CP1252 no soporta símbolos unicode)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SRC = Path(__file__).parent  # raíz del proyecto

# ============================================================
# CONFIGURACIÓN — editá esta sección para cada tanda
# ============================================================

DOMAIN = "https://www.legendtravel.com.ar"

# Carpeta destino. Queda fuera del árbol de git (ver .gitignore).
DEST = SRC / "dist-tanda1"

# Archivos sueltos en la raíz del proyecto
ROOT_FILES = [
    "index.html",
    "robots.txt",
    "llms.txt",
    "og-image.jpg",
    "404.html",
    ".htaccess",
    ".nojekyll",
    "favicon.ico",
    "favicon-16x16.png",
    "favicon-32x32.png",
    "apple-touch-icon.png",
    "logo-wordmark.png",
]

# Carpetas de servicios: se copian COMPLETAS (index.html + todos sus assets)
FULL_DIRS = [
    "quienes-somos",
    "financiacion",
    "viajes-a-medida",
    "lunas-de-miel",
    "politica-de-privacidad",
    "terminos-y-condiciones",
]

# Las 12 madres: se copia SOLO index.html + logo-wordmark.png si existe.
# Las subcarpetas (hijas/nietas) NO se copian.
MADRE_DIRS = [
    "usa",
    "caribe",
    "europa",
    "brasil",
    "argentina",
    "latinoamerica",
    "viajes-deportivos",
    "asia",
    "africa",
    "medio-oriente",
    "oceania",
    "cruceros",
]

# Sub-madres excluidas de tanda 1 (nota informativa al final del resumen):
EXCLUIDAS_NOTA = [
    "europa/sur-occidental/, central/, del-este/, islas-britanicas/, escandinavia/",
    "usa/costa-oeste/ (y otras hijas)",
    "caribe/republica-dominicana/ (y otras hijas)",
]

# ============================================================
# TRANSFORMACIÓN "PRÓXIMAMENTE"
# ============================================================
# Clases de cards que se transforman si su destino no está en la tanda.
CARD_CLASSES = ['dcard', 'dest-card', 'dest-luna-card']

# Regex para encontrar un elemento <a class="dcard|dest-card|dest-luna-card" ...>...</a>
_cls_pat = '|'.join(re.escape(c) for c in CARD_CLASSES)
CARD_RE = re.compile(
    r'<a\b([^>]*\bclass="[^"]*\b(?:' + _cls_pat + r')\b[^"]*"[^>]*)>'
    r'(.*?)'
    r'</a>',
    re.DOTALL | re.IGNORECASE,
)

HREF_RE = re.compile(r'\bhref=["\']([^"\']*)["\']', re.IGNORECASE)

# CSS que se inyecta en el <head> de cada HTML que tenga cards transformadas.
PROX_CSS = (
    '\n<style>'
    '.prox-card{opacity:.7;pointer-events:none;cursor:default;position:relative;}'
    '.prox-badge{'
    'position:absolute;top:12px;right:12px;z-index:20;'
    'background:rgba(14,35,45,.88);color:#F2B33D;'
    'font-size:9px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;'
    'padding:5px 10px;border-radius:5px;'
    'border:1px solid rgba(242,179,61,.35);'
    'backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);'
    'font-family:inherit;line-height:1;white-space:nowrap;'
    '}'
    '</style>'
)


def build_published_set() -> set:
    """Construye el conjunto de paths root-relativos publicados en esta tanda."""
    paths = {'/', '/index.html', '/index.html/'}
    for d in FULL_DIRS + MADRE_DIRS:
        paths.add(f'/{d}/')
        paths.add(f'/{d}/index.html')
        paths.add(f'/{d}')
    return paths


def normalize_card_href(href: str) -> str | None:
    """
    Normaliza un href de card a path root-relativo con trailing slash.
    Devuelve None si es externo o no resoluble.
    """
    if not href:
        return None
    href = href.strip().split('?')[0].split('#')[0]
    if not href:
        return None
    skip = ('http://', 'https://', '//', 'mailto:', 'tel:', 'javascript:', 'data:')
    if any(href.startswith(p) for p in skip):
        return None  # externo — no transformar

    # Resolver a root-relativo (todas las páginas del sitio tienen base href="/")
    if href.startswith('/'):
        path = href
    else:
        path = '/' + href

    # Normalizar: /xxx/index.html → /xxx/  |  /xxx.html → /xxx.html
    if path.endswith('/index.html'):
        path = path[: -len('index.html')]
    # Asegurar trailing slash si no tiene extensión
    last_seg = path.rstrip('/').split('/')[-1]
    if '.' not in last_seg and not path.endswith('/'):
        path += '/'

    return path


def has_base_root(html_text: str) -> bool:
    """True si el HTML inyecta <base href="/"> (estático o via document.write)."""
    if re.search(r'<base\b[^>]*href=["\']/', html_text, re.IGNORECASE):
        return True
    if re.search(r"document\.write\(['\"]<base href=", html_text):
        return True
    return False


def transform_html(html_text: str, published: set) -> tuple:
    """
    Transforma cards en html_text: los que apuntan a páginas no publicadas
    pasan a <div class="prox-card"> con badge "Próximamente".
    Devuelve (nuevo_html, n_transformados, n_activos).
    """
    count_prox = [0]
    count_ok = [0]

    def replace_card(m):
        attrs   = m.group(1)   # atributos del <a ...>
        inner   = m.group(2)   # contenido interior

        href_m = HREF_RE.search(attrs)
        href   = href_m.group(1) if href_m else ''

        # Externo → nunca transformar
        if any(href.startswith(p) for p in ('http://', 'https://', '//', 'mailto:', 'tel:')):
            count_ok[0] += 1
            return m.group(0)

        path = normalize_card_href(href)
        if path is None:
            count_ok[0] += 1
            return m.group(0)

        if path in published:
            count_ok[0] += 1
            return m.group(0)

        # Transformar → quitar href, agregar clase prox-card, badge
        new_attrs = HREF_RE.sub('', attrs).strip()
        # Añadir prox-card a la clase existente
        new_attrs = re.sub(
            r'(class="[^"]*)',
            lambda ma: ma.group(1) + ' prox-card',
            new_attrs, count=1,
        )
        badge = '<span class="prox-badge">Próximamente</span>'
        count_prox[0] += 1
        return f'<div {new_attrs}>{badge}{inner}</div>'

    new_html = CARD_RE.sub(replace_card, html_text)

    if count_prox[0] > 0:
        new_html = new_html.replace('</head>', PROX_CSS + '\n</head>', 1)

    return new_html, count_prox[0], count_ok[0]


# ============================================================
# Helpers de copia
# ============================================================

def copy_file(src_path: Path, dest_path: Path):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_path, dest_path)


def copy_html_transformed(src_path: Path, dest_path: Path,
                          published: set, transform_log: dict):
    """Lee un HTML, aplica transformación y guarda en destino."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    text = src_path.read_text(encoding='utf-8', errors='ignore')
    new_text, n_prox, n_ok = transform_html(text, published)
    dest_path.write_text(new_text, encoding='utf-8')
    if n_prox > 0:
        rel = dest_path.relative_to(DEST).as_posix()
        transform_log[rel] = n_prox


def make_copytree_fn(published: set, transform_log: dict):
    """Devuelve un copy_function compatible con shutil.copytree."""
    def _copy(src, dst):
        src_p, dst_p = Path(src), Path(dst)
        dst_p.parent.mkdir(parents=True, exist_ok=True)
        if src_p.suffix.lower() == '.html':
            copy_html_transformed(src_p, dst_p, published, transform_log)
        else:
            shutil.copy2(src, dst)
    return _copy


# ============================================================
# Verificación de integridad
# ============================================================

def extract_local_refs(html_text: str) -> set:
    refs = set()
    skip = ('http://', 'https://', '//', '#', 'mailto:', 'tel:', 'data:', 'javascript:')
    for val in re.findall(r'(?:src|href)=["\']([^"\']+)["\']', html_text):
        val = val.strip().split('?')[0].split('#')[0]
        if val and not any(val.startswith(p) for p in skip):
            if '.' in val.rstrip('/').split('/')[-1]:
                refs.add(val)
    for val in re.findall(r"url\(['\"]?([^'\")\s]+)['\"]?\)", html_text):
        val = val.strip().split('?')[0].split('#')[0]
        if val and not any(val.startswith(p) for p in ('http://', 'https://', '//', 'data:')):
            if '.' in val.rstrip('/').split('/')[-1]:
                refs.add(val)
    return refs


def resolve_ref(ref: str, html_rel: str, base_is_root: bool) -> str:
    if ref.startswith('./'):
        ref = ref[2:]
    if ref.startswith('/'):
        return ref.lstrip('/')
    if base_is_root:
        return ref
    html_dir = Path(html_rel).parent
    try:
        resolved = (html_dir / ref).resolve().relative_to(Path('.').resolve())
        return resolved.as_posix()
    except Exception:
        return ref


# ============================================================
# Main
# ============================================================

def main():
    copied_files:    list[str] = []
    warnings:        list[str] = []
    notes:           list[str] = []
    transform_log:   dict      = {}   # html_rel → n_cards transformadas

    published = build_published_set()

    print(f"\n{'='*62}")
    print(f"  build-tanda.py — generando: {DEST.name}")
    print(f"{'='*62}")

    # 1. Limpiar y crear destino
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    print(f"\n✓  Destino limpiado y recreado: {DEST}")

    # 2. Archivos raíz
    print("\n→  Raíz:")
    for name in ROOT_FILES:
        src = SRC / name
        if not src.exists():
            warnings.append(f"Raíz: '{name}' no encontrado")
            print(f"   ⚠  {name} — NO ENCONTRADO")
            continue
        dest = DEST / name
        if src.suffix.lower() == '.html':
            copy_html_transformed(src, dest, published, transform_log)
        else:
            copy_file(src, dest)
        copied_files.append(name)
        print(f"   {name}")

    # 3. Servicios completos
    print("\n→  Servicios (completos):")
    copyfn = make_copytree_fn(published, transform_log)
    for d in FULL_DIRS:
        src_dir = SRC / d
        dest_dir = DEST / d
        if not src_dir.exists():
            warnings.append(f"Servicio: '{d}/' no encontrado")
            print(f"   ⚠  {d}/ — NO ENCONTRADO")
            continue
        shutil.copytree(src_dir, dest_dir, copy_function=copyfn)
        n = sum(1 for f in dest_dir.rglob('*') if f.is_file())
        for f in dest_dir.rglob('*'):
            if f.is_file():
                copied_files.append(f.relative_to(DEST).as_posix())
        print(f"   {d}/  ({n} archivos)")

    # 4. Madres (solo index.html + logo-wordmark.png)
    print("\n→  Madres (index.html + logo si existe):")
    for d in MADRE_DIRS:
        src_dir = SRC / d
        dest_dir = DEST / d
        if not src_dir.exists():
            warnings.append(f"Madre: '{d}/' no encontrada")
            print(f"   ⚠  {d}/ — NO ENCONTRADO")
            continue
        dest_dir.mkdir(parents=True, exist_ok=True)
        extras = []
        idx = src_dir / "index.html"
        if idx.exists():
            copy_html_transformed(idx, dest_dir / "index.html", published, transform_log)
            copied_files.append(f"{d}/index.html")
        else:
            warnings.append(f"Madre: '{d}/index.html' no encontrado")
        logo = src_dir / "logo-wordmark.png"
        if logo.exists():
            copy_file(logo, dest_dir / "logo-wordmark.png")
            copied_files.append(f"{d}/logo-wordmark.png")
            extras.append("logo-wordmark.png")
        subcarpetas = [x.name for x in src_dir.iterdir()
                       if x.is_dir() and not x.name.startswith('.')]
        if subcarpetas:
            notes.append(f"'{d}/': subcarpetas omitidas → {', '.join(subcarpetas)}")
        label = "index.html" + (f" + {', '.join(extras)}" if extras else "")
        prox_label = f"  [{transform_log.get(f'{d}/index.html', 0)} cards → prox]" \
                     if f'{d}/index.html' in transform_log else ""
        print(f"   {d}/  ({label}){prox_label}")

    # 5. Generar sitemap
    today = datetime.date.today().isoformat()
    sitemap_paths = ["/"]
    for d in FULL_DIRS:
        sitemap_paths.append(f"/{d}/")
    for d in MADRE_DIRS:
        sitemap_paths.append(f"/{d}/")

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in sitemap_paths:
        lines.append(f'  <url><loc>{DOMAIN}{p}</loc><lastmod>{today}</lastmod></url>')
    lines.append('</urlset>')
    (DEST / "sitemap.xml").write_text('\n'.join(lines), encoding='utf-8')
    print(f"\n✓  sitemap.xml generado ({len(sitemap_paths)} URLs)")

    # 6. Transformaciones "Próximamente"
    total_prox = sum(transform_log.values())
    if transform_log:
        print(f"\n→  Cards transformadas a 'Próximamente' ({total_prox} en {len(transform_log)} páginas):")
        for rel, n in sorted(transform_log.items()):
            print(f"   {rel}: {n} card{'s' if n != 1 else ''}")
    else:
        print("\n→  Sin cards transformadas (todas las páginas destino están incluidas)")

    # 7. Verificación de integridad de recursos
    print("\n→  Verificando recursos locales en HTMLs copiados...")
    broken_resources: list[str] = []
    nav_missing: list[str] = []
    html_files = [f for f in copied_files if f.endswith('.html')]
    for html_rel in html_files:
        html_path = DEST / html_rel
        try:
            html_text = html_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        base_root = has_base_root(html_text)
        for ref in extract_local_refs(html_text):
            resolved = resolve_ref(ref, html_rel, base_root)
            if not resolved or resolved.startswith('http') or resolved.startswith('//'):
                continue
            if (DEST / resolved).exists():
                continue
            if resolved.endswith('.html') or resolved.endswith('/'):
                nav_missing.append(f"   [{html_rel}] → '{ref}'")
            else:
                broken_resources.append(f"   [{html_rel}] → '{ref}'")

    if broken_resources:
        print(f"   ⚠  RECURSOS rotos ({len(broken_resources)}):")
        for b in broken_resources:
            print(b)
        warnings.extend(broken_resources)
    else:
        print("   ✓  Sin recursos rotos")

    if nav_missing:
        print(f"   (i) Links de navegación a páginas no incluidas — {len(nav_missing)} (esperado)")

    # 8. Resumen final
    print(f"\n{'='*62}")
    print(f"  RESUMEN")
    print(f"{'='*62}")
    print(f"  Archivos copiados       : {len(copied_files)}")
    print(f"  Páginas en sitemap      : {len(sitemap_paths)}")
    print(f"  Cards → Próximamente    : {total_prox} (en {len(transform_log)} páginas)")
    print(f"  Carpeta destino         : {DEST}")
    print(f"\n  Páginas incluidas:")
    for p in sitemap_paths:
        print(f"    {DOMAIN}{p}")

    if warnings:
        warn_set = sorted(set(warnings))
        print(f"\n  ⚠  ADVERTENCIAS ({len(warn_set)}) — requieren atención:")
        for w in warn_set:
            print(f"    {w}")
    else:
        print(f"\n  ✓  Sin advertencias")

    if notes:
        print(f"\n  (i) Subcarpetas omitidas intencionalmente ({len(notes)}):")
        for n in sorted(set(notes)):
            print(f"    {n}")

    print(f"\n  Sub-madres NO incluidas en tanda 1 (para tu revisión):")
    for e in EXCLUIDAS_NOTA:
        print(f"    - {e}")

    print()
    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
