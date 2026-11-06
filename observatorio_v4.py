"""Observatorio Humanitario OPS/OMS · Sala situacional ejecutiva (prototipo).

Un producto para discusión técnica de PHE, NO un mecanismo oficial de alerta.
Diferencia hechos, señales contextuales, hipótesis de salud y vacíos.
Cada tarjeta contigua usa la misma altura y diseño, ver QA de navegador.
Los datos provienen de snapshots versionados, nunca APIs en la UI.
"""
from __future__ import annotations

import base64
import html
from contextlib import contextmanager
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from observatorio_v2 import (
    load_all, filtered, valid_needs, latest_ops, OPS_LABELS, HAPI_TYPES, URLS,
)
from ui_ops import map_countries, BASE as OPS_BASE
from graficos import rank_bars, trend, strip_countries, finish

NAVY="#004B87"
BLUE="#0072CE"
TEAL="#008C95"
ORANGE="#F39200"
INK="#19374D"
SLATE="#607588"
BORDER="#D7E2EA"
BG="#F5F8FB"
CARD_H=510
SHORT_H=438
PAGES=[
    "Sala situacional",
    "Vigilancia de señales",
    "Preparación en salud",
    "Análisis por país",
    "Fuentes y calidad",
]

STYLES="""
<style>
/* PAHO/OPS brand. Quiet neutral canvas, strong hierarchy, and matched cards. */
html,body,[class*="css"]{font-family:"Arial",sans-serif!important}
[data-testid="stAppViewContainer"]{background:#F5F8FB}
.block-container{max-width:1400px!important;padding-top:1.0rem!important;
 padding-bottom:2.0rem!important}
[data-testid="stSidebar"]{background:#FFFFFF!important;
 border-right:1px solid #D7E2EA!important}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{font-size:.86rem}
[data-testid="stSidebar"] [role="radiogroup"] label{padding:5px 0}
h1,h2,h3{color:#004B87!important;letter-spacing:-.025em}
.obs-hero{display:flex;justify-content:space-between;align-items:center;
 gap:25px;background:linear-gradient(110deg,#004B87,#006DBB);
 border-radius:16px;padding:24px 30px;color:white;margin:1px 0 19px;
 min-height:146px;position:relative;overflow:hidden}
.obs-hero:after{content:"";position:absolute;right:225px;top:-80px;
 width:280px;height:280px;border:1px solid rgba(255,255,255,.13);
 border-radius:50%;pointer-events:none}
.obs-hero .eyebrow{font-size:.70rem;font-weight:800;letter-spacing:.14em;
 color:#BCE8FC;text-transform:uppercase}
.obs-hero .main{font-size:1.80rem;line-height:1.14;font-weight:780;
 letter-spacing:-.035em;margin:6px 0 6px}
.obs-hero .sub{font-size:.86rem;line-height:1.5;color:#E0F0FA;max-width:710px}
.obs-hero .brand{height:auto;width:160px;max-width:100%;padding:10px;
 background:white;border-radius:9px;position:relative;z-index:2}
.obs-section-k{font:.79rem Arial;color:#0072CE;font-weight:800;
 letter-spacing:.10em;text-transform:uppercase;margin-top:7px}
.obs-section-h{font:750 1.56rem/1.22 Arial;color:#004B87;
 letter-spacing:-.03em;margin:5px 0 3px}
.obs-section-sub{font:400 .89rem/1.5 Arial;color:#64788A;
 margin-bottom:13px}
.obs-card-title{font:750 1.06rem/1.23 Arial;color:#004B87;
 margin:0 0 7px;letter-spacing:-.015em}
.obs-card-sub{font:.81rem/1.4 Arial;color:#607588;
 min-height:28px;margin-bottom:8px}
.obs-card-foot{font:.71rem/1.35 Arial;color:#778997;
 margin-top:6px}
.obs-section-divider{height:1px;background:#DFE7EF;margin:13px 0 18px}
.obs-pill{display:inline-block;border-radius:40px;border:1px solid #C9DFEB;
 color:#004B87;font-size:.72rem;font-weight:750;background:#EFF7FC;
 padding:5px 10px;margin-right:7px}
.obs-pill-muted{border-color:#E3EAF0;color:#647789;background:#F6F8FA}
.obs-pill-orange{border-color:#FAD8AE;color:#8C4A03;background:#FFF5E8}
div[data-testid="stVerticalBlockBorderWrapper"]{
 border:1px solid #D7E2EA!important;border-radius:13px!important;
 box-shadow:0 2px 10px rgba(22,65,94,.04)!important;
 background:#FFFFFF!important;
}
div[data-testid="stHorizontalBlock"]{align-items:stretch!important}
div[data-testid="stMetric"]{border:1px solid #D7E2EA!important;
 border-top:3px solid #0072CE!important;
 background:white!important;min-height:103px!important;
 border-radius:12px!important;padding:12px 14px 9px!important;
 box-shadow:0 1px 5px rgba(22,65,94,.02)!important}
div[data-testid="stMetricValue"]{color:#004B87!important;font-size:1.70rem!important}
div[data-testid="stMetricLabel"]{color:#607588!important;font-size:.79rem!important}
[data-testid="stPlotlyChart"]{width:100%!important}
[data-testid="stAlert"]{border-radius:10px!important}
[data-testid="stExpander"]{border:1px solid #DFE7EF!important;
 border-radius:10px!important;background:#FFF!important;margin:9px 0}
[data-testid="stDataFrame"]{border:1px solid #E1E9EF;border-radius:7px}
[data-testid="stTabs"] button[aria-selected="true"]{
 color:#004B87!important;border-bottom-color:#0072CE!important}
@media(max-width:900px){
 .obs-hero{padding:19px 17px;gap:10px}
 .obs-hero .main{font-size:1.36rem}
 .obs-hero .brand{width:95px}
 .obs-section-h{font-size:1.32rem}
}
</style>
"""

