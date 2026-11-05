#!/usr/bin/env python3
"""Evaluación del alcance regional (35 países soberanos) en HDX HAPI y OIM DTM.
Guarda SOLO metadatos de cobertura, nunca secretos, URLs autenticadas o microdatos.
El catálogo maestro es data/catalogos/paises_americas.csv.
"""
import contextlib
import csv
import io
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
CATALOGO = ROOT / "data/catalogos/paises_americas.csv"
SALIDA = ROOT / "docs/fase1"
HAPI_URL = "https://hapi.humdata.org/api/v2/coordination-context/conflict-events"
FECHA = datetime.now(timezone.utc).isoformat()
MAX_PAGINAS_HAPI = 15
TAMANO_PAGINA = 1000

# Se compara contra los nombres exactos de catálogo SOLO si no hay ISO3 en la fila.
ALIAS_INGLES = {
    "ATG": ["antigua and barbuda"],
    "BHS": ["bahamas", "the bahamas"],
    "BOL": ["bolivia", "bolivia (plurinational state of)"],
    "CAN": ["canada"],
    "COL": ["colombia"],
    "CRI": ["costa rica"],
    "CUB": ["cuba"],
    "DMA": ["dominica"],
    "DOM": ["dominican republic"],
    "ECU": ["ecuador"],
    "GTM": ["guatemala"],
    "GUY": ["guyana"],
    "HTI": ["haiti", "haïti"],
    "HND": ["honduras"],
    "JAM": ["jamaica"],
    "KNA": ["saint kitts and nevis", "st. kitts and nevis"],
    "LCA": ["saint lucia", "st. lucia"],
    "MEX": ["mexico"],
    "NIC": ["nicaragua"],
    "PAN": ["panama"],
    "PRY": ["paraguay"],
    "PER": ["peru"],
    "SLV": ["el salvador"],
    "SUR": ["suriname"],
    "TTO": ["trinidad and tobago"],
    "USA": ["united states", "united states of america"],
    "URY": ["uruguay"],
    "VCT": ["saint vincent and the grenadines", "st. vincent and the grenadines"],
    "VEN": ["venezuela", "venezuela (bolivarian republic of)"],
    "ARG": ["argentina"], "BLZ": ["belize"], "BRA": ["brazil"], "BRB": ["barbados"],
    "CHL": ["chile"], "GRD": ["grenada"],
}
S = requests.Session()
S.headers.update({"User-Agent": "observatorio-humanitario-ops/0.2 (regional coverage audit)"})

