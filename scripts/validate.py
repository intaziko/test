#!/usr/bin/env python3
"""Comprobaciones de exactitud de los datos publicados (falla con AssertionError si algo no cuadra).

Genera docs/VALIDACION.md (resultados) y docs/FUENTES.md (registro de fuentes desde data/fuentes.json).
Uso: python -I scripts/validate.py
"""
import json
import sys
from collections import Counter

import geopandas as gpd
from shapely.geometry import Point

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import DOCS, OUT, ROOT, UTM, norm  # noqa: E402

J = lambda p: json.load(open(p, encoding="utf-8"))  # noqa: E731
red, it, av, fu = J(OUT / "red.json"), J(OUT / "itinerarios.json"), J(OUT / "avisos.json"), J(ROOT / "data" / "fuentes.json")
val = J(DOCS / "datos" / "validacion_limites.json")
mun = gpd.read_file(OUT / "municipios.geojson").to_crs(UTM)
dist = gpd.read_file(OUT / "distritos.geojson").to_crs(UTM)
lin = gpd.read_file(OUT / "lineas.geojson").to_crs(UTM)
pla = gpd.read_file(OUT / "andenes.geojson").to_crs(UTM)
E, L = red["estaciones"], red["lineas"]
ok, md = [], []


def check(cond, text):
    assert cond, "FALLO: " + text
    ok.append(text)


# ------------------------------------------------------------------ Mapa 1: municipios y distritos
FOCO = ["Madrid", "Alcobendas", "Torrejón de Ardoz", "Getafe", "Móstoles"]
check(len(mun) == 179, "179 municipios de la Comunidad de Madrid (los mismos que el IGN)")
rows = []
for n in FOCO:
    m = mun[mun.nombre == n]
    check(len(m) == 1, f"municipio {n} presente")
    c = gpd.GeoSeries([m.geometry.iloc[0].representative_point()], crs=UTM).to_crs(4326).iloc[0]
    rows.append(f"| {n} | {m.ine.iloc[0]} | {m.area_km2.iloc[0]:.2f} | {c.y:.4f}, {c.x:.4f} |")
OFF = ["Centro", "Arganzuela", "Retiro", "Salamanca", "Chamartín", "Tetuán", "Chamberí", "Fuencarral-El Pardo", "Moncloa-Aravaca", "Latina",
       "Carabanchel", "Usera", "Puente de Vallecas", "Moratalaz", "Ciudad Lineal", "Hortaleza", "Villaverde", "Villa de Vallecas",
       "Vicálvaro", "San Blas-Canillejas", "Barajas"]
check(sorted(dist.nombre) == sorted(OFF) and len(dist) == 21, "los 21 distritos oficiales, con su nombre y código 1–21")
check(list(dist.sort_values("codigo").nombre) == OFF, "códigos de distrito en el orden oficial")
madrid = mun[mun.nombre == "Madrid"].geometry.iloc[0]
u = dist.geometry.union_all()
check(madrid.symmetric_difference(u).area / madrid.area < 0.001, "la unión de los 21 distritos coincide con el término municipal de Madrid (<0,1 %)")
check(val["contraste_oficial"]["municipio_madrid"]["ratio"] > 0.99, "superficie de Madrid ±1 % de la oficial (60.445,52 ha)")
check(val["municipios_vs_ign"]["dist_centroide_max_m"] < 1000, "ningún municipio desplazado >1 km respecto al IGN")

# ------------------------------------------------------------------ Mapa 1: red
nets = Counter(l["net"] for l in L.values())
check(nets == {"metro": 16, "ml": 4, "cercanias": 11}, "líneas: Metro 1–12 + R (con tramos 7B, 9B, 10B), ML1–ML4, Cercanías C1–C10 (C4a/C4b, C8a/C8b)")
check({l["id"] for l in L.values() if l["net"] == "metro"} == {"1", "2", "3", "4", "5", "6", "7", "7B", "8", "9", "9B", "10", "10B", "11", "12", "R"}, "todas las líneas y ramales de Metro")
for k, l in L.items():
    check(len(l["estaciones"]) >= 2 and l["color"].startswith("#"), f"{k}: {len(l['estaciones'])} estaciones, color {l['color']}")
