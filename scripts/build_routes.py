#!/usr/bin/env python3
"""Itinerarios del Mapa 2: Metro Carabanchel Alto ⇄ Cristo Social Club (C/ de Juan Bravo, 35).

Todo se calcula con datos, nada se dibuja a mano:
  · tiempos de viaje entre estaciones: stop_times del GTFS de Metro (CRTM);
  · esperas: mitad del intervalo de frequencies.txt para la franja horaria de cada escenario;
  · autobuses (SC1/SC2 sustitutivos de la L6, búhos N2/N17): GTFS de EMT Madrid;
  · trayectos a pie: camino más corto por la red peatonal de OpenStreetMap (Overture), desde/hasta los
    accesos oficiales de las estaciones (GTFS CRTM) y el portal oficial de Juan Bravo 35 (CartoCiudad);
  · trazado de cada tramo: geometría de public/data/lineas.geojson (Metro) o shapes.txt (EMT).
Salida: public/data/itinerarios.json y public/data/itinerarios.geojson
"""
import json
import math
import sys
from collections import defaultdict

import geopandas as gpd
import networkx as nx
import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as pads
from shapely.geometry import LineString, Point
from shapely.ops import substring
from shapely.strtree import STRtree

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import OUT, RAW, UTM, norm, write_json  # noqa: E402

WALK = 75.0            # m/min (4,5 km/h), velocidad de planificación habitual
STAIRS_MIN = 1.0       # minuto añadido por escaleras/ascensores en cada entrada, salida o transbordo
INDOOR_DETOUR = 1.3    # factor de rodeo de los pasillos respecto a la distancia en línea recta
TO_UTM = lambda lon, lat: gpd.GeoSeries([Point(lon, lat)], crs=4326).to_crs(UTM).iloc[0]  # noqa: E731
red = json.load(open(OUT / "red.json", encoding="utf-8"))
EST = red["estaciones"]
sid_by_name = {norm(v["nombre"]): k for k, v in EST.items() if v["red"] == "metro"}


def S(name):
    return sid_by_name[norm(name)]


# ------------------------------------------------------------------ origen y destino (verificados)
ad = gpd.read_parquet(RAW / "overture" / "addresses_salamanca.parquet")
portal = ad[(ad.street.str.upper() == "CALLE JUAN BRAVO") & (ad.number == "35")]
assert len(portal) == 1, "portal Juan Bravo 35 no encontrado"
pl = gpd.read_parquet(RAW / "overture" / "places_salamanca.parquet")
pl["nm"] = pl.names.apply(lambda n: n.get("primary") if n is not None else None)
poi = pl[pl.nm == "Cristo Social Club"]
assert len(poi) == 1
V = portal.geometry.iloc[0]
V_utm = TO_UTM(V.x, V.y)
poi_d = round(TO_UTM(poi.geometry.iloc[0].x, poi.geometry.iloc[0].y).distance(V_utm))
assert poi_d < 40, "el POI y el portal no coinciden"
DEST = dict(nombre="Cristo Social Club", direccion="Calle de Juan Bravo, 35 · 28006 Madrid", distrito="Salamanca",
            coord=[round(V.x, 6), round(V.y, 6)], coord_poi=[round(poi.geometry.iloc[0].x, 6), round(poi.geometry.iloc[0].y, 6)],
            dist_poi_portal_m=poi_d,
            verificacion=[
                "Portal oficial «CALLE JUAN BRAVO 35, 28006» (CartoCiudad/IGN vía OpenAddresses, Overture addresses 2026-10-21).",
                "Establecimiento «Cristo Social Club», Calle de Juan Bravo, 35, 28006 (Overture places, fuente Meta), a %d m del portal." % poi_d,
                "Mismo local que los anteriores «Marusha Society» y «ALMONTE sala rociera» (misma dirección en Overture places).",
                "Dirección coincidente en Venuu, VenuesPlace, DiscoMadrid, Apple Maps, Resident Advisor y DICE (búsqueda web 05/11/2026)."],
            horario="Según DiscoMadrid: jueves 23:59–05:30; viernes y sábado 23:59–06:00 (fuente secundaria; confírmalo con la sala).")
ORIG_SID = S("Carabanchel Alto")
ORIG = dict(nombre="Carabanchel Alto", sid=ORIG_SID, lineas=EST[ORIG_SID]["lineas"], coord=EST[ORIG_SID]["coord"],
            municipio=EST[ORIG_SID]["municipio"], distrito=EST[ORIG_SID]["distrito"], accesos=EST[ORIG_SID]["accesos"])
assert ORIG["lineas"] == ["11"], f"Carabanchel Alto debería ser sólo L11: {ORIG['lineas']}"

# ------------------------------------------------------------------ red peatonal (OSM vía Overture)
WALKABLE = {"footway": 1.0, "pedestrian": 1.0, "steps": 1.1, "path": 1.05, "living_street": 1.0, "cycleway": 1.1,
            "residential": 1.12, "service": 1.15, "unclassified": 1.15, "tertiary": 1.2, "secondary": 1.25, "primary": 1.3}
BOXES = [(-3.705, 40.412, -3.660, 40.446), (-3.765, 40.362, -3.705, 40.392)]  # Salamanca–Cibeles y Carabanchel–Plaza Elíptica


