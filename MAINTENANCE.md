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

Notas:
- El script intenta detectar `python` en `PATH` si no se proporciona `-PythonExe`.
- El task se crea como `NT AUTHORITY\SYSTEM` para que se ejecute sin sesión de usuario; ajusta si quieres usar un usuario específico.
- Revisa los logs/outputs del task en el Visor de eventos o configura redirección a un archivo si lo prefieres.
