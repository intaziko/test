#!/usr/bin/env python3
"""Mapa base vectorial propio (PMTiles) a partir de OpenStreetMap vía Overture Maps.

Capas: water, waterway, landuse, roads, rail, aeroway, buildings. El estilo se define en src/basemap-style.js.
El mapa no depende de ningún servidor de teselas externo.
Requiere tippecanoe (variable TIPPECANOE o en el PATH).
Uso: python -I scripts/build_basemap.py
"""
import json
import os
import shutil
import subprocess
import sys

import geopandas as gpd
from shapely.geometry import box

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import RAW, ROOT  # noqa: E402

BUILD = ROOT / "data" / "build"
BUILD.mkdir(parents=True, exist_ok=True)
OV = RAW / "overture"
METRO = box(-3.95, 40.20, -3.35, 40.65)  # área metropolitana: aquí se incluyen todas las calles

# zoom mínimo por clase de vía (fuera del área metropolitana sólo se incluyen hasta «tertiary»)
ROAD_Z = {"motorway": 6, "trunk": 7, "primary": 8, "secondary": 10, "tertiary": 11, "unclassified": 13,
          "residential": 13, "living_street": 13, "pedestrian": 14, "service": 15, "footway": 15, "steps": 15,
          "path": 15, "cycleway": 15, "track": 14}
MAIN = {"motorway", "trunk", "primary", "secondary", "tertiary"}
LANDUSE = {("park", "park"): ("park", 11), ("recreation", "recreation_ground"): ("park", 13), ("park", "village_green"): ("park", 13),
           ("park", "dog_park"): ("park", 15), ("golf", "golf_course"): ("park", 11), ("protected", "national_park"): ("protected", 7),
           ("protected", "nature_reserve"): ("protected", 9), ("cemetery", "cemetery"): ("cemetery", 12),
           ("pedestrian", "plaza"): ("plaza", 15), ("pedestrian", "pedestrian"): ("plaza", 15),
           ("education", "university"): ("institutional", 13), ("medical", "hospital"): ("institutional", 13),
           ("developed", "industrial"): ("industrial", 12), ("military", "military"): ("industrial", 12),
           ("entertainment", "zoo"): ("park", 13), ("entertainment", "theme_park"): ("park", 13)}


def flags(fl):
    return {v for e in (fl if fl is not None else []) if e["between"] is None for v in e["values"]}


def dump(name, gdf, props):
    """GeoJSON por líneas con zoom mínimo por objeto para tippecanoe."""
    path = BUILD / f"{name}.geojsonl"
    with open(path, "w", encoding="utf-8") as f:
        for row in gdf.itertuples():
            feat = {"type": "Feature", "geometry": row.geometry.__geo_interface__,
                    "properties": {k: getattr(row, k) for k in props if gpd.pd.notna(getattr(row, k))},
                    "tippecanoe": {"minzoom": int(row.minzoom)}}
            f.write(json.dumps(feat, ensure_ascii=False) + "\n")
    print(f"  {name}: {len(gdf)}")
    return path


layers = {}

# agua
w = gpd.read_parquet(OV / "water.parquet")
w["nombre"] = w.names.apply(lambda n: n.get("primary") if n is not None else None)
poly = w[w.geom_type.isin(["Polygon", "MultiPolygon"]) & ~w["class"].isin(["swimming_pool", "wastewater", "reflecting_pool", "fish_pass"])].copy()
poly["minzoom"] = poly.geometry.to_crs(25830).area.apply(lambda a: 6 if a > 5e6 else 9 if a > 2e5 else 12 if a > 2e4 else 14)
poly["clase"] = poly["class"]
layers["water"] = dump("water", poly, ["clase", "nombre"])
ln = w[w.geom_type.isin(["LineString", "MultiLineString"]) & w["class"].isin(["river", "canal", "stream"])].copy()
ln["minzoom"] = ln["class"].map({"river": 8, "canal": 11, "stream": 12})
ln["clase"] = ln["class"]
layers["waterway"] = dump("waterway", ln, ["clase", "nombre"])

