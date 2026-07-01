# Mantenimiento automático — Smart AI Gallery

Este repositorio incluye utilidades para ejecutar mantenimiento periódico que limpia registros huérfanos y symlinks rotos.

Archivos añadidos:
- `smart_gallery_v2/tools/maintenance_runner.py` — runner CLI que ejecuta `cleanup_missing_files()` y `cleanup_broken_symlinks()` (registro por consola).
- `tasks/register_maintenance_task.ps1` — PowerShell helper para crear una tarea programada de Windows que ejecute el runner diariamente.

Registrar la tarea (ejemplo):

```powershell
# desde la carpeta `tasks`
.\register_maintenance_task.ps1
# o especificando python
.\register_maintenance_task.ps1 -PythonExe 'C:\Users\User\AppData\Local\Programs\Python\Python310\python.exe'
```

Uso del runner:

```powershell
# dry-run: informa sin eliminar
python .\smart_gallery_v2\tools\maintenance_runner.py --dry-run

# ejecutar y guardar logs rotativos
python .\smart_gallery_v2\tools\maintenance_runner.py --log-file C:\logs\sg_maintenance.log
```

### Programación en Linux / macOS (Crontab)

Para ejecutar la limpieza diariamente en sistemas Unix:

1.  Abre el editor de crontab: `crontab -e`
2.  Añade la siguiente línea para ejecutarlo a las 03:00 AM:
    ```bash
    0 3 * * * /usr/bin/python3 /ruta/a/gallery_organizer/smart_gallery_v2/tools/maintenance_runner.py >> /ruta/a/logs/maintenance.log 2>&1
    ```

---

## Seguridad y Privilegios

- **Windows**: La tarea se registra por defecto como `NT AUTHORITY\SYSTEM` para ejecución sin sesión. Se recomienda revisar si prefieres un usuario restringido con permisos de escritura en las carpetas de entrada/resultados.
- **Linux**: No ejecutes el cron como `root`. Usa el crontab del usuario que gestiona las fotos.
