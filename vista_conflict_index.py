"""ACLED Conflict Index 2025: clasificación original y cuatro dimensiones.

Snapshot público del archivo ACLED Conflict Index - December 2025, agregado
exclusivamente por país. No asigna una prioridad institucional OPS.
"""
from __future__ import annotations

import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from observatorio_v2 import filtered
from observatorio_v4 import plot, table, fmt, info_missing
from graficos import rank_bars, finish
from ui_ops import geography
from mapa_coe import _parts, NODATA
from estilo_coe import BORDER, TEXT, MUTED, FONT
from panel_coe import card, table_card
from tarjetas_resumen import metric_strip

SOURCE = "ACLED · Conflict Index 2025"
SOURCE_URL = "https://acleddata.com/series/acled-conflict-index"
PERIOD = "1 dic. 2024 – 28 nov. 2025"
H = 430

# Las cuatro clases pertenecen a ACLED, no a una evaluación de prioridad OPS.
CLASSES = {
    "Extreme": ("Extremo", "#AA4749"),
    "High": ("Alto", "#E38454"),
    "Turbulent": ("Turbulento", "#E6BC6A"),
    "Low/Inactive": ("Bajo/inactivo", "#92AEC0"),
}
DIMENSIONS = {
    "Letalidad (fallecidos reportados)": (
        "fallecidos_reportados", "Fallecidos reportados", ".0f"),
    "Difusión territorial (%)": (
        "difusion_pct", "Superficie habitada de alta violencia (%)", ".1f"),
    "Peligro para civiles (eventos)": (
        "eventos_violencia_dirigida_civiles", "Eventos dirigidos a civiles", ".0f"),
    "Fragmentación (grupos activos)": (
        "grupos_armados_activos", "Grupos armados activos", ".0f"),
}


def _prepare(D: dict, selected: set[str]) -> pd.DataFrame:
    raw = D.get("acled_conflict_index", pd.DataFrame())
    if raw is None or raw.empty:
        return pd.DataFrame()
    scope = filtered(raw, selected).copy()
    if scope.empty:
        return scope
    names = D["countries"].set_index("iso3")["pais"].to_dict()
    scope["pais"] = scope["iso3"].map(names).fillna(scope["pais_fuente"])
    scope["nivel_es"] = scope["nivel_indice"].map(
        {key: label for key, (label, _) in CLASSES.items()}
    ).fillna("Sin clasificación")
    scope["difusion_pct"] = (
        pd.to_numeric(scope["proporcion_difusion"], errors="coerce") * 100
    )
    return scope


def _class_map(frame: pd.DataFrame) -> None:
    """Coropleta categórica: nunca presentar categorías como escala continua."""
    geo = geography()
    if geo is None or geo.empty:
        info_missing("geometría de países de las Américas")
        return
    cols = frame[["iso3", "pais", "nivel_indice", "ranking_global"]].drop_duplicates("iso3")
    geo = geo.merge(cols, left_on="ISO_CC", right_on="iso3", how="left")
    fig = go.Figure()
    for _, item in geo.iterrows():
        level = item["nivel_indice"]
        if pd.isna(level) or level not in CLASSES:
            color = NODATA
            shown = "Sin dato para el ámbito seleccionado"
        else:
            label, color = CLASSES[level]
            rank = item["ranking_global"]
            shown = f"{label} · Puesto mundial {int(rank)}" if pd.notna(rank) else label
        xs, ys = [], []
        for polygon in _parts(item.geometry):
            x, y = polygon.exterior.xy
            xs.extend(list(x) + [None])
            ys.extend(list(y) + [None])
        if not xs:
            continue
        name = item["pais"] if pd.notna(item["pais"]) else item["COUNTRY"]
        tip = f"<b>{html.escape(str(name))}</b><br>ACLED 2025: {shown}"
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", fill="toself",
            fillcolor=color, line=dict(color="#FFFFFF", width=0.75),
            hoveron="fills", hoverinfo="text", hovertemplate=tip+"<extra></extra>",
            showlegend=False, name=str(name),
        ))
    fig.update_xaxes(range=[-175, -24], fixedrange=True, visible=False,
                     showgrid=False, zeroline=False, constrain="domain")
    fig.update_yaxes(range=[-64, 85], fixedrange=True, visible=False,
                     showgrid=False, zeroline=False, scaleanchor="x",
                     scaleratio=1, constrain="domain")
    fig.update_layout(
        height=335, paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        font=dict(family=FONT, size=11, color=TEXT),
        margin=dict(l=2, r=2, t=4, b=4),
        dragmode=False, hovermode="closest", showlegend=False,
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=BORDER,
                        font=dict(family=FONT, color=TEXT, size=11)),
    )
    st.plotly_chart(fig, width="stretch",
        config={"displayModeBar": False, "scrollZoom": False, "responsive": True})
    key = " · ".join(
        f'<span style="color:{color};font-weight:700">●</span> {label}'
        for label, color in CLASSES.values()
    )
    st.markdown(
        f'<div style="font-size:11px;color:{MUTED};padding:1px 0 4px">'
        f'{key} · <span style="color:{NODATA}">●</span> Sin datos</div>',
        unsafe_allow_html=True,
    )


