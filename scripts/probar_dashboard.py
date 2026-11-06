#!/usr/bin/env python3
"""Pruebas de arranque de todas las páginas con Streamlit AppTest."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/"app.py"
PAGES=[
    "Sala situacional",
    "Vigilancia de señales",
    "Preparación en salud",
    "Análisis por país",
    "Fuentes y calidad",
]

def check(at,page):
    errors=[e.message for e in at.exception]
    assert not errors, f"Página '{page}' con errores: {errors}"
    print("OK:",page)

def main():
    report=ROOT/"docs/fase1/hapi_extraccion_completa.json"
    if report.exists():
        import json
        j=json.loads(report.read_text(encoding="utf-8"))
        assert j.get("paises_completos")==35, "HAPI regional exige 35 extracciones verificadas"
        assert not j.get("paises_excluidos"), "HAPI regional contiene países incompletos"
        print("OK: HAPI 35/35 países, sin datos parciales")
    for required in [
        ROOT/"assets/ops_oms.png",
        ROOT/"data/geografia/paises_americas.gpkg",
        ROOT/"data/observaciones/reliefweb_reportes_americas.csv",
        ROOT/"data/observaciones/acaps_acceso_americas.csv",
        ROOT/"data/observaciones/acaps_severity_americas.csv",
        ROOT/"data/observaciones/hapi_necesidades_nacional.csv",
        ROOT/"data/observaciones/hapi_financiacion_apelaciones.csv",
        ROOT/"data/observaciones/hapi_inform_componentes.csv",
        ROOT/"data/observaciones/hapi_pobreza_multidimensional.csv",
        ROOT/"data/observaciones/hapi_seguridad_alimentaria_ipc.csv",
        ROOT/"data/observaciones/hapi_presencia_sector.csv",
    ]:
        assert required.exists(), f"Falta archivo obligatorio: {required}"
    meta=ROOT/"docs/fase2/hapi_contexto_actualizacion.json"
    if meta.exists():
        import json
        j=json.loads(meta.read_text(encoding="utf-8"))
        assert j.get("descargas_completas") is True
        assert j.get("paises_catalogo")==35
        assert len(j.get("temas",{}))==5
        print("OK: cinco datasets HAPI con cobertura 35/35 consultas")
    # Todas las parejas de paneles se dibujan con un borde nativo y
    # altura fija compartida. Se rechazan regresiones que los dejen desparejos.
    code=(ROOT/"observatorio_v4.py").read_text(encoding="utf-8")
    assert 'height=height if height is not None else "content"' in code
    assert code.count("height=CARD_H")+code.count("height=SHORT_H")+code.count("height=590") >= 10
    assert "def executive(" in code and "def readiness(" in code
    assert "posibles repercusiones sanitarias" in code.lower() or "repercusiones sanitarias" in code
    assert "no constituyen" in code or "no constituye" in code.lower()
    at=AppTest.from_file(str(APP),default_timeout=90)
    at.run()
    check(at,PAGES[0])
    for page in PAGES[1:]:
        at.sidebar.radio[0].set_value(page).run()
        check(at,page)
    # Regresión: las cinco páginas deben soportar países con cobertura limitada.
    at.sidebar.selectbox[0].set_value("Caribe").run()
    at.sidebar.selectbox[1].set_value("ATG").run()
    for page in PAGES:
        at.sidebar.radio[0].set_value(page).run()
        check(at,page+" · país de cobertura limitada (ATG)")
    # Y un país con múltiples crisis y datos humanitarios.
    at.sidebar.selectbox[0].set_value("Sudamérica").run()
    at.sidebar.selectbox[1].set_value("COL").run()
    for page in PAGES:
        at.sidebar.radio[0].set_value(page).run()
        check(at,page+" · Colombia")

if __name__=="__main__":
    main()
