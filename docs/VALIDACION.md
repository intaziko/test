# Validación de datos

Generado por `scripts/validate.py` · datos consultados el 2026-11-05.

## Resultado

- ✅ 179 municipios de la Comunidad de Madrid (los mismos que el IGN)
- ✅ municipio Madrid presente
- ✅ municipio Alcobendas presente
- ✅ municipio Torrejón de Ardoz presente
- ✅ municipio Getafe presente
- ✅ municipio Móstoles presente
- ✅ los 21 distritos oficiales, con su nombre y código 1–21
- ✅ códigos de distrito en el orden oficial
- ✅ la unión de los 21 distritos coincide con el término municipal de Madrid (<0,1 %)
- ✅ superficie de Madrid ±1 % de la oficial (60.445,52 ha)
- ✅ ningún municipio desplazado >1 km respecto al IGN
- ✅ líneas: Metro 1–12 + R (con tramos 7B, 9B, 10B), ML1–ML4, Cercanías C1–C10 (C4a/C4b, C8a/C8b)
- ✅ todas las líneas y ramales de Metro
- ✅ metro:1: 33 estaciones, color #2DBEF0
- ✅ metro:2: 20 estaciones, color #ED1C24
- ✅ metro:3: 19 estaciones, color #FFD000
- ✅ metro:4: 23 estaciones, color #B65518
- ✅ metro:5: 32 estaciones, color #8FD400
- ✅ metro:6: 28 estaciones, color #98989B
- ✅ metro:7: 24 estaciones, color #EE7518
- ✅ metro:7B: 8 estaciones, color #EE7518
- ✅ metro:8: 8 estaciones, color #EC82B1
- ✅ metro:9: 24 estaciones, color #A60084
- ✅ metro:9B: 6 estaciones, color #A60084
- ✅ metro:10: 21 estaciones, color #005AA9
- ✅ metro:10B: 11 estaciones, color #005AA9
- ✅ metro:11: 7 estaciones, color #009B3A
- ✅ metro:12: 28 estaciones, color #A49800
- ✅ metro:R: 2 estaciones, color #FFFFFF
- ✅ ml:ML1: 9 estaciones, color #3A7DDA
- ✅ ml:ML2: 13 estaciones, color #A60084
- ✅ ml:ML3: 16 estaciones, color #ED1C24
- ✅ ml:ML4: 15 estaciones, color #7DB713
- ✅ cercanias:C1: 7 estaciones, color #75B6E0
- ✅ cercanias:C2: 19 estaciones, color #00943D
- ✅ cercanias:C3: 13 estaciones, color #952585
- ✅ cercanias:C4a: 15 estaciones, color #2C2A86
- ✅ cercanias:C4b: 15 estaciones, color #2C2A86
- ✅ cercanias:C5: 23 estaciones, color #FECB00
- ✅ cercanias:C7: 28 estaciones, color #E5202A
- ✅ cercanias:C8a: 12 estaciones, color #868584
- ✅ cercanias:C8b: 14 estaciones, color #868584
- ✅ cercanias:C9: 3 estaciones, color #915419
- ✅ cercanias:C10: 18 estaciones, color #BCCF00
- ✅ todos los andenes (528) están sobre el trazado de su línea (desviación máx. 0.10 m)
- ✅ los 393 nombres de estación coinciden con el nombre oficial del GTFS (sólo cambia la tipografía)
- ✅ Torrejón de Ardoz sólo tiene Cercanías (Torrejón de Ardoz, Soto del Henares)
- ✅ 33 correspondencias entre redes, todas a <450 m y con nombre coincidente o verificadas
- ✅ Cristo Social Club (Overture/Meta) a 14 m del portal oficial Juan Bravo 35
- ✅ origen: estación Carabanchel Alto (sólo L11), distrito Carabanchel
- ✅ estación de acceso óptima: Diego de León (342 m a pie, 45.3 min)
- ✅ ida: estaciones del tramo L11 pertenecen a la línea
- ✅ ida: transbordo real en Plaza Elíptica (L11 ↔ L6)
- ✅ ida: estaciones del tramo L6 pertenecen a la línea
- ✅ ida_corte_l6: estaciones del tramo L11 pertenecen a la línea
- ✅ ida_corte_l6: transbordo real en Plaza Elíptica (L11 ↔ L6)
- ✅ ida_corte_l6: estaciones del tramo L6 pertenecen a la línea
- ✅ ida_corte_l6: transbordo real en Oporto (L6 ↔ L5)
- ✅ ida_corte_l6: estaciones del tramo L5 pertenecen a la línea
- ✅ ida_noche_sc1: estaciones del tramo L11 pertenecen a la línea
- ✅ vuelta: estaciones del tramo L6 pertenecen a la línea
- ✅ vuelta: transbordo real en Plaza Elíptica (L6 ↔ L11)
- ✅ vuelta: estaciones del tramo L11 pertenecen a la línea
- ✅ vuelta_corte_l6: estaciones del tramo L5 pertenecen a la línea
- ✅ vuelta_corte_l6: transbordo real en Oporto (L5 ↔ L6)
- ✅ vuelta_corte_l6: estaciones del tramo L6 pertenecen a la línea
- ✅ vuelta_corte_l6: transbordo real en Plaza Elíptica (L6 ↔ L11)
- ✅ vuelta_corte_l6: estaciones del tramo L11 pertenecen a la línea
- ✅ vuelta_noche_sc2: estaciones del tramo L11 pertenecen a la línea
- ✅ IDA recomendada: L11 → L6
- ✅ L6 desde Plaza Elíptica por Andén 1 (Usera, Legazpi…) hasta Diego de León
- ✅ VUELTA: L6 por Andén 2 (Manuel Becerra…) y L11 dirección La Fortuna

