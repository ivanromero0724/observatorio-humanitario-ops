#!/usr/bin/env python3
"""Sondeo de filtros HAPI movilidad para evitar doble conteo sexo/edad."""
import json,os,requests
from pathlib import Path
from datetime import datetime,timezone
S=requests.Session()
API="https://hapi.humdata.org/api/v2/affected-people/refugees-persons-of-concern"
def get(key,host,extra):
    p={"app_identifier":key,"asylum_location_code":host,
       "start_date":"2024-01-01","output_format":"json","limit":5,
       "offset":0,**extra}
    try:
        r=S.get(API,params=p,timeout=50)
        if r.status_code!=200:return {"http":r.status_code}
        rows=r.json().get("data",[])
        return {"http":200,"n":len(rows),"muestra":[{
            "origen":v.get("origin_location_code"),
            "asilo":v.get("asylum_location_code"),
            "anio":str(v.get("reference_period_start"))[:4],
            "grupo":v.get("population_group"),
            "genero":v.get("gender"),"edad":v.get("age_range")}
            for v in rows]}
    except (requests.RequestException,ValueError):
        return {"http":"ERROR"}
def main():
    key=os.getenv("HDX_APP_IDENTIFIER","").strip()
    if not key:raise SystemExit("No key")
    out={"fecha_utc":datetime.now(timezone.utc).isoformat(),"casos":{}}
    for host in ["COL","HTI","VEN","BRA"]:
        for label,ex in [
            ("sin_filtros",{}),
            ("solo_total",{"gender":"all","age_range":"all"}),
            ("total_ref",{"gender":"all","age_range":"all","population_group":"REF"}),
            ("ref",{"population_group":"REF"}),
        ]:
            out["casos"][host+"_"+label]=get(key,host,ex)
            print(host,label,out["casos"][host+"_"+label].get("http"),
                  out["casos"][host+"_"+label].get("n"),flush=True)
    path=Path("docs/fase2/hapi_migracion_filtros.json")
    path.parent.mkdir(exist_ok=True,parents=True)
    path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__":main()
