import pandas as pd

from censo import pueblos


def panel(filas):
    return pd.DataFrame(filas, columns=["eleccion", "cod", "CER", "CERE"])


def test_cada_municipal_va_con_las_generales_siguientes():
    p = dict(pueblos.pares())
    assert p["m2019"] == "g2019n"   # no las de abril, que son anteriores
    assert p["m2023"] == "g2023"


def test_senala_subida_que_cae_y_no_el_ruido():
    d = pueblos.senala(panel([
        ("m2023", "09244", 63, 0), ("g2023", "09244", 48, 0),   # Padrones de Bureba: cae 15
        ("m2023", "00002", 500, 0), ("g2023", "00002", 495, 0),  # cae 5: ruido
        ("m2023", "00003", 60, 0), ("g2023", "00003", 54, 0),    # cae 6 pero es el 10 %
        ("m2023", "00004", 300, 0), ("g2023", "00004", 290, 0),  # cae 10 pero solo el 3 %
        ("m2023", "00005", 25, 0), ("g2023", "00005", 10, 0),    # demasiado pequeño
    ]))
    s = set(d[d.senalado].cod)
    assert s == {"09244", "00003"}
    assert "00005" not in set(d.cod)


def test_margen_con_una_sola_lista_es_su_total():
    v = pd.DataFrame({"cod": ["1", "2", "2"], "candidatura": ["A", "A", "B"], "votos": [30, 25, 24],
                      "nombre": ["x", "y", "y"], "poblacion": 0, "censo_mesa": 0, "votantes": 0})
    m = pueblos.margenes(v)
    assert m.loc["1", "margen"] == 30
    assert m.loc["2", "margen"] == 1 and m.loc["2", "gana"] == "A"


def test_el_exceso_excluido_de_la_mesa_no_decide():
    s = pd.DataFrame({"cod": ["carcedo", "padrones"], "cer_municipal": [53, 63], "cer_base": [38, 48],
                      "cere_municipal": [0, 0], "exceso": [15, 15]})
    m = pd.DataFrame({"censo_mesa": [39, 51], "margen": [16, 1]}, index=["carcedo", "padrones"])
    d = pueblos.decide(s, m).set_index("cod")
    assert d.loc["carcedo", "exceso_en_mesa"] == 1 and not d.loc["carcedo", "pudo_decidir"]
    assert d.loc["padrones", "exceso_en_mesa"] == 3 and d.loc["padrones", "pudo_decidir"]


def test_ventanas_saltan_las_generales_con_el_mismo_cierre_de_censo():
    v = {m: (antes, despues) for m, antes, despues in pueblos.ventanas()}
    assert v["m2019"] == ("g2015b", ["g2019n"])           # abril de 2019 queda fuera por los dos lados
    assert v["m2015"] == ("g2011", ["g2015b", "g2019a"])  # la caída puede llegar hasta la siguiente municipal


def test_pico_encuentra_a_quien_se_queda_y_no_al_pueblo_que_se_vacia():
    filas = []
    for cod, serie in {
        "47070": (33, 43, 41, 30),    # Gatón de Campos: sube 10 y no se va hasta 2019
        "00002": (130, 120, 115, 100),  # se vacía poco a poco: nunca sube
        "00003": (100, 104, 103, 90),   # sube 4: ruido
    }.items():
        for e, v in zip(["g2011", "m2015", "g2015b", "g2019a"], serie):
            filas.append((e, cod, v, 0))
    d = pueblos.senala(panel(filas)).set_index("cod")
    assert d.loc["47070", "senal_pico"] and not d.loc["47070", "senal_caida"]
    assert d.loc["47070", "exceso"] == 10 and d.loc["47070", "cer_base"] == 33
    assert not d.loc["00002", "senalado"] and not d.loc["00003", "senalado"]


# Casos con respaldo público (OCE, Junta Electoral, juzgado o condena) que el detector debe ver.
CONOCIDOS = {("m2015", "47070"): "Gatón de Campos", ("m2015", "50173"): "Monterde",
             ("m2019", "09172"): "Huérmeces", ("m2019", "28001"): "La Acebeda",
             ("m2023", "09071"): "Carcedo de Bureba", ("m2023", "09244"): "Padrones de Bureba",
             ("m2023", "09030"): "Los Ausines"}
# Manchones 2015 (condenado): 124 -> 127 -> 117. Sus empadronados venían de antes y
# se fueron despacio; ninguna señal lo ve sin señalar cientos de pueblos que se vacían.
NO_LO_VE = {("m2015", "50161")}


def test_casos_conocidos_con_datos_reales():
    import pytest
    from censo import lectura
    from censo.fuentes import BRUTOS_INE
    if not BRUTOS_INE.exists():
        pytest.skip("sin datos/brutos (uv run censo descarga)")
    d = pueblos.senala(lectura.censo_panel()).set_index(["eleccion", "cod"])
    falta = {n for k, n in CONOCIDOS.items() if not d.loc[k, "senalado"]}
    assert not falta, f"el detector ya no ve: {falta}"
    assert not any(d.loc[k, "senalado"] for k in NO_LO_VE)
