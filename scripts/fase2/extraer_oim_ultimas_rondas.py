#!/usr/bin/env python3
"""Descargar series IDP agregadas OIM DTM Baseline y conservar última ronda/operación.

No se suman filas ni operaciones. Cada fila publicada conserva operación,
origen territorial, fecha, ronda y población reportada por el proveedor.
La falta de datos no equivale a cero desplazados. Se publican solo si todas las
consultas de los países catalogados se completaron con éxito.
"""
from __future__ import annotations
import csv
import json
import os
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
from dtmapi import DTMApi

ROOT=Path(__file__).resolve().parents[2]
STATUS=ROOT/"docs/fase1/resumen_piloto_regional.json"
OUT=ROOT/"data/observaciones/oim_dtm_ultima_ronda.csv"
META=ROOT/"docs/fase2/oim_actualizacion.json"
FIELDS=["iso3","operacion","fecha_reporte","anio_reporte","mes_reporte",
        "ronda","tipo_evaluacion","causa_desplazamiento","origen_admin1",
        "origen_admin1_codigo","personas_idp_reportadas","hombres","mujeres",
        "fecha_extraccion_utc"]

def main():
    key=os.getenv("DTMAPI_SUBSCRIPTION_KEY","").strip()
    if not key:raise SystemExit("Falta DTMAPI_SUBSCRIPTION_KEY")
    catalog=json.loads(STATUS.read_text(encoding="utf-8"))
    countries=catalog["fuentes"]["OIM DTM Baseline"]["paises_con_registros"]
    assert len(countries)>=1
    client=DTMApi(subscription_key=key,api_version="v3",
                  timeout=40,max_retries=1)
    all_rows=[];states=[];today=datetime.now(timezone.utc).isoformat()
    for iso in countries:
        try:
            df=client.get_idp_admin0_data(Admin0Pcode=iso)
            if not hasattr(df,"columns"):raise TypeError("No DataFrame")
            required={"operation","admin0Pcode","numPresentIdpInd",
                      "reportingDate","roundNumber"}
            if not required.issubset(df.columns):raise ValueError("Columnas faltantes")
            df=df[df["admin0Pcode"].astype(str).str.upper()==iso].copy()
            if df.empty:
                states.append({"iso3":iso,"estado":"SIN_FILAS","total":0,"ultimas":0})
                continue
            total_rows=len(df)
            df["_fecha"]=pd.to_datetime(df["reportingDate"],errors="coerce")
            if df["_fecha"].isna().any():raise ValueError("Fecha inválida")
            df["_ronda_num"]=pd.to_numeric(df["roundNumber"],errors="coerce")
            df["_num"]=pd.to_numeric(df["numPresentIdpInd"],errors="coerce")
            if df["_num"].isna().any() or (df["_num"]<0).any():
                raise ValueError("Población inválida")
            # Ultima combinación de fecha y ronda por operación. No se suman.
            df=df.sort_values(["operation","_fecha","_ronda_num"],
                              ascending=[True,False,False])
            latest=df.drop_duplicates("operation")[["operation","_fecha","_ronda_num"]]
            df=df.merge(latest,on=["operation","_fecha","_ronda_num"],
                        how="inner",validate="many_to_one")
            df=df.drop_duplicates(subset=[c for c in df.columns if c not in
                        ("_num","_ronda_num","_fecha")])
            for _,v in df.iterrows():
                def val(k):
                    x=v.get(k)
                    return "" if pd.isna(x) else str(x)
                all_rows.append({
                    "iso3":iso,"operacion":val("operation"),
                    "fecha_reporte":val("reportingDate")[:10],
                    "anio_reporte":val("yearReportingDate"),
                    "mes_reporte":val("monthReportingDate"),
                    "ronda":val("roundNumber"),
                    "tipo_evaluacion":val("assessmentType"),
                    "causa_desplazamiento":val("displacementReason"),
                    "origen_admin1":val("idpOriginAdmin1Name"),
                    "origen_admin1_codigo":val("idpOriginAdmin1Pcode"),
                    "personas_idp_reportadas":int(v["_num"]),
                    "hombres":val("numberMales"),
                    "mujeres":val("numberFemales"),
                    "fecha_extraccion_utc":today,
                })
            states.append({"iso3":iso,"estado":"OK",
                           "total":int(total_rows),
                           "ultimas":int(len(df)),
                           "operaciones":int(df["operation"].nunique())})
            print(iso,"OK",states[-1]["ultimas"],flush=True)
        except Exception as exc:
            states.append({"iso3":iso,"estado":"ERROR",
                           "motivo":type(exc).__name__})
            print(iso,"ERROR",type(exc).__name__,flush=True)
    if any(x["estado"]=="ERROR" for x in states):
        raise RuntimeError("Faltaron países; no publicar dataset parcial")
    OUT.parent.mkdir(exist_ok=True,parents=True)
    tmp=OUT.with_suffix(".tmp")
    with tmp.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(all_rows)
    tmp.replace(OUT)
    META.parent.mkdir(exist_ok=True,parents=True)
    result={"fecha_utc":today,"paises_catalogo_dtm":len(countries),
            "paises_con_datos":len({r["iso3"] for r in all_rows}),
            "registros_ultima_ronda":len(all_rows),
            "metodo":"Última fecha y ronda por operación; conservar filas de origen admin1, sin sumar operaciones ni rondas.",
            "precaucion":"Los campos de población pueden solaparse entre operaciones y lugares de origen. No representan un total nacional estandarizado.",
            "estado_paises":states}
    META.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("FIN",len(all_rows),"registros últimas rondas")

if __name__=="__main__":main()
