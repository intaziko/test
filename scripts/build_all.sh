#!/usr/bin/env bash
# Regenera todos los datos de public/ a partir de data/raw/ (ver README «Actualizar los datos»).
set -euo pipefail
cd "$(dirname "$0")/.."
PY="python -I"
[ -d data/raw/gtfs_metro/extracted ] || bash scripts/fetch_data.sh
$PY scripts/build_network.py      # líneas, andenes, estaciones, transbordos (GTFS + vías OSM)
$PY scripts/build_boundaries.py   # 179 municipios, 21 distritos, etiquetas, municipio/distrito de cada estación
$PY scripts/build_avisos.py       # avisos de servicio y registro de fuentes
$PY scripts/build_routes.py       # itinerarios del Mapa 2 (ida, vuelta y alternativas)
$PY scripts/build_basemap.py      # mapa base PMTiles (requiere tippecanoe)
$PY scripts/validate.py           # comprobaciones de exactitud → docs/VALIDACION.md y docs/FUENTES.md
