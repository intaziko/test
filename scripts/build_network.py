#!/usr/bin/env python3
"""Red ferroviaria (Metro, Metro Ligero, Cercanías) a partir de los GTFS oficiales (CRTM / Renfe).

Salidas en public/data/:
  lineas.geojson      trazado real de cada línea o tramo (shapes.txt)
  andenes.geojson     punto de parada de cada línea en cada estación, ajustado sobre su trazado
  enlaces.geojson     transbordos: pasillos entre andenes de una estación y correspondencias entre redes
  estaciones.geojson  un punto por estación (etiqueta, búsqueda, selección)
  red.json            metadatos para la interfaz (líneas ordenadas, vecinas, accesos, transbordos)
Uso: python -I scripts/build_network.py
"""
import sys
from collections import Counter, defaultdict

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point
from shapely.ops import linemerge, substring, unary_union

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import OUT, RAW, ROOT, UTM, norm, write_geojson, write_json  # noqa: E402
from railmatch import Matcher  # noqa: E402

NET = {
    "metro": {"dir": "gtfs_metro", "label": "Metro de Madrid"},
    "ml": {"dir": "gtfs_metro_ligero", "label": "Metro Ligero / Tranvía"},
    "cercanias": {"dir": "gtfs_cercanias_crtm", "label": "Cercanías Madrid"},
}
SNAP_MAX_M = 400          # distancia máxima parada GTFS → trazado (algunas coordenadas GTFS son las del intercambiador)
CORR_MAX_M = 450          # distancia máxima para considerar correspondencia entre redes
LOWER = {"de", "del", "la", "las", "los", "el", "y", "e", "a"}


def read(net, name, **kw):
    return pd.read_csv(RAW / NET[net]["dir"] / "extracted" / f"{name}.txt", dtype=str, encoding="utf-8-sig", **kw)


def title_es(s):
    """Respaldo si no hay forma oficial con tildes: 'PUERTA DEL SUR' -> 'Puerta del Sur'."""
    w = s.lower().split()
    return " ".join(x if (i and x in LOWER) else x[:1].upper() + x[1:] for i, x in enumerate(w))


# --------------------------------------------------------------------------- nombres con tildes
# El GTFS de Metro/ML publica los nombres en mayúsculas sin tildes. La forma tipográfica se toma de
# los accesos del propio CRTM o de OpenStreetMap (Overture), SOLO si su normalización coincide
# exactamente con el nombre oficial del GTFS; así nunca se cambia el nombre, sólo su escritura.
infra = gpd.read_parquet(RAW / "overture" / "infrastructure.parquet")
infra = infra[infra["subtype"] == "transit"].copy()
infra["nm"] = infra["names"].apply(lambda n: n.get("primary") if n is not None else None)
infra = infra.dropna(subset=["nm"]).to_crs(UTM)
osm_names = defaultdict(list)
for nm, geom in zip(infra["nm"], infra.geometry):
    osm_names[norm(nm)].append((nm, geom.centroid))


def proper_name(gtfs_name, xy, extra=()):
    key = norm(gtfs_name)
    for cand in extra:                      # accesos del CRTM con la misma grafía normalizada
        if norm(cand) == key:
            return cand, "crtm-acceso"
    best = None
    for nm, p in osm_names.get(key, []):
        d = p.distance(Point(xy))
        if d < 800 and (best is None or d < best[1]):
            best = (nm, d)
    if best:
        return best[0], "osm"
    return title_es(gtfs_name), "titulo"


