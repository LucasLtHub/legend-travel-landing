# -*- coding: utf-8 -*-
"""
Planilla de carga de paquetes (P3).

  python planilla-paquetes.py exportar          genera data/paquetes-completar.csv
  python planilla-paquetes.py importar          vuelca la planilla en data/paquetes.json
  python planilla-paquetes.py importar --probar revisa la planilla sin guardar nada

- Una fila por paquete activo y una columna por cada campo de precios (P1),
  hoteles, vuelos, crucero y foto de portada (P2).
- Separador punto y coma, UTF-8 con BOM: abre bien con doble clic en Excel.
- Importar NUNCA borra un dato con una celda vacia: lo vacio se deja como esta.
- Si hay un solo error, no se guarda nada y se lista todo lo que hay que corregir.
- Antes de guardar, copia el JSON anterior en data/respaldos/.
Instrucciones para quien completa la planilla: docs/planilla-paquetes.md
"""
import csv
import datetime
import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data" / "paquetes.json"
CSV = ROOT / "data" / "paquetes-completar.csv"
RESPALDOS = ROOT / "data" / "respaldos"

BASES = ["single", "doble", "triple", "cuadruple"]
MONEDAS = ["USD", "ARS", "EUR"]
MAX_CABINAS, MAX_HOTELES, MAX_VUELOS = 4, 12, 4
HOTEL = ["ciudad", "nombre", "categoria", "noches", "web"]
VUELO = ["aerolinea", "ruta", "clase", "fecha", "horario", "numero", "equipaje"]
CRUCERO = ["naviera", "barco", "cabina", "bebidas", "propinas", "wifi", "asistencia", "web"]
NO_VALE = ("a confirmar", "a definir", "consultar", "-", "n/a", "s/d")


def columnas():
    cols = ["id", "titulo (no se importa)", "moneda"]
    cols += ["precio_" + b for b in BASES]
    for i in range(1, MAX_CABINAS + 1):
        cols += ["cabina{}_tipo".format(i)] + ["cabina{}_precio_{}".format(i, b) for b in BASES]
    for i in range(1, MAX_HOTELES + 1):
        cols += ["hotel{}_{}".format(i, c) for c in HOTEL]
    for i in range(1, MAX_VUELOS + 1):
        cols += ["vuelo{}_{}".format(i, c) for c in VUELO]
    cols += ["crucero_" + c for c in CRUCERO]
    cols += ["foto_portada"]
    return cols


def leer_json():
    raw = json.loads(DATA.read_text(encoding="utf-8"))
    return raw, raw["paquetes"]


