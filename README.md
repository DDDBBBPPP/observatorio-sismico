# Observatorio Sísmico

Proyecto local de cinco servicios: Kafka, PostgreSQL, productor Python,
consumidor Python y API FastAPI. El panel Angular se ejecuta aparte. Consulta
`ENUNCIADO.md`, `CONTRATO-API.md`, [estado](docs/ESTADO-PROYECTO.md),
[calidad](docs/ANALISIS-CALIDAD.md), [modelo](docs/MODELO-DATOS.md),
[diccionario](docs/DICCIONARIO-DATOS.md),
[mediciones y costes](docs/ANALISIS-COMPLEJIDAD-COSTES.md) y
[aceptación](docs/ACEPTACION.md).

## Revisión de la rama 002 y prueba de 24 horas

El sobre Kafka live y replay utiliza `event_id` como clave. Live conserva el
Feature original en el mensaje y referencia la respuesta GeoJSON completa
guardada en `evidence/`, con SHA-256. El consumidor verifica referencia,
integridad y pertenencia del evento antes de guardar la respuesta una sola vez
en PostgreSQL. Acepta además los sobres antiguos con el GeoJSON integrado.
Los mensajes malformados se registran en cuarentena por topic, partición y
offset para que no bloqueen el avance; los errores de base de datos conservan
el offset sin confirmar. El batch histórico valida el contenido real del
manifiesto, su cobertura, recuentos y versiones. Un run antiguo `completed`
sin checkpoints se reconoce por su recuento y las respuestas conservadas.
Ninguno de estos cambios requiere volver a cargar el histórico existente.

Desde la raíz y con los cinco servicios activos, se puede tomar una muestra
breve con límite de tiempo:

```powershell
python tools/monitor_24h.py --once --output evidence/002-ingesta-usgs-persistencia/monitor-smoke.jsonl
```

Para iniciar la prueba larga en segundo plano sin bloquear PowerShell:

```powershell
$probe = Start-Process -FilePath (Get-Command python).Source -ArgumentList @('tools/monitor_24h.py','--duration-hours','24','--interval-seconds','300') -WorkingDirectory (Get-Location).Path -WindowStyle Hidden -PassThru -RedirectStandardOutput 'evidence/002-ingesta-usgs-persistencia/monitor-24h.stdout.log' -RedirectStandardError 'evidence/002-ingesta-usgs-persistencia/monitor-24h.stderr.log'
$probe.Id | Set-Content evidence/002-ingesta-usgs-persistencia/monitor-24h.pid
```

Cada línea de `evidence/002-ingesta-usgs-persistencia/monitor-24h.jsonl`
contiene fecha UTC, salud de los cinco servicios, última consulta USGS
correcta, recuentos live/histórico/replay/cuarentena, errores de descarga y
retraso del grupo consumidor Kafka cuando se puede leer. Consultar la última
muestra con:

```powershell
Get-Content evidence/002-ingesta-usgs-persistencia/monitor-24h.jsonl | Select-Object -Last 1
```

Para detenerla antes de completar las 24 horas:

```powershell
Stop-Process -Id ([int](Get-Content evidence/002-ingesta-usgs-persistencia/monitor-24h.pid))
```

El monitor de esta revisión empezó el **18-11-2026 a las 00:13:39 UTC**
(01:13:39 en Madrid), PID guardado en `monitor-24h.pid`. La primera muestra
registró cinco servicios sanos, cero errores y lag Kafka 0. Evaluar mañana
la cadencia, huecos mayores de 450 segundos, servicios no sanos, antigüedad
de la consulta USGS mayor de diez minutos, errores y lag con:

```powershell
python tools/evaluate_monitor.py
```

`complete_24h` solo pasa a `true` cuando las muestras abarcan al menos 24
horas. La auditoría reproducible por país usa la instantánea conservada en
`evidence/002-ingesta-usgs-persistencia/audit-country-20261117/all_day.geojson`
y la ventana fija `2026-11-17T12:00:00Z` a `23:00:00Z`:

```powershell
python tools/audit_countries.py
python tools/run_checks.py --skip-kafka
```

La opción `--skip-kafka` deja al consumidor en marcha durante la medición de
24 horas; la prueba Kafka con reinicio ya se ejecutó antes de iniciar el
monitor. El panel publicado en
`https://stellar-basbousa-cee41b.netlify.app/` corresponde al despliegue
Netlify `6afcef8a47d80fa7d8a964ed` de esta revisión. **Un build local
posterior no actualiza automáticamente esa web:** requiere otro despliegue.

## Instalación en Windows