# --------------------------------------------------------------------------- lectura GTFS
def load(net):
    st = read(net, "stops")
    st["lat"], st["lon"] = st.stop_lat.astype(float), st.stop_lon.astype(float)
    for col in ("location_type", "parent_station", "stop_desc"):  # el GTFS de Cercanías no las trae
        if col not in st:
            st[col] = None
    ro = read(net, "routes")
    tr = read(net, "trips")
    stt = read(net, "stop_times", usecols=["trip_id", "stop_id", "stop_sequence", "arrival_time"])
    stt["sq"] = stt.stop_sequence.astype(int)
    seq = stt.sort_values(["trip_id", "sq"]).groupby("trip_id").stop_id.apply(tuple)
    tr["seq"] = tr.trip_id.map(seq)
    tr = tr.merge(ro[["route_id", "route_short_name", "route_long_name", "route_color", "route_text_color", "route_type"]], on="route_id")
    sh = read(net, "shapes")
    sh["sq"] = sh.shape_pt_sequence.astype(int)
    shapes = {k: LineString(list(zip(g.shape_pt_lon.astype(float), g.shape_pt_lat.astype(float))))
              for k, g in sh.sort_values(["shape_id", "sq"]).groupby("shape_id")}
    return st, tr, shapes


def line_id(net, r):
    if net == "metro" and "_B_" in r.shape_id:      # tramos 7B, 9B y 10B (cambio de tren obligatorio)
        return r.route_short_name + "B"
    return r.route_short_name


matcher = None
rail_report = []


def shape_piece(pa, pb, shapes):
    """Tramo de un shape oficial entre dos estaciones (el más corto de los que pasan junto a ambas)."""
    best = None
    for sg in shapes:
        if sg.distance(pa) <= 150 and sg.distance(pb) <= 150:
            x, y = sorted((sg.project(pa), sg.project(pb)))
            seg = substring(sg, x, y)
            if seg.geom_type == "LineString" and seg.length > 0 and (best is None or seg.length < best.length):
                best = seg
    return best


def rail_geometry(net, ln, g, sh_utm, st_utm):
    """Trazado de una línea de Cercanías: servicios reales del GTFS ajustados a las vías de OSM."""
    global matcher
    if matcher is None:
        matcher = Matcher()
    guide = unary_union([sh_utm[c] for c in g.shape_id.unique()])
    pair = {}
    for q in set(g.seq):
        for a, b in zip(q, q[1:]):
            k = tuple(sorted((a, b)))
            if k in pair:
                continue
            pa, pb = st_utm[a], st_utm[b]
            gd = guide if guide.distance(pa) < 150 and guide.distance(pb) < 150 else None
            seg = matcher.path(pa, pb, gd)
            official = shape_piece(pa, pb, [sh_utm[c] for c in g.shape_id.unique()])
            src = "osm"
            dmax = round(max(guide.distance(Point(c)) for c in seg.coords)) if seg is not None and gd is not None else None
            # Se acepta la vía OSM sólo si coincide con el shape oficial (≤300 m) y no es más larga que él;
            # si no, se usa el tramo del shape oficial entre ambas estaciones.
            if official is not None and (seg is None or dmax > 300 or seg.length > 1.25 * official.length):
                seg, src = official, "shape_oficial"
            assert seg is not None, f"{ln}: sin vía OSM ni shape oficial entre {a} y {b}"
            ratio = seg.length / max(pa.distance(pb), 1)
            rail_report.append(dict(linea=ln, de=a, a=b, km=round(seg.length / 1000, 2), sinuosidad=round(ratio, 2),
                                    guiado=gd is not None, dist_max_shape_m=dmax, geometria=src))
            pair[k] = seg
    m = linemerge(list(pair.values()))
    return list(m.geoms) if m.geom_type == "MultiLineString" else [m]


lines, stations, platforms = {}, {}, {}
patterns = []          # (net, line, terminal_label, [sid...], ntrips)
station_of = {}        # (net, stop_id) -> sid

