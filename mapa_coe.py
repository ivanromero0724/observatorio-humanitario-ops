"""Mapa de países con presentación COE-regional: Plotly, fondo blanco y vista fija.

La geometría y los datos provienen de las fuentes del observatorio.
Las tonalidades representan magnitud del indicador, nunca prioridad OPS.
"""
from __future__ import annotations

import math
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import sample_colorscale
import streamlit as st
from ui_ops import geography
from estilo_coe import NAVY, CYAN, BORDER, TEXT, MUTED, FONT

BLUES = ["#EAF3F9", "#75B8D6", "#009BDA", "#005A8B"]
NODATA = "#E8EDF2"
ZERO = "#F3F7FA"


def _parts(geometry):
    if geometry is None or geometry.is_empty:
        return []
    if geometry.geom_type == "Polygon":
        return [geometry]
    if geometry.geom_type == "MultiPolygon":
        return list(geometry.geoms)
    return []


def pa_map(frame, mode, legend_title, height=428, unit="eventos"):
    """Coropleta descriptiva nacional sin zoom/pan y con hover accesible."""
    geo = geography()
    if geo is None or geo.empty:
        st.info("No se dispone de la geometría de países.")
        return
    if frame is None or frame.empty:
        st.info("No hay registros geográficos para los filtros seleccionados.")
        return

    vals = frame[["iso3", "valor"]].drop_duplicates("iso3").copy()
    vals["valor"] = pd.to_numeric(vals["valor"], errors="coerce")
    names = (frame[["iso3", "pais"]].drop_duplicates("iso3")
             if "pais" in frame.columns
             else pd.DataFrame(columns=["iso3", "pais"]))
    geo = geo.merge(vals, left_on="ISO_CC", right_on="iso3", how="left")
    geo = geo.merge(names.rename(columns={"pais": "label_country"}),
                    on="iso3", how="left")
    geo["label_country"] = geo["label_country"].fillna(geo["COUNTRY"])

    maximum = vals["valor"].max()
    if pd.isna(maximum) or maximum <= 0:
        maximum = 1.0

    fig = go.Figure()
    for _, item in geo.iterrows():
        value = item["valor"]
        if pd.isna(value):
            color = NODATA
            shown = "Sin dato comparable"
        elif value == 0:
            color = ZERO
            shown = "0 " + unit if mode != "severity" else "0 / 10"
        else:
            z = (float(value) / 10) if mode == "severity" else (
                math.log1p(max(0, float(value))) / math.log1p(float(maximum)))
            z = min(1, max(0, z))
            color = sample_colorscale(BLUES, z)[0]
            shown = (f"{float(value):,.1f} / 10" if mode == "severity"
                     else f"{float(value):,.0f} {unit}")
        x, y = [], []
        for polygon in _parts(item.geometry):
            # Exterior, como el mapa de COE-regional; separación por islas.
            xs, ys = polygon.exterior.xy
            x.extend(list(xs) + [None])
            y.extend(list(ys) + [None])
        if not x:
            continue
        name = str(item["label_country"])
        tip = f"<b>{name}</b><br><b>{legend_title}:</b> {shown}"
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="lines", fill="toself", fillcolor=color,
            line=dict(color="#FFFFFF", width=.75),
            hoveron="fills", hoverinfo="text", hovertemplate=tip+"<extra></extra>",
            showlegend=False, name=name,
        ))

    # Vista fija para todas las Américas (análogo al COE, con ámbito mayor).
    fig.update_xaxes(range=[-175, -24], fixedrange=True, visible=False,
                     showgrid=False, zeroline=False, constrain="domain")
    fig.update_yaxes(range=[-64, 85], fixedrange=True, visible=False,
                     showgrid=False, zeroline=False, scaleanchor="x",
                     scaleratio=1, constrain="domain")
    fig.update_layout(
        height=height, paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        font=dict(family=FONT, size=11, color=TEXT),
        margin=dict(l=2, r=2, t=4, b=4),
        dragmode=False, hovermode="closest", showlegend=False,
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=BORDER,
                        font=dict(family=FONT, color=TEXT, size=11), align="left"),
    )
    legend = ("Severidad ACAPS · 0–10" if mode == "severity"
              else "Magnitud de "+unit+" · escala logarítmica")
    fig.add_annotation(
        x=.018, y=.025, xref="paper", yref="paper",
        xanchor="left", yanchor="bottom", showarrow=False,
        text=f"<b>{legend}</b><br>Azul claro: menor · azul oscuro: mayor<br>"
             "Gris: sin dato comparable",
        bgcolor="rgba(255,255,255,0.95)", bordercolor=BORDER, borderwidth=1,
        borderpad=8, align="left", font=dict(size=10, color=MUTED),
    )
    st.plotly_chart(fig, width="stretch",
        config={"displayModeBar":False,"scrollZoom":False,"responsive":True})
