# Diseño técnico, variables y fuentes — Observatorio Humanitario OPS/OMS

**Versión:** 6 de noviembre de 2026. **Estado:** prototipo Streamlit con **nueve páginas**; del tablero `el-nino-ops` solo se conservaron logos, paleta y GeoPackage, mientras que los gráficos analíticos tienen un lenguaje visual propio. **Territorio:** 35 Estados soberanos de América. El GeoPackage Natural Earth 1:50m puede incluir otros territorios como contexto cartográfico gris; no se inventan datos para ellos.

## Principios de lectura

- Separar **amenaza/evento**, **población afectada**, **vulnerabilidad**, **impacto humanitario/sanitario** y **capacidad de respuesta**.
- Los valores de INFORM y ACAPS representan **índices externos**, no una prioridad operacional asignada por OPS.
- Una extracción «completa» quiere decir que todas las páginas de la respuesta API para **el corte y los filtros definidos** fueron recibidas y validadas; no implica un censo exhaustivo de eventos en la realidad.
- **No sumar:** categorías HAPI/ACLED solapadas, distintas crisis ACAPS, poblaciones por sector (PiN), stock y flujos de desplazados, múltiples rondas DTM, reportes ReliefWeb asociados a más de un país.
- Faltante, no documentado y cero **no son sinónimos**.
- Revisión de ITS, protección de datos y condiciones de republicación antes de uso institucional.

## Tablas y variables implementadas

