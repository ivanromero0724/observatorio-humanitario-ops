#!/usr/bin/env python3
"""Inspeccionar forma real de rondas nacionales de DTM (sin claves ni PII)."""
import json,os
from datetime import datetime,timezone
from pathlib import Path
from dtmapi import DTMApi

key=os.getenv("DTMAPI_SUBSCRIPTION_KEY","").strip()
if not key:raise SystemExit("Falta DTMAPI_SUBSCRIPTION_KEY")
c=DTMApi(subscription_key=key,api_version="v3",timeout=35,max_retries=0)
meta={"fecha_utc":datetime.now(timezone.utc).isoformat(),"muestras":{}}
for iso in ["HTI","ECU","PER","BOL","GTM"]:
    d={"estado":"NO_VERIFICADO","filas":None,"columnas":[],"tipos":{},
       "muestras_campos":{"no_contiene_datos_restringidos":True}}
    try:
        df=c.get_idp_admin0_data(Admin0Pcode=iso)
        d["estado"]="OK";d["filas"]=len(df);d["columnas"]=list(df.columns)
        if len(df):
            d["tipos"]={x:type(v).__name__ for x,v in df.iloc[0].items()}
            d["muestras_campos"]= {
                k:str(v)[:70] for k,v in df.iloc[0].items()
                if any(word in k.lower() for word in
                    ("country","admin0","round","year","month","date","population",
                     "individual","total","operation","assessment","idp"))
            }
    except Exception as e:
        d["estado"]="ERROR";d["error_type"]=type(e).__name__
    meta["muestras"][iso]=d
    print(iso,d["estado"],d["filas"],d["columnas"],flush=True)
out=Path("docs/fase2/oim_variables.json")
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
