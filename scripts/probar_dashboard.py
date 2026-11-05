#!/usr/bin/env python3
"""Pruebas de arranque de todas las páginas con Streamlit AppTest."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/"app.py"
PAGES=[
    "Panorama regional",
    "Conflicto y violencia",
    "Desplazamiento y movilidad",
    "Salud y vulnerabilidad",
    "Perfiles de país",
    "Fuentes y metodología",
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
    at=AppTest.from_file(str(APP),default_timeout=55)
    at.run()
    check(at,PAGES[0])
    for page in PAGES[1:]:
        at.sidebar.radio[0].set_value(page).run()
        check(at,page)

if __name__=="__main__":
    main()
