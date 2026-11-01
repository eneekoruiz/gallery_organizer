import os
import re
from pathlib import Path

RESULTADOS_DIR = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados")

print("Iniciando purga de enlaces duros duplicados en disco...")

deleted_count = 0
pattern = re.compile(r"^(.+)_\d+(\.[a-zA-Z0-9]+)$")

for root, dirs, files in os.walk(str(RESULTADOS_DIR)):
    # Mapear inodos presentes en este directorio
    inodes_in_dir = {}
    for f in files:
        fpath = Path(root) / f
        try:
            ino = os.stat(str(fpath)).st_ino
            if ino not in inodes_in_dir:
                inodes_in_dir[ino] = []
            inodes_in_dir[ino].append(fpath)
        except Exception:
            pass

    for ino, file_list in inodes_in_dir.items():
        if len(file_list) > 1:
            # Ordenar para conservar el más corto (sin _1, _2...)
            file_list.sort(key=lambda p: len(p.name))
            keeper = file_list[0]
            duplicates = file_list[1:]
            
            for dup in duplicates:
                try:
                    os.remove(str(dup))
                    deleted_count += 1
                    print(f"Borrado duplicado inodo: {dup.name} (se mantiene {keeper.name})")
                except Exception as e:
                    print(f"Error borrando {dup}: {e}")

print(f"========================================")
print(f"Purga finalizada. Se han eliminado {deleted_count} copias duplicadas de enlaces duros en el disco.")
print(f"========================================")