def fmt(n,decimals=0):
    try:
        if pd.isna(n):return "—"
        return f"{float(n):,.{decimals}f}".replace(",","·").replace(".",",").replace("·",".")
    except (ValueError,TypeError):return "—"

def esc(s):return html.escape(str(s),quote=True)

def hero():
    img=Path(OPS_BASE)/"assets/ops_oms.png"
    logo=""
    if img.is_file():
        payload=base64.b64encode(img.read_bytes()).decode("ascii")
        logo=f'<img class="brand" alt="OPS OMS" src="data:image/png;base64,{payload}">'
    st.markdown(f"""
    <div class="obs-hero">
     <div style="position:relative;z-index:1">
       <div class="eyebrow">OPS / OMS · Programa de Emergencias en Salud · Américas</div>
       <div class="main">Inteligencia humanitaria para la preparación en salud</div>
       <div class="sub">Situaciones documentadas · señales de evolución ·
          posibles repercusiones sanitarias · capacidad para responder</div>
     </div>{logo}
    </div>""",unsafe_allow_html=True)

def heading(n,title,sub):
    st.markdown(f'<div class="obs-section-k">{esc(n)}</div>'
       f'<div class="obs-section-h">{esc(title)}</div>'
       f'<div class="obs-section-sub">{esc(sub)}</div>',
       unsafe_allow_html=True)

@contextmanager
def card(title,subtitle="",source="",height=None):
    with st.container(border=True,
        height=height if height is not None else "content"):
        st.markdown(f'<div class="obs-card-title">{esc(title)}</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="obs-card-sub">{esc(subtitle)}</div>',
                    unsafe_allow_html=True)
        yield
        if source:
            st.markdown(f'<div class="obs-card-foot">FUENTE · {esc(source)}</div>',
                        unsafe_allow_html=True)

def plot(fig,height=320):
    fig.update_layout(height=height,
         margin=dict(l=12,r=48,t=16,b=37))
    st.plotly_chart(fig,use_container_width=True,
                    config={"displayModeBar":False,"responsive":True})

def info_missing(what):
    st.info(f"Sin registros de {what} en este ámbito. No equivale "
            "a ausencia de la situación.")

def table(df,*,height=270,columns=None,labels=None,link=None):
    data=df[columns].rename(columns=labels or {}) if columns else df
    cfg={}
    for col in data.columns:
        if col in {"Contexto evaluado","Informe","Descripción",
                   "Situación","Plan humanitario","Descriptores"}:
            cfg[col]=st.column_config.TextColumn(col,width="large")
        if col in {"Severidad / 10","Acceso / 5",
                   "Severidad ACAPS / 10"}:
            cfg[col]=st.column_config.NumberColumn(col,format="%.1f")
    if link in data.columns:
        cfg[link]=st.column_config.LinkColumn(link,display_text="Abrir ↗")
    st.dataframe(data,use_container_width=True,hide_index=True,
                 height=height,column_config=cfg)

def crisis_table(D,chosen):
    df=filtered(D["severity"],chosen)
    if df.empty:return df
    access=filtered(D["access"],chosen)
    if not access.empty:
        access=access[["iso3","crisis_id","acceso"]].drop_duplicates(
            ["iso3","crisis_id"])
        df=df.merge(access,on=["iso3","crisis_id"],how="left")
    else:df["acceso"]=float("nan")
    return df.sort_values(["puntuacion","pais"],ascending=[False,True])

def risk_map(D,chosen,mode="severidad",height=300):
    countries=filtered(D["countries"],chosen)
    if mode=="cobertura":
        crises=crisis_table(D,chosen)
        available=set(crises["iso3"]) if not crises.empty else set()
        base=countries.copy()
        base["estado"]=base["iso3"].isin(available).map({
            True:"Con registros",False:"Sin registros en catálogo"})
        map_countries(base,"estado","Cobertura ACAPS",
                      categorical=True,height=height)
    else:
        crises=crisis_table(D,chosen)
        if crises.empty:
            base=countries.copy()
            base["puntuacion"]=float("nan")
        else:
            base=(crises.drop_duplicates("iso3")
                [["iso3","puntuacion","pais"]])
        map_countries(base,"puntuacion",
                      "Máxima severidad ACAPS",height=height,
                      legend_title="INFORM Severity / 10")

def conflict_complete_window(D,chosen,category="political_violence"):
    d=filtered(D["conflict"],chosen)
    if d.empty:return d
    return d[(d["tipo_evento"]==category)&d["fecha"].notna()].copy()

def months_for_signal(D):
    df=D["conflict"]
    if df.empty or df["fecha"].dropna().empty:return []
    last=df["fecha"].max().to_period("M")
    return [pd.Timestamp((last-i).start_time) for i in range(5,-1,-1)]

def change_signals(D,chosen,category="political_violence"):
    """Descriptive 3mo vs preceding 3mo, only for complete six-month coverage.

    No alert scoring. If one month is missing in either window, exclude country.
    """
    df=conflict_complete_window(D,chosen,category)
    dates=months_for_signal(D)
    fields=["iso3","pais","eventos_antes","eventos_recientes","cambio",
            "cambio_pct","fin_periodo"]
    if df.empty or len(dates)!=6:return pd.DataFrame(columns=fields)
    df=df[df["fecha"].isin(dates)].copy()
    df["eventos"]=pd.to_numeric(df["eventos"],errors="coerce")
    counts=df.groupby(["iso3","fecha"],as_index=False).agg(
        eventos=("eventos","sum"))
    eligible=counts.groupby("iso3")["fecha"].nunique()
    eligible=set(eligible[eligible==6].index)
    rows=[]
    name=D["countries"].set_index("iso3")["pais"].to_dict()
    for iso in eligible:
        x=counts[counts["iso3"]==iso].sort_values("fecha")
        prev=x[x["fecha"].isin(dates[:3])]["eventos"].sum()
        curr=x[x["fecha"].isin(dates[3:])]["eventos"].sum()
        if pd.isna(prev) or pd.isna(curr):continue
        diff=curr-prev
        pct=(diff/prev*100) if prev>0 else float("nan")
        rows.append({"iso3":iso,"pais":name.get(iso,iso),
            "eventos_antes":int(prev),"eventos_recientes":int(curr),
            "cambio":int(diff),"cambio_pct":pct,
            "fin_periodo":dates[-1].strftime("%Y-%m")})
    return pd.DataFrame(rows,columns=fields).sort_values(
        "cambio",ascending=False)

