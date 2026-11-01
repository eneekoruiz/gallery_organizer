import os
import sys
import time
import ctypes
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Windows Cloud Files API (cldapi.dll)
cfapi = ctypes.WinDLL("cldapi.dll")

FILE_WRITE_ATTRIBUTES = 0x0100
FILE_READ_ATTRIBUTES = 0x0080
OPEN_EXISTING = 3
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
FILE_SHARE_DELETE = 4
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000

photos_dir = Path(r"C:\Users\User\Pictures\iCloud Photos\Photos")

print(f"=== INICIANDO VIRTUALIZACIÓN DE FOTOS DE ICLOUD ===")
print(f"Directorio objetivo: {photos_dir}")

high = ctypes.c_ulong()
files_to_dehydrate = []
total_bytes_allocated = 0

print("Escaneando archivos que ocupan espacio físico...")
for root, _, files in os.walk(str(photos_dir)):
    for fname in files:
        fpath = os.path.join(root, fname)
        low = ctypes.windll.kernel32.GetCompressedFileSizeW(fpath, ctypes.byref(high))
        alloc = (high.value << 32) + low
        if alloc > 0:
            files_to_dehydrate.append((fpath, alloc))
            total_bytes_allocated += alloc

print(f"Archivos encontrados ocupando espacio local: {len(files_to_dehydrate)}")
print(f"Espacio total a liberar: {total_bytes_allocated / (1024**3):.2f} GB")

dehydrated_count = 0
bytes_freed = 0
error_count = 0

t0 = time.time()
for idx, (fpath, alloc) in enumerate(files_to_dehydrate, 1):
    try:
        handle = ctypes.windll.kernel32.CreateFileW(
            fpath,
            FILE_WRITE_ATTRIBUTES | FILE_READ_ATTRIBUTES,
            FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
            None,
            OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS,
            None
        )
        if handle != -1 and handle != 0:
            hr = cfapi.CfDehydratePlaceholder(
                handle,
                ctypes.c_longlong(0),
                ctypes.c_longlong(-1),
                0,
                None
            )
            ctypes.windll.kernel32.CloseHandle(handle)
            if hr == 0:
                dehydrated_count += 1
                bytes_freed += alloc
            else:
                error_count += 1
        else:
            error_count += 1
    except Exception:
        error_count += 1

    if idx % 1000 == 0 or idx == len(files_to_dehydrate):
        elapsed = time.time() - t0
        print(f"[{idx}/{len(files_to_dehydrate)}] Virtualizados: {dehydrated_count} | Liberados: {bytes_freed / (1024**3):.2f} GB | Errores: {error_count} ({elapsed:.1f}s)", flush=True)

print(f"\n=== VIRTUALIZACIÓN COMPLETADA ===")
print(f"Total archivos convertidos a nube virtual: {dehydrated_count}")
print(f"Espacio total de disco recuperado: {bytes_freed / (1024**3):.2f} GB")
