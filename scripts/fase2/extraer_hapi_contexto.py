#!/usr/bin/env python3
"""HAPI v2: 5 familias de indicadores nacionales, descarga íntegra 35 países.

Fuentes: humanitarian-needs, funding, national-risk, poverty-rate, food-security.
Solo se solicita admin_level=0 cuando esa variable existe; se evita sumar
niveles administrativos o desagregaciones de población. Nada de PII.
Cada página se obtiene completamente o el workflow falla SIN publicar nuevo
snapshot. Sin exponer el app_identifier en logs, CSV ni metadatos.
"""
from __future__ import annotations
import csv
import json
import math
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[2]
CAT=ROOT/"data/catalogos/paises_americas.csv"
DEST=ROOT/"data/observaciones"
METADATA=ROOT/"docs/fase2/hapi_contexto_actualizacion.json"
BASE="https://hapi.humdata.org/api/v2/"
LIMIT=5000
MAX_PAGES=65
S=requests.Session()
S.headers["User-Agent"]="ObservatorioHumanitarioOPS/1.0; humanitarian-data"

SOURCES={
 "necesidades":{
   "path":"affected-people/humanitarian-needs",
   "file":"hapi_necesidades_nacional.csv",
   "params":{"admin_level":0,"start_date":"2024-01-01"},
   "fields":["resource_hdx_id","location_code","admin_level",
        "sector_code","sector_name","category","population_status",
        "population","reference_period_start","reference_period_end"]},
 "financiacion":{
   "path":"coordination-context/funding",
   "file":"hapi_financiacion_apelaciones.csv",
   "params":{"start_date":"2023-01-01"},
   "fields":["resource_hdx_id","location_code","appeal_code","appeal_name",
        "appeal_type","requirements_usd","funding_usd","funding_pct",
        "reference_period_start","reference_period_end"]},
 "riesgo":{
   "path":"coordination-context/national-risk",
   "file":"hapi_inform_componentes.csv",
   "params":{},
   "fields":["resource_hdx_id","location_code","risk_class","global_rank",
        "overall_risk","hazard_exposure_risk","vulnerability_risk",
        "coping_capacity_risk","meta_missing_indicators_pct",
        "meta_avg_recentness_years","reference_period_start","reference_period_end"]},
 "pobreza":{
   "path":"food-security-nutrition-poverty/poverty-rate",
   "file":"hapi_pobreza_multidimensional.csv",
   "params":{"admin_level":0},
   "fields":["resource_hdx_id","location_code","admin_level","mpi",
        "headcount_ratio","intensity_of_deprivation","vulnerable_to_poverty",
        "in_severe_poverty","reference_period_start","reference_period_end"]},
 "inseguridad_alimentaria":{
   "path":"food-security-nutrition-poverty/food-security",
   "file":"hapi_seguridad_alimentaria_ipc.csv",
   "params":{"admin_level":0,"start_date":"2023-01-01"},
   "fields":["resource_hdx_id","location_code","admin_level","ipc_phase",
        "ipc_type","population_in_phase","population_fraction_in_phase",
        "reference_period_start","reference_period_end"]},
}

def fetch(iso,topic,key):
    cfg=SOURCES[topic]
    u=BASE+cfg["path"]
    base={"app_identifier":key,"location_code":iso,
        "output_format":"json","limit":LIMIT,**cfg["params"]}
    data=[];signatures=set()
    for p in range(MAX_PAGES):
        params={**base,"offset":p*LIMIT}
        for attempt in range(4):
            try:
                res=S.get(u,params=params,timeout=70)
                if res.status_code in (429,500,502,503,504) and attempt<3:
                    time.sleep(3*(attempt+1))
                    continue
                if res.status_code!=200:raise RuntimeError("HTTP_ERROR_"+str(res.status_code))
                payload=res.json()
                chunk=payload.get("data")
                if not isinstance(chunk,list) or len(chunk)>LIMIT:
                    raise RuntimeError("INVALID_PAGE")
                break
            except (requests.RequestException,ValueError) as e:
                if attempt==3:raise RuntimeError(type(e).__name__) from None
                time.sleep(2*(attempt+1))
        for row in chunk:
            if str(row.get("location_code","")).upper()!=iso:
                raise RuntimeError("INCORRECT_COUNTRY")
            signature=json.dumps(row,ensure_ascii=False,sort_keys=True,default=str)
            if signature in signatures:
                # Duplicados idénticos nunca se contabilizan dos veces.
                continue
            signatures.add(signature)
            rec={f:row.get(f) for f in cfg["fields"]}
            rec["iso3"]=iso
            data.append(rec)
        if len(chunk)<LIMIT:
            return data,(p+1),len(signatures)
    raise RuntimeError("MAX_PAGES_REACHED")

