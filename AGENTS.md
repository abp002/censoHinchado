# censoHinchado

Anomalías del censo electoral por municipio con datos públicos (INE + Infoelectoral):
1. **Pueblos**: el censo de residentes (CER) sube para las municipales y cae después.
   Señalado = **pico de padrón** (la población a 1 de enero del año de la municipal sube
   ≥ 6 y ≥ 10 % frente al año anterior y se va en uno o dos años) **y** el CER sube y baja
   ≥ 6 (`pico`) o cae ≥ 6 en las generales siguientes (`caida`). Sin padrón, `senala`
   usa solo las señales del CER (caída y pico con ≥ 8 %), que confunden la pandemia.
   Se cruza con la diferencia de votos entre 1ª y 2ª lista.
2. **CERA**: el voto exterior y la ola de la ley de nietos (padrón exterior, PERE), y
   si cambia o puede cambiar escaños del Congreso.

Se habla siempre de **anomalías estadísticas**, nunca de fraude.

## Uso

```
uv run censo descarga   # INE automático; lista lo que falta de Infoelectoral
uv run censo pueblos    # salidas/pueblos_senalados.csv, pueblos_margen.csv
uv run censo alerta m2027  # antes de votar: salidas/alerta_m2027.csv
uv run censo cera       # salidas/cera_escanos.csv, cera_ola_municipios.csv, cera_margen_2023_vs_g2026.csv
uv run censo ensayo     # la noche electoral hacia atrás, 2011-2023: salidas/noche_ensayo.csv
uv run censo noche provisionales.json  # 29-N: salidas/noche_pendientes_cera.csv
uv run censo web        # la página pública en _site/, a partir de salidas/
uv run pytest -q
```

## Alerta previa (municipales)

`censo pueblos` confirma el hinchado cuando el censo ya ha caído. `censo alerta <municipal>`
avisa antes de votar, con lo publicado entonces: el CER de las listas de la municipal
frente al de las generales anteriores de otro cierre (`anteriores`), menos lo que creció
el padrón hasta el 1 de enero del año anterior (lo que decrece no se suma). Alerta si
sobran ≥ 6 electores y ≥ 8 %. Ensayo: 2023 da 167 alertas con los tres casos de Burgos, y
un 13 % están en la lista de la OCE (2,8 % de base); 2015 y 2019, 54 y 79, con 4 de los 5
casos conocidos (Manchones no: su censo apenas subió). Los ensayos comparan con generales
de 3-4 años antes; para mayo de 2027 serán las del 29-N, a unos seis meses: hay que mirar
si los umbrales siguen valiendo. Para 2027: entrada `m2027` en `ELECCIONES` con la tabla de
listas por municipio de la OCE (sale hacia abril), y `uv run censo alerta m2027`.

## Noche del 29-N

El voto CERA no entra en el recuento de la noche: se cuenta en el escrutinio general,
cinco días después. `censo noche` toma los provisionales y dice qué último escaño puede dar la vuelta el exterior.
`ventaja_neta` = votos que le faltan al aspirante / votantes exteriores esperados
(CERA del 29-N × participación exterior de 2023, con y sin suspendidos). En el ensayo,
los dos vuelcos reales (Bizkaia nov-2019, Madrid 2023) quedaron por debajo del 5 % y
fueron la primera de su elección; con el umbral del 10 % salen 5 provincias en 6
elecciones y cambian 2. Señala lo que está en juego, no hacia dónde cae.

Los provisionales salen de la web de resultados (`resultados.29neleccionesgenerales.es`,
con contraseña hasta la noche). Su servidor (`backend-difu`) sirve JSON por ámbito; en
2023 era así y `censo/provisionales.py` lee ese formato. Paso a paso:
1. Abrir la web de resultados en el navegador y ejecutar dentro
   `herramientas/provisionales.js`: baja las 52 provincias a `~/Downloads/provisionales_HHMM.json`.
   Si da 404, mirar en la pestaña Red qué `getScopeData` pide al abrir una provincia y
   ajustar `SUFIJO`.
2. `uv run censo noche ~/Downloads/provisionales_HHMM.json` (acepta también una carpeta de
   JSON o el CSV a mano `prov, candidatura, votos, diputados, validos`). Avisa de las
   provincias sin escrutinio y saca el % escrutado: con poco escrutado no vale.
Ensayado con 2023 en ese formato: las 52 provincias dan lo mismo que `censo ensayo`.

## Web

<https://alejandroborrego.dev/censoHinchado/> (GitHub Pages; `.github/workflows/pages.yml` la monta y
publica en cada push a `main`). `censo/web.py` no calcula nada: lee `salidas/*.csv` y `referencia/`,
rellena la plantilla de `censo/sitio/` (`{{clave}}`) y deja los pueblos en un JSON que pinta `app.js`.
- Para que cambie la web hay que subir los CSV de `salidas/` regenerados: CI no tiene `datos/`.
- **La noche de unas generales**: `censo noche <provisionales>` escribe `salidas/noche_pendientes_cera.csv`;
  con ese fichero subido, la página cambia el aviso por la tabla de escaños pendientes del exterior.
