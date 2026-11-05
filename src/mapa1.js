import { addStationLabels, addTransit, badge, createMap, esc, getJSON, maplibregl, NET_LABEL, norm, northArrow, PARAMS, PRINT, WS, zw } from "./common.js";
import { basemapLabelLayers } from "./basemap.js";
import { renderSources } from "./sources.js";

const VIEW_METRO = [[-3.935, 40.262], [-3.405, 40.590]];     // Madrid + Alcobendas, Torrejón, Getafe y Móstoles
const VIEW_ALL = [[-4.58, 39.88], [-3.05, 41.17]];           // Comunidad de Madrid
const VIEW_CENTRO = [[-3.745, 40.383], [-3.640, 40.465]];    // almendra central (exportación de detalle)
const PAL = ["#ead9c2", "#d5e4cc", "#d6dcec", "#ecd8e2", "#e6e2c3", "#cfe4e3"];
const zi = (...s) => ["interpolate", ["exponential", 1.4], ["zoom"], ...s];

const map = createMap("map", { bounds: PRINT === "a3-centro" ? VIEW_CENTRO : PRINT ? [[-3.95, 40.255], [-3.39, 40.60]] : VIEW_METRO });
northArrow(document.querySelector(".map"));
const [red, mun, dist, etq, cam, avisos, fuentes] = await Promise.all(
  ["red.json", "municipios.geojson", "distritos.geojson", "etiquetas_admin.geojson", "comunidad.geojson", "avisos.json", "fuentes.json"].map((f) => getJSON("data/" + f)));
const LINES = red.lineas, EST = red.estaciones;
renderSources(document.getElementById("fuentes-c"), fuentes, avisos);
document.getElementById("btn-fuentes").onclick = () => document.getElementById("fuentes").showModal();
document.querySelector("#fuentes .x").onclick = () => document.getElementById("fuentes").close();

const state = { hidden: new Set(), sel: [], chipMode: "sel", hiddenLayers: new Set() };
const lineKeyOfStation = (sid) => EST[sid].lineas.map((l) => `${EST[sid].red}:${l}`);

