import os
import time
from pathlib import Path

temp_dir = Path(r"C:\Users\User\AppData\Local\Temp")
now = time.time()
one_day = 86400

deleted = 0
freed_bytes = 0

print("Limpiando archivos temporales obsoletos (> 24 horas)...")
for item in temp_dir.iterdir():
    try:
        if item.is_file():
            mtime = item.stat().st_mtime
            if now - mtime > one_day:
                size = item.stat().st_size
                item.unlink(missing_ok=True)
                deleted += 1
                freed_bytes += size
    except Exception:
        pass

print(f"Limpieza temporal completada: {deleted} archivos borrados, {freed_bytes / (1024**2):.2f} MB liberados.")
