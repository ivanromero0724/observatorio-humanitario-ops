# Alineación del Observatorio con el encargo de Mauricio y la propuesta del 5 de noviembre de 2026

**Estado:** prototipo técnico OPS/PHE, sujeto a validación de Laura y autorización institucional.  
**Base documental:** correo de Mauricio Cerpa (EOC) y *Propuesta técnica — Observatorio Regional de Amenazas y Vulnerabilidad Humanitaria en las Américas* (5 nov. 2026).

## Encargo que cumple la interfaz

> Mapear por país la presencia, magnitud documentada y evolución de temas humanitarios relevantes para OPS, empezando por violencia/conflicto y migración/desplazamiento forzado; registrar contexto de acceso, vulnerabilidad y capacidad, y dejar abierta la ampliación futura a otras amenazas.

**No es** un monitor de brotes, otro tablero de El Niño, una clasificación oficial de prioridad OPS, ni una lista de todos los campos disponibles de cada API.

### Matriz de correspondencia

| Necesidad expresada por Mauricio | Información que ya se muestra | Precaución para directivos |
|---|---|---|
| Mapeo de países con temas humanitarios | Mapa regional de **eventos de violencia política en 12 meses**, **ataques contra civiles en 12 meses** o **máxima gravedad ACAPS de crisis evaluadas**; controles independientes | Los colores representan solo el indicador elegido. No existe un «riesgo OPS» combinado ni una prioridad automática |
| Nivel de eventos y seguimiento de cambios | Comparación país por país de volumen HAPI/ACLED y variación de los últimos 3 meses respecto a los 3 anteriores; series de 6/12/24 meses | Variación descriptiva, no prueba de crisis ni necesidad de apoyo. Requiere meses completos |
| Violencia y conflicto | Eventos agregados mensuales, ataques contra civiles y otras categorías HAPI/ACLED; crisis ACAPS con componente conflicto | Categorías ACLED pueden solaparse. No sumar eventos de distintas categorías |
| Migración, refugio y desplazamiento | ACNUR por país de acogida, origen, año y tipo de población; OIM DTM por operación/última ronda | Refugiados/solicitantes de asilo son **stocks**; DTM puede tener rondas históricas. No sumar categorías o distintas operaciones |
| Acceso humanitario y contexto | Índice Humanitarian Access de ACAPS por crisis, 3W OCHA y financiación FTS de apelaciones | Acceso ACAPS no equivale a continuidad de un servicio sanitario. Presencia de organizaciones no es capacidad instalada |
| Impactos que pueden interesar a OPS | PiN intersectorial donde hay un total inequívoco; contexto social y capacidad sanitaria OPS; registro de vacío en ataques a salud e interrupción de servicios | No inferir víctimas, afectación de centros de salud ni emergencias epidemiológicas con indicadores indirectos |
| Crimen organizado, cultivos, minería y fragilidad sociopolítica | Identificados como **pendientes de fuentes y definiciones expertas** | No inventar series, categorías ni niveles; revisar UNODC, GI-TOC y reportes por país |
| Ampliación posterior a desastres naturales | Arquitectura de 5 páginas y archivos de datos conservan capacidad de integrar nuevas dimensiones | La portada de **fase 1 excluye crisis exclusivamente por desastres**. Se mantienen las crisis mixtas que incluyen conflicto/desplazamiento/entorno político, aunque también tengan factores climáticos |

### Navegación que ve el equipo

1. **Mapa y seguimiento regional**: mapa principal y tabla de países con números originales, cambios, crisis evaluadas y disponibilidad de información de refugio/OIM; debajo serie y evaluaciones.
2. **Violencia, conflicto y acceso**: evolución y comparación por categoría, últimos 3 vs 3 meses, y restricciones de acceso por contexto.
3. **Migración y desplazamiento**: orígenes/destinos ACNUR, datos OIM DTM con fechas y operación, PiN con filtro intersectorial.
4. **Vulnerabilidad y respuesta**: desigualdad, educación, recursos sanitarios, vacunación, presencia de organizaciones, financiación; sin desviar la portada a vigilancia epidemiológica.
5. **Perfil humanitario por país**: evidencia desagregada para la discusión de apoyo y reportes originales ReliefWeb; no sustitución de SitRep y verificaciones de campo.

La ficha de procedencia, limitaciones y cobertura se encuentra en un desplegable común, no añade otra página al menú.

## Cinco dimensiones conceptuales de la propuesta

