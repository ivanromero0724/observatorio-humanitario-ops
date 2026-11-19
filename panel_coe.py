"""Paneles compactos COE: título externo, gráfico como única superficie blanca."""
from __future__ import annotations
from contextlib import contextmanager
from hashlib import sha1

import streamlit as st
from observatorio_v4 import esc


@contextmanager
def card(title: str, subtitle: str = "", source: str = "", height=None):
    # ID estable por panel y asunto, permite selectores CSS robustos para QA.
    stamp = sha1((title + "\\0" + subtitle + "\\0" + source).encode("utf-8")).hexdigest()[:12]
    st.markdown(
        f'<div class="obs-card-title">{esc(title)}</div>'
        + (f'<div class="obs-card-sub">{esc(subtitle)}</div>' if subtitle else ""),
        unsafe_allow_html=True,
    )
    with st.container(border=True,
                      height=height if height is not None else "content",
                      key=f"coe_chart_{stamp}"):
        yield
    if source:
        st.markdown(
            f'<div class="obs-card-source">Fuente: {esc(source)}</div>',
            unsafe_allow_html=True,
        )


@contextmanager
def table_card(title: str, subtitle: str = "", source: str = "", height=None):
    """Panel COE para tablas: marco y altura iguales a tarjetas de gráficos.

    El único borde pertenece al panel exterior y la tabla se integra en su
    interior. Las tablas emparejadas comparten altura con el gráfico vecino;
    una tabla independiente conserva altura natural si no se solicita.
    """
    stamp = sha1((title + "\\0" + subtitle + "\\0" + source).encode("utf-8")).hexdigest()[:12]
    st.markdown(
        f'<div class="obs-card-title">{esc(title)}</div>'
        + (f'<div class="obs-card-sub">{esc(subtitle)}</div>' if subtitle else ""),
        unsafe_allow_html=True,
    )
    # El COE usa el mismo marco #DFE9F1 de los gráficos, con contenido
    # separado por un margen interior. El contenedor controla la altura.
    with st.container(
        border=True,
        height=height if height is not None else "content",
        key=f"coe_table_{stamp}",
    ):
        yield
    if source:
        st.markdown(
            f'<div class="obs-card-source">Fuente: {esc(source)}</div>',
            unsafe_allow_html=True,
        )
