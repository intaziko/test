import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Protocol } from "pmtiles";
import "@fontsource-variable/inter";
import "./style.css";
import { basemapLabelLayers, basemapLayers } from "./basemap.js";

const protocol = new Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile);

export const PARAMS = new URLSearchParams(location.search);
export const PRINT = PARAMS.get("print");               // "a3" → modo exportación (scripts/export.mjs)
const ROOT = new URL(import.meta.env.BASE_URL, location.href).href;
export const url = (p) => ROOT + p;
export const getJSON = (p) => fetch(url(p)).then((r) => { if (!r.ok) throw new Error(`${p}: ${r.status}`); return r.json(); });

export const ATTRIB = [
  "Red: GTFS © CRTM (Metro, Metro Ligero, Cercanías/Renfe) y © EMT Madrid",
  "Límites, calles y vías: © OpenStreetMap contributors (ODbL), vía Overture Maps; validado con IGN",
  "Portal Juan Bravo 35: CartoCiudad (IGN) vía OpenAddresses",
].join(" · ");

export const norm = (s) => String(s).normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/['’]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
export const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
export const NET_LABEL = { metro: "Metro", ml: "Metro Ligero", cercanias: "Cercanías" };

export function badge(line, color, text, net = "metro") {
  const white = color.toUpperCase() === "#FFFFFF";
  return `<span class="badge ${net}${white ? " white" : ""}" style="background:${color};color:${text};--b:${text}" title="${NET_LABEL[net] || ""} ${esc(line)}">${esc(line)}</span>`;
}

export function createMap(container, { bounds, maxBounds = [[-5.2, 39.6], [-2.6, 41.5]] } = {}) {
  const map = new maplibregl.Map({
    container,
    style: {
      version: 8,
      glyphs: ROOT + "fonts/{fontstack}/{range}.pbf",
      sources: { base: { type: "vector", url: "pmtiles://" + url("tiles/base.pmtiles"), attribution: "© OpenStreetMap contributors · Overture Maps" } },
      layers: basemapLayers(),
    },
    bounds, maxBounds, fitBoundsOptions: { padding: 30 },
    attributionControl: { compact: true, customAttribution: ATTRIB },
    pixelRatio: window.devicePixelRatio,  // en exportación = deviceScaleFactor de Playwright (3 → ~290 ppp en A3)
    canvasContextAttributes: { preserveDrawingBuffer: !!PRINT },
    fadeDuration: PRINT ? 0 : 300,
    dragRotate: false, pitchWithRotate: false, touchPitch: false,
  });
  map.touchZoomRotate.disableRotation();
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
  map.addControl(new maplibregl.ScaleControl({ unit: "metric", maxWidth: 150 }), "bottom-left");
  map.on("error", (e) => console.warn("MapLibre:", e.error?.message || e));
  map.once("load", () => document.querySelector(".maplibregl-ctrl-attrib")?.classList.remove("maplibregl-compact-show"));
  return map;
}

export function northArrow(el) {
  el.insertAdjacentHTML("beforeend", `<svg class="north" viewBox="0 0 40 52" aria-label="Norte">
    <circle cx="20" cy="31" r="17" fill="rgba(255,255,255,.9)" stroke="#4f4b45" stroke-width="1"/>
    <path d="M20 14 27 38 20 33 13 38z" fill="#1d1c1a"/><path d="M20 14 20 33 13 38z" fill="#85807a"/>
    <text x="20" y="11" text-anchor="middle" font-family="Inter Variable, sans-serif" font-size="11" font-weight="800" fill="#1d1c1a">N</text></svg>`);
}

/* ------------------------------------------------------------------ iconos (dibujados en canvas, sin sprites externos) */
function icon(map, id, size, draw) {
  const r = 2, c = document.createElement("canvas");
  c.width = c.height = size * r;
  const g = c.getContext("2d");
  g.scale(r, r);
  draw(g, size);
  map.addImage(id, g.getImageData(0, 0, size * r, size * r), { pixelRatio: r });
}
function addIcons(map) {
  const sq = (stroke, lw, s) => (g) => { g.fillStyle = "#fff"; g.strokeStyle = stroke; g.lineWidth = lw; g.beginPath(); g.roundRect(lw / 2 + 1, lw / 2 + 1, s - lw - 2, s - lw - 2, 3); g.fill(); g.stroke(); };
  icon(map, "cer", 14, sq("#3b3836", 2.4, 14));
  icon(map, "cer-tr", 18, sq("#000", 3.2, 18));
  icon(map, "closed", 18, (g) => { g.fillStyle = "#c9472b"; g.beginPath(); g.arc(9, 9, 8, 0, 7); g.fill(); g.strokeStyle = "#fff"; g.lineWidth = 2.4; g.beginPath(); g.moveTo(5.5, 5.5); g.lineTo(12.5, 12.5); g.moveTo(12.5, 5.5); g.lineTo(5.5, 12.5); g.stroke(); });
}

/* ------------------------------------------------------------------ capas de transporte (compartidas por los dos mapas) */
const zi = (...s) => ["interpolate", ["exponential", 1.4], ["zoom"], ...s];
// anchuras por zoom como paradas [zoom, px]; zw() aplica una función a cada parada (MapLibre exige el zoom en el nivel superior)
export const WS = { metro: [[8, 1.2], [11, 2.4], [14, 4.2], [17, 7.5]], ml: [[10, 1.1], [14, 3.2], [17, 5.5]], cer: [[8, 1.1], [11, 2.2], [14, 3.8], [17, 6.5]] };
export const zw = (stops, f = (w) => w) => ["interpolate", ["exponential", 1.4], ["zoom"], ...stops.flatMap(([z, w]) => [z, f(w)])];
export const W = { metro: zw(WS.metro), ml: zw(WS.ml), cer: zw(WS.cer) };

export async function addTransit(map, { dim = false, avisos = true } = {}) {
  const [lineas, andenes, enlaces, estaciones, av] = await Promise.all(
    ["lineas.geojson", "andenes.geojson", "enlaces.geojson", "estaciones.geojson", "avisos.geojson"].map((f) => getJSON("data/" + f)));
  for (const f of lineas.features) f.properties.key = `${f.properties.net}:${f.properties.line}`;
  for (const f of andenes.features) f.properties.key = `${f.properties.net}:${f.properties.line}`;
  map.addSource("lineas", { type: "geojson", data: lineas });
  map.addSource("andenes", { type: "geojson", data: andenes });
  map.addSource("enlaces", { type: "geojson", data: enlaces });
  map.addSource("estaciones", { type: "geojson", data: estaciones, promoteId: "id" });
  map.addSource("avisos", { type: "geojson", data: av });
  addIcons(map);
  const op = dim ? 0.28 : 1;
  const isWhite = ["==", ["get", "color"], "#FFFFFF"];
  const L = (id, filter, paint, layout = {}) => map.addLayer({ id, type: "line", source: "lineas", filter, layout: { "line-cap": "round", "line-join": "round", ...layout }, paint });
  // Cercanías: color oficial + traviesas blancas (simbología ferroviaria)
  L("cer-case", ["==", ["get", "net"], "cercanias"], { "line-color": "#ffffff", "line-width": zw(WS.cer, (w) => w + 2), "line-opacity": op });
  L("cer-line", ["==", ["get", "net"], "cercanias"], { "line-color": ["get", "color"], "line-width": W.cer, "line-opacity": op });
  L("cer-ties", ["==", ["get", "net"], "cercanias"], { "line-color": "#ffffff", "line-width": zi(10, 0.6, 14, 1.4, 17, 2.4), "line-dasharray": [1.2, 1.6], "line-opacity": op }, { "line-cap": "butt" });
  // Metro Ligero: doble línea (color + hilo blanco central)
  L("ml-case", ["==", ["get", "net"], "ml"], { "line-color": "#ffffff", "line-width": zw(WS.ml, (w) => w + 2), "line-opacity": op });
  L("ml-line", ["==", ["get", "net"], "ml"], { "line-color": ["get", "color"], "line-width": W.ml, "line-opacity": op });
  L("ml-center", ["==", ["get", "net"], "ml"], { "line-color": "#ffffff", "line-width": zi(10, 0.4, 14, 1, 17, 1.8), "line-opacity": op });
  // Metro: trazo continuo (el Ramal, blanco oficial, con borde azul)
  L("metro-case", ["==", ["get", "net"], "metro"], { "line-color": ["case", isWhite, ["get", "texto"], "#ffffff"], "line-width": zw(WS.metro, (w) => ["case", isWhite, w + 3, w + 2]), "line-opacity": op });
  L("metro-line", ["==", ["get", "net"], "metro"], { "line-color": ["get", "color"], "line-width": W.metro, "line-opacity": op });
  // avisos: tramos sin servicio o con cortes
  if (avisos) {
    map.addLayer({ id: "avisos-line", type: "line", source: "avisos", filter: ["==", ["geometry-type"], "LineString"],
      paint: { "line-color": ["match", ["get", "estado"], "vigente", "#c9472b", "#e39a2d"], "line-width": zi(9, 2, 14, 4, 17, 7), "line-dasharray": [1.2, 1.2], "line-opacity": 0.95, "line-offset": zi(9, 3, 14, 6, 17, 10) } });
  }
  // enlaces de transbordo
  map.addLayer({ id: "enlace-corr", type: "line", source: "enlaces", minzoom: 11.5, filter: ["==", ["get", "tipo"], "correspondencia"],
    paint: { "line-color": "#3b3836", "line-width": zi(12, 1, 16, 2.2), "line-dasharray": [1.5, 1.2], "line-opacity": op } });
  map.addLayer({ id: "enlace-pasillo-case", type: "line", source: "enlaces", minzoom: 11, filter: ["==", ["get", "tipo"], "pasillo"],
    layout: { "line-cap": "round" }, paint: { "line-color": "#1d1c1a", "line-width": zi(11, 6, 14, 11, 17, 17), "line-opacity": op } });
  map.addLayer({ id: "enlace-pasillo", type: "line", source: "enlaces", minzoom: 11, filter: ["==", ["get", "tipo"], "pasillo"],
    layout: { "line-cap": "round" }, paint: { "line-color": "#ffffff", "line-width": zi(11, 3, 14, 6.5, 17, 11), "line-opacity": op } });
  // andenes: Metro y ML círculos; Cercanías cuadrados; transbordos mayores con borde negro
  const C = (id, filter, r, stroke, sw, minzoom = 0) => map.addLayer({ id, type: "circle", source: "andenes", minzoom, filter,
    paint: { "circle-radius": r, "circle-color": "#ffffff", "circle-stroke-color": stroke, "circle-stroke-width": sw, "circle-opacity": op, "circle-stroke-opacity": op } });
  C("st-ml", ["all", ["==", ["get", "net"], "ml"], ["==", ["get", "transfer"], 0]], zi(10, 1.2, 13, 2.6, 16, 4.5), ["get", "color"], zi(10, 0.8, 14, 1.6), 10.5);
  C("st-metro", ["all", ["==", ["get", "net"], "metro"], ["==", ["get", "transfer"], 0]], zi(9, 1.3, 12, 2.6, 15, 4.6, 17, 6.5), ["case", ["==", ["get", "color"], "#FFFFFF"], "#005AA9", ["get", "color"]], zi(9, 0.8, 13, 1.8, 16, 2.6), 9);
  C("st-transfer", ["all", ["!=", ["get", "net"], "cercanias"], ["==", ["get", "transfer"], 1]], zi(8, 1.8, 11, 3.2, 14, 5.6, 17, 8.5), "#1d1c1a", zi(8, 1, 12, 2, 15, 3));
  map.addLayer({ id: "st-cer", type: "symbol", source: "andenes", filter: ["==", ["get", "net"], "cercanias"],
    layout: { "icon-image": ["case", ["==", ["get", "transfer"], 1], "cer-tr", "cer"], "icon-size": zi(8, 0.32, 10, 0.5, 12, 0.8, 14, 1.05, 17, 1.4), "icon-allow-overlap": true, "icon-ignore-placement": true },
    paint: { "icon-opacity": op } });
  if (avisos) map.addLayer({ id: "avisos-closed", type: "symbol", source: "avisos", filter: ["==", ["get", "estado"], "cerrada"],
    layout: { "icon-image": "closed", "icon-size": zi(10, 0.7, 15, 1.1), "icon-allow-overlap": true, "icon-ignore-placement": true } });
  return { lineas, andenes, enlaces, estaciones };
}

export function addStationLabels(map, { dim = false } = {}) {
  const base = {
    "text-field": ["get", "name"], "text-variable-anchor": ["left", "right", "top", "bottom", "top-left", "bottom-right"],
    "text-radial-offset": 0.85, "text-justify": "auto", "text-max-width": 9, "text-padding": 2, "symbol-sort-key": ["-", 10, ["get", "rank"]],
  };
  const paint = { "text-color": dim ? "#8f8880" : "#1d1c1a", "text-halo-color": "rgba(255,255,255,.95)", "text-halo-width": 1.6, "text-halo-blur": 0.3 };
  const lay = (id, minzoom, filter, font, size) => map.addLayer({ id, type: "symbol", source: "estaciones", minzoom, filter,
    layout: { ...base, "text-font": [font], "text-size": size }, paint });
  const one = ["!=", ["get", "nolbl"], 1];
  lay("lbl-st-1", 13.4, ["all", one, ["<", ["get", "rank"], 2]], "Noto Sans Regular", zi(13.4, 10.5, 17, 13));
  lay("lbl-st-2", 12.2, ["all", one, ["==", ["get", "rank"], 2]], "Noto Sans Medium", zi(12, 10.5, 16, 13));
  lay("lbl-st-3", 10.6, ["all", one, [">=", ["get", "rank"], 3]], "Noto Sans Medium", zi(10.5, 10.5, 15, 13.5));
}

export function wireSourcesDialog(btn) {
  const dlg = document.getElementById("fuentes");
  btn?.addEventListener("click", () => dlg.showModal());
  dlg?.querySelector(".x")?.addEventListener("click", () => dlg.close());
}

export const ready = (map) => new Promise((res) => (map.loaded() ? res() : map.once("load", res)));
export function whenIdle(map) {
  return new Promise((res) => map.once("idle", res));
}
export { maplibregl };
