"""Vistas operativas del Observatorio Humanitario OPS/OMS.

Solo indicadores con datos integrados; eventos, personas, contexto y respuesta
se visualizan por separado. No se asignan niveles propios de OPS.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from observatorio_v2 import filtered, latest_ops, valid_needs, OPS_LABELS, HAPI_TYPES
from observatorio_v4 import plot, table, info_missing, crisis_table, reports, fmt
from panel_coe import card, table_card
from observatorio_v5 import (
    title, events_by_country, common_last, list_months,
    crisis_core, oim_scope,
)
from graficos import rank_bars, trend, strip_countries
from mapa_coe import pa_map
from detalle_riesgo import risk_page, acaps_detail
from tarjetas_resumen import metric_strip
from perfil_integral import profile_page
from pin_utils import intersectoral_pin, sectoral_pin
from vista_awsd_idmc import awsd_tab, gidd_tab, idu_tab
from vista_conflict_index import acled_conflict_tab

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

    # La cuadrícula de controles coincide con las dos columnas de gráficos.
    controls_left, controls_right = st.columns(2, gap="medium")
    with controls_left:
        kind = st.selectbox(
            "Tipo de evento", available, key="op_event_kind",
            format_func=lambda v: EVENT_TYPES[v],
            width="stretch",
        )
    with controls_right:
        months = st.select_slider(
            "Últimos meses analizados",
            options=[1, 3, 6, 9, 12],
            value=12,
            format_func=lambda v: f"{v} mes" if v == 1 else f"{v} meses",
            key="op_event_months",
            help="Selecciona cuántos meses de eventos de violencia quieres consultar (1, 3, 6, 9 o 12).",
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

    kpis=[
        (f"{len(eligible)}/{len(selected)}", "PAÍSES COMPARABLES", "Serie mensual completa"),
        (fmt(eligible["eventos"].sum()) if not eligible.empty else "—",
         "EVENTOS REPORTADOS", EVENT_TYPES[kind]),
    ]
    if has_deaths:
        kpis.append((fmt(eligible["muertes_reportadas"].sum()),
                     "MUERTES REPORTADAS", "Estimaciones ACLED"))
    kpis.append((cut.strftime("%Y-%m") if cut is not None else "—",
                 "MES DE REFERENCIA", "Último mes disponible"))
    metric_strip(kpis)

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
    metric_strip([
        (crises["crisis_id"].nunique(),"CRISIS EVALUADAS","Contextos ACAPS"),
        (crises["iso3"].nunique(),"PAÍSES EVALUADOS","Con crisis documentadas"),
    ])
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
          "Violencia, crisis, seguridad humanitaria y movilidad forzada: "
          "información verificable por país.")
    topic = _subgroup("Subtema", ["Eventos de violencia",
                                  "Índice de conflicto (ACLED)",
                                  "Crisis evaluadas y acceso",
                                  "Seguridad del personal humanitario",
                                  "Movilidad y desplazamiento"],
                      "op_amenazas_grupo")
    if topic == "Eventos de violencia":
        _event_tab(D, selected)
    elif topic == "Índice de conflicto (ACLED)":
        acled_conflict_tab(D, selected)
    elif topic == "Crisis evaluadas y acceso":
        _crisis_tab(D, selected)
    elif topic == "Seguridad del personal humanitario":
        awsd_tab(D, selected)
    else:
        _movilidad_tab(D, selected)


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
    metric_strip([
        (f"{len(present)}/{len(selected)}","PAÍSES CON REGISTROS","Acogida ACNUR"),
        (str(year),"AÑO DE REFERENCIA",choices[code]),
    ])
    _section_note("Son poblaciones registradas en el año, no movimientos ocurridos durante ese año. "
                  "No se suman grupos poblacionales diferentes.")
    left, right = st.columns(2, gap="medium")
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
    metric_strip([
        (str(d["fecha_reporte"].iloc[0])[:10],"FECHA DE REFERENCIA","OIM DTM"),
        (str(d["ronda"].iloc[0]),"RONDA PUBLICADA","Operación seleccionada"),
    ])
    _section_note(
        "Estas cifras corresponden a una operación y ronda específica; no representan "
        "necesariamente el stock nacional actual. Se excluyen operaciones etiquetadas "
        "como desastre natural; una causa no indicada no se asume conflicto."
    )
    with table_card("Población desplazada registrada en la operación",
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
    """PiN intersectorial entre países y desglose sectorial por país y año.

    Las estimaciones de sectores no son categorías mutuamente excluyentes,
    ni pueden agregarse para calcular un PiN regional o nacional.
    """
    needs = filtered(D["needs"], selected)
    general = intersectoral_pin(needs)
    sectors = sectoral_pin(needs)
    if general.empty and sectors.empty:
        info_missing("estimaciones HAPI de personas en necesidad (PiN)")
        return

    names = _countries(D)
    st.markdown("#### PiN intersectorial (general)")
    if general.empty:
        info_missing("estimaciones intersectoriales nacionales")
    else:
        n = (general.sort_values("anio")
             .drop_duplicates("iso3", keep="last").copy())
        n["pais"] = n["iso3"].map(names).fillna(n["iso3"])
        n["anio"] = n["anio"].astype(int)
        metric_strip([
            (n["iso3"].nunique(), "PAÍSES CON PiN", "Estimación intersectorial"),
            (f"{n['anio'].min()}–{n['anio'].max()}",
             "AÑOS DE REFERENCIA", "Último corte disponible por país"),
        ])
        _section_note(
            "PiN intersectorial = estimación general de personas que necesitan "
            "asistencia humanitaria. Los años pueden variar entre países; "
            "no se presenta un total regional."
        )
        left, right = st.columns(2, gap="medium")
        with left:
            with card("Estimaciones nacionales de PiN",
                      "Última estimación publicada para cada país y su año.",
                      "OCHA Humanitarian Needs vía HAPI", height=H):
                plot(strip_countries(
                    n, name="pais", val="population", year="anio",
                    units="Personas en necesidad", decimals=0,
                ), height=365)
        with right:
            with table_card("Valores y años de referencia",
                            "Cada país tiene una estimación intersectorial.",
                            "OCHA Humanitarian Needs vía HAPI", height=H):
                table(n.sort_values("population", ascending=False),
                      height=390, columns=["pais", "anio", "population"],
                      labels={"pais": "País", "anio": "Año",
                              "population": "Personas en necesidad"})

    st.markdown("#### PiN por sector")
    _section_note(
        "Consulta las necesidades por sector para un solo país y año. "
        "Una persona puede necesitar atención en varios sectores; las cifras "
        "no se suman ni representan partes excluyentes del PiN general. "
        "Los subsectores de protección pueden solaparse con Protección."
    )
    if sectors.empty:
        info_missing("desglose de necesidades por sector en el ámbito seleccionado")
        return
    available = sorted(sectors["iso3"].dropna().unique(),
                       key=lambda iso: names.get(iso, iso))
    left_filter, right_filter = st.columns(2, gap="medium")
    with left_filter:
        country = st.selectbox(
            "País", available, index=available.index("COL") if "COL" in available else 0,
            format_func=lambda iso: names.get(iso, iso), key="op_pin_sector_country",
            width="stretch",
        )
    chosen = sectors[sectors["iso3"].eq(country)].copy()
    years = sorted(chosen["anio"].dropna().astype(int).unique(), reverse=True)
    with right_filter:
        year = st.selectbox(
            "Año de referencia sectorial", years,
            key="op_pin_sector_year", width="stretch",
        )
    chosen = chosen[chosen["anio"].eq(year)].copy()
    chosen = chosen.sort_values("population", ascending=False)
    matched = general[(general["iso3"].eq(country)) &
                      (general["anio"].eq(year))]
    if matched.empty:
        _section_note(
            f"{names.get(country, country)} · {year}: hay {len(chosen)} sectores "
            "reportados, pero no un PiN intersectorial inequívoco del mismo año. "
            "No se calculan totales a partir de los sectores."
        )
    else:
        general_value = fmt(matched["population"].iloc[0], 0)
        _section_note(
            f"{names.get(country, country)} · {year}: PiN intersectorial "
            f"{general_value} personas y {len(chosen)} sectores con estimaciones. "
            "Las cifras sectoriales pueden superponerse."
        )

    l, r = st.columns(2, gap="medium")
    with l:
        with card("Necesidades por sector",
                  f"{names.get(country, country)} · {year} · personas en necesidad.",
                  "OCHA Humanitarian Needs vía HAPI", height=H):
            plot(rank_bars(
                chosen, label="sector", value="population", limit=13,
                units="Personas en necesidad", formats=".0f",
            ), height=365)
    with r:
        with table_card("Estimaciones sectoriales",
                        "Valores por sector del año seleccionado; no sumables.",
                        "OCHA Humanitarian Needs vía HAPI", height=H):
            table(chosen, height=390, columns=["sector", "population"],
                  labels={"sector": "Sector", "population": "Personas en necesidad"})


def _movilidad_tab(D, selected):
    """Refugio, asilo y desplazamiento forzado dentro de Amenazas y eventos."""
    st.caption("Refugio y asilo (ACNUR), desplazamiento interno (IDMC) "
               "y operaciones de movilidad (OIM DTM); son indicadores distintos.")
    topic = _subgroup("Tipo de movilidad",
                      ["Refugio y asilo", "Desplazamiento interno"],
                      "op_movilidad_grupo")
    if topic == "Refugio y asilo":
        _acnur_tab(D, selected)
    elif topic == "Desplazamiento interno":
        mode = _subgroup("Fuente de desplazamiento",
            ["Estimaciones anuales", "Desplazamiento reciente", "Operaciones OIM"],
            "op_desplazamiento_modo")
        if mode == "Estimaciones anuales":
            gidd_tab(D, selected)
        elif mode == "Desplazamiento reciente":
            idu_tab(D, selected)
        else:
            _dtm_tab(D, selected)

POVERTY_CONTEXT_INDICATOR = "MPI_HEADCOUNT_RATIO"
CONTEXT_INDICATOR_LABELS = {
    **OPS_LABELS,
    POVERTY_CONTEXT_INDICATOR: "Incidencia de pobreza multidimensional (%)",
}


def _poverty_context_frame(D, selected):
    """Normalizar OPHI MPI a las columnas del comparador de Salud y sociedad.

    headcount_ratio ya está expresado en porcentaje en el snapshot HAPI:
    NO multiplicar por 100. Conservar el año real de cada país.
    """
    columns = ["iso3", "pais", "indicador", "valor", "periodo"]
    mpi = filtered(D.get("mpi", pd.DataFrame()), selected)
    required = {"iso3", "pais", "headcount_ratio", "reference_period_start"}
    if mpi.empty or not required.issubset(mpi.columns):
        return pd.DataFrame(columns=columns)
    frame = mpi[["iso3", "pais", "headcount_ratio",
                 "reference_period_start"]].copy()
    frame["valor"] = pd.to_numeric(frame["headcount_ratio"], errors="coerce")
    frame["periodo"] = pd.to_numeric(
        frame["reference_period_start"].astype(str).str[:4], errors="coerce")
    frame = frame.dropna(subset=["iso3", "valor", "periodo"]).copy()
    frame = frame[frame["valor"].between(0, 100)]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    frame["periodo"] = frame["periodo"].astype(int)
    frame["indicador"] = POVERTY_CONTEXT_INDICATOR
    frame = (frame.sort_values("periodo")
             .drop_duplicates(["iso3", "periodo"], keep="last"))
    return frame[columns]


def _ops_tab(D, selected):
    ops = filtered(D["ops"], selected)
    poverty = _poverty_context_frame(D, selected)
    existing = set(ops["indicador"].dropna()) if not ops.empty else set()
    opts = [x for x in OPS_OPTIONS if x in existing]
    # El indicador debe ser visible sin desplazarse al final del selector.
    # Mantenerlo aunque el país seleccionado no disponga de registros MPI.
    if not D.get("mpi", pd.DataFrame()).empty:
        opts.insert(1 if "GINI" in opts else 0, POVERTY_CONTEXT_INDICATOR)
    if not opts:
        info_missing("indicadores de salud, sociedad y pobreza")
        return

    l, r = st.columns([1.15, .85])
    with l:
        choice = st.selectbox(
            "Indicador", opts, key="op_ops_ind",
            format_func=lambda x: CONTEXT_INDICATOR_LABELS.get(x, x))
    with r:
        common = st.checkbox("Mismo año en todos los países",
                             key="op_ops_common")

    is_poverty = choice == POVERTY_CONTEXT_INDICATOR
    source_data = poverty if is_poverty else ops
    source_label = ("OPHI MPI · vía OCHA HAPI" if is_poverty
                    else "OPS · Indicadores Básicos")
    years = sorted(
        source_data[source_data["indicador"].eq(choice)]["periodo"]
        .dropna().astype(int).unique(), reverse=True)
    year = (st.selectbox("Año", years, key="op_ops_year")
            if common and years else None)
    picked = latest_ops(source_data, choice, year).copy()
    if picked.empty:
        info_missing("incidencia de pobreza multidimensional para el ámbito y año seleccionados"
                     if is_poverty else "observaciones para la selección")
        return
    picked["anio"] = picked["periodo"].astype(int)
    label = CONTEXT_INDICATOR_LABELS.get(choice, choice)

    metric_strip([
        (f"{picked['iso3'].nunique()}/{len(selected)}", "PAÍSES CON DATO",
         "OPHI MPI · vía HAPI" if is_poverty else "Indicador OPS seleccionado"),
        (str(year) if year is not None else "Según país",
         "PERIODO", "Último por país" if year is None else "Año común"),
    ])
    if is_poverty:
        _section_note(
            "Incidencia de pobreza multidimensional de OPHI, disponible "
            "a través de OCHA HAPI (% de la población), no de Indicadores "
            "Básicos de OPS. La cobertura y los años varían entre países; "
            "al seleccionar un mismo año solo aparecen países con datos "
            "para ese año."
        )
    else:
        _section_note(
            "Estos indicadores describen contexto y capacidad sanitaria nacional, "
            "no respuesta operativa durante una crisis. Sin año común, cada país "
            "puede tener un corte diferente."
        )

    with card("Comparación entre países",
              "Valor publicado y año de referencia disponibles al pasar el cursor.",
              source_label):
        plot(strip_countries(picked, name="pais", val="valor", year="anio",
                             units=label, max_items=25), height=425)



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
        with table_card("Financiación de planes humanitarios",
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
    title("02 / VULNERABILIDAD Y RESPUESTA", "Vulnerabilidad y respuesta",
          "Riesgo estructural, contexto social y sanitario, personas en necesidad, seguridad alimentaria y respuesta.")
    topic = _subgroup("Subtema",
                      ["Riesgo INFORM", "Salud y sociedad", "Personas en necesidad",
                       "Seguridad alimentaria", "Respuesta"],
                      "op_vulnerabilidad_grupo")
    if topic == "Riesgo INFORM":
        risk_page(D, selected)
    elif topic == "Salud y sociedad":
        _ops_tab(D, selected)
    elif topic == "Personas en necesidad":
        _pin_tab(D, selected)
    elif topic == "Seguridad alimentaria":
        _ipc_tab(D, selected)
    else:
        _response_tab(D, selected)

def perfil_page(D, selected, names):
    """Mantener contrato de navegación; la ficha completa vive en perfil_integral."""
    profile_page(D, selected, names)