- `referencia/casos_publicos.csv`: lo publicado sobre un pueblo (cod, municipal, frase, medio, URL), que
  sale en su ficha y rotula su punto. Cada frase dice solo lo que dice la fuente; un test exige que
  cada fila sea de un pueblo señalado.
- `referencia/municipios_coords.csv` y `provincias.json` salen de `herramientas/geografia.py` (es-atlas).
- Estilo: oscuro cálido, el mapa de portada a pantalla completa, Newsreader en titulares, Inter y
  JetBrains Mono; animaciones en CSS y `app.js` sin librerías (se apagan con `prefers-reduced-motion`).

## Datos (en `datos/`, ignorado por git)

- `datos/brutos/ine/`: electores por municipio de cada elección (PX históricos y CSV
  `jaxi/files/tpx/es/csv_bdsc/<id>.csv`) y el PERE (Tempus, tabla 71118). Se bajan solos.
- `datos/brutos/ine/oce_g2026_listas_provincias.xlsx`: electores CER y CERA por provincia
  de las listas de votación del 29-N (Oficina del Censo Electoral, censo cerrado el
  1-8-2026; página `ine.es/dyngs/CEL/index.htm?cid=1703`). Se baja solo. Los "números
  definitivos" (`elecgen2026_tab*_def.xlsx`) aún daban 404 el 2026-11-02.
- `g2026` en el panel: las listas del 29-N por municipio (OCE, `elecgral_2026_lv_tab4.xlsx`,
  CER y CERA, sin CERE). Ziortza-Bolibar llega sin código de provincia: se hereda.
- `datos/brutos/infoelectoral/<código>/`: resultados de Interior. **Interior da 403 a
  curl**: se bajan desde el navegador con `fetch` dentro de la página de
  Infoelectoral y se pasan a un receptor HTTP en 127.0.0.1. Ficheros:
  `docxl/{02,04}_AAAAMM_1.zip` (por municipio) y `docxl/PROV_02_AAAAMM_1.zip`
  (Congreso por provincia, con el voto CERA dentro).

## Elección nueva

Una entrada en `ELECCIONES` (`censo/fuentes.py`) con la tabla del INE; si es municipal,
su código de Infoelectoral. Las generales con voto exterior van en `GENERALES_INFOE`
(`censo/cli.py`). `pares()` empareja cada municipal con las generales siguientes solo.

## Trampas conocidas

- Usar solo el **CER**: el total mezcla CERE (británicos en Alicante antes del Brexit) y CERA.
- El censo total de Infoelectoral de las municipales de 2019 trae errores (La Vid y
  Barrios 531 frente a 243 de CER). El censo de la mesa sirve solo para ver si el
  exceso seguía el día de votar.
- `g2015b` es la PX `p09/a2015_1`; no está claro si es dic-2015 o jun-2016.
- m2007 → g2008 son 10 meses: mucho más ruido (120 señalados).
- Las generales a menos de 6 meses de una municipal (abril de 2019) comparten cierre de
  censo con ella: no valen como "antes" (`MESES_ANTES`).
- `test_casos_conocidos_con_datos_reales` exige ver los 8 casos con respaldo público
  (Gatón de Campos, Monterde, Manchones, Huérmeces, La Acebeda, Carcedo, Padrones, Los
  Ausines) y no ver Talarn. La caída a más plazo sola está descartada: 1.905 pueblos en 2015.
- **Por qué el padrón**: el CER solo existe en años de elecciones, y entre nov-2019 y
  mayo-2023 suben ≥ 8 % 619 pueblos (la pandemia; 137 en 2015, 156 en 2019). El padrón es
  anual: un salto de un año que se deshace no es la pandemia. Tasa de fondo: en los años
  sin municipales hay pico de padrón en 5-31 pueblos; en los de municipales, 52-102
  (`picos_por_anyo`, lo imprime `censo pueblos` y lo comprueba un test).
- `referencia/oce_m2023_altas_no_justificadas.csv`: la lista de la OCE del 4-4-2023
  (`ine.es/oficina_censo/elecmun2023/elec_mun_2023_municipios_impugnables.xlsx`), 137
  municipios y 99 entidades menores, con código INE puesto a mano. Es una criba amplia
  (altas pequeñas en pueblos grandes también): el detector solo ve el 7 % de sus
  municipios, pero un señalado está en ella el 25 % de las veces frente al 2,8 % de un
  pueblo cualquiera. Un test exige que sea al menos 5 veces más. No hay lista así de 2019.
- Padrón: `padron_29005.json` (Tempus, tabla 29005, cifras oficiales a 1 de enero desde 2006).
- Talarn (academia militar de suboficiales) mueve el CER sin pico de padrón: ya no sale.
- CERA nuevo del 29-N = CERA de las listas de la OCE − `Censo CERA` de Infoelectoral 2023.
  Los 163.020 con voto suspendido por el Supremo siguen en las listas y no hay cifra
  por provincia: se reparten en proporción al CERA ganado (`reparte_suspendidos`) y
  sale como escenario aparte, no como dato.
- El voto CERA por partido = provincial − suma de municipios. `efecto_cera` comprueba
  que el D'Hondt reproduce el reparto oficial y falla si no.

## QA

Nivel: activo. Tests de la lógica (detector, margen, D'Hondt, lectores) en `tests/`.

Issues: abp002/censoHinchado
