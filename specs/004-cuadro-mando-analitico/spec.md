# Especificación: Cuadro de mando analítico

## Objetivo y alcance

Añadir a la web Angular publicada en Netlify una sección «Cuadro de mando», sin
mapa, que consulte datos analíticos alojados en Supabase. El flujo existente
USGS → productor → Kafka → consumidor → PostgreSQL → API y la exploración actual
de Angular se conservan. Supabase recibe una copia de lectura analítica desde
PostgreSQL local cuando el equipo está encendido; no sustituye la base local ni
la API existente.

Las reglas de presentación están en `guia-visualizacion.md`. El diseño inicial
de T001 no autoriza ninguna descarga ni carga histórica.

## Escenarios y requisitos

### Consulta con el equipo encendido

- **CM-01** La sección consulta exclusivamente el conjunto analítico de
  Supabase mediante una superficie de lectura limitada. No depende de que la
  API local o el túnel estén disponibles para mostrar los datos sincronizados.
- **CM-02** La sincronización local copia solo terremotos reales de USGS que
  sean la versión vigente. Una repetición no crea duplicados y una versión
  antigua no reemplaza otra más reciente.
- **CM-03** La sincronización conserva un progreso recuperable. Tras un corte o
  reinicio reintenta lo no confirmado y reconcilia posibles huecos antes de
  declarar la copia al día. Una carga inicial y los incrementos posteriores
  usan la misma regla de identidad y revisión.

### Consulta con el equipo apagado

- **CM-04** Netlify sigue sirviendo Angular y el cuadro muestra los datos ya
  sincronizados en Supabase, junto con la **fecha y hora de última
  sincronización correcta**. La etiqueta explica que es una copia y no afirma
  que sea actividad en tiempo real. Se distingue esa fecha de la del terremoto
  más reciente y de la hora en que el navegador hizo la consulta.
- **CM-05** Un fallo de lectura muestra un estado de error o de datos no
  disponibles; nunca convierte el fallo en cero terremotos ni cambia la fecha
  de sincronización. Un conjunto vacío válido se identifica por separado.

### Periodos y coherencia

- **CM-06** Los filtros son **año**, **últimos 12 meses**, **última semana** y
  **magnitud mínima**. El umbral del cuadro es siempre ≥4; uno menor se rechaza
  o se explica como fuera del conjunto comparable. Todos los límites de tiempo
  son `[inicio, fin)` UTC. Cada respuesta identifica intervalo efectivo,
  cobertura y fecha de copia. Título, rango, KPI y gráficos usan un único filtro
  aplicado y una única instantánea; las respuestas antiguas no los mezclan.
- **CM-07** El conjunto comparable inicial **propuesto** son 2023, 2024 y 2025
  completos: terremotos USGS mundiales con magnitud ≥4 y
  `eventtype=earthquake`. La cobertura de 2025 existente no acredita 2023–2024:
  esos años se muestran «sin cobertura» hasta cargarlos y conciliarlos. 2026
  es parcial hasta acreditar su cobertura. Un hueco nunca cuenta como cero.
- **CM-10** La cabecera muestra periodo UTC, fuente USGS, criterio de selección
  y última sincronización correcta con Supabase. Los tres KPI son registros
  únicos (`event_id` vigente), media diaria sobre días cubiertos y magnitud
  máxima con fecha de ocurrencia UTC. La media usa como numerador los registros
  elegibles ocurridos en días cubiertos del filtro y como denominador el número
  de días UTC cubiertos del mismo filtro; con cero días cubiertos se muestra
  «sin cobertura», no cero. La magnitud máxima ignora magnitudes nulas; si no
  hay ninguna válida se muestra ND, sin inventar fecha. Un empate se resuelve
  por fecha de evento más reciente y después por `event_id` estable.
- **CM-11** Un día cubierto es un día calendario UTC cuya intersección con el
  intervalo solicitado tiene cobertura de origen acreditada y ya sincronizada
  de extremo a extremo. Los KPI y gráficos usan solo esos días. Se informa
  «N de M días cubiertos»; los días restantes se marcan «sin cobertura». Una
  ventana válida con días cubiertos y sin eventos sí puede mostrar cero.
