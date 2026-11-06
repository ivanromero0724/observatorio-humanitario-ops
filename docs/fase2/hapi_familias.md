# Ampliación HAPI v2 — fuentes, variables y visualización

**Fecha del primer corte:** 6 noviembre 2026. **Universo consultado:** 35 países soberanos de las Américas. **Credencial:** `HDX_APP_IDENTIFIER` guardada como GitHub Secret, nunca expuesta al usuario de Streamlit. **Datos utilizados:** snapshots completos y validados, no llamadas desde la interfaz.

HAPI proporciona distintas clases de datos; **"35 países consultados" no equivale a "35 países con observaciones"**. Las fechas se conservan por registro. El producto no establece prioridades operacionales de OPS.

## Familias integradas

| Familia API HAPI v2 | Variables disponibles en el CSV | Países con registros | Filas verificadas | Frecuencia de nuestra extracción | En el tablero |
|---|---|---:|---:|---|---|
| **Conflict Events** (ACLED público mensual agregado) | `iso3`, `periodo`, `tipo_evento`, `eventos`, `muertes_reportadas` | 35 | 8.574 | Lunes | Conflicto y perfil |
| **Humanitarian Needs** (OCHA HPC) | `sector_code`, `sector_name`, `population_status` (INN/TGT/AFF/REA), `category`, `population`, fechas | 6 | 1.043 | Día 8 de cada mes | Necesidades y respuesta |
| **Funding** (OCHA FTS) | `appeal_code`, `appeal_name`, `appeal_type`, `requirements_usd`, `funding_usd`, `funding_pct`, fechas | 26 | 229 | Día 8 de cada mes | Necesidades y respuesta |
| **National Risk** (INFORM) | `overall_risk`, `hazard_exposure_risk`, `vulnerability_risk`, `coping_capacity_risk`, ranking, año | 35 | 35 | Día 8 de cada mes | Necesidades y respuesta |
| **Poverty Rate** (OPHI MPI) | `mpi`, `headcount_ratio`, `intensity_of_deprivation`, `vulnerable_to_poverty`, `in_severe_poverty`, año | 21 | 50 | Día 8 de cada mes | Necesidades y respuesta |
| **Food Security** (IPC) | `ipc_phase`, `ipc_type`, `population_in_phase`, `population_fraction_in_phase`, periodo | 5 | 322 | Día 8 de cada mes | Necesidades y respuesta |
| **Operational Presence** (OCHA 3W) | `sector`, `sector_code`, `fecha_hasta`, `organizaciones_distintas`, `unidades_territoriales` | 3 | 25 filas resumen | Día 8 de cada mes | Necesidades y respuesta, por sector |
| **Refugees & Persons of Concern** (UNHCR, país de acogida) | `asilo_iso3`, `origen_iso3`, `grupo_poblacion`, `anio`, `personas`, periodo, fuente | 31 | 3.765 | Día 9 de cada mes | Desplazamiento y movilidad |

Estos son **8 conjuntos**, todos consultados país por país y paginados completamente. En las familias de necesidades, pobreza e IPC se consultan **únicamente los registros admin0** para evitar totalizar filas nacionales y subnacionales a la vez. HAPI puede tener más información subnacional que no forma parte de estos indicadores nacionales.

### Precauciones que deben conservarse