for net in NET:
    st, tr, shapes = load(net)
    st_by_id = st.set_index("stop_id")
    if net == "cercanias":
        # «C4» agrupa servicios Parla–Chamartín ya incluidos en C4a y C4b: se valida y se omite.
        c4 = {s for q in tr[tr.route_short_name == "C4"].seq for s in q}
        c4ab = {s for q in tr[tr.route_short_name.isin(["C4a", "C4b"])].seq for s in q}
        assert c4 <= c4ab, "C4 tiene estaciones no cubiertas por C4a/C4b"
        tr = tr[tr.route_short_name != "C4"]
    tr["line"] = [line_id(net, r) for r in tr.itertuples()]

    # estación (padre) de cada parada
    def sid_of(stop_id):
        if net == "cercanias":
            return f"cer_{stop_id}"
        p = st_by_id.at[stop_id, "parent_station"]
        if isinstance(p, str):
            return p
        alt = stop_id.replace("par_", "est_")
        return alt if alt in st_by_id.index else stop_id

    access = defaultdict(list)
    for r in st[st.location_type == "2"].itertuples():
        access[r.parent_station].append({"nombre": r.stop_name, "dir": r.stop_desc if isinstance(r.stop_desc, str) else "",
                                         "coord": [round(r.lon, 6), round(r.lat, 6)], "id": r.stop_id})

    used = {s for q in tr.seq for s in q}
    for stop_id in used:
        sid = sid_of(stop_id)
        station_of[(net, stop_id)] = sid
        if sid not in stations:
            row = st_by_id.loc[sid] if sid in st_by_id.index else st_by_id.loc[stop_id]
            name_src = st_by_id.at[stop_id, "stop_name"]  # nombre de la parada (no «Intercambiador de …»)
            stations[sid] = {"id": sid, "net": net, "gtfs_name": name_src, "lon": float(row.lon), "lat": float(row.lat),
                             "grupo": row.stop_name if sid.startswith("est_90") else None,
                             "accesos": access.get(sid, []), "stops": set(), "lines": set()}
        stations[sid]["stops"].add(stop_id)

    # patrones de paradas por línea
    for (ln, shp, seq), g in tr.groupby(["line", "shape_id", "seq"]):
        r = g.iloc[0]
        tsn = r.get("trip_short_name") if "trip_short_name" in g else None
        circ = seq[0] == seq[-1]
        sids = [sid_of(s) for s in seq]
        for s, sid in zip(seq, sids):
            stations[sid]["lines"].add(ln)
            platforms.setdefault((sid, ln), set()).add(s)
        andn = None
        if isinstance(tsn, str) and "ANDEN" in tsn:
            andn = "Andén " + tsn.split("ANDEN")[-1].strip(" -)")
        patterns.append(dict(net=net, line=ln, shape=shp, seq=sids, n=len(g), circ=circ, anden=andn))

    # geometría: conjunto mínimo de shapes que cubre todas las paradas de cada línea
    st_utm = gpd.GeoSeries(gpd.points_from_xy(st.lon, st.lat), index=st.stop_id, crs=4326).to_crs(UTM)
    sh_utm = gpd.GeoSeries(list(shapes.values()), index=list(shapes.keys()), crs=4326).to_crs(UTM)
    for ln, g in tr.groupby("line"):
        r = g.iloc[0]
        if net == "cercanias":
            geoms = rail_geometry(net, ln, g, sh_utm, st_utm)
            lines[(net, ln)] = dict(net=net, id=ln, color="#" + r.route_color.upper(), text="#" + r.route_text_color.upper(),
                                    long=r.route_long_name, type=int(r.route_type),
                                    shapes=gpd.GeoSeries(geoms, crs=UTM).to_crs(4326).tolist(),
                                    shape_ids=[f"osm_{i}" for i in range(len(geoms))],
                                    bus_trips=int((g.route_type == "3").sum()))
            continue
        stops = {s for q in g.seq for s in q}
        cand = g.shape_id.value_counts().index.tolist()
        # selección estricta (80 m) para no omitir variantes de trazado (p. ej. los dos bucles del tranvía de Parla)
        cover = {c: {s for s in stops if sh_utm[c].distance(st_utm[s]) <= 80} for c in cand}
        chosen, left = [], set(stops)
        while left:
            c = max(cand, key=lambda c: (len(cover[c] & left), sh_utm[c].length))
            if not cover[c] & left:
                break
            chosen.append(c)
            left -= cover[c]
        # paradas a más de 80 m pero a menos de SNAP_MAX_M: coordenada GTFS imprecisa (p. ej. la del intercambiador)
        left -= {s for s in left if any(sh_utm[c].distance(st_utm[s]) <= SNAP_MAX_M for c in chosen)}
        # quita shapes que sean el mismo trazado en sentido contrario (se dibujaría dos veces)
        uniq = []
        for c in chosen:
            if not any(sh_utm[c].hausdorff_distance(sh_utm[u]) < 60 for u in uniq):
                uniq.append(c)
        geoms = [sh_utm[c] for c in uniq]
        # Tramos sin shape propio (p. ej. servicios C1 desde Atocha): se toman del shape oficial de otra
        # línea de la misma red que pasa por ambas paradas (misma vía), nunca se dibujan a mano.
        pieces = []
        if left:
            for q in {q for q in g.seq}:
                for a, b in zip(q, q[1:]):
                    if a not in left and b not in left:
                        continue
                    pa, pb = st_utm[a], st_utm[b]
                    best = None
                    for k, sg in sh_utm.items():
                        if sg.distance(pa) <= SNAP_MAX_M and sg.distance(pb) <= SNAP_MAX_M:
                            x, y = sorted((sg.project(pa), sg.project(pb)))
                            seg = substring(sg, x, y)
                            if seg.length > 0 and (best is None or seg.length < best.length):
                                best = seg
                    assert best is not None, f"{net} {ln}: sin trazado oficial entre {a} y {b}"
                    pieces.append(best)
            left -= {s for s in left if any(p.distance(st_utm[s]) <= SNAP_MAX_M for p in pieces)}
        assert not left, f"{net} {ln}: paradas sin trazado cercano {left}"
        geoms += [p for p in pieces if not any(p.hausdorff_distance(u) < 60 for u in geoms)]
        lines[(net, ln)] = dict(net=net, id=ln, color="#" + r.route_color.upper(), text="#" + r.route_text_color.upper(),
                                long=r.route_long_name, type=int(r.route_type),
                                shapes=gpd.GeoSeries(geoms, crs=UTM).to_crs(4326).tolist(),
                                shape_ids=uniq + [f"tramo_{i}" for i in range(len(geoms) - len(uniq))],
                                bus_trips=int((g.route_type == "3").sum()))

