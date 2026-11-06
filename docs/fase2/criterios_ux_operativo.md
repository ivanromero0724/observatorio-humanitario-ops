# Replanteamiento funcional del observatorio — interfaz operativa v3
**Fecha:** 6 de noviembre de 2026 · **Estado:** prototipo sujeto a revisión OPS/PHE

## Objetivo concreto

Una persona del equipo PHE debe poder responder, en ese orden:

1. **¿Qué contextos existen con evaluación documentada?** Revisar situación ACAPS, país, temática, gravedad de crisis publicada y acceso, con su fuente. No atribuir prioridad OPS.
2. **¿Cómo evoluciona la amenaza documentada?** Variación mensual de una categoría de eventos HAPI/ACLED, con comparaciones entre países; no sumar categorías superpuestas.
3. **¿Qué se conoce sobre las personas y la atención en salud?** PiN intersectorial por país/año, ACNUR por acogida/origen/grupo, OIM por operación/ronda. Los impactos de ataques a salud requieren SSA: todavía no integrados.
4. **¿Qué condiciones y recursos contextualizan el problema?** OPS (desigualdad, educación, recursos sanitarios, vacunación), OPHI (pobreza), HAPI 3W y financiación FTS.
5. **¿Qué dice la ficha del país y dónde contrastar?** Crisis, riesgo, evolución, poblaciones y recursos, con informes ReliefWeb y fecha de cada fuente.

La primera pantalla **no** debe presentar una suma heterogénea de indicadores o un mapa de INFORM Risk como sustituto de seguimiento. La pantalla principal es un **registro filtrable de contextos humanitarios**. El mapa muestra *dónde existe evaluación en el corte*, no un mapa de ausencia/presencia de amenazas reales.

## Alcance confirmado por la propuesta técnica

- Foco inicial: violencia/conflicto, migración/desplazamiento, acceso y entorno político, crimen/economías ilícitas. No incluir brotes ni El Niño como ejes principales; desastres naturales pueden integrarse después.
- Dimensiones conceptuales diferenciadas: amenaza, exposición, vulnerabilidad, impacto en personas/salud, capacidad de respuesta.
- Crítico, alto, elevado y moderado **no se asignan en este prototipo**. Laura/equipo PHE deben validar indicadores, signos, límites, prioridades y manejo de faltantes.
- La información de crimen organizado, minería/cultivos ilícitos, ataques a salud y servicios interrumpidos **no está aún estandarizada** en el dashboard; no imputar ceros.
- 35 países soberanos actualmente en el catálogo, con arquitectura geográfica para territorios cuando haya datos y reglas aprobadas.

## Jerarquía y diseño en Streamlit

| Pantalla | Visible inmediatamente | Bajo interacción / expansión |
|---|---|---|
| Situaciones documentadas | Filtro de tema; tres métricas de evidencia; tabla de crisis ACAPS con severidad y acceso; mapa de disponibilidad y tendencia HAPI del mismo ámbito | Últimos 8 informes ReliefWeb; cobertura técnica |
| Amenazas y acceso | Dos pestañas: eventos ACLED por categoría, acceso por contexto ACAPS | Indicadores de acceso y tabla de evaluación; amenazas aún no armonizadas |
| Personas e impacto | PiN intersectorial y movilidad transfronteriza; registro de impacto sanitario disponible de OPS | Detalles sectoriales, OIM por operación, notas SSA |
| Vulnerabilidad y respuesta | Comparaciones OPS en indicadores seleccionados y respuesta humanitaria | MPI, tablas históricas y cortes |
| Ficha por país | Registro de contextos, tendencia violencia, necesidades, movilidad y capacidades | Documentos originales, datos por fuente, fechas |

### Proporciones y alineación

- **Contenedor único**: `st.container(border=True)`; borde `#D6E1E9`, radio 12px, fondo blanco, sombra discreta; título azul `#004B87`, subtítulo gris.
- **Paneles emparejados**: todos los pares se crean con `st.columns(2)` y ambos `st.container(border=True,height=490)` o `height=440`. Se elimina la causa de bordes desiguales del layout anterior (contenido desigual que estira un contenedor más que otro).
- **Paneles completos de una columna**: usar `height="content"` para crecer según la tabla o gráfico. Evitar tamaños rígidos cuando no hay un par que igualar.
- **Gráficos**: altura controlada (315/325px en pares), rankings horizontales, tendencias con una sola categoría y código de color constante. `plot` y estilos en `graficos.py`.
- **Responsive**: al apilarse las columnas en dispositivos estrechos se mantiene el alto fijo de cada tarjeta, salvo futura revisión móvil especializada.
- **Control visual de geometrías**: `scripts/probar_layout_browser.py` abre Chromium, captura las cinco vistas y valida la altura de paneles con y inicial común. GitHub Actions almacena los PNG como artefactos temporales, sin datos confidenciales.
- **Fechas y cortes**: captions de cada tarjeta y desplegable de calidad. No representar conteo de reportes como magnitud de crisis.

### Datos y calidad

| Uso | Datos | Condición imprescindible |
|---|---|---|
| Contextos | ACAPS Severity (Nov2026), Access | Son crisis evaluadas, no prioridad OPS; un país puede contener más de una |
| Señales de conflicto | HAPI ACLED 35/35 | Mensual, por categoría, sin suma transversal entre categorías |
| Personas en necesidad | HAPI HPC (6 países) | Solo total intersectorial `INN` sin desgloses; diferentes años |
| Refugio/asilo | HAPI ACNUR (31 países con registros) | País acogida/origen, año y grupo; totales sexo/edad no duplicados |
| Internamente desplazados | OIM DTM (12 países) | Por operación/ronda con fecha; no stock nacional actual |
| Vulnerabilidad | OPS Gini/escolaridad/recursos, OPHI MPI | Último año por país o selección de año común; no agregar fuentes |
| Respuesta | HAPI 3W (3 países), financiación (26) | Socios distintos por sector; FTS solo apelaciones |
| Evidencia documental | ReliefWeb (90 días) | Metadatos, enlaces, sin convertir documentos en severidad |
| Salud afectada directamente | OMS SSA | Sin integración regional validada; no mostrar supuestos valores |

La aplicación solo lee los CSV/JSON versionados y el GeoPackage de `el-nino-ops`; la extracción ocurre en Actions. Se requieren revisión metodológica de Laura y autorización institucional de ITS antes de presentar este instrumento como sistema oficial.

## Enlaces de implementación

- Código interfaz: [observatorio_v3.py](../../observatorio_v3.py)
- Estilos/mapa: [ui_ops.py](../../ui_ops.py)
- Gráficos: [graficos.py](../../graficos.py)
- CI funcional: [dashboard_ci.yml](../../.github/workflows/dashboard_ci.yml)
- CI navegador: [revisar_diseno.yml](../../.github/workflows/revisar_diseno.yml)
- Variables por API: [arquitectura_indicadores_dashboard.md](arquitectura_indicadores_dashboard.md)
