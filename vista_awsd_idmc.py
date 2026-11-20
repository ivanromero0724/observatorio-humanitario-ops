"""Vistas agregadas de IDMC y AWSD, integradas sin nuevas páginas principales.

Unidades separadas: movimientos nuevos ≠ personas todavía desplazadas.
AWSD refiere a trabajadores humanitarios, no a ataques contra centros de salud.
Datos fuente: exportaciones públicas autorizadas, nunca incidentes individuales.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from observatorio_v2 import filtered, ROOT, SOURCES
from observatorio_v4 import info_missing, plot, table, fmt
from graficos import rank_bars, trend
from mapa_coe import pa_map
from panel_coe import card, table_card
from tarjetas_resumen import metric_strip

H = 420
ORANGE = "#F36B32"
AWS_SOURCE = "AWSD / Humanitarian Outcomes · registros agregados"
IDMC_SOURCE = "IDMC GIDD · CC BY-NC-SA 3.0 IGO"

AWS_METRICS = (
    ("incidentes", "INCIDENTES REGISTRADOS"),
    ("trabajadores_muertos", "TRABAJADORES FALLECIDOS"),
    ("trabajadores_heridos", "TRABAJADORES HERIDOS"),
    ("trabajadores_secuestrados", "TRABAJADORES SECUESTRADOS"),
)
GIDD_METRICS = {
    "Nuevos desplazamientos": "nuevos_desplazamientos",
    "Personas desplazadas al cierre del año": "personas_desplazadas_fin_anio",
}

def _data(D, key, selected):
    frame=D.get(key, pd.DataFrame())
    if frame is None or frame.empty:return pd.DataFrame()
    return filtered(frame,selected)

def _names(D):
    return D["countries"].set_index("iso3")["pais"].to_dict()

def _metric_number(series):
    s=pd.to_numeric(series, errors="coerce")
    # Sin imputación de datos faltantes por cero.
    return fmt(s.sum(),0) if len(s) and s.notna().all() else "—"

def _map_frame(D, selected, source, col):
    base=filtered(D["countries"], selected)[["iso3","pais"]]
    return base.merge(source[["iso3",col]].rename(columns={col:"valor"}),
                      on="iso3",how="left")

def _status(D):
    return D.get("idmc_awsd_meta",{})

def awsd_tab(D, selected):
    """Amenazas / tercer subtema: solo totales nacionales anuales."""
    a=_data(D,"awsd",selected)
    if a.empty:
        info_missing("datos agregados AWSD para el ámbito seleccionado")
        st.caption("Fuente: AWSD / Humanitarian Outcomes. La ausencia de registros "
                   "no equivale a ausencia de incidentes.")
        return
    names=_names(D)
    years=sorted(a["anio"].dropna().astype(int).unique(),reverse=True)
    if not years:
        info_missing("años con incidentes AWSD")
        return
    # El tablero presenta únicamente totales anuales verificados por país;
    # no ofrece un selector de tipo de ataque.
    year=st.selectbox("Año de incidentes",years,key="op_awsd_year",
                      width="stretch")
    scope=a[a["anio"].eq(year)].copy()
    scope["pais"]=scope["iso3"].map(names).fillna(scope["iso3"])
    scope=scope.sort_values("incidentes",ascending=False)
    metric_strip([(_metric_number(scope[k]),label,
                   "AWSD · año seleccionado") for k,label in AWS_METRICS])
    st.caption(
        f"AWSD · {year}: {len(scope)} países con registros en el ámbito. "
        "Los incidentes afectan a personal humanitario de distintos sectores; "
        "no son equivalentes a ataques contra servicios de salud. "
        "Los países sin registros en AWSD se muestran sin dato, no como cero. "
        + ("Año en curso, potencialmente incompleto. " if year==pd.Timestamp.utcnow().year else "")
    )
    a1,a2=st.columns(2,gap="medium")
    with a1:
        with card("Incidentes de seguridad por país",
                  f"AWSD · {year} · incidentes registrados.",
                  AWS_SOURCE,height=H):
            pa_map(_map_frame(D,selected,scope,"incidentes"),
                   "events","Incidentes registrados",height=366)
    with a2:
        with card("Países con más incidentes",
                  "Registros documentados durante el año seleccionado.",
                  AWS_SOURCE,height=H):
            plot(rank_bars(scope,label="pais",value="incidentes",limit=11,
                           units="Incidentes",formats=".0f"),height=366)
    a3,a4=st.columns(2,gap="medium")
    with a3:
        with card("Evolución anual de incidentes",
                  "Solo años con registros; no se imputan ceros.",
                  AWS_SOURCE,height=H):
            yearly=a.groupby("anio",as_index=False)["incidentes"].sum()
            yearly["fecha"]=pd.to_datetime(yearly["anio"].astype(int).astype(str)+"-01-01")
            plot(trend(yearly,x="fecha",y="incidentes",units="Incidentes"),
                 height=366)
    with a4:
        with table_card("Incidentes y afectaciones",
                        "Cifras agregadas por país; no incluye detalles individuales.",
                        AWS_SOURCE,height=H):
            table(scope,height=385,
                columns=["pais","incidentes","trabajadores_muertos",
                         "trabajadores_heridos","trabajadores_secuestrados"],
                labels={"pais":"País","incidentes":"Incidentes",
                        "trabajadores_muertos":"Fallecidos",
                        "trabajadores_heridos":"Heridos",
                        "trabajadores_secuestrados":"Secuestrados"})
    st.caption("Fuente: Aid Worker Security Database, Humanitarian Outcomes. "
               "Los valores son incidentes y personas afectadas reportadas "
               "en la base; no equivalen a un censo ni a vigilancia sanitaria.")

def gidd_tab(D, selected):
    """Estimaciones anuales revisadas: flujo y stock nunca mezclados."""
    a=_data(D,"idmc_gidd",selected)
    if a.empty:
        info_missing("estimaciones anuales IDMC GIDD para el ámbito seleccionado")
        return
    names=_names(D)
    years=sorted(a["anio"].dropna().astype(int).unique(),reverse=True)
    left,right=st.columns(2,gap="medium")
    with left:
        year=st.selectbox("Año de referencia GIDD",years,
                          key="op_gidd_year",width="stretch")
    with right:
        label=st.selectbox("Indicador",list(GIDD_METRICS),
                          key="op_gidd_metric",width="stretch")
    metric=GIDD_METRICS[label]
    n=a[a["anio"].eq(year)].dropna(subset=[metric]).copy()
    n["pais"]=n["iso3"].map(names).fillna(n["iso3"])
    metric_strip([
        (fmt(len(n)), "PAÍSES CON ESTIMACIÓN",f"GIDD · {year}"),
        (str(year), "AÑO DE REFERENCIA", "Estimaciones anuales revisadas"),
    ])
    st.caption(
        f"IDMC GIDD · conflicto y violencia · {year}. "
        "Nuevos desplazamientos contabiliza movimientos durante el año; "
        "personas desplazadas al cierre del año es una estimación de población "
        "que permanece desplazada. No se suman, ni se deduce un indicador del otro. "
        "La cobertura varía entre países y años."
    )
    l,r=st.columns(2,gap="medium")
    with l:
        with card("Distribución geográfica",
                  f"{label} · {year}",
                  IDMC_SOURCE,height=H):
            pa_map(_map_frame(D,selected,n,metric),"events",label,height=366)
    with r:
        with card("Comparación entre países",
                  f"{label} · estimaciones nacionales.",
                  IDMC_SOURCE,height=H):
            if n.empty:info_missing("estimaciones nacionales para ese año e indicador")
            else:plot(rank_bars(n,label="pais",value=metric,
                          limit=13,formats=".0f",units=label),height=366)
    countries=sorted(a["iso3"].unique(),key=lambda iso:names.get(iso,iso))
    if not countries:return
    selected_country="COL" if "COL" in countries else countries[0]
    country=st.selectbox("País para evolución histórica",countries,
          index=countries.index(selected_country),
          format_func=lambda iso:names.get(iso,iso),key="op_gidd_country",
          width="stretch")
    history=a[a["iso3"].eq(country)].dropna(subset=[metric]).copy()
    history["fecha"]=pd.to_datetime(history["anio"].astype(int).astype(str)+"-01-01")
    c1,c2=st.columns(2,gap="medium")
    with c1:
        with card("Evolución histórica del país",
                  f"{names.get(country,country)} · {label.lower()}",
                  IDMC_SOURCE,height=H):
            if history.empty:info_missing("serie de ese indicador")
            else:plot(trend(history,x="fecha",y=metric,units=label),height=366)
    with c2:
        with table_card("Cifras y años de referencia",
                        "No mezclar desplazamientos nuevos con población desplazada.",
                        IDMC_SOURCE,height=H):
            data=history.sort_values("anio",ascending=False)
            table(data,height=385,
                  columns=["anio","nuevos_desplazamientos",
                           "personas_desplazadas_fin_anio"],
                  labels={"anio":"Año","nuevos_desplazamientos":"Nuevos desplazamientos",
                          "personas_desplazadas_fin_anio":"Personas desplazadas al cierre"})
    st.caption("Fuente: Internal Displacement Monitoring Centre (IDMC), GIDD. "
       "Licencia CC BY-NC-SA 3.0 IGO; atribución IDMC obligatoria. "
       "Las estimaciones se someten a validación y pueden actualizarse retrospectivamente.")

def idu_tab(D, selected):
    """Actualizaciones IDMC IDU de conflicto, por ventana de inicio del evento."""
    meta=_status(D).get("idu",{})
    all_idu=D.get("idu",pd.DataFrame())
    if all_idu is None or all_idu.empty:
        file=ROOT/SOURCES["idu"]
        file_present=file.is_file()
        st.warning("No hay tabla IDMC IDU disponible en esta sesión. "
                   "La ausencia de datos aquí no equivale a ausencia de desplazamientos.")
        st.caption(
            "Diagnóstico de despliegue: CSV IDU "
            + ("presente" if file_present else "ausente")
            + f" · extracción: {meta.get('estado','sin metadatos')}."
            + (" Actualiza la página; si continúa, reinicia la app en "
               "Streamlit Cloud para sincronizar archivos y caché."
               if file_present else
               " Esta versión no incluye el CSV: verifica el repositorio y "
               "la rama configurados en Streamlit Cloud.")
        )
        return

    names=_names(D)
    n=_data(D,"idu",selected)
    if n.empty:
        available=sorted(all_idu["iso3"].dropna().unique(),
                         key=lambda iso:names.get(iso,iso))
        st.info("No hay eventos de conflicto/violencia IDMC IDU publicados para "
                "los países seleccionados. Esto no significa ausencia de desplazamientos.")
        st.caption("Países con registros en esta extracción: "
                   + ", ".join(names.get(iso,iso) for iso in available)
                   + ". Selecciona uno de ellos o amplía el ámbito.")
        return

    n=n.dropna(subset=["periodo","actualizaciones"]).copy()
    n["periodo"]=n["periodo"].astype(str)
    n["actualizaciones"]=pd.to_numeric(n["actualizaciones"],errors="coerce")
    n=n.dropna(subset=["actualizaciones"])
    if n.empty:
        info_missing("eventos IDU con periodos válidos")
        return

    latest=pd.Period(n["periodo"].max(),freq="M")
    months=st.select_slider(
        "Meses de inicio de eventos",options=[1,3,6,12],value=6,
        format_func=lambda v: f"{v} mes" if v==1 else f"{v} meses",
        key="op_idu_lookback",
        help="Ventana relativa al último mes de inicio registrado en el ámbito; "
             "no equivale a la fecha de publicación.")
    earliest=str(latest-(months-1))
    last=str(latest)
    scope=n[n["periodo"].between(earliest,last)].copy()
    if scope.empty:
        info_missing("eventos IDU para la ventana consultada")
        return
    by_country=scope.groupby("iso3",as_index=False).agg(
        actualizaciones=("actualizaciones","sum"),
        meses_reportados=("periodo","nunique"),
        ultimo_mes=("periodo","max"))
    by_country["pais"]=by_country["iso3"].map(names).fillna(by_country["iso3"])
    by_country=by_country.sort_values("actualizaciones",ascending=False)

    period=f"{earliest} a {last}"
    metric_strip([
        (fmt(by_country["actualizaciones"].sum()),"EVENTOS IDU",
         "Eventos identificados en la ventana"),
        (fmt(by_country["iso3"].nunique()),"PAÍSES CON REGISTROS",
         "Sin asumir cobertura completa"),
        (last,"ÚLTIMO MES REPORTADO","Inicio del evento"),
    ])
    st.caption(
        f"IDMC IDU · conflicto y violencia · meses de inicio {period}. "
        "Fuente: archivo de actualizaciones de los últimos 180 días, "
        "que también puede incluir eventos de inicio anterior. "
        "Se cuentan eventos únicos por país y mes, no personas desplazadas. "
        "Las ausencias no equivalen a cero; la serie no es exhaustiva ni "
        "directamente comparable con las estimaciones anuales GIDD."
    )
    l,r=st.columns(2,gap="medium")
    with l:
        with card("Eventos IDU por país",period,
                  "IDMC IDU · preliminar",height=H):
            pa_map(_map_frame(D,selected,by_country,"actualizaciones"),
                   "events","Eventos IDU",height=366)
    with r:
        with card("Países con eventos IDU",period,
                  "IDMC IDU · preliminar",height=H):
            plot(rank_bars(by_country,label="pais",value="actualizaciones",
                           limit=13,formats=".0f",units="Eventos IDU"),height=366)
    with st.expander("Ver periodos reportados por país"):
        table(by_country.sort_values("pais"),height=325,
              columns=["pais","actualizaciones","meses_reportados","ultimo_mes"],
              labels={"pais":"País","actualizaciones":"Eventos IDU",
                      "meses_reportados":"Meses con registros",
                      "ultimo_mes":"Último mes de inicio"})
    st.caption("Fuente: IDMC, Internal Displacement Updates (IDU). "
               "Registros preliminares sujetos a revisión; no sumar con GIDD "
               "ni con las cifras OIM DTM.")

def profile_awsd(D, selected):
    n=_data(D,"awsd",selected)
    if n.empty:return
    recent=n.sort_values("anio").tail(8).copy()
    latest=recent.iloc[-1]
    with card("Seguridad del personal humanitario",
              "Incidentes reportados por año; no equivalen a ataques a la salud.",
              AWS_SOURCE,height=H):
        st.metric(f"Incidentes · {int(latest['anio'])}",fmt(latest["incidentes"]))
        st.metric("Trabajadores fallecidos",fmt(latest["trabajadores_muertos"]))
        year=recent[["anio","incidentes"]].copy()
        year["fecha"]=pd.to_datetime(year["anio"].astype(int).astype(str)+"-01-01")
        plot(trend(year,x="fecha",y="incidentes",units="Incidentes"),height=230)

def profile_idmc(D, selected):
    n=_data(D,"idmc_gidd",selected)
    if n.empty:return
    recent=n.sort_values("anio").tail(10).copy()
    last=recent.iloc[-1]
    with card("Desplazamiento interno · IDMC",
              f"Estimaciones anuales por conflicto · {int(last['anio'])}.",
              IDMC_SOURCE,height=H):
        st.metric("Nuevos desplazamientos",fmt(last["nuevos_desplazamientos"]))
        st.metric("Personas desplazadas al cierre",fmt(last["personas_desplazadas_fin_anio"]))
        st.caption("Movimientos durante el año ≠ personas desplazadas al cierre. "
                   "Ambas estimaciones se interpretan por separado.")