def reports(D,chosen,limit=12):
    r=filtered(D["reports"],chosen)
    if r.empty:return r
    return r.drop_duplicates("reporte_id").sort_values(
        "fecha",ascending=False).head(limit).copy()

def notes_dates(D):
    crisis=crisis_table(D,set(D["countries"]["iso3"]))
    acaps=crisis["corte_api"].dropna().iloc[0] if not crisis.empty else "sin corte"
    latest=months_for_signal(D)
    date=latest[-1].strftime("%b %Y") if latest else "sin datos"
    return str(acaps),date

def health_paths(D,iso):
    """Direct evidence/proxy/missing explicitly labelled; no causal inference."""
    conflicts=conflict_complete_window(D,{iso})
    months=months_for_signal(D)
    conflict_months=conflicts[conflicts["fecha"].isin(months[-3:])] if months else conflicts.iloc[:0]
    total=int(conflict_months["eventos"].sum()) if not conflict_months.empty else None
    access=filtered(D["access"],{iso})
    hi=float(access["acceso"].max()) if not access.empty and
         access["acceso"].notna().any() else None
    un=filtered(D["acnur"],{iso},"asilo_iso3")
    dtm=filtered(D["dtm"],{iso})
    has_mob=not un.empty or not dtm.empty
    return [
      ("Trauma y atención de urgencias",
       (f"{fmt(total)} eventos de violencia política en los tres meses "
        "del corte disponible" if total is not None else
        "Sin serie local verificada en el corte"),
       "Señal indirecta" if total is not None else "Sin indicador",
       "¿Existen víctimas, lesiones, saturación de urgencias o ataques a personal sanitario?"),
      ("Acceso a servicios y suministros",
       (f"Restricción de acceso ACAPS: máximo {fmt(hi,1)}/5 entre crisis "
        "evaluadas" if hi is not None else
        "Sin evaluación de acceso para este país"),
       "Señal contextual" if hi is not None else "Sin indicador",
       "¿Hay dificultades verificadas para llegar a establecimientos, movilizar equipos o abastecer?"),
      ("Demanda por movilidad humana",
       ("Hay registros de población de interés ACNUR y/o rondas OIM "
        "—con fechas y categorías propias—" if has_mob else
        "Sin registros de estas fuentes en el corte"),
       "Información contextual" if has_mob else "Sin indicador",
       "¿Se conoce un desplazamiento reciente que cambie la demanda de vacunación, consulta o refugio?"),
      ("Vigilancia y servicios esenciales",
       "Sin integración regional validada de ataques a la salud (OMS SSA) "
       "ni interrupciones de agua, energía o telecomunicaciones",
       "Pendiente de verificación",
       "¿Se han confirmado fallas de agua, saneamiento, medicamentos, cadena de frío o prestación de servicios?")
    ]

def evidence_table(D,chosen):
    sources=[
        ("Contextos de crisis ACAPS","severity","iso3"),
        ("Acceso humanitario ACAPS","access","iso3"),
        ("Conflicto HAPI / ACLED","conflict","iso3"),
        ("Personas en necesidad HAPI","needs","iso3"),
        ("ACNUR / HAPI","acnur","asilo_iso3"),
        ("OIM DTM","dtm","iso3"),
        ("Capacidad sanitaria OPS","ops","iso3"),
        ("Organizaciones HAPI 3W","presence","iso3"),
        ("Financiación HAPI FTS","funding","iso3"),
        ("Informes ReliefWeb","reports","iso3"),
    ]
    result=[]
    for title,key,col in sources:
        src=D[key]
        n=len(set(src[col].dropna())&chosen) if not src.empty else 0
        result.append({"Fuente":title,"Países con datos":n,
                       "Sin registros":len(chosen)-n,
                       "Unidad":"Cobertura de registros, no intensidad"})
    return pd.DataFrame(result)

