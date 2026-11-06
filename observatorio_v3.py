"""Observatorio Humanitario OPS · interfaz operativa, 6 nov 2026.

La navegación sigue decisiones analíticas: situaciones documentadas, señales,
impacto en personas, vulnerabilidad/capacidad, país. No es un catálogo de APIs
ni una clasificación oficial de prioridad OPS.

Fuente de datos y controles QA: observatorio_v2.load_all; sin consultas a API
ni secretos en Streamlit. Todos los paneles en columnas usan alturas iguales.
"""
from __future__ import annotations

import html
from contextlib import contextmanager

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from observatorio_v2 import (
    load_all, filtered, valid_needs, latest_ops, OPS_LABELS, HAPI_TYPES,
    URLS, META,
)
from ui_ops import apply_style, header as ops_header, footer as ops_footer, map_countries
from graficos import rank_bars, trend, strip_countries

BLUE="#0072CE"
ORANGE="#E87C2A"
NAVY="#004B87"
PAGES=[
    "Situaciones documentadas",
    "Amenazas y acceso",
    "Personas e impacto",
    "Vulnerabilidad y respuesta",
    "Ficha por país",
]
THEMES={
    "Todas las situaciones":None,
    "Conflicto y violencia":r"conflict|violence|armed|insecurity|criminal|gang",
    "Desplazamiento y refugio":r"displacement|refugee|migration|migrat",
}
CARD=490
CSS="""
<style>
.block-container {max-width:1320px!important;padding-top:1rem!important}
.obs-title{font:760 1.43rem Arial,sans-serif;color:#004B87;margin:8px 0 1px;
 letter-spacing:-.03em}
.obs-eyebrow{font:800 .69rem Arial,sans-serif;color:#0072CE;
 letter-spacing:.12em;margin-top:3px}
.obs-card-title{font:750 1.05rem Arial,sans-serif;color:#004B87;
 line-height:1.25;min-height:25px;margin:0 0 7px}
.obs-card-sub{font:400 .80rem/1.35 Arial,sans-serif;color:#5B7080;
 min-height:35px;margin-bottom:7px}
.obs-meta{font:400 .75rem Arial,sans-serif;color:#6A7E8C;}
/* Streamlit native containers provide the SAME border, padding and radius.
   Paired panels receive an identical explicit pixel height in Python. */
div[data-testid="stVerticalBlockBorderWrapper"]{
 border:1px solid #D6E1E9!important;border-radius:12px!important;
 background:#FFF!important;box-shadow:0 2px 6px rgba(10,55,82,.045)!important;
}
div[data-testid="stHorizontalBlock"]{align-items:stretch!important}
div[data-testid="stMetric"]{min-height:110px!important;border-radius:11px!important;
 border:1px solid #D6E1E9!important;border-top:3px solid #0072CE!important}
[data-testid="stMetricValue"]{font-size:1.65rem!important}
[data-testid="stPlotlyChart"]{width:100%!important}
[data-testid="stSidebar"]{background:#F6F9FC!important}
</style>
"""

def title(kicker,heading,question):
    st.markdown(f'<div class="obs-eyebrow">{html.escape(kicker)}</div>'
      f'<div class="obs-title">{html.escape(heading)}</div>',unsafe_allow_html=True)
    st.caption(question)

@contextmanager
def card(heading,sub="",source="",height=None):
    """Native Streamlit border; side-by-side panels MUST use identical height."""
    with st.container(border=True,height=height):
        st.markdown(f'<div class="obs-card-title">{html.escape(heading)}</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="obs-card-sub">{html.escape(sub)}</div>',
                    unsafe_allow_html=True)
        yield
        if source:
            st.caption("Fuente: "+source)

def plot(fig,height=315):
    fig.update_layout(height=height,margin=dict(l=14,r=40,t=15,b=40))
    st.plotly_chart(fig,use_container_width=True,
       config={"displayModeBar":False,"responsive":True})

def empty(label):
    st.info(f"Sin registros de {label} para el filtro seleccionado. "
            "La ausencia de datos no significa ausencia del fenómeno.")

def data_table(df,height=290,cols=None,ren=None,link=None):
    out=df[cols].rename(columns=ren or {}) if cols else df
    config={}
    if link:config[link]=st.column_config.LinkColumn(link,display_text="Abrir")
    st.dataframe(out,use_container_width=True,hide_index=True,height=height,
      column_config=config)

