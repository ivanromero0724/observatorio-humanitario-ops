#!/usr/bin/env python3
"""Fase 1: inventario automatizado de disponibilidad, NO un índice OPS.
Fuentes: WarMonit (datos CC BY 4.0), INFORM Risk/Severity, OPS y ACNUR.
Sólo se publican metadatos/cobertura; no se guardan bases originales en GitHub.
"""
import argparse
import csv
import io
import json
import os
import re
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
import requests

PAISES = [
("ATG","AG","Antigua y Barbuda"),("ARG","AR","Argentina"),("BHS","BS","Bahamas"),
("BRB","BB","Barbados"),("BLZ","BZ","Belice"),("BOL","BO","Bolivia"),
("BRA","BR","Brasil"),("CAN","CA","Canadá"),("CHL","CL","Chile"),
("COL","CO","Colombia"),("CRI","CR","Costa Rica"),("CUB","CU","Cuba"),
("DMA","DM","Dominica"),("DOM","DO","República Dominicana"),
("ECU","EC","Ecuador"),("SLV","SV","El Salvador"),("GRD","GD","Granada"),
("GTM","GT","Guatemala"),("GUY","GY","Guyana"),("HTI","HT","Haití"),
("HND","HN","Honduras"),("JAM","JM","Jamaica"),("MEX","MX","México"),
("NIC","NI","Nicaragua"),("PAN","PA","Panamá"),("PRY","PY","Paraguay"),
("PER","PE","Perú"),("KNA","KN","San Cristóbal y Nieves"),
("LCA","LC","Santa Lucía"),("VCT","VC","San Vicente y las Granadinas"),
("SUR","SR","Surinam"),("TTO","TT","Trinidad y Tobago"),
("USA","US","Estados Unidos"),("URY","UY","Uruguay"),
("VEN","VE","Venezuela")]
PILOTO = ["COL","HTI","VEN","ECU","PAN"]
RISK_URL = "https://drmkc.jrc.ec.europa.eu/inform-index/Portals/0/InfoRM/2026/INFORM_Risk_Mid_2026_v073.xlsx"
SEVERITY_URL = "https://drmkc.jrc.ec.europa.eu/inform-index/Portals/0/InfoRM/Severity/2026/202609%20INFORM%20Severity%20-%20September%202026.xlsx"
PAHO_PAGE = "https://opendata.paho.org/es/indicadores-basicos/descarga-datos"
WAR_URL = "https://warmonit.com/data/cii.json"
UNHCR_URL = "https://api-data.unhcr.org/api/v0/data/PopStatsOfficial"
HAPI_URL = "https://hapi.humdata.org/api/v2/coordination-context/conflict-events"
DATA_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
S = requests.Session()
S.headers["User-Agent"] = "ObservatorioHumanitarioOPS-Fase1/0.1 (estudio de cobertura; contacto institucional pendiente)"

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            self.hrefs += [v for k,v in attrs if k=="href" and v]

def fetch(url, params=None, timeout=70):
    r=S.get(url,params=params,timeout=timeout)
    r.raise_for_status()
    return r

def registro(source,iso,pais,status,period_start="",period_end="",rows="",detail="",url=""):
    return {"fuente":source,"iso3":iso,"pais":pais,"estado":status,
        "primer_periodo":str(period_start),"ultimo_periodo":str(period_end),
        "registros":str(rows),"detalle":str(detail)[:220],"url":url,"ejecutado_utc":DATA_DATE}

def try_source(name, callback, logs):
    try:
        value=callback()
        logs[name]={"estado":"descarga_ok","detalle":str(value)[:200]}
        print(name, "OK", str(value)[:150],flush=True)
        return value
    except Exception as exc:
        logs[name]={"estado":"error_fuente","detalle":str(exc)[:300]}
        print(name, "ERROR",type(exc).__name__,str(exc)[:200],flush=True)
        return None