- **CM-12** El cuadro incluye evolución mensual comparable, histograma de
  magnitud, distribución de profundidad en km con ND y barras horizontales de
  países con «Sin país asignado». Cada gráfico utiliza los mismos eventos
  elegibles que los KPI y hace visibles nulos, cobertura y denominadores. Una
  comparación mensual usa idénticos filtros y solo trata como equivalentes los
  meses completamente cubiertos; los meses incompletos quedan marcados como
  parciales o «sin cobertura». Los recuentos por país describen asignaciones,
  **no riesgo sísmico**.

### Separación de datos y seguridad

- **CM-08** Replay, pruebas sintéticas y eventos `controlled-*` quedan fuera de
  las cifras reales, tanto en la carga inicial como en cada sincronización y
  consulta. La procedencia y el alcance de la cobertura deben poder auditarse.
- **CM-09** El navegador no contiene credenciales de escritura ni conexión a
  PostgreSQL. La lectura pública solo expone columnas y operaciones necesarias
  para el cuadro; no da acceso a originales, procedencia interna, tablas de
  control ni funciones de escritura. Se prueban permisos y aislamiento con el
  rol público antes de publicar.

## Criterios de aceptación para las entregas futuras

1. Una misma identidad de USGS aparece una sola vez; reejecutar la carga o el
   sincronizador deja idénticos recuentos. Una revisión nueva actualiza la
   copia y una antigua no la revierte.
2. Cortar el proceso a mitad de lote y reiniciarlo completa la copia sin
   pérdidas ni duplicados. Los controles de integridad comparan el origen real
   elegible con Supabase en periodos cubiertos.
3. Replay y sintéticos no figuran en la copia pública ni en los agregados. El
   rol público no puede leer tablas privadas ni escribir, incluso mediante
   llamadas directas a la API de Supabase.
4. Con el PC, Docker y el túnel apagados, la sección sigue consultando la copia
   desde la web publicada y muestra la última sincronización correcta. No
   muestra una señal de «en directo».
5. Cambiar de periodo actualiza conjuntamente título, rango efectivo y todas
   las cifras. Un año sin cobertura y un error de red se distinguen de un cero
   real; una respuesta lenta anterior no sobrescribe el filtro nuevo.
6. Para un año completo acreditado, el contrato devuelve 365 o 366 días
   cubiertos según corresponda; 2023 y 2024 devuelven «sin cobertura» hasta
   que existan cargas conciliadas. 2026 indica cobertura parcial mientras
   falten días. Si faltan 3 de 7 días, se muestra `4/7` y la media usa 4,
   no 7; si no hay días cubiertos, no hay media ni máximo.
7. Al cambiar año/ventana o magnitud, cabecera, 3 KPI y 4 gráficos comparten
   identificador de consulta, rango UTC y marca de sincronización. Sus totales
   coinciden: suma de países incluida la categoría sin asignar = registros
   únicos; suma de profundidad incluida ND = registros únicos; suma de
   magnitud = registros con magnitud válida, con nulos declarados aparte.
8. En móvil (375 px) no hay desplazamiento horizontal de la página; las
   secciones siguen el orden cabecera → KPI → evolución → magnitud/profundidad
   → países. En escritorio, evolución ocupa el ancho, magnitud y profundidad
   dos columnas y países va al final. Ejes, unidades, porcentajes y estado
   «sin cobertura» se leen sin depender solo del color.

## Decisiones aún abiertas

- Confirmar cuándo se cargan y concilian 2023 y 2024; hasta entonces son
  objetivos de cobertura, no datos disponibles.
- Elegir el año/periodo predeterminado según cobertura realmente acreditada.
- Concretar los cortes del histograma y de la profundidad, el número máximo de
  barras de países y los redondeos visibles sin alterar los totales subyacentes.
