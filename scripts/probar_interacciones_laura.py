#!/usr/bin/env python3
"""QA interactivo del planteamiento de Laura: subtipos y dimensiones sin datos."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/"app.py"

def pick(at,key,value):
    matches=[x for x in at.selectbox if x.key==key]
    assert len(matches)==1,(key,[(x.key,x.value) for x in at.selectbox])
    matches[0].set_value(value).run()
    assert not at.exception,[e.message for e in at.exception]
    print(f"OK: {key} = {value}",flush=True)

def main():
    at=AppTest.from_file(str(APP),default_timeout=90)
    at.run()
    assert not at.exception,[e.message for e in at.exception]
    at.sidebar.radio[0].set_value("Amenazas y eventos").run()
    assert not at.exception,[e.message for e in at.exception]
    # Cada tema de Laura debe navegar sin usar datos simulados.
    for grupo in [
        "Violencia",
        "Migración y desplazamiento",
        "Violencia generalizada y acceso",
        "Contexto político frágil",
        "Minería ilegal",
        "Crimen organizado",
        "Mercados ilícitos y cultivos",
        "Delincuencia transnacional",
    ]:
        pick(at,"laura_grupo_amenaza",grupo)
        if grupo=="Violencia":
            pick(at,"laura_subtipo","Ataques a objetivos y población civil")
        elif grupo=="Migración y desplazamiento":
            pick(at,"laura_subtipo","Desplazamiento interno")
        elif grupo=="Violencia generalizada y acceso":
            pick(at,"laura_subtipo","Restricciones a la movilidad y acceso humanitario")
    at.sidebar.radio[0].set_value("Vulnerabilidad y respuesta").run()
    assert not at.exception,[e.message for e in at.exception]
    for dim in ["Económico","Educación","Ambiental","Social",
                "Capacidad del sistema de salud","Morbimortalidad",
                "Cobertura de vacunación","Demografía"]:
        pick(at,"laura_dimension",dim)
        if dim=="Económico":
            pick(at,"laura_vuln_ind","Pobreza multidimensional")
        if dim=="Social":
            pick(at,"laura_vuln_ind","Pobreza multidimensional")
    at.sidebar.radio[0].set_value("Impacto humanitario y salud").run()
    assert not at.exception,[e.message for e in at.exception]
    print("OK: taxonomía, vulnerabilidad e impacto funcionan al cambiar filtros")

if __name__=="__main__":
    main()
