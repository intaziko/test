// Estilo del mapa base propio (public/tiles/base.pmtiles, OSM vía Overture). Fondo claro y discreto para
// que la cartografía de transporte sea la protagonista.
export const C = {
  bg: "#f4f2ee", water: "#bcd6e8", waterLine: "#a9c9df", park: "#dcead2", protected: "#e7efdd",
  cemetery: "#e2e6da", institutional: "#efe8e1", industrial: "#ecebe7", plaza: "#fbfaf8",
  road: "#ffffff", roadCase: "#dcd7cf", major: "#fffdf8", majorCase: "#d2ccc2", motorway: "#fdf6e8",
  motorwayCase: "#cfc5b3", rail: "#c9c3b9", building: "#e7e3dc", buildingLine: "#d9d3ca", label: "#6f685f",
};

const z = (...stops) => ["interpolate", ["exponential", 1.5], ["zoom"], ...stops];
const cls = (...v) => ["match", ["get", "clase"], v, true, false];

export function basemapLayers() {
  const S = "base";
  return [
    { id: "bg", type: "background", paint: { "background-color": C.bg } },
    { id: "landuse-protected", type: "fill", source: S, "source-layer": "landuse", filter: cls("protected"), paint: { "fill-color": C.protected, "fill-opacity": 0.7 } },
    { id: "landuse-industrial", type: "fill", source: S, "source-layer": "landuse", filter: cls("industrial"), paint: { "fill-color": C.industrial } },
    { id: "landuse-institutional", type: "fill", source: S, "source-layer": "landuse", filter: cls("institutional"), paint: { "fill-color": C.institutional } },
    { id: "landuse-cemetery", type: "fill", source: S, "source-layer": "landuse", filter: cls("cemetery"), paint: { "fill-color": C.cemetery } },
    { id: "landuse-park", type: "fill", source: S, "source-layer": "landuse", filter: cls("park"), paint: { "fill-color": C.park } },
    { id: "landuse-plaza", type: "fill", source: S, "source-layer": "landuse", filter: cls("plaza"), paint: { "fill-color": C.plaza } },
    { id: "aeroway", type: "line", source: S, "source-layer": "aeroway", filter: cls("runway", "taxiway"),
      paint: { "line-color": "#dedad3", "line-width": z(9, ["match", ["get", "clase"], "runway", 1.5, 0], 13, ["match", ["get", "clase"], "runway", 12, 1], 16, ["match", ["get", "clase"], "runway", 60, 10]) } },
    { id: "water", type: "fill", source: S, "source-layer": "water", paint: { "fill-color": C.water } },
    { id: "waterway", type: "line", source: S, "source-layer": "waterway", paint: { "line-color": C.waterLine,
      "line-width": z(8, ["match", ["get", "clase"], "river", 0.8, 0.2], 13, ["match", ["get", "clase"], "river", 2.5, 0.6], 16, ["match", ["get", "clase"], "river", 6, 1.5]) } },
    { id: "buildings", type: "fill", source: S, "source-layer": "buildings", minzoom: 14,
      paint: { "fill-color": C.building, "fill-outline-color": C.buildingLine, "fill-opacity": ["interpolate", ["linear"], ["zoom"], 14, 0, 15, 1] } },
    // viario: carcasa + relleno, de menor a mayor jerarquía
    { id: "road-path", type: "line", source: S, "source-layer": "roads", minzoom: 15, filter: cls("footway", "path", "steps", "cycleway", "pedestrian", "track"),
      paint: { "line-color": "#d8d2c8", "line-width": z(15, 0.6, 18, 1.6), "line-dasharray": [2, 1.5] } },
    { id: "road-minor-case", type: "line", source: S, "source-layer": "roads", minzoom: 13, filter: cls("residential", "living_street", "unclassified", "service"),
      layout: { "line-cap": "round", "line-join": "round" }, paint: { "line-color": C.roadCase, "line-width": z(13, 1.2, 16, 9, 18, 22) } },
    { id: "road-minor", type: "line", source: S, "source-layer": "roads", minzoom: 13, filter: cls("residential", "living_street", "unclassified", "service"),
      layout: { "line-cap": "round", "line-join": "round" }, paint: { "line-color": C.road, "line-width": z(13, 0.6, 16, 7.5, 18, 20) } },
    { id: "road-major-case", type: "line", source: S, "source-layer": "roads", filter: cls("primary", "secondary", "tertiary"),
      layout: { "line-cap": "round", "line-join": "round" }, paint: { "line-color": C.majorCase, "line-width": z(8, 0.6, 12, 2.4, 16, 14, 18, 30) } },
    { id: "road-major", type: "line", source: S, "source-layer": "roads", filter: cls("primary", "secondary", "tertiary"),
      layout: { "line-cap": "round", "line-join": "round" }, paint: { "line-color": C.major, "line-width": z(8, 0.3, 12, 1.6, 16, 12, 18, 27) } },
    { id: "road-motorway-case", type: "line", source: S, "source-layer": "roads", filter: cls("motorway", "trunk"),
      layout: { "line-cap": "round", "line-join": "round" }, paint: { "line-color": C.motorwayCase, "line-width": z(6, 0.6, 10, 2, 14, 7, 18, 30),
        "line-opacity": ["case", ["==", ["get", "tunel"], 1], 0.35, 1] } },
    { id: "road-motorway", type: "line", source: S, "source-layer": "roads", filter: cls("motorway", "trunk"),
      layout: { "line-cap": "round", "line-join": "round" }, paint: { "line-color": C.motorway, "line-width": z(6, 0.3, 10, 1.2, 14, 5, 18, 26),
        "line-opacity": ["case", ["==", ["get", "tunel"], 1], 0.4, 1] } },
    { id: "rail-context", type: "line", source: S, "source-layer": "rail", minzoom: 9,
      paint: { "line-color": C.rail, "line-width": z(9, 0.5, 14, 1.4), "line-dasharray": [3, 2] } },
  ];
}

export function basemapLabelLayers() {
  const S = "base";
  return [
    { id: "label-water", type: "symbol", source: S, "source-layer": "waterway", minzoom: 12, filter: ["all", cls("river", "canal"), ["has", "nombre"]],
      layout: { "symbol-placement": "line", "text-field": ["get", "nombre"], "text-font": ["Noto Sans Italic"], "text-size": 11, "text-letter-spacing": 0.05 },
      paint: { "text-color": "#5d87a6", "text-halo-color": "#ffffff", "text-halo-width": 1.2 } },
    { id: "label-road", type: "symbol", source: S, "source-layer": "roads", minzoom: 13.5, filter: ["has", "nombre"],
      layout: { "symbol-placement": "line", "text-field": ["get", "nombre"], "text-font": ["Noto Sans Regular"],
        "text-size": z(13.5, 9.5, 17, 12.5), "symbol-spacing": 280, "text-max-angle": 30, "text-padding": 4,
        "symbol-sort-key": ["match", ["get", "clase"], ["motorway", "trunk", "primary"], 1, ["secondary", "tertiary"], 2, 3] },
      paint: { "text-color": C.label, "text-halo-color": "#ffffff", "text-halo-width": 1.4, "text-opacity": 0.95 } },
    { id: "label-park", type: "symbol", source: S, "source-layer": "landuse", minzoom: 14, filter: ["all", cls("park"), ["has", "nombre"]],
      layout: { "text-field": ["get", "nombre"], "text-font": ["Noto Sans Italic"], "text-size": 11, "text-max-width": 8 },
      paint: { "text-color": "#5c8a4e", "text-halo-color": "#ffffff", "text-halo-width": 1.2 } },
  ];
}