def _world_ranking(frame: pd.DataFrame):
    """Puesto global original de ACLED: el número menor indica mayor conflicto."""
    top = frame.sort_values(["ranking_global", "pais"]).head(15)
    fig = go.Figure()
    for key, (label, color) in CLASSES.items():
        part = top[top["nivel_indice"].eq(key)].sort_values(
            "ranking_global", ascending=False
        )
        if part.empty:
            continue
        fig.add_trace(go.Scatter(
            x=part["ranking_global"], y=part["pais"],
            mode="markers+text", text=["#" + str(int(v)) for v in part["ranking_global"]],
            textposition="middle right", textfont=dict(size=10, color=TEXT),
            marker=dict(color=color, size=11, line=dict(color="white", width=1)),
            name=label, showlegend=False,
            hovertemplate="<b>%{y}</b><br>Puesto mundial: %{x}<br>"
                          + label + "<extra></extra>",
        ))
    finish(fig, height=350, orient="horizontal", units="Puesto mundial")
    max_rank = int(top["ranking_global"].max()) if not top.empty else 15
    fig.update_xaxes(range=[0, max_rank + max(7, max_rank * .12)],
                     dtick=5 if max_rank <= 60 else 20)
    fig.update_layout(margin=dict(l=8, r=44, t=10, b=42))
    return fig


