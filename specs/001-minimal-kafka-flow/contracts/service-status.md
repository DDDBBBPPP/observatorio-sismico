# Contrato de estado de servicios

Este contrato define la evidencia mínima de arranque del hito. No sustituye el
contrato futuro de la API sísmica.

## Estados

- `starting`: iniciado pero no preparado.
- `ready`: comprobación específica superada y proceso persistente disponible.
- `completed`: activación controlada terminada correctamente; nunca se
  interpreta como `ready`.
- `failed`: comprobación o proceso fallido.
- `unavailable`: no se pudo comprobar o contactar.

## Comprobaciones

| Servicio | Comprobación prevista |
|---|---|
| Kafka | Verificación de disponibilidad del broker y acceso al topic de prueba |
| PostgreSQL | `pg_isready` y conexión local del servicio |
| API FastAPI | `GET /api/salud` en `http://127.0.0.1:8000/api/salud` dentro del contenedor; solo se publica `127.0.0.1:8000:8000` al host |
| Consumidor | Proceso persistente iniciado y conexión al broker |
| Productor | Proceso persistente con comprobación de conexión al broker; `exec` informa `completed` o `failed` |

La evidencia debe conservar la hora, el estado, el comando o comprobación
usada y el síntoma si falla. La salud de PostgreSQL o API no afirma que haya
datos guardados ni que existan consultas de terremotos.

El productor persistente no se declara `ready` hasta conectar con Kafka,
crear o validar idempotentemente el topic de prueba con una partición y una
réplica, y completar la operación de cliente requerida. El proceso persistente
se inicia con `python /app/src/main.py serve`; la activación controlada usa
`python /app/src/main.py publish-test` y puede terminar en `completed` sin
cambiar el estado persistente a `ready`.