def valid_rows(rows,topic):
    cfg=SOURCES[topic]
    for row in rows:
        if topic in ("necesidades","pobreza","inseguridad_alimentaria"):
            if int(row.get("admin_level") or 0)!=0:
                raise RuntimeError("MIXED_ADMIN_LEVELS")
        if topic=="necesidades":
            amount=row.get("population")
            if amount is not None and (not isinstance(amount,(int,float))
                or not math.isfinite(float(amount)) or amount<0):
                raise RuntimeError("INVALID_POPULATION")
        elif topic=="financiacion":
            for f in ("funding_usd","requirements_usd"):
                v=row.get(f)
                if v is not None and (not isinstance(v,(int,float)) or v<0):
                    raise RuntimeError("INVALID_FUNDING")

def main():
    app=os.environ.get("HDX_APP_IDENTIFIER","").strip()
    if not app:raise SystemExit("Falta HDX_APP_IDENTIFIER")
    with CAT.open(encoding="utf-8-sig",newline="") as f:
        countries=[x["iso3"] for x in csv.DictReader(f)]
    assert len(set(countries))==len(countries)==35
    now=datetime.now(timezone.utc).isoformat()
    snapshots={};notes={}
    for topic,cfg in SOURCES.items():
        full=[];checks=[]
        for iso in countries:
            try:
                rows,pages,unique=fetch(iso,topic,app)
                valid_rows(rows,topic)
                full.extend(rows)
                checks.append({"iso3":iso,
                    "estado":"CON_DATOS" if rows else "SIN_REGISTROS",
                    "filas":len(rows),"paginas":pages})
                print(topic,iso,len(rows),"filas; completas",flush=True)
            except Exception as e:
                # No continuar con una descarga parcial.
                print(topic,iso,"ERROR",type(e).__name__,flush=True)
                raise
        keys=[(r["iso3"],
            *[str(r.get(f) or "") for f in cfg["fields"]])
            for r in full]
        if len(keys)!=len(set(keys)):
            raise RuntimeError("DUPLICATED_NORMALIZED_ROWS_"+topic)
        snapshots[topic]=full
        notes[topic]={"endpoint":cfg["path"],
            "paises_consultados":35,
            "paises_con_datos":sum(x["estado"]=="CON_DATOS" for x in checks),
            "paises_sin_datos":sum(x["estado"]=="SIN_REGISTROS" for x in checks),
            "filas":len(full),"detalle":checks,
            "filtros":{k:v for k,v in cfg["params"].items()},
            "unidad_analisis":"Fila original publicada por HAPI a nivel país / apelación / fase / categoría"}
    # Escribir solo después de terminar exhaustivamente los 5 temas.
    DEST.mkdir(parents=True,exist_ok=True)
    for topic,rows in snapshots.items():
        cfg=SOURCES[topic]
        target=DEST/cfg["file"]
        tmp=target.with_suffix(".tmp")
        with tmp.open("w",encoding="utf-8",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=["iso3"]+cfg["fields"])
            writer.writeheader()
            writer.writerows(rows)
        tmp.replace(target)
    METADATA.parent.mkdir(exist_ok=True,parents=True)
    obj={"fecha_extraccion_utc":now,
        "paises_catalogo":35,"descargas_completas":True,
        "advertencias":[
          "Ausencia de registros en un país no significa ausencia de necesidades.",
          "PiN y estados de población no sumables entre sectores/categorías.",
          "FINANCIACIÓN: solo apelaciones FTS; no financiación humanitaria total.",
          "IPC: no agregar admin0 con subnacional ni análisis con proyecciones.",
          "OPHI: pobreza y dimensiones no son comparables con otras metodologías.",
          "Los cortes y años varían por indicador; no imputar ni inventar ceros."],
        "temas":notes}
    METADATA.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("OK", {k:(v["filas"],v["paises_con_datos"]) for k,v in notes.items()})

if __name__=="__main__":main()
