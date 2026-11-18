# Observatorio sísmico

**Panel público:** https://stellar-basbousa-cee41b.netlify.app/

El proyecto recoge terremotos comunicados por USGS, conserva el original y sus
revisiones, les asigna un país cuando un polígono lo permite y ofrece un panel
para explorar magnitud, profundidad, lugar y periodo. La comparación con 2025
sirve para describir registros con filtros equivalentes; los recuentos por país
no son una medida de riesgo sísmico ni de cobertura mundial uniforme.

## Recorrido de los datos

```text
USGS → productor Python → Kafka → consumidor Python → PostgreSQL
                                               ↓
                                  FastAPI → Angular + Leaflet
                                               ↑
                                   Natural Earth (países)
```

| Servicio Compose | Función |
| --- | --- |
| `producer` | Consulta cada minuto el feed USGS y publica eventos nuevos o revisados. |
| `kafka` | Transporta mensajes live y replay en topics distintos. |
| `consumer` | Valida, versiona, asigna país y persiste; aparta mensajes defectuosos. |
| `postgres` | Guarda versiones, estado actual, originales, checkpoints y cuarentena. |
| `api` | Expone salud, eventos GeoJSON y estadísticas a la interfaz. |

Angular se ejecuta aparte: localmente con `npm start` o publicado en Netlify.
El mapa usa Leaflet y el catálogo Natural Earth incluido en el repositorio.
El túnel ngrok publica **solo la API** por HTTPS; Kafka y PostgreSQL no se
exponen. Véanse el [modelo](docs/MODELO-DATOS.md), el
[SQL del esquema](consumer/src/migrations/001_ingestion_schema.sql) y el
[diccionario](docs/DICCIONARIO-DATOS.md).

## Tres conjuntos diferentes

- **Live:** `all_day.geojson` es una ventana móvil de 24 horas, consultada
  periódicamente. Una respuesta nueva puede traer eventos tardíos o revisiones.
- **Histórico:** instantánea del catálogo USGS de `[2025-01-01, 2026-01-01)`
  UTC, mundo, `type=earthquake`, magnitud ≥4. La copia documentada tiene
  **18.302 eventos**; otra descarga futura puede diferir.
- **Replay:** reenvía una selección histórica por Kafka a tablas separadas.
  Sus tiempos de ocurrencia son antiguos y no se suman al live.

`event_id` es la clave Kafka. PostgreSQL conserva una versión única por
`(event_id, updated)`; una revisión posterior sustituye el estado actual y un
duplicado o versión antigua no lo retrocede. Los mensajes irrecuperables van a
cuarentena para evitar un bucle de reinicio. Los originales y su procedencia
son verificables. «Sin país asignado» incluye mar y puntos fuera de los
polígonos simplificados; no equivale a evento inválido. Magnitud y profundidad
desconocidas permanecen como `null`/ND. Más detalle en
[calidad y análisis](docs/ANALISIS-CALIDAD.md).

## Arranque local en Windows

Requisitos: Git, Docker Desktop con motor Linux y Compose v2, PowerShell,
Python 3.12+ y Node.js 22.12+ con npm. Mientras el PR #1 siga sin fusionar,
clone **esta rama**:

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

Cambie en `.env` la contraseña de desarrollo y añada a `CORS_ORIGINS` los
orígenes desde los que abrirá el panel. No publique `.env` ni el token ngrok.
Espere a que **los cinco servicios** aparezcan `healthy` en `docker compose ps`.
La API local está en http://127.0.0.1:8000/docs y su salud en
http://127.0.0.1:8000/api/salud. Los volúmenes de Kafka y PostgreSQL conservan
los datos entre reinicios; no use `docker compose down -v` para esta instalación.

Compose inicia automáticamente **live**. **No descarga ni carga el histórico
2025**. Una instalación limpia necesita esa operación separada para mostrar
la comparación histórica o ejecutar replay. Los comandos y checkpoints están
en la [guía de instalación](docs/GUIA-INSTALACION.md); no repita esa carga en
una instalación que ya tenga el histórico.

