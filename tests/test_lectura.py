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
