# Observatorio Regional de Amenazas y Vulnerabilidad Humanitaria — OPS/OMS

Proyecto de información humanitaria en la Región de las Américas. **Ya existe un prototipo de dashboard en Streamlit** y sus pruebas automáticas, pero la aplicación todavía debe desplegarse en Streamlit Cloud. No existe un índice oficial OPS de prioridades: las categorías y umbrales necesitan validación con el equipo técnico.

## Observatorio humanitario — propuesta OPS, Mauricio y taxonomía de Laura

**Objetivo:** mapear por país situaciones humanitarias de interés para OPS/OMS
(violencia, conflicto, movilidad forzada, acceso y entorno humanitario),
contextualizar su vulnerabilidad e identificar consecuencias documentadas sobre
personas y servicios. **No es un monitor de brotes ni de El Niño.**

**Interfaz activa:** [`app.py`](app.py) → [`observatorio_v6.py`](observatorio_v6.py).
Las tres páginas principales utilizan solo indicadores con información integrada:

1. **Amenazas y eventos:** violencia agregada (HAPI/ACLED), **ACLED Conflict Index 2025** con clasificación mundial, ranking y cuatro dimensiones, crisis y acceso (ACAPS), seguridad del personal humanitario (AWSD) y **Movilidad y desplazamiento** como subtema con ACNUR/HAPI, IDMC GIDD/IDU y OIM DTM.
2. **Vulnerabilidad y respuesta:** personas en necesidad (PiN intersectorial y sectorial OCHA/HAPI), indicadores sociales y de salud (OPS), pobreza MPI, inseguridad alimentaria IPC, presencia 3W y financiación FTS.
3. **Perfiles por país:** resumen de eventos, crisis, movilidad, indicadores de capacidad sanitaria y reportes ReliefWeb.

Las categorías aún sin datos integrados (crimen organizado, minería ilegal, ataques a salud y servicios esenciales afectados) no aparecen como filtros ni paneles vacíos; permanecen solo en documentación técnica para futura ampliación.

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

El job de [CI del dashboard](.github/workflows/dashboard_ci.yml) prueba las **tres páginas principales**. El job [revisión visual](.github/workflows/revisar_diseno.yml) abre Chromium a 1440 px, comprueba alturas de paneles lado a lado y publica capturas para inspección.

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

## Identidad visual

El observatorio usa la identidad del repositorio `COE-regional`: tipografía DM Sans, azul `#005A8B`, cian `#009BDA`, naranja `#F36B32`, fondo `#F7FAFC`, tarjetas blancas con borde `#DFE9F1`. Los mapas del observatorio utilizan una vista fija Plotly, sin zoom ni desplazamiento y con el mismo tratamiento de superficies y bordes del COE (dominio completo de las Américas). No se cambian fuentes ni niveles de seguimiento por motivos visuales. Componentes: `estilo_coe.py`, `mapa_coe.py`, `graficos.py`.

### Lectura de datos recientes IDMC IDU

La vista **Desplazamiento reciente** agrupa eventos únicos de conflicto y violencia registrados por IDMC IDU en una ventana seleccionable de 1, 3, 6 o 12 meses de **inicio del evento**, tomando como referencia el mes más reciente con registros en el ámbito consultado. El origen es una descarga de actualizaciones de los últimos 180 días; no equivale a una serie exhaustiva ni a cifras de personas desplazadas. Países sin actualizaciones publicadas se muestran sin dato, nunca como cero. El PiN se presenta en **Vulnerabilidad y respuesta**, no como cifra de movilidad.

### Índice de conflicto ACLED 2025

Fuente: [ACLED Conflict Index](https://acleddata.com/series/acled-conflict-index) (edición diciembre 2025); datos originales proporcionados en el archivo `ACLED_Conflict_Index_2025.xlsx` y reducidos a los 35 Estados soberanos del catálogo OPS en [data/observaciones/acled_conflict_index_2025.csv](data/observaciones/acled_conflict_index_2025.csv). Periodo de eventos: **1 de diciembre de 2024 a 28 de noviembre de 2025**. Los códigos ISO3 y los nombres en español se incorporan para interoperabilidad; no se recalculan los niveles ni los rangos originales de ACLED.

En la sección **Amenazas y eventos → Índice de conflicto (ACLED)** se muestran: mapa de las cuatro categorías originales (extremo, alto, turbulento, bajo/inactivo), distribución por país, **ranking mundial** (no ranking exclusivo de América) y las cuatro dimensiones: letalidad (fallecidos reportados), difusión territorial (valor fuente en proporción convertido a **porcentaje**), peligro para civiles (eventos dirigidos a civiles) y fragmentación (grupos armados activos). Estas medidas tienen distintas unidades, no se suman ni constituyen un índice de prioridad OPS. La clasificación anual no se actualiza semanalmente; la edición 2025 es un corte histórico.

**Atribución:** ACLED (Armed Conflict Location & Event Data), *Conflict Index, December 2025*, [acleddata.com/series/acled-conflict-index](https://acleddata.com/series/acled-conflict-index). Consulta del archivo original proporcionado: 20 de noviembre de 2026. Uso transformado: selección de 35 países, adición de código ISO3, etiquetas traducidas y difusión presentada como porcentaje. [Política de atribución](https://acleddata.com/attributionpolicy).
