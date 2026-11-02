"""censo descarga | pueblos | cera | ensayo | noche <csv> | todo  — escribe los resultados en salidas/."""
import argparse
from pathlib import Path

import pandas as pd

from . import cera, fuentes, lectura, pueblos

SALIDAS = Path(__file__).resolve().parent.parent / "salidas"
# Ventaja neta dentro del voto exterior por debajo de la cual un escaño está en juego.
# En el ensayo 2011-2023 los dos cambios reales quedaron por debajo del 5 %.
UMBRAL_EN_JUEGO = 0.10
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
    padron = lectura.lee_padron_mun()
    fondo = pueblos.picos_por_anyo(padron)
    print("Pueblos con pico de padrón por año (municipales en 2007, 2011, 2015, 2019, 2023):")
    print(" ".join(f"{y}:{n}" for y, n in fondo.items()))
    s = pueblos.senala(lectura.censo_panel(), padron)
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
    # Ola de la ley de nietos: CERA del 29-N (listas de votación de la OCE) menos el de 2023
    pr, vp = lectura.lee_generales_provincias("02_202307_1")
    oce = lectura.lee_oce_provincias().set_index("prov")
    nuevos = oce.cera - pr.set_index("prov").censo_cera
    m = cera.margen_ultimo_escano(pr, vp, nuevos, cera.reparte_suspendidos(nuevos, fuentes.SUSPENDIDOS_G2026))
    m.to_csv(SALIDAS / "cera_margen_2023_vs_g2026.csv", index=False)
    print(f"\nCERA del 29-N: {oce.cera.sum():,} ({nuevos.sum():+,} desde 2023). Votantes exteriores nuevos")
    print("esperados frente al margen del último escaño de 2023 (sin suspendidos: escenario proporcional):")
    print(m.head(10).to_string(index=False))

def cmd_ensayo(_):
    """La noche electoral hacia atrás: votos sin CERA de cada generales y su voto exterior real."""
    esc = pd.read_csv(SALIDAS / "cera_escanos.csv", dtype={"prov": str})
    filas = []
    for c in GENERALES_INFOE:
        pr, vp = lectura.lee_generales_provincias(c)
        sin = cera.votos_sin_cera(vp, lectura.lee_generales_municipios(c))
        p = pr.set_index("prov")
        ratio = sin.groupby("prov").votos.sum() / vp.groupby("prov").votos.sum()
        d = cera.pendientes(sin, (p.validos * ratio).round(), p.votantes_cera)
        filas.append(d.assign(eleccion=c, provincia=d.prov.map(p.nombre),
                              cambio_real=d.prov.isin(set(esc[esc.eleccion == c].prov))))
    d = pd.concat(filas)
    d.to_csv(SALIDAS / "noche_ensayo.csv", index=False)
    jugadas = d[d.ventaja_neta <= UMBRAL_EN_JUEGO]
    print(f"Ventaja neta <= {UMBRAL_EN_JUEGO:.0%}: {len(jugadas)} provincias señaladas, "
          f"{jugadas.cambio_real.sum()} cambiaron; cambios reales fuera del umbral: "
          f"{(d.cambio_real & (d.ventaja_neta > UMBRAL_EN_JUEGO)).sum()}")
    print(jugadas[["eleccion", "provincia", "aspirante", "votos_que_faltan", "votantes_cera",
                   "ventaja_neta", "cambio_real"]].to_string(index=False))


def cmd_noche(a):
    """Resultados provisionales del 29-N (CSV: prov, candidatura, votos, diputados, validos)."""
    if not a.fichero:
        raise SystemExit("uso: censo noche <resultados.csv>")
    r = pd.read_csv(a.fichero, dtype={"prov": str})
    r["prov"] = r.prov.str.zfill(2)
    validos = r.groupby("prov").validos.first()
    pr, _ = lectura.lee_generales_provincias("02_202307_1")
    part = pr.set_index("prov").pipe(lambda p: p.votantes_cera / p.censo_cera)
    oce = lectura.lee_oce_provincias().set_index("prov")
    sus = cera.reparte_suspendidos(oce.cera - pr.set_index("prov").censo_cera, fuentes.SUSPENDIDOS_G2026)
    con = cera.pendientes(r, validos, (oce.cera * part).round())
    sin = cera.pendientes(r, validos, ((oce.cera - sus) * part).round())
    d = con.merge(sin[["prov", "votantes_cera", "ventaja_neta"]], on="prov", suffixes=("", "_sin_suspendidos"))
    d.insert(1, "provincia", d.prov.map(oce.nombre))
    d.to_csv(SALIDAS / "noche_pendientes_cera.csv", index=False)
    print("Último escaño que puede dar la vuelta el voto exterior (escrutinio general, 5 días después):")
    print(d[d.ventaja_neta <= 2 * UMBRAL_EN_JUEGO].to_string(index=False))


def main():
    ap = argparse.ArgumentParser(prog="censo")
    ap.add_argument("orden", choices=["descarga", "pueblos", "cera", "ensayo", "noche", "todo"])
    ap.add_argument("fichero", nargs="?")
    a = ap.parse_args()
    SALIDAS.mkdir(exist_ok=True)
    ordenes = {"descarga": [cmd_descarga], "pueblos": [cmd_pueblos], "cera": [cmd_cera],
               "ensayo": [cmd_ensayo], "noche": [cmd_noche],
               "todo": [cmd_descarga, cmd_pueblos, cmd_cera, cmd_ensayo]}
    for f in ordenes[a.orden]:
        f(a)


if __name__ == "__main__":
    main()
