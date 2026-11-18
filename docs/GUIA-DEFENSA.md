# Guion oral de defensa (unos cinco minutos)

Las cifras de 2025 pertenecen a la instantánea documentada, con periodo
`[2025-01-01, 2026-01-01)` UTC, mundo, `type=earthquake` y magnitud ≥4.
Las cifras de la ventana reciente que cito son **observaciones fechadas**,
no valores actuales del panel. Llevar abiertas la
[aceptación](ACEPTACION.md), las [capturas](../evidence/002-ingesta-usgs-persistencia/visual-depth-night-20261118/manifest.json)
y el [panel público](https://stellar-basbousa-cee41b.netlify.app/).

## 0:00–0:45 · Problema y alcance

«Quiero responder dónde **se han comunicado** terremotos y cómo se distribuyen
en una ventana temporal, sin confundir esa muestra con todo el riesgo sísmico
del mundo. El panel permite explorar mapa, países, magnitudes, profundidades y
horas. Comienza con una comparación mundial de magnitud cuatro o superior; la
otra vista deja examinar todos los registros del feed USGS, donde la cobertura
de terremotos pequeños es desigual. Por eso enseño siempre ventana UTC y
filtros aplicados.»

## 0:45–1:40 · Cómo llegan los datos

«Cinco servicios Docker forman el backend. El productor consulta cada minuto
`all_day.geojson`, una ventana móvil de 24 horas. Publica en Kafka con
`event_id` como clave. El consumidor valida tipo, fechas, coordenadas y
versiones, busca país en los polígonos Natural Earth y guarda en PostgreSQL.
FastAPI lee las tablas preparadas; Angular muestra los resultados y está
publicado en Netlify. Un túnel ngrok une la web con la API local. Los
originales y su procedencia quedan conservados o referenciados con hash para
auditar qué recibió el sistema.»

## 1:40–2:30 · Calidad y modelo

«La identidad de una versión es `(event_id, updated)`: repetirla no duplica
el evento y una revisión más nueva puede actualizar su estado. Una versión
antigua no lo hace retroceder. Los mensajes imposibles de procesar se
registran en cuarentena con topic, partición y offset; una caída de base de
datos conserva el mensaje para reintentarlo. Magnitud o profundidad nulas
siguen siendo ND: no las convierto en cero. El país puede quedar sin asignar
porque el punto está en el mar o fuera de los polígonos simplificados; eso no
invalida el terremoto. El replay usa tablas propias y nunca se suma al live.»

## 2:30–3:45 · Tres conclusiones con filtros fijos

«Primero: en la instantánea mundial de 2025, magnitud ≥4, **14.350 de 18.302
eventos, el 78,41 %**, no recibieron país del catálogo. Mantener la categoría
evita perderlos. Segundo: con los mismos filtros y profundidad **0–70 km
inclusive**, hay **13.690 de 18.302, el 74,80 %**. El límite importa: un
evento está exactamente a 70 km. Tercero: en la ventana fija
**17 de noviembre de 2026 a las 00:43 hasta el 18 a las 00:43 UTC**, mundo y
magnitud ≥4, el estado persistido observado a las 12:34 UTC tenía **24**
eventos, frente a una media de **50,14 por día** calculada con los 18.302 de
2025; la diferencia es **−52,1 %**. La instantánea USGS tomada al cerrar la
ventana tenía 22: llegaron dos registros más tarde. Esa comparación describe
dos muestras y no predice actividad futura ni corrige estacionalidad.»

## 3:45–4:35 · Coste, límites y disponibilidad

«La base separa versión, estado actual, original y cuarentena. Los índices por
tiempo y país permiten consultas de ventanas; medí también casos con y sin
índice, pero esas mediciones no garantizan el mismo rendimiento en otra
máquina. La copia histórica documentada contiene doce originales y su coste
de almacenamiento es medible; no invento una factura eléctrica o laboral.
Netlify puede servir la interfaz aunque mi equipo esté apagado, pero los
datos requieren este PC, Docker y ngrok. La prueba local de 24 horas solo
podrá declararse completada tras transcurrir y evaluar todas las muestras;
además queda probar caída y recuperación del túnel desde otro dispositivo.»

## 4:35–5:00 · Cierre

«El resultado es una cadena reproducible desde el original USGS hasta un
panel filtrable y auditable. Lo más importante es leer cada cifra junto a su
periodo, filtro y procedencia. Las capturas y la aceptación permiten revisar
las tres conclusiones sin depender de que el feed móvil siga igual mañana.»

## Esquema de demostración en vivo

1. Abra el panel: señale ventana UTC, última consulta USGS y vista mundial ≥4.
2. Cambie a «Todos los registros comunicados por USGS» y muestre el aviso de
   cobertura desigual de magnitudes pequeñas; **no memorice el recuento live**.
3. Aplique país y profundidad 0–70 km: señale «Vista aplicada» y confirme que
   mapa, gráficos y tabla cambian juntos. Limpie filtros.
4. Abra las capturas de las tres conclusiones y su manifiesto: tienen filtro,
   ventana UTC, fecha y recuento reproducibles.
5. Si la API y el túnel están activos, muestre `/api/salud` y distinga última
   consulta USGS de último evento nuevo. Para replay, seleccione el modo y
   enseñe fecha original frente a fecha de reenvío.

## Preguntas probables: respuesta breve

| Pregunta | Respuesta defendible |
| --- | --- |
| ¿Por qué domina USA entre los pequeños? | En la captura fija del 17–18/11/2026, 189/236 registros eran USA, pero con magnitud ≥4 eran 0/22. El feed de pequeños depende de redes y políticas de reporte; el gráfico por sí solo no mide actividad ni riesgo mundial. |
| ¿Qué significa «Sin país asignado»? | Un punto en el mar o fuera de los polígonos Natural Earth simplificados; se conserva con sus coordenadas y no se inventa país. |
| ¿Qué pasa con duplicados y revisiones? | La clave única `(event_id, updated)` evita repetir la versión. Una `updated` posterior sustituye el estado actual; una antigua no. |
| ¿Cuándo avanza el offset Kafka? | Tras persistir con éxito, o tras guardar un mensaje irrecuperable en cuarentena. Si falla PostgreSQL, se hace rollback y no se confirma el offset. |
| ¿Cómo trata los nulos? | `null` permanece ND. Sin filtro de profundidad se incluye; con un rango no coincide. Nunca significa cero. |
| ¿Replay es actividad actual? | No. Reenvía eventos históricos por otro topic y tablas separadas; muestra fecha del terremoto y de reenvío. |
| ¿Cómo compara 2025? | La instantánea 2025 es mundial, `earthquake`, magnitud ≥4; se aplican país y profundidad equivalentes. La media diaria no corrige estacionalidad y el catálogo puede revisarse después. |
| ¿Está siempre disponible? | La interfaz Netlify sí puede cargar; la API y datos actuales dependen del PC, cinco contenedores y ngrok. El monitor local no prueba disponibilidad externa. |
