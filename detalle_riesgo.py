"""Desgloses metodológicos verificables de ACAPS e INFORM/HAPI.

Se evita confundir el índice estructural INFORM (2025) con la severidad
ACAPS por crisis (2026), o con prioridades institucionales OPS.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from observatorio_v2 import filtered
from observatorio_v4 import info_missing, plot, fmt
from observatorio_v5 import title, crisis_core
from panel_coe import card
from mapa_coe import pa_map
from graficos import rank_bars

BLUE = "#009BDA"
ORANGE = "#F36B32"

INFORM_DIMENSIONS = {
    "hazard_exposure_risk": "Amenazas y exposición",
    "vulnerability_risk": "Vulnerabilidad",
    "coping_capacity_risk": "Falta de capacidad de afrontamiento",
}

ACCESS_PILLARS = {
    "pilar_1": "P1 · Acceso de la población a la ayuda",
    "pilar_2": "P2 · Acceso de actores humanitarios",
    "pilar_3": "P3 · Restricciones físicas, ambientales y de seguridad",
}
# Los indicadores quedan identificados con su código ACAPS en lugar de
# atribuirles nombres que no consten en el snapshot de la API.
ACCESS_INDICATORS = {
    "indicador_1": "I1 · Negación de necesidades",
    "indicador_2": "I2 · Acceso a servicios",
    "indicador_3": "I3 · Entrada al país",
    "indicador_4": "I4 · Movilidad interna",
    "indicador_5": "I5 · Interferencia a la ayuda",
    "indicador_6": "I6 · Violencia contra actores",
    "indicador_7": "I7 · Inseguridad",
    "indicador_8": "I8 · Minas y explosivos",
    "indicador_9": "I9 · Barreras físicas",
}


def _names(D):
    return D["countries"].set_index("iso3")["pais"].to_dict()


def risk_page(D, selected):
    """Riesgo nacional compuesto y tres componentes HAPI/INFORM (edición 2025)."""
    risk = filtered(D["inform_hapi"], selected)
    if risk.empty:
        info_missing("riesgo nacional INFORM/HAPI")
        return
    risk = risk.copy()
    names = _names(D)
    risk["pais"] = risk["iso3"].map(names).fillna(risk["iso3"])
    for col in ["overall_risk", *INFORM_DIMENSIONS,
                "meta_missing_indicators_pct", "meta_avg_recentness_years"]:
        risk[col] = pd.to_numeric(risk[col], errors="coerce")

    a, b = st.columns(2)
    a.metric("Países con perfil INFORM", f"{risk['overall_risk'].notna().sum()}/{len(selected)}")
    b.metric("Edición del indicador HAPI", "2025")
    st.caption(
        "INFORM integra amenazas de distinto origen (incluidas naturales), "
        "vulnerabilidad y falta de capacidad de afrontamiento. "
        "La puntuación va de 0 a 10; no es un nivel de prioridad asignado por OPS."
    )
    left, right = st.columns(2, gap="medium")
    with left:
        with card("Riesgo estructural por país",
                  "Puntuación compuesta INFORM · escala 0–10.",
                  "INFORM Risk a través de OCHA HAPI · 2025", height=420):
            pa_map(risk[["iso3", "pais", "overall_risk"]].rename(
                columns={"overall_risk": "valor"}), "risk", "Riesgo INFORM", height=366)
    with right:
        with card("Países con mayor riesgo INFORM",
                  "Comparación nacional del mismo corte 2025.",
                  "INFORM Risk a través de OCHA HAPI · 2025", height=420):
            plot(rank_bars(risk, label="pais", value="overall_risk", limit=12,
                           units="Puntuación / 10", max_x=10,
                           formats=".1f", color=BLUE), height=366)

    available = sorted(risk.loc[risk["overall_risk"].notna(), "iso3"],
                       key=lambda x: names.get(x,x))
    if not available:
        return
    default = "COL" if "COL" in available else available[0]
    selected_iso = st.selectbox(
        "Explorar los componentes del riesgo en un país",
        available, index=available.index(default),
        format_func=lambda c: names.get(c,c),
        key="op_inform_country",
    )
    record = risk.set_index("iso3").loc[selected_iso]
    parts = pd.DataFrame([
        {"Componente": label, "Puntuación": record.get(key)}
        for key, label in INFORM_DIMENSIONS.items()
    ]).dropna(subset=["Puntuación"])
    left, right = st.columns([1.15,.85], gap="medium")
    with left:
        with card(f"¿Qué explica el riesgo en {names.get(selected_iso,selected_iso)}?",
                  "Componentes estructurales; no son porcentajes ni son sumables.",
                  "INFORM Risk / HAPI · 2025", height=360):
            plot(rank_bars(parts, label="Componente", value="Puntuación",
                           formats=".1f", limit=3, units="Puntuación / 10",
                           max_x=10), height=298)
    with right:
        with card("Calidad y referencia del dato",
                  "Información de soporte del perfil INFORM.",
                  "OCHA HAPI · metadatos INFORM", height=360):
            score = record.get("overall_risk")
            st.metric("Riesgo compuesto", f"{score:.1f} / 10" if pd.notna(score) else "—")
            pct = record.get("meta_missing_indicators_pct")
            st.metric("Indicadores originales faltantes/estimados",
                      f"{pct*100:.1f} %" if pd.notna(pct) else "—")
            recent = record.get("meta_avg_recentness_years")
            st.caption(f"Antigüedad media de indicadores: {recent:.2f} años."
                       if pd.notna(recent) else "Antigüedad no informada.")
            st.caption(
                "Clase de riesgo INFORM: " + str(record.get("risk_class", "—")) +
                " · Posición global: " + str(record.get("global_rank", "—"))
            )
            st.caption("Edición 2025; no comparar directamente con la base INFORM Mid 2026.")


def acaps_detail(D, selected):
    """Selector de crisis y lectura de pilares, indicadores y brecha informativa."""
    severity = crisis_core(D, selected)
    if severity.empty:
        return
    access = filtered(D["access"], selected)
    if access.empty:
        info_missing("desglose de acceso ACAPS para el ámbito")
        return

    cols = ["iso3", "crisis_id", "brecha_info", "acceso", *ACCESS_PILLARS,
            *ACCESS_INDICATORS]
    access = access[[col for col in cols if col in access.columns]].drop_duplicates(
        ["iso3", "crisis_id"])
    detail = severity.merge(access, on=["iso3", "crisis_id"],
                            how="left", suffixes=("", "_detalle"))
    detail = detail.sort_values(["puntuacion", "pais"], ascending=[False, True])
    detail["nombre"] = detail["pais"].astype(str) + " · " + detail["crisis"].astype(str)
    options = detail.index.tolist()
    if not options:
        return
    idx = st.selectbox("Explorar una crisis evaluada", options, key="op_acaps_crisis",
                       format_func=lambda i: detail.loc[i, "nombre"])
    record = detail.loc[idx]
    drivers = str(record.get("drivers") or "").strip()
    if drivers and drivers.lower() not in ["nan", "none"]:
        st.caption("Factores impulsores publicados: " + drivers)
    st.caption(
        "Identificador de referencia: " + str(record.get("crisis_id", "—")) +
        " · Edición: " + str(record.get("corte_api","—"))
    )
    x, y, z = st.columns(3)
    severity_score = record.get("puntuacion")
    access_score = record.get("acceso")
    gap = pd.to_numeric(pd.Series([record.get("brecha_info")]), errors="coerce").iloc[0]
    x.metric("Severidad de la crisis", f"{severity_score:.1f} / 10"
             if pd.notna(severity_score) else "—")
    y.metric("Restricción de acceso", f"{access_score:.1f} / 5"
             if pd.notna(access_score) else "—")
    z.metric("Brecha de información", f"{gap*100:.1f} %"
             if pd.notna(gap) else "—")

    left, right = st.columns(2, gap="medium")
    pillars = pd.DataFrame([
        {"Pilar":label, "Valor":pd.to_numeric(
            pd.Series([record.get(key)]), errors="coerce").iloc[0]}
        for key, label in ACCESS_PILLARS.items()
    ]).dropna(subset=["Valor"])
    indicators = pd.DataFrame([
        {"Indicador":label, "Valor":pd.to_numeric(
            pd.Series([record.get(key)]), errors="coerce").iloc[0]}
        for key, label in ACCESS_INDICATORS.items()
    ]).dropna(subset=["Valor"])
    with left:
        with card("Tres pilares de acceso",
                  "Obstáculos para la población, las organizaciones y el entorno.",
                  "ACAPS Humanitarian Access · escala 0–5", height=384):
            if pillars.empty:
                info_missing("pilares de acceso")
            else:
                plot(rank_bars(pillars, label="Pilar", value="Valor",
                               formats=".1f", max_x=5, limit=3,
                               units="Puntuación / 5"), height=320)
    with right:
        with card("Nueve indicadores de acceso",
                  "I1–I9, agrupados por pilar; cada uno en escala 0–3.",
                  "ACAPS Humanitarian Access · escala 0–3", height=384):
            if indicators.empty:
                info_missing("indicadores de acceso")
            else:
                plot(rank_bars(indicators, label="Indicador", value="Valor",
                               formats=".1f", max_x=3, limit=9, color=ORANGE,
                               units="Puntuación / 3"), height=320)
    st.caption(
        "P1: acceso de personas afectadas a la ayuda (I1–I2). "
        "P2: acceso de actores humanitarios (I3–I6). "
        "P3: restricciones físicas, ambientales y de seguridad (I7–I9). "
        "La brecha de información expresa datos insuficientes, no ausencia de restricciones."
    )
