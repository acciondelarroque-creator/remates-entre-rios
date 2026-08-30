import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

API_URL = "https://www.consignatarias.com.ar/api/remates/proximos"
OUTPUT = Path("remates.json")
DIAS = 21
TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def normalizar(valor):
    """Normaliza texto para comparar provincias y otros campos."""
    if not valor:
        return ""
    return (
        str(valor)
        .strip()
        .upper()
        .replace("Á", "A")
        .replace("É", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ú", "U")
    )


def extraer_rows(payload):
    """Acepta las variantes de estructura que puede devolver la API."""
    data = payload.get("data", [])

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("remates", "items", "results", "auctions", "proximos"):
            value = data.get(key)
            if isinstance(value, list):
                return value

        for value in data.values():
            if isinstance(value, list):
                return value

    return []


def obtener_nombre_consignataria(item):
    consignataria = item.get("consignataria") or {}
    if isinstance(consignataria, dict):
        return (
            consignataria.get("nombre")
            or consignataria.get("name")
            or item.get("consignatariaName")
            or ""
        )
    return str(consignataria) if consignataria else (
        item.get("consignatariaName") or ""
    )


def obtener_provincia(item, ubicacion):
    """Prioriza provincia explícita y contempla variantes de la API."""
    candidatos = [
        item.get("provincia"),
        item.get("province"),
        item.get("provincia_nombre"),
        item.get("provinceName"),
    ]

    for candidato in candidatos:
        if candidato:
            return str(candidato)

    if isinstance(item.get("ubicacion"), dict):
        ubic = item["ubicacion"]
        return (
            ubic.get("provincia")
            or ubic.get("province")
            or ubic.get("provincia_nombre")
            or ubic.get("provinceName")
            or ""
        )

    return ubicacion


def obtener_fecha(item):
    return item.get("fecha") or item.get("date") or item.get("fecha_remate")


def main():
    ahora = datetime.now(TZ)
    desde = ahora.date()
    hasta = desde + timedelta(days=DIAS)

    # La API documenta /remates/proximos con ?dias=N. Pedimos las tres
    # semanas completas y luego filtramos por fecha y provincia localmente.
    response = requests.get(
        API_URL,
        params={"dias": DIAS},
        headers={"User-Agent": "AccionRural-remates-entre-rios/2.0"},
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

        # Solo remates publicados cuya fecha cae dentro de las próximas 3 semanas.
        if not (desde <= fecha_obj <= hasta):
            continue

        ubicacion_raw = item.get("ubicacion") or item.get("location") or ""
        if isinstance(ubicacion_raw, dict):
            localidad = (
                ubicacion_raw.get("localidad")
                or ubicacion_raw.get("city")
                or ubicacion_raw.get("nombre")
                or ""
            )
        else:
            localidad = str(ubicacion_raw)

        provincia = obtener_provincia(item, ubicacion_raw)
        if "ENTRE RIOS" not in normalizar(provincia):
            continue

        hora = item.get("hora") or item.get("time") or ""
        consignataria_nombre = obtener_nombre_consignataria(item)

        # Evita duplicados del mismo remate aunque la fuente lo publique
        # repetido en distintas vistas.
        key = (
            str(item.get("id") or ""),
            str(fecha),
            str(hora),
            normalizar(consignataria_nombre),
            normalizar(localidad),
            normalizar(item.get("titulo") or item.get("title") or ""),
        )
        if key in seen:
            continue
        seen.add(key)

        remates.append(
            {
                "id": item.get("id"),
                "fecha": str(fecha)[:10],
                "hora": hora or None,
                "consignataria": consignataria_nombre or None,
                "localidad": localidad,
                "provincia": "ENTRE RÍOS",
                "tipo": item.get("tipo") or item.get("type"),
                "titulo": item.get("titulo") or item.get("title"),
                "cabezas_estimadas": (
                    item.get("cabezas_estimadas")
                    or item.get("estimatedHeads")
                ),
                "url_catalogo": (
                    item.get("catalogo_url")
                    or item.get("catalogUrl")
                ),
                "url_youtube": (
                    item.get("youtube_url")
                    or item.get("youtubeUrl")
                ),
            }
        )

    remates.sort(key=lambda r: (r["fecha"], r["hora"] or "23:59", r["consignataria"] or ""))

    output = {
        "actualizado": ahora.isoformat(),
        "fuente": "Consignatarias.com.ar",
        "url_fuente": "https://www.consignatarias.com.ar/remates/entre-rios",
        "periodo": {
            "desde": desde.isoformat(),
            "hasta": hasta.isoformat(),
            "dias": DIAS,
        },
        "cantidad": len(remates),
        "remates": remates,
    }

    OUTPUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        f"Guardados {len(remates)} remates de Entre Ríos "
        f"entre {desde} y {hasta}"
    )


if __name__ == "__main__":
    main()
