#!/usr/bin/env python3
"""Pruebas de arranque de todas las páginas con Streamlit AppTest."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/"app.py"
PAGES=[
    "Amenazas y eventos",
    "Vulnerabilidad y respuesta",
    "Perfiles por país",
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
    code=(ROOT/"observatorio_v5.py").read_text(encoding="utf-8")
    assert 'height=CARD_H' in code and 'height=645' in code
    assert code.count("height=CARD_H")>=6, "Faltan parejas de paneles de altura uniforme"
    assert "def map_page(" in code and "def migration_page(" in code
    assert "def violence_page(" in code and "def profile_page(" in code
    assert "def crisis_core(" in code
    assert "desplazamiento forzado" in code.lower()
    assert "no constituyen" in code or "no constituye" in code.lower()
    # La escala numérica del mapa debe representar valores reales, no
    # solo tonalidades descriptivas. ACAPS/INFORM mantienen rango 0–10.
    import sys
    sys.path.insert(0, str(ROOT))
    from mapa_coe import _legend_ticks
    ticks = _legend_ticks("events", 10000)
    assert ticks[0] == (0.0, "0")
    assert ticks[-1] == (1.0, "10,000")
    assert len(ticks) >= 4
    assert _legend_ticks("severity", 10) == [(0.0,"0"),(0.5,"5"),(1.0,"10")]
    assert _legend_ticks("risk", 10)[-1][1] == "10"
    map_code=(ROOT/"mapa_coe.py").read_text(encoding="utf-8")
    assert "_numeric_legend(fig, mode, maximum, legend_title)" in map_code
    assert "Azul claro: menor" not in map_code
    # Regresión visual/funcional de tablas: sin relleno artificial,
    # con formato de miles y escapes seguros para contenido externo.
    from unittest.mock import patch
    from observatorio_v4 import table
    import pandas as pd
    example=pd.DataFrame({
        "País":["Venezuela","<script>alert(1)</script>"],
        "Año":[2026,2024],
        "Personas en necesidad":[7900000,6414193],
    })
    with patch("observatorio_v4.st.markdown") as renderer:
        table(example,height=390)
        html=renderer.call_args.args[0]
    assert html.count("<tbody>")==1 and html.count("<tr>")==3
    assert "7,900,000" in html and "6,414,193" in html
    assert "2026" in html and "2,026" not in html
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "ops-data-table" in html
    # PiN intersectorial y sectorial son medidas separadas: filtrado por
    # categoría agregada y selección de un solo año/país para el desglose.
    from pin_utils import intersectoral_pin, sectoral_pin, SECTOR_LABELS
    raw_pin=pd.read_csv(ROOT/"data/observaciones/hapi_necesidades_nacional.csv")
    pin_general=intersectoral_pin(raw_pin)
    pin_sector=sectoral_pin(raw_pin)
    assert pin_general.duplicated(["iso3","anio"]).sum()==0
    assert pin_sector.duplicated(["iso3","anio","sector_code"]).sum()==0
    assert pin_sector["category"].fillna("").eq("").all()
    assert not pin_sector["sector_code"].eq("Intersectoral").any()
    assert pin_general.query("iso3=='COL' and anio==2026")["population"].iloc[0]==6900000
    assert len(pin_sector.query("iso3=='COL' and anio==2025"))==10
    assert pin_sector.query("iso3=='COL' and anio==2026").empty
    assert len(pin_sector.query("iso3=='HTI' and anio==2026"))==8
    assert pin_general.query("iso3=='SLV' and anio==2025")["population"].iloc[0]==818700
    assert SECTOR_LABELS["HEA"]=="Salud"
    assert pin_sector.query("iso3=='COL' and anio==2025")["population"].sum() != (
        pin_general.query("iso3=='COL' and anio==2025")["population"].iloc[0])
    # Nuevas bases IDMC y AWSD: publicar únicamente agregados seguros.
    from observatorio_v2 import load_all, csv, _data_file_signature
    from unittest.mock import patch
    from tempfile import TemporaryDirectory
    # Evitar que Streamlit conserve en caché una tabla vacía si el CSV se
    # publica en GitHub Actions después del primer arranque del tablero.
    with TemporaryDirectory() as tmp:
        root=Path(tmp)
        relative="data/observaciones/idmc_idu_pais_mes.csv"
        source=root/relative
        with patch("observatorio_v2.ROOT",root):
            before=_data_file_signature()
            assert csv(relative).empty
            source.parent.mkdir(parents=True,exist_ok=True)
            source.write_text("iso3,anio,mes,periodo,actualizaciones\nCOL,2026,10,2026-10,4\n",
                              encoding="utf-8")
            after=_data_file_signature()
            assert before!=after, "No se detectó nuevo snapshot IDU"
            assert csv(relative)["actualizaciones"].iloc[0]==4, (
                "El CSV IDU quedó bloqueado en caché negativa")
    D=load_all()
    for key in ("idmc_gidd","idu","awsd","awsd_types","acled_conflict_index"):
        assert key in D and not D[key].empty, f"Falta fuente: {key}"
    # ACLED Conflict Index 2025 es una instantánea nacional, no un índice OPS.
    acled=D["acled_conflict_index"]
    assert len(acled)==35 and acled["iso3"].nunique()==35
    assert acled["anio"].eq(2025).all()
    assert not acled.duplicated(["iso3","anio"]).any()
    assert set(acled["nivel_indice"])=={
        "Extreme","High","Turbulent","Low/Inactive"}
    assert acled["nivel_indice"].value_counts().to_dict()=={
        "Low/Inactive":22,"Turbulent":5,"High":4,"Extreme":4}
    assert int(acled.set_index("iso3").loc["COL","ranking_global"])==14
    assert int(acled.set_index("iso3").loc["MEX","ranking_global"])==4
    assert abs(float(acled.set_index("iso3").loc["MEX","proporcion_difusion"])*100-1.2)<1e-9
    ci_module=(ROOT/"vista_conflict_index.py").read_text(encoding="utf-8")
    assert "def acled_conflict_tab(" in ci_module
    assert "def profile_acled_conflict(" in ci_module
    assert "No se suman" in ci_module or "no se suman" in ci_module
    assert '"Clasificación ACLED 2025, no prioridad OPS"' not in ci_module
    assert (ci_module.index('#### Comparación regional de las dimensiones')
            < ci_module.index('#### Detalle de un país'))
    assert ci_module.index('key="op_acled_index_dimension"') < ci_module.index(
        'key="op_acled_index_country"')
    assert '"Índice de conflicto (ACLED)"' in (
        ROOT/"paginas_operativas.py").read_text(encoding="utf-8")
    gidd=D["idmc_gidd"]
    awsd=D["awsd"]
    typed=D["awsd_types"]
    idu=D["idu"]
    assert not gidd.duplicated(["iso3","anio"]).any()
    assert not awsd.duplicated(["iso3","anio"]).any()
    assert not typed.duplicated(["iso3","anio","tipo_ataque"]).any()
    assert not idu.duplicated(["iso3","periodo"]).any()
    assert len(gidd)>=100 and len(awsd)>=70 and len(idu)>=1
    assert gidd["anio"].max()>=2025
    assert (pd.to_numeric(awsd["incidentes"],errors="coerce")>=0).all()
    assert (pd.to_numeric(idu["actualizaciones"],errors="coerce")>0).all()
    # Los incidentes anuales deben ser iguales al desglose exhaustivo por tipo.
    checktypes=typed.groupby(["iso3","anio"],as_index=False)["incidentes"].sum()
    cmp=awsd.merge(checktypes,on=["iso3","anio"],suffixes=("_anual","_tipos"),
                   validate="one_to_one")
    assert len(cmp)==len(awsd)
    assert (cmp["incidentes_anual"]==cmp["incidentes_tipos"]).all()
    # Verificar explícitamente que no se publicaron filas individuales.
    for forbidden in ("latitude","longitude","incident_id","event_id","details"):
        assert forbidden not in awsd.columns and forbidden not in idu.columns
    new_module=(ROOT/"vista_awsd_idmc.py").read_text(encoding="utf-8")
    assert "def awsd_tab(" in new_module and "def gidd_tab(" in new_module
    assert "def idu_tab(" in new_module
    assert 'key="op_idu_lookback"' in new_module
    assert 'options=[1,3,6,12],value=6' in new_module
    assert "No se suman" in new_module or "no se suman" in new_module
    # La ventana IDU de 6 meses conserva eventos válidos incluso si
    # el mes más reciente tiene información para muy pocos países.
    six_start=str(pd.Period(idu["periodo"].max(),freq="M")-5)
    recent=idu[idu["periodo"].astype(str).between(six_start,idu["periodo"].max())]
    assert recent["actualizaciones"].sum()>0
    # El selector Salud y sociedad incluye incidencia OPHI MPI, preservando
    # exactamente el porcentaje fuente (headcount_ratio ya está en %).
    from paginas_operativas import _poverty_context_frame, POVERTY_CONTEXT_INDICATOR
    poverty=_poverty_context_frame(D,set(D["countries"]["iso3"]))
    assert not poverty.empty
    assert poverty["iso3"].nunique()>=20
    assert poverty["indicador"].eq(POVERTY_CONTEXT_INDICATOR).all()
    assert not poverty.duplicated(["iso3","periodo"]).any()
    mex=poverty[(poverty["iso3"]=="MEX")&(poverty["periodo"]==2023)]
    assert len(mex)==1 and abs(float(mex["valor"].iloc[0])-5.274)<1e-7
    assert "OPHI MPI" in (ROOT/"paginas_operativas.py").read_text(encoding="utf-8")
    operational=(ROOT/"paginas_operativas.py").read_text(encoding="utf-8")
    assert operational.index('elif topic == "Personas en necesidad"') > operational.index('def vulnerabilidad_page(')
    assert '["Refugio y asilo", "Desplazamiento interno"]' in operational
    for name in ("amenazas_page", "_movilidad_tab", "vulnerabilidad_page", "perfil_page"):
        assert f"def {name}(" in operational
    assert '"Incidencia de pobreza multidimensional (%)"' in operational
    assert "POVERTY_CONTEXT_INDICATOR" in operational
    assert '"op_ops_ind"' in operational
    assert '"op_ops_common"' in operational
    assert '"Movilidad y desplazamiento"' in operational.split(
        'def amenazas_page(')[1].split('def _acnur_tab(')[0]
    assert "_movilidad_tab(D, selected)" in operational
    for label in ("Eventos de violencia", "Crisis evaluadas y acceso",
                  "Refugio y asilo", "Desplazamiento interno",
                  "Personas en necesidad", "Riesgo INFORM",
                  "Salud y sociedad", "Seguridad alimentaria", "Respuesta"):
        assert label in operational
    risk=(ROOT/"detalle_riesgo.py").read_text(encoding="utf-8")
    assert "def risk_page(" in risk and "def acaps_detail(" in risk
    assert "brecha_info" in risk and "indicador_9" in risk
    assert "Minería ilegal" not in operational
    assert "muertes_reportadas" in operational
    assert "Último mes disponible" in operational
    assert "st.tabs(" not in operational
    assert "st.segmented_control(" in operational
    profile=(ROOT/"perfil_integral.py").read_text(encoding="utf-8")
    for label in ("Amenazas y crisis","Movilidad y desplazamiento",
                  "Riesgo y vulnerabilidad","Respuesta e informes",
                  "Crisis humanitarias evaluadas"):
        assert label in profile
    for key in ('"inform_hapi"','"mpi"','"ipc"','"presence"',
                '"funding"','"acnur"','"dtm"','"needs"'):
        assert key in profile, f"Falta fuente {key} en perfil integral"
    assert "reports(D,chosen" in profile, "No integra ReliefWeb"

    assert "metric_strip(" in operational and "metric_strip(" in profile
    assert "OCHA ReliefWeb" in profile and "OIM DTM" in profile
    assert "ACCESS_PILLARS.items()" in profile
    assert "ACCESS_INDICATORS.items()" in profile
    assert 'f"P{n} · Pilar"' not in profile
    assert 'f"I{n} · Indicador"' not in profile
    from detalle_riesgo import ACCESS_PILLARS, ACCESS_INDICATORS
    assert len(ACCESS_PILLARS)==3 and len(ACCESS_INDICATORS)==9
    assert all(not name.startswith(("P1", "P2", "P3", "I1", "I2", "I3"))
               for name in [*ACCESS_PILLARS.values(), *ACCESS_INDICATORS.values()])
    # Se deben conservar separadores coma (miles) y punto (decimales).
    from observatorio_v4 import fmt
    assert fmt(12500) == "12,500" and fmt(12500.75,2) == "12,500.75"
    assert fmt(4.56,1) == "4.6"
    from graficos import rank_bars
    import pandas as pd
    chart=rank_bars(pd.DataFrame({"nombre":["A"],"valor":[12345]}),
                    label="nombre",value="valor",formats=".0f")
    assert chart.data[0].text[0]=="12,345"
    assert chart.layout.separators==".,"
    assert 'options=[1, 3, 6, 9, 12]' in operational
    assert "PiN intersectorial (general)" in operational
    assert "PiN por sector" in operational
    assert "op_pin_sector_country" in operational and "op_pin_sector_year" in operational
    assert "sectoral_pin(needs)" in operational
    assert "sectoral_pin(needs)" in profile
    assert "profile_acled_conflict(D,scope)" in profile
    assert "profile_awsd(D,scope)" in profile
    assert "profile_idmc(D,scope)" in profile
    assert "Seguridad del personal humanitario" in operational
    assert "Desplazamiento reciente" in operational and "Estimaciones anuales" in operational
    assert "Operaciones OIM" in operational


    for field in ("impacto_geografico", "personas_idp_reportadas",
                  "headcount_ratio", "funding_usd"):
        assert field in profile, f"Perfil incompleto: falta {field}"
    assert "def perfil_page(" in operational and "profile_page(D, selected, names)" in operational
    nav=(ROOT/"observatorio_v6.py").read_text(encoding="utf-8")
    assert all(page in nav for page in PAGES)
    at=AppTest.from_file(str(APP),default_timeout=90)
    at.run()
    check(at,PAGES[0])
    for page in PAGES[1:]:
        at.sidebar.radio[0].set_value(page).run()
        check(at,page)
    # Regresión: las tres páginas principales deben soportar países con cobertura limitada.
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
