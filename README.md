# Observatorio Regional de Amenazas y Vulnerabilidad Humanitaria — OPS/OMS

Proyecto de información humanitaria en la Región de las Américas. **Ya existe un prototipo de dashboard en Streamlit** y sus pruebas automáticas, pero la aplicación todavía debe desplegarse en Streamlit Cloud. No existe un índice oficial OPS de prioridades: las categorías y umbrales necesitan validación con el equipo técnico.

## Observatorio humanitario — propuesta OPS, Mauricio y taxonomía de Laura

**Objetivo:** mapear por país situaciones humanitarias de interés para OPS/OMS
(violencia, conflicto, movilidad forzada, acceso y entorno humanitario),
contextualizar su vulnerabilidad e identificar consecuencias documentadas sobre
personas y servicios. **No es un monitor de brotes ni de El Niño.**

**Interfaz activa:** [`app.py`](app.py) → [`observatorio_v6.py`](observatorio_v6.py).
Las cinco páginas corresponden a la propuesta técnica del 5 de noviembre:

1. **Panorama regional:** mapa de magnitud documentada por país, tendencia,
   crisis evaluadas y tabla comparativa, sin índice propio OPS.
2. **Amenazas y eventos:** nueva [taxonomía de Laura](paginas_laura.py):
   acciones armadas (indicador parcial ACLED), ataques a civiles, migración,
   desplazamiento, acceso, fragilidad política, minería ilegal, crimen organizado,
   cultivos/mercados ilícitos y delincuencia transnacional. Cada subtipo declara
   fuente disponible, precisión y limitaciones.
3. **Vulnerabilidad y respuesta:** contexto económico, educación, calidad de aire,
   contexto social, capacidad sanitaria, morbimortalidad, vacunación y
   demografía. Los indicadores no conectados figuran como **pendientes**,
   no como valores inventados.
4. **Impacto humanitario y salud:** personas en necesidad (PiN), refugiados,
   establecimientos/personal de salud afectados y servicios esenciales:
   agua, electricidad, gas y telecomunicaciones. Las últimas variables
   requieren fuentes oficiales validadas para mostrar números.
5. **Perfiles por país:** ficha integradora de evidencia disponible,
   tendencias y reportes originales.

Los niveles **crítico, alto, elevado y moderado** se muestran como propuesta
de categorías de trabajo pero **no se asignan a países**, porque Laura y el
equipo OPS/PHE deben validar indicadores, umbrales, fuentes y criterios.

La cartografía y los gráficos mantienen la paleta OPS, y los mapas representan
datos a escala **nacional**, nunca coordenadas puntuales inventadas. Países
sin información quedan diferenciados de ceros reportados. Gráficos adyacentes
usan tarjetas con borde y alturas iguales.

**Referencias de implementación:**
- [Correspondencia detallada con la propuesta de Laura](docs/fase2/taxonomia_laura_matriz.md)
- [Mandato de Mauricio y metodología de seguimiento](docs/fase2/mandato_mauricio_propuesta.md)
- [Catálogo de fuentes e indicadores HAPI](docs/fase2/hapi_familias.md)
- [Código de las nuevas páginas](paginas_laura.py)
- [Arquitectura y limitaciones](docs/fase2/arquitectura_indicadores_dashboard.md)

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

El job de [CI del dashboard](.github/workflows/dashboard_ci.yml) prueba las **cinco páginas**. El job [revisión visual](.github/workflows/revisar_diseno.yml) abre Chromium a 1440 px, comprueba alturas de paneles lado a lado y publica capturas para inspección.

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

La exploración preliminar de ACNUR para cinco países sigue como antecedente. La serie regional de **ACNUR vía HAPI ya fue extraída para los 35 países de acogida**, con registros en 31 y categorías de población de 2024 en adelante separadas por origen/destino; ver [`hapi_acnur_actualizacion.json`](docs/fase2/hapi_acnur_actualizacion.json).

## Fase 1 — Datos, factibilidad y extracción inicial (05/11/2026)

**Datos realmente descargados y procesados** mediante GitHub Actions:

| Fuente / edición | Registros CSV | Cobertura comprobada | Archivo |
|---|---:|---|---|
| OPS, Indicadores Básicos octubre 2026 | 3.038 país–indicador–año | 35 países, 8 indicadores; 266/280 combinaciones país–indicador | [ops_8_indicadores_pais_anio.csv](data/observaciones/ops_8_indicadores_pais_anio.csv) |
| INFORM Risk Mid 2026 | 35 | 35/35 países soberanos de las Américas incluidos en el catálogo | [inform_risk_mid_2026.csv](data/observaciones/inform_risk_mid_2026.csv) |
| INFORM Severity septiembre 2026 | 25 crisis | 16 países; varias crisis por país | [inform_severity_2026_09_crisis.csv](data/observaciones/inform_severity_2026_09_crisis.csv) |
| WarMonit 05/11/2026 | 2 países de las Américas | Venezuela y Estados Unidos, de 20 mundiales | [warmonit_cii_ultimo.csv](data/observaciones/warmonit_cii_ultimo.csv) |

**ACNUR API:** 9 de 10 consultas del piloto de 5 países devolvieron al menos un registro; la combinación Haití/solicitantes de asilo no devolvió filas **con los filtros empleados**. Son pruebas de conectividad y cobertura muestral; no equivalen a análisis completo de flujos. No se han publicado cifras derivadas de esta API.

**HDX HAPI conflicto y OIM DTM:** claves configuradas y autenticación verificada; extracción HAPI completada para 35/35 países y reglas de integridad documentadas. **ACLED detallado:** en espera de licencia de sector público aplicable a OPS. **OMS SSA:** revisar exportación/cobertura/licencia. **ReliefWeb:** appname aprobado y metadatos de reportes integrados mediante GitHub Actions semanal. No se inventaron resultados para esas fuentes.

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
