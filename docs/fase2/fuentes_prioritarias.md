# Fuentes para ampliar el Observatorio Humanitario OPS — versión de trabajo

Fecha: 2026-11-05. Alcance territorial: **35 países soberanos de las Américas**.

## Criterios obligatorios de publicación

1. **No presentar extracciones truncadas.** Cada país, fuente, periodo y nivel geográfico debe tener paginación completa, conteos verificados y fecha de corte. Si falla, excluir el indicador hasta corregirlo, pero mantener al país en el mapa.
2. **No igualar falta de dato a cero.** Conservar NA y el estado de cobertura por fuente.
3. **No mezclar diferentes denominadores, años, stocks/flows o geografías.** Homologar ISO3, fecha, tipo de indicador, población objetivo y definición.
4. **Respetar licencias.** GitHub es público, no guardar microdatos restringidos ni tokens. En Streamlit se visualizan copias locales de agregados autorizados.
5. **Sin índice ni categorías OPS de prioridad** hasta validación metodológica con Laura/equipo de emergencias.
6. **Trazabilidad:** valores con fuente, edición/corte, URL, fecha de descarga, nivel administrativo, completitud y advertencias.

## Datos ya disponibles en el repositorio

| Tema | Fuente | Nivel / estado | Acción |
|---|---|---|---|
| Riesgo estructural | INFORM Risk Mid 2026 | 35 países; completo | Visualizar |
| Severidad de crisis | INFORM Severity Sep 2026 | 25 crisis en 16 países | Visualizar por crisis, no sumar |
| Salud/vulnerabilidad | OPS Indicadores Básicos Oct 2026 | 3.038 filas en 35 países, 8 indicadores y años diversos | Visualizar por indicador y año |
| Conflicto | HDX HAPI / ACLED público agregado | 35 países consultados; sólo aceptar país con paginación completa y QA geográfica | Visualizar categorías separadas |
| Desplazamiento interno | OIM DTM Baseline | 12 países con registro nacional, rondas y años heterogéneos | Inventario; no sumar rondas |
| Necesidades | OIM DTM HNA | Ninguno de los 35 países en catálogo de 4 registros mundiales | No usar como indicador regional |
| Refugee Data Portal | ACNUR | Piloto de conectividad de 5 países | Expandir método/documentar licencia |

## Ampliación prioritaria

### 1. IDMC GIDD — máximo valor para desplazamiento interno comparable

- [Portal y descarga de datos](https://www.internal-displacement.org/database/displacement-data/)
- [API oficial y solicitud de acceso](https://helix-tools-api.idmcdb.org/external-api/)
- GIDD contiene estimaciones **validadas anuales** de desplazamientos internos (flujos) y población internamente desplazada (stock), diferenciando conflicto/violencia y desastres. Históricamente desde 2008.
- Descarga Excel pública por el portal. Para API enviar solicitud a `ch.datainfo@idmc.ch`; al recibir `client_id` guardarlo como `IDMC_CLIENT_ID` en GitHub Secrets. Revisar condiciones de distribución.
- Nunca sumar stock con flujo, ni nuevos movimientos con personas únicas.

### 2. ACNUR Refugee Data Finder — flujos migratorios y refugio

- [Documentación oficial UNHCR Data Finder API](https://www.unhcr.org/refugee-statistics/insights/explainers/forcibly-displaced-api.html)
- Proporciona población refugiada, solicitudes de asilo, país de origen y país de acogida, en un formato adecuado para productos de análisis.
- Separar dimensión de `country of origin` y `country of asylum`; no sumar flujos con stocks.
- Evaluar técnicamente API y términos antes de poner una extracción periódica en producción; la API `api-data.unhcr.org` del Refugee Data Portal indica que no es un backend para dashboards de terceros y no debe usarse para consultas masivas frecuentes.

### 3. OCHA HAPI — necesidades y respuesta

- [Documentación de personas afectadas y necesidades](https://hdx-hapi.readthedocs.io/en/latest/data_usage_guides/affected_people/)
- También permite explorar `humanitarian-needs`, IDP, refugiados y `operational-presence` con nuestra clave HAPI.
- Personas en necesidad (PiN) no se deben sumar entre sectores sin una metodología de deduplicación validada; la cobertura geográfica es irregular.

### 4. OMS SSA — ataques contra servicios de salud

- [Sistema de Vigilancia de Ataques a la Atención de Salud](https://extranet.who.int/ssa/index.aspx)
- Comprobar exportaciones oficiales, cobertura regional, condiciones de publicación y fecha de actualización antes de cargar cifras.

### 5. GDACS / IFRC GO — próxima ampliación de amenazas naturales

- [API GDACS](https://www.gdacs.org/gdacsapi/swagger/index.html) — alertas georreferenciadas de desastres, disponible sin clave, con condiciones de atribución.
- [API IFRC GO](https://go-wiki.ifrc.org/en/go-api/api-overview) — eventos, apelaciones y respuesta de la Cruz Roja.
- Son fuentes de **desastres**, no sustituirlas por indicadores de violencia política.

### 6. OCHA ReliefWeb y ACLED detallado

- ReliefWeb: solicitud de `appname` presentada. El identificador debe aprobarse antes de usar API en producción.
- ACLED: solicitud de licencia institucional presentada. No publicar eventos individuales ni usar microdatos en repositorio público sin autorización.

## MVP Streamlit

El código se encuentra en `app.py`. El prototipo inicial no depende de claves en tiempo de visualización: lee tablas del repositorio que pasaron QA. Las conexiones institucionales solo existen en GitHub Actions Secrets, con pruebas y extracción separadas.

**Próxima decisión técnica:** incorporar primero IDMC GIDD y ACNUR para fortalecer desplazamiento interno y transfronterizo; mantener OIM DTM como fuente operativa subnacional donde exista. Ampliar los indicadores sanitarios OPS relacionados con vulnerabilidad, sin proponer puntajes de riesgo sintéticos antes de la revisión metodológica.
