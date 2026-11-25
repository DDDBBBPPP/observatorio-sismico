# T001: modelo analítico y contrato de lectura

## Origen y proyección

La fuente local es `event_current` de
`consumer/src/migrations/001_ingestion_schema.sql`, unida por
`event_version_id` a `event_version`. El sincronizador futuro debe leer una
instantánea consistente y enviar estos valores a `analytics_apply_event`:

| Origen local | Argumento / destino remoto | Regla |
| --- | --- | --- |
| `c.event_id` | `p_event_id` / `event_id` | Clave USGS única; excluir `controlled-*`. |
| `c.current_updated` | `p_updated_ms` / `updated_ms` | Revisión USGS; solo un valor mayor reemplaza el vigente. |
| `c.event_time` | `p_event_time_ms` / `event_time_ms` | Milisegundos UTC de ocurrencia; filtros `[inicio, fin)`. |
| `c.mag` | `p_mag` / `mag` | Magnitud finita; elegible si ≥4. Una revisión posterior <4 o nula conserva solo una marca privada de revisión y desaparece de la lectura. |
| `c.depth_km` | `p_depth_km` / `depth_km` | Puede ser nula (ND); km. |
| `c.country_id`, `c.country_name` | argumentos homónimos / columnas homónimas | Nulos se presentan «Sin país asignado». |
| `c.source`, `c.is_synthetic`, `v.mode` | `p_source`, `p_is_synthetic`, `p_mode` | Solo `usgs`, no sintético, modo `live` o `historical`. |
| `c.original_jsonb #>> '{properties,type}'` | `p_event_type` | Debe ser `earthquake`; el JSON original no sale de PostgreSQL local. |

`event_current` ya contiene la fila vigente y `event_version` conserva la
procedencia y el modo. El filtro debe comprobar además que
`c.current_updated = v.updated`, `c.event_id = v.event_id`, que la versión
no es sintética y que su fuente es USGS. Las tablas `replay_event_*` nunca
participan. La selección local no debe filtrar únicamente magnitud ≥4 antes
de sincronizar: una revisión nueva que baje del umbral debe enviar su marca de
revisión para retirar el valor antiguo del cuadro. `analytics_apply_event`
rechaza fuente, modo, tipo o marca sintética indebidos; para magnitud <4 o
nula guarda la última revisión solo en la tabla privada con `eligible=false`.

La tabla privada no almacena originales JSON, lugar, coordenadas, ID de
respuesta, `run_id`, cuarentena ni filas de replay. Las migraciones versionadas
están en `supabase/migrations/202611250001_analytics_private.sql` y
`202611250002_analytics_rpc.sql`. `coverage_day` nace vacío: cada fila
certificará en T002/T003 un día UTC completo ya conciliado y sincronizado.
`sync_state` también nace vacío; ninguna fecha de actualización se inventa en
T001.

## Superficie pública acotada

**RPC `public.analytics_events_page`** (`POST /rest/v1/rpc/analytics_events_page`)
es la única lectura otorgada a `anon`. Recibe:

| Parámetro | Límite |
| --- | --- |
| `p_start_ms`, `p_end_ms` | Enteros positivos, inicio < fin, ventana ≤367 días; extremos UTC incluidos/excluidos respectivamente. |
| `p_min_mag` | Número finito ≥4; por defecto 4. |
| `p_after_time_ms`, `p_after_event_id` | Cursor opcional; ambos presentes o ambos ausentes. |
| `p_limit` | De 1 a 500; por defecto 200. |

La respuesta es una página ordenada por `(event_time_ms, event_id)` con solo
`event_id`, `event_time_ms`, `mag`, `depth_km`, `country_id`, `country_name`.
Solo aparecen versiones elegibles de días certificados en `coverage_day`.
Para la página siguiente se usan el tiempo e ID de la última fila. Una página
vacía no prueba por sí misma que haya cobertura; T004 añadirá la consulta de
cobertura, agregados y `last_synced_at` en un contrato de instantánea única.
Hasta entonces esta RPC es una superficie mínima verificable, no el contrato
final que consumirá Angular.

Parámetros fuera de límite devuelven error SQL `22023`, que la capa HTTP debe
tratar como error de solicitud; errores de servidor no se convierten en cero.
La función no acepta SQL dinámico ni campos arbitrarios. Se revoca `EXECUTE`
de `PUBLIC` y `authenticated`; solo `anon` puede leer. La escritura
`public.analytics_apply_event` se concede únicamente a `service_role`. Ambas
funciones fijan `search_path=''` y califican las tablas privadas. Las tres
tablas privadas tienen RLS activado y ningún permiso directo para `anon`,
`authenticated` o `service_role`; el rol de servicio solo escribe mediante la
RPC validada. Las funciones no revelan originales ni tablas de control.

La clave pública de lectura puede ir en la configuración del frontend cuando
se implemente T005. La clave secreta o credencial de escritura solo se guarda
en el entorno del proceso local/servidor; no se añade a Angular, Netlify ni Git.
No hay credenciales reales en este repositorio para T001.

## Comprobación local y despliegue pendiente

`python tests/run_analytics_t001.py` crea un PostgreSQL 16 temporal sin red,
aplica ambas migraciones bajo roles equivalentes a Supabase y ejecuta
`tests/analytics_t001.sql`. Comprueba lectura limitada, denegaciones de
lectura/escritura, cobertura aún no certificada, idempotencia
`(event_id, updated)`, revisión posterior y antigua, cruce del umbral y
rechazo de replay/sintéticos. Al terminar destruye solo ese contenedor.

Para aplicar T001 a Supabase de verdad falta que David cree un proyecto vacío
en su cuenta y facilite el **identificador o URL pública del proyecto**, nunca
una clave secreta en el chat. Las migraciones se aplicarán desde su entorno
autorizado o mediante el editor SQL de su cuenta, en orden, y allí se repetirán
las pruebas de permisos con el rol `anon` antes de cualquier carga. Sin proyecto
no se afirma que Supabase remoto haya sido verificado.
