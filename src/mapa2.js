import { addStationLabels, addTransit, badge, createMap, esc, getJSON, maplibregl, northArrow, PARAMS, PRINT } from "./common.js";
import { basemapLabelLayers } from "./basemap.js";
import { renderSources } from "./sources.js";

const zi = (...s) => ["interpolate", ["exponential", 1.4], ["zoom"], ...s];
const [data, geo, red, avisos, fuentes, andenes] = await Promise.all(
  ["itinerarios.json", "itinerarios.geojson", "red.json", "avisos.json", "fuentes.json", "andenes.geojson"].map((f) => getJSON("data/" + f)));
const EST = red.estaciones, LINES = red.lineas, IT = data.itinerarios;
renderSources(document.getElementById("fuentes-c"), fuentes, avisos);
document.getElementById("btn-fuentes").onclick = () => document.getElementById("fuentes").showModal();
document.querySelector("#fuentes .x").onclick = () => document.getElementById("fuentes").close();

const state = { modo: PARAMS.get("modo") === "vuelta" ? "vuelta" : "ida", esc: +(PARAMS.get("escenario") || 0) };
const routeBounds = () => {
  const fs = geo.features.filter((f) => f.properties.it === cur().id);
  const b = new maplibregl.LngLatBounds();
  for (const f of fs) for (const c of f.geometry.coordinates) b.extend(c);
  return b;
};
const cur = () => IT[state.modo][state.esc] || IT[state.modo][0];

const map = createMap("map", { bounds: [[-3.765, 40.36], [-3.66, 40.44]] });
northArrow(document.querySelector(".map"));
const markers = [];
const BASE = {};

