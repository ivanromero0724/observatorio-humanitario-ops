#!/usr/bin/env python3
"""Series agregadas AWSD e IDMC para el Observatorio OPS (solo 35 países).

No se almacenan incidentes, coordenadas, actores, detalles personales,
identificadores individuales, claves o URLs firmadas. Las cifras de GIDD
flujos (new_displacement) y stock (total_displacement) NO se suman entre sí.
IDU se inspecciona antes de decidir cómo resumir su esquema.
"""
from __future__ import annotations
import csv
import io
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit, parse_qs

import requests

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"data/observaciones"
META=ROOT/"docs/fase2/monitoreo_idmc_awsd.json"
CATALOG=ROOT/"data/catalogos/paises_americas.csv"
GIDD=DATA/"idmc_gidd_conflicto_pais_anio.csv"
AWSD=DATA/"awsd_seguridad_pais_anio.csv"
AWSD_TYPES=DATA/"awsd_tipos_pais_anio.csv"
IDU=DATA/"idmc_idu_pais_mes.csv"
S=requests.Session()
S.headers.update({"Accept":"application/json","User-Agent":"OPS-Observatorio-Humanitario/1.0"})
BASE="https://helix-tools-api.idmcdb.org/external-api/"
AWS_URL="https://www.aidworkersecurity.org/incidents/search"
S3_HOST="helix-copilot-prod-helix-media-external.s3.amazonaws.com"

