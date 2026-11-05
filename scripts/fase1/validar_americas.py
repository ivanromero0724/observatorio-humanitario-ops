#!/usr/bin/env python3
"""Valida correspondencia 35 países × HAPI, DTM Baseline y DTM HNA."""
import csv
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CAT=ROOT/"data/catalogos/paises_americas.csv"
COV=ROOT/"docs/fase1/cobertura_hapi_oim_americas.csv"
RES=ROOT/"docs/fase1/resumen_piloto_regional.json"

def read(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def main():
    countries=read(CAT); data=read(COV); summary=json.loads(RES.read_text(encoding="utf-8"))
    expected={r["iso3"] for r in countries}
    assert len(expected)==len(countries)==35, "Catálogo no tiene 35 países únicos"
    sources={"HAPI conflicto 2020+","OIM DTM Baseline","OIM DTM HNA"}
    assert len(data)==105, f"Se esperaban 105 filas de cobertura, hay {len(data)}"
    keys=[(r["iso3"],r["fuente"]) for r in data]
    assert len(keys)==len(set(keys)), "Combinaciones país–fuente duplicadas"
    assert {r["fuente"] for r in data}==sources, "Fuentes inesperadas"
    for source in sources:
        subset=[r for r in data if r["fuente"]==source]
        assert {r["iso3"] for r in subset}==expected, f"Falta país para {source}"
    assert all(r["estado"] for r in data),"Falta estado de cobertura"
    assert summary["paises_catalogo"]==35
    assert any(r["estado"] not in ("sin_credencial","error_catalogo") for r in data
               if r["fuente"]=="OIM DTM Baseline"),"OIM Baseline sin evaluación"
    assert any(r["estado"] not in ("sin_credencial","error_catalogo") for r in data
               if r["fuente"]=="HAPI conflicto 2020+"),"HAPI no respondió"
    print(json.dumps({"validacion":"OK","paises":35,"filas":len(data),
        "fuentes":dict(Counter(x["fuente"] for x in data))},ensure_ascii=False))

if __name__=="__main__":main()
