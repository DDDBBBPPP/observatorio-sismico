# Guía de visualización del Cuadro de mando

## Contrato semántico y cobertura

- Fuente: terremotos USGS mundiales, `eventtype=earthquake`, magnitud ≥4;
  umbral adicional del usuario ≥4. Una fila por `event_id` vigente. Replay y
  sintéticos fuera de cualquier cifra.
- Candidatos comparables: 2023, 2024 y 2025 completos. 2023–2024 se rotulan
  «sin cobertura» hasta carga y conciliación verificadas. 2026 es parcial hasta
  acreditar los intervalos correspondientes. No se rellenan huecos con ceros.
- Filtros: año, últimos 12 meses, última semana y magnitud mínima. Periodos
  `[inicio, fin)` UTC. El ancla de las ventanas móviles y la última
  sincronización se muestran; un PC apagado deja una copia fechada, nunca un
  indicador de tiempo real.
- Un día cubierto es el día UTC cuya parte solicitada tiene cobertura USGS
  acreditada y ya sincronizada. Mostrar siempre `días cubiertos / días del
  periodo`; los días restantes dicen «sin cobertura». Las cifras y gráficos
  usan únicamente días cubiertos. Sin días cubiertos, KPI y gráficos dicen
  «sin cobertura». Un cero solo corresponde a un periodo cubierto sin eventos.
- KPI: (1) registros únicos = `count(distinct event_id)`; (2) media diaria =
  registros únicos elegibles / días cubiertos, con denominador explícito; (3)
  magnitud máxima no nula y fecha UTC de ocurrencia, ND si no hay magnitud.
  Un empate de magnitud se resuelve por fecha más reciente y luego por ID.
- Reconciliación visible/automática: los países (incluido «Sin país asignado»)
  y las profundidades (incluido ND) suman los registros únicos. Las clases de
  magnitud más ND suman los registros únicos. Los porcentajes indican su
  denominador, por ejemplo `n / total de registros únicos`; los valores
  calculados mantienen precisión y solo se redondean al mostrarse.

## Composición y lectura

1. **Cabecera compacta:** título, rango UTC, fuente USGS, criterio de selección
   y «Última sincronización con Supabase: fecha y hora UTC». Aclarar que son
   datos sincronizados, no actividad en directo; mostrar cobertura y filtros
   aplicados en el mismo bloque.
2. **Tres KPI:** registros únicos, media diaria con `N días cubiertos` y
   magnitud máxima con fecha. Una cifra sin cobertura o ND no se reemplaza por
   cero. Etiquetas y unidades visibles.
3. **Evolución mensual a todo el ancho:** meses en orden UTC y recuentos con
   eje desde cero. Solo comparar meses completos bajo los mismos filtros;
   marcar los parciales y los que no tienen cobertura. Si se muestran varios
   años, distinguirlos con leyenda y texto legible, sin depender solo de color.
4. **Dos columnas en escritorio:** histograma de magnitud y distribución de
   profundidad en km, con clases rotuladas, eje de recuento desde cero y
   categorías ND explícitas. Los cortes exactos se fijan antes de T004/T005 y
   deben ser estables entre filtros comparados.
5. **Países al final:** barras horizontales desde cero, orden y criterio de
   agrupación documentados, «Sin país asignado» visible y porcentajes con
   denominador. Los recuentos describen registros asignados; no miden riesgo
   sísmico ni cobertura mundial uniforme.
6. **Móvil:** una columna en el mismo orden, sin desplazamiento horizontal de
   página a 375 px. Títulos informativos, ejes/unidades legibles, color limitado
   y coherente, contraste suficiente y texto para estado/ND/cobertura. Evitar
   decoración que dificulte comparar barras o valores.

## Comprobaciones de presentación

- Al cambiar cualquier filtro, cabecera, rango, 3 KPI y 4 gráficos se actualizan
  en una sola transición de estado; una respuesta anterior no pisa la nueva.
- Una semana con 4 de 7 días cubiertos muestra `4/7`, media con divisor 4 y
  tres días «sin cobertura». Con 0 de 7 no muestra cero en los KPI.
- Un año bisiesto completo usa 366 días; uno común, 365. 2023–2024 no se
  ofrecen como completos hasta que la conciliación lo demuestre.
- En escritorio y a 375 px se comprueban orden, legibilidad de unidades y
  etiquetas, ejes desde cero, ND, porcentajes y ausencia de scroll horizontal.

## Referencias aportadas por David

Los enlaces son inspiración para crear un diseño propio, no una plantilla que
se copie. La lectura web básica de Tableau exigió JavaScript y no permitió
inspeccionar sus paneles; el navegador integrado tampoco estuvo disponible en
esta revisión. No se atribuyen rasgos concretos a esos ejemplos.

- [Marketing Campaign](https://public.tableau.com/app/profile/kelsey.oehrke/viz/MarketingCampaign_17707801166540/Overview?utm_source=chatgpt.com)
- [Superstore](https://public.tableau.com/app/profile/pradeepkumar.g/viz/SuperstoreDashboard-VizExtensionsEdition/viz?utm_source=chatgpt.com)
- [Animal Shelter](https://public.tableau.com/app/profile/jemarlim/viz/AnimalShelterOperation/Overivew?utm_source=chatgpt.com)
- [Automation Control Room](https://public.tableau.com/app/profile/maureen.okonkwo/viz/AutomationControlRoomDashboard/ControlRoom)
- [Medical Devices](https://public.tableau.com/app/profile/sarah.pallett/viz/MedicalDeviceSalesDashboard/MedicalDevicesSalesInventory)

David también señaló dos sesiones de `juanarrow.github.io/BigData` en la
conversación. Sus URL y contenidos no constan en el contexto disponible para
esta revisión; quedan registradas como referencias pendientes de identificación
y no se les atribuyen decisiones visuales.