| Fuente | Tabla / corte | Variables aprovechadas y propósito | Actualización real | Visualización |
|---|---|---|---|---|
| **OCHA HDX HAPI / ACLED agregado** | `data/observaciones/hapi_conflicto_pais_mes.csv`; desde 2020; 8.574 filas país–mes–tipo para 35 países, extracción íntegra | `iso3`, `periodo`, `tipo_evento` (political_violence, civilian_targeting, demonstration), `eventos`, `muertes_reportadas` (ausente si proveedor no reporta), `nivel_admin`, `unidades_fuente`. No sumar categorías entre sí. | **Semanal**: `hapi_completo.yml`, lunes 11:25 UTC; también manual/cambios de código | Conflicto, panorama y perfil |
| **ACAPS INFORM Severity** | `data/observaciones/acaps_severity_americas.csv`; Nov2026, 25 crisis/16 países | `crisis_id`, `crisis`, `drivers`, `puntuacion`, `categoria`, `confiabilidad`, `impacto_crisis`, `impacto_geografico`, `impacto_humano`, `condiciones_afectados`, `personas_necesidad`, `concentracion_condiciones`, `complejidad`, `sociedad_seguridad`, `entorno_operativo`. Se evalúa cada crisis por separado. | **Mensual**: `acaps_americas.yml`, día 5, 12:25 UTC | Panorama, perfiles |
| **ACAPS Humanitarian Access** | `data/observaciones/acaps_acceso_americas.csv`; Nov2026, 25 contextos/16 países | `crisis_id`, `crisis`, `drivers`, `acceso` (ACCESS), `pilar_1` / `pilar_2` / `pilar_3` (P1–P3), `indicador_1`–`indicador_9` (I1–I9), `brecha_info` (Infogap). Las puntuaciones son por crisis. | **Mensual** junto con ACAPS Severity | Seguridad y acceso |
| **ReliefWeb** | `data/observaciones/reliefweb_reportes_americas.csv`; ventana de 90 días: 965 informes únicos, 1.746 relaciones país–reporte, 35 países | `reporte_id`, `titulo`, `url`, `fecha_publicacion_rw`, `fecha_publicacion_origen`, `pais_principal_iso3`, `paises_mencionados`, `fuentes`, `temas`, `formatos`, `idiomas`, `tipo_desastre`. **Metadatos y enlaces**, nunca contenido íntegro ni adjuntos. | **Semanal**: `reliefweb_reportes.yml`, lunes 12:35 UTC | Informes y situaciones, panorama |
| **INFORM Risk** | `data/observaciones/inform_risk_mid_2026.csv`, 35 países | `iso3`, `puntuacion`, `categoria` y dimensiones existentes en archivo. Riesgo estructural multiamenaza (incluye amenazas naturales), no solo conflicto. | Revisar **mensualmente** en `fase1_cobertura.yml`, día 6; solo cambia cuando cambia edición original | Mapa regional, perfil |
| **OPS Indicadores Básicos** | `data/observaciones/ops_8_indicadores_pais_anio.csv`, 3.038 país–indicador–año | Año, valor, unidad, definición, país. Indicadores: Gini, escolaridad, mortalidad por homicidios, camas, médicos, enfermería, DTP3, SRP1. Conservar años individuales. | Comprobar **mensualmente**, pero la frecuencia de cada indicador depende de OPS | Salud y vulnerabilidad, perfil |
| **INFORM Severity archivo** | `data/observaciones/inform_severity_2026_09_crisis.csv`, septiembre 2026 | Fallback histórico reproducible; al existir ACAPS Nov2026 no es la fuente principal del dashboard | Revisión por edición | Respaldo de transparencia |
| **OIM DTM Baseline** | `data/observaciones/oim_dtm_ultima_ronda.csv`, 64 registros de últimas rondas en 12 países + matriz de cobertura regional | `operacion`, `fecha_reporte`, `ronda`, `tipo_evaluacion`, `causa_desplazamiento`, `origen_admin1`, `personas_idp_reportadas`, `hombres`, `mujeres`. **Se visualizan por operación y origen, sin sumar poblaciones ni rondas**. | **Mensual**: `oim_ultimas_rondas.yml` (día 6, 12:45 UTC) y `piloto_americas.yml` (día 6, 13:10 UTC) | Desplazamiento: cifras de última ronda y cobertura |
| **OIM DTM HNA** | Mismo inventario, cero países americanos en su catálogo consultado | Acceso operativo pero sin datos comparables para los 35 en el catálogo disponible. No se interpreta ausencia como cero personas en necesidad. | Mensual | Estado metodológico |
| **WarMonit** | `data/observaciones/warmonit_cii_ultimo.csv`, dos países americanos | Indicador propio de inestabilidad contextual. No está en los gráficos por baja cobertura regional. | Revisar por archivo fuente | Respaldo y análisis complementario |
| **HAPI Humanitarian Needs** | `data/observaciones/hapi_necesidades_nacional.csv`, 1.043 filas, 6 países | PiN por estado, sector, categoría, año y país; solo admin0. No sumar sectores | Día 8 cada mes: `hapi_contexto.yml` | Necesidades y respuesta, perfiles |
| **HAPI Funding** | `data/observaciones/hapi_financiacion_apelaciones.csv`, 229 filas, 26 países | Aportes y porcentajes de apelaciones, corte, código y tipo; incluir solo apelaciones identificadas para comparaciones | Día 8 cada mes | Necesidades y respuesta, perfiles |
| **HAPI National Risk** | `data/observaciones/hapi_inform_componentes.csv`, 35 filas | Riesgo, exposición, vulnerabilidad y capacidad. **Corte fuente 2025, distinto a INFORM Mid 2026** | Día 8 cada mes | Necesidades y respuesta |
| **HAPI Poverty Rate** | `data/observaciones/hapi_pobreza_multidimensional.csv`, 50 filas, 21 países | MPI, incidencia, intensidad, pobreza severa/vulnerable y año; solo admin0 | Día 8 cada mes | Necesidades y respuesta, perfiles |
| **HAPI Food Security (IPC)** | `data/observaciones/hapi_seguridad_alimentaria_ipc.csv`, 322 filas, 5 países | Fase, tipo actual/proyección, personas y periodo; solo admin0 | Día 8 cada mes | Necesidades y respuesta, perfiles |
| **HAPI Operational Presence (3W)** | `data/observaciones/hapi_presencia_sector.csv`, 25 resúmenes en 3 países | Número de socios distintos por sector, geografía y fecha; no sumar sectores | Día 8 cada mes: `hapi_presencia.yml` | Necesidades y respuesta, perfiles |
| **AWSD** | `docs/fase2/accesos_awsd_reliefweb.json` | **Clave detectada, respuesta JSON pendiente de validar.** Futuras variables: incidentes, fechas, países, tipos de incidente y víctimas (sujeto al codebook y licencia). No hay estadísticas AWSD en el dashboard. | Pendiente de validar autenticación; después corte publicado | Seguridad, todavía sin valores |
| **ACNUR vía HAPI** | `data/observaciones/hapi_acnur_acogida.csv`, 3.765 filas; 31/35 países de acogida | `asilo_iso3`, `origen_iso3`, `grupo_poblacion`, `anio`, `personas` y periodo; solo filas `gender=all, age_range=all` para evitar doble conteo de sexo/edad. No sumar categorías poblacionales. | **Mensual**: `hapi_acnur.yml`, día 9 | Desplazamiento y perfiles |

**Nota ACAPS:** `Humanitarian Access Events` dejó de recopilarse el 31-jul-2026; disponible solo como histórico. No utilizarlo como señal viva de seguridad.

## Variables y vistas previstas adicionales

