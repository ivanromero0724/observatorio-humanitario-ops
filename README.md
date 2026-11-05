# Observatorio Regional de Amenazas y Vulnerabilidad Humanitaria — OPS/OMS

Proyecto en fase de diseño y evaluación de fuentes. **No hay todavía un dashboard operativo ni una clasificación OPS de riesgo.**

## Fase 1 · Inventario y factibilidad (corte documental: 2026-11-05)

La matriz de trabajo se compone de **13 fuentes, 39 indicadores candidatos, 13 categorías de amenazas y 5 países piloto**. La versión Excel detallada fue preparada como documento editable para validación técnica con Laura.

### Componentes de esta fase
- `docs/fase1/diagnostico.md`: fuentes, viabilidad y restricciones identificadas.
- `data/catalogos/fuentes.csv`: directorio de fuentes institucionales y enlaces.
- `data/catalogos/indicadores_base.csv`: listado base de indicadores candidatos (la matriz Excel contiene definiciones completas).
- `scripts/fase1/probar_fuentes.py`: diagnóstico de WarMonit y HAPI con acceso a internet; no publica datos.

### Principios metodológicos
1. Diferenciar amenaza/evento, vulnerabilidad, exposición, impacto y capacidad de respuesta.
2. No sumar categorías de eventos ACLED no excluyentes ni datos PiN por sectores.
3. Distinguir población refugiada, solicitantes de asilo, desplazamiento y personas en necesidad.
4. Tratar `sin datos` de forma separada a `0`.
5. Mantener INFORM Risk, INFORM Severity y la prioridad operativa OPS como conceptos distintos.
6. Validar licencias y privacidad antes de descargar o publicar datos.

### Para probar conectividad
```bash
python -m pip install -r requirements.txt
python scripts/fase1/probar_fuentes.py
HDX_APP_IDENTIFIER=TU_IDENTIFICADOR python scripts/fase1/probar_fuentes.py
```

**Pendiente:** ejecutar pruebas con red y credenciales, validar cobertura por país y definir con Laura indicadores mínimos y taxonomía. OPS/ITS deberá validar la infraestructura de alojamiento.