def summary_dataset(D,selected,selected_theme):
    sev=filtered(D["severity"],selected)
    if sev.empty:return sev
    sev=sev.copy()
    if selected_theme and THEMES.get(selected_theme):
        sev=sev[sev["drivers"].fillna("").str.contains(
            THEMES[selected_theme],case=False,regex=True)]
    access=filtered(D["access"],selected)
    if not access.empty:
        access=access[["iso3","crisis_id","acceso"]].drop_duplicates(
            ["iso3","crisis_id"])
        sev=sev.merge(access,on=["iso3","crisis_id"],how="left",
                      suffixes=("","_access"))
        if "acceso_access" in sev:
            sev["acceso"]=sev["acceso_access"]
    if "acceso" not in sev:sev["acceso"]=pd.NA
    sev["acceso"]=pd.to_numeric(sev["acceso"],errors="coerce")
    sev=sev.sort_values(["puntuacion","pais"],ascending=[False,True])
    return sev

def only_conflict(D,selected,months,kind="political_violence"):
    d=filtered(D["conflict"],selected)
    if d.empty:return d
    d=d[(d["tipo_evento"]==kind)&d["fecha"].notna()].copy()
    if d.empty:return d
    # Mismo corte para todas las observaciones del ámbito seleccionado.
    end=d["fecha"].max()
    return d[d["fecha"]>end-pd.DateOffset(months=months)].copy()

def recent_reports(D,selected):
    df=filtered(D["reports"],selected)
    if df.empty:return df
    return df.drop_duplicates("reporte_id").sort_values("fecha",ascending=False)

def cover_notes(D,selected):
    keys=[
      ("Crisis ACAPS","severity","iso3"),
      ("Conflicto HAPI","conflict","iso3"),
      ("Necesidades HAPI","needs","iso3"),
      ("Refugio / asilo ACNUR","acnur","asilo_iso3"),
      ("Desplazamiento OIM","dtm","iso3"),
      ("Acceso ACAPS","access","iso3"),
      ("Presencia 3W","presence","iso3"),
      ("Indicadores OPS","ops","iso3"),
      ("ReliefWeb","reports","iso3"),
    ]
    rows=[]
    for label,key,col in keys:
        df=D[key]
        n=len(set(df[col].dropna())&selected) if not df.empty else 0
        rows.append({"Fuente":label,"Países con registros":n,
                     "Países sin registros":len(selected)-n})
    return pd.DataFrame(rows)

