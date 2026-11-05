#!/usr/bin/env bash
# Descarga los datos de origen en data/raw/ (no se versionan). Intenta primero la URL oficial y, si no
# responde o no devuelve un ZIP válido, la copia íntegra del mismo feed en Mobility Database.
set -euo pipefail
cd "$(dirname "$0")/.."
R=data/raw
mkdir -p $R
gtfs() {  # nombre  url_oficial  id_mobility_database
  local d=$R/gtfs_$1
  mkdir -p "$d"
  if curl -fsSL -m 300 -o "$d/feed.zip" "$2" && unzip -tq "$d/feed.zip" >/dev/null 2>&1; then
    echo "$1: descargado de la fuente oficial"
  else
    curl -fsSL -m 600 -o "$d/feed.zip" "https://storage.googleapis.com/mobilitydata-datasets-prod/mdb-$3/latest.zip"
    echo "$1: descargado del espejo Mobility Database (mdb-$3)"
  fi
  rm -rf "$d/extracted" && unzip -q -o "$d/feed.zip" -d "$d/extracted"
}
gtfs metro "https://crtm.maps.arcgis.com/sharing/rest/content/items/5c7f2951962540d69ffe8f640d94c246/data" 794
gtfs metro_ligero "https://www.arcgis.com/sharing/rest/content/items/aaed26cc0ff64b0c947ac0bc3e033196/data" 2802
gtfs cercanias_crtm "https://www.arcgis.com/sharing/rest/content/items/1a25440bf66f499bae2657ec7fb40144/data" 2720
gtfs emt "https://servicios.emtmadrid.es:8443/gtfs/transitemt.zip" 793
bash scripts/fetch_overture_all.sh
# IGN (es-atlas) para validar municipios
mkdir -p $R/npm_es_atlas
(cd $R/npm_es_atlas && npm pack es-atlas@0.6.0 --silent >/dev/null && tar xzf es-atlas-0.6.0.tgz)
node scripts/topo2geo.mjs $R/npm_es_atlas/package/es/municipalities.json municipalities $R/npm_es_atlas/municipios_ign.geojson
echo "Datos de origen listos en $R"
