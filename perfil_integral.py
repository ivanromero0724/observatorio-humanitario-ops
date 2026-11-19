"""Ficha nacional integral del Observatorio Humanitario OPS/OMS.

Cada fuente mantiene unidad, fecha y cobertura propias. Se muestran solamente
los registros del país elegido sin convertir la ficha en un índice de riesgo OPS.
"""
from __future__ import annotations

from datetime import date
import pandas as pd
import streamlit as st

from observatorio_v2 import filtered, latest_ops, valid_needs, OPS_LABELS
from observatorio_v4 import plot, table, info_missing, reports, fmt
from observatorio_v5 import title, events_by_country, common_last, list_months, crisis_core, oim_scope
from graficos import rank_bars, trend
from panel_coe import card
from tarjetas_resumen import metric_strip

PAHO_BLUE="#009BDA"
ORANGE="#F36B32"
OPS_KEYS=("GINI","Escolaridad","Mortalidad por homicidio","Médicos",
          "Enfermería","Camas hospitalarias","DTP3","SRP1")
CATEGORIES={
    "political_violence":"Violencia política",
    "civilian_targeting":"Violencia contra civiles",
    "demonstration":"Manifestaciones",
}
RISK_DIMENSIONS={
    "hazard_exposure_risk":"Amenazas y exposición",
    "vulnerability_risk":"Vulnerabilidad",
    "coping_capacity_risk":"Falta de capacidad de afrontamiento",
}


def _number(value, decimals=0):
    return fmt(value, decimals) if pd.notna(value) else "—"


def _year(df, column="reference_period_start"):
    if df.empty or column not in df:
        return pd.Series(dtype="Int64")
    return pd.to_numeric(df[column].astype(str).str[:4], errors="coerce").astype("Int64")


def _latest_record(df, field):
    if df.empty or field not in df.columns:
        return None
    v=df.copy()
    v["_when"]=pd.to_datetime(v[field], errors="coerce")
    v=v[v["_when"].notna()].sort_values("_when")
    return None if v.empty else v.iloc[-1]


def _country_deaths(D, iso, months=12):
    events=filtered(D["conflict"],{iso})
    cutoff=common_last(D,"political_violence")
    if events.empty or cutoff is None:
        return float("nan")
    expected=list_months(cutoff,months)
    m=events[(events["tipo_evento"]=="political_violence")&
             (events["fecha"].isin(expected))].copy()
    if m["fecha"].nunique()!=months:
        return float("nan")
    m["muertes_reportadas"]=pd.to_numeric(m["muertes_reportadas"],errors="coerce")
    if m.groupby("fecha")["muertes_reportadas"].count().eq(0).any():
        return float("nan")
    return m["muertes_reportadas"].sum(min_count=1)


def _un_latest(un, group):
    subset=un[un["grupo_poblacion"]==group].copy() if not un.empty else un
    if subset.empty:
        return float("nan"), None
    subset["anio"]=pd.to_numeric(subset["anio"],errors="coerce")
    year=subset["anio"].max()
    subset=subset[subset["anio"]==year]
    return pd.to_numeric(subset["personas"],errors="coerce").sum(min_count=1), int(year)


def _pin_latest(needs):
    """Una sola estimación intersectorial sin duplicar año, categoría o fuente."""
    n=valid_needs(needs)
    if n.empty:
        return None
    n=n.copy()
    n["anio"]=_year(n)
    n=n[n["anio"].notna()]
    # Si una misma referencia publica dos cifras distintas, se considera ambigua.
    n=n[~n.duplicated(["iso3","anio"],keep=False)]
    n=n.dropna(subset=["population"]).sort_values("anio")
    return None if n.empty else n.iloc[-1]


def _data_note(message):
    st.caption(message)


