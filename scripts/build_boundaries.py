#!/usr/bin/env python3
"""Límites administrativos: 179 municipios de la Comunidad de Madrid y 21 distritos de Madrid capital.

Geometría: OpenStreetMap (vía Overture Maps «divisions»), cuyos límites municipales españoles proceden de
la BDLL del IGN. Se valida contra el IGN (es-atlas: Equipamiento Geográfico de Referencia Nacional) y
contra las superficies oficiales de los distritos publicadas por el Ayuntamiento.
Salidas: public/data/{municipios,distritos,comunidad,etiquetas_admin}.geojson, docs/datos/validacion_limites.json
"""
import json
import sys

import geopandas as gpd
import networkx as nx
import shapely
from shapely.geometry import Point
from shapely.ops import polylabel, unary_union

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import DOCS, OUT, RAW, UTM, norm, write_geojson, write_json  # noqa: E402

DISTRITOS = ["Centro", "Arganzuela", "Retiro", "Salamanca", "Chamartín", "Tetuán", "Chamberí", "Fuencarral-El Pardo",
             "Moncloa-Aravaca", "Latina", "Carabanchel", "Usera", "Puente de Vallecas", "Moratalaz", "Ciudad Lineal",
             "Hortaleza", "Villaverde", "Villa de Vallecas", "Vicálvaro", "San Blas-Canillejas", "Barajas"]
FOCO = ["Madrid", "Alcobendas", "Torrejón de Ardoz", "Getafe", "Móstoles"]
SIMPLIFY_M = 4  # simplificación de cobertura (conserva bordes compartidos); invisible hasta zoom 16
PALETTE = 6     # nº de tonos de fondo para distritos colindantes

areas = gpd.read_parquet(RAW / "overture" / "division_area.parquet")
areas = areas[areas.country == "ES"].copy()
areas["nm"] = areas.names.apply(lambda n: n.get("primary"))
areas = areas.to_crs(UTM)

cam = areas[(areas.subtype == "region") & (areas.nm == "Comunidad de Madrid")].geometry.iloc[0]
loc = areas[areas.subtype == "locality"].copy()
mun = loc[loc.geometry.representative_point().within(cam)].copy()
# OSM incluye como «locality» dos territorios mancomunados que no son municipios (El Redegüelo, Los Baldíos):
# se excluyen los polígonos sin homólogo en el IGN (ni por nombre ni por superficie equivalente).
ign0 = gpd.read_file(RAW / "npm_es_atlas" / "municipios_ign.geojson")
ign0 = ign0[ign0.id.astype(str).str.startswith("28")].to_crs(UTM)
ign_names = set(ign0.name.apply(norm))


def is_municipio(r):
    if norm(r.nm) in ign_names:
        return True
    inter = ign0.geometry.intersection(r.geometry).area
    best = ign0.geometry.iloc[inter.argmax()]
    return 0.9 < r.geometry.area / best.area < 1.1
keep = mun.apply(is_municipio, axis=1)
excluded = mun[~keep].nm.tolist()
mun = mun[keep].copy()
assert len(mun) == 179, f"se esperaban 179 municipios, hay {len(mun)} (excluidos {excluded})"

madrid = mun[mun.nm == "Madrid"].geometry.iloc[0]
cand = areas[areas.subtype.isin(["macrohood", "neighborhood"]) & areas.geometry.representative_point().within(madrid)]
rows = []
for i, name in enumerate(DISTRITOS, 1):
    m = cand[cand.nm.apply(norm) == norm(name)]
    assert len(m) == 1, f"distrito {name}: {len(m)} candidatos"
    rows.append(dict(codigo=i, nombre=name, osm=m.sources.iloc[0][0]["record_id"], geometry=m.geometry.iloc[0]))
dist = gpd.GeoDataFrame(rows, crs=UTM)

# --- validación ------------------------------------------------------------------------------
val = {"territorios_no_municipales_excluidos": excluded}
u = unary_union(dist.geometry)
val["distritos_vs_municipio_madrid"] = dict(area_municipio_km2=round(madrid.area / 1e6, 2), area_union_distritos_km2=round(u.area / 1e6, 2),
                                            diferencia_simetrica_km2=round(madrid.symmetric_difference(u).area / 1e6, 3))
assert madrid.symmetric_difference(u).area / madrid.area < 0.005, "los distritos no cubren el municipio"
ov = sum(a.intersection(b).area for a, b in zip(dist.geometry, dist.geometry[1:]))
val["solape_entre_distritos_m2"] = round(ov)