def load_walk():
    dset = pads.dataset(RAW / "overture" / "segments.parquet")
    f = lambda k: pc.field("bbox", k)  # noqa: E731
    tabs = []
    for xmin, ymin, xmax, ymax in BOXES:
        flt = (f("xmin") <= xmax) & (f("xmax") >= xmin) & (f("ymin") <= ymax) & (f("ymax") >= ymin)
        tabs.append(dset.to_table(filter=flt, columns=["id", "class", "subclass", "names", "connectors", "road_flags", "access_restrictions", "geometry"]).to_pandas())
    s = pd.concat(tabs).drop_duplicates("id")
    s = s[s["class"].isin(WALKABLE)]
    s = gpd.GeoDataFrame(s, geometry=gpd.GeoSeries.from_wkb(s.geometry), crs=4326).to_crs(UTM)

    def denied(ar):
        """Prohibido a peatones en todo el tramo. Las restricciones con «heading» son sentidos únicos para
        vehículos y no afectan a quien camina; las condicionales (horario, vehículo…) tampoco se aplican."""
        for a in ar if ar is not None else []:
            if a["access_type"] != "denied" or a["between"] is not None:
                continue
            w = a["when"]
            if w is None:
                return True
            if w.get("heading") is not None or any(w.get(k) is not None for k in ("during", "using", "recognized", "vehicle")):
                continue
            m = list(w.get("mode")) if w.get("mode") is not None else []
            if not m or "foot" in m:
                return True
        return False

    def tunnel(fl):
        return fl is not None and any(e["between"] is None and "is_tunnel" in list(e["values"]) for e in fl)
    s = s[~s.access_restrictions.apply(denied) & ~s.road_flags.apply(tunnel)]
    G, edges, xy = nx.Graph(), [], {}
    for geom, cons, cls, nm, sub in zip(s.geometry, s.connectors, s["class"], s.names, s.subclass):
        cons = sorted(cons, key=lambda c: c["at"])
        L = geom.length
        name = nm.get("primary") if nm is not None else None
        for c1, c2 in zip(cons, cons[1:]):
            seg = substring(geom, c1["at"] * L, c2["at"] * L)
            if seg.geom_type != "LineString" or seg.length == 0:
                continue
            c = list(seg.coords)
            c[0] = xy.setdefault(c1["connector_id"], c[0])
            c[-1] = xy.setdefault(c2["connector_id"], c[-1])
            seg = LineString(c)
            G.add_edge(c1["connector_id"], c2["connector_id"], length=seg.length, w=seg.length * WALKABLE[cls], geom=seg, name=name, cls=cls,
                       cruce=sub == "crosswalk")
            edges.append((c1["connector_id"], c2["connector_id"]))
    # sólo componentes grandes: evita fijar un punto a un tramo aislado (interiores, aceras sueltas)
    big = set().union(*[c for c in nx.connected_components(G) if len(c) > 500])
    G = G.subgraph(big).copy()
    edges = [(u, v) for u, v in edges if u in big and v in big and G.has_edge(u, v)]
    return G, edges, STRtree([G[u][v]["geom"] for u, v in edges]), xy


WG, WEDGES, WTREE, WXY = load_walk()
print("red peatonal:", WG.number_of_nodes(), "nodos", WG.number_of_edges(), "tramos")


def snap(p):
    """Inserta un nodo en el tramo peatonal más cercano al punto (proyección perpendicular)."""
    u, v = WEDGES[WTREE.nearest(p)]
    d = WG[u][v]
    g = d["geom"]
    x = g.project(p)
    nid = f"p{p.x:.1f},{p.y:.1f}"
    if nid in WG:
        return nid, g.distance(p)
    c0 = list(g.coords)
    a = substring(g, 0, x) if x > 0 else None
    b = substring(g, x, g.length) if x < g.length else None
    q = g.interpolate(x)
    WXY[nid] = (q.x, q.y)
    start = u if c0[0] == WXY[u] else v
    end = v if start == u else u
    for (n1, part) in ((start, a), (end, b)):
        if part is not None and part.geom_type == "LineString" and part.length > 0:
            WG.add_edge(n1, nid, length=part.length, w=part.length * d["w"] / d["length"], geom=part, name=d["name"], cls=d["cls"], cruce=d["cruce"])
    return nid, g.distance(p)


NAMED = [(u, v) for u, v in WEDGES if WG[u][v]["name"] and WG[u][v]["cls"] not in ("footway", "steps", "path")]
NTREE = STRtree([WG[u][v]["geom"] for u, v in NAMED])
WIND = ["el este", "el noreste", "el norte", "el noroeste", "el oeste", "el suroeste", "el sur", "el sureste"]
SIDE = ["este", "norte", "oeste", "sur"]


