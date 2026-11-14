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


def test_pico_de_padron_es_un_salto_de_un_año():
    padron = pd.DataFrame({2014: [168, 100, 100], 2015: [278, 120, 120], 2016: [198, 125, 100],
                           2017: [168, 124, 99]}, index=["monterde", "llegan_y_se_quedan", "salto_puntual"])
    p = pueblos.pico_padron(padron, 2015)
    assert p.loc["monterde", "pico_padron"] == 110         # sube 110 y en dos años se han ido todos
    assert p.loc["llegan_y_se_quedan", "pico_padron"] < 0  # la pandemia: suben y no bajan
    assert list(pueblos.senal_padron(p)) == [True, False, True]


def test_con_padron_cae_el_censo_que_sube_sin_pico_de_padron():
    filas = []
    for cod, serie in {"talarn": (339, 473, 440, 390), "manchones": (124, 127, 117, 103)}.items():
        for e, v in zip(["g2011", "m2015", "g2015b", "g2019a"], serie):
            filas.append((e, cod, v, 0))
    padron = pd.DataFrame({2014: [480, 120], 2015: [470, 140], 2016: [475, 118], 2017: [470, 115]},
                          index=["talarn", "manchones"])
    d = pueblos.senala(panel(filas), padron).set_index("cod")
    assert d.loc["talarn", "senal_pico"] and not d.loc["talarn", "senalado"]   # el padrón no sube
    assert not d.loc["manchones", "senal_caida"] and d.loc["manchones", "senalado"]  # cae 10 (7,9 %)
    assert d.loc["manchones", "exceso"] == 10


# Casos con respaldo público (OCE, Junta Electoral, juzgado o condena) que el detector debe ver.
CONOCIDOS = {("m2015", "47070"): "Gatón de Campos", ("m2015", "50173"): "Monterde",
             ("m2015", "50161"): "Manchones",
             ("m2019", "09172"): "Huérmeces", ("m2019", "28001"): "La Acebeda",
             ("m2023", "09071"): "Carcedo de Bureba", ("m2023", "09244"): "Padrones de Bureba",
             ("m2023", "09030"): "Los Ausines"}
# Talarn: su academia militar de suboficiales mueve el censo sin pico de padrón.
NO_LO_VE = {("m2015", "25215"), ("m2019", "25215"), ("m2023", "25215")}


def test_casos_conocidos_con_datos_reales():
    import pytest
    from censo import lectura
    from censo.fuentes import BRUTOS_INE
    if not (BRUTOS_INE / "padron_29005.json").exists():
        pytest.skip("sin datos/brutos (uv run censo descarga)")
    padron = lectura.lee_padron_mun()
    d = pueblos.senala(lectura.censo_panel(), padron).set_index(["eleccion", "cod"])
    falta = {n for k, n in CONOCIDOS.items() if not d.loc[k, "senalado"]}
    assert not falta, f"el detector ya no ve: {falta}"
    assert not any(d.loc[k, "senalado"] for k in NO_LO_VE)
    # el pico de padrón es propio de los años de municipales: al menos el triple que el resto
    fondo = pueblos.picos_por_anyo(padron)
    municipales = fondo[fondo.index.isin([2011, 2015, 2019, 2023])]
    otros = fondo[~fondo.index.isin([2007, 2011, 2015, 2019, 2023])]
    assert municipales.min() >= 3 * otros.median()


def test_los_senalados_de_2023_abundan_en_la_lista_de_la_oce():
    """La OCE publicó el 4-4-2023 las entidades con altas no justificadas en los seis
    meses previos (referencia/oce_m2023_altas_no_justificadas.csv). Es una criba amplia
    (también altas pequeñas en pueblos grandes), no una lista de culpables, pero un
    señalado del detector debe estar en ella muchas más veces que un pueblo cualquiera."""
    import pytest
    from pathlib import Path
    from censo import lectura
    from censo.fuentes import BRUTOS_INE
    if not (BRUTOS_INE / "padron_29005.json").exists():
        pytest.skip("sin datos/brutos (uv run censo descarga)")
    lista = set(pd.read_csv(Path(__file__).parent.parent / "referencia" / "oce_m2023_altas_no_justificadas.csv",
                            dtype={"cod": str}).cod)
    d = pueblos.senala(lectura.censo_panel(), lectura.lee_padron_mun())
    d = d[d.eleccion == "m2023"]
    base = d.cod.isin(lista).mean()
    señalados = d[d.senalado].cod.isin(lista).mean()
    assert señalados >= 5 * base, (señalados, base)


def test_alerta_descuenta_lo_que_crece_el_padron_pero_no_lo_que_decrece():
    i = ["crece", "vacia", "salta"]
    d = pueblos.alerta(pd.Series([100, 100, 100], i), pd.Series([120, 100, 120], i),
                       pd.Series([200, 200, 200], i), pd.Series([240, 150, 200], i))
    assert d.loc["crece", "exceso"] == 0 and not d.loc["crece", "alerta"]  # +20 % de padrón lo explica
    assert d.loc["vacia", "exceso"] == 0 and not d.loc["vacia", "alerta"]  # no se le suma por vaciarse
    assert d.loc["salta", "exceso"] == 20 and d.loc["salta", "alerta"]


def test_alerta_compara_con_generales_de_otro_cierre_de_censo():
    assert pueblos.anteriores("m2019") == "g2015b"  # abril de 2019 comparte cierre con mayo
    assert pueblos.anteriores("m2023") == "g2019n"


def test_alerta_previa_con_datos_reales():
    """Antes de votar en 2023 ya se veían los tres casos de Burgos, y una alerta está en la
    lista de la OCE muchas más veces que un pueblo cualquiera. Manchones (2015) no se ve:
    su censo apenas subió, solo cayó después."""
    import pytest
    from pathlib import Path
    from censo import lectura
    from censo.fuentes import BRUTOS_INE, POR_ID
    if not (BRUTOS_INE / "padron_29005.json").exists():
        pytest.skip("sin datos/brutos (uv run censo descarga)")
    cer = lectura.censo_panel().pivot_table(index="cod", columns="eleccion", values="CER")
    padron = lectura.lee_padron_mun()
    vistos = set()
    for m in ("m2015", "m2019", "m2023"):
        a = pueblos.anteriores(m)
        d = pueblos.alerta(cer[a], cer[m], padron[int(POR_ID[a].fecha[:4])], padron[int(m[1:]) - 1])
        vistos |= {(m, c) for c in d[d.alerta].index}
    assert set(CONOCIDOS) - vistos == {("m2015", "50161")}
    lista = set(pd.read_csv(Path(__file__).parent.parent / "referencia" / "oce_m2023_altas_no_justificadas.csv",
                            dtype={"cod": str}).cod)
    alertas = [c for m, c in vistos if m == "m2023"]
    base = d.index.isin(list(lista)).mean()
    assert pd.Index(alertas).isin(list(lista)).mean() >= 4 * base
