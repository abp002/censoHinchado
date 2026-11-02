"""Lectores de los ficheros brutos: PX y CSV del INE, PERE (Tempus) y resultados de Infoelectoral."""
import itertools
import json
import re
from pathlib import Path

import pandas as pd

from .fuentes import BRUTOS_INE, BRUTOS_INFOE, ELECCIONES, OCE_G2026_FICHERO, Eleccion

MUNICIPIO = re.compile(r"^(\d{2}) ?(\d{3})\b")


def tipo_elector(etiqueta: str) -> str | None:
    """CER (españoles residentes), CERA (españoles en el extranjero), CERE (extranjeros UE) o None (totales)."""
    e = etiqueta.lower()
    if "españoles" in e and "extranjero" in e:
        return "CERA"
    if "españoles" in e and "residentes en españa" in e:
        return "CER"
    if "extranjeros" in e and "parlamento" not in e:  # el CERE de europeas va aparte
        return "CERE"
    return None


def codigo(municipio: str) -> str | None:
    m = MUNICIPIO.match(municipio.strip())
    return m.group(1) + m.group(2) if m else None


def _numero(x, miles: bool = True) -> int | None:
    """'1.234' -> 1234 en los CSV; en los PX no hay separador de miles. Vacíos y '..' -> None."""
    x = str(x).strip().strip('"')
    if miles:
        x = x.replace(".", "")
    return int(float(x)) if x not in ("", ".", "..", "...", "nan", "-") else None


def lee_px(texto: str) -> pd.DataFrame:
    """PX de electores (Municipios x Tipo de elector) -> cod, tipo, electores."""
    def lista(clave):
        m = re.search(clave + r"=(.*?);", texto, re.S)
        return re.findall(r'"([^"]*)"', m.group(1))
    dims = lista("STUB") + lista("HEADING")
    valores = [lista(r'VALUES\("%s"\)' % re.escape(d)) for d in dims]
    datos = re.search(r"DATA=(.*?);", texto, re.S).group(1).split()
    i_mun = dims.index("Municipios")
    filas = []
    for combo, v in zip(itertools.product(*valores), datos):
        cod = codigo(combo[i_mun])
        otras = [x for i, x in enumerate(combo) if i != i_mun]
        tipo = tipo_elector(otras[0]) if otras else None
        if cod and tipo:
            filas.append((cod, tipo, _numero(v, miles=False)))
    return pd.DataFrame(filas, columns=["cod", "tipo", "electores"])


def lee_csv(ruta: Path) -> pd.DataFrame:
    """CSV de electores del INE (Municipios;<tipo>;Total) -> cod, tipo, electores."""
    d = pd.read_csv(ruta, sep=";", dtype=str, encoding="utf-8-sig")
    mun, tipo, total = "Municipios", d.columns[-2], d.columns[-1]
    d = d.dropna(subset=[mun, tipo])
    d = pd.DataFrame({"cod": d[mun].map(codigo), "tipo": d[tipo].map(tipo_elector),
                      "electores": d[total].map(_numero)})
    return d.dropna(subset=["cod", "tipo"])


def lee_eleccion(e: Eleccion) -> pd.DataFrame:
    ruta = BRUTOS_INE / e.fichero
    if ruta.suffix == ".px":
        d = lee_px(ruta.read_text(encoding="latin1"))
    elif ruta.suffix == ".xlsx":
        d = lee_oce_municipios(ruta)
    else:
        d = lee_csv(ruta)
    d = d.pivot_table(index="cod", columns="tipo", values="electores", aggfunc="first")
    return d.assign(eleccion=e.id).reset_index()


def censo_panel() -> pd.DataFrame:
    """Formato largo: eleccion, cod, CER, CERA, CERE para todas las elecciones del catálogo."""
    return pd.concat([lee_eleccion(e) for e in ELECCIONES], ignore_index=True)


def lee_pere(ruta: Path = BRUTOS_INE / "pere_71118.json") -> pd.DataFrame:
    """Padrón de españoles residentes en el extranjero por municipio de inscripción, a 1 de enero."""
    filas = []
    for serie in json.loads(ruta.read_text()):
        meta = {m["T3_Variable"]: m for m in serie["MetaData"]}
        if meta["Sexo"]["Nombre"] != "Ambos sexos" or "Municipios" not in meta:
            continue
        cod = meta["Municipios"]["Codigo"]
        for x in serie["Data"]:
            if x["Valor"] is not None:
                filas.append((cod, meta["Municipios"]["Nombre"], x["Anyo"], int(x["Valor"])))
    return pd.DataFrame(filas, columns=["cod", "nombre", "anyo", "pere"])


def lee_oce_municipios(ruta: Path) -> pd.DataFrame:
    """Tabla de la OCE de electores por municipio -> cod, tipo (CER, CERA), electores.

    Columnas: provincia, número de municipio, nombre, residentes en España, en el extranjero, total.
    Las filas de provincia y de total no traen número de municipio.
    Alguna fila llega sin código de provincia (Ziortza-Bolibar, 48915, en 2026): se hereda
    el de la fila anterior, que está en la misma provincia.
    """
    h = pd.read_excel(ruta, header=None, engine="calamine")
    c0 = h.iloc[:, 0].astype(str)
    prov = c0.where(c0.str.fullmatch(r"\d{1,2}")).ffill()
    h, prov = h[pd.to_numeric(h.iloc[:, 1], errors="coerce").notna()], prov[pd.to_numeric(h.iloc[:, 1], errors="coerce").notna()]
    cod = prov.str.zfill(2) + h.iloc[:, 1].astype(float).astype(int).map("{:03d}".format)
    return pd.concat([pd.DataFrame({"cod": cod.values, "tipo": t, "electores": h.iloc[:, i].astype(int).values})
                      for t, i in (("CER", 3), ("CERA", 4))], ignore_index=True)


