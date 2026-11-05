# Mapa de transporte de Madrid · Ruta a Cristo Social Club

Dos mapas web interactivos, independientes y enlazados entre sí, construidos con datos geográficos reales
(no es un plano esquemático):

| | Página | Qué muestra |
|---|---|---|
| **Mapa 1 · Red completa** | `index.html` | Comunidad de Madrid centrada en la capital: 179 municipios (Madrid, Alcobendas, Torrejón de Ardoz, Getafe y Móstoles destacados), los 21 distritos, Metro (1–12, R y tramos 7B/9B/10B), Metro Ligero (ML1–ML4) y Cercanías (C1–C10) con trazado y estaciones en su posición real, transbordos, correspondencias entre redes y avisos de servicio. Buscador, capas, selección de líneas y fichas de estación. |
| **Mapa 2 · Ruta** | `ruta.html` | Itinerario Metro **Carabanchel Alto ⇄ Cristo Social Club** (C/ de Juan Bravo, 35) en modo **IDA** y **VUELTA**, con paso a paso, andén/dirección de cada tren, salida de estación, recorrido a pie calle a calle, comparativa de estaciones y alternativas (corte de la L6, cierre nocturno de la L6, búhos). |

Exportaciones A3 horizontal listas en [`exports/`](exports/): `MAPA1-red-transporte-Madrid-A3.pdf` (vista metropolitana + detalle del centro),
`MAPA2-ruta-Cristo-Social-Club-IDA-y-VUELTA-A3.pdf` (una página por sentido) y los PNG equivalentes (4761 × 3369 px, ≈ 290 ppp).

## Resultado del Mapa 2 (datos a 5/11/2026)

**Destino verificado:** *Cristo Social Club*, Calle de Juan Bravo, 35 · 28006 Madrid (distrito de Salamanca). Portal oficial
CartoCiudad (IGN) en 40.43278, −3.67851; el establecimiento (Overture/Meta) está a 13 m y en la misma dirección figuraban antes
*Marusha Society* y *Almonte*. Dirección coincidente en Venuu, VenuesPlace, DiscoMadrid, Apple Maps, RA y DICE.

**IDA recomendada (≈ 45 min, 1 transbordo, 342 m a pie):**
1. Metro **Carabanchel Alto** → Línea **11** dirección **Plaza Elíptica** (4 paradas).
2. Transbordo en **Plaza Elíptica** a la Línea **6**, **Andén 1** (sentido Usera, Legazpi, Arganzuela-Planetario…).
3. Bajar en **Diego de León** (10 paradas) y salir por el acceso **«Juan Bravo - Conde Peñalver»** (C/ de Juan Bravo, 52).
4. Caminar 342 m hacia el oeste por Juan Bravo (cruzando a la acera norte) hasta el n.º 35.

