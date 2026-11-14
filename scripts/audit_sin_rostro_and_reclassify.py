#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/audit_sin_rostro_and_reclassify.py
Rigorous audit of Sin_Rostro:
1. Identifies all files in Sin_Rostro that have detected faces.
2. If faces belong to known persons, reclassifies and moves them to their proper person album.
3. If faces are unassigned or invalid person name, moves them to Desconocidos.
4. Updates apple_db.json and rebuilds gallery_cache.json cleanly.
"""

import os
import re
import shutil
import json
import pickle
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "apple_db.json"
CACHE_FILE = BASE_DIR / "gallery_cache.json"
FACES_CACHE_FILE = BASE_DIR / "faces_cache.pkl"

SIN_ROSTRO_DIR = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados\Revision_Interactiva\Sin_Rostro")
RESULTADOS_DIR = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados")

print("=== STARTING RIGOROUS AUDIT OF SIN_ROSTRO ===")

# 1. Load DB
with open(DB_FILE, "r", encoding="utf-8") as f:
    apple_db = json.load(f)

# 2. Load faces_cache
faces_cache = {}
if FACES_CACHE_FILE.exists():
    with open(FACES_CACHE_FILE, "rb") as f:
        faces_cache = pickle.load(f)
print(f"Loaded faces_cache with {len(faces_cache)} entries.")

# Build basename lookup
fc_by_base = {}
for k, v in faces_cache.items():
    if v and len(v) > 0:
        fc_by_base[os.path.basename(k).lower()] = (k, v)

# Category lookup from DB
ident_to_cat = {}
for p, info in apple_db.items():
    cat = info.get("category")
    ident = info.get("identity")
    if ident and cat and cat != "📋 Revisión / Por Organizar":
        ident_to_cat[ident] = cat

def is_valid_person(name):
    if not name: return False
    nl = name.lower()
    if any(k in nl for k in ['sin rostro', 'sin_rostro', 'filtro', 'desconocid', 'falso_positivo', 'ignorar', 'excluid', 'descartad', 'error']):
        return False
    return True

# 3. Scan files in Sin_Rostro
sin_files = list(SIN_ROSTRO_DIR.glob("*"))
print(f"Found {len(sin_files)} files in Sin_Rostro directory.")

moved_to_person = 0
moved_to_desconocidos = 0
kept_sin_rostro = 0

for file_path in sin_files:
    if not file_path.is_file():
        continue
    sp = str(file_path)
    bname = file_path.name.lower()
    
    # Check if file has detected faces in cache
    faces = None
    if sp in faces_cache and faces_cache[sp]:
        faces = faces_cache[sp]
    elif bname in fc_by_base:
        orig_p, faces = fc_by_base[bname]

    if faces and len(faces) > 0:
        # Check if any face has an identified person
        valid_ids = [
            f.get("identity") for f in faces
            if f.get("identity") and is_valid_person(str(f.get("identity")))
        ]
        
        if valid_ids:
            target_person = valid_ids[0].strip()
            # Sanitize path characters
            clean_person = re.sub(r'[\\/:*?"<>|]', '_', target_person).strip()
            target_cat = ident_to_cat.get(target_person)
            if not target_cat:
                if clean_person.startswith(("C.", "C ")): target_cat = "Conocidos"
                elif clean_person.startswith(("F.", "F ")): target_cat = "Familia"
                elif clean_person == "YO": target_cat = "YO"
                elif clean_person.startswith("P."): target_cat = "Profesores"
                elif clean_person.startswith("M."): target_cat = "Mascotas"
                else: target_cat = "Conocidos"
            
            target_dir = RESULTADOS_DIR / target_cat / clean_person
            target_dir.mkdir(parents=True, exist_ok=True)
            new_path = target_dir / file_path.name
            
            try:
                shutil.move(str(file_path), str(new_path))
                apple_db[str(new_path)] = {
                    "category": target_cat,
                    "identity": clean_person,
                    "manual": True,
                    "confidence": 1.0,
                    "faces": faces
                }
                if sp in apple_db:
                    del apple_db[sp]
                moved_to_person += 1
                if moved_to_person <= 15:
                    print(f"  [PERSON] Moved {file_path.name} -> {target_cat} / {clean_person}")
            except Exception as e:
                print(f"  [ERROR] Failed to move {file_path.name}: {e}")
        else:
            # Has faces, but unknown or unassigned
            target_dir = RESULTADOS_DIR / "Personas Sin Nombre" / "Desconocidos"
            target_dir.mkdir(parents=True, exist_ok=True)
            new_path = target_dir / file_path.name
            
            try:
                shutil.move(str(file_path), str(new_path))
                apple_db[str(new_path)] = {
                    "category": "📋 Revisión / Por Organizar",
                    "identity": "❓ Desconocidos (Por Identificar)",
                    "confidence": 0.5,
                    "faces": faces
                }
                if sp in apple_db:
                    del apple_db[sp]
                moved_to_desconocidos += 1
                if moved_to_desconocidos <= 15:
                    print(f"  [DESCONOCIDOS] Moved {file_path.name} -> Desconocidos")
            except Exception as e:
                print(f"  [ERROR] Failed to move {file_path.name}: {e}")
    else:
        kept_sin_rostro += 1

print(f"\nAudit complete:")
print(f"  Moved to Known Person: {moved_to_person}")
print(f"  Moved to Desconocidos (has faces): {moved_to_desconocidos}")
print(f"  Kept in Sin_Rostro (genuine no faces): {kept_sin_rostro}")

# 4. Save updated apple_db.json
with open(DB_FILE, "w", encoding="utf-8") as f:
    json.dump(apple_db, f, indent=2, ensure_ascii=False)
print("Updated apple_db.json successfully.")

# 5. Clear stale gallery_cache.json
if CACHE_FILE.exists():
    CACHE_FILE.unlink()
    print("Deleted stale gallery_cache.json to trigger full clean rebuild.")

print("=== AUDIT AND RECLASSIFICATION COMPLETE ===")
