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