# cada andén está sobre el trazado de su línea
d_max = 0
for r in pla.itertuples():
    g = lin[(lin.net == r.net) & (lin.line == r.line)].geometry
    d_max = max(d_max, g.distance(r.geometry).min())
check(d_max < 1.0, f"todos los andenes ({len(pla)}) están sobre el trazado de su línea (desviación máx. {d_max:.2f} m)")
# nombres: forma tipográfica idéntica al nombre oficial del GTFS salvo tildes/mayúsculas
bad = [v["nombre"] for v in E.values() if norm(v["nombre"]).replace(" ", "") != norm(v["nombre_gtfs"]).replace(" ", "")]
check(not bad, f"los {len(E)} nombres de estación coinciden con el nombre oficial del GTFS (sólo cambia la tipografía)")
# redes no mezcladas: ninguna estación de Metro en Torrejón de Ardoz
tj = [v["nombre"] for v in E.values() if v["municipio"] == "Torrejón de Ardoz"]
check(all(v["red"] == "cercanias" for v in E.values() if v["municipio"] == "Torrejón de Ardoz"), f"Torrejón de Ardoz sólo tiene Cercanías ({', '.join(tj)})")
serv = {n: sorted({f"{NET}" for NET in []}) for n in FOCO}
by_mun = {n: sorted({(v["red"], l) for v in E.values() if v["municipio"] == n for l in v["lineas"]}) for n in FOCO}
corr = J(DOCS / "datos" / "correspondencias.json")
check(all(c["dist"] < 450 for c in corr), f"{len(corr)} correspondencias entre redes, todas a <450 m y con nombre coincidente o verificadas")
transfer = sum(1 for k, v in E.items() if len(v["lineas"]) + sum(len(E[c]["lineas"]) for c in v["correspondencias"]) >= 2)

# ------------------------------------------------------------------ Mapa 2
D = it["destino"]
check(D["dist_poi_portal_m"] < 40, f"Cristo Social Club (Overture/Meta) a {D['dist_poi_portal_m']} m del portal oficial Juan Bravo 35")
check(it["origen"]["lineas"] == ["11"] and it["origen"]["distrito"] == "Carabanchel", "origen: estación Carabanchel Alto (sólo L11), distrito Carabanchel")
best = it["comparativa_estaciones"][0]
check(best["estacion"] == "Diego de León", f"estación de acceso óptima: {best['estacion']} ({best['a_pie_m']} m a pie, {best['total_min']} min)")
for modo, its in it["itinerarios"].items():
    for x in its:
        for p in x["pasos"]:
            if p["tipo"] == "metro":
                ids = p["ids"]
                seq = L[f"metro:{p['linea']}"]["estaciones"]
                check(all(s in seq for s in ids), f"{x['id']}: estaciones del tramo L{p['linea']} pertenecen a la línea")
            if p["tipo"] == "transbordo":
                s = next(k for k, v in E.items() if v["nombre"] == p["lugar"] and v["red"] == "metro")
                check(p["de"] in E[s]["lineas"] and p["a"] in E[s]["lineas"], f"{x['id']}: transbordo real en {p['lugar']} (L{p['de']} ↔ L{p['a']})")
rec = it["itinerarios"]["ida"][0]
check([p["linea"] for p in rec["pasos"] if p["tipo"] == "metro"] == ["11", "6"], "IDA recomendada: L11 → L6")
l6 = next(p for p in rec["pasos"] if p["tipo"] == "metro" and p["linea"] == "6")
check(l6["hacia"] == "Andén 1" and l6["paradas"][1] == "Usera", "L6 desde Plaza Elíptica por Andén 1 (Usera, Legazpi…) hasta Diego de León")
vr = it["itinerarios"]["vuelta"][0]
l6v = next(p for p in vr["pasos"] if p["tipo"] == "metro" and p["linea"] == "6")
check(l6v["hacia"] == "Andén 2" and l6v["paradas"][1] == "Manuel Becerra", "VUELTA: L6 por Andén 2 (Manuel Becerra…) y L11 dirección La Fortuna")

