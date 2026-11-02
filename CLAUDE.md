# censoHinchado

Anomalías del censo electoral por municipio con datos públicos (INE + Infoelectoral):
1. **Pueblos**: el censo de residentes (CER) sube para las municipales y cae después.
   Dos señales: **caída** (frente a las generales siguientes, ≥ 6 y ≥ 8 %) y **pico**
   (subida frente a las generales anteriores que se deshace antes de la siguiente
   municipal, ≥ 6 y ≥ 8 %). El pico ve a quien se queda empadronado un tiempo (Gatón de
   Campos 2015) y es más preciso: en 2019 señala 8 pueblos frente a 34. Se cruza con la diferencia de votos entre 1ª y 2ª lista.
2. **CERA**: el voto exterior y la ola de la ley de nietos (padrón exterior, PERE), y
   si cambia o puede cambiar escaños del Congreso.

Se habla siempre de **anomalías estadísticas**, nunca de fraude.

## Uso

```
uv run censo descarga   # INE automático; lista lo que falta de Infoelectoral
uv run censo pueblos    # salidas/pueblos_senalados.csv, pueblos_margen.csv
uv run censo cera       # salidas/cera_escanos.csv, cera_ola_municipios.csv, cera_margen_2023_vs_g2026.csv
uv run censo ensayo     # la noche electoral hacia atrás, 2011-2023: salidas/noche_ensayo.csv
uv run censo noche r.csv  # 29-N: salidas/noche_pendientes_cera.csv
uv run pytest -q
```

## Noche del 29-N

El voto CERA no entra en el recuento de la noche: se cuenta en el escrutinio general,
cinco días después. `censo noche` toma los provisionales en un CSV con columnas
`prov, candidatura, votos, diputados, validos` (una fila por provincia y candidatura;
`validos` repetido) y dice qué último escaño puede dar la vuelta el exterior.
`ventaja_neta` = votos que le faltan al aspirante / votantes exteriores esperados
(CERA del 29-N × participación exterior de 2023, con y sin suspendidos). En el ensayo,
los dos vuelcos reales (Bizkaia nov-2019, Madrid 2023) quedaron por debajo del 5 % y
fueron la primera de su elección; con el umbral del 10 % salen 5 provincias en 6
elecciones y cambian 2. Señala lo que está en juego, no hacia dónde cae.
El formato de los provisionales de Interior no se conoce hasta esa noche: hay que
pasarlos a ese CSV.

## Datos (en `datos/`, ignorado por git)

- `datos/brutos/ine/`: electores por municipio de cada elección (PX históricos y CSV
  `jaxi/files/tpx/es/csv_bdsc/<id>.csv`) y el PERE (Tempus, tabla 71118). Se bajan solos.
- `datos/brutos/ine/oce_g2026_listas_provincias.xlsx`: electores CER y CERA por provincia
  de las listas de votación del 29-N (Oficina del Censo Electoral, censo cerrado el
  1-8-2026; página `ine.es/dyngs/CEL/index.htm?cid=1703`). Se baja solo. Los "números
  definitivos" (`elecgen2026_tab*_def.xlsx`) aún daban 404 el 2026-11-02.
- `datos/brutos/infoelectoral/<código>/`: resultados de Interior. **Interior da 403 a
  curl**: se bajan desde el Chrome de Alejandro con `fetch` dentro de la página de
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
- `test_casos_conocidos_con_datos_reales` exige ver los 7 casos con respaldo público
  (Gatón de Campos, Monterde, Huérmeces, La Acebeda, Carcedo, Padrones, Los Ausines).
  Manchones 2015 (condenado) no lo ve ninguna señal: sus altas venían de antes y se
  fueron despacio. La caída a más plazo sola lo vería, pero señala 1.905 pueblos en 2015.
- Falsos positivos: Talarn (academia militar de suboficiales).
- CERA nuevo del 29-N = CERA de las listas de la OCE − `Censo CERA` de Infoelectoral 2023.
  Los 163.020 con voto suspendido por el Supremo siguen en las listas y no hay cifra
  por provincia: se reparten en proporción al CERA ganado (`reparte_suspendidos`) y
  sale como escenario aparte, no como dato.
- El voto CERA por partido = provincial − suma de municipios. `efecto_cera` comprueba
  que el D'Hondt reproduce el reparto oficial y falla si no.

## QA

Nivel: activo. Tests de la lógica (detector, margen, D'Hondt, lectores) en `tests/`.

Issues: abp002/censoHinchado
