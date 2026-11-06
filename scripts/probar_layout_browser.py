#!/usr/bin/env python3
"""Auditoría automática del diseño del Observatorio en navegador Chromium.

Verifica en DOM alturas de paneles *en paralelo* con el CSS real aplicado,
captura las cinco páginas a viewport 1440px. No inspecciona credenciales ni
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
    ("Situaciones documentadas","situaciones"),
    ("Amenazas y acceso","amenazas"),
    ("Personas e impacto","personas"),
    ("Vulnerabilidad y respuesta","vulnerabilidad"),
    ("Ficha por país","ficha"),
]

def geometries(page):
    return page.locator('[data-testid="stVerticalBlockBorderWrapper"]').evaluate_all("""
      es => es.map(e => {
        const b=e.getBoundingClientRect(), css=getComputedStyle(e);
        return {x:b.x,y:b.y,w:b.width,h:b.height,
          border:css.borderTopWidth,
          visible:b.height>0 && b.width>0}
      }).filter(x=>x.visible && x.w>=200 && x.h>=270)
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
        page.locator(".obs-title").wait_for(timeout=90000)
        for index,(label,name) in enumerate(PAGES):
            if index:
                page.locator('[data-testid="stSidebar"]').get_by_text(
                    label,exact=True).click(timeout=25000)
                page.locator(".obs-title").wait_for(timeout=60000)
            page.wait_for_timeout(3000)
            errs=page.locator('[data-testid="stException"]').count()
            if errs:
                raise RuntimeError(f"{label}: excepción visible en la app")
            geom=geometries(page)
            # Diagnóstico DOM: Streamlit puede cambiar el selector de wrapper
            # entre versiones; registrar geometría antes de evaluar.
            raw=page.locator('[data-testid="stVerticalBlockBorderWrapper"]').evaluate_all("""
              es => es.slice(0,25).map(e => {
                 const b=e.getBoundingClientRect();
                 return {x:b.x,y:b.y,w:b.width,h:b.height,
                   className:String(e.className).slice(0,80)}
              })
            """)
            print("GEOMETRIA",name,"filtrada",geom[:12],"raw",raw[:12],flush=True)
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
            if name in ("situaciones","amenazas","personas","vulnerabilidad","ficha") and not pairs:
                raise AssertionError(f"{label}: no se detectaron parejas de paneles para verificar")
            results[name]={"paneles_visibles":len(geom),"parejas_alineadas":len(pairs),
                "captura":str(image)}
            print(label,results[name],flush=True)
        browser.close()
    (OUTPUT/"resultado.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
    print("OK: todas las parejas de paneles están alineadas en navegador real")

if __name__=="__main__":main()
