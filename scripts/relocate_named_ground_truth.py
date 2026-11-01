"""Relocate ground-truth named photos to their correct canonical folders.

Fixes 1,605+ misplaced photos like 'Fotos Sara Callejón~XX' sitting in other people's albums.
Uses atomic safe_move_file with zero data loss.
"""

import sys
import re
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.utils.file_ops import safe_move_file
from app.globals import clear_gallery_cache

base = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados")

# Map clean person names to real destination directories
target_dirs = {}
for cat in ['Conocidos', 'Familia', 'Mascotas', 'YO', 'Profesores', 'Amigos']:
    cat_dir = base / cat
    if not cat_dir.exists():
        continue
    for p_dir in cat_dir.iterdir():
        if p_dir.is_dir():
            clean = re.sub(r'^[CFM]\.\s*', '', p_dir.name).lower().strip()
            target_dirs[clean] = p_dir

print(f"Mapped {len(target_dirs)} canonical identity folders.")

mismatches = []
for cat in ['Conocidos', 'Familia', 'Mascotas', 'YO', 'Profesores', 'Amigos']:
    cat_dir = base / cat
    if not cat_dir.exists():
        continue
    for person_dir in cat_dir.iterdir():
        if not person_dir.is_dir():
            continue
        folder_name = person_dir.name
        clean_folder = re.sub(r'^[CFM]\.\s*', '', folder_name).lower().strip()
        
        for f in person_dir.iterdir():
            if not f.is_file():
                continue
            m = re.match(r'^Fotos\s+([^~]+)~', f.name, re.IGNORECASE)
            if m:
                named = m.group(1).lower().strip()
                if named != clean_folder and not clean_folder.startswith(named) and not named.startswith(clean_folder):
                    mismatches.append((person_dir, f, named))

print(f"Found {len(mismatches)} misplaced ground-truth photos to relocate.")

moved = 0
created = 0
errors = 0

for src_dir, file_path, named in mismatches:
    try:
        dest_dir = target_dirs.get(named)
        if not dest_dir:
            # Create new Conocidos folder for this person
            folder_title = "C. " + " ".join(word.capitalize() for word in named.split())
            dest_dir = base / "Conocidos" / folder_title
            dest_dir.mkdir(parents=True, exist_ok=True)
            target_dirs[named] = dest_dir
            created += 1
            
        success = safe_move_file(file_path, dest_dir)
        if success:
            moved += 1
        else:
            errors += 1
    except Exception as e:
        errors += 1

print("\n--- RESUMEN DE REUBICACIÓN ---")
print(f"Total fotos reubicadas correctamente a sus verdaderos dueños: {moved}")
print(f"Carpetas creadas para personas sin carpeta previa: {created}")
print(f"Errores: {errors}")

clear_gallery_cache()
print("Caché de galería invalidado exitosamente.")
