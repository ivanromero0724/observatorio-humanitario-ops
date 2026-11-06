"""Observatorio Humanitario OPS/OMS · navegación guiada por la propuesta técnica.

Cinco páginas analíticas (propuesta 05/11/2026). La unidad conceptual es
amenaza → vulnerabilidad → impacto → respuesta, no la lista de APIs.
Laura/equipo PHE validarán taxonomía, criterios y prioridades: no se asigna
ninguna categoría operativa OPS automáticamente.

Cada figura/mapa usa st.container(border=True); datos y QA siguen accesibles
en los snapshots versionados del repositorio. No se realiza ninguna llamada
externa desde Streamlit ni se requieren secretos en la app.
"""
from __future__ import annotations

import html
import json
from contextlib import contextmanager
from pathlib import Path

import pandas as pd
import streamlit as st

from ui_ops import (
    apply_style, header as ops_header, footer as ops_footer,
    map_countries, BLUE, ORANGE,
)
from graficos import rank_bars, trend, strip_countries

ROOT=Path(__file__).resolve().parent
PAGES=[
    "Panorama regional",
    "Amenazas y eventos",
    "Vulnerabilidad y respuesta",
    "Impacto humanitario y salud",
    "Perfiles por país",
]
HAPI_TYPES={
    "political_violence":"Violencia política",
    "civilian_targeting":"Ataques contra civiles",
    "demonstration":"Manifestaciones",
}
OPS_LABELS={
    "GINI":"Índice de Gini (0–100)",
    "Escolaridad":"Años promedio de escolaridad",
    "Mortalidad por homicidio":"Mortalidad por homicidios / 100.000",
    "Médicos":"Médicos / 10.000 habitantes",
    "Enfermería":"Personal de enfermería / 10.000 habitantes",
    "Camas hospitalarias":"Camas hospitalarias / 1.000 habitantes",
    "DTP3":"Vacunación DTP3 (%)",
    "SRP1":"Vacunación SRP1 (%)",
}
URLS={
    "HAPI":"https://hapi.humdata.org/docs",
    "ACAPS":"https://www.acaps.org/en/data",
    "INFORM":"https://drmkc.jrc.ec.europa.eu/inform-index",
    "OPS":"https://opendata.paho.org/es/indicadores-basicos/descarga-datos",
    "OIM":"https://dtm.iom.int/",
    "ACNUR":"https://refugeedata.unhcr.org/",
    "ReliefWeb":"https://reliefweb.int/updates",
    "SSA":"https://extranet.who.int/ssa/index.aspx",
}
SOURCES={
    "risk":"data/observaciones/inform_risk_mid_2026.csv",
    "severity":"data/observaciones/acaps_severity_americas.csv",
    "access":"data/observaciones/acaps_acceso_americas.csv",
    "conflict":"data/observaciones/hapi_conflicto_pais_mes.csv",
    "ops":"data/observaciones/ops_8_indicadores_pais_anio.csv",
    "needs":"data/observaciones/hapi_necesidades_nacional.csv",
    "acnur":"data/observaciones/hapi_acnur_acogida.csv",
    "dtm":"data/observaciones/oim_dtm_ultima_ronda.csv",
    "mpi":"data/observaciones/hapi_pobreza_multidimensional.csv",
    "funding":"data/observaciones/hapi_financiacion_apelaciones.csv",
    "presence":"data/observaciones/hapi_presencia_sector.csv",
    "ipc":"data/observaciones/hapi_seguridad_alimentaria_ipc.csv",
    "reports":"data/observaciones/reliefweb_reportes_americas.csv",
}
META={
    "acaps":"docs/fase2/acaps_actualizacion.json",
    "hapi":"docs/fase1/hapi_extraccion_completa.json",
    "hapi_context":"docs/fase2/hapi_contexto_actualizacion.json",
    "acnur":"docs/fase2/hapi_acnur_actualizacion.json",
    "dtm":"docs/fase2/oim_actualizacion.json",
    "reports":"docs/fase2/reliefweb_actualizacion.json",
    "presence":"docs/fase2/hapi_presencia_actualizacion.json",
    "security":"docs/fase2/accesos_awsd_reliefweb.json",
}

@st.cache_data(show_spinner=False)
def csv(path:str)->pd.DataFrame:
    file=ROOT/path
    if not file.is_file():
        return pd.DataFrame()
    return pd.read_csv(file,encoding="utf-8",low_memory=False,
                       dtype={"iso3":"str","asilo_iso3":"str","origen_iso3":"str"})

@st.cache_data(show_spinner=False)
def json_file(path:str)->dict:
    file=ROOT/path
    if not file.is_file():return {}
    try:return json.loads(file.read_text(encoding="utf-8"))
    except (ValueError,OSError):return {}