def briefing_text(D,iso,names):
    risk=filtered(D["risk"],{iso})
    severity=crisis_table(D,{iso})
    signal=change_signals(D,{iso})
    needs=valid_needs(filtered(D["needs"],{iso}))
    cap=filtered(D["ops"],{iso})
    parts=[
       f"# Ficha de revisión humanitaria · {names.get(iso,iso)}",
       "Observatorio Humanitario OPS / OMS · borrador de apoyo analítico",
       "No constituye alerta, clasificación de prioridad ni evaluación directa de impacto en salud.",
       "",
       "## Contexto documentado",
       f"INFORM Risk Mid 2026: {fmt(risk['puntuacion'].iloc[0],1)+'/10' if not risk.empty else 'sin datos'}.",
       f"Crisis evaluadas ACAPS en el corte: {len(severity)}.",
    ]
    if not severity.empty:
        for _,row in severity.iterrows():
            parts.append(f"- {row['crisis']} · Severity {fmt(row['puntuacion'],1)}/10 · "
                        f"acceso {fmt(row['acceso'],1)}/5 · {row['corte_api']}")
    parts+=["","## Señal de violencia política (últimos 3 vs 3 meses anteriores)"]
    if signal.empty:parts.append("Sin serie de seis meses completa y comparable.")
    else:
        row=signal.iloc[0]
        parts.append(f"{row['eventos_antes']} → {row['eventos_recientes']} eventos; "
                     f"cambio {row['cambio']:+d}. Corte hasta {row['fin_periodo']}.")
    parts+=["","## Personas en necesidad"]
    if not needs.empty:
        ns=needs.copy()
        ns["anio"]=ns["reference_period_start"].astype(str).str[:4]
        ns=ns[~ns.duplicated("anio",keep=False)]
        if not ns.empty:
            ns=ns.sort_values("anio").iloc[-1]
            parts.append(f"PiN intersectorial: {fmt(ns['population'])}, año {ns['anio']}.")
        else:parts.append("No hay un total intersectorial inequívoco.")
    else:parts.append("Sin total intersectorial comparable en HAPI.")
    parts+=["","## Posibles repercusiones en salud: preguntas para verificar"]
    for label,signal,status,question in health_paths(D,iso):
        parts.append(f"- {label} [{status}]: {signal}. {question}")
    parts+=["","## Capacidades sanitarias de contexto OPS"]
    if not cap.empty:
        for ind in ["Médicos","Enfermería","Camas hospitalarias","DTP3","SRP1"]:
            row=latest_ops(cap,ind)
            if not row.empty:
                r=row.iloc[0]
                parts.append(f"- {OPS_LABELS.get(ind,ind)}: {fmt(r['valor'],1)} "
                             f"(año {int(r['periodo'])}).")
    parts+=["","Fuentes: ACAPS, INFORM, HAPI/ACLED, OIM DTM, ACNUR, OPS y ReliefWeb.",
       "La información no reemplaza reportes de país ni verificación con autoridades sanitarias."]
    return "\n".join(parts)

def executive(D,selected,names,months):
    heading("01 / LECTURA EJECUTIVA","Sala situacional humanitaria",
        "Lo documentado, los cambios observados y lo que se debe confirmar para "
        "anticipar posibles afectaciones a la salud pública.")
    acaps_cut,conflict_cut=notes_dates(D)
    st.markdown(f'<span class="obs-pill">ACAPS · {esc(acaps_cut)}</span>'
         f'<span class="obs-pill">Conflicto HAPI · hasta {esc(conflict_cut)}</span>'
         '<span class="obs-pill obs-pill-muted">Sin clasificación de prioridad OPS</span>',
         unsafe_allow_html=True)
    st.write("")
    crisis=crisis_table(D,selected)
    sg=change_signals(D,selected)
    valid_incr=sg[sg["cambio"]>0] if not sg.empty else sg
    a,b,c,d=st.columns(4,gap="medium")
    a.metric("Situaciones evaluadas",len(crisis))
    b.metric("Países con evaluación",crisis["iso3"].nunique() if not crisis.empty else 0)
    c.metric("Países con aumento de eventos",
             f"{len(valid_incr)}/{len(sg)}" if not sg.empty else "—",
             help="Aumento absoluto de violencia política en los 3 meses más recientes "
                  "de HAPI respecto a los 3 anteriores, solo con seis meses de datos.")
    d.metric("Cobertura PiN intersectorial",
             f"{valid_needs(filtered(D['needs'],selected))['iso3'].nunique()}/{len(selected)}")
    st.caption("Los indicadores representan unidades distintas: crisis ACAPS, países con "
       "evaluación, variación descriptiva de eventos y cobertura PiN. No se agregan "
       "ni equivalen a países priorizados o alertas.")

    left,right=st.columns([1.08,1],gap="medium")
    with left:
        with card("Geografía de contextos humanitarios",
            "Máxima severidad ACAPS entre crisis evaluadas en cada país "
            "(escala externa 0–10). Gris = sin evaluación en este corte.",
            "ACAPS Severity · cartografía OPS",height=590):
            mode=st.segmented_control("Mostrar",["Severidad ACAPS","Cobertura"],
                default="Severidad ACAPS",key="exec_map",label_visibility="collapsed")
            risk_map(D,selected,"cobertura" if mode=="Cobertura" else "severidad",
                     height=377)
            st.caption("La severidad mide crisis evaluadas, no es un indicador "
                       "de riesgo OPS ni una estimación de impacto sanitario.")
    with right:
        with card("Situaciones con evaluación publicada",
            "Ordenadas por puntuación de gravedad ACAPS; el orden NO constituye "
            "una prioridad de intervención OPS.",
            f"ACAPS Severity / Access · {acaps_cut}",height=590):
            if crisis.empty:info_missing("evaluaciones ACAPS")
            else:
                display=crisis[["pais","crisis","puntuacion","acceso"]].head(11).copy()
                table(display,height=415,
                    columns=["pais","crisis","puntuacion","acceso"],
                    labels={"pais":"País","crisis":"Contexto evaluado",
                            "puntuacion":"Severidad / 10","acceso":"Acceso / 5"})
                st.caption("Una misma región puede incluir varias crisis; "
                           "la ausencia de evaluaciones no implica ausencia de necesidades.")

    st.markdown('<div class="obs-section-divider"></div>',unsafe_allow_html=True)
    l,r=st.columns(2,gap="medium")
    with l:
        with card("¿Qué ha cambiado recientemente?",
            "Variación de eventos de violencia política en los tres meses "
            "disponibles frente a los tres anteriores. No es una alerta automática.",
            f"HAPI / ACLED · corte {conflict_cut}",height=SHORT_H):
            if sg.empty:info_missing("series de seis meses comparables")
            else:
                pos=sg[sg["cambio"]>0].head(7).copy()
                if pos.empty:
                    st.info("No se observan aumentos absolutos positivos en el ámbito "
                            "y periodo con cobertura completa.")
                else:
                    plot(rank_bars(pos,label="pais",value="cambio",
                         limit=7,units="Eventos adicionales",formats=".0f",
                         color=BLUE),height=269)
                st.caption(f"{len(sg)} países con series comparables; "
                           "cambios en conteos, no tasas ni alertas.")
    with r:
        with card("¿Qué podría afectar la salud pública?",
            "Rutas de impacto que los equipos deben verificar con autoridades "
            "y reportes sanitarios; no son daños confirmados por el tablero.",
            "Marco analítico OPS/PHE · hipótesis de preparación",height=SHORT_H):
            for title,detail in [
              ("Atención de urgencias","Lesiones y sobrecarga de servicios ante violencia."),
              ("Acceso y continuidad","Rutas, personal, medicamentos y abastecimiento."),
              ("Movilidad humana","Demanda de consulta, vacunación, protección y salud mental."),
              ("Servicios esenciales","Agua segura, saneamiento, energía y vigilancia epidemiológica."),
            ]:
                st.markdown(f"**{title}** · {detail}")
            st.caption("Los ataques a la atención de salud (OMS SSA) y las "
                       "interrupciones de servicios requieren datos directos "
                       "que aún no están integrados regionalmente.")

    with st.expander("Ver informes originales recientes de los países seleccionados",
                     expanded=False):
        doc=reports(D,selected,limit=15)
        if doc.empty:info_missing("informes de ReliefWeb")
        else:
            doc["Fecha"]=doc["fecha_publicacion_rw"].astype(str).str[:10]
            table(doc,height=345,columns=["Fecha","titulo","fuentes","url"],
                labels={"titulo":"Informe","fuentes":"Organización",
                        "url":"Documento"},link="Documento")
            st.caption("Son informes asociados a países, no necesariamente a una "
                       "crisis ACAPS específica. Su volumen no mide gravedad.")

