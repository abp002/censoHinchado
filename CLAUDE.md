# censoHinchado

Anomalías del censo electoral por municipio con datos públicos (INE + Infoelectoral):
1. **Pueblos**: el censo de residentes (CER) sube para las municipales y cae en las
   generales siguientes. Se cruza con la diferencia de votos entre 1ª y 2ª lista.
2. **CERA**: el voto exterior y la ola de la ley de nietos (padrón exterior, PERE), y
   si cambia o puede cambiar escaños del Congreso.

Se habla siempre de **anomalías estadísticas**, nunca de fraude.

## Uso

```
uv run censo descarga   # INE automático; lista lo que falta de Infoelectoral
uv run censo pueblos    # salidas/pueblos_senalados.csv, pueblos_margen.csv
uv run censo cera       # salidas/cera_escanos.csv, cera_ola_municipios.csv, cera_margen_*.csv
uv run pytest -q
```

## Datos (en `datos/`, ignorado por git)

- `datos/brutos/ine/`: electores por municipio de cada elección (PX históricos y CSV
  `jaxi/files/tpx/es/csv_bdsc/<id>.csv`) y el PERE (Tempus, tabla 71118). Se bajan solos.
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
- Falsos positivos: Talarn (academia militar de suboficiales).
- El voto CERA por partido = provincial − suma de municipios. `efecto_cera` comprueba
  que el D'Hondt reproduce el reparto oficial y falla si no.

## QA

Nivel: activo. Tests de la lógica (detector, margen, D'Hondt, lectores) en `tests/`.

Issues: abp002/censoHinchado
