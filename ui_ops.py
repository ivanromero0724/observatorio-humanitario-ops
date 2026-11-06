"""Componentes visuales OPS/OMS y cartografía reutilizada de el-nino-ops.

Geopackage Natural Earth 1:50m: data/geografia/paises_americas.gpkg
Paleta y tratamientos visuales derivados de dashboard.py de el-nino-ops.
Se conserva el mapa completo y países/territorios sin datos en gris.
"""
from __future__ import annotations

import base64
from pathlib import Path

import branca.colormap as bcm
import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from shapely.geometry import box

BASE = Path(__file__).resolve().parent
GPKG = BASE / "data/geografia/paises_americas.gpkg"
OPS = "#004B87"
BLUE = "#0072CE"
INK = "#17324D"
BORDER = "#D9E6EE"
SEA = "#D9EEF7"
ORANGE = "#F39200"
GREY = "#D7DEE5"

CSS = """
<style>
  .block-container {max-width: 1390px; padding-top:1.05rem; padding-bottom:3rem;}
  h1,h2,h3 {color:#004B87; letter-spacing:-.02em; font-family:Arial,sans-serif;}
  h1 {font-size:1.95rem!important; font-weight:770!important;}
  h2 {font-size:1.44rem!important;}
  h3 {font-size:1.12rem!important;}
  p,span,li {font-family:Arial,sans-serif;}
  [data-testid="stSidebar"] {background:#F4F8FA;border-right:1px solid #D9E6EE;}
  [data-testid="stSidebar"] h3 {color:#004B87;}
  div[data-testid="stMetric"] {border:1px solid #D9E6EE; border-top:4px solid #0072CE;
    border-radius:13px; padding:18px 18px 13px; background:#FFFFFF;
    box-shadow:0 2px 7px rgba(10,55,82,.035);}
  div[data-testid="stMetricLabel"] {color:#5C7182;font-size:.8rem;}
  div[data-testid="stMetricValue"] {color:#004B87;font-size:1.75rem;}
  [data-testid="stHorizontalBlock"] {align-items:stretch;}
  [data-testid="stAlert"] {border-radius:9px;}
  .ops-head {background:linear-gradient(105deg,#FFFFFF 0%,#FFFFFF 64%,#EEF8FC 100%);
    border:1px solid #D9E6EE; border-radius:16px; padding:18px 22px 15px;
    box-shadow:0 3px 9px rgba(0,47,81,.04);margin:4px 0 19px;}
  .ops-head .kicker {font-size:.71rem;color:#0072CE;letter-spacing:.15em;
    font-weight:800;text-transform:uppercase;}
  .ops-head .main {font-size:1.75rem; font-weight:750;color:#004B87;
    letter-spacing:-.035em;line-height:1.16;margin:5px 0;}
  .ops-head .sub {font-size:.86rem;color:#5C7182;}
  .ops-head .logo {width:195px;max-width:100%;height:auto;}
  .ops-kicker {font-size:.72rem;font-weight:800;letter-spacing:.12em;
    color:#0072CE;margin:12px 0 0;}
  .ops-section {font-size:1.39rem;color:#004B87;font-weight:720;
    margin:0 0 7px;letter-spacing:-.02em;}
  .ops-note {font-size:.86rem;color:#546E7F;}
  .ops-divider {height:1px;background:#DEE8F0;margin:13px 0 19px;}
  .ops-chip {font-size:.71rem; border:1px solid #D9E6EE;background:#F3F9FD;
    color:#004B87; padding:5px 9px; border-radius:6px;font-weight:700;display:inline-block;}
  .ops-legend-item {display:inline-flex;align-items:center;font-size:.78rem;
    margin-right:15px;color:#17324D;}
  .ops-legend-swatch {height:11px;width:11px;border-radius:2px;display:inline-block;
    margin-right:5px;vertical-align:middle;}
  .ops-footer {border-top:1px solid #E0EBF2;padding-top:12px;color:#698091;font-size:.75rem;}
  a {color:#006EAE!important;}
</style>
"""

def apply_style():
    st.markdown(CSS,unsafe_allow_html=True)

def header():
    logo=BASE/"assets/ops_oms.png"
    image_markup=""
    if logo.exists():
        b64=base64.b64encode(logo.read_bytes()).decode("ascii")
        image_markup=f'<img class="logo" alt="OPS / OMS" src="data:image/png;base64,{b64}">'
    st.markdown(f"""
    <div class="ops-head">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:20px;">
        <div style="flex:1;min-width:0;">
          <div class="kicker">OPS / OMS · Emergencias en Salud · PHE</div>
          <div class="main">Observatorio Regional de Amenazas<br>y Vulnerabilidad Humanitaria</div>
          <div class="sub">Américas · 35 países soberanos · datos trazables y comparables por fuente</div>
        </div>
        <div style="flex-shrink:0;text-align:right;">{image_markup}</div>
      </div>
    </div>
    """,unsafe_allow_html=True)

