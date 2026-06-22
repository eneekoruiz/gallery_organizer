# Migraciones

La actualización se aplica automáticamente al arrancar y es idempotente.
Conserva `KnownFaces`, `Detections` y `FileIdentities` para que instalaciones
anteriores sigan funcionando mientras el dominio normalizado toma el relevo.

Para ejecutar todo el esquema y todas las migraciones conocidas juntas, con una
copia de seguridad previa:

```powershell
python smart_gallery_v2/tools/apply_upgrade.py --db "C:\ruta\gallery.db"
```

El ejecutor crea un `.bak` fechado y usa exactamente la misma ruta de migración
que el arranque normal, por lo que no puede divergir de la aplicación y puede
volver a ejecutarse sin duplicar datos.

La versión v5 crea identidades normalizadas, regiones, evidencia humana,
prototipos multimodales, ejemplos de Active Learning, eventos, relaciones de
eventos, caché geográfica y una outbox para efectos sobre el filesystem.