# --------------------------------------------------------------------------- Línea 3 (reconstrucción)
# El GTFS de Metro del CRTM (feed_version 20250527) no contiene viajes ni shape de la L3, aunque sí sus 18
# paradas (par_4_43..53 y par_4_267..273). La L3 se prolongó de Villaverde Alto a El Casar el 21/04/2025
# (Comunidad de Madrid). Se reconstruye: paradas oficiales CRTM + El Casar (estación de la L12), orden
# geográfico y trazado sobre los túneles de metro de OSM (Overture, clase «subway").
def add_line3():
    st = read("metro", "stops")
    used = {s for (n, s) in station_of if n == "metro"}
    cand = st[st.stop_id.str.startswith("par_") & ~st.stop_id.isin(used)].copy()
    assert len(cand) == 18, f"L3: se esperaban 18 paradas sin viajes, hay {len(cand)}"
    pts = gpd.GeoSeries(gpd.points_from_xy(cand.stop_lon.astype(float), cand.stop_lat.astype(float)), index=cand.stop_id, crs=4326).to_crs(UTM)
    casar_sid = next(k for k, v in stations.items() if v["net"] == "metro" and norm(v["gtfs_name"]) == "el casar")
    casar_stop = next(iter(stations[casar_sid]["stops"]))
    pc = gpd.GeoSeries([Point(stations[casar_sid]["lon"], stations[casar_sid]["lat"])], crs=4326).to_crs(UTM).iloc[0]
    chain = [max(pts.index, key=lambda k: pts[k].distance(pc))]   # cabecera opuesta a El Casar (Moncloa)
    rest = set(pts.index) - set(chain)
    while rest:
        nxt = min(rest, key=lambda k: pts[k].distance(pts[chain[-1]]))
        chain.append(nxt)
        rest.remove(nxt)
    assert min(pts.index, key=lambda k: pts[k].distance(pc)) == chain[-1], "L3: orden geográfico incoherente"
    chain.append(casar_stop)
    xy = {**{k: pts[k] for k in pts.index}, casar_stop: pc}
    m = Matcher(classes=("subway",), k=6, name="Línea 3")  # sólo vías que OSM identifica como Línea 3
    guide = LineString([(xy[k].x, xy[k].y) for k in chain])
    segs = []
    for a, b in zip(chain, chain[1:]):
        seg = m.path(xy[a], xy[b], guide)
        assert seg is not None and seg.length < 3 * xy[a].distance(xy[b]) + 500, f"L3: sin túnel OSM entre {a} y {b}"
        segs.append(seg)
        rail_report.append(dict(linea="3", de=a, a=b, km=round(seg.length / 1000, 2),
                                sinuosidad=round(seg.length / max(xy[a].distance(xy[b]), 1), 2), guiado=True,
                                dist_max_shape_m=round(max(guide.distance(Point(c)) for c in seg.coords))))
    by_id = st.set_index("stop_id")
    for s_ in chain[:-1]:
        sid = s_.replace("par_", "est_") if s_.replace("par_", "est_") in set(st.stop_id) else (by_id.at[s_, "parent_station"] if isinstance(by_id.at[s_, "parent_station"], str) else s_)
        station_of[("metro", s_)] = sid
        if sid not in stations:
            row = by_id.loc[sid] if sid in by_id.index else by_id.loc[s_]
            stations[sid] = {"id": sid, "net": "metro", "gtfs_name": by_id.at[s_, "stop_name"], "lon": float(row.stop_lon),
                             "lat": float(row.stop_lat), "grupo": row.stop_name if sid.startswith("est_90") else None,
                             "accesos": [], "stops": set(), "lines": set()}
            acc = st[(st.location_type == "2") & (st.parent_station == sid)]
            stations[sid]["accesos"] = [{"nombre": r.stop_name, "dir": r.stop_desc if isinstance(r.stop_desc, str) else "",
                                         "coord": [round(float(r.stop_lon), 6), round(float(r.stop_lat), 6)], "id": r.stop_id}
                                        for r in acc.itertuples()]
        stations[sid]["stops"].add(s_)
    sids = [station_of[("metro", s_)] for s_ in chain]
    for s_, sid in zip(chain, sids):
        stations[sid]["lines"].add("3")
        platforms.setdefault((sid, "3"), set()).add(s_)
    patterns.append(dict(net="metro", line="3", shape="osm", seq=sids, n=1, circ=False, anden=None))
    patterns.append(dict(net="metro", line="3", shape="osm", seq=sids[::-1], n=1, circ=False, anden=None))
    ro = read("metro", "routes").set_index("route_short_name")
    coords = []
    for seg in segs:  # tramos consecutivos estación a estación → una sola polilínea continua
        c = list(seg.coords)
        coords += c if not coords else c[1:]
    lines[("metro", "3")] = dict(net="metro", id="3", color="#" + ro.at["3", "route_color"], text="#" + ro.at["3", "route_text_color"],
                                 long=ro.at["3", "route_long_name"], type=1,
                                 shapes=gpd.GeoSeries([LineString(coords)], crs=UTM).to_crs(4326).tolist(),
                                 shape_ids=["osm_l3"], bus_trips=0, reconstruida=True)


