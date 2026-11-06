"""Observatorio Humanitario OPS/OMS | Mandato Mauricio Cerpa + propuesta 05-nov-2026.

FASE 1: violencia y conflicto; migración y desplazamiento forzado;
restricciones al acceso y entorno humanitario. Crimen organizado y fragilidad
sociopolítica son líneas para validación con Laura, no indicadores inventados.
No se priorizan brotes, fenómeno El Niño ni desastres naturales.
NO EXISTE clasificación propia OPS ni alerta automática.
"""
from __future__ import annotations

import base64
import html
import math
from pathlib import Path

import branca.colormap as bcm
import folium
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from observatorio_v2 import (
    load_all, filtered, valid_needs, latest_ops, OPS_LABELS, HAPI_TYPES,
)
from observatorio_v4 import (
    STYLES, esc, fmt, card, plot, table, info_missing,
    crisis_table, change_signals, conflict_complete_window,
    reports, health_paths, evidence_table, briefing_text,
)
from ui_ops import geography, BASE as UI_BASE
from graficos import rank_bars, trend, strip_countries

NAVY="#004B87"
BLUE="#0072CE"
ORANGE="#F39200"
TEAL="#008C95"
SLATE="#687C8C"
BORDER="#D7E2EA"
CARD_H=545
PAGES=[
    "Mapa y seguimiento regional",
    "Violencia, conflicto y acceso",
    "Migración y desplazamiento",
    "Vulnerabilidad y respuesta",
    "Perfil humanitario por país",
]
MAP_METRICS={
    "Violencia política · últimos 12 meses":"political_violence",
    "Ataques contra civiles · últimos 12 meses":"civilian_targeting",
    "Severidad de las crisis evaluadas · ACAPS":"acaps_severity",
}
UX_CSS="""
<style>
/* Rectangular PAHO executive layout. Avoid asymmetric widget stretching. */
.obs-hero{background:linear-gradient(111deg,#004B87 0%,#0066AA 78%,#0086BA 100%)!important}
.obs-hero .main{font-size:1.69rem!important;letter-spacing:-.026em!important}
.obs-hero .sub{max-width:820px!important}
.obs-phase{font:780 .69rem Arial,sans-serif;letter-spacing:.13em;
 color:#0072CE;text-transform:uppercase;margin-top:13px}
.obs-page{font:770 1.57rem/1.25 Arial,sans-serif;color:#004B87;
 letter-spacing:-.03em;margin:5px 0}
.obs-lead{font:.87rem/1.5 Arial,sans-serif;color:#66798A;
 margin:0 0 16px}
.obs-card-title{font-size:1.04rem!important}
.obs-card-sub{font-size:.79rem!important;min-height:36px!important}
.obs-scope{display:flex;align-items:center;gap:10px;flex-wrap:wrap;
 margin:5px 0 12px}
.obs-tag{border-radius:5px;border:1px solid #D2E5F0;
 padding:4px 8px;color:#004B87;background:#F0F7FB;
 font:700 .71rem Arial,sans-serif}
.obs-tag-muted{border-color:#E3E9ED;background:#F8FAFC;color:#667B88}
.obs-brief{border-left:3px solid #F39200;background:#FFF9F0;
 padding:11px 15px;border-radius:0 8px 8px 0;
 color:#344D5E;font:.84rem/1.5 Arial,sans-serif;
 margin:9px 0 13px}
[data-testid="stMetric"]{min-height:102px!important}
[data-testid="stHorizontalBlock"]{align-items:stretch!important}
</style>
"""

def title(number,headline,description):
    st.markdown(f'<div class="obs-phase">{esc(number)}</div>'
      f'<div class="obs-page">{esc(headline)}</div>'
      f'<div class="obs-lead">{esc(description)}</div>',
      unsafe_allow_html=True)

