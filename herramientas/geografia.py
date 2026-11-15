"""Geografía de la web: centro de cada municipio y contorno de cada provincia.

    uv run python herramientas/geografia.py

Baja es-atlas (https://github.com/martgnz/es-atlas, licencia ISC; datos del IGN, CC BY 4.0)
y escribe referencia/municipios_coords.csv (cod, lon, lat) y referencia/provincias.json
(código, nombre y anillos lon/lat). Solo hay que repetirlo si cambia el mapa municipal.
"""
import csv
import json
import urllib.request
from pathlib import Path

ATLAS = "https://cdn.jsdelivr.net/npm/es-atlas@0.6.0/es/{}.json"
REFERENCIA = Path(__file__).resolve().parent.parent / "referencia"


def baja(nombre: str) -> dict:
    with urllib.request.urlopen(ATLAS.format(nombre), timeout=120) as r:
        return json.load(r)


def arcos(topo: dict) -> list[list[tuple[float, float]]]:
    """Arcos de un TopoJSON cuantizado, ya en lon/lat."""
    (kx, ky), (dx, dy) = topo["transform"]["scale"], topo["transform"]["translate"]
    out = []
    for arco in topo["arcs"]:
        x = y = 0
        puntos = []
        for ax, ay in arco:
            x, y = x + ax, y + ay
            puntos.append((x * kx + dx, y * ky + dy))
        out.append(puntos)
    return out


def anillos(geom: dict, arcs: list) -> list[list[tuple[float, float]]]:
    """Anillos exteriores e interiores de un Polygon o MultiPolygon, sin distinguir."""
    if geom["type"] == "Polygon":
        poligonos = [geom["arcs"]]
    elif geom["type"] == "MultiPolygon":
        poligonos = geom["arcs"]
    else:
        return []
    out = []
    for pol in poligonos:
        for anillo in pol:
            puntos = []
            for i in anillo:
                tramo = arcs[i] if i >= 0 else arcs[~i][::-1]
                puntos.extend(tramo[1:] if puntos else tramo)
            out.append(puntos)
    return out


def area_y_centro(anillo: list[tuple[float, float]]) -> tuple[float, float, float]:
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(anillo, anillo[1:] + anillo[:1]):
        f = x0 * y1 - x1 * y0
        a += f
        cx += (x0 + x1) * f
        cy += (y0 + y1) * f
    if a == 0:
        return 0.0, anillo[0][0], anillo[0][1]
    return abs(a) / 2, cx / (3 * a), cy / (3 * a)


def centro(geom: dict, arcs: list) -> tuple[float, float]:
    """Centroide del anillo más grande: basta para poner un punto en el mapa."""
    _, x, y = max(area_y_centro(a) for a in anillos(geom, arcs))
    return x, y


def main():
    muni = baja("municipalities")
    arcs = arcos(muni)
    with open(REFERENCIA / "municipios_coords.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cod", "lon", "lat"])
        for g in sorted(muni["objects"]["municipalities"]["geometries"], key=lambda g: g["id"]):
            if g.get("arcs"):
                x, y = centro(g, arcs)
                w.writerow([g["id"], f"{x:.4f}", f"{y:.4f}"])
    prov = baja("provinces")
    arcs = arcos(prov)
    provincias = [{"cod": g["id"], "nombre": g["properties"]["name"],
                   "anillos": [[[round(x, 3), round(y, 3)] for x, y in a] for a in anillos(g, arcs)]}
                  for g in sorted(prov["objects"]["provinces"]["geometries"], key=lambda g: g["id"])
                  if g.get("arcs") and g["id"] <= "52"]
    (REFERENCIA / "provincias.json").write_text(json.dumps(provincias, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(provincias)} provincias; municipios en {REFERENCIA / 'municipios_coords.csv'}")


if __name__ == "__main__":
    main()
