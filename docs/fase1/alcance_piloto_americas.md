# Alcance del piloto regional — las Américas (35 países)

**Decisión de alcance:** el piloto del observatorio cubre los **35 países soberanos de las Américas**, sin seleccionar únicamente países con crisis o información disponible. El catálogo maestro está en `data/catalogos/paises_americas.csv`; esta tabla se utiliza como denominador común al evaluar fuentes.

| Subregión | Número de países |
|---|---:|
| América del Norte | 3 |
| Centroamérica | 7 |
| Caribe | 13 |
| Sudamérica | 12 |
| Total | **35** |

**Alcance geográfico:** los 35 Estados soberanos. Territorios dependientes y otros territorios del Caribe o América no se incluyen en este corte, aunque pueden incorporarse como unidades diferenciadas en una revisión posterior con OPS. No se confunde la disponibilidad de información con la inclusión territorial.

## Fuentes integradas en la prueba regional

1. **HAPI/OCHA, conflicto:** búsqueda por ISO3, periodo desde 2020, paginación con límite documentado, primera y última fecha y escala administrativa disponible. Las filas de las tres categorías ACLED son **no excluyentes**; no sumar sus conteos de eventos o muertes sin criterio validado. Los registros de HAPI no equivalen a sucesos individuales.
2. **OIM DTM Baseline:** consulta del catálogo mundial; para países de América presentes, prueba de datos nacionales Admin0 y número de filas reportadas. Un país ausente del catálogo no significa que tenga cero desplazados.
3. **OIM DTM HNA:** búsqueda en el catálogo mundial por país; la disponibilidad se determina por operación y año de evaluación. La prueba no suma necesidades de diferentes poblaciones, no publica microdatos y no inventa cobertura subnacional.

El archivo `docs/fase1/cobertura_hapi_oim_americas.csv` contiene **105 filas: 35 países × 3 fuentes** y la columna `estado`. `docs/fase1/resumen_piloto_regional.json` resume cobertura efectiva, estados de consulta y limitaciones.

## Estados posibles y lectura correcta

- `cobertura_verificada`, `registros_verificados`, `catalogo_verificado`: hay resultados bajo el método utilizado.
- `sin_registros_en_consulta`, `sin_registros_catalogo`: **sin registros bajo estos filtros / en el catálogo consultado**, distinto de ausencia de crisis.
- `paginacion_incompleta`: límite técnico alcanzado, no se debe tratar como serie completa.
- `consulta_error`, `error_consulta_admin0`, `error_catalogo`: la consulta falló, no se puede concluir cobertura.
- `sin_credencial`: clave no disponible para el workflow.

**No estamos generando niveles crítico/alto/elevado/moderado** hasta que Laura y OPS aprueben criterios. Tampoco existe todavía un tablero regional operativo con estas fuentes; esta es una evaluación verificable de factibilidad y cobertura.

## Ejecución

El flujo de GitHub Actions `.github/workflows/piloto_americas.yml` se activa al modificar el código regional o manualmente. Utiliza secretos del repositorio:

- `HDX_APP_IDENTIFIER`
- `DTMAPI_SUBSCRIPTION_KEY`
- `DTMHNA_SUBSCRIPTION_KEY`

No registrar los secretos en incidencias, tablas, capturas, scripts o archivos de configuración. La publicación automática incluye exclusivamente el inventario de **cobertura y metadatos**, no datasets de incidentes individuales ni contenido protegido por licencias.

## Próxima fase

Construir páginas de Panorama regional y Amenazas con un mapa de los 35 países, etiquetas de disponibilidad, filtros geográficos/temporales e indicadores sujetos a validación metodológica y autorización de las fuentes. La actualización debe hacer explícitas las diferentes fechas de referencia y cobertura temática.
