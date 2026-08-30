import json
from datetime import datetime, timezone
from pathlib import Path

import requests

API_URL = "https://www.consignatarias.com.ar/api/remates/proximos"
OUTPUT = Path("remates.json")


def normalizar_provincia(valor):
    """Normaliza nombres de provincia para comparar sin problemas de acentos/case."""
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


def main():
    # El filtro por provincia de la API está documentado, pero el servidor
    # responde 400 con "Entre Ríos". Pedimos los próximos 30 días y
    # filtramos Entre Ríos localmente, de forma más robusta.
    params = {"dias": 30}

    response = requests.get(
        API_URL,
        params=params,
        headers={"User-Agent": "AccionRural-remates-entre-rios/1.0"},
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"La API respondió HTTP {response.status_code}: {response.text[:500]}"
        )

    payload = response.json()

    if not payload.get("success", True):
        raise RuntimeError(f"La API respondió con error: {payload}")

    # La API puede devolver la lista directamente en data o anidada en data.remates.
    data = payload.get("data", [])
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        # Algunas versiones de la API agrupan la lista con nombres diferentes.
        rows = next(
            (
                value
                for value in (
                    data.get("remates"),
                    data.get("items"),
                    data.get("results"),
                    data.get("auctions"),
                    data.get("proximos"),
                    *data.values(),
                )
                if isinstance(value, list)
            ),
            [],
        )
    else:
        rows = []

    if not isinstance(rows, list):
        raise RuntimeError("Formato inesperado: no se encontró una lista de remates")
    remates = []
    seen = set()

    for item in rows:
        consignataria = item.get("consignataria") or {}
        consignataria_nombre = (
            consignataria.get("nombre") if isinstance(consignataria, dict) else None
        ) or item.get("consignatariaName")
        ubicacion = item.get("ubicacion") or item.get("location") or ""
        provincia = item.get("provincia") or item.get("province") or ubicacion

        # La ubicación es el dato geográfico del evento; la provincia de la
        # consignataria puede ser distinta de la provincia donde se realiza.
        if "ENTRE RIOS" not in normalizar_provincia(provincia):
            continue

        date = item.get("fecha") or item.get("date")
        if not date:
            continue

        key = (
            date,
            item.get("hora") or item.get("time") or "",
            consignataria_nombre or "",
            ubicacion,
        )
        if key in seen:
            continue
        seen.add(key)

        remates.append(
            {
                "id": item.get("id"),
                "fecha": date,
                "hora": item.get("hora") or item.get("time"),
                "consignataria": consignataria_nombre,
                "localidad": ubicacion,
                "provincia": "ENTRE RÍOS",
                "tipo": item.get("tipo") or item.get("type"),
                "titulo": item.get("titulo") or item.get("title"),
                "cabezas_estimadas": item.get("cabezas_estimadas") or item.get("estimatedHeads"),
                "url_catalogo": item.get("catalogo_url") or item.get("catalogUrl"),
                "url_youtube": item.get("youtube_url") or item.get("youtubeUrl"),
            }
        )

    remates.sort(key=lambda r: (r["fecha"], r["hora"] or "23:59"))

    output = {
        "actualizado": datetime.now(timezone.utc).isoformat(),
        "fuente": "Consignatarias.com.ar",
        "url_fuente": "https://www.consignatarias.com.ar/remates/entre-rios",
        "cantidad": len(remates),
        "remates": remates,
    }

    OUTPUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Guardados {len(remates)} remates de Entre Ríos")


if __name__ == "__main__":
    main()