def surveillance(D,selected,names,months):
    heading("02 / MONITOREO","Señales que merecen verificación",
        "Comparación temporal de eventos, restricciones de acceso y documentación. "
        "No se asignan umbrales ni alertas OPS.")
    category=st.selectbox("Tipo de eventos publicado por HAPI",
       list(HAPI_TYPES),format_func=lambda k:HAPI_TYPES[k],
       key="sig_category")
    signal=change_signals(D,selected,category)
    a,b=st.columns([1,1],gap="medium")
    with a:
        with card("Cambios en los últimos seis meses disponibles",
            "Tres meses recientes frente a los tres anteriores, "
            "solo países con registro en los seis meses.",
            "HAPI / ACLED agregado",height=540):
            if signal.empty:info_missing("series de eventos comparables")
            else:
                current=signal.copy().sort_values("cambio",ascending=False)
                # Do not misinterpret negative or small deltas as severity.
                table(current.head(12),height=381,
                  columns=["pais","eventos_antes","eventos_recientes","cambio"],
                  labels={"pais":"País","eventos_antes":"Antes · 3m",
                          "eventos_recientes":"Reciente · 3m",
                          "cambio":"Δ eventos"})
                st.caption("Diferencias absolutas descriptivas, no predicciones. "
                           "No se combinan categorías solapadas de ACLED.")
    with b:
        with card("Evolución mensual en el ámbito seleccionado",
           f"Últimos {months} meses por categoría; sin interpretar como "
           "número de personas afectadas.",
           "HAPI / ACLED agregado",height=540):
            d=conflict_complete_window(D,selected,category)
            if d.empty:info_missing("eventos")
            else:
                last=d["fecha"].max()
                d=d[d["fecha"]>last-pd.DateOffset(months=months)].copy()
                ts=d.groupby("fecha",as_index=False)["eventos"].sum()
                plot(trend(ts,x="fecha",y="eventos",
                           units="Eventos mensuales"),height=340)
                st.caption(f"Último mes presente en HAPI: {last.strftime('%Y-%m')}. "
                           "Puede incluir revisiones retrospectivas.")
    st.write("")
    left,right=st.columns(2,gap="medium")
    with left:
        with card("Restricciones al acceso humanitario",
            "Evaluaciones a nivel de crisis, no medición de accesibilidad "
            "de establecimientos de salud.",
            "ACAPS Humanitarian Access",height=510):
            a=filtered(D["access"],selected)
            if a.empty:info_missing("evaluaciones de acceso")
            else:
                a=a.copy()
                a["etiqueta"]=a["pais"]+" · "+a["crisis"].astype(str)
                plot(rank_bars(a,label="etiqueta",value="acceso",
                     limit=10,color=ORANGE,units="ACAPS / 5",
                     max_x=5.25),height=342)
                st.caption("Mayor índice = mayores restricciones según ACAPS. "
                           "No es un diagnóstico sanitario directo.")
    with right:
        with card("Acceso a evidencia actualizada",
           "Fuentes y fechas que pueden alimentar una verificación "
           "con oficinas de país y redes de salud.",
           "ReliefWeb · metadatos publicados",height=510):
            r=reports(D,selected,limit=10)
            if r.empty:info_missing("informes recientes")
            else:
                r["Fecha"]=r["fecha_publicacion_rw"].astype(str).str[:10]
                table(r,height=337,columns=["Fecha","titulo","url"],
                     labels={"titulo":"Informe","url":"Documento"},
                     link="Documento")
            st.caption("Documentos relacionados con el país; el contenido y "
                       "la relación con una crisis específica deben revisarse.")
    with st.expander("Otros riesgos de la propuesta aún sin serie regional homologada"):
        st.markdown("Crimen organizado, mercados ilícitos, tensiones políticas, "
            "ataques directos a salud y cortes de agua o electricidad requieren "
            "fuentes específicas y revisión de licencia. No se presentan como "
            "ceros ni se sustituyen por indicadores indirectos.")

