#!/usr/bin/env python3
"""Extracción completa de HAPI para 35 países, sin publicar filas subnacionales.

- Nunca escribe series si no terminó la paginación del país.
- No publica los identificadores ni URLs autenticadas.
- No suma tipos de eventos entre sí: las categorías se superponen.
- No mezcla admin0 con admin2 en la misma combinación país/mes/tipo.
- Publica solo totales mensuales por tipo, más estatus de validación.
"""
import csv
import json
import os
import re
import time
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
COUNTRIES = ROOT / "data/catalogos/paises_americas.csv"
OUT = ROOT / "data/observaciones/hapi_conflicto_pais_mes.csv"
META = ROOT / "docs/fase1/hapi_extraccion_completa.json"
API = "https://hapi.humdata.org/api/v2/coordination-context/conflict-events"
MAX_PAGES = 250
PAGE_SIZE = 10000
START_DATE = "2020-01-01"
DATE_RUN = datetime.now(timezone.utc).isoformat()
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "ObservatorioHumanitarioOPS/0.3 (auditoria de agregados HAPI)"

def get_page(iso, key, offset):
    params = {
        "app_identifier": key,
        "location_code": iso,
        "start_date": START_DATE,
        "output_format": "json",
        "limit": PAGE_SIZE,
        "offset": offset,
    }
    for attempt in range(4):
        try:
            r = SESSION.get(API, params=params, timeout=80)
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(2 * (attempt + 1))
                continue
            r.raise_for_status()
            obj = r.json()
            rows = obj["data"]
            if not isinstance(rows, list):
                raise ValueError("La respuesta no tiene data[]")
            return rows
        except (requests.RequestException, ValueError, KeyError):
            if attempt == 3:raise
            time.sleep(2 * (attempt + 1))

def month(text):
    s=str(text)[:7]
    return s if re.fullmatch(r"\d{4}-\d{2}",s) else None

def adm_level(v):
    try:
        raw = v.get("admin_level")
        if raw is not None and str(raw).isdigit():
            return int(raw)
    except (TypeError, ValueError):
        pass
    if v.get("admin2_code"):return 2
    if v.get("admin1_code"):return 1
    return 0

def norm_group(raw,iso):
    grouped=defaultdict(lambda: {"events":0,"fatalities":0,"fatalities_missing":0,
                                  "levels":set(),"n_rows":0,
                                  "geographies":{}})
    suspicious=Counter()
    removed_identical=0
    conflict_examples=[]
    for rec in raw:
        if str(rec.get("location_code","")).upper()!=iso:
            suspicious["wrong_country"]+=1
            continue
        d=month(rec.get("reference_period_start"))
        typ=str(rec.get("event_type") or "")
        if not d or typ not in {"political_violence","civilian_targeting","demonstration"}:
            suspicious["invalid_period_or_type"]+=1
            continue
        try:
            events=float(rec["events"])
        except (TypeError,ValueError,KeyError):
            suspicious["invalid_events"]+=1
            continue
        if not (events>=0 and events.is_integer()):
            suspicious["invalid_events"]+=1
            continue
        raw_fatalities=rec.get("fatalities")
        if raw_fatalities is None or str(raw_fatalities).strip()=="":
            fatalities=None
        else:
            try:
                fatalities=float(raw_fatalities)
                if not (fatalities>=0 and fatalities.is_integer()):
                    raise ValueError("invalid deaths")
            except (TypeError,ValueError):
                suspicious["invalid_fatalities"]+=1
                continue
        level=adm_level(rec)
        geo=(str(rec.get("admin1_code") or rec.get("admin1_name") or ""),
             str(rec.get("admin2_code") or rec.get("admin2_name") or ""))
        key=(iso,d,typ)
        g=grouped[key]
        # Deduplicar solo si TODO coincide (misma fuente, área y cifras).
        # Si hay valores en conflicto, el país sigue excluido por QA.
        stamp=(level,geo)
        signature=(int(events),None if fatalities is None else int(fatalities),
                   str(rec.get("resource_hdx_id") or ""),
                   str(rec.get("reference_period_end") or ""),
                   str(rec.get("admin1_name") or ""),
                   str(rec.get("admin2_name") or ""))
        if stamp in g["geographies"]:
            if g["geographies"][stamp]==signature:
                removed_identical+=1
                continue
            suspicious["conflicting_geo_month_type"]+=1
            if len(conflict_examples)<10:
                previous=g["geographies"][stamp]
                conflict_examples.append({
                    "mes":d,"tipo":typ,"geo":str(stamp),
                    "prev_events":previous[0],"actual_events":signature[0],
                    "prev_fatalities":previous[1],"actual_fatalities":signature[1],
                    "misma_fuente":previous[2]==signature[2],
                    "mismo_fin_periodo":previous[3]==signature[3],
                    "mismo_nombre_admin":previous[4:]==signature[4:],
                })
            continue
        g["geographies"][stamp]=signature
        g["events"]+=int(events)
        if fatalities is None:
            g["fatalities_missing"]+=1
        else:
            g["fatalities"]+=int(fatalities)
        g["levels"].add(level)
        g["n_rows"]+=1
    problems=[]
    for key,g in grouped.items():
        if len(g["levels"])>1:
            problems.append((key,"niveles_administrativos_mezclados"))
    if suspicious or problems:
        return [],{
            "errores":dict(suspicious),
            "mezclas_niveles":len(problems),
            "muestra":str(problems[:2])[:120],
            "conflictos_muestra":conflict_examples,
        },removed_identical
    output=[]
    for (iso,d,typ),g in sorted(grouped.items()):
        output.append({"iso3":iso,"periodo":d,"tipo_evento":typ,
            "eventos":g["events"],
            "muertes_reportadas":"" if g["fatalities_missing"] else g["fatalities"],
            "nivel_admin":next(iter(g["levels"])),"unidades_fuente":g["n_rows"],
            "fuente":"OCHA HDX HAPI / ACLED agregado",
            "consultado_utc":DATE_RUN})
    return output,{},removed_identical

