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


def normalizar(valor):
    if not valor:
        return ""
    return (
        str(valor).strip().upper()
        .replace("Á", "A").replace("É", "E").replace("Í", "I")
        .replace("Ó", "O").replace("Ú", "U")
    )


def capitalizar_localidad(valor):
    """Uniforma localidades: inicial mayúscula y resto minúscula."""
    texto = limpiar_localidad(valor)
    if not texto:
        return ""
    return " ".join(palabra[:1].upper() + palabra[1:].lower() for palabra in texto.split())


def limpiar_localidad(valor):
    if not valor:
        return ""
    texto = str(valor).strip()
    texto = re.sub(r"\s*[,/\-–—]?\s*\(?\s*Entre\s+Ríos\s*\)?", "", texto, flags=re.I)
    texto = re.sub(r"\s{2,}", " ", texto)
    return texto.strip(" ,-/–—")


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
        provincia = (
            ubicacion.get("provincia") or ubicacion.get("province")
            or ubicacion.get("provincia_nombre") or ubicacion.get("provinceName") or ""
        )
    else:
        localidad = str(ubicacion)
        provincia = ""
    provincia = (
        item.get("provincia") or item.get("province")
        or item.get("provincia_nombre") or item.get("provinceName") or provincia
    )
    return capitalizar_localidad(localidad), provincia


def obtener_fecha(item):
    return item.get("fecha") or item.get("date") or item.get("fecha_remate")


def main():
    ahora = datetime.now(TZ)
    desde = ahora.date()
    hasta = desde + timedelta(days=DIAS)

    response = requests.get(
        API_URL,
        params={"dias": DIAS},
        headers={"User-Agent": "AccionRural-remates-entre-rios/4.0"},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    if not payload.get("success", True):
        raise RuntimeError(f"La API respondió con error: {payload}")

    rows = extraer_rows(payload)
    if not isinstance(rows, list):
        raise RuntimeError("Formato inesperado: no se encontró una lista de remates")

    remates = []
    seen = set()

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

        localidad, provincia = obtener_ubicacion(item)
        if "ENTRE RIOS" not in normalizar(provincia):
            continue

        hora = item.get("hora") or item.get("time") or ""
        consignataria = obtener_nombre_consignataria(item)
        titulo = item.get("titulo") or item.get("title") or ""

        key = (
            str(item.get("id") or ""), str(fecha), str(hora),
            normalizar(consignataria), normalizar(localidad), normalizar(titulo)
        )
        if key in seen:
            continue
        seen.add(key)

        remates.append({
            "id": item.get("id"),
            "fecha": str(fecha)[:10],
            "hora": hora or None,
            "consignataria": consignataria or None,
            "localidad": localidad,
            "provincia": "ENTRE RÍOS",
            "tipo": item.get("tipo") or item.get("type"),
            "titulo": titulo or None,
            "cabezas_estimadas": item.get("cabezas_estimadas") or item.get("estimatedHeads"),
            "url_catalogo": item.get("catalogo_url") or item.get("catalogUrl"),
            "url_youtube": item.get("youtube_url") or item.get("youtubeUrl"),
        })

    remates.sort(key=lambda r: (r["fecha"], r["hora"] or "23:59", r["localidad"] or "", r["consignataria"] or ""))

    output = {
        "actualizado": ahora.isoformat(),
        "fuente": "Consignatarias.com.ar",
        "url_fuente": "https://www.consignatarias.com.ar/remates/entre-rios",
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat(), "dias": DIAS},
        "cantidad": len(remates),
        "remates": remates,
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Guardados {len(remates)} remates de Entre Ríos entre {desde} y {hasta}")


if __name__ == "__main__":
    main()