ign = gpd.read_file(RAW / "npm_es_atlas" / "municipios_ign.geojson")
ign = ign[ign.id.astype(str).str.startswith("28")].to_crs(UTM)
assert len(ign) == 179
ign["k"] = ign.name.apply(norm)
mun["k"] = mun.nm.apply(norm)
j = mun.merge(ign[["k", "id", "geometry"]].rename(columns={"id": "ine", "geometry": "g_ign"}), on="k", how="left")
miss = j[j.ine.isna()].nm.tolist()
# nombres con variantes (p. ej. artículos pospuestos en el IGN): emparejar por solape máximo
for nm in miss:
    g = mun[mun.nm == nm].geometry.iloc[0]
    best = ign.iloc[ign.geometry.intersection(g).area.argmax()]
    j.loc[j.nm == nm, "ine"] = best.id
    j.loc[j.nm == nm, "g_ign"] = best.geometry
j["ratio_area"] = j.geometry.area / gpd.GeoSeries(j.g_ign, crs=UTM).area
j["dist_centroide_m"] = j.geometry.centroid.distance(gpd.GeoSeries(j.g_ign, crs=UTM).centroid)
val["municipios_vs_ign"] = dict(n=int(len(j)), emparejados_por_solape=miss,
                                ratio_area_min=round(j.ratio_area.min(), 3), ratio_area_max=round(j.ratio_area.max(), 3),
                                dist_centroide_mediana_m=round(j.dist_centroide_m.median()), dist_centroide_max_m=round(j.dist_centroide_m.max()),
                                mayores_diferencias=j.assign(dif=(j.ratio_area - 1).abs()).nlargest(5, "dif")[["nm", "ratio_area", "dist_centroide_m"]].round(3).to_dict("records"))
# es-atlas está muy generalizado (cartografía a pequeña escala): en municipios pequeños la superficie varía
# por la simplificación; se exige coincidencia de posición en todos y de superficie (±5 %) en los >50 km².
big = j.geometry.area > 50e6
val["municipios_vs_ign"]["ratio_area_mediana"] = round(j.ratio_area.median(), 3)
val["municipios_vs_ign"]["ratio_area_>50km2"] = [round(j[big].ratio_area.min(), 3), round(j[big].ratio_area.max(), 3)]
assert (j.dist_centroide_m < 1000).all(), "algún municipio desplazado >1 km respecto al IGN"
assert j[big].ratio_area.between(0.95, 1.05).all(), "algún municipio >50 km² difiere >5 % en superficie del IGN"
assert len(set(j.ine)) == 179, "emparejamiento con el IGN no biunívoco"
mun = mun.merge(j[["nm", "ine"]], on="nm")

# Cifras oficiales del Ayuntamiento verificadas en esta sesión (búsqueda web 05/11/2026):
#   término municipal 60.445,52 ha (documento municipal, enero 2020); distrito Centro 522,8 ha (Anuario Estadístico 2015)
dist["area_km2"] = (dist.area / 1e6).round(2)
val["contraste_oficial"] = dict(
    municipio_madrid=dict(oficial_ha=60445.52, calculado_ha=round(madrid.area / 1e4, 1), ratio=round(madrid.area / 1e4 / 60445.52, 4)),
    distrito_centro=dict(oficial_ha=522.8, calculado_ha=round(dist[dist.nombre == "Centro"].area.iloc[0] / 1e4, 1),
                         ratio=round(dist[dist.nombre == "Centro"].area.iloc[0] / 1e4 / 522.8, 4)))
assert abs(val["contraste_oficial"]["municipio_madrid"]["ratio"] - 1) < 0.01
assert abs(val["contraste_oficial"]["distrito_centro"]["ratio"] - 1) < 0.02
val["distritos"] = dist[["codigo", "nombre", "area_km2", "osm"]].to_dict("records")

# --- simplificación de cobertura (bordes compartidos idénticos) ------------------------------------
mun["geometry"] = shapely.coverage_simplify(mun.geometry.values, SIMPLIFY_M)
dist["geometry"] = shapely.coverage_simplify(dist.geometry.values, SIMPLIFY_M)

# colores: coloreado de grafo para que distritos colindantes tengan tonos distintos
G = nx.Graph()
G.add_nodes_from(dist.index)
for a in dist.index:
    for b in dist.index:
        if a < b and dist.geometry[a].buffer(1).intersects(dist.geometry[b]):
            G.add_edge(a, b)
col = nx.greedy_color(G, strategy="largest_first")
assert max(col.values()) < PALETTE
dist["color"] = dist.index.map(col)

# --- etiquetas: lejos de las líneas de transporte para no solaparse con ellas ----------------------
lines_path = OUT / "lineas.geojson"
lines = unary_union(gpd.read_file(lines_path).to_crs(UTM).geometry).buffer(180) if lines_path.exists() else None


def label_point(poly, avoid=None):
    p = poly.buffer(-150) if poly.buffer(-150).area > 0 else poly
    if avoid is not None and p.difference(avoid).area > 0.15 * p.area:
        p = p.difference(avoid)
    if p.geom_type == "MultiPolygon":
        p = max(p.geoms, key=lambda g: g.area)
    return polylabel(p, tolerance=10)