def war(coverage,logs):
    def run():
        body=fetch(WAR_URL).json()
        rows=body.get("rows",[])
        if not isinstance(rows,list) or len(rows)<10:
            raise ValueError("JSON sin arreglo rows válido")
        by_iso2={r.get("country_code"):r for r in rows}
        selected=[]
        for iso,alpha2,name in PAISES:
            d=by_iso2.get(alpha2)
            if d:
                selected.append({"iso3":iso,"pais":name,"fecha":d.get("date"),
                    "score":d.get("score"),"baseline":d.get("baseline"),
                    "dynamic":d.get("dynamic"),"trend":d.get("trend"),
                    "fuente":WAR_URL,"licencia":"CC BY 4.0"})
            coverage.append(registro("WarMonit",iso,name,
                "registro_verificado" if d else "sin_registro_en_archivo",
                d.get("date","") if d else "",d.get("date","") if d else "",
                1 if d else 0,
                f"puntaje={d.get('score')}; tendencia={d.get('trend')}" if d else "No equivale a riesgo cero",
                WAR_URL))
        if selected:
            directory=Path("data/observaciones");directory.mkdir(parents=True,exist_ok=True)
            with (directory/"warmonit_cii_ultimo.csv").open("w",encoding="utf-8",newline="") as fh:
                w=csv.DictWriter(fh,fieldnames=list(selected[0]));w.writeheader();w.writerows(selected)
        return {"total_mundial":len(rows),"americas":sum(1 for _,s,_ in PAISES if s in by_iso2),
                "fecha":body.get("date"),"licencia":body.get("license",{}).get("id")}
    return try_source("WarMonit",run,logs)

