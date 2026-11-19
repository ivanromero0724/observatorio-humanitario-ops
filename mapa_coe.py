"""Mapa de países con presentación COE-regional: Plotly, fondo blanco y vista fija.

La geometría y los datos provienen de las fuentes del observatorio.
Las tonalidades representan magnitud del indicador, nunca prioridad OPS.
"""
from __future__ import annotations

import math
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from ui_ops import geography
from estilo_coe import NAVY, CYAN, BORDER, TEXT, MUTED, FONT

BLUES = ["#EAF3F9", "#75B8D6", "#009BDA", "#005A8B"]
NODATA = "#E8EDF2"

ZERO = "#F3F7FA"


def _gradient(z):
    """Interpolación RGB estable; no depende de cambios de Plotly."""
    z = min(1.0, max(0.0, float(z)))
    t = z * (len(BLUES) - 1)
    i = min(len(BLUES) - 2, int(t))
    mix = t - i
    def rgb(color):
        return tuple(int(color[j:j + 2], 16) for j in (1, 3, 5))
    a, b = rgb(BLUES[i]), rgb(BLUES[i + 1])
    return "#" + "".join(f"{round(x + (y - x) * mix):02X}" for x, y in zip(a, b))


def _parts(geometry):
    if geometry is None or geometry.is_empty:
        return []
    if geometry.geom_type == "Polygon":
        return [geometry]
    if geometry.geom_type == "MultiPolygon":
        return list(geometry.geoms)
    return []


def _legend_ticks(mode, maximum):
    """Etiquetas numéricas en la misma escala que los colores reales.

    Para eventos/personas conservamos la transformación logarítmica,
    pero las etiquetas corresponden a cantidades, no a logaritmos.
    """
    if mode in ("severity", "risk"):
        return [(0.0, "0"), (0.5, "5"), (1.0, "10")]
    if maximum <= 0:
        return [(0.0, "0")]
    positions = (0.0, 1 / 3, 2 / 3, 1.0)
    ticks = []
    for z in positions:
        actual = math.expm1(math.log1p(maximum) * z)
        if math.isclose(z, 1.0):
            actual = maximum
        value = int(round(actual)) if float(maximum).is_integer() else actual
        label = f"{value:,.0f}" if float(value).is_integer() else f"{value:,.1f}"
        if not ticks or label != ticks[-1][1]:
            ticks.append((z, label))
    return ticks


def _numeric_legend(fig, mode, maximum, legend_title):
    """Barra continua con valores 0–máximo dentro del mapa, estilo COE."""
    # Los rectángulos usan coordenadas del papel y nunca dependen del zoom.
    x0, x1 = .039, .405
    y0, y1 = .022, .225
    fig.add_shape(
        type="rect", xref="paper", yref="paper", x0=.017, x1=.429,
        y0=y0, y1=y1, fillcolor="rgba(255,255,255,0.96)",
        line=dict(color=BORDER, width=1), layer="above",
    )
    title = (legend_title.split(" · ")[0] if mode not in ("severity", "risk")
             else "Severidad ACAPS" if mode == "severity" else "Riesgo INFORM")
    fig.add_annotation(
        x=x0, y=.194, xref="paper", yref="paper",
        xanchor="left", yanchor="middle", showarrow=False,
        text=f"<b>{title}</b>", font=dict(size=10, color=TEXT),
    )
    for i in range(48):
        a, b = i / 48, (i + 1) / 48
        fig.add_shape(
            type="rect", xref="paper", yref="paper",
            x0=x0 + (x1 - x0) * a, x1=x0 + (x1 - x0) * b + 0.0003,
            y0=.129, y1=.156, fillcolor=_gradient((a + b) / 2),
            line=dict(width=0), layer="above",
        )
    for pos, label in _legend_ticks(mode, maximum):
        fig.add_annotation(
            x=x0 + (x1 - x0) * pos, y=.103, xref="paper", yref="paper",
            text=label, showarrow=False,
            xanchor="left" if pos == 0 else "right" if pos == 1 else "center",
            yanchor="middle", font=dict(size=9, color=TEXT),
        )
    fig.add_annotation(
        x=x0, y=.051, xref="paper", yref="paper",
        xanchor="left", yanchor="middle", showarrow=False,
        text=("Gris: sin datos · Escala logarítmica"
              if mode not in ("severity", "risk") else "Gris: sin datos · Escala 0–10"),
        font=dict(size=9, color=MUTED),
    )


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
        maximum = 0.0
    color_maximum = max(1.0, float(maximum))

    fig = go.Figure()
    for _, item in geo.iterrows():
        value = item["valor"]
        if pd.isna(value):
            color = NODATA
            shown = "Sin dato comparable"
        elif value == 0:
            color = BLUES[0]
            shown = "0 / 10" if mode in ("severity", "risk") else "0 " + unit
        else:
            z = (float(value) / 10) if mode in ("severity", "risk") else (
                math.log1p(max(0, float(value))) / math.log1p(color_maximum))
            z = min(1, max(0, z))
            color = _gradient(z)
            shown = (f"{float(value):,.1f} / 10" if mode in ("severity", "risk")
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
    _numeric_legend(fig, mode, maximum, legend_title)
    st.plotly_chart(fig, width="stretch",
        config={"displayModeBar":False,"scrollZoom":False,"responsive":True})
