# Matriz de implementación del planteamiento de Laura

**Fecha:** 6 noviembre 2026  
**Base:** planteamiento remitido por Laura en la conversación y *Propuesta Técnica: Observatorio Regional de Amenazas y Vulnerabilidad Humanitaria en las Américas* del 5 de noviembre.

## Interpretación operativa del planteamiento

La primera dimensión del observatorio es **AMENAZAS (tipo de evento)**. Cada registro futuro debe identificar al menos fuente, tipo y subtipo de evento, unidad del indicador, periodo, geografía y precisión, y disponibilidad de personas afectadas. No confundir eventos con personas o impactos sobre la infraestructura.

**La interfaz incorpora la taxonomía completa de Laura**, pero solo presenta cifras donde existe una correspondencia verificable con datos actualmente almacenados en el repositorio. Cuando una categoría no tiene fuente integrada, no se asigna cero ni se colorea el mapa.

## Página 02 · Amenazas y eventos

| Grupo de Laura | Subtipo | Indicador en la versión 6 | Estado / precisión |
|---|---|---|---|
| Violencia | Acciones armadas | HAPI/ACLED `political_violence`: eventos país–mes, muertes reportadas | **Proxy**. No equivale exclusivamente a acciones armadas. Los eventos están agregados a escala nacional |
| Violencia | Ataques a objetivos y población civil | HAPI/ACLED `civilian_targeting` | **Parcial**: objetivos civiles; no cubre todos los blancos o infraestructura |
| Migración | Refugio / asilo | HAPI/ACNUR por país de acogida, origen, año y grupo REF o ASY | **Disponible con restricciones**: stocks, no flujos o nuevos desplazamientos |
| Migración | Desplazamiento interno | OIM DTM por operación, ronda, causa, ubicación reportada | **Parcial**: no sumar operaciones ni tratar ronda como población actual; excluidos desastres solo en la vista de fase 1 |
| Violencia generalizada | Tensiones entre países | Revisar reportes ReliefWeb y fuentes oficiales | **Sin indicador regional armonizado** |
| Violencia generalizada | Restricciones a la movilidad | Índice ACAPS Humanitarian Access por crisis | **Contextual**; no conteo de cierres o restricciones puntuales a movilidad |
| Contexto político frágil | Contexto político y económico frágil | Crisis ACAPS con componente político/económico | **Parcial**; no equivale a índice homogéneo de fragilidad |
| Minería ilegal | Extracción de minería ilegal | Por validar: fuentes especializadas | **Pendiente** |
| Crimen organizado | Actividades de crimen organizado | Por validar: fuentes especializadas | **Pendiente** |
| Drogas y cultivos | Mercados de drogas ilícitas y cultivos | Por validar: datos UNODC y otras fuentes | **Pendiente** |
| Delincuencia transnacional | Delincuencia organizada transnacional | Por validar: fuentes especializadas | **Pendiente** |

**Georreferenciación:** el mapa actual solo muestra país ISO3 y sus límites del GeoPackage. Los totales de HAPI/ACLED son país–mes, **no eventos puntuales**, y no deben representarse mediante coordenadas inventadas. Cualquier futuro detalle subnacional debe indicar precisión, fecha, condiciones de licencia y revisión de sensibilidad.

**Niveles crítico, alto, elevado y moderado:** previstos como etiquetas de trabajo, pero **NO ASIGNADOS**. Para habilitarlos Laura debe definir variables, periodos, umbrales, sentido, ponderación, tratamiento de faltantes y validación experta. INFORM Risk/Severity y ACAPS son índices ajenos; no se renombran como «nivel OPS».

## Página 04 · Impacto humanitario y salud

