// Convierte el TopoJSON de es-atlas (IGN) a GeoJSON: node scripts/topo2geo.mjs <entrada.json> <objeto> <salida.geojson>
import { readFileSync, writeFileSync } from "node:fs";
import { feature } from "topojson-client";
const [, , src, obj, out] = process.argv;
const topo = JSON.parse(readFileSync(src, "utf8"));
writeFileSync(out, JSON.stringify(feature(topo, topo.objects[obj])));
