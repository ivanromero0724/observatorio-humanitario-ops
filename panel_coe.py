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
    """Presentar tablas como superficies propias, no dentro de otra caja.

    Se conserva la posición de títulos y fuentes respecto a los gráficos.
    El parámetro height es compatible con las llamadas antiguas, pero no
    fuerza una altura artificial ni deja grandes áreas vacías.
    """
    stamp = sha1((title + "\\0" + subtitle + "\\0" + source).encode("utf-8")).hexdigest()[:12]
    st.markdown(
        f'<div class="obs-card-title">{esc(title)}</div>'
        + (f'<div class="obs-card-sub">{esc(subtitle)}</div>' if subtitle else ""),
        unsafe_allow_html=True,
    )
    # Contenedor estructural sin borde ni altura fija: la tabla es la única
    # superficie visual. Los controles y notas se quedan junto a sus datos.
    with st.container(border=False, key=f"coe_table_{stamp}"):
        yield
    if source:
        st.markdown(
            f'<div class="obs-card-source">Fuente: {esc(source)}</div>',
            unsafe_allow_html=True,
        )
