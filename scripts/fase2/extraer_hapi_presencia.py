#!/usr/bin/env python3
"""HAPI 3W operational presence: cobertura de socios por sector.

Consulta íntegra por cada uno de 35 países, todos niveles. No publica
nombres de organizaciones ni pretende medir personas alcanzadas.
Los conteos de org son distintos por país, sector y corte de referencia.
"""
import csv,json,os,time
from datetime import datetime,timezone
from pathlib import Path
from collections import defaultdict
import requests
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"data/observaciones/hapi_presencia_sector.csv"
META=ROOT/"docs/fase2/hapi_presencia_actualizacion.json"
C=ROOT/"data/catalogos/paises_americas.csv"
API="https://hapi.humdata.org/api/v2/coordination-context/operational-presence"
SESSION=requests.Session()
SESSION.headers["User-Agent"]="ObservatorioHumanitarioOPS/1.0"
FIELDS=["iso3","sector_code","sector","fecha_hasta","organizaciones_distintas",
        "unidades_territoriales","filas_fuente","fecha_extraccion_utc"]
def pages(iso,key):
    result=[];fingerprints=set()
    for p in range(95):
        params={"app_identifier":key,"location_code":iso,
                "output_format":"json","limit":5000,"offset":p*5000}
        for a in range(4):
            try:
                r=SESSION.get(API,params=params,timeout=75)
                if r.status_code in (429,500,502,503,504) and a<3:
                    time.sleep(3*(a+1));continue
                if r.status_code!=200:raise RuntimeError("HAPI_HTTP_"+str(r.status_code))
                data=r.json()["data"]
                if not isinstance(data,list) or len(data)>5000:raise ValueError("data")
                break
            except (requests.RequestException,ValueError,KeyError):
                if a==3:raise RuntimeError("HAPI_REQUEST_ERROR") from None
                time.sleep(2*(a+1))
        for item in data:
            if str(item.get("location_code","")).upper()!=iso:
                raise RuntimeError("GEO_INCORRECTA")
            h=json.dumps(item,sort_keys=True,ensure_ascii=False,default=str)
            if h in fingerprints:continue
            fingerprints.add(h)
            result.append(item)
        if len(data)<5000:return result,p+1
    raise RuntimeError("PAGINACION_NO_COMPLETA")
def main():
    key=os.getenv("HDX_APP_IDENTIFIER","").strip()
    if not key:raise SystemExit("Falta HDX_APP_IDENTIFIER")
    with C.open(encoding="utf-8-sig",newline="") as f:
        countries=[r["iso3"] for r in csv.DictReader(f)]
    assert len(countries)==35
    today=datetime.now(timezone.utc).isoformat()
    all_rows=[];stats=[]
    for iso in countries:
        try:
            rows,n=pages(iso,key)
            stats.append({"iso3":iso,"filas":len(rows),"paginas":n,
                          "estado":"CON_DATOS" if rows else "SIN_REGISTROS"})
            print(iso,len(rows),"filas verificadas",flush=True)
            # Separar por sector y corte real; no juntar datos de años diferentes.
            groups=defaultdict(lambda:{"orgs":set(),"geo":set(),"count":0})
            for r in rows:
                sector=str(r.get("sector_code") or "").strip()
                name=str(r.get("sector_name") or sector).strip()
                date=str(r.get("reference_period_end") or "")[:10]
                org=str(r.get("org_name") or r.get("org_acronym") or "").strip().casefold()
                geo=(str(r.get("admin_level") or ""),
                     str(r.get("admin1_code") or r.get("admin1_name") or ""),
                     str(r.get("admin2_code") or r.get("admin2_name") or ""))
                if not sector or not org:continue
                g=groups[(sector,name,date)]
                g["orgs"].add(org)
                g["geo"].add(geo)
                g["count"]+=1
            # El corte de referencia es parte de la llave; no sumamos rondas.
            for (sector,name,date),g in groups.items():
                all_rows.append({"iso3":iso,"sector_code":sector,"sector":name,
                    "fecha_hasta":date,"organizaciones_distintas":len(g["orgs"]),
                    "unidades_territoriales":len(g["geo"]),
                    "filas_fuente":g["count"],"fecha_extraccion_utc":today})
        except Exception as e:
            print(iso,type(e).__name__,flush=True)
            raise
    OUT.parent.mkdir(exist_ok=True,parents=True)
    tmp=OUT.with_suffix(".tmp")
    with tmp.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(all_rows)
    tmp.replace(OUT)
    META.parent.mkdir(exist_ok=True,parents=True)
    meta={"fecha_extraccion_utc":today,"paises_consultados":35,
          "paises_con_datos":sum(x["estado"]=="CON_DATOS" for x in stats),
          "filas_resumen":len(all_rows),"detalle":stats,
          "advertencia":"Organizaciones distintas dentro de un sector y periodo; la misma organización puede operar en múltiples sectores y territorios. No sumar entre sectores, cortes ni países para estimar población atendida.",
          "estado":"COMPLETO"}
    META.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__":main()
