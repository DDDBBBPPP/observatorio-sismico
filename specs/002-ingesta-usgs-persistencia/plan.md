# Implementation Plan: Ingesta USGS y persistencia trazable

**Branch**: `002-ingesta-usgs-persistencia` | **Date**: 2026-11-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-ingesta-usgs-persistencia/spec.md`

## Summary

El hito añade ingesta real de USGS al flujo de cinco servicios existente. El
productor conservará respuestas y metadatos, consultará el feed reciente y
ejecutará una carga batch mensual del histórico completo de 2025. Las
novedades y revisiones del feed se publicarán en un topic live separado del
topic sintético, con mensajes cuyo `mode` solo podrá ser `live` o `replay`.

El consumidor validará y transformará cada versión, asignará país mediante
GeoPandas/Shapely y el catálogo entregado en WGS84, y persistirá de forma
idempotente estado actual, versiones, ingestas, originales JSONB y cuarentena
en PostgreSQL. La carga histórica reutilizará las mismas reglas de validación y
persistencia, pero se identificará mediante metadatos de ejecución batch y no
como recepción reciente.

## Technical Context

**Language/Version**: Python 3.12.8 en las imágenes actuales; PowerShell y
Python local para validaciones documentadas.

**Primary Dependencies**: aiokafka, cliente HTTP, PostgreSQL, GeoPandas/Shapely
y el catálogo Natural Earth entregado.

**Storage**: PostgreSQL persistente con modelo híbrido: columnas y claves para
consultas e integridad, JSONB para originales y payloads; archivos locales
regenerables para respuestas USGS y evidencias.

**Testing**: pruebas unitarias de validación, timestamps y geografía; pruebas
de integración con PostgreSQL/Kafka; escenarios reproducibles de duplicados,
revisiones, cuarentena, histórico, fallos de fuente y reinicio.

**Target Platform**: Docker Desktop con contenedores Linux en Windows; los
cinco servicios del hito 001 siguen siendo los únicos servicios Compose.

**Project Type**: pipeline de ingesta y persistencia con productor,
consumidor, broker y base de datos; API y frontend permanecen fuera del
alcance funcional de este hito.

**Performance Goals**: el feed reciente debe poder procesarse en su intervalo
configurado sin perder el estado válido; la carga anual debe ejecutarse por
meses sin truncar respuestas y con recuentos por intervalo. No se fija un
objetivo de throughput antes de medir.

**Constraints**: `mode` de Kafka limitado a `live`/`replay`; carga inicial
identificada por metadatos batch; no sobrescribir originales; confirmación
posterior a persistencia; errores explícitos; sin secretos ni grandes
descargas en Git; sin endpoints sísmicos, frontend, Netlify, ngrok o replay
implementado en este hito.

**Scale/Scope**: feed móvil de 24 horas y un histórico mundial completo de
2025 con los filtros documentados por el proyecto; un solo repositorio y
volúmenes persistentes locales.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Principio I — contrato y rúbrica: PASS condicionado.** El plan conserva el
contrato GeoJSON para el hito de API posterior y prioriza procedencia,
calidad, modelado, idempotencia y geografía exigidos por la rúbrica.

**Principio II — entrega incremental y vertical: PASS.** El primer incremento
ejecutable será un evento USGS real que atraviese Kafka, consumidor y
PostgreSQL; la carga anual y las evidencias se incorporan después.

**Principio III — integridad, trazabilidad e idempotencia: PASS.** Las claves
`event_id`, `(event_id, updated)`, los originales JSONB, las restricciones,
la cuarentena y el commit antes del offset cubren las reglas obligatorias.

**Principio IV — integración y secretos: PASS.** Se mantienen cinco servicios,
volúmenes y variables de entorno; el catálogo se reutiliza sin descargar
artefactos grandes ni incluir credenciales.

**Principio V — verificación y defensa: PASS.** La guía Windows y las pruebas
por incremento registrarán resultados observados, procedencia, calidad,
fallos, reinicios y limitaciones.

## Project Structure

### Documentation (this feature)

```text
specs/002-ingesta-usgs-persistencia/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── usgs-source.md
│   ├── kafka-event-envelope.md
│   ├── persistence-processing.md
│   └── quality-evidence.md
└── tasks.md             # creado por /speckit-tasks
```

### Source Code (repository root)

```text
compose.yaml
producer/
├── src/
│   ├── main.py
│   ├── event_model.py
│   ├── topic_config.py
│   ├── usgs_client.py
│   ├── live_ingest.py
│   ├── historical_loader.py
│   └── ingestion_state.py
consumer/
└── src/
    ├── main.py
    ├── validation.py
    ├── geography.py
    ├── persistence.py
    └── migrations/
        └── 001_ingestion_schema.sql
