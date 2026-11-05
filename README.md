# Observatorio Regional de Amenazas y Vulnerabilidad Humanitaria — OPS/OMS

Proyecto de información humanitaria en la Región de las Américas. **Todavía no existe un dashboard operativo ni un índice oficial OPS de prioridades:** las categorías y los umbrales necesitan validación con el equipo técnico.

## Fase 1 — Datos, factibilidad y extracción inicial (05/11/2026)

**Datos realmente descargados y procesados** mediante GitHub Actions:

| Fuente / edición | Registros CSV | Cobertura comprobada | Archivo |
|---|---:|---|---|
| OPS, Indicadores Básicos octubre 2026 | 3.038 país–indicador–año | 35 países, 8 indicadores; 266/280 combinaciones país–indicador | [ops_8_indicadores_pais_anio.csv](data/observaciones/ops_8_indicadores_pais_anio.csv) |
| INFORM Risk Mid 2026 | 35 | 35/35 países soberanos de las Américas incluidos en el catálogo | [inform_risk_mid_2026.csv](data/observaciones/inform_risk_mid_2026.csv) |
| INFORM Severity septiembre 2026 | 25 crisis | 16 países; varias crisis por país | [inform_severity_2026_09_crisis.csv](data/observaciones/inform_severity_2026_09_crisis.csv) |
| WarMonit 05/11/2026 | 2 países de las Américas | Venezuela y Estados Unidos, de 20 mundiales | [warmonit_cii_ultimo.csv](data/observaciones/warmonit_cii_ultimo.csv) |

**ACNUR API:** 9 de 10 consultas del piloto de 5 países devolvieron al menos un registro; la combinación Haití/solicitantes de asilo no devolvió filas **con los filtros empleados**. Son pruebas de conectividad y cobertura muestral; no equivalen a análisis completo de flujos. No se han publicado cifras derivadas de esta API.

**HDX HAPI conflicto:** pendiente de un `HDX_APP_IDENTIFIER` institucional real. **ACLED detallado:** verificar licencia de sector público aplicable a OPS. **OIM DTM:** requiere clave. **OMS SSA:** revisar exportación/cobertura/licencia. **ReliefWeb:** acceso institucional para uso API. No se inventaron resultados para esas fuentes.

### Estructura del proyecto
- `docs/fase1/diagnostico.md`: inventario de 13 fuentes, metodología inicial, límites y decisiones pendientes.
- `docs/fase1/resultados_cobertura.csv`: 400 observaciones de disponibilidad/extracción por país y fuente (incluye las 280 combinaciones OPS).
- `docs/fase1/ejecucion_fuentes.json`, `esquemas_fuentes.json`, `qa_normalizados.json`: controles verificables.
- `data/catalogos/`: 39 indicadores preliminares, taxonomía de 13 categorías, 5 países piloto, plan de trabajo, fuentes.
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