@st.cache_data(show_spinner=False)
def load_all()->dict:
    countries=csv("data/catalogos/paises_americas.csv")
    if countries.empty or "iso3" not in countries:
        return {"countries":pd.DataFrame()}
    data={"countries":countries}
    iso=set(countries["iso3"])
    labels=countries.set_index("iso3")["pais"].to_dict()
    for key,path in SOURCES.items():
        df=csv(path).copy()
        if not df.empty:
            country_col="asilo_iso3" if key=="acnur" else "iso3"
            if country_col in df:
                df=df[df[country_col].isin(iso)].copy()
                df["pais"]=df[country_col].map(labels)
            if key=="conflict":
                df["eventos"]=pd.to_numeric(df["eventos"],errors="coerce")
                df["muertes_reportadas"]=pd.to_numeric(df["muertes_reportadas"],errors="coerce")
                df["fecha"]=pd.to_datetime(df["periodo"]+"-01",errors="coerce")
                df=df[df["iso3"].isin({
                    p["iso3"] for p in json_file(META["hapi"]).get("paises",[])
                    if p.get("estado")=="COMPLETO"
                })]
            elif key in ("severity","risk"):
                df["puntuacion"]=pd.to_numeric(df["puntuacion"],errors="coerce")
            elif key=="access":
                for col in ("acceso","pilar_1","pilar_2","pilar_3"):
                    df[col]=pd.to_numeric(df[col],errors="coerce")
            elif key=="ops":
                df["valor"]=pd.to_numeric(df["valor"],errors="coerce")
                df["periodo"]=pd.to_numeric(df["periodo"],errors="coerce")
            elif key=="acnur":
                df["personas"]=pd.to_numeric(df["personas"],errors="coerce")
            elif key=="reports":
                df["fecha"]=pd.to_datetime(df["fecha_publicacion_rw"],
                                           errors="coerce",utc=True)
            elif key=="dtm":
                df["personas_idp_reportadas"]=pd.to_numeric(
                    df["personas_idp_reportadas"],errors="coerce")
            elif key=="needs":
                df["population"]=pd.to_numeric(df["population"],errors="coerce")
            elif key=="mpi":
                for col in ("mpi","headcount_ratio","intensity_of_deprivation"):
                    df[col]=pd.to_numeric(df[col],errors="coerce")
            elif key=="funding":
                for col in ("funding_usd","requirements_usd","funding_pct"):
                    df[col]=pd.to_numeric(df[col],errors="coerce")
            elif key=="presence":
                df["organizaciones_distintas"]=pd.to_numeric(
                    df["organizaciones_distintas"],errors="coerce")
            elif key=="ipc":
                df["population_in_phase"]=pd.to_numeric(
                    df["population_in_phase"],errors="coerce")
        data[key]=df
    for k,v in META.items():
        data[k+"_meta"]=json_file(v)
    return data

@contextmanager
def panel(title:str,subtitle:str="",source:str=""):
    """Contenedor visual único: borde gris, radius y título azul."""
    with st.container(border=True):
        st.markdown(
            '<div class="obs-panel-title">'+html.escape(title)+'</div>',
            unsafe_allow_html=True,
        )
        if subtitle:st.caption(subtitle)
        yield
        if source:st.caption("Fuente: "+source)

def plot(fig):
    st.plotly_chart(fig,use_container_width=True,
        config={"displayModeBar":False,"responsive":True})

def section(idx:str,title:str,question:str):
    st.markdown('<div class="obs-kicker">'+html.escape(idx)+" / OBSERVATORIO REGIONAL</div>"
                '<div class="obs-section-title">'+html.escape(title)+"</div>",
                unsafe_allow_html=True)
    st.caption(question)

def warn_no(source:str):
    st.info("No hay registros de "+source+" para los filtros seleccionados. "
        "Esto no equivale a ausencia del fenómeno.")

def label_map(df:pd.DataFrame,country_col="iso3")->dict:
    return dict(zip(df[country_col],df["pais"]))

def filtered(df:pd.DataFrame,selected:set[str],field="iso3")->pd.DataFrame:
    return (df[df[field].isin(selected)].copy() if not df.empty else df)

def year_values(df:pd.DataFrame,col="reference_period_start")->list[str]:
    return sorted(df[col].dropna().astype(str).str[:4].unique().tolist(),reverse=True)

def choose_country(df:pd.DataFrame,names:dict,key:str,field="iso3")->str|None:
    if df.empty:return None
    options=sorted(df[field].dropna().unique().tolist(),
                   key=lambda x:names.get(x,x))
    return st.selectbox("País",options,format_func=lambda c:names.get(c,c),
                        key=key) if options else None

def latest_ops(df:pd.DataFrame,indicator:str,year:int|None=None)->pd.DataFrame:
    sub=df[(df["indicador"]==indicator)&df["valor"].notna()&
           df["periodo"].notna()].copy()
    if year is not None:
        sub=sub[sub["periodo"]==year]
    return sub.sort_values("periodo").drop_duplicates("iso3",keep="last")

def ops_selector(df:pd.DataFrame,indicators:list[str],key:str):
    available=[v for v in indicators if v in set(df["indicador"])]
    if not available:
        warn_no("indicadores OPS");return
    ind=st.selectbox("Indicador",available,key=key+"_ind",
                     format_func=lambda x:OPS_LABELS.get(x,x))
    year_common=st.checkbox("Usar el mismo año en todos los países",
                            key=key+"_common",value=False)
    year=None
    if year_common:
        years=sorted(df[df["indicador"]==ind]["periodo"].dropna().astype(int).unique(),
                     reverse=True)
        year=st.selectbox("Año de referencia",years,key=key+"_year") if years else None
    sub=latest_ops(df,ind,year)
    with panel("Comparación entre países",
        "Último dato disponible por país" if not year_common
        else f"Comparación del año {year}",
        "OPS · Indicadores Básicos, edición octubre de 2026"):
        if sub.empty:
            warn_no(OPS_LABELS.get(ind,ind))
        else:
            sub["anio"]=sub["periodo"].astype(int)
            plot(strip_countries(sub,name="pais",val="valor",
                year="anio",max_items=20,units=OPS_LABELS.get(ind,ind)))
            if not year_common:
                st.caption("Los años pueden diferir. El valor y su año se "
                           "consultan al pasar el cursor.")
    with st.expander("Ver serie histórica del país y tabla de datos"):
        if not sub.empty:
            names=sub.set_index("iso3")["pais"].to_dict()
            iso=choose_country(sub,names,key+"_country")
            serie=df[(df["iso3"]==iso)&(df["indicador"]==ind)].copy()
            serie["fecha"]=pd.to_datetime(
                serie["periodo"].astype("Int64").astype(str)+"-01-01",errors="coerce")
            with panel("Serie histórica",source="OPS · edición octubre 2026"):
                plot(trend(serie,x="fecha",y="valor",
                           units=OPS_LABELS.get(ind,ind),area=False))
            st.dataframe(sub[["pais","periodo","valor"]].rename(columns={
                "pais":"País","periodo":"Año","valor":"Valor"}),
                hide_index=True,use_container_width=True)

