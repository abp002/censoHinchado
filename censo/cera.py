"""Censo de españoles residentes en el extranjero (CERA) y su padrón (PERE).

Desde 2011 el CERA no vota en municipales, pero sí en generales, autonómicas y
europeas, y su voto se suma a la provincia del municipio de inscripción. La ley
de memoria democrática (en vigor desde el 21-10-2022) abrió la nacionalidad a
nietos de exiliados y emigrantes: el padrón exterior se dispara desde 2023.
"""
import pandas as pd


def ola(pere: pd.DataFrame, antes=(2018, 2022), despues=(2022, 2026)) -> pd.DataFrame:
    """Crecimiento anual medio del PERE por municipio antes y después de la ley."""
    p = pere.pivot_table(index=["cod", "nombre"], columns="anyo", values="pere")
    a0, a1 = antes
    d0, d1 = despues
    out = pd.DataFrame({
        "pere_" + str(d0): p[d0], "pere_" + str(d1): p[d1],
        "ritmo_antes": (p[a1] - p[a0]) / (a1 - a0),
        "ritmo_despues": (p[d1] - p[d0]) / (d1 - d0),
    })
    out["aceleracion"] = out.ritmo_despues - out.ritmo_antes
    return out.reset_index()


def dhondt(votos: dict[str, int], escanos: int, umbral: float = 0.03, validos: int | None = None) -> dict[str, int]:
    """Reparto D'Hondt del Congreso: umbral del 3 % sobre votos válidos (incluye blancos)."""
    validos = validos if validos is not None else sum(votos.values())
    elegibles = {p: v for p, v in votos.items() if v >= umbral * validos}
    cocientes = sorted(((v / d, v, p) for p, v in elegibles.items() for d in range(1, escanos + 1)),
                       reverse=True)
    reparto = {p: 0 for p in votos}
    for _, _, p in cocientes[:escanos]:
        reparto[p] += 1
    return reparto


def efecto_cera(provincias: pd.DataFrame, votos_prov: pd.DataFrame, votos_mun: pd.DataFrame) -> pd.DataFrame:
    """Escaños del Congreso por provincia con y sin el voto CERA.

    El voto CERA por partido es el provincial (que lo incluye) menos la suma de los
    municipios (que no). Devuelve una fila por provincia y partido con escaños cambiados,
    y comprueba de paso que el D'Hondt reproduce el reparto oficial.
    """
    sin_cera = votos_sin_cera(votos_prov, votos_mun).set_index(["prov", "candidatura"]).votos
    filas = []
    for prov, g in votos_prov.groupby("prov"):
        info = provincias.set_index("prov").loc[prov]
        con = dict(zip(g.candidatura, g.votos))
        sin = {p: int(sin_cera[prov, p]) for p in con}
        escanos = int(g.diputados.sum())
        oficial = dict(zip(g.candidatura, g.diputados))
        r_con = dhondt(con, escanos, validos=int(info.validos))
        ratio = sum(sin.values()) / max(sum(con.values()), 1)
        r_sin = dhondt(sin, escanos, validos=int(info.validos * ratio))
        if r_con != oficial:
            raise ValueError(f"El D'Hondt no reproduce el reparto oficial en {prov}: {r_con} vs {oficial}")
        for p in con:
            if r_con[p] != r_sin[p]:
                filas.append({"prov": prov, "provincia": info.nombre, "candidatura": p,
                              "escanos_con_cera": r_con[p], "escanos_sin_cera": r_sin[p],
                              "votos_cera": con[p] - sin[p], "votantes_cera": int(info.votantes_cera),
                              "censo_cera": int(info.censo_cera)})
    return pd.DataFrame(filas)


def votos_para_un_escano(votos: dict[str, int], escanos: int, validos: int | None = None) -> dict[str, int]:
    """Votos que le faltan a cada partido para arrancar un escaño más (los demás quietos).

    Aproximación: compara con el cociente del último escaño repartido e ignora que
    sumar votos mueve también el umbral del 3 %.
    """
    r = dhondt(votos, escanos, validos=validos)
    out = {}
    for p, v in votos.items():
        # el escaño nuevo desplaza al último cociente ganador de otro partido
        ganadores = [votos[q] / r[q] for q in r if r[q] > 0 and q != p]
        if ganadores:  # si p tiene todos los escaños, no hay a quién quitárselo
            out[p] = int(min(ganadores) * (r[p] + 1) - v) + 1
    return out


