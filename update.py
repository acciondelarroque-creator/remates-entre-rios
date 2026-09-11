import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

OUTPUT = Path("remates.json")
TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def main():
    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    hoy = datetime.now(TZ).date().isoformat()

    remates = [
        r for r in data.get("remates", [])
        if (r.get("fecha") or "") >= hoy
    ]

    vistos = set()
    unicos = []
    for r in remates:
        clave = (
            r.get("fecha"),
            r.get("hora"),
            str(r.get("consignataria", "")).strip().upper(),
            str(r.get("localidad", "")).strip().upper(),
            str(r.get("titulo", "")).strip().upper(),
        )
        if clave in vistos:
            continue
        vistos.add(clave)
        unicos.append(r)

    unicos.sort(key=lambda r: (
        r.get("fecha", "9999-12-31"),
        r.get("hora") or "99:99",
        r.get("consignataria", ""),
        r.get("localidad", ""),
        r.get("titulo", ""),
    ))

    data["remates"] = unicos
    data["cantidad"] = len(unicos)
    data["periodo"]["desde"] = hoy
    data["periodo"]["hasta"] = max((r.get("fecha", hoy) for r in unicos), default=hoy)
    data["periodo"]["dias"] = (
        datetime.fromisoformat(data["periodo"]["hasta"]).date()
        - datetime.fromisoformat(hoy).date()
    ).days
    data["fuente"] = "Etchevehere Rural + Consignataria Hasenkamp + Coop. La Ganadera"
    data["fuentes"] = [
        "https://etchevehere-rural.com.ar/",
        "https://chsrl.com.ar/proximos-remates/",
        "https://laganadera.com.ar/remates",
    ]
    data["actualizado"] = datetime.now(TZ).isoformat()

    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
