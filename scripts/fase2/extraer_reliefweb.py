#!/usr/bin/env python3
"""Extrae metadatos de ReliefWeb por país para una ventana temporal COMPLETA.

No descarga cuerpos, PDFs, imágenes ni microdatos. El filtro country.iso3
puede devolver reportes regionales para varios países. Se conserva la
relación reporte–país y no se suman estas filas como reportes únicos.
Solo publica si los 35 países completaron su paginación sin errores.
"""
from __future__ import annotations

import csv
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT/"data/catalogos/paises_americas.csv"
OUT = ROOT/"data/observaciones/reliefweb_reportes_americas.csv"
META = ROOT/"docs/fase2/reliefweb_actualizacion.json"
API = "https://api.reliefweb.int/v2/reports"
DAYS = int(os.getenv("RELIEFWEB_DAYS","90"))
PAGE = 500
MAX_PER_COUNTRY = 30000
S = requests.Session()
S.headers.update({"User-Agent":"observatorio-humanitario-ops/0.5",
                  "Accept":"application/json"})

def items(obj):
    if obj is None:return []
    if isinstance(obj,list):return obj
    return [obj]

def names(obj,key="name"):
    return " | ".join(str(v.get(key,"")).strip() for v in items(obj)
                    if isinstance(v,dict) and v.get(key))

def request(country, appname, start):
    collected=[];total=None
    for offset in range(0,MAX_PER_COUNTRY,PAGE):
        payload={
            "profile":"list","preset":"latest",
            "fields":{"include":["date.original","country.iso3","country.name",
                "primary_country.iso3","source.name","theme.name",
                "format.name","language.name","disaster_type.name"]},
            "filter":{"operator":"AND","conditions":[
                {"field":"country.iso3","value":country},
                {"field":"date.created","value":{"from":start}}
            ]},
            "sort":["date.created:desc"],
            "limit":PAGE,"offset":offset,
        }
        for attempt in range(3):
            try:
                r=S.post(API,params={"appname":appname},json=payload,timeout=45)
                if r.status_code in (429,500,502,503,504) and attempt<2:
                    time.sleep(2*(attempt+1));continue
                r.raise_for_status()
                obj=r.json()
                rows=obj["data"]
                if not isinstance(rows,list):raise ValueError("data no es lista")
                if total is None: total=int(obj["totalCount"])
                if len(rows)>PAGE:raise ValueError("más filas que limit")
                collected.extend(rows)
                break
            except (requests.RequestException,KeyError,ValueError,TypeError):
                if attempt==2:raise RuntimeError("Fallo consulta o validación de ReliefWeb")
                time.sleep(2*(attempt+1))
        if len(collected)>=total:break
        if not rows:raise RuntimeError("Paginación truncada")
    if len(collected)!=total:
        raise RuntimeError(f"Consulta país sin completar ({len(collected)}/{total})")
    return collected,total

def normalize(rows,iso,fecha):
    result=[]
    for rec in rows:
        f=rec.get("fields",{})
        dt=f.get("date") or {}
        if not isinstance(dt,dict):dt={}
        pc=f.get("primary_country") or {}
        if not isinstance(pc,dict):pc={}
        result.append({
            "iso3":iso,"reporte_id":str(rec.get("id","")),
            "titulo":str(f.get("title") or ""),
            "url":str(f.get("url") or ""),
            "fecha_publicacion_rw":str(dt.get("created") or ""),
            "fecha_publicacion_origen":str(dt.get("original") or ""),
            "pais_principal_iso3":str(pc.get("iso3") or ""),
            "paises_mencionados":names(f.get("country"),"iso3"),
            "fuentes":names(f.get("source")),
            "temas":names(f.get("theme")),
            "formatos":names(f.get("format")),
            "idiomas":names(f.get("language")),
            "tipo_desastre":names(f.get("disaster_type")),
            "fecha_extraccion_utc":fecha,
        })
    return result

def main():
    appname=os.environ.get("RELIEFWEB_APPNAME","").strip()
    if not appname:raise SystemExit("No existe RELIEFWEB_APPNAME en el entorno")
    now=datetime.now(timezone.utc)
    date=now.isoformat()
    start=(now-timedelta(days=DAYS)).replace(microsecond=0).isoformat()
    with CAT.open(encoding="utf-8-sig",newline="") as f:
        countries=list(csv.DictReader(f))
    assert len(countries)==35
    all_rows=[];check=[]
    for c in countries:
        iso=c["iso3"]
        try:
            records,total=request(iso,appname,start)
            parsed=normalize(records,iso,date)
            if len(parsed)!=total:raise RuntimeError("No coinciden conteos")
            if len({x["reporte_id"] for x in parsed})!=len(parsed):
                raise RuntimeError("Reporte duplicado en un mismo país")
            all_rows.extend(parsed)
            check.append({"iso3":iso,"estado":"COMPLETO","reportes":total})
            print(iso,"COMPLETO",total,flush=True)
        except Exception as e:
            check.append({"iso3":iso,"estado":"ERROR","reportes":None,
                          "motivo":type(e).__name__})
            print(iso,"ERROR",type(e).__name__,flush=True)
    if len(check)!=35 or any(x["estado"]!="COMPLETO" for x in check):
        raise RuntimeError("No se publican datos parciales; revisar errores por país")
    OUT.parent.mkdir(exist_ok=True,parents=True)
    cols=["iso3","reporte_id","titulo","url","fecha_publicacion_rw",
          "fecha_publicacion_origen","pais_principal_iso3","paises_mencionados",
          "fuentes","temas","formatos","idiomas","tipo_desastre",
          "fecha_extraccion_utc"]
    tmp=OUT.with_suffix(".tmp")
    with tmp.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(all_rows)
    tmp.replace(OUT)
    META.parent.mkdir(exist_ok=True,parents=True)
    state={"fecha_utc":date,"desde_utc":start,"ventana_dias":DAYS,
           "paises_evaluados":35,"paises_completos":35,
           "filas_pais_reporte":len(all_rows),
           "reportes_unicos":len({r["reporte_id"] for r in all_rows}),
           "metodologia":"Todos los reportes de 90 días asociados al país, con paginación exhaustiva. Un reporte regional puede aparecer para varios países; no son eventos ni totales de crisis.",
           "datos_guardados":"Solo metadatos enlazados a ReliefWeb, sin cuerpos o adjuntos",
           "detalle":check}
    META.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",
                    encoding="utf-8")
    print("RESUMEN",json.dumps({k:state[k] for k in
           ("paises_completos","filas_pais_reporte","reportes_unicos")},ensure_ascii=False))

if __name__=="__main__":main()
