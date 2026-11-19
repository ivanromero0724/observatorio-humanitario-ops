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
            # v4 tiene paneles iguales visibles en cada página; no requiere
            # entrar a pestañas para medirlos.
            geom=geometries(page)
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
            ("Perfiles por país", "Informes recientes",
             "Informes humanitarios recientes", "perfil_informes"),
        ]:
            page.locator('[data-testid="stSidebar"]').get_by_text(
                page_label, exact=True).click(timeout=25000)
            page.get_by_text(topic, exact=True).last.click(timeout=25000)
            page.get_by_text(expected, exact=True).first.wait_for(timeout=50000)
            page.wait_for_timeout(900)
            if page.locator('[data-testid="stException"]').count():
                raise RuntimeError(f"{page_label} / {topic}: excepción en la app")
            if shot in ("acaps_desglose", "vulnerabilidad_ops",
                        "vulnerabilidad_respuesta_3w"):
                page.screenshot(path=str(OUTPUT/f"{shot}.png"),
                                full_page=True, animations="disabled", timeout=60000)
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
        browser.close()
    (OUTPUT/"resultado.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
    print("OK: todas las parejas de paneles están alineadas en navegador real")

if __name__=="__main__":main()
