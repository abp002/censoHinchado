"""Pueblos cuyo censo de residentes (CER) sube para las municipales y cae después.

Dos señales:
- caída: la municipal frente a las generales inmediatamente siguientes.
- pico: la subida frente a las generales anteriores (de al menos 6 meses antes, para no
  comparar con el mismo cierre de censo) que luego se deshace antes de la siguiente
  municipal. Encuentra a quien se queda empadronado un tiempo (Gatón de Campos 2015) y
  descarta los pueblos que solo se vacían.

Con el padrón anual del INE se exige además un **pico de padrón**: la población a 1 de
enero del año de la municipal sube frente al año anterior y baja en uno o dos años. Así
cae lo que dura más (la gente que llegó en la pandemia y se fue después) y lo que no es
una alta puntual (Talarn y su academia militar). En los años sin municipales ese pico
sale en 7-15 pueblos; en los de municipales, en 50-100.

Es una anomalía estadística, no una prueba de fraude: empadronarse donde uno tiene
casa o familia es legal, y hay falsos positivos conocidos (Talarn, por su academia militar).
"""
import pandas as pd

from .fuentes import ELECCIONES

# Umbrales: calibrados con los casos de 2019 y 2023 que la Oficina del Censo Electoral señaló
CAIDA_MIN = 6        # electores
CAIDA_REL_MIN = 0.08  # sobre el censo de la municipal
PICO_MIN, PICO_REL_MIN = 6, 0.08  # electores que suben y luego se van
PADRON_REL_MIN = 0.10  # pico de padrón sobre la población del año de la municipal
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


def pico_padron(padron: pd.DataFrame, anyo: int) -> pd.DataFrame:
    """Por municipio: población a 1 de enero de `anyo` y lo que sube frente al año anterior
    y se va en uno o dos años (el mínimo de las dos cosas)."""
    a = padron[anyo]
    despues = padron[[y for y in (anyo + 1, anyo + 2) if y in padron]].min(axis=1)
    pico = pd.concat([a - padron[anyo - 1], a - despues], axis=1).min(axis=1)
    return pd.DataFrame({"pob": a, "pico_padron": pico})


def senal_padron(p: pd.DataFrame) -> pd.Series:
    return (p.pico_padron >= PICO_MIN) & (p.pico_padron / p.pob >= PADRON_REL_MIN)


def picos_por_anyo(padron: pd.DataFrame, cer_min=CER_MIN, cer_max=CER_MAX) -> pd.Series:
    """Pueblos con pico de padrón cada año: los años sin municipales dan la tasa de fondo."""
    anyos = [y for y in padron.columns if y - 1 in padron and y + 1 in padron]
    out = {}
    for y in anyos:
        p = pico_padron(padron, y)
        out[y] = int((senal_padron(p) & padron[y - 1].between(cer_min, cer_max)).sum())
    return pd.Series(out)


def senala(panel: pd.DataFrame, padron: pd.DataFrame | None = None) -> pd.DataFrame:
    """panel largo (eleccion, cod, CER, CERE) -> una fila por municipio y municipal.

    Sin padrón: señalado si salta la caída o el pico del censo. Con padrón: señalado si hay
    pico de padrón y el censo sube y baja al menos PICO_MIN o cae CAIDA_MIN (sin umbral
    relativo: el padrón ya filtra el ruido).
    exceso: electores de más que se le suponen a la municipal; cer_base: el censo sin ellos.
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
        if padron is None:
            d["senalado"] = d.senal_caida | d.senal_pico
            d["exceso"] = pd.concat([d.caida.where(d.senal_caida, 0), d.pico.where(d.senal_pico, 0)], axis=1).max(axis=1)
        else:
            d = d.join(pico_padron(padron, int(m[1:])))
            d["senal_padron"] = senal_padron(d)
            d["senalado"] = d.senal_padron & ((d.caida >= CAIDA_MIN) | (d.pico >= PICO_MIN))
            d["exceso"] = pd.concat([d.caida, d.pico], axis=1).max(axis=1).clip(lower=0).where(d.senalado, 0)
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


# --- Alerta previa: antes de votar, con las listas de la municipal recién publicadas ---
ALERTA_MIN, ALERTA_REL_MIN = 6, 0.08


def anteriores(municipal: str) -> str | None:
    """Las generales más recientes a ≥ MESES_ANTES de la municipal."""
    m = next(e for e in ELECCIONES if e.id == municipal)
    previas = [g for g in sorted(ELECCIONES, key=lambda e: e.fecha)
               if not g.municipal and 0 < _mes(m.fecha) - _mes(g.fecha) and _mes(m.fecha) - _mes(g.fecha) >= MESES_ANTES]
    return previas[-1].id if previas else None


def alerta(cer_antes: pd.Series, cer_municipal: pd.Series, pob_antes: pd.Series, pob_ultimo: pd.Series) -> pd.DataFrame:
    """Pueblos cuyo censo de la municipal sube por encima de lo que explica su padrón.

    Solo usa lo que se sabe antes de votar: el censo de las generales anteriores, el de
    las listas de la municipal y el padrón publicado (hasta el 1 de enero del año
    anterior). Lo que crece el padrón se descuenta; lo que decrece no se suma, porque
    el censo de un pueblo que se vacía no baja al mismo ritmo.
    exceso: electores por encima de lo esperado.
    """
    d = pd.DataFrame({"cer_antes": cer_antes, "cer_municipal": cer_municipal}).dropna()
    d = d[d.cer_municipal.between(CER_MIN, CER_MAX)]
    crece = (pob_ultimo / pob_antes - 1).reindex(d.index).fillna(0).clip(lower=0)
    d["sube"] = d.cer_municipal - d.cer_antes
    d["crece_padron"] = crece.round(3)
    d["exceso"] = (d.cer_municipal - d.cer_antes * (1 + crece)).round(1)
    d["exceso_rel"] = (d.exceso / d.cer_municipal).round(3)
    d["alerta"] = (d.exceso >= ALERTA_MIN) & (d.exceso_rel >= ALERTA_REL_MIN)
    return d.sort_values("exceso_rel", ascending=False)