def _summary(D, iso, chosen):
    events, last=events_by_country(D,chosen,"political_violence",12)
    event_value=events["eventos"].iloc[0] if not events.empty else float("nan")
    deaths=_country_deaths(D,iso)
    acaps=crisis_core(D,chosen)
    risk=filtered(D["inform_hapi"],chosen)
    rv=risk["overall_risk"].iloc[0] if not risk.empty else float("nan")
    un=filtered(D["acnur"],chosen,"asilo_iso3")
    ref,ref_year=_un_latest(un,"REF")
    metric_strip([
        (_number(event_value),"EVENTOS DE VIOLENCIA","Política · 12 meses"),
        (_number(deaths),"MUERTES REPORTADAS","ACLED · 12 meses"),
        (str(acaps["crisis_id"].nunique()) if not acaps.empty else "—",
         "CRISIS EVALUADAS","ACAPS · último corte"),
        (_number(rv,1),"RIESGO INFORM","Índice 0–10 · 2025"),
        (_number(ref),"PERSONAS REFUGIADAS",
         f"Acogidas · ACNUR {ref_year}" if ref_year else "ACNUR · sin registro"),
    ])
    _data_note("Fuentes y fechas independientes. Las muertes ACLED son estimaciones; "
               "INFORM y ACAPS no establecen prioridades OPS. "
               f"Eventos hasta {last.strftime('%Y-%m') if last is not None else 'sin fecha'}.")


def _violence(D,chosen):
    source=filtered(D["conflict"],chosen)
    if source.empty:
        info_missing("eventos HAPI/ACLED")
        return
    cat=st.selectbox("Tipo de evento",list(CATEGORIES),
       format_func=lambda c:CATEGORIES[c],key="op_profile_event_type")
    counts,cut=events_by_country(D,chosen,cat,12)
    val=counts["eventos"].iloc[0] if not counts.empty else float("nan")
    window=source[(source["tipo_evento"]==cat)&
                  (source["fecha"].isin(list_months(cut,12) if cut is not None else []))].copy()
    window["muertes_reportadas"]=pd.to_numeric(window["muertes_reportadas"],errors="coerce")
    left,right=st.columns(2,gap="medium")
    with left:
        with card("Evolución de eventos",
                  f"{CATEGORIES[cat]} · últimos 12 meses, sin mezclar categorías.",
                  "OCHA HAPI / ACLED",height=420):
            if window.empty:
                info_missing("serie mensual")
            else:
                by=window.groupby("fecha",as_index=False)["eventos"].sum(min_count=1)
                plot(trend(by,x="fecha",y="eventos",units="Eventos por mes"),height=366)
    with right:
        with card("Magnitud y muertes reportadas",
                  "Los fallecimientos no equivalen a mortalidad oficial.",
                  "OCHA HAPI / ACLED",height=420):
            st.metric("Eventos · 12 meses",_number(val))
            if window["muertes_reportadas"].notna().any() and cat!="demonstration":
                st.metric("Muertes reportadas",_number(
                    window["muertes_reportadas"].sum(min_count=1)))
            else:
                st.caption("La fuente no publica muertes para esta categoría.")
            st.caption(f"Último mes: {cut.strftime('%Y-%m') if cut is not None else '—'}. "
                       "Puede estar incompleto.")
    _data_note("Las categorías de violencia política y violencia contra civiles pueden "
               "solaparse; no se suman entre sí.")