def valid_needs(df):
    if df.empty:return df
    return df[(df["sector_code"].astype(str).str.lower()=="intersectoral")&
        (df["population_status"]=="INN")&
        (df["category"].fillna("").astype(str).str.lower().isin(["","all","total"]))].copy()

def overview(D,selected,names,period):
    section("01","Panorama regional",
            "¿Qué contextos están documentados y cuáles requieren una revisión más profunda?")
    risk=filtered(D["risk"],selected)
    severity=filtered(D["severity"],selected)
    reports=filtered(D["reports"],selected)
    needs=filtered(D["needs"],selected)
    a,b,c,d=st.columns(4)
    a.metric("Países del ámbito",len(selected))
    b.metric("Contextos ACAPS",severity["crisis_id"].nunique() if not severity.empty else "—")
    c.metric("Países con PiN reportada",needs["iso3"].nunique() if not needs.empty else "—")
    d.metric("Informes recientes",reports["reporte_id"].nunique() if not reports.empty else "—")
    st.caption("Lectura sugerida: partir del riesgo estructural INFORM, "
        "revisar las crisis ACAPS y después abrir las señales y los reportes "
        "que aportan evidencia. Ninguna fuente define por sí sola la prioridad OPS.")
    st.caption("Países, crisis, estimaciones e informes son unidades diferentes: "
        "no se suman entre sí ni constituyen una puntuación institucional.")
    col1,col2=st.columns([1.35,1.0],gap="medium")
    with col1:
        with panel("Riesgo estructural INFORM · Mid 2026",
            "Mapa contextual, no clasificación de prioridad operacional OPS.",
            "INFORM Risk, JRC · Mid 2026"):
            if risk.empty:warn_no("INFORM Risk")
            else:map_countries(risk,"puntuacion","Riesgo estructural",
                               height=470,legend_title="INFORM Risk / 10")
    with col2:
        with panel("Crisis evaluadas por ACAPS",
            "Se muestran contextos individuales. Una crisis puede abarcar varios países.",
            "ACAPS INFORM Severity · "+str(D["acaps_meta"].get("datasets",{}).
                get("severity",{}).get("corte_api","edición disponible"))):
            if severity.empty:warn_no("ACAPS Severity")
            else:
                temp=severity.sort_values("puntuacion",ascending=False)
                table=temp[["pais","crisis","puntuacion"]].head(12).rename(
                    columns={"pais":"País","crisis":"Crisis",
                             "puntuacion":"Severidad / 10"})
                st.dataframe(table,hide_index=True,use_container_width=True,height=430,
                    column_config={"Crisis":st.column_config.TextColumn(width="large")})
    with st.expander("Explorar evolución y reportes que respaldan la lectura regional",expanded=False):
        st.markdown("#### Señales y evidencia complementaria")
        col1,col2=st.columns(2,gap="medium")
        with col1:
            h=filtered(D["conflict"],selected)
            h=h[h["tipo_evento"]=="political_violence"] if not h.empty else h
            if not h.empty:
                h=h[h["fecha"]>=h["fecha"].max()-pd.DateOffset(months=period)]
                ts=h.groupby("fecha",as_index=False)["eventos"].sum()
            else:ts=pd.DataFrame()
            with panel("Violencia política · evolución mensual",
                "Eventos registrados en los países seleccionados; fuente ACLED agregada.",
                "OCHA HDX HAPI / ACLED · cortes mensuales"):
                if ts.empty:warn_no("conflicto HAPI")
                else:plot(trend(ts,x="fecha",y="eventos",units="Eventos reportados"))
        with col2:
            with panel("Informes de situación recientes",
                "Documentos originales para interpretación y seguimiento, no conteos de crisis.",
                "OCHA ReliefWeb · últimos 90 días"):
                if reports.empty:warn_no("ReliefWeb")
                else:
                    rows=reports.drop_duplicates("reporte_id").sort_values("fecha",ascending=False).head(8).copy()
                    rows["Fecha"]=rows["fecha_publicacion_rw"].astype(str).str[:10]
                    st.dataframe(rows[["Fecha","titulo","url"]].rename(columns={
                        "titulo":"Informe","url":"Documento"}),
                        hide_index=True,use_container_width=True,height=345,
                        column_config={"Documento":st.column_config.LinkColumn(
                            display_text="Abrir"),
                            "Informe":st.column_config.TextColumn(width="large")})
    st.caption("No se presenta un ranking de países prioritarios: las categorías "
        "crítico, alto, elevado y moderado requieren criterios aprobados por Laura/PHE.")

