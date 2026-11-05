# Fase 1 — Diagnóstico inicial de fuentes
**Fecha de revisión documental: 05/11/2026.** Este documento no presenta estadísticas extraídas ni una evaluación de cobertura empírica por país.

## Hallazgos
| Fuente | Acceso | Uso propuesto | Limitaciones |
|---|---|---|---|
| OCHA/HDX HAPI — ACLED agregado | API, `app_identifier` | Eventos y muertes reportadas por violencia política y violencia dirigida contra civiles; series mensuales | Categorías no excluyentes; revisar licencia sector público ACLED |
| OCHA/HDX HAPI — Humanitarian Needs | API, `app_identifier` | Personas en necesidad intersectorial (PiN) | No sumar sectores o estados poblacionales |
| INFORM Risk Mid-2026 | XLSX público | Riesgo estructural y sus tres dimensiones | No es gravedad actual ni prioridad OPS |
| INFORM Severity Sep-2026 | XLSX público | Gravedad por crisis evaluada | No todos los países tienen crisis calificadas; escala 0–10 tras revisión metodológica de feb/2026 |
| OPS — Indicadores Básicos Oct-2026 | ZIP/CSV público | Demografía, desigualdad, educación, ambiente y salud | Periodo de referencia variable según indicador |
| ACNUR — Refugee Data Portal | API sin clave; límites y términos | Personas refugiadas y solicitantes de asilo | Stock frente a flujo y origen frente a asilo |
| OIM — DTM API v3 | Suscripción y clave | Desplazamiento interno agregado | Cobertura por operación y metodología |
| OMS — SSA | Exportación Excel | Ataques a salud, muertos, lesionados | Cobertura seleccionada y confidencialidad |
| WarMonit — CII | JSON/CSV, CC BY 4.0 cifras propias | Índice contextual complementario | Archivo de 20 países: en Américas VEN y USA el 05/11/2026 |
| OCHA — ReliefWeb | API con appname aprobado | Documentos/SitRep y curaduría | No es indicador cuantitativo homogéneo |
| GI-TOC — Organized Crime Index 2025 | XLSX | Criminalidad organizada, mercados ilícitos y redes | Índices estructurales, no incidentes |
| UNODC — WDR 2026 | Informes/tablas | Cultivos ilícitos por países reportantes | Cobertura no uniforme |
| ACLED directa | API bajo licencia | Eventos diarios y actores, fase posterior | Se requiere autorización sector público para multilaterales |

## Metodología propuesta
Cinco componentes: (1) amenazas/eventos, (2) población expuesta/movilidad, (3) vulnerabilidad, (4) impacto humanitario y en salud y (5) capacidad de respuesta. No calcular un índice OPS propio ni clasificar países en crítico/alto/elevado/moderado antes de definir umbrales y proceso de aprobación.

### Piloto
COL, HTI, VEN, ECU y PAN. **Los cruces país-fuente NO se han comprobado con descarga**, salvo presencia/ausencia en JSON público WarMonit. No inferir que un país sin registros carece de amenaza.

### Definiciones que requieren especial cuidado
- `HAPI political_violence` y `HAPI civilian_targeting` se solapan, por lo que no deben sumarse.
- PiN debe interpretarse por periodo, sector y cobertura; no sumar estimaciones sectoriales.
- En OMS-SSA, ataques a instalaciones **no** equivale a número de establecimientos únicos.
- Indicadores OPS están sujetos a año de referencia, denominador y ficha técnica.
- La movilidad general no es necesariamente desplazamiento forzado.

## Pruebas y decisiones pendientes
1. Obtener `HDX_APP_IDENTIFIER` y ejecutar consulta paginada para los cinco países.
2. Descargar y documentar los archivos XLSX oficiales de INFORM Risk y Severity.
3. Descargar OPS CSV, identificar series, fechas y cobertura país-año.
4. Revisar API de ACNUR, clave OIM y alcance de permisos ACLED con OPS.
5. Curar restricciones, tensiones fronterizas, servicios esenciales y economías ilegales por informe y país.
6. Aprobar con Laura el conjunto mínimo de indicadores y la taxonomía.
7. Definir con ITS el alojamiento institucional.

## Fuentes (consulta: 05/11/2026)
- HDX HAPI: https://hdx-hapi.readthedocs.io/en/latest/
- HAPI conflicto: https://hdx-hapi.readthedocs.io/en/latest/data_usage_guides/coordination_and_context/
- HAPI necesidades: https://hdx-hapi.readthedocs.io/en/latest/data_usage_guides/affected_people/
- INFORM Risk: https://drmkc.jrc.ec.europa.eu/inform-index/INFORM-Risk/Results-and-data
- INFORM Severity: https://drmkc.jrc.ec.europa.eu/inform-index/INFORM-Severity/Results-and-data
- OPS: https://opendata.paho.org/es/indicadores-basicos/descarga-datos
- ACNUR: https://refugeedata.unhcr.org/en/documentation/technical-reference/api/
- OIM: https://dtm.iom.int/es/node/38776
- OMS SSA: https://extranet.who.int/ssa/index.aspx
- WarMonit: https://warmonit.com/press
- ReliefWeb: https://apidoc.reliefweb.int/
- GI-TOC: https://ocindex.net/downloads
- UNODC: https://data.unodc.org/wdr2026
- ACLED licencia: https://acleddata.com/eula
