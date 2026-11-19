"""Franja compacta de indicadores, estilo Clúster Salud OPS.

Presenta indicadores independientes sin añadirlos, promediarlos o alterar
unidades. Escapa todo texto antes de incluirlo en HTML.
"""
from __future__ import annotations

from html import escape
from numbers import Real
import pandas as pd
import streamlit as st

from observatorio_v4 import fmt


def metric_strip(items):
    """items = [(valor, etiqueta, descripción), ...]"""
    if not items:
        return
    parts=[]
    for value, label, description in items:
        parts.append(
            '<div class="ops-strip-item">'
            f'<div class="ops-strip-value">{escape(fmt(value) if isinstance(value, Real) and not isinstance(value, bool) and pd.notna(value) else str(value))}</div>'
            f'<div class="ops-strip-label">{escape(str(label))}</div>'
            f'<div class="ops-strip-desc">{escape(str(description))}</div>'
            '</div>'
        )
    st.markdown(
        '<div class="ops-metric-strip" role="group" aria-label="Indicadores principales"'
        f' style="--ops-items:{len(items)}">' + ''.join(parts) + '</div>',
        unsafe_allow_html=True,
    )