api/
└── src/                  # solo salud técnica en este hito
frontend/
└── public/datos/paises.geojson
evidence/002-ingesta-usgs-persistencia/
tests/
├── unit/
└── integration/
```

**Structure Decision**: Se amplían `producer/` y `consumer/` existentes sin
crear un sexto servicio Compose. El productor separa cliente live y carga
batch, pero ambos reutilizan estado y contratos. El consumidor concentra
validación, geografía y persistencia. Los originales y evidencias de ejecución
son regenerables y quedan fuera de Git cuando contienen descargas locales.

## Phase 0: Research

1. Documentar el contrato real de las respuestas USGS recientes e históricas:
   campos opcionales, unidades, límites, errores y ventanas temporales.
2. Comparar la carga mensual batch con una carga monolítica y justificar la
   división mensual, la deduplicación de límites y la reutilización de
   originales.
3. Documentar reglas de GeoPandas/Shapely para WGS84, fronteras, múltiples
   coincidencias, geometrías inválidas y ausencia de país.
4. Justificar el modelo híbrido, las restricciones y los índices a partir de
   las consultas de estado actual, versiones, intervalos y cuarentena.
5. Precisar recuperación ante fallo entre persistencia y confirmación de
   offset sin prometer transacción distribuida Kafka-PostgreSQL.

El resultado queda en [research.md](./research.md). No quedan decisiones
materiales sin resolver salvo la topología futura de replay, que está fuera
del alcance.

## Phase 1: Design

1. Definir entidades, claves, estados, transiciones y reglas de actualización
   en [data-model.md](./data-model.md).
2. Definir el contrato de fuente en [usgs-source.md](./contracts/usgs-source.md),
   el sobre Kafka en [kafka-event-envelope.md](./contracts/kafka-event-envelope.md),
   la frontera de persistencia en
   [persistence-processing.md](./contracts/persistence-processing.md) y el
   formato mínimo de evidencias en [quality-evidence.md](./contracts/quality-evidence.md).
3. Validar en Windows el primer flujo real, después duplicados/revisiones,
   validación/cuarentena, geografía y carga histórica con
   [quickstart.md](./quickstart.md).
4. Recalcular la puerta constitucional: PASS; los contratos no introducen
   endpoints de API ni fijan replay.

## Incrementos de implementación previstos

1. **Evento USGS real hasta PostgreSQL**: feed live, mensaje `mode=live`,
   validación mínima, esquema híbrido y persistencia de una versión válida.
2. **Idempotencia y revisiones**: duplicado exacto, revisión posterior,
   versión antigua, confirmación posterior a escritura y reinicio.
3. **Calidad y cuarentena**: nulos, tipos no sísmicos, coordenadas inválidas,
   errores de fuente, originales y motivos duraderos.
4. **Integración geográfica**: catálogo WGS84, punto en polígono, fronteras,
   varias coincidencias y «Sin país asignado».
5. **Histórico anual**: descarga mensual de 2025, metadatos batch,
   deduplicación de límites, reutilización de originales y comparación de
   recuentos.
6. **Evidencias de calidad**: comprobaciones de completitud, unicidad,
   validez, consistencia, actualidad y exactitud con denominadores y
   resultados antes/después.

El replay de demostración, su topología y su aislamiento final se planificarán
en un hito posterior.

## Complexity Tracking

No hay violaciones constitucionales que justificar.
