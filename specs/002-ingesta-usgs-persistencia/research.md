# Research: Ingesta USGS y persistencia trazable

## Decisiones

### Fuente reciente y catálogo histórico

- **Decisión**: usar el feed móvil `all_day.geojson` para live y consultas
  mensuales del catálogo USGS para el histórico completo de 2025.
- **Motivo**: el feed reciente se actualiza aproximadamente cada minuto y el
  catálogo permite dividir el año, registrar consultas y repetir la carga sin
  depender de una ventana móvil.
- **Alternativas consideradas**: descargar un año en una sola petición o usar
  exclusivamente el feed reciente. La primera puede truncar resultados y la
  segunda no permite una comparación anual reproducible.

### Carga mensual y originales

- **Decisión**: descargar cada mes una vez, conservar respuesta, parámetros,
  fecha y recuentos, y reutilizar el mismo conjunto de reglas de validación y
  persistencia.
- **Motivo**: los límites temporales pueden solapar eventos; la división
  permite subdividir consultas grandes y auditar cada intervalo.
- **Alternativas consideradas**: una carga monolítica o repetir descargas en
  cada reinicio. Ambas empeoran la reproducibilidad y pueden perder o duplicar
  registros.

### Contratos de mensajes

- **Decisión**: los mensajes Kafka de datos reales admiten únicamente
  `mode=live` y `mode=replay`. La carga histórica inicial es un proceso batch y
  se identifica con `load_type`, `period`, `interval` y `run_id` en metadatos de
  extracción, no con `mode=historical`.
- **Motivo**: `live` y `replay` son los modos funcionales del contrato; la
  descarga inicial no es una reproducción de demostración.
- **Alternativas consideradas**: añadir `mode=historical`, rechazado porque
  contradice el enunciado.

### Modelo híbrido PostgreSQL

- **Decisión**: columnas tipadas y restricciones para estado actual,
  versiones, ingestas y cuarentena; JSONB para el original y payloads.
- **Motivo**: las consultas por tiempo, evento, versión y estado necesitan
  claves e índices, mientras que JSONB conserva procedencia sin perder campos
  futuros de USGS.
- **Alternativas consideradas**: solo JSONB, que debilita restricciones y
  filtros; o un modelo completamente descompuesto, que dificulta conservar
  exactamente el original.

### Geografía

- **Decisión**: GeoPandas/Shapely en el consumidor, con puntos y catálogo en
  WGS84/EPSG:4326.
- **Motivo**: hace explícita la operación punto-en-polígono y permite
  documentar fronteras, varias coincidencias y ausencia de cobertura.
- **Alternativas consideradas**: asignar país desde `place`, rechazado porque
  no es una integración geográfica; o posponer la geografía, rechazado por la
  rúbrica del incremento.

### Idempotencia y confirmación

- **Decisión**: persistencia al menos una vez, clave única por evento actual y
  por `(event_id, updated)`, actualización solo si la versión es posterior y
  confirmación del offset después de la transacción.
- **Motivo**: cubre reentregas y fallos entre escritura y confirmación sin
  exigir una transacción distribuida Kafka-PostgreSQL.
- **Alternativas consideradas**: confirmar antes de escribir, que puede perder
  datos; o exigir exactamente una vez distribuido, fuera del alcance local.

## Incertidumbres resueltas

- El periodo inicial es 2025 completo.
- El feed live usará un topic separado del topic sintético.
- El histórico inicial no introduce un tercer valor de `mode`.
- La topología futura de replay no se decide en este hito.