def _acaps(D,chosen):
    acaps=crisis_core(D,chosen)
    access=filtered(D["access"],chosen)
    if acaps.empty:
        info_missing("evaluaciones ACAPS de conflicto, movilidad o inseguridad")
        return
    names=acaps[["crisis_id","crisis","puntuacion","acceso","drivers","corte_api"]].copy()
    left,right=st.columns(2,gap="medium")
    with left:
        with card("Crisis humanitarias evaluadas",
                  "Severidad y acceso se expresan en escalas diferentes.",
                  "ACAPS Severity / Humanitarian Access",height=420):
            table(names,height=354,
                  columns=["crisis","puntuacion","acceso","corte_api"],
                  labels={"crisis":"Crisis","puntuacion":"Severidad / 10",
                          "acceso":"Acceso / 5","corte_api":"Edición"})
    with right:
        with card("Factores y dimensiones de las crisis",
                  "Factores publicados, impacto y complejidad de cada contexto.",
                  "ACAPS INFORM Severity",height=420):
            choices=acaps["crisis_id"].dropna().unique().tolist()
            cid=st.selectbox("Crisis",choices,key="op_profile_acaps_crisis",
                format_func=lambda k:str(acaps.loc[acaps["crisis_id"]==k,"crisis"].iloc[0]))
            v=acaps[acaps["crisis_id"]==cid].iloc[0]
            st.caption("Factores impulsores: "+str(v.get("drivers") or "Sin detalle"))
            components=pd.DataFrame([
                {"Dimensión":name,"Puntuación":v.get(key)}
                for key,name in [
                    ("impacto_crisis","Impacto de la crisis"),
                    ("impacto_humano","Impacto humano"),
                    ("complejidad","Complejidad"),
                    ("entorno_operativo","Entorno operativo")]])
            plot(rank_bars(components,label="Dimensión",value="Puntuación",
                           limit=4,formats=".1f",units="Puntuación / 10",
                           max_x=10),height=250)
    # Dimensiones completas de Severidad para la crisis elegida.
    severity_dimensions=[
        ("impacto_crisis","Impacto de la crisis"),
        ("impacto_geografico","Impacto geográfico"),
        ("impacto_humano","Impacto humano"),
        ("condiciones_afectados","Condiciones de afectados"),
        ("personas_necesidad","Personas en necesidad · componente"),
        ("concentracion_condiciones","Concentración de condiciones"),
        ("complejidad","Complejidad"),
        ("sociedad_seguridad","Sociedad y seguridad"),
        ("entorno_operativo","Entorno operativo"),
    ]
    v=acaps[acaps["crisis_id"]==cid].iloc[0]
    left,right=st.columns(2,gap="medium")
    with left:
        with card("Dimensiones de severidad ACAPS",
                  "Puntuaciones de una crisis; no son recuentos de personas.",
                  "ACAPS INFORM Severity · escala 0–10",height=425):
            dim=pd.DataFrame([
                {"Dimensión":label,"Puntuación":v.get(key)}
                for key,label in severity_dimensions])
            table(dim,height=345)
    with right:
        with card("Indicadores de acceso humanitario",
                  "Pilares P1–P3 e indicadores I1–I9 de la crisis elegida.",
                  "ACAPS Humanitarian Access",height=425):
            sub=access[access["crisis_id"]==cid]
            if sub.empty:
                info_missing("desglose de acceso de la crisis")
            else:
                z=sub.iloc[0]
                measures=[
                    {"Componente":f"P{n} · Pilar","Valor":z.get(f"pilar_{n}")}
                    for n in range(1,4)
                ]+[
                    {"Componente":f"I{n} · Indicador","Valor":z.get(f"indicador_{n}")}
                    for n in range(1,10)
                ]
                table(pd.DataFrame(measures),height=323)
                gap=z.get("brecha_info")
                if pd.notna(gap):
                    st.caption("Brecha de información: "+_number(float(gap)*100,1)+" %.")
    st.caption("Los valores de severidad, acceso, pilares e indicadores usan escalas "
               "distintas y no deben sumarse. P1–P3 e I1–I9 se interpretan "
               "conforme al código de ACAPS.")