def paises():
    with CATALOGO.open(encoding="utf-8-sig",newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 35 and len({r["iso3"] for r in rows}) == 35
    return rows

def fila(country,fuente,estado,n=0,desde="",hasta="",detalle="",nivel=""):
    return {"iso3":country["iso3"],"pais":country["pais"],"subregion":country["subregion"],
        "fuente":fuente,"estado":estado,"filas_consultadas":n,
        "periodo_desde":desde,"periodo_hasta":hasta,
        "nivel_geografico":nivel,"detalle":detalle[:180],
        "fecha_consulta_utc":FECHA}

def request_hapi(iso,key,offset):
    # No se imprime ni se devuelve la URL (contiene el identificador en parámetros).
    params={"app_identifier":key,"location_code":iso,"limit":TAMANO_PAGINA,
            "offset":offset,"output_format":"json","start_date":"2020-01-01"}
    for attempt in range(3):
        try:
            r=S.get(HAPI_URL,params=params,timeout=45)
            if r.status_code in (429,500,502,503,504) and attempt<2:
                time.sleep(1.5*(attempt+1))
                continue
            return r
        except requests.RequestException:
            if attempt==2:raise
            time.sleep(1.5*(attempt+1))
    raise RuntimeError("No se completó la solicitud HAPI")

def hapi_regional(countries):
    result=[]
    key=os.getenv("HDX_APP_IDENTIFIER","").strip()
    for country in countries:
        iso=country["iso3"]
        if not key:
            result.append(fila(country,"HAPI conflicto 2020+","sin_credencial",
                               detalle="Secreto HDX_APP_IDENTIFIER no disponible"))
            continue
        num=0;dates=[];types=set();levels=set();error="";complete=False
        for page in range(MAX_PAGINAS_HAPI):
            try:
                r=request_hapi(iso,key,page*TAMANO_PAGINA)
            except requests.RequestException:
                error="error_red";break
            if r.status_code != 200:
                error=("acceso_rechazado" if r.status_code in (401,403)
                       else "error_api_http_"+str(r.status_code))
                break
            try:
                payload=r.json()
                rows=payload.get("data",[])
                if not isinstance(rows,list):raise ValueError("data no es lista")
            except (ValueError,TypeError):
                error="respuesta_no_json";break
            bad=[v for v in rows if v.get("location_code","").upper() not in ("",iso)]
            if bad:
                error="respuesta_pais_incorrecto";break
            num += len(rows)
            for v in rows:
                d=str(v.get("reference_period_start",""))[:10]
                if re.match(r"^\d{4}-\d{2}-\d{2}$",d):
                    dates.append(d)
                typ=v.get("event_type")
                if typ: types.add(str(typ))
                if v.get("admin2_code") or v.get("admin2_name"):levels.add("admin2")
                elif v.get("admin1_code") or v.get("admin1_name"):levels.add("admin1")
                else: levels.add("país")
            if len(rows)<TAMANO_PAGINA:
                complete=True;break
        status=("consulta_error" if error else
                "sin_registros_en_consulta" if num==0 else
                "cobertura_verificada" if complete else "paginacion_incompleta")
        detail=(error if error else
                "Filas de HAPI, no eventos únicos; categorías superpuestas: "
                +", ".join(sorted(types))+
                ("; paginación completada" if complete else "; límite de paginación"))
        result.append(fila(country,"HAPI conflicto 2020+",status,num,
                           min(dates) if dates else "",max(dates) if dates else "",
                           detail,"/".join(sorted(levels))))
        print("HAPI",iso,status,num,flush=True)
    return result

def normaliza(s):
    s=str(s).strip().lower()
    return re.sub(r"\s+"," ",s)

def match_pais(row,countries):
    # Match por ISO3 en cualquier columna. Evitar coincidencias parciales de nombres.
    values=[normaliza(v) for v in row.values() if v is not None]
    by_iso3={c["iso3"] for c in countries}
    for v in values:
        if v.upper() in by_iso3:
            return v.upper()
    for c in countries:
        candidates={normaliza(c["pais"]),*map(normaliza,ALIAS_INGLES.get(c["iso3"],[]))}
        if any(v in candidates for v in values):
            return c["iso3"]
    return None

def dtm_regional(countries,hna=False):
    source="OIM DTM HNA" if hna else "OIM DTM Baseline"
    env="DTMHNA_SUBSCRIPTION_KEY" if hna else "DTMAPI_SUBSCRIPTION_KEY"
    token=os.getenv(env,"").strip()
    if not token:
        return [fila(c,source,"sin_credencial",detalle=env+" no disponible")
                for c in countries], {"estado":"sin_credencial"}
    try:
        from dtmapi import DTMApi, DTMHnaApi
        # El cliente podría imprimir mensajes; no registrar salidas ni excepciones con claves.
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            client=(DTMHnaApi(subscription_key=token,timeout=30,max_retries=0)
                    if hna else DTMApi(subscription_key=token,api_version="v3",
                                       timeout=30,max_retries=0))
            catalog=client.get_all_countries()
        if not hasattr(catalog,"to_dict"):
            raise TypeError("El catálogo no es DataFrame")
    except Exception as exc:
        return [fila(c,source,"error_catalogo",detalle="Error "+type(exc).__name__)
                for c in countries], {"estado":"error_catalogo","error":type(exc).__name__}
    records=catalog.fillna("").to_dict(orient="records")
    mapping={}
    for rec in records:
        iso=match_pais(rec,countries)
        if iso:mapping.setdefault(iso,[]).append(rec)
    result=[]
    for c in countries:
        iso=c["iso3"]
        subset=mapping.get(iso,[])
        if not subset:
            result.append(fila(c,source,"sin_registros_catalogo",
                               detalle="El catálogo mundial API no incluye país; no equivale a cero desplazados"))
            continue
        # HNA está condicionada al año específico y se consulta en fase posterior
        if hna:
            result.append(fila(c,source,"catalogo_verificado",len(subset),
                               detalle="País con evaluaciones HNA; consultar años y admin2"))
            continue
        try:
            with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                data=client.get_idp_admin0_data(Admin0Pcode=iso)
            if not hasattr(data,"to_dict"):
                raise TypeError("Respuesta DTM no tabular")
            rows=data.fillna("").to_dict(orient="records")
            candidate_dates=[]
            for row in rows:
                for k,v in row.items():
                    if re.search(r"date|year|fecha",k,re.I):
                        d=str(v)[:10]
                        if re.match(r"^(19|20)\d{2}(-\d{2}(-\d{2})?)?$",d):
                            candidate_dates.append(d)
            result.append(fila(c,source,
                               "registros_verificados" if rows else "sin_filas_consulta_admin0",
                               len(rows),min(candidate_dates) if candidate_dates else "",
                               max(candidate_dates) if candidate_dates else "",
                               "Admin0; cada registro puede ser una ronda/operación, no agregar sin deduplicar",
                               "país"))
        except Exception as exc:
            result.append(fila(c,source,"error_consulta_admin0",
                               len(subset),detalle="Catálogo presente; "+type(exc).__name__))
        print(source,iso,result[-1]["estado"],result[-1]["filas_consultadas"],flush=True)
    return result,{"estado":"catalogo_descargado","filas_catalogo_mundial":len(records),
                   "paises_americas_catalogo":sorted(mapping),
                   "columnas_catalogo":list(catalog.columns)}

def main():
    countries=paises()
    hapi=hapi_regional(countries)
    dtm,dtm_stats=dtm_regional(countries)
    hna,hna_stats=dtm_regional(countries,hna=True)
    output=hapi+dtm+hna
    assert len(output)==len(countries)*3
    SALIDA.mkdir(parents=True,exist_ok=True)
    path=SALIDA/"cobertura_hapi_oim_americas.csv"
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(output[0]))
        w.writeheader();w.writerows(output)
    stats={}
    for fuente in ["HAPI conflicto 2020+","OIM DTM Baseline","OIM DTM HNA"]:
        subset=[v for v in output if v["fuente"]==fuente]
        stats[fuente]={"paises_evaluados":len(subset),
            "estados":dict(sorted(__import__("collections").Counter(r["estado"] for r in subset).items())),
            "paises_con_registros":[v["iso3"] for v in subset
                if v["estado"] in ("cobertura_verificada","paginacion_incompleta",
                                  "registros_verificados","catalogo_verificado")],
            "paises_sin_registros_catalogo":[v["iso3"] for v in subset
                if v["estado"]=="sin_registros_catalogo"]}
    summary={"fecha_ejecucion_utc":FECHA,
        "alcance":"35 países soberanos de las Américas; los territorios dependientes no están incluidos",
        "paises_catalogo":len(countries),
        "fuentes":stats,
        "dtm_catalogo":dtm_stats,"hna_catalogo":hna_stats,
        "interpretacion":"Una ausencia en API o catálogo no implica ausencia de amenazas o desplazamientos.",
        "advertencia_hapi":"Las 3 categorías ACLED agregadas HAPI no son mutuamente excluyentes; no sumar.",
        "advertencia_oim":"DTM cubre países/operaciones específicas y no necesariamente toda la región."}
    (SALIDA/"resumen_piloto_regional.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("RESUMEN SEGURO",json.dumps({"paises":len(countries),
        "estados_por_fuente":{k:v["estados"] for k,v in stats.items()}},ensure_ascii=False))

if __name__=="__main__":
    main()