def situations(D,selected,names,months):
    title("01 / SITUACIONES","Situaciones humanitarias documentadas",
          "Comenzar por contextos evaluados, revisar las señales recientes "
          "y abrir los documentos que permiten interpretarlos.")
    col1,col2=st.columns([1.35,1.0])
    with col1:
        theme=st.selectbox("Tipo de situación",list(THEMES),
                           key="situacion_tipo")
    with col2:
        st.caption("Los temas corresponden a los descriptores originales de "
                   "ACAPS y no a una clasificación asignada por OPS.")
    sev=summary_dataset(D,selected,theme)
    all_reports=recent_reports(D,selected)
    c1,c2,c3=st.columns(3)
    c1.metric("Contextos evaluados por ACAPS",
              sev["crisis_id"].nunique() if not sev.empty else 0)
    c2.metric("Países con contextos evaluados",
              sev["iso3"].nunique() if not sev.empty else 0)
    c3.metric("Informes vinculados · 90 días",
              all_reports["reporte_id"].nunique() if not all_reports.empty else 0)
    st.caption("Contextos, países e informes tienen unidades distintas; no "
               "se suman ni definen por sí solos niveles de prioridad OPS.")

    with card("Contextos documentados para revisión técnica",
         "Tabla ordenada por el valor de INFORM Severity de ACAPS. "
         "Esto NO es un ranking de prioridad OPS.",
         "ACAPS · INFORM Severity y Humanitarian Access · noviembre 2026"):
        if sev.empty:
            empty("crisis ACAPS")
        else:
            view=sev[["pais","crisis","drivers","puntuacion","acceso",
                       "confiabilidad"]].rename(columns={
                "pais":"País","crisis":"Situación evaluada",
                "drivers":"Descriptores de la situación",
                "puntuacion":"Severidad / 10","acceso":"Restricción acceso / 5",
                "confiabilidad":"Confianza fuente"})
            data_table(view,height=335)
            st.caption("Una misma situación puede afectar a varios países. "
                       "La ausencia de evaluación ACAPS no implica ausencia de crisis.")

    left,right=st.columns([1,1],gap="medium")
    with left:
        with card("¿Dónde hay contextos evaluados?",
            "Azul: país con al menos un contexto ACAPS documentado. "
            "Gris: sin registro en este corte.",
            "ACAPS / GeoPackage Américas",height=CARD):
            base=D["countries"][D["countries"]["iso3"].isin(selected)].copy()
            has=set(sev["iso3"]) if not sev.empty else set()
            base["Disponibilidad"]=base["iso3"].isin(has).map({
                True:"Con registros",False:"Sin registros en catálogo"})
            map_countries(base,"Disponibilidad","Contextos ACAPS",
                          categorical=True,height=320)
    with right:
        with card("¿Cómo evoluciona la violencia política?",
            f"Eventos de la categoría HAPI/ACLED durante los últimos {months} meses. "
            "No equivale al total de situaciones humanitarias.",
            "HAPI / ACLED agregado",height=CARD):
            conflict=only_conflict(D,selected,months)
            if conflict.empty:empty("violencia política")
            else:
                time=(conflict.groupby("fecha",as_index=False)
                      ["eventos"].sum().sort_values("fecha"))
                plot(trend(time,x="fecha",y="eventos",
                    units="Eventos registrados"),height=305)
            st.caption("Las categorías ACLED pueden solaparse; "
                       "esta curva presenta únicamente violencia política.")

    with st.expander("Leer los informes recientes vinculados a las situaciones",expanded=True):
        if all_reports.empty:empty("documentos ReliefWeb")
        else:
            docs=all_reports.head(8).copy()
            docs["Fecha"]=docs["fecha_publicacion_rw"].astype(str).str[:10]
            data_table(docs,height=260,
                 cols=["Fecha","titulo","fuentes","url"],
                 ren={"titulo":"Informe","fuentes":"Organización","url":"Documento"},
                 link="Documento")
            st.caption("Informes indexados en ReliefWeb. La cantidad publicada "
                       "no representa la magnitud ni la gravedad de una crisis.")