def lee_oce_provincias(ruta: Path = BRUTOS_INE / OCE_G2026_FICHERO) -> pd.DataFrame:
    """Tabla de la OCE de electores por provincia -> prov, nombre, cer, cera (sin la fila de total)."""
    h = pd.read_excel(ruta, header=None, engine="calamine")
    h = h[h.iloc[:, 0].astype(str).str.fullmatch(r"\d{1,2}")]
    return pd.DataFrame({"prov": h.iloc[:, 0].astype(str).str.zfill(2).values,
                         "nombre": h.iloc[:, 1].astype(str).str.strip().values,
                         "cer": h.iloc[:, 2].astype(int).values,
                         "cera": h.iloc[:, 3].astype(int).values})


def _hoja_municipios(carpeta: Path, desfase: int) -> pd.DataFrame:
    """Hoja Municipios de Infoelectoral -> cod, nombre, poblacion, censo_mesa, votantes, candidatura, votos.

    desfase: las municipales traen una columna más al principio que las generales.
    """
    xlsx = next(carpeta.glob("*.xlsx"))
    hoja = pd.read_excel(xlsx, sheet_name="Municipios", header=None, engine="calamine")
    siglas = hoja.iloc[5]
    cuerpo = hoja.iloc[6:].reset_index(drop=True)
    base = cuerpo.iloc[:, desfase:]
    ok = base.iloc[:, 1].notna() & base.iloc[:, 3].notna()
    cuerpo, base = cuerpo[ok], base[ok]
    cod = base.iloc[:, 1].astype(int).map("{:02d}".format) + base.iloc[:, 3].astype(int).map("{:03d}".format)
    fijo = pd.DataFrame({"cod": cod, "nombre": base.iloc[:, 4].astype(str).str.strip(),
                         "poblacion": base.iloc[:, 5], "censo_mesa": base.iloc[:, 7],
                         "votantes": base.iloc[:, 8]})
    primera = 13 + desfase
    partidos = cuerpo.iloc[:, primera:].copy()
    partidos.columns = [str(x).strip() for x in siglas.iloc[primera:]]
    partidos["cod"] = cod.values
    largo = partidos.melt(id_vars="cod", var_name="candidatura", value_name="votos")
    largo = largo[pd.to_numeric(largo.votos, errors="coerce").fillna(0) > 0]
    largo["votos"] = largo.votos.astype(int)
    return fijo.merge(largo, on="cod")


def lee_municipales(e: Eleccion) -> pd.DataFrame:
    return _hoja_municipios(BRUTOS_INFOE / e.infoelectoral, desfase=1)


def lee_generales_municipios(codigo_infoe: str) -> pd.DataFrame:
    """Votos del Congreso por municipio. No incluye el voto CERA, que solo está por provincia."""
    return _hoja_municipios(BRUTOS_INFOE / codigo_infoe, desfase=0)


def lee_generales_provincias(codigo_infoe: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """PROV_02_… -> (provincias: prov, nombre, censo_cer, censo_cera, votantes_cera, validos;
                    votos: prov, candidatura, votos, diputados), ya con el voto CERA sumado."""
    xlsx = next((BRUTOS_INFOE / ("PROV_" + codigo_infoe)).glob("*.xlsx"))
    hoja = pd.read_excel(xlsx, sheet_name=0, header=None, engine="calamine")
    cab = hoja.iloc[5].astype(str).str.strip()
    siglas = hoja.iloc[4]
    cuerpo = hoja.iloc[6:]
    cuerpo = cuerpo[pd.to_numeric(cuerpo.iloc[:, 1], errors="coerce").notna()]
    col = {n: i for i, n in enumerate(cab)}
    prov = cuerpo.iloc[:, 1].astype(int).map("{:02d}".format)
    provincias = pd.DataFrame({
        "prov": prov.values, "nombre": cuerpo.iloc[:, 2].astype(str).str.strip().values,
        "censo_cer": cuerpo.iloc[:, col["Censo electoral sin CERA"]].astype(int).values,
        "censo_cera": cuerpo.iloc[:, col["Censo CERA"]].astype(int).values,
        "votantes_cera": cuerpo.iloc[:, col["Total votantes CERA"]].astype(int).values,
        "validos": cuerpo.iloc[:, col["Votos válidos"]].astype(int).values,
    })
    filas = []
    for j in range(len(cab)):
        if cab.iloc[j] == "Votos" and j + 1 < len(cab) and cab.iloc[j + 1] == "Diputados":
            v = pd.to_numeric(cuerpo.iloc[:, j], errors="coerce").fillna(0).astype(int)
            dip = pd.to_numeric(cuerpo.iloc[:, j + 1], errors="coerce").fillna(0).astype(int)
            filas.append(pd.DataFrame({"prov": prov.values, "candidatura": str(siglas.iloc[j]).strip(),
                                       "votos": v.values, "diputados": dip.values}))
    votos = pd.concat(filas)
    return provincias, votos[votos.votos > 0]