def threats(D,selected,names,period):
    section("02","Amenazas y eventos",
            "¿Qué ocurrió, en qué periodo y qué evidencia de restricciones de acceso existe?")
    tab1,tab2,tab3=st.tabs(["Violencia y conflicto","Acceso humanitario","Contexto y reportes"])
    with tab1:
        group=st.selectbox("Tipo de amenaza",
            list(HAPI_TYPES),format_func=lambda x:HAPI_TYPES[x],
            key="amenaza_evento")
        raw=filtered(D["conflict"],selected)
        raw=raw[raw["tipo_evento"]==group] if not raw.empty else raw
        if not raw.empty:
            raw=raw[raw["fecha"]>=raw["fecha"].max()-pd.DateOffset(months=period)]
        if raw.empty:warn_no("eventos de conflicto HAPI")
        else:
            col1,col2=st.columns([1.2,1],gap="medium")
            with col1:
                ts=raw.groupby("fecha",as_index=False)["eventos"].sum()
                with panel("Evolución de eventos",
                    "Categoría individual; no sumar con las demás categorías.",
                    "HAPI / ACLED agregado · 2020 en adelante"):
                    plot(trend(ts,x="fecha",y="eventos",units="Eventos/mes"))
            with col2:
                grouped=raw.groupby("pais",as_index=False)["eventos"].sum()
                with panel("Países con más eventos registrados",
                    "Suma dentro de la categoría y periodo seleccionados, no todas las violencias.",
                    "HAPI / ACLED · cobertura por país variable"):
                    plot(rank_bars(grouped,label="pais",value="eventos",
                        limit=12,units="Eventos",formats=".0f"))
            st.caption("La fuente registra eventos agregados. No mide población "
                "afectada ni equivale a una evaluación de gravedad de crisis.")
            with st.expander("Detalle por país, muertes y descarga"):
                iso=choose_country(raw,names,"threat_country")
                r=raw[raw["iso3"]==iso].sort_values("fecha")
                a,b=st.columns(2)
                a.metric("Eventos del periodo",int(r["eventos"].sum()))
                if group=="demonstration":
                    b.metric("Muertes", "Sin dato en esta serie")
                else:
                    total=r["muertes_reportadas"].sum(min_count=1)
                    b.metric("Muertes reportadas",f"{total:,.0f}" if pd.notna(total) else "Sin dato")
                table=r[["periodo","eventos","muertes_reportadas"]]
                st.dataframe(table,hide_index=True,use_container_width=True)
                st.download_button("Descargar serie país",
                    table.to_csv(index=False).encode("utf-8-sig"),
                    file_name="violencia_hapi_pais.csv",mime="text/csv")
    with tab2:
        a=filtered(D["access"],selected)
        if a.empty:warn_no("evaluaciones de acceso ACAPS")
        else:
            a["etiqueta"]=a["pais"]+" · "+a["crisis"].fillna("")
            cols=st.columns([1.2,1],gap="medium")
            with cols[0]:
                with panel("Restricciones de acceso por crisis",
                    "Índice ACAPS por contexto evaluado; escala 0–5. No es un índice OPS.",
                    "ACAPS Humanitarian Access · "+str(a["corte_api"].iloc[0])):
                    plot(rank_bars(a,label="etiqueta",value="acceso",
                                   limit=12,color=ORANGE,units="Acceso / 5",max_x=5.3))
            with cols[1]:
                with panel("Interpretación y componentes",
                    "Elegir una crisis para consultar sus pilares originales.",
                    "ACAPS · P1, P2 y P3 según codebook"):
                    choices=a.sort_values("acceso",ascending=False)["crisis_id"].dropna().unique()
                    chosen=st.selectbox("Contexto",choices,format_func=lambda k:
                        a[a["crisis_id"]==k]["etiqueta"].iloc[0],key="access_crisis")
                    row=a[a["crisis_id"]==chosen].iloc[0]
                    st.metric("Índice de restricciones de acceso",
                        f"{row['acceso']:.1f} / 5" if pd.notna(row["acceso"]) else "Sin dato")
                    for i in (1,2,3):
                        v=row[f"pilar_{i}"]
                        st.write(f"Pilar P{i}: "+(f"{v:.1f}" if pd.notna(v) else "Sin dato"))
                    st.caption("Estos son componentes de ACAPS, no categorías "
                        "de seguimiento crítico/alto/elevado/moderado de OPS.")
        with st.expander("Seguridad del personal humanitario · AWSD"):
            sec=D["security_meta"].get("resultados",[])
            record=next((x for x in sec if x.get("fuente")=="AWSD"),{})
            if record.get("estado")=="CONECTADO":
                st.caption("Conexión AWSD validada; pendiente integración de series de incidentes.")
            else:
                st.info("La credencial AWSD está registrada, pero la API de incidentes "
                    "todavía no se ha validado en JSON. No se presentan cifras inventadas.")
    with tab3:
        st.markdown("**Fragilidad sociopolítica, crimen organizado y economías ilícitas**")
        st.caption("La propuesta incluye estos fenómenos, pero aún no existe una "
            "serie regional homologada y licenciada en el repositorio. Por ello "
            "no se asignan valores de amenaza ni colores de gravedad.")
        reports=filtered(D["reports"],selected)
        query=st.text_input("Buscar en títulos de informes ReliefWeb",
            placeholder="Ej. violence, access, displacement, crime",
            key="threat_reports_search")
        with panel("Evidencia documental para revisión",
            "Búsqueda en títulos solamente; no es una clasificación automática del contenido.",
            "OCHA ReliefWeb · metadatos de los últimos 90 días"):
            if reports.empty:warn_no("reportes ReliefWeb")
            else:
                docs=reports.drop_duplicates("reporte_id")
                if query.strip():
                    docs=docs[docs["titulo"].fillna("").str.contains(
                        query.strip(),case=False,regex=False)]
                docs=docs.sort_values("fecha",ascending=False).head(18).copy()
                docs["Fecha"]=docs["fecha_publicacion_rw"].str[:10]
                st.dataframe(docs[["Fecha","titulo","fuentes","url"]].rename(
                    columns={"titulo":"Título","fuentes":"Publicado por",
                             "url":"Abrir"}),hide_index=True,
                    use_container_width=True,height=430,
                    column_config={"Abrir":st.column_config.LinkColumn(display_text="Abrir")})
        st.caption("Fuentes especializadas para la fase siguiente: GI-TOC/Índice "
            "Global de Crimen Organizado, UNODC y registros nacionales curados. "
            "La identificación de situaciones de interés requiere revisión técnica.")

