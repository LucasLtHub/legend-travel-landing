#!/usr/bin/env python3
"""
build-tanda.py
Genera la carpeta de publicación para una tanda de páginas.
Copia desde el proyecto original (solo lectura) y genera un sitemap acotado.
NUNCA modifica el proyecto original.

Uso: python build-tanda.py
"""
import os, sys, shutil, re, datetime
from pathlib import Path

# Forzar UTF-8 en stdout para que los simbolos no rompan en Windows
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

# Las 12 madres: se copia SOLO index.html + logo-wordmark.png si existe en la carpeta.
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

# Sub-madres excluidas de tanda 1 (para revisión manual):
EXCLUIDAS_NOTA = [
    "europa/sur-occidental/, central/, del-este/, islas-britanicas/, escandinavia/",
    "usa/costa-oeste/ (y otras hijas)",
    "caribe/republica-dominicana/ (y otras hijas)",
]

# ============================================================
# Helpers
# ============================================================

def copy_file(src_path: Path, dest_path: Path):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_path, dest_path)


def has_base_root(html_text: str) -> bool:
    """True si el HTML tiene base href="/" (estático o via document.write)."""
    # Tag estático: <base href="/">
    if re.search(r'<base\b[^>]*href=["\']/', html_text, re.IGNORECASE):
        return True
    # Dinámico: document.write('<base href="' + ... + '/')
    if re.search(r"document\.write\(['\"]<base href=", html_text):
        return True
    return False


def extract_local_refs(html_text: str) -> set:
    """
    Extrae referencias a archivos locales (con extensión) desde atributos
    src/href y url() de CSS inline. Excluye URLs absolutas, anchors y
    esquemas especiales.
    """
    refs = set()
    skip_prefixes = ('http://', 'https://', '//', '#', 'mailto:', 'tel:', 'data:', 'javascript:')

    for val in re.findall(r'(?:src|href)=["\']([^"\']+)["\']', html_text):
        val = val.strip().split('?')[0].split('#')[0]
        if val and not any(val.startswith(p) for p in skip_prefixes):
            last_seg = val.rstrip('/').split('/')[-1]
            if '.' in last_seg:  # tiene extensión → archivo
                refs.add(val)

    for val in re.findall(r"url\(['\"]?([^'\")\s]+)['\"]?\)", html_text):
        val = val.strip().split('?')[0].split('#')[0]
        if val and not any(val.startswith(p) for p in ('http://', 'https://', '//', 'data:')):
            last_seg = val.rstrip('/').split('/')[-1]
            if '.' in last_seg:
                refs.add(val)

    return refs


def resolve_ref(ref: str, html_rel: str, base_is_root: bool) -> str:
    """
    Resuelve una referencia local a path relativo desde la raíz del sitio.
    Devuelve el path normalizado (con separadores forward slash).
    """
    # Quitar ./ inicial
    if ref.startswith('./'):
        ref = ref[2:]

    if ref.startswith('/'):
        return ref.lstrip('/')

    if base_is_root:
        # Relativo a la raíz del sitio
        return ref

    # Relativo al directorio del HTML
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
    copied_files: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []

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
        if src.exists():
            copy_file(src, DEST / name)
            copied_files.append(name)
            print(f"   {name}")
        else:
            msg = f"Raíz: '{name}' no encontrado en el proyecto"
            warnings.append(msg)
            print(f"   ⚠  {name} — NO ENCONTRADO")

    # 3. Servicios completos
    print("\n→  Servicios (completos):")
    for d in FULL_DIRS:
        src_dir = SRC / d
        dest_dir = DEST / d
        if not src_dir.exists():
            warnings.append(f"Servicio: '{d}/' no encontrado")
            print(f"   ⚠  {d}/ — NO ENCONTRADO")
            continue
        shutil.copytree(src_dir, dest_dir)
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
            copy_file(idx, dest_dir / "index.html")
            copied_files.append(f"{d}/index.html")
        else:
            warnings.append(f"Madre: '{d}/index.html' no encontrado")
        logo = src_dir / "logo-wordmark.png"
        if logo.exists():
            copy_file(logo, dest_dir / "logo-wordmark.png")
            copied_files.append(f"{d}/logo-wordmark.png")
            extras.append("logo-wordmark.png")
        # Registrar subcarpetas omitidas (nota informativa, no error)
        subcarpetas = [x.name for x in src_dir.iterdir()
                       if x.is_dir() and not x.name.startswith('.')]
        if subcarpetas:
            omitidas = ", ".join(subcarpetas)
            notes.append(f"'{d}/': subcarpetas omitidas → {omitidas}")
        label = f"index.html" + (f" + {', '.join(extras)}" if extras else "")
        print(f"   {d}/  ({label})")

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

    # 6. Verificación de integridad
    print("\n→  Verificando referencias locales en HTMLs copiados...")
    broken_resources: list[str] = []   # imágenes/fonts/css/js que faltan (real)
    nav_missing: list[str] = []        # links .html a páginas no incluidas (esperado)
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
            # Separar recursos de navegación
            if resolved.endswith('.html') or resolved.endswith('/'):
                nav_missing.append(f"   [{html_rel}] → '{ref}'")
            else:
                broken_resources.append(f"   [{html_rel}] → '{ref}'")

    if broken_resources:
        print(f"   ⚠  RECURSOS rotos (imágenes/css/js no copiados) — {len(broken_resources)}:")
        for b in broken_resources:
            print(b)
        warnings.extend(broken_resources)
    else:
        print("   ✓  Sin recursos rotos")

    if nav_missing:
        print(f"   (i) Links a páginas no incluidas en tanda 1 — {len(nav_missing)} (esperado):")
        for n in nav_missing[:10]:
            print(n)
        if len(nav_missing) > 10:
            print(f"   ... y {len(nav_missing)-10} más")

    # 7. Resumen final
    print(f"\n{'='*62}")
    print(f"  RESUMEN")
    print(f"{'='*62}")
    print(f"  Archivos copiados  : {len(copied_files)}")
    print(f"  Páginas en sitemap : {len(sitemap_paths)}")
    print(f"  Carpeta destino    : {DEST}")
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