def threats(D,selected,names,months):
    title("02 / AMENAZAS","Amenazas y restricciones de acceso",
          "Seguimiento de eventos registrados, evolución, países con actividad "
          "reportada y condiciones de acceso humanitario.")
    tab1,tab2=st.tabs(["Conflicto y violencia","Acceso humanitario"])
    with tab1:
        kind=st.selectbox("Evento",list(HAPI_TYPES),
            format_func=lambda x:HAPI_TYPES[x],key="ev_tipo")
        d=only_conflict(D,selected,months,kind)
        if d.empty:empty("eventos HAPI")
        else:
            a,b=st.columns(2)
            with a:
                with card("Evolución temporal",
                    f"Últimos {months} meses; una sola categoría por gráfico.",
                    "HAPI / ACLED agregado",height=CARD):
                    ts=d.groupby("fecha",as_index=False)["eventos"].sum()
                    plot(trend(ts,x="fecha",y="eventos",
                         units="Eventos reportados"),height=315)
            with b:
                with card("Países con eventos registrados",
                    "Comparación dentro de la categoría y periodo seleccionados.",
                    "HAPI / ACLED agregado",height=CARD):
                    rank=d.groupby("pais",as_index=False)["eventos"].sum()
                    plot(rank_bars(rank,label="pais",value="eventos",
                        limit=11,formats=".0f",units="Eventos"),height=320)
            st.caption("Violencia política, ataques contra civiles y manifestaciones "
                       "no se suman entre categorías por sus posibles solapamientos. "
                       "Los registros agregados no son incidentes geolocalizados.")
    with tab2:
        a=filtered(D["access"],selected)
        if a.empty:empty("evaluaciones de acceso ACAPS")
        else:
            scores=a.dropna(subset=["acceso"]).sort_values(
                "acceso",ascending=False).copy()
            scores["etiqueta"]=scores["pais"]+" · "+scores["crisis"].astype(str)
            l,r=st.columns(2)
            with l:
                with card("Restricciones de acceso por contexto",
                    "Escala de ACAPS, no indicador elaborado por OPS.",
                    "ACAPS Humanitarian Access",height=CARD):
                    plot(rank_bars(scores,label="etiqueta",
                       value="acceso",limit=10,max_x=5.3,
                       units="ACAPS / 5",color=ORANGE),height=330)
            with r:
                with card("Desglose del índice de acceso",
                    "Selecciona el contexto para revisar P1, P2 y P3.",
                    "ACAPS Humanitarian Access",height=CARD):
                    options=sorted(a["crisis_id"].dropna().unique())
                    cid=st.selectbox("Contexto",options,
                         format_func=lambda k:str(a[a["crisis_id"]==k]
                         ["crisis"].iloc[0]),key="access_crisis")
                    row=a[a["crisis_id"]==cid].iloc[0]
                    vals=pd.DataFrame([
                        {"Componente":"P1","Valor":row["pilar_1"]},
                        {"Componente":"P2","Valor":row["pilar_2"]},
                        {"Componente":"P3","Valor":row["pilar_3"]},
                    ])
                    plot(rank_bars(vals,label="Componente",value="Valor",
                       limit=3,color=BLUE,units="ACAPS / 5",
                       max_x=5.3),height=245)
                    st.caption("P1–P3 conservan las claves de ACAPS; "
                               "consultar el codebook para definiciones.")
            with st.expander("Ver todas las evaluaciones y fechas"):
                data_table(a,height=260,cols=["pais","crisis","acceso",
                   "brecha_info","corte_api"],ren={"pais":"País",
                   "crisis":"Situación","acceso":"Índice de acceso",
                   "brecha_info":"Brecha de información","corte_api":"Corte"})
    with st.expander("Amenazas sin serie regional comparable"):
        st.write("Crimen organizado, minería ilegal, economías ilícitas y "
                 "fragilidad sociopolítica forman parte de la propuesta, "
                 "pero requieren fuentes especializadas y validación. "
                 "No se asignan valores cero ni niveles de prioridad.")