map.on("load", async () => {
  // ---- límites administrativos (bajo el viario)
  map.addSource("municipios", { type: "geojson", data: mun });
  map.addSource("distritos", { type: "geojson", data: dist });
  map.addSource("comunidad", { type: "geojson", data: cam });
  map.addSource("etq", { type: "geojson", data: etq });
  map.addSource("hl", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
  map.addLayer({ id: "dist-fill", type: "fill", source: "distritos",
    paint: { "fill-color": ["match", ["get", "color"], 0, PAL[0], 1, PAL[1], 2, PAL[2], 3, PAL[3], 4, PAL[4], PAL[5]],
      "fill-opacity": ["interpolate", ["linear"], ["zoom"], 8, 0.35, 12, 0.5, 14.5, 0.32, 16.5, 0.12] } }, "aeroway");
  map.addLayer({ id: "mun-foco", type: "fill", source: "municipios", filter: ["all", ["==", ["get", "foco"], 1], ["!=", ["get", "nombre"], "Madrid"]],
    paint: { "fill-color": "#efe0c9", "fill-opacity": ["interpolate", ["linear"], ["zoom"], 8, 0.55, 13, 0.3, 15, 0] } }, "aeroway");
  map.addLayer({ id: "dist-line", type: "line", source: "distritos", paint: { "line-color": "#9d8f80", "line-width": zi(9, 0.5, 13, 1.3, 16, 2), "line-opacity": 0.85 } });
  map.addLayer({ id: "mun-line", type: "line", source: "municipios", paint: { "line-color": "#857e74", "line-width": zi(7, 0.5, 12, 1.2, 16, 1.8), "line-dasharray": [3, 2] } });
  map.addLayer({ id: "cam-line", type: "line", source: "comunidad", paint: { "line-color": "#4f4a43", "line-width": zi(6, 1.2, 12, 2.6), "line-dasharray": [5, 2, 1, 2] } });
  for (const l of basemapLabelLayers()) map.addLayer(l);

  // ---- red de transporte
  await addTransit(map);
  map.addLayer({ id: "hl-poly", type: "line", source: "hl", filter: ["==", ["geometry-type"], "Polygon"], paint: { "line-color": "#b8003c", "line-width": 3 } });
  map.addLayer({ id: "hl-poly2", type: "line", source: "hl", filter: ["==", ["geometry-type"], "MultiPolygon"], paint: { "line-color": "#b8003c", "line-width": 3 } });
  map.addLayer({ id: "hl-pt", type: "circle", source: "hl", filter: ["==", ["geometry-type"], "Point"],
    paint: { "circle-radius": 16, "circle-color": "rgba(184,0,60,.12)", "circle-stroke-color": "#b8003c", "circle-stroke-width": 2.5 } });

  // ---- etiquetas: municipios y distritos (posiciones calculadas lejos de las líneas), estaciones
  const halo = { "text-halo-color": "rgba(255,255,255,.92)", "text-halo-width": 1.8 };
  const munLbl = (id, filter, minzoom, maxzoom, size, font, color, extra = {}) => map.addLayer({ id, type: "symbol", source: "etq", minzoom, maxzoom,
    filter: ["all", ["==", ["get", "tipo"], "municipio"], filter],
    layout: { "text-field": ["get", "nombre"], "text-font": [font], "text-size": size, "text-max-width": 8, "text-padding": 4, "symbol-sort-key": ["get", "rank"], ...extra },
    paint: { "text-color": color, ...halo } });
  munLbl("lbl-mun-3", ["all", ["==", ["get", "foco"], 0], ["==", ["get", "rank"], 3]], 10.4, 22, 10.5, "Noto Sans Regular", "#6f685f");
  munLbl("lbl-mun-2", ["all", ["==", ["get", "foco"], 0], ["==", ["get", "rank"], 2]], 9.3, 22, zi(9, 10, 12, 12), "Noto Sans Regular", "#5f5951");
  munLbl("lbl-mun-1", ["all", ["==", ["get", "foco"], 0], ["==", ["get", "rank"], 1]], 8, 22, zi(8, 10.5, 12, 13), "Noto Sans Medium", "#4f4a43");
  munLbl("lbl-mun-foco", ["all", ["==", ["get", "foco"], 1], [">", ["get", "rank"], 0]], 7, 22, zi(7, 11.5, 12, 15), "Noto Sans Medium", "#2f2a25", { "text-transform": "uppercase", "text-letter-spacing": 0.08 });
  munLbl("lbl-madrid", ["all", ["==", ["get", "rank"], 0], PRINT === "a3" ? ["==", ["get", "alt"], 1] : ["!=", ["get", "alt"], 1]], 5, PRINT === "a3" ? 24 : 10.45, zi(6, 15, 10, 26), "Noto Sans Medium", "#3d3832", { "text-field": "MADRID", "text-letter-spacing": 0.25 });
  map.addLayer({ id: "lbl-dist", type: "symbol", source: "etq", minzoom: 10.45, maxzoom: 15.6, filter: ["==", ["get", "tipo"], "distrito"],
    layout: { "text-field": ["upcase", ["get", "nombre"]], "text-font": ["Noto Sans Medium"], "text-size": zi(10.45, 9.5, 13, 12.5, 15, 14),
      "text-letter-spacing": 0.14, "text-max-width": 7, "text-padding": 6, "symbol-sort-key": 1 },
    paint: { "text-color": "#86735d", ...halo, "text-opacity": ["interpolate", ["linear"], ["zoom"], 10.45, 0.4, 10.9, 1, 15, 1, 15.5, 0] } });
  addStationLabels(map);
  // prioridad de rotulación (MapLibre coloca primero las capas superiores): municipios destacados y distritos
  for (const id of ["lbl-dist", "lbl-mun-foco", "lbl-madrid"]) map.moveLayer(id);

  buildChips();
  buildAvisos();
  wireUI();
  applyFilters();
  if (PRINT) printFrame();
  window.__map = map;
  map.once("idle", () => { window.__READY = true; });
});

/* ------------------------------------------------------------------ filtros: visibilidad y resaltado */
const TRANSIT_LINE_LAYERS = ["cer-case", "cer-line", "cer-ties", "ml-case", "ml-line", "ml-center", "metro-case", "metro-line"];
const STOP_LAYERS = ["st-ml", "st-metro", "st-transfer", "st-cer"];
const BASE_FILTER = {};

function applyFilters() {
  const hidden = ["literal", [...state.hidden]];
  for (const id of [...TRANSIT_LINE_LAYERS, ...STOP_LAYERS]) {
    BASE_FILTER[id] ??= map.getFilter(id);
    map.setFilter(id, ["all", BASE_FILTER[id], ["!", ["in", ["get", "key"], hidden]]]);
  }
  // estaciones visibles: alguna de sus líneas visible
  const vis = Object.keys(EST).filter((k) => lineKeyOfStation(k).some((x) => !state.hidden.has(x)));
  for (const id of ["lbl-st-1", "lbl-st-2", "lbl-st-3"]) {
    BASE_FILTER[id] ??= map.getFilter(id);
    map.setFilter(id, ["all", BASE_FILTER[id], ["in", ["get", "id"], ["literal", vis]]]);
  }
  for (const id of ["enlace-pasillo", "enlace-pasillo-case", "enlace-corr"]) {
    BASE_FILTER[id] ??= map.getFilter(id);
    map.setFilter(id, ["all", BASE_FILTER[id], ["in", ["get", "a"], ["literal", vis]], ["in", ["get", "b"], ["literal", vis]]]);
  }
  // resaltado
  const sel = state.sel, on = ["in", ["get", "key"], ["literal", sel]];
  const fade = (a, b = 0.13) => (sel.length ? ["case", on, a, b] : a);
  for (const id of TRANSIT_LINE_LAYERS) map.setPaintProperty(id, "line-opacity", fade(1));
  const white = ["==", ["get", "color"], "#FFFFFF"];
  for (const [net, st] of [["metro", WS.metro], ["ml", WS.ml], ["cer", WS.cer]]) {
    map.setPaintProperty(`${net}-line`, "line-width", zw(st, (w) => (sel.length ? ["case", on, w * 1.7, w] : w)));
    map.setPaintProperty(`${net}-case`, "line-width", zw(st, (w) => {
      const base = net === "metro" ? ["case", white, w + 3, w + 2] : w + 2;
      return sel.length ? ["case", on, w * 1.7 + 3, base] : base;
    }));
  }
  for (const id of ["st-ml", "st-metro", "st-transfer"]) {
    map.setPaintProperty(id, "circle-opacity", fade(1, 0.25));
    map.setPaintProperty(id, "circle-stroke-opacity", fade(1, 0.25));
  }
  map.setPaintProperty("st-cer", "icon-opacity", fade(1, 0.25));
  const selSt = sel.length ? Object.keys(EST).filter((k) => lineKeyOfStation(k).some((x) => sel.includes(x))) : null;
  for (const id of ["lbl-st-1", "lbl-st-2", "lbl-st-3"]) map.setPaintProperty(id, "text-opacity", selSt ? ["case", ["in", ["get", "id"], ["literal", selSt]], 1, 0.25] : 1);
  document.querySelectorAll(".chip").forEach((c) => {
    c.classList.toggle("off", state.hidden.has(c.dataset.key));
    c.classList.toggle("sel", sel.includes(c.dataset.key));
  });
  for (const [layer, ids] of Object.entries({ distritos: ["dist-fill", "dist-line", "lbl-dist"], municipios: ["mun-line", "mun-foco"], avisos: ["avisos-line", "avisos-closed"] }))
    for (const id of ids) map.setLayoutProperty(id, "visibility", state.hiddenLayers.has(layer) ? "none" : "visible");
}

/* ------------------------------------------------------------------ panel lateral */
function buildChips() {
  const box = document.getElementById("chips");
  const byNet = {};
  for (const [k, l] of Object.entries(LINES)) (byNet[l.net] ??= []).push([k, l]);
  box.innerHTML = Object.entries(byNet).map(([net, ls]) => `
    <div class="netlabel"><span>${NET_LABEL[net]}</span><button class="linkbtn" data-all="${net}">todas / ninguna</button></div>
    <div class="chips">${ls.map(([k, l]) => `<button class="chip" data-key="${k}" title="${esc(l.nombre)}" style="background:${l.color};color:${l.texto};${l.color === "#FFFFFF" ? `box-shadow:inset 0 0 0 2px ${l.texto}` : ""}">${esc(l.id)}</button>`).join("")}</div>`).join("");
  box.addEventListener("click", (e) => {
    const chip = e.target.closest(".chip"), all = e.target.closest("[data-all]");
    if (all) {
      const keys = Object.keys(LINES).filter((k) => LINES[k].net === all.dataset.all);
      const anyOn = keys.some((k) => !state.hidden.has(k));
      keys.forEach((k) => (anyOn ? state.hidden.add(k) : state.hidden.delete(k)));
      document.querySelector(`[data-net="${all.dataset.all}"]`).checked = !anyOn;
      return applyFilters();
    }
    if (!chip) return;
    const k = chip.dataset.key;
    if (state.chipMode === "vis") { state.hidden.has(k) ? state.hidden.delete(k) : state.hidden.add(k); applyFilters(); }
    else showLine(k);
  });
}

function buildAvisos() {
  document.getElementById("avisos").innerHTML = avisos.avisos.map((a) => `<div class="aviso ${a.estado}"><b>${esc(a.titulo)}</b>${esc(a.detalle)}
    <div>${a.fuentes.map((f) => `<a href="${f.url}" target="_blank" rel="noopener">${esc(f.titulo)}</a>`).join(" · ")}</div></div>`).join("") +
    `<p class="muted">${esc(avisos.nota)}</p>`;
}

function wireUI() {
  document.getElementById("toggles").addEventListener("change", (e) => {
    const t = e.target;
    if (t.dataset.net) {
      Object.keys(LINES).filter((k) => LINES[k].net === t.dataset.net).forEach((k) => (t.checked ? state.hidden.delete(k) : state.hidden.add(k)));
    } else if (t.dataset.layer) t.checked ? state.hiddenLayers.delete(t.dataset.layer) : state.hiddenLayers.add(t.dataset.layer);
    applyFilters();
  });
  document.getElementById("chipmode").addEventListener("click", (e) => {
    const b = e.target.closest(".mode"); if (!b) return;
    state.chipMode = b.dataset.m;
    document.querySelectorAll("#chipmode .mode").forEach((x) => x.setAttribute("aria-pressed", x === b));
  });
  document.getElementById("btn-madrid").onclick = () => fitBbox(mun.features.find((f) => f.properties.nombre === "Madrid").properties.bbox);
  document.getElementById("btn-all").onclick = () => { map.fitBounds(VIEW_ALL, { padding: 20 }); };
  document.getElementById("info-x").onclick = closeInfo;
  document.getElementById("sidetoggle").onclick = () => document.getElementById("side").classList.toggle("collapsed");
  if (matchMedia("(max-width: 860px)").matches) document.getElementById("side").classList.add("collapsed");

  // clic en el mapa: estación > línea > distrito/municipio
  const clickable = ["st-transfer", "st-metro", "st-ml", "st-cer", "lbl-st-1", "lbl-st-2", "lbl-st-3", "enlace-pasillo"];
  map.on("click", (e) => {
    const box = [[e.point.x - 6, e.point.y - 6], [e.point.x + 6, e.point.y + 6]];
    const st = map.queryRenderedFeatures(box, { layers: clickable })[0];
    if (st) return showStation(st.properties.sid || st.properties.id || st.properties.a);
    const ln = map.queryRenderedFeatures(box, { layers: ["metro-line", "ml-line", "cer-line"] })[0];
    if (ln) return showLine(ln.properties.key);
    const d = map.queryRenderedFeatures(e.point, { layers: ["dist-fill"] })[0];
    const m = map.queryRenderedFeatures(e.point, { layers: ["mun-line"] }).length ? null : null;
    if (d && map.getZoom() > 9.5) return showArea("distrito", d.properties.nombre);
    const mm = mun.features.find((f) => turfInside([e.lngLat.lng, e.lngLat.lat], f));
    if (mm && !m) return showArea("municipio", mm.properties.nombre);
    state.sel = []; applyFilters(); closeInfo();
  });
  for (const id of [...clickable, "metro-line", "ml-line", "cer-line"]) {
    map.on("mouseenter", id, () => (map.getCanvas().style.cursor = "pointer"));
    map.on("mouseleave", id, () => (map.getCanvas().style.cursor = ""));
  }
  setupSearch();
}

/* ------------------------------------------------------------------ información */
const info = document.getElementById("info"), infoC = document.getElementById("info-c");
function openInfo(html) { infoC.innerHTML = html; info.classList.add("open"); info.scrollTop = 0; }
function closeInfo() { info.classList.remove("open"); setHL(null); }
const lb = (net, l) => { const L = LINES[`${net}:${l}`]; return L ? badge(l, L.color, L.texto, net) : esc(l); };

function showStation(sid) {
  const s = EST[sid]; if (!s) return;
  const corr = s.correspondencias.map((c) => EST[c]);
  const keys = [...lineKeyOfStation(sid), ...s.correspondencias.flatMap(lineKeyOfStation)];
  state.sel = keys; applyFilters();
  setHL({ type: "Point", coordinates: s.coord });
  const ntr = keys.length;
  const dirs = Object.entries(s.vecinas).map(([l, arr]) => `<li>${lb(s.red, l)}<div>${arr.map((d) => `hacia <b>${esc(d.hacia)}</b>: siguiente <a href="#" data-st="${d.id}">${esc(d.siguiente)}</a>`).join("<br>")}</div></li>`).join("");
  openInfo(`<header><h3>${esc(s.nombre)}</h3><div class="sub">${NET_LABEL[s.red]}${s.grupo ? " · " + esc(s.grupo) : ""}</div></header>
  <div class="body">
    <dl class="kv"><dt>Líneas</dt><dd>${s.lineas.map((l) => lb(s.red, l)).join(" ")}</dd>
    <dt>${s.distrito ? "Distrito" : "Municipio"}</dt><dd>${esc(s.distrito ? `${s.distrito} (Madrid)` : s.municipio || "—")}</dd>
    <dt>Transbordo</dt><dd>${ntr >= 2 ? `<span class="tag ok">Sí · ${ntr} líneas</span>` : `<span class="tag">No</span>`}</dd></dl>
    ${corr.length ? `<h2 style="margin:14px 0 6px;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3)">Correspondencias</h2>
      ${corr.map((c) => `<div style="margin-bottom:6px"><a href="#" data-st="${s.correspondencias[corr.indexOf(c)]}">${esc(c.nombre)}</a> <span class="muted">(${NET_LABEL[c.red]})</span> ${c.lineas.map((l) => lb(c.red, l)).join(" ")}</div>`).join("")}` : ""}
    <h2 style="margin:14px 0 6px;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3)">Estaciones anterior y siguiente</h2>
    <ul class="dirs">${dirs}</ul>
    ${s.accesos.length ? `<details style="margin-top:12px"><summary class="small">Accesos oficiales (${s.accesos.length})</summary><ul class="small">${s.accesos.map((a) => `<li>${esc(a.nombre)} · <span class="muted">${esc(a.dir)}</span></li>`).join("")}</ul></details>` : ""}
    <p class="muted" style="margin-top:12px">Nombre oficial GTFS: ${esc(s.nombre_gtfs)} · coordenadas ${s.coord[1].toFixed(5)}, ${s.coord[0].toFixed(5)}</p>
  </div>`);
}

function showLine(key) {
  const L = LINES[key]; if (!L) return;
  state.sel = [key]; applyFilters();
  const coords = map.querySourceFeatures("lineas", { filter: ["==", ["get", "key"], key] }).flatMap((f) => f.geometry.type === "LineString" ? f.geometry.coordinates : f.geometry.coordinates.flat());
  if (coords.length) { const b = coords.reduce((b, c) => b.extend(c), new maplibregl.LngLatBounds(coords[0], coords[0])); map.fitBounds(b, { padding: { top: 40, bottom: 40, left: 40, right: info.offsetWidth ? 400 : 40 }, maxZoom: 14 }); }
  const st = (sid) => { const s = EST[sid]; const others = [...s.lineas.filter((l) => l !== L.id).map((l) => lb(s.red, l)), ...s.correspondencias.flatMap((c) => EST[c].lineas.map((l) => lb(EST[c].red, l)))];
    return `<li class="${others.length ? "tr" : ""}" data-st="${sid}">${esc(s.nombre)}${others.length ? `<span class="mini">${others.join(" ")}</span>` : ""}</li>`; };
  const av = avisos.avisos.filter((a) => a.red === L.net && a.linea === L.id);
  openInfo(`<header><h3>${lb(L.net, L.id)} ${esc(L.nombre)}</h3><div class="sub">${NET_LABEL[L.net]} · ${L.estaciones.length} estaciones · ${L.km} km de trazado${L.circular ? " · circular" : ""}</div></header>
  <div class="body">
    ${av.map((a) => `<div class="aviso ${a.estado}"><b>${esc(a.titulo)}</b>${esc(a.detalle)}</div>`).join("")}
    ${L.id === "3" ? `<div class="note warn">El GTFS de Metro del CRTM (versión 20250527) no publica viajes ni trazado de la L3. Estaciones oficiales del CRTM + prolongación a El Casar (abierta el 21/04/2025); trazado tomado de las vías de OSM rotuladas «Línea 3».</div>` : ""}
    ${L.viajes_autobus ? `<div class="note warn">${L.viajes_autobus} servicios de esta línea figuran en el GTFS como autobús (route_type 3).</div>` : ""}
    <ul class="stlist" style="--c:${L.color === "#FFFFFF" ? L.texto : L.color}">${L.estaciones.map(st).join("")}</ul>
    ${L.otros_servicios.length ? `<details style="margin-top:10px"><summary class="small">Otros servicios de la línea (${L.otros_servicios.length})</summary>${L.otros_servicios.map((s) => `<p class="small">${s.map(esc).join(" → ")}</p>`).join("")}</details>` : ""}
    <p class="muted">Nombre en el GTFS: ${esc(L.fuente_nombre)}</p>
    <button class="mapbtn" id="hide-line">Ocultar esta línea</button>
  </div>`);
  document.getElementById("hide-line").onclick = () => { state.hidden.add(key); state.sel = []; applyFilters(); closeInfo(); };
}

function showArea(kind, name) {
  const src = kind === "distrito" ? dist : mun;
  const f = src.features.find((x) => x.properties.nombre === name);
  setHL(f.geometry);
  state.sel = []; applyFilters();
  const inside = Object.entries(EST).filter(([, s]) => (kind === "distrito" ? s.distrito === name : s.municipio === name));
  const byNet = {};
  for (const [k, s] of inside) (byNet[s.red] ??= []).push([k, s]);
  openInfo(`<header><h3>${esc(name)}</h3><div class="sub">${kind === "distrito" ? `Distrito ${f.properties.codigo} de Madrid` : `Municipio · código INE ${f.properties.ine}`} · ${f.properties.area_km2.toLocaleString("es")} km²</div></header>
  <div class="body">${inside.length ? Object.entries(byNet).map(([net, arr]) => `<p><b>${NET_LABEL[net]}</b> (${arr.length} estaciones)<br>${arr.sort((a, b) => a[1].nombre.localeCompare(b[1].nombre, "es"))
      .map(([k, s]) => `<a href="#" data-st="${k}">${esc(s.nombre)}</a>`).join(" · ")}</p>`).join("") : `<p class="muted">Sin estaciones de Metro, Metro Ligero ni Cercanías.</p>`}</div>`);
  fitBbox(f.properties.bbox);
}

infoC.addEventListener("click", (e) => {
  const a = e.target.closest("[data-st]"); if (!a) return;
  e.preventDefault();
  const s = EST[a.dataset.st];
  map.flyTo({ center: s.coord, zoom: Math.max(map.getZoom(), 14.5) });
  showStation(a.dataset.st);
});

function setHL(geom) { map.getSource("hl")?.setData({ type: "FeatureCollection", features: geom ? [{ type: "Feature", geometry: geom, properties: {} }] : [] }); }
function fitBbox(b) { const [x1, y1, x2, y2] = String(b).split(",").map(Number); map.fitBounds([[x1, y1], [x2, y2]], { padding: 50 }); }
function turfInside(pt, f) {
  const polys = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
  const inRing = (r) => { let c = false; for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const [xi, yi] = r[i], [xj, yj] = r[j]; if ((yi > pt[1]) !== (yj > pt[1]) && pt[0] < ((xj - xi) * (pt[1] - yi)) / (yj - yi) + xi) c = !c; } return c; };
  return polys.some((p) => inRing(p[0]) && !p.slice(1).some(inRing));
}

/* ------------------------------------------------------------------ buscador */
function setupSearch() {
  const items = [
    ...Object.entries(EST).map(([k, s]) => ({ t: "est", k, name: s.nombre, n: norm(s.nombre), extra: s.lineas.map((l) => lb(s.red, l)).join(" "), kind: `Estación · ${NET_LABEL[s.red]}` })),
    ...mun.features.map((f) => ({ t: "mun", name: f.properties.nombre, n: norm(f.properties.nombre), kind: "Municipio" })),
    ...dist.features.map((f) => ({ t: "dist", name: f.properties.nombre, n: norm(f.properties.nombre), kind: "Distrito de Madrid" })),
  ];
  const q = document.getElementById("q"), res = document.getElementById("results");
  let list = [], idx = 0;
  const go = (it) => {
    res.innerHTML = ""; q.value = it.name;
    if (it.t === "est") { map.flyTo({ center: EST[it.k].coord, zoom: 15 }); showStation(it.k); }
    else showArea(it.t === "dist" ? "distrito" : "municipio", it.name);
  };
  q.addEventListener("input", () => {
    const v = norm(q.value);
    if (!v) { res.innerHTML = ""; return; }
    const toks = v.split(" ");
    list = items.filter((it) => toks.every((t) => it.n.includes(t)))
      .sort((a, b) => (b.n.startsWith(v) - a.n.startsWith(v)) || ((a.t !== "est") - (b.t !== "est")) || a.name.localeCompare(b.name, "es")).slice(0, 12);
    idx = 0;
    res.innerHTML = list.length ? list.map((it, i) => `<div class="result${i === 0 ? " active" : ""}" data-i="${i}" role="option"><span>${esc(it.name)}</span>${it.extra || ""}<span class="kind">${it.kind}</span></div>`).join("")
      : `<div class="result muted">Sin resultados</div>`;
  });
  q.addEventListener("keydown", (e) => {
    if (!list.length) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") { idx = (idx + (e.key === "ArrowDown" ? 1 : list.length - 1)) % list.length; res.querySelectorAll(".result").forEach((r, i) => r.classList.toggle("active", i === idx)); e.preventDefault(); }
    if (e.key === "Enter") go(list[idx]);
    if (e.key === "Escape") res.innerHTML = "";
  });
  res.addEventListener("click", (e) => { const r = e.target.closest("[data-i]"); if (r) go(list[+r.dataset.i]); });
  if (PARAMS.get("q")) { q.value = PARAMS.get("q"); q.dispatchEvent(new Event("input")); if (list[0]) go(list[0]); }
}

/* ------------------------------------------------------------------ marco de impresión (exportación A3) */
function printFrame() {
  document.body.classList.add("print");
  map.resize();
  // encuadre de impresión: la leyenda ocupa la franja izquierda, así que el mapa se centra en el resto
  const centro = PRINT === "a3-centro";
  map.fitBounds(centro ? VIEW_CENTRO : [[-3.93, 40.255], [-3.40, 40.60]], { padding: { top: 40, bottom: 40, left: centro ? 40 : 520, right: 40 }, duration: 0 });
  if (!centro) { map.setLayerZoomRange("lbl-st-3", 9.4, 24); map.setLayerZoomRange("lbl-st-2", 10.2, 24); map.setLayerZoomRange("lbl-dist", 9.5, 24); map.setPaintProperty("lbl-dist", "text-opacity", 0.95);
    map.setLayoutProperty("lbl-dist", "text-allow-overlap", true); }  // los 21 distritos siempre rotulados en el A3 general
  else map.setLayerZoomRange("lbl-st-1", 12.3, 24);
  const chips = (net) => Object.entries(LINES).filter(([, l]) => l.net === net)
    .map(([, l]) => `<span class="chip" style="background:${l.color};color:${l.texto};${l.color === "#FFFFFF" ? `box-shadow:inset 0 0 0 2px ${l.texto}` : ""}">${esc(l.id)}</span>`).join("");
  document.getElementById("printframe").innerHTML = `
    <div class="pf-title"><h1>${PRINT === "a3-centro" ? "Madrid centro · red de Metro, Metro Ligero y Cercanías" : "Madrid y área metropolitana · red de transporte ferroviario"}</h1>
      <p>Trazados y estaciones en su posición geográfica real · 21 distritos de Madrid · límites municipales${PRINT === "a3-centro" ? "" : " · Alcobendas, Torrejón de Ardoz, Getafe y Móstoles destacados"}</p></div>
    <div class="pf-legend">
      <div class="netlabel" style="margin-top:0">Metro de Madrid</div><div class="chips">${chips("metro")}</div>
      <div class="netlabel">Metro Ligero / Tranvía</div><div class="chips">${chips("ml")}</div>
      <div class="netlabel">Cercanías Madrid</div><div class="chips">${chips("cercanias")}</div>
      <div class="legend" style="grid-template-columns:1fr 1fr;margin-top:10px">${document.getElementById("legend").innerHTML}</div>
    </div>
    <div class="pf-src">Datos: GTFS CRTM (Metro 20250527, Metro Ligero 20261015, Cercanías 19/10/2026) · límites y calles © OpenStreetMap (ODbL) vía Overture Maps 2026-10-21, validados con IGN · L3 reconstruida (ver documentación) · Avisos a 05/11/2026 · Proyección Web Mercator, escala gráfica válida en el centro.</div>`;
}
