#!/usr/bin/env bash
# Descarga de Overture Maps (S3 público, sin clave) de todas las capas que usa el proyecto.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="python -I scripts/overture.py"
O=data/raw/overture
mkdir -p $O
REGION="-4.60 39.85 -3.03 41.18"            # Comunidad de Madrid y bordes
$PY divisions division_area $REGION $O/division_area.parquet
$PY divisions division $REGION $O/division.parquet id,names,subtype,class,country,region,geometry,bbox,population
$PY transportation segment $REGION $O/segments.parquet id,names,subtype,class,subclass,connectors,road_flags,access_restrictions,level_rules,geometry,bbox
$PY transportation segment $REGION $O/rail.parquet id,names,subtype,class,subclass,connectors,rail_flags,level_rules,routes,geometry,bbox subtype=rail
$PY base water $REGION $O/water.parquet id,names,subtype,class,is_intermittent,geometry,bbox
$PY base land_use $REGION $O/land_use.parquet id,names,subtype,class,geometry,bbox
$PY base infrastructure -4.20 40.05 -3.30 40.75 $O/infrastructure.parquet id,names,subtype,class,geometry,bbox,source_tags
# entorno del destino (portales y establecimientos) y edificios de origen y destino (Mapa 2)
$PY places place -3.70 40.42 -3.65 40.445 $O/places_salamanca.parquet
$PY addresses address -3.70 40.42 -3.65 40.445 $O/addresses_salamanca.parquet
$PY buildings building -3.6960 40.4230 -3.6650 40.4420 $O/buildings_destino.parquet id,class,height,num_floors,geometry,bbox
$PY buildings building -3.7640 40.3640 -3.7400 40.3800 $O/buildings_origen.parquet id,class,height,num_floors,geometry,bbox
