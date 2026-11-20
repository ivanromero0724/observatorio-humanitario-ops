# IDMC y AWSD: metodología, límites y licencias

Actualización inicial: 20 de noviembre de 2026.

## Navegación del Observatorio

- **Amenazas y eventos → Seguridad del personal humanitario:** AWSD, agregados nacionales por año y tipo de ataque.
- **Movilidad y necesidades → Desplazamiento interno:** IDMC GIDD (estimaciones anuales), IDMC IDU (eventos con actualizaciones preliminares) y OIM DTM (operaciones/rondas).
- **Perfiles por país:** resúmenes de AWSD e IDMC cuando hay registros.

## Fuentes, unidades y criterios

### IDMC GIDD (conflicto)

**Fuente:** Internal Displacement Monitoring Centre (IDMC), Global Internal Displacement Database (GIDD), endpoint `gidd/conflicts/`, https://www.internal-displacement.org/ y https://helix-tools-api.idmcdb.org/external-api/.

- `nuevos_desplazamientos`: desplazamientos **nuevos** durante el año (movimientos, no necesariamente personas distintas).
- `personas_desplazadas_fin_anio`: personas que **permanecen desplazadas** al cierre del año.
- **No sumar entre indicadores** ni inferir flujos a partir de diferencias de stock.
- Se conserva el valor faltante como vacío, nunca se reemplaza por cero.
- Las cifras comparadas se filtran por el **mismo año**.
- Se publican solo estimaciones nacionales de los 35 países del catálogo; los países sin registros no son ausencia de desplazamiento.

### IDMC IDU (actualizaciones preliminares)

**Fuente:** IDMC, Internal Displacement Updates, endpoint `idus/last-180-days/`.

- La API devuelve un archivo JSON alojado en S3; el token solo se envía al dominio IDMC.
- Se conservan registros de países del catálogo, `displacement_type=Conflict` y `role=Recommended figure`.
- Se consideran únicamente registros con `figure` numérica válida y fecha de evento interpretable.
- Se deduplican `event_id` dentro de cada combinación país + mes de inicio.
- **La variable publicada es el número de eventos IDU con estimación**, NO el total de personas desplazadas ni una cifra agregada de nuevos desplazamientos.
- Los eventos pueden aparecer en más de un mes según actualizaciones; no se suman períodos para inferir eventos únicos históricos.
- El mes corresponde al **inicio reportado del evento**, no necesariamente a su actualización o publicación; las cifras de origen son preliminares.
- No se publican `latitude`, `longitude`, coordenadas, textos libres, `source_url`, identificadores de incidente o `figure` individuales.

### AWSD

**Fuente:** Humanitarian Outcomes, Aid Worker Security Database (AWSD), https://www.aidworkersecurity.org/.

**Cita recomendada:** Humanitarian Outcomes, Aid Worker Security Database, aidworkersecurity.org. Fecha de acceso: registrada en el manifiesto de extracción.

- Se utiliza `/incidents/search?format=json` con `api_key` leída exclusivamente de GitHub Actions Secrets.
- Se cuentan incidentes distintos por `incident_id`, agrupados por país ISO3, año y tipo principal de ataque.
- Las variables `trabajadores_muertos`, `trabajadores_heridos`, `trabajadores_secuestrados` corresponden a los campos informados por AWSD; los valores ausentes NO se rellenan con cero.
- La categoría `tipo_ataque` es el mecanismo principal reportado en el registro. La selección **Todos** usa el agregado anual (no la suma de otras categorías).
- No representa todos los actos de violencia contra personal humanitario ni solamente ataques contra trabajadores **sanitarios**.
- Solo se publican agregados; no nombres, detalles, ubicaciones precisas o filas originales.

## Licencia y atribución

- **IDMC:** datos bajo **Creative Commons BY-NC-SA 3.0 IGO**. El uso debe ser no comercial, con atribución y distribuciones de adaptaciones bajo los términos de licencia aplicables. Fuente oficial: https://helix-tools-api.idmcdb.org/external-api/.
- **AWSD:** los datos están disponibles para uso no comercial, con referencia de la base, organización y fecha de acceso. Humanitarian Outcomes solicita informarles de productos desarrollados con los datos mediante **info@aidworkersecurity.org**. Condiciones: https://humanitarianoutcomes.org/terms-agreement.
- Los archivos CSV de origen IDMC en `data/observaciones/idmc_*.csv` son transformaciones de datos IDMC sujetas a su licencia indicada. Esta nota no pretende cambiar las licencias de otros conjuntos de datos del repositorio.

## Actualización, seguridad y control de calidad

El workflow `.github/workflows/actualizar_idmc_awsd.yml` se ejecuta semanalmente o manualmente.
Emplea `IDMC_API_TOKEN` y `AWSD_API_KEY` desde Secrets, sin publicar sus valores ni URLs firmadas.
Publica CSV de agregados e información de trazabilidad en `docs/fase2/monitoreo_idmc_awsd.json`.
Un error de la extracción principal aborta la publicación; se conservan archivos anteriores. Los CSV no sustituyen la validación de OPS/PHE ni producen prioridades institucionales.