def street_of(seg):
    """Calle de referencia de un tramo sin nombre (acera, paso de peatones) y lado de la calzada."""
    m = seg.interpolate(0.5, normalized=True)
    u, v = NAMED[NTREE.nearest(m)]
    road = WG[u][v]["geom"]
    if road.distance(m) > 30:
        return None, None
    q = road.interpolate(road.project(m))
    ang = math.degrees(math.atan2(m.y - q.y, m.x - q.x)) % 360
    return WG[u][v]["name"], (SIDE[int(((ang + 45) % 360) // 90)] if q.distance(m) > 3 else None)


def bearing(a, b):
    return WIND[int(((math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 360) + 22.5) // 45) % 8]


def walk(p_from, p_to):
    """Ruta a pie por la red OSM: (geometría, metros, indicaciones). Las indicaciones agrupan tramos por calle,
    indicando sentido de la marcha, acera y pasos de peatones."""
    a, da = snap(p_from)
    b, db = snap(p_to)
    nodes = nx.shortest_path(WG, a, b, weight="w")
    coords, length, groups = [(p_from.x, p_from.y)], da + db, []
    for n1, n2 in zip(nodes, nodes[1:]):
        d = WG[n1][n2]
        c = list(d["geom"].coords)
        if c[0] != WXY[n1]:
            c = c[::-1]
        coords += c
        length += d["length"]
        name, side = (d["name"], None) if d["name"] and d["cls"] not in ("footway", "path") else street_of(d["geom"])
        key = ("cruce" if d["cruce"] else "tramo", name)
        if groups and groups[-1]["key"] == key:
            g = groups[-1]
            g["m"] += d["length"]
            g["end"] = c[-1]
            g["sides"].append((side, d["length"]))
        else:
            groups.append(dict(key=key, m=d["length"], start=c[0], end=c[-1], sides=[(side, d["length"])]))
    coords.append((p_to.x, p_to.y))
    # tramo corto con otro nombre entre dos de la misma calle = se cruza esa bocacalle sin cambiar de calle
    for i in range(1, len(groups) - 1):
        g, prev, nxt = groups[i], groups[i - 1], groups[i + 1]
        if g["key"][0] == "tramo" and g["m"] < 45 and prev["key"] == nxt["key"] and prev["key"][0] == "tramo" and g["key"] != prev["key"]:
            g["key"] = ("cruce", g["key"][1])
    steps = []
    for g in groups:
        kind, name = g["key"]
        if kind == "cruce":
            steps.append(f"Cruza {name} por el paso de peatones" if name else "Cruza por el paso de peatones")
        elif g["m"] >= 8:
            side = Counter_side(g["sides"])
            txt = f"Camina {round(g['m'] / 5) * 5:.0f} m hacia {bearing(g['start'], g['end'])}"
            txt += f" por {name}" if name else ""
            txt += f" (acera {side})" if side else ""
            steps.append(txt)
    streets = []
    for g in groups:
        nm = g["key"][1]
        if nm and g["key"][0] == "tramo":
            if streets and streets[-1][0] == nm:
                streets[-1][1] += g["m"]
            else:
                streets.append([nm, g["m"]])
    return LineString(coords), length, dict(calles=[(n, round(m)) for n, m in streets if m >= 10], indicaciones=steps)


def Counter_side(sides):
    tot = defaultdict(float)
    for s_, m in sides:
        if s_:
            tot[s_] += m
    return max(tot, key=tot.get) if tot and max(tot.values()) > 0.6 * sum(m for _, m in sides) else None


# ------------------------------------------------------------------ Metro: tiempos y frecuencias (GTFS CRTM)
MR = RAW / "gtfs_metro" / "extracted"
mst = pd.read_csv(MR / "stops.txt", dtype=str, encoding="utf-8-sig").set_index("stop_id")
mtr = pd.read_csv(MR / "trips.txt", dtype=str, encoding="utf-8-sig")
mtt = pd.read_csv(MR / "stop_times.txt", dtype=str, encoding="utf-8-sig")
mfq = pd.read_csv(MR / "frequencies.txt", dtype=str, encoding="utf-8-sig").merge(mtr[["trip_id", "route_id", "service_id"]], on="trip_id")
mro = pd.read_csv(MR / "routes.txt", dtype=str, encoding="utf-8-sig").set_index("route_id")
secs = lambda t: sum(int(x) * m for x, m in zip(t.split(":"), (3600, 60, 1)))  # noqa: E731


def station_of(stop):
    p = mst.at[stop, "parent_station"]
    if isinstance(p, str):
        return p
    alt = stop.replace("par_", "est_")
    return alt if alt in mst.index else stop


def line_of(r):
    return mro.at[r.route_id, "route_short_name"] + ("B" if "_B_" in r.shape_id else "")


PAT = {}   # (línea, shape) -> dict(route, sids, stops, t)
for r in mtr.drop_duplicates("shape_id").itertuples():
    s = mtt[mtt.trip_id == r.trip_id].copy()
    s["sq"] = s.stop_sequence.astype(int)
    s = s.sort_values("sq")
    t0 = secs(s.departure_time.iloc[0])
    PAT[(line_of(r), r.shape_id)] = dict(route=r.route_id, tsn=r.trip_short_name, head=r.trip_headsign,
                                         stops=list(s.stop_id), sids=[station_of(x) for x in s.stop_id],
                                         t=[secs(x) - t0 for x in s.arrival_time])


def headway(route, service, hhmm):
    t = secs(hhmm + ":00")
    f = mfq[(mfq.route_id == route) & (mfq.service_id == service)]
    for a, b, h in zip(f.start_time, f.end_time, f.headway_secs):
        if secs(a) <= t < secs(b):
            return int(h) / 60
    return None


def plat_xy(sid, line):
    """Coordenada del andén (GTFS par_) de una línea en una estación."""
    for (ln, sh), p in PAT.items():
        if ln == line and sid in p["sids"]:
            st = p["stops"][p["sids"].index(sid)]
            return TO_UTM(float(mst.at[st, "stop_lon"]), float(mst.at[st, "stop_lat"]))
    raise KeyError((sid, line))


def indoor_min(a, b):
    return a.distance(b) * INDOOR_DETOUR / WALK + STAIRS_MIN


def metro_graph(service, hhmm, closed=frozenset()):
    """Grafo de viaje: nodos andén (sid, línea) y nodos «a bordo» (sid, línea, shape). closed = tramos sin servicio."""
    G = nx.DiGraph()
    for (ln, sh), p in PAT.items():
        h = headway(p["route"], service, hhmm)
        if h is None:
            continue
        for i, sid in enumerate(p["sids"]):
            G.add_edge(("and", sid, ln), ("bordo", sid, ln, sh), w=h / 2, tipo="espera", h=h)
            G.add_edge(("bordo", sid, ln, sh), ("and", sid, ln), w=0, tipo="bajar")
            if i + 1 < len(p["sids"]) and (ln, frozenset((sid, p["sids"][i + 1]))) not in closed:
                G.add_edge(("bordo", sid, ln, sh), ("bordo", p["sids"][i + 1], ln, sh), w=(p["t"][i + 1] - p["t"][i]) / 60, tipo="viaje")
    lines_at = defaultdict(set)
    for n in G.nodes:
        if n[0] == "and":
            lines_at[n[1]].add(n[2])
    for sid, ls in lines_at.items():
        for a in ls:
            for b in ls:
                if a != b:
                    G.add_edge(("and", sid, a), ("and", sid, b), w=indoor_min(plat_xy(sid, a), plat_xy(sid, b)), tipo="transbordo")
    return G, lines_at


def arc(line, a, b, shape):
    """Tramos (pares de estaciones) de un patrón entre a y b, para declarar cortes de servicio."""
    p = PAT[(line, shape)]["sids"]
    i, j = p.index(a), p.index(b)
    seq = p[i:j + 1] if i <= j else p[i:] + p[1:j + 1]
    return {(line, frozenset(x)) for x in zip(seq, seq[1:])}


# ------------------------------------------------------------------ geometría de tramos de metro
lineas = gpd.read_file(OUT / "lineas.geojson").to_crs(UTM)
andenes = gpd.read_file(OUT / "andenes.geojson").to_crs(UTM)


def ride_geom(line, sids):
    """Trazado oficial entre andenes consecutivos (une las piezas de la línea, maneja líneas circulares)."""
    geoms = lineas[(lineas.net == "metro") & (lineas.line == line)].geometry.tolist()
    pts = [andenes[(andenes.sid == s) & (andenes.line == line)].geometry.iloc[0] for s in sids]
    out = []
    for a, b in zip(pts, pts[1:]):
        g = min(geoms, key=lambda g: g.distance(a) + g.distance(b))
        x, y = g.project(a), g.project(b)
        circ = Point(g.coords[0]).distance(Point(g.coords[-1])) < 50
        if circ and abs(y - x) > g.length / 2:   # el tramo corto cruza el origen del anillo
            seg = list(substring(g, x, g.length).coords) + list(substring(g, 0, y).coords) if x > y else \
                list(substring(g, x, 0).coords) + list(substring(g, g.length, y).coords)
        else:
            seg = list(substring(g, x, y).coords)
        out += seg if not out else seg[1:]
    return LineString(out)


# ------------------------------------------------------------------ EMT (autobús) para escenarios nocturnos
ER = RAW / "gtfs_emt" / "extracted"
est = pd.read_csv(ER / "stops.txt", dtype=str).set_index("stop_id")
etr = pd.read_csv(ER / "trips.txt", dtype=str)
eru = pd.read_csv(ER / "routes.txt", dtype=str).set_index("route_id")
efq = pd.read_csv(ER / "frequencies.txt", dtype=str).merge(etr[["trip_id", "route_id", "service_id", "direction_id"]], on="trip_id")
ett = None
esh = None


def emt_leg(route_short, direction, board, alight, service, hhmm):
    global ett, esh
    if ett is None:
        ett = pd.read_csv(ER / "stop_times.txt", dtype=str, usecols=["trip_id", "stop_id", "stop_sequence", "arrival_time"])
        esh = pd.read_csv(ER / "shapes.txt", dtype=str)
    rid = eru.index[eru.route_short_name == route_short][0]
    t = etr[(etr.route_id == rid) & (etr.direction_id == direction) & (etr.service_id == service)]
    assert len(t), f"{route_short}: sin viajes {service}/{direction}"
    trip = t.iloc[0]
    s = ett[ett.trip_id == trip.trip_id].copy()
    s["sq"] = s.stop_sequence.astype(int)
    s = s.sort_values("sq")
    ids = list(s.stop_id)
    i, j = ids.index(board), ids.index(alight)
    assert i < j, f"{route_short}: {board} no está antes que {alight}"
    tt = [secs(x) for x in s.arrival_time]
    f = efq[(efq.route_id == rid) & (efq.service_id == service) & (efq.direction_id == direction)]
    h = next((int(x) / 60 for a, b, x in zip(f.start_time, f.end_time, f.headway_secs) if secs(a) <= secs(hhmm + ":00") <= secs(b)), None)
    shp = esh[esh.shape_id == trip.shape_id].copy()
    shp["sq"] = shp.shape_pt_sequence.astype(int)
    g = gpd.GeoSeries([LineString(list(zip(shp.sort_values("sq").shape_pt_lon.astype(float), shp.sort_values("sq").shape_pt_lat.astype(float))))], crs=4326).to_crs(UTM).iloc[0]
    pa, pb = (TO_UTM(float(est.at[x, "stop_lon"]), float(est.at[x, "stop_lat"])) for x in (board, alight))
    geom = substring(g, g.project(pa), g.project(pb))
    return dict(tipo="bus", linea=route_short, color="#" + eru.at[rid, "route_color"], direccion=trip.trip_headsign,
                desde=est.at[board, "stop_name"], desde_id=board, hasta=est.at[alight, "stop_name"], hasta_id=alight,
                paradas=[est.at[x, "stop_name"] for x in ids[i:j + 1]], min=round((tt[j] - tt[i]) / 60, 1),
                coords=[[round(float(est.at[x, "stop_lon"]), 6), round(float(est.at[x, "stop_lat"]), 6)] for x in ids[i:j + 1]],
                n_paradas=j - i,
                intervalo_min=h, espera_min=round(h / 2, 1) if h else None, servicio=service, _geom=geom,
                _pa=pa, _pb=pb, block=trip.block_id)


# ------------------------------------------------------------------ construcción de itinerarios
FEATURES = []


def feat(it_id, i, kind, geom, color, **props):
    g = gpd.GeoSeries([geom], crs=UTM).to_crs(4326).iloc[0]
    FEATURES.append({"type": "Feature", "geometry": json.loads(gpd.GeoSeries([g]).to_json())["features"][0]["geometry"],
                     "properties": dict(it=it_id, paso=i, tipo=kind, color=color, **props)})


def access_xy(a):
    return TO_UTM(*a["coord"])


def walk_back(g, info):
    """Indicaciones del camino inverso (de la sala a la estación): se recalcula en ese sentido."""
    _, _, inv = walk(Point(g.coords[-1]), Point(g.coords[0]))
    return inv


WALKS = {}


def access_walk(sid, a):
    """Recorrido a pie real (red OSM) entre un acceso oficial y el portal de Juan Bravo 35 (con caché)."""
    k = (sid, a["id"])
    if k not in WALKS:
        WALKS[k] = walk(access_xy(a), V_utm)
    return WALKS[k]


def choose_access(sid, line):
    """Acceso que minimiza pasillo desde el andén de esa línea + calle hasta la sala (no el más cercano en línea recta)."""
    best = None
    for a in EST[sid]["accesos"]:
        g, m, info = access_walk(sid, a)
        cost = indoor_min(plat_xy(sid, line), access_xy(a)) + m / WALK
        if best is None or cost < best[1]:
            best = (a, cost, g, m, info)
    return best


def metro_path(service, hhmm, origins, dests, closed=frozenset()):
    """Mejor recorrido (Dijkstra sobre tiempos GTFS). origins/dests: {(sid, línea): minutos de acceso/salida}."""
    G, lines_at = metro_graph(service, hhmm, closed)
    src, dst = ("src",), ("dst",)
    for (sid, ln), w in origins.items():
        if ln in lines_at[sid]:
            G.add_edge(src, ("and", sid, ln), w=w)
    for (sid, ln), w in dests.items():
        if ln in lines_at[sid]:
            G.add_edge(("and", sid, ln), dst, w=w)
    nodes = nx.shortest_path(G, src, dst, weight="w")
    legs, cur = [], None
    for a, b in zip(nodes, nodes[1:]):
        e = G[a][b]
        if e.get("tipo") == "espera":
            cur = dict(tipo="metro", linea=b[2], shape=b[3], sids=[b[1]], min=0, espera_min=e["w"], intervalo_min=e["h"])
        elif e.get("tipo") == "viaje":
            cur["sids"].append(b[1])
            cur["min"] += e["w"]
        elif e.get("tipo") == "bajar" and cur:
            legs.append(cur)
            cur = None
        elif e.get("tipo") == "transbordo":
            legs.append(dict(tipo="transbordo", sid=a[1], de=a[2], a=b[2], min=round(e["w"], 1)))
    return legs


def venue_side(closed_lines=()):
    """{(sid, línea): coste} de las estaciones candidatas junto a la sala."""
    return {(sid, ln): choose_access(sid, ln)[1] for sid in near_stations for ln in EST[sid]["lineas"] if ln not in closed_lines}


def describe_metro(leg):
    p = PAT[(leg["linea"], leg["shape"])]
    names = [EST[s]["nombre"] for s in leg["sids"]]
    tsn = p["tsn"] or ""
    if "ANDEN" in tsn:          # líneas circulares (L6, L12): el sentido se indica por andén y próximas estaciones
        hacia = "Andén " + tsn.split("ANDEN")[-1].strip(" -)")
        direction = f"sentido {', '.join(names[1:4])}… (línea circular)"
    else:
        hacia = EST[p["sids"][-1]]["nombre"]
        direction = f"dirección {hacia}"
    lm = red["lineas"][f"metro:{leg['linea']}"]
    return dict(tipo="metro", linea=leg["linea"], color=lm["color"], texto=lm["texto"], direccion=direction, hacia=hacia,
                desde=names[0], hasta=names[-1], desde_id=leg["sids"][0], hasta_id=leg["sids"][-1], paradas=names, ids=leg["sids"],
                n_paradas=len(names) - 1, min=round(leg["min"], 1), espera_min=round(leg["espera_min"], 1),
                intervalo_min=leg["intervalo_min"])


def build(it_id, titulo, cuando, service, hhmm, start, end, closed=frozenset(), notas=()):
    """start/end: ('station', sid) o ('venue',)."""
    pasos = []
    orig_in = {(ORIG_SID, ln): indoor_min(access_xy(ORIG["accesos"][0]), plat_xy(ORIG_SID, ln)) for ln in ORIG["lineas"]}
    if start[0] == "station":            # IDA
        legs = metro_path(service, hhmm, orig_in, venue_side(), closed)
    else:                                # VUELTA
        legs = metro_path(service, hhmm, venue_side(), orig_in, closed)
    # ---- etapas
    total = 0
    walk_m = 0
    if start[0] == "station":
        a0 = EST[start[1]]["accesos"][0]
        t_in = indoor_min(access_xy(a0), plat_xy(start[1], legs[0]["linea"]))
        pasos.append(dict(tipo="inicio", texto=f"Entra en la estación de Metro {EST[start[1]]['nombre']} (Línea {legs[0]['linea']}).",
                          lugar=EST[start[1]]["nombre"], coord=EST[start[1]]["coord"], min=round(t_in, 1),
                          nota="El GTFS sólo publica el acceso por ascensor (" + a0["dir"] + "); el resto de bocas no figuran en los datos oficiales."))
        total += t_in
    else:
        sid0 = legs[0]["sids"][0]
        a, _, g, m, streets = choose_access(sid0, legs[0]["linea"])
        pasos.append(dict(tipo="inicio", texto="Sal de Cristo Social Club (Calle de Juan Bravo, 35).", lugar="Cristo Social Club", coord=DEST["coord"], min=0))
        pasos.append(dict(tipo="pie", desde="Cristo Social Club", hasta=f"Acceso «{a['nombre']}» de {EST[sid0]['nombre']}",
                          m=round(m), min=round(m / WALK, 1), **walk_back(g, streets), acceso=a))
        feat(it_id, len(pasos) - 1, "pie", LineString(list(g.coords)[::-1]), "#E6007E")
        walk_m += m
        total += m / WALK
        t_in = indoor_min(access_xy(a), plat_xy(sid0, legs[0]["linea"]))
        pasos.append(dict(tipo="entrada", texto=f"Entra por el acceso «{a['nombre']}» ({a['dir']}) y baja al andén de la Línea {legs[0]['linea']}.",
                          min=round(t_in, 1), lugar=EST[sid0]["nombre"]))
        total += t_in
    for leg in legs:
        if leg["tipo"] == "metro":
            d = describe_metro(leg)
            pasos.append(d)
            feat(it_id, len(pasos) - 1, "metro", ride_geom(leg["linea"], leg["sids"]), d["color"], linea=leg["linea"])
            total += d["min"] + d["espera_min"]
        else:
            pasos.append(dict(tipo="transbordo", lugar=EST[leg["sid"]]["nombre"], de=leg["de"], a=leg["a"], min=leg["min"],
                              coord=EST[leg["sid"]]["coord"],
                              texto=f"En {EST[leg['sid']]['nombre']} baja del tren y sigue los indicadores «Línea {leg['a']}» (correspondencia dentro de la estación)."))
            total += leg["min"]
    if end[0] == "venue":
        sid_f = legs[-1]["sids"][-1]
        a, _, g, m, streets = choose_access(sid_f, legs[-1]["linea"])
        t_out = indoor_min(plat_xy(sid_f, legs[-1]["linea"]), access_xy(a))
        pasos.append(dict(tipo="salida", lugar=EST[sid_f]["nombre"], min=round(t_out, 1), acceso=a,
                          texto=f"Sal por el acceso «{a['nombre']}» ({a['dir']})."))
        pasos.append(dict(tipo="pie", desde=f"Acceso «{a['nombre']}»", hasta="Cristo Social Club (Juan Bravo, 35)", m=round(m),
                          min=round(m / WALK, 1), **streets, acceso=a))
        feat(it_id, len(pasos) - 1, "pie", g, "#E6007E")
        walk_m += m
        total += t_out + m / WALK
        pasos.append(dict(tipo="fin", texto="Llegada a Cristo Social Club, Calle de Juan Bravo, 35 (acera de los números impares).",
                          lugar="Cristo Social Club", coord=DEST["coord"]))
    else:
        sid_f = legs[-1]["sids"][-1]
        t_out = indoor_min(plat_xy(sid_f, legs[-1]["linea"]), access_xy(EST[sid_f]["accesos"][0]))
        pasos.append(dict(tipo="fin", texto=f"Llegada a la estación {EST[sid_f]['nombre']}.", lugar=EST[sid_f]["nombre"],
                          coord=EST[sid_f]["coord"], min=round(t_out, 1)))
        total += t_out
    return dict(id=it_id, titulo=titulo, cuando=cuando, servicio=service, hora_ref=hhmm, total_min=round(total), a_pie_m=round(walk_m),
                transbordos=sum(1 for p in pasos if p["tipo"] == "transbordo"), pasos=pasos, notas=list(notas))


# estaciones candidatas: todas las de Metro con algún acceso a ≤1,2 km en línea recta del portal
near_stations = [k for k, v in EST.items() if v["red"] == "metro" and v["accesos"] and
                 min(access_xy(a).distance(V_utm) for a in v["accesos"]) < 1200]
print("estaciones candidatas:", [EST[s]["nombre"] for s in near_stations])

# comparativa de estaciones de acceso (justifica la elección): IDA, viernes 23:30
comp = []
orig_in0 = {(ORIG_SID, ln): indoor_min(access_xy(ORIG["accesos"][0]), plat_xy(ORIG_SID, ln)) for ln in ORIG["lineas"]}
for sid in near_stations:
    dests = {(sid, ln): choose_access(sid, ln)[1] for ln in EST[sid]["lineas"]}
    legs = metro_path("4_I15", "23:30", orig_in0, dests)
    ln = legs[-1]["linea"]
    a, cost, g, m, info = choose_access(sid, ln)
    ride = sum(l.get("min", 0) + l.get("espera_min", 0) for l in legs) + orig_in0[(ORIG_SID, "11")]
    straight = min(access_xy(x).distance(V_utm) for x in EST[sid]["accesos"])
    comp.append(dict(estacion=EST[sid]["nombre"], sid=sid, lineas=EST[sid]["lineas"], llegada_linea=ln, acceso=a["nombre"], acceso_dir=a["dir"],
                     linea_recta_m=round(straight), a_pie_m=round(m), a_pie_min=round(m / WALK, 1), pasillo_min=round(cost - m / WALK, 1),
                     metro_desde_origen_min=round(ride, 1), transbordos=sum(1 for l in legs if l["tipo"] == "transbordo"),
                     total_min=round(ride + cost, 1)))
comp.sort(key=lambda c: c["total_min"])

# ------------------------------------------------------------------ escenarios
pe, ab, cu = S("Plaza Elíptica"), S("Arganzuela-Planetario"), S("Ciudad Universitaria")
SH1 = next(sh for (ln, sh) in PAT if ln == "6" and "_1_" in sh)
SH2 = next(sh for (ln, sh) in PAT if ln == "6" and "_2_" in sh)
CORTE_L6 = arc("6", ab, cu, SH1) | arc("6", cu, ab, SH2)    # Arganzuela-Planetario ↔ Ciudad Universitaria por Avda. de América
nota_corte = ("Metro de Madrid suspende la L6 entre Arganzuela-Planetario y Ciudad Universitaria (por Avenida de América) "
              "del 7 al 9 y el 21 y 22 de noviembre de 2026 (pruebas de conducción automática); ambas estaciones abiertas como cabeceras "
              "provisionales y autobús gratuito SE6. Fuente: nota de prensa de Metro de Madrid, 03/11/2026.")
nota_noche = ("La L6 cierra a las 23:00 de domingo a jueves desde el 11/01/2026 (obras de automatización); la sustituyen los autobuses "
              "gratuitos SC1 y SC2 de 23:00 a 1:30. Viernes y sábado mantiene el horario habitual (6:00–1:30).")
nota_metro = "Horario general de Metro: 6:00–1:30 todos los días (CRTM). Entre la 1:30 y las 6:00 no hay metro."

IT = {"ida": [], "vuelta": []}
IT["ida"].append(build("ida", "Recomendada", "Cualquier día hasta las 23:00 · viernes y sábado hasta la 1:30",
                       "4_I15", "23:30", ("station", ORIG_SID), ("venue",), notas=[nota_metro]))
IT["ida"].append(build("ida_corte_l6", "Si la L6 está cortada (7–9 y 21–22 nov 2026)", "Fechas del corte parcial de la L6",
                       "4_I12", "23:30", ("station", ORIG_SID), ("venue",), CORTE_L6, notas=[nota_corte]))
IT["vuelta"].append(build("vuelta", "Recomendada", "Con metro en servicio: hasta la 1:30 o desde las 6:00 (al cierre de la sala)",
                          "4_I12", "06:15", ("venue",), ("station", ORIG_SID), notas=[nota_metro]))
IT["vuelta"].append(build("vuelta_corte_l6", "Si la L6 está cortada (7–9 y 21–22 nov 2026)", "Fechas del corte parcial de la L6",
                          "4_I13", "06:15", ("venue",), ("station", ORIG_SID), CORTE_L6, notas=[nota_corte]))


# ---- escenarios con autobús (GTFS EMT): IDA domingo–jueves desde las 23:00 (SC1) y VUELTA nocturna (N2 + N17)
def bus_itinerary(it_id, titulo, cuando, steps, notas):
    """steps: lista de ('pie', p_from, p_to, desde, hasta) | ('bus', leg) | ('metro', line, sids, service, hhmm) | ('texto', dict)."""
    pasos, total, walk_m = [], 0, 0
    for st in steps:
        if st[0] == "pie":
            g, m, streets = walk(st[1], st[2])
            pasos.append(dict(tipo="pie", desde=st[3], hasta=st[4], m=round(m), min=round(m / WALK, 1), **streets))
            feat(it_id, len(pasos) - 1, "pie", g, "#E6007E")
            total += m / WALK
            walk_m += m
        elif st[0] == "bus":
            leg = {k: v for k, v in st[1].items() if not k.startswith("_")}
            pasos.append(leg)
            feat(it_id, len(pasos) - 1, "bus", st[1]["_geom"], leg["color"], linea=leg["linea"])
            total += leg["min"] + (leg["espera_min"] or 0)
        elif st[0] == "metro":
            line, sids, service, hhmm = st[1:]
            sh = next(sh for (ln, sh), p in PAT.items() if ln == line and sids[0] in p["sids"] and sids[-1] in p["sids"]
                      and p["sids"].index(sids[0]) < p["sids"].index(sids[-1]))
            p = PAT[(line, sh)]
            i, j = p["sids"].index(sids[0]), p["sids"].index(sids[-1])
            h = headway(p["route"], service, hhmm)
            d = describe_metro(dict(linea=line, shape=sh, sids=p["sids"][i:j + 1], min=(p["t"][j] - p["t"][i]) / 60, espera_min=h / 2, intervalo_min=h))
            pasos.append(d)
            feat(it_id, len(pasos) - 1, "metro", ride_geom(line, p["sids"][i:j + 1]), d["color"], linea=line)
            total += d["min"] + d["espera_min"]
        else:
            pasos.append(st[1])
            total += st[1].get("min", 0)
    legs = sum(1 for p in pasos if p["tipo"] in ("metro", "bus"))
    same_vehicle = sum(1 for p in pasos if p["tipo"] == "cambio")   # p. ej. SC1 que continúa en Legazpi
    return dict(id=it_id, titulo=titulo, cuando=cuando, total_min=round(total), a_pie_m=round(walk_m),
                transbordos=legs - 1 - same_vehicle, pasos=pasos, notas=notas)


def stop_xy(i):
    return TO_UTM(float(est.at[i, "stop_lon"]), float(est.at[i, "stop_lat"]))


def nearest_access(sid, p):
    return min(EST[sid]["accesos"], key=lambda a: access_xy(a).distance(p))


# IDA domingo–jueves ≥23:00: L11 → Plaza Elíptica → SC1 (parada 5050) → Legazpi (sigue como SC1) → Diego de León (5296)
dl = S("Diego de León")
sc1a = emt_leg("SC1", "0", "5050", "51095", "LJ", "23:30")
sc1b = emt_leg("SC1", "1", "51095", "5296", "LJ", "23:30")
same_bus = True  # comprobado: en el GTFS de EMT los viajes SC1 «Legazpi» y «Cuatro Caminos» encadenan en el mismo bloque
pe_acc = nearest_access(pe, stop_xy("5050"))
IT["ida"].append(bus_itinerary("ida_noche_sc1", "Domingo a jueves desde las 23:00 (L6 cerrada)",
    "Domingo a jueves, 23:00–1:30 (L6 sustituida por autobús SC1)", [
        ("texto", dict(tipo="inicio", texto="Entra en la estación de Metro Carabanchel Alto (Línea 11).", lugar="Carabanchel Alto", coord=ORIG["coord"], min=round(indoor_min(access_xy(ORIG["accesos"][0]), plat_xy(ORIG_SID, "11")), 1))),
        ("metro", "11", [ORIG_SID, pe], "4_I14", "23:30"),
        ("texto", dict(tipo="salida", lugar="Plaza Elíptica", min=round(indoor_min(plat_xy(pe, "11"), access_xy(pe_acc)), 1), acceso=pe_acc,
                       texto=f"Sal a la calle por el acceso «{pe_acc['nombre']}» ({pe_acc['dir']}).")),
        ("pie", access_xy(pe_acc), stop_xy("5050"), f"Acceso «{pe_acc['nombre']}»", "Parada SC1 «Plaza Elíptica» (5050)"),
        ("bus", sc1a),
        ("texto", dict(tipo="cambio", lugar="Legazpi", min=0, texto="En Legazpi el mismo autobús continúa como SC1 hacia Cuatro Caminos (viajes encadenados en el GTFS de EMT); no hace falta cambiar de vehículo.")),
        ("bus", {**sc1b, "espera_min": 0}),
        ("pie", stop_xy("5296"), V_utm, "Parada SC1 «Diego de León» (5296, Francisco Silvela)", "Cristo Social Club (Juan Bravo, 35)"),
        ("texto", dict(tipo="fin", texto="Llegada a Cristo Social Club, Calle de Juan Bravo, 35.", lugar="Cristo Social Club", coord=DEST["coord"])),
    ], [nota_noche, "Los SC1/SC2 son gratuitos para viajeros de Metro; frecuencias del GTFS de EMT (publicado 03/11/2026)."]))

# VUELTA nocturna (1:30–6:00, sin metro): búho N2 → Cibeles → búho N17 → Metro Carabanchel Alto
n2 = emt_leg("N2", "1", "2234", "5727", "VV", "26:00")
n17 = emt_leg("N17", "0", "69", "4019", "VV", "26:00")
ca_acc = nearest_access(ORIG_SID, stop_xy("4019"))
IT["vuelta"].append(bus_itinerary("vuelta_buho", "De madrugada, sin metro (1:30–6:00)", "Noches de viernes y sábado (frecuencias del GTFS de EMT)", [
    ("texto", dict(tipo="inicio", texto="Sal de Cristo Social Club (Calle de Juan Bravo, 35).", lugar="Cristo Social Club", coord=DEST["coord"], min=0)),
    ("pie", V_utm, stop_xy("2234"), "Cristo Social Club", "Parada «Príncipe de Vergara – Diego de León» (2234)"),
    ("bus", n2),
    ("pie", stop_xy("5727"), stop_xy("69"), "Parada N2 «Cibeles» (5727)", "Parada N17 «Cibeles» (69)"),
    ("bus", n17),
    ("pie", stop_xy("4019"), access_xy(ca_acc), "Parada «Metro Carabanchel Alto» (4019)", "Estación Carabanchel Alto"),
    ("texto", dict(tipo="fin", texto="Llegada a la estación Carabanchel Alto.", lugar="Carabanchel Alto", coord=ORIG["coord"])),
], [nota_metro, "Búhos de EMT: N2 Cibeles–Valdebebas y N17 Cibeles–Carabanchel Alto. Frecuencias de madrugada de viernes y sábado del GTFS de EMT "
    "(entre semana el intervalo es de 35–40 min). También sirve el N3 desde «Metro Diego de León» hacia Cibeles."]))

# VUELTA domingo–jueves 23:00–1:30: SC2 Diego de León (786) → Legazpi (sigue) → Plaza Elíptica (2430) → L11
sc2a = emt_leg("SC2", "0", "786", "5128", "LJ", "23:30")
sc2b = emt_leg("SC2", "1", "5128", "2430", "LJ", "23:30")
pe_acc2 = nearest_access(pe, stop_xy("2430"))
IT["vuelta"].append(bus_itinerary("vuelta_noche_sc2", "Domingo a jueves de 23:00 a 1:30 (L6 cerrada)", "Domingo a jueves, 23:00–1:30", [
    ("texto", dict(tipo="inicio", texto="Sal de Cristo Social Club (Calle de Juan Bravo, 35).", lugar="Cristo Social Club", coord=DEST["coord"], min=0)),
    ("pie", V_utm, stop_xy("786"), "Cristo Social Club", "Parada SC2 «Diego de León» (786, Francisco Silvela)"),
    ("bus", sc2a),
    ("texto", dict(tipo="cambio", lugar="Legazpi", min=0, texto="En Legazpi el autobús continúa como SC2 hacia Cuatro Caminos por Usera y Plaza Elíptica.")),
    ("bus", {**sc2b, "espera_min": 0}),
    ("pie", stop_xy("2430"), access_xy(pe_acc2), "Parada SC2 «Plaza Elíptica» (2430)", f"Acceso «{pe_acc2['nombre']}» de Plaza Elíptica"),
    ("texto", dict(tipo="entrada", lugar="Plaza Elíptica", min=round(indoor_min(access_xy(pe_acc2), plat_xy(pe, "11")), 1),
                   texto="Entra en Plaza Elíptica y baja al andén de la Línea 11.")),
    ("metro", "11", [pe, ORIG_SID], "4_I14", "23:30"),
    ("texto", dict(tipo="fin", texto="Llegada a la estación Carabanchel Alto.", lugar="Carabanchel Alto", coord=ORIG["coord"])),
], [nota_noche]))

# ------------------------------------------------------------------ comprobaciones
for k, its in IT.items():
    for it in its:
        kinds = [p["tipo"] for p in it["pasos"]]
        assert kinds[0] == "inicio" and kinds[-1] == "fin", it["id"]
        for p in it["pasos"]:
            if p["tipo"] == "metro":
                assert p["n_paradas"] >= 1
            if p["tipo"] == "pie":
                assert p["m"] < 2500, (it["id"], p)
rec_ida = IT["ida"][0]
assert [p["linea"] for p in rec_ida["pasos"] if p["tipo"] == "metro"][0] == "11"

write_json(OUT / "itinerarios.json", dict(origen=ORIG, destino=DEST, comparativa_estaciones=comp, itinerarios=IT,
                                          supuestos=dict(velocidad_pie_kmh=WALK * 60 / 1000, escaleras_min=STAIRS_MIN, rodeo_pasillos=INDOOR_DETOUR,
                                                         espera="mitad del intervalo de paso (frequencies.txt) en la franja del escenario")))
write_json(OUT / "itinerarios.geojson", {"type": "FeatureCollection", "features": FEATURES})
for k, its in IT.items():
    for it in its:
        print(f"{it['id']:18s} {it['total_min']:3d} min · {it['a_pie_m']:4d} m a pie · {it['transbordos']} transb. · " +
              " → ".join(p.get("linea", "") and f"{p['tipo']}:{p['linea']}({p['desde']}→{p['hasta']})" or p["tipo"] for p in it["pasos"]))
print("comparativa:", [(c["estacion"], c["a_pie_m"], c["total_min"]) for c in comp])
