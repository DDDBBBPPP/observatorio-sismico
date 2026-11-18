# Contrato mínimo de la API

## GET /api/eventos

Devuelve HTTP 200, `Content-Type: application/json` y un GeoJSON `FeatureCollection`. Sin eventos: `features: []`, no un error. Cada evento aparece una sola vez, con su versión actual. Por defecto devuelve terremotos ocurridos en las últimas 24 horas.

```json
{
  "type": "FeatureCollection",
  "metadata": {
    "generated": 1793113200000,
    "last_ingestion": 1793113140000,
    "mode": "live",
    "count": 1,
    "truncated": false
  },
  "features": [{
    "type": "Feature",
    "id": "ejemplo-ficticio",
    "geometry": {"type": "Point", "coordinates": [-3.7, 40.4, 12]},
    "properties": {
      "mag": 3.2,
      "magType": "ml",
      "place": "Ejemplo ficticio",
      "time": 1793109600000,
      "updated": 1793110000000,
      "country_id": "ESP",
      "country_name": "España"
    }
  }]
}
```

`generated`: generación de esta respuesta; no implica que la ingesta siga activa. `last_ingestion`: última consulta correcta a USGS. Fechas en milisegundos Unix UTC. Coordenadas en orden longitud, latitud, profundidad (km). Usa `null`, nunca NaN/Infinity, para magnitud, profundidad o país desconocidos. Geometría válida obligatoria en este endpoint.

Filtros implementados: `start` (ISO8601, inclusive), `end` (ISO8601, exclusive), `min_mag`, `country_id`, `min_depth_km` y `max_depth_km`. Los dos límites de profundidad son opcionales e inclusivos, en km; admiten números negativos. Sin rango, se conservan las profundidades nulas; con cualquier límite, no coinciden. Valores no numéricos/no finitos o mínimo mayor que máximo devuelven HTTP 400 con motivo. El mismo rango se aplica a `/api/eventos`, `/api/estadisticas` y a la comparación histórica 2025. La magnitud nula no cumple `min_mag` y se contabiliza por separado.

Para limitar el tamaño, la API puede aplicar un máximo documentado de puntos. Si trunca, debe indicar `truncated: true`, el total completo y un mecanismo de paginación. El panel final deberá mostrarlo y no calcular estadísticas globales sobre una muestra truncada. El componente inicial espera una colección pequeña y completa.

## Otros endpoints a implementar

| Ruta | Resultado |
|---|---|
| GET /api/salud | Estado API y fecha de última ingesta; no credenciales |
| GET /api/estadisticas | Conteos por hora UTC/país, distribuciones y comparación histórica |

`/api/salud` distingue `source_last_fetch.received_at` (última consulta USGS
correcta, incluso sin eventos nuevos) de `ingestion.finished_at` (último run
procesado por el consumidor). `metadata.last_ingestion` en `/api/eventos`
refleja la primera fecha, en milisegundos Unix UTC; si aún no existe la marca
del productor, usa el último run procesado disponible.

`/api/salud.trace` es lectura de PostgreSQL para la ingesta live acumulada:
`last_new_event_persisted_at` usa la primera versión live por ID;
`last_persisted_at` es el máximo `ingested_at` live; `revisions_stored` cuenta
versiones live adicionales por ID y `quarantined` excluye eventos de prueba
`controlled-*`. Los descartes duplicados y el lag del consumidor no tienen
contador persistente fiable en esta API: se devuelven como `null` y el panel
presenta «no medido». No se invoca Docker ni se publican rutas administrativas.

Los filtros de estadísticas deben equivaler a los del mapa. Cada resultado debe indicar periodo, filtros, unidad y registros sin valor. Si la base falla, devuelve un error explícito; no cero eventos como si fuera un resultado válido.

## Acceso desde Netlify

Configura CORS en FastAPI para el origen exacto de la web y `http://localhost:4200` durante desarrollo; métodos GET y OPTIONS, y cabecera `ngrok-skip-browser-warning`. Si utilizas `CORSMiddleware`, este middleware atiende el preflight. No necesitas cookies para una API pública de consulta de estos datos.

El encabezado de ngrok evita su página intermedia cuando es aplicable; no autentica al usuario. No incluir secretos en config.json. Añade timeout y manejo de errores en el frontend.

## Transporte y contenedores

La API es un servicio Docker, igual que productor, consumidor, Kafka y PostgreSQL. Uvicorn escucha en `0.0.0.0:8000`. ngrok termina el HTTPS público y gestiona el certificado; la API recibe HTTP local. El frontend utiliza la URL HTTPS del túnel. Desde otro contenedor de la misma red, el agente se conecta a `http://api:8000`; desde el host, al puerto publicado.
