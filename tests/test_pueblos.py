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
    s = pd.DataFrame({"cod": ["carcedo", "padrones"], "cer_municipal": [53, 63], "cer_despues": [38, 48],
                      "cere_municipal": [0, 0], "caida": [15, 15]})
    m = pd.DataFrame({"censo_mesa": [39, 51], "margen": [16, 1]}, index=["carcedo", "padrones"])
    d = pueblos.decide(s, m).set_index("cod")
    assert d.loc["carcedo", "exceso_en_mesa"] == 1 and not d.loc["carcedo", "pudo_decidir"]
    assert d.loc["padrones", "exceso_en_mesa"] == 3 and d.loc["padrones", "pudo_decidir"]
