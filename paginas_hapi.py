"""HAPI: necesidades, apelaciones, IPC, pobreza e INFORM Risk.

Solo datos nacionales originales y snapshots exhaustivos. Nunca se suman
sectores, diferentes años, proyecciones, apelaciones ni países sin datos.
"""
from __future__ import annotations

from datetime import datetime,timezone
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from graficos import finish,rank_bars,strip_countries

def _date(x):
    return str(x).split("T")[0][:10]

def _year(d):
    return d.astype(str).str[:4].str.extract(r"(\d{4})")[0]

def _country(df,countries,key):
    valid=sorted(set(df["iso3"]))
    if not valid:return None
    names=countries.set_index("iso3")["pais"].to_dict()
    return st.selectbox("País",valid,format_func=lambda code:names.get(code,code),key=key)

def _export(df,name):
    st.download_button("Descargar tabla filtrada",
        df.to_csv(index=False).encode("utf-8-sig"),
        file_name=name,mime="text/csv",key="exp_"+name)

def _empty(source,valid):
    st.info(f"No se registran datos nacionales de {source} para los países "
            "seleccionados. Esto no significa que el fenómeno esté ausente.")
    st.caption(f"Cobertura verificada en el catálogo: {valid} países.")

def render(needs:pd.DataFrame,funding:pd.DataFrame,risk:pd.DataFrame,
           poverty:pd.DataFrame,ipc:pd.DataFrame,countries:pd.DataFrame,
           selected:set,meta:dict):
    st.markdown('<div class="ops-kicker">05 / NECESIDADES Y RESPUESTA</div>'
                '<div class="ops-section">Necesidades, vulnerabilidad y respuesta humanitaria</div>',
                unsafe_allow_html=True)
    st.caption("Cinco familias de HDX HAPI con alcance y cortes diferenciados. "
        "Las 35 consultas por fuente terminaron completamente; esto no implica "
        "que todas contengan registros. No se han calculado índices OPS.")
    names=countries.set_index("iso3")["pais"].to_dict()
    sources=[("necesidades",needs,"Necesidades"),
             ("financiacion",funding,"Financiación"),
             ("riesgo",risk,"INFORM"),
             ("pobreza",poverty,"Pobreza"),
             ("inseguridad_alimentaria",ipc,"IPC")]
    a,b,c,d,e=st.columns(5)
    for box,(_,data,label) in zip([a,b,c,d,e],sources):
        box.metric(label+" · países",
                   f"{data[data['iso3'].isin(selected)]['iso3'].nunique()}/{len(selected)}" if not data.empty else "—")
    ts=meta.get("fecha_extraccion_utc","")
    st.caption("Extracción HAPI: "+str(ts)[:10]+". "
        "Se diferencian los países sin registros de los que cuentan con estimaciones.")
    st.divider()
    t1,t2,t3,t4,t5=st.tabs([
        "Personas en necesidad","Financiación",
        "Pobreza multidimensional","Seguridad alimentaria","Riesgo y capacidades"
    ])
    with t1:
        st.markdown("#### Población con necesidades humanitarias")
        st.caption("PiN (INN), población objetivo (TGT), afectada (AFF) y "
            "alcanzada (REA) son estados distintos. No sumar sectores: "
            "la misma persona puede estar incluida en varios.")
        if needs.empty:
            _empty("HAPI Humanitarian Needs",0)
        else:
            df=needs[needs["iso3"].isin(selected)].copy()
            if df.empty:_empty("necesidades",0)
            else:
                df["poblacion"]=pd.to_numeric(df["population"],errors="coerce")
                df["anio"]=_year(df["reference_period_start"])
                # Solo intersectoral con categoría total/no desagregada.
                agg=df[(df["sector_code"].astype(str).str.lower()=="intersectoral")&
                       (df["population_status"].astype(str)=="INN")&
                       (df["category"].fillna("").astype(str).str.lower().isin(
                           ["","total","all"]))].copy()
                agg=agg.sort_values(["iso3","anio","reference_period_end"],
                                    ascending=[True,False,False])
                # Country-year may have multiple resources or categories. Never sum.
                cnt=agg.groupby(["iso3","anio"]).size()
                ambiguous=set(cnt[cnt>1].index)
                if ambiguous:
                    agg=agg[~agg.set_index(["iso3","anio"]).index.isin(ambiguous)]
                    st.caption("Las parejas país-año con más de una fila agregada "
                        "se excluyen del ranking para evitar duplicación.")
                latest=agg.drop_duplicates("iso3",keep="first")
                if not latest.empty:
                    latest["pais"]=latest["iso3"].map(names)
                    latest["periodo"] = latest["anio"]
                    st.markdown("**Personas en necesidad · intersectorial (último año disponible)**")
                    fig=strip_countries(latest,name="pais",val="poblacion",
                                        year="periodo",max_items=16,
                                        units="Personas estimadas")
                    st.plotly_chart(fig,use_container_width=True,
                                    config={"displayModeBar":False})
                    st.caption("Diferentes años por país; la comparación NO es "
                               "una estimación homogénea del mismo corte.")
                iso=_country(df,countries,"hapi_needs_country")
                sub=df[df["iso3"]==iso].copy()
                years=sorted(sub["anio"].dropna().unique(),reverse=True)
                yr=st.selectbox("Año de estimación",years,
                               key="hapi_needs_year")
                sub=sub[sub["anio"]==yr]
                choices=sorted(sub["population_status"].dropna().unique())
                status=st.selectbox("Estado de población",choices,
                         index=choices.index("INN") if "INN" in choices else 0,
                         key="hapi_needs_status")
                sub=sub[sub["population_status"]==status]
                sectors=sorted(sub["sector_name"].dropna().unique())
                if sectors:
                    sector=st.selectbox("Sector",sectors,index=sectors.index(
                        "Intersectoral") if "Intersectoral" in sectors else 0,
                        key="hapi_needs_sector")
                    sub=sub[sub["sector_name"]==sector]
                # Más de una categoría representa desglose, no sumable a total.
                cols=["sector_name","category","population_status","poblacion",
                      "reference_period_start","reference_period_end"]
                display=sub[cols].rename(columns={
                    "sector_name":"Sector","category":"Categoría",
                    "population_status":"Estado","poblacion":"Personas estimadas",
                    "reference_period_start":"Desde","reference_period_end":"Hasta"})
                st.dataframe(display,use_container_width=True,hide_index=True,height=230)
                _export(display,"hapi_necesidades.csv")
    with t2:
        st.markdown("#### Financiación de apelaciones y planes")
        st.caption("Cobertura limitada a apelaciones incluidas en OCHA FTS. "
            "No refleja todos los recursos recibidos para un país. "
            "Una misma apelación puede aparecer en varios países o años.")
        if funding.empty:_empty("FTS",0)
        else:
            df=funding[funding["iso3"].isin(selected)].copy()
            if df.empty:_empty("financiación",0)
            else:
                df["anio"]=_year(df["reference_period_start"])
                current_year=datetime.now(timezone.utc).year
                years=sorted([y for y in df["anio"].dropna().unique()
                              if y.isdigit() and int(y)<=current_year],reverse=True)
                year=st.selectbox("Año de financiación",years, key="hapi_fund_year") if years else None
                if year:
                    df=df[df["anio"]==year]
                iso=_country(df,countries,"hapi_fund_country")
                if iso:
                    sub=df[df["iso3"]==iso].copy()
                    for k in ("funding_usd","requirements_usd","funding_pct"):
                        sub[k]=pd.to_numeric(sub[k],errors="coerce")
                    filtered=sub[(sub["appeal_code"].fillna("").str.lower()!="not specified")&
                                 sub["appeal_code"].notna()].copy()
                    if filtered.empty:
                        st.info("Solo se registraron aportes sin apelación especificada "
                                "para este país y año. No hay un porcentaje financiado calculable.")
                    else:
                        st.markdown("**Apelaciones identificadas**")
                        cols=["appeal_name","appeal_type","requirements_usd",
                              "funding_usd","funding_pct"]
                        table=filtered[cols].rename(columns={
                           "appeal_name":"Apelación","appeal_type":"Tipo",
                           "requirements_usd":"Requerimiento (USD)",
                           "funding_usd":"Financiado (USD)",
                           "funding_pct":"Cobertura reportada (%)"})
                        st.dataframe(table,use_container_width=True,
                                     hide_index=True,height=300)
                        plot=filtered.dropna(subset=["funding_pct"])
                        if not plot.empty:
                            fig=rank_bars(plot,label="appeal_name",
                                value="funding_pct",limit=12,
                                units="% financiado",formats=".1f")
                            st.plotly_chart(fig,use_container_width=True,
                                             config={"displayModeBar":False})
                        _export(table,"hapi_apelaciones.csv")
                    if not sub.empty:
                        st.caption("El proveedor también puede tener financiación "
                            "no atribuida a una apelación. Esos registros no se "
                            "utilizan para calcular porcentajes.")
    with t3:
        st.markdown("#### Índice de Pobreza Multidimensional (MPI)")
        st.caption("OPHI: MPI es un índice fraccional; incidencia, intensidad y "
            "pobreza severa se expresan en porcentajes. Los años pueden variar.")
        if poverty.empty:_empty("pobreza multidimensional",0)
        else:
            df=poverty[poverty["iso3"].isin(selected)].copy()
            if df.empty:_empty("pobreza multidimensional",0)
            else:
                for k in ("mpi","headcount_ratio","intensity_of_deprivation",
                          "in_severe_poverty","vulnerable_to_poverty"):
                    df[k]=pd.to_numeric(df[k],errors="coerce")
                df["anio"]=_year(df["reference_period_start"])
                last=df.sort_values(["iso3","anio"],ascending=[True,False])
                last=last.drop_duplicates("iso3",keep="first").copy()
                last["pais"]=last["iso3"].map(names)
                st.markdown("**Incidencia de pobreza multidimensional · último corte disponible**")
                fig=strip_countries(last,name="pais",val="headcount_ratio",
                            year="anio",max_items=20,units="% población")
                st.plotly_chart(fig,use_container_width=True,
                                config={"displayModeBar":False})
                iso=_country(df,countries,"hapi_mpi_country")
                if iso:
                    current=df[df["iso3"]==iso].sort_values("anio",ascending=False)
                    year=st.selectbox("Año de medición",
                        sorted(current["anio"].dropna().unique(),reverse=True),
                        key="hapi_mpi_year")
                    row=current[current["anio"]==year].iloc[0]
                    a,b,c,d=st.columns(4)
                    a.metric("MPI",f"{row['mpi']:.3f}" if pd.notna(row["mpi"]) else "—")
                    b.metric("Incidencia",f"{row['headcount_ratio']:.1f}%" if pd.notna(row["headcount_ratio"]) else "—")
                    c.metric("Intensidad",f"{row['intensity_of_deprivation']:.1f}%" if pd.notna(row["intensity_of_deprivation"]) else "—")
                    d.metric("Pobreza severa",f"{row['in_severe_poverty']:.1f}%" if pd.notna(row["in_severe_poverty"]) else "—")
                    st.caption("No interpretar diferencias entre países como tendencias "
                               "si los años y metodologías de las encuestas no coinciden.")
    with t4:
        st.markdown("#### Clasificación Integrada de la Seguridad Alimentaria (IPC)")
        st.caption("Fases 1–5; distinguir análisis actuales de proyecciones. "
            "Cada evaluación tiene una fecha de inicio y fin.")
        if ipc.empty:_empty("IPC",0)
        else:
            df=ipc[ipc["iso3"].isin(selected)].copy()
            if df.empty:_empty("IPC",0)
            else:
                df["personas"]=pd.to_numeric(df["population_in_phase"],errors="coerce")
                iso=_country(df,countries,"hapi_ipc_country")
                current=df[df["iso3"]==iso]
                types=sorted(current["ipc_type"].dropna().unique())
                typ=st.selectbox("Tipo de estimación",types,
                    index=types.index("current") if "current" in types else 0,
                    key="hapi_ipc_type")
                current=current[current["ipc_type"]==typ]
                periods=sorted(current["reference_period_start"].dropna().unique(),reverse=True)
                date=st.selectbox("Inicio del periodo",periods,
                    format_func=_date,key="hapi_ipc_date")
                current=current[current["reference_period_start"]==date]
                count=current.groupby("ipc_phase").size()
                if (count>1).any():
                    st.warning("Existen registros repetidos por fase para este periodo; "
                               "no se publicará un gráfico agregado.")
                else:
                    cur=current.sort_values("ipc_phase").copy()
                    cur["Fase"]=cur["ipc_phase"].astype(str)
                    fig=rank_bars(cur,label="Fase",value="personas",
                        units="Personas",limit=10,formats=".0f")
                    st.plotly_chart(fig,use_container_width=True,
                                    config={"displayModeBar":False})
                table=current[["ipc_phase","ipc_type","personas",
                    "population_fraction_in_phase","reference_period_end"]].rename(
                    columns={"ipc_phase":"Fase","ipc_type":"Tipo",
                    "personas":"Personas estimadas",
                    "population_fraction_in_phase":"Fracción población",
                    "reference_period_end":"Fin periodo"})
                st.dataframe(table,use_container_width=True,hide_index=True)
                _export(table,"hapi_ipc.csv")
                st.caption("Los datos no se extrapolan a países que carecen de "
                    "evaluación IPC. Un 'cero' no se imputa por ausencia.")
    with t5:
        st.markdown("#### Componentes del riesgo nacional INFORM")
        st.caption("HAPI proporciona el corte INFORM publicado en su propia API, "
            "que puede ser distinto del archivo INFORM Risk Mid 2026 del mapa "
            "regional. No se combinan sus versiones en un mismo valor.")
        if risk.empty:_empty("INFORM HAPI",0)
        else:
            df=risk[risk["iso3"].isin(selected)].copy()
            if df.empty:_empty("INFORM HAPI",0)
            else:
                iso=_country(df,countries,"hapi_inform_country")
                r=df[df["iso3"]==iso].iloc[-1]
                period=_date(r["reference_period_start"])[:4]
                a,b,c,d=st.columns(4)
                for box,k,label in zip([a,b,c,d],
                   ["overall_risk","hazard_exposure_risk",
                    "vulnerability_risk","coping_capacity_risk"],
                   ["Riesgo global","Amenaza y exposición",
                    "Vulnerabilidad","Déficit de respuesta"]):
                    v=pd.to_numeric(pd.Series([r[k]]),errors="coerce").iloc[0]
                    box.metric(label,f"{v:.1f} / 10" if pd.notna(v) else "—")
                st.caption(f"Edición de referencia HAPI: {period}; "
                    "ranking mundial y cobertura de indicadores disponibles "
                    "en el CSV de origen.")
                df["pais"]=df["iso3"].map(names)
                df["overall_risk"]=pd.to_numeric(df["overall_risk"],errors="coerce")
                fig=rank_bars(df,label="pais",value="overall_risk",
                            limit=15,units="Puntuación / 10",max_x=10.8)
                st.plotly_chart(fig,use_container_width=True,
                                config={"displayModeBar":False})
    st.divider()
    st.caption("Fuente: HDX Humanitarian API v2 · 35 países consultados para "
               "cada tema, con paginación completa por fuente y fecha. "
               "La disponibilidad es específica de cada dataset.")