def readiness(D,selected,names):
    heading("03 / PREPARACIÓN","Preparación para posibles consecuencias en salud",
       "Una ficha orientada a revisar vulnerabilidades y vacíos de información. "
       "Las preguntas son hipótesis de preparación, no afectaciones confirmadas.")
    focus=st.selectbox("País para revisión sanitaria",
        sorted(selected,key=lambda c:names.get(c,c)),
        format_func=lambda c:names.get(c,c),
        key="health_focus")
    country={focus}
    ops=filtered(D["ops"],country)
    a,b,c,d=st.columns(4)
    for box,indicator,short in [
        (a,"Médicos","Personal médico / 10.000"),
        (b,"Enfermería","Enfermería / 10.000"),
        (c,"Camas hospitalarias","Camas / 1.000"),
        (d,"DTP3","Vacunación DTP3 · %"),
    ]:
        q=latest_ops(ops,indicator)
        if q.empty:box.metric(short,"Sin dato")
        else:
            x=q.iloc[0]
            box.metric(short,fmt(x["valor"],1),
                       help=f"{OPS_LABELS.get(indicator,indicator)}. Año {int(x['periodo'])}. "
                            "Dato de contexto nacional; no mide la capacidad operativa actual.")
    st.caption("Valores nacionales OPS del último año disponible para cada indicador; "
               "los años pueden diferir. No equivalen a recursos desplegables en una emergencia.")
    l,r=st.columns([1,1],gap="medium")
    with l:
        with card("Vías de afectación que requieren confirmación",
             "Cruce explícito entre evidencia indirecta disponible "
             "y preguntas pendientes para la oficina de país.",
             "HAPI / ACAPS / ACNUR / OIM + preguntas de preparación",height=650):
            for title,datum,status,question in health_paths(D,focus):
                badge=("obs-pill-orange" if "Pendiente" in status
                       else "obs-pill-muted")
                st.markdown(f"**{title}**")
                st.markdown(f'<span class="obs-pill {badge}">{esc(status)}</span>',
                            unsafe_allow_html=True)
                st.caption(datum)
                st.markdown(f"*A verificar:* {question}")
                st.write("")
    with r:
        with card("Capacidad y continuidad de atención",
            "Información nacional disponible y asuntos operativos "
            "que aún no pueden evaluarse con las API existentes.",
            "OPS Indicadores Básicos / marco de verificación",height=650):
            st.markdown("**Capacidad sanitaria de referencia**")
            avail=[]
            for indicator in ["Médicos","Enfermería","Camas hospitalarias","DTP3","SRP1"]:
                q=latest_ops(ops,indicator)
                if not q.empty:
                    row=q.iloc[0]
                    avail.append({"Indicador":OPS_LABELS.get(indicator,indicator),
                                 "Valor":fmt(row["valor"],1),
                                 "Año":int(row["periodo"])})
            if avail:table(pd.DataFrame(avail),height=234)
            else:info_missing("capacidad sanitaria")
            st.markdown("**Preguntas para enlace con oficina de país**")
            st.markdown("¿Hay afectación confirmada de centros y personal de salud? "
                "¿Funcionan las rutas de referencia y transporte? "
                "¿Existen interrupciones de electricidad, agua, medicamentos, "
                "cadena de frío o servicios esenciales? ¿Hay capacidades "
                "locales que requieran apoyo?")
            st.info("El tablero no puede confirmar estas condiciones "
                    "sin reportes sanitarios directos (p. ej., OMS SSA y autoridades).")

    st.write("")
    l,r=st.columns(2,gap="medium")
    with l:
        with card("Presencia de socios humanitarios",
           "Organizaciones distintas dentro del sector/corte seleccionado; "
           "no representa capacidad sanitaria total del país.",
           "OCHA HAPI 3W",height=480):
            p=filtered(D["presence"],country)
            if p.empty:info_missing("presencia operacional 3W")
            else:
                p=p[p["fecha_hasta"]==p["fecha_hasta"].max()].copy()
                plot(rank_bars(p,label="sector",value="organizaciones_distintas",
                    limit=9,units="Socios distintos por sector",
                    formats=".0f"),height=312)
                st.caption(f"Corte: {p['fecha_hasta'].max()}. "
                           "No sumar socios entre sectores.")
    with r:
        with card("Financiación documentada de apelaciones",
           "Planes identificados del país; no es gasto en salud "
           "ni la totalidad del financiamiento humanitario.",
           "OCHA FTS a través de HAPI",height=480):
            f=filtered(D["funding"],country)
            if f.empty:info_missing("financiación de apelaciones")
            else:
                f=f[f["appeal_code"].notna()&
                    (f["appeal_code"].str.lower()!="not specified")].copy()
                f["anio"]=pd.to_numeric(
                    f["reference_period_start"].astype(str).str[:4],
                    errors="coerce")
                f=f[f["anio"]<=pd.Timestamp.today().year]
                if f.empty:info_missing("apelaciones identificadas")
                else:
                    f=f.sort_values("anio",ascending=False)
                    f["Requerido (USD)"]=f["requirements_usd"].map(
                        lambda x:fmt(x,0))
                    f["Financiado (USD)"]=f["funding_usd"].map(
                        lambda x:fmt(x,0))
                    table(f,height=303,
                          columns=["appeal_name","anio",
                                   "Requerido (USD)","Financiado (USD)"],
                          labels={"appeal_name":"Plan humanitario","anio":"Año"})
                st.caption("Montos por apelación y año, sin sumas regionales.")

    text=briefing_text(D,focus,names)
    st.download_button("Descargar ficha de preparación para reunión",
          text.encode("utf-8"),
          file_name=f"ops_ficha_preparacion_{focus}.md",
          mime="text/markdown",type="primary")
    st.caption("Ficha basada en snapshots publicados y preguntas de "
               "verificación. No acredita preparación suficiente ni define una alerta.")