add_line3()

# --------------------------------------------------------------------------- nombres de estación
for s in stations.values():
    xy = gpd.GeoSeries([Point(s["lon"], s["lat"])], crs=4326).to_crs(UTM).iloc[0]
    if s["net"] == "cercanias":
        s["name"], s["name_src"] = s["gtfs_name"], "gtfs"
    else:
        s["name"], s["name_src"] = proper_name(s["gtfs_name"], (xy.x, xy.y), [a["nombre"] for a in s["accesos"]])
    s["xy"] = (xy.x, xy.y)

# --------------------------------------------------------------------------- andenes ajustados al trazado
line_utm = {k: gpd.GeoSeries(v["shapes"], crs=4326).to_crs(UTM).tolist() for k, v in lines.items()}
stop_xy = {}
for net in NET:
    st = read(net, "stops")
    pts = gpd.GeoSeries(gpd.points_from_xy(st.stop_lon.astype(float), st.stop_lat.astype(float)), index=st.stop_id, crs=4326).to_crs(UTM)
    for k, p in pts.items():
        stop_xy[(net, k)] = p

plat_rows, snap_report = [], []
for (sid, ln), stops in platforms.items():
    net = stations[sid]["net"]
    p = Point(np.mean([stop_xy[(net, s)].x for s in stops]), np.mean([stop_xy[(net, s)].y for s in stops]))
    geoms = line_utm[(net, ln)]
    g = min(geoms, key=lambda g: g.distance(p))
    d = g.distance(p)
    snapped = g.interpolate(g.project(p)) if d <= SNAP_MAX_M else p
    snap_report.append(d)
    plat_rows.append(dict(sid=sid, net=net, line=ln, geometry=snapped, snap_m=round(d, 1)))