def impacts(D,selected,names):
    title("03 / PERSONAS","Personas afectadas e impacto en salud",
          "Distinguir necesidades humanitarias, poblaciones desplazadas "
          "y daños sanitarios documentados.")
    t1,t2,t3=st.tabs(["Personas en necesidad","Refugio y desplazamiento",
                     "Impacto sanitario"])
    with t1:
        needs=filtered(D["needs"],selected)
        if needs.empty:empty("necesidades humanitarias")
        else:
            total=valid_needs(needs)
            total["anio"]=total["reference_period_start"].astype(str).str[:4]
            dup=total.duplicated(["iso3","anio"],keep=False)
            total=total[~dup].sort_values("anio").drop_duplicates(
                "iso3",keep="last")
            with card("Estimaciones intersectoriales de personas en necesidad",
                "Último año publicado por país cuando existe un único total "
                "intersectorial. Los años varían.",
                "OCHA / HAPI Humanitarian Needs"):
                if total.empty:
                    empty("totales intersectoriales comparables")
                else:
                    plot(strip_countries(total,name="pais",
                        val="population",year="anio",max_items=16,
                        units="Personas estimadas"),height=370)
                    st.caption("No se suman sectores ni se interpreta como "
                               "un total regional del mismo año.")
            with st.expander("Consultar estados, sectores y fechas"):
                countries=sorted(needs["iso3"].dropna().unique())
                iso=st.selectbox("País",countries,
                      format_func=lambda c:names.get(c,c),key="needs_country")
                x=needs[needs["iso3"]==iso].copy()
                yr=st.selectbox("Año",sorted(x["reference_period_start"]
                    .astype(str).str[:4].unique(),reverse=True),
                    key="needs_year")
                x=x[x["reference_period_start"].astype(str).str[:4]==yr]
                state=st.selectbox("Estado",sorted(x["population_status"]
                    .dropna().unique()),key="needs_state")
                x=x[x["population_status"]==state]
                data_table(x,height=320,cols=["sector_name","category",
                    "population","reference_period_start","reference_period_end"],
                    ren={"sector_name":"Sector","category":"Categoría",
                         "population":"Personas","reference_period_start":"Desde",
                         "reference_period_end":"Hasta"})
    with t2:
        un=filtered(D["acnur"],selected,"asilo_iso3")
        if un.empty:empty("refugio y asilo ACNUR")
        else:
            l,r=st.columns(2)
            with l:
                with card("Seleccionar población de acogida",
                    "Las personas contabilizadas son stocks, no nuevos flujos del año.",
                    "ACNUR a través de HAPI",height=CARD):
                    iso=st.selectbox("País de acogida",
                        sorted(un["asilo_iso3"].unique(),key=lambda c:names.get(c,c)),
                        format_func=lambda c:names.get(c,c),key="acnur_host")
                    x=un[un["asilo_iso3"]==iso].copy()
                    yrs=sorted(x["anio"].astype(str).unique(),reverse=True)
                    yr=st.selectbox("Año",yrs,key="acnur_year")
                    x=x[x["anio"].astype(str)==yr]
                    groups=sorted(x["grupo_poblacion"].dropna().unique())
                    g=st.selectbox("Tipo de población",groups,
                        format_func=lambda c:{"REF":"Refugiados",
                          "ASY":"Solicitantes de asilo"}.get(c,c),
                        index=groups.index("REF") if "REF" in groups else 0,
                        key="acnur_group")
                    x=x[x["grupo_poblacion"]==g]
                    st.metric("Países de origen representados",
                              x["origen_iso3"].nunique())
                    st.caption("HAPI filtrada por sexo=all y edad=all. "
                               "Los grupos se mantienen separados.")
            with r:
                with card("Personas registradas por origen",
                    "Para el país de acogida, año y categoría elegidos.",
                    "ACNUR / HAPI",height=CARD):
                    x=x.copy()
                    x["origen"]=x["origen_iso3"].map(names).fillna(
                        x["origen_iso3"])
                    plot(rank_bars(x,label="origen",value="personas",
                         limit=12,units="Personas",formats=".0f"),height=325)
        with st.expander("Desplazamiento interno · últimas rondas OIM DTM"):
            dtm=filtered(D["dtm"],selected)
            if dtm.empty:empty("OIM DTM")
            else:
                iso=st.selectbox("País con operación DTM",
                     sorted(dtm["iso3"].unique()),format_func=lambda c:names.get(c,c),
                     key="dtm_country")
                ops=dtm[dtm["iso3"]==iso]
                operation=st.selectbox("Operación",
                     sorted(ops["operacion"].dropna().unique()),key="dtm_op")
                rows=ops[ops["operacion"]==operation]
                st.caption(f"Ronda reportada: {rows['ronda'].iloc[0]} · "
                           f"Fecha: {rows['fecha_reporte'].max()}. "
                           "Las rondas pueden ser antiguas y no equivalen a stock actual.")
                data_table(rows,height=230,cols=["origen_admin1",
                     "personas_idp_reportadas","hombres","mujeres"],
                     ren={"origen_admin1":"Origen",
                         "personas_idp_reportadas":"IDP reportadas",
                         "hombres":"Hombres","mujeres":"Mujeres"})
    with t3:
        st.caption("No sustituir los ataques directos a servicios de salud "
                   "por el conteo general de hechos violentos.")
        ops=filtered(D["ops"],selected)
        h=latest_ops(ops,"Mortalidad por homicidio")
        l,r=st.columns(2)
        with l:
            with card("Mortalidad por homicidios",
                "Indicador de contexto, NO de ataques contra establecimientos.",
                "OPS / Indicadores Básicos",height=CARD):
                if h.empty:empty("mortalidad por homicidio")
                else:
                    h["anio"]=h["periodo"].astype(int)
                    plot(strip_countries(h,name="pais",val="valor",
                        year="anio",max_items=12,
                        units="Tasa OPS por 100.000"),height=325)
        with r:
            with card("Ataques a la atención sanitaria",
                "Registro de afectación de personal, establecimientos "
                "e interrupciones de servicios.",
                "OMS / SSA · pendiente de integración validada",height=CARD):
                st.info("Esta serie todavía no está integrada con cobertura "
                        "verificable en las Américas. Se deja explícito el "
                        "vacío de datos, sin inferir ataques a partir de homicidios.")
                st.markdown("[Consultar fuente OMS SSA]("+URLS["SSA"]+")")