def response(D,selected,names):
    section("03","Vulnerabilidad y respuesta",
            "¿Qué condiciones incrementan la susceptibilidad y con qué recursos se cuenta?")
    tab1,tab2,tab3=st.tabs(["Condiciones sociales","Capacidad del sistema de salud",
                            "Respuesta humanitaria"])
    ops=filtered(D["ops"],selected)
    with tab1:
        st.caption("Comparación contextual, no resultado causal ni índice sintético de vulnerabilidad.")
        ops_selector(ops,["GINI","Escolaridad"],"social")
        with st.expander("Pobreza multidimensional (OPHI · HAPI)"):
            mpi=filtered(D["mpi"],selected)
            if mpi.empty:warn_no("pobreza multidimensional")
            else:
                mpi["anio"]=mpi["reference_period_start"].astype(str).str[:4]
                mpi=mpi.sort_values("anio").drop_duplicates("iso3",keep="last")
                with panel("Incidencia de pobreza multidimensional",
                    "Último dato de cada país; los años son diferentes.",
                    "OPHI / HAPI Poverty Rate"):
                    plot(strip_countries(mpi,name="pais",val="headcount_ratio",
                        year="anio",max_items=20,units="% población"))
    with tab2:
        st.caption("Recursos y coberturas de contexto; no equivalen a "
            "disponibilidad inmediata durante una emergencia.")
        ops_selector(ops,["Médicos","Enfermería","Camas hospitalarias","DTP3","SRP1"],
            "capacidad")
    with tab3:
        c1,c2=st.columns(2,gap="medium")
        with c1:
            present=filtered(D["presence"],selected)
            with panel("Presencia operacional de socios · 3W",
                "Elegir país y corte. No sumar socios entre sectores.",
                "HAPI Operational Presence"):
                if present.empty:warn_no("presencia operacional")
                else:
                    iso=choose_country(present,names,"response_3w_country")
                    t=present[present["iso3"]==iso]
                    date=st.selectbox("Fecha de referencia",
                        sorted(t["fecha_hasta"].astype(str).unique(),reverse=True),
                        key="response_3w_cut")
                    t=t[t["fecha_hasta"]==date]
                    plot(rank_bars(t,label="sector",value="organizaciones_distintas",
                        limit=13,units="Socios distintos",formats=".0f"))
                    st.caption("La misma organización puede figurar en varios "
                        "sectores, localidades o evaluaciones.")
        with c2:
            fund=filtered(D["funding"],selected)
            with panel("Financiación de apelaciones",
                "Por plan identificado y año; no es la financiación total recibida por un país.",
                "OCHA FTS vía HAPI"):
                if fund.empty:warn_no("financiación")
                else:
                    iso=choose_country(fund,names,"response_funding_country")
                    t=fund[fund["iso3"]==iso].copy()
                    t=t[(t["appeal_code"].fillna("").str.lower()!="not specified")&
                        t["appeal_code"].notna()]
                    t["anio"]=t["reference_period_start"].astype(str).str[:4]
                    if t.empty:
                        st.info("No hay apelaciones con código identificable para "
                            "esta selección. Los desembolsos sin plan identificado "
                            "no permiten calcular porcentaje de cobertura.")
                    else:
                        years=sorted(t["anio"].unique(),reverse=True)
                        years=[v for v in years if v.isdigit() and int(v)<=pd.Timestamp.now().year]
                        if years:
                            y=st.selectbox("Año del plan",years,key="response_funding_year")
                            t=t[t["anio"]==y]
                            st.dataframe(t[["appeal_name","funding_usd",
                                           "requirements_usd","funding_pct"]].rename(
                                columns={"appeal_name":"Plan / apelación",
                                    "funding_usd":"Financiado USD",
                                    "requirements_usd":"Requerido USD",
                                    "funding_pct":"Cobertura (%)"}),
                                hide_index=True,use_container_width=True,height=390)
                        else:st.info("Sin planes hasta el año de referencia actual.")
        st.caption("Ambos componentes representan capacidad de respuesta reportada. "
            "La oferta real de establecimientos y personal en la zona de una "
            "emergencia requiere fuentes territoriales adicionales.")

