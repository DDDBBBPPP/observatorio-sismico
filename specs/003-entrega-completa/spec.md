# Especificación: entrega completa del Observatorio Sísmico

## Objetivo

Una persona evaluadora debe poder arrancar el sistema en Windows, consultar
datos USGS recientes e históricos, revisar su procedencia y analizar los
resultados desde el panel Angular sin confundir datos sintéticos, históricos y
live.

## Escenarios de usuario

### US1 — Consulta reciente

El usuario abre el panel y ve un mapa GeoJSON de los terremotos actuales,
filtros compartidos, una tabla alternativa y el momento de la última lectura.
Si la API falla, el panel conserva la última lectura y muestra un aviso
explícito.

### US2 — Análisis histórico comparable

El usuario filtra por periodo, magnitud y país y consulta recuentos horarios,
distribuciones y la media diaria de 2025, cuyo denominador incluye los días sin
eventos.

### US3 — Reproducción aislada

La persona defensora selecciona una parte del histórico, la publica por Kafka
como reproducción acelerada y observa que sus eventos llevan tiempo original,
tiempo de reproducción y etiqueta de reproducción, sin mezclarse con live.

### US4 — Operación y trazabilidad

La persona operadora arranca los cinco servicios, ejecuta la ingesta periódica,
consulta los originales y puede repetir una carga sin duplicar versiones.

## Requisitos funcionales

- **REQ-001** La API ofrecerá `/api/eventos`, `/api/estadisticas` y
  `/api/salud` con errores explícitos y sin convertir fallos de base de datos
  en cero resultados.
- **REQ-002** `/api/eventos` devolverá una única versión actual por evento en
  GeoJSON, con filtros equivalentes de fecha UTC, magnitud y país, metadatos y
  paginación cuando proceda.
- **REQ-003** Las estadísticas usarán el mismo conjunto filtrado que el mapa,
  incluirán país sin asignar, nulos, ventanas horarias UTC y comparación con
  2025 usando días cero en el denominador.
- **REQ-004** El productor consultará USGS cada 60 segundos, conservará
  originales y procedencia y publicará solo novedades o revisiones posteriores.
- **REQ-005** El consumidor validará, enriquecerá geográficamente y persistirá
  de forma transaccional e idempotente; los rechazos quedarán en cuarentena.
- **REQ-006** Los registros sintéticos, incluidos los identificados como
  `controlled-*`, quedarán excluidos de los resultados reales mediante una
  marca persistente y una migración reproducible.
- **REQ-007** El histórico inicial usará los filtros mundiales de 2025,
  magnitud mínima 4 y `eventtype=earthquake`; sus originales y manifiesto serán
  reutilizables.
- **REQ-008** La reproducción histórica usará un topic aislado, `mode=replay`,
  timestamps original y de reproducción y etiquetas visibles en API/panel.
- **REQ-009** El panel conservará el mapa entregado, añadirá filtros,
  indicadores, tabla, leyendas, nulos, estado de API e ingesta y refresco de
  60 segundos.
- **REQ-010** La documentación incluirá instalación Windows, procedencia,
  diccionario, modelo de datos, calidad, conclusiones, complejidad, costes,
  límites y pruebas observadas.
- **REQ-011** La comparación aplicará magnitud mínima al menos 4 tanto a la
  ventana consultada como a la instantánea histórica `historical_initial` de
  2025; informará duración, recuentos y media histórica para esa duración.
- **REQ-012** Las respuestas live completas se conservarán 30 días en disco y
  PostgreSQL; después permanecerán los metadatos y originales por evento.
  El histórico no caduca por esta regla.
- **REQ-013** El panel mostrará histogramas de magnitud y profundidad, y
  tratará los valores `datetime-local` etiquetados UTC como UTC.
- **REQ-014** El panel separará filtros editados de filtros aplicados en mapa,
  indicadores, gráficos y tabla; ofrecerá país por nombre y código, opción
  «Sin país asignado», limpieza de filtros y recuadre al resultado cuando
  corresponda. La vista de reproducción explicará y mostrará ambos tiempos.

## Criterios de aceptación

1. `docker compose up --build -d` deja saludables exactamente cinco servicios.
2. Un evento live real aparece en Kafka, PostgreSQL y `/api/eventos` con su
   original y procedencia.
3. Reenviar la misma versión no aumenta el estado actual; una revisión posterior
   sí actualiza el estado y una antigua no lo reemplaza.
4. Magnitud nula, mar y coordenadas inválidas se muestran o se conservan según
   las reglas documentadas, sin puntos inventados.
5. La API devuelve `truncated`, `total` y páginas coherentes cuando el límite
   de respuesta se alcanza.
6. El panel muestra filtros, tabla, mapa, indicadores y aviso si la lectura o
   la ingesta están antiguas.
7. El histórico corregido contiene los filtros exigidos y puede reconstruirse
   sin descargar de nuevo.
8. La reproducción no aparece como live y conserva ambos tiempos.

## Fuera de alcance

Autenticación de la API pública, predicción sísmica, Spark/Flink, Kubernetes,
un sexto servicio Compose y credenciales de Netlify/ngrok.

## Supuestos

- El catálogo Natural Earth entregado es la fuente geográfica de referencia.
- La URL de Netlify y la URL pública de ngrok se aportan manualmente durante la
  publicación y nunca se guardan como secretos.
- Las estadísticas se calculan sobre el estado actual, salvo la comparación
  histórica, que usa versiones del histórico inicial.
- David eligió desempatar múltiples polígonos con el menor `ADM0_A3` y marcar
  `multiple_matches`; avisar tras 10 minutos sin ingesta completada. Motivos y
  consecuencias en `docs/ANALISIS-CALIDAD.md`.