- **INFORM Risk:** la API HAPI entrega en esta extracción un **corte 2025**, distinto del archivo original **INFORM Risk Mid 2026** usado en el mapa regional. Las tres dimensiones se muestran en su pestaña específica y no se mezclan con la edición 2026.
- **Necesidades:** PiN es el estado `INN`. Solo un registro intersectorial sin desglose o identificado como total puede utilizarse en la comparación de población total en necesidad. No sumar sector salud, nutrición, protección, etc., porque una persona puede figurar en varios sectores. Comparar años diferentes solo con advertencia.
- **Financiación:** HAPI FTS contiene financiación asignada a apelaciones y contribuciones no clasificadas. Los indicadores de cobertura (%) solo se visualizan cuando la apelación está identificada y tiene porcentaje informado. No representan toda la financiación humanitaria recibida en un país. No confundir años futuros en la fuente con financiación observada presente.
- **Pobreza:** `mpi` es una fracción; `headcount_ratio`, `intensity_of_deprivation`, `in_severe_poverty` y `vulnerable_to_poverty` son porcentajes. Los años difieren y no se imputan.
- **IPC:** no sumar análisis actuales con pronósticos; no sumar niveles administrativos ni periodos; las fases 1–5 son distintas. La ausencia de evaluación no significa seguridad alimentaria adecuada.
- **Presencia 3W:** número de socios distintos **dentro de un mismo sector y periodo**. La misma organización puede operar en muchos sectores y áreas. No sumar socios sectoriales para estimar el total de organizaciones, ni interpretar como número de personas atendidas. La fuente puede usar variantes del nombre de una organización.
- **Refugio y asilo:** se solicitan solo registros con `gender=all` y `age_range=all` para impedir doble conteo por sexo/edad; se conserva país de origen, país de acogida y `population_group` (REF, ASY, OIP, etc.). Son poblaciones, no flujos anuales. No sumar categorías.
- **Conflicto:** las categorías ACLED (`political_violence`, `civilian_targeting`, `demonstration`) pueden solaparse; se visualizan por separado. Los 8.574 registros son agregados país-mes-categoría, no hechos individuales.
- **Cobertura:** cero registros del API no equivale a cero personas/organizaciones/eventos.

## Otras familias HAPI verificadas, sin datos cuantitativos aún en el tablero

| Familia | Estado | Qué permitiría | Próxima decisión |
|---|---|---|---|
| **Internally Displaced Persons (IDPs)** | Endpoint probado; fuente IOM DTM, ya conectada directamente | Operación, ronda, lugar y población desplazada | Evitar duplicar la misma fuente OIM publicada en el apartado movilidad |
| **Returnees** | Endpoint probado; requiere seleccionar la dirección origen/retorno | Retornados por origen/recepción y año | Validar interpretación de campos, sexo/edad y diferencias respecto de OIM |
| **Baseline Population** | Endpoint probado | Denominadores por edad/sexo, nacional o subnacional | Controlar años y compatibilidad de fuentes demográficas antes de tasas |
| **Food Prices & Market Monitor** | Endpoint probado, con datos para algunos países | Precios de bienes, unidad, moneda, mercado, fecha | No comparar precios nominales de países/monedas sin estandarización |
| **Rainfall / CHIRPS** | La ruta probada `climate/hazards-rainfall` respondió 404 | Lluvia, anomalías y periodo | Verificar la ruta exacta y limitar la descarga por fechas/admin1; no publicar un indicador inexistente |

## Decisiones de interfaz

- No copiar los gráficos del tablero de El Niño: se reutilizan únicamente **paleta OPS, logos y geografía**.
- Figuras propias de investigación: *dot plots* con años en el hover, rankings horizontales (máximo 12–16 países), curvas temporales limpias, y matriz visual de **cobertura 35 países × 13 fuentes**.
- La interfaz debe explicar fecha, unidad, población de referencia y comparabilidad. No usar gráficos de barras verticales con 35 nombres inclinados.
- No publicar fuentes con extracción truncada. Si una actualización falla, conservar el corte anterior e informar la fecha.
- El archivo `docs/fase2/hapi_catalogo_endpoints.json` guarda los nombres de campos del sondeo, no los datos de personas.

## Procesos y evidencia

- [Auditoría de 12 rutas HAPI](hapi_catalogo_endpoints.json)
- [QA de cinco temas HAPI](hapi_contexto_actualizacion.json)
- [QA de presencia 3W](hapi_presencia_actualizacion.json)
- [QA de HAPI ACNUR](hapi_acnur_actualizacion.json)
- [QA de conflicto desde 2020](../fase1/hapi_extraccion_completa.json)

Código: `scripts/fase2/extraer_hapi_contexto.py`, `extraer_hapi_presencia.py`, `extraer_hapi_acnur.py`; workflows equivalentes en `.github/workflows/`. Gráficos en `graficos.py`, página temática en `paginas_hapi.py`.

Documentación oficial: https://hdx-hapi.readthedocs.io/en/latest/ y sandbox https://hapi.humdata.org/docs.