# usos del suelo
lu = gpd.read_parquet(OV / "land_use.parquet")
lu["k"] = list(zip(lu.subtype, lu["class"]))
lu = lu[lu.k.isin(LANDUSE)].copy()
lu["clase"] = lu.k.map(lambda k: LANDUSE[k][0])
lu["minzoom"] = lu.k.map(lambda k: LANDUSE[k][1])
lu["nombre"] = lu.names.apply(lambda n: n.get("primary") if n is not None else None)
lu = lu[lu.geom_type.isin(["Polygon", "MultiPolygon"])]
layers["landuse"] = dump("landuse", lu, ["clase", "nombre"])

# viario
s = gpd.read_parquet(OV / "segments.parquet", columns=["subtype", "class", "subclass", "names", "road_flags", "geometry"])
s = s[(s.subtype == "road") & s["class"].isin(ROAD_Z)].copy()
fl = s.road_flags.apply(flags)
s = s[~fl.apply(lambda f: bool(f & {"is_abandoned", "is_under_construction", "is_indoor"}))]
fl = fl.loc[s.index]
inside = s.geometry.intersects(METRO)
s = s[inside | s["class"].isin(MAIN)].copy()
s["clase"] = s["class"]
s["enlace"] = (s.subclass == "link").astype(int)
s["tunel"] = fl.loc[s.index].apply(lambda f: int("is_tunnel" in f))
s["puente"] = fl.loc[s.index].apply(lambda f: int("is_bridge" in f))
s["nombre"] = s.names.apply(lambda n: n.get("primary") if n is not None else None)
s["minzoom"] = s["class"].map(ROAD_Z) + s.enlace * 2
s.loc[s.subclass.isin(["sidewalk", "crosswalk", "driveway", "parking_aisle"]), "minzoom"] = 16
layers["roads"] = dump("roads", s, ["clase", "enlace", "tunel", "puente", "nombre"])

# ferrocarril de contexto (vías no subterráneas; las líneas de Cercanías se dibujan con datos propios)
r = gpd.read_parquet(OV / "rail.parquet")
rf = r.rail_flags.apply(flags)
r = r[r["class"].isin(["standard_gauge", "narrow_gauge"]) & ~rf.apply(lambda f: bool(f & {"is_tunnel", "is_disused", "is_abandoned", "is_under_construction"}))].copy()
r["minzoom"] = 9
layers["rail"] = dump("rail", r, [])

# aeropuertos (pistas)
i = gpd.read_parquet(OV / "infrastructure.parquet", columns=["subtype", "class", "geometry"])
a = i[(i.subtype == "airport") & i["class"].isin(["runway", "taxiway", "apron"])].copy()
a["clase"] = a["class"]
a["minzoom"] = a["class"].map({"runway": 9, "taxiway": 13, "apron": 12})
layers["aeroway"] = dump("aeroway", a, ["clase"])

# edificios (sólo entorno de origen y destino del Mapa 2)
b = gpd.pd.concat([gpd.read_parquet(OV / f).to_crs(4326) for f in ("buildings_destino.parquet", "buildings_origen.parquet")])
b = b[b.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
b["minzoom"] = 14
layers["buildings"] = dump("buildings", b, [])

tip = os.environ.get("TIPPECANOE") or shutil.which("tippecanoe")
assert tip, "tippecanoe no encontrado: defina TIPPECANOE=/ruta/tippecanoe (ver README)"
out = BUILD / "base.pmtiles"   # tippecanoe elige el formato por la extensión .pmtiles
pub = ROOT / "public" / "tiles" / "base.pmtiles.png"  # se publica como .png: GitHub Pages no lo comprime (ver src/common.js)
pub.parent.mkdir(parents=True, exist_ok=True)
cmd = [tip, "-o", str(out), "--force", "-Z5", "-z16", "--no-feature-limit", "--no-tile-size-limit",
       "--simplification=4", "--detect-shared-borders", "-n", "Mapa base Madrid (OSM/Overture)",
       "-A", "© OpenStreetMap contributors (ODbL) vía Overture Maps Foundation", "-q"]
for k, p in layers.items():
    cmd += ["-L", f"{k}:{p}"]
subprocess.run(cmd, check=True)
shutil.move(out, pub)
print("PMTiles:", pub, round(pub.stat().st_size / 1e6, 1), "MB")
