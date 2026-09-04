import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

API_URL = "https://www.consignatarias.com.ar/api/remates/proximos"
OUTPUT = Path("remates.json")
DIAS = 21
TZ = ZoneInfo("America/Argentina/Buenos_Aires")

# Remates aportados directamente por Acción Rural y que no necesariamente
# aparecen en la fuente automática. Se conservan en cada actualización.
MANUALES = [
    {"id":"manual-2026-09-02-hasenkamp","fecha":"2026-09-02","hora":None,"consignataria":"Consignataria Hasenkamp","localidad":"Hasenkamp","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Haciendas Generales","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-02-urdinarrain","fecha":"2026-09-02","hora":None,"consignataria":"Consignataria Spiazzi","localidad":"San José de Urdinarrain","provincia":"ENTRE RÍOS","tipo":"reproductores","titulo":"Reproductores – Limangus","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-02-federal","fecha":"2026-09-02","hora":None,"consignataria":"Etchevehere Rural","localidad":"Federal","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Haciendas Generales","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-04-rosario","fecha":"2026-09-04","hora":None,"consignataria":"Ildarraz Hermanos","localidad":"Rosario","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Remate Habitual Rosgan","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-04-maria-dolores","fecha":"2026-09-04","hora":None,"consignataria":"Etchevehere Rural","localidad":"Feria María Dolores – General Ramírez","provincia":"ENTRE RÍOS","tipo":"reproductores","titulo":"Cabaña Malaika","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-05-gualeguay","fecha":"2026-09-05","hora":None,"consignataria":"Consignataria Hasenkamp","localidad":"Gualeguay","provincia":"ENTRE RÍOS","tipo":"especial","titulo":"Especial Faena – Expo Gualeguay","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-05-urdinarrain","fecha":"2026-09-05","hora":None,"consignataria":"Ildarraz Hermanos","localidad":"Urdinarrain","provincia":"ENTRE RÍOS","tipo":"reproductores","titulo":"Reproductores – Angus de Primera","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-06-gualeguay","fecha":"2026-09-06","hora":None,"consignataria":"Consignataria Hasenkamp","localidad":"Gualeguay","provincia":"ENTRE RÍOS","tipo":"reproductores","titulo":"Especial Reproductores – Expo Gualeguay","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-06-lapaz","fecha":"2026-09-06","hora":None,"consignataria":"Coop. La Ganadera","localidad":"La Paz","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Haciendas Generales","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-08-maria-dolores","fecha":"2026-09-08","hora":"09:30","consignataria":"Etchevehere Rural","localidad":"Feria María Dolores – General Ramírez","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Haciendas Generales","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-09-hasenkamp","fecha":"2026-09-09","hora":None,"consignataria":"Consignataria Hasenkamp","localidad":"Hasenkamp","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Haciendas Generales","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-09-tala","fecha":"2026-09-09","hora":None,"consignataria":"Coop. El Pronunciamiento","localidad":"Rosario del Tala","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Haciendas Generales","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-09-villaguay","fecha":"2026-09-09","hora":None,"consignataria":"Coop. La Ganadera","localidad":"Villaguay","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Haciendas Generales","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-11-gualeguaychu","fecha":"2026-09-11","hora":None,"consignataria":"Casa Usandizaga","localidad":"Gualeguaychú","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Remate – Expo Rural","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-11-televisado","fecha":"2026-09-11","hora":None,"consignataria":"Coop. La Ganadera","localidad":"—","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Remate Televisado","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-12-gualeguay-hasenkamp","fecha":"2026-09-12","hora":None,"consignataria":"Consignataria Hasenkamp","localidad":"Gualeguay","provincia":"ENTRE RÍOS","tipo":"reproductores","titulo":"Reproductores y Vientres","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-12-gualeguay-litoral","fecha":"2026-09-12","hora":None,"consignataria":"La Matilde / La Carreta","localidad":"Gualeguay","provincia":"ENTRE RÍOS","tipo":"reproductores","titulo":"Reproductores – Selección para el Litoral","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-15-gualeguaychu","fecha":"2026-09-15","hora":None,"consignataria":"Consignataria Duarte","localidad":"Gualeguaychú","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Haciendas Generales","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-15-maria-dolores","fecha":"2026-09-15","hora":None,"consignataria":"Etchevehere Rural","localidad":"Feria María Dolores – General Ramírez","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Haciendas Generales","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-16-gualeguay","fecha":"2026-09-16","hora":None,"consignataria":"Campos Bajos S.R.L.","localidad":"Gualeguay","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Haciendas Generales","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-16-hasenkamp","fecha":"2026-09-16","hora":None,"consignataria":"Consignataria Hasenkamp","localidad":"Hasenkamp","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Haciendas Generales","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-16-federal","fecha":"2026-09-16","hora":None,"consignataria":"Ildarraz Hermanos","localidad":"Federal","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Haciendas Generales","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-17-lapaz","fecha":"2026-09-17","hora":None,"consignataria":"Ildarraz Hermanos","localidad":"La Paz","provincia":"ENTRE RÍOS","tipo":"reproductores","titulo":"Reproductores – Braford, Brangus y Búfalos","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-18-lapaz","fecha":"2026-09-18","hora":None,"consignataria":"Sociedad Rural de La Paz","localidad":"La Paz","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Haciendas Generales","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-18-federal","fecha":"2026-09-18","hora":None,"consignataria":"Etchevehere Rural","localidad":"Federal","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Haciendas Generales","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-19-basavilbaso","fecha":"2026-09-19","hora":None,"consignataria":"Cooperativa Ganadera El Pronunciamiento Ltda.","localidad":"Basavilbaso","provincia":"ENTRE RÍOS","tipo":"reproductores","titulo":"Gran Remate de Reproductores y Vientres","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-22-maria-dolores","fecha":"2026-09-22","hora":None,"consignataria":"Etchevehere Rural","localidad":"Feria María Dolores – General Ramírez","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Haciendas Generales","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-23-gualeguaychu","fecha":"2026-09-23","hora":None,"consignataria":"Consignataria del Sur","localidad":"Gualeguaychú","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Haciendas Generales","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-24-gualeguay","fecha":"2026-09-24","hora":None,"consignataria":"Consignataria Hasenkamp","localidad":"Gualeguay","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Haciendas Generales","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-24-concepcion","fecha":"2026-09-24","hora":None,"consignataria":"Etchevehere Rural","localidad":"Concepción del Uruguay","provincia":"ENTRE RÍOS","tipo":"especial","titulo":"Prueba Pastoril Mesopotámica Hereford","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-25-tala","fecha":"2026-09-25","hora":None,"consignataria":"Feria Don Luis","localidad":"Rosario del Tala","provincia":"ENTRE RÍOS","tipo":"reproductores","titulo":"Reproductores y Vientres","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-25-gualeguaychu","fecha":"2026-09-25","hora":None,"consignataria":"Daroca y Buschiazzo","localidad":"Gualeguaychú","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Haciendas Generales","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-29-nogoya","fecha":"2026-09-29","hora":None,"consignataria":"Consignataria Hasenkamp","localidad":"Nogoyá","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Haciendas Generales","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-29-maria-dolores","fecha":"2026-09-29","hora":None,"consignataria":"Etchevehere Rural","localidad":"Feria María Dolores – General Ramírez","provincia":"ENTRE RÍOS","tipo":"general","titulo":"Haciendas Generales","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
    {"id":"manual-2026-09-30-hasenkamp","fecha":"2026-09-30","hora":None,"consignataria":"Consignataria Hasenkamp","localidad":"Hasenkamp","provincia":"ENTRE RÍOS","tipo":"reproductores","titulo":"Especial Reproductores y Vientres","cabezas_estimadas":None,"url_catalogo":None,"url_youtube":None},
]


def normalizar(valor):
    if not valor:
        return ""
    return str(valor).strip().upper().replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")


def limpiar_localidad(valor):
    if not valor:
        return ""
    texto = str(valor).strip()
    texto = re.sub(r"\s*[,/\-–—]?\s*\(?\s*Entre\s+Ríos\s*\)?", " ", texto, flags=re.I)
    texto = re.sub(r"\s{2,}", " ", texto)
    return texto.strip(" ,-/–—")


LOCALIDADES_CORRECTAS = {
    "maria grande": "María Grande", "general ramirez": "General Ramírez", "gualeguaychu": "Gualeguaychú",
    "gualeguay": "Gualeguay", "nogoya": "Nogoyá", "urdinarrain": "Urdinarrain", "villaguay": "Villaguay",
    "hasenkamp": "Hasenkamp", "rosario del tala": "Rosario del Tala", "villa elisa": "Villa Elisa", "basavilbaso": "Basavilbaso",
}


def capitalizar_localidad(valor):
    texto = limpiar_localidad(valor)
    if not texto: return ""
    partes = [p.strip() for p in texto.split("/")]
    resultado = []
    for parte in partes:
        clave = normalizar(parte).lower(); clave = re.sub(r"\s+", " ", clave).strip()
        resultado.append(LOCALIDADES_CORRECTAS.get(clave, " ".join(p[:1].upper() + p[1:].lower() for p in parte.split())))
    return " / ".join(resultado)


def extraer_rows(payload):
    data = payload.get("data", [])
    if isinstance(data, list): return data
    if isinstance(data, dict):
        for key in ("remates", "items", "results", "auctions", "proximos"):
            if isinstance(data.get(key), list): return data[key]
        for value in data.values():
            if isinstance(value, list): return value
    return []


def obtener_nombre_consignataria(item):
    consignataria = item.get("consignataria") or {}
    if isinstance(consignataria, dict): return consignataria.get("nombre") or consignataria.get("name") or item.get("consignatariaName") or ""
    return str(consignataria) if consignataria else (item.get("consignatariaName") or "")


def obtener_ubicacion(item):
    ubicacion = item.get("ubicacion") or item.get("location") or ""
    if isinstance(ubicacion, dict):
        localidad = ubicacion.get("localidad") or ubicacion.get("city") or ubicacion.get("nombre") or ""
        provincia = ubicacion.get("provincia") or ubicacion.get("province") or ubicacion.get("provincia_nombre") or ubicacion.get("provinceName") or ""
    else: localidad, provincia = str(ubicacion), ""
    provincia = item.get("provincia") or item.get("province") or item.get("provincia_nombre") or item.get("provinceName") or provincia
    return localidad, provincia


def obtener_fecha(item): return item.get("fecha") or item.get("date") or item.get("fecha_remate")


def es_entre_rios(item, localidad, provincia):
    texto = " ".join([normalizar(provincia), normalizar(localidad), normalizar(item.get("url") or item.get("slug") or "")])
    return "ENTRE RIOS" in texto


def corregir_ubicacion_especifica(localidad, consignataria, titulo):
    if "MENDIZABAL" in normalizar(f"{consignataria} {titulo}"): return "Gualeguay"
    return localidad


def clave_remate(r):
    return (str(r.get("fecha") or ""), normalizar(r.get("consignataria")), normalizar(r.get("localidad")), normalizar(r.get("titulo")))


def main():
    ahora = datetime.now(TZ); desde = ahora.date(); hasta = desde + timedelta(days=DIAS)
    response = requests.get(API_URL, params={"dias": DIAS}, headers={"User-Agent": "AccionRural-remates-entre-rios/7.2"}, timeout=30)
    response.raise_for_status(); payload = response.json()
    if not payload.get("success", True): raise RuntimeError(f"La API respondió con error: {payload}")
    rows = extraer_rows(payload); remates, seen = [], set()

    for item in rows:
        if not isinstance(item, dict): continue
        fecha = obtener_fecha(item)
        if not fecha: continue
        try: fecha_obj = datetime.strptime(str(fecha)[:10], "%Y-%m-%d").date()
        except ValueError: continue
        if not (desde <= fecha_obj <= hasta): continue
        localidad_raw, provincia = obtener_ubicacion(item)
        if not es_entre_rios(item, localidad_raw, provincia): continue
        localidad = corregir_ubicacion_especifica(capitalizar_localidad(localidad_raw), obtener_nombre_consignataria(item), item.get("titulo") or item.get("title") or "")
        remate = {
            "id": item.get("id"), "fecha": str(fecha)[:10], "hora": item.get("hora") or item.get("time") or None,
            "consignataria": obtener_nombre_consignataria(item) or None, "localidad": localidad,
            "provincia": "ENTRE RÍOS", "tipo": item.get("tipo") or item.get("type"),
            "titulo": item.get("titulo") or item.get("title") or None, "cabezas_estimadas": item.get("cabezas_estimadas") or item.get("estimatedHeads"),
            "url_catalogo": item.get("catalogo_url") or item.get("catalogUrl"), "url_youtube": item.get("youtube_url") or item.get("youtubeUrl"),
        }
        key = clave_remate(remate)
        if key not in seen: seen.add(key); remates.append(remate)

    for manual in MANUALES:
        try: fecha_obj = datetime.strptime(manual["fecha"], "%Y-%m-%d").date()
        except (KeyError, ValueError): continue
        if not (desde <= fecha_obj <= hasta): continue
        key = clave_remate(manual)
        if key not in seen: seen.add(key); remates.append(manual)

    remates.sort(key=lambda r: (r["fecha"], r["hora"] or "23:59", r["localidad"] or "", r["consignataria"] or ""))
    output = {"actualizado": ahora.isoformat(), "fuente": "Consignatarias.com.ar + Acción Rural", "url_fuente": "https://www.consignatarias.com.ar/remates/entre-rios", "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat(), "dias": DIAS}, "cantidad": len(remates), "remates": remates}
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Guardados {len(remates)} remates de Entre Ríos entre {desde} y {hasta}")


if __name__ == "__main__": main()