def country_profile(D,selected,names,months):
    heading("04 / ANÁLISIS DE PAÍS","Ficha integrada para reunión de situación",
       "Un recorrido por hechos documentados, señales temporales, "
       "poblaciones y capacidad sanitaria, con trazabilidad por fuente.")
    iso=st.selectbox("Seleccionar país",sorted(selected,
        key=lambda x:names.get(x,x)),
        format_func=lambda x:names.get(x,x),key="profile_country")
    country={iso}
    c=crisis_table(D,country)
    risk=filtered(D["risk"],country)
    sig=change_signals(D,country)
    n=valid_needs(filtered(D["needs"],country))
    a,b,d=st.columns(3)
    a.metric("INFORM Risk · Mid 2026",
        f"{fmt(risk['puntuacion'].iloc[0],1)} / 10" if not risk.empty else "Sin dato")
    b.metric("Crisis ACAPS evaluadas",len(c))
    d.metric("Eventos de violencia política · cambio 3m/3m",
             f"{int(sig.iloc[0]['cambio']):+d}" if not sig.empty else "Sin comparabilidad")
    st.caption("Riesgo estructural, evaluaciones de crisis y cambio de eventos "
               "son medidas distintas y no definen una prioridad OPS.")
    l,r=st.columns(2,gap="medium")
    with l:
        with card("Situaciones, severidad y acceso",
           "Evaluaciones por crisis y corte publicados por ACAPS.",
           "ACAPS Severity + Humanitarian Access",height=CARD_H):
            if c.empty:info_missing("crisis evaluadas")
            else:
                table(c,height=337,columns=["crisis","puntuacion",
                       "acceso","corte_api"],
                    labels={"crisis":"Contexto evaluado",
                       "puntuacion":"Severidad / 10",
                       "acceso":"Acceso / 5","corte_api":"Corte"})
                st.caption("No sumar puntuaciones entre crisis.")
    with r:
        with card("Tendencia de violencia política",
           f"Eventos agregados de los últimos {months} meses en HAPI.",
           "HAPI / ACLED",height=CARD_H):
            ev=conflict_complete_window(D,country)
            if ev.empty:info_missing("violencia política")
            else:
                last=ev["fecha"].max()
                ev=ev[ev["fecha"]>last-pd.DateOffset(months=months)]
                plot(trend(ev,x="fecha",y="eventos",
                    units="Eventos mensuales"),height=338)
                st.caption(f"Último corte: {last.strftime('%Y-%m')}. "
                     "No se infieren víctimas ni afectación sanitaria.")

    l,r=st.columns(2,gap="medium")
    with l:
        with card("Personas y movilidad · contexto",
           "Estimar necesidades sin sumar sectores ni confundir "
           "stocks de refugio con flujos de desplazamiento.",
           "OCHA HAPI / ACNUR / OIM",height=CARD_H):
            if n.empty:st.caption("PiN intersectorial: sin estimación comparable.")
            else:
                n=n.copy()
                n["anio"]=n["reference_period_start"].astype(str).str[:4]
                n=n[~n.duplicated("anio",keep=False)]
                if n.empty:st.caption("PiN: múltiples totales por año; no agregables.")
                else:
                    row=n.sort_values("anio").iloc[-1]
                    st.metric(f"PiN intersectorial · {row['anio']}",
                              fmt(row["population"]))
            un=filtered(D["acnur"],country,"asilo_iso3")
            if un.empty:st.caption("ACNUR: sin registros de acogida.")
            else:
                year=max(un["anio"].astype(str).tolist())
                st.markdown(f"**Poblaciones ACNUR por origen y grupo · {year}**")
                x=un[un["anio"].astype(str)==year].sort_values(
                      "personas",ascending=False).head(5)
                table(x,height=174,columns=["origen_iso3",
                       "grupo_poblacion","personas"],
                    labels={"origen_iso3":"Origen",
                        "grupo_poblacion":"Grupo","personas":"Personas"})
            dtm=filtered(D["dtm"],country)
            if not dtm.empty:
                st.caption("OIM DTM: existen rondas por operación, algunas históricas; "
                           "no equivalen a población nacional desplazada actual.")
    with r:
        with card("Capacidad sanitaria de contexto",
            "Última observación publicada para recursos y coberturas; "
            "cada indicador conserva su año.",
            "OPS Indicadores Básicos",height=CARD_H):
            ops=filtered(D["ops"],country)
            data=[]
            for indicator in ["Médicos","Enfermería","Camas hospitalarias","DTP3","SRP1"]:
                val=latest_ops(ops,indicator)
                if not val.empty:
                    row=val.iloc[0]
                    data.append({"Indicador":OPS_LABELS.get(indicator,indicator),
                          "Valor":fmt(row["valor"],1),"Año":int(row["periodo"])})
            if data:table(pd.DataFrame(data),height=326)
            else:info_missing("indicadores de capacidad sanitaria")
            st.caption("Capacidad nacional no equivale a disponibilidad operativa "
                       "en las zonas de una emergencia.")

    with st.expander("Preguntas sanitarias para verificar con las autoridades"):
        for title,datum,status,question in health_paths(D,iso):
            st.markdown(f"**{title}** · {status}")
            st.caption(datum)
            st.write(question)
    with st.expander("Documentos recientes del país y enlaces originales"):
        df=reports(D,country,limit=15)
        if df.empty:info_missing("informes ReliefWeb")
        else:
            df["Fecha"]=df["fecha_publicacion_rw"].astype(str).str[:10]
            table(df,height=330,columns=["Fecha","titulo","fuentes","url"],
                labels={"titulo":"Informe","fuentes":"Organización",
                        "url":"Documento"},link="Documento")
    st.download_button("Descargar briefing del país",
       briefing_text(D,iso,names).encode("utf-8"),
       file_name=f"ops_briefing_{iso}.md",mime="text/markdown",
       type="primary")

