"""censo descarga | pueblos | cera | todo  — escribe los resultados en salidas/."""
import argparse
from pathlib import Path

import pandas as pd

from . import cera, fuentes, lectura, pueblos

SALIDAS = Path(__file__).resolve().parent.parent / "salidas"
GENERALES_INFOE = ["02_201111_1", "02_201512_1", "02_201606_1", "02_201904_1", "02_201911_1", "02_202307_1"]


def _nombres() -> pd.Series:
    p = lectura.lee_pere()
    return p.drop_duplicates("cod").set_index("cod").nombre


def cmd_descarga(_):
    fuentes.descarga_ine()
    faltan = fuentes.faltan_infoelectoral()
    if faltan:
        print("Infoelectoral bloquea las descargas automáticas. Bájalos desde el navegador y")
        print(f"descomprímelos en {fuentes.BRUTOS_INFOE}/<nombre>/:")
        print("\n".join("  " + u for u in faltan))


def cmd_pueblos(_):
    s = pueblos.senala(lectura.censo_panel())
    nombres = _nombres()
    sen = s[s.senalado].assign(nombre=lambda d: d.cod.map(nombres))
    veces = sen.groupby("cod").eleccion.transform("count")
    sen = sen.assign(veces=veces).sort_values(["eleccion", "caida_rel"], ascending=[True, False])
    sen.to_csv(SALIDAS / "pueblos_senalados.csv", index=False)
    print(sen.groupby("eleccion").size().to_string())
    decididos = []
    for e in fuentes.ELECCIONES:
        if e.municipal and e.infoelectoral and (fuentes.BRUTOS_INFOE / e.infoelectoral).exists():
            m = pueblos.margenes(lectura.lee_municipales(e))
            decididos.append(pueblos.decide(sen[sen.eleccion == e.id].drop(columns="nombre"), m))
    d = pd.concat(decididos)
    d.to_csv(SALIDAS / "pueblos_margen.csv", index=False)
    print("\n¿El exceso que siguió en la mesa supera la diferencia entre 1ª y 2ª lista?")
    print(d.groupby("eleccion").pudo_decidir.agg(["sum", "count"]).to_string())


def cmd_cera(_):
    ola = cera.ola(lectura.lee_pere())
    ola.to_csv(SALIDAS / "cera_ola_municipios.csv", index=False)
    filas = []
    for c in GENERALES_INFOE:
        if not (fuentes.BRUTOS_INFOE / ("PROV_" + c)).exists() or not (fuentes.BRUTOS_INFOE / c).exists():
            print("falta", c)
            continue
        pr, vp = lectura.lee_generales_provincias(c)
        filas.append(cera.efecto_cera(pr, vp, lectura.lee_generales_municipios(c)).assign(eleccion=c))
    e = pd.concat(filas)
    e.to_csv(SALIDAS / "cera_escanos.csv", index=False)
    print("Escaños que cambian al sumar el voto exterior:")
    print(e.to_string(index=False))
    # Ola de la ley de nietos: padrón exterior nuevo desde la última generales (2023 -> último año)
    pere = lectura.lee_pere()
    ult = pere.anyo.max()
    t = pere.assign(prov=pere.cod.str[:2]).pivot_table(index="prov", columns="anyo", values="pere", aggfunc="sum")
    pr, vp = lectura.lee_generales_provincias("02_202307_1")
    m = cera.margen_ultimo_escano(pr, vp, t[ult] - t[2023])
    m.to_csv(SALIDAS / f"cera_margen_2023_vs_pere_{ult}.csv", index=False)
    print(f"\nVotantes exteriores nuevos esperados (PERE 2023-{ult}) frente al margen del último escaño de 2023:")
    print(m.head(10).to_string(index=False))


def main():
    ap = argparse.ArgumentParser(prog="censo")
    ap.add_argument("orden", choices=["descarga", "pueblos", "cera", "todo"])
    a = ap.parse_args()
    SALIDAS.mkdir(exist_ok=True)
    ordenes = {"descarga": [cmd_descarga], "pueblos": [cmd_pueblos], "cera": [cmd_cera],
               "todo": [cmd_descarga, cmd_pueblos, cmd_cera]}
    for f in ordenes[a.orden]:
        f(a)


if __name__ == "__main__":
    main()
