#!/usr/bin/env python3
"""Indicadores CRISIS de ACAPS para los 35 países; completa todas las páginas.

Dos datasets:
- INFORM Severity Index: puntuación de crisis y dimensiones (NO suma entre crisis).
- Humanitarian Access: ACCESS, P1–P3 e I1–I9 por crisis/país.
El flujo conserva sólo series de acceso público y metadatos, no claves.
Al fallar una página, NO reemplaza la versión anterior.
Humanitarian Access Events se discontinuó 31-jul-2026 y no se usa como señal actual.
"""
from __future__ import annotations
import csv
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests

ROOT=Path(__file__).resolve().parents[2]
CAT=ROOT/"data/catalogos/paises_americas.csv"
DIR=ROOT/"data/observaciones"
META=ROOT/"docs/fase2/acaps_actualizacion.json"
BASE="https://api.acaps.org/api/v1/"
DATASETS={
  "severity":{"path":"inform-severity-index/",
    "out":"acaps_severity_americas.csv",
    "fields":{
      "puntuacion":"INFORM Severity Index",
      "categoria":"INFORM Severity category",
      "confiabilidad":"Reliability",
      "impacto_crisis":"Impact of the crisis",
      "impacto_geografico":"Geographical Impact",
      "impacto_humano":"Human Impact",
      "condiciones_afectados":"Conditions of affected people",
      "personas_necesidad":"People in need",
      "concentracion_condiciones":"Concentration of conditions",
      "complejidad":"Complexity",
      "sociedad_seguridad":"Society and safety",
      "entorno_operativo":"Operating environment",
    }},
  "access":{"path":"humanitarian-access/",
    "out":"acaps_acceso_americas.csv",
    "fields":{"acceso":"ACCESS","brecha_info":"Infogap",
              **{f"pilar_{i}":f"P{i}" for i in range(1,4)},
              **{f"indicador_{i}":f"I{i}" for i in range(1,10)}}},
}
HEADERS=["iso3","crisis_id","crisis","drivers","paises_crisis",
         "crisis_multinacional","corte_api","fecha_extraccion_utc"]
S=requests.Session()

def download(path,token):
    url=BASE+path;visited=set();out=[];count=None;cut=""
    for page in range(30):
        if url in visited:raise RuntimeError("Página repetida ACAPS")
        visited.add(url)
        parsed=urlparse(url)
        if parsed.netloc!="api.acaps.org":
            raise RuntimeError("Enlace de paginación fuera de ACAPS")
        r=S.get(url,headers={"Authorization":"Token "+token,
            "Accept":"application/json","User-Agent":"ObservatorioOPS/0.5"},
            timeout=45)
        r.raise_for_status()
        if page==0:
            cut=urlparse(r.url).path.rstrip("/").split("/")[-1]
        j=r.json()
        if not isinstance(j,dict) or not isinstance(j.get("results"),list):
            raise ValueError("Estructura de página inesperada")
        if count is None:count=int(j["count"])
        out.extend(j["results"])
        nxt=j.get("next")
        if not nxt:break
        if isinstance(nxt,str) and nxt.startswith("/"):
            url="https://api.acaps.org"+nxt
        elif isinstance(nxt,str) and nxt.startswith("http"):url=nxt
        else:raise ValueError("next inválido")
    if len(out)!=count:raise RuntimeError("ACAPS incompleto")
    return out,cut,count

def normalize(data,name,config,countries,cut,now):
    out=[]
    for rec in data:
        if not isinstance(rec,dict):continue
        codes=rec.get("iso3") or []
        if isinstance(codes,str): codes=[codes]
        if not isinstance(codes,list):continue
        codes=sorted(set(str(c).upper() for c in codes if isinstance(c,str)))
        valid=[c for c in codes if c in countries]
        for iso in valid:
            row={"iso3":iso,
                "crisis_id":str(rec.get("crisis_id") or ""),
                "crisis":str(rec.get("crisis_name") or ""),
                "drivers":" | ".join(str(v) for v in rec.get("drivers",[])
                        if isinstance(v,(str,int))),
                "paises_crisis":" | ".join(codes),
                "crisis_multinacional":len(codes)>1,
                "corte_api":cut,"fecha_extraccion_utc":now}
            for target,original in config["fields"].items():
                v=rec.get(original)
                if isinstance(v,(list,dict)):v=json.dumps(v,ensure_ascii=False)
                row[target]="" if v is None else v
            out.append(row)
    keys=[(r["iso3"],r["crisis_id"]) for r in out]
    if len(keys)!=len(set(keys)):
        # Algunas crisis tienen el mismo id en distintos subcomponentes.
        # No colapsar arbitrariamente; detener para revisión.
        raise RuntimeError(f"{name}: duplicados país-crisis_id")
    return out

def main():
    token=os.environ.get("ACAPS_API_TOKEN","").strip()
    if not token:raise SystemExit("Secreto ACAPS_API_TOKEN no disponible")
    with CAT.open(encoding="utf-8-sig",newline="") as f:
        countries={r["iso3"] for r in csv.DictReader(f)}
    assert len(countries)==35
    now=datetime.now(timezone.utc).isoformat()
    staging={};meta={}
    for name,config in DATASETS.items():
        raw,cut,count=download(config["path"],token)
        normalized=normalize(raw,name,config,countries,cut,now)
        staging[name]=normalized
        meta[name]={"corte_api":cut,"registros_globales":count,
                    "filas_pais_crisis_americas":len(normalized),
                    "paises_americas":len({r["iso3"] for r in normalized}),
                    "categorias_variables":config["fields"],
                    "paises_con_registros":sorted({r["iso3"] for r in normalized})}
        print(name,"OK",cut,count,"global",len(normalized),"Américas",flush=True)
    # Transacción: escribir archivos únicamente tras dos descargas completas.
    DIR.mkdir(exist_ok=True,parents=True)
    for name,rows in staging.items():
        config=DATASETS[name]
        cols=HEADERS+list(config["fields"])
        path=DIR/config["out"]
        tmp=path.with_suffix(".tmp")
        with tmp.open("w",encoding="utf-8",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=cols)
            writer.writeheader()
            writer.writerows(rows)
        tmp.replace(path)
    META.parent.mkdir(exist_ok=True,parents=True)
    j={"fecha_utc":now,"paises_catalogo":35,
       "completitud":"100% de la paginación global en ambos endpoints",
       "limitacion":"Crisis multinacionales pueden aparecer en varios países; no sumar crisis ni ponderaciones entre geografías",
       "eventos_acceso_discontinuados":"ACAPS informó que Humanitarian Access Events dejó de recopilarse el 31-jul-2026; solo histórico",
       "datasets":meta}
    META.write_text(json.dumps(j,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":main()
