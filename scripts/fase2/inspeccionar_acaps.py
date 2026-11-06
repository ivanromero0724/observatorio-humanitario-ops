#!/usr/bin/env python3
"""Explora esquemas ACAPS con secreto; guarda campos, nunca registros ni claves."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import requests

OUT=Path("docs/fase2/acaps_esquemas.json")
BASE="https://api.acaps.org/api/v1/"
ENDPOINTS={
  "INFORM Severity":"inform-severity-index/",
  "Acceso humanitario":"humanitarian-access/",
  "Eventos de acceso (historico)":"humanitarian-access-events/",
}

def run():
    key=os.getenv("ACAPS_API_TOKEN","").strip()
    if not key:raise SystemExit("Falta ACAPS_API_TOKEN")
    output={"fecha_utc":datetime.now(timezone.utc).isoformat(),
            "nota":"Estructuras de respuesta, nunca claves ni registros completos",
            "endpoints":{}}
    for name,path in ENDPOINTS.items():
        record={"estado":"NO_VERIFICADO","status":None,"columnas":[],"tipos":{},
                "cantidad_pagina":0,"total_api":None}
        try:
            r=requests.get(BASE+path,headers={"Authorization":"Token "+key,
                "Accept":"application/json"},timeout=45)
            record["status"]=r.status_code
            if r.status_code==200 and "json" in r.headers.get("Content-Type",""):
                o=r.json()
                if isinstance(o,dict):
                    records=o.get("results",[])
                    record["total_api"]=o.get("count")
                else:records=o
                if isinstance(records,list):
                    record["cantidad_pagina"]=len(records)
                    if records and isinstance(records[0],dict):
                        record["columnas"]=sorted(records[0])
                        record["tipos"]={k:type(v).__name__ for k,v in records[0].items()}
                    record["estado"]="CONECTADO"
                else:record["estado"]="ESQUEMA_DESCONOCIDO"
            elif r.status_code in (403,401):record["estado"]="NO_AUTORIZADO"
            elif r.status_code==404:record["estado"]="ENDPOINT_NO_DISPONIBLE"
            else:record["estado"]="RESPUESTA_NO_ESPERADA"
        except (requests.RequestException,ValueError):
            record["estado"]="ERROR_RED_O_JSON"
        output["endpoints"][name]=record
        print(name,record["estado"],record["status"],record["columnas"],flush=True)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":run()
