from censo.cera import dhondt


def test_dhondt_ejemplo_de_libro():
    # 7 escaños: A 340k, B 280k, C 160k, D 60k  ->  A3 B3 C1 D0
    assert dhondt({"A": 340_000, "B": 280_000, "C": 160_000, "D": 60_000}, 7) == {"A": 3, "B": 3, "C": 1, "D": 0}


def test_dhondt_umbral_del_3_por_ciento_sobre_validos():
    r = dhondt({"A": 600, "B": 370, "C": 29}, 10, validos=1000)  # C no llega al 3 %
    assert r["C"] == 0 and sum(r.values()) == 10


def test_dhondt_empate_de_cociente_lo_gana_quien_tiene_mas_votos():
    # A/2 = 50 = B/1, el último escaño va a A por tener más votos en total
    assert dhondt({"A": 100, "B": 50}, 2) == {"A": 2, "B": 0}


def test_votos_para_un_escano_basta_y_es_justo():
    from censo.cera import votos_para_un_escano
    v = {"A": 340_000, "B": 280_000, "C": 160_000, "D": 60_000}
    falta = votos_para_un_escano(v, 7)
    for p, n in falta.items():
        mas = dict(v, **{p: v[p] + n})
        assert dhondt(mas, 7)[p] == dhondt(v, 7)[p] + 1          # con n, lo gana
        menos = dict(v, **{p: v[p] + n - 2})
        assert dhondt(menos, 7)[p] == dhondt(v, 7)[p]            # con casi n, todavía no


def test_reparte_suspendidos_en_proporcion_a_lo_ganado():
    import pandas as pd
    from censo.cera import reparte_suspendidos
    nuevos = pd.Series({"28": 30_000, "08": 10_000, "49": -500})
    r = reparte_suspendidos(nuevos, 20_000)
    assert r["28"] == 15_000 and r["08"] == 5_000 and r["49"] == 0  # quien pierde CERA no recibe
    tope = reparte_suspendidos(nuevos, 1_000_000)
    assert (tope <= nuevos.clip(lower=0)).all()  # nadie pierde más de lo que ganó


def test_pendientes_ventaja_neta_y_orden():
    import pandas as pd
    from censo.cera import pendientes
    # 01: B está a 1 voto del último escaño de A (cocientes 100/2=50 frente a 49/1)
    # 02: lejos de cualquier vuelco
    v = pd.DataFrame({"prov": ["01", "01", "02", "02"], "candidatura": ["A", "B", "A", "B"],
                      "votos": [100, 49, 900, 100], "diputados": [2, 0, 2, 0]})
    d = pendientes(v, pd.Series({"01": 149, "02": 1000}), pd.Series({"01": 20, "02": 20}))
    assert list(d.prov) == ["01", "02"]  # lo más en juego primero
    assert d.iloc[0].aspirante == "B" and d.iloc[0].votos_que_faltan == 2
    assert d.iloc[0].ventaja_neta == 0.1 and d.iloc[1].ventaja_neta > 1  # en 02 no le da ni todo el exterior


def test_votos_sin_cera_es_la_suma_de_municipios():
    import pandas as pd
    from censo.cera import votos_sin_cera
    prov = pd.DataFrame({"prov": ["28", "28"], "candidatura": ["A", "B"], "votos": [110, 60], "diputados": [1, 1]})
    mun = pd.DataFrame({"cod": ["28001", "28002", "28001"], "candidatura": ["A", "A", "B"], "votos": [50, 50, 55]})
    d = votos_sin_cera(prov, mun).set_index("candidatura")
    assert d.votos.to_dict() == {"A": 100, "B": 55} and d.diputados.sum() == 2