## Municipios solicitados

| Municipio | INE | Superficie (km²) | Punto interior (lat, lon) |
|---|---|---|---|
| Madrid | 28079 | 603.90 | 40.4778, -3.6860 |
| Alcobendas | 28006 | 45.37 | 40.5446, -3.6549 |
| Torrejón de Ardoz | 28148 | 32.62 | 40.4707, -3.4626 |
| Getafe | 28065 | 78.56 | 40.3008, -3.6681 |
| Móstoles | 28092 | 45.09 | 40.3196, -3.8935 |

Servicio ferroviario por municipio (estaciones situadas dentro del término):

- **Madrid**: Cercanías C1, Cercanías C10, Cercanías C2, Cercanías C3, Cercanías C4a, Cercanías C4b, Cercanías C5, Cercanías C7, Cercanías C8a, Cercanías C8b, ML ML1, ML ML2, ML ML3, Metro 1, Metro 10, Metro 10B, Metro 11, Metro 2, Metro 3, Metro 4, Metro 5, Metro 6, Metro 7, Metro 7B, Metro 8, Metro 9, Metro 9B, Metro R
- **Alcobendas**: Cercanías C4a, Metro 10B
- **Torrejón de Ardoz**: Cercanías C2, Cercanías C7
- **Getafe**: Cercanías C3, Cercanías C4a, Cercanías C4b, Metro 12, Metro 3
- **Móstoles**: Cercanías C5, Metro 12

## Distritos

| Código | Distrito | km² | Relación OSM |
|---|---|---|---|
| 1 | Centro | 5.17 | r356761@26 |
| 2 | Arganzuela | 6.51 | r356775@30 |
| 3 | Retiro | 5.45 | r356879@22 |
| 4 | Salamanca | 5.39 | r356962@52 |
| 5 | Chamartín | 9.21 | r356983@50 |
| 6 | Tetuán | 5.36 | r356984@27 |
| 7 | Chamberí | 4.7 | r356998@31 |
| 8 | Fuencarral-El Pardo | 237.77 | r356771@37 |
| 9 | Moncloa-Aravaca | 46.58 | r356760@69 |
| 10 | Latina | 25.41 | r355676@40 |
| 11 | Carabanchel | 14.05 | r355666@39 |
| 12 | Usera | 7.76 | r349469@16 |
| 13 | Puente de Vallecas | 14.94 | r354080@21 |
| 14 | Moratalaz | 6.11 | r354223@17 |
| 15 | Ciudad Lineal | 11.41 | r1675818@39 |
| 16 | Hortaleza | 27.61 | r354522@35 |
| 17 | Villaverde | 20.15 | r349470@10 |
| 18 | Villa de Vallecas | 51.48 | r349485@33 |
| 19 | Vicálvaro | 34.85 | r354389@25 |
| 20 | San Blas-Canillejas | 22.31 | r354377@33 |
| 21 | Barajas | 41.69 | r354410@16 |

