"""Observatorio Regional de Amenazas y Vulnerabilidad Humanitaria — prototipo OPS/OMS.

Dashboard de datos públicos agregados y metadatos de cobertura, 35 países.
SIN puntuación de prioridades OPS ni conclusiones de causalidad / atribución.
Cifras HAPI solo si están completas y validadas para cada país.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from ui_ops import apply_style, header as ops_header, heading as ops_heading, map_countries, footer as ops_footer
from paginas_extra import access_page, reports_page
from graficos import finish as chart_finish, rank_bars, trend, strip_countries, severity_matrix
from paginas_hapi import render as render_hapi

ROOT = Path(__file__).resolve().parent
OBS = ROOT / "data/observaciones"
CAT = ROOT / "data/catalogos"
DOC = ROOT / "docs/fase1"

NAVY = "#004B87"
BLUE = "#0072CE"
LIGHT = "#E9F4FC"
CYAN = "#198CC7"
ORANGE = "#F39200"
MUTED = "#566779"
GRAY = "#E8EDF2"
MAX_WIDTH = 1320
METRIC_LABELS = {
    "Camas hospitalarias": "Camas hospitalarias / 1.000 habitantes",
    "DTP3": "Cobertura de vacunación DTP3 (%)",
    "Enfermería": "Personal de enfermería / 10.000 habitantes",
    "Escolaridad": "Años promedio de escolaridad",
    "GINI": "Índice de Gini (0–100)",
    "Mortalidad por homicidio": "Tasa ajustada de mortalidad por homicidio / 100.000",
    "Médicos": "Personal médico / 10.000 habitantes",
    "SRP1": "Cobertura de vacunación SRP1 (%)",
}
HAPI_TYPES = {
    "political_violence": "Violencia política",
    "civilian_targeting": "Civiles como objetivo",
    "demonstration": "Manifestaciones",
}
SOURCES = {
    "INFORM Risk": "https://drmkc.jrc.ec.europa.eu/inform-index/INFORM-Risk/Results-and-data",
    "INFORM Severity": "https://drmkc.jrc.ec.europa.eu/inform-index/INFORM-Severity/Results-and-data",
    "OPS": "https://opendata.paho.org/es/indicadores-basicos/descarga-datos",
    "HAPI": "https://hdx-hapi.readthedocs.io/en/latest/data_usage_guides/coordination_and_context/",
    "OIM": "https://dtm.iom.int/es/node/38776",
    "ACNUR": "https://refugeedata.unhcr.org/en/documentation/technical-reference/api/",
    "ReliefWeb": "https://reliefweb.int/updates",
    "AWSD": "https://www.aidworkersecurity.org/",
    "ACAPS": "https://www.acaps.org/en/thematics/all-topics/humanitarian-access-overview",
}

st.set_page_config(
    page_title="Observatorio Humanitario | OPS/OMS",
    page_icon="🌎",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_style()


@st.cache_data(show_spinner=False)
def load_csv(path: str) -> pd.DataFrame:
    file = ROOT / path
    if not file.exists():
        return pd.DataFrame()
    return pd.read_csv(file, dtype={"iso3": str}, encoding="utf-8")


@st.cache_data(show_spinner=False)
def load_json(path: str) -> dict:
    file = ROOT / path
    if not file.exists():
        return {}
    try:
        return json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


countries = load_csv("data/catalogos/paises_americas.csv")
risk = load_csv("data/observaciones/inform_risk_mid_2026.csv")
severity = load_csv("data/observaciones/inform_severity_2026_09_crisis.csv")
ops = load_csv("data/observaciones/ops_8_indicadores_pais_anio.csv")
coverage = load_csv("docs/fase1/cobertura_hapi_oim_americas.csv")
hapi_meta = load_json("docs/fase1/hapi_extraccion_completa.json")
hapi = load_csv("data/observaciones/hapi_conflicto_pais_mes.csv")
hapi_needs = load_csv("data/observaciones/hapi_necesidades_nacional.csv")
hapi_funding = load_csv("data/observaciones/hapi_financiacion_apelaciones.csv")
hapi_inform = load_csv("data/observaciones/hapi_inform_componentes.csv")
hapi_poverty = load_csv("data/observaciones/hapi_pobreza_multidimensional.csv")
hapi_ipc = load_csv("data/observaciones/hapi_seguridad_alimentaria_ipc.csv")
hapi_presence = load_csv("data/observaciones/hapi_presencia_sector.csv")
hapi_presence_meta = load_json("docs/fase2/hapi_presencia_actualizacion.json")
hapi_context_meta = load_json("docs/fase2/hapi_contexto_actualizacion.json")

reliefweb = load_csv("data/observaciones/reliefweb_reportes_americas.csv")
rw_meta = load_json("docs/fase2/reliefweb_actualizacion.json")
security_meta = load_json("docs/fase2/accesos_awsd_reliefweb.json")
warmonit = load_csv("data/observaciones/warmonit_cii_ultimo.csv")
acaps_severity = load_csv("data/observaciones/acaps_severity_americas.csv")
acaps_access = load_csv("data/observaciones/acaps_acceso_americas.csv")
acaps_meta = load_json("docs/fase2/acaps_actualizacion.json")
dtm_latest = load_csv("data/observaciones/oim_dtm_ultima_ronda.csv")
dtm_meta = load_json("docs/fase2/oim_actualizacion.json")

severity_edition = "septiembre 2026 (INFORM Severity, archivo)"


if countries.empty or risk.empty or severity.empty or ops.empty:
    st.error(
        "No se encontraron los archivos principales de datos. "
        "Verifica que se ejecute desde la raíz del repositorio."
    )
    st.stop()

valid_iso = set(countries["iso3"].astype(str))
countries = countries[countries["iso3"].isin(valid_iso)].copy()
risk = risk[risk["iso3"].isin(valid_iso)].copy()
severity = severity[severity["iso3"].isin(valid_iso)].copy()
ops = ops[ops["iso3"].isin(valid_iso)].copy()
risk["puntuacion"] = pd.to_numeric(risk["puntuacion"], errors="coerce")
severity["puntuacion"] = pd.to_numeric(severity["puntuacion"], errors="coerce")
ops["valor"] = pd.to_numeric(ops["valor"], errors="coerce")
ops["periodo"] = pd.to_numeric(ops["periodo"], errors="coerce")
risk = risk.merge(countries[["iso3", "subregion"]], on="iso3", how="left")
severity = severity.merge(countries[["iso3", "subregion"]], on="iso3", how="left")
ops = ops.merge(countries[["iso3", "pais", "subregion"]], on="iso3", how="left")
# Sustituir el corte de septiembre por la edición más reciente descargada
# desde ACAPS, conservando el archivo antiguo como respaldo reproducible.
if not acaps_severity.empty:
    acaps_severity = acaps_severity[
        acaps_severity["iso3"].isin(valid_iso)
    ].copy()
    acaps_severity["puntuacion"] = pd.to_numeric(
        acaps_severity["puntuacion"], errors="coerce"
    )
    acaps_severity = acaps_severity.merge(
        countries[["iso3", "pais", "subregion"]], on="iso3", how="left"
    )
    severity = acaps_severity.copy()
    severity_edition = str(acaps_severity["corte_api"].iloc[0]) + " (ACAPS API)"
if not acaps_access.empty:
    acaps_access = acaps_access[
        acaps_access["iso3"].isin(valid_iso)
    ].copy()
    acaps_access = acaps_access.merge(
        countries[["iso3", "pais", "subregion"]], on="iso3", how="left"
    )

if not coverage.empty:
    coverage = coverage[coverage["iso3"].isin(valid_iso)].copy()

valid_hapi = set()
if hapi_meta:
    valid_hapi = {
        p["iso3"] for p in hapi_meta.get("paises", [])
        if p.get("estado") == "COMPLETO" and p.get("iso3") in valid_iso
    }
if not hapi.empty:
    hapi = hapi[hapi["iso3"].isin(valid_hapi)].copy()
    hapi["eventos"] = pd.to_numeric(hapi["eventos"], errors="coerce")
    hapi["muertes_reportadas"] = pd.to_numeric(
        hapi["muertes_reportadas"], errors="coerce"
    )
    hapi["periodo_dt"] = pd.to_datetime(
        hapi["periodo"].astype(str) + "-01", errors="coerce"
    )
    hapi = hapi.merge(countries[["iso3", "pais", "subregion"]], on="iso3", how="left")

if not reliefweb.empty:
    reliefweb = reliefweb[reliefweb["iso3"].isin(valid_iso)].copy()
    reliefweb = reliefweb.merge(
        countries[["iso3", "pais", "subregion"]], on="iso3", how="left"
    )
    reliefweb["fecha_dt"] = pd.to_datetime(
        reliefweb["fecha_publicacion_rw"], errors="coerce", utc=True
    )
if not warmonit.empty:
    warmonit = warmonit[warmonit["iso3"].isin(valid_iso)].copy()
if not dtm_latest.empty:
    dtm_latest = dtm_latest[dtm_latest["iso3"].isin(valid_iso)].copy()
    dtm_latest["personas_idp_reportadas"]=pd.to_numeric(
        dtm_latest["personas_idp_reportadas"], errors="coerce"
    )
    dtm_latest = dtm_latest.merge(
        countries[["iso3", "pais", "subregion"]], on="iso3", how="left"
    )


for _hapi_data in [hapi_needs,hapi_funding,hapi_inform,hapi_poverty,hapi_ipc,hapi_presence]:
    if not _hapi_data.empty:
        _hapi_data.drop(_hapi_data[
            ~_hapi_data["iso3"].isin(valid_iso)].index,inplace=True)


def section(title: str, index: str, note: str = "") -> None:
    ops_heading(title,index,note)

def describe(source: str, edition: str, caveat: str = "") -> None:
    st.caption(
        f"Fuente: {source}. Edición/corte: {edition}."
        + (f" {caveat}" if caveat else "")
    )


def default_layout(fig: go.Figure, height: int = 440) -> go.Figure:
    # Identidad gráfica propia del Observatorio, no el estilo de El Niño.
    return chart_finish(fig, height=height)


def choropleth(df: pd.DataFrame, metric: str, title: str,
               hover: list[str] | None = None,
               continuous: bool = True) -> go.Figure:
    if continuous:
        fig = px.choropleth(
            df, locations="iso3", color=metric,
            hover_name="pais", hover_data=hover or [],
            color_continuous_scale=[
                [0, "#DEEDF8"], [.38, "#65B5E4"], [.72, "#1779BC"], [1, "#003B6B"]
            ],
            range_color=(0, 10),
            labels={metric: title},
        )
        fig.update_layout(coloraxis_colorbar=dict(title="0–10", len=.77, thickness=13))
    else:
        fig = px.choropleth(
            df, locations="iso3", color=metric, hover_name="pais",
            color_discrete_map={
                "Con registros": BLUE,
                "Sin registros en catálogo": "#CDD7E0",
                "Excluido por QA": ORANGE,
                "Sin verificar": "#E6EDF2",
            },
            category_orders={metric: [
                "Con registros", "Sin registros en catálogo",
                "Excluido por QA", "Sin verificar",
            ]},
        )
    fig.update_geos(
        projection_type="natural earth",
        showframe=False, showcoastlines=False,
        showland=True, landcolor="#F2F6FA",
        showcountries=True, countrycolor="#BBCDDC",
        showocean=True, oceancolor="#F8FBFE",
        lataxis_range=[-60, 84], lonaxis_range=[-170, -29],
    )
    return default_layout(fig, height=520)


def risk_snapshot(subset: pd.DataFrame) -> pd.DataFrame:
    return subset[["iso3", "pais", "subregion", "puntuacion"]].dropna(
        subset=["puntuacion"]
    ).sort_values("puntuacion", ascending=False)


def latest_ops(source: pd.DataFrame, indicator: str) -> pd.DataFrame:
    sub = source[(source["indicador"] == indicator) &
                 source["valor"].notna() &
                 source["periodo"].notna()].copy()
    sub = sub.sort_values(["iso3", "periodo"])
    return sub.drop_duplicates("iso3", keep="last")


with st.sidebar:
    st.markdown("### <span style='color:#003B6B'>OPS / OMS</span>",
                unsafe_allow_html=True)
    st.caption("Health Emergencies · Región de las Américas")
    page = st.radio(
        "Explorar",
        ["Panorama regional", "Conflicto y violencia",
         "Seguridad y acceso", "Necesidades y respuesta",
         "Desplazamiento y movilidad", "Informes y situaciones",
         "Salud y vulnerabilidad", "Perfiles de país",
         "Fuentes y metodología"],
        label_visibility="collapsed",
    )
    st.divider()
    region = st.selectbox(
        "Subregión",
        ["Todas las Américas"] + sorted(countries["subregion"].dropna().unique()),
    )
    sub_countries = (
        countries if region == "Todas las Américas"
        else countries[countries["subregion"] == region]
    )
    selected = set(sub_countries["iso3"])
    st.caption(f"Ámbito geográfico: {len(selected)} de 35 países soberanos.")
    st.divider()
    st.caption("Versión exploratoria de trabajo · 2026")
    if rw_meta.get("fecha_utc"):
        st.caption("ReliefWeb actualizado: "+str(rw_meta["fecha_utc"])[:10])
    if acaps_meta.get("fecha_utc"):
        st.caption("ACAPS actualizado: "+str(acaps_meta["fecha_utc"])[:10])
    if hapi_meta.get("fecha_utc"):
        st.caption("HAPI actualizado: "+str(hapi_meta["fecha_utc"])[:10])
    st.caption("No constituye una clasificación oficial de prioridades de OPS.")

ops_header()
st.caption("Prototipo de análisis con fuentes institucionales. Los indicadores mantienen cortes y denominadores separados; no es una clasificación oficial de prioridades OPS.")

if page == "Panorama regional":
    section("Situación regional", "01",
            "Panorama comparativo de riesgo estructural y crisis registradas; "
            "no equivale a un índice compuesto de amenaza humanitaria.")
    rc = risk_snapshot(risk[risk["iso3"].isin(selected)])
    sc = severity[severity["iso3"].isin(selected)]
    a,b,c,d = st.columns(4)
    a.metric("Países en el análisis", f"{len(selected)}/35")
    b.metric("INFORM Risk", f"{len(rc)}/{len(selected)}")
    c.metric("Países con crisis INFORM Severity", f"{sc['iso3'].nunique()}")
    d.metric("Crisis individuales registradas", f"{len(sc)}")
    if not reliefweb.empty or not acaps_access.empty:
        with st.expander("Cobertura de otras fuentes humanitarias", expanded=False):
            q1,q2,q3=st.columns(3)
            q1.metric("Reportes ReliefWeb · 90 días",
                int(reliefweb[reliefweb["iso3"].isin(selected)]["reporte_id"].nunique())
                if not reliefweb.empty else "Sin datos")
            q2.metric("Países con acceso ACAPS",
                int(acaps_access[acaps_access["iso3"].isin(selected)]["iso3"].nunique())
                if not acaps_access.empty else "Sin datos")
            q3.metric("Series de conflicto HAPI validadas",
                len(valid_hapi.intersection(selected)))
            st.caption("Unidades diferentes: no se suman ni constituyen un índice.")
    st.markdown('<div class="section-line"></div>', unsafe_allow_html=True)
    col1,col2=st.columns([1.45,1],gap="large")
    with col1:
        st.markdown("#### Riesgo estructural por país")
        map_countries(rc,"puntuacion","INFORM Risk",legend_title="INFORM Risk · escala 0–10")
    with col2:
        st.markdown("#### Países con mayor puntuación INFORM Risk")
        fig = rank_bars(rc, label="pais",value="puntuacion",
                        limit=12,color=BLUE,units="INFORM Risk / 10",max_x=10.8)
        st.plotly_chart(fig,use_container_width=True,
                        config={"displayModeBar":False})
    describe("INFORM Risk, Centro Común de Investigación (JRC/Comisión Europea)",
             "Mid 2026","Índice estructural multiamenaza, no únicamente conflicto.")

    section("Crisis documentadas", "02",
            "INFORM Severity evalúa cada crisis por separado; "
            "un país puede aparecer varias veces.")
    if sc.empty:
        st.info("No hay crisis registradas en este corte de INFORM Severity "
                "para los países seleccionados. No significa ausencia de crisis.")
    else:
        col1,col2=st.columns([1,1.2],gap="large")
        with col1:
            summaries=(sc.groupby(["pais","iso3"],as_index=False)
                       .agg(crisis=("crisis_id","nunique"),
                            puntuacion_maxima=("puntuacion","max"))
                       .sort_values("puntuacion_maxima",ascending=False))
            st.markdown("#### Máxima gravedad entre crisis registradas")
            fig=rank_bars(summaries,label="pais",value="puntuacion_maxima",
                          limit=12,color=ORANGE,units="Gravedad / 10",max_x=10.8)
            st.plotly_chart(fig,use_container_width=True,
                            config={"displayModeBar":False})
            st.caption("El máximo es solo un resumen visual; NO suma ni constituye "
                       "una puntuación general del país.")
        with col2:
            st.markdown("#### Detalle de crisis")
            tab=sc.sort_values("puntuacion",ascending=False)[
                ["pais","crisis","puntuacion","crisis_id"]
            ].rename(columns={"pais":"País","crisis":"Crisis",
                               "puntuacion":"Severity (0–10)",
                               "crisis_id":"Código"})
            st.dataframe(tab,use_container_width=True,hide_index=True,height=420)
            st.download_button(
                "Descargar crisis filtradas (CSV)",
                tab.to_csv(index=False).encode("utf-8-sig"),
                "inform_severity_crisis.csv","text/csv",
            )
    describe("INFORM Severity / ACAPS",severity_edition,
             "Corte de crisis específicas, no cobertura exhaustiva de cualquier emergencia.")

elif page == "Conflicto y violencia":
    section("Conflicto y violencia política", "03",
            "HDX HAPI redistribuye datos mensuales agregados de ACLED. "
            "Nunca se combinan sus tres categorías, porque no son excluyentes.")
    if hapi.empty:
        st.warning(
            "La extracción HAPI de los 35 países todavía no cuenta con un archivo "
            "mensual completo y validado. Por rigor metodológico, el dashboard "
            "no muestra conteos ni tendencias parciales."
        )
        if not coverage.empty:
            r=coverage[(coverage["fuente"]=="HAPI conflicto 2020+") &
                       coverage["iso3"].isin(selected)]
            st.dataframe(
                r[["pais","estado","filas_consultadas","periodo_desde",
                   "periodo_hasta"]].rename(columns={
                    "pais":"País","estado":"Estado de extracción",
                    "filas_consultadas":"Filas revisadas",
                    "periodo_desde":"Primer periodo","periodo_hasta":"Último periodo"}),
                use_container_width=True,hide_index=True,
            )
    else:
        complete=[c for c in sub_countries["iso3"] if c in valid_hapi]
        a,b,c=st.columns(3)
        a.metric("Países con extracción íntegra",f"{len(complete)}/{len(selected)}")
        b.metric("Categorías disponibles",hapi["tipo_evento"].nunique())
        c.metric("Último mes disponible",
                 str(hapi["periodo"].max()) if not hapi.empty else "—")
        if len(complete)<len(selected):
            st.warning(
                "Hay países excluidos por controles de integridad. "
                "No se muestran totales de toda la región con países faltantes."
            )
        st.markdown("#### Evolución regional por categoría")
        regional=hapi[hapi["iso3"].isin(selected)].copy()
        if not regional.empty:
            group=st.selectbox(
                "Categoría regional HAPI",
                list(HAPI_TYPES),
                format_func=lambda x:HAPI_TYPES[x],
                key="hapi_region_category")
            region_type=regional[regional["tipo_evento"]==group].copy()
            region_type=region_type.dropna(subset=["periodo_dt"])
            if not region_type.empty:
                meses=sorted(region_type["periodo_dt"].unique())
                start=meses[max(0,len(meses)-24)]
                region_type=region_type[region_type["periodo_dt"]>=start]
                weekly=(region_type.groupby("periodo_dt",as_index=False)
                    .agg(eventos=("eventos","sum"),
                         paises_con_registros=("iso3","nunique")))
                top=region_type.groupby(["iso3","pais"],as_index=False)[
                    "eventos"].sum().sort_values("eventos",ascending=False).head(12)
                c1,c2=st.columns([1.25,1],gap="large")
                with c1:
                    fig=trend(weekly,x="periodo_dt",y="eventos",
                              units="Eventos reportados",area=True)
                    st.plotly_chart(fig,use_container_width=True,
                                    config={"displayModeBar":False})
                with c2:
                    fig=rank_bars(top,label="pais",value="eventos",limit=12,
                         color=BLUE,units="Eventos",formats=".0f")
                    st.plotly_chart(fig,use_container_width=True,
                                    config={"displayModeBar":False})
                st.caption("Se muestran los últimos 24 meses disponibles por "
                    "categoría. La suma regional corresponde a los países con "
                    "registros del mes; no significa cobertura exhaustiva de "
                    "todos los hechos ocurridos. No se suman categorías superpuestas.")
        choices=[(c["iso3"],c["pais"]) for _,c in sub_countries.iterrows()
                 if c["iso3"] in valid_hapi and c["iso3"] in set(hapi["iso3"])]
        if choices:
            iso=st.selectbox("País",choices,format_func=lambda t:t[1],
                             key="hapi_country")[0]
            label=st.selectbox(
                "Categoría de eventos",list(HAPI_TYPES),
                format_func=lambda s:HAPI_TYPES[s],
            )
            variable=st.radio(
                "Variable",["eventos"] if label=="demonstration"
                else ["eventos","muertes_reportadas"],horizontal=True,
                format_func=lambda s: "Eventos reportados" if s=="eventos"
                else "Muertes reportadas",
            )
            if label=="demonstration":
                st.caption("HAPI no comunica muertes para manifestaciones en esta serie; "
                           "un valor no informado no se interpreta como cero.")
            series=hapi[(hapi["iso3"]==iso)&
                        (hapi["tipo_evento"]==label)].sort_values("periodo_dt")
            if not series.empty:
                fig=trend(series,x="periodo_dt",y=variable,
                          units="Eventos" if variable=="eventos" else "Muertes reportadas")
                st.plotly_chart(fig,use_container_width=True,
                                config={"displayModeBar":False})
                st.caption("Cifras HAPI/ACLED agregadas por mes y tipo. "
                           "Se verificó la paginación de este país, pero "
                           "la cobertura del proveedor puede variar temporal "
                           "y territorialmente. No representan un censo de todos "
                           "los hechos violentos.")
                display=series[["periodo","eventos","muertes_reportadas"]]
                st.download_button(
                    "Descargar la serie seleccionada",
                    display.to_csv(index=False).encode("utf-8-sig"),
                    f"hapi_{iso}_{label}.csv","text/csv",
                )
        else:
            st.info("No hay una serie aprobada en este ámbito. "
                    "Revisa la validación de extracción.")
    st.markdown(
        "Referencia técnica: [HDX HAPI / Conflict Events]"
        f"({SOURCES['HAPI']}). "
        "Para eventos diarios o actores se requiere autorización "
        "directa de ACLED."
    )
    with st.expander("¿Por qué no sumamos las categorías de ACLED?"):
        st.markdown(
            "Un mismo hecho violento puede pertenecer tanto a **violencia política** "
            "como a **civiles como objetivo**. Por eso una suma de los tres tipos "
            "sobrestimaría el total. Las tendencias y cifras se analizan "
            "**por categoría independiente**."
        )

elif page == "Seguridad y acceso":
    access_page(acaps_access,acaps_severity,security_meta,
                countries,selected,acaps_meta)

elif page == "Necesidades y respuesta":
    render_hapi(hapi_needs,hapi_funding,hapi_inform,
                hapi_poverty,hapi_ipc,hapi_presence,
                countries,selected,hapi_context_meta)

elif page == "Desplazamiento y movilidad":
    section("Desplazamiento y movilidad humana", "04",
            "Mapa de disponibilidad de OIM DTM Baseline. La información agregada "
            "tiene diferentes rondas de levantamiento y años.")
    if coverage.empty:
        st.info("No se encontró la matriz regional de OIM DTM.")
    else:
        dtm=coverage[(coverage["fuente"]=="OIM DTM Baseline")&
                     (coverage["iso3"].isin(selected))].copy()
        dtm["Disponibilidad"] = dtm["estado"].map({
            "registros_verificados":"Con registros",
            "sin_registros_catalogo":"Sin registros en catálogo",
            "error_consulta_admin0":"Sin verificar",
            "sin_credencial":"Sin verificar",
        }).fillna("Sin verificar")
        dm=sub_countries.merge(
            dtm[["iso3","Disponibilidad","filas_consultadas",
                 "periodo_desde","periodo_hasta","estado"]],
            on="iso3",how="left",
        )
        dm["Disponibilidad"]=dm["Disponibilidad"].fillna("Sin verificar")
        a,b,c=st.columns(3)
        a.metric("Países evaluados",f"{len(dtm)}/{len(selected)}")
        b.metric("Con registros nacionales",
                 f"{sum(dtm['Disponibilidad']=='Con registros')}")
        c.metric("Sin registros en catálogo",
                 f"{sum(dtm['Disponibilidad']=='Sin registros en catálogo')}")
        col1,col2=st.columns([1.45,1],gap="large")
        with col1:
            st.markdown("#### Disponibilidad de datos OIM DTM")
            map_countries(dm,"Disponibilidad","Cobertura",categorical=True)
        with col2:
            st.markdown("#### Cobertura por subregión")
            counts=(dm.groupby(["subregion","Disponibilidad"],as_index=False)
                    .size().rename(columns={"size":"Países"}))
            fig=px.bar(
                counts,x="Países",y="subregion",orientation="h",
                color="Disponibilidad",
                color_discrete_map={"Con registros":BLUE,
                                    "Sin registros en catálogo":"#CDD7E0",
                                    "Sin verificar":ORANGE},
                labels={"subregion":"","Países":"Número de países"},
                barmode="stack",
            )
            st.plotly_chart(default_layout(fig,420),
                            use_container_width=True,
                            config={"displayModeBar":False})
        st.caption(
            "OIM DTM proporciona cifras agregadas según operaciones, rondas y "
            "áreas administrativas. No sumamos diferentes rondas como "
            "si fueran desplazamientos nuevos o personas únicas."
        )
        st.markdown("#### Cobertura detallada")
        table=dm[["pais","subregion","Disponibilidad","filas_consultadas",
                  "periodo_desde","periodo_hasta"]].rename(columns={
            "pais":"País","subregion":"Subregión",
            "filas_consultadas":"Registros nacionales",
            "periodo_desde":"Primer periodo","periodo_hasta":"Último periodo",
        })
        st.dataframe(table,use_container_width=True,hide_index=True)
        st.download_button(
            "Descargar cobertura DTM",
            table.to_csv(index=False).encode("utf-8-sig"),
            "cobertura_oim_dtm_americas.csv","text/csv",
        )
    if not dtm_latest.empty:
        st.divider()
        st.markdown("#### Cifras por última ronda de operación · OIM DTM")
        st.caption("Se muestra la **última fecha y ronda por operación**. "
            "Cada fila conserva su origen geográfico y población reportada; "
            "no se suman operaciones ni rondas como si fueran personas únicas.")
        filtered=dtm_latest[dtm_latest["iso3"].isin(selected)].copy()
        if filtered.empty:
            st.info("No se dispone de rondas DTM en los países del filtro.")
        else:
            co=st.selectbox("País con datos de rondas",
                sorted(filtered["iso3"].unique()),
                format_func=lambda iso:
                    countries.set_index("iso3").loc[iso,"pais"],
                key="dtm_pais")
            current=filtered[filtered["iso3"]==co].copy()
            operation=st.selectbox("Operación o emergencia",
                sorted(current["operacion"].dropna().unique()),
                key="dtm_operacion")
            current=current[current["operacion"]==operation]
            a,b,c=st.columns(3)
            a.metric("Registros última ronda",len(current))
            b.metric("Ronda reportada",
                str(current["ronda"].iloc[0]) if len(current) else "—")
            c.metric("Fecha reportada",
                str(current["fecha_reporte"].max()) if len(current) else "—")
            tabla=current[["fecha_reporte","ronda","causa_desplazamiento",
                "tipo_evaluacion","origen_admin1","personas_idp_reportadas",
                "hombres","mujeres"]].rename(columns={
                  "fecha_reporte":"Fecha","ronda":"Ronda",
                  "causa_desplazamiento":"Causa",
                  "tipo_evaluacion":"Tipo de evaluación",
                  "origen_admin1":"Origen declarado",
                  "personas_idp_reportadas":"Población IDP reportada",
                  "hombres":"Hombres","mujeres":"Mujeres"})
            st.dataframe(tabla,use_container_width=True,hide_index=True)
            st.download_button("Descargar registros de la operación",
                tabla.to_csv(index=False).encode("utf-8-sig"),
                f"dtm_{co}_ultima_ronda.csv","text/csv")
            st.caption("El periodo y los conteos son propios de esta operación. "
                "El usuario no debe sumar orígenes o sexo cuando existan "
                "categorías solapadas o faltantes.")
    st.divider()
    st.markdown("#### Otras fuentes de movilidad humana")
    st.info(
        "ACNUR permite consultar refugiados, solicitantes de asilo y "
        "otras poblaciones desplazadas. La integración numérica "
        "para los 35 países aún requiere una extracción completa, "
        "homologación de país de origen frente a país de asilo "
        "y revisión de la licencia de uso. No presentamos cifras "
        "de una prueba piloto parcial."
    )
    st.markdown(f"[API oficial ACNUR]({SOURCES['ACNUR']}) · "
                f"[OIM DTM]({SOURCES['OIM']})")
    if not coverage.empty:
        hna=coverage[(coverage["fuente"]=="OIM DTM HNA")&
                     (coverage["iso3"].isin(selected))]
        st.caption(
            f"OIM DTM Humanitarian Needs Assessment: "
            f"{sum(hna['estado']=='catalogo_verificado')} países con registros "
            "en el catálogo consultado. Sin registros no significa "
            "sin necesidades humanitarias."
        )

elif page == "Informes y situaciones":
    reports_page(reliefweb,rw_meta,countries,selected)

elif page == "Salud y vulnerabilidad":
    section("Salud y vulnerabilidad", "05",
            "Indicadores básicos OPS: períodos y unidades heterogéneos. "
            "Se muestran valores observados, sin interpolar ni imputar.")
    valid=sorted(ops["indicador"].dropna().unique())
    indicator=st.selectbox(
        "Indicador OPS",valid,
        format_func=lambda s:METRIC_LABELS.get(s,s),
    )
    latest=latest_ops(ops[ops["iso3"].isin(selected)],indicator)
    years=sorted(
        ops[ops["indicador"]==indicator]["periodo"].dropna().astype(int).unique()
    )
    restrict=st.checkbox("Comparar exclusivamente observaciones del mismo año",
                         value=False)
    if restrict:
        year=st.select_slider("Año",options=years,value=years[-1])
        latest=ops[(ops["iso3"].isin(selected)) &
                   (ops["indicador"]==indicator) &
                   (ops["periodo"]==year)].dropna(subset=["valor"]).copy()
    a,b,c=st.columns(3)
    a.metric("Países con valor",f"{latest['iso3'].nunique()}/{len(selected)}")
    b.metric("Año más reciente disponible",
             f"{int(latest['periodo'].max())}" if not latest.empty else "—")
    c.metric("Año más antiguo en comparación",
             f"{int(latest['periodo'].min())}" if not latest.empty else "—")
    if latest.empty:
        st.info("No hay observaciones para estos filtros.")
    else:
        plot=latest.sort_values("valor",ascending=False)
        fig=strip_countries(plot,name="pais",val="valor",
            year="periodo",max_items=25,units=METRIC_LABELS.get(indicator,indicator))
        st.plotly_chart(fig,use_container_width=True,
                        config={"displayModeBar":False})
        st.caption("Gráfico horizontal de hasta 25 países; tabla completa debajo. "
                   "El año correspondiente aparece al pasar el cursor sobre cada punto.")
        if not restrict:
            st.warning(
                "Se seleccionó el último valor observado en cada país. "
                "Los años pueden ser diferentes: compara magnitudes "
                "con cautela. Activa el filtro de año común para "
                "realizar comparaciones temporalmente consistentes."
            )
        st.markdown("#### Evolución temporal")
        options=latest["iso3"].tolist()
        n=st.selectbox(
            "País para ver la serie histórica",options,
            format_func=lambda iso: countries.set_index("iso3").loc[iso,"pais"],
        )
        series=ops[(ops["iso3"]==n)&(ops["indicador"]==indicator)].dropna(
            subset=["valor","periodo"]).sort_values("periodo")
        series=series.copy()
        series["periodo_dt"]=pd.to_datetime(
             series["periodo"].astype(int).astype(str)+"-01-01",errors="coerce")
        f2=trend(series,x="periodo_dt",y="valor",
              units=METRIC_LABELS.get(indicator,indicator),area=False)
        st.plotly_chart(f2,use_container_width=True,
                        config={"displayModeBar":False})
        tab=plot[["pais","periodo","valor","etiqueta_fuente"]].rename(
            columns={"pais":"País","periodo":"Año",
                     "valor":"Valor","etiqueta_fuente":"Definición en la fuente"})
        st.dataframe(tab,use_container_width=True,hide_index=True)
        st.download_button(
            "Descargar los valores filtrados",
            tab.to_csv(index=False).encode("utf-8-sig"),
            "indicador_ops.csv","text/csv",
        )
    describe("OPS/OMS, Indicadores Básicos","descarga octubre de 2026",
             "Los indicadores son descriptivos; no determinan riesgo humanitario.")

elif page == "Perfiles de país":
    section("Perfiles nacionales", "06",
            "Ficha descriptiva; las fechas de referencia varían por fuente.")
    options=list(sub_countries["iso3"])
    iso=st.selectbox(
        "Selecciona un país",options,
        format_func=lambda s:countries.set_index("iso3").loc[s,"pais"],
    )
    country=countries.set_index("iso3").loc[iso]
    r=risk[risk["iso3"]==iso]
    s=severity[severity["iso3"]==iso]
    h=hapi[hapi["iso3"]==iso] if not hapi.empty else pd.DataFrame()
    dtm=coverage[(coverage["iso3"]==iso)&
                 (coverage["fuente"]=="OIM DTM Baseline")] if not coverage.empty else pd.DataFrame()
    a,b,c,d=st.columns(4)
    a.metric("INFORM Risk 2026",
             f"{float(r['puntuacion'].iloc[0]):.1f} / 10" if len(r) else "N/D")
    b.metric("Crisis INFORM Severity",f"{len(s)}")
    c.metric("Serie HAPI",
             "Verificada" if iso in valid_hapi and not h.empty else "No disponible")
    d.metric("OIM DTM",
             "Con registros" if not dtm.empty and
             dtm.iloc[0]["estado"]=="registros_verificados" else "No disponible")
    cl1,cl2=st.columns([1,1],gap="large")
    with cl1:
        st.markdown("#### Riesgo y crisis")
        if s.empty:
            st.info("El país no figura en este corte de INFORM Severity. "
                    "No implica ausencia de crisis.")
        else:
            tab=s[["crisis","puntuacion","crisis_id"]].sort_values(
                "puntuacion",ascending=False)
            st.dataframe(
                tab.rename(columns={"crisis":"Crisis",
                                    "puntuacion":"Severity (0–10)",
                                    "crisis_id":"ID"}),
                hide_index=True,use_container_width=True,height=300,
            )
        if not h.empty:
            st.markdown("#### Violencia política (HAPI)")
            event=h[h["tipo_evento"]=="political_violence"].sort_values("periodo_dt")
            if not event.empty:
                fig=trend(event,x="periodo_dt",y="eventos",units="Eventos")
                st.plotly_chart(fig,use_container_width=True,
                                config={"displayModeBar":False})
    with cl2:
        st.markdown("#### Últimos indicadores de salud disponibles")
        available=ops[ops["iso3"]==iso]
        last=(available.dropna(subset=["valor","periodo"])
              .sort_values("periodo").drop_duplicates("indicador",keep="last"))
        last=last[["indicador","periodo","valor"]].copy()
        last["indicador"]=last["indicador"].map(
            lambda k:METRIC_LABELS.get(k,k)
        )
        last=last.rename(columns={"indicador":"Indicador",
                                  "periodo":"Año","valor":"Valor"})
        st.dataframe(last,use_container_width=True,hide_index=True,height=340)
        st.caption("No todos los indicadores tienen el mismo año de reporte.")
    if not acaps_access.empty:
        ca=acaps_access[acaps_access["iso3"]==iso].copy()
        if not ca.empty:
            st.markdown("#### Restricciones al acceso humanitario (ACAPS)")
            st.dataframe(ca[["crisis","acceso","pilar_1","pilar_2","pilar_3","brecha_info"]].rename(
                columns={"crisis":"Crisis","acceso":"Índice acceso (0–5)",
                         "pilar_1":"Acceso población",
                         "pilar_2":"Acceso organizaciones",
                         "pilar_3":"Obstáculos físicos / seguridad",
                         "brecha_info":"Brecha de información"}),
                use_container_width=True,hide_index=True,height=225)
            st.caption("Indicadores de crisis separadas; no se suman ni constituyen prioridad OPS.")
    if not dtm_latest.empty:
        op=dtm_latest[dtm_latest["iso3"]==iso].copy()
        if not op.empty:
            st.markdown("#### Operaciones OIM DTM disponibles (última ronda)")
            st.dataframe(op[["operacion","fecha_reporte","ronda",
                "origen_admin1","personas_idp_reportadas"]].rename(columns={
                "operacion":"Operación","fecha_reporte":"Fecha",
                "ronda":"Ronda","origen_admin1":"Origen",
                "personas_idp_reportadas":"Población IDP reportada"}),
                use_container_width=True,hide_index=True,height=215)
            st.caption("Los registros no se agregan entre operaciones ni orígenes.")
    if not reliefweb.empty:
        docs=reliefweb[reliefweb["iso3"]==iso].copy()
        if not docs.empty:
            st.markdown("#### Informes recientes asociados al país")
            docs=docs.drop_duplicates("reporte_id").sort_values("fecha_dt",ascending=False).head(8)
            docs["Fecha"]=docs["fecha_publicacion_rw"].astype(str).str[:10]
            st.dataframe(docs[["Fecha","titulo","fuentes","url"]].rename(
                columns={"titulo":"Informe","fuentes":"Organización","url":"Enlace"}),
                use_container_width=True,hide_index=True,height=260,
                column_config={"Enlace":st.column_config.LinkColumn(
                    "Abrir informe",display_text="Abrir"),
                    "Informe":st.column_config.TextColumn("Informe",width="large")})
    st.markdown("#### Estado de fuentes disponibles")
    if not coverage.empty:
        info=coverage[coverage["iso3"]==iso].copy()
        st.dataframe(info[["fuente","estado","periodo_desde",
                           "periodo_hasta"]].rename(columns={
            "fuente":"Fuente","estado":"Estado",
            "periodo_desde":"Desde","periodo_hasta":"Hasta"}),
            hide_index=True,use_container_width=True,
        )
    st.caption(
        "Perfil descriptivo por país. No se calculó índice sintético, "
        "clasificación oficial ni tendencia atribuible a una intervención."
    )

elif page == "Fuentes y metodología":
    section("Fuentes, integridad y metodología", "07",
            "Transparencia de trazabilidad, fecha y controles de integridad.")
    source_rows=[
        ("INFORM Risk","Mid 2026","35 países",
         "Riesgo estructural multiamenaza; no exclusivamente violencia.",
         SOURCES["INFORM Risk"]),
        ("INFORM Severity",""+severity_edition,"25 crisis / 16 países",
         "Evaluación por crisis; varias crisis pueden corresponder al mismo país.",
         SOURCES["INFORM Severity"]),
        ("OPS Indicadores Básicos","Descarga octubre 2026","3.038 observaciones",
         "8 indicadores; unidades y años diferentes.",SOURCES["OPS"]),
        ("HDX HAPI / ACLED agregado","Según HAPI","35 países evaluados",
         "Se publican solo series completas que superan QA; categorías solapadas.",
         SOURCES["HAPI"]),
        ("OIM DTM Baseline","Según operación","12 países con datos",
         "Rondas y fechas no comparables sin homologación.",
         SOURCES["OIM"]),
        ("OIM DTM HNA","Catálogo consultado noviembre 2026","0 países americanos",
         "Ausencia de catálogo no significa ausencia de necesidades.",
         SOURCES["OIM"]),
        ("ReliefWeb", "90 días – consulta semanal",
         f"{rw_meta.get('reportes_unicos','—')} reportes únicos",
         "Documentos y metadatos; un reporte puede cubrir varios países.",
         SOURCES["ReliefWeb"]),
        ("ACAPS acceso", str(acaps_meta.get('datasets',{}).get('access',{}).get('corte_api','—')),
         f"{acaps_meta.get('datasets',{}).get('access',{}).get('paises_americas','—')} países",
         "Indicadores por contexto y crisis; categorías no agregables.",
         SOURCES["ACAPS"]),
        ("AWSD", "Clave recibida", "Por validar",
         "No publicar indicadores hasta autenticar el endpoint JSON.",
         SOURCES["AWSD"]),
        ("ACNUR","Por integrar","Piloto de conectividad anterior",
         "Exige armonizar país de origen y país de asilo.",
         SOURCES["ACNUR"]),
    ]
    source_table=pd.DataFrame(
        source_rows,columns=["Fuente","Corte","Disponibilidad",
                             "Consideración metodológica","Enlace"]
    )
    st.dataframe(
        source_table,use_container_width=True,hide_index=True,
        column_config={"Enlace":st.column_config.LinkColumn("Documentación")},
    )
    st.markdown("#### Controles de calidad")
    for t in [
        "35 países soberanos y códigos ISO3 únicos como universo territorial.",
        "Sin imputaciones de cero para países o periodos sin información.",
        "Sin extrapolar datos subnacionales parciales a resultados nacionales.",
        "HAPI: consulta paginada completa por país, controles de tipos, fechas y geografía.",
        "Sin sumar categorías superpuestas de conflicto; sin mezclar crisis diferentes.",
        "OPS: no comparar distintos años sin advertir la heterogeneidad temporal.",
        "Ni ACLED detallado ni ReliefWeb se usan hasta contar con autorización.",
    ]:
        st.markdown("✓ "+t)
    st.markdown("#### Integridad regional HAPI")
    if hapi_meta:
        st.json(
            {k:hapi_meta.get(k) for k in
             ["fecha_utc","paises_esperados","paises_completos",
              "paises_excluidos","filas_mensuales_publicadas"]},
            expanded=False,
        )
    else:
        st.info("Aún no está publicado el informe final de extracción HAPI.")
    st.markdown(
        "Consulta el [repositorio y metodología]"
        "(https://github.com/ivanromero0724/observatorio-humanitario-ops) "
        "para reproducibilidad y control de versiones."
    )


ops_footer()
