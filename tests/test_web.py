"""La página pública: que cada pueblo señalado llegue al mapa, con su sitio y sin huecos."""
import json
import re
from pathlib import Path

import pandas as pd
import pytest

from censo import web

RAIZ = Path(__file__).resolve().parent.parent
SALIDAS, REFERENCIA = RAIZ / "salidas", RAIZ / "referencia"


@pytest.fixture(scope="module")
def mapa():
    return web.Mapa(json.loads((REFERENCIA / "provincias.json").read_text()))


def test_nombre_legible():
    assert web.nombre_legible("Acebeda, La") == "La Acebeda"
    assert web.nombre_legible("Ausines, Los") == "Los Ausines"
    assert web.nombre_legible("SAN MARTÍN DE LA VEGA") == "San Martín de la Vega"
    assert web.nombre_legible("Josa i Tuixén") == "Josa i Tuixén"
    assert web.nombre_legible("Hospitalet de Llobregat, L'") == "L'Hospitalet de Llobregat"


def test_num_a_la_espanola():
    assert web.num(1340) == "1.340"
    assert web.num(448385) == "448.385"
    assert web.num(11.03, 1) == "11,0"


def test_canarias_va_en_su_recuadro_sin_pisar_la_peninsula(mapa):
    """Las islas se dibujan al suroeste: a la izquierda de Cádiz y por debajo de Huelva."""
    palmas = mapa.xy(-15.45, 28.09, "35")
    cadiz = mapa.xy(-6.29, 36.53, "11")
    huelva = mapa.xy(-6.95, 37.26, "21")
    assert palmas[0] < cadiz[0] and palmas[1] > huelva[1]
    for x, y in (palmas, mapa.xy(-18.0, 27.7, "38"), mapa.xy(3.2, 39.9, "07"), mapa.xy(-2.94, 35.29, "52")):
        assert 0 <= x <= mapa.ancho and 0 <= y <= mapa.alto


def test_cada_senalado_esta_en_el_mapa(mapa):
    d = web.datos_pueblos(SALIDAS, REFERENCIA, mapa)
    sen = pd.read_csv(SALIDAS / "pueblos_senalados.csv", dtype={"cod": str})
    mar = pd.read_csv(SALIDAS / "pueblos_margen.csv", dtype={"cod": str})
    assert {e["id"]: e["n"] for e in d["elecciones"]} == sen.groupby("eleccion").size().to_dict()
    assert sum(e["alcanzan"] for e in d["elecciones"]) == int(mar.pudo_decidir.sum())
    for p in d["pueblos"]:
        assert 0 <= p["x"] <= mapa.ancho and 0 <= p["y"] <= mapa.alto, p["n"]
    # Padrones de Bureba 2023: de los 18 de más solo 3 seguían en la mesa, y la diferencia fue 1
    padrones = next(p for p in d["pueblos"] if p["cod"] == "09244" and p["e"] == "m2023")
    assert (padrones["exceso"], padrones["res"]["mesa"], padrones["res"]["margen"]) == (18, 3, 1)
    assert padrones["res"]["alcanza"] and padrones["oce"] == "municipio"


def test_lo_publicado_apunta_a_un_senalado(mapa):
    """Una fuente de referencia/casos_publicos.csv sin pueblo señalado no saldría en ninguna ficha."""
    d = web.datos_pueblos(SALIDAS, REFERENCIA, mapa)
    casos = pd.read_csv(REFERENCIA / "casos_publicos.csv", dtype=str)
    con_fuente = {(p["cod"], p["e"]) for p in d["pueblos"] if "casos" in p}
    assert con_fuente == set(zip(casos.cod, casos.eleccion))
    assert casos.url.str.startswith("https://").all()


def test_construye_la_pagina_entera(tmp_path):
    pagina = web.construye(tmp_path).read_text()
    assert "{{" not in pagina
    datos = json.loads(re.search(r'<script id="datos" type="application/json">(.*?)</script>', pagina, re.S).group(1))
    assert len(datos["pueblos"]) == len(pd.read_csv(SALIDAS / "pueblos_senalados.csv"))
    assert not re.search(r"\bnan\b", pagina, re.I)
    assert (tmp_path / "app.js").exists() and (tmp_path / "style.css").exists()
    assert "29 de noviembre" in pagina  # sin provisionales, el aviso de la noche


def test_la_noche_ensena_los_escanos_pendientes(tmp_path):
    """Con salidas/noche_pendientes_cera.csv la página cambia el aviso por la tabla."""
    salidas = tmp_path / "salidas"
    salidas.mkdir()
    for f in SALIDAS.glob("*.csv"):
        (salidas / f.name).write_bytes(f.read_bytes())
    pd.DataFrame({"prov": ["28", "08"], "provincia": ["Madrid", "Barcelona"], "escrutado": [99.1, 98.0],
                  "escanos": [37, 32], "aspirante": ["PP", "ERC"], "votos_que_faltan": [1200, 90000],
                  "votantes_cera": [60000, 30000], "ventaja_neta": [0.02, 3.0],
                  "votantes_cera_sin_suspendidos": [50000, 25000],
                  "ventaja_neta_sin_suspendidos": [0.024, 3.6]}).to_csv(salidas / "noche_pendientes_cera.csv", index=False)
    h = web.html_noche(salidas)
    assert "Madrid" in h and "2,0 %" in h and "2,4 %" in h and "99,1 %" in h
    assert "Barcelona" not in h  # fuera de alcance: no sale