Para abrir el panel local sin túnel, ajuste la URL de la API en el archivo de
configuración público y arranque Angular en otra consola:

```powershell
$configPath = (Resolve-Path frontend/public/config.json).Path
$cfg = Get-Content $configPath -Raw | ConvertFrom-Json
$cfg.apiUrl = 'http://127.0.0.1:8000'
[System.IO.File]::WriteAllText($configPath, ($cfg | ConvertTo-Json -Depth 10), [System.Text.UTF8Encoding]::new($false))
Set-Location frontend
npm ci
npm start -- --host 127.0.0.1 --poll 2000
```

Abra http://127.0.0.1:4200/. Restablezca una URL HTTPS de túnel en
`frontend/public/config.json` antes de compilar para Netlify. El panel ofrece
la vista inicial **«Comparación mundial · magnitud ≥4»** y la exploración
**«Todos los registros comunicados por USGS»**; los filtros aplicados y la
ventana UTC aparecen explícitos. Mapa, gráficos y tabla usan los mismos filtros.

## Publicación desde otra instalación

Inicie `ngrok http 8000` con su cuenta configurada **localmente** y copie la
URL HTTPS que entregue. Compruebe `https://SU-TUNEL/api/salud`. Ponga esa URL
base, sin `/api`, en `frontend/public/config.json` como `apiUrl`; conserve
`mode: "api"` y `skipNgrokWarning: true`. Añada el origen exacto de su sitio
Netlify a `CORS_ORIGINS` en `.env` y aplique el cambio recreando solo la API.
Desde `frontend/`, ejecute `npm run build` y publique
`frontend/dist/observatorio/browser` en Netlify. Los pasos y una comprobación
de CORS figuran en la [guía de instalación](docs/GUIA-INSTALACION.md).

La web **permanece servida por Netlify** aunque se apague el equipo, pero los
datos de la API requieren PC, Docker y túnel activos. Una compilación local no
actualiza automáticamente la web pública: hay que publicar el build nuevo.

## Pruebas y evidencias

Con los servicios sanos y el histórico preparado, desde la raíz:

```powershell
python tools/run_checks.py
docker compose config --quiet
```

`run_checks.py` limita la duración de cada prueba e incluye contrato API,
filtros, SQL, componente Angular, build e integración Kafka. Su prueba de
integración interrumpe el consumidor: **no la ejecute durante una medición de
disponibilidad**. Las pruebas y observaciones anteriores están en
[aceptación](docs/ACEPTACION.md). El contrato de partida se conserva en
[material del profesor](docs/material-profesor/CONTRATO-API.md).

- [Calidad, transformaciones y tres conclusiones](docs/ANALISIS-CALIDAD.md)
- [Modelo de datos](docs/MODELO-DATOS.md) y [diccionario](docs/DICCIONARIO-DATOS.md)
- [Complejidad y costes](docs/ANALISIS-COMPLEJIDAD-COSTES.md)
- [Aceptación y rúbrica](docs/ACEPTACION.md) y [estado](docs/ESTADO-PROYECTO.md)
- [Capturas y manifiesto UTC](evidence/002-ingesta-usgs-persistencia/visual-depth-night-20261118/manifest.json)
- [Guion de defensa](docs/GUIA-DEFENSA.md)
- [Fuentes y licencias](FUENTES-Y-LICENCIAS.md)
- [Enunciado y guía de entregables](docs/material-profesor/README.md)

## Estado de entrega

Los **cinco criterios de la rúbrica** tienen evidencia documentada en
[aceptación](docs/ACEPTACION.md); eso no sustituye una calificación externa.
T005 visual está cerrada con capturas reproducibles. T006 sigue pendiente para
probar desde **otro dispositivo** la caída y recuperación del túnel. La
medición de 24 horas solo puede declararse superada tras completar y evaluar
sus muestras; consulte el [estado actual](docs/ESTADO-PROYECTO.md). El PR #1
sigue en borrador y no se ha fusionado.
