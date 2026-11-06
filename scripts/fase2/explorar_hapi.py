#!/usr/bin/env python3
"""Explorar endpoints HAPI v2 por país, sin secretos ni valores originales.

La prueba usa limit=1; no es extracción ni indicador. El fin es verificar
rutas, filtros y variables disponibles para diseñar cargas completas.
"""
import json,os,time,csv
from datetime import datetime,timezone
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"docs/fase2/hapi_catalogo_endpoints.json"
ENDPOINTS={
 "necesidades":"affected-people/humanitarian-needs",
 "desplazados":"affected-people/idps",
 "refugio":"affected-people/refugees-persons-of-concern",
 "retornados":"affected-people/returnees",
 "organizaciones":"coordination-context/operational-presence",
 "financiacion":"coordination-context/funding",
 "riesgo":"coordination-context/national-risk",
 "inseguridad_alimentaria":"food-security-nutrition-poverty/food-security",
 "precios_alimentos":"food-security-nutrition-poverty/food-prices-market-monitor",
 "pobreza":"food-security-nutrition-poverty/poverty-rate",
 "poblacion":"geography-infrastructure/baseline-population",
 "lluvia":"climate/hazards-rainfall",
}
S=requests.Session()
S.headers["User-Agent"]="observatorio-humanitario-ops/0.7 (HAPI audit)"
def query(name,path,iso,key):
    u="https://hapi.humdata.org/api/v2/"+path
    params={"app_identifier":key,"location_code":iso,
            "output_format":"json","limit":1,"offset":0}
    try:
        for a in range(3):
            r=S.get(u,params=params,timeout=35)
            if r.status_code in (429,502,503,504):
                if a<2:time.sleep((a+1)*3);continue
            break
        status=r.status_code
        if status!=200:return {"estado":"HTTP_ERROR","codigo":status}
        body=r.json()
        rows=body.get("data",[])
        if not isinstance(rows,list):return {"estado":"JSON_INESPERADO","codigo":status}
        return {"estado":"CON_DATOS" if rows else "SIN_REGISTROS",
                "codigo":status,"columnas":sorted(rows[0].keys()) if rows else [],
                "total_api":body.get("totalCount") or body.get("total_count") or body.get("count")}
    except (requests.RequestException,ValueError,TypeError):
        return {"estado":"ERROR_CONEXION"}
def main():
    key=os.getenv("HDX_APP_IDENTIFIER","").strip()
    if not key:raise SystemExit("Falta secreto HAPI")
    countries=["COL","HTI","VEN","MEX","BRA"]
    output={"fecha_utc":datetime.now(timezone.utc).isoformat(),
            "muestra_paises":countries,
            "nota":"limit=1 solo exploración; SIN cobertura completa ni datos publicables",
            "fuentes":{}}
    for name,path in ENDPOINTS.items():
        checks={}
        for iso in countries:
            checks[iso]=query(name,path,iso,key)
        output["fuentes"][name]={"endpoint_v2":path,"paises_muestra":checks}
        print(name, {c:(v["estado"],v.get("total_api")) for c,v in checks.items()},flush=True)
    OUT.parent.mkdir(exist_ok=True,parents=True)
    OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__":main()
