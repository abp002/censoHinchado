"""Catálogo de elecciones y de dónde sale cada censo.

Para añadir una elección nueva: una entrada en ELECCIONES con la URL del INE
(tabla de electores CER/CERA/CERE por municipio) y, si es municipal, el fichero
de resultados de Infoelectoral, que hay que bajar a mano desde el navegador
(Interior da 403 a las descargas automáticas).
"""
from dataclasses import dataclass
from pathlib import Path
import urllib.request

DATOS = Path(__file__).resolve().parent.parent / "datos"
BRUTOS_INE = DATOS / "brutos" / "ine"
BRUTOS_INFOE = DATOS / "brutos" / "infoelectoral"

PX = "https://www.ine.es/jaxi/files/_px/es/px/t44/{}"
CSV = "https://www.ine.es/jaxi/files/tpx/es/csv_bdsc/{}.csv"
INFOE = "https://infoelectoral.interior.gob.es/estaticos/docxl/{}.zip"
PERE = "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/71118?nult=40&tip=AM"


@dataclass(frozen=True)
class Eleccion:
    id: str          # m2023, g2023…  (m = municipales, g = generales)
    fecha: str       # AAAA-MM
    fichero: str     # nombre local en datos/brutos/ine
    url: str
    infoelectoral: str | None = None  # código de Infoelectoral (04_202305_1…)

    @property
    def municipal(self) -> bool:
        return self.id.startswith("m")


ELECCIONES = [
    Eleccion("m2007", "2007-05", "p06_2007_0310.px", PX.format("p06/a2007/l0/0310.px")),
    Eleccion("g2008", "2008-03", "p09_2008.px", PX.format("p09/a2008/l0/0309.px")),
    Eleccion("m2011", "2011-05", "p06_2011.px", PX.format("p06/a2011/l0/0309.px"), "04_201105_1"),
    Eleccion("g2011", "2011-11", "p09_2011.px", PX.format("p09/a2011/l0/0309.px")),
    Eleccion("m2015", "2015-05", "p06_2015.px", PX.format("p06/a2015/l0/0309.px"), "04_201505_1"),
    # a2015_1: generales de diciembre de 2015 o de junio de 2016; el INE no lo deja claro
    Eleccion("g2015b", "2015-12", "p09_2015_1.px", PX.format("p09/a2015_1/l0/0309.px")),
    Eleccion("g2019a", "2019-04", "p09_2019.px", PX.format("p09/a2019/l0/0309.px")),
    Eleccion("m2019", "2019-05", "cer_32085.csv", CSV.format(32085), "04_201905_1"),
    Eleccion("g2019n", "2019-11", "cer_33524.csv", CSV.format(33524)),
    Eleccion("m2023", "2023-05", "cer_m2023.csv", CSV.format(59378), "04_202305_1"),
    Eleccion("g2023", "2023-07", "cer_59776.csv", CSV.format(59776)),
]
POR_ID = {e.id: e for e in ELECCIONES}


def descarga(url: str, destino: Path, forzar: bool = False) -> Path:
    if destino.exists() and not forzar:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "censo-hinchado"})
    with urllib.request.urlopen(req, timeout=120) as r:
        destino.write_bytes(r.read())
    return destino


def descarga_ine(forzar: bool = False) -> None:
    for e in ELECCIONES:
        descarga(e.url, BRUTOS_INE / e.fichero, forzar)
    descarga(PERE, BRUTOS_INE / "pere_71118.json", forzar)


def faltan_infoelectoral() -> list[str]:
    """URLs de Infoelectoral que hay que bajar a mano (y descomprimir en datos/brutos/infoelectoral)."""
    return [INFOE.format(e.infoelectoral) for e in ELECCIONES
            if e.infoelectoral and not (BRUTOS_INFOE / e.infoelectoral).exists()]
