// Mapa, ficha y lista de los pueblos señalados. Los datos los deja `censo web` en #datos.
(function () {
  const D = JSON.parse(document.getElementById("datos").textContent);
  const SVG = "http://www.w3.org/2000/svg";
  const mapa = document.getElementById("mapa");
  const gPuntos = document.getElementById("puntos");
  const gRotulos = document.getElementById("rotulos");
  const ficha = document.getElementById("ficha");
  const pista = document.getElementById("pista");
  const cajaAnyos = document.getElementById("anyos");
  const raya = document.getElementById("raya");
  const listaCaja = document.getElementById("lista");
  const ANCHO = mapa.viewBox.baseVal.width;
  const quieto = matchMedia("(prefers-reduced-motion: reduce)").matches;

  let eleccion = D.elecciones[0];
  let elegido = null;
  let paseo = null; // el recorrido automático por las municipales al cargar

  const num = (v) => (v == null ? "—" : String(Math.round(v)).replace(/\B(?=(\d{3})+(?!\d))/g, "."));
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const plural = (n, uno, varios) => `${num(n)} ${n === 1 ? uno : varios}`;
  const deEleccion = () => D.pueblos.filter((p) => p.e === eleccion.id);
  const alcanza = (p) => !!(p.res && p.res.alcanza);
  const orden = (a, b) => alcanza(b) - alcanza(a) || b.exceso - a.exceso || a.n.localeCompare(b.n, "es");

  // --- Titular letra a letra ---
  (function titular() {
    const h = document.getElementById("titular");
    const palabras = h.textContent.split(" ");
    h.setAttribute("aria-label", h.textContent);
    h.textContent = "";
    let i = 0;
    palabras.forEach((palabra, k) => {
      const p = document.createElement("span");
      p.className = "p";
      p.setAttribute("aria-hidden", "true");
      for (const letra of palabra) {
        const l = document.createElement("span");
        l.className = "l";
        l.textContent = letra;
        l.style.animationDelay = `${i++ * 22}ms`;
        p.appendChild(l);
      }
      h.appendChild(p);
      if (k < palabras.length - 1) h.appendChild(document.createTextNode(" "));
    });
  })();

  // --- El mapa se dibuja provincia a provincia, de norte a sur ---
  document.querySelectorAll(".provincias path").forEach((p) => {
    const b = p.getBBox();
    p.style.animationDelay = `${Math.round((b.y + b.x * 0.35) * 0.9)}ms`;
  });

  // --- Números que cuentan ---
  const cuentas = new WeakMap();
  function cuenta(el, hasta) {
    cancelAnimationFrame(cuentas.get(el));
    const desde = parseInt(el.textContent.replace(/\D/g, ""), 10) || 0;
    if (quieto || desde === hasta) { el.textContent = num(hasta); return; }
    const dur = 600;
    let t0 = null;
    const paso = (t) => {
      if (t0 === null) t0 = t;
      const k = Math.min(1, (t - t0) / dur);
      el.textContent = num(desde + (hasta - desde) * (1 - Math.pow(1 - k, 3)));
      if (k < 1) cuentas.set(el, requestAnimationFrame(paso));
    };
    cuentas.set(el, requestAnimationFrame(paso));
  }

  // --- Años ---
  for (const e of D.elecciones) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = e.anyo;
    b.setAttribute("aria-label", `Municipales de ${e.anyo}: ${e.n} pueblos señalados`);
    b.addEventListener("click", () => { paraPaseo(); cambia(e); });
    cajaAnyos.insertBefore(b, raya);
  }
  function marcaAnyo() {
    [...cajaAnyos.querySelectorAll("button")].forEach((b, i) => {
      const activo = D.elecciones[i] === eleccion;
      b.setAttribute("aria-pressed", activo);
      if (activo) {
        raya.style.width = b.offsetWidth + "px";
        raya.style.transform = `translateX(${b.offsetLeft}px)`;
      }
    });
  }

  // --- Puntos ---
  const px = () => ANCHO / (mapa.getBoundingClientRect().width || ANCHO);
  const radio = (p, k) => Math.max(4, 1.9 * Math.sqrt(p.exceso)) * Math.min(k, 2.2);

  function puntos(entrada) {
    const k = px();
    gPuntos.innerHTML = "";
    const lista = deEleccion().sort((a, b) => b.exceso - a.exceso);
    // Entran de norte a sur
    const retraso = new Map([...lista].sort((a, b) => a.y - b.y).map((p, i) => [p, i * 14]));
    for (const p of lista) {
      const g = document.createElementNS(SVG, "g");
      if (alcanza(p)) g.classList.add("alcanza");
      if (p === elegido) g.classList.add("elegido");
      const r = radio(p, k).toFixed(1);
      for (const clase of ["onda", "p"]) {
        const c = document.createElementNS(SVG, "circle");
        c.setAttribute("class", clase);
        c.setAttribute("cx", p.x);
        c.setAttribute("cy", p.y);
        c.setAttribute("r", r);
        if (clase === "p") c.style.animationDelay = entrada ? `${retraso.get(p)}ms` : "-1s";
        g.appendChild(c);
      }
      g.addEventListener("click", () => { paraPaseo(); elige(p); });
      g.addEventListener("pointerenter", (ev) => muestraPista(p, ev));
      g.addEventListener("pointermove", muevePista);
      g.addEventListener("pointerleave", () => { pista.hidden = true; });
      g.dataset.cod = p.cod;
      gPuntos.appendChild(g);
    }
    const arriba = gPuntos.querySelector(".elegido");
    if (arriba) gPuntos.appendChild(arriba);
    rotulos(k);
  }

  // Rótulos: los pueblos con algo publicado y el elegido; si dos se pisan, el de abajo baja
  function rotulos(k) {
    gRotulos.innerHTML = "";
    const alto = 14 * Math.min(k, 2.2);
    const rs = deEleccion().filter((p) => p.casos || p === elegido).map((p) => {
      const izq = p.x > ANCHO * 0.72;
      const d = radio(p, k) + 6 * k;
      return { p, izq, x: p.x + (izq ? -d : d), y: p.y + 4 * k };
    }).sort((a, b) => a.y - b.y);
    rs.forEach((r, i) => {
      for (const o of rs.slice(0, i)) {
        if (o.izq === r.izq && Math.abs(o.x - r.x) < 170 * k && r.y - o.y < alto) r.y = o.y + alto;
      }
      const t = document.createElementNS(SVG, "text");
      t.setAttribute("x", r.x.toFixed(1));
      t.setAttribute("y", r.y.toFixed(1));
      t.setAttribute("text-anchor", r.izq ? "end" : "start");
      t.setAttribute("font-size", (12.5 * Math.min(k, 2.2)).toFixed(1));
      if (r.p !== elegido) t.setAttribute("fill-opacity", "0.6");
      t.textContent = r.p.n;
      gRotulos.appendChild(t);
    });
  }

  function muestraPista(p, ev) {
    if (ev.pointerType === "touch") return;
    const r = p.res;
    pista.innerHTML = `<b>${esc(p.n)}</b>${plural(p.exceso, "elector", "electores")} de más` +
      (r && r.segundo != null ? ` · diferencia de ${plural(r.margen, "voto", "votos")}` : "");
    pista.hidden = false;
    muevePista(ev);
  }
  function muevePista(ev) {
    pista.style.left = Math.min(ev.clientX + 14, window.innerWidth - pista.offsetWidth - 8) + "px";
    pista.style.top = ev.clientY + 16 + "px";
  }

  // --- Ficha ---
  function grafica(p) {
    const pasos = [];
    if (p.antes != null) pasos.push(["Antes", eleccion.antes, p.antes]);
    pasos.push(["Municipales", eleccion.fecha, p.mun]);
    pasos.push(["Después", eleccion.despues, p.desp]);
    const W = 360, H = 132, arriba = 26, abajo = 38, lado = 42;
    const vs = pasos.map((s) => s[2]);
    const min = Math.min(...vs, p.mun - p.exceso), max = Math.max(...vs);
    const y = (v) => arriba + (H - arriba - abajo) * (1 - (v - min) / (max - min || 1));
    const x = (i) => lado + (i * (W - 2 * lado)) / (pasos.length - 1);
    const pts = pasos.map((q, i) => `${x(i)},${y(q[2])}`).join(" ");
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Censo de residentes: ${vs.join(", ")}">`;
    s += `<polygon class="zona" points="${pts} ${x(pasos.length - 1)},${H - abajo + 6} ${x(0)},${H - abajo + 6}"/>`;
    s += `<polyline class="linea" pathLength="1" points="${pts}"/>`;
    pasos.forEach((q, i) => {
      const pico = q[0] === "Municipales";
      s += `<circle${pico ? ' class="pico"' : ""} cx="${x(i)}" cy="${y(q[2])}" r="${pico ? 5 : 4}"/>`;
      s += `<text class="valor" x="${x(i)}" y="${y(q[2]) - 11}" text-anchor="middle">${num(q[2])}</text>`;
      s += `<text x="${x(i)}" y="${H - 14}" text-anchor="middle">${q[0]}</text>`;
      s += `<text x="${x(i)}" y="${H}" text-anchor="middle">${esc(q[1])}</text>`;
    });
    return s + "</svg>";
  }

  function pintaFicha() {
    const p = elegido;
    if (!p) { ficha.innerHTML = ""; return; }
    const r = p.res;
    let h = `<p class="donde">${esc(p.p)} · municipales de ${eleccion.anyo} · censo de residentes</p><h2>${esc(p.n)}</h2>`;
    h += grafica(p);
    h += `<div class="cifras"><div><b>${num(p.exceso)}</b><span>electores de más</span></div>`;
    if (r) {
      h += `<div><b>${num(r.mesa)}</b><span>seguían en la mesa al votar</span></div>`;
      h += r.segundo == null
        ? `<div><b>1</b><span>sola lista</span></div>`
        : `<div><b>${num(r.margen)}</b><span>${r.margen === 1 ? "voto" : "votos"} entre ${esc(r.gana)} y ${esc(r.segundo)}</span></div>`;
    } else {
      h += `<div><b>${num(p.padron)}</b><span>habitantes de más en el padrón</span></div>`;
    }
    h += `</div>`;
    if (r && r.segundo != null) {
      h += r.alcanza
        ? `<p class="veredicto alcanza">Los que seguían en la mesa alcanzan la diferencia de votos.</p>`
        : `<p class="veredicto">Los que seguían en la mesa no alcanzan la diferencia de votos.</p>`;
    } else if (!r) {
      h += `<p class="veredicto">Sin cruzar con el resultado de ${eleccion.anyo}.</p>`;
    }
    if (p.oce || p.casos) {
      h += `<div class="publicado">`;
      for (const c of p.casos || []) h += `<p>${esc(c.texto)} <a href="${esc(c.url)}">${esc(c.medio)}</a></p>`;
      if (p.oce) {
        h += `<p>${p.oce === "municipio" ? "Está" : "Una entidad menor del municipio está"} en la lista de altas sin justificar de la Oficina del Censo Electoral de 2023. <a href="${esc(D.oce.url)}">INE</a></p>`;
      }
      h += `</div>`;
    }
    ficha.innerHTML = h;
  }

  // --- Lista ---
  function lista() {
    document.getElementById("lista-titulo").textContent = `Los ${eleccion.n} pueblos de ${eleccion.anyo}`;
    listaCaja.innerHTML = "";
    for (const p of deEleccion().sort(orden)) {
      const b = document.createElement("button");
      b.type = "button";
      b.dataset.cod = p.cod;
      b.setAttribute("aria-pressed", p === elegido);
      b.innerHTML = `<i class="marca${alcanza(p) ? " alcanza" : ""}"></i>` +
        `<span class="quien">${esc(p.n)}<small>${esc(p.p)}</small></span><span class="cuanto">+${num(p.exceso)}</span>`;
      b.addEventListener("click", () => {
        paraPaseo();
        elige(p);
        document.getElementById("pueblos").scrollIntoView({ behavior: quieto ? "auto" : "smooth" });
      });
      listaCaja.appendChild(b);
    }
  }

  function elige(p) {
    elegido = p;
    for (const g of gPuntos.children) g.classList.toggle("elegido", g.dataset.cod === p.cod);
    const arriba = gPuntos.querySelector(".elegido");
    if (arriba) gPuntos.appendChild(arriba);
    rotulos(px());
    pintaFicha();
    for (const b of listaCaja.children) b.setAttribute("aria-pressed", b.dataset.cod === p.cod);
  }

  function cambia(e) {
    eleccion = e;
    const ps = deEleccion().sort(orden);
    elegido = ps.find((p) => p.casos) || ps[0];
    marcaAnyo();
    cuenta(document.getElementById("n-pueblos"), e.n);
    document.getElementById("alcanzan-caja").hidden = !e.resultados;
    if (e.resultados) cuenta(document.getElementById("n-alcanzan"), e.alcanzan);
    gPuntos.classList.add("se-va");
    setTimeout(() => {
      gPuntos.classList.remove("se-va");
      puntos(true);
      pintaFicha();
      lista();
    }, gPuntos.childElementCount && !quieto ? 220 : 0);
  }

  // Al cargar recorre las municipales de la primera a la última; cualquier clic lo para
  function paraPaseo() { clearTimeout(paseo); paseo = null; }
  function pasea(i) {
    cambia(D.elecciones[i]);
    if (i < D.elecciones.length - 1) paseo = setTimeout(() => pasea(i + 1), 1500);
  }

  // --- Lo de más abajo aparece al llegar ---
  const mira = new IntersectionObserver((es) => {
    for (const e of es) if (e.isIntersecting) { e.target.classList.add("visto"); mira.unobserve(e.target); }
  }, { threshold: 0.2 });
  document.querySelectorAll(".ver, .ola, .cambio").forEach((el) => mira.observe(el));
  document.querySelectorAll(".ola").forEach((o) => {
    const pista0 = o.querySelector(".ola-pista");
    if (pista0) o.style.setProperty("--ancho-pista", pista0.offsetWidth + "px");
  });

  let espera;
  window.addEventListener("resize", () => {
    clearTimeout(espera);
    espera = setTimeout(() => { puntos(false); marcaAnyo(); }, 120);
  });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(marcaAnyo);

  if (quieto) cambia(D.elecciones[D.elecciones.length - 1]);
  else setTimeout(() => pasea(0), 900);
})();
