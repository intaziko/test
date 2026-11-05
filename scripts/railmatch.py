"""Ajuste ("map matching") de los recorridos de Cercanías sobre las vías reales de OpenStreetMap.

Los shapes del GTFS de Cercanías son poco densos (un punto cada ~200 m) y algunos son históricos
(p. ej. C8 hasta Guadalajara). Para dibujar el trazado exacto se calcula, entre cada par de estaciones
consecutivas de cada servicio real (stop_times), el camino más corto por el grafo ferroviario de OSM
(Overture), penalizando las vías que se alejan del shape oficial de esa línea. Así el recorrido lo
fija el GTFS oficial y la geometría fina la aporta OSM.
"""
import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString
from shapely.ops import substring
from shapely.strtree import STRtree

from common import RAW, UTM

BAD = {"is_disused", "is_abandoned", "is_under_construction"}


def build_graph(classes=("standard_gauge", "narrow_gauge", "unknown"), name=None):
    r = gpd.read_parquet(RAW / "overture" / "rail.parquet")
    r = r[r["class"].isin(classes)]
    if name:  # p. ej. sólo las vías que OSM identifica como «Línea 3»
        r = r[r.names.apply(lambda n: n is not None and n.get("primary") == name)]
    r = r[~r.rail_flags.apply(lambda fl: fl is not None and any(e["between"] is None and BAD & set(e["values"]) for e in fl))]
    r = r.to_crs(UTM)
    G = nx.Graph()
    edges, xy = [], {}
    for geom, cons in zip(r.geometry, r.connectors):
        cons = sorted(cons, key=lambda c: c["at"])
        L = geom.length
        for c1, c2 in zip(cons, cons[1:]):
            seg = substring(geom, c1["at"] * L, c2["at"] * L)
            if seg.length == 0 or c1["connector_id"] == c2["connector_id"]:
                continue
            c = list(seg.coords)  # extremos idénticos en las uniones para poder encadenar aristas
            c[0] = xy.setdefault(c1["connector_id"], c[0])
            c[-1] = xy.setdefault(c2["connector_id"], c[-1])
            seg = LineString(c)
            G.add_edge(c1["connector_id"], c2["connector_id"], length=seg.length, geom=seg)
            edges.append((c1["connector_id"], c2["connector_id"], seg))
    tree = STRtree([e[2] for e in edges])
    return G, edges, tree, xy


class Matcher:
    def __init__(self, classes=("standard_gauge", "narrow_gauge", "unknown"), k=3, name=None):
        self.G, self.edges, self.tree, self.xy = build_graph(classes, name)
        self.k = k  # vías candidatas por estación (en nudos de metro se cruzan varias líneas)

    def coords(self, a, b):
        c = list(self.G[a][b]["geom"].coords)
        return c if c[0] == self.xy[a] else c[::-1]

    def near_edges(self, p, maxd=250, k=3):
        """Aristas candidatas cerca de una estación (puede haber vías de distinto ancho que no conectan)."""
        idx = sorted(self.tree.query(p.buffer(maxd)), key=lambda i: self.edges[i][2].distance(p))
        out, seen = [], set()
        for i in idx:
            u, v, g = self.edges[i]
            if (u, v) not in seen:
                seen.add((u, v))
                out.append((u, v, g))
            if len(out) == k:
                break
        return out

    def path(self, pa, pb, guide=None):
        """Geometría por vía entre dos puntos (estaciones); guide = shape oficial para penalizar desvíos."""
        best = None
        for ea in self.near_edges(pa, k=self.k):
            for eb in self.near_edges(pb, k=self.k):
                r = self._path(pa, pb, ea, eb, guide)
                if r and (best is None or r[0] < best[0]):
                    best = r
        return best[1] if best else None

    def _path(self, pa, pb, ea, eb, guide):

        def w(u, v, d):
            if guide is None:
                return d["length"]
            m = d["geom"].interpolate(0.5, normalized=True)
            return d["length"] * (1 + 4 * min(1.0, guide.distance(m) / 200))

        best = None
        if ea[2] is eb[2]:  # ambas estaciones sobre la misma arista
            x, y = ea[2].project(pa), ea[2].project(pb)
            seg = substring(ea[2], x, y) if x <= y else substring(ea[2], y, x).reverse()
            ok = seg.geom_type == "LineString" and seg.length > 0
            return (seg.length + 20 * (ea[2].distance(pa) + eb[2].distance(pb)), seg) if ok else None
        for s in ea[:2]:
            for t in eb[:2]:
                try:
                    nodes = nx.shortest_path(self.G, s, t, weight=w)
                except nx.NetworkXNoPath:
                    continue
                ca = self.coords(ea[1] if s == ea[0] else ea[0], s)   # arista inicial terminando en s
                cb = self.coords(t, eb[1] if t == eb[0] else eb[0])   # arista final empezando en t
                mid = [c for a, b in zip(nodes, nodes[1:]) for c in self.coords(a, b)[1:]]
                line = LineString(ca + mid + cb[1:])
                x = LineString(ca).project(pa)                      # posición de la estación A en la arista inicial
                y = len(mid) and line.length - LineString(cb).length + LineString(cb).project(pb) or line.project(pb)
                if y <= x:
                    continue
                seg = substring(line, x, y)
                cost = sum(w(a, b, self.G[a][b]) for a, b in zip(nodes, nodes[1:])) + (LineString(ca).length - x) + LineString(cb).project(pb)
                cost += 20 * (ea[2].distance(pa) + eb[2].distance(pb))  # preferir la vía más próxima al andén
                if seg.length > 0 and (best is None or cost < best[0]):
                    best = (cost, seg)
        return best