### Amenaza y violencia
- HAPI: categorías mensuales separadas, evolución por país/subregión, presencia de datos y cambio temporal.
- AWSD (cuando sea validada): incidentes contra personal humanitario, muertos, heridos y secuestrados, con agregación de nivel país–mes/año y atribución. No republicar identificadores sensibles.
- UNODC y GI-TOC: cultivos ilícitos, mercados criminales y resiliencia, principalmente por país y edición de informe.

### Movilidad humana e impacto humanitario
- **IDMC** (solicitud de API enviada): nuevos desplazamientos (flujo) y personas desplazadas internas (stock), separadas por violencia/conflicto y desastres.
- **ACNUR**: refugiados, solicitantes de asilo, origen y acogida, edad/sexo cuando exista cobertura, utilizando snapshots anuales autorizados.
- **HAPI Humanitarian Needs**: `population`, `population_status` (INN/TGT/AFF/REA), `sector_name`, `category`, `reference_period_*`, `location_code`. Para PiN intersectoral, seleccionar sector intersectoral; no sumar sectores.
- **HAPI Operational Presence**: `org_name`, `org_type_description`, `sector_name`, `admin1/2` y periodo; organizaciones distintas por área, no personas atendidas.
- **HAPI funding**: `appeal_code`, `requirements_usd`, `funding_usd`, `funding_pct`, año y país. No representar como financiación total de todos los actores, pues HAPI cubre apelaciones.

### Salud y capacidad de respuesta
- OMS SSA: ataques contra personal e infraestructura sanitaria, muertes y lesiones, con fecha y nivel de publicación disponible.
- OPS Indicadores Básicos: ampliar cobertura social y sanitaria en la medida en que sus series y años sean comparables.
- Banco Mundial: población para denominadores, pobreza y desigualdad; conservar año y definición.

## Arquitectura, confiabilidad y visualización

1. **Extracción protegida:** GitHub Actions accede a tokens como secretos. AWSD y ReliefWeb quedan nombrados `AWSD_API_KEY` y `RELIEFWEB_APPNAME`. Streamlit no accede directamente a las credenciales.
2. **Control QA:** autenticación, todas las páginas descargadas, duplicados, claves ISO3, fecha, definiciones, variables, valores ausentes y validez geográfica. Nunca sustituir silenciosamente el último corte bueno por uno incompleto.
3. **Snapshots versionados:** CSV/JSON en el repositorio público, únicamente cuando el tipo de dato y licencia lo permitan; fuentes restringidas requieren acceso separado.
4. **Visualización:** nueve páginas: panorama, conflicto, seguridad/acceso, necesidades/respuesta, desplazamiento, informes, salud/vulnerabilidad, perfiles, fuentes. De `el-nino-ops` proceden paleta, logos y GeoPackage; los gráficos son originales del Observatorio (`graficos.py`): líneas limpias, rankings horizontales, dot plots y matriz de cobertura.
5. **Cartografía:** `data/geografia/paises_americas.gpkg` copiado de `el-nino-ops`, Natural Earth 1:50m, EPSG:4326. Se representa el continente, con países sin dato en gris y visualización separada por fuente. El objetivo analítico permanece en 35 países soberanos.
6. **Fecha:** distinguir `fecha_publicacion_origen`, `fecha_publicacion_rw`, fecha de referencia y `fecha_extraccion_utc`. Un documento publicado puede describir un periodo distinto.
7. **Gobernanza:** estado de prototipo. Antes de publicarlo institucionalmente, revisar seguridad, control de la plataforma y autorización de ITS en OPS.

## Enlaces útiles

- [Aplicación Streamlit](../../app.py)
- [Diseño reutilizado de El Niño](https://github.com/ivanromero0724/el-nino-ops)
- [Control HAPI 35/35](../fase1/hapi_extraccion_completa.json)
- [Ocho familias HAPI, variables y decisiones](hapi_familias.md)
- [Control HAPI cinco conjuntos](hapi_contexto_actualizacion.json)
- [Control HAPI presencia 3W](hapi_presencia_actualizacion.json)
- [Control HAPI ACNUR](hapi_acnur_actualizacion.json)
- [Control ACAPS](acaps_actualizacion.json)
- [Control OIM (últimas rondas)](oim_actualizacion.json)
- [Control ReliefWeb](reliefweb_actualizacion.json)
- [Diagnóstico AWSD](accesos_awsd_reliefweb.json)
- [Documentación HAPI Affected People](https://hdx-hapi.readthedocs.io/en/latest/data_usage_guides/affected_people/)
- [Documentación HAPI Coordination](https://hdx-hapi.readthedocs.io/en/latest/data_usage_guides/coordination_and_context/)
- [API ReliefWeb](https://apidoc.reliefweb.int/read/)
- [ACAPS Data](https://www.acaps.org/en/data)
