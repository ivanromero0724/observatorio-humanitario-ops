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
        for iso,alpha2,name in PAISES:
            d=by_iso2.get(alpha2)
            coverage.append(registro("WarMonit",iso,name,
                "registro_verificado" if d else "sin_registro_en_archivo",
                d.get("date","") if d else "",d.get("date","") if d else "",
                1 if d else 0,
                f"puntaje={d.get('score')}; tendencia={d.get('trend')}" if d else "No equivale a riesgo cero",
                WAR_URL))
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
        candidates=[x for x in summaries if x["iso3_americas_en_muestra"]>=5]
        for iso,a,name in PAISES:
            if candidates:
                coverage.append(registro(kind,iso,name,"archivo_descargado_requiere_mapeo_columnas",
                    detail="Archivo XLSX accesible; falta mapear hoja, campo ISO3, puntuación y fecha",
                    url=url))
            else:
                coverage.append(registro(kind,iso,name,"archivo_descargado_sin_mapeo_de_filas",
                    detail="No se identificó tabla estructurada; no inferir ausencia del país",url=url))
        return {"bytes":len(r.content),"hojas":len(sheets),"candidatas":len(candidates)}
    return try_source(kind,run,logs)

PAHO_NAMES = ["Coeficiente de GINI","Años de escolaridad promedio (en años)",
 "Razón de camas hospitalarias (1 000 habs)",
 "Densidad de Médicos/as (10 000 habs) [nuevo]",
 "Densidad de personal de enfermería (10 000 habs) [nuevo]",
 "Cobertura de inmunización en menores de 1 año (%), DTP3-vc",
 "Cobertura de inmunización en niños de 1 año (%), SRP1",
 "Tasa de mortalidad por homicidio (ajustada por edad por 100 000 habs)"]
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
        found={}
        headers=[]
        with z.open(largest) as f:
            reader=csv.DictReader(io.TextIOWrapper(f,encoding="utf-8-sig",errors="replace",newline=""))
            headers=reader.fieldnames or []
            for row in reader:
                name=row.get("nombre_indicador","").strip()
                iso=row.get("spatial_dim","").upper().strip()
                yr=row.get("time_dim","").strip()
                if name not in PAHO_NAMES or iso not in {x for x,_,_ in PAISES}: continue
                if not row.get("numeric_value","").strip():continue
                key=(iso,name)
                if yr.isdigit() and len(yr)==4:
                    found.setdefault(key,set()).add(int(yr))
        schema["OPS"]={"csv":largest,"headers":headers,"indicadores_filtrados":PAHO_NAMES,
                       "filas_pais_indicador":len(found)}
        for iso,a,pais in PAISES:
            for name in PAHO_NAMES:
                ys=found.get((iso,name),set())
                coverage.append(registro("OPS:"+name,iso,pais,
                    "registro_verificado" if ys else "sin_registro_en_extraccion",
                    min(ys) if ys else "",max(ys) if ys else "",len(ys),
                    "Serie país-año; no sumar sexos, urbano/rural y categorías",u))
        return {"bytes":len(data),"registros_pais_indicador":len(found),"csv":largest}
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
