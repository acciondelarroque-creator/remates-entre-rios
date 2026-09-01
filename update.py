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
    {
        "id": "manual-2026-09-19-basavilbaso",
        "fecha": "2026-09-19",
        "hora": None,
        "consignataria": "Cooperativa Ganadera El Pronunciamiento Ltda.",
        "localidad": "Basavilbaso",
        "provincia": "ENTRE RÍOS",
        "tipo": "reproductores",
        "titulo": "Gran Remate de Reproductores y Vientres",
        "cabezas_estimadas": None,
        "url_catalogo": None,
        "url_youtube": None,
    }
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
    "maria grande": "María Grande",
    "general ramirez": "General Ramírez",
    "gualeguaychu": "Gualeguaychú",
    "gualeguay": "Gualeguay",
    "nogoya": "Nogoyá",
    "urdinarrain": "Urdinarrain",
    "villaguay": "Villaguay",
    "hasenkamp": "Hasenkamp",
    "rosario del tala": "Rosario del Tala",
    "villa elisa": "Villa Elisa",
    "basavilbaso": "Basavilbaso",
}


def capitalizar_localidad(valor):
    texto = limpiar_localidad(valor)
    if not texto:
        return ""
    partes = [p.strip() for p in texto.split("/")]
    resultado = []
    for parte in partes:
        clave = normalizar(parte).lower()
        clave = re.sub(r"\s+", " ", clave).strip()
        if clave in LOCALIDADES_CORRECTAS:
            resultado.append(LOCALIDADES_CORRECTAS[clave])
        else:
            resultado.append(" ".join(p[:1].upper() + p[1:].lower() for p in parte.split()))
    return " / ".join(resultado)


def extraer_rows(payload):
    data = payload.get("data", [])
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("remates", "items", "results", "auctions", "proximos"):
            if isinstance(data.get(key), list):
                return data[key]
        for value in data.values():
            if isinstance(value, list):
                return value
    return []


def obtener_nombre_consignataria(item):
    consignataria = item.get("consignataria") or {}
    if isinstance(consignataria, dict):
        return consignataria.get("nombre") or consignataria.get("name") or item.get("consignatariaName") or ""
    return str(consignataria) if consignataria else (item.get("consignatariaName") or "")


def obtener_ubicacion(item):
    ubicacion = item.get("ubicacion") or item.get("location") or ""
    if isinstance(ubicacion, dict):
        localidad = ubicacion.get("localidad") or ubicacion.get("city") or ubicacion.get("nombre") or ""
        provincia = ubicacion.get("provincia") or ubicacion.get("province") or ubicacion.get("provincia_nombre") or ubicacion.get("provinceName") or ""
    else:
        localidad, provincia = str(ubicacion), ""
    provincia = item.get("provincia") or item.get("province") or item.get("provincia_nombre") or item.get("provinceName") or provincia
    return localidad, provincia


def obtener_fecha(item):
    return item.get("fecha") or item.get("date") or item.get("fecha_remate")


def es_entre_rios(item, localidad, provincia):
    texto = " ".join([normalizar(provincia), normalizar(localidad), normalizar(item.get("url") or item.get("slug") or "")])
    return "ENTRE RIOS" in texto


def corregir_ubicacion_especifica(localidad, consignataria, titulo):
    """Correcciones conocidas de ubicación que la fuente puede devolver mal."""
    texto = normalizar(f"{consignataria} {titulo}")
    if "MENDIZABAL" in texto:
        return "Gualeguay"
    return localidad


def main():
    ahora = datetime.now(TZ)
    desde = ahora.date()
    hasta = desde + timedelta(days=DIAS)

    response = requests.get(API_URL, params={"dias": DIAS}, headers={"User-Agent": "AccionRural-remates-entre-rios/7.1"}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success", True):
        raise RuntimeError(f"La API respondió con error: {payload}")

    rows = extraer_rows(payload)
    remates, seen = [], set()

    for item in rows:
        if not isinstance(item, dict):
            continue
        fecha = obtener_fecha(item)
        if not fecha:
            continue
        try:
            fecha_obj = datetime.strptime(str(fecha)[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        if not (desde <= fecha_obj <= hasta):
            continue

        localidad_raw, provincia = obtener_ubicacion(item)
        if not es_entre_rios(item, localidad_raw, provincia):
            continue

        localidad = capitalizar_localidad(localidad_raw)
        hora = item.get("hora") or item.get("time") or ""
        consignataria = obtener_nombre_consignataria(item)
        titulo = item.get("titulo") or item.get("title") or ""
        localidad = corregir_ubicacion_especifica(localidad, consignataria, titulo)

        key = (str(item.get("id") or ""), str(fecha), str(hora), normalizar(consignataria), normalizar(localidad), normalizar(titulo))
        if key in seen:
            continue
        seen.add(key)

        remates.append({
            "id": item.get("id"), "fecha": str(fecha)[:10], "hora": hora or None,
            "consignataria": consignataria or None, "localidad": localidad,
            "provincia": "ENTRE RÍOS", "tipo": item.get("tipo") or item.get("type"),
            "titulo": titulo or None, "cabezas_estimadas": item.get("cabezas_estimadas") or item.get("estimatedHeads"),
            "url_catalogo": item.get("catalogo_url") or item.get("catalogUrl"),
            "url_youtube": item.get("youtube_url") or item.get("youtubeUrl"),
        })

    for manual in MANUALES:
        try:
            fecha_obj = datetime.strptime(manual["fecha"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            continue
        if not (desde <= fecha_obj <= hasta):
            continue
        key = (
            str(manual.get("id") or ""), manual.get("fecha", ""), manual.get("hora") or "",
            normalizar(manual.get("consignataria")), normalizar(manual.get("localidad")),
            normalizar(manual.get("titulo")),
        )
        if key not in seen:
            seen.add(key)
            remates.append(manual)

    remates.sort(key=lambda r: (r["fecha"], r["hora"] or "23:59", r["localidad"] or "", r["consignataria"] or ""))
    output = {
        "actualizado": ahora.isoformat(), "fuente": "Consignatarias.com.ar + Acción Rural",
        "url_fuente": "https://www.consignatarias.com.ar/remates/entre-rios",
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat(), "dias": DIAS},
        "cantidad": len(remates), "remates": remates,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Guardados {len(remates)} remates de Entre Ríos entre {desde} y {hasta}")


if __name__ == "__main__":
    main()
