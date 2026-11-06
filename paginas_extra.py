"""Páginas temáticas ampliadas: acceso humanitario y reportes.

Estas vistas consumen únicamente snapshots completados por GitHub Actions.
No consultan API en tiempo de visualización ni necesitan secretos en Streamlit.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st
from ui_ops import OPS, BLUE, ORANGE, map_countries
from graficos import finish as chart_finish,rank_bars,trend

PILLARS = {
    "pilar_1": "Acceso de las personas a la asistencia",
    "pilar_2": "Acceso de las organizaciones humanitarias",
    "pilar_3": "Restricciones físicas, ambientales y de seguridad",
}
COLOR = "#0072CE"

def _plot(fig,height=390):
    fig=chart_finish(fig,height=height)
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

def _source_note(source,cut,detail=""):
    st.caption(f"Fuente: {source}. Corte: {cut}. {detail}")

def access_page(access:pd.DataFrame,severity:pd.DataFrame,
                security_meta:dict,countries:pd.DataFrame,
                selected:set[str],acaps_meta:dict):
    st.markdown('<div class="ops-kicker">03 / ENTORNO OPERATIVO</div>'
                '<div class="ops-section">Seguridad y acceso humanitario</div>',
                unsafe_allow_html=True)
    st.caption("La accesibilidad humanitaria se evalúa por contexto o crisis. "
               "No confundir el índice de acceso con un indicador de ataques "
               "contra trabajadores humanitarios.")
    if access.empty:
        st.warning("Todavía no existe un snapshot completo y validado de ACAPS Humanitarian Access.")
    else:
        df=access[access["iso3"].isin(selected)].copy()
        df["acceso"]=pd.to_numeric(df["acceso"],errors="coerce")
        pillars=list(PILLARS)
        for c in pillars+[f"indicador_{i}" for i in range(1,10)]:
            if c in df:df[c]=pd.to_numeric(df[c],errors="coerce")
        a,b,c,d=st.columns(4)
        a.metric("Países incluidos",len(selected))
        b.metric("Países con contexto ACAPS",df["iso3"].nunique())
        c.metric("Contextos con evaluación",df["crisis_id"].nunique())
        d.metric("Corte ACAPS",str(df["corte_api"].iloc[0]) if len(df) else "Sin datos")
        if len(df):
            cols=st.columns([1.3,1],gap="large")
            with cols[0]:
                st.markdown("#### Disponibilidad del índice de acceso por país")
                idx=countries[countries["iso3"].isin(selected)][["iso3","pais","subregion"]].copy()
                idx["Disponibilidad"]=idx["iso3"].isin(set(df["iso3"])).map(
                    {True:"Con registros",False:"Sin registros en catálogo"})
                map_countries(idx,"Disponibilidad","Cobertura ACAPS",categorical=True)
            with cols[1]:
                st.markdown("#### Contextos con mayores restricciones reportadas")
                top=df.dropna(subset=["acceso"]).sort_values("acceso",ascending=False).head(13).copy()
                top["etiqueta"]=top["crisis"].fillna("Crisis")+" · "+top["pais"].fillna(top["iso3"])
                fig=rank_bars(top,label="etiqueta",value="acceso",limit=13,
                     color=ORANGE,units="Restricción de acceso / 5",max_x=5.3)
                _plot(fig,height=520)
            st.caption("El índice de acceso ACAPS se interpreta por contexto. Un país "
                "puede aparecer en varias crisis; no sumamos sus puntuaciones.")
            st.markdown("#### Componentes del acceso humanitario")
            choices=sorted(df["iso3"].unique())
            country=st.selectbox("País / país asociado",choices,
                format_func=lambda v:countries.set_index("iso3").loc[v,"pais"],
                key="acaps_access_country")
            sub=df[df["iso3"]==country].copy()
            crises=list(sub["crisis_id"].astype(str))
            crisis=st.selectbox("Contexto evaluado",crises,
                format_func=lambda v:str(sub.loc[sub["crisis_id"].astype(str)==v,"crisis"].iloc[0]),
                key="acaps_access_crisis")
            rec=sub[sub["crisis_id"].astype(str)==crisis].iloc[0]
            a,b,c=st.columns(3)
            for (code,label),box in zip(PILLARS.items(),[a,b,c]):
                v=rec.get(code)
                box.metric(label,
                    f"{float(v):.1f}" if pd.notna(v) else "Sin dato")
            indicators=[{"Indicador":f"I{i}","Puntuación":rec.get(f"indicador_{i}")}
                        for i in range(1,10)]
            ind=pd.DataFrame(indicators)
            ind["Puntuación"]=pd.to_numeric(ind["Puntuación"],errors="coerce")
            plotted=ind.dropna(subset=["Puntuación"])
            if not plotted.empty:
                fig=rank_bars(plotted,label="Indicador",value="Puntuación",
                              limit=9,color=BLUE,units="Escala del proveedor")
                _plot(fig,340)
            st.caption("I1–I9 mantienen las claves técnicas de ACAPS. Las definiciones "
                       "y escalas deben leerse con el codebook original; no son "
                       "índices OPS y no se agregan en un puntaje propio.")
            _source_note("ACAPS Humanitarian Access",str(rec["corte_api"]),
                         "Exclusivamente contextos incluidos en la evaluación.")
    st.divider()
    st.markdown("#### Seguridad de trabajadores humanitarios · AWSD")
    status=None
    for source in security_meta.get("resultados",[]):
        if source.get("fuente")=="AWSD":status=source
    if status and status.get("estado")=="CONECTADO":
        st.info("Acceso AWSD validado. La integración estadística de incidentes "
                "requiere descargar la serie completa y revisar licencias.")
    elif status and status.get("secreto_configurado"):
        st.warning("La clave AWSD está guardada en GitHub, pero todavía no se ha "
                   "confirmado el endpoint de descarga JSON. No se presentan "
                   "incidentes ni totales hasta validar la respuesta.")
    else:
        st.info("AWSD aún no está integrada. Se presentarán incidencias graves "
                "contra personal humanitario cuando se valide la API.")
    st.markdown("[Fuente AWSD](https://www.aidworkersecurity.org/) "
                "· [ACAPS – acceso humanitario](https://www.acaps.org/en/thematics/all-topics/humanitarian-access-overview)")
    st.caption("ACAPS discontinuó la recopilación de 'Humanitarian Access Events' "
               "el 31 de julio de 2026; por tanto, no debe presentarse como "
               "serie de incidentes en tiempo real.")

def reports_page(reports:pd.DataFrame,meta:dict,
                 countries:pd.DataFrame,selected:set[str]):
    st.markdown('<div class="ops-kicker">06 / INFORMACIÓN OPERACIONAL</div>'
                '<div class="ops-section">Reportes y situaciones humanitarias</div>',
                unsafe_allow_html=True)
    st.caption("Documentos catalogados en ReliefWeb y enlazados a su fuente "
               "original. Un reporte puede estar asociado a varios países. "
               "La cantidad de reportes NO equivale a gravedad, magnitud de "
               "una emergencia ni personas afectadas.")
    if reports.empty:
        st.warning("La extracción de ReliefWeb aún no ha sido completada o publicada.")
        return
    sub=reports[reports["iso3"].isin(selected)].copy()
    if sub.empty:
        st.info("No hay reportes asociados a los países del filtro "
                "en la ventana temporal definida.")
        return
    options=sorted(sub["iso3"].unique())
    chooser=[None]+options
    iso=st.selectbox("País",chooser,format_func=lambda v:
       "Todos los países seleccionados" if v is None else
       countries.set_index("iso3").loc[v,"pais"],key="reliefweb_country")
    if iso:sub=sub[sub["iso3"]==iso]
    unique=sub.drop_duplicates("reporte_id").copy()
    theme_options=sorted(set(t.strip() for s in unique["temas"].dropna()
                          for t in str(s).split(" | ") if t.strip()))
    if theme_options:
        theme=st.selectbox("Tema del reporte",["Todos"]+theme_options)
        if theme!="Todos":
            unique=unique[unique["temas"].fillna("").str.contains(
                theme,regex=False)]
    search=st.text_input("Buscar en títulos","",key="report_search")
    if search.strip():
        unique=unique[unique["titulo"].fillna("").str.contains(
            search.strip(),case=False,regex=False)]
    a,b,c,d=st.columns(4)
    a.metric("Países en filtro",sub["iso3"].nunique())
    b.metric("Reportes únicos",unique["reporte_id"].nunique())
    c.metric("Organizaciones editoras",unique["fuentes"].nunique())
    d.metric("Ventana de extracción",f"{meta.get('ventana_dias','—')} días")
    st.markdown('<div class="ops-divider"></div>',unsafe_allow_html=True)
    l,r=st.columns([1.05,1],gap="large")
    with l:
        st.markdown("#### Publicaciones por semana")
        by_week=(unique.dropna(subset=["fecha_dt"])
                 .groupby(pd.Grouper(key="fecha_dt",freq="W-MON"))["reporte_id"]
                 .nunique().reset_index(name="reportes"))
        if not by_week.empty:
            fig=trend(by_week,x="fecha_dt",y="reportes",
                      units="Reportes únicos",area=True)
            _plot(fig,360)
    with r:
        st.markdown("#### Fuentes más frecuentes")
        orgs=(unique.assign(organizacion=unique["fuentes"].fillna("").str.split(" | ",regex=False))
              .explode("organizacion"))
        orgs=orgs[orgs["organizacion"].notna() & (orgs["organizacion"]!="")]
        top=(orgs.groupby("organizacion")["reporte_id"].nunique()
             .nlargest(10).sort_values().reset_index(name="reportes"))
        if not top.empty:
            fig=rank_bars(top,label="organizacion",value="reportes",
                         limit=10,color=BLUE,units="Reportes",formats=".0f")
            _plot(fig,360)
    st.markdown("#### Documentos y enlaces originales")
    shown=unique.sort_values("fecha_dt",ascending=False).copy()
    shown["Fecha"]=shown["fecha_publicacion_rw"].astype(str).str[:10]
    table=shown[["Fecha","titulo","fuentes","temas","formatos","url"]].rename(
         columns={"titulo":"Título","fuentes":"Organización",
                  "temas":"Tema","formatos":"Formato","url":"Abrir reporte"})
    st.dataframe(table,use_container_width=True,hide_index=True,height=510,
         column_config={"Abrir reporte":st.column_config.LinkColumn(
             "Documento original",display_text="Abrir"),
             "Título":st.column_config.TextColumn("Título",width="large")})
    st.download_button("Descargar listado filtrado CSV",
        table.to_csv(index=False).encode("utf-8-sig"),
        file_name="reliefweb_reportes_filtrados.csv",mime="text/csv")
    _source_note("ReliefWeb, OCHA",f"{meta.get('desde_utc','—')} a {meta.get('fecha_utc','—')}",
                 "Metadatos y enlaces; no se redistribuye el contenido de informes.")