- **Amenaza/evento:** tipo, magnitud, tendencia, geografía y periodo de hechos reportados.
- **Exposición/población:** personas refugiadas, solicitantes de asilo y desplazadas reportadas, sin confundir stocks con flujos.
- **Vulnerabilidad:** datos económicos y sociales con año (Gini, escolaridad, pobreza) y riesgo estructural externo en fuentes.
- **Impacto humanitario/sanitario:** PiN donde hay estimación; indicadores directos de ataques a salud/servicios **pendientes**; nunca inferidos sin fuente.
- **Capacidad de respuesta:** recursos sanitarios OPS, presencia 3W y financiación de apelaciones (no necesariamente salud), con sus límites.

## Propuesta de indicadores que Laura debe revisar y aprobar

| Dimensión | Candidato | Unidad y corte | Acordar antes de utilizarlo para prioridad |
|---|---|---|---|
| Violencia/conflicto | Eventos political_violence y civilian_targeting | Registros/país/mes; últimos 12 meses; mismo periodo para todos | Categorías, calidad, denominadores y umbral de cambio |
| Tendencia | Δ absoluto de eventos: últimos 3 meses frente a 3 anteriores | País–categoría, solo 6 meses completos | Si conviene usar tasas, periodos alternos y variación relativa |
| Gravedad de crisis | ACAPS INFORM Severity y Humanitarian Access | Escalas oficiales por crisis, edición publicada | Tratamiento de países sin evaluación y crisis superpuestas |
| Movilidad/refugio | Refugiados, solicitantes de asilo, DTM IDP | País de acogida, origen, categoría, operación/año/ronda | Cobertura, stocks vs flujos y uso de IDMC para nuevos desplazamientos |
| Necesidad humanitaria | PiN intersectorial | Personas/año/país, solo cuando no existan totales duplicados | Conceptos de necesidad, diferencias entre países y vigencia |
| Vulnerabilidad y respuesta | Gini, escolaridad, médicos, enfermería, camas, 3W, financiación | País–indicador–año o apelación/sector | Selección final de indicadores y pesos, si se necesitan |
| Impactos directos en salud | Ataques y establecimientos afectados; interrupciones de servicios | Evento, territorio, fecha, fuente directa | Acceso autorizado a OMS SSA y reportes de autoridades |

**Ninguna columna anterior tiene un umbral OPS definido.** Las categorías de seguimiento *crítico, alto, elevado y moderado* permanecen como propuestas metodológicas sin asignación automática, pendientes de Laura.

## Criterios y cautelas de publicación

- Mapa y tabla incluyen países sin datos como **«sin información»**, no como cero ni como ausencia de amenaza. Un cero solo es legítimo si el proveedor publicó un cero para un mes efectivamente incluido.
- Las comparaciones de eventos solo se presentan cuando un país tiene los 12 meses del periodo común; el Δ 3m/3m solo si hay 6 meses.
- Para mapas de eventos, los matices de azul muestran volumen en una escala descriptiva logarítmica. No son límites de riesgo ni de prioridad.
- ACAPS se filtra por `drivers` para el alcance inicial: conflicto, violencia, desplazamiento o crisis sociopolíticas. Las crisis exclusivamente por terremoto quedan disponibles en datos y no aparecen en el monitoreo inicial. Se conservan las **crisis mixtas** con factores de conflicto y climáticos porque siguen siendo humanitarias dentro del alcance inicial.
- Refugio/ACNUR distingue país de acogida, origen, año y categoría. En la vista OIM de la **fase 1 se excluyen 37 registros clasificados como `Natural disaster`** y se conservan en el CSV original; se muestran los 27 registros con causa `Conflict`, `Insecurity` o **causa no reportada**. El último grupo no se etiqueta como desplazamiento forzado sin validación. Los registros PiN no se suman entre sectores.
- Los datos de API se extraen mediante GitHub Actions y se almacenan con su fecha; Streamlit no utiliza ni muestra tokens.
- La cobertura actual del catálogo es de 35 países soberanos. Los **territorios adicionales** previstos en la propuesta requieren homologación y fuentes verificadas.

## Verificación y mejoras posteriores

Las pruebas automáticas inspeccionan las cinco páginas, filtros en países con distintos niveles de datos y la simetría de tarjetas en Chromium. Capturas de cada página se adjuntan a GitHub Actions.

Las siguientes ampliaciones *no bloquean el prototipo* pero son importantes para cumplir integralmente el objetivo: nueva base de desplazamientos IDMC cuando se apruebe acceso; UNODC/GI-TOC para crimen organizado/economías ilícitas; OMS SSA y reportes de OPS/autoridades para impacto sanitario; mejoras de indicadores de exposición y tasas, y evaluación experta de prioridades.

**Responsabilidades:** Laura valida taxonomía, indicadores y criterios; Iván integra fuentes, automatiza QA y desarrolla; equipo OPS/PHE decide gobernanza, publicación y uso operacional.
