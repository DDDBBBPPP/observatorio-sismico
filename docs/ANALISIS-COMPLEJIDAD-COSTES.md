# Complejidad, rendimiento y costes

## Medición reproducible

`docker compose run --rm --no-deps producer python /app/src/measure_transform.py`
midió cinco repeticiones del filtro en memoria `new_earthquakes` sobre las
primeras filas del original de enero de 2025. Equipo: AMD Ryzen 5 3600,
34.276.089.856 bytes de RAM, Windows y Docker Desktop. Mediana de tiempo;
pico de memoria Python medido con `tracemalloc`, sin incluir el JSON ya cargado,
arranque Docker, Kafka, red, geografía ni PostgreSQL.

| Entrada | Mediana | Pico Python |
|---:|---:|---:|
| 100 features | 0,034 ms | 1,3 KiB |
| 500 features | 0,175 ms | 4,4 KiB |
| 1.000 features | 0,381 ms | 8,9 KiB |

El filtro recorre N features: O(N) tiempo. `IngestionState` usa diccionario para
consultar una versión por ID con coste O(1) medio y O(U) memoria para U IDs;
el estado se escribe en JSON tras publicar cada versión, lo que añade E/S
proporcional al número de IDs y limita el rendimiento sostenido. PostgreSQL
usa una clave única `(event_id,updated)` para idempotencia y un índice temporal
para ventanas. La asignación geográfica consulta un índice espacial para
reducir polígonos candidatos; su coste depende también de geometrías y
solapamientos. Estos números no predicen throughput extremo a extremo.

En una consulta de una hora de 2025 sobre 18.724 filas actuales, `EXPLAIN
(ANALYZE, BUFFERS)` observó `Index Scan` en `event_current_event_time_idx`:
1 fila, 3 bloques y 0,070 ms de ejecución. Al desactivar temporalmente
`enable_indexscan` y `enable_bitmapscan` dentro de una transacción, el recorrido
secuencial tardó 6,622 ms y leyó 2.688 bloques. Son dos ejecuciones con caché
distinta y no una garantía de aceleración para todas las consultas.

## Costes y límites

Los 12 originales históricos corregidos ocupan **21.384.619 bytes** locales.
Se suman PostgreSQL, índices, Kafka, imágenes Docker, frontend y backups;
los originales se conservan fuera de Git. El coste de desarrollo se calcula
como horas reales trabajadas × tarifa aplicable; no hay registro fiable de
horas ni tarifa en este repositorio, así que no se inventa un importe.

Ejemplo de presupuesto eléctrico, **supuesto no medido**: 50 W adicionales
durante 4 h/día por 30 días = 6 kWh. Con una tarifa supuesta de 0,20 €/kWh,
serían 1,20 €. Para estimarlo de verdad, medir potencia incremental en el
equipo y usar la factura vigente de David. Netlify y ngrok pueden tener cuotas;
un plan gratuito no elimina tiempo, almacenamiento ni mantenimiento. La
operación local depende del portátil, Docker y túnel. Para escala mayor,
considerar partición temporal, almacenamiento frío de originales y métricas
del pipeline completo antes de elegir infraestructura adicional.
