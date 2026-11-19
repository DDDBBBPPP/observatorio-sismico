# Plan de implementación: entrega completa

## Arquitectura

Se mantienen los cinco servicios Compose. PostgreSQL expone el estado actual,
versiones, procedencia, ejecuciones y cuarentena. Kafka separa el topic
sintético, live y replay. FastAPI consulta únicamente PostgreSQL y Angular
consume FastAPI, nunca USGS.

## Incrementos

1. Corregir filtros y metadatos del histórico 2025; aislar sintéticos.
2. Completar API, filtros, estadísticas, errores y CORS.
3. Activar productor periódico y consumidor de replay.
4. Completar panel Angular y configuración de despliegue.
5. Ejecutar validación integrada y cerrar documentación con resultados reales.

## Pruebas

- Sintaxis Python y configuración Compose.
- Pruebas HTTP de los tres endpoints con base real.
- Casos de duplicado, revisión, versión antigua, cuarentena y replay.
- Build Angular y comprobación de filtros, tabla, mapa y estado.
- Consulta del manifiesto: año completo, mundial, magnitud mínima 4 y
  `eventtype=earthquake`.
- Mediciones de transformación con 100, 500 y 1.000 registros, separando datos
  controlados del análisis real.

## Riesgos y límites

La descarga histórica depende de USGS y puede tardar varios minutos. Netlify y
ngrok requieren acciones manuales y no se ejecutan sin sus cuentas. Los
originales locales no se versionan.

## Cierre local 16-11-2026

El manifiesto corregido tiene 12 intervalos y 18.302 versiones/IDs históricos.
La comparación consulta solo `historical_initial`; la ventana reciente usa el
estado actual sin sintéticos. Se corrigieron el umbral comparable ≥4, fechas UTC,
tipo de `last_ingestion` y distribuciones del panel. Configuración SPA, ruta de
build y cinco servicios se verifican localmente. La inspección visual y ambas
URLs públicas requieren pasos manuales documentados en README.