def sources_page(D,selected):
    heading("05 / TRANSPARENCIA","Fuentes, cobertura y calidad",
        "Lo que el tablero sabe, lo que no sabe y el periodo al que "
        "corresponde cada registro.")
    coverage=evidence_table(D,selected)
    a,b=st.columns([1.15,.85],gap="medium")
    with a:
        with card("Cobertura real de las fuentes",
            "Países con al menos un registro del proveedor dentro del ámbito "
            "seleccionado. No mide intensidad ni calidad del dato.",
            "Inventario versionado de datos OPS",height=CARD_H):
            table(coverage,height=354)
    with b:
        with card("Estado de integración sanitaria",
            "No inferir daños de salud sin una fuente explícita que "
            "documente el evento o el establecimiento afectado.",
            "Alcance validado para el prototipo",height=CARD_H):
            st.markdown("**Disponibles como evidencia contextual**")
            st.markdown("Violencia agregada (HAPI/ACLED); gravedad y acceso (ACAPS); "
                "riesgo estructural (INFORM); PiN (HAPI); movilidad (ACNUR y OIM); "
                "capacidad sanitaria (OPS); 3W y financiación (HAPI); documentos (ReliefWeb).")
            st.markdown("**Aún no integrados como impactos directos**")
            st.markdown("Ataques a salud (OMS SSA), establecimientos afectados, "
                "interrupción de servicios, abastecimiento WASH, "
                "economías ilícitas y tensión política. No asignarles valores cero.")
            st.caption("La autorización de uso, trazabilidad y validación técnica "
                "se revisarán antes de una publicación institucional.")

    with card("Metodología para interpretar el tablero",
         "Las fuentes tienen definiciones, cobertura y años heterogéneos.",
         "Propuesta técnica del Observatorio · OPS/PHE"):
        st.markdown(
         "El tablero separa **hechos documentados**, **señales descriptivas**, "
         "**condiciones de vulnerabilidad**, **hipótesis sanitarias a verificar** "
         "y **vacíos de datos**. Una variación mensual no es una predicción; "
         "una puntuación ACAPS no es un nivel de prioridad OPS. "
         "La ausencia de registros nunca se representa como ausencia de amenaza.")
        df=pd.DataFrame([
          {"Fuente":"ACAPS Severity y Access","Unidad":"Crisis evaluada / país",
           "Límite":"No hay evaluación de todas las crisis; gravedad y acceso no son equivalentes."},
          {"Fuente":"HAPI / ACLED","Unidad":"País–mes–categoría",
           "Límite":"Categorías pueden solaparse; no son víctimas ni incidentes geolocalizados."},
          {"Fuente":"ACNUR / HAPI","Unidad":"Origen–acogida–año–grupo",
           "Límite":"Stock, no flujo; no sumar grupos entre sí."},
          {"Fuente":"OIM DTM","Unidad":"Operación / última ronda",
           "Límite":"Rondas de antigüedad variable; no sumar operaciones."},
          {"Fuente":"HAPI necesidades","Unidad":"Intersectorial / año / categoría",
           "Límite":"PiN se presenta solo si hay total inequívoco; no sumar sectores."},
          {"Fuente":"OPS Indicadores Básicos","Unidad":"País / indicador / año",
           "Límite":"No implica continuidad operativa en el momento de la emergencia."},
          {"Fuente":"ReliefWeb","Unidad":"Informe publicado / país mencionado",
           "Límite":"La publicación no verifica por sí sola el impacto de una crisis."},
        ])
        table(df,height=320)
        st.markdown("[Arquitectura, indicadores y criterios de calidad]"
           "(https://github.com/ivanromero0724/observatorio-humanitario-ops/"
           "blob/main/docs/fase2/arquitectura_indicadores_dashboard.md)")
        st.caption("Las etiquetas crítico, alto, elevado y moderado requieren "
            "definición de indicadores, umbrales y validación por Laura / PHE.")

def main():
    st.set_page_config(page_title="Sala Situacional Humanitaria · OPS/OMS",
         page_icon="🌎",layout="wide",initial_sidebar_state="expanded")
    st.markdown(STYLES,unsafe_allow_html=True)
    D=load_all()
    countries=D.get("countries",pd.DataFrame())
    if countries.empty:st.error("Catálogo regional no disponible.");st.stop()
    names=countries.set_index("iso3")["pais"].to_dict()
    with st.sidebar:
        st.markdown("### OPS / OMS")
        st.caption("Emergencias en Salud · Observatorio Humanitario")
        section=st.radio("Navegación",PAGES,key="nav")
        st.divider()
        region=st.selectbox("Subregión",["Todas las Américas"]+
            sorted(countries["subregion"].dropna().unique()),
            key="region")
        regional=(countries if region=="Todas las Américas" else
                  countries[countries["subregion"]==region])
        choices=sorted(regional["iso3"],key=lambda x:names.get(x,x))
        country=st.selectbox("Ámbito",["Todos los países"]+choices,
               format_func=lambda c:names.get(c,c),key="scope")
        chosen=set(choices) if country=="Todos los países" else {country}
        months=st.selectbox("Periodo de eventos",[6,12,24],
              index=1,format_func=lambda x:f"Últimos {x} meses",
              key="months")
        st.caption(f"{len(chosen)} países en el ámbito. El periodo solo "
                   "filtra eventos mensuales: otras fuentes mantienen su corte.")
        st.divider()
        st.caption("PROTOTIPO ANALÍTICO · no constituye alerta oficial OPS. "
                   "Priorización y umbrales sujetos a validación técnica.")
    hero()
    if section==PAGES[0]:executive(D,chosen,names,months)
    elif section==PAGES[1]:surveillance(D,chosen,names,months)
    elif section==PAGES[2]:readiness(D,chosen,names)
    elif section==PAGES[3]:country_profile(D,chosen,names,months)
    else:sources_page(D,chosen)
    st.write("")
    st.caption("OPS/OMS · Observatorio Humanitario de las Américas · "
               "Fuentes publicadas con cortes heterogéneos. "
               "Producto de apoyo al análisis, no sistema de alerta.")
if __name__=="__main__":
    main()