Contraste oficial: término municipal 60390 ha frente a 60.445,52 ha (ratio 0.9991); distrito Centro 517.3 ha frente a 522,8 ha (ratio 0.9894).

Municipios frente al IGN (es-atlas, generalizado): distancia de centroides mediana 110 m, máx. 496 m; superficie en municipios >50 km² entre [0.96, 1.039]. Excluidos por no ser municipios: El Redegüelo, Los Baldíos.

## Líneas

| Red | Línea | Recorrido | Estaciones | km |
|---|---|---|---|---|
| metro | 1 | Pinar de Chamartín – Valdecarros | 33 | 21.7 |
| metro | 2 | Las Rosas – Cuatro Caminos | 20 | 13.3 |
| metro | 3 | Moncloa – El Casar | 19 | 16.9 |
| metro | 4 | Argüelles – Pinar de Chamartín | 23 | 14.2 |
| metro | 5 | Alameda de Osuna – Casa de Campo | 32 | 22.5 |
| metro | 6 | Circular | 28 | 23.5 |
| metro | 7 | Estadio Metropolitano – Pitis | 24 | 19.2 |
| metro | 7B | Hospital del Henares – Estadio Metropolitano | 8 | 8.8 |
| metro | 8 | Nuevos Ministerios – Aeropuerto T-4 | 8 | 15.8 |
| metro | 9 | Paco de Lucía – Puerta de Arganda | 24 | 20.5 |
| metro | 9B | Puerta de Arganda – Arganda del Rey | 6 | 19.0 |
| metro | 10 | Tres Olivos – Puerta del Sur | 21 | 23.4 |
| metro | 10B | Hospital Infanta Sofía – Tres Olivos | 11 | 14.8 |
| metro | 11 | Plaza Elíptica – La Fortuna | 7 | 6.8 |
| metro | 12 | Circular | 28 | 40.6 |
| metro | R | Ópera – Príncipe Pío | 2 | 1.0 |
| ml | ML1 | Pinar de Chamartín – Las Tablas | 9 | 5.1 |
| ml | ML2 | Colonia Jardín – Estación de Aravaca | 13 | 8.6 |
| ml | ML3 | Colonia Jardín – Puerta de Boadilla | 16 | 13.5 |
| ml | ML4 | Circular | 15 | 16.1 |
| cercanias | C1 | Madrid-Atocha Cercanías – Madrid-Aeropuerto T4 | 7 | 17.4 |
| cercanias | C2 | Madrid-Chamartín-Clara Campoamor – Guadalajara | 19 | 90.8 |
| cercanias | C3 | Madrid-Chamartín-Clara Campoamor – Aranjuez | 13 | 76.8 |
| cercanias | C4a | Parla – Alcobendas-San Sebastián de los Reyes | 15 | 48.8 |
| cercanias | C4b | Colmenar Viejo – Parla | 15 | 67.6 |
| cercanias | C5 | Móstoles-El Soto – Humanes | 23 | 45.0 |
| cercanias | C7 | Guadalajara – Madrid-Príncipe Pío | 28 | 143.2 |
| cercanias | C8a | El Escorial – Madrid-Chamartín-Clara Campoamor | 12 | 72.9 |
| cercanias | C8b | Cercedilla – Madrid-Chamartín-Clara Campoamor | 14 | 97.4 |
| cercanias | C9 | Cercedilla – Los Cotos | 3 | 18.1 |
| cercanias | C10 | Villalba de Guadarrama – Madrid-Chamartín-Clara Campoamor | 18 | 91.6 |

Estaciones: Counter({'metro': 242, 'cercanias': 95, 'ml': 56}) · estaciones con transbordo (≥2 líneas o correspondencia): 129.

La **L3** se reconstruye (el GTFS 20250527 no tiene viajes ni shape de la L3): 18 paradas oficiales del CRTM + El Casar (prolongación inaugurada el 21/04/2025), trazado por las vías OSM rotuladas «Línea 3». Ver `docs/datos/cercanias_ajuste_vias.json`.

## Correspondencias entre redes