map.on("load", async () => {
  for (const l of basemapLabelLayers()) map.addLayer(l);
  await addTransit(map, { dim: true, avisos: false });
  addStationLabels(map, { dim: true });
  for (const id of ["lbl-st-1", "lbl-st-2", "lbl-st-3"]) BASE[id] = map.getFilter(id);
  map.on("zoom", () => document.querySelector(".map").classList.toggle("z-lo", map.getZoom() < 14.2));
  map.addSource("route", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
  map.addSource("rstops", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
  map.addSource("accesos", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
  const ride = ["in", ["get", "tipo"], ["literal", ["metro", "bus"]]];
  map.addLayer({ id: "route-glow", type: "line", source: "route", filter: ride, layout: { "line-cap": "round", "line-join": "round" },
    paint: { "line-color": "#e6007e", "line-opacity": 0.28, "line-width": zi(10, 12, 14, 22, 17, 32), "line-blur": 2 } });
  map.addLayer({ id: "route-case", type: "line", source: "route", filter: ride, layout: { "line-cap": "round", "line-join": "round" },
    paint: { "line-color": "#ffffff", "line-width": zi(10, 6.5, 14, 11, 17, 16) } });
  map.addLayer({ id: "route-line", type: "line", source: "route", filter: ride, layout: { "line-cap": "round", "line-join": "round" },
    paint: { "line-color": ["case", ["==", ["get", "color"], "#FFFFFF"], "#005AA9", ["get", "color"]], "line-width": zi(10, 4, 14, 7, 17, 11) } });
  map.addLayer({ id: "route-walk-case", type: "line", source: "route", filter: ["==", ["get", "tipo"], "pie"], layout: { "line-cap": "round", "line-join": "round" },
    paint: { "line-color": "#ffffff", "line-width": zi(12, 6, 17, 11) } });
  map.addLayer({ id: "route-walk", type: "line", source: "route", filter: ["==", ["get", "tipo"], "pie"], layout: { "line-cap": "round", "line-join": "round" },
    paint: { "line-color": "#e6007e", "line-width": zi(12, 3.5, 17, 7), "line-dasharray": [0.1, 1.7] } });
  map.addLayer({ id: "acc-other", type: "circle", source: "accesos", filter: ["==", ["get", "sel"], 0], minzoom: 15,
    paint: { "circle-radius": 4, "circle-color": "#ffffff", "circle-stroke-color": "#85807a", "circle-stroke-width": 1.5 } });
  map.addLayer({ id: "acc-other-lbl", type: "symbol", source: "accesos", filter: ["==", ["get", "sel"], 0], minzoom: 16,
    layout: { "text-field": ["get", "nombre"], "text-font": ["Noto Sans Regular"], "text-size": 10.5, "text-anchor": "top", "text-offset": [0, 0.7], "text-max-width": 8 },
    paint: { "text-color": "#6f685f", "text-halo-color": "#fff", "text-halo-width": 1.4 } });
  map.addLayer({ id: "rstops", type: "circle", source: "rstops",
    paint: { "circle-radius": zi(10, ["case", ["==", ["get", "major"], 1], 5, 3], 15, ["case", ["==", ["get", "major"], 1], 8, 5]), "circle-color": "#ffffff",
      "circle-stroke-color": ["case", ["==", ["get", "major"], 1], "#1d1c1a", ["get", "color"]], "circle-stroke-width": ["case", ["==", ["get", "major"], 1], 3, 2] } });
  map.addLayer({ id: "rstops-lbl", type: "symbol", source: "rstops",
    layout: { "text-field": ["get", "name"], "text-font": ["case", ["==", ["get", "major"], 1], ["literal", ["Noto Sans Medium"]], ["literal", ["Noto Sans Regular"]]],
      "text-size": ["case", ["==", ["get", "major"], 1], 13, 11], "text-variable-anchor": ["left", "right", "top", "bottom"], "text-radial-offset": 0.9,
      "symbol-sort-key": ["-", 1, ["get", "major"]], "text-padding": 2 },
    paint: { "text-color": "#1d1c1a", "text-halo-color": "#ffffff", "text-halo-width": 2 } });
  render();
  if (PRINT) printFrame();
  window.__map = map;
  // en exportación, reencuadre final cuando ya está aplicado el diseño de página (tamaño definitivo del mapa)
  map.once("idle", () => { if (PRINT) { map.resize(); fitRoute(); map.once("idle", () => { window.__READY = true; }); } else window.__READY = true; });
});

/* ------------------------------------------------------------------ panel */
function render() {
  const it = cur();
  document.querySelectorAll("#modes .mode").forEach((b) => b.setAttribute("aria-pressed", b.dataset.m === state.modo));
  document.getElementById("scen").innerHTML = IT[state.modo].map((x, i) => `<button data-i="${i}" aria-pressed="${i === state.esc}"><span class="t">${i === 0 ? "★ " : ""}${esc(x.titulo)}</span><span class="w">${esc(x.cuando)} · ≈ ${x.total_min} min</span></button>`).join("");
  document.getElementById("r-title").textContent = state.modo === "ida" ? "IDA · Carabanchel Alto → Cristo Social Club" : "VUELTA · Cristo Social Club → Carabanchel Alto";
  document.getElementById("summary").innerHTML = `
    <div class="metric"><b>≈ ${it.total_min} min</b><span>tiempo total estimado</span></div>
    <div class="metric"><b>${it.a_pie_m} m</b><span>a pie por la calle</span></div>
    <div class="metric"><b>${it.transbordos}</b><span>${it.transbordos === 1 ? "transbordo" : "transbordos"}</span></div>`;
  document.getElementById("steps").innerHTML = it.pasos.map(stepHTML).join("");
  document.getElementById("notes").innerHTML = [...it.notas.map((n) => `<div class="note warn">${esc(n)}</div>`),
    `<div class="note">Tiempos orientativos: trayectos entre estaciones del GTFS oficial; espera = mitad del intervalo de paso en la franja indicada; a pie a ${data.supuestos.velocidad_pie_kmh} km/h por la red peatonal de OSM; pasillos de estación estimados (distancia × ${data.supuestos.rodeo_pasillos} + ${data.supuestos.escaleras_min} min). No es información en tiempo real.</div>`].join("");
  renderDest();
  renderCmp();
  drawRoute(it);
}

const lb = (l) => { const L = LINES[`metro:${l}`]; return L ? badge(l, L.color, L.texto) : esc(l); };
function stepHTML(p, i) {
  const ic = { inicio: "A", fin: "★", pie: "🚶", transbordo: "⇄", cambio: "↻", salida: "↗", entrada: "↘" };
  if (p.tipo === "metro") {
    const L = LINES[`metro:${p.linea}`];
    return `<li class="step metro" data-i="${i}" style="--c:${L.color === "#FFFFFF" ? L.texto : L.color};--tc:${L.color === "#FFFFFF" ? "#fff" : L.texto}"><span class="sicon">${esc(p.linea)}</span><div>
      <div class="stxt">Toma la <b>Línea ${esc(p.linea)}</b> ${lb(p.linea)} en <b>${esc(p.desde)}</b></div>
      <div class="dirbox">Dirección: <b>${esc(p.hacia)}</b>${p.direccion.startsWith("sentido") ? `<br><span class="small">${esc(p.direccion)}</span>` : ""}</div>
      <div class="stxt" style="margin-top:6px">Baja en <b>${esc(p.hasta)}</b> · ${p.n_paradas} ${p.n_paradas === 1 ? "parada" : "paradas"} · ${Math.round(p.min)} min</div>
      <div class="sdet">Tren cada ${fmt(p.intervalo_min)} min en la franja de referencia (espera media ≈ ${fmt(p.espera_min)} min)</div>
      <details class="stops"><summary>Estaciones del tramo (${p.paradas.length})</summary>${p.paradas.map(esc).join(" → ")}</details></div></li>`;
  }
  if (p.tipo === "bus") {
    return `<li class="step bus" data-i="${i}" style="--c:${p.color}"><span class="sicon" style="font-size:11px">${esc(p.linea)}</span><div>
      <div class="stxt">Toma el autobús <b>${esc(p.linea)}</b> (EMT) en la parada <b>«${esc(p.desde)}»</b> (n.º ${esc(p.desde_id)})</div>
      <div class="dirbox">Dirección: <b>${esc(p.direccion)}</b></div>
      <div class="stxt" style="margin-top:6px">Baja en <b>«${esc(p.hasta)}»</b> (n.º ${esc(p.hasta_id)}) · ${p.n_paradas} paradas · ${Math.round(p.min)} min</div>
      ${p.intervalo_min ? `<div class="sdet">Un autobús cada ${fmt(p.intervalo_min)} min (GTFS de EMT${p.espera_min ? `; espera media ≈ ${fmt(p.espera_min)} min` : ""})</div>` : ""}
      <details class="stops"><summary>Paradas (${p.paradas.length})</summary>${p.paradas.map(esc).join(" → ")}</details></div></li>`;
  }
  if (p.tipo === "pie") {
    return `<li class="step pie" data-i="${i}"><span class="sicon">${ic.pie}</span><div>
      <div class="stxt">Camina <b>${p.m} m</b> (≈ ${Math.max(1, Math.round(p.min))} min): ${esc(p.desde)} → <b>${esc(p.hasta)}</b></div>
      ${p.indicaciones?.length ? `<div class="sdet"><ol>${p.indicaciones.map((x) => `<li>${esc(x)}</li>`).join("")}</ol></div>` : ""}</div></li>`;
  }
  const txt = p.tipo === "transbordo"
    ? `<b>Transbordo en ${esc(p.lugar)}</b>: baja del tren y sigue los indicadores <b>Línea ${esc(p.a)}</b> ${lb(p.a)} (pasillo ≈ ${Math.max(1, Math.round(p.min))} min)`
    : esc(p.texto).replace(/«([^»]+)»/g, "«<b>$1</b>»");
  return `<li class="step ${p.tipo}" data-i="${i}"><span class="sicon">${ic[p.tipo] || "•"}</span><div><div class="stxt">${txt}</div>
    ${p.tipo === "salida" || p.tipo === "entrada" ? `<div class="sdet">Accesos oficiales del CRTM · recorrido interior estimado ≈ ${Math.max(1, Math.round(p.min))} min</div>` : ""}
    ${p.nota ? `<div class="sdet">${esc(p.nota)}</div>` : ""}</div></li>`;
}
const fmt = (x) => (x == null ? "—" : (Math.round(x * 2) / 2).toLocaleString("es"));

function renderDest() {
  const d = data.destino;
  document.getElementById("dest").innerHTML = `<h2>Destino verificado</h2>
    <p style="margin:0 0 6px"><b>${esc(d.nombre)}</b><br>${esc(d.direccion)} · distrito ${esc(d.distrito)}<br><span class="muted">Portal: ${d.coord[1].toFixed(5)}, ${d.coord[0].toFixed(5)} (ETRS89/WGS84)</span></p>
    <ul class="small" style="padding-left:18px;margin:6px 0">${d.verificacion.map((v) => `<li>${esc(v)}</li>`).join("")}</ul>
    <div class="note">${esc(d.horario)} La sala cierra cuando el metro aún no funciona o acaba de abrir: revisa la VUELTA de madrugada.</div>`;
}

function renderCmp() {
  const c = data.comparativa_estaciones.slice(0, 6), best = c[0], nb = data.comparativa_estaciones.find((x) => x.estacion === "Núñez de Balboa");
  document.getElementById("cmp").innerHTML = `<h2>¿Por qué ${esc(best.estacion)}?</h2>
    <p class="small" style="margin-top:0">Comparativa de estaciones cercanas para la IDA (viernes 23:30): distancia <b>real a pie</b> desde la salida óptima y tiempo total desde Carabanchel Alto.</p>
    <table class="cmp"><thead><tr><th>Estación</th><th>Salida</th><th>A pie</th><th>Total</th></tr></thead><tbody>
    ${c.map((x, i) => `<tr class="${i === 0 ? "best" : ""}"><td>${esc(x.estacion)}<br>${x.lineas.map(lb).join(" ")}</td><td>${esc(x.acceso)}<br><span class="muted">${esc(x.acceso_dir)}</span></td>
      <td>${x.a_pie_m} m<br><span class="muted">${x.linea_recta_m} m recta</span></td><td>${Math.round(x.total_min)} min<br><span class="muted">${x.transbordos} transb.</span></td></tr>`).join("")}
    </tbody></table>
    ${nb ? `<p class="small">Núñez de Balboa queda a ${nb.linea_recta_m} m en línea recta, casi igual que ${esc(best.estacion)} (${best.linea_recta_m} m), pero son ${nb.a_pie_m} m a pie y exige ${nb.transbordos} transbordos desde Carabanchel Alto: por eso sólo se propone cuando la L6 está cortada.</p>` : ""}`;
}

/* ------------------------------------------------------------------ mapa */
function drawRoute(it) {
  const fs = geo.features.filter((f) => f.properties.it === it.id);
  map.getSource("route").setData({ type: "FeatureCollection", features: fs });
  const pts = [], seen = new Set();
  it.pasos.forEach((p, i) => {
    if (p.tipo === "metro") {
      p.ids.forEach((sid, k) => {
        const a = andenes.features.find((f) => f.properties.sid === sid && f.properties.line === p.linea);
        const major = k === 0 || k === p.ids.length - 1 ? 1 : 0;
        const key = sid + major;
        if (!a || seen.has(sid) && !major) return;
        seen.add(sid);
        pts.push({ type: "Feature", geometry: a.geometry, properties: { name: EST[sid].nombre, color: LINES[`metro:${p.linea}`].color, major } });
      });
    }
    if (p.tipo === "bus") p.coords.forEach((c, k) => pts.push({ type: "Feature", geometry: { type: "Point", coordinates: c },
      properties: { name: k === 0 || k === p.coords.length - 1 ? `${p.paradas[k]} (${p.linea})` : "", color: p.color, major: k === 0 || k === p.coords.length - 1 ? 1 : 0 } }));
  });
  map.getSource("rstops").setData({ type: "FeatureCollection", features: pts });
  // las estaciones del itinerario se rotulan una sola vez (capa del recorrido), no también en la red de contexto
  const onRoute = it.pasos.flatMap((p) => p.ids || []);
  for (const id of ["lbl-st-1", "lbl-st-2", "lbl-st-3"]) map.setFilter(id, ["all", BASE[id], ["!", ["in", ["get", "id"], ["literal", onRoute]]]]);
  // accesos de las estaciones de entrada/salida junto a la sala
  const acc = [];
  for (const p of it.pasos) if (p.acceso) {
    const sid = Object.keys(EST).find((k) => EST[k].accesos.some((a) => a.id === p.acceso.id));
    for (const a of EST[sid].accesos) acc.push({ type: "Feature", geometry: { type: "Point", coordinates: a.coord }, properties: { nombre: a.nombre, sel: a.id === p.acceso.id ? 1 : 0 } });
  }
  map.getSource("accesos").setData({ type: "FeatureCollection", features: acc });
  // marcadores: origen, destino, transbordos y salida
  markers.splice(0).forEach((m) => m.remove());
  const mk = (cls, html, lnglat, anchor = "center") => { const el = document.createElement("div"); el.className = "mk " + cls; el.innerHTML = html; markers.push(new maplibregl.Marker({ element: el, anchor }).setLngLat(lnglat).addTo(map)); };
  mk("mk-dest", "", data.destino.coord, "bottom");
  mk("mk-orig", "", data.origen.coord);
  mk("mk-label", `Cristo Social Club · Juan Bravo, 35`, data.destino.coord, "top");
  mk("mk-label", `Metro Carabanchel Alto ${lb("11")}`, data.origen.coord, "top");
  let n = 0;
  it.pasos.forEach((p) => {
    if (p.tipo === "transbordo" || p.tipo === "cambio") { const c = p.coord || EST[Object.keys(EST).find((k) => EST[k].nombre === p.lugar && EST[k].red === "metro")]?.coord; if (c) mk("mk-num", `${++n}`, c); }
    if (p.acceso && (p.tipo === "salida" || p.tipo === "entrada")) mk("mk-exit", `${p.tipo === "salida" ? "Salida" : "Entrada"}: ${esc(p.acceso.nombre)}`, p.acceso.coord, "bottom");
  });
  if (!PRINT || !window.__fitted) { window.__fitted = true; fitRoute(); }
}
function fitRoute() {
  const side = document.getElementById("side");
  const pad = PRINT ? { top: 190, bottom: 110, left: 80, right: 80 } : matchMedia("(max-width: 860px)").matches ? 40 : { top: 60, bottom: 60, left: 60, right: 60 };
  map.fitBounds(routeBounds(), { padding: pad, duration: PRINT ? 0 : 800, maxZoom: 15.5 });
}

document.getElementById("modes").addEventListener("click", (e) => { const b = e.target.closest(".mode"); if (!b) return; state.modo = b.dataset.m; state.esc = 0; render(); fitRoute(); });
document.getElementById("scen").addEventListener("click", (e) => { const b = e.target.closest("[data-i]"); if (!b) return; state.esc = +b.dataset.i; render(); fitRoute(); });
document.getElementById("steps").addEventListener("click", (e) => {
  const li = e.target.closest(".step"); if (!li || e.target.closest("summary")) return;
  const f = geo.features.filter((x) => x.properties.it === cur().id && x.properties.paso === +li.dataset.i);
  const p = cur().pasos[+li.dataset.i];
  if (f.length) { const b = new maplibregl.LngLatBounds(); f.forEach((x) => x.geometry.coordinates.forEach((c) => b.extend(c))); map.fitBounds(b, { padding: 80, maxZoom: 17 }); }
  else if (p.coord) map.flyTo({ center: p.coord, zoom: 16 });
});
document.getElementById("btn-route").onclick = fitRoute;
document.getElementById("btn-dest").onclick = () => map.flyTo({ center: data.destino.coord, zoom: 16.6 });
document.getElementById("sidetoggle").onclick = () => document.getElementById("side").classList.toggle("collapsed");

function printFrame() {
  document.body.classList.add("print");
  document.querySelectorAll("#steps details").forEach((d) => (d.open = true));
  map.resize();
  fitRoute();
  const it = cur();
  document.getElementById("printframe").innerHTML = `
    <div class="pf-title"><h1>${state.modo === "ida" ? "IDA · Metro Carabanchel Alto → Cristo Social Club" : "VUELTA · Cristo Social Club → Metro Carabanchel Alto"}</h1>
      <p>${esc(it.titulo)} — ${esc(it.cuando)} · ≈ ${it.total_min} min · ${it.a_pie_m} m a pie · ${it.transbordos} transbordo(s)</p></div>
    <div class="pf-legend"><div class="legend">
      <div class="row"><span class="sym"><span class="swatch" style="border-top:6px solid #009b3a;box-shadow:0 0 0 4px rgba(230,0,126,.25)"></span></span>Tramo en metro/autobús (color oficial de la línea, halo del itinerario)</div>
      <div class="row"><span class="sym"><span class="swatch" style="border-top:4px dotted #e6007e;width:30px"></span></span>Recorrido a pie (red peatonal OSM)</div>
      <div class="row"><span class="sym"><span class="mk mk-num" style="display:inline-grid">1</span></span>Transbordo · <span class="mk mk-exit" style="display:inline-block;margin-left:6px">Salida</span> acceso oficial</div>
      <div class="row"><span class="sym"><span class="mk-orig" style="display:inline-block;width:18px;height:18px"></span></span>Origen: Metro Carabanchel Alto · ★ destino: Juan Bravo, 35</div></div></div>
    <div class="pf-src">GTFS CRTM (Metro 20250527) y EMT (03/11/2026) · calles © OpenStreetMap (ODbL) vía Overture · portal CartoCiudad (IGN) · avisos a 05/11/2026 · orientativo, no en tiempo real.</div>`;
}