def _movement(D,chosen):
    un=filtered(D["acnur"],chosen,"asilo_iso3")
    dtm=oim_scope(filtered(D["dtm"],chosen))
    left,right=st.columns(2,gap="medium")
    with left:
        with card("Refugio y asilo en el país de acogida",
                  "Existencias de población por año, no nuevos desplazamientos.",
                  "ACNUR / OCHA HAPI",height=420):
            data=[]
            for code,label in (("REF","Personas refugiadas"),
                               ("ASY","Solicitantes de asilo")):
                value,year=_un_latest(un,code)
                if year:
                    data.append({"Categoría":label,"Año":year,"Personas":value})
            if data:
                table(pd.DataFrame(data),height=265)
                st.caption("Cada categoría se interpreta por separado; no sumar años.")
            else:
                info_missing("datos de acogida ACNUR")
    with right:
        with card("Desplazamiento interno por operación",
                  "Últimas rondas reportadas; no equivalen al stock nacional.",
                  "OIM DTM Baseline",height=420):
            if dtm.empty:
                info_missing("operaciones de conflicto/inseguridad DTM")
            else:
                operations=sorted(dtm["operacion"].dropna().unique())
                operation=st.selectbox("Operación DTM",operations,
                                       key="op_profile_dtm_operation")
                detail=dtm[dtm["operacion"]==operation].copy()
                latest=detail["fecha_reporte"].max()
                detail=detail[detail["fecha_reporte"]==latest]
                rounds=pd.to_numeric(detail["ronda"],errors="coerce")
                if rounds.notna().any():
                    detail=detail[rounds==rounds.max()]
                table(detail,height=246,
                    columns=["origen_admin1","personas_idp_reportadas","hombres","mujeres"],
                    labels={"origen_admin1":"Área","personas_idp_reportadas":"Personas",
                            "hombres":"Hombres","mujeres":"Mujeres"})
                st.caption("Corte: "+str(latest)[:10]+
                           ". No sumar diferentes rondas u operaciones.")


def _needs(D,chosen):
    needs=filtered(D["needs"],chosen)
    top=_pin_latest(needs)
    ipc=filtered(D["ipc"],chosen)
    left,right=st.columns(2,gap="medium")
    with left:
        with card("Personas en necesidad humanitaria",
                  "Total intersectorial publicado, cuando existe una estimación inequívoca.",
                  "OCHA Humanitarian Needs / HAPI",height=420):
            if top is None:
                info_missing("estimación intersectorial PiN no duplicada")
            else:
                st.metric("PiN · "+str(top["anio"]),_number(top["population"]))
                st.caption("No sumar PiN entre sectores o grupos de población.")
            if not needs.empty:
                sector=needs[(needs["population_status"]=="INN")&
                    (needs["sector_code"].astype(str).str.lower()!="intersectoral")].copy()
                if not sector.empty:
                    sector["year"]=_year(sector)
                    yr=sector["year"].max()
                    sector=sector[sector["year"]==yr].copy()
                    sector=sector.sort_values("population",ascending=False)
                    st.caption(f"Necesidades sectoriales publicadas ({yr}); pueden superponerse.")
                    table(sector.head(5),height=174,
                          columns=["sector_name","population"],
                          labels={"sector_name":"Sector","population":"Personas"})
    with right:
        with card("Seguridad alimentaria · IPC",
                  "Fases individuales de la evaluación actual más reciente.",
                  "IPC / OCHA HAPI",height=420):
            if ipc.empty:
                info_missing("evaluaciones IPC")
            else:
                ipc=ipc.copy()
                ipc=ipc[ipc["ipc_type"]=="current"]
                if ipc.empty:
                    info_missing("evaluación IPC actual")
                else:
                    end=ipc["reference_period_end"].max()
                    v=ipc[(ipc["reference_period_end"]==end)&
                          (ipc["ipc_phase"].astype(str).isin(["1","2","3","4","5"]))].copy()
                    if v.empty:
                        info_missing("fases individuales IPC")
                    else:
                        v["personas"]=pd.to_numeric(v["population_in_phase"],errors="coerce")
                        plot(rank_bars(v,label="ipc_phase",value="personas",
                          limit=5,formats=".0f",units="Personas"),height=292)
                        st.caption("Corte: "+str(end)[:10]+". No sumar fases agregadas 3+.")


