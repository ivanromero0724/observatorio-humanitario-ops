"""Vistas operativas del Observatorio Humanitario OPS/OMS.

Solo indicadores con datos integrados; eventos, personas, contexto y respuesta
se visualizan por separado. No se asignan niveles propios de OPS.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from observatorio_v2 import filtered, latest_ops, valid_needs, OPS_LABELS, HAPI_TYPES
from observatorio_v4 import plot, table, info_missing, crisis_table, reports, fmt
from panel_coe import card
from observatorio_v5 import (
    title, events_by_country, common_last, list_months,
    crisis_core, oim_scope,
)
from graficos import rank_bars, trend, strip_countries
from mapa_coe import pa_map
from detalle_riesgo import risk_page, acaps_detail

BLUE = "#009BDA"
ORANGE = "#F36B32"
H = 420
EVENT_TYPES = {
    "political_violence": "Violencia política",
    "civilian_targeting": "Violencia contra civiles",
    "demonstration": "Manifestaciones",
}
OPS_OPTIONS = [
    "GINI", "Escolaridad", "Mortalidad por homicidio",
    "Médicos", "Enfermería", "Camas hospitalarias", "DTP3", "SRP1",
]


def _scope(D, selected):
    return filtered(D["countries"], selected)[["iso3", "pais"]].copy()


def _countries(D):
    return D["countries"].set_index("iso3")["pais"].to_dict()


def _section_note(text):
    st.caption(text)


def _source(text):
    st.caption("Fuente y alcance: " + text)


def _event_tab(D, selected):
    """Serie mensual comparable y fallecimientos reportados, sin superponer categorías."""
    e = filtered(D["conflict"], selected)
    if e.empty:
        info_missing("eventos de violencia")
        return
    available = [v for v in EVENT_TYPES if v in set(e["tipo_evento"].dropna())]
    if not available:
        info_missing("categorías de eventos")
        return

    col1, col2 = st.columns([1.2, 1], gap="medium")
    with col1:
        kind = st.selectbox("Tipo de evento", available, key="op_event_kind",
                            format_func=lambda v: EVENT_TYPES[v])
    with col2:
        months = st.selectbox(
            "Periodo", [1, 6, 12, 24], index=2, key="op_event_months",
            format_func=lambda v: ("Último mes disponible" if v == 1
                                   else f"Últimos {v} meses"),
        )

    total_by_country, cut = events_by_country(D, selected, kind, months)
    totals = _scope(D, selected).merge(total_by_country, on="iso3", how="left")
    eligible = totals.dropna(subset=["eventos"]).copy()

    # La fuente informa fallecimientos para violencia política y contra civiles.
    # "demonstration" tiene el campo vacío: nunca imputar muertes=0.
    deaths = pd.DataFrame(columns=["iso3", "muertes_reportadas"])
    if cut is not None and not eligible.empty:
        expected = list_months(cut, months)
        window = e[(e["tipo_evento"] == kind) &
                   e["iso3"].isin(eligible["iso3"]) &
                   e["fecha"].isin(expected)].copy()
        window["muertes_reportadas"] = pd.to_numeric(
            window["muertes_reportadas"], errors="coerce")
        by_month = window.groupby(["iso3", "fecha"], as_index=False).agg(
            muertes_reportadas=("muertes_reportadas", lambda x: x.sum(min_count=1)),
        )
        counts = by_month.groupby("iso3").agg(
            meses=("fecha", "nunique"),
            completos=("muertes_reportadas", "count"),
            muertes_reportadas=("muertes_reportadas", lambda x: x.sum(min_count=1)),
        )
        counts.loc[counts["completos"] != months, "muertes_reportadas"] = float("nan")
        counts.loc[counts["meses"] != months, "muertes_reportadas"] = float("nan")
        deaths = counts[["muertes_reportadas"]].reset_index()
    eligible = eligible.merge(deaths, on="iso3", how="left")
    has_deaths = eligible["muertes_reportadas"].notna().any()

    kpis = st.columns(4 if has_deaths else 3, gap="small")
    kpis[0].metric("Países con serie completa", f"{len(eligible)}/{len(selected)}")
    kpis[1].metric("Eventos registrados", fmt(eligible["eventos"].sum())
                    if not eligible.empty else "—")
    offset = 2
    if has_deaths:
        kpis[2].metric("Muertes reportadas", fmt(eligible["muertes_reportadas"].sum()))
        offset = 3
    kpis[offset].metric("Último mes con registros",
                        cut.strftime("%Y-%m") if cut is not None else "—")

    period_text = ("último mes disponible" if months == 1 else f"últimos {months} meses")
    st.caption("Comparación por país en el mismo periodo. Las categorías ACLED pueden "
               "solaparse y no deben sumarse entre sí. "
               + ("El último mes disponible puede estar incompleto." if months == 1 else ""))

    left, right = st.columns(2, gap="medium")
    with left:
        with card(
            "Distribución geográfica de eventos",
            f"{EVENT_TYPES[kind]} · {period_text}",
            "OCHA HAPI / ACLED · registros agregados por país y mes", height=H,
        ):
            geo = totals[["iso3", "pais", "eventos"]].rename(
                columns={"eventos": "valor"})
            pa_map(geo, "events", "Eventos registrados", height=366)
    with right:
        with card(
            "Países con más eventos",
            f"Ranking · {EVENT_TYPES[kind].lower()}",
            "OCHA HAPI / ACLED", height=H,
        ):
            if eligible.empty:
                info_missing("series nacionales completas")
            else:
                plot(rank_bars(eligible, label="pais", value="eventos",
                               limit=11, formats=".0f", units="Eventos"), height=366)

    st.markdown("#### Evolución y consecuencias registradas")
    left, right = st.columns(2, gap="medium") if has_deaths else (None, None)
    if has_deaths:
        with left:
            with card("Evolución de los eventos",
                      "Registro mensual de la categoría y países comparables.",
                      "OCHA HAPI / ACLED", height=H):
                series = window.groupby("fecha", as_index=False)["eventos"].sum()
                plot(trend(series, x="fecha", y="eventos",
                           units="Eventos por mes"), height=366)
        with right:
            with card("Muertes reportadas por país",
                      "Fallecimientos asociados a eventos de la categoría seleccionada.",
                      "OCHA HAPI / ACLED · estimaciones de fallecimientos", height=H):
                fatalities = eligible.dropna(subset=["muertes_reportadas"])
                plot(rank_bars(fatalities, label="pais", value="muertes_reportadas",
                               limit=11, formats=".0f", color=ORANGE,
                               units="Muertes reportadas"), height=366)
        st.caption("Las muertes reportadas por ACLED son estimaciones asociadas a eventos, "
                   "no equivalen al registro oficial de defunciones ni al total de personas afectadas.")
    else:
        with card("Evolución de los eventos",
                  "Registro mensual para la categoría y los países con serie completa.",
                  "OCHA HAPI / ACLED", height=H):
            if eligible.empty or cut is None:
                info_missing("evolución de eventos")
            else:
                months_list = list_months(cut, months)
                period = e[(e["tipo_evento"] == kind) &
                           (e["iso3"].isin(eligible["iso3"])) &
                           (e["fecha"].isin(months_list))]
                series = period.groupby("fecha", as_index=False)["eventos"].sum()
                plot(trend(series, x="fecha", y="eventos",
                           units="Eventos por mes"), height=366)


def _crisis_tab(D, selected):
    crises = crisis_core(D, selected)
    if crises.empty:
        info_missing("crisis evaluadas por ACAPS para este ámbito")
        return
    a, b = st.columns(2)
    a.metric("Contextos evaluados", crises["crisis_id"].nunique())
    b.metric("Países con evaluación", crises["iso3"].nunique())
    st.caption("ACAPS evalúa crisis concretas. Su severidad y su acceso no equivalen al "
               "riesgo estructural INFORM ni a una prioridad institucional OPS.")
    left, right = st.columns(2, gap="medium")
    with left:
        with card("Severidad de crisis en las Américas",
                  "Mayor puntuación entre las crisis evaluadas de cada país.",
                  "ACAPS INFORM Severity · escala 0–10", height=420):
            m = crises.sort_values("puntuacion").drop_duplicates("iso3", keep="last")
            m = m[["iso3", "pais", "puntuacion"]].rename(
                columns={"puntuacion": "valor"})
            pa_map(m, "severity", "Severidad ACAPS", height=366)
    with right:
        with card("Contextos de mayor severidad",
                  "Una barra representa una crisis, no la prioridad de un país.",
                  "ACAPS INFORM Severity", height=420):
            c = crises.dropna(subset=["puntuacion"]).copy()
            c["contexto"] = c["pais"] + " · " + c["crisis"].str.slice(0, 36)
            plot(rank_bars(c, label="contexto", value="puntuacion",
                           limit=10, units="Severidad / 10",
                           formats=".1f", max_x=10), height=366)
    st.markdown("#### Detalle de acceso por crisis")
    acaps_detail(D, selected)


def _subgroup(label, values, key):
    """Única navegación secundaria por página: breve, horizontal y persistente."""
    selected = st.segmented_control(
        label, values, default=values[0],
        selection_mode="single", key=key, width="content",
        label_visibility="collapsed",
    )
    return selected or values[0]


def amenazas_page(D, selected, names):
    title("01 / AMENAZAS Y EVENTOS", "Amenazas y eventos humanitarios",
          "Eventos de violencia y contexto de crisis: información verificable por país.")
    topic = _subgroup("Subtema", ["Eventos de violencia", "Crisis evaluadas y acceso"],
                      "op_amenazas_grupo")
    if topic == "Eventos de violencia":
        _event_tab(D, selected)
    else:
        _crisis_tab(D, selected)


def _acnur_tab(D, selected):
    un = filtered(D["acnur"], selected, "asilo_iso3")
    if un.empty:
        info_missing("población de interés de ACNUR")
        return
    choices = {"REF": "Personas refugiadas", "ASY": "Solicitantes de asilo"}
    available = [k for k in choices if k in set(un["grupo_poblacion"].dropna())]
    if not available:
        info_missing("categorías de refugio y asilo")
        return
    l, r = st.columns(2)
    with l:
        code = st.selectbox("Grupo de población", available,
                            format_func=lambda c: choices[c], key="op_un_group")
    un = un[un["grupo_poblacion"] == code].copy()
    years = sorted(pd.to_numeric(un["anio"], errors="coerce").dropna().astype(int).unique(),
                   reverse=True)
    if not years:
        info_missing("años de referencia de ACNUR")
        return
    with r:
        year = st.selectbox("Año común entre países", years, key="op_un_year")
    un = un[pd.to_numeric(un["anio"], errors="coerce") == year].copy()
    un["personas"] = pd.to_numeric(un["personas"], errors="coerce")
    summary = un.groupby("asilo_iso3", as_index=False)["personas"].sum(min_count=1)
    summary = _scope(D, selected).merge(summary, left_on="iso3", right_on="asilo_iso3", how="left")
    present = summary.dropna(subset=["personas"])
    a, b = st.columns(2)
    a.metric("Países de acogida con datos", f"{len(present)}/{len(selected)}")
    b.metric("Año seleccionado", str(year))
    _section_note("Son poblaciones registradas en el año, no movimientos ocurridos durante ese año. "
                  "No se suman grupos poblacionales diferentes.")
    left, right = st.columns([1.05, .95], gap="medium")
    with left:
        with card("¿En qué países se encuentran?",
                  "Población por país de acogida y categoría seleccionada.",
                  f"ACNUR vía HAPI · {year}", height=H):
            pa_map(summary[["iso3", "pais", "personas"]].rename(
                columns={"personas": "valor"}), "events",
                f"{choices[code]} · {year}", height=360, unit="personas")
            st.caption("Los países sin registros para el grupo y año se muestran en gris.")
    with right:
        with card("Países de acogida con mayor población registrada",
                  "Comparación dentro del mismo año y la misma categoría.",
                  f"ACNUR vía HAPI · {year}", height=H):
            if present.empty:
                info_missing("población para este año y grupo")
            else:
                plot(rank_bars(present, label="pais", value="personas",
                               limit=11, formats=".0f", units="Personas"), height=355)

def _dtm_tab(D, selected):
    d = oim_scope(filtered(D["dtm"], selected))
    if d.empty:
        info_missing("operaciones OIM DTM incluidas en el alcance de conflicto/inseguridad")
        return
    names = _countries(D)
    countries = sorted(d["iso3"].dropna().unique(), key=lambda x: names.get(x, x))
    l, r = st.columns([.8, 1.2])
    with l:
        code = st.selectbox("País con operaciones", countries,
                            format_func=lambda x: names.get(x, x), key="op_dtm_country")
    d = d[d["iso3"] == code].copy()
    ops = sorted(d["operacion"].dropna().unique())
    if not ops:
        info_missing("operaciones registradas")
        return
    with r:
        op = st.selectbox("Operación OIM DTM", ops, key="op_dtm_operation")
    d = d[d["operacion"] == op].copy()
    dates = pd.to_datetime(d["fecha_reporte"], errors="coerce")
    latest = dates.max()
    if pd.notna(latest):
        d = d[dates.eq(latest)]
    round_col = pd.to_numeric(d["ronda"], errors="coerce")
    if round_col.notna().any():
        d = d[round_col == round_col.max()]
    a, b = st.columns(2)
    a.metric("Fecha de referencia", str(d["fecha_reporte"].iloc[0])[:10])
    b.metric("Ronda", str(d["ronda"].iloc[0]))
    _section_note(
        "Estas cifras corresponden a una operación y ronda específica; no representan "
        "necesariamente el stock nacional actual. Se excluyen operaciones etiquetadas "
        "como desastre natural; una causa no indicada no se asume conflicto."
    )
    with card("Población desplazada registrada en la operación",
              "Desagregación territorial y por sexo cuando el proveedor informa esos datos.",
              "OIM DTM Baseline"):
        table(d, height=380,
              columns=["origen_admin1", "personas_idp_reportadas", "hombres", "mujeres",
                       "causa_desplazamiento"],
              labels={"origen_admin1": "Área de origen",
                      "personas_idp_reportadas": "Personas reportadas",
                      "hombres": "Hombres", "mujeres": "Mujeres",
                      "causa_desplazamiento": "Causa reportada"})


def _pin_tab(D, selected):
    n = valid_needs(filtered(D["needs"], selected))
    if n.empty:
        info_missing("totales intersectoriales de personas en necesidad")
        return
    n = n.copy()
    n["anio"] = pd.to_numeric(n["reference_period_start"].astype(str).str[:4],
                              errors="coerce")
    # Evitar dobles conteos: seleccionar solo país-año con una fila inequívoca.
    n = n[~n.duplicated(["iso3", "anio"], keep=False)]
    n = n.sort_values("anio").drop_duplicates("iso3", keep="last")
    n = n.dropna(subset=["population", "anio"])
    if n.empty:
        info_missing("totales nacionales no duplicados de PiN")
        return
    n["pais"] = n["iso3"].map(_countries(D))
    n["anio"] = n["anio"].astype(int)
    a, b = st.columns(2)
    a.metric("Países con estimación intersectorial única", n["iso3"].nunique())
    b.metric("Años de referencia", f"{n['anio'].min()}–{n['anio'].max()}")
    _section_note("PiN = personas en necesidad de asistencia humanitaria. Los años difieren "
                  "entre países; no se suman sectores ni se presenta un total regional.")
    left, right = st.columns(2, gap="medium")
    with left:
        with card("Estimaciones nacionales de PiN",
                  "Último año inequívoco disponible para cada país, visible en el gráfico.",
                  "OCHA Humanitarian Needs vía HAPI", height=H):
            plot(strip_countries(n, name="pais", val="population", year="anio",
                                 units="Personas en necesidad", decimals=0), height=365)
    with right:
        with card("Valores y años de referencia",
                  "Cada fila corresponde a una estimación intersectorial distinta.",
                  "OCHA Humanitarian Needs vía HAPI", height=H):
            table(n.sort_values("population", ascending=False),
                  height=390, columns=["pais", "anio", "population"],
                  labels={"pais": "País", "anio": "Año",
                          "population": "Personas en necesidad"})


def movilidad_page(D, selected, names):
    title("02 / MOVILIDAD Y NECESIDADES", "Movilidad y necesidades humanitarias",
          "Refugio y asilo, desplazamiento por operación y estimaciones de necesidades.")
    topic = _subgroup("Subtema",
                      ["Refugio y asilo", "Desplazamiento interno", "Personas en necesidad"],
                      "op_movilidad_grupo")
    if topic == "Refugio y asilo":
        _acnur_tab(D, selected)
    elif topic == "Desplazamiento interno":
        _dtm_tab(D, selected)
    else:
        _pin_tab(D, selected)


def _ops_tab(D, selected):
    df = filtered(D["ops"], selected)
    if df.empty:
        info_missing("indicadores OPS")
        return
    opts = [x for x in OPS_OPTIONS if x in set(df["indicador"].dropna())]
    if not opts:
        info_missing("indicadores comparables de salud y contexto")
        return
    l, r = st.columns([1.15, .85])
    with l:
        choice = st.selectbox("Indicador", opts, key="op_ops_ind",
                              format_func=lambda x: OPS_LABELS.get(x, x))
    with r:
        common = st.checkbox("Mismo año en todos los países", key="op_ops_common")
    years = sorted(df[df["indicador"] == choice]["periodo"].dropna().astype(int).unique(),
                   reverse=True)
    year = st.selectbox("Año", years, key="op_ops_year") if common and years else None
    picked = latest_ops(df, choice, year).copy()
    if picked.empty:
        info_missing("observaciones para la selección")
        return
    picked["anio"] = picked["periodo"].astype(int)
    a, b = st.columns(2)
    a.metric("Países con datos", f"{picked['iso3'].nunique()}/{len(selected)}")
    b.metric("Periodo", str(year) if year is not None else "Último por país")
    _section_note(
        "Estos indicadores describen contexto y capacidad sanitaria nacional, no respuesta "
        "operativa durante una crisis. Sin año común, cada país puede tener un corte diferente."
    )
    with card("Comparación entre países",
              "Valor publicado y año de referencia disponibles al pasar el cursor.",
              "OPS · Indicadores Básicos"):
        plot(strip_countries(picked, name="pais", val="valor", year="anio",
                             units=OPS_LABELS.get(choice, choice), max_items=25), height=425)

def _mpi_tab(D, selected):
    mpi = filtered(D["mpi"], selected)
    if mpi.empty:
        info_missing("pobreza multidimensional")
        return
    mpi = mpi.copy()
    mpi["anio"] = pd.to_numeric(mpi["reference_period_start"].astype(str).str[:4],
                                errors="coerce")
    mpi = mpi.sort_values("anio").drop_duplicates("iso3", keep="last")
    mpi = mpi.dropna(subset=["headcount_ratio", "anio"])
    if mpi.empty:
        info_missing("incidencia de pobreza multidimensional")
        return
    mpi["anio"] = mpi["anio"].astype(int)
    st.metric("Países con estimaciones", mpi["iso3"].nunique())
    _section_note("Incidencia de pobreza multidimensional (porcentaje de población). "
                  "La publicación y el año de referencia varían entre países.")
    with card("Incidencia de pobreza multidimensional",
              "Comparación del último dato disponible por país.",
              "OPHI MPI vía OCHA HAPI"):
        plot(strip_countries(mpi, name="pais", val="headcount_ratio",
                             year="anio", units="Población (%)"), height=430)


def _ipc_tab(D, selected):
    df = filtered(D["ipc"], selected)
    if df.empty:
        info_missing("evaluaciones de seguridad alimentaria IPC")
        return
    names = _countries(D)
    available = sorted(df["iso3"].dropna().unique(), key=lambda x: names.get(x, x))
    country = st.selectbox("País con evaluación", available,
                           format_func=lambda x: names.get(x, x), key="op_ipc_country")
    q = df[df["iso3"] == country].copy()
    types = sorted(q["ipc_type"].dropna().unique())
    if types:
        typ = st.selectbox("Tipo de evaluación", types,
                           format_func=lambda x: {"current": "Actual",
                                                   "projection": "Proyección"}.get(x, x),
                           key="op_ipc_type")
        q = q[q["ipc_type"] == typ]
    cuts = sorted(q["reference_period_end"].dropna().unique(), reverse=True)
    if cuts:
        cut = st.selectbox("Fin del periodo", cuts, key="op_ipc_cut")
        q = q[q["reference_period_end"] == cut]
    q["population_in_phase"] = pd.to_numeric(q["population_in_phase"], errors="coerce")
    _section_note("IPC estima condiciones de seguridad alimentaria por fase. "
                  "No sumar las filas '3+' o 'all' con las fases individuales.")
    with card("Población estimada por fase IPC",
              "Fases del periodo elegido (se muestran por separado).",
              "IPC vía OCHA HAPI"):
        chart = q[q["ipc_phase"].astype(str).isin(["1", "2", "3", "4", "5"])].copy()
        if chart.empty:
            info_missing("fases individuales IPC para este periodo")
        else:
            plot(rank_bars(chart, label="ipc_phase", value="population_in_phase",
                           units="Personas", formats=".0f", limit=5), height=330)
            st.caption("Fase 1 = mínima; fase 5 = catástrofe/hambruna según metodología IPC.")

def _response_tab(D, selected):
    st.markdown("#### Presencia de organizaciones humanitarias")
    p = filtered(D["presence"], selected)
    f = filtered(D["funding"], selected)
    left, right = st.columns(2, gap="medium")
    with left:
        with card("Organizaciones reportadas por sector",
                  "Número de organizaciones distintas dentro de cada sector y periodo.",
                  "OCHA 3W vía HAPI", height=520):
            if p.empty:
                info_missing("presencia operativa en el ámbito")
            else:
                names = _countries(D)
                host = st.selectbox("País", sorted(p["iso3"].unique(),
                       key=lambda x: names.get(x, x)),
                       format_func=lambda x: names.get(x, x), key="op_3w_host")
                d = p[p["iso3"] == host].copy()
                date = st.selectbox("Corte 3W", sorted(d["fecha_hasta"].dropna().unique(),
                                    reverse=True), key="op_3w_date")
                d = d[d["fecha_hasta"] == date]
                plot(rank_bars(d, label="sector", value="organizaciones_distintas",
                               units="Organizaciones", formats=".0f", limit=12), height=340)
                st.caption("No sumar sectores: una misma organización puede trabajar en varios.")
    with right:
        with card("Financiación de planes humanitarios",
                  "Requerimientos y fondos reportados para apelaciones identificadas.",
                  "OCHA FTS vía HAPI · USD", height=520):
            if f.empty:
                info_missing("financiación humanitaria en el ámbito")
            else:
                names = _countries(D)
                host = st.selectbox("País", sorted(f["iso3"].unique(),
                       key=lambda x: names.get(x, x)),
                       format_func=lambda x: names.get(x, x), key="op_fts_host")
                d = f[f["iso3"] == host].copy()
                d = d[d["appeal_code"].fillna("").astype(str).str.lower() != "not specified"]
                d["anio"] = pd.to_numeric(d["reference_period_start"].astype(str).str[:4],
                                           errors="coerce")
                d = d[d["anio"] <= pd.Timestamp.today().year]
                if d.empty:
                    info_missing("planes identificados del país")
                else:
                    years = sorted(d["anio"].dropna().unique(), reverse=True)
                    if years:
                        year = st.selectbox("Año de apelación", years, key="op_fts_year")
                        d = d[d["anio"] == year]
                    table(d, height=355, columns=["appeal_name", "requirements_usd",
                                                 "funding_usd", "funding_pct"],
                          labels={"appeal_name": "Plan humanitario",
                                  "requirements_usd": "Requerido (USD)",
                                  "funding_usd": "Financiado (USD)",
                                  "funding_pct": "Financiado (%)"})
                    st.caption("No equivale a toda la ayuda recibida en el país.")


def vulnerabilidad_page(D, selected, names):
    title("03 / VULNERABILIDAD Y RESPUESTA", "Vulnerabilidad y respuesta",
          "Riesgo estructural, condiciones sociales y sanitarias, seguridad alimentaria y respuesta.")
    topic = _subgroup("Subtema",
                      ["Riesgo INFORM", "Salud y sociedad", "Pobreza",
                       "Seguridad alimentaria", "Respuesta"],
                      "op_vulnerabilidad_grupo")
    if topic == "Riesgo INFORM":
        risk_page(D, selected)
    elif topic == "Salud y sociedad":
        _ops_tab(D, selected)
    elif topic == "Pobreza":
        _mpi_tab(D, selected)
    elif topic == "Seguridad alimentaria":
        _ipc_tab(D, selected)
    else:
        _response_tab(D, selected)


def perfil_page(D, selected, names):
    title("04 / PERFILES POR PAÍS", "Ficha humanitaria por país",
          "Reúne indicadores de distintas fuentes sin combinarlos en un puntaje de riesgo.")
    choices = sorted(selected, key=lambda c: names.get(c, c))
    iso = st.selectbox("País", choices,
           index=choices.index("COL") if "COL" in choices else 0,
           format_func=lambda x: names.get(x, x), key="op_profile_country")
    chosen = {iso}
    e, last = events_by_country(D, chosen, "political_violence", 12)
    v = e["eventos"].iloc[0] if not e.empty else float("nan")
    c = crisis_core(D, chosen)
    un = filtered(D["acnur"], chosen, "asilo_iso3")
    n = valid_needs(filtered(D["needs"], chosen))
    m1, m2, m3 = st.columns(3)
    m1.metric("Violencia política · 12 meses", fmt(v) if pd.notna(v) else "Sin serie")
    m2.metric("Crisis ACAPS evaluadas", c["crisis_id"].nunique() if not c.empty else "Sin evaluación")
    m3.metric("ACNUR · datos de acogida", "Disponible" if not un.empty else "Sin registros")
    _section_note("Los indicadores no describen la misma unidad ni año; no deben sumarse. "
                  f"Corte de eventos: {last.strftime('%Y-%m') if last is not None else 'no disponible'}.")
    view = _subgroup("Detalle de la ficha",
                     ["Indicadores", "Informes recientes"],
                     "op_perfil_grupo")
    if view == "Indicadores":
        left, right = st.columns(2, gap="medium")
        with left:
            with card("Violencia política reciente",
                      "Serie mensual de eventos reportados para el país.",
                      "OCHA HAPI / ACLED", height=420):
                source = filtered(D["conflict"], chosen)
                if source.empty or last is None:
                    info_missing("eventos en el país")
                else:
                    source = source[(source["tipo_evento"] == "political_violence") &
                                    source["fecha"].isin(list_months(last, 12))]
                    if source.empty:
                        info_missing("eventos mensuales")
                    else:
                        plot(trend(source.groupby("fecha", as_index=False)["eventos"].sum(),
                                   x="fecha", y="eventos", units="Eventos por mes"), height=345)
        with right:
            with card("Crisis evaluadas y restricciones de acceso",
                      "Puntuaciones por crisis según metodología de ACAPS.",
                      "ACAPS Severity + Access", height=420):
                if c.empty:
                    info_missing("evaluaciones ACAPS")
                else:
                    table(c, height=350, columns=["crisis", "puntuacion", "acceso", "corte_api"],
                          labels={"crisis": "Contexto evaluado",
                                  "puntuacion": "Severidad / 10",
                                  "acceso": "Acceso / 5", "corte_api": "Corte"})
        left, right = st.columns(2, gap="medium")
        with left:
            with card("Personas refugiadas y solicitantes de asilo",
                      "Poblaciones de acogida según ACNUR, por año y grupo.",
                      "ACNUR vía HAPI", height=410):
                if un.empty:
                    info_missing("registros ACNUR")
                else:
                    un = un.copy()
                    un["anio_num"] = pd.to_numeric(un["anio"], errors="coerce")
                    year = un["anio_num"].max()
                    un = un[un["anio_num"] == year]
                    g = un[un["grupo_poblacion"].isin(["REF", "ASY"])].copy()
                    if g.empty:
                        info_missing("refugiados y solicitantes de asilo")
                    else:
                        g = g.groupby("grupo_poblacion", as_index=False)["personas"].sum(min_count=1)
                        g["grupo_poblacion"] = g["grupo_poblacion"].map({
                            "REF": "Personas refugiadas", "ASY": "Solicitantes de asilo"})
                        table(g, height=260, columns=["grupo_poblacion", "personas"],
                              labels={"grupo_poblacion": "Población", "personas": "Personas"})
                        st.caption(f"Año {int(year)}. Categorías diferenciadas; no se suman.")
        with right:
            with card("Capacidad sanitaria de referencia",
                      "Último indicador publicado; no representa recursos disponibles en la crisis.",
                      "OPS Indicadores Básicos", height=410):
                data = filtered(D["ops"], chosen)
                rows = []
                for key in ["Médicos", "Enfermería", "Camas hospitalarias", "DTP3", "SRP1"]:
                    latest = latest_ops(data, key)
                    if not latest.empty:
                        r = latest.iloc[0]
                        rows.append({"Indicador": OPS_LABELS.get(key, key),
                                     "Valor": fmt(r["valor"], 1), "Año": int(r["periodo"])})
                if rows:
                    table(pd.DataFrame(rows), height=320)
                else:
                    info_missing("capacidad sanitaria")
        if not n.empty:
            n = n.copy()
            n["anio"] = n["reference_period_start"].astype(str).str[:4]
            n = n[~n.duplicated(["iso3", "anio"], keep=False)]
            if not n.empty:
                n = n.sort_values("anio").tail(1)
                with st.container():
                    st.metric(f"Total intersectorial documentado · {n['anio'].iloc[0]}",
                              fmt(n["population"].iloc[0]))
                    st.caption("PiN no es un conteo de víctimas de hechos violentos.")
    else:
        d = reports(D, chosen, limit=12)
        if d.empty:
            info_missing("informes")
        else:
            d["Fecha"] = d["fecha_publicacion_rw"].astype(str).str[:10]
            with card("Informes humanitarios recientes",
                      "Documentos y metadatos disponibles para el país seleccionado.",
                      "OCHA ReliefWeb"):
                table(d, height=450, columns=["Fecha", "titulo", "fuentes", "url"],
                      labels={"titulo": "Informe", "fuentes": "Organización",
                              "url": "Documento"}, link="Documento")
