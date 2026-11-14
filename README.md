# censoHinchado

Dos anomalías del censo electoral español, medidas con datos públicos del INE y del
Ministerio del Interior:

- **Pueblos** que ganan electores justo para las municipales y los pierden en las
  generales siguientes, y si ese exceso supera la diferencia de votos con la que se ganó.
- **Voto exterior (CERA)**: qué escaños del Congreso ha cambiado y cuántos votantes
  nuevos trae la ley de nietos frente al margen del último escaño de cada provincia.

Son anomalías estadísticas, no pruebas de fraude.

```
uv run censo todo
```

Lo que sale queda en `salidas/`: `pueblos_senalados.csv` y `pueblos_margen.csv` (pueblos
y si el exceso alcanzaba la diferencia de votos), `cera_*.csv` (voto exterior) y
`noche_ensayo.csv` (la noche electoral hacia atrás, 2011-2023).

La noche de unas generales, `uv run censo noche <provisionales.json>` dice qué último
escaño de cada provincia puede dar la vuelta el voto exterior, que se cuenta cinco días
después. Los provisionales se bajan desde la web de resultados de Interior con
`herramientas/provisionales.js`.

## Fuentes

INE (censo electoral por municipio, padrón, PERE y Oficina del Censo Electoral) y
Ministerio del Interior (Infoelectoral y web de resultados). Los datos brutos no van en
el repo: `uv run censo descarga` baja los del INE y dice qué falta de Interior.

## Licencia

Código bajo licencia MIT. Los datos son de sus fuentes, con sus condiciones de reutilización.