def acled_conflict_tab(D: dict, selected: set[str]) -> None:
    frame = _prepare(D, selected)
    if frame.empty:
        info_missing("clasificación ACLED Conflict Index 2025 para estos países")
        return

    counts = frame["nivel_indice"].value_counts().to_dict()
    metric_strip([
        (fmt(counts.get(key, 0)), f"CONFLICTO {label.upper()}",
         "Clasificación ACLED 2025, no prioridad OPS")
        for key, (label, _) in CLASSES.items()
    ])
    st.caption(
        f"ACLED Conflict Index 2025 · periodo {PERIOD}. "
        "La clasificación y el ranking son mundiales; se muestra el subconjunto "
        "de países de las Américas seleccionado. No equivale al riesgo INFORM, "
        "a la severidad ACAPS ni a un nivel de prioridad institucional OPS."
    )

    a, b = st.columns(2, gap="medium")
    with a:
        with card("Clasificación del conflicto por país",
                  "Cuatro niveles originales de ACLED · no escala OPS.",
                  SOURCE, height=H):
            _class_map(frame)
    with b:
        with card("Países mejor posicionados en el ranking de conflicto",
                  "15 primeros del ámbito · puesto mundial (1 = mayor conflicto).",
                  SOURCE, height=H):
            plot(_world_ranking(frame), height=362)

    st.markdown("#### Cuatro dimensiones del índice")
    choices = sorted(frame["iso3"].unique(), key=lambda c:
                     frame.set_index("iso3").loc[c, "pais"])
    default = "COL" if "COL" in choices else choices[0]
    country = st.selectbox(
        "País para examinar las dimensiones", choices,
        index=choices.index(default),
        format_func=lambda c: frame.set_index("iso3").loc[c, "pais"],
        key="op_acled_index_country", width="stretch",
    )
    r = frame.set_index("iso3").loc[country]
    metric_strip([
        (fmt(r["fallecidos_reportados"], 0), "LETALIDAD",
         "Fallecidos reportados, no estimación exhaustiva"),
        (f'{r["difusion_pct"]:.1f} %', "DIFUSIÓN TERRITORIAL",
         "Porcentaje de celdas habitadas de alta violencia"),
        (fmt(r["eventos_violencia_dirigida_civiles"], 0),
         "PELIGRO PARA CIVILES", "Eventos de violencia dirigidos a civiles"),
        (fmt(r["grupos_armados_activos"], 0), "FRAGMENTACIÓN",
         "Grupos activos conforme a la definición ACLED"),
    ])
    st.caption(
        f'{r["pais"]} · clasificación {r["nivel_es"]} · puesto mundial '
        f'{int(r["ranking_global"])}. Cada dimensión tiene unidades diferentes: '
        "no se suman ni se interpretan como puntuaciones comparables."
    )

    selected_dimension = st.selectbox(
        "Indicador para comparar países", list(DIMENSIONS),
        key="op_acled_index_dimension", width="stretch",
    )
    col, unit, number_format = DIMENSIONS[selected_dimension]
    c, d = st.columns(2, gap="medium")
    with c:
        with card("Comparación de países por dimensión",
                  f"{selected_dimension} · mismo periodo 2025.",
                  SOURCE, height=H):
            plot(rank_bars(
                frame, label="pais", value=col, limit=13,
                units=unit, formats=number_format,
            ), height=366)
    with d:
        with table_card("Ranking y valores por país",
                        "Puesto mundial original; la difusión se muestra en porcentaje.",
                        SOURCE, height=H):
            ordered = frame.sort_values(["ranking_global", "pais"])
            table(ordered, height=385,
                  columns=["pais", "nivel_es", "ranking_global",
                           "fallecidos_reportados", "difusion_pct",
                           "eventos_violencia_dirigida_civiles",
                           "grupos_armados_activos"],
                  labels={"pais": "País", "nivel_es": "Nivel ACLED",
                          "ranking_global": "Puesto mundial",
                          "fallecidos_reportados": "Fallecidos",
                          "difusion_pct": "Difusión (%)",
                          "eventos_violencia_dirigida_civiles": "Eventos contra civiles",
                          "grupos_armados_activos": "Grupos activos"})
    st.caption(
        "Fuente: ACLED, Conflict Index (edición diciembre 2025). "
        "Datos por país del archivo original, asociados con códigos ISO3 y "
        "denominaciones en español para el observatorio. "
        f"Metodología: {SOURCE_URL}. El índice es un corte de 2025, no "
        "seguimiento en tiempo real."
    )


def profile_acled_conflict(D: dict, selected: set[str]) -> None:
    """Ficha por país: no mezclar ranking ACLED con riesgo INFORM."""
    n = _prepare(D, selected)
    if n.empty:
        return
    r = n.sort_values("ranking_global").iloc[0]
    with card("Índice de conflicto ACLED 2025",
              f"Clasificación mundial · {PERIOD}", SOURCE, height=H):
        st.metric("Nivel de conflicto ACLED", r["nivel_es"])
        st.metric("Puesto mundial", f'{int(r["ranking_global"])}')
        st.metric("Fallecidos reportados", fmt(r["fallecidos_reportados"], 0))
        st.metric("Difusión territorial", f'{r["difusion_pct"]:.1f} %')
        st.caption("Ranking global, no prioridad OPS. Indicadores y método: "
                   + SOURCE_URL)
