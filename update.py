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

    rows = payload.get("data", [])
    if not isinstance(rows, list):
        raise RuntimeError("Formato inesperado: data no es una lista")

    remates = []
    seen = set()

    for item in rows:
        if normalizar_provincia(item.get("province")) != "ENTRE RIOS":
            continue

        date = item.get("date")
        if not date:
            continue

        key = (
            date,
            item.get("time") or "",
            item.get("consignatariaSlug") or item.get("consignatariaName") or "",
            item.get("location") or "",
        )
        if key in seen:
            continue
        seen.add(key)

        remates.append(
            {
                "id": item.get("id"),
                "fecha": date,
                "hora": item.get("time"),
                "consignataria": item.get("consignatariaName"),
                "localidad": item.get("location"),
                "provincia": item.get("province"),
                "tipo": item.get("type"),
                "titulo": item.get("title"),
                "cabezas_estimadas": item.get("estimatedHeads"),
                "url_catalogo": item.get("catalogUrl"),
                "url_youtube": item.get("youtubeUrl"),
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
