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

1. **HAPI/OCHA, conflicto:** búsqueda por ISO3 y periodo desde 2020. Se descargaron todas las páginas necesarias de los 35 países y se construyeron 8.574 agregados país–mes–categoría, sin truncamiento. Se eliminaron 238 duplicados idénticos de Colombia y se reconciliaron 8 marcadores cero con sus registros positivos para la misma fuente, área y mes. El control de calidad se conserva en `docs/fase1/hapi_extraccion_completa.json`. Las filas de las tres categorías ACLED son **no excluyentes**; no sumar sus conteos de eventos o muertes sin criterio validado. Los registros de HAPI no equivalen a sucesos individuales.
2. **OIM DTM Baseline:** consulta del catálogo mundial; para países de América presentes, prueba de datos nacionales Admin0 y número de filas reportadas. Un país ausente del catálogo no significa que tenga cero desplazados.
3. **OIM DTM HNA:** búsqueda en el catálogo mundial por país; la disponibilidad se determina por operación y año de evaluación. La prueba no suma necesidades de diferentes poblaciones, no publica microdatos y no inventa cobertura subnacional.

El archivo `docs/fase1/cobertura_hapi_oim_americas.csv` contiene **105 filas: 35 países × 3 fuentes** y la columna `estado`. `docs/fase1/resumen_piloto_regional.json` resume cobertura efectiva, estados de consulta y limitaciones.

## Estados posibles y lectura correcta

- `cobertura_verificada`, `registros_verificados`, `catalogo_verificado`: hay resultados bajo el método utilizado.
- `sin_registros_en_consulta`, `sin_registros_catalogo`: **sin registros bajo estos filtros / en el catálogo consultado**, distinto de ausencia de crisis.
- `paginacion_incompleta`: límite técnico alcanzado, no se debe tratar como serie completa.
- `consulta_error`, `error_consulta_admin0`, `error_catalogo`: la consulta falló, no se puede concluir cobertura.
- `sin_credencial`: clave no disponible para el workflow.

**No estamos generando niveles crítico/alto/elevado/moderado** hasta que Laura y OPS aprueben criterios. Ya existe un **prototipo de dashboard Streamlit** en `app.py`, con seis secciones. Su publicación en Streamlit Cloud está pendiente; no constituye aún un producto oficial OPS.

## Ejecución

El flujo de GitHub Actions `.github/workflows/piloto_americas.yml` se activa al modificar el código regional o manualmente. Utiliza secretos del repositorio:

- `HDX_APP_IDENTIFIER`
- `DTMAPI_SUBSCRIPTION_KEY`
- `DTMHNA_SUBSCRIPTION_KEY`

No registrar los secretos en incidencias, tablas, capturas, scripts o archivos de configuración. La publicación automática incluye exclusivamente el inventario de **cobertura y metadatos**, no datasets de incidentes individuales ni contenido protegido por licencias.

## Próxima fase

Desplegar en Streamlit Community Cloud el prototipo validado, revisar su diseño y métodos con OPS, y ampliar indicadores anuales de desplazamiento interno con IDMC GIDD y refugiados/asilo con ACNUR, preservando fechas, cobertura y fuentes. Consulta también `docs/fase2/fuentes_prioritarias.md`.