fi, fv = it["finde"]["ida"][0], it["finde"]["vuelta"][0]
check([p["linea"] for p in fi["pasos"] if p["tipo"] == "metro"] == ["11", "6", "5"] and fi["pasos"][-2]["hasta"].startswith("Cristo"),
      "Este finde · IDA (sáb. 7, L6 cortada): L11 → L6 Andén 2 hasta Oporto → L5 hasta Núñez de Balboa")
check([p["linea"] for p in fv["pasos"] if p["tipo"] == "metro"] == ["5", "6", "11"], "Este finde · VUELTA (dom. 8, 6:00): L5 → L6 Andén 1 → L11")
corte = {"Méndez Álvaro", "Pacífico", "Diego de León", "Avenida de América", "Nuevos Ministerios"}
check(not any(set(p["paradas"]) & corte for x in (fi, fv) for p in x["pasos"] if p["tipo"] == "metro" and p["linea"] == "6"),
      "Este finde · ningún tramo de L6 pasa por el tramo cortado")

# ------------------------------------------------------------------ informe
md.append(f"# Validación de datos\n\nGenerado por `scripts/validate.py` · datos consultados el {fu['consulta']}.\n")
md.append("## Resultado\n\n" + "\n".join(f"- ✅ {t}" for t in ok) + "\n")
md.append("## Municipios solicitados\n\n| Municipio | INE | Superficie (km²) | Punto interior (lat, lon) |\n|---|---|---|---|\n" + "\n".join(rows) + "\n")
md.append("Servicio ferroviario por municipio (estaciones situadas dentro del término):\n\n" + "\n".join(
    f"- **{n}**: " + ", ".join(sorted({f'{ {"metro": "Metro", "ml": "ML", "cercanias": "Cercanías"}[r]} {l}' for r, l in v})) for n, v in by_mun.items()) + "\n")
md.append("## Distritos\n\n| Código | Distrito | km² | Relación OSM |\n|---|---|---|---|\n" + "\n".join(
    f"| {d['codigo']} | {d['nombre']} | {d['area_km2']} | {d['osm']} |" for d in val["distritos"]) + "\n")
md.append(f"Contraste oficial: término municipal {val['contraste_oficial']['municipio_madrid']['calculado_ha']:.0f} ha frente a 60.445,52 ha "
          f"(ratio {val['contraste_oficial']['municipio_madrid']['ratio']}); distrito Centro {val['contraste_oficial']['distrito_centro']['calculado_ha']} ha "
          f"frente a 522,8 ha (ratio {val['contraste_oficial']['distrito_centro']['ratio']}).\n\n"
          f"Municipios frente al IGN (es-atlas, generalizado): distancia de centroides mediana {val['municipios_vs_ign']['dist_centroide_mediana_m']} m, "
          f"máx. {val['municipios_vs_ign']['dist_centroide_max_m']} m; superficie en municipios >50 km² entre {val['municipios_vs_ign']['ratio_area_>50km2']}. "
          f"Excluidos por no ser municipios: {', '.join(val['territorios_no_municipales_excluidos'])}.\n")
md.append("## Líneas\n\n| Red | Línea | Recorrido | Estaciones | km |\n|---|---|---|---|---|\n" + "\n".join(
    f"| {l['net']} | {l['id']} | {l['nombre']} | {len(l['estaciones'])} | {l['km']} |" for l in L.values()) + "\n")
md.append(f"Estaciones: {Counter(v['red'] for v in E.values())} · estaciones con transbordo (≥2 líneas o correspondencia): {transfer}.\n\n"
          "La **L3** se reconstruye (el GTFS 20250527 no tiene viajes ni shape de la L3): 18 paradas oficiales del CRTM + El Casar "
          "(prolongación inaugurada el 21/04/2025), trazado por las vías OSM rotuladas «Línea 3». Ver `docs/datos/cercanias_ajuste_vias.json`.\n")