def reparte_suspendidos(nuevos_cera: pd.Series, total: int) -> pd.Series:
    """Escenario: los inscritos con el voto suspendido se reparten en proporción al CERA
    ganado por cada provincia (son altas recientes de la ley de nietos). Las provincias
    que pierden CERA no reciben ninguno, y nadie pierde más de lo que ganó.
    """
    ganado = nuevos_cera.clip(lower=0)
    return (ganado * min(total / ganado.sum(), 1)).round().astype(int) if ganado.sum() else ganado * 0


def margen_ultimo_escano(provincias: pd.DataFrame, votos_prov: pd.DataFrame, nuevos_cera: pd.Series,
                         suspendidos: pd.Series | None = None) -> pd.DataFrame:
    """Por provincia: votos que le faltaron al partido más cercano para un escaño más,
    frente a los votantes exteriores nuevos que cabe esperar con la participación CERA
    de esa elección. Es un orden de magnitud, no una predicción: el voto del año
    siguiente será otro. Con `suspendidos`, añade el mismo cálculo descontándolos.
    """
    pr = provincias.set_index("prov")
    filas = []
    for prov, g in votos_prov.groupby("prov"):
        falta = votos_para_un_escano(dict(zip(g.candidatura, g.votos)), int(g.diputados.sum()),
                                     validos=int(pr.loc[prov, "validos"]))
        partido, n = min(falta.items(), key=lambda x: x[1])
        part = pr.loc[prov, "votantes_cera"] / pr.loc[prov, "censo_cera"]
        nuevos = int(nuevos_cera.get(prov, 0))
        filas.append({"prov": prov, "provincia": pr.loc[prov, "nombre"], "escanos": int(g.diputados.sum()),
                      "partido_mas_cerca": partido, "votos_que_faltan": n,
                      "censo_cera": int(pr.loc[prov, "censo_cera"]), "participacion_cera": round(part, 3),
                      "cera_nuevos": nuevos, "votantes_nuevos_esperados": round(nuevos * part)})
        if suspendidos is not None:
            sus = int(suspendidos.get(prov, 0))
            filas[-1] |= {"suspendidos_estimados": sus, "votantes_nuevos_sin_suspendidos": round((nuevos - sus) * part)}
    d = pd.DataFrame(filas)
    d["veces_el_margen"] = (d.votantes_nuevos_esperados / d.votos_que_faltan).round(2)
    if suspendidos is not None:
        d["veces_sin_suspendidos"] = (d.votantes_nuevos_sin_suspendidos / d.votos_que_faltan).round(2)
    return d.sort_values("veces_el_margen", ascending=False)


def votos_sin_cera(votos_prov: pd.DataFrame, votos_mun: pd.DataFrame) -> pd.DataFrame:
    """Votos por provincia como se verían la noche electoral: la suma de los municipios
    (el voto CERA solo está en el total provincial). Mantiene los diputados de la provincia."""
    mun = votos_mun.assign(prov=votos_mun.cod.str[:2]).groupby(["prov", "candidatura"]).votos.sum()
    out = votos_prov[["prov", "candidatura", "diputados"]].copy()
    out["votos"] = [int(mun.get(k, 0)) for k in zip(out.prov, out.candidatura)]
    return out


def pendientes(votos: pd.DataFrame, validos: pd.Series, votantes_cera: pd.Series) -> pd.DataFrame:
    """Qué último escaño puede dar la vuelta el voto exterior que aún no se ha contado.

    votos: prov, candidatura, votos, diputados sin el CERA (resultados de la noche).
    validos: votos válidos por provincia sin el CERA (para el umbral del 3 %).
    votantes_cera: votantes exteriores que se esperan por provincia.

    ventaja_neta es la parte del voto exterior que el aspirante tendría que sacarle de
    ventaja al que tiene el último escaño: votos que le faltan / votantes exteriores.
    Por encima de 1 es imposible; cuanto más baja, más en juego.
    """
    filas = []
    for prov, g in votos.groupby("prov"):
        falta = votos_para_un_escano(dict(zip(g.candidatura, g.votos)), int(g.diputados.sum()),
                                     validos=int(validos[prov]))
        partido, n = min(falta.items(), key=lambda x: x[1])
        c = int(votantes_cera.get(prov, 0))
        filas.append({"prov": prov, "escanos": int(g.diputados.sum()), "aspirante": partido,
                      "votos_que_faltan": n, "votantes_cera": c,
                      "ventaja_neta": round(n / c, 3) if c else float("inf")})
    return pd.DataFrame(filas).sort_values("ventaja_neta").reset_index(drop=True)