| Estación | Red | ↔ | Estación | Red | Distancia (m) | Criterio |
|---|---|---|---|---|---|---|
| Pinar de Chamartín | metro | ↔ | Pinar de Chamartín | ml | 3 | nombre+proximidad |
| Atocha | metro | ↔ | Madrid-Atocha Cercanías | cercanias | 3 | nombre+proximidad |
| Colonia Jardín | metro | ↔ | Colonia Jardín | ml | 5 | nombre+proximidad |
| Cuatro Vientos | metro | ↔ | Cuatro Vientos | cercanias | 6 | nombre+proximidad |
| Pirámides | metro | ↔ | Pirámides | cercanias | 7 | nombre+proximidad |
| Getafe Central | metro | ↔ | Getafe-Centro | cercanias | 9 | nombre+proximidad |
| Puerta de Arganda | metro | ↔ | Vicálvaro | cercanias | 10 | nombre+proximidad |
| Nuevos Ministerios | metro | ↔ | Madrid-Nuevos Ministerios | cercanias | 10 | nombre+proximidad |
| Aluche | metro | ↔ | Aluche | cercanias | 11 | nombre+proximidad |
| El Casar | metro | ↔ | El Casar | cercanias | 11 | nombre+proximidad |
| Las Tablas | metro | ↔ | Las Tablas | ml | 14 | nombre+proximidad |
| Alcorcón Central | metro | ↔ | Alcorcón | cercanias | 18 | nombre+proximidad |
| Móstoles Central | metro | ↔ | Móstoles | cercanias | 19 | nombre+proximidad |
| Paco de Lucía | metro | ↔ | Mirasierra-Paco de Lucía | cercanias | 19 | nombre+proximidad |
| Laguna | metro | ↔ | Laguna | cercanias | 20 | nombre+proximidad |
| Fuente de la Mora | ml | ↔ | Fuente de la Mora | cercanias | 20 | nombre+proximidad |
| Sierra de Guadalupe | metro | ↔ | Vallecas | cercanias | 25 | nombre+proximidad |
| Estación de Aravaca | ml | ↔ | Aravaca | cercanias | 33 | nombre+proximidad |
| Sol | metro | ↔ | Sol | cercanias | 37 | nombre+proximidad |
| Pitis | metro | ↔ | Pitis | cercanias | 41 | nombre+proximidad |
| Parla Centro - Bulevar Norte | ml | ↔ | Parla | cercanias | 41 | nombre+proximidad |
| Leganés Central | metro | ↔ | Leganés | cercanias | 43 | nombre+proximidad |
| Villaverde Alto | metro | ↔ | Madrid-Villaverde Alto | cercanias | 50 | nombre+proximidad |
| Méndez Álvaro | metro | ↔ | Méndez Álvaro P.V. | cercanias | 53 | nombre+proximidad |
| Embajadores | metro | ↔ | Embajadores | cercanias | 54 | nombre+proximidad |
| Coslada Central | metro | ↔ | Coslada | cercanias | 56 | nombre+proximidad |
| Aeropuerto T-4 | metro | ↔ | Madrid-Aeropuerto T4 | cercanias | 77 | nombre+proximidad |
| Fuenlabrada Central | metro | ↔ | Fuenlabrada | cercanias | 90 | nombre+proximidad |
| Chamartín | metro | ↔ | Madrid-Chamartín-Clara Campoamor | cercanias | 105 | nombre+proximidad |
| Príncipe Pío | metro | ↔ | Madrid-Príncipe Pío | cercanias | 128 | nombre+proximidad |
| Delicias | metro | ↔ | Delicias | cercanias | 135 | nombre+proximidad |
| Gran Vía | metro | ↔ | Sol | cercanias | 361 | verificada |
| Acacias | metro | ↔ | Embajadores | metro | 364 | verificada |

No incluidas por no poder verificarse en esta sesión: Plaza de España ↔ Noviciado (fuentes contradictorias).

## Mapa 2 · comparativa de estaciones de acceso (IDA, viernes 23:30)