plat = gpd.GeoDataFrame(plat_rows, crs=UTM)
for r in sorted(plat_rows, key=lambda r: -r["snap_m"])[:12]:
    print("  desplazamiento", r["snap_m"], "m", r["sid"], stations[r["sid"]]["gtfs_name"], r["net"], r["line"])
print(f"andenes: {len(plat)}  desplazamiento al trazado: mediana {np.median(snap_report):.1f} m, máx {max(snap_report):.1f} m")

# --------------------------------------------------------------------------- correspondencias entre redes
STRIP = ("madrid ", "estacion de ")
GENERIC = {"puerta", "plaza", "hospital", "parque", "avenida", "universidad", "colonia", "barrio", "santa",
           "ciudad", "campus", "centro", "estadio", "poligono", "pinar", "fuente", "reyes"}


def key_tokens(name):
    n = norm(name)
    for p in STRIP:
        n = n[len(p):] if n.startswith(p) else n
    for suf in (" cercanias", " p v", " renfe"):
        n = n[: -len(suf)] if n.endswith(suf) else n
    return n


extra = pd.read_json(ROOT / "data" / "correspondencias_verificadas.json")
corr = []
by_net = defaultdict(list)
for s in stations.values():
    by_net[s["net"]].append(s)
nets = list(NET)
for i, a_net in enumerate(nets):
    for b_net in nets[i + 1:]:
        for a in by_net[a_net]:
            best = None
            for b in by_net[b_net]:
                d = Point(a["xy"]).distance(Point(b["xy"]))
                if d > CORR_MAX_M:
                    continue
                ka, kb = key_tokens(a["name"]), key_tokens(b["name"])
                t1, t2 = ka.split()[0], kb.split()[0]
                same = (ka == kb or f" {ka} " in f" {kb} " or f" {kb} " in f" {ka} "
                        or (t1 == t2 and len(t1) >= 5 and t1 not in GENERIC) or d < 120)
                if same and (best is None or d < best[1]):
                    best = (b, d)
            if best:
                corr.append(dict(a=a["id"], b=best[0]["id"], dist=round(best[1]), tipo="nombre+proximidad"))
def resolve(i):
    for c in (i, i.replace("par_", "est_"), i.replace("est_", "par_")):
        if c in stations:
            return c
    raise KeyError(f"correspondencia verificada con id desconocido: {i}")


for r in extra.itertuples():
    r = r._replace(a=resolve(r.a), b=resolve(r.b))
    corr.append(dict(a=r.a, b=r.b, dist=round(Point(stations[r.a]["xy"]).distance(Point(stations[r.b]["xy"]))),
                     tipo="verificada", fuente=r.fuente))
