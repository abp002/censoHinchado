"""La página pública: `censo web` la monta en _site/ a partir de salidas/ y referencia/.

No calcula nada nuevo: lee los CSV que escriben `censo pueblos`, `censo cera`, `censo alerta`,
`censo ensayo` y `censo noche`, coloca cada pueblo en el mapa y rellena la plantilla de
censo/sitio/. Si existe salidas/noche_pendientes_cera.csv (la noche de unas generales),
la página enseña qué escaños quedan pendientes del voto exterior.
"""
import html
import json
import math
import shutil
from pathlib import Path

import pandas as pd

from . import fuentes, pueblos

RAIZ = Path(__file__).resolve().parent.parent
SITIO = Path(__file__).resolve().parent / "sitio"
ANCHO = 1000  # ancho del mapa en unidades del SVG
CANARIAS = ("35", "38")
# Las islas van en un recuadro al suroeste: su esquina superior derecha, en lon/lat de la península
CANARIAS_ESQUINA = (-6.4, 36.0)
MESES = ["ene.", "feb.", "mar.", "abr.", "mayo", "jun.", "jul.", "ago.", "sept.", "oct.", "nov.", "dic."]
# g2015b es la tabla p09/a2015_1 del INE, que no aclara si es diciembre de 2015 o junio de 2016
ETIQUETAS = {"g2015b": "dic. 2015 o jun. 2016"}
UMBRAL_EN_JUEGO = 0.10  # el mismo que usa `censo ensayo`
OCE_2023 = "https://www.ine.es/oficina_censo/elecmun2023/elec_mun_2023_municipios_impugnables.xlsx"


def _mercator(lon: float, lat: float) -> tuple[float, float]:
    return math.radians(lon), -math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


class Mapa:
    """Proyección del mapa: Mercator, con Canarias desplazada a un recuadro al suroeste."""

    def __init__(self, provincias: list[dict], ancho: int = ANCHO, margen: int = 12):
        self.provincias = provincias
        islas = [_mercator(x, y) for p in provincias if p["cod"] in CANARIAS for a in p["anillos"] for x, y in a]
        ex, ey = _mercator(*CANARIAS_ESQUINA)
        self._dx = ex - max(x for x, _ in islas)
        self._dy = ey - min(y for _, y in islas)
        todo = [self._plano(x, y, p["cod"]) for p in provincias for a in p["anillos"] for x, y in a]
        self._x0, self._y0 = min(x for x, _ in todo), min(y for _, y in todo)
        self._k = (ancho - 2 * margen) / (max(x for x, _ in todo) - self._x0)
        self._margen = margen
        self.ancho = ancho
        self.alto = round((max(y for _, y in todo) - self._y0) * self._k + 2 * margen)
        # Recuadro de Canarias: una línea por encima y otra a la derecha
        cx, cy = self.xy(*CANARIAS_ESQUINA, "00")
        self.recuadro = f"M0 {cy - 8:.1f}H{cx + 8:.1f}V{self.alto}"

    def _plano(self, lon: float, lat: float, prov: str) -> tuple[float, float]:
        x, y = _mercator(lon, lat)
        return (x + self._dx, y + self._dy) if prov in CANARIAS else (x, y)

    def xy(self, lon: float, lat: float, prov: str) -> tuple[float, float]:
        x, y = self._plano(lon, lat, prov)
        return (round((x - self._x0) * self._k + self._margen, 1),
                round((y - self._y0) * self._k + self._margen, 1))

    def trazos(self) -> list[str]:
        """Un `d` de SVG por provincia."""
        out = []
        for p in self.provincias:
            d = []
            for a in p["anillos"]:
                pts = [self.xy(x, y, p["cod"]) for x, y in a]
                d.append("M" + "L".join(f"{x:g} {y:g}" for x, y in pts) + "Z")
            out.append("".join(d))
        return out