**VUELTA recomendada (≈ 47 min):** mismo acceso de Diego de León → L6 **Andén 2** (sentido Manuel Becerra, O'Donnell…) → Plaza Elíptica →
L11 dirección **La Fortuna** → Carabanchel Alto. Se calcula por separado; coincide con la ida porque es la combinación más rápida también en sentido inverso.

**Restricciones a tener en cuenta** (incluidas como escenarios alternativos):
- Metro funciona de 6:00 a 1:30. La sala cierra a las 6:00 (vie/sáb, según DiscoMadrid): de 1:30 a 6:00, **búho N2** (Príncipe de Vergara–Diego de León → Cibeles) + **N17** (Cibeles → Metro Carabanchel Alto), ≈ 72 min.
- La L6 cierra a las 23:00 de **domingo a jueves** (obras de automatización): autobuses gratuitos **SC1** (ida) / **SC2** (vuelta).
- **7–9 y 21–22 de noviembre de 2026**: L6 cortada entre Arganzuela-Planetario y Ciudad Universitaria → ida por L11 → L6 (Andén 2) → Oporto → **L5** dirección Alameda de Osuna → **Núñez de Balboa** (≈ 55 min).

Es un itinerario orientativo (horarios programados del GTFS), no información en tiempo real.

## Estructura

```
index.html, ruta.html        páginas (Vite, multipágina)
src/                         interfaz: common.js (mapa y capas de transporte), mapa1.js, mapa2.js, basemap.js (estilo), style.css
public/data/                 datos procesados que carga la web (GeoJSON / JSON)
public/tiles/base.pmtiles    mapa base vectorial propio (calles, agua, parques…), sin servidores externos
public/fonts/                tipografías de rotulación del mapa (Noto Sans, OFL)
scripts/                     pipeline de datos (Python) y utilidades (Node)
data/                        entradas manuales: avisos.json, fuentes.json, correspondencias_verificadas.json
data/raw/ (no versionado)    descargas de origen (GTFS, Overture, IGN)
docs/FUENTES.md              registro de fuentes, fechas, licencias y limitaciones
docs/VALIDACION.md           resultado de las comprobaciones de exactitud
exports/                     PDF y PNG A3
```

Datos separados por tipo: `municipios.geojson`, `distritos.geojson`, `etiquetas_admin.geojson`, `estaciones.geojson`, `andenes.geojson`,
`lineas.geojson`, `enlaces.geojson` (transbordos y correspondencias), `red.json` (metadatos de líneas y estaciones),
`itinerarios.json` / `itinerarios.geojson` (ida, vuelta, alternativas y recorridos peatonales), `avisos.json/.geojson`.

## Ejecutar

Requisitos: Node.js 20 o superior.

```bash
npm install
```

```bash
npm run dev
```

Abre http://localhost:5173/ (Mapa 1) y http://localhost:5173/ruta.html (Mapa 2). Para publicar:

```bash
npm run build
```

`dist/` es estático: sirve en cualquier servidor web que admita peticiones *Range* (lo necesita PMTiles); para probarlo, `npm run preview`.
La web no usa claves, APIs de pago ni servicios externos en tiempo de ejecución.

## Actualizar los datos

Requisitos: Python 3.11+, [tippecanoe](https://github.com/felt/tippecanoe) (`brew install tippecanoe` o compilarlo desde GitHub) y acceso a internet.

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
```

```bash
bash scripts/fetch_data.sh
```

```bash
npm run data
```

- `fetch_data.sh` descarga los GTFS del CRTM/EMT (primero la URL oficial; si falla, la copia íntegra en Mobility Database), las capas de
  Overture Maps (S3 público) y es-atlas (IGN). Para cambiar de versión de Overture edita `RELEASE` en `scripts/overture.py`.
- `npm run data` ejecuta `scripts/build_all.sh`: red → límites → avisos → itinerarios → mapa base → validación. Cualquier incoherencia
  detiene el proceso (asserts), p. ej. si cambian los 179 municipios, los 21 distritos o una estación queda lejos de su línea.
- **Avisos de servicio**: se mantienen a mano en `data/avisos.json` (con fuente y estado); los tramos se dibujan solos sobre el trazado.
- **Correspondencias con distinto nombre** (p. ej. Gran Vía ↔ Cercanías Sol) se declaran, con fuente, en `data/correspondencias_verificadas.json`.
- Si el GTFS de Metro vuelve a incluir la Línea 3, `build_network.py` lo detecta (dejarán de quedar 18 paradas sin viajes) y la reconstrucción debe retirarse.

## Exportar PDF / PNG

Necesita Playwright con Chromium (no es dependencia del proyecto por su tamaño):

```bash
npm i -D playwright && npx playwright install chromium
```

```bash
npm run build && npm run export
```

Cada página se abre en modo impresión (`?print=a3`, `?print=a3-centro`, `ruta.html?print=a3&modo=ida|vuelta`) a 1587 × 1123 px CSS (A3 a 96 ppp)
con `deviceScaleFactor` 3; el PDF conserva textos y paneles en vectorial y el mapa como imagen de alta resolución.

## Comprobaciones

```bash
python -I scripts/validate.py
```

```bash
npm run build && npm run check
```

`validate.py` (72 comprobaciones) escribe `docs/VALIDACION.md`; `check.mjs` abre ambos mapas en escritorio y móvil y verifica consola sin
errores, buscador (estaciones, municipios, distritos), capas, selección de línea, cambio IDA/VUELTA y dibujo del recorrido.

## Metodología y precisión

- **Trazados de Metro y Metro Ligero**: `shapes.txt` del GTFS oficial del CRTM (un punto cada ~8 m). **Estaciones**: andenes (`par_`) del GTFS
  situados sobre su línea (mediana de ajuste 10 m); si los andenes de una estación están separados se dibujan ambos unidos por el pasillo.
- **Cercanías**: los *shapes* del GTFS son poco densos y algunos históricos (C8 hasta Guadalajara). El recorrido de cada servicio real
  (`stop_times`) se ajusta a las vías de OpenStreetMap entre estaciones consecutivas, guiado por el *shape* oficial; si OSM discrepa
  (>300 m o más largo) se usa el tramo del *shape* oficial. Informe por tramo en `docs/datos/cercanias_ajuste_vias.json`.
- **Línea 3**: el GTFS de Metro accesible (versión 20250527) no trae viajes ni trazado de la L3 (sí sus 18 paradas). Se reconstruye con esas
  paradas + El Casar (prolongación inaugurada el 21/04/2025) y las vías de OSM rotuladas «Línea 3». Avisado en la interfaz.
- **Nombres**: el GTFS publica mayúsculas sin tildes; se toma la grafía de los accesos del CRTM o de OSM sólo si coincide letra a letra
  tras normalizar (comprobado para las 393 estaciones).
- **Transbordos**: misma estación GTFS con varias líneas; entre redes, mismo nombre a <450 m o andenes a <120 m, más 3 casos verificados
  con fuente. Listado completo en `docs/VALIDACION.md`.
- **Límites**: relaciones administrativas de OSM (Overture), que en España derivan de la BDLL del IGN; contrastadas con el IGN (179 municipios,
  códigos INE) y con las superficies oficiales del Ayuntamiento.
- **Recorridos a pie**: camino más corto por la red peatonal de OSM (aceras y pasos de peatones), desde los accesos oficiales del CRTM hasta el
  portal oficial; la salida elegida minimiza pasillo + calle, no la distancia en línea recta.
- **Tiempos**: trayectos entre estaciones de `stop_times`; espera = mitad del intervalo (`frequencies.txt`) en la franja del escenario;
  a pie a 4,5 km/h; pasillos estimados (distancia × 1,3 + 1 min).
- **Proyección**: Web Mercator para la visualización; las distancias y superficies se calculan en ETRS89 / UTM 30N (EPSG:25830).

## Limitaciones conocidas

- Los portales oficiales (CRTM, Ayuntamiento, IGN, Renfe, Metro de Madrid) no eran accesibles desde el entorno donde se generó el proyecto:
  se usaron copias íntegras de los mismos GTFS (Mobility Database) y Overture Maps. Con acceso, `fetch_data.sh` usa la URL oficial.
- El GTFS de Metro es de mayo de 2025 (frecuencias orientativas). No se han detectado aperturas de estaciones posteriores, salvo la L3 a
  El Casar (incluida). Las alteraciones vigentes (L10 Nuevos Ministerios–Cuzco, Santiago Bernabéu cerrada, L6) figuran como avisos.
- No hay datos oficiales de pasillos de transbordo: los minutos de pasillo son estimaciones. De Carabanchel Alto sólo consta el acceso por ascensor.
- En los troncos compartidos de Cercanías (Atocha–Chamartín) las líneas se superponen sobre la misma vía.
- Plaza de España ↔ Noviciado no se muestra como correspondencia porque las fuentes consultadas se contradicen.
- El horario de la sala procede de una fuente secundaria; confírmalo con el local.

## Licencias y atribución

Código: MIT. Datos: GTFS © Consorcio Regional de Transportes de Madrid, Renfe y EMT Madrid (condiciones de reutilización de cada
organismo); © OpenStreetMap contributors (ODbL) vía Overture Maps Foundation; CartoCiudad e IGN (CC BY 4.0). Tipografías Noto Sans e
Inter (SIL OFL). Detalle en [`docs/FUENTES.md`](docs/FUENTES.md).
