#!/usr/bin/env python3
"""Diagnóstico breve de duplicación HAPI para Colombia.
El output contiene solo 3 ejemplos de registros agregados, no credenciales,
no URL de consulta y no datos de eventos individuales.
"""
import os
import requests
from collections import defaultdict,Counter
from datetime import datetime

key=os.environ["HDX_APP_IDENTIFIER"].strip()
r=requests.get("https://hapi.humdata.org/api/v2/coordination-context/conflict-events",
 params={"app_identifier":key,"location_code":"COL","limit":10000,"offset":0,
         "start_date":"2020-01-01","output_format":"json"},timeout=70)
r.raise_for_status()
a=r.json().get("data",[])
print("Filas primera página:",len(a))
counter=Counter(str(x.get("admin_level")) for x in a)
print("Distribución niveles:",dict(counter))
d=defaultdict(list)
for x in a:
 geo=(str(x.get("admin1_code") or x.get("admin1_name") or ""),
      str(x.get("admin2_code") or x.get("admin2_name") or ""))
 k=(str(x.get("reference_period_start"))[:7],str(x.get("event_type")),str(x.get("admin_level")),geo)
 d[k].append(x)
rep=[(k,rows) for k,rows in d.items() if len(rows)>1]
print("Claves geográficas repetidas en primera página:",len(rep))
for k,rows in rep[:5]:
 print("Ejemplo seguro",{"periodo":k[0],"tipo":k[1],"nivel":k[2],
 "geo":k[3],"numero":len(rows),
 "sumas":[{"eventos":str(v.get("events")),"muertes":str(v.get("fatalities")),
 "recurso":str(v.get("resource_hdx_id"))[:8]} for v in rows[:3]]})
print("Eventos nulos por tipo:",dict(Counter(str(x.get("event_type")) for x in a
                                     if x.get("events") is None)))
print("Muertes nulas por tipo:",dict(Counter(str(x.get("event_type")) for x in a
                                     if x.get("fatalities") is None)))
