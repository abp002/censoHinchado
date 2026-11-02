from pathlib import Path

import pandas as pd

from censo.lectura import codigo, lee_csv, lee_px, tipo_elector

FIX = Path(__file__).parent / "fixtures"


def test_tipo_elector():
    assert tipo_elector("Electores españoles residentes en España") == "CER"
    assert tipo_elector("Electores españoles residentes en el extranjero") == "CERA"
    assert tipo_elector("Electores extranjeros residentes en España: Elecciones Municipales") == "CERE"
    assert tipo_elector("Electores extranjeros residentes en España: Parlamento Europeo") is None
    assert tipo_elector("Total") is None


def test_codigo_con_y_sin_espacio():
    assert codigo("02 001 ABENGIBRE") == codigo("02001 Abengibre") == "02001"
    assert codigo("ALBACETE") is None


def test_px_del_ine():
    d = lee_px((FIX / "mini.px").read_text(encoding="latin1")).set_index(["cod", "tipo"]).electores
    assert d["01001", "CER"] == 1755 and d["01001", "CERA"] == 22
    assert pd.isna(d["01002", "CERA"])  # ".." es dato no disponible
    assert "Total" not in d.index.get_level_values(0)


def test_csv_del_ine_con_miles():
    d = lee_csv(FIX / "mini.csv").set_index(["cod", "tipo"]).electores
    assert d["02001", "CER"] == 703 and d["28079", "CER"] == 2_456_789
    assert len(d) == 3  # se descartan totales y provincias


def test_tabla_de_provincias_de_la_oce():
    from censo.lectura import lee_oce_provincias
    d = lee_oce_provincias(FIX / "oce_provincias.xlsx").set_index("prov")
    assert len(d) == 52 and "Total general" not in d.nombre.values  # 50 provincias + Ceuta y Melilla
    assert d.loc["02", "cer"] == 299_550 and d.loc["02", "cera"] == 8_995
    assert d.loc["52", "cera"] == 6_882
    assert d.cera.sum() == 2_776_645  # el total que trae la propia tabla


def test_tabla_de_municipios_de_la_oce_con_datos_reales():
    import pytest
    from censo.fuentes import BRUTOS_INE, POR_ID
    from censo.lectura import lee_oce_municipios
    ruta = BRUTOS_INE / POR_ID["g2026"].fichero
    if not ruta.exists():
        pytest.skip("sin datos/brutos (uv run censo descarga)")
    d = lee_oce_municipios(ruta).set_index(["cod", "tipo"]).electores
    assert d["28079", "CER"] == 2_424_110 and d["28079", "CERA"] == 429_670  # Madrid
    assert d["02001", "CER"] == 640 and d["52001", "CERA"] == 6_882          # Abengibre, Melilla
    assert d["48915", "CER"] == 315  # Ziortza-Bolibar llega sin código de provincia
    # sin filas de provincia ni de total: la suma cuadra con el total general de la tabla
    assert d.xs("CER", level="tipo").sum() == 35_953_542
    assert d.xs("CERA", level="tipo").sum() == 2_776_645
