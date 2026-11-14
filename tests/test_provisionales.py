from pathlib import Path

import pytest

from censo.cera import dhondt, pendientes
from censo.provisionales import lee

FIX = Path(__file__).parent / "fixtures" / "provisionales"


def test_solo_provincias_con_escrutinio_y_el_envio_mas_reciente():
    # provincias.json: Girona en dos envíos (40 % y 97,5 % escrutado) y Ceuta sin escrutinio
    d = lee(FIX / "provincias.json")
    assert set(d.prov) == {"17"}
    assert (d.escrutado == 97.5).all() and len(d) == 5
    assert d.validos.iloc[0] == 340_000 and d.votos.sum() == 334_000


def test_carpeta_ignora_comunidades_y_municipios():
    # comunidad (nivel 20) y municipio (nivel 90) reales de 2023 traen el mismo esquema
    d = lee(FIX)
    assert set(d.prov) == {"17"}


def test_sin_provincias_avisa():
    with pytest.raises(ValueError):
        lee(FIX / "municipio_villarroya_2023.json")


def test_lo_leido_sirve_a_la_noche():
    # el reparto provisional de Interior es el que sale del D'Hondt con los votos leídos
    d = lee(FIX / "provincias.json")
    votos = dict(zip(d.candidatura, d.votos))
    assert dhondt(votos, int(d.diputados.sum()), validos=340_000) == dict(zip(d.candidatura, d.diputados))
    validos = d.groupby("prov").validos.first()
    p = pendientes(d, validos, validos * 0 + 5_000)
    assert p.iloc[0].prov == "17" and p.iloc[0].votos_que_faltan > 0
