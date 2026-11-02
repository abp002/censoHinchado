"""Pueblos cuyo censo de residentes (CER) sube para las municipales y cae después.

Dos señales:
- caída: la municipal frente a las generales inmediatamente siguientes.
- pico: la subida frente a las generales anteriores (de al menos 6 meses antes, para no
  comparar con el mismo cierre de censo) que luego se deshace antes de la siguiente
  municipal. Encuentra a quien se queda empadronado un tiempo (Gatón de Campos 2015) y
  descarta los pueblos que solo se vacían.

Es una anomalía estadística, no una prueba de fraude: empadronarse donde uno tiene
casa o familia es legal, y hay falsos positivos conocidos (Talarn, por su academia militar).
"""
import pandas as pd

from .fuentes import ELECCIONES

# Umbrales: calibrados con los casos de 2019 y 2023 que la Oficina del Censo Electoral señaló
CAIDA_MIN = 6        # electores
CAIDA_REL_MIN = 0.08  # sobre el censo de la municipal
PICO_MIN, PICO_REL_MIN = 6, 0.08  # electores que suben y luego se van
MESES_ANTES = 6  # unas generales a menos de 6 meses comparten cierre de censo con la municipal
CER_MIN, CER_MAX = 20, 2000  # la OCE solo vigila < 2.000 habitantes; por debajo de 20, ruido


def pares() -> list[tuple[str, str]]:
    """Cada municipal con las generales inmediatamente posteriores del catálogo."""
    orden = sorted(ELECCIONES, key=lambda e: e.fecha)
    out = []
    for i, e in enumerate(orden):
        if e.municipal:
            sig = next((g for g in orden[i + 1:] if not g.municipal), None)
            if sig:
                out.append((e.id, sig.id))
    return out


def _mes(fecha: str) -> int:
    return int(fecha[:4]) * 12 + int(fecha[5:7])


def ventanas() -> list[tuple[str, str | None, list[str]]]:
    """Cada municipal con las generales anteriores (a ≥ MESES_ANTES) y las posteriores
    hasta la siguiente municipal."""
    orden = sorted(ELECCIONES, key=lambda e: e.fecha)
    out = []
    for i, e in enumerate(orden):
        if not e.municipal:
            continue
        antes = [g.id for g in orden[:i] if not g.municipal and _mes(e.fecha) - _mes(g.fecha) >= MESES_ANTES]
        j = next((k for k in range(i + 1, len(orden)) if orden[k].municipal), len(orden))
        despues = [g.id for g in orden[i + 1:j] if not g.municipal]
        if despues:
            out.append((e.id, antes[-1] if antes else None, despues))
    return out


def senala(panel: pd.DataFrame) -> pd.DataFrame:
    """panel largo (eleccion, cod, CER, CERE) -> una fila por municipio y municipal.

    exceso: electores de más que se le suponen a la municipal (el mayor de las señales que
    saltan); cer_base: el censo sin ese exceso.
    """
    cer = panel.pivot_table(index="cod", columns="eleccion", values="CER")
    cere = panel.pivot_table(index="cod", columns="eleccion", values="CERE")
    filas = []
    for m, antes, despues in ventanas():
        despues = [g for g in despues if g in cer]
        if m not in cer or not despues:
            continue
        g = despues[0]
        d = pd.DataFrame({"cer_antes": cer[antes] if antes in cer else float("nan"), "cer_municipal": cer[m],
                          "cer_despues": cer[g], "cer_min_despues": cer[despues].min(axis=1),
                          "cere_municipal": cere.get(m)}).dropna(subset=["cer_municipal", "cer_despues"])
        d = d[d.cer_despues.between(CER_MIN, CER_MAX)]
        d["caida"] = d.cer_municipal - d.cer_despues
        d["caida_rel"] = d.caida / d.cer_municipal
        d["senal_caida"] = (d.caida >= CAIDA_MIN) & (d.caida_rel >= CAIDA_REL_MIN)
        d["pico"] = pd.concat([d.cer_municipal - d.cer_antes, d.cer_municipal - d.cer_min_despues], axis=1).min(axis=1)
        d["senal_pico"] = (d.pico >= PICO_MIN) & (d.pico / d.cer_municipal >= PICO_REL_MIN)
        d["senalado"] = d.senal_caida | d.senal_pico
        d["exceso"] = pd.concat([d.caida.where(d.senal_caida, 0), d.pico.where(d.senal_pico, 0)], axis=1).max(axis=1)
        d["cer_base"] = d.cer_municipal - d.exceso
        filas.append(d.assign(eleccion=m, despues=g).reset_index())
    return pd.concat(filas, ignore_index=True)


def margenes(votos: pd.DataFrame) -> pd.DataFrame:
    """votos (cod, candidatura, votos, …) -> por municipio: 1ª y 2ª lista y su diferencia.

    Con una sola lista la diferencia es su total de votos.
    """
    def uno(g):
        g = g.sort_values("votos", ascending=False)
        a = g.iloc[0]
        b = g.iloc[1] if len(g) > 1 else None
        return pd.Series({"gana": a.candidatura, "v1": a.votos,
                          "segundo": b.candidatura if b is not None else None,
                          "v2": b.votos if b is not None else 0})
    m = votos.groupby("cod")[["candidatura", "votos"]].apply(uno)
    m["margen"] = m.v1 - m.v2
    fijo = votos.drop_duplicates("cod").set_index("cod")[["nombre", "poblacion", "censo_mesa", "votantes"]]
    return fijo.join(m)


def decide(senalados: pd.DataFrame, margen: pd.DataFrame) -> pd.DataFrame:
    """¿El exceso de censo pudo cambiar qué lista ganó?

    El exceso que cuenta es el que seguía en el censo de la mesa el día de votar:
    si la OCE lo excluyó antes (Carcedo de Bureba, 2023), no pudo votar.
    censo de la mesa = CER + CERE de la municipal.
    """
    d = senalados.set_index("cod").join(margen, how="inner")
    en_mesa = d.censo_mesa - d.cere_municipal.fillna(0) - d.cer_base
    d["exceso_en_mesa"] = en_mesa.clip(lower=0).combine(d.exceso, min)
    d["pudo_decidir"] = d.exceso_en_mesa >= d.margen
    return d.reset_index()