def vulnerability(D,selected,names):
    title("04 / CONDICIONES","Vulnerabilidad y capacidad de respuesta",
          "Factores estructurales y recursos de salud, no resultados "
          "directos de un incidente ni prioridad operacional OPS.")
    t1,t2,t3=st.tabs(["Contexto social","Capacidad sanitaria",
                      "Respuesta humanitaria"])
    def ops_chart(options,key):
        df=filtered(D["ops"],selected)
        indicators=[x for x in options if not df.empty and
                    x in set(df["indicador"])]
        if not indicators:empty("indicadores OPS");return
        ind=st.selectbox("Indicador",indicators,
            format_func=lambda x:OPS_LABELS.get(x,x),key=key)
        common=st.checkbox("Comparar el mismo año",value=False,key=key+"_common")
        year=None
        if common:
            ys=sorted(df[df["indicador"]==ind]["periodo"].dropna()
                     .astype(int).unique(),reverse=True)
            year=st.selectbox("Año",ys,key=key+"_year") if len(ys) else None
        sub=latest_ops(df,ind,year)
        with card(OPS_LABELS.get(ind,ind),
            "Comparación de un año común" if common else
            "Última observación por país; los años pueden diferir.",
            "OPS / Indicadores Básicos · edición octubre 2026"):
            if sub.empty:empty("indicador seleccionado")
            else:
                sub["anio"]=sub["periodo"].astype(int)
                plot(strip_countries(sub,name="pais",val="valor",year="anio",
                    max_items=25,units=OPS_LABELS.get(ind,ind)),height=445)
        with st.expander("Tabla completa y trazabilidad"):
            if not sub.empty:data_table(sub,height=330,
                cols=["pais","periodo","valor"],ren={"pais":"País",
                    "periodo":"Año","valor":"Valor"})
    with t1:
        ops_chart(["GINI","Escolaridad"],"social")
        with st.expander("Consultar pobreza multidimensional OPHI"):
            mpi=filtered(D["mpi"],selected)
            if mpi.empty:empty("MPI")
            else:
                mpi=mpi.copy()
                mpi["anio"]=mpi["reference_period_start"].astype(str).str[:4]
                mpi=mpi.sort_values("anio").drop_duplicates("iso3",keep="last")
                plot(strip_countries(mpi,name="pais",
                    val="headcount_ratio",year="anio",max_items=18,
                    units="% pobreza multidimensional"),height=355)
    with t2:
        ops_chart(["Médicos","Enfermería","Camas hospitalarias",
                   "DTP3","SRP1"],"capacity")
        st.caption("Personal, camas y vacunación representan capacidades "
                   "de contexto; no garantizan disponibilidad efectiva "
                   "durante una emergencia.")
    with t3:
        l,r=st.columns(2)
        with l:
            with card("Presencia humanitaria por sector",
                "Organizaciones distintas dentro de un mismo sector y periodo.",
                "OCHA / HAPI Operational Presence",height=CARD):
                present=filtered(D["presence"],selected)
                if present.empty:empty("presencia 3W")
                else:
                    iso=st.selectbox("País con reporte 3W",sorted(present["iso3"].unique()),
                        format_func=lambda c:names.get(c,c),key="3w_country")
                    p=present[present["iso3"]==iso]
                    when=st.selectbox("Corte",sorted(p["fecha_hasta"].unique(),
                        reverse=True),key="3w_date")
                    p=p[p["fecha_hasta"]==when]
                    plot(rank_bars(p,label="sector",
                        value="organizaciones_distintas",limit=10,
                        units="Socios por sector",formats=".0f"),height=275)
                st.caption("No sumar sectores: los socios pueden repetirse.")
        with r:
            with card("Financiación de apelaciones",
                "Monto y cobertura exclusivamente de planes identificados.",
                "OCHA / FTS a través de HAPI",height=CARD):
                fund=filtered(D["funding"],selected)
                if fund.empty:empty("financiación de apelaciones")
                else:
                    iso=st.selectbox("País con registros",sorted(fund["iso3"].unique()),
                         format_func=lambda c:names.get(c,c),key="fts_country")
                    f=fund[fund["iso3"]==iso].copy()
                    f=f[f["appeal_code"].fillna("").str.lower()!="not specified"]
                    f["anio"]=f["reference_period_start"].astype(str).str[:4]
                    f=f[f["anio"].str.isdigit() &
                        (f["anio"].fillna("9999").astype(int)<=pd.Timestamp.today().year)]
                    if f.empty:empty("apelaciones identificadas")
                    else:
                        yy=st.selectbox("Año",sorted(f["anio"].unique(),reverse=True),
                            key="fts_year")
                        f=f[f["anio"]==yy]
                        data_table(f,height=250,cols=["appeal_name",
                            "requirements_usd","funding_usd","funding_pct"],
                            ren={"appeal_name":"Apelación",
                                "requirements_usd":"Requerido USD",
                                "funding_usd":"Financiado USD",
                                "funding_pct":"Cobertura (%)"})
                st.caption("No equivale a toda la financiación humanitaria recibida.")