def heading(title,idx,note=""):
    st.markdown(f'<div class="ops-kicker">{idx} / OBSERVATORIO REGIONAL</div>'
                f'<div class="ops-section">{title}</div>',unsafe_allow_html=True)
    if note:st.caption(note)

@st.cache_data(show_spinner=False)
def geography():
    if not GPKG.exists():return None
    frame=gpd.read_file(GPKG,layer="paises_americas")
    frame=frame[frame["geometry"].notna()].copy().to_crs(4326)
    frame.geometry=frame.geometry.intersection(box(-168,-62,-25,86))
    frame=frame[~frame.geometry.is_empty].copy()
    frame.geometry=frame.geometry.simplify(0.025,preserve_topology=True)
    return frame[["COUNTRY","ISO_CC","geometry"]]

def map_countries(df:pd.DataFrame, metric:str, title:str,
                  *, categorical:bool=False, height:int=520,
                  legend_title:str|None=None):
    """Mapa Folium con todos los polígonos Natural Earth (no datos en gris)."""
    base=geography()
    if base is None:
        st.warning("GeoPackage aún no está disponible en este despliegue.")
        return
    one=df.copy()
    one=one.drop_duplicates("iso3")
    metric_cols=["iso3",metric]
    if "pais" in one.columns:metric_cols.append("pais")
    merged=base.merge(one[metric_cols],left_on="ISO_CC",right_on="iso3",how="left")
    merged["mostrar_pais"]=merged["pais"].fillna(merged["COUNTRY"]) if "pais" in merged else merged["COUNTRY"]
    value=merged[metric]
    if categorical:
        merged["mostrar_valor"]=value.fillna("Sin información").astype(str)
        category_color={"Con registros":BLUE,
                        "Sin registros en catálogo":"#CAD4DC",
                        "Sin verificar":ORANGE,
                        "Excluido por QA":"#EB8D50",
                        "Sin información":"#E1E5E9"}
        colors=merged["mostrar_valor"].map(category_color).fillna("#D8E0E6")
    else:
        numeric=pd.to_numeric(value,errors="coerce")
        merged["mostrar_valor"]=numeric.map(
            lambda v:f"{v:.2f} / 10" if pd.notna(v) else "Sin información")
        colormap=bcm.LinearColormap(["#E4EFF8","#7CC4E7","#1788C8","#004B87"],
                                    vmin=0,vmax=10)
        colors=numeric.map(lambda v:colormap(v) if pd.notna(v) else "#D5DEE5")
    merged["hex_color"]=colors
    mapa=folium.Map(location=[-8.0,-81.5],zoom_start=3,tiles=None,zoom_control=True,
                    min_zoom=2,max_zoom=7,control_scale=False,
                    prefer_canvas=True,width="100%",height=height)
    mapa.get_root().html.add_child(
        folium.Element("<style>.leaflet-container{background:#D9EEF7!important}"
        ".leaflet-tooltip.ops-tooltip{background:white;color:#17324D;"
        "border:1px solid #D9E6EE;border-radius:8px;font-size:12px;"
        "font-family:Arial,sans-serif;padding:9px;}</style>"))
    feature=folium.GeoJson(
        merged.to_json(drop_id=True),
        name="Países",
        style_function=lambda x:{"fillColor":x["properties"]["hex_color"],
            "color":"#FFFFFF","weight":0.85,"fillOpacity":1},
        highlight_function=lambda x:{"color":"#004B87",
            "weight":1.8,"fillOpacity":.91},
        smooth_factor=.25,
        tooltip=folium.GeoJsonTooltip(
            fields=["mostrar_pais","mostrar_valor"],
            aliases=["País:","Dato:"],labels=True,
            sticky=True,style="font:12px Arial,sans-serif;"
        )
    )
    feature.add_to(mapa)
    if categorical:
        legend=''.join(f'<div style="display:flex;align-items:center;gap:8px;margin:3px 0">'
            f'<span style="display:inline-block;width:13px;height:11px;background:{c};border-radius:1px"></span>'
            f'<span>{k}</span></div>' for k,c in category_color.items())
        legend='<div style="position:absolute;bottom:22px;left:17px;z-index:9999;'
        legend+='background:#fff;padding:9px 13px;border-radius:9px;'
        legend+='border:1px solid #D9E6EE;box-shadow:0 3px 10px #0001;'
        legend+='font:11px Arial;color:#17324D;"><strong>Disponibilidad</strong>'+''.join(
            f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0">'
            f'<span style="background:{c};width:12px;height:10px;display:inline-block"></span>'
            f'<span>{k}</span></div>' for k,c in category_color.items())+'</div>'
        mapa.get_root().html.add_child(folium.Element(legend))
    else:
        colormap.caption=legend_title or title
        colormap.add_to(mapa)
    components.html(mapa.get_root().render(),height=height+12,scrolling=False)

def footer():
    st.markdown(
      '<div class="ops-footer">OPS/OMS · Prototipo de análisis humanitario. '
      'Cada fuente mantiene su propia cobertura, metodología y fecha de referencia. '
      'Sin clasificación oficial de prioridad operacional.</div>',
      unsafe_allow_html=True)