Requisitos: Docker Desktop con motor Linux y Compose v2, PowerShell, Node.js
22.12+/npm y Python 3.12+ para las comprobaciones locales. Desde la raíz
**local** del proyecto:

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
docker compose config --quiet
docker compose up --build -d
docker compose ps
Invoke-RestMethod http://127.0.0.1:8000/api/salud
```

`docker compose up --build -d` arranca automáticamente el flujo **live**:
productor → Kafka → consumidor → PostgreSQL → API. No descarga ni reconstruye
el histórico 2025 de 18.302 registros.

Esperar a que los cinco servicios indiquen `healthy`. PostgreSQL y Kafka
persisten en volúmenes Compose; **no** usar `down -v` para reiniciar. La API
solo expone `127.0.0.1:8000` en el equipo. El productor consulta el feed USGS
cada 60 segundos por defecto (`USGS_POLL_INTERVAL_SECONDS`), reintenta fallos
de HTTP y conserva originales en `evidence/002-ingesta-usgs-persistencia/`.
Los fallos periódicos se registran en `live-errors.jsonl` en ese directorio.
Los originales completos live se conservan 30 días en archivos y
`source_response`; después permanecen los metadatos y originales por evento.
La elección y su motivo están en `docs/ANALISIS-CALIDAD.md`.

El panel local, en **otra ventana de PowerShell** desde la raíz del proyecto:

```powershell
Set-Location frontend
npm ci
npm start -- --host 127.0.0.1 --poll 2000
```

Abrir `http://127.0.0.1:4200/`. `frontend/public/config.json` contiene la URL
HTTPS del túnel usado en la publicación actual; para una instalación local sin
ese túnel, cambiar temporalmente `apiUrl` a `http://127.0.0.1:8000` y devolverlo
a HTTPS antes de compilar para Netlify. Si la API falla, el panel conserva la
última lectura con un aviso; distingue la hora de lectura, generación de
respuesta y última consulta USGS correcta, incluso si no hubo eventos nuevos.
El mapa, filtros, barras y tabla consultan la API. Las respuestas grandes se
paginan (por defecto 1.000, máximo 5.000 puntos); los indicadores usan el
conjunto filtrado completo.
El selector muestra nombres de países y envía su código `ADM0_A3` a la API;
incluye «Sin país asignado». Al cambiar un filtro aparece «Cambios sin
aplicar»: mapa, gráficos y tabla conservan el último conjunto hasta pulsar
«Aplicar filtros». «Limpiar filtros» vuelve a la vista general. REPRODUCCIÓN
presenta la fecha original y la fecha de reenvío por separado. El sondeo de
archivos de `ng serve` evita que Windows siga sirviendo una versión anterior
tras editar el panel. Si una pestaña aún muestra «País/código» como campo
libre, recargarla con `Ctrl+Shift+R` y comprobar que el servidor se inició con
el comando anterior.

## Histórico y replay

En el estado local actual, el histórico comparable es 2025 mundial,
`minmagnitude=4`, `eventtype=earthquake`: 12 originales y 18.302 registros. El
manifiesto antiguo de 140.559 registros tiene filtros distintos. Los originales
históricos están excluidos de Git: una instalación limpia puede mostrar live
tras arrancar los servicios, pero necesita descargar y procesar el histórico
una vez para disponer de comparación. La cifra de una descarga nueva puede
variar si USGS revisa el catálogo. En un Windows nuevo, ejecutar el comando
de descarga siguiente y después el comando principal de procesamiento de este
apartado; el comando de prueba de un intervalo es opcional. Para obtener o
reutilizar la descarga:

```powershell
docker compose exec -T producer python /app/src/main.py load-historical 2025
```

Para procesar, usar **un único batch a la vez**. Primero un intervalo de prueba
con sufijo propio; después el comando principal. El batch confirma por
intervalo, usa checkpoints y no elimina originales ni runs. Si el run ya está
completo responde `already_completed`.

```powershell
docker compose run --rm --no-deps consumer python /app/src/main.py process-historical /evidence/002-ingesta-usgs-persistencia/historical/2025-minmag4-earthquake-manifest.json --max-intervals 1 --run-suffix=-smoke
docker compose run --rm --no-deps consumer python /app/src/main.py process-historical /evidence/002-ingesta-usgs-persistencia/historical/2025-minmag4-earthquake-manifest.json
```

Para una carga larga, ejecutar el comando con `docker compose run -d` y un
`--name` único, sin `--rm`, y seguir **un solo registro** con `docker logs -f
NOMBRE`; consultar checkpoints en PostgreSQL si se interrumpe. No lanzar otro
batch mientras esté activo.

El replay publica por Kafka una selección limitada (10 por defecto) y guarda
versiones en tablas separadas; no altera el histórico ni los eventos live:

```powershell
docker compose run --rm --no-deps producer python /app/src/main.py replay-historical /evidence/002-ingesta-usgs-persistencia/historical/2025-minmag4-earthquake-manifest.json --limit 10 --delay-seconds 0.25
```

Seleccionar «REPRODUCCIÓN» en Angular. Son terremotos reales antiguos
reenviados por Kafka en un conjunto separado; no representan actividad actual.
La vista consulta enero de 2025: «Desde» y «Hasta» filtran la **fecha original**,
no `replay_at`. La ficha y la tabla muestran la fecha original y la fecha de
reenvío. El aviso de retraso de la ingesta live solo se presenta en «Datos
reales». Los sintéticos del hito 001 y `controlled-*` están marcados y
excluidos del análisis real.