def header():
    logo=Path(UI_BASE)/"assets/ops_oms.png"
    im=""
    if logo.is_file():
        b=base64.b64encode(logo.read_bytes()).decode("ascii")
        im=f'<img class="brand" alt="OPS / OMS" src="data:image/png;base64,{b}">'
    st.markdown(f"""<div class="obs-hero">
      <div style="z-index:1;position:relative">
        <div class="eyebrow">OPS / OMS · Emergencias en Salud · PHE</div>
        <div class="main">Observatorio Regional de Amenazas y Vulnerabilidad Humanitaria</div>
        <div class="sub">Violencia y conflicto · migración y desplazamiento forzado ·
          acceso humanitario · vulnerabilidad y capacidad de respuesta</div>
      </div>{im}</div>""",unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def list_months(period,months=12):
    if pd.isna(period):return []
    last=pd.Timestamp(period).to_period("M")
    return [(last-i).to_timestamp() for i in range(months-1,-1,-1)]

def common_last(D,cat):
    df=D["conflict"]
    if df.empty:return None
    sub=df[(df["tipo_evento"]==cat)&df["fecha"].notna()]
    if sub.empty:return None
    return sub["fecha"].max()

def events_by_country(D,chosen,category="political_violence",months=12):
    """Country counts in the SAME N months, only complete country-month coverage.

    An observed zero is retained as zero. A missing month makes result NA.
    """
    df=filtered(D["conflict"],chosen)
    out=pd.DataFrame({"iso3":sorted(chosen)})
    out["eventos"]=float("nan")
    cut=common_last(D,category)
    if cut is None:return out,None
    expected=list_months(cut,months)
    f=df[df["tipo_evento"].eq(category)&df["fecha"].isin(expected)].copy()
    if f.empty:return out,cut
    g=f.groupby(["iso3","fecha"],as_index=False).agg(
        eventos=("eventos",lambda v:v.sum(min_count=1)))
    coverage=g.groupby("iso3")["fecha"].nunique()
    eligible=set(coverage[coverage==months].index)
    total=g[g["iso3"].isin(eligible)].groupby("iso3")["eventos"].sum(min_count=1)
    out["eventos"]=out["iso3"].map(total)
    return out,cut

def crisis_core(D,chosen):
    """Fase 1: ACAPS con componentes de conflicto, movilidad o entorno político.

    Crisis exclusivamente por terremoto/ciclón/inundación se excluyen de la
    portada inicial, pero se conservan en los snapshots para fase posterior.
    Crisis mixtas se mantienen por su driver humanitario relevante.
    """
    frame=crisis_table(D,chosen)
    if frame.empty:return frame
    pattern=r"conflict|violence|displacement|political|economic|insecurity"
    return frame[frame["drivers"].fillna("").str.contains(
        pattern,case=False,regex=True)].copy()

def oim_scope(df):
    """Mantener conflicto/inseguridad y causa no informada; excluir desastres.

    Las filas sin causa se identifican en tablas, nunca se asume desplazamiento
    forzado. Los 37 registros de desastres naturales se conservan en el CSV.
    """
    if df.empty:return df
    return df[df["causa_desplazamiento"].fillna("").astype(str)
        .str.lower().ne("natural disaster")].copy()

def summary_countries(D,chosen):
    """One row per country; independent dimensions with explicit missing values."""
    allc=filtered(D["countries"],chosen)[["iso3","pais","subregion"]].copy()
    if allc.empty:return allc
    violent,cut=events_by_country(D,chosen,"political_violence",12)
    allc=allc.merge(violent,on="iso3",how="left")
    sv=crisis_core(D,chosen)
    if not sv.empty:
        by=sv.groupby("iso3").agg(
            crisis_count=("crisis_id","nunique"),
            severity_max=("puntuacion","max"),
            access_max=("acceso","max"))
        allc=allc.join(by,on="iso3")
    else:
        for x in ("crisis_count","severity_max","access_max"):
            allc[x]=float("nan")
    signals=change_signals(D,chosen,"political_violence")
    if not signals.empty:
        allc=allc.join(signals.set_index("iso3")["cambio"].rename(
            "delta_3m"),on="iso3")
    else:allc["delta_3m"]=float("nan")
    un=filtered(D["acnur"],chosen,"asilo_iso3")
    allc["refugio_datos"]=allc["iso3"].isin(set(un["asilo_iso3"])) if not un.empty else False
    dtm=oim_scope(filtered(D["dtm"],chosen))
    allc["dtm_datos"]=allc["iso3"].isin(set(dtm["iso3"])) if not dtm.empty else False
    needs=filtered(D["needs"],chosen)
    allc["pin_datos"]=allc["iso3"].isin(set(
        valid_needs(needs)["iso3"])) if not needs.empty else False
    return allc

def display_comparison(frame,sort):
    if frame.empty:return frame
    f=frame.copy()
    keys={
        "Eventos de violencia (12 meses)":("eventos",False),
        "Cambio reciente de violencia (3 meses)":("delta_3m",False),
        "Mayor severidad de crisis ACAPS":("severity_max",False),
        "País (A–Z)":("pais",True)
    }
    col,asc=keys[sort]
    f=f.sort_values([col,"pais"],ascending=[asc,True],na_position="last")
    f["País"]=f["pais"]
    f["Violencia · 12m"]=f["eventos"].map(lambda v:fmt(v) if pd.notna(v) else "Sin dato")
    f["Δ eventos · 3m"]=f["delta_3m"].map(
        lambda v:f"{int(v):+d}" if pd.notna(v) else "Sin serie")
    f["Crisis ACAPS"]=f["crisis_count"].map(
        lambda v:str(int(v)) if pd.notna(v) else "Sin evaluación")
    f["Severidad ACAPS /10"]=f["severity_max"].map(
        lambda v:fmt(v,1) if pd.notna(v) else "—")
    f["Acceso ACAPS /5"]=f["access_max"].map(
        lambda v:fmt(v,1) if pd.notna(v) else "—")
    f["Refugio (datos)"]=f["refugio_datos"].map({True:"Sí",False:"Sin registros"})
    f["OIM (datos)"]=f["dtm_datos"].map({True:"Sí",False:"Sin registros"})
    return f[["País","Violencia · 12m","Δ eventos · 3m",
              "Crisis ACAPS","Severidad ACAPS /10","Acceso ACAPS /5",
              "Refugio (datos)","OIM (datos)"]]

def pa_map(frame,mode,legend_title,height=428):
    """Map actual values, keeping missing and documented zero distinct.

    Color shades for events are continuous on log1p scale, descriptive only.
    Does not use normalized OPS priorities or interpret colors as alert levels.
    """
    geo=geography()
    if geo is None or geo.empty:
        info_missing("geografía regional")
        return
    col=frame[["iso3","pais","valor"]].drop_duplicates("iso3").copy()
    geo=geo.merge(col,left_on="ISO_CC",right_on="iso3",how="left")
    geo["nombre"]=geo["pais"].fillna(geo["COUNTRY"])
    x=pd.to_numeric(geo["valor"],errors="coerce")
    maximum=max(float(x.max()),1) if x.notna().any() else 1
    linear=bcm.LinearColormap(["#D9EDF8","#8BC9E7","#268DC7","#004B87"],vmin=0,vmax=1)
    if mode=="severity":
        geo["hex"]=x.map(lambda v:linear(float(v)/10) if pd.notna(v) else "#CED8E0")
    else:
        den=math.log1p(maximum)
        geo["hex"]=x.map(lambda v:
            ("#ECF3F8" if v==0 else linear(math.log1p(float(v))/den))
            if pd.notna(v) else "#CED8E0")
    geo["valor_texto"]=x.map(
        lambda v:(fmt(v,1)+"/10" if mode=="severity" else fmt(v)+" eventos")
        if pd.notna(v) else "Sin información comparable")
    m=folium.Map(location=[7,-89],zoom_start=2,tiles=None,zoom_control=True,
                 min_zoom=1,max_zoom=7,prefer_canvas=True,height=height)
    # La extensión completa de las Américas debe verse sin pan inicial.
    m.fit_bounds([[-59,-169],[83,-24]],padding=(14,14))
    m.get_root().html.add_child(folium.Element(
        "<style>.leaflet-container{background:#EAF4F8!important}"
        ".leaflet-tooltip{border:1px solid #D7E2EA;border-radius:8px;"
        "font:12px Arial,sans-serif;color:#19374D;padding:7px}</style>"))
    folium.GeoJson(
       geo.to_json(drop_id=True),
       style_function=lambda f:{"fillColor":f["properties"]["hex"],
         "color":"white","weight":.8,"fillOpacity":.98},
       highlight_function=lambda f:{"weight":1.8,"color":"#004B87"},
       tooltip=folium.GeoJsonTooltip(
         fields=["nombre","valor_texto"],aliases=["País:","Indicador:"],
         labels=True,sticky=True),
    ).add_to(m)
    legend=(
        '<div style="position:absolute;z-index:9999;bottom:17px;left:16px;'
        'background:white;border:1px solid #D7E2EA;border-radius:8px;'
        'padding:10px 12px;font:11px Arial;color:#19374D;max-width:240px;">'
        f'<strong>{esc(legend_title)}</strong>'
        '<div style="margin-top:5px;display:flex;align-items:center;gap:6px">'
        '<span style="width:95px;height:9px;display:inline-block;'
        'background:linear-gradient(90deg,#D9EDF8,#8BC9E7,#268DC7,#004B87);"></span>'
        '<span>menor → mayor</span></div>'
        '<div style="margin-top:5px">'
        '<span style="display:inline-block;width:9px;height:9px;'
        'background:#CED8E0;margin-right:5px"></span>Sin dato'
        +(' · escala logarítmica descriptiva' if mode!="severity"
          else ' · escala ACAPS 0–10')+
        '</div></div>')
    m.get_root().html.add_child(folium.Element(legend))
    components.html(m.get_root().render(),height=height+12,scrolling=False)

def map_frame(D,frame,choice):
    if choice=="Violencia política · últimos 12 meses":
        return frame[["iso3","pais","eventos"]].rename(columns={"eventos":"valor"}),"events"
    if choice=="Ataques contra civiles · últimos 12 meses":
        v,_=events_by_country(D,set(frame["iso3"]),"civilian_targeting",12)
        out=frame[["iso3","pais"]].merge(v,on="iso3",how="left").rename(
            columns={"eventos":"valor"})
        return out,"events"
    return frame[["iso3","pais","severity_max"]].rename(
        columns={"severity_max":"valor"}),"severity"

def map_page(D,selected,names):
    title("01 / MAPEO Y SEGUIMIENTO",
          "Mapa de situaciones humanitarias en las Américas",
          "Qué países presentan eventos documentados, cómo cambian y en cuáles "
          "hay evaluaciones de crisis. Los indicadores se interpretan por separado.")
    frame=summary_countries(D,selected)
    latest=common_last(D,"political_violence")
    sv=crisis_table(D,selected)
    inc=change_signals(D,selected)
    a,b,c,d=st.columns(4,gap="small")
    a.metric("Países en el análisis",len(selected))
    b.metric("Con datos de violencia · 12m",int(frame["eventos"].notna().sum()))
    c.metric("Con crisis evaluadas ACAPS",
        int(frame["crisis_count"].notna().sum()))
    d.metric("Con aumento reciente de eventos",
        f"{int((inc['cambio']>0).sum())}/{len(inc)}" if not inc.empty else "—",
        help="Comparación descriptiva 3 meses frente a los 3 anteriores; "
             "no es una alerta ni implica asistencia necesaria.")
    st.caption("Una cifra de eventos no equivale a población afectada ni a necesidad de apoyo. "
               "El tablero no asigna una prioridad humanitaria OPS.")
    left,right=st.columns([1.18,.92],gap="medium")
    with left:
        with card("Distribución territorial",
            "Mapa temático por indicador original. Gris: sin registro comparable; "
            "cero documentado se diferencia de dato ausente.",
            "OCHA HAPI / ACLED o ACAPS · unidades distintas",height=645):
            choice=st.selectbox("Indicador del mapa",list(MAP_METRICS),
                key="regional_map_choice")
            mv,mode=map_frame(D,frame,choice)
            pa_map(mv,mode,choice,height=434)
            cutoff=(latest.strftime("%Y-%m") if latest is not None else "—")
            st.caption(f"Corte de violencia política en HAPI: {cutoff}. "
                "Los colores muestran magnitud dentro de este indicador; "
                "no representan categorías de prioridad OPS.")
    with right:
        with card("Países para revisar",
            "Tabla comparativa; el orden se puede cambiar, pero no determina "
            "necesidad de asistencia ni prioridad OPS.",
            "ACAPS y HAPI · misma ventana para eventos",height=645):
            sorting=st.selectbox("Ordenar por",[
                "Eventos de violencia (12 meses)",
                "Cambio reciente de violencia (3 meses)",
                "Mayor severidad de crisis ACAPS",
                "País (A–Z)"],key="compare_sort")
            compact=display_comparison(frame,sorting)
            compact=compact[["País","Violencia · 12m","Δ eventos · 3m",
                             "Severidad ACAPS /10"]].rename(columns={
                "Violencia · 12m":"Eventos 12m",
                "Δ eventos · 3m":"Δ 3m",
                "Severidad ACAPS /10":"Sev. ACAPS"})
            table(compact,height=451)
            st.caption("Severidad = valor máximo entre crisis evaluadas; "
                       "no equivale a un índice humanitario nacional.")

    with st.expander("Ver la matriz completa por país y descargar CSV",expanded=False):
        complete=display_comparison(frame,sorting)
        table(complete,height=330)
        st.download_button("Descargar comparación por país (CSV)",
            complete.to_csv(index=False).encode("utf-8-sig"),
            file_name="ops_seguimiento_humanitario_paises.csv",
            mime="text/csv",key="regional_csv")
        st.caption("Campos de cobertura de datos ACNUR/OIM indican registros "
                   "disponibles, no presencia o ausencia del fenómeno.")
    a,b=st.columns([1,1],gap="medium")
    with a:
        with card("Evolución regional de violencia política",
            "Eventos reportados por HAPI/ACLED en una sola categoría, "
            "sin sumar categorías que se solapan.",
            "HAPI / ACLED agregado",height=465):
            d=conflict_complete_window(D,selected)
            if d.empty:info_missing("eventos de violencia")
            else:
                t=d.groupby("fecha",as_index=False)["eventos"].sum()
                t=t.sort_values("fecha").tail(18)
                plot(trend(t,x="fecha",y="eventos",
                    units="Eventos mensuales"),height=298)
                st.caption("Es una serie descriptiva, no una predicción "
                           "ni una medida de personas que necesitan apoyo.")
    with b:
        with card("Contextos de crisis que ya tienen evaluación",
            "ACAPS clasifica la gravedad de crisis específicas, "
            "no la prioridad operacional de cada país.",
            "ACAPS INFORM Severity · noviembre 2026",height=465):
            if sv.empty:info_missing("evaluaciones ACAPS")
            else:
                x=sv[["pais","crisis","puntuacion"]].head(10)
                table(x,height=316,columns=["pais","crisis","puntuacion"],
                    labels={"pais":"País","crisis":"Contexto evaluado",
                            "puntuacion":"Severidad / 10"})
    with st.expander("Documentos recientes de referencia",expanded=False):
        docs=reports(D,selected,limit=15)
        if docs.empty:info_missing("reportes recientes")
        else:
            docs["Fecha"]=docs["fecha_publicacion_rw"].astype(str).str[:10]
            table(docs,height=327,
                columns=["Fecha","titulo","fuentes","url"],
                labels={"titulo":"Informe","fuentes":"Organización",
                        "url":"Documento"},link="Documento")
            st.caption("ReliefWeb asocia reportes a países: no se asume que "
                       "cada documento esté vinculado a una crisis ACAPS.")

def violence_page(D,selected,names,months,category):
    title("02 / VIOLENCIA, CONFLICTO Y ACCESO",
        "Eventos violentos y restricciones humanitarias",
        "Monitoreo territorial de eventos y cambios temporales; acceso humanitario "
        "como condición contextual para la respuesta.")
    st.markdown(
      '<div class="obs-scope">'
      '<span class="obs-tag">Eventos y muertes · HAPI/ACLED</span>'
      '<span class="obs-tag">Acceso · ACAPS</span>'
      '<span class="obs-tag obs-tag-muted">Crimen organizado: fuentes por validar</span>'
      '</div>',unsafe_allow_html=True)
    d=conflict_complete_window(D,selected,category)
    last=common_last(D,category)
    if last is not None:
        d=d[d["fecha"].isin(list_months(last,months))].copy()
    left,right=st.columns(2,gap="medium")
    with left:
        with card("Evolución temporal de eventos",
            f"{HAPI_TYPES.get(category,category)} · {months} meses del mismo corte.",
            "OCHA HDX HAPI / ACLED",height=CARD_H):
            if d.empty:info_missing("eventos")
            else:
                series=d.groupby("fecha",as_index=False)["eventos"].sum()
                plot(trend(series,x="fecha",y="eventos",
                    units="Eventos reportados"),height=343)
                st.caption(f"Último mes consultado: {last.strftime('%Y-%m')}. "
                           "No se agrega con otras categorías ACLED.")
    with right:
        with card("Países según eventos de la misma categoría",
            "Comparación de registros; el volumen no es un nivel de "
            "riesgo institucional ni una tasa poblacional.",
            "OCHA HDX HAPI / ACLED",height=CARD_H):
            v,cut=events_by_country(D,selected,category,months)
            v=v.merge(D["countries"][["iso3","pais"]],on="iso3",how="left")
            fig=rank_bars(v.dropna(subset=["eventos"]),label="pais",
                value="eventos",limit=12,color=BLUE,
                units="Eventos",formats=".0f")
            plot(fig,height=340)
            st.caption(f"Países con {months} meses completos: {v['eventos'].notna().sum()}/"
                       f"{len(selected)}. Datos faltantes no se imputan.")
    st.write("")
    left,right=st.columns(2,gap="medium")
    with left:
        with card("Cambio reciente de eventos",
            "Tres meses más recientes comparados con los tres previos "
            "de la misma categoría y cobertura.",
            "HAPI / ACLED · variación descriptiva",height=CARD_H):
            signal=change_signals(D,selected,category)
            if signal.empty:info_missing("seis meses completos")
            else:
                view=signal[["pais","eventos_antes",
                              "eventos_recientes","cambio"]].head(13)
                table(view,height=362,
                  columns=["pais","eventos_antes","eventos_recientes","cambio"],
                  labels={"pais":"País","eventos_antes":"Antes · 3m",
                          "eventos_recientes":"Últimos · 3m",
                          "cambio":"Δ eventos"})
                st.caption("Un incremento señala cambio en registros, no prueba "
                           "una emergencia ni determina asistencia humanitaria.")
    with right:
        with card("Restricciones al acceso humanitario",
            "Gravedad del acceso evaluada por crisis (ACAPS); "
            "no medir automáticamente accesibilidad sanitaria.",
            "ACAPS Humanitarian Access",height=CARD_H):
            ac=filtered(D["access"],selected)
            if ac.empty:info_missing("evaluación de acceso")
            else:
                ac=ac.copy()
                ac["Contexto"]=ac["pais"]+" · "+ac["crisis"]
                plot(rank_bars(ac,label="Contexto",value="acceso",limit=10,
                         color=ORANGE,units="ACAPS / 5",max_x=5.3),
                     height=342)
                st.caption("Mayor valor = mayores restricciones según ACAPS. "
                           "No es una calificación de acceso OPS.")
    with st.expander("Otras amenazas del mandato: crimen organizado, economías ilícitas y tensiones políticas"):
        st.markdown("La propuesta incluye economías ilícitas, crimen organizado, "
            "minería ilegal, cultivos ilícitos, fragilidad y tensiones políticas. "
            "Todavía requieren que Laura valide definiciones y fuentes "
            "comparables (por ejemplo UNODC/GI-TOC). No presentar ceros, "
            "clasificaciones o eventos inventados.")

def migration_page(D,selected,names):
    title("03 / MIGRACIÓN Y DESPLAZAMIENTO",
        "Movilidad humana y afectaciones documentadas",
        "Separar refugiados, solicitantes de asilo, desplazamiento interno "
        "y necesidades de asistencia por fuente, categoría y fecha.")
    acnur=filtered(D["acnur"],selected,"asilo_iso3")
    dtm=oim_scope(filtered(D["dtm"],selected))
    needs=valid_needs(filtered(D["needs"],selected))
    a,b,c=st.columns(3,gap="medium")
    a.metric("Países con registros ACNUR",
             acnur["asilo_iso3"].nunique() if not acnur.empty else 0)
    b.metric("OIM DTM · países en fase 1",
             dtm["iso3"].nunique() if not dtm.empty else 0)
    c.metric("Países con PiN intersectorial",
             needs["iso3"].nunique() if not needs.empty else 0)
    st.caption("Estos son conteos de cobertura, no cifras de población. "
               "OIM excluye operaciones clasificadas como desastre natural "
               "del módulo inicial; las conserva en la base histórica. "
               "La causa no reportada nunca se interpreta como conflicto.")
    left,right=st.columns(2,gap="medium")
    with left:
        with card("Refugio y asilo · país de acogida y origen",
            "Población registrada por ACNUR vía HAPI; "
            "stocks anuales, no flujos nuevos.",
            "ACNUR / HAPI · total por sexo y edad",height=620):
            if acnur.empty:info_missing("ACNUR")
            else:
                hosts=sorted(acnur["asilo_iso3"].unique(),
                           key=lambda c:names.get(c,c))
                host=st.selectbox("País de acogida",hosts,
                    index=hosts.index("COL") if "COL" in hosts else 0,
                    format_func=lambda c:names.get(c,c),
                    key="migration_host")
                df=acnur[acnur["asilo_iso3"]==host].copy()
                year=st.selectbox("Año",sorted(df["anio"].astype(str)
                         .unique(),reverse=True),key="migration_year")
                df=df[df["anio"].astype(str)==str(year)]
                groups=sorted(df["grupo_poblacion"].dropna().unique())
                group=st.selectbox("Grupo",groups,
                    format_func=lambda x:{"REF":"Refugiados","ASY":"Solicitantes de asilo"}.get(x,x),
                    index=groups.index("REF") if "REF" in groups else 0,
                    key="migration_group")
                df=df[df["grupo_poblacion"]==group].copy()
                df["origen"]=df["origen_iso3"].map(names).fillna(df["origen_iso3"])
                plot(rank_bars(df,label="origen",value="personas",
                    limit=11,units="Personas registradas",formats=".0f"),
                    height=294)
                st.caption("Las categorías poblacionales se analizan por separado. "
                           "No se suman refugiados con solicitantes de asilo.")
    with right:
        with card("Desplazamiento interno · OIM DTM",
            "Última ronda reportada por operación: puede ser histórica y "
            "no equivale al número nacional actual de desplazados.",
            "OIM DTM Baseline · operación/ronda",height=620):
            if dtm.empty:info_missing("operaciones DTM")
            else:
                hosts=sorted(dtm["iso3"].unique(),key=lambda c:names.get(c,c))
                host=st.selectbox("País con datos DTM",hosts,
                    index=hosts.index("HTI") if "HTI" in hosts else 0,
                    format_func=lambda c:names.get(c,c),
                    key="migration_dtm_host")
                operations=dtm[dtm["iso3"]==host]
                op=st.selectbox("Operación",
                    sorted(operations["operacion"].dropna().unique()),
                    key="migration_dtm_operation")
                view=operations[operations["operacion"]==op].copy()
                st.caption(f"Fecha reportada: {view['fecha_reporte'].max()} "
                           f"· ronda: {view['ronda'].iloc[0]}")
                table(view,height=278,
                   columns=["origen_admin1","personas_idp_reportadas",
                           "hombres","mujeres"],
                   labels={"origen_admin1":"Área de origen",
                           "personas_idp_reportadas":"Personas reportadas",
                           "hombres":"Hombres","mujeres":"Mujeres"})
                st.caption("Causa del registro: "+
                           ", ".join(sorted(view["causa_desplazamiento"]
                               .dropna().astype(str).unique()))+
                           ". No sumar operaciones ni rondas diferentes; "
                           "una causa no reportada no demuestra desplazamiento forzado.")
    with card("Personas en necesidad de asistencia humanitaria",
       "Estimaciones PiN intersectoriales publicadas por OCHA cuando hay "
       "un único total nacional para el año. No sumar sectores ni periodos.",
       "OCHA HAPI Humanitarian Needs"):
        if needs.empty:info_missing("PiN intersectorial")
        else:
            frame=needs.copy()
            frame["anio"]=frame["reference_period_start"].astype(str).str[:4]
            conflict=frame.duplicated(["iso3","anio"],keep=False)
            frame=frame.loc[~conflict].sort_values("anio")
            frame=frame.drop_duplicates("iso3",keep="last")
            if frame.empty:info_missing("totales PiN inequívocos")
            else:
                frame["pais"]=frame["iso3"].map(names)
                plot(strip_countries(frame,name="pais",val="population",
                    year="anio",max_items=20,
                    units="Personas en necesidad"),height=365)
                st.caption("Los años son propios de cada país; estas "
                           "cifras no constituyen un total regional homogéneo.")

def vulnerability_page(D,selected,names):
    title("04 / ACCESO, VULNERABILIDAD Y RESPUESTA",
        "Factores que condicionan la respuesta humanitaria",
        "La vulnerabilidad social y la capacidad sanitaria contextualizan "
        "los eventos, pero no determinan automáticamente la prioridad OPS.")
    a,b=st.tabs(["Condiciones sociales y capacidad OPS",
                  "Presencia humanitaria y financiación"])
    with a:
        ops=filtered(D["ops"],selected)
        if ops.empty:info_missing("indicadores OPS")
        else:
            opts=["GINI","Escolaridad","Médicos","Enfermería",
                 "Camas hospitalarias","DTP3","SRP1"]
            available=[x for x in opts if x in set(ops["indicador"])]
            ind=st.selectbox("Indicador para comparar países",
                 available,format_func=lambda k:OPS_LABELS[k],
                 key="context_indicator")
            same=st.checkbox("Comparar únicamente un mismo año",value=False,
                 key="context_same_year")
            year=None
            if same:
                ys=sorted(ops[ops["indicador"]==ind]["periodo"].dropna()
                    .astype(int).unique(),reverse=True)
                year=st.selectbox("Año de referencia",ys,
                    key="context_year") if ys else None
            observed=latest_ops(ops,ind,year)
            l,r=st.columns([1.2,.8],gap="medium")
            with l:
                with card("Comparación territorial",
                    "Última observación disponible por país" if not same else
                    f"Comparación del año {year}.",
                    "OPS Indicadores Básicos",height=610):
                    if observed.empty:info_missing("indicador OPS")
                    else:
                        observed=observed.copy()
                        observed["anio"]=observed["periodo"].astype(int)
                        fig=strip_countries(observed,name="pais",
                              val="valor",year="anio",max_items=24,
                              units=OPS_LABELS[ind])
                        plot(fig,height=460)
                        st.caption("Fechas de referencia visibles al pasar el cursor. "
                                   "No mide capacidad de respuesta en tiempo real.")
            with r:
                with card("Lectura para OPS/PHE",
                   "Factores de contexto que deben contrastarse con "
                   "la situación humanitaria en cada territorio.",
                   "Interpretación contextual, no causal",height=610):
                    st.markdown("**Vulnerabilidad**")
                    st.markdown("Pobreza, desigualdad y escolaridad pueden "
                        "modificar la exposición y la capacidad de recuperación.")
                    st.markdown("**Capacidad sanitaria**")
                    st.markdown("Personal, camas y vacunación pueden contextualizar "
                        "la respuesta, pero no indican su disponibilidad en "
                        "las zonas afectadas.")
                    st.markdown("**Necesita confirmación territorial**")
                    st.markdown("Capacidad de establecimientos, acceso, "
                        "continuidad de servicios, recursos desplegables "
                        "y logística de abastecimiento.")
                    st.info("Las fuentes de contexto no generan automáticamente "
                            "niveles crítico/alto/elevado/moderado.")
    with b:
        l,r=st.columns(2,gap="medium")
        with l:
            with card("Presencia de organizaciones · 3W",
                "Organizaciones distintas dentro de un sector y periodo "
                "de referencia; cobertura restringida de la fuente.",
                "OCHA HAPI 3W",height=CARD_H):
                p=filtered(D["presence"],selected)
                if p.empty:info_missing("presencia 3W")
                else:
                    host=st.selectbox("País con inventario 3W",
                        sorted(p["iso3"].unique(),key=lambda c:names.get(c,c)),
                        format_func=lambda c:names.get(c,c),
                        key="presence_country")
                    q=p[p["iso3"]==host].copy()
                    date=st.selectbox("Corte",
                        sorted(q["fecha_hasta"].unique(),reverse=True),
                        key="presence_date")
                    q=q[q["fecha_hasta"]==date]
                    plot(rank_bars(q,label="sector",
                        value="organizaciones_distintas",limit=12,
                        formats=".0f",units="Organizaciones por sector"),
                        height=334)
                    st.caption("No sumar organizaciones entre sectores; "
                               "un mismo socio puede reportarse en varios.")
        with r:
            with card("Financiación de planes humanitarios",
                "Requerimientos y aportes de apelaciones identificadas; "
                "no representa todos los recursos de ayuda.",
                "OCHA FTS / HAPI",height=CARD_H):
                f=filtered(D["funding"],selected)
                if f.empty:info_missing("financiación de apelaciones")
                else:
                    host=st.selectbox("País con registros",
                        sorted(f["iso3"].unique(),key=lambda c:names.get(c,c)),
                        format_func=lambda c:names.get(c,c),
                        key="funding_country")
                    q=f[f["iso3"]==host].copy()
                    q=q[q["appeal_code"].fillna("").str.lower()!="not specified"]
                    q["anio"]=pd.to_numeric(q["reference_period_start"]
                           .astype(str).str[:4],errors="coerce")
                    q=q[q["anio"]<=pd.Timestamp.today().year]
                    if q.empty:info_missing("planes identificados")
                    else:
                        year=st.selectbox("Año",sorted(q["anio"].dropna()
                          .unique(),reverse=True),key="funding_year")
                        q=q[q["anio"]==year]
                        table(q,height=324,
                          columns=["appeal_name","requirements_usd",
                                   "funding_usd","funding_pct"],
                          labels={"appeal_name":"Plan humanitario",
                                  "requirements_usd":"Requerido (USD)",
                                  "funding_usd":"Financiado (USD)",
                                  "funding_pct":"Cobertura (%)"})
                        st.caption("Las apelaciones pueden tener coberturas "
                                   "diferentes; no se suman porcentajes.")
    with st.expander("Impacto en servicios de salud · información pendiente"):
        st.markdown("La propuesta prevé ataques a personal y establecimientos "
            "sanitarios (OMS SSA) e interrupciones de agua, electricidad, "
            "telecomunicaciones y servicios esenciales. "
            "**No existe una serie regional validada de estos impactos** "
            "en el prototipo actual. Se muestra el vacío de información, "
            "no un cero o una estimación inferida de eventos de violencia.")

def profile_page(D,selected,names,months):
    title("05 / FICHA DE PAÍS",
        "Situación humanitaria por país",
        "Una ficha que permite revisar eventos, crisis, movilidad, "
        "vulnerabilidad y fuentes antes de discutir posibles necesidades de apoyo.")
    choices=sorted(selected,key=lambda c:names.get(c,c))
    iso=st.selectbox("País",choices,
        index=choices.index("COL") if "COL" in choices else 0,
        format_func=lambda c:names.get(c,c),key="profile_iso")
    chosen={iso}
    matrix=summary_countries(D,chosen)
    row=matrix.iloc[0]
    c=crisis_core(D,chosen)
    a,b,d=st.columns(3)
    a.metric("Eventos de violencia · 12m",
        fmt(row["eventos"]) if pd.notna(row["eventos"]) else "Sin serie")
    b.metric("Crisis evaluadas ACAPS",
        str(int(row["crisis_count"])) if pd.notna(row["crisis_count"])
        else "Sin evaluación")
    d.metric("Cambio de eventos · 3m/3m",
        f"{int(row['delta_3m']):+d}" if pd.notna(row["delta_3m"])
        else "Sin serie")
    st.caption("La disponibilidad de una evaluación y la variación de eventos "
               "son indicadores distintos; ninguno es una categoría de prioridad OPS.")
    left,right=st.columns(2,gap="medium")
    with left:
        with card("Violencia y evolución temporal",
           f"Registros de violencia política en los últimos {months} meses.",
           "OCHA HAPI / ACLED",height=CARD_H):
            ev=conflict_complete_window(D,chosen)
            if ev.empty:info_missing("serie de eventos")
            else:
                last=ev["fecha"].max()
                ev=ev[ev["fecha"].isin(list_months(last,months))]
                plot(trend(ev,x="fecha",y="eventos",
                          units="Eventos mensuales"),height=345)
                st.caption(f"Corte final: {last.strftime('%Y-%m')}.")
    with right:
        with card("Gravedad de crisis y acceso",
            "Valores originales de ACAPS por cada contexto humanitario "
            "evaluado en el país.",
            "ACAPS Severity / Access",height=CARD_H):
            if c.empty:info_missing("contextos ACAPS")
            else:
                table(c,height=354,
                  columns=["crisis","puntuacion","acceso","corte_api"],
                  labels={"crisis":"Contexto evaluado",
                          "puntuacion":"Severidad / 10",
                          "acceso":"Acceso / 5",
                          "corte_api":"Corte"})
                st.caption("Una misma crisis puede contener varios factores; "
                           "se mantiene la clasificación original.")
    left,right=st.columns(2,gap="medium")
    with left:
        with card("Movilidad forzada y personas en necesidad",
            "No se suman stocks, rondas ni estimaciones de diferentes años.",
            "ACNUR / OIM / OCHA HAPI",height=CARD_H):
            un=filtered(D["acnur"],chosen,"asilo_iso3")
            if not un.empty:
                year=sorted(un["anio"].astype(str).unique())[-1]
                st.markdown(f"**ACNUR · acogida, año {year}**")
                x=un[un["anio"].astype(str)==year].sort_values(
                    "personas",ascending=False).head(8)
                table(x,height=225,
                    columns=["origen_iso3","grupo_poblacion","personas"],
                    labels={"origen_iso3":"Origen",
                            "grupo_poblacion":"Grupo","personas":"Personas"})
            else:st.caption("Sin registros ACNUR para el país.")
            dtm=oim_scope(filtered(D["dtm"],chosen))
            if not dtm.empty:
                st.caption(f"OIM DTM: {dtm['operacion'].nunique()} "
                    "operaciones con rondas de referencia variable.")
            needs=valid_needs(filtered(D["needs"],chosen))
            if not needs.empty:
                st.caption("PiN intersectorial: disponible con año de referencia "
                           "en el módulo de movilidad; no suma de sectores.")
    with right:
        with card("Contexto de respuesta y capacidad sanitaria",
           "Última observación de indicadores OPS y contexto "
           "para una eventual discusión operativa.",
           "OPS Indicadores Básicos",height=CARD_H):
            op=filtered(D["ops"],chosen)
            records=[]
            for indicator in ["Médicos","Enfermería","Camas hospitalarias",
                              "DTP3","SRP1"]:
                x=latest_ops(op,indicator)
                if not x.empty:
                    r=x.iloc[0]
                    records.append({"Indicador":OPS_LABELS[indicator],
                                    "Valor":fmt(r["valor"],1),
                                    "Año":int(r["periodo"])})
            if records:table(pd.DataFrame(records),height=320)
            else:info_missing("capacidad sanitaria")
            st.caption("No indica la capacidad desplegable en los territorios afectados.")
    with st.expander("Documentos ReliefWeb del país y enlaces originales"):
        docs=reports(D,chosen,limit=14)
        if docs.empty:info_missing("reportes recientes")
        else:
            docs["Fecha"]=docs["fecha_publicacion_rw"].astype(str).str[:10]
            table(docs,height=295,
                  columns=["Fecha","titulo","fuentes","url"],
                  labels={"titulo":"Informe","fuentes":"Organización",
                          "url":"Documento"},link="Documento")
    with st.expander("Posibles consecuencias sanitarias a verificar — no confirmadas"):
        for title_text,context,status,question in health_paths(D,iso):
            st.markdown(f"**{title_text}** · {status}")
            st.caption(context)
            st.write(question)
    st.download_button("Descargar ficha de revisión para reunión",
        briefing_text(D,iso,names).encode("utf-8"),
        file_name=f"OPS_observatorio_{iso}.md",mime="text/markdown",
        key="country_briefing")

def quality_footer(D,selected):
    with st.expander("Fuentes, alcance y limitaciones de los datos",expanded=False):
        table(evidence_table(D,selected),height=305)
        st.caption("Las áreas sin registros no representan ausencia de necesidad. "
                   "Las categorías de países crítico, alto, elevado y moderado "
                   "no están definidas ni aprobadas para una clasificación OPS.")
        st.markdown("[Metodología e indicadores]"
           "(https://github.com/ivanromero0724/observatorio-humanitario-ops/"
           "blob/main/docs/fase2/arquitectura_indicadores_dashboard.md)")

def main():
    st.set_page_config(page_title="Observatorio Humanitario OPS/OMS",
        page_icon="🌎",layout="wide",initial_sidebar_state="expanded")
    st.markdown(STYLES+UX_CSS,unsafe_allow_html=True)
    D=load_all()
    countries=D["countries"]
    if countries.empty:st.error("Catálogo regional no disponible.");st.stop()
    names=countries.set_index("iso3")["pais"].to_dict()
    with st.sidebar:
        st.markdown("### OPS / OMS")
        st.caption("Emergencias en Salud · PHE")
        page=st.radio("Secciones del Observatorio",PAGES,key="nav")
        st.divider()
        region=st.selectbox("Subregión",
            ["Todas las Américas"]+sorted(
                countries["subregion"].dropna().unique()),
            key="region")
        regional=(countries if region=="Todas las Américas" else
                  countries[countries["subregion"]==region])
        options=sorted(regional["iso3"],key=lambda x:names.get(x,x))
        selected_country=st.selectbox("Ámbito",
           ["Todos los países"]+options,
           format_func=lambda x:names.get(x,x),key="scope")
        selected=set(options) if selected_country=="Todos los países" else {selected_country}
        months=st.selectbox("Periodo de eventos",[6,12,24],
           index=1,format_func=lambda x:f"{x} meses",key="months")
        category=st.selectbox("Categoría de evento",
           list(HAPI_TYPES),format_func=lambda x:HAPI_TYPES[x],
           key="event_category")
        st.caption("El periodo y la categoría afectan solamente las "
            "series de eventos; ACAPS, ACNUR, OIM y OPS conservan sus fechas.")
        st.divider()
        st.caption("Mandato inicial: violencia, conflicto, migración, "
                   "desplazamiento y acceso. "
                   "Brotes, El Niño y desastres naturales: fuera del alcance inicial.")
    header()
    if page==PAGES[0]:map_page(D,selected,names)
    elif page==PAGES[1]:violence_page(D,selected,names,months,category)
    elif page==PAGES[2]:migration_page(D,selected,names)
    elif page==PAGES[3]:vulnerability_page(D,selected,names)
    else:profile_page(D,selected,names,months)
    quality_footer(D,selected)
    st.caption("OPS/OMS · Observatorio Humanitario en desarrollo. "
        "El nivel de seguimiento y la priorización requieren "
        "definiciones e interpretación experta de Laura/PHE. "
        "No es un sistema oficial de alertas.")

if __name__=="__main__":
    main()
