"""Observatorio OPS/OMS · organización funcional definida por Laura.

Cuatro vistas de datos integrados: amenazas, movilidad, vulnerabilidad/respuesta
 y fichas nacionales. Sin categorías vacías ni niveles OPS no validados.
"""
from __future__ import annotations
import streamlit as st

from observatorio_v2 import load_all
from observatorio_v5 import STYLES, UX_CSS, header, quality_footer
from paginas_operativas import amenazas_page, movilidad_page, vulnerabilidad_page, perfil_page

PAGES=[
    "Amenazas y eventos",
    "Movilidad y necesidades",
    "Vulnerabilidad y respuesta",
    "Perfiles por país",
]

LAURA_CSS="""
<style>
/* Identidad visual común: azul PAHO, naranja, fondo muy claro, bordes.
   Usar paneles de altura idéntica en columnas emparejadas. */
.obs-hero{margin-bottom:15px!important}
.obs-page{font-weight:770!important}
[data-testid="stMetricValue"]{color:#004B87!important}
[data-testid="stVerticalBlockBorderWrapper"]{
 border:1px solid #D7E2EA!important;border-radius:12px!important;
 background:#FFFFFF!important;
}
[data-testid="stSidebar"]{background:#F8FBFD!important}
</style>
"""

def main():
    st.set_page_config(page_title="Observatorio Humanitario · OPS/OMS",
       page_icon="🌎",layout="wide",initial_sidebar_state="expanded")
    st.markdown(STYLES+UX_CSS+LAURA_CSS,unsafe_allow_html=True)
    D=load_all()
    countries=D["countries"]
    if countries.empty:
        st.error("El catálogo de países está vacío o no disponible.")
        st.stop()
    names=countries.set_index("iso3")["pais"].to_dict()
    with st.sidebar:
        st.markdown("### OPS / OMS")
        st.caption("Programa de Emergencias en Salud · PHE")
        page=st.radio("Secciones del Observatorio",PAGES,key="nav")
        st.divider()
        region=st.selectbox("Subregión",
            ["Todas las Américas"]+
            sorted(countries["subregion"].dropna().unique()),key="region")
        regional=(countries if region=="Todas las Américas" else
             countries[countries["subregion"]==region])
        opts=sorted(regional["iso3"],key=lambda code:names.get(code,code))
        scope=st.selectbox("Ámbito",["Todos los países"]+opts,
               format_func=lambda code:names.get(code,code),key="scope")
        selected=set(opts) if scope=="Todos los países" else {scope}
        st.divider()
        st.caption("Prototipo de monitoreo humanitario. "
                   "Criterios y niveles de seguimiento sujetos "
                   "a validación de Laura y OPS/PHE.")
    header()
    if page==PAGES[0]:
        amenazas_page(D,selected,names)
    elif page==PAGES[1]:
        movilidad_page(D,selected,names)
    elif page==PAGES[2]:
        vulnerabilidad_page(D,selected,names)
    else:
        perfil_page(D,selected,names)
    quality_footer(D,selected)
    st.caption("Fuentes: OCHA HAPI/ACLED, ACAPS, ACNUR, OIM DTM, "
      "OPS y ReliefWeb. Sin asignación automática de riesgo OPS. "
      "No implica alerta institucional ni reemplaza validación técnica.")

if __name__=="__main__":
    main()