def catalog():
    with CATALOG.open(encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==35
    return {r["iso3"]:r for r in rows}

def fetch(url,params=None,*,stream=False):
    # No incluir mensajes del proveedor en excepciones: podrían contener claves.
    try:
        r=S.get(url,params=params,timeout=(15,60),stream=stream,allow_redirects=False)
        return r
    except requests.RequestException:
        raise RuntimeError("Error de red durante extracción API") from None

def validated_json(response,*,expected=None):
    try:
        if response.status_code!=200:
            raise RuntimeError(f"Servicio responde HTTP {response.status_code}")
        result=response.json()
        if expected and not isinstance(result,expected):
            raise RuntimeError("Estructura JSON inesperada")
        return result
    except ValueError:
        raise RuntimeError("El proveedor no devolvió JSON válido") from None
    finally:
        response.close()

def write_csv(path,fields,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    # Escritura solo cuando la extracción ha terminado y fue validada.
    with path.open("w",newline="",encoding="utf-8") as f:
        out=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        out.writeheader()
        out.writerows(rows)

def as_nonnegative(v):
    if v is None or isinstance(v,bool) or str(v).strip().lower() in ("","none","nan","null","n/a"):
        return None
    try:
        x=float(str(v).replace(",",""))
        if not (0<=x<1e13):
            return None
        return x
    except (ValueError,TypeError):
        return None

def pretty_number(x):
    if x is None:return ""
    return str(int(x)) if x.is_integer() else str(x)

def idmc_gidd(token,cat,stamp):
    path="gidd/conflicts/"
    url=BASE+path
    results=[]
    seen_pages=set()
    params={"client_id":token,"format":"json","limit":500,"offset":0}
    declared=None
    for page in range(150):
        offset=int(params["offset"])
        if offset in seen_pages:raise RuntimeError("Paginación GIDD duplicada")
        seen_pages.add(offset)
        obj=validated_json(fetch(url,params),expected=dict)
        batch=obj.get("results")
        if not isinstance(batch,list):
            raise RuntimeError("GIDD sin lista results")
        declared=int(obj.get("count",-1))
        if declared<0 or declared>200000:
            raise RuntimeError("Total GIDD fuera de límites")
        results.extend(batch)
        nxt=obj.get("next")
        if not nxt:
            if len(results)!=declared:
                raise RuntimeError("GIDD incompleto: recuento de páginas no coincide")
            break
        qp=urlsplit(nxt)
        if qp.hostname!="helix-tools-api.idmcdb.org" or not qp.path.endswith(path):
            raise RuntimeError("Paginación GIDD fuera del endpoint permitido")
        qs=parse_qs(qp.query)
        newoffset=int(qs.get("offset",[len(results)])[0])
        if newoffset<=offset:raise RuntimeError("Paginación GIDD sin avance")
        params["offset"]=newoffset
        if "limit" in qs:params["limit"]=int(qs["limit"][0])
    else:raise RuntimeError("GIDD excede límite de páginas")
    out={}
    for row in results:
        if not isinstance(row,dict):raise RuntimeError("Fila GIDD no estructurada")
        iso=str(row.get("iso3","")).strip().upper()
        if iso not in cat:continue
        try:year=int(row.get("year"))
        except (TypeError,ValueError):continue
        if not 1990<=year<=datetime.now(timezone.utc).year:continue
        k=(iso,year)
        values=(as_nonnegative(row.get("new_displacement")),
                as_nonnegative(row.get("total_displacement")))
        if k in out and out[k]!=values:
            raise RuntimeError("Cifras GIDD diferentes para mismo país/año")
        out[k]=values
    if not out:raise RuntimeError("GIDD no devuelve registros para los 35 países")
    records=[{"iso3":iso,"anio":year,"nuevos_desplazamientos":pretty_number(vals[0]),
              "personas_desplazadas_fin_anio":pretty_number(vals[1]),
              "fuente":"IDMC GIDD conflictos","fecha_extraccion_utc":stamp}
             for (iso,year),vals in sorted(out.items())]
    write_csv(GIDD,["iso3","anio","nuevos_desplazamientos",
                    "personas_desplazadas_fin_anio","fuente",
                    "fecha_extraccion_utc"],records)
    return {"estado":"PUBLICADO","filas":len(records),
            "paises_con_registros":len({r["iso3"] for r in records}),
            "anio_min":min(r["anio"] for r in records),
            "anio_max":max(r["anio"] for r in records),
            "endpoint":"gidd/conflicts/", "registros_descargados":len(results)}

def awsd(token,cat,stamp):
    # Una llamada, no 35 consultas: minimizar riesgo de límite HTTP 429.
    obj=validated_json(fetch(AWS_URL,{"format":"json","api_key":token}),expected=list)
    code={p["iso2"].upper():iso for iso,p in cat.items()}
    byname={p["pais"].casefold():iso for iso,p in cat.items()}
    # Solo nombres ingleses seguros para los códigos de AWSD si no hay ISO.
    names={"colombia":"COL","haiti":"HTI","haití":"HTI","venezuela":"VEN",
        "dominican republic":"DOM","guatemala":"GTM","el salvador":"SLV",
        "honduras":"HND","brazil":"BRA","peru":"PER","mexico":"MEX",
        "ecuador":"ECU","united states":"USA","canada":"CAN",
        "argentina":"ARG","bolivia":"BOL","chile":"CHL","uruguay":"URY",
        "paraguay":"PRY","costa rica":"CRI","panama":"PAN",
        "nicaragua":"NIC","cuba":"CUB","trinidad and tobago":"TTO",
        "guyana":"GUY","suriname":"SUR","belize":"BLZ","jamaica":"JAM",
        "bahamas":"BHS","barbados":"BRB"}
    seen_ids=set()
    agg=defaultdict(list)
    duplicates=0
    for row in obj:
        if not isinstance(row,dict):raise RuntimeError("AWSD estructura inesperada")
        c=str(row.get("country_code") or "").strip().upper()
        iso=c if c in cat else code.get(c)
        if not iso:
            name=str(row.get("country") or "").strip().casefold()
            iso=byname.get(name) or names.get(name)
        if iso not in cat:continue
        try: year=int(row.get("year"))
        except (ValueError,TypeError):continue
        if not 1990<=year<=datetime.now(timezone.utc).year:continue
        incident=row.get("incident_id")
        if incident is not None and str(incident).strip():
            key=str(incident)
            if key in seen_ids:
                duplicates+=1
                continue
            seen_ids.add(key)
        agg[(iso,year)].append(row)
    if not agg:raise RuntimeError("AWSD sin incidentes de países del catálogo")
    rows=[]
    fields={"total_killed":"trabajadores_muertos",
            "total_wounded":"trabajadores_heridos",
            "total_kidnapped":"trabajadores_secuestrados",
            "total_affected":"trabajadores_afectados"}
    for (iso,year),items in sorted(agg.items()):
        r={"iso3":iso,"anio":year,"incidentes":len(items),
           "fecha_extraccion_utc":stamp}
        for key,outkey in fields.items():
            vals=[as_nonnegative(it.get(key)) for it in items]
            # Los incidentes con cifra ausente NO equivalen a cero.
            r[outkey]=(pretty_number(float(sum(x for x in vals if x is not None)))
                       if all(x is not None for x in vals) else "")
        rows.append(r)
    write_csv(AWSD,["iso3","anio","incidentes","trabajadores_muertos",
                    "trabajadores_heridos","trabajadores_secuestrados",
                    "trabajadores_afectados","fecha_extraccion_utc"],rows)
    # Un solo tipo principal por incidente, sin publicar identificadores.
    by_type={}
    for (iso,year),items in agg.items():
        for row in items:
            method=str(row.get("means_of_attack_description") or
                       row.get("means_of_attack") or "No especificado").strip()
            method=method[:85] or "No especificado"
            by_type.setdefault((iso,year,method),[]).append(row)
    typed=[]
    for (iso,year,method),items in sorted(by_type.items()):
        rec={"iso3":iso,"anio":year,"tipo_ataque":method,
             "incidentes":len(items),"fecha_extraccion_utc":stamp}
        for key,outkey in fields.items():
            vals=[as_nonnegative(x.get(key)) for x in items]
            rec[outkey]=(pretty_number(float(sum(x for x in vals if x is not None)))
                         if all(x is not None for x in vals) else "")
        typed.append(rec)
    assert sum(x["incidentes"] for x in typed)==sum(x["incidentes"] for x in rows)
    write_csv(AWSD_TYPES,["iso3","anio","tipo_ataque","incidentes",
              "trabajadores_muertos","trabajadores_heridos",
              "trabajadores_secuestrados","trabajadores_afectados",
              "fecha_extraccion_utc"],typed)
    return {"estado":"PUBLICADO","filas":len(rows),"desgloses_tipos":len(typed),
            "paises_con_registros":len({r["iso3"] for r in rows}),
            "anio_min":min(r["anio"] for r in rows),
            "anio_max":max(r["anio"] for r in rows),
            "incidentes_descargados":len(obj),
            "incidentes_region_tras_deduplicacion":sum(r["incidentes"] for r in rows),
            "ids_repetidos_omitidos":duplicates,
            "endpoint":"/incidents/search"}

def inspect_idu(token,cat,stamp):
    """Descarga solo para verificar ESQUEMA, sin guardar filas ni publicar cifras.
    El endpoint redirige a S3. Mantener URL firmada fuera de logs y archivos.
    """
    entry=fetch(BASE+"idus/last-180-days/",{"client_id":token,"format":"json"},stream=True)
    try:
        if entry.status_code!=302:raise RuntimeError(f"IDU HTTP {entry.status_code}")
        dest=urlsplit(urljoin(entry.url,entry.headers.get("Location","")))
        if dest.hostname!="helix-copilot-prod-helix-media-external.s3.amazonaws.com" or dest.scheme!="https":
            raise RuntimeError("IDU redirige a host no autorizado")
    finally:entry.close()
    res=fetch(dest.geturl(),stream=True)
    try:
        if res.status_code!=200:raise RuntimeError(f"IDU archivo HTTP {res.status_code}")
        raw=bytearray()
        for piece in res.iter_content(262144):
            raw.extend(piece)
            if len(raw)>32_000_000:
                return {"estado":"ARCHIVO_EXCEDE_32MB","nota":"No se publicó ningún dato"}
        obj=json.loads(raw)
    except (ValueError, UnicodeError):
        return {"estado":"JSON_NO_COMPLETO","nota":"No se publicó ningún dato"}
    finally:res.close()
    if isinstance(obj,dict):
        keys=sorted(obj)
        items=next((obj[k] for k in ("results","data","records","items") if isinstance(obj.get(k),list)),None)
        shape="dict"
    elif isinstance(obj,list):
        keys=[]
        items=obj
        shape="list"
    else:
        return {"estado":"ESQUEMA_DESCONOCIDO"}
    if not isinstance(items,list):
        return {"estado":"SIN_LISTA","forma":shape,"campos_superiores":keys[:35]}
    sample=[row for row in items if isinstance(row,dict)]
    # IDU puede aportar varias figuras para el MISMO evento: usar solo
    # cifras recomendadas, conflicto/violencia y contar eventos únicos
    # por país y mes del evento. NO sumar 'figure' ni publicar geometrías.
    event_groups=defaultdict(set)
    valid_conflict=0
    for row in sample:
        iso=str(row.get("iso3") or "").strip().upper()
        if iso not in cat:continue
        if str(row.get("displacement_type","")).casefold()!="conflict":
            continue
        if str(row.get("role","")).casefold()!="recommended figure":
            continue
        if as_nonnegative(row.get("figure")) is None:continue
        ident=row.get("event_id")
        if ident is None or not str(ident).strip():continue
        dt=None
        for name in ("displacement_start_date","displacement_date",
                     "event_start_date"):
            v=str(row.get(name) or "")[:10]
            try:
                dt=datetime.fromisoformat(v).date()
                break
            except ValueError:pass
        if dt is None:continue
        # La consulta es últimos 180 días de actualizaciones, pero las
        # fechas de eventos pueden ser más antiguas. Conservamos meses
        # reportados sin afirmar que cada evento haya comenzado hoy.
        if not 1990<=dt.year<=datetime.now(timezone.utc).year:continue
        period=dt.strftime("%Y-%m")
        event_groups[(iso,period)].add(str(ident))
        valid_conflict+=1
    idu_records=[{"iso3":iso,"anio":int(period[:4]),
                  "mes":int(period[5:7]),"periodo":period,
                  "actualizaciones":len(ids),"fecha_extraccion_utc":stamp}
                 for (iso,period),ids in sorted(event_groups.items())]
    write_csv(IDU,["iso3","anio","mes","periodo","actualizaciones",
                   "fecha_extraccion_utc"],idu_records)

    from collections import Counter
    summaries={}
    for key in ("displacement_type","category","type","displacement_occurred",
                "qualifier","role","year"):
        counts=Counter(str(row.get(key,""))[:60] for row in sample)
        summaries[key]=dict(counts.most_common(12))
    iso_codes=Counter(str(row.get("iso3",""))[:4] for row in sample)
    ids=[str(row.get("event_id")) for row in sample if row.get("event_id") is not None]
    figures_valid=sum(as_nonnegative(row.get("figure")) is not None for row in sample)
    return {"estado":"PUBLICADO" if idu_records else "SIN_REGISTROS",
            "forma":shape,
            "registros":len(items),"campos_superiores":keys[:35],
            "campos_registro":sorted(items[0].keys())[:70]
               if items and isinstance(items[0],dict) else [],
            "categorias":summaries,
            "iso3_35_paises":{k:v for k,v in iso_codes.items() if k in catalog()},
            "eventos_id_repetidos":len(ids)-len(set(ids)),
            "figuras_numericas":figures_valid,
            "eventos_idu_agrupados":len(idu_records),
            "paises_conflicto_con_registros":len({r["iso3"] for r in idu_records}),
            "registros_conflicto_recomendados_procesados":valid_conflict,
            "criterio":"event_id único por país y mes de inicio; sin sumar figuras"}

def main():
    cat=catalog()
    stamp=datetime.now(timezone.utc).isoformat()
    report={"fecha_utc":stamp,"alcance":"35 países OPS; solo agregados nacionales",
            "derechos":"IDMC: CC BY-NC-SA 3.0 IGO; AWSD: atribución a Humanitarian Outcomes",
            "awsd":{},"gidd":{},"idu":{}}
    g=os.getenv("IDMC_API_TOKEN","").strip()
    w=os.getenv("AWSD_API_KEY","").strip()
    if not g or not w:raise SystemExit("Faltan secretos IDMC_API_TOKEN o AWSD_API_KEY")
    failures=[]
    for name,fn in (("gidd",lambda:idmc_gidd(g,cat,stamp)),
                    ("awsd",lambda:awsd(w,cat,stamp)),
                    ("idu",lambda:inspect_idu(g,cat,stamp))):
        try:
            report[name]=fn()
        except Exception as exc:
            report[name]={"estado":"ERROR","clase":type(exc).__name__}
            failures.append(name)
    META.parent.mkdir(parents=True,exist_ok=True)
    META.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    # Retener datos ya publicados si una de las dos extracciones falla.
    if "gidd" in failures or "awsd" in failures:
        raise SystemExit("Extracción de una fuente principal incompleta")

if __name__=="__main__":main()