def _risk(D,chosen):
    risk=filtered(D["inform_hapi"],chosen)
    newer=filtered(D["risk"],chosen)
    ops=filtered(D["ops"],chosen)
    left,right=st.columns(2,gap="medium")
    with left:
        with card("Riesgo estructural INFORM",
                  "Componentes del índice (2025), no prioridad OPS.",
                  "INFORM Risk / OCHA HAPI · 2025",height=420):
            if risk.empty:
                info_missing("perfil INFORM")
            else:
                r=risk.iloc[0]
                st.metric("Índice compuesto · 2025",_number(r["overall_risk"],1)+" / 10")
                new=float("nan") if newer.empty else newer["puntuacion"].iloc[0]
                st.caption("Edición Mid 2026 (otra versión): "+_number(new,1)+" / 10")
                data=pd.DataFrame([
                    {"Componente":label,"Valor":r.get(key)}
                    for key,label in RISK_DIMENSIONS.items()
                ])
                plot(rank_bars(data,label="Componente",value="Valor",limit=3,
                    formats=".1f",max_x=10,units="Puntuación / 10"),height=225)
    with right:
        with card("Indicadores sociales y sanitarios",
                  "Último año publicado de cada indicador; años no necesariamente iguales.",
                  "OPS · Indicadores Básicos",height=420):
            rows=[]
            for key in OPS_KEYS:
                r=latest_ops(ops,key) if not ops.empty else pd.DataFrame()
                if not r.empty:
                    v=r.iloc[0]
                    rows.append({"Indicador":OPS_LABELS.get(key,key),
                                 "Valor":_number(v["valor"],1),
                                 "Año":int(v["periodo"])})
            if not rows:
                info_missing("indicadores OPS")
            else:
                table(pd.DataFrame(rows),height=345)
    _data_note("INFORM incluye amenazas naturales y otros riesgos; no se usa como "
               "calificación de seguridad ni se combina con ACAPS.")


def _poverty(D,chosen):
    mpi=filtered(D["mpi"],chosen)
    left,right=st.columns(2,gap="medium")
    with left:
        with card("Pobreza multidimensional",
                  "Indicadores OPHI: incidencia, intensidad y privación.",
                  "OPHI MPI / OCHA HAPI",height=350):
            recent=_latest_record(mpi,"reference_period_start")
            if recent is None:
                info_missing("pobreza multidimensional")
            else:
                rows=[
                    {"Indicador":"Incidencia de pobreza","Valor":_number(recent.get("headcount_ratio"),1)+" %"},
                    {"Indicador":"Intensidad de privación","Valor":_number(recent.get("intensity_of_deprivation"),1)+" %"},
                    {"Indicador":"Índice MPI","Valor":_number(recent.get("mpi"),3)},
                    {"Indicador":"Pobreza severa","Valor":_number(recent.get("in_severe_poverty"),1)+" %"},
                    {"Indicador":"Vulnerables a pobreza","Valor":_number(recent.get("vulnerable_to_poverty"),1)+" %"},
                ]
                table(pd.DataFrame(rows),height=240)
                st.caption("Año de referencia: "+str(recent["reference_period_start"])[:4])
    with right:
        with card("Metadatos del riesgo INFORM",
                  "Calidad informada de los indicadores subyacentes.",
                  "INFORM / OCHA HAPI · 2025",height=350):
            risk=filtered(D["inform_hapi"],chosen)
            if risk.empty:
                info_missing("metadatos INFORM")
            else:
                r=risk.iloc[0]
                score=pd.to_numeric(r.get("meta_missing_indicators_pct"),errors="coerce")
                recent=pd.to_numeric(r.get("meta_avg_recentness_years"),errors="coerce")
                st.metric("Indicadores fuente faltantes/estimados",
                          _number(score*100,1)+" %" if pd.notna(score) else "—")
                st.metric("Antigüedad media de indicadores",
                          _number(recent,2)+" años" if pd.notna(recent) else "—")