def impacts(D,selected,names):
    section("04","Impacto humanitario y salud",
            "¿Qué efectos sobre personas, movilidad y servicios están documentados?")
    tab1,tab2,tab3=st.tabs(["Personas en necesidad","Movilidad forzada",
                            "Consecuencias sanitarias"])
    with tab1:
        df=filtered(D["needs"],selected)
        st.caption("HAPI Humanitarian Needs: INN = personas en necesidad; "
            "TGT = población objetivo; AFF = afectada; REA = alcanzada. "
            "Los sectores se superponen, por lo que no se suman.")
        if df.empty:warn_no("estimaciones de necesidad humanitaria")
        else:
            t=valid_needs(df)
            t["anio"]=t["reference_period_start"].astype(str).str[:4]
            # Multiple intersectoral totals for the same country-year remain
            # excluded, not summed. Published table is not a severity ranking.
            duplicated=t.duplicated(["iso3","anio"],keep=False)
            t=t[~duplicated].sort_values("anio").drop_duplicates("iso3",keep="last")
            if not t.empty:
                with panel("Personas en necesidad · estimación intersectorial",
                    "Solo estimaciones INN totales sin desglose y sin duplicados país-año. "
                    "Los años varían; no sumar países como total regional.",
                    "HAPI / OCHA Humanitarian Needs"):
                    plot(strip_countries(t,name="pais",val="population",
                        year="anio",max_items=12,units="Personas estimadas"))
            with st.expander("Explorar sector, población y año"):
                iso=choose_country(df,names,"needs_country")
                rows=df[df["iso3"]==iso].copy()
                ys=year_values(rows)
                year=st.selectbox("Año",ys,key="needs_year")
                rows=rows[rows["reference_period_start"].astype(str).str[:4]==year]
                codes=sorted(rows["population_status"].dropna().unique())
                status=st.selectbox("Estado de población",codes,
                    index=codes.index("INN") if "INN" in codes else 0,key="needs_status")
                rows=rows[rows["population_status"]==status]
                sector=st.selectbox("Sector",sorted(rows["sector_name"].dropna().unique()),
                    key="needs_sector")
                rows=rows[rows["sector_name"]==sector]
                st.dataframe(rows[["category","population","reference_period_start",
                    "reference_period_end"]].rename(columns={
                        "category":"Categoría","population":"Personas",
                        "reference_period_start":"Desde",
                        "reference_period_end":"Hasta"}),
                    hide_index=True,use_container_width=True)
    with tab2:
        mode=st.radio("Población de interés",
                      ["Refugio y asilo (ACNUR)","Desplazamiento interno (OIM)"],
                      horizontal=True,key="mobility_mode")
        if mode.startswith("Refugio"):
            df=filtered(D["acnur"],selected,"asilo_iso3")
            if df.empty:warn_no("personas de interés ACNUR")
            else:
                c1,c2=st.columns([1.3,1],gap="medium")
                with c2:
                    with panel("Definir población",source="ACNUR vía HAPI"):
                        iso=choose_country(df,names,"mobility_host","asilo_iso3")
                        df=df[df["asilo_iso3"]==iso]
                        years=sorted(df["anio"].astype(str).unique(),reverse=True)
                        year=st.selectbox("Año",years,key="mobility_year")
                        df=df[df["anio"].astype(str)==year]
                        groups=sorted(df["grupo_poblacion"].dropna().unique())
                        g=st.selectbox("Categoría",groups,
                            index=groups.index("REF") if "REF" in groups else 0,
                            format_func=lambda x:{"REF":"Refugiados (REF)",
                                "ASY":"Solicitantes de asilo (ASY)"}.get(x,x),
                            key="mobility_group")
                        df=df[df["grupo_poblacion"]==g].copy()
                        st.metric("Orígenes representados",df["origen_iso3"].nunique())
                        st.caption("Stock de personas con registro para origen "
                            "y acogida; no llegadas del año.")
                with c1:
                    with panel("Población por país de origen",
                        "Totales del proveedor (sexo=all, edad=all) para evitar duplicar desgloses.",
                        "ACNUR vía HAPI · origen/acogida"):
                        if df.empty:warn_no("datos de origen")
                        else:
                            df["origen"]=df["origen_iso3"].map(names).fillna(df["origen_iso3"])
                            plot(rank_bars(df,label="origen",value="personas",
                                limit=15,units="Personas",formats=".0f"))
        else:
            df=filtered(D["dtm"],selected)
            if df.empty:warn_no("operaciones OIM DTM")
            else:
                with panel("Última ronda por operación",
                    "Elegir operación; las cifras no se suman entre rondas, "
                    "operaciones ni orígenes que puedan solaparse.",
                    "OIM DTM Baseline"):
                    iso=choose_country(df,names,"dtm_host")
                    country=df[df["iso3"]==iso]
                    op=st.selectbox("Operación",sorted(country["operacion"].dropna().unique()),
                                    key="dtm_operation")
                    sub=country[country["operacion"]==op]
                    st.caption("Fecha de reporte: "+str(sub["fecha_reporte"].max())+
                               " · ronda: "+str(sub["ronda"].iloc[0]))
                    st.dataframe(sub[["origen_admin1","personas_idp_reportadas",
                        "hombres","mujeres","causa_desplazamiento"]].rename(
                        columns={"origen_admin1":"Origen declarado",
                                 "personas_idp_reportadas":"IDP reportadas",
                                 "hombres":"Hombres","mujeres":"Mujeres",
                                 "causa_desplazamiento":"Causa"}),
                        use_container_width=True,hide_index=True)
                st.caption("La última ronda disponible puede ser antigua. "
                    "Esta tabla no equivale a una estimación nacional actual.")
    with tab3:
        st.caption("La propuesta distingue daños sanitarios reales de condiciones "
            "de capacidad previa. Los eventos contra establecimientos y personal "
            "sanitario requieren OMS SSA o reportes validados.")
        col1,col2=st.columns([1.3,1],gap="medium")
        with col1:
            ops_selector(filtered(D["ops"],selected),
                ["Mortalidad por homicidio"],"health_impact")
        with col2:
            with panel("Ataques y servicios esenciales afectados",
                "Datos no disponibles de manera regional comparable en este corte.",
                "OMS Surveillance System for Attacks on Health Care (SSA)"):
                st.info("No hay todavía una serie integrada y verificada de "
                    "establecimientos afectados, ataques a personal sanitario "
                    "o interrupciones de agua, electricidad y atención. "
                    "No se sustituyen por conteos de eventos violentos.")
                st.markdown("[Consultar fuente OMS SSA]("+URLS["SSA"]+")")
                st.caption("La documentación de daños y continuidad de servicios "
                    "requiere revisión técnica y trazabilidad de los reportes.")