# una estación de Cercanías debe enlazar con UNA estación de cada red (la más cercana)
seen, corr_ok = set(), []
for c in sorted(corr, key=lambda c: c["dist"]):
    k = (c["b"], stations[c["a"]]["net"]) if c["tipo"] != "verificada" else None
    pair_k = frozenset((c["a"], c["b"]))
    if (k and k in seen) or pair_k in seen:
        continue
    seen |= {k, pair_k} - {None}
    corr_ok.append(c)
corr = corr_ok

# --------------------------------------------------------------------------- vecinas por línea
nb = defaultdict(lambda: defaultdict(Counter))   # sid -> line -> Counter((hacia, siguiente))
for p in patterns:
    seq = p["seq"]
    term = p["anden"] or stations[seq[-1]]["name"]
    for i in range(len(seq) - 1):
        nb[seq[i]][p["line"]][(term, seq[i + 1])] += p["n"]

line_meta = {}
for (net, ln), L in lines.items():
    pats = [p for p in patterns if p["net"] == net and p["line"] == ln]
    main = max(pats, key=lambda p: (len(p["seq"]), p["n"]))
    seq = main["seq"]
    if main["circ"]:
        seq = seq[:-1]
    name = "Circular" if main["circ"] else f'{stations[seq[0]]["name"]} – {stations[seq[-1]]["name"]}'
    others = []
    covered = set(seq)
    for p in sorted(pats, key=lambda p: -p["n"]):
        extra_st = [s for s in p["seq"] if s not in covered]
        if extra_st:
            others.append([stations[s]["name"] for s in p["seq"]])
            covered |= set(p["seq"])
    length = sum(g.length for g in line_utm[(net, ln)]) / 1000
    line_meta[f"{net}:{ln}"] = dict(net=net, id=ln, nombre=name, color=L["color"], texto=L["text"], circular=main["circ"],
                                    estaciones=seq, otros_servicios=others, km=round(length, 1),
                                    fuente_nombre=L["long"], viajes_autobus=L["bus_trips"])

# municipio y distrito de cada estación: los asigna build_boundaries.py con los límites definitivos
# --------------------------------------------------------------------------- salidas
order = {"metro": 0, "ml": 1, "cercanias": 2}


def lkey(ln):
    import re
    m = re.match(r"([A-Z]*)(\d+)([A-Za-z]*)", ln)
    return (m.group(1), int(m.group(2)), m.group(3)) if m else (ln, 99, "")


rows = []
for (net, ln), L in lines.items():
    assert len(L["shapes"]) == len(L["shape_ids"]), (net, ln)
    for g, sid in zip(L["shapes"], L["shape_ids"]):
        rows.append(dict(net=net, line=ln, color=L["color"], texto=L["text"], shape=sid,
                         sort=order[net] * 100 + lkey(ln)[1], geometry=g))
write_geojson(OUT / "lineas.geojson", gpd.GeoDataFrame(rows, crs=4326))

corr_of = defaultdict(set)
for c in corr:
    corr_of[c["a"]].add(c["b"])
    corr_of[c["b"]].add(c["a"])

