#!/usr/bin/env python3
"""Auditoría automática del diseño del Observatorio en navegador Chromium.

Verifica en DOM alturas de paneles *en paralelo* con el CSS real aplicado,
captura las cuatro páginas a viewport 1440px. No inspecciona credenciales ni
navega a APIs. Las capturas se guardan como artifact de GitHub Actions.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

OUTPUT=Path("docs/qa_capturas")
OUTPUT.mkdir(parents=True,exist_ok=True)
PAGES=[
    ("Amenazas y eventos","amenazas_eventos"),
    ("Movilidad y necesidades","movilidad_necesidades"),
    ("Vulnerabilidad y respuesta","vulnerabilidad_respuesta"),
    ("Perfiles por país","perfil_pais"),
]

def geometries(page):
    """Medir el marco único de cada gráfico. Títulos y fuentes quedan fuera."""
    return page.locator('[class*="st-key-coe_chart_"]').evaluate_all("""
      es => es.map(e => {
        const b=e.getBoundingClientRect();
        const c=getComputedStyle(e);
        if(b.width<200 || b.height<240) return null;
        return {x:b.x,y:b.y,w:b.width,h:b.height,
                border:c.borderTopWidth || '1px'};
      }).filter(x=>x!==null)
    """)

def paired_boxes(xs):
    # Se comparan paneles cuya y superior coincide y x es distinta.
    # Los wrappers externos no figuran como parejas porque son más anchos.
    pairs=[]
    for i,a in enumerate(xs):
        for b in xs[i+1:]:
            if abs(a["y"]-b["y"])<12 and abs(a["x"]-b["x"])>60:
                if a["w"]>0 and b["w"]>0:
                    pairs.append((a,b))
    return pairs

def validate_grid(geom, label):
    """Verificar anchos y bordes de una cuadrícula real de dos columnas.

    Se excluyen paneles de ancho completo que no deben llenar media columna.
    No basta con comprobar las parejas: deben conservar la misma división
    vertical en todas las filas y con los mismos anchos.
    """
    if len(geom) < 2:
        return
    # No incluir tarjetas a ancho completo en comprobaciones de dos columnas.
    # Son paneles intencionales y se evalúan por separado.
    base_width=min(g["w"] for g in geom)
    candidates=[g for g in geom if g["w"]<=base_width*1.35]
    if len(candidates)<2:
        return
    xs=sorted(candidates, key=lambda g:g["x"])
    left=xs[0]["x"]
    # Cada pareja tiene columnas izquierda/derecha. Una tarjeta a ancho
    # completo no genera dos posiciones horizontales y se excluye.
    right_candidates=sorted(x["x"] for x in candidates if x["x"] > left+75)
    if not right_candidates:
        return
    right=right_candidates[0]
    cols=[x for x in candidates if abs(x["x"]-left)<8 or abs(x["x"]-right)<8]
    displaced=[x for x in candidates if x not in cols]
    if displaced:
        raise AssertionError(f"{label}: tarjetas desplazadas fuera de la cuadrícula: {displaced}")
    left_cards=sorted((x for x in cols if abs(x["x"]-left)<8), key=lambda x:x["y"])
    right_cards=sorted((x for x in cols if abs(x["x"]-right)<8), key=lambda x:x["y"])
    for group in (left_cards,right_cards):
        if any(abs(p["x"]-group[0]["x"])>5 or abs(p["w"]-group[0]["w"])>5 for p in group):
            raise AssertionError(f"{label}: cambia ancho o margen dentro de una columna: {group}")
    if abs(left_cards[0]["w"]-right_cards[0]["w"])>8:
        raise AssertionError(f"{label}: columnas izquierda/derecha de distinto ancho")
    # Cuando una tabla se presenta sin caja, puede quedar un solo gráfico
    # en una fila. Comparar exclusivamente los gráficos de LA MISMA fila:
    # emparejar por orden produciría falsos desalineados entre filas distintas.
    for a in left_cards:
        peers=[b for b in right_cards if abs(a["y"]-b["y"])<=9]
        for b in peers:
            if abs(a["h"]-b["h"])>5:
                raise AssertionError(f"{label}: pareja de gráficos con distinta altura: {a} / {b}")
    print("CUADRICULA",label,
          {"columnas":2,"filas_pares":min(len(left_cards),len(right_cards)),
           "ancho":round(left_cards[0]["w"],1)},flush=True)


def main():
    url=os.getenv("STREAMLIT_URL","http://127.0.0.1:8501")
    results={}
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        page=browser.new_page(viewport={"width":1440,"height":900},
                              device_scale_factor=1)
        page.goto(url,wait_until="domcontentloaded",timeout=90000)
        page.locator(".obs-page").wait_for(timeout=90000)
        for index,(label,name) in enumerate(PAGES):
            if index:
                page.locator('[data-testid="stSidebar"]').get_by_text(
                    label,exact=True).click(timeout=25000)
                page.locator(".obs-page").wait_for(timeout=60000)
            page.wait_for_timeout(3000)
            errs=page.locator('[data-testid="stException"]').count()
            if errs:
                raise RuntimeError(f"{label}: excepción visible en la app")
            # Los indicadores superiores usan una franja única con divisores,
            # y no deben volver a verse como tarjetas sueltas.
            stripe=page.locator(".ops-metric-strip")
            if stripe.count()==0:
                raise AssertionError(f"{label}: falta la franja unificada de indicadores")
            cells=stripe.first.locator(".ops-strip-item")
            if cells.count()<2:
                raise AssertionError(f"{label}: banda de KPIs incompleta")
            print("BANDA_KPI",label,{"indicadores":cells.count()},flush=True)
            # v4 tiene paneles iguales visibles en cada página; no requiere
            # entrar a pestañas para medirlos.
            geom=geometries(page)
            validate_grid(geom, label)
            if label == "Amenazas y eventos":
                controls = page.evaluate("""
                    () => {
                      const bounds = key => {
                        const el = document.querySelector('.st-key-' + key);
                        if (!el) return null;
                        const r = el.getBoundingClientRect();
                        return {x:r.x,width:r.width,y:r.y,height:r.height};
                      };
                      const root = document.querySelector('.st-key-op_event_months');
                      const slider = root ? root.querySelector(
                        '[role="slider"], [data-baseweb="slider"], [data-testid="stSlider"], input[type="range"]'
                      ) : null;
                      return {event:bounds('op_event_kind'),
                              period:bounds('op_event_months'),
                              slider: slider ? {
                                tag:slider.tagName,
                                type:slider.getAttribute('data-testid'),
                                value: slider.getAttribute('aria-valuenow')
                              } : null,
                              html_sample:root ? root.innerHTML.slice(0, 1800) : ''};
                    }
                """)
                print("FILTROS_AMENAZAS",controls,flush=True)
                if not controls["event"] or not controls["period"] or len(geom)<2:
                    raise AssertionError("Faltan filtros de amenazas o tarjetas comparables")
                if abs(controls["event"]["x"] - geom[0]["x"]) > 8:
                    raise AssertionError("Tipo de evento no inicia en la columna del mapa")
                if abs(controls["period"]["x"] - geom[1]["x"]) > 8:
                    raise AssertionError("Periodo no inicia en la columna del ranking")
                if abs(controls["event"]["width"] - geom[0]["w"]) > 10:
                    raise AssertionError("Tipo de evento no ocupa el ancho del mapa")
                if not controls["slider"]:
                    raise AssertionError("Periodo debe ser un control deslizante horizontal")
            print("GEOMETRIA",name,geom[:12],flush=True)
            if not geom:
                chains=page.locator(".obs-card-title").evaluate_all("""
                  es => es.slice(0,3).map(e=>{
                    let p=e,levels=[];
                    for(let i=0;i<9 && p;i++,p=p.parentElement){
                      const b=p.getBoundingClientRect(),c=getComputedStyle(p);
                      levels.push({tag:p.tagName,
                        testid:p.getAttribute('data-testid'),
                        width:b.width,height:b.height,border:c.borderTopWidth});
                    }
                    return levels;
                  })
                """)
                print("ANCESTROS",name,chains,flush=True)
            image=OUTPUT/f"{name}.png"
            page.screenshot(path=str(image),full_page=True,
                            animations="disabled",timeout=60000)
            pairs=paired_boxes(geom)
            # Los paneles están definidos con alturas fijas de 490/440.
            mismatch=[]
            for a,b in pairs:
                if abs(a["h"]-b["h"])>4:
                    mismatch.append({"a":a,"b":b,"difference":round(abs(a["h"]-b["h"]),1)})
                if a["border"]=="0px" or b["border"]=="0px":
                    raise AssertionError(f"{label}: panel sin borde")
            if mismatch:
                raise AssertionError(f"{label}: paneles desalineados {mismatch[:3]}")
            if not geom:
                raise AssertionError(f"{label}: no se detectaron paneles visibles")
            # Algunas páginas muestran un único gráfico ancho; en ellas no hay parejas.
            results[name]={"paneles_visibles":len(geom),"parejas_alineadas":len(pairs),
                "captura":str(image)}
            print(label,results[name],flush=True)
        # Abrir opciones que no están visibles por defecto. El objetivo es
        # comprobar que la navegación secundaria evita páginas larguísimas.
        for page_label, topic, expected, shot in [
            ("Amenazas y eventos", "Crisis evaluadas y acceso",
             "Tres pilares de acceso", "acaps_desglose"),
            ("Movilidad y necesidades", "Desplazamiento interno",
             "Población desplazada registrada en la operación", "movilidad_dtm"),
            ("Movilidad y necesidades", "Personas en necesidad",
             "Estimaciones nacionales de PiN", "movilidad_pin"),
            ("Vulnerabilidad y respuesta", "Salud y sociedad",
             "Comparación entre países", "vulnerabilidad_ops"),
            ("Vulnerabilidad y respuesta", "Pobreza",
             "Incidencia de pobreza multidimensional", "vulnerabilidad_pobreza"),
            ("Vulnerabilidad y respuesta", "Seguridad alimentaria",
             "Población estimada por fase IPC", "vulnerabilidad_ipc"),
            ("Vulnerabilidad y respuesta", "Respuesta",
             "Organizaciones reportadas por sector", "vulnerabilidad_respuesta_3w"),
            ("Perfiles por país", "Movilidad y necesidades",
             "Refugio y asilo en el país de acogida", "perfil_movilidad"),
            ("Perfiles por país", "Riesgo y vulnerabilidad",
             "Riesgo estructural INFORM", "perfil_riesgo"),
            ("Perfiles por país", "Respuesta e informes",
             "Informes humanitarios asociados al país", "perfil_informes"),
        ]:
            page.locator('[data-testid="stSidebar"]').get_by_text(
                page_label, exact=True).click(timeout=25000)
            # Evitar confundir el botón del subtema con la sección homónima
            # de la barra lateral (p. ej. "Movilidad y necesidades").
            page.locator('[data-testid="stMainBlockContainer"]').get_by_text(
                topic, exact=True).last.click(timeout=25000)
            page.get_by_text(expected, exact=True).first.wait_for(timeout=50000)
            page.wait_for_timeout(900)
            if page.locator('[data-testid="stException"]').count():
                raise RuntimeError(f"{page_label} / {topic}: excepción en la app")
            if shot in ("acaps_desglose", "vulnerabilidad_ops",
                        "vulnerabilidad_respuesta_3w", "perfil_movilidad",
                        "perfil_riesgo", "perfil_informes"):
                page.screenshot(path=str(OUTPUT/f"{shot}.png"),
                                full_page=True, animations="disabled", timeout=60000)
            if shot == "movilidad_pin":
                # No filas de relleno ni valores pegados como 7900000.
                compact=page.locator(".ops-data-table").first
                compact.wait_for(timeout=15000)
                num_rows=compact.locator("tbody tr").count()
                numbers=compact.locator("tbody td.ops-numeric").all_text_contents()
                if not 1 <= num_rows <= 12:
                    raise AssertionError(f"Tabla PiN no es compacta: {num_rows} filas")
                if not any("," in v for v in numbers if len(v.strip()) >= 5):
                    raise AssertionError(f"PiN sin separadores de miles: {numbers}")
                frame=page.locator('[class*="st-key-coe_table_"]').filter(
                    has=page.locator(".ops-data-table")).first
                frame.wait_for(timeout=10000)
                style=frame.evaluate("""
                    e => {
                        let wrap=e.querySelector('[data-testid="stVerticalBlockBorderWrapper"]');
                        let t=e.querySelector('.ops-table-wrap');
                        let a=e.getBoundingClientRect();
                        let b=t.getBoundingClientRect();
                        return {
                          outer_border:getComputedStyle(e).borderTopWidth,
                          outer_radius:getComputedStyle(e).borderTopLeftRadius,
                          wrapper_border:wrap?getComputedStyle(wrap).borderTopWidth:null,
                          table_border:getComputedStyle(t).borderTopWidth,
                          last_row_border: getComputedStyle(
                            t.querySelector('tbody tr:last-child td')
                          ).borderBottomWidth,
                          header_color: getComputedStyle(
                            t.querySelector('thead th')
                          ).backgroundColor,
                          inner_borders: Array.from(e.querySelectorAll(
                            '[data-testid="stVerticalBlockBorderWrapper"]'
                          )).map(w=>getComputedStyle(w).borderTopWidth),
                          border_color:getComputedStyle(e).borderTopColor,
                          x:a.x,y:a.y,width:a.width,height:a.height,
                          table_height:Math.round(b.height),
                          bottom_space:Math.round(a.bottom-b.bottom)
                        };
                    }
                """)
                if (style["outer_border"] != "1px" or
                    style["wrapper_border"] not in (None,"0px") or
                    style["table_border"] != "0px"):
                    raise AssertionError(f"El marco debe ser único y del estilo COE: {style}")
                if float(style["outer_radius"].replace("px",""))<10:
                    raise AssertionError(f"El borde no coincide con las tarjetas COE: {style}")
                if style["last_row_border"]!="1px":
                    raise AssertionError(f"Falta el cierre horizontal de la última fila: {style}")
                if any(border!="0px" for border in style["inner_borders"]):
                    raise AssertionError(f"Marcos interiores duplicados: {style}")
                graph=page.locator('[class*="st-key-coe_chart_"]').first
                graph_bounds=graph.bounding_box()
                graph_style=graph.evaluate("""
                    e=>({border:getComputedStyle(e).borderTopWidth,
                          radius:getComputedStyle(e).borderTopLeftRadius,
                          color:getComputedStyle(e).borderTopColor,
                          inner:Array.from(e.querySelectorAll(
                            '[data-testid="stVerticalBlockBorderWrapper"]'
                          )).map(w=>getComputedStyle(w).borderTopWidth)})
                """)
                if (graph_style["border"]!=style["outer_border"] or
                    graph_style["radius"]!=style["outer_radius"] or
                    graph_style["color"]!=style["border_color"]):
                    raise AssertionError(
                        f"El borde de tabla y gráfico no es idéntico: {style} / {graph_style}")
                if any(border!="0px" for border in graph_style["inner"]):
                    raise AssertionError(f"Gráfico con segunda línea interna: {graph_style}")

                if graph_bounds and (
                    abs(graph_bounds["height"]-style["height"])>6 or
                    abs(graph_bounds["width"]-style["width"])>6 or
                    abs(graph_bounds["y"]-style["y"])>6
                ):
                    raise AssertionError(f"Tabla y gráfico de PiN no son de igual tamaño: "
                                         f"{style} / {graph_bounds}")
                if style["bottom_space"]>35:
                    raise AssertionError(f"Demasiado espacio vacío bajo la tabla: {style}")
                print("TABLA_PIN_COMPACTA", {"filas":num_rows,
                      "cifras":numbers[:4],"estilo":style},flush=True)
            validate_grid(geometries(page), f"{page_label} / {topic}")
            print("OK SUBTEMA", page_label, topic, flush=True)

        # Fondo blanco uniforme desde el borde hasta el interior del gráfico.
        page.locator('[data-testid="stSidebar"]').get_by_text(
            "Amenazas y eventos", exact=True).click(timeout=25000)
        plot=page.locator('[data-testid="stPlotlyChart"]').first
        plot.wait_for(timeout=30000)
        backgrounds=plot.evaluate("""
          e => {
            const get = el => el ? getComputedStyle(el).backgroundColor : null;
            let parent=e;
            while(parent && !String(parent.className).includes('st-key-coe_chart_')){
              parent=parent.parentElement;
            }
            return {contenedor:get(parent), grafico:get(e)};
          }
        """)
        print("FONDOS_PANEL", backgrounds, flush=True)
        white="rgb(255, 255, 255)"
        if backgrounds["grafico"] != white or backgrounds["contenedor"] != white:
            raise AssertionError(f"Hay fondos distintos al blanco: {backgrounds}")
        # Comprobar que el gráfico no quede pegado al borde superior.
        chart_positions=page.locator('[class*="st-key-coe_chart_"]').evaluate_all("""
          elements => elements.map(e => {
            const chart=e.querySelector('[data-testid="stPlotlyChart"]');
            if(!chart) return null;
            if(e.querySelector('[data-testid="stDataFrame"], [data-testid="stMetric"], [data-testid="stSelectbox"]')) return null;
            const b=e.getBoundingClientRect(),p=chart.getBoundingClientRect();
            return {alto:b.height, grafico:p.height, arriba:Math.round(p.top-b.top),
                    abajo:Math.round(b.bottom-p.bottom)};
          }).filter(Boolean)
        """)
        print("CENTRADO_GRAFICOS",chart_positions,flush=True)
        if chart_positions and any(abs(x["arriba"]-x["abajo"])>12 for x in chart_positions):
            raise AssertionError(f"Gráfico descentrado verticalmente: {chart_positions}")
        # La tabla de fuentes del desplegable usa EXACTAMENTE el mismo
        # componente que las tablas de la cuadrícula y debe cerrar la última fila.
        footer=page.get_by_text("Fuentes, alcance y limitaciones de los datos",
                                exact=True).first
        footer.click(timeout=25000)
        footer_table=page.locator('[data-testid="stExpander"] .ops-data-table').first
        footer_table.wait_for(timeout=25000)
        footer_style=footer_table.evaluate("""
            t=>({header:getComputedStyle(t.querySelector('thead th')).backgroundColor,
                 bottom:getComputedStyle(t.querySelector(
                   'tbody tr:last-child td')).borderBottomWidth,
                 rows:t.querySelectorAll('tbody tr').length})
        """)
        if footer_style["bottom"]!="1px" or footer_style["rows"]<5:
            raise AssertionError(f"Pie de fuentes sin fila inferior: {footer_style}")
        if footer_style["header"]!=style["header_color"]:
            raise AssertionError(f"Tablas con diferentes colores: {footer_style} vs {style}")
        print("TABLAS_UNIFICADAS",footer_style,flush=True)
        browser.close()
    (OUTPUT/"resultado.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
    print("OK: todas las parejas de paneles están alineadas en navegador real")

if __name__=="__main__":main()
