"""Resultados provisionales de la noche electoral, tal como los sirve la web de Interior.

La web de resultados (resultados.<dominio de la elección>) pide al servidor JSON por
ámbito: `backend-difu/scope/data/getScopeData/<scopeId>/...`. El nomenclátor
(`backend-difu/nomenclator/getNomenclator`) da el scopeId de cada provincia (nivel 30).
Formato visto en las generales de 2023; `herramientas/provisionales.js` los baja todos
desde el Chrome de la página a un único JSON.

Cada cifra viene como {"pro": provisional, "def": definitivo}; la noche cuenta "pro".
"""
import json
from pathlib import Path

import pandas as pd

PROVINCIA = 30  # nivel del ámbito en el nomenclátor


def filas_de_ambito(respuesta: dict) -> list[dict]:
    """Una respuesta de getScopeData -> filas prov, candidatura, votos, diputados, validos,
    escrutado. Vacío si el ámbito no es una provincia o aún no hay escrutinio."""
    s = respuesta.get("scope") or {}
    e = s.get("escrutinio")
    if s.get("nivel") != PROVINCIA or not e or not e.get("partidos"):
        return []
    base = {"prov": str(s["codigo"]).zfill(2), "validos": e["votosValidos"]["pro"],
            "escrutado": e["porcCensoEscrutado"]["pro"], "envio": s.get("envio", 0)}
    return [base | {"candidatura": p["siglas"], "votos": p["votos"]["pro"],
                    "diputados": (p.get("cargos") or {}).get("pro", 0)} for p in e["partidos"]]


def lee(ruta: Path) -> pd.DataFrame:
    """Un JSON (una respuesta o una lista de ellas) o una carpeta de JSON -> filas para
    `censo noche`. Si una provincia sale varias veces, se queda el envío más reciente."""
    ruta = Path(ruta)
    ficheros = sorted(ruta.glob("*.json")) if ruta.is_dir() else [ruta]
    filas = []
    for f in ficheros:
        datos = json.loads(f.read_text(encoding="utf-8"))
        for r in datos if isinstance(datos, list) else [datos]:
            filas += filas_de_ambito(r)
    if not filas:
        raise ValueError(f"{ruta}: ninguna provincia con escrutinio")
    d = pd.DataFrame(filas)
    ultimo = d.groupby("prov").envio.transform("max")
    d = d[d.envio == ultimo].drop_duplicates(["prov", "candidatura"])
    return d[["prov", "candidatura", "votos", "diputados", "validos", "escrutado"]].reset_index(drop=True)