| Indicador planteado por Laura | Lo que se puede reportar hoy | Situación |
|---|---|---|
| Personas afectadas por evento | **Sin una base regional comparable de víctimas directas** | No sustituir por eventos, refugiados o PiN |
| Personas en necesidad | OCHA HAPI: PiN intersectorial nacional por año, donde sea inequívoco | Disponible parcialmente; cobertura y periodos variables |
| Población migrante/desplazada | ACNUR stocks REF/ASY; OIM DTM por operación/ronda | No sumar, ni convertir a personas afectadas por un evento individual |
| Establecimientos de salud impactados | OMS SSA / reportes OPS de país | **Pendiente de integración con datos validados** |
| Personal de salud afectado | OMS SSA / reportes oficiales | **Pendiente de integración** |
| Servicios esenciales: agua, electricidad, gas, telecomunicaciones | OCHA SitRep, informes nacionales/OPS con fecha y lugar | **Pendiente de sistematización** |

Se muestra una lista de indicadores ausentes con estado **«sin datos verificados»** en lugar de atribuirles valor cero. La tasa de homicidios OPS es **mortalidad de contexto**; no es número de muertos de un incidente ni número de ataques a la salud.

## Página 03 · Vulnerabilidad y respuesta

| Dimensión de Laura | Indicador mostrado o contemplado | Disponibilidad |
|---|---|---|
| Contexto económico | Desigualdad (Gini OPS), pobreza multidimensional (HAPI/OPHI) | Cobertura y año específicos |
| Educación | Escolaridad media (OPS) | Disponible según país y año |
| Contexto ambiental | Calidad de aire, inicialmente PM2.5 como posible candidato | **No integrado**; falta selección de fuente regional y comparabilidad temporal/geográfica |
| Contexto social | Gini y pobreza multidimensional | No son equivalentes; mostrar por separado |
| Capacidad sistema salud | Médicos, enfermería, camas hospitalarias (OPS) | Series de referencia nacionales, no capacidad operativa actual |
| Morbimortalidad | Mortalidad por homicidio (OPS); otras causas o morbilidad por integrar | No equiparar con incidencia de heridas o enfermedad |
| Cobertura vacunación | DTP3 y SRP1 (OPS) | Año y indicador específicos; no convertir a monitor de brotes |
| Demografía | Población por sexo y edad | **No integrada de forma regional homogénea**; seleccionar fuente, año y denominador |

Organizaciones 3W y financiación FTS complementan la dimensión de **respuesta**, pero no se suman para producir un índice de vulnerabilidad.

## Arquitectura de cinco páginas

1. **Panorama regional:** mapa y situación regional por país; indicador seleccionado, eventos y tendencias. Conserva el propósito comparativo de Mauricio.
2. **Amenazas y eventos:** **primera dimensión**, taxonomía completa de Laura, subtipos y mapas de datos disponibles; nivel OPS aún por definir.
3. **Vulnerabilidad y respuesta:** ocho ámbitos del planteamiento de Laura, con procedencia y vacíos.
4. **Impacto humanitario y salud:** personas en necesidad y movilidad, afectación de salud y servicios esenciales, sin inferencias.
5. **Perfiles por país:** integración de hechos, contexto y documentación para revisión cualitativa.

Cada pestaña está documentada en código, mantiene los colores OPS y permite revisión de consistencia y alineación mediante GitHub Actions.

## Próximas decisiones técnicas para Laura

- Acordar la **taxonomía oficial** de eventos, diferenciando hechos, condiciones y consecuencias.
- Identificar fuentes directas para crimen organizado, minería y cultivos ilícitos, ataques a salud, servicios interrumpidos y población afectada por evento.
- Revisar la posibilidad de tasas por población, desagregaciones subnacionales y actualización comparativa.
- Elegir indicadores económicos, escolares, ambientales, sociales y demográficos con definiciones y fuentes.
- Aprobar una **metodología auditable** para niveles crítico, alto, elevado y moderado, si realmente se desean implementar.
- Definir validación editorial, protección de datos, permisos de publicación y plataforma autorizada por ITS.

**Roles del documento:** Laura define indicadores y validación técnica; Iván integra fuentes y desarrolla/actualiza la plataforma. Las decisiones de publicación y priorización son institucionales.