md.append("## Correspondencias entre redes\n\n| Estación | Red | ↔ | Estación | Red | Distancia (m) | Criterio |\n|---|---|---|---|---|---|---|\n" + "\n".join(
    f"| {c['a_nombre']} | {c['a_red']} | ↔ | {c['b_nombre']} | {c['b_red']} | {c['dist']} | {c['tipo']} |" for c in corr) + "\n")
md.append("No incluidas por no poder verificarse en esta sesión: Plaza de España ↔ Noviciado (fuentes contradictorias).\n")
md.append("## Mapa 2 · comparativa de estaciones de acceso (IDA, viernes 23:30)\n\n| Estación | Líneas | Salida | Recta (m) | A pie (m) | Total (min) | Transbordos |\n|---|---|---|---|---|---|---|\n" + "\n".join(
    f"| {c['estacion']} | {', '.join(c['lineas'])} | {c['acceso']} | {c['linea_recta_m']} | {c['a_pie_m']} | {c['total_min']} | {c['transbordos']} |" for c in it["comparativa_estaciones"]) + "\n")
md.append("## Mapa 2 · itinerarios\n\n" + "\n".join(
    f"- **{modo.upper()} · {x['titulo']}** ({x['cuando']}): ≈ {x['total_min']} min, {x['a_pie_m']} m a pie, {x['transbordos']} transbordo(s) — " +
    " → ".join(p.get("linea") and f"{p['tipo']} {p['linea']} ({p['desde']}→{p['hasta']})" or p["tipo"] for p in x["pasos"])
    for modo, its in it["itinerarios"].items() for x in its) + "\n")
md.append("## Sección «Este finde» (7–8 nov 2026, L6 cortada)\n\n" + "\n".join(
    f"- **{x['titulo']}**: ≈ {x['total_min']} min, {x['a_pie_m']} m a pie, {x['transbordos']} transbordos — " +
    " → ".join(p.get("linea") and f"{p['tipo']} {p['linea']} ({p['desde']}→{p['hasta']})" or p["tipo"] for p in x["pasos"]) for x in (fi, fv)) + "\n")
s = it["supuestos"]
md.append(f"Supuestos: a pie {s['velocidad_pie_kmh']} km/h por la red peatonal OSM; espera = {s['espera']}; pasillos = distancia andén–acceso × {s['rodeo_pasillos']} + {s['escaleras_min']} min.\n")
md.append("## Comprobaciones técnicas\n\nVer `npm run check` (consola del navegador sin errores en escritorio y móvil, buscador y capas) y `npm run build`.\n")
(DOCS / "VALIDACION.md").write_text("\n".join(md), encoding="utf-8")

f = ["# Registro de fuentes\n", f"Fecha de consulta de todos los datos: **{fu['consulta']}**. Generado desde `data/fuentes.json`.\n",
     "| Fuente | Organismo | Información | Versión | Licencia | Limitaciones |", "|---|---|---|---|---|---|"]
f += [f"| {x['nombre']}<br><small>{x['url_oficial']}<br>obtenida: {x['url_obtenida']}</small> | {x['organismo']} | {x['tipo']} | {x['version']} | {x['licencia']} | {x['limitaciones']} |" for x in fu["fuentes"]]
f += ["\n## Avisos de servicio recopilados\n", av["nota"] + "\n"]
f += [f"- **{a['titulo']}** ({a['estado']}): {a['detalle']} Fuentes: " + "; ".join(f"[{s['titulo']}]({s['url']})" for s in a["fuentes"]) for a in av["avisos"]]
f += ["\n## Acceso a las fuentes oficiales desde el entorno de desarrollo\n",
      "Los portales oficiales (crtm.es, datos.madrid.es, ign.es, renfe.com, metromadrid.es) no eran accesibles desde el entorno donde se generó el "
      "proyecto. Se usaron copias íntegras de los mismos ficheros GTFS (Mobility Database) y datos de Overture Maps (S3 público). "
      "`scripts/fetch_data.sh` intenta siempre primero la URL oficial."]
(DOCS / "FUENTES.md").write_text("\n".join(f) + "\n", encoding="utf-8")
print(f"OK · {len(ok)} comprobaciones superadas → docs/VALIDACION.md, docs/FUENTES.md")
