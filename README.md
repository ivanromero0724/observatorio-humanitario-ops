# Observatorio Regional de Amenazas y Vulnerabilidad Humanitaria — OPS/OMS

Proyecto de información humanitaria en la Región de las Américas. **Ya existe un prototipo de dashboard en Streamlit** y sus pruebas automáticas, pero la aplicación todavía debe desplegarse en Streamlit Cloud. No existe un índice oficial OPS de prioridades: las categorías y umbrales necesitan validación con el equipo técnico.

## Dashboard Streamlit — prototipo regional

La aplicación se encuentra en [`app.py`](app.py), con paleta OPS/OMS. Incluye seis páginas: panorama regional, conflicto y violencia, desplazamiento y movilidad, salud y vulnerabilidad, perfiles por país, y fuentes/metodología.

- **Mapa regional:** INFORM Risk Mid 2026 (35 países) y detalle de 25 crisis INFORM Severity.
- **Salud:** ocho series OPS por país, filtro de año y advertencias de comparabilidad.
- **Desplazamiento:** cobertura OIM DTM para 35 países sin imputar ceros ni sumar rondas incompatibles.
- **Conflicto:** 8.574 agregados país–mes–categoría de HAPI, a partir de las 35 extracciones completas y con QA; no sumar categorías ACLED.
- **Países:** ficha con crisis, riesgo, indicadores OPS, y disponibilidad de fuentes.
- **Fuentes:** fechas y limitaciones para permitir revisión metodológica.

### Ejecutar localmente

```bash
git clone https://github.com/ivanromero0724/observatorio-humanitario-ops.git
cd observatorio-humanitario-ops
python -m pip install -r requirements.txt
streamlit run app.py
```

### Publicar en Streamlit Community Cloud

