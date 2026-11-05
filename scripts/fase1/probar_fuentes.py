#!/usr/bin/env python3
"""Pruebas de conectividad documentales; no publican datos ni requieren credenciales en archivos."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import requests

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "outputs" / "fase1" / "diagnostico_conectividad.json"

def get_summary(name, url, params=None):
    result = {"fuente":name, "estado":"pendiente", "http_status":None, "campos":[], "filas_muestra":None}
    try:
        r = requests.get(url, params=params, timeout=35,
                         headers={"User-Agent":"observatorio-humanitario-ops/fase1"})
        result["http_status"] = r.status_code
        r.raise_for_status()
        d = r.json()
        rows = d.get("data", d.get("rows", [])) if isinstance(d, dict) else []
        result["filas_muestra"] = len(rows) if isinstance(rows,list) else None
        result["campos"] = list(rows[0].keys()) if isinstance(rows,list) and rows else []
        result["estado"] = "respuesta_json_obtenida"
    except (ValueError, requests.RequestException) as e:
        result["estado"] = "error"
        result["detalle"] = f"{type(e).__name__}: {str(e)[:160]}"
    return result

def main():
    items = [get_summary("WarMonit CII","https://warmonit.com/data/cii.json")]
    app_id = os.getenv("HDX_APP_IDENTIFIER")
    if app_id:
        for iso in ["COL","HTI","VEN","ECU","PAN"]:
            items.append(get_summary(
                "HAPI conflicto "+iso,
                "https://hapi.humdata.org/api/v2/coordination-context/conflict-events",
                {"app_identifier":app_id, "location_code":iso,
                 "output_format":"json", "limit":2, "offset":0}))
    else:
        items.append({"fuente":"HDX HAPI","estado":"pendiente_credencial",
                      "detalle":"Definir variable HDX_APP_IDENTIFIER"})
    result={"fecha_utc":datetime.now(timezone.utc).isoformat(),
            "nota":"Muestras de conectividad, no cobertura temporal completa.",
            "resultados":items}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    print("Archivo:",OUT)

if __name__=="__main__":
    main()
