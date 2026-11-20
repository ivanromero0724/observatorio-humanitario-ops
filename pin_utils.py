"""Preparación de PiN intersectorial y sectorial para HAPI Humanitarian Needs.

PiN=population_status INN. Los registros por sector, grupo de población o
subsector pueden solaparse. NUNCA deben sumarse para reconstruir el PiN total.
"""
from __future__ import annotations

import pandas as pd

SECTOR_LABELS = {
    "CCM": "Gestión de campamentos",
    "EDU": "Educación",
    "ERY": "Recuperación temprana",
    "FSC": "Seguridad alimentaria",
    "HEA": "Salud",
    "NUT": "Nutrición",
    "PRO": "Protección",
    "PRO-CPN": "Protección de la niñez",
    "PRO-GBV": "Violencia basada en género",
    "PRO-MIN": "Acción contra minas",
    "SHL": "Alojamiento",
    "WSH": "Agua, saneamiento e higiene",
}


def _base_pin(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna solo las estimaciones nacionales PiN, categoría general.

    La categoría vacía es la cifra agregada de HAPI. Excluimos 'total'
    y subgrupos, que frecuentemente replican esa cifra o incluyen
    valores distintos por redondeo. Sin estimación inequívoca no
    seleccionamos un grupo como si fuera el agregado.
    """
    if df.empty:
        return df.copy()
    n = df.copy()
    n = n[
        n["population_status"].fillna("").astype(str).str.strip().eq("INN")
        & n["category"].fillna("").astype(str).str.strip().eq("")
    ].copy()
    if "admin_level" in n.columns:
        admin = pd.to_numeric(n["admin_level"], errors="coerce")
        n = n[admin.eq(0)].copy()
    n["anio"] = pd.to_numeric(
        n["reference_period_start"].astype(str).str[:4], errors="coerce"
    )
    n["population"] = pd.to_numeric(n["population"], errors="coerce")
    return n.dropna(subset=["anio", "population", "iso3", "sector_code"])


def _unique_estimates(n: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if n.empty:
        return n
    # Si dos recursos nacionales dan cifras distintas para la misma
    # selección, se descarta el grupo ambiguo sin sumar/escoger al azar.
    values = n.groupby(columns, dropna=False)["population"].transform("nunique")
    return n[values.eq(1)].drop_duplicates(columns).copy()


def intersectoral_pin(df: pd.DataFrame) -> pd.DataFrame:
    """Una cifra intersectorial por país y año, si no es ambigua."""
    n = _base_pin(df)
    n = n[n["sector_code"].astype(str).str.casefold().eq("intersectoral")]
    return _unique_estimates(n, ["iso3", "anio"])


def sectoral_pin(df: pd.DataFrame) -> pd.DataFrame:
    """Una cifra por país, año y sector (no sumable entre sectores)."""
    n = _base_pin(df)
    n = n[~n["sector_code"].astype(str).str.casefold().eq("intersectoral")]
    n = _unique_estimates(n, ["iso3", "anio", "sector_code"])
    n["sector"] = n["sector_code"].map(SECTOR_LABELS).fillna(n["sector_name"])
    return n
