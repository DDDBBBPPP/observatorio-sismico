# Instalación, histórico y publicación

Todos los comandos PowerShell de esta guía se ejecutan desde la raíz del
repositorio salvo que se indique otra carpeta. El [README](../README.md)
resume el sistema. Esta guía sirve para una **instalación nueva**; no vuelva a
cargar el histórico si PostgreSQL ya contiene esa instantánea.

## Arrancar los cinco servicios

Instale Git, Docker Desktop con motor Linux y Compose v2, Python 3.12+ y
Node.js 22.12+ con npm. Mientras el PR esté en borrador, clone la rama:

```powershell
git clone --branch 002-ingesta-usgs-persistencia --single-branch https://github.com/DDDBBBPPP/observatorio-sismico.git
Set-Location observatorio-sismico
Copy-Item .env.example .env
notepad .env
docker compose config --quiet
docker compose up --build -d
docker compose ps
Invoke-RestMethod http://127.0.0.1:8000/api/salud
```

Cambie `POSTGRES_PASSWORD` por un valor local, configure `CORS_ORIGINS` con
los orígenes exactos y guarde `.env` solo en su equipo. Compose aplica el
esquema PostgreSQL al arrancar el consumidor y el productor comienza a
consultar el feed móvil; compruebe que `kafka`, `postgres`, `producer`,
`consumer` y `api` están `healthy`. `docker compose logs --tail 100 SERVICE`
permite diagnosticar un servicio concreto. Kafka y PostgreSQL tienen
volúmenes persistentes; no los borre para reiniciar.

## Panel y API locales

La API responde en `http://127.0.0.1:8000/api/salud`,
`/api/eventos`, `/api/estadisticas` y `/docs`. Para Angular, ponga
`"apiUrl": "http://127.0.0.1:8000"` en `frontend/public/config.json`, con
`"mode": "api"`. En otra consola:

```powershell
Set-Location frontend
npm ci
npm start -- --host 127.0.0.1 --poll 2000
```

Abra `http://127.0.0.1:4200/`. El `CORS_ORIGINS` de `.env.example` ya permite
`localhost:4200` y `127.0.0.1:4200`. Si cambia `.env`, aplique la nueva
configuración de la API con `docker compose up -d --no-deps --force-recreate
api` desde la raíz. No ejecute esta recreación durante una medición de 24 h.

## Carga histórica separada

Compose **no** descarga el catálogo 2025. En una instalación limpia, tras
verificar los servicios, descargue una vez el periodo mundial 2025 con
`minmagnitude=4` y `eventtype=earthquake`:

```powershell
docker compose exec -T producer python /app/src/main.py load-historical 2025
```

El comando conserva originales y manifiesto bajo
`evidence/002-ingesta-usgs-persistencia/historical/`. Revise el manifiesto
real antes de procesarlo. El batch valida intervalos y usa checkpoints; no
presupone que una nueva descarga reproduzca exactamente los 18.302 eventos
de la instantánea documentada. Ejecute **un solo batch a la vez**:

```powershell
docker compose run --rm --no-deps consumer python /app/src/main.py process-historical /evidence/002-ingesta-usgs-persistencia/historical/2025-minmag4-earthquake-manifest.json
```

Si un run ya terminó, responde `already_completed`; no lo fuerce de nuevo.
Los filtros y el periodo de la instantánea conservada figuran en
[calidad](ANALISIS-CALIDAD.md). El replay es optativo y se aísla de live e
histórico:

```powershell
docker compose run --rm --no-deps producer python /app/src/main.py replay-historical /evidence/002-ingesta-usgs-persistencia/historical/2025-minmag4-earthquake-manifest.json --limit 10 --delay-seconds 0.25
```

## ngrok, CORS y Netlify

Instale el agente ngrok y configure su token **en el equipo**, con las
instrucciones de su cuenta. No lo añada a Git ni a `config.json`. Con la API
local sana, ejecute `ngrok http 8000`; conserve abierto el agente y compruebe
`https://SU-TUNEL/api/salud`. En
`frontend/public/config.json`, escriba esa URL base HTTPS en `apiUrl`, sin
`/api`; conserve `mode: "api"` y `skipNgrokWarning: true`.

Añada el origen exacto de Netlify, sin barra final, al `.env` local:

```dotenv
CORS_ORIGINS=http://localhost:4200,http://127.0.0.1:4200,https://SU-SITIO.netlify.app
```

Antes de una medición, aplique el cambio con
`docker compose up -d --no-deps --force-recreate api`. Verifique que el
preflight desde ese origen pasa y que la API responde por el túnel. Desde
`frontend/` compile y publique la carpeta generada:

```powershell
$origin = 'https://SU-SITIO.netlify.app'
$tunnel = 'https://SU-TUNEL'
$headers = @{ Origin = $origin; 'Access-Control-Request-Method' = 'GET'; 'Access-Control-Request-Headers' = 'ngrok-skip-browser-warning'; 'ngrok-skip-browser-warning' = 'true' }
(Invoke-WebRequest -UseBasicParsing -Method Options -Uri "$tunnel/api/eventos" -Headers $headers).Headers['Access-Control-Allow-Origin']
```

Debe devolver exactamente el valor de `$origin`. Después compile:

```powershell
Set-Location frontend
npm ci
npm run build
```

Para despliegue manual, suba `frontend/dist/observatorio/browser` al proyecto
Netlify. Si conecta el repositorio, use base `frontend`, comando
`npm run build` y directorio publicado `dist/observatorio/browser` relativo
a esa base; `frontend/netlify.toml` declara el build. Compruebe el
`config.json` y la vista pública después de publicar. La interfaz queda
servida por Netlify, pero los datos requieren equipo, Docker y ngrok activos.
Una URL ngrok nueva exige actualizar `config.json`, compilar y desplegar otra
vez; un build local por sí solo no modifica Netlify.

## Pruebas y monitor

`python tools/run_checks.py` ejecuta comprobaciones con límites de tiempo,
incluida integración Kafka y build Angular. Use esa batería fuera de la
medición de disponibilidad, porque puede interrumpir un servicio. Para
inspeccionar una medición existente sin detenerla:

```powershell
Get-Content evidence/002-ingesta-usgs-persistencia/monitor-entrega-20261118.jsonl | Select-Object -Last 1
python tools/evaluate_monitor.py evidence/002-ingesta-usgs-persistencia/monitor-entrega-20261118.jsonl
```

El monitor local toma muestras de servicios, API, BD y lag Kafka cuando está
disponible. No demuestra por sí solo disponibilidad externa de Netlify o
ngrok. La evaluación de 24 horas solo es válida cuando transcurre el periodo
completo sin huecos ni reinicios que invaliden la medición.