def profile(D,selected,names,period):
    section("05","Perfiles por país",
            "¿Qué evidencia existe sobre amenazas, poblaciones, vulnerabilidad y respuesta?")
    codes=sorted(selected,key=lambda x:names.get(x,x))
    iso=st.selectbox("País",codes,format_func=lambda x:names.get(x,x),
                    key="profile_country")
    st.markdown("### "+names.get(iso,iso))
    risk=filtered(D["risk"],{iso})
    severity=filtered(D["severity"],{iso})
    conflict=filtered(D["conflict"],{iso})
    a,b,c=st.columns(3)
    a.metric("Riesgo estructural INFORM",
             f"{risk['puntuacion'].iloc[0]:.1f} / 10" if not risk.empty else "Sin dato",
             help="INFORM Mid 2026, no prioridad OPS")
    b.metric("Crisis con evaluación ACAPS",
             severity["crisis_id"].nunique() if not severity.empty else "Sin registros")
    c.metric("Último mes conflicto HAPI",
             str(conflict["periodo"].max()) if not conflict.empty else "Sin registros")
    st.caption("La combinación no es un índice. Las fuentes tienen cobertura, "
        "unidad y fechas diferentes.")
    c1,c2=st.columns([1.15,1],gap="medium")
    with c1:
        with panel("Situaciones documentadas",
            "INFORM Severity/ACAPS: contextos individuales, no prioridad OPS.",
            "ACAPS · "+str(D["acaps_meta"].get("datasets",{}).
            get("severity",{}).get("corte_api","edición disponible"))):
            if severity.empty:warn_no("crisis ACAPS")
            else:
                st.dataframe(severity[["crisis","puntuacion","categoria"]].rename(
                    columns={"crisis":"Crisis","puntuacion":"Severidad / 10",
                             "categoria":"Categoría ACAPS"}),
                    hide_index=True,use_container_width=True,height=280)
    with c2:
        with panel("Evolución de violencia política",
            "Eventos mensuales, no cantidad de personas afectadas.",
            "OCHA HAPI / ACLED"):
            raw=conflict[conflict["tipo_evento"]=="political_violence"] if not conflict.empty else conflict
            if raw.empty:warn_no("conflicto")
            else:
                raw=raw[raw["fecha"]>=raw["fecha"].max()-pd.DateOffset(months=period)]
                plot(trend(raw,x="fecha",y="eventos",units="Eventos/mes"))
    # Unified evidence table with explicit missingness. No synthetic index.
    needs=valid_needs(filtered(D["needs"],{iso}))
    un=filtered(D["acnur"],{iso},"asilo_iso3")
    op=filtered(D["ops"],{iso})
    pres=filtered(D["presence"],{iso})
    access=filtered(D["access"],{iso})
    mp=filtered(D["mpi"],{iso})
    def fmt_date(s):
        try:return str(s)[:10]
        except (TypeError,ValueError):return "—"
    entries=[]
    entries.append(("Amenaza / evento",
        f"Último mes con registros HAPI: {conflict['periodo'].max()}" if not conflict.empty
        else "Sin registros en la extracción",
        "HAPI / ACLED","mensual" if not conflict.empty else "—"))
    entries.append(("Exposición / población",
        f"Refugio y asilo: {un['grupo_poblacion'].nunique()} categorías registradas"
        if not un.empty else "Sin registros de acogida ACNUR",
        "ACNUR / HAPI",str(un["anio"].max()) if not un.empty else "—"))
    entries.append(("Vulnerabilidad",
        f"Pobreza multidimensional: {len(mp)} mediciones históricas"
        if not mp.empty else "Sin datos de pobreza multidimensional",
        "HAPI / OPHI",str(mp["reference_period_start"].max())[:4] if not mp.empty else "—"))
    entries.append(("Impacto humanitario",
        f"Necesidades intersectoriales: {len(needs)} registros por periodo"
        if not needs.empty else "Sin estimación intersectorial PiN",
        "HAPI / OCHA",str(needs["reference_period_start"].max())[:4] if not needs.empty else "—"))
    entries.append(("Capacidad de respuesta",
        f"Presencia 3W: {pres['sector'].nunique()} sectores documentados"
        if not pres.empty else "Sin informe 3W del país",
        "HAPI / OCHA",fmt_date(pres["fecha_hasta"].max()) if not pres.empty else "—"))
    with panel("Lectura integrada de evidencias",
        "Resumen de disponibilidad, no una escala de prioridad ni de gravedad.",
        "HAPI / ACNUR / OPHI / OCHA"):
        st.dataframe(pd.DataFrame(entries,columns=[
            "Dimensión","Hallazgo documentado","Fuente","Periodo"]),
            hide_index=True,use_container_width=True,height=233)
    with st.expander("Detalle por fuente: salud, acceso, necesidades y documentos"):
        if not access.empty:
            st.markdown("**Acceso humanitario ACAPS**")
            st.dataframe(access[["crisis","acceso"]],use_container_width=True,
                         hide_index=True)
        if not needs.empty:
            st.markdown("**Personas en necesidad intersectorial**")
            st.dataframe(needs[["reference_period_start","population"]],
                         use_container_width=True,hide_index=True)
        if not op.empty:
            st.markdown("**Indicadores OPS · último dato por indicador**")
            latest=op.sort_values("periodo").drop_duplicates("indicador",keep="last")
            st.dataframe(latest[["indicador","periodo","valor"]],
                         use_container_width=True,hide_index=True)
        reports=filtered(D["reports"],{iso})
        if not reports.empty:
            st.markdown("**Informes ReliefWeb recientes**")
            reports=reports.drop_duplicates("reporte_id").sort_values("fecha",ascending=False).head(10)
            st.dataframe(reports[["titulo","url"]].rename(columns={
                "titulo":"Informe","url":"Abrir"}),use_container_width=True,
                hide_index=True,column_config={
                "Abrir":st.column_config.LinkColumn(display_text="Abrir")})
    st.caption("Prioridad operacional OPS: **pendiente de definición y "
        "validación técnica por Laura/equipo PHE**. Ninguna de estas filas "
        "es una recomendación automática de priorización.")

