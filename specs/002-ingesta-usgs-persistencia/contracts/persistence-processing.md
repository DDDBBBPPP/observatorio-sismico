# Contrato de procesamiento y persistencia

## Entrada

Un mensaje que cumple [kafka-event-envelope.md](./kafka-event-envelope.md) o un
registro batch con la misma forma de evento y metadatos de carga.

## Salidas observables

- `accepted`: versión válida persistida.
- `duplicate_version`: `(event_id, updated)` ya existente, sin nuevo efecto.
- `older_version`: versión anterior conservada sin reemplazar el estado actual.
- `quarantined`: original y motivo duraderos.
- `failed`: error de persistencia o infraestructura; no se confirma el offset.

## Reglas

1. Validar campos, tipos, unidades, fechas y coordenadas.
2. Convertir tiempos a UTC conservando originales.
3. Asignar país mediante punto en polígono WGS84, sin usar `place`.
4. Persistir versión e historial de forma transaccional.
5. Actualizar estado actual solo si `updated` es posterior.
6. Confirmar offset después de commit o cuarentena duradera.