## API, aceptación y publicación

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/eventos?min_mag=4&page_size=100'
Invoke-RestMethod 'http://127.0.0.1:8000/api/estadisticas?min_mag=4'
python tests/acceptance.py
```

La aceptación verifica GeoJSON, paginación, filtros, media histórica con 365
días, replay, CORS y error por ventana inválida. El modo replay se consulta con
`mode=replay&start=2025-01-01T00:00:00Z&end=2025-02-01T00:00:00Z`.

La comparación del panel aplica magnitud mínima efectiva ≥4 a ambos periodos:
eventos actuales únicos sin sintéticos frente a la instantánea de 2025. Si la
ventana filtrada no dura 24 horas, se muestra la media histórica ajustada a su
duración; no implica equivalencia estacional. Los filtros de fecha del panel
se interpretan en UTC. Las distribuciones incluyen registros sin valor.

### Revisión visual local

Con frontend y los cinco servicios activos, abrir `http://127.0.0.1:4200/`.
Comprobar mapa con fronteras y círculos (tamaño por magnitud, color por
profundidad), filtros UTC/magnitud/país, barras por país/hora y distribuciones,
comparación ≥4, tabla, modo REPRODUCCIÓN y horas de lectura/ingesta. Tomar una
captura con filtros visibles. Para el fallo de API, ejecutar `docker compose
stop api`, refrescar el panel y comprobar el aviso y la última lectura;
`docker compose start api` debe permitir la recuperación en el siguiente
refresco (hasta 60 s). Dejar los cinco servicios activos al terminar. David
observó en la versión nueva «País», «Filtros aplicados» y la explicación de
las dos fechas. En REPRODUCCIÓN de enero de 2025, USA **aplicado** mostró cero
y «Todos los países» **aplicado** mostró diez. En Netlify, David aportó capturas
del mapa, indicador, gráficos por país/hora y tabla. Siguen pendientes la
observación visual completa de distribuciones y del aviso de caída/recuperación.

### Publicación manual y disponibilidad

1. En la cuenta de ngrok, instalar y vincular el agente para Windows siguiendo
   sus instrucciones **solo en el equipo**. Ejecutar `ngrok http 8000` y
   mantenerlo abierto. Copiar la URL base pública HTTPS sin `/api` y comprobar
   su `/api/salud`. Compartir solo esa URL pública, nunca datos de acceso.
2. Escribir esa URL en `frontend/public/config.json`, campo `apiUrl`, dejando
   `mode: "api"` y `skipNgrokWarning: true`. En `frontend/`, ejecutar
   `npm run build`. Verificar `dist/observatorio/browser/index.html`,
   `config.json` y `_redirects` (`/* /index.html 200`). **Recompilar** después
   de cualquier cambio de URL antes de subir la carpeta.
3. En la cuenta Netlify, elegir **Add new project → Deploy manually** y subir
   la carpeta compilada `frontend/dist/observatorio/browser`. Obtener la URL
   principal exacta `https://NOMBRE.netlify.app`. Si se conecta el repositorio
   en otro momento: directorio base `frontend`, comando `npm run build`,
   directorio publicado `dist/observatorio/browser` relativo a esa base;
   `frontend/netlify.toml` ya declara los dos últimos. No subir la raíz del
   repositorio como si fuera el build.
4. Añadir el origen exacto de Netlify, sin barra final, en `CORS_ORIGINS` de
   `.env`, conservando `http://localhost:4200,http://127.0.0.1:4200`; ejemplo:
   `CORS_ORIGINS=http://localhost:4200,http://127.0.0.1:4200,https://NOMBRE.netlify.app`.
   Aplicar con `docker compose up -d --no-deps --force-recreate api`. Verificar el
   preflight y abrir el panel desde otro dispositivo con ngrok activo.

En la sesión del 16-11-2026 se comprobó la URL principal pública
`https://stellar-basbousa-cee41b.netlify.app/` y su `config.json` sin sesión:
ambas responden HTTP 200. El JSON apunta a
`https://sapling-unlearned-blush.ngrok-free.dev`, cuyo agente local dirige el
túnel al puerto 8000. El `.env` **local**, excluido de Git, autoriza CORS para
la URL principal y la URL del despliegue además de los dos orígenes locales.
En una instalación Windows nueva, añadir el origen exacto de su propio sitio
al `.env` antes de recrear la API. David observó en incógnito el mapa con
círculos, indicadores y filas de la tabla; véase `docs/ACEPTACION.md`.

Netlify sirve la interfaz aun si se detienen el PC, Docker o ngrok, pero en
ese caso no puede consultar la API local. Para mostrar datos y mantener la
ingesta durante la defensa deben seguir activos el equipo, los cinco
servicios y el túnel. No incluir authtoken, credenciales, `node_modules` ni
originales en Git.

El análisis propio, los costes, las limitaciones y las cifras observadas están
en `docs/`. Las comprobaciones HTTP y la observación visual comunicada por
David constan por separado en `docs/ACEPTACION.md`.
