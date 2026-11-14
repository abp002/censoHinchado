// Baja los provisionales del Congreso de las 52 provincias a un único JSON.
// Se ejecuta en la consola (o con javascript_tool) DENTRO de la web de resultados de
// Interior, para que las peticiones lleven su origen y sus cookies (curl da 403).
// El fichero cae en ~/Descargas como provisionales_HHMM.json; después:
//   uv run censo noche ~/Downloads/provisionales_HHMM.json
//
// Rutas vistas en las generales de 2023 (resultados.generales23j.es). Si la web de 2026
// cambia, mira en la pestaña Red qué getScopeData pide al abrir una provincia y ajusta
// SUFIJO (lo que va detrás del scopeId).
(async () => {
  const BASE = location.origin + "/backend-difu";
  const CONGRESO = 2;
  const SUFIJO = "/1/2/1/0"; // 2023, ámbito con todas las candidaturas
  const nom = await (await fetch(`${BASE}/nomenclator/getNomenclator`)).json();
  const ambitos = nom.amb.find((a) => a.elec === CONGRESO).ambitos;
  const provincias = ambitos.filter((a) => a.l === 30);
  const respuestas = [];
  for (const p of provincias) {
    const r = await fetch(`${BASE}/scope/data/getScopeData/${p.c}${SUFIJO}`);
    if (r.ok) respuestas.push(await r.json());
    else console.warn("provisionales:", p.n, r.status);
  }
  const hora = new Date().toTimeString().slice(0, 5).replace(":", "");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(respuestas)], { type: "application/json" }));
  a.download = `provisionales_${hora}.json`;
  a.click();
  return `${respuestas.length}/${provincias.length} provincias -> ${a.download}`;
})();
