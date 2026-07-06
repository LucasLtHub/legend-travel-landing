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
import sys, shutil, re, datetime, urllib.parse, html
from pathlib import Path

# Forzar UTF-8 en stdout (Windows CP1252 no soporta símbolos unicode)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SRC = Path(__file__).parent  # raíz del proyecto

# ============================================================
# CONFIGURACIÓN — editá esta sección para cada tanda
# ============================================================

DOMAIN = "https://www.legendtravel.com.ar"

# Carpeta destino — FUERA de OneDrive para evitar bloqueos de sincronización.
# FileZilla: apuntar a esta ruta cuando subas.
DEST = Path.home() / "legend-tanda1"

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
# TRANSFORMACIÓN → WHATSAPP
# ============================================================
# Clases de cards que se transforman si su destino no está en la tanda.
CARD_CLASSES = ['dcard', 'dest-card', 'dest-luna-card']

# Regex para encontrar <a class="dcard|dest-card|dest-luna-card" ...>...</a>
_cls_pat = '|'.join(re.escape(c) for c in CARD_CLASSES)
CARD_RE = re.compile(
    r'<a\b([^>]*\bclass="[^"]*\b(?:' + _cls_pat + r')\b[^"]*"[^>]*)>'
    r'(.*?)'
    r'</a>',
    re.DOTALL | re.IGNORECASE,
)

HREF_RE = re.compile(r'\bhref=["\']([^"\']*)["\']', re.IGNORECASE)

WA_NUMBER  = "5491127489446"
WA_TEMPLATE = "Hola Legend Travel, quiero más información sobre un viaje a {destino}"

# Texto del <span class="cta"> en cards redirigidas a WhatsApp.
WA_CTA = 'Consultar más información →'  # sin rojo, sin icono


def extract_h3_text(inner_html: str) -> str | None:
    """Texto plano del primer <h3> dentro del HTML de una card."""
    m = re.search(r'<h3[^>]*>(.*?)</h3>', inner_html, re.DOTALL | re.IGNORECASE)
    if not m:
        return None
    text = html.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip()
    return text or None


def build_wa_url(destino: str) -> str:
    msg = WA_TEMPLATE.format(destino=destino)
    return f"https://wa.me/{WA_NUMBER}?text={urllib.parse.quote(msg)}"


def replace_cta(inner_html: str) -> str:
    """Reemplaza el span cta/cta-lnk completo, forzando color neutro."""
    replacement = f'<span class="cta" style="color:rgba(255,255,255,.8)">{WA_CTA}</span>'
    return re.sub(
        r'<span\s+class="cta(?:-lnk)?"[^>]*>.*?</span>',
        replacement,
        inner_html, count=1, flags=re.DOTALL | re.IGNORECASE,
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


def transform_html(html_text: str, published: set, wa_examples: list) -> tuple:
    """
    Transforma cards cuyo destino no está publicado: cambia href a WhatsApp
    con el nombre del destino y reemplaza el CTA por "Consultar por WhatsApp".
    Devuelve (nuevo_html, n_transformados).
    """
    count_wa = [0]

    def replace_card(m):
        attrs = m.group(1)
        inner = m.group(2)

        href_m = HREF_RE.search(attrs)
        href   = href_m.group(1) if href_m else ''

        # Externo (WhatsApp existente, redes, etc.) → nunca transformar
        if any(href.startswith(p) for p in ('http://', 'https://', '//', 'mailto:', 'tel:')):
            return m.group(0)

        path = normalize_card_href(href)
        if path is None or path in published:
            return m.group(0)

        # Nombre del destino desde <h3> o fallback desde URL
        destino = (extract_h3_text(inner)
                   or path.rstrip('/').split('/')[-1].replace('-', ' ').title())

        wa_url = build_wa_url(destino)

        # Reemplazar href; añadir target/_blank si no está
        new_attrs = HREF_RE.sub(f'href="{wa_url}"', attrs, count=1)
        if 'target=' not in new_attrs:
            new_attrs = new_attrs.rstrip() + ' target="_blank" rel="noopener noreferrer"'

        new_inner = replace_cta(inner)
        count_wa[0] += 1
        wa_examples.append((destino, wa_url))
        return f'<a {new_attrs}>{new_inner}</a>'

    new_html = CARD_RE.sub(replace_card, html_text)
    return new_html, count_wa[0]


# ============================================================
# Helpers de copia
# ============================================================

def copy_file(src_path: Path, dest_path: Path):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_path, dest_path)


def copy_html_transformed(src_path: Path, dest_path: Path,
                          published: set, transform_log: dict,
                          wa_examples: list):
    """Lee un HTML, aplica transformación WhatsApp y guarda en destino."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    text = src_path.read_text(encoding='utf-8', errors='ignore')
    new_text, n_wa = transform_html(text, published, wa_examples)
    dest_path.write_text(new_text, encoding='utf-8')
    if n_wa > 0:
        rel = dest_path.relative_to(DEST).as_posix()
        transform_log[rel] = n_wa


def make_copytree_fn(published: set, transform_log: dict, wa_examples: list):
    """Devuelve un copy_function compatible con shutil.copytree."""
    def _copy(src, dst):
        src_p, dst_p = Path(src), Path(dst)
        dst_p.parent.mkdir(parents=True, exist_ok=True)
        if src_p.suffix.lower() == '.html':
            copy_html_transformed(src_p, dst_p, published, transform_log, wa_examples)
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
    transform_log:   dict      = {}   # html_rel → n_cards → WhatsApp
    wa_examples:     list      = []   # (destino, wa_url) para el resumen

    published = build_published_set()

    print(f"\n{'='*62}")
    print(f"  build-tanda.py — generando: {DEST.name}")
    print(f"{'='*62}")

    # 1. Limpiar y crear destino
    if DEST.exists():
        try:
            shutil.rmtree(DEST)
        except PermissionError:
            # Windows: algún proceso (Explorer, IDE) tiene la carpeta abierta.
            # Se eliminan archivos internos y se sobreescribe en su lugar.
            shutil.rmtree(DEST, ignore_errors=True)
    DEST.mkdir(parents=True, exist_ok=True)
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
            copy_html_transformed(src, dest, published, transform_log, wa_examples)
        else:
            copy_file(src, dest)
        copied_files.append(name)
        print(f"   {name}")

    # 3. Servicios completos
    print("\n→  Servicios (completos):")
    copyfn = make_copytree_fn(published, transform_log, wa_examples)
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
            copy_html_transformed(idx, dest_dir / "index.html", published, transform_log, wa_examples)
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
        prox_label = f"  [{transform_log[f'{d}/index.html']} cards → WA]" \
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

    # 6. Transformaciones → WhatsApp
    total_wa = sum(transform_log.values())
    if transform_log:
        print(f"\n→  Cards redirigidas a WhatsApp ({total_wa} en {len(transform_log)} páginas):")
        for rel, n in sorted(transform_log.items()):
            print(f"   {rel}: {n} card{'s' if n != 1 else ''}")
        print(f"\n   Ejemplos de mensajes generados (primeros 5):")
        for destino, url in wa_examples[:5]:
            decoded = urllib.parse.unquote(url.split('text=')[1])
            print(f"   · {destino}: \"{decoded}\"")
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
    print(f"  Cards → WhatsApp        : {total_wa} (en {len(transform_log)} páginas)")
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
