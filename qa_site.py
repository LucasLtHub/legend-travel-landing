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
from urllib.parse import urlparse, unquote

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Falta BeautifulSoup. Instalá con: pip install beautifulsoup4 lxml")
    sys.exit(2)

# ─────────────────────────────────────────────────────────────────────
# CONFIG — ajustá estos valores a tu sitio
# ─────────────────────────────────────────────────────────────────────
EXPECTED_GTM = "GTM-PMHNZSSJ"           # tu contenedor de Google Tag Manager
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

    # 10) anchors root-relative /#  → tu bug de navbar conocido
    # 11) links internos rotos
    base_dir = os.path.dirname(abspath)
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#"):
            continue
        if href.startswith("/#"):
            add(ERROR, rel, f"Anchor root-relative '{href}' → redirige al home. "
                            f"Usá '{href[1:]}' (sin la barra inicial).")
            continue
        if is_external(href) or is_whatsapp(href):
            continue
        # link interno a un archivo: resolver y verificar que exista
        parsed = urlparse(href)
        path = unquote(parsed.path)
        if not path:
            continue
        if path.startswith("/"):
            target = os.path.join(root, path.lstrip("/"))
            add(INFO, rel, f"Link root-relative '{href}' (funciona en el dominio, "
                           f"rompe en file:// y al mover de carpeta).")
        else:
            target = os.path.normpath(os.path.join(base_dir, path))
        # si apunta a carpeta, probar index.html
        if os.path.isdir(target):
            target = os.path.join(target, "index.html")
        if path.endswith((".html", ".htm", "/")) and not os.path.exists(target):
            add(ERROR, rel, f"Link interno roto: '{href}' → no existe el archivo.")

    # 12) JSON-LD / schema
    ld = soup.find_all("script", attrs={"type": "application/ld+json"})
    if not ld:
        add(WARN, rel, "Sin JSON-LD (schema). Falta TravelAgency/LocalBusiness para GEO.")
    else:
        tipos = []
        for s in ld:
            try:
                data = json.loads(s.string or "{}")
                blocks = data if isinstance(data, list) else [data]
                for b in blocks:
                    t = b.get("@type")
                    if t:
                        tipos.append(t if isinstance(t, str) else ",".join(t))
            except Exception:
                add(WARN, rel, "JSON-LD presente pero no parsea (revisá la sintaxis).")

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
    for dirpath, _, filenames in os.walk(root):
        if any(x in dirpath for x in ("node_modules", ".git")):
            continue
        for fn in filenames:
            if fn.lower().endswith((".html", ".htm")):
                html_files.append(os.path.join(dirpath, fn))

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
