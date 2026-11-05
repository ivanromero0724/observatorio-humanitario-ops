# Fase 1 — Informe de resultados de extracción y factibilidad
**Corte de ejecución:** 5 de noviembre de 2026 · **Estado técnico:** aprobado por pruebas automatizadas · **Aprobación metodológica OPS:** pendiente.

## Ampliación posterior: piloto de los 35 países soberanos (05/11/2026)

Después de la exploración inicial de cinco países, el piloto de seguimiento de HAPI y OIM-DTM se amplió a **los 35 países soberanos de América**, todos representados en el [catálogo maestro](../../data/catalogos/paises_americas.csv). La ejecución de GitHub Actions completó la verificación de claves y consultas.

| Fuente | Resultado real | Advertencias |
|---|---|---|
| HAPI Conflicto, desde 2020 | 35 países, 35 extracciones completas; 8.574 agregados país–mes–categoría | Colombia: 238 duplicados idénticos y 8 marcadores cero por geo/mes/fuente reconciliados; NO son eventos individuales ni categorías excluyentes |
| OIM DTM Baseline | 12 países con registros Admin0: El Salvador, Guatemala, Honduras, Antigua y Barbuda, Bahamas, Dominica, Granada, Haití, San Vicente y las Granadinas, Bolivia, Ecuador y Perú | Ausencia en catálogo no equivale a cero desplazamiento |
| OIM DTM HNA | Catálogo mundial de cuatro registros sin países del grupo de 35 | No significa ausencia de necesidades humanitarias |
 
La tabla país×fuente incluye **105 filas y no contiene valores cero imputados para países ausentes**. Los registros de DTM pueden corresponder a diferentes rondas, años u operaciones y no se deben sumar automáticamente. La extracción HAPI completa quedó resuelta; no hay series truncadas. El método de conciliación de duplicados de Colombia está registrado en `hapi_extraccion_completa.json`.

**Documentación:** [alcance](alcance_piloto_americas.md), [matriz de cobertura](cobertura_hapi_oim_americas.csv), [resumen verificable](resumen_piloto_regional.json).

---

## Resultado cuantitativo verificado

| Componente | Registros o consultas | Interpretación |
|---|---:|---|
| INFORM Risk, Mid 2026 | 35 países con puntuación | Cobertura de los 35 países soberanos incluidos; **no** es índice exclusivo de violencia |
| INFORM Severity, sept. 2026 | 25 crisis en 16 países | Una misma jurisdicción puede tener varias crisis de diferente naturaleza |
| OPS, octubre 2026 | 3.038 observaciones únicas país–indicador–año | Ocho indicadores exactos, 266 de 280 combinaciones país–indicador con al menos un año disponible |
| WarMonit, 05/11/2026 | 2 países americanos (VEN y USA) | 20 países a escala mundial; sin fila ≠ ausencia de conflicto |
| ACNUR API, cinco países piloto | 10 respuestas; 9 con filas | Muestras REF_UNHCR/ASY 2020+, no series completas normalizadas |
| OCHA HDX HAPI | Sin extracción | Hace falta identificador institucional de aplicación |

**Control QA:** `docs/fase1/qa_normalizados.json` registra comprobación de rangos, ausencia de claves duplicadas y huellas SHA-256. El último control concluyó `pasa`, con cero errores de integridad en estos cuatro archivos.

## Valores de ejemplo de los países piloto

| País | INFORM Risk (0–10) | Número de crisis Severity | Mayor puntuación de una crisis (0–10) | ACNUR piloto |
|---|---:|---:|---:|---|
| Colombia | 5,3 | 4 | 8,5 | Refugiados y solicitantes de asilo: filas |
| Haití | 7,6 | 1 | 8,9 | Refugiados: filas; solicitantes: sin filas bajo consulta |
| Venezuela | 6,4 | 3 | 8,5 | Ambas consultas: filas |
| Ecuador | 5,8 | 3 | 7,4 | Ambas consultas: filas |
| Panamá | 4,0 | 1 | 3,8 | Ambas consultas: filas |

Los máximos de crisis son **sólo un resumen descriptivo de puntuaciones de crisis distintas** y **no constituyen una clasificación agregada de gravedad por país**. Los valores no equivalen a prioridades aprobadas por OPS.

## Indicadores OPS armonizados

La base `data/observaciones/ops_8_indicadores_pais_anio.csv` incluye: GINI Index; Mean years of schooling; Hospital beds ratio; Density of medical doctors; Density of nursing personnel; Immunization coverage DTP3; Immunization coverage MMR1; Homicide mortality rate age-adjusted. Se excluyeron variantes por sexo, recuentos absolutos y tasas con distintos denominadores. Los periodos y denominadores reales se conservan en cada registro.

## Capacidades para el dashboard

**Preparados para visualización exploratoria:** panorama regional INFORM Risk, distribución y ficha por crisis Severity, series OPS por país con fecha y ficha de indicador.

**Requieren revisión antes de publicación:** qué amenazas entran, si se usa INFORM Risk total o sólo componentes humanos/vulnerabilidad, clasificación “crítico, alto, elevado, moderado”, comparabilidad de años, georreferenciación subnacional, interpretación de fuentes.

**No disponibles todavía con descarga homogénea:** eventos OCHA HAPI/ACLED, PiN, desplazamiento OIM, afectaciones de instalaciones y personal de salud OMS, cortes de acceso humanitario, servicios esenciales, minería ilícita y tráfico. No se asignaron ceros ni se imputaron faltantes.

## Requisitos y decisiones institucionales

1. Laura y Mauricio: revisar y aprobar taxonomía, indicadores mínimos, ventanas de seguimiento y protocolo de prioridad OPS.
2. OPS: proporcionar identificador HAPI válido y resolver licencia ACLED detallada / términos ACNUR / clave OIM DTM.
3. OPS/ITS: confirmar alojamiento institucional y gobernanza de datos.
4. Desarrollo: incorporar territorialidad y modelos regionales solo tras comprobar cobertura y permisos.
5. Mantenimiento: versiones de fuentes, fechas de consulta, fuente original, QA y fallos de descarga con alertas.

## Código y reproducibilidad

`scripts/fase1/extraer_cobertura.py` y `scripts/fase1/validar_datos.py`; ejecución manual desde GitHub Actions en `.github/workflows/fase1_cobertura.yml`, con actualización de tablas y JSON de verificación. No hay actualización diaria programada. El trabajo de selección de indicadores o curaduría contextual sigue siendo humano.

*Este cierre describe factibilidad y pruebas técnicas; no equivale a una aprobación institucional ni al cierre de los asuntos de licenciamiento/credenciales.*