def nombre_legible(nombre: str) -> str:
    """«Acebeda, La» -> «La Acebeda»; «SACAÑET» -> «Sacañet». El INE pone el artículo
    detrás y algún nombre llega en mayúsculas."""
    if nombre.isupper():
        menores = {"de", "del", "la", "el", "los", "las", "y", "i"}
        nombre = " ".join(w if i and w in menores else w.capitalize()
                          for i, w in enumerate(nombre.lower().split(" ")))
    if ", " in nombre:
        resto, articulo = nombre.rsplit(", ", 1)
        if len(articulo) <= 4 and " " not in articulo:
            union = "" if articulo.endswith("'") else " "
            return f"{articulo}{union}{resto}"
    return nombre


def etiqueta(eleccion: str | None) -> str | None:
    """m2023 -> «mayo 2023»."""
    if eleccion is None:
        return None
    if eleccion in ETIQUETAS:
        return ETIQUETAS[eleccion]
    anyo, mes = fuentes.POR_ID[eleccion].fecha.split("-")
    return f"{MESES[int(mes) - 1]} {anyo}"


def _n(v):
    """NaN -> None y los enteros como enteros: el JSON de la página no admite NaN."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def _lee(salidas: Path, nombre: str, **kw) -> pd.DataFrame:
    return pd.read_csv(salidas / nombre, dtype={"cod": str, "prov": str}, **kw)


def datos_pueblos(salidas: Path, referencia: Path, mapa: Mapa) -> dict:
    """Elecciones y pueblos señalados, cada uno con su sitio en el mapa, su resultado
    (si hay), si está en la lista de la OCE de 2023 y lo publicado sobre él."""
    sen = _lee(salidas, "pueblos_senalados.csv")
    mar = _lee(salidas, "pueblos_margen.csv").set_index(["eleccion", "cod"])
    coords = pd.read_csv(referencia / "municipios_coords.csv", dtype={"cod": str}).set_index("cod")
    provs = {p["cod"]: p["nombre"] for p in mapa.provincias}
    oce = pd.read_csv(referencia / "oce_m2023_altas_no_justificadas.csv", dtype=str)
    oce_mun = set(oce[oce.entidad_menor.isna()].cod)
    oce_menor = set(oce[oce.entidad_menor.notna()].cod) - oce_mun
    casos = pd.read_csv(referencia / "casos_publicos.csv", dtype=str)
    ventanas = {m: (antes, despues[0]) for m, antes, despues in pueblos.ventanas()}

    filas = []
    for r in sen.itertuples():
        if r.cod not in coords.index:
            raise SystemExit(f"{r.cod} {r.nombre}: sin coordenadas; repite herramientas/geografia.py")
        x, y = mapa.xy(coords.lon[r.cod], coords.lat[r.cod], r.cod[:2])
        f = {"cod": r.cod, "e": r.eleccion, "n": nombre_legible(r.nombre), "p": provs[r.cod[:2]],
             "x": x, "y": y, "antes": _n(r.cer_antes), "mun": _n(r.cer_municipal), "desp": _n(r.cer_despues),
             "exceso": _n(r.exceso), "pob": _n(r.pob), "padron": _n(r.pico_padron),
             "otras": sorted(int(e[1:]) for e in sen[(sen.cod == r.cod) & (sen.eleccion != r.eleccion)].eleccion)}
        if (r.eleccion, r.cod) in mar.index:
            m = mar.loc[(r.eleccion, r.cod)]
            f["res"] = {"gana": m.gana, "v1": _n(float(m.v1)), "segundo": _n(m.segundo), "v2": _n(float(m.v2)),
                        "margen": _n(float(m.margen)), "mesa": _n(float(m.exceso_en_mesa)),
                        "alcanza": bool(m.pudo_decidir)}
        if r.eleccion == "m2023" and r.cod in oce_mun | oce_menor:
            f["oce"] = "municipio" if r.cod in oce_mun else "entidad menor"
        c = casos[(casos.cod == r.cod) & (casos.eleccion == r.eleccion)]
        if len(c):
            f["casos"] = c[["texto", "medio", "url"]].to_dict("records")
        filas.append(f)

    elecciones = []
    for m in sorted(sen.eleccion.unique()):
        antes, despues = ventanas[m]
        de_m = [f for f in filas if f["e"] == m]
        elecciones.append({"id": m, "anyo": int(m[1:]), "fecha": etiqueta(m), "antes": etiqueta(antes),
                           "despues": etiqueta(despues), "n": len(de_m),
                           "resultados": any("res" in f for f in de_m),
                           "alcanzan": sum(1 for f in de_m if f.get("res", {}).get("alcanza"))})
    return {"elecciones": elecciones, "pueblos": filas,
            "oce": {"municipios": len(oce_mun), "url": OCE_2023,
                    "vistos": sum(1 for f in filas if f.get("oce") == "municipio"),
                    "senalados": sum(1 for f in filas if "oce" in f)}}


# --- Trozos de HTML que se montan aquí porque salen de los datos ---

def num(v, decimales: int = 0) -> str:
    """1340 -> «1.340»; 11.03 -> «11,0» con un decimal."""
    s = f"{v:,.{decimales}f}"
    return s.replace(",", "·").replace(".", ",").replace("·", ".")


def _esc(v) -> str:
    return html.escape(str(v).strip())


def html_cambios(salidas: Path) -> tuple[str, int]:
    """Los escaños que cambiaron de partido al sumarse el voto exterior."""
    e = _lee(salidas, "cera_escanos.csv")
    fichas = []
    for (elec, prov), g in e.groupby(["eleccion", "prov"], sort=False):
        gana = g[g.escanos_con_cera > g.escanos_sin_cera].iloc[0]
        pierde = g[g.escanos_con_cera < g.escanos_sin_cera].iloc[0]
        anyo, mes = elec.split("_")[1][:4], int(elec.split("_")[1][4:])
        fichas.append(
            f"<article class='cambio ver'><p class='donde'>{_esc(gana.provincia)} · generales de {MESES[mes - 1]} {anyo}</p>"
            f"<p class='paso'><s>{_esc(pierde.candidatura)}</s><i>→</i><span>{_esc(gana.candidatura)}</span></p>"
            f"<p>El último escaño cambió de partido al contarse <b>{num(gana.votantes_cera)}</b> votos del exterior.</p></article>")
    return f"<div class='cambios'>{''.join(fichas)}</div>", len(fichas)


def html_ola(salidas: Path, minimo: float = 0.1) -> tuple[str, dict]:
    """Votantes exteriores nuevos esperados frente al margen del último escaño de 2023,
    por provincia, en escala logarítmica: con todos los inscritos y sin los suspendidos."""
    m = _lee(salidas, "cera_margen_2023_vs_g2026.csv")
    cifras = {"nuevos": int(m.cera_nuevos.sum()), "total": int((m.censo_cera + m.cera_nuevos).sum()),
              "sobre": int((m.veces_el_margen >= 1).sum()), "sobre_sin": int((m.veces_sin_suspendidos >= 1).sum())}
    d = m[m.veces_el_margen >= minimo]
    lo, hi = math.log10(0.05), math.log10(20)

    def pos(v: float) -> float:
        return round(100 * (math.log10(max(v, 0.05)) - lo) / (hi - lo), 2)

    marcas = "".join(f"<span style='left:{pos(t)}%'>×{num(t, 0 if t >= 1 else 1)}</span>" for t in (0.1, 0.5, 1, 2, 5, 10))
    filas = [f"<div class='ola-fila ola-eje'><span></span><div class='ola-pista'>{marcas}</div><span></span></div>"]
    for i, r in enumerate(d.itertuples()):
        a, b = pos(r.veces_sin_suspendidos), pos(r.veces_el_margen)
        filas.append(
            f"<div class='ola-fila' style='--i:{i}'><span class='ola-prov'>{_esc(r.provincia)}</span>"
            f"<div class='ola-pista'><i class='uno' style='left:{pos(1)}%'></i>"
            f"<i class='tramo' style='left:{a}%;width:{round(b - a, 2)}%'></i>"
            f"<i class='punto sin' style='left:{a}%'></i><i class='punto con' style='left:{b}%'></i></div>"
            f"<span class='ola-valor mono'>×{num(r.veces_el_margen, 1)} <small>×{num(r.veces_sin_suspendidos, 1)}</small></span></div>")
    detalle = "".join(
        f"<tr><td>{_esc(r.provincia)}</td><td>{_esc(r.partido_mas_cerca)}</td><td class='n'>{num(r.votos_que_faltan)}</td>"
        f"<td class='n'>{num(r.cera_nuevos)}</td><td class='n'>{num(r.votantes_nuevos_esperados)}</td>"
        f"<td class='n'>{num(r.votantes_nuevos_sin_suspendidos)}</td></tr>" for r in d.itertuples())
    tabla = ("<details class='detalle ver'><summary>Las cifras de cada provincia</summary><div class='desliza'><table class='tabla'>"
             "<thead><tr><th>Provincia</th><th>Partido más cerca de otro escaño en 2023</th><th class='n'>Votos que le faltaron</th>"
             "<th class='n'>Electores exteriores nuevos</th><th class='n'>Votantes nuevos esperados</th>"
             "<th class='n'>Sin los suspendidos</th></tr></thead>"
             f"<tbody>{detalle}</tbody></table></div></details>")
    return f"<div class='ola'>{''.join(filas)}</div>{tabla}", cifras


def html_ensayo(salidas: Path) -> tuple[str, dict]:
    """La noche electoral hacia atrás: provincias con el último escaño al alcance del exterior."""
    d = _lee(salidas, "noche_ensayo.csv")
    j = d[d.ventaja_neta <= UMBRAL_EN_JUEGO].sort_values("ventaja_neta")
    filas = []
    for r in j.itertuples():
        anyo, mes = r.eleccion.split("_")[1][:4], int(r.eleccion.split("_")[1][4:])
        filas.append(
            f"<tr{' class=si' if r.cambio_real else ''}><td>{_esc(r.provincia)}</td><td class='mono'>{MESES[mes - 1]} {anyo}</td>"
            f"<td>{_esc(r.aspirante)}</td><td class='n'>{num(r.votos_que_faltan)}</td><td class='n'>{num(r.votantes_cera)}</td>"
            f"<td class='n'>{num(100 * r.ventaja_neta, 1)} %</td><td>{'Cambió' if r.cambio_real else 'No cambió'}</td></tr>")
    tabla = ("<div class='desliza'><table class='tabla'><thead><tr><th>Provincia</th><th>Generales</th><th>Aspirante al último escaño</th>"
             "<th class='n'>Votos que le faltaban</th><th class='n'>Votantes exteriores</th>"
             "<th class='n'>Ventaja que necesitaba</th><th>Escrutinio general</th></tr></thead>"
             f"<tbody>{''.join(filas)}</tbody></table></div>")
    return tabla, {"elecciones": d.eleccion.nunique(), "senaladas": len(j), "cambiaron": int(j.cambio_real.sum()),
                   "fuera": int((d.cambio_real & (d.ventaja_neta > UMBRAL_EN_JUEGO)).sum())}


def html_noche(salidas: Path) -> str:
    """La noche de las generales: lo que deja `censo noche`. Antes de esa noche, un aviso."""
    f = salidas / "noche_pendientes_cera.csv"
    if not f.exists():
        return ("<p class='aviso'>Con los resultados provisionales de esa noche, aquí saldrán las provincias cuyo "
                "último escaño queda al alcance del voto exterior, que se cuenta cinco días después.</p>")
    d = pd.read_csv(f, dtype={"prov": str})
    d = d[d.ventaja_neta <= 2 * UMBRAL_EN_JUEGO].sort_values("ventaja_neta")
    if d.empty:
        return "<p class='aviso'>Con los provisionales de esta noche, ningún último escaño queda al alcance del voto exterior.</p>"
    escr = "escrutado" in d
    filas = "".join(
        f"<tr{' class=si' if r.ventaja_neta <= UMBRAL_EN_JUEGO else ''}><td>{_esc(r.provincia)}</td>"
        + (f"<td class='n'>{num(r.escrutado, 1)} %</td>" if escr else "")
        + f"<td>{_esc(r.aspirante)}</td><td class='n'>{num(r.votos_que_faltan)}</td><td class='n'>{num(r.votantes_cera)}</td>"
        f"<td class='n'>{num(100 * r.ventaja_neta, 1)} %</td><td class='n'>{num(100 * r.ventaja_neta_sin_suspendidos, 1)} %</td></tr>"
        for r in d.itertuples())
    return ("<div class='desliza'><table class='tabla'><thead><tr><th>Provincia</th>"
            + ("<th class='n'>Escrutado</th>" if escr else "")
            + "<th>Aspirante al último escaño</th><th class='n'>Votos que le faltan</th>"
            "<th class='n'>Votantes exteriores esperados</th><th class='n'>Ventaja que necesita</th>"
            "<th class='n'>Sin los suspendidos</th></tr></thead>"
            f"<tbody>{filas}</tbody></table></div>"
            "<p class='nota'>Provisionales de la noche electoral. Dice qué está en juego, no hacia dónde cae.</p>")


def cifras_alerta(salidas: Path, referencia: Path) -> dict:
    a = _lee(salidas, "alerta_m2023.csv")
    oce = pd.read_csv(referencia / "oce_m2023_altas_no_justificadas.csv", dtype=str)
    return {"n": len(a), "en_oce": int(a.cod.isin(set(oce.cod)).sum())}


def construye(destino: Path, salidas: Path = RAIZ / "salidas", referencia: Path = RAIZ / "referencia") -> Path:
    """Escribe la página en `destino` y devuelve la ruta de index.html."""
    mapa = Mapa(json.loads((referencia / "provincias.json").read_text()))
    datos = datos_pueblos(salidas, referencia, mapa)
    cambios, n_cambios = html_cambios(salidas)
    ola, c_ola = html_ola(salidas)
    ensayo, c_ens = html_ensayo(salidas)
    alerta = cifras_alerta(salidas, referencia)
    el = datos["elecciones"]
    con_res = [e for e in el if e["resultados"]]
    total, oce = sum(e["n"] for e in el), datos["oce"]
    m2023 = next(e for e in el if e["id"] == "m2023")
    valores = {
        "mapa_ancho": mapa.ancho, "mapa_alto": mapa.alto, "recuadro": mapa.recuadro,
        "provincias": "".join(f"<path d='{d}'/>" for d in mapa.trazos()),
        "datos": json.dumps(datos, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("</", "<\\/"),
        "total": total, "n_elecciones": len(el), "primera": el[0]["anyo"], "ultima": el[-1]["anyo"],
        "alcanzan": sum(e["alcanzan"] for e in con_res), "con_resultados": sum(e["n"] for e in con_res),
        "desde_resultados": con_res[0]["anyo"],
        "por_eleccion": ", ".join(f"{e['n']} en {e['anyo']}" for e in el),
        "oce_municipios": oce["municipios"], "oce_vistos": oce["vistos"], "oce_senalados": oce["senalados"],
        "oce_vistos_pct": num(100 * oce["vistos"] / oce["municipios"]),
        "oce_senalados_pct": num(100 * oce["senalados"] / m2023["n"]), "n_2023": m2023["n"], "oce_url": oce["url"],
        "alerta_n": alerta["n"], "alerta_oce": alerta["en_oce"], "alerta_pct": num(100 * alerta["en_oce"] / alerta["n"]),
        "cambios": cambios, "n_cambios": n_cambios, "ola": ola, "ensayo": ensayo, "noche": html_noche(salidas),
        "cera_nuevos": num(c_ola["nuevos"]), "cera_total": num(c_ola["total"]), "ola_sobre": c_ola["sobre"],
        "ola_sobre_sin": c_ola["sobre_sin"], "suspendidos": num(fuentes.SUSPENDIDOS_G2026),
        "ens_elecciones": c_ens["elecciones"], "ens_senaladas": c_ens["senaladas"], "ens_cambiaron": c_ens["cambiaron"],
        "umbral": num(100 * UMBRAL_EN_JUEGO),
    }
    pagina = (SITIO / "index.html").read_text()
    for k, v in valores.items():
        pagina = pagina.replace("{{" + k + "}}", str(v))
    if "{{" in pagina:
        raise SystemExit("plantilla con huecos sin rellenar: " + pagina[pagina.index("{{"):][:40])
    destino.mkdir(parents=True, exist_ok=True)
    for f in ("style.css", "app.js"):
        shutil.copy(SITIO / f, destino / f)
    (destino / "index.html").write_text(pagina)
    return destino / "index.html"
