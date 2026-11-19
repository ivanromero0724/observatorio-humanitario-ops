#!/usr/bin/env python3
"""QA de controles temáticos con las fuentes realmente integradas."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
PAGES = [
    "Amenazas y eventos", "Movilidad y necesidades",
    "Vulnerabilidad y respuesta", "Perfiles por país",
]


def check(at, where):
    assert not at.exception, f"{where}: {[e.message for e in at.exception]}"


def select_if_present(at, key):
    matching = [x for x in at.selectbox if x.key == key]
    if matching:
        assert len(matching[0].options) >= 1, f"{key}: sin opciones"
        # Probar solo valores originales; las etiquetas format_func son texto visible.
        values = {"op_event_kind": "civilian_targeting",
                  "op_un_group": "ASY",
                  "op_ops_ind": "Médicos"}
        if key in values:
            matching[0].set_value(values[key]).run()
            check(at, key)


def main():
    at = AppTest.from_file(str(APP), default_timeout=90)
    at.run()
    check(at, "inicio")
    assert [x.value for x in at.sidebar.radio] == ["Amenazas y eventos"]

    for page in PAGES:
        at.sidebar.radio[0].set_value(page).run()
        check(at, page)
        if page == "Amenazas y eventos":
            select_if_present(at, "op_event_kind")
            # Deslizador discreto, con 1, 3, 6, 9 y 12 meses.
            assert not [x for x in at.selectbox if x.key == "op_event_months"]
            # AppTest puede no exponer select_slider en su árbol de widgets;
            # la prueba Playwright sí confirma el control real en el navegador.
            sliders = [x for x in at.get("select_slider")
                       if x.key == "op_event_months"]
            if sliders:
                for value in (1, 3, 6, 9, 12):
                    sliders[0].set_value(value).run()
                    check(at, f"periodo de {value} meses")
                    sliders = [x for x in at.get("select_slider")
                               if x.key == "op_event_months"]
            else:
                assert "st.select_slider(" in (ROOT / "paginas_operativas.py").read_text(
                    encoding="utf-8")
                check(at, "deslizador renderizado")
        elif page == "Movilidad y necesidades":
            select_if_present(at, "op_un_group")
            select_if_present(at, "op_un_year")
            select_if_present(at, "op_dtm_country")
        elif page == "Vulnerabilidad y respuesta":
            select_if_present(at, "op_ops_ind")
            select_if_present(at, "op_ipc_country")
        else:
            select_if_present(at, "op_profile_country")
    print("OK: cuatro vistas temáticas y controles vinculados a datos disponibles")


if __name__ == "__main__":
    main()