def guardar_json(raw):
    texto = json.dumps(raw, ensure_ascii=False, indent=2)
    with open(DATA, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(texto)


def cabinas_de(p):
    """Tipos de cabina en el orden en que estan cargados."""
    out = []
    for x in p.get("precios") or []:
        c = x.get("cabina")
        if c and c not in out:
            out.append(c)
    return out


# ------------------------------------------------------------------ exportar
def exportar():
    _, paquetes = leer_json()
    filas, avisos = [], []
    for p in paquetes:
        if not p.get("activo"):
            continue
        f = {c: "" for c in columnas()}
        f["id"], f["titulo (no se importa)"] = p["id"], p["titulo"]
        f["moneda"] = p["precio_desde"].get("moneda", "")
        cabs = cabinas_de(p)
        for x in p.get("precios") or []:
            if x.get("cabina"):
                i = cabs.index(x["cabina"]) + 1
                if i > MAX_CABINAS:
                    avisos.append("{}: mas de {} cabinas".format(p["id"], MAX_CABINAS))
                    continue
                f["cabina{}_tipo".format(i)] = x["cabina"]
                f["cabina{}_precio_{}".format(i, x["base"])] = x["valor"]
            else:
                f["precio_" + x["base"]] = x["valor"]
        for i, h in enumerate(p.get("hoteles") or [], 1):
            if i > MAX_HOTELES:
                avisos.append("{}: mas de {} hoteles".format(p["id"], MAX_HOTELES))
                break
            if isinstance(h, str):
                h = {"nombre": h}
            for c in HOTEL:
                f["hotel{}_{}".format(i, c)] = "" if h.get(c) is None else h.get(c)
        for i, v in enumerate(p.get("vuelos") or [], 1):
            if i > MAX_VUELOS:
                avisos.append("{}: mas de {} vuelos".format(p["id"], MAX_VUELOS))
                break
            for c in VUELO:
                f["vuelo{}_{}".format(i, c)] = v.get(c) or ""
        for c in CRUCERO:
            f["crucero_" + c] = (p.get("crucero") or {}).get(c) or ""
        f["foto_portada"] = p.get("foto_portada") or ""
        filas.append(f)
    with open(CSV, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columnas(), delimiter=";", quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(filas)
    print("OK  {} ({} paquetes activos, {} columnas)".format(CSV.relative_to(ROOT), len(filas), len(columnas())))
    for a in avisos:
        print("!   " + a)
    return 0


# ------------------------------------------------------------------ importar
def entero(valor, donde, errores):
    s = valor.strip()
    for m in MONEDAS:
        s = s.replace(m, "")
    s = s.replace("$", "").replace(" ", "")
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", s):   # 2.490 o 1.322.790
        s = s.replace(".", "")
    if not s.isdigit() or int(s) <= 0:
        errores.append('{}: "{}" no es un numero entero (ejemplo: 2490)'.format(donde, valor))
        return None
    return int(s)


def texto(valor, donde, errores):
    s = valor.strip()
    if s.lower() in NO_VALE:
        errores.append('{}: "{}" no se carga; si el dato no esta, deja la celda vacia'.format(donde, valor))
        return None
    return s


def web(valor, donde, errores):
    s = texto(valor, donde, errores)
    if s is not None and not re.match(r"https?://\S+\.\S+$", s):
        errores.append('{}: "{}" tiene que ser una direccion web completa (https://...)'.format(donde, valor))
        return None
    return s


def categoria(valor, donde, errores):
    s = texto(valor, donde, errores)
    if s is None:
        return None
    m = re.fullmatch(r"(\d)\s*(\*|estrellas?|★)?\s*(sup(?:erior)?\.?)?", s, re.I)
    if m:
        return m.group(1) + "*" + (" Sup" if m.group(3) else "")
    return s


def si_no(valor, donde, errores):
    s = texto(valor, donde, errores)
    if s is None:
        return None
    if s.lower() in ("si", "sí"):
        return "Incluido"
    if s.lower() == "no":
        return "No incluido"
    return s


def importar(probar):
    if not CSV.exists():
        print("ERROR: no esta {}. Generala con: python planilla-paquetes.py exportar".format(CSV.relative_to(ROOT)))
        return 1
    raw, paquetes = leer_json()
    por_id = {p["id"]: p for p in paquetes}
    claves_antes = {p["id"]: set(p) for p in paquetes}
    with open(CSV, encoding="utf-8-sig", newline="") as fh:
        muestra = fh.read(4096)
        fh.seek(0)
        sep = ";" if muestra.count(";") >= muestra.count(",") else ","
        filas = list(csv.DictReader(fh, delimiter=sep))
    errores, cambios = [], []
    faltan = [c for c in ("id", "moneda") if filas and c not in filas[0]]
    if faltan:
        print("ERROR: a la planilla le faltan las columnas {}".format(", ".join(faltan)))
        return 1
    desconocidas = [c for c in (filas[0].keys() if filas else []) if c and c not in columnas()]
    if desconocidas:
        errores.append("columnas que no se reconocen: {}".format(", ".join(desconocidas)))

    for n, f in enumerate(filas, 2):
        f = {k: (v or "") for k, v in f.items() if k}
        pid = f.get("id", "").strip()
        if not pid:
            if any(v.strip() for v in f.values()):
                errores.append("fila {}: falta el id del paquete".format(n))
            continue
        if pid not in por_id:
            errores.append('fila {}: no existe un paquete con id "{}"'.format(n, pid))
            continue
        p = por_id[pid]
        donde = lambda col: "fila {} ({}), columna {}".format(n, pid, col)

        def poner(obj, clave, valor, col):
            if valor is not None and obj.get(clave) != valor:
                cambios.append("{} · {}: {} -> {}".format(pid, col, obj.get(clave), valor))
                obj[clave] = valor

        # moneda
        if f.get("moneda", "").strip():
            m = f["moneda"].strip().upper()
            if m not in MONEDAS:
                errores.append('{}: "{}" tiene que ser USD, ARS o EUR'.format(donde("moneda"), f["moneda"]))
            else:
                poner(p["precio_desde"], "moneda", m, "moneda")

        # precios: generales y por cabina
        precios = p.setdefault("precios", [])

        def poner_precio(base, cabina, valor, col):
            for x in precios:
                if x["base"] == base and (x.get("cabina") or "") == (cabina or ""):
                    if x["valor"] != valor:
                        cambios.append("{} · {}: {} -> {}".format(pid, col, x["valor"], valor))
                        x["valor"] = valor
                    return
            nuevo = {"base": base, "valor": valor}
            if cabina:
                nuevo = {"base": base, "cabina": cabina, "valor": valor}
            precios.append(nuevo)
            cambios.append("{} · {}: (vacio) -> {}".format(pid, col, valor))

        for b in BASES:
            col = "precio_" + b
            if f.get(col, "").strip():
                v = entero(f[col], donde(col), errores)
                if v:
                    poner_precio(b, "", v, col)
        cabs = cabinas_de(p)
        for i in range(1, MAX_CABINAS + 1):
            tipo = texto(f.get("cabina{}_tipo".format(i), ""), donde("cabina{}_tipo".format(i)), errores) or ""
            con_precio = [b for b in BASES if f.get("cabina{}_precio_{}".format(i, b), "").strip()]
            if not tipo and not con_precio:
                continue
            viejo = cabs[i - 1] if i <= len(cabs) else ""
            if not tipo:
                tipo = viejo
            if not tipo:
                errores.append("{}: hay precios pero falta el tipo de cabina".format(donde("cabina{}_tipo".format(i))))
                continue
            if viejo and tipo != viejo:   # se renombro la cabina: se actualizan sus precios
                for x in precios:
                    if x.get("cabina") == viejo:
                        x["cabina"] = tipo
                cambios.append("{} · cabina{}_tipo: {} -> {}".format(pid, i, viejo, tipo))
            for b in con_precio:
                col = "cabina{}_precio_{}".format(i, b)
                v = entero(f[col], donde(col), errores)
                if v:
                    poner_precio(b, tipo, v, col)

        # hoteles y vuelos: la fila N completa o corrige el hotel/vuelo N
        for lista, campos, maxi, pref in (("hoteles", HOTEL, MAX_HOTELES, "hotel"),
                                          ("vuelos", VUELO, MAX_VUELOS, "vuelo")):
            items = p.setdefault(lista, [])
            for i in range(1, maxi + 1):
                celdas = {c: f.get("{}{}_{}".format(pref, i, c), "") for c in campos}
                if not any(v.strip() for v in celdas.values()):
                    continue
                while len(items) < i:
                    items.append({c: ("" if c != "noches" else None) for c in campos})
                if isinstance(items[i - 1], str):
                    items[i - 1] = {"ciudad": "", "nombre": items[i - 1], "categoria": "", "noches": None, "web": ""}
                for c, v in celdas.items():
                    if not v.strip():
                        continue
                    col = "{}{}_{}".format(pref, i, c)
                    if c == "noches":
                        val = entero(v, donde(col), errores)
                    elif c == "web":
                        val = web(v, donde(col), errores)
                    elif c == "categoria":
                        val = categoria(v, donde(col), errores)
                    else:
                        val = texto(v, donde(col), errores)
                    poner(items[i - 1], c, val, col)
            if pref == "hotel":
                for i, h in enumerate(items, 1):
                    if isinstance(h, dict) and not (h.get("nombre") or "").strip() and any(
                            str(h.get(c) or "").strip() for c in campos):
                        errores.append("fila {} ({}): el hotel {} tiene datos pero no tiene nombre".format(n, pid, i))

        # crucero
        cel = {c: f.get("crucero_" + c, "") for c in CRUCERO}
        if any(v.strip() for v in cel.values()):
            cru = p.get("crucero") if isinstance(p.get("crucero"), dict) else {}
            p["crucero"] = cru
            for c, v in cel.items():
                if not v.strip():
                    continue
                col = "crucero_" + c
                if c == "web":
                    val = web(v, donde(col), errores)
                elif c in ("bebidas", "propinas", "wifi", "asistencia"):
                    val = si_no(v, donde(col), errores)
                else:
                    val = texto(v, donde(col), errores)
                poner(cru, c, val, col)

        # foto de portada
        if f.get("foto_portada", "").strip():
            ft = texto(f["foto_portada"], donde("foto_portada"), errores)
            if ft and not re.match(r"https?://", ft) and not (ROOT / ft.lstrip("/")).exists():
                errores.append('{}: no se encuentra el archivo "{}" en la carpeta del sitio'.format(donde("foto_portada"), ft))
            elif ft:
                poner(p, "foto_portada", ft, "foto_portada")

        # P1: el precio destacado es el de base doble (el mas bajo si hay varias cabinas)
        dobles = [x["valor"] for x in precios if x["base"] == "doble"]
        if dobles:
            pd = p["precio_desde"]
            if pd["valor"] != min(dobles):
                cambios.append("{} · precio destacado: {} -> {}".format(pid, pd["valor"], min(dobles)))
                pd["valor"] = min(dobles)
            nota = pd.get("nota") or ""
            if not nota.startswith("por persona en base doble"):
                resto = re.split(r"\s+—\s+", nota, maxsplit=1)
                pd["nota"] = "por persona en base doble" + (" — " + resto[1] if len(resto) > 1 else "")
                cambios.append("{} · nota del precio -> {}".format(pid, pd["nota"]))

    if errores:
        print("\nHay {} problema(s). No se guardo nada. Corregilos en la planilla y volve a importar:\n".format(len(errores)))
        for x in errores:
            print("  x  " + x)
        return 1
    if not cambios:
        print("=   La planilla no trae datos nuevos. No hay nada que guardar.")
        return 0
    print("\n{} cambio(s):".format(len(cambios)))
    for c in cambios:
        print("  +  " + c)
    if probar:
        print("\n(prueba: no se guardo nada)")
        return 0
    for p in paquetes:   # no se agregan listas vacias a paquetes que no las tenian
        for k in ("precios", "hoteles", "vuelos"):
            if k not in claves_antes[p["id"]] and not p.get(k):
                p.pop(k, None)
    RESPALDOS.mkdir(exist_ok=True)
    copia = RESPALDOS / "paquetes-{}.json".format(datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(DATA, copia)
    guardar_json(raw)
    print("\nOK  data/paquetes.json actualizado (copia anterior en {}).".format(copia.relative_to(ROOT)))
    print("    Ahora corre: python build-paquetes.py")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["exportar"]:
        sys.exit(exportar())
    if args[:1] == ["importar"]:
        sys.exit(importar("--probar" in args))
    print(__doc__)
    sys.exit(2)
