// Mapa, ficha y lista de los pueblos señalados. Los datos los deja `censo web` en #datos.
(function () {
  const D = JSON.parse(document.getElementById("datos").textContent);
  const SVG = "http://www.w3.org/2000/svg";
  const mapa = document.getElementById("mapa");
  const gPuntos = document.getElementById("puntos");
  const gRotulos = document.getElementById("rotulos");
  const ficha = document.getElementById("ficha");
  const pista = document.getElementById("pista");
  const cuerpo = document.querySelector("#lista tbody");
  const ANCHO = mapa.viewBox.baseVal.width;

  let eleccion = D.elecciones[D.elecciones.length - 1];
  let elegido = null;

  const num = (v) => (v == null ? "—" : String(Math.round(v)).replace(/\B(?=(\d{3})+(?!\d))/g, "."));
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const plural = (n, uno, varios) => `${num(n)} ${n === 1 ? uno : varios}`;
  const deEleccion = () => D.pueblos.filter((p) => p.e === eleccion.id);
  const alcanza = (p) => !!(p.res && p.res.alcanza);
  // Primero los que alcanzan la diferencia; dentro, de más a menos electores de más
  const orden = (a, b) => alcanza(b) - alcanza(a) || b.exceso - a.exceso || a.n.localeCompare(b.n, "es");

  function selector() {
    const caja = document.getElementById("selector");
    caja.innerHTML = "";
    for (const e of D.elecciones) {
      const b = document.createElement("button");
      b.type = "button";
      b.setAttribute("aria-pressed", e === eleccion);
      b.innerHTML = `<span class="anyo">${e.anyo}</span><span class="cuenta">${e.n}</span>`;
      b.setAttribute("aria-label", `Municipales de ${e.anyo}: ${e.n} pueblos señalados`);
      b.addEventListener("click", () => { eleccion = e; elegido = null; pinta(); });
      caja.appendChild(b);
    }
  }

  // Un píxel de pantalla en unidades del mapa: los puntos no encogen en el móvil
  const px = () => ANCHO / (mapa.getBoundingClientRect().width || ANCHO);
  const radio = (p, k) => Math.max(4, 1.9 * Math.sqrt(p.exceso)) * Math.min(k, 2.2);

  function puntos() {
    const k = px();
    gPuntos.innerHTML = "";
    gRotulos.innerHTML = "";
    const lista = deEleccion().sort((a, b) => b.exceso - a.exceso);
    for (const p of lista) {
      const c = document.createElementNS(SVG, "circle");
      c.setAttribute("cx", p.x);
      c.setAttribute("cy", p.y);
      c.setAttribute("r", radio(p, k).toFixed(1));
      if (alcanza(p)) c.classList.add("alcanza");
      if (p === elegido) c.classList.add("elegido");
      c.addEventListener("click", () => elige(p, true));
      c.addEventListener("pointerenter", (ev) => muestraPista(p, ev));
      c.addEventListener("pointermove", muevePista);
      c.addEventListener("pointerleave", () => { pista.hidden = true; });
      gPuntos.appendChild(c);
    }
    const arriba = gPuntos.querySelector(".elegido");
    if (arriba) gPuntos.appendChild(arriba); // el elegido, encima
    // Rótulos: los pueblos con algo publicado y el elegido; si dos se pisan, el de abajo baja
    const alto = 13 * Math.min(k, 2.2);
    const rotulos = lista.filter((p) => p.casos || p === elegido).map((p) => {
      const izq = p.x > ANCHO * 0.72;
      const d = radio(p, k) + 5 * k;
      return { p, izq, x: p.x + (izq ? -d : d), y: p.y + 4 * k };
    }).sort((a, b) => a.y - b.y);
    rotulos.forEach((r, i) => {
      for (const o of rotulos.slice(0, i)) {
        if (o.izq === r.izq && Math.abs(o.x - r.x) < 160 * k && r.y - o.y < alto) r.y = o.y + alto;
      }
      const t = document.createElementNS(SVG, "text");
      t.setAttribute("x", r.x.toFixed(1));
      t.setAttribute("y", r.y.toFixed(1));
      t.setAttribute("text-anchor", r.izq ? "end" : "start");
      t.setAttribute("font-size", (12 * Math.min(k, 2.2)).toFixed(1));
      if (r.p === elegido) t.setAttribute("font-weight", "500");
      t.textContent = r.p.n;
      gRotulos.appendChild(t);
    });
  }

  function muestraPista(p, ev) {
    const r = p.res;
    pista.innerHTML = `<b>${esc(p.n)}</b>${plural(p.exceso, "elector", "electores")} de más` +
      (r ? `<br>diferencia de ${plural(r.margen, "voto", "votos")}` : "");
    pista.hidden = false;
    muevePista(ev);
  }
  function muevePista(ev) {
    const w = pista.offsetWidth;
    pista.style.left = Math.min(ev.clientX + 14, window.innerWidth - w - 8) + "px";
    pista.style.top = ev.clientY + 16 + "px";
  }

  function grafica(p) {
    const pasos = [];
    if (p.antes != null) pasos.push(["Generales", eleccion.antes, p.antes]);
    pasos.push(["Municipales", eleccion.fecha, p.mun]);
    pasos.push(["Generales", eleccion.despues, p.desp]);
    const W = 340, H = 168, arriba = 30, abajo = 44, lado = 46;
    const vs = pasos.map((s) => s[2]);
    const min = Math.min(...vs), max = Math.max(...vs);
    const y = (v) => arriba + (H - arriba - abajo) * (1 - (v - min) / (max - min || 1));
    const x = (i) => lado + (i * (W - 2 * lado)) / (pasos.length - 1);
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Censo de residentes: ${vs.join(", ")}">`;
    s += `<line class="base" x1="0" x2="${W}" y1="${H - abajo + 8}" y2="${H - abajo + 8}"/>`;
    s += `<polyline class="linea" points="${pasos.map((q, i) => `${x(i)},${y(q[2])}`).join(" ")}"/>`;
    pasos.forEach((q, i) => {
      const pico = q[0] === "Municipales";
      s += `<circle${pico ? ' class="pico"' : ""} cx="${x(i)}" cy="${y(q[2])}" r="${pico ? 5.5 : 4.5}"/>`;
      s += `<text class="valor" x="${x(i)}" y="${y(q[2]) - 12}" text-anchor="middle">${num(q[2])}</text>`;
      s += `<text x="${x(i)}" y="${H - 18}" text-anchor="middle">${q[0]}</text>`;
      s += `<text x="${x(i)}" y="${H - 3}" text-anchor="middle">${esc(q[1])}</text>`;
    });
    return s + "</svg>";
  }

  function pintaFicha() {
    const p = elegido;
    if (!p) { ficha.innerHTML = ""; return; }
    let h = `<span class="kicker">${esc(p.p)} · Municipales de ${eleccion.anyo}</span><h3>${esc(p.n)}</h3>`;
    h += `<div><span class="kicker">Censo de residentes</span>${grafica(p)}</div>`;
    h += `<p><strong>${plural(p.exceso, "elector", "electores")} de más</strong> en la municipal. ` +
      `El padrón del pueblo, de ${plural(p.pob, "habitante", "habitantes")} ese 1 de enero, ` +
      `tenía ${num(p.padron)} que no estaban el año anterior y dejaron de estar en uno o dos años.</p>`;
    const r = p.res;
    if (r) {
      if (r.segundo == null) {
        h += `<p>Solo hubo una lista: ${esc(r.gana)}, con ${plural(r.v1, "voto", "votos")}.</p>`;
      } else if (r.margen === 0) {
        h += `<p>Las dos primeras listas, ${esc(r.gana)} y ${esc(r.segundo)}, <strong>empataron a ${plural(r.v1, "voto", "votos")}</strong>.</p>`;
      } else {
        h += `<p>Ganó ${esc(r.gana)} con ${plural(r.v1, "voto", "votos")}; la segunda lista, ${esc(r.segundo)}, tuvo ${num(r.v2)}: ` +
          `<strong>${plural(r.margen, "voto", "votos")} de diferencia</strong>.</p>`;
      }
      h += `<p>De los ${num(p.exceso)} de más, <strong>${r.mesa === p.exceso ? "todos seguían" : r.mesa === 1 ? "1 seguía" : num(r.mesa) + " seguían"}</strong> en el censo de la mesa el día de votar.</p>`;
      if (r.segundo != null) {
        h += r.alcanza
          ? `<div class="veredicto alcanza">El exceso alcanza la diferencia de votos</div>`
          : `<div class="veredicto">El exceso no alcanza la diferencia de votos</div>`;
      }
    } else {
      h += `<div class="veredicto">Sin cruzar con el resultado de ${eleccion.anyo}</div>`;
    }
    if (p.oce || p.casos) {
      h += `<div class="publicado"><span class="kicker">Lo publicado</span>`;
      for (const c of p.casos || []) {
        h += `<p>${esc(c.texto)} <a href="${esc(c.url)}">${esc(c.medio)}</a></p>`;
      }
      if (p.oce) {
        h += `<p>${p.oce === "municipio" ? "Está" : "Una entidad menor del municipio está"} en la lista de altas sin justificar de la Oficina del Censo Electoral de abril de 2023. <a href="${esc(D.oce.url)}">INE</a></p>`;
      }
      h += `</div>`;
    }
    if (p.otras.length) {
      h += `<p class="mono" style="font-size:13px">También señalado en ${p.otras.join(", ")}.</p>`;
    }
    h += `<p class="mono" style="font-size:12px;color:var(--faint)">Anomalía estadística: no dice quién se empadronó ni por qué.</p>`;
    ficha.innerHTML = h;
  }

  function lista() {
    const ps = deEleccion().sort(orden);
    document.getElementById("lista-titulo").textContent = `Municipales de ${eleccion.anyo}: ${eleccion.n} pueblos`;
    document.getElementById("lista-nota").textContent = eleccion.resultados
      ? `En ${eleccion.alcanzan}, el exceso alcanza la diferencia de votos`
      : "Sin cruzar con resultados";
    cuerpo.innerHTML = "";
    for (const p of ps) {
      const tr = document.createElement("tr");
      tr.tabIndex = 0;
      tr.setAttribute("aria-selected", p === elegido);
      if (alcanza(p)) tr.className = "si";
      const r = p.res;
      const dif = !r ? "—" : r.segundo == null ? "una lista" : r.margen === 0 ? "empate" : num(r.margen);
      tr.innerHTML = `<td><i class="marca${alcanza(p) ? " alcanza" : ""}"></i>${esc(p.n)}${p.casos ? '<span class="fuente">publicado</span>' : ""}</td><td>${esc(p.p)}</td>` +
        `<td class="n">${num(p.antes)}</td><td class="n">${num(p.mun)}</td><td class="n">${num(p.desp)}</td>` +
        `<td class="n">${num(p.exceso)}</td><td class="n">${r ? num(r.mesa) : "—"}</td><td class="n">${dif}</td>`;
      tr.addEventListener("click", () => elige(p, false));
      tr.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); elige(p, false); }
      });
      tr.dataset.cod = p.cod;
      cuerpo.appendChild(tr);
    }
  }

  function elige(p, desdeMapa) {
    elegido = p;
    puntos();
    pintaFicha();
    for (const tr of cuerpo.children) tr.setAttribute("aria-selected", tr.dataset.cod === p.cod);
    if (desdeMapa) {
      const tr = cuerpo.querySelector(`[data-cod="${p.cod}"]`);
      const caja = tr && tr.closest(".desliza");
      if (caja) caja.scrollTop = tr.offsetTop - caja.clientHeight / 2;
    }
  }

  function pinta() {
    const ps = deEleccion().sort(orden);
    elegido = elegido || ps.find((p) => p.casos) || ps[0];
    selector();
    puntos();
    pintaFicha();
    lista();
  }

  let espera;
  window.addEventListener("resize", () => { clearTimeout(espera); espera = setTimeout(puntos, 120); });
  pinta();
})();
