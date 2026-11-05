"""Descarga por bbox desde Overture Maps (S3 público, sin clave) a GeoParquet local.

Uso: python -I scripts/overture.py <theme> <type> <xmin> <ymin> <xmax> <ymax> <salida.parquet> [columnas,...] [campo=valor]
"""
import sys
import pyarrow.dataset as ds
import pyarrow.compute as pc
import pyarrow.parquet as pq
import s3fs

RELEASE = "2026-10-21.0"  # actualizar aquí al refrescar datos (ver docs/ACTUALIZAR.md)

def fetch(theme, typ, bbox, out, columns=None, where=None):
    fs = s3fs.S3FileSystem(anon=True, client_kwargs={"region_name": "us-west-2"})
    path = f"overturemaps-us-west-2/release/{RELEASE}/theme={theme}/type={typ}/"
    dset = ds.dataset(path, filesystem=fs, format="parquet")
    xmin, ymin, xmax, ymax = bbox
    f = lambda k: pc.field("bbox", k)
    flt = (f("xmin") <= xmax) & (f("xmax") >= xmin) & (f("ymin") <= ymax) & (f("ymax") >= ymin)
    if where:
        k, v = where.split("=")
        flt = flt & (pc.field(k) == v)
    table = dset.to_table(filter=flt, columns=columns)
    # conservar metadatos GeoParquet para que geopandas lo lea como geometría
    meta = dset.schema.metadata or {}
    table = table.replace_schema_metadata({**meta, **(table.schema.metadata or {})})
    pq.write_table(table, out)
    print(f"{theme}/{typ}: {table.num_rows} filas -> {out}")

if __name__ == "__main__":
    a = sys.argv[1:]
    cols = a[7].split(",") if len(a) > 7 and a[7] else None
    fetch(a[0], a[1], tuple(map(float, a[2:6])), a[6], cols, a[8] if len(a) > 8 else None)