def away_from_lines(p, poly, clear=260, step=120, radius=1800):
    """Si el centro urbano cae sobre una línea de transporte, desplaza la etiqueta al punto libre más próximo."""
    if lines is None or p.distance(lines) > clear - 180:
        return p
    best = None
    for dx in range(-radius, radius + 1, step):
        for dy in range(-radius, radius + 1, step):
            q = Point(p.x + dx, p.y + dy)
            d = (dx * dx + dy * dy) ** 0.5
            if d <= radius and (best is None or d < best[0]) and poly.contains(q) and q.distance(lines) > clear - 180:
                best = (d, q)
    return best[1] if best else p


pts = gpd.read_parquet(RAW / "overture" / "division.parquet")
pts = pts[(pts.subtype == "locality")].copy()
pts["nm"] = pts.names.apply(lambda n: n.get("primary"))
pts = pts.to_crs(UTM)
lab = []
for r in mun.itertuples():
    p = pts[(pts.nm == r.nm) & pts.within(r.geometry)]
    pop = float(p.population.max()) if len(p) and p.population.notna().any() else 0
    g = p.geometry.iloc[0] if len(p) else label_point(r.geometry)
    g = g if r.nm == "Madrid" else away_from_lines(g, r.geometry)  # MADRID se rotula en su centro a escala regional
    lab.append(dict(tipo="municipio", nombre=r.nm, foco=int(r.nm in FOCO), rank=0 if r.nm == "Madrid" else (1 if pop > 100000 or r.nm in FOCO else 2 if pop > 20000 else 3),
                    geometry=g))
# rótulo alternativo de MADRID para la escala metropolitana impresa: en el interior despejado del término
dlab = {r.nombre: label_point(r.geometry, lines) for r in dist.itertuples()}
avoid = unary_union([lines] + [p.buffer(2500) for p in dlab.values()]) if lines is not None else None
lab.append(dict(tipo="municipio", nombre="Madrid", foco=1, rank=0, alt=1, geometry=label_point(madrid, avoid)))
for r in dist.itertuples():
    lab.append(dict(tipo="distrito", nombre=r.nombre, codigo=r.codigo, rank=1, geometry=dlab[r.nombre]))
lab = gpd.GeoDataFrame(lab, crs=UTM)

mun["foco"] = mun.nm.isin(FOCO).astype(int)
mun["area_km2"] = (mun.area / 1e6).round(2)
bbox = lambda g: [round(x, 5) for x in gpd.GeoSeries([g], crs=UTM).to_crs(4326).total_bounds]  # noqa: E731
mun["bbox"] = mun.geometry.apply(lambda g: ",".join(map(str, bbox(g))))
dist["bbox"] = dist.geometry.apply(lambda g: ",".join(map(str, bbox(g))))

# municipio y distrito de cada estación (red.json lo genera build_network.py)
red_path = OUT / "red.json"
red = json.load(open(red_path, encoding="utf-8"))
sp = gpd.GeoDataFrame([{"sid": k, "geometry": Point(v["coord"])} for k, v in red["estaciones"].items()], crs=4326).to_crs(UTM)
prov = areas[areas.subtype == "county"][["nm", "geometry"]].rename(columns={"nm": "prov"})
jm = gpd.sjoin(sp, loc[["nm", "geometry"]], how="left", predicate="within").drop_duplicates("sid").set_index("sid")
jp = gpd.sjoin(sp, prov, how="left", predicate="within").drop_duplicates("sid").set_index("sid")
jd = gpd.sjoin(sp, dist[["nombre", "geometry"]], how="left", predicate="within").drop_duplicates("sid").set_index("sid")
for k, v in red["estaciones"].items():
    m = jm.at[k, "nm"]
    p_ = jp.at[k, "prov"]
    v["municipio"] = (m if p_ == "Comunidad de Madrid" else f"{m} (prov. de {p_})") if isinstance(m, str) else None
    v["distrito"] = jd.at[k, "nombre"] if isinstance(jd.at[k, "nombre"], str) else None
assert all(v["municipio"] for v in red["estaciones"].values()), "estación sin municipio"
assert sum(1 for v in red["estaciones"].values() if v["distrito"]) > 200
write_json(red_path, red)

n1 = write_geojson(OUT / "municipios.geojson", mun[["ine", "nm", "foco", "area_km2", "bbox", "geometry"]].rename(columns={"nm": "nombre"}))
n2 = write_geojson(OUT / "distritos.geojson", dist[["codigo", "nombre", "area_km2", "color", "bbox", "geometry"]])
write_geojson(OUT / "comunidad.geojson", gpd.GeoDataFrame([{"nombre": "Comunidad de Madrid", "geometry": cam.boundary}], crs=UTM))
write_geojson(OUT / "etiquetas_admin.geojson", lab)
write_json(DOCS / "datos" / "validacion_limites.json", val, pretty=True)
print(f"municipios {n1}, distritos {n2}; validación:", {k: v for k, v in val.items() if k != "distritos"})
