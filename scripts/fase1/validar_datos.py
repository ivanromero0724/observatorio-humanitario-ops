#!/usr/bin/env python3
"""Validación básica de CSV armonizados para evitar publicar datos incompletos."""
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"data"/"observaciones"
DOC=ROOT/"docs"/"fase1"
SOURCES={
    "risk": DATA/"inform_risk_mid_2026.csv",
    "severity": DATA/"inform_severity_2026_09_crisis.csv",
    "ops": DATA/"ops_8_indicadores_pais_anio.csv",
    "warmonit": DATA/"warmonit_cii_ultimo.csv",
}
INDICADORES={"GINI","Escolaridad","Camas hospitalarias","Médicos",
             "Enfermería","DTP3","SRP1","Mortalidad por homicidio"}

def table(path):
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def check_unique(rows,keys,label,errors):
    values=[tuple(row.get(k,"") for k in keys) for row in rows]
    repeated=[item for item,n in Counter(values).items() if n>1]
    if repeated:
        errors.append(f"{label}: {len(repeated)} claves duplicadas")

def main():
    errors=[]
    for name,p in SOURCES.items():
        if not p.exists(): errors.append(f"Falta {p}")
    if errors: raise ValueError("; ".join(errors))
    all_data={k:table(p) for k,p in SOURCES.items()}
    risk=all_data["risk"]; severity=all_data["severity"]
    ops=all_data["ops"];war=all_data["warmonit"]
    if len(risk)<30: errors.append("INFORM Risk: menos de 30 países")
    if not severity: errors.append("INFORM Severity sin crisis")
    if len(ops)<1000: errors.append("OPS menos de 1000 series país-año")
    if not war: errors.append("WarMonit sin filas")

    check_unique(risk,["iso3","edicion"],"INFORM Risk",errors)
    check_unique(severity,["iso3","crisis_id"],"INFORM Severity",errors)
    check_unique(ops,["iso3","indicador","periodo"],"OPS",errors)
    check_unique(war,["iso3","fecha"],"WarMonit",errors)

    for name in ["risk","severity"]:
        for r in all_data[name]:
            try:v=float(r["puntuacion"])
            except (ValueError,TypeError,KeyError):
                errors.append(f"{name}: puntuación no numérica");break
            if not (0<=v<=10):
                errors.append(f"{name}: puntuación fuera de 0-10");break
    for r in ops:
        if r["indicador"] not in INDICADORES:
            errors.append("OPS: indicador fuera de catálogo");break
        try:
            y=int(r["periodo"]);v=float(r["valor"])
            if not 1990<=y<=datetime.now(timezone.utc).year or not (-10000<=v<=1e10):
                raise ValueError("rango inesperado")
        except (KeyError,ValueError,TypeError):
            errors.append("OPS: fecha o valor inválido");break

    report={
        "evaluacion_utc":datetime.now(timezone.utc).isoformat(),
        "aprobacion_metodologica_ops":False,
        "estado":"pasa" if not errors else "falla",
        "validaciones":{"riesgo_paises":len(risk),"severity_crisis":len(severity),
                        "severity_paises":len({r['iso3'] for r in severity}),
                        "ops_filas_pais_anio":len(ops),
                        "ops_paises":len({r['iso3'] for r in ops}),
                        "ops_indicadores":len({r['indicador'] for r in ops}),
                        "warmonit_paises":len(war)},
        "archivos":{
            name:{"bytes":p.stat().st_size,
                  "sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
            for name,p in SOURCES.items()
        },
        "errores":errors
    }
    DOC.mkdir(parents=True,exist_ok=True)
    (DOC/"qa_normalizados.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if errors: raise SystemExit(1)

if __name__=="__main__":
    main()