def metadata_sidebar(D,selected):
    with st.sidebar.expander("Fuentes, calidad y metodología",expanded=False):
        st.caption("Últimos snapshots disponibles; no son necesariamente "
                   "fechas de referencia de los datos originales.")
        for key,label,datekey in [
            ("acaps","ACAPS","fecha_utc"),
            ("hapi","HAPI / conflicto","fecha_utc"),
            ("hapi_context","HAPI / contexto","fecha_extraccion_utc"),
            ("acnur","HAPI / ACNUR","fecha_extraccion_utc"),
            ("reports","ReliefWeb","fecha_utc"),
            ("dtm","OIM DTM","fecha_utc"),
        ]:
            obj=D.get(key+"_meta",{})
            value=obj.get(datekey)
            if value:st.caption(label+": "+str(value)[:10])
        st.markdown("[Catálogo completo de variables](https://github.com/"
            "ivanromero0724/observatorio-humanitario-ops/blob/main/docs/fase2/hapi_familias.md)")
        st.markdown("[Metodología y cobertura](https://github.com/"
            "ivanromero0724/observatorio-humanitario-ops/blob/main/docs/fase2/"
            "arquitectura_indicadores_dashboard.md)")
        st.caption("Vacío no equivale a cero. Los niveles crítico, alto, "
            "elevado y moderado requieren definición y revisión PHE.")

def main():
    st.set_page_config(page_title="Observatorio Humanitario | OPS/OMS",
        page_icon="🌎",layout="wide",initial_sidebar_state="expanded")
    apply_style()
    st.markdown("""
    <style>
    .obs-kicker{font:800 .71rem Arial,sans-serif;color:#0072CE;
        letter-spacing:.12em;margin:8px 0 3px}
    .obs-section-title{font:750 1.42rem Arial,sans-serif;color:#004B87;
        letter-spacing:-.025em;margin:0 0 4px}
    .obs-panel-title{font:750 1.06rem Arial,sans-serif;color:#004B87;
        line-height:1.35;margin:3px 0 8px}
    /* El contenedor real de Streamlit admite dos selectores segun version.
       Usar borde, radio y separacion IDENTICOS en cada mapa y grafico. */
    [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"],
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"]{
        border:1px solid #D8E2E9!important;
        border-radius:12px!important;
        background:#FFFFFF!important;
        box-shadow:0 2px 7px rgba(0,57,99,.045)!important;}
    [data-testid="stPlotlyChart"]{padding-top:0!important;overflow:hidden}
    [data-testid="stPlotlyChart"] > div{width:100%!important}
    [data-testid="stMetric"]{background:white}
    [data-testid="stSidebar"] [data-testid="stRadio"] label{font-size:.87rem}
    [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stCaptionContainer"] p{
        color:#667A89!important;font-size:.79rem!important}
    .obs-section-title{margin-top:.35rem!important}
    </style>
    """,unsafe_allow_html=True)
    D=load_all()
    countries=D["countries"]
    if countries.empty:
        st.error("Falta catálogo de países. Verifica data/catalogos/paises_americas.csv")
        st.stop()
    names=dict(zip(countries["iso3"],countries["pais"]))
    with st.sidebar:
        st.markdown("### OPS / OMS")
        st.caption("Emergencias en Salud · Región de las Américas")
        page=st.radio("Explorar",PAGES,label_visibility="collapsed",
                      key="nav")
        st.divider()
        region=st.selectbox("Subregión",
            ["Todas las Américas"]+sorted(countries["subregion"].unique()),
            key="filter_region")
        scope=countries if region=="Todas las Américas" else countries[
            countries["subregion"]==region]
        options=sorted(scope["iso3"],key=lambda c:names.get(c,c))
        picked=st.selectbox("País",
            ["Todos los países"]+options,
            format_func=lambda x:x if x=="Todos los países" else names.get(x,x),
            key="filter_country")
        selected=set(options) if picked=="Todos los países" else {picked}
        period=st.selectbox("Periodo de series HAPI",
            [12,24,60],format_func=lambda n:f"Últimos {n} meses",
            key="filter_violence_period")
        st.caption(f"Ámbito: {len(selected)} países · cortes por proveedor.")
    metadata_sidebar(D,selected)
    ops_header()
    st.caption("Análisis territorial de amenazas humanitarias y consecuencias "
        "en salud. Prototipo metodológico, no sistema de alerta ni clasificación "
        "oficial de prioridad OPS.")
    if page==PAGES[0]:
        overview(D,selected,names,period)
    elif page==PAGES[1]:
        threats(D,selected,names,period)
    elif page==PAGES[2]:
        response(D,selected,names)
    elif page==PAGES[3]:
        impacts(D,selected,names)
    else:
        profile(D,selected,names,period)
    ops_footer()

if __name__=="__main__":
    main()