NS={"m":"http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r":"http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
def xlsx_sheets(data):
    """Lee contenido tabular limitado de XLSX sin ejecutar fórmulas ni macros."""
    z=zipfile.ZipFile(io.BytesIO(data))
    strings=[]
    if "xl/sharedStrings.xml" in z.namelist():
        root=ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall("m:si",NS):
            strings.append("".join(t.text or "" for t in si.findall(".//m:t",NS)))
    wb=ET.fromstring(z.read("xl/workbook.xml"))
    sheetnames=[x.attrib.get("name","") for x in wb.findall(".//m:sheets/m:sheet",NS)]
    manifest={n for n in z.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml",n)}
    result=[]
    for n in range(1,len(sheetnames)+1):
        p=f"xl/worksheets/sheet{n}.xml"
        if p not in manifest:
            continue
        with z.open(p) as file:
            # Iterparse avoids decoding every worksheet into a large DOM
            seen=[]
            for event,row in ET.iterparse(file,events=("end",)):
                if row.tag != "{%s}row"%NS["m"]:
                    continue
                cols={}
                for cell in row.findall("m:c",NS):
                    addr=cell.attrib.get("r","")
                    col=re.match(r"[A-Z]+",addr)
                    if not col:continue
                    colid=col.group()
                    t=cell.attrib.get("t")
                    v=cell.find("m:v",NS)
                    inline=cell.find("m:is",NS)
                    content=(v.text or "") if v is not None else ""
                    if t=="s":
                        try:content=strings[int(content)]
                        except (IndexError,ValueError):content=""
                    elif t=="inlineStr" and inline is not None:
                        content="".join(e.text or "" for e in inline.findall(".//m:t",NS))
                    if content.strip():cols[colid]=content[:90]
                if cols:
                    seen.append(cols)
                row.clear()
                if len(seen)>=1500:
                    break
        result.append((sheetnames[n-1],seen))
    return result

def inform(kind,url,coverage,logs,schema):
    def run():
        r=fetch(url,timeout=110)
        if not r.content.startswith(b"PK"):
            raise ValueError(f"Respuesta no XLSX: {r.headers.get('Content-Type')}")
        sheets=xlsx_sheets(r.content)
        summaries=[]
        for name,rs in sheets:
            tokens={x for row in rs for x in row.values()}
            hits=[iso for iso,a,n in PAISES if iso in tokens]
            # Looking up an ISO code anywhere is a weak signal; do not call it verified coverage.
            summaries.append({"hoja":name,"filas_leidas":len(rs),"iso3_pilotos":[x for x in hits if x in PILOTO],
                "iso3_americas_en_muestra":len(hits),"muestra_primera_fila":list(rs[0].values())[:14] if rs else []})
        schema[kind]=summaries[:45]
        wanted = ("INFORM Risk 2026 (a-z)" if kind == "INFORM_Risk"
                  else "INFORM Severity - hidden")
        target = next(((n,rs) for n,rs in sheets if n == wanted),None)
        found={}
        normalized=[]
        if target:
            rows=target[1]
            header=next((r for r in rows[:12] if "ISO3" in r.values()
                         and ("INFORM RISK" in r.values() or "INFORM Severity Index" in r.values())),None)
            if header:
                reverse={v:k for k,v in header.items()}
                code_col=reverse["ISO3"]
                score_col=(reverse["INFORM RISK"] if kind=="INFORM_Risk"
                           else reverse["INFORM Severity Index"])
                for row in rows:
                    iso=row.get(code_col,"").strip().upper()
                    if iso not in {x[0] for x in PAISES}:continue
                    raw=row.get(score_col,"").strip()
                    try:score=float(raw)
                    except (TypeError,ValueError):continue
                    if 0<=score<=10:
                        found.setdefault(iso,[]).append(score)
                        normalized.append({
                            "iso3":iso,
                            "pais":next(n for k,a,n in PAISES if k==iso),
                            "edicion":"Mid 2026" if kind=="INFORM_Risk" else "Septiembre 2026",
                            "puntuacion":score,
                            "crisis_id":row.get(reverse.get("CRISIS ID",""),"") if kind=="INFORM_Severity" else "",
                            "crisis":row.get(reverse.get("CRISIS",""),"") if kind=="INFORM_Severity" else "",
                            "fuente":url
                        })
        if normalized:
            directory=Path("data/observaciones")
            directory.mkdir(parents=True,exist_ok=True)
            filename=("inform_risk_mid_2026.csv" if kind=="INFORM_Risk"
                      else "inform_severity_2026_09_crisis.csv")
            with (directory/filename).open("w",encoding="utf-8",newline="") as fh:
                writer=csv.DictWriter(fh,fieldnames=list(normalized[0]))
                writer.writeheader()
                writer.writerows(normalized)
        schema[kind+"_parse"]={"hoja":wanted,"paises_con_puntaje":len(found),
            "registros_entre_paises":sum(len(x) for x in found.values()),
            "ejemplo_piloto":{iso:found.get(iso,[])[:4] for iso in PILOTO}}
        for iso,a,name in PAISES:
            scores=found.get(iso,[])
            coverage.append(registro(kind,iso,name,
                "puntuacion_verificada" if scores else "sin_puntuacion_en_hoja",
                "2026" if kind=="INFORM_Risk" and scores else ("2026-09" if scores else ""),
                "2026" if kind=="INFORM_Risk" and scores else ("2026-09" if scores else ""),
                len(scores),
                ("valor="+str(scores[0]) if kind=="INFORM_Risk"
                 else "crisis="+str(len(scores))+"; máximo="+str(max(scores))) if scores
                else "Ausencia en tabla seleccionada no equivale a puntaje cero",
                url=url))
        return {"bytes":len(r.content),"hojas":len(sheets),
                "paises_con_puntaje":len(found)}
    return try_source(kind,run,logs)

PAHO_PATTERNS = {
    "GINI": r"^GINI Index$",
    "Escolaridad": r"^Mean years of schooling \(years\)$",
    "Camas hospitalarias": r"^Hospital beds ratio \(1 000 pop\)$",
    "Médicos": r"^Density of medical doctors \(10 000 pop\)$",
    "Enfermería": r"^Density of nursing personnel \(10 000 pop\)$",
    "DTP3": r"^Immunization coverage of under-1 year old \(%\), DTP3-cv$",
    "SRP1": r"^Immunization coverage of 1 year old \(%\), MMR1$",
    "Mortalidad por homicidio": r"^Homicide mortality rate \(age-adjusted per 100 000 pop\)$",
}
def paho(coverage,logs,schema):
    def run():
        page=fetch(PAHO_PAGE,timeout=50)
        parser=Links()
        parser.feed(page.text)
        urls=[urljoin(PAHO_PAGE,h) for h in parser.hrefs if re.search(r"\.zip(?:\?|$)",h,re.I)]
        if not urls:
            # A page can be accessible while the direct bulk-data link is not discoverable.
            raise ValueError("Página accesible, enlace ZIP no encontrado en HTML: comprobar interfaz manual")
        downloaded=None
        tried=[]
        for u in urls[:10]:
            try:
                r=fetch(u,timeout=125)
                if r.content.startswith(b"PK"):
                    downloaded=(u,r.content)
                    break
            except requests.RequestException as exc:
                tried.append(str(exc)[:60])
        if not downloaded:
            raise ValueError("ZIP no descargable desde los enlaces detectados: "+";".join(tried))
        u,data=downloaded
        z=zipfile.ZipFile(io.BytesIO(data))
        candidates=[k for k in z.namelist() if k.lower().endswith(".csv")]
        if not candidates: raise ValueError("ZIP sin CSV")
        largest=max(candidates,key=lambda k:z.getinfo(k).file_size)
        found={};samples=[];matched={};records={};conflicts=0
        headers=[]
        with z.open(largest) as f:
            reader=csv.DictReader(io.TextIOWrapper(f,encoding="utf-8-sig",errors="replace",newline=""))
            headers=reader.fieldnames or []
            for row in reader:
                name=row.get("label_en","").strip()
                iso=row.get("country_code_iso3","").upper().strip()
                yr=row.get("period_id","").strip()
                if iso not in {x for x,_,_ in PAISES}:continue
                if len(samples)<30 and name and name not in samples:samples.append(name)
                kind=next((k for k,p in PAHO_PATTERNS.items()
                           if re.search(p,name,re.I)),None)
                if not kind or not row.get("val","").strip():continue
                key=(iso,kind)
                if re.match(r"^20[0-9]{2}$",yr):
                    found.setdefault(key,set()).add(int(yr))
                    matched.setdefault(kind,set()).add(name)
                    try:
                        numeric=float(row.get("val",""))
                    except (TypeError,ValueError):
                        continue
                    record={"iso3":iso,"indicador":kind,"periodo":int(yr),
                        "valor":numeric,"etiqueta_fuente":name,
                        "indicator_id":row.get("indicator_id",""),
                        "source_url":row.get("source_url","") or PAHO_PAGE,
                        "preliminar":row.get("preliminary",""),
                        "edicion":"OPS octubre 2026"}
                    records.setdefault((iso,kind,int(yr)),[]).append(record)
        normalized=[]
        for key,group in sorted(records.items()):
            uniques={x["valor"] for x in group}
            if len(uniques)!=1:
                conflicts += 1
                continue
            normalized.append(group[0])
        if normalized:
            directory=Path("data/observaciones")
            directory.mkdir(parents=True,exist_ok=True)
            with (directory/"ops_8_indicadores_pais_anio.csv").open("w",encoding="utf-8",newline="") as fh:
                w=csv.DictWriter(fh,fieldnames=list(normalized[0]))
                w.writeheader();w.writerows(normalized)
        schema["OPS"]={"csv":largest,"headers":headers,"etiquetas_ejemplo":samples,
                       "etiquetas_seleccionadas":{k:sorted(v)[:12] for k,v in matched.items()},
                       "filas_pais_indicador":len(found),
                       "filas_pais_anio_normalizadas":len(normalized),
                       "claves_con_valores_contradictorios_excluidas":conflicts}
        for iso,a,pais in PAISES:
            for name in PAHO_PATTERNS:
                ys=found.get((iso,name),set())
                coverage.append(registro("OPS:"+name,iso,pais,
                    "registro_verificado" if ys else "sin_registro_en_extraccion",
                    min(ys) if ys else "",max(ys) if ys else "",len(ys),
                    "Serie país-año; no sumar sexos, urbano/rural y categorías",u))
        return {"bytes":len(data),"registros_pais_indicador":len(found),
                "registros_pais_anio":len(normalized),"conflictos_excluidos":conflicts,
                "csv":largest}
    return try_source("OPS",run,logs)

def unhcr(coverage,logs):
    def run():
        ok=0
        for iso,a,pais in PAISES:
            if iso not in PILOTO:continue
            for pop in ["REF_UNHCR","ASY"]:
                p={"c[pop_type]":pop,"c[ref_area_adm0]":iso,
                    "time_period":"ge:2020","dimensions":"default","page_size":100,"page":1}
                try:
                    d=fetch(UNHCR_URL,p,timeout=55).json()
                    rows=d.get("data",[])
                    paging=d.get("pagination",{})
                    periods=sorted({r.get("time_period","") for r in rows if r.get("time_period")})
                    status="muestra_verificada" if rows else "sin_registros_en_consulta"
                    coverage.append(registro("ACNUR:"+pop,iso,pais,status,
                        periods[0] if periods else "",periods[-1] if periods else "",
                        paging.get("total_rows",len(rows)),
                        "Consulta de una página; total_rows según API; no implica extracción completa",
                        UNHCR_URL))
                    ok += 1
                except Exception as exc:
                    coverage.append(registro("ACNUR:"+pop,iso,pais,"error_consulta",
                        detail=str(exc)[:140],url=UNHCR_URL))
                time.sleep(0.15)
        return {"consultas":10,"respuestas_json":ok}
    return try_source("ACNUR",run,logs)

def hapi(coverage,logs):
    app_id=os.getenv("HDX_APP_IDENTIFIER")
    if not app_id:
        logs["HAPI"]={"estado":"requiere_identificador_institucional",
            "detalle":"No generar identificadores con correos inventados"}
        for iso,a,pais in PAISES:
            if iso in PILOTO:
                coverage.append(registro("HAPI conflicto",iso,pais,"pendiente_identificador",
                    detail="Proporcionar HDX_APP_IDENTIFIER institucional",url=HAPI_URL))
        return
    def run():
        for iso,a,pais in PAISES:
            if iso not in PILOTO:continue
            try:
                d=fetch(HAPI_URL,{"app_identifier":app_id,
                    "location_code":iso.lower(),"limit":1000,"offset":0,
                    "output_format":"json"},timeout=90).json()
                rows=d.get("data",[])
                dates=sorted({str(x.get("reference_period_start",""))[:10] for x in rows
                              if x.get("reference_period_start")})
                coverage.append(registro("HAPI conflicto",iso,pais,
                    "muestra_verificada" if rows else "sin_registros_en_consulta",
                    dates[0] if dates else "", dates[-1] if dates else "",len(rows),
                    "Sólo primera página: verificar offset total; clases no excluyentes",HAPI_URL))
            except Exception as exc:
                coverage.append(registro("HAPI conflicto",iso,pais,"error_consulta",
                     detail=str(exc)[:140],url=HAPI_URL))
        return "5 consultas piloto efectuadas"
    return try_source("HAPI",run,logs)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="docs/fase1/resultados_cobertura.csv")
    p.add_argument("--report",default="docs/fase1/ejecucion_fuentes.json")
    p.add_argument("--schema",default="docs/fase1/esquemas_fuentes.json")
    args=p.parse_args()
    coverage=[];logs={};schema={}
    war(coverage,logs)
    inform("INFORM_Risk",RISK_URL,coverage,logs,schema)
    inform("INFORM_Severity",SEVERITY_URL,coverage,logs,schema)
    paho(coverage,logs,schema)
    unhcr(coverage,logs)
    hapi(coverage,logs)
    fuentes_esenciales = ["WarMonit","INFORM_Risk","INFORM_Severity","OPS","ACNUR"]
    fallidas = [x for x in fuentes_esenciales
                if logs.get(x,{}).get("estado") != "descarga_ok"]
    if fallidas:
        raise SystemExit("Extracción incompleta. Se preserva el corte publicado. Fuentes: "
                         + ", ".join(fallidas))
    for filename, obj in [(args.report,{"fecha_utc":DATA_DATE,"estado":logs,
                          "observacion":"Cobertura exploratoria; no equivale a aprobación metodológica"}),
                          (args.schema,schema)]:
        path=Path(filename);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    fields=["fuente","iso3","pais","estado","primer_periodo","ultimo_periodo",
           "registros","detalle","url","ejecutado_utc"]
    with out.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(coverage)
    print("FINAL:",len(coverage),"filas de cobertura",json.dumps(logs,ensure_ascii=False))
    return 0

if __name__=="__main__":
    sys.exit(main())
