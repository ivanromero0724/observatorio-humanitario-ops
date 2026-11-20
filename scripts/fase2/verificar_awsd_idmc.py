#!/usr/bin/env python3
"""Auditoría segura de IDMC y AWSD mediante GitHub Actions.

No muestra secretos, URLs autenticadas, cabeceras ni cuerpos completos.
Solo publica códigos HTTP, formas JSON y nombres de campos sin datos.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urljoin

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
        if res.is_redirect:
            # Publicar solo el host y la clase de destino, nunca la
            # cabecera Location completa (puede contener claves o firmas).
            destination=urlsplit(urljoin(url, res.headers.get("Location","")))
            source=urlsplit(url)
            profile=response_profile(res)
            profile["redirect_host"]=destination.hostname or "desconocido"
            profile["redirect_same_host"]=(destination.hostname==source.hostname
                                           and destination.scheme=="https")
            profile["redirect_kind"]=(
                "ALMACENAMIENTO_IDMC" if destination.hostname==
                "helix-copilot-prod-helix-media-external.s3.amazonaws.com"
                else "OTRA_RUTA"
            )
            if (destination.hostname==
                "helix-copilot-prod-helix-media-external.s3.amazonaws.com"
                and destination.scheme=="https"):
                try:
                    # URL S3 firmada por IDMC: no anexar token original,
                    # no imprimir ni almacenar URL, firma o contenido.
                    download=S.get(destination.geturl(),stream=True,
                                   allow_redirects=False,
                                   headers={"Range":"bytes=0-65535"},
                                   timeout=(12,40))
                    profile["archivo"]=response_profile(download)
                except requests.RequestException:
                    profile["archivo"]={"estado":"ERROR_DESCARGA"}
            return profile
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
    gidd=r["endpoints"]["gidd_conflicto"]
    idu=r["endpoints"]["idu_ultimos_180_dias"]
    gidd_ok=(gidd.get("http")==200 and gidd.get("estado")=="JSON_VALIDO")
    idu_file=idu.get("archivo",{})
    idu_ok=(idu.get("http")==302
            and idu.get("redirect_kind")=="ALMACENAMIENTO_IDMC"
            and idu_file.get("http") in (200,206)
            and idu_file.get("estado") in ("JSON_VALIDO","JSON_GRANDE_PARCIAL"))
    r["estado"]=("CONECTADO" if gidd_ok and idu_ok
                 else "GIDD_OK_IDU_PENDIENTE" if gidd_ok else "POR_VALIDAR")
    return r

def awsd():
    secret=os.getenv("AWSD_API_KEY","").strip()
    r={"fuente":"AWSD","secreto_configurado":bool(secret)}
    if not secret:
        r["estado"]="SIN_SECRETO"
        return r
    # Endpoint exacto entregado por AWSD al titular de la clave:
    # /incidents/search?format=json&api_key={TOKEN}
    # Usar un solo año/país para reducir la respuesta y evitar 429.
    result=query(
        "https://www.aidworkersecurity.org/incidents/search",
        params={"format":"json","api_key":secret,
                "country":"CO","start":"2025","end":"2025"},
    )
    r["prueba"]=result
    r["estado"]=(
        "CONECTADO" if result.get("http")==200
        and result.get("estado") in ("JSON_VALIDO","JSON_GRANDE_PARCIAL")
        else "LIMITADO_429" if result.get("http")==429
        else "POR_VALIDAR"
    )
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
