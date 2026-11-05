#!/usr/bin/env python3
"""Prueba segura de autenticación de HAPI, DTM IDP y DTM HNA.
No imprime ni guarda secretos, cabeceras, URL con credenciales ni cuerpos de respuesta.
"""
import contextlib
import io
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

OUT = Path("docs/fase1/estado_conexiones.json")
logging.disable(logging.CRITICAL)

def result(servicio, enabled, estado, detalle):
    return {"servicio": servicio, "secreto_configurado": enabled, "estado": estado, "detalle": detalle}

def hapi():
    value = os.getenv("HDX_APP_IDENTIFIER", "").strip()
    if not value:
        return result("HDX HAPI", False, "SIN_SECRETO", "HDX_APP_IDENTIFIER no está disponible")
    try:
        r = requests.get(
            "https://hapi.humdata.org/api/v2/coordination-context/conflict-events",
            params={"app_identifier": value, "location_code": "COL", "limit": 1, "offset": 0,
                    "output_format": "json"},
            timeout=30,
        )
        if r.status_code == 200:
            try:
                data = r.json()
                if isinstance(data, dict) and isinstance(data.get("data"), list):
                    return result("HDX HAPI", True, "OK", "HTTP 200; consulta de conflicto con JSON válido")
                return result("HDX HAPI", True, "RESPUESTA_INESPERADA", "HTTP 200; estructura no esperada")
            except ValueError:
                return result("HDX HAPI", True, "RESPUESTA_INESPERADA", "HTTP 200; JSON inválido")
        if r.status_code in (401, 403):
            return result("HDX HAPI", True, "ACCESO_RECHAZADO", f"HTTP {r.status_code}")
        if r.status_code in (400, 404, 422):
            return result("HDX HAPI", True, "CONSULTA_INVALIDA", f"HTTP {r.status_code}; revisar identificador o parámetros")
        return result("HDX HAPI", True, "ERROR_HTTP", f"HTTP {r.status_code}")
    except requests.RequestException:
        return result("HDX HAPI", True, "ERROR_RED", "No se pudo completar la solicitud")

def iom(servicio, env_name, hna=False):
    token = os.getenv(env_name, "").strip()
    if not token:
        return result(servicio, False, "SIN_SECRETO", f"{env_name} no está disponible")
    try:
        from dtmapi import DTMApi, DTMHnaApi
        # Silenciar todo texto que pudiese emitir la biblioteca. No incluir mensajes de excepciones.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            client = (DTMHnaApi(subscription_key=token, timeout=30, max_retries=0)
                      if hna else DTMApi(subscription_key=token, api_version="v3",
                                        timeout=30, max_retries=0))
            df = client.get_all_countries()
        if hasattr(df, "__len__"):
            return result(servicio, True, "OK", f"Catálogo respondido; filas: {len(df)}")
        return result(servicio, True, "RESPUESTA_INESPERADA", "No se recibió un catálogo tabular")
    except Exception as exc:
        typ = type(exc).__name__
        if "Authentication" in typ or "Unauthorized" in typ or "Forbidden" in typ:
            state = "ACCESO_RECHAZADO"
        elif "Timeout" in typ:
            state = "TIMEOUT"
        elif "Response" in typ:
            state = "RESPUESTA_API_ERROR"
        else:
            state = "ERROR_CONSULTA"
        return result(servicio, True, state, "Clase de error: " + typ)

def main():
    output = {
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "alcance": "Prueba de disponibilidad y autenticación, no evaluación de cobertura regional",
        "sin_valores_secretos": True,
        "resultados": [
            hapi(),
            iom("OIM DTM Baseline API v3", "DTMAPI_SUBSCRIPTION_KEY"),
            iom("OIM DTM HNA API", "DTMHNA_SUBSCRIPTION_KEY", hna=True),
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