1. Ingresar a [share.streamlit.io](https://share.streamlit.io/) con la cuenta de GitHub con acceso al repositorio.
2. **Create app → From existing repo**; seleccionar `ivanromero0724/observatorio-humanitario-ops`, rama `main`, archivo principal `app.py`.
3. Presionar **Deploy**. No es necesario cargar los secretos HAPI/DTM en Streamlit: la app consume las **tablas derivadas y verificadas** publicadas por GitHub Actions, no consulta directamente las API protegidas.
4. Revisar la URL asignada y los permisos de visibilidad antes de compartir la aplicación con OPS. El repositorio es público y este despliegue es exploratorio.

El job de [CI del dashboard](.github/workflows/dashboard_ci.yml) realiza una prueba automática de apertura de las seis secciones.

## Piloto ampliado a toda la Región de las Américas — 5 de noviembre de 2026

**El alcance vigente es de 35 países soberanos, no únicamente los 5 países utilizados en la exploración original de ACNUR.** El catálogo regional de referencia es [`data/catalogos/paises_americas.csv`](data/catalogos/paises_americas.csv), agrupado en América del Norte (3), Centroamérica (7), Caribe (13) y Sudamérica (12).

La primera ejecución de [`piloto_americas.yml`](.github/workflows/piloto_americas.yml) verificó las tres fuentes con las credenciales institucionales:

| Fuente | Países evaluados | Disponibilidad bajo filtros aplicados |
|---|---:|---|
| HDX HAPI / conflicto desde 2020 | 35 | 35 países con paginación exhaustiva y QA aprobada; 8.574 registros país–mes–categoría; Colombia: 238 duplicados idénticos eliminados y 8 marcadores cero reconciliados |
| OIM DTM Baseline (IDP) | 35 | 12 países con registros Admin0; 23 sin país en el catálogo de la API |
| OIM DTM Humanitarian Needs Assessment (HNA) | 35 | Ningún país americano en el catálogo actual de 4 filas globales |

**No se interpreta ausencia de datos como ausencia de amenaza, personas desplazadas o necesidades.** Las filas HAPI representan registros agregados por periodo/categoría/territorio, **no son eventos individuales**; sus tres categorías de ACLED se superponen y no pueden sumarse sin reglas metodológicas. Las fechas, grados de disponibilidad y límites se conservan explícitamente.

- [Cobertura región × fuente, 105 registros](docs/fase1/cobertura_hapi_oim_americas.csv)
- [Resumen regional con estados y límites](docs/fase1/resumen_piloto_regional.json)
- [Matriz de 35 países](data/catalogos/cobertura_piloto.csv)
- [Metodología y alcance](docs/fase1/alcance_piloto_americas.md)

La exploración preliminar de ACNUR para cinco países sigue documentada como antecedente; no representa el alcance final del observatorio. La cobertura regional de ACNUR podrá completarse en un flujo de trabajo independiente.

## Fase 1 — Datos, factibilidad y extracción inicial (05/11/2026)

**Datos realmente descargados y procesados** mediante GitHub Actions:

| Fuente / edición | Registros CSV | Cobertura comprobada | Archivo |
|---|---:|---|---|
| OPS, Indicadores Básicos octubre 2026 | 3.038 país–indicador–año | 35 países, 8 indicadores; 266/280 combinaciones país–indicador | [ops_8_indicadores_pais_anio.csv](data/observaciones/ops_8_indicadores_pais_anio.csv) |
| INFORM Risk Mid 2026 | 35 | 35/35 países soberanos de las Américas incluidos en el catálogo | [inform_risk_mid_2026.csv](data/observaciones/inform_risk_mid_2026.csv) |
| INFORM Severity septiembre 2026 | 25 crisis | 16 países; varias crisis por país | [inform_severity_2026_09_crisis.csv](data/observaciones/inform_severity_2026_09_crisis.csv) |
| WarMonit 05/11/2026 | 2 países de las Américas | Venezuela y Estados Unidos, de 20 mundiales | [warmonit_cii_ultimo.csv](data/observaciones/warmonit_cii_ultimo.csv) |

**ACNUR API:** 9 de 10 consultas del piloto de 5 países devolvieron al menos un registro; la combinación Haití/solicitantes de asilo no devolvió filas **con los filtros empleados**. Son pruebas de conectividad y cobertura muestral; no equivalen a análisis completo de flujos. No se han publicado cifras derivadas de esta API.

**HDX HAPI conflicto y OIM DTM:** claves configuradas y autenticación verificada; extracción HAPI completada para 35/35 países y reglas de integridad documentadas. **ACLED detallado:** en espera de licencia de sector público aplicable a OPS. **OMS SSA:** revisar exportación/cobertura/licencia. **ReliefWeb:** solicitud de appname presentada y pendiente de aprobación. No se inventaron resultados para esas fuentes.

### Estructura del proyecto
- `docs/fase1/diagnostico.md`: inventario de 13 fuentes, metodología inicial, límites y decisiones pendientes.
- `docs/fase1/resultados_cobertura.csv`: 400 observaciones de disponibilidad/extracción por país y fuente (incluye las 280 combinaciones OPS).
- `docs/fase1/ejecucion_fuentes.json`, `esquemas_fuentes.json`, `qa_normalizados.json`: controles verificables.
- `data/catalogos/`: 39 indicadores preliminares, taxonomía de 13 categorías, 35 países en el piloto regional, plan de trabajo, fuentes.
- `data/observaciones/`: cuatro CSV normalizados por edición.
- `scripts/fase1/extraer_cobertura.py`: descarga y normalización de INFORM, OPS, WarMonit, consulta piloto ACNUR e interfaz HAPI.
- `scripts/fase1/validar_datos.py`: validación de rangos, duplicados, integridad SHA-256.
- `.github/workflows/fase1_cobertura.yml`: ejecución automática al cambiar código y manual mediante `workflow_dispatch`. Los archivos de observaciones se actualizan **al ejecutarse**, no de manera programada diaria. La publicación falla si una fuente esencial no responde.
 
### Ejecutar localmente
```bash
python -m pip install -r requirements.txt
python scripts/fase1/extraer_cobertura.py
python scripts/fase1/validar_datos.py
```
Para sumar HAPI:
```bash
export HDX_APP_IDENTIFIER="IDENTIFICADOR_INSTITUCIONAL"
python scripts/fase1/extraer_cobertura.py
```
En GitHub Actions configura `HDX_APP_IDENTIFIER` como secreto, no dentro del repositorio. Si no está definido, el proceso continúa sin HAPI y registra el bloqueo.

### Criterios de lectura
1. **No confundir cobertura con ausencia:** un país sin filas en una consulta no tiene necesariamente cero eventos/personas.
2. **No sumar poblaciones solapadas:** PiN de distintos sectores, stocks de desplazamiento/refugiados y otras cifras requieren comprobación de denominadores y periodos.
3. **INFORM Risk es estructural e incluye amenazas naturales.** No describe sólo violencia, conflicto o movilidad.
4. **INFORM Severity es por crisis**, no un puntaje único de amenaza de cada país; los datos incluyen crisis de naturaleza diversa.
5. **OPS contiene series históricas heterogéneas**; cada fila conserva año e indicador, pero no deben compararse valores de años distintos como si fueran del mismo corte.
6. Las puntuaciones disponibles son de las **fuentes originales**; no representan una clasificación aprobada por OPS.
7. WarMonit CC BY 4.0 requiere atribución; otras fuentes tienen condiciones propias.

**Pendiente de validación humana:** aprobación por Laura de definiciones y taxonomía, selección de indicadores operativos, licencias/accesos, territorios adicionales, alojamiento ITS, y reglas de prioridad crítico/alto/elevado/moderado.

La matriz Excel validada y el informe de cierre Word se entregan aparte, listos para revisión técnica.
