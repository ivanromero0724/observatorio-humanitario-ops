"""Identidad visual compartida con COE-regional (OPS/OMS).

Basada en dashboard/visual_style.py y la interfaz de COE-regional.
No modifica indicadores ni interpretaciones del Observatorio Humanitario.
"""
from __future__ import annotations

import base64
from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parent

NAVY = "#005A8B"
CYAN = "#009BDA"
ORANGE = "#F36B32"
TEXT = "#17324D"
MUTED = "#607B8A"
BORDER = "#DFE9F1"
SURFACE = "#F7FAFC"
FONT = "'DM Sans', 'Avenir Next', 'Segoe UI', Arial, sans-serif"

STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp {
  font-family:'DM Sans','Avenir Next','Segoe UI',Arial,sans-serif!important;
}
.stApp, [data-testid="stAppViewContainer"] {
  background:#F7FAFC!important;color:#17324D!important;
}
[data-testid="stHeader"] {
  position:fixed!important;top:0!important;z-index:999990!important;
  background:#F7FAFC!important;opacity:1!important;backdrop-filter:none!important;
  border-bottom:1px solid #E1EAF1;box-shadow:0 2px 8px rgba(0,65,115,.035);
}
[data-testid="stMainBlockContainer"], .block-container {
  width:min(100%,1280px)!important;max-width:1280px!important;
  margin-left:auto!important;margin-right:auto!important;
  padding:3.25rem 1.35rem 2.6rem!important;box-sizing:border-box;
}
[data-testid="stSidebar"] {
  background:#FFFFFF!important;border-right:1px solid #E1EAF1!important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
  font-size:.82rem!important;color:#607B8A;
}
[data-testid="stSidebar"] [role="radiogroup"] label {
  border-radius:9px!important;padding:5px 7px!important;
}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
  background:#EEF7FC!important;
}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {
  font-weight:750!important;color:#005A8B!important;
}
h1,h2,h3,h4 {color:#005A8B!important;font-weight:800;letter-spacing:-.025em;}
h2{font-size:1.42rem!important} h3{font-size:1.06rem!important}
.paho-header {
  background:#FFFFFF;border:1px solid #DFE9F1;border-radius:14px;
  margin:0 0 18px;overflow:hidden;box-shadow:0 4px 18px rgba(25,75,110,.04);
}
.paho-strip {
  height:7px;
  background:linear-gradient(90deg,#005A8B 0%,#005A8B 75%,#F36B32 75%,#F36B32 100%);
}
.paho-hero {
  display:grid;grid-template-columns:minmax(0,1fr) 172px;gap:24px;
  padding:22px 26px;align-items:center;
}
.paho-eyebrow {
  font-size:.71rem;letter-spacing:.15em;font-weight:800;color:#F36B32;
}
.paho-title {
  font-size:clamp(1.45rem,2.1vw,2.10rem);font-weight:800;line-height:1.17;
  letter-spacing:-.035em;color:#005A8B;margin:7px 0;
}
.paho-desc{font-size:.85rem;line-height:1.5;color:#62798C;max-width:710px;}
.paho-brand{max-width:100%;max-height:95px;object-fit:contain;display:block;margin-left:auto;}
.obs-phase{
  font-size:.70rem!important;letter-spacing:.14em!important;
  font-weight:800!important;color:#009BDA!important;margin:10px 0 3px!important;
}
.obs-page{
  font-size:1.26rem!important;line-height:1.25!important;
  font-weight:800!important;letter-spacing:-.02em!important;
  color:#005A8B!important;margin:0 0 5px!important;
}
.obs-lead{font-size:.83rem!important;line-height:1.5!important;
  color:#607B8A!important;margin:0 0 15px!important;
}
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stVerticalBlockBorderWrapper"] > div {
  border-color:#DFE9F1!important;border-radius:12px!important;
  background:#FFFFFF!important;
}
[data-testid="stVerticalBlockBorderWrapper"] {
  box-shadow:0 2px 12px rgba(0,75,120,.035)!important;
}
.obs-card-title {
  font-size:1.02rem!important;line-height:1.25!important;
  font-weight:800!important;color:#005A8B!important;margin:0 0 6px!important;
}
.obs-card-sub {
  font-size:.78rem!important;line-height:1.42!important;
  color:#607B8A!important;margin-bottom:8px!important;min-height:30px!important;
}
.obs-card-foot {
  color:#718594!important;font-size:.69rem!important;
  border-top:1px solid #ECF1F5;padding-top:8px;margin-top:9px;
}
[data-testid="stMetric"] {
  background:#FFFFFF!important;border:1px solid #DFE9F1!important;
  border-top:3px solid #005A8B!important;border-radius:12px!important;
  padding:13px 15px 12px!important;min-height:111px!important;
  box-shadow:0 2px 12px rgba(0,75,120,.035)!important;
}
[data-testid="stMetricValue"] {
  color:#005A8B!important;font-size:1.58rem!important;
  font-weight:800!important;line-height:1.12!important;
  overflow-wrap:anywhere!important;
}
[data-testid="stMetricLabel"] {
  color:#597184!important;font-size:.75rem!important;
  font-weight:700!important;
}
[data-testid="stTabs"] [role="tablist"]{
  border-bottom:1px solid #DFE9F1!important;
  gap:10px!important;margin-bottom:12px!important;
}
[data-testid="stTabs"] button[role="tab"] {
  border-radius:0!important;color:#607B8A!important;
  font-weight:700!important;font-size:.83rem!important;
  padding:8px 13px!important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
  color:#005A8B!important;border-bottom:3px solid #009BDA!important;
}
[data-testid="stSelectbox"] label p,
[data-testid="stCheckbox"] label p,
.st-key-op_event_months [data-testid="stWidgetLabel"] p {
  color:#526F84!important;font-size:.79rem!important;font-weight:700!important;
}
[data-baseweb="select"] > div, [data-testid="stSelectbox"] [role="combobox"] {
  border-color:#DFE9F1!important;border-radius:9px!important;
  background:#FFFFFF!important;
}
div.stButton>button[kind="primary"]{
  background:#005A8B!important;border-color:#005A8B!important;
}
/* Las tarjetas ya tienen un borde: evitar una segunda caja en tablas
   de muchas filas, que permanecen interactivas. */
[class*="st-key-coe_chart_"] [data-testid="stDataFrame"] {
  border:0!important;border-radius:0!important;
  background:#FFFFFF!important;box-shadow:none!important;
}
.ops-table-wrap{
  width:100%;overflow-x:auto;overflow-y:hidden;
  background:#FFFFFF;border:0;border-radius:0;
  padding:2px 1px;scrollbar-color:#C5DAE7 transparent;
}
.ops-data-table{
  width:100%;border-collapse:separate;border-spacing:0;
  border:0;background:#FFFFFF;color:#17324D;
  font-family:'DM Sans','Avenir Next','Segoe UI',Arial,sans-serif;
  font-size:.83rem;line-height:1.35;table-layout:auto;
}
.ops-data-table thead th{
  padding:11px 12px;text-align:left;vertical-align:middle;
  background:#EFF6FA;color:#526C7F;
  font-size:.72rem;letter-spacing:.025em;font-weight:800;
  border-bottom:1px solid #DCE8F0;white-space:normal;
}
.ops-data-table tbody td{
  padding:11px 12px;vertical-align:middle;
  border-bottom:1px solid #ECF2F6;background:#FFFFFF;
  color:#17324D;white-space:normal;word-break:normal;
}
.ops-data-table tbody tr:nth-child(even) td{background:#FAFCFD;}
.ops-data-table tbody tr:hover td{background:#EAF5FB;}
.ops-data-table tbody tr:last-child td{border-bottom:0;}
.ops-data-table .ops-numeric{
  text-align:right;font-variant-numeric:tabular-nums;
  white-space:nowrap;
}
.ops-data-table a{color:#0068A9;text-decoration:none;font-weight:700;}
.ops-data-table a:hover{text-decoration:underline;}
@media(max-width:700px){
 .ops-data-table{font-size:.77rem;}
 .ops-data-table thead th,.ops-data-table tbody td{padding:9px 10px;}
}
[data-testid="stExpander"] {
  border:1px solid #DFE9F1!important;border-radius:10px!important;
  background:#FFFFFF!important;
}
[data-testid="stPlotlyChart"]{width:100%!important;}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stPlotlyChart"] {
  border:0!important;border-radius:0!important;
}
[data-testid="stAlert"] {border-radius:10px!important;}
[data-testid="stHorizontalBlock"]{align-items:stretch!important;}
@media(max-width:850px){
  .paho-hero{grid-template-columns:minmax(0,1fr) 95px;padding:18px 16px;gap:10px;}
  .paho-title{font-size:1.35rem}
  .paho-brand{max-height:65px}
  .obs-page{font-size:1.18rem!important}
}

/* El COE separa títulos del área gráfica y evita las tarjetas enormes. */
.obs-card-title {
  font-size:.97rem!important;font-weight:800!important;color:#005A8B!important;
  margin:12px 1px 3px!important;line-height:1.24!important;min-height:0!important;
}
.obs-card-sub {
  font-size:.77rem!important;color:#607B8A!important;
  margin:0 1px 8px!important;min-height:0!important;line-height:1.38!important;
}
.obs-card-source {
  color:#718594!important;font-size:.70rem!important;line-height:1.25!important;
  margin:5px 1px 17px!important;border:0!important;padding:0!important;
}
/* Un solo marco, blanco uniforme, alrededor del área gráfica; no otro recuadro interior. */
div[class*="st-key-coe_chart_"] [data-testid="stVerticalBlockBorderWrapper"],
div[class*="st-key-coe_chart_"] [data-testid="stVerticalBlockBorderWrapper"] > div {
  background:#FFFFFF!important;border-color:#DFE9F1!important;
  border-radius:12px!important;
}
div[class*="st-key-coe_chart_"] [data-testid="stPlotlyChart"] {
  background:#FFFFFF!important;border:0!important;
  box-shadow:none!important;border-radius:0!important;
}
div[class*="st-key-coe_chart_"] .js-plotly-plot,
div[class*="st-key-coe_chart_"] .plot-container {
  background:#FFFFFF!important;
}
div[class*="st-key-coe_chart_"] [data-testid="stVerticalBlock"] {
  gap:.25rem!important;
}


/* Panel blanco de extremo a extremo: contenido, relleno, lienzo Plotly y marco. */
[class*="st-key-coe_chart_"] {
  background:#FFFFFF!important;border-radius:12px!important;
}
[class*="st-key-coe_chart_"] [data-testid="stVerticalBlock"],
[class*="st-key-coe_chart_"] [data-testid="stVerticalBlockBorderWrapper"],
[class*="st-key-coe_chart_"] [data-testid="stVerticalBlockBorderWrapper"] > div,
[class*="st-key-coe_chart_"] [data-testid="stElementContainer"],
[class*="st-key-coe_chart_"] [data-testid="stPlotlyChart"],
[class*="st-key-coe_chart_"] [data-testid="stDataFrame"] {
  background:#FFFFFF!important;
}
[class*="st-key-coe_chart_"] .js-plotly-plot,
[class*="st-key-coe_chart_"] .svg-container,
[class*="st-key-coe_chart_"] .plot-container {
  background:#FFFFFF!important;
}
[class*="st-key-coe_chart_"] [data-testid="stVerticalBlockBorderWrapper"]{
  box-shadow:none!important;
}
/* Centrar VERTICALMENTE gráficos dentro de las tarjetas con altura fija.
   No aplicar a tarjetas con tablas, métricas ni filtros: allí se prioriza
   lectura natural y controles accesibles. */
[class*="st-key-coe_chart_"]:has([data-testid="stPlotlyChart"]):not(:has([data-testid="stDataFrame"])):not(:has([data-testid="stMetric"])):not(:has([data-testid="stSelectbox"])) [data-testid="stVerticalBlockBorderWrapper"] {
  display:flex!important;
  flex-direction:column!important;
}
[class*="st-key-coe_chart_"]:has([data-testid="stPlotlyChart"]):not(:has([data-testid="stDataFrame"])):not(:has([data-testid="stMetric"])):not(:has([data-testid="stSelectbox"])) [data-testid="stVerticalBlockBorderWrapper"] > div {
  flex:1 1 auto!important;
  display:flex!important;
  flex-direction:column!important;
}
[class*="st-key-coe_chart_"]:has([data-testid="stPlotlyChart"]):not(:has([data-testid="stDataFrame"])):not(:has([data-testid="stMetric"])):not(:has([data-testid="stSelectbox"])) [data-testid="stVerticalBlock"] {
  flex:1 1 auto!important;
  justify-content:center!important;
}
/* Evitar desplazamientos del Plotly respecto al centro del área disponible. */
[class*="st-key-coe_chart_"] [data-testid="stPlotlyChart"] {
  margin-top:auto!important;
  margin-bottom:auto!important;
}

/* Ajuste óptico medido en Chromium: el lienzo Plotly queda 11px más
   cerca del borde superior con la disposición nativa de Streamlit.
   Desplazar SOLO paneles de gráfico puro (sin filtros, tablas ni métricas)
   equilibra los márgenes superior e inferior de la tarjeta. */
[class*="st-key-coe_chart_"]:has([data-testid="stPlotlyChart"]):not(:has([data-testid="stDataFrame"])):not(:has([data-testid="stMetric"])):not(:has([data-testid="stSelectbox"])):not(:has([data-testid="stCaptionContainer"])) [data-testid="stPlotlyChart"] {
  position:relative!important;
  top:11px!important;
}

/* Indicadores superiores unidos: misma banda visual de Clúster Salud OPS. */
.ops-metric-strip{
  --ops-items:4;
  display:grid;
  grid-template-columns:repeat(var(--ops-items),minmax(0,1fr));
  background:#FFFFFF;
  border:1px solid #D8E5EE;
  border-radius:18px;
  box-shadow:0 4px 13px rgba(14,63,96,.045);
  overflow:hidden;
  margin:12px 0 15px;
}
.ops-strip-item{
  padding:14px 17px 15px;
  min-width:0;
  background:#FFFFFF;
}
.ops-strip-item + .ops-strip-item{
  border-left:1px solid #DFE9F1;
}
.ops-strip-value{
  color:#0068A9;
  font-size:clamp(1.3rem,1.9vw,1.87rem);
  font-weight:800;
  line-height:1.12;
  letter-spacing:-.025em;
  white-space:nowrap;
}
.ops-strip-label{
  font-size:.70rem;
  font-weight:800;
  color:#536A7C;
  letter-spacing:.045em;
  line-height:1.2;
  margin-top:8px;
  overflow-wrap:anywhere;
}
.ops-strip-desc{
  font-size:.70rem;
  font-weight:500;
  color:#72889A;
  margin-top:5px;
  line-height:1.3;
  overflow-wrap:anywhere;
}
@media(max-width:900px){
 .ops-metric-strip{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;}
 .ops-strip-item{flex:1 0 145px;scroll-snap-align:start;}
}

/* Selector principal de subtema: compacto, horizontal y con identidad COE. */
[data-testid="stSegmentedControl"] {
  background:#FFFFFF!important;border:1px solid #DFE9F1!important;
  padding:3px 4px!important;border-radius:10px!important;
  margin:3px 0 14px!important;
  display:inline-flex!important;width:fit-content!important;
  max-width:100%!important;justify-content:flex-start!important;
}
[data-testid="stSegmentedControl"] button {
  font-size:.83rem!important;font-weight:700!important;
  border-radius:7px!important;
  flex:0 0 auto!important;
}
[data-testid="stSegmentedControl"] button[aria-checked="true"],
[data-testid="stSegmentedControl"] button[aria-pressed="true"]{
  background:#EAF3F9!important;color:#005A8B!important;
}
/* Selector deslizante: cinco posiciones discretas (1, 3, 6, 9 y 12 meses). */
.st-key-op_event_months [data-testid="stSlider"] {
  width:100%!important;
  max-width:100%!important;
}
.st-key-op_event_months [data-testid="stTickBar"] {
  color:#607B8A!important;
  font-size:.78rem!important;
}
.st-key-op_event_months [data-baseweb="slider"] {
  margin-top:5px!important;
  margin-bottom:5px!important;
}
.st-key-op_event_months [data-baseweb="slider"] [role="slider"] {
  border-color:#009BDA!important;
  box-shadow:0 1px 5px rgba(0,90,139,.16)!important;
}
</style>
"""

def header():
    logo = ROOT / "assets/ops_oms.png"
    image = ""
    if logo.is_file():
        payload = base64.b64encode(logo.read_bytes()).decode("ascii")
        image = f'<img class="paho-brand" alt="OPS/OMS" src="data:image/png;base64,{payload}">'
    st.markdown(
        '<div class="paho-header"><div class="paho-strip"></div><div class="paho-hero">'
        '<div><div class="paho-eyebrow">OPS / OMS · EMERGENCIAS EN SALUD · AMÉRICAS</div>'
        '<div class="paho-title">Observatorio Regional de Amenazas y Vulnerabilidad Humanitaria</div>'
        '<div class="paho-desc">Violencia y conflicto · movilidad humana · vulnerabilidad '
        'y respuesta humanitaria. Datos verificables de fuentes regionales.</div></div>'
        + image + '</div></div>', unsafe_allow_html=True
    )
