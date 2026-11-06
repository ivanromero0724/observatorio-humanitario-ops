#!/usr/bin/env python3
"""Auditoría de conexión AWSD y ReliefWeb con secretos (sin registrar credenciales).

Este script evita imprimir urls o bodies que pudieran contener credenciales.
AWSD: prueba parámetros candidatos en modo diagnóstico, nunca publica incidentes.
ReliefWeb: POST oficial de solo lectura con appname autorizado.
"""
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/fase2/accesos_awsd_reliefweb.json"
S = requests.Session()
S.headers.update({"User-Agent": "ObservatorioHumanitarioOPS/0.4 (API access validation)"})

def status(code):
    return f"HTTP {code}" if isinstance(code,int) else "sin_respuesta"

def check_rw():
    secret = os.getenv("RELIEFWEB_APPNAME", "").strip()
    record = {"fuente":"ReliefWeb", "secreto_configurado":bool(secret),
              "estado":"SIN_SECRETO", "status":None, "cantidad_muestra":None,
              "total_reportes_globales":None, "campos_disponibles":[]}
    if not secret:return record
    try:
        r = S.post("https://api.reliefweb.int/v2/reports",
            params={"appname":secret},
            json={"profile":"list","limit":2,"preset":"latest"},
            timeout=35,allow_redirects=False)
        record["status"]=status(r.status_code)
        if r.status_code==200:
            obj=r.json()
            rows=obj.get("data",[])
            if not isinstance(rows,list):raise ValueError()
            record.update(estado="CONECTADO", cantidad_muestra=len(rows),
                total_reportes_globales=obj.get("totalCount"),
                campos_disponibles=sorted(rows[0].get("fields",{})) if rows else [])
        elif r.status_code in (401,403):
            record["estado"]="NO_AUTORIZADO"
        else: record["estado"]="RESPUESTA_INESPERADA"
    except (requests.RequestException,ValueError,TypeError):
        record["estado"]="ERROR_CONSULTA"
    return record

def check_awsd():
    key=os.getenv("AWSD_API_KEY","").strip()
    record={"fuente":"AWSD", "secreto_configurado":bool(key),
            "estado":"SIN_SECRETO", "metodo_autenticacion":None,
            "status":None,"tipo_respuesta":None,"columnas_ejemplo":[],
            "observacion":"No se publican incidentes, coordenadas ni claves."}
    if not key:return record
    url="https://www.aidworkersecurity.org/incidents/api"
    base={"detail":1,"format":"json","country":"CO"}
    # La página de AWSD indica que puede entregarse la API key en un
    # enlace directo, pero no publica el nombre del parámetro. Se prueban
    # convenciones comunes hasta encontrar JSON estructurado verificable.
    candidates=[
        ("key","query"),("api_key","query"),("apikey","query"),
        ("token","query"),("api-key","query"),
        ("Authorization Bearer","header"),
        ("X-API-Key","header"),
    ]
    statuses=[]
    for label,mode in candidates:
        try:
            p=dict(base);headers={"Accept":"application/json"}
            if mode=="query":p[label]=key
            elif label=="Authorization Bearer":headers["Authorization"]="Bearer "+key
            else:headers["X-API-Key"]=key
            r=S.get(url,params=p,headers=headers,timeout=25,
                    allow_redirects=False)
            statuses.append({label:r.status_code})
            if r.status_code!=200:continue
            try:obj=r.json()
            except ValueError:continue
            if isinstance(obj,list):
                rows=obj;keys=sorted(obj[0]) if obj and isinstance(obj[0],dict) else []
                useful=True
            elif isinstance(obj,dict):
                rows=(obj.get("data") or obj.get("results")
                      or obj.get("incidents") or [])
                keys=sorted(rows[0]) if isinstance(rows,list) and rows and isinstance(rows[0],dict) else sorted(obj)
                useful=("error" not in obj and ("data" in obj or "results" in obj or "incidents" in obj or "id" in obj))
            else:useful=False;rows=[];keys=[]
            if useful:
                record.update(estado="CONECTADO",metodo_autenticacion=label,
                    status=status(r.status_code),tipo_respuesta=type(obj).__name__,
                    columnas_ejemplo=keys[:70])
                break
        except (requests.RequestException,TypeError):
            statuses.append({label:"error_red"})
    if record["estado"]!="CONECTADO":
        record.update(estado="POR_VALIDAR", status="; ".join(
            str(list(item.values())[0]) for item in statuses))
        record["observacion"]="Key presente, pero no se identificó una respuesta JSON autorizada. Revisar enlace directo en correo de AWSD."
    return record

def main():
    record={"fecha_utc":datetime.now(timezone.utc).isoformat(),
            "uso":"Auditoría de conexión, sin publicación de microdatos",
            "resultados":[check_rw(),check_awsd()]}
    OUT.parent.mkdir(exist_ok=True,parents=True)
    OUT.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",
                   encoding="utf-8")
    print(json.dumps(record,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