| Estación | Líneas | Salida | Recta (m) | A pie (m) | Total (min) | Transbordos |
|---|---|---|---|---|---|---|
| Diego de León | 4, 5, 6 | Juan Bravo - Conde Peñalver | 309 | 342 | 45.3 | 1 |
| Avenida de América | 4, 6, 7, 9 | Ascensor exterior intercambiador | 564 | 678 | 49.2 | 1 |
| Núñez de Balboa | 5, 9 | Núñez de Balboa | 322 | 386 | 52.0 | 2 |
| Manuel Becerra | 2, 6 | Doctor Esquerdo | 970 | 1213 | 52.7 | 1 |
| Lista | 4 | Conde de Peñalver | 430 | 619 | 56.3 | 2 |
| Goya | 2, 4 | Ascensor ext nº4 a A2 L4 | 883 | 1108 | 58.2 | 2 |
| Príncipe de Vergara | 2, 9 | Alcalá | 1064 | 1248 | 60.2 | 2 |
| Rubén Darío | 5 | Almagro | 1057 | 1171 | 65.0 | 2 |
| Cruz del Rayo | 9 | Príncipe de Vergara impares | 1149 | 1305 | 65.6 | 2 |
| Velázquez | 4 | Goya impares | 930 | 1236 | 66.9 | 3 |
| Serrano | 4 | Goya impares | 1041 | 1451 | 70.3 | 2 |

## Mapa 2 · itinerarios

- **IDA · Recomendada** (Cualquier día hasta las 23:00 · viernes y sábado hasta la 1:30): ≈ 45 min, 342 m a pie, 1 transbordo(s) — inicio → metro 11 (Carabanchel Alto→Plaza Elíptica) → transbordo → metro 6 (Plaza Elíptica→Diego de León) → salida → pie → fin
- **IDA · Si la L6 está cortada (7–9 y 21–22 nov 2026)** (Fechas del corte parcial de la L6): ≈ 55 min, 386 m a pie, 2 transbordo(s) — inicio → metro 11 (Carabanchel Alto→Plaza Elíptica) → transbordo → metro 6 (Plaza Elíptica→Oporto) → transbordo → metro 5 (Oporto→Núñez de Balboa) → salida → pie → fin
- **IDA · Domingo a jueves desde las 23:00 (L6 cerrada)** (Domingo a jueves, 23:00–1:30 (L6 sustituida por autobús SC1)): ≈ 67 min, 673 m a pie, 1 transbordo(s) — inicio → metro 11 (Carabanchel Alto→Plaza Elíptica) → salida → pie → bus SC1 (Plaza Elíptica→Legazpi) → cambio → bus SC1 (Legazpi→Diego De León) → pie → fin
- **VUELTA · Recomendada** (Con metro en servicio: hasta la 1:30 o desde las 6:00 (al cierre de la sala)): ≈ 47 min, 342 m a pie, 1 transbordo(s) — inicio → pie → entrada → metro 6 (Diego de León→Plaza Elíptica) → transbordo → metro 11 (Plaza Elíptica→Carabanchel Alto) → fin
- **VUELTA · Si la L6 está cortada (7–9 y 21–22 nov 2026)** (Fechas del corte parcial de la L6): ≈ 57 min, 386 m a pie, 2 transbordo(s) — inicio → pie → entrada → metro 5 (Núñez de Balboa→Oporto) → transbordo → metro 6 (Oporto→Plaza Elíptica) → transbordo → metro 11 (Plaza Elíptica→Carabanchel Alto) → fin
- **VUELTA · De madrugada, sin metro (1:30–6:00)** (Noches de viernes y sábado (frecuencias del GTFS de EMT)): ≈ 72 min, 597 m a pie, 1 transbordo(s) — inicio → pie → bus N2 (Príncipe De Vergara - Diego De León→Cibeles) → pie → bus N17 (Cibeles→Metro Carabanchel Alto) → pie → fin
- **VUELTA · Domingo a jueves de 23:00 a 1:30 (L6 cerrada)** (Domingo a jueves, 23:00–1:30): ≈ 61 min, 638 m a pie, 1 transbordo(s) — inicio → pie → bus SC2 (Diego De León→Legazpi) → cambio → bus SC2 (Legazpi→Plaza Elíptica) → pie → entrada → metro 11 (Plaza Elíptica→Carabanchel Alto) → fin

Supuestos: a pie 4.5 km/h por la red peatonal OSM; espera = mitad del intervalo de paso (frequencies.txt) en la franja del escenario; pasillos = distancia andén–acceso × 1.3 + 1.0 min.

## Comprobaciones técnicas

Ver `npm run check` (consola del navegador sin errores en escritorio y móvil, buscador y capas) y `npm run build`.