def profile(D,selected,names,months):
    title("05 / PAÍS","Ficha integral de país",
          "Síntesis por dimensión, evidencias originales, tendencias "
          "y vacíos que requieren revisión técnica.")
    iso=st.selectbox("País",sorted(selected,key=lambda c:names.get(c,c)),
        format_func=lambda c:names.get(c,c),key="country_profile")
    crisis=filtered(D["severity"],{iso})
    risk=filtered(D["risk"],{iso})
    conflict=only_conflict(D,{iso},months)
    reports=recent_reports(D,{iso})
    a,b,c=st.columns(3)
    a.metric("Riesgo INFORM · Mid 2026",
             f"{risk['puntuacion'].iloc[0]:.1f} / 10" if not risk.empty else "Sin dato")
    b.metric("Contextos evaluados ACAPS",
             crisis["crisis_id"].nunique() if not crisis.empty else 0)
    c.metric("Informes · últimos 90 días",
             reports["reporte_id"].nunique() if not reports.empty else 0)
    l,r=st.columns(2)
    with l:
        with card("Contextos y gravedad documentada",
             "Situaciones ACAPS por separado, nunca prioridad OPS.",
             "ACAPS INFORM Severity",height=CARD):
            if crisis.empty:empty("contextos evaluados")
            else:
                data_table(crisis,height=340,
                    cols=["crisis","puntuacion","categoria","drivers"],
                    ren={"crisis":"Situación",
                         "puntuacion":"Severidad / 10",
                         "categoria":"Categoría ACAPS",
                         "drivers":"Descriptores"})
    with r:
        with card("Eventos de violencia política",
            f"Últimos {months} meses; eventos mensuales reportados.",
            "OCHA HAPI / ACLED",height=CARD):
            if conflict.empty:empty("violencia política")
            else:
                plot(trend(conflict,x="fecha",y="eventos",
                    units="Eventos/mes"),height=315)
    l,r=st.columns(2)
    with l:
        with card("Poblaciones y necesidades",
            "Registros disponibles para este país, con su periodo propio.",
            "HAPI Humanitarian Needs / ACNUR",height=440):
            needs=valid_needs(filtered(D["needs"],{iso}))
            un=filtered(D["acnur"],{iso},"asilo_iso3")
            if not needs.empty:
                needs=needs.sort_values("reference_period_start",ascending=False)
                row=needs.iloc[0]
                st.metric("PiN intersectorial · corte disponible",
                  f"{row['population']:,.0f}" if pd.notna(row["population"]) else "—")
                st.caption("Referencia: "+str(row["reference_period_start"])[:10])
            else:st.caption("Sin estimación intersectorial PiN comparable.")
            if not un.empty:
                st.markdown("**Refugio y asilo**")
                st.caption("Registrados por acogida; no son flujos nuevos.")
                data_table(un.head(6),height=175,
                    cols=["origen_iso3","grupo_poblacion","anio","personas"],
                    ren={"origen_iso3":"Origen","grupo_poblacion":"Grupo",
                         "anio":"Año","personas":"Personas"})
            else:st.caption("Sin registros ACNUR de acogida.")
    with r:
        with card("Capacidad sanitaria · datos OPS",
            "Última medición disponible de cada indicador; los años varían.",
            "OPS Indicadores Básicos",height=440):
            op=filtered(D["ops"],{iso})
            if op.empty:empty("capacidad sanitaria")
            else:
                latest=op.sort_values("periodo").drop_duplicates("indicador",keep="last")
                latest=latest[latest["indicador"].isin(["Médicos","Enfermería",
                    "Camas hospitalarias","DTP3","SRP1"])]
                data_table(latest,height=275,
                  cols=["indicador","periodo","valor"],
                  ren={"indicador":"Indicador","periodo":"Año","valor":"Valor"})
    with st.expander("Informes originales y evaluación de acceso"):
        if not reports.empty:
            docs=reports.head(12).copy()
            docs["Fecha"]=docs["fecha_publicacion_rw"].astype(str).str[:10]
            data_table(docs,height=300,
                 cols=["Fecha","titulo","url"],
                 ren={"titulo":"Informe","url":"Documento"},link="Documento")
        access=filtered(D["access"],{iso})
        if not access.empty:
            st.markdown("**Acceso humanitario ACAPS**")
            data_table(access,height=215,
                cols=["crisis","acceso","corte_api"],
                ren={"crisis":"Contexto","acceso":"Índice / 5",
                     "corte_api":"Corte"})
    st.caption("La clasificación crítico/alto/elevado/moderado y las "
               "reglas de seguimiento OPS quedan pendientes de validación de "
               "Laura y el equipo PHE.")

