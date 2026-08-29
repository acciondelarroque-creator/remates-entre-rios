# Remates Entre Ríos

Calendario y marquesina automática de remates ganaderos de Entre Ríos para Acción Rural.

## Fuente

Los datos se obtienen de Consignatarias.com.ar mediante su API pública de remates.

- Calendario: https://www.consignatarias.com.ar/remates/entre-rios
- API: https://www.consignatarias.com.ar/api/remates/proximos

## Actualización

GitHub Actions ejecuta `update.py` diariamente a las 14:20 ART y actualiza `remates.json` con los próximos 30 días.
