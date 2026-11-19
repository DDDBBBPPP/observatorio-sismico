# Quickstart de validación en Windows

Esta guía valida los incrementos de ingesta sin implementar todavía la API
sísmica, el frontend, Netlify, ngrok ni replay.

## Prerrequisitos

- Docker Desktop con contenedores Linux y Compose v2.
- Rama `002-ingesta-usgs-persistencia` y `.env` local generado desde
  `.env.example`.
- Python local para ejecutar verificadores y evidencias.
- Las imágenes y dependencias disponibles; las descargas USGS se conservan
  localmente y no se versionan.

## Incremento 1: un evento USGS real

1. Arrancar los cinco servicios del hito 001:

   ```powershell
   docker compose up --build -d
   docker compose ps
   ```

2. Ejecutar una consulta controlada del feed live y registrar `run_id`,
   respuesta original y metadatos.
   Desde PowerShell, el comando operativo dentro del productor es:

   ```powershell
   docker compose exec -T producer python /app/src/main.py ingest-live
   ```

3. Comprobar que el mensaje publicado usa el topic live y `mode=live`.
4. Esperar al consumidor y comprobar en PostgreSQL el evento actual, su versión
   y la referencia al original.
5. Conservar comando, salida, recuentos y timestamps en
   `evidence/002-ingesta-usgs-persistencia/<run_id>/`.

Resultado esperado: un evento real válido llega a PostgreSQL sin mezclarse con
el topic sintético ni con una carga histórica.

## Incremento 2: duplicados y revisiones

Procesar una secuencia controlada:

1. versión inicial;
2. repetición idéntica;
3. revisión con `updated` posterior;
4. versión antigua recibida después.

Comprobar que el estado actual tiene una fila, que el historial tiene dos
versiones y que la versión antigua no reemplaza a la revisión.

## Incremento 3: validación y cuarentena

Ejecutar casos sintéticos separados para magnitud nula, tipo no `earthquake`,
coordenada inválida, JSON incompleto y evento marítimo. Comprobar que:

- los nulos conservan su significado;
- los tipos excluidos registran motivo;
- los inválidos conservan original y motivo en cuarentena;
- el evento marítimo queda como «Sin país asignado»;
- los mensajes posteriores continúan.

## Incremento 4: geografía

Validar un punto dentro de un país, un punto marítimo, un punto sobre frontera
y una geometría con varias coincidencias según la regla documentada. Registrar
catálogo, sistema WGS84, resultado, razón y limitación.

## Incremento 5: histórico 2025

1. Ejecutar la carga mensual una sola vez.
2. Conservar cada respuesta original, consulta, intervalo, fecha y recuento.
3. Subdividir únicamente los intervalos que superen el límite de la fuente.
4. Deduplicar los límites por `(event_id, updated)`.
5. Reiniciar el entorno y repetir desde los originales sin descargar de nuevo.

La carga inicial se identifica con `load_type=historical_initial` y
`mode=historical` en PostgreSQL, fuera de Kafka. Los mensajes Kafka solo usan
`mode=live` o `mode=replay`.

Los originales live se conservan bajo
`evidence/002-ingesta-usgs-persistencia/originals/<run_id>/` junto con sus
metadatos. Son regenerables y están excluidos de Git; la repetición desde
archivo se reservará para la tarea T046.

## Evidencia de calidad

Para cada dimensión conservar conjunto, denominador, consulta o código,
resultado antes/después, acción, limitación y `run_id`. Cubrir como mínimo
completitud, unicidad, validez y consistencia; añadir actualidad y exactitud
cuando los datos permitan medirlas.

## Fallos y recuperación

Repetir con timeout, HTTP 429/5xx, JSON inválido, consumidor detenido y fallo
entre escritura y confirmación. El resultado debe identificar el componente,
conservar el último estado válido, evitar confirmaciones ficticias y demostrar
que el reinicio no duplica efectos.
