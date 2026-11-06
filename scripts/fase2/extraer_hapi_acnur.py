#!/usr/bin/env python3
"""HAPI UNHCR personas de interés por país de acogida: totales sexo/edad.

Solo filas de fuente con gender=all y age_range=all; evita sumar
desagregaciones de mujeres/hombres y rangos etarios. Series desde 2024.
Consulta íntegra los 35 países de acogida. El año, origen y grupo se conservan.
No se imputan ceros y las categorías REF, ASY, etc. no se mezclan.
"""
import csv,json,os,time,math
from pathlib import Path
from datetime import datetime,timezone
import requests
ROOT=Path(__file__).resolve().parents[2]
CAT=ROOT/"data/catalogos/paises_americas.csv"
OUT=ROOT/"data/observaciones/hapi_acnur_acogida.csv"
META=ROOT/"docs/fase2/hapi_acnur_actualizacion.json"
API="https://hapi.humdata.org/api/v2/affected-people/refugees-persons-of-concern"
FIELDS=["asilo_iso3","origen_iso3","grupo_poblacion","anio",
        "personas","periodo_inicio","periodo_fin","fuente_recurso","fecha_extraccion_utc"]
S=requests.Session()
S.headers["User-Agent"]="ObservatorioHumanitarioOPS/1.1"
LIMIT=5000
def fetch(code,key):
    result=[];seen=set()
    for page in range(75):
        params={"app_identifier":key,"output_format":"json",
                "asylum_location_code":code,
                "gender":"all","age_range":"all",
                "start_date":"2024-01-01",
                "limit":LIMIT,"offset":page*LIMIT}
        for attempt in range(4):
            try:
                r=S.get(API,params=params,timeout=75)
                if r.status_code in (429,500,502,503,504) and attempt<3:
                    time.sleep(4*(attempt+1));continue
                if r.status_code!=200:raise RuntimeError("HTTP_ERROR_"+str(r.status_code))
                rows=r.json()["data"]
                if not isinstance(rows,list) or len(rows)>LIMIT:
                    raise ValueError("NO_DATA_LIST")
                break
            except (requests.RequestException,KeyError,ValueError):
                if attempt==3:raise RuntimeError("ERROR_API") from None
                time.sleep(3*(attempt+1))
        for row in rows:
            if str(row.get("asylum_location_code","")).upper()!=code:
                raise RuntimeError("WRONG_HOST")
            if str(row.get("gender","")).lower()!="all" or str(row.get("age_range","")).lower()!="all":
                raise RuntimeError("SEX_AGE_FILTER_FAILED")
            v=row.get("population")
            if not isinstance(v,(int,float)) or not math.isfinite(float(v)) or v<0:
                raise RuntimeError("BAD_POPULATION")
            sig=json.dumps(row,sort_keys=True,default=str)
            if sig in seen:continue
            seen.add(sig)
            result.append(row)
        if len(rows)<LIMIT:return result,page+1
    raise RuntimeError("PAGINATION_CAP")
def main():
    key=os.getenv("HDX_APP_IDENTIFIER","").strip()
    if not key:raise SystemExit("Sin HDX_APP_IDENTIFIER")
    with CAT.open(encoding="utf-8-sig",newline="") as f:
        codes=[r["iso3"] for r in csv.DictReader(f)]
    assert len(codes)==35
    now=datetime.now(timezone.utc).isoformat()
    out=[];check=[]
    for iso in codes:
        rows,pg=fetch(iso,key)
        check.append({"iso3":iso,"filas":len(rows),"paginas":pg,
            "estado":"CON_DATOS" if rows else "SIN_REGISTROS"})
        for r in rows:
            out.append({
                "asilo_iso3":iso,
                "origen_iso3":str(r.get("origin_location_code") or "").upper(),
                "grupo_poblacion":str(r.get("population_group") or ""),
                "anio":str(r.get("reference_period_start") or "")[:4],
                "personas":r.get("population"),
                "periodo_inicio":str(r.get("reference_period_start") or "")[:10],
                "periodo_fin":str(r.get("reference_period_end") or "")[:10],
                "fuente_recurso":str(r.get("resource_hdx_id") or ""),
                "fecha_extraccion_utc":now,
            })
        print(iso,len(rows),"registros totales sin desglose de sexo y edad",flush=True)
    keys=[(r["asilo_iso3"],r["origen_iso3"],r["grupo_poblacion"],r["anio"])
          for r in out]
    if len(set(keys))!=len(keys):raise RuntimeError("DUPLICATE_HOST_ORIGIN_GROUP_YEAR")
    OUT.parent.mkdir(exist_ok=True,parents=True)
    tmp=OUT.with_suffix(".tmp")
    with tmp.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(out)
    tmp.replace(OUT)
    META.parent.mkdir(exist_ok=True,parents=True)
    m={"fecha_extraccion_utc":now,"paises_acogida_consultados":35,
       "paises_con_registros":sum(x["estado"]=="CON_DATOS" for x in check),
       "filas":len(out),"desde":"2024-01-01","estado":"COMPLETO",
       "filtros":{"gender":"all","age_range":"all"},
       "advertencias":["Categorías REF/ASY/OIP/etc. no son sinónimos.",
         "Una persona en acogida no debe contarse como un desplazamiento interno.",
         "Las cifras describen poblaciones (stocks), no movimientos del año.",
         "No sumar categorías distintas como si fueran grupos mutuamente excluyentes.",
         "Conservar país de origen, país de acogida, categoría y año."],
       "detalle":check}
    META.write_text(json.dumps(m,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("FIN",len(out),"filas")
if __name__=="__main__":main()