st_rows, meta_st = [], {}
for k, s in stations.items():
    ls = sorted(s["lines"], key=lkey)
    other = sorted({ln2 for o in corr_of[k] for ln2 in stations[o]["lines"]}, key=lkey)
    ntr = len(ls) + len(other)
    rank = 3 if ntr >= 3 else 2 if ntr == 2 else 1
    terminal = any(seq and (seq[0] == k or seq[-1] == k) for seq in (lm["estaciones"] for lm in line_meta.values() if lm["net"] == s["net"]))
    # misma estación con dos redes y mismo nombre (p. ej. Sol): se rotula una sola vez (la de Metro)
    dup = s["net"] != "metro" and any(stations[o]["net"] == "metro" and key_tokens(stations[o]["name"]) == key_tokens(s["name"])
                                      and Point(stations[o]["xy"]).distance(Point(s["xy"])) < 150 for o in corr_of[k])
    st_rows.append(dict(id=k, name=s["name"], net=s["net"], lines="|" + "|".join(ls) + "|", nlines=len(ls), nolbl=int(dup),
                        transfer=int(ntr >= 2), rank=rank + (1 if terminal and rank == 1 else 0),
                        geometry=Point(s["xy"])))
    meta_st[k] = dict(nombre=s["name"], red=s["net"], lineas=ls, municipio=None, distrito=None,
                      grupo=s["grupo"], coord=[round(s["lon"], 6), round(s["lat"], 6)], accesos=s["accesos"],
                      correspondencias=sorted(corr_of[k]), nombre_gtfs=s["gtfs_name"], nombre_fuente=s["name_src"],
                      vecinas={ln: [{"hacia": t, "siguiente": stations[n]["name"], "id": n} for (t, n), _ in c.most_common()]
                               for ln, c in nb[k].items()})
write_geojson(OUT / "estaciones.geojson", gpd.GeoDataFrame(st_rows, crs=UTM))

prow = []
for r in plat.itertuples():
    s = st_rows_by = None
    meta = meta_st[r.sid]
    ntr = len(meta["lineas"]) + len({x for o in meta["correspondencias"] for x in meta_st[o]["lineas"]})
    prow.append(dict(sid=r.sid, net=r.net, line=r.line, color=lines[(r.net, r.line)]["color"], transfer=int(ntr >= 2),
                     geometry=r.geometry))
pl_gdf = gpd.GeoDataFrame(prow, crs=UTM)
write_geojson(OUT / "andenes.geojson", pl_gdf)

# enlaces: pasillos entre andenes separados de una misma estación + correspondencias entre redes
erows = []
for sid, g in pl_gdf.groupby("sid"):
    pts = list(dict.fromkeys((round(p.x, 1), round(p.y, 1)) for p in g.geometry))
    for a, b in zip(pts, pts[1:]):
        if Point(a).distance(Point(b)) > 25:
            erows.append(dict(tipo="pasillo", a=sid, b=sid, geometry=LineString([a, b])))
for c in corr:
    pa = pl_gdf[pl_gdf.sid == c["a"]].geometry
    pb = pl_gdf[pl_gdf.sid == c["b"]].geometry
    a, b = min(((x, y) for x in pa for y in pb), key=lambda t: t[0].distance(t[1]))
    erows.append(dict(tipo="correspondencia", a=c["a"], b=c["b"], dist=c["dist"], geometry=LineString([a, b])))
write_geojson(OUT / "enlaces.geojson", gpd.GeoDataFrame(erows, crs=UTM))

write_json(OUT / "red.json", {
    "redes": {k: v["label"] for k, v in NET.items()},
    "lineas": dict(sorted(line_meta.items(), key=lambda kv: (order[kv[1]["net"]], lkey(kv[1]["id"])))),
    "estaciones": meta_st,
})
write_json(ROOT / "docs" / "datos" / "correspondencias.json",
           [dict(c, a_nombre=stations[c["a"]]["name"], b_nombre=stations[c["b"]]["name"],
                 a_red=stations[c["a"]]["net"], b_red=stations[c["b"]]["net"]) for c in corr], pretty=True)
write_json(ROOT / "docs" / "datos" / "nombres_estaciones.json",
           sorted([dict(id=k, gtfs=s["gtfs_name"], nombre=s["name"], fuente=s["name_src"]) for k, s in stations.items()],
                  key=lambda x: x["fuente"]), pretty=True)

write_json(ROOT / "docs" / "datos" / "cercanias_ajuste_vias.json", rail_report, pretty=True)
cnt = Counter(s["net"] for s in stations.values())
print("estaciones:", dict(cnt), " líneas:", Counter(n for n, _ in lines), " correspondencias:", len(corr))
print("nombres:", Counter(s["name_src"] for s in stations.values()))
