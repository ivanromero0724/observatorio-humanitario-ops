"""Páginas centradas en la taxonomía inicial de Laura (OPS/PHE).

Ninguna ausencia de dato se convierte en cero y no se asignan niveles de
seguimiento OPS sin ficha metodológica validada. El catálogo es explícito
sobre qué subtipo corresponde realmente a un campo de cada proveedor.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from observatorio_v2 import filtered, valid_needs, latest_ops, OPS_LABELS
from observatorio_v4 import (
    card, plot, table, info_missing, fmt, crisis_table,
)
from observatorio_v5 import (
    title, pa_map, events_by_country, common_last, list_months,
    oim_scope, crisis_core, CARD_H,
)
from graficos import rank_bars, trend, strip_countries

BLUE="#0072CE"
ORANGE="#F39200"
PANEL=565

# Los nombres provienen del planteamiento de Laura. Los indicadores fuente
# se declaran PROXY si no equivalen exactamente al subtipo solicitado.
TAXONOMY=[
    {"grupo":"Violencia","tipo":"Acciones armadas",
     "fuente":"OCHA HAPI / ACLED","estado":"Indicador aproximado",
     "dato":"political_violence",
     "nota":"Violencia política agregada; no identifica exclusivamente acciones armadas."},
    {"grupo":"Violencia","tipo":"Ataques a objetivos y población civil",
     "fuente":"OCHA HAPI / ACLED","estado":"Indicador parcial",
     "dato":"civilian_targeting",
     "nota":"Ataques contra civiles. No hay desglose regional validado de todos los tipos de objetivos."},
    {"grupo":"Migración y desplazamiento","tipo":"Refugiados y solicitantes de asilo",
     "fuente":"ACNUR vía HAPI","estado":"Población disponible",
     "dato":"acnur",
     "nota":"Existencias anuales por acogida, origen y categoría; no nuevos desplazamientos."},
    {"grupo":"Migración y desplazamiento","tipo":"Desplazamiento interno",
     "fuente":"OIM DTM","estado":"Datos por operación",
     "dato":"dtm",
     "nota":"Rondas por operación y causa; cobertura parcial, sin cifra nacional comparable."},
    {"grupo":"Violencia generalizada y acceso","tipo":"Tensiones entre países",
     "fuente":"ReliefWeb / fuentes de país","estado":"Pendiente de armonización",
     "dato":None,
     "nota":"No hay serie regional validada que cuantifique tensiones internacionales."},
    {"grupo":"Violencia generalizada y acceso","tipo":"Restricciones a la movilidad y acceso humanitario",
     "fuente":"ACAPS Humanitarian Access","estado":"Indicador contextual",
     "dato":"access",
     "nota":"Índice de acceso por crisis, no un conteo de restricciones de movimiento."},
    {"grupo":"Contexto político frágil","tipo":"Fragilidad y crisis político-económicas",
     "fuente":"ACAPS / fuentes especializadas","estado":"Cobertura parcial",
     "dato":"political",
     "nota":"Descriptores de crisis ACAPS, no índice uniforme de fragilidad política."},
    {"grupo":"Minería ilegal","tipo":"Extracción de minería ilegal",
     "fuente":"Por validar con Laura","estado":"Sin serie integrada",
     "dato":None,
     "nota":"Requiere definición de actividad, territorio y fuente especializada."},
    {"grupo":"Crimen organizado","tipo":"Crimen organizado",
     "fuente":"Por validar con Laura","estado":"Sin serie integrada",
     "dato":None,
     "nota":"Los eventos HAPI no representan el universo de crimen organizado."},
    {"grupo":"Mercados ilícitos y cultivos","tipo":"Mercados de drogas ilícitas y cultivos",
     "fuente":"Por validar con Laura","estado":"Sin serie integrada",
     "dato":None,
     "nota":"No hay series integradas de cultivos, producción y mercados comparables."},
    {"grupo":"Delincuencia transnacional","tipo":"Delincuencia organizada transnacional",
     "fuente":"Por validar con Laura","estado":"Sin serie integrada",
     "dato":None,
     "nota":"No puede inferirse a partir del conteo agregado de violencia política."},
]

IMPACT_ROWS=[
    ("Personas afectadas directamente","Sin serie regional comparable",
     "No equiparar eventos, refugiados, PiN o personas desplazadas con víctimas directas del evento."),
    ("Personas en necesidad de asistencia (PiN)","Datos por país y año",
     "OCHA HAPI. Solo total intersectorial inequívoco; cobertura limitada."),
    ("Personas desplazadas / refugiadas","Datos parciales con metodología propia",
     "OIM DTM por ronda; ACNUR por población, acogida, origen y año."),
    ("Establecimientos de salud impactados","Pendiente de fuente validada",
     "OMS SSA, oficinas de país y reportes oficiales; no imputar cero."),
    ("Personal de salud afectado","Pendiente de fuente validada",
     "OMS SSA: personal lesionado, agredido o fallecido, según disponibilidad autorizada."),
    ("Agua y saneamiento afectados","Pendiente de verificación",
     "SitRep/OCHA/OPS: lugar, tipo de interrupción, fecha y fuente."),
    ("Electricidad afectada","Pendiente de verificación",
     "Informes de situación con territorio y duración cuando estén disponibles."),
    ("Gas afectado","Pendiente de verificación",
     "No existe integración comparable en esta versión."),
    ("Telecomunicaciones afectadas","Pendiente de verificación",
     "No existe integración comparable en esta versión."),
]

VULN={
    "Económico":["GINI"],
    "Educación":["Escolaridad"],
    "Ambiental":["Calidad del aire"],
    "Social":["GINI","Pobreza multidimensional"],
    "Capacidad del sistema de salud":["Médicos","Enfermería","Camas hospitalarias"],
    "Morbimortalidad":["Mortalidad por homicidio"],
    "Cobertura de vacunación":["DTP3","SRP1"],
    "Demografía":["Población por edad y sexo"],
}

def _country_names(D):
    return D["countries"].set_index("iso3")["pais"].to_dict()

def _event_series(D,selected,category,months):
    e=filtered(D["conflict"],selected)
    if e.empty:return e,None
    cut=common_last(D,category)
    if cut is None:return e.iloc[0:0],None
    e=e[e["tipo_evento"].eq(category)&
        e["fecha"].isin(list_months(cut,months))].copy()
    return e,cut

def _mapped_events(D,selected,category,months):
    frame,cut=events_by_country(D,selected,category,months)
    frame=frame.merge(D["countries"][["iso3","pais"]],
                      on="iso3",how="left")
    frame["valor"]=frame["eventos"]
    return frame,cut

def _crisis_access(D,selected):
    c=crisis_core(D,selected)
    if c.empty:return c
    return c

def _acnur_stock(D,selected,group):
    df=filtered(D["acnur"],selected,"asilo_iso3")
    if df.empty:return pd.DataFrame(),None
    df=df[df["grupo_poblacion"].eq(group)].copy()
    if df.empty:return df,None
    # Un año compartido entre países: nunca sumar periodos incompatibles.
    df["anio_num"]=pd.to_numeric(df["anio"],errors="coerce")
    year=df["anio_num"].max()
    df=df[df["anio_num"].eq(year)].copy()
    out=df.groupby("asilo_iso3",as_index=False).agg(
        valor=("personas",lambda x:x.sum(min_count=1)))
    out=out.rename(columns={"asilo_iso3":"iso3"})
    out=out.merge(D["countries"][["iso3","pais"]],
                  on="iso3",how="left")
    return out,int(year) if pd.notna(year) else None

def _no_level():
    st.markdown("**Nivel de seguimiento humanitario OPS**")
    st.info("**Crítico · Alto · Elevado · Moderado:** categorías propuestas "
            "por Laura, **sin país asignado**. Deben acordarse indicadores, "
            "periodos, umbrales, revisión experta y manejo de datos faltantes. "
            "ACAPS Severity e INFORM Risk no son una clasificación OPS.")
    with st.expander("Ver criterios necesarios antes de utilizar niveles"):
        st.markdown("Taxonomía validada; fuente y unidad de cada indicador; "
                    "periodicidad y ventana temporal; magnitud y variación; "
                    "número y tipo de personas afectadas; impacto en salud; "
                    "geografía y precisión; ponderaciones, umbrales, ausencia "
                    "de datos y validación editorial. **No existe un algoritmo "
                    "institucional aprobado para asignarlos.**")

def _event_visuals(D,selected,category,months):
    names=_country_names(D)
    mapped,cut=_mapped_events(D,selected,category,months)
    events,cut=_event_series(D,selected,category,months)
    l,r=st.columns(2,gap="medium")
    with l:
        with card("Distribución geográfica de eventos",
                  "Mapa nacional, no localización puntual de incidentes. "
                  "Países sin los meses requeridos aparecen sin datos.",
                  "OCHA HAPI / ACLED · agregado país–mes",height=PANEL):
            pa_map(mapped,"events",f"Eventos · {months} meses",height=343)
            st.caption(f"Georreferenciación: país ISO3. "
                       f"Último mes de la fuente: {cut.strftime('%Y-%m') if cut is not None else '—'}. "
                       "Sin coordenadas verificadas de hechos individuales.")
    with r:
        with card("Comparación y gravedad documentada",
                  f"{months} meses completos por país; una categoría ACLED "
                  "por vez, sin sumar grupos que se superponen.",
                  "OCHA HAPI / ACLED",height=PANEL):
            good=mapped.dropna(subset=["eventos"]).copy()
            if good.empty:info_missing("eventos comparables")
            else:
                plot(rank_bars(good,label="pais",value="eventos",
                     formats=".0f",limit=11,units="Eventos"),height=336)
                st.caption(f"Países con ventana completa: {len(good)}/{len(selected)}. "
                           "La magnitud no es una categoría de riesgo OPS.")
    with card("Evolución y fallecimientos reportados",
              "Los fallecimientos asociados a registros de eventos no equivalen "
              "al número total de personas afectadas.",
              "OCHA HAPI / ACLED"):
        if events.empty:info_missing("serie de eventos")
        else:
            left,right=st.columns([1.3,.7])
            with left:
                ts=events.groupby("fecha",as_index=False).agg(
                    eventos=("eventos","sum"))
                plot(trend(ts,x="fecha",y="eventos",
                     units="Eventos registrados"),height=275)
            with right:
                death=pd.to_numeric(events["muertes_reportadas"],errors="coerce")
                st.metric("Muertes reportadas (periodo)",
                    fmt(death.sum()) if death.notna().any() else "Sin dato")
                st.caption("Dato de la categoría seleccionada; hay solapamientos "
                           "entre categorías y posibles revisiones retrospectivas.")
            with st.expander("Ver eventos por país y mes"):
                view=events.groupby(["pais","periodo"],as_index=False).agg(
                    eventos=("eventos","sum"),
                    muertes_reportadas=("muertes_reportadas",
                       lambda x:x.sum(min_count=1)))
                table(view,height=280,columns=["pais","periodo","eventos",
                    "muertes_reportadas"],labels={"pais":"País","periodo":"Mes",
                    "eventos":"Eventos","muertes_reportadas":"Muertes reportadas"})

def _migration_visual(D,selected,type_code):
    if type_code=="acnur":
        options={"REF":"Personas refugiadas","ASY":"Solicitantes de asilo"}
        group=st.selectbox("Grupo de población",list(options),
                           format_func=lambda x:options[x],
                           key="laura_acnur_group")
        mapped,year=_acnur_stock(D,selected,group)
        if mapped.empty:info_missing("ACNUR en el ámbito")
        else:
            l,r=st.columns(2,gap="medium")
            with l:
                with card("País de acogida · personas registradas",
                          "Mapa nacional de población de acogida; no flujos.",
                          f"ACNUR/HAPI · {year}",height=PANEL):
                    pa_map(mapped,"events",
                        f"{options[group]} · {year}",height=343)
                    st.caption("País de acogida. Se evita mezclar personas "
                               "refugiadas y solicitantes de asilo.")
            with r:
                with card("Países con población registrada",
                          "Comparación del mismo año y grupo poblacional.",
                          f"ACNUR/HAPI · {year}",height=PANEL):
                    plot(rank_bars(mapped,label="pais",value="valor",
                        limit=11,formats=".0f",units="Personas"),height=341)
                    st.caption("Existencias de población; no desplazamientos "
                               "ocurridos durante ese año.")
    else:
        dtm=oim_scope(filtered(D["dtm"],selected))
        with card("Operaciones de desplazamiento interno de OIM",
                  "Conserva operación, causa, ronda y periodo; no sumar "
                  "poblaciones entre operaciones ni interpretar causa no informada.",
                  "OIM DTM Baseline"):
            if dtm.empty:info_missing("operaciones OIM DTM")
            else:
                data=dtm[["pais","operacion","causa_desplazamiento",
                          "ronda","fecha_reporte","personas_idp_reportadas"]].copy()
                table(data,height=355,labels={"pais":"País",
                     "operacion":"Operación","causa_desplazamiento":"Causa",
                     "ronda":"Ronda","fecha_reporte":"Corte",
                     "personas_idp_reportadas":"Personas reportadas"})
                st.caption("Se excluyen del módulo inicial registros clasificados "
                           "como desastres naturales, pero no se borran del CSV.")

def _access_visual(D,selected,political=False):
    crises=crisis_core(D,selected)
    if political and not crises.empty:
        crises=crises[crises["drivers"].fillna("").str.contains(
            r"political|economic",case=False,regex=True)].copy()
    if crises.empty:info_missing("contextos ACAPS")
    else:
        with card("Contextos evaluados por ACAPS",
                 "Puntuación de gravedad de crisis; no índice propio de fragilidad "
                 "ni clasificación institucional OPS.",
                 "ACAPS INFORM Severity + Humanitarian Access"):
            table(crises,height=320,
                  columns=["pais","crisis","drivers","puntuacion","acceso"],
                  labels={"pais":"País","crisis":"Situación",
                          "drivers":"Descriptores","puntuacion":"Severidad / 10",
                          "acceso":"Acceso / 5"})
            st.caption("La evaluación ACAPS se conserva por crisis; países "
                       "sin evaluación no reciben puntuación cero.")

def amenazas_page(D,selected,names,months):
    title("02 / AMENAZAS · TAXONOMÍA DE LAURA",
          "Amenazas y eventos humanitarios",
          "Primera categoría del análisis: qué ocurrió, dónde, cuándo "
          "y qué evidencia existe sobre su impacto.")
    st.caption("Las amenazas incluyen violencia, migración, tensiones, "
               "fragilidad política, minería ilegal, crimen y mercados ilícitos. "
               "No todos los subtipos cuentan aún con una serie homologada.")
    col1,col2=st.columns([1,1],gap="medium")
    with col1:
        grupos=list(dict.fromkeys(x["grupo"] for x in TAXONOMY))
        grupo=st.selectbox("Tipo de amenaza",grupos,
                           key="laura_grupo_amenaza")
    with col2:
        candidates=[x for x in TAXONOMY if x["grupo"]==grupo]
        tipo=st.selectbox("Subtipo de evento o condición",
            [x["tipo"] for x in candidates],key="laura_subtipo")
    entry=next(x for x in candidates if x["tipo"]==tipo)
    st.markdown(f"**Fuente:** {entry['fuente']} · **Disponibilidad:** "
                f"{entry['estado']}")
    st.caption(entry["nota"])
    _no_level()
    code=entry["dato"]
    if code in ("political_violence","civilian_targeting"):
        _event_visuals(D,selected,code,months)
    elif code in ("acnur","dtm"):
        _migration_visual(D,selected,code)
    elif code in ("access","political"):
        _access_visual(D,selected,political=code=="political")
    else:
        with card("Georreferenciación y magnitud pendientes",
                  "Sin serie nacional comparable para este subtipo. "
                  "No se dibuja un mapa coloreado ni se asigna riesgo.",
                  "Pendiente de fuente validada con Laura"):
            st.info("Este subtipo está incorporado a la **taxonomía**, "
                    "pero falta seleccionar una fuente autorizada que "
                    "permita medir eventos, territorio, fecha y personas "
                    "afectadas con definiciones reproducibles.")
            docs=filtered(D["reports"],selected)
            if not docs.empty:
                st.caption("ReliefWeb dispone de documentos por país que pueden "
                           "servir de evidencia cualitativa, pero no constituyen "
                           "un indicador homologado de este subtipo.")
    with st.expander("Ver taxonomía completa y estado de los indicadores"):
        table(pd.DataFrame(TAXONOMY)[["grupo","tipo","estado","fuente","nota"]]
              .rename(columns={"grupo":"Familia","tipo":"Tipo o subtipo",
               "estado":"Estado del indicador","fuente":"Fuente",
               "nota":"Precaución"}),height=400)
    with st.expander("Personas afectadas, servicios y establecimientos de salud"):
        st.caption("El evento, los daños y las personas afectadas son dimensiones "
                   "diferentes. Sus números no se imputan unos a partir de otros.")
        table(pd.DataFrame(IMPACT_ROWS,
             columns=["Indicador","Disponibilidad","Interpretación"]),
             height=330)
        st.caption("Los indicadores disponibles con fecha y fuente están en "
                   "la página «Impacto humanitario y salud».")

def _pin_latest(D,selected):
    n=valid_needs(filtered(D["needs"],selected))
    if n.empty:return pd.DataFrame()
    n=n.copy()
    n["Año"]=n["reference_period_start"].astype(str).str[:4]
    n=n[~n.duplicated(["iso3","Año"],keep=False)]
    return n.sort_values("Año").drop_duplicates("iso3",keep="last")

def impacto_page(D,selected,names):
    title("04 / IMPACTO HUMANITARIO Y EN SALUD",
          "Personas y servicios potencialmente afectados",
          "Mostrar únicamente daños y necesidades documentados; "
          "mantener visible la información que todavía falta.")
    t1,t2,t3=st.tabs(["Personas afectadas / en necesidad",
                     "Establecimientos y personal de salud",
                     "Servicios esenciales"])
    with t1:
        pin=_pin_latest(D,selected)
        l,r=st.columns(2,gap="medium")
        with l:
            with card("Personas en necesidad de asistencia (PiN)",
                      "Estimaciones nacionales intersectoriales, "
                      "sin sumar sectores y con años distintos.",
                      "OCHA HAPI · Humanitarian Needs",height=PANEL):
                if pin.empty:info_missing("PiN intersectorial comparable")
                else:
                    pin=pin.copy()
                    pin["pais"]=pin["iso3"].map(names)
                    plot(strip_countries(pin,name="pais",val="population",
                        year="Año",max_items=14,units="Personas"),height=340)
                    st.caption("PiN no significa personas impactadas "
                               "directamente por un incidente.")
        with r:
            with card("Población en movimiento",
                      "Refugiados y solicitantes de asilo por separado; "
                      "existencias, no nuevos flujos.",
                      "ACNUR / HAPI",height=PANEL):
                opt={"REF":"Personas refugiadas",
                     "ASY":"Solicitantes de asilo"}
                group=st.selectbox("Grupo",list(opt),
                      format_func=lambda k:opt[k],key="impact_group")
                df,year=_acnur_stock(D,selected,group)
                if df.empty:info_missing("ACNUR")
                else:
                    plot(rank_bars(df,label="pais",value="valor",
                        limit=11,formats=".0f",
                        units="Personas registradas"),height=312)
                    st.caption(f"País de acogida; año {year}. "
                               "Categorías ACNUR no aditivas.")
        st.caption("El desplazamiento interno OIM se visualiza por operación "
                   "en la página de Amenazas. No se suma con PiN o ACNUR.")
    with t2:
        col1,col2=st.columns(2,gap="medium")
        for col,head,expl in [
            (col1,"Establecimientos de salud impactados",
             "Número de instalaciones atacadas, dañadas o inoperativas."),
            (col2,"Personal de salud afectado",
             "Personal lesionado, fallecido, agredido o impedido de trabajar.")]:
            with col:
                with card(head,"La información no puede inferirse del número "
                          "de eventos violentos ni de homicidios.",
                          "OMS SSA / oficinas de país · integración pendiente",
                          height=400):
                    st.metric("Registros regionales verificados","Sin datos")
                    st.info("Indicador propuesto por Laura. Requiere fuente "
                            "validada, fecha, definición de afectación y "
                            "cobertura geográfica. No se interpreta como cero.")
                    st.caption(expl)
        with st.expander("Mortalidad y morbilidad: contexto disponible"):
            _ops_context(D,selected,"Mortalidad por homicidio",
                         "Mortalidad por homicidios (OPS)")
            st.caption("Es un indicador contextual poblacional; no corresponde "
                       "a fallecidos o lesionados en ataques a la salud.")
    with t3:
        data=[
         ("Agua y saneamiento","Sin serie regional integrada",
          "Corte, localidad, personas afectadas y reporte OCHA/OPS"),
         ("Electricidad","Sin serie regional integrada",
          "Interrupción, duración y establecimientos afectados"),
         ("Gas","Sin serie regional integrada",
          "Tipo de interrupción y lugar"),
         ("Telecomunicaciones","Sin serie regional integrada",
          "Red afectada, periodo y población usuaria"),
        ]
        with card("Servicios esenciales afectados",
                  "Indicadores propuestos por Laura que requieren "
                  "reportes de situación verificables.",
                  "OCHA SitRep / oficinas OPS · aún no integrado"):
            table(pd.DataFrame(data,
                columns=["Servicio","Estado","Información mínima requerida"]),
                height=330)
            st.info("Estos servicios no se contabilizan como afectados "
                    "sin fuente directa. No se asignan cifras ni ceros.")
    with st.expander("Matriz completa de impacto y estado de datos"):
        table(pd.DataFrame(IMPACT_ROWS,
            columns=["Indicador","Disponibilidad","Interpretación"]),
            height=345)

def _ops_context(D,selected,ind,title_text):
    vals=filtered(D["ops"],selected)
    if vals.empty or ind not in set(vals["indicador"]):
        info_missing(title_text)
        return
    ys=latest_ops(vals,ind)
    if ys.empty:
        info_missing(title_text)
        return
    ys=ys.copy()
    ys["Año"]=ys["periodo"].astype(int)
    plot(strip_countries(ys,name="pais",val="valor",year="Año",
        max_items=20,units=OPS_LABELS.get(ind,ind)),height=325)
    st.caption("La fecha puede diferir entre países. "
               "Indicador de contexto, no evento actual.")

def vulnerabilidad_page(D,selected,names):
    title("03 / NIVEL DE VULNERABILIDAD",
          "Condiciones que pueden agravar una situación humanitaria",
          "Separar dimensiones económicas, educativas, ambientales, sociales, "
          "capacidad del sistema de salud, morbimortalidad, vacunación y demografía.")
    dim=st.selectbox("Dimensión de vulnerabilidad",list(VULN),
                     key="laura_dimension")
    opts=VULN[dim]
    ind=st.selectbox("Indicador",opts,
        format_func=lambda k:OPS_LABELS.get(k,k),
        key="laura_vuln_ind")
    l,r=st.columns([1.15,.85],gap="medium")
    with l:
        with card("Indicador territorial y año de referencia",
                  "Se muestra el valor original sin convertirlo en "
                  "un puntaje de vulnerabilidad OPS.",
                  "OPS Indicadores Básicos / HAPI MPI",height=PANEL):
            if ind=="Calidad del aire":
                st.info("**Calidad del aire:** Laura la incluye en contexto "
                        "ambiental, pero todavía no hay una serie regional "
                        "armonizada (contaminante, unidad, año y cobertura) "
                        "integrada en este repositorio.")
                st.caption("No sustituirla por valores inventados. "
                           "La integración requerirá PM2.5 u otro indicador "
                           "y un protocolo de comparabilidad.")
            elif ind=="Población por edad y sexo":
                st.info("**Demografía:** no existe aún un denominador "
                        "regional homogéneo por edad, sexo, año y país "
                        "integrado. Debe verificarse la fuente y la licencia.")
            elif ind=="Pobreza multidimensional":
                mpi=filtered(D["mpi"],selected)
                if mpi.empty:info_missing("pobreza multidimensional")
                else:
                    mpi=mpi.copy()
                    mpi["Año"]=mpi["reference_period_start"].astype(str).str[:4]
                    mpi=mpi.sort_values("Año").drop_duplicates("iso3",keep="last")
                    plot(strip_countries(mpi,name="pais",
                        val="headcount_ratio",year="Año",
                        max_items=20,units="Incidencia MPI (%)"),height=329)
                    st.caption("Fuente OPHI vía HAPI. No equivale al índice "
                               "de Gini; los años son específicos del proveedor.")
            else:_ops_context(D,selected,ind,OPS_LABELS.get(ind,ind))
    with r:
        with card("Cómo interpretar esta dimensión",
                  "Vulnerabilidad contextual, distinta del tipo de amenaza "
                  "y del número de personas impactadas.",
                  "Planteamiento Laura / propuesta OPS",height=PANEL):
            for desc in {
                "Económico":"Pobreza y desigualdad pueden afectar la capacidad "
                           "de los hogares para enfrentar emergencias.",
                "Educación":"La escolaridad es un factor social contextual; "
                            "no representa por sí sola riesgo humanitario.",
                "Ambiental":"El contexto ambiental, incluida la calidad del aire, "
                            "requiere fuente, periodo y resolución apropiados.",
                "Social":"Gini y pobreza multidimensional tienen metodologías "
                         "diferentes y años de referencia distintos.",
                "Capacidad del sistema de salud":"Personal y camas describen "
                    "disponibilidad nacional de referencia, no preparación "
                    "operativa en el territorio de la crisis.",
                "Morbimortalidad":"La mortalidad por homicidio es contexto "
                    "poblacional. La morbilidad general todavía no está integrada.",
                "Cobertura de vacunación":"DTP3 y SRP1 son coberturas "
                    "poblacionales con año propio, no evidencia de brote.",
                "Demografía":"Población por sexo/edad permitirá denominadores "
                    "y exposición. Actualmente no se asumen distribuciones.",
            }[dim].split("\n"):st.write(desc)
            st.markdown("**Cobertura y limitaciones**")
            st.caption("Para cada valor deben conservarse fuente, año, "
                       "definición y escala geográfica. "
                       "Ausencia de valor no es riesgo moderado.")
            st.markdown("**Nivel de vulnerabilidad OPS**")
            st.info("Sin clasificación propia hasta que Laura defina "
                    "indicadores finales, dirección, umbrales y tratamiento "
                    "de datos faltantes.")
    with st.expander("Inventario de dimensiones de vulnerabilidad"):
        rows=[]
        for fam,inds in VULN.items():
            for value in inds:
                if value in ("Calidad del aire","Población por edad y sexo"):
                    state="Por integrar"
                elif value=="Pobreza multidimensional":
                    state="Disponible parcialmente (HAPI)"
                else:state="Disponible según cobertura OPS"
                rows.append({"Dimensión":fam,"Indicador":OPS_LABELS.get(value,value),
                             "Estado":state})
        table(pd.DataFrame(rows),height=330)
    with st.expander("Respuesta humanitaria y capacidad operativa"):
        st.caption("Organizaciones por sector 3W y financiación FTS se "
                   "mantienen disponibles en el repositorio. "
                   "No son equivalentes al nivel de vulnerabilidad.")
        p=filtered(D["presence"],selected)
        f=filtered(D["funding"],selected)
        a,b=st.columns(2)
        a.metric("Países con datos de presencia 3W",
                 p["iso3"].nunique() if not p.empty else 0)
        b.metric("Países con reportes de financiación",
                 f["iso3"].nunique() if not f.empty else 0)