def quality(D,selected):
    with st.expander("Cobertura, fechas y límites metodológicos",expanded=False):
        st.caption("Una fuente puede tener registros en un país y no en otro. "
            "La actualización del repositorio no garantiza que el proveedor "
            "haya publicado un nuevo año o nueva evaluación.")
        data_table(cover_notes(D,selected),height=260)
        meta=D.get("acaps_meta",{})
        last=meta.get("fecha_utc","—")
        hapi=D.get("hapi_context_meta",{}).get("fecha_extraccion_utc","—")
        relief=D.get("reports_meta",{}).get("fecha_utc","—")
        st.caption(f"Última extracción registrada: ACAPS {str(last)[:10]}; "
                   f"HAPI contexto {str(hapi)[:10]}; "
                   f"ReliefWeb {str(relief)[:10]}.")
        st.markdown("[Documentación de fuentes y limitaciones]"
                    "(https://github.com/ivanromero0724/"
                    "observatorio-humanitario-ops/blob/main/"
                    "docs/fase2/arquitectura_indicadores_dashboard.md)")
        st.caption("Crimen organizado, economías ilícitas, ataques contra "
            "servicios de salud y afecciones de servicios esenciales todavía "
            "no cuentan con series completas validadas. "
            "No se presentan valores inventados.")

def main():
    st.set_page_config(page_title="Observatorio humanitario | OPS/OMS",
      page_icon="🌎",layout="wide",initial_sidebar_state="expanded")
    apply_style()
    st.markdown(CSS,unsafe_allow_html=True)
    D=load_all()
    countries=D["countries"]
    if countries.empty:
        st.error("Falta el catálogo de países.")
        st.stop()
    names=countries.set_index("iso3")["pais"].to_dict()
    with st.sidebar:
        st.markdown("### OPS / OMS")
        st.caption("Emergencias en Salud · Américas")
        page=st.radio("Secciones",PAGES,key="nav")
        st.divider()
        region=st.selectbox("Subregión",["Todas las Américas"]+
            sorted(countries["subregion"].unique()),key="region")
        regional=countries if region=="Todas las Américas" else countries[
            countries["subregion"]==region]
        options=sorted(regional["iso3"],key=lambda c:names.get(c,c))
        country=st.selectbox("Ámbito",["Todos los países"]+options,
          format_func=lambda c:names.get(c,c),key="scope")
        selected=set(options) if country=="Todos los países" else {country}
        months=st.selectbox("Periodo de eventos",[12,24,36],
            format_func=lambda n:f"Últimos {n} meses",key="months")
        st.caption(f"Ámbito: {len(selected)} países. "
                   "Cada fuente conserva su periodo original.")
    ops_header()
    if page==PAGES[0]:situations(D,selected,names,months)
    elif page==PAGES[1]:threats(D,selected,names,months)
    elif page==PAGES[2]:impacts(D,selected,names)
    elif page==PAGES[3]:vulnerability(D,selected,names)
    else:profile(D,selected,names,months)
    quality(D,selected)
    ops_footer()

if __name__=="__main__":
    main()
