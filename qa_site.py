#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qa_site.py — Auditoría QA del sitio estático de Legend Travel
=============================================================
Recorre todos los .html del sitio y revisa los errores que más duelen
al publicar: anchors rotos (/#...), links internos muertos, falta de GTM,
títulos/metas duplicados o ausentes, imágenes sin alt, schema, etc.

USO
---
    python qa_site.py                 # audita la carpeta actual
    python qa_site.py ./public        # audita otra carpeta
    python qa_site.py --strict        # devuelve exit code 1 si hay WARN (no solo ERROR)

SALIDA
------
- Resumen en consola, agrupado por severidad.
- qa-report.md  -> reporte legible para pegarle a Claude Code.
- qa-report.json -> mismo dato en JSON por si querés automatizar.

Exit code 0 si no hay ERROR. !=0 si hay ERROR (o WARN con --strict),
para que puedas usarlo como compuerta antes de publicar.

Requisitos: pip install beautifulsoup4 lxml
"""

import os
import re
import sys
import json
from collections import defaultdict
from urllib.parse import urlparse, unquote, urljoin

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Falta BeautifulSoup. Instalá con: pip install beautifulsoup4 lxml")
    sys.exit(2)

# ─────────────────────────────────────────────────────────────────────
# CONFIG — ajustá estos valores a tu sitio
# ─────────────────────────────────────────────────────────────────────
EXPECTED_GTM = "GTM-NNPCCJFX"           # tu contenedor de Google Tag Manager
CANONICAL_DOMAIN = "legendtravel.com.ar"  # dominio sin protocolo
# Carpetas/patrones de páginas de destino que DEBEN tener CTA de WhatsApp.
# Si una ruta contiene alguno de estos textos, se exige link de WhatsApp.
DESTINO_HINTS = ["destino", "viaje", "europa", "disney", "caribe",
                 "brasil", "miami", "crucero", "luna-de-miel", "lunas-de-miel"]
# Largos recomendados (SEO)
TITLE_MIN, TITLE_MAX = 25, 65
DESC_MIN, DESC_MAX = 70, 160

# Prefijos de href que NO son links internos a archivos (se ignoran en chequeo de roto)
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:", "javascript:",
                     "whatsapp:", "data:", "sms:")
# Carpetas que no son sitio (entornos de Python, dependencias, git): no se auditan
EXCLUIR_DIRS = {".venv", "venv", "node_modules", ".git", "__pycache__"}

# ─────────────────────────────────────────────────────────────────────

ERROR, WARN, INFO = "ERROR", "WARN", "INFO"
issues = []          # lista de (severidad, archivo, mensaje)
titles_seen = defaultdict(list)   # title -> [archivos]
descs_seen = defaultdict(list)    # description -> [archivos]


def add(sev, rel, msg):
    issues.append((sev, rel, msg))


def is_external(href):
    return href.startswith(EXTERNAL_PREFIXES)


def is_whatsapp(href):
    h = href.lower()
    return ("wa.me" in h or "api.whatsapp.com" in h or h.startswith("whatsapp:"))


def looks_like_destino(rel):
    low = rel.lower()
    return any(h in low for h in DESTINO_HINTS)


# Las páginas fijan la base por JavaScript antes de cargar nada:
#   document.write('<base href="'+(p.indexOf(r)===0?r:'/')+'">')
# r es la subcarpeta de GitHub Pages; en el dominio queda la otra rama ('/').
BASE_JS = re.compile(r"""document\.write\(\s*['"]<base href="['"]\s*\+\s*\(.*?\?\s*r\s*:\s*['"]([^'"]*)['"]\s*\)""")
ORIGEN = "https://qa.local"   # origen ficticio: solo importa la ruta


def base_de_pagina(soup, rel):
    """URL contra la que el navegador resuelve los href relativos de esta página."""
    url_pagina = urljoin(ORIGEN + "/", rel.replace(os.sep, "/"))
    base = soup.find("base", href=True)
    if base:
        return urljoin(url_pagina, base["href"].strip())
    for s in soup.find_all("script"):
        m = BASE_JS.search(s.string or "")
        if m:
            return urljoin(url_pagina, m.group(1))
    return url_pagina


_anclas = {}


def anclas_de(path):
    """Fragmentos válidos de una página: sus id y los filtros que lee de location.hash
    (chips de /paquetes/ con data-r="caribe" → paquetes/#caribe)."""
    path = os.path.normpath(path)
    if path not in _anclas:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                t = f.read()
        except OSError:
            t = ""
        _anclas[path] = set(re.findall(r'\bid="([^"]+)"', t)) | set(re.findall(r'\bdata-r="([^"]+)"', t))
    return _anclas[path]


def check_file(abspath, root):
    rel = os.path.relpath(abspath, root)
    with open(abspath, encoding="utf-8", errors="replace") as f:
        raw = f.read()
    soup = BeautifulSoup(raw, "lxml")

    # 1) <html lang>
    html_tag = soup.find("html")
    if not (html_tag and html_tag.get("lang")):
        add(WARN, rel, "Falta atributo lang en <html> (poné lang=\"es-AR\").")

    # 2) viewport
    if not soup.find("meta", attrs={"name": "viewport"}):
        add(WARN, rel, "Falta <meta viewport> (mobile-first).")

    # 3) <title>
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""
    if not title:
        add(ERROR, rel, "Falta <title> o está vacío.")
    else:
        titles_seen[title].append(rel)
        if not (TITLE_MIN <= len(title) <= TITLE_MAX):
            add(WARN, rel, f"Largo de <title> = {len(title)} (ideal {TITLE_MIN}-{TITLE_MAX}).")

    # 4) meta description
    desc_tag = soup.find("meta", attrs={"name": "description"})
    desc = desc_tag.get("content", "").strip() if desc_tag else ""
    if not desc:
        add(WARN, rel, "Falta meta description.")
    else:
        descs_seen[desc].append(rel)
        if not (DESC_MIN <= len(desc) <= DESC_MAX):
            add(INFO, rel, f"Largo de description = {len(desc)} (ideal {DESC_MIN}-{DESC_MAX}).")

    # 5) canonical
    if not soup.find("link", attrs={"rel": "canonical"}):
        add(WARN, rel, "Falta <link rel=\"canonical\">.")

    # 6) h1: exactamente uno
    h1s = soup.find_all("h1")
    if len(h1s) == 0:
        add(ERROR, rel, "No hay <h1>.")
    elif len(h1s) > 1:
        add(WARN, rel, f"Hay {len(h1s)} <h1> (debería haber 1).")

    # 7) Open Graph
    for prop in ("og:title", "og:description", "og:image"):
        if not soup.find("meta", attrs={"property": prop}):
            add(WARN, rel, f"Falta meta {prop} (compartir en redes/WhatsApp).")

    # 8) GTM
    if EXPECTED_GTM not in raw:
        add(ERROR, rel, f"Falta el snippet de GTM ({EXPECTED_GTM}). Sin esto no medís esta página.")

    # 9) imágenes sin alt
    sin_alt = [img.get("src", "?") for img in soup.find_all("img")
               if not (img.get("alt") or "").strip()]
    if sin_alt:
        muestra = ", ".join(sin_alt[:4]) + (" …" if len(sin_alt) > 4 else "")
        add(WARN, rel, f"{len(sin_alt)} imagen(es) sin alt: {muestra}")

    # 10) y 11) links internos y anchors — resueltos como el navegador: URL de la
    #     página, después la <base> (estática o la que fija el script) y recién ahí
    #     el href. Con <base href="/">, "#x" y "/#x" van al mismo lugar: la home.
    base_url = base_de_pagina(soup, rel)
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href == "#" or is_external(href) or is_whatsapp(href):
            continue
        parsed = urlparse(href)
        if href.startswith("#") and parsed.fragment in anclas_de(abspath):
            continue   # el destino está en la misma página: el script hace scroll sin navegar
        if parsed.path.startswith("/"):
            add(INFO, rel, f"Link root-relative '{href}' (funciona en el dominio, "
                           f"rompe en file:// y al mover de carpeta).")
        resuelto = urlparse(urljoin(base_url, href))
        destino = unquote(resuelto.path)
        target = os.path.normpath(os.path.join(root, destino.lstrip("/")))
        # si apunta a carpeta, probar index.html (como Apache con DirectoryIndex)
        if os.path.isdir(target):
            target = os.path.join(target, "index.html")
        sin_extension = "." not in os.path.basename(destino.rstrip("/"))
        if not os.path.exists(target):
            if destino.endswith((".html", ".htm", "/")) or sin_extension:
                add(ERROR, rel, f"Link interno roto: '{href}' → {destino} no existe.")
            continue
        if resuelto.fragment and target.endswith((".html", ".htm")) and resuelto.fragment not in anclas_de(target):
            add(ERROR, rel, f"Anchor roto: '{href}' → {destino}#{resuelto.fragment} no existe en esa página.")

    # 12) JSON-LD / schema
    ld = soup.find_all("script", attrs={"type": "application/ld+json"})
    if not ld:
        add(WARN, rel, "Sin JSON-LD (schema). Falta TravelAgency/LocalBusiness para GEO.")
    else:
        tipos = []
        nodos = []
        for s in ld:
            try:
                data = json.loads(s.string or "{}")
                blocks = data if isinstance(data, list) else [data]
                for b in blocks:
                    t = b.get("@type")
                    if t:
                        tipos.append(t if isinstance(t, str) else ",".join(t))
                    nodos.extend(b.get("@graph") or [b])
            except Exception:
                add(WARN, rel, "JSON-LD presente pero no parsea (revisá la sintaxis).")
        # Search Console: "Varias reseñas sin el objeto aggregateRating" — las review
        # tienen que colgar de la misma entidad que el aggregateRating, y una sola.
        agencias = [n for n in nodos if isinstance(n, dict) and n.get("@type") == "TravelAgency"]
        if len(agencias) > 1:
            add(ERROR, rel, f"{len(agencias)} entidades TravelAgency en la página (tiene que haber una sola).")
        for n in nodos:
            if not isinstance(n, dict):
                continue
            if n.get("@type") == "Review":
                add(ERROR, rel, "Review suelto en el JSON-LD (tiene que ir dentro de la entidad con aggregateRating).")
            elif n.get("review") and not n.get("aggregateRating"):
                add(ERROR, rel, f"{n.get('@type')} con review pero sin aggregateRating en la misma entidad.")

    # 13) referencias hardcodeadas a localhost / dominio equivocado
    if re.search(r"https?://localhost|127\.0\.0\.1|192\.168\.", raw):
        add(ERROR, rel, "Referencia a localhost/IP local hardcodeada (no publicar así).")

    # 14) CTA de WhatsApp en páginas de destino
    if looks_like_destino(rel):
        if not any(is_whatsapp(a.get("href", "")) for a in soup.find_all("a", href=True)):
            add(WARN, rel, "Página de destino sin CTA de WhatsApp (arriba y abajo).")


def cross_checks():
    for t, files in titles_seen.items():
        if len(files) > 1:
            add(WARN, files[0], f"<title> duplicado en {len(files)} páginas "
                                f"(canibalización SEO): {', '.join(files[:5])}")
    for d, files in descs_seen.items():
        if len(files) > 1:
            add(INFO, files[0], f"meta description duplicada en {len(files)} páginas: "
                                f"{', '.join(files[:5])}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    strict = "--strict" in sys.argv
    root = os.path.abspath(args[0]) if args else os.getcwd()

    html_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUIR_DIRS]   # no se baja a esas carpetas
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            # los index.html vacíos de las carpetas data/ protegidas no son páginas:
            # existen solo para que el servidor no liste la carpeta
            if fn.lower().endswith((".html", ".htm")) and os.path.getsize(fp) > 0:
                html_files.append(fp)

    if not html_files:
        print(f"No encontré .html en {root}")
        sys.exit(2)

    for fp in sorted(html_files):
        try:
            check_file(fp, root)
        except Exception as e:
            add(ERROR, os.path.relpath(fp, root), f"No se pudo procesar: {e}")

    cross_checks()

    # Resumen por severidad
    by_sev = defaultdict(list)
    for sev, rel, msg in issues:
        by_sev[sev].append((rel, msg))

    n_err, n_warn, n_info = len(by_sev[ERROR]), len(by_sev[WARN]), len(by_sev[INFO])

    print(f"\n=== QA Legend Travel — {len(html_files)} páginas revisadas ===")
    print(f"  ERROR: {n_err}   WARN: {n_warn}   INFO: {n_info}\n")
    for sev in (ERROR, WARN, INFO):
        if not by_sev[sev]:
            continue
        print(f"── {sev} ──")
        for rel, msg in by_sev[sev]:
            print(f"  [{rel}] {msg}")
        print()

    # Reporte markdown para Claude Code
    lines = [f"# Reporte QA — Legend Travel",
             f"Páginas: {len(html_files)} · ERROR: {n_err} · WARN: {n_warn} · INFO: {n_info}\n"]
    for sev in (ERROR, WARN, INFO):
        if not by_sev[sev]:
            continue
        lines.append(f"## {sev}")
        for rel, msg in by_sev[sev]:
            lines.append(f"- **{rel}** — {msg}")
        lines.append("")
    with open(os.path.join(root, "qa-report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    with open(os.path.join(root, "qa-report.json"), "w", encoding="utf-8") as f:
        json.dump([{"sev": s, "file": r, "msg": m} for s, r, m in issues],
                  f, ensure_ascii=False, indent=2)

    print(f"Reportes escritos: qa-report.md  /  qa-report.json")

    if n_err > 0 or (strict and n_warn > 0):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