def main():
    key=os.getenv("HDX_APP_IDENTIFIER","").strip()
    if not key:raise SystemExit("Falta HDX_APP_IDENTIFIER")
    with COUNTRIES.open(encoding="utf-8-sig",newline="") as f:
        countries=list(csv.DictReader(f))
    assert len(countries)==35
    clean=[];statuses=[]
    for c in countries:
        iso=c["iso3"]; raw=[]; reason="";complete=False
        try:
            for page in range(MAX_PAGES):
                rows=get_page(iso,key,page*PAGE_SIZE)
                raw.extend(rows)
                if len(rows)<PAGE_SIZE:
                    complete=True
                    break
        except Exception as e:
            reason="error_consulta_"+type(e).__name__
        if not complete and not reason:
            reason="paginacion_incompleta"
        agg=[];issues={};removed_identical=0
        if complete:
            agg,issues,removed_identical=norm_group(raw,iso)
            if issues:
                reason="validacion_geografica_o_numerica"
        if complete and not reason:
            clean.extend(agg)
        statuses.append({"iso3":iso,"pais":c["pais"],
            "estado":"COMPLETO" if complete and not reason else "EXCLUIDO",
            "paginas_descargadas":(len(raw)+PAGE_SIZE-1)//PAGE_SIZE,
            "registros_api":len(raw),"registros_mensuales":len(agg) if not reason else 0,
            "motivo_exclusion":reason,"resumen_inconsistencias":issues,
            "duplicados_identicos_eliminados":removed_identical})
        print(iso,statuses[-1]["estado"],"filas",len(raw),
              "mensuales",len(agg) if not reason else 0,
              "duplicados_idénticos_eliminados",removed_identical,reason,flush=True)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    fields=["iso3","periodo","tipo_evento","eventos","muertes_reportadas",
            "nivel_admin","unidades_fuente","fuente","consultado_utc"]
    with OUT.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(clean)
    stats={"fecha_utc":DATE_RUN,"fecha_inicio":START_DATE,"paises_esperados":len(countries),
        "paises_completos":sum(s["estado"]=="COMPLETO" for s in statuses),
        "paises_excluidos":[s["iso3"] for s in statuses if s["estado"]!="COMPLETO"],
        "filas_mensuales_publicadas":len(clean),
        "sin_credenciales_en_reporte":True,
        "metodologia":"Totales mensuales por tipo; NO sumar tipos. Una serie solo se incluye si se completó la paginación y pasó QA de geografía y números.",
        "paises":statuses}
    META.parent.mkdir(parents=True,exist_ok=True)
    META.write_text(json.dumps(stats,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("FIN",json.dumps({k:stats[k] for k in
          ["paises_esperados","paises_completos","paises_excluidos",
           "filas_mensuales_publicadas"]},ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