def _response(D,chosen):
    presence=filtered(D["presence"],chosen)
    funding=filtered(D["funding"],chosen)
    left,right=st.columns(2,gap="medium")
    with left:
        with card("Presencia operativa por sector",
                  "Organizaciones distintas dentro de cada sector; no sumar sectores.",
                  "OCHA 3W / HAPI",height=440):
            if presence.empty:
                info_missing("presencia humanitaria 3W")
            else:
                p=presence.copy()
                d=p["fecha_hasta"].max()
                p=p[p["fecha_hasta"]==d]
                plot(rank_bars(p,label="sector",value="organizaciones_distintas",
                     limit=12,formats=".0f",units="Organizaciones"),height=310)
                st.caption("Corte: "+str(d)[:10])
    with right:
        with card("Financiación de planes humanitarios",
                  "Apelaciones identificadas, no toda la financiación recibida.",
                  "OCHA FTS / HAPI · USD",height=440):
            if funding.empty:
                info_missing("apelaciones FTS")
            else:
                f=funding[~funding["appeal_code"].fillna("").astype(str)
                          .str.lower().isin(["not specified",""])].copy()
                f["_year"]=_year(f)
                f=f[f["_year"]<=date.today().year]
                if f.empty:
                    info_missing("apelaciones con código identificado")
                else:
                    y=f["_year"].max()
                    f=f[f["_year"]==y]
                    f=f[["appeal_name","requirements_usd","funding_usd","funding_pct"]]
                    table(f,height=303,labels={
                        "appeal_name":"Plan","requirements_usd":"Requerido (USD)",
                        "funding_usd":"Financiado (USD)","funding_pct":"Cobertura (%)"})
                    st.caption("Año del plan: "+str(y))


def _documents(D,chosen):
    data=reports(D,chosen,limit=20)
    if data.empty:
        info_missing("informes humanitarios recientes")
        return
    data=data.drop_duplicates("reporte_id").copy()
    data["Fecha"]=data["fecha_publicacion_rw"].astype(str).str[:10]
    with card("Informes humanitarios asociados al país",
              "Documentos originales, organizaciones y fecha de publicación.",
              "OCHA ReliefWeb · metadatos publicados"):
        table(data,height=490,columns=["Fecha","titulo","fuentes","url"],
              labels={"titulo":"Informe","fuentes":"Organización","url":"Documento"},
              link="Documento")
    st.caption("La aparición en un informe no implica necesariamente que "
               "todos los hechos narrados ocurrieran en el país.")


def profile_page(D, selected, names):
    title("04 / PERFILES POR PAÍS","Ficha humanitaria por país",
          "Todos los ámbitos del observatorio, reunidos para un país con sus fuentes y fechas.")
    choices=sorted(selected,key=lambda c:names.get(c,c))
    if not choices:
        info_missing("países del ámbito")
        return
    country=st.selectbox("Seleccionar país",choices,
            index=choices.index("COL") if "COL" in choices else 0,
            format_func=lambda code:names.get(code,code),key="op_profile_country")
    scope={country}
    _summary(D,country,scope)
    group=st.segmented_control("Contenido del país",
          ["Amenazas y crisis","Movilidad y necesidades",
           "Riesgo y vulnerabilidad","Respuesta e informes"],
          default="Amenazas y crisis",selection_mode="single",
          width="content",label_visibility="collapsed",key="op_perfil_grupo")
    group=group or "Amenazas y crisis"
    if group=="Amenazas y crisis":
        _violence(D,scope)
        _acaps(D,scope)
    elif group=="Movilidad y necesidades":
        _movement(D,scope)
        _needs(D,scope)
    elif group=="Riesgo y vulnerabilidad":
        _risk(D,scope)
        _poverty(D,scope)
    else:
        _response(D,scope)
        _documents(D,scope)
