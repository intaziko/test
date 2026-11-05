"""Utilidades compartidas por los scripts del pipeline de datos."""
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "public" / "data"
DOCS = ROOT / "docs"
UTM = 25830  # ETRS89 / UTM 30N: proyección oficial en España para medir distancias y áreas


def norm(s: str) -> str:
    """Normaliza nombres para comparar (sin tildes, minúsculas, sin puntuación)."""
    s = unicodedata.normalize("NFKD", str(s).replace("'", "").replace("’", "")).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def write_json(path: Path, obj, pretty=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1 if pretty else None, separators=None if pretty else (",", ":"))


def write_geojson(path: Path, gdf, precision=6):
    """GeoJSON compacto en WGS84 con coordenadas redondeadas (6 decimales ≈ 0,1 m)."""
    gdf = gdf.to_crs(4326)
    path.parent.mkdir(parents=True, exist_ok=True)
    txt = gdf.to_json(drop_id=True, to_wgs84=False)
    data = json.loads(txt)

    def rnd(c):
        return [round(c[0], precision), round(c[1], precision)] if isinstance(c[0], (int, float)) else [rnd(x) for x in c]

    for f in data["features"]:
        if f["geometry"]:
            f["geometry"]["coordinates"] = rnd(f["geometry"]["coordinates"])
        f["properties"] = {k: v for k, v in f["properties"].items() if v is not None}
    write_json(path, data)
    return len(data["features"])
