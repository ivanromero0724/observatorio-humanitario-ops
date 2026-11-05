#!/usr/bin/env python3
"""Prueba segura de conexión de ACAPS API desde GitHub Actions.

Sólo guarda estado, HTTP y nombres de recursos; nunca valores de token,
cuerpos de respuesta, URLs con secretos, ni datos con restricciones.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/fase2/acaps_conexion.json"
BASE = "https://api.acaps.org/api/v1/inform-severity-index/"

def main():
    token = os.environ.get("ACAPS_API_TOKEN", "").strip()
    record = {
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "fuente": "ACAPS API",
        "secreto_configurado": bool(token),
        "estado": "SIN_SECRETO" if not token else "NO_VERIFICADO",
        "http_status": None,
        "content_type_json": False,
        "recursos_disponibles": [],
        "nota": "Prueba del endpoint INFORM Severity (no del índice web que redirige a login). No implica integración al dashboard.",
    }
    if token:
        try:
            res = requests.get(
                BASE,
                headers={
                    "Authorization": "Token " + token,
                    "Accept": "application/json",
                    "User-Agent": "observatorio-humanitario-ops/0.3 (ACAPS API check)",
                },
                timeout=35,
                allow_redirects=False,
            )
            record["http_status"] = res.status_code
            content_type = res.headers.get("Content-Type", "").lower()
            record["content_type_json"] = "json" in content_type
            if res.status_code == 200 and record["content_type_json"]:
                obj = res.json()
                if isinstance(obj, dict):
                    keys = sorted(str(k) for k in obj.keys())
                    # Documentation index keys only; no request payload saved.
                    record["recursos_disponibles"] = keys[:120]
                record["estado"] = "CONECTADO"
            elif res.status_code in (401, 403):
                record["estado"] = "ACCESO_RECHAZADO"
            elif res.status_code in (301, 302, 303, 307, 308):
                record["estado"] = "REDIRECCION"
                record["nota"] = "El endpoint de datos redirige; verificar autenticación y ruta."
            else:
                record["estado"] = "RESPUESTA_INESPERADA"
        except (requests.RequestException, ValueError):
            record["estado"] = "ERROR_CONSULTA"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False, indent=2))
if __name__ == "__main__":
    main()
