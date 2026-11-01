import os
import sys
import re
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

base = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados")
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
                named_person = m.group(1).lower().strip()
                if named_person != clean_folder and not clean_folder.startswith(named_person) and not named_person.startswith(clean_folder):
                    mismatches.append((cat, folder_name, f.name, named_person, str(f)))

print(f"Total ground-truth filename mismatches found across ALL folders: {len(mismatches)}")
for cat, folder, fname, named, fpath in mismatches[:35]:
    print(f"  [{cat}] In '{folder}': '{fname}' -> Belongs to '{named}'")
