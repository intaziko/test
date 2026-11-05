#!/usr/bin/env python3
"""Avisos de servicio (data/avisos.json, recopilación manual con fuentes) → public/data/avisos.json + avisos.geojson.

Los tramos afectados se dibujan sobre el trazado oficial de la línea, entre los andenes de las estaciones citadas.
"""
import json
import sys

import geopandas as gpd
from shapely.geometry import LineString
from shapely.ops import substring

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import OUT, ROOT, UTM, norm, write_json  # noqa: E402

av = json.load(open(ROOT / "data" / "avisos.json", encoding="utf-8"))
red = json.load(open(OUT / "red.json", encoding="utf-8"))
lin = gpd.read_file(OUT / "lineas.geojson").to_crs(UTM)
pla = gpd.read_file(OUT / "andenes.geojson").to_crs(UTM)


def sid(net, name):
    m = [k for k, v in red["estaciones"].items() if v["red"] == net and norm(v["nombre"]) == norm(name)]
    assert len(m) == 1, f"estación no encontrada o ambigua: {name} ({net})"
    return m[0]


feats = []
for a in av["avisos"]:
    if a["tramo"]:
        net, ln = a["red"], a["linea"]
        seq = red["lineas"][f"{'metro' if net == 'metro' else net}:{ln}"]["estaciones"]
        s1, s2 = (sid(net, x) for x in a["tramo"])
        i, j = seq.index(s1), seq.index(s2)
        if red["lineas"][f"{net}:{ln}"]["circular"]:
            fwd = seq[i:j + 1] if i <= j else seq[i:] + seq[:j + 1]
            bwd = (seq[j:i + 1] if j <= i else seq[j:] + seq[:i + 1])[::-1]
            path = fwd if a["via"] is None or sid(net, a["via"]) in fwd else bwd
        else:
            path = seq[i:j + 1] if i <= j else seq[j:i + 1][::-1]
        geoms = lin[(lin.net == net) & (lin.line == ln)].geometry.tolist()
        pts = [pla[(pla.sid == s) & (pla.line == ln)].geometry.iloc[0] for s in path]
        coords = []
        for p, q in zip(pts, pts[1:]):
            g = min(geoms, key=lambda g: g.distance(p) + g.distance(q))
            x, y = g.project(p), g.project(q)
            seg = substring(g, x, y)
            if seg.length > 2.5 * p.distance(q) + 300:      # tramo que cruza el origen de un shape circular
                seg = LineString(list(substring(g, x, g.length if x > y else 0).coords) + list(substring(g, 0 if x > y else g.length, y).coords))
            c = list(seg.coords)
            coords += c if not coords else c[1:]
        g = gpd.GeoSeries([LineString(coords)], crs=UTM).to_crs(4326).iloc[0]
        feats.append({"type": "Feature", "geometry": g.__geo_interface__, "properties": {"id": a["id"], "estado": a["estado"], "linea": ln, "red": net}})
        a["estaciones_tramo"] = [red["estaciones"][s]["nombre"] for s in path]
    for name in a["estaciones_cerradas"]:
        s = sid(a["red"], name)
        p = gpd.GeoSeries([pla[pla.sid == s].geometry.iloc[0]], crs=UTM).to_crs(4326).iloc[0]
        feats.append({"type": "Feature", "geometry": p.__geo_interface__, "properties": {"id": a["id"], "estado": "cerrada", "nombre": name, "sid": s}})
        a.setdefault("sids_cerradas", []).append(s)

write_json(OUT / "avisos.json", av)
write_json(OUT / "avisos.geojson", {"type": "FeatureCollection", "features": json.loads(json.dumps(feats))})
print("avisos:", len(av["avisos"]), "geometrías:", len(feats), [a.get("estaciones_tramo") for a in av["avisos"] if a.get("estaciones_tramo")])

# registro de fuentes (mismo contenido para la interfaz y para docs/FUENTES.md)
write_json(OUT / "fuentes.json", json.load(open(ROOT / "data" / "fuentes.json", encoding="utf-8")))
