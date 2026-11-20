#!/usr/bin/env python3
"""Auditoría segura de IDMC y AWSD mediante GitHub Actions.

No muestra secretos, URLs autenticadas, cabeceras ni cuerpos completos.
Solo publica códigos HTTP, formas JSON y nombres de campos sin datos.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests

OUT=Path("docs/fase2/estado_awsd_idmc.json")
USER_AGENT="OPS-Humanitarian-Observatory/1.0 (API connectivity audit)"
S=requests.Session()
S.headers.update({"User-Agent":USER_AGENT,"Accept":"application/json"})
S.trust_env=True

def response_profile(response):
    """Inspección acotada de contenido; nunca devuelve contenido de filas."""
    data={"http":response.status_code,
          "content_type":response.headers.get("Content-Type","").split(";")[0][:75],
          "redirect":response.is_redirect}
    if response.is_redirect:
        data["estado"]="REDIRECCION_NO_SEGUIDA"
        return data
    try:
        # Respuestas grandes: solo leer la primera sección; JSON se valida
        # completo exclusivamente si cabe en 1 MB.
        limit=1_000_000
        raw=bytearray()
        for chunk in response.iter_content(chunk_size=65536):
            raw.extend(chunk)
            if len(raw)>limit:
                break
        data["bytes_primera_muestra"]=min(len(raw),limit)
        data["limite_muestra_alcanzado"]=len(raw)>limit
        if not raw:
            data["estado"]="VACIO"
            return data
        try:
            obj=json.loads(raw) if len(raw)<=limit else None
        except (ValueError, UnicodeError):
            obj=None
        if isinstance(obj,(list,dict)):
            data["estado"]="JSON_VALIDO"
            data["json_forma"]=type(obj).__name__
            if isinstance(obj,list):
                data["registros_muestra"]=len(obj)
                if obj and isinstance(obj[0],dict):
                    data["campos_registro"]=sorted(map(str,obj[0].keys()))[:55]
            else:
                data["campos_superiores"]=sorted(map(str,obj.keys()))[:55]
                for field in ("data","results","features","items","records"):
                    value=obj.get(field)
                    if isinstance(value,list):
                        data["contenedor"]=field
                        data["registros_muestra"]=len(value)
                        if value and isinstance(value[0],dict):
                            data["campos_registro"]=sorted(map(str,value[0].keys()))[:55]
                        break
            return data
        # Respuesta grande no completa: inspección conservadora de encabezado,
        # sin presentar claves sensibles ni datos de filas.
        sample=bytes(raw[:250])
        data["estado"]=("JSON_GRANDE_PARCIAL" if sample.lstrip().startswith((b"{",b"["))
                        else "HTML_NO_ES_API" if sample.lstrip().lower().startswith((b"<!doctype html",b"<html"))
                        else "NO_JSON")
        return data
    except (requests.RequestException, ValueError, UnicodeError, OSError):
        data["estado"]="ERROR_LECTURA"
        return data
    finally:
        response.close()

def query(url, params=None, headers=None):
    try:
        # Sin redirects: no transmitir una credencial a otro dominio.
        res=S.get(url,params=params,headers=headers or {},
                  allow_redirects=False,stream=True,timeout=(12,45))
        return response_profile(res)
    except requests.Timeout:
        return {"estado":"TIMEOUT"}
    except requests.RequestException:
        return {"estado":"ERROR_RED"}

def idmc():
    secret=os.getenv("IDMC_API_TOKEN","").strip()
    r={"fuente":"IDMC","secreto_configurado":bool(secret),"endpoints":{}}
    if not secret:
        r["estado"]="SIN_SECRETO"
        return r
    base="https://helix-tools-api.idmcdb.org/external-api/"
    paths={
        "gidd_conflicto":"gidd/conflicts/",
        "gidd_desastres":"gidd/disasters/",
        "gidd_ambos":"gidd/displacements/",
        "gidd_analisis":"gidd/public-figure-analyses/",
        "idu_ultimos_180_dias":"idus/last-180-days/",
        "idu_todos":"idus/all/",
    }
    # Para no descargar de forma masiva, dos endpoints principales con GET,
    # los otros con HEAD no siempre indican autorización real.
    # GET con page_size/limit pequeños; si proveedor los ignora se limita
    # la lectura a 1MB. No guardar ni imprimir filas.
    for tag,path in paths.items():
        r["endpoints"][tag]=query(base+path,
              params={"client_id":secret,"format":"json","limit":2,"page_size":2})
    main=[r["endpoints"]["gidd_conflicto"],r["endpoints"]["idu_ultimos_180_dias"]]
    r["estado"]=("CONECTADO" if all(x.get("estado") in
                   ("JSON_VALIDO","JSON_GRANDE_PARCIAL") and x.get("http")==200 for x in main)
                 else "PARCIAL" if any(x.get("http")==200 for x in main) else "POR_VALIDAR")
    return r

def awsd():
    secret=os.getenv("AWSD_API_KEY","").strip()
    r={"fuente":"AWSD","secreto_configurado":bool(secret),"intentos":{}}
    if not secret:
        r["estado"]="SIN_SECRETO"
        return r
    root="https://www.aidworkersecurity.org/incidents/api"
    base_params={"format":"json","start":"2025"}
    # Son variantes comunes: el sitio no publica en su página el nombre
    # del parámetro. No exponer credencial en informes ni logs.
    options=[
        ("query_key","key","query"),
        ("query_api_key","api_key","query"),
        ("query_apikey","apikey","query"),
        ("header_x_api_key","X-API-Key","header"),
        ("header_bearer","Authorization","bearer"),
    ]
    for tag,key,mode in options:
        params=dict(base_params)
        headers={}
        if mode=="query":params[key]=secret
        elif mode=="header":headers[key]=secret
        else:headers["Authorization"]="Bearer "+secret
        profile=query(root,params=params,headers=headers)
        r["intentos"][tag]=profile
        if profile.get("http")==200 and profile.get("estado") in ("JSON_VALIDO","JSON_GRANDE_PARCIAL"):
            r["estado"]="CONECTADO"
            r["metodo_autenticacion"]=tag
            break
        # No seguir probando si servicio limita solicitudes.
        if profile.get("http")==429:
            r["estado"]="LIMITADO_429"
            break
    r.setdefault("estado","POR_VALIDAR")
    return r

def main():
    record={"fecha_utc":datetime.now(timezone.utc).isoformat(),
            "proposito":"Prueba de conexiones, sin microdatos ni credenciales",
            "IDMC":idmc(),"AWSD":awsd()}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(record,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
