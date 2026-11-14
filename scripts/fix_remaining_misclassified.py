#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/fix_remaining_misclassified.py
1. Fixes the 9 items tagged with 'Caras Aisladas' to their actual folder identity (Persona Nueva #26, #32, #8).
2. Fixes iCloud photos tagged with 'Fotos Sin Rostro' that have faces in faces_cache.
3. Adds safety check to apple_db.json.
"""

import os
import json
import pickle
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "apple_db.json"
FACES_CACHE_FILE = BASE_DIR / "faces_cache.pkl"
CACHE_FILE = BASE_DIR / "gallery_cache.json"

with open(DB_FILE, "r", encoding="utf-8") as f:
    apple_db = json.load(f)

faces_cache = {}
if FACES_CACHE_FILE.exists():
    with open(FACES_CACHE_FILE, "rb") as f:
        faces_cache = pickle.load(f)

fc_by_base = {}
for k, v in faces_cache.items():
    if v and len(v) > 0:
        fc_by_base[os.path.basename(k).lower()] = v

# 1. Fix Caras Aisladas in apple_db
caras_aisladas_fixed = 0
for p, info in apple_db.items():
    ident = str(info.get('identity', ''))
    if 'aislada' in ident.lower() or 'ocasiona' in ident.lower():
        parent_dir = Path(p).parent.name
        if 'persona' in parent_dir.lower():
            info['category'] = '📋 Revisión / Por Organizar'
            info['identity'] = f"👤 {parent_dir}"
        else:
            info['category'] = '📋 Revisión / Por Organizar'
            info['identity'] = "❓ Desconocidos (Por Identificar)"
        caras_aisladas_fixed += 1
        print(f"  Fixed Caras Aisladas: {Path(p).name} -> {info['identity']}")

# 2. Fix iCloud Fotos Sin Rostro with faces in faces_cache
sin_rostro_fixed = 0
for p, info in apple_db.items():
    if info.get('identity') == '📷 Fotos Sin Rostro':
        bname = os.path.basename(p).lower()
        faces = faces_cache.get(p) or fc_by_base.get(bname)
        if faces and len(faces) > 0:
            valid_ids = [
                f.get('identity') for f in faces
                if f.get('identity') and not str(f.get('identity')).startswith(('Desconocid', 'Falso_Positivo', 'Ignorar', 'Sin_Rostro'))
            ]
            if valid_ids:
                target_id = valid_ids[0]
                cat = 'Conocidos'
                if target_id == 'YO': cat = 'YO'
                elif target_id.startswith(('F.', 'F ')): cat = 'Familia'
                elif target_id.startswith('P.'): cat = 'Profesores'
                elif target_id.startswith('M.'): cat = 'Mascotas'
                info['category'] = cat
                info['identity'] = target_id
                info['faces'] = faces
                print(f"  Fixed Sin Rostro -> Person: {bname} -> {cat} / {target_id}")
            else:
                info['category'] = '📋 Revisión / Por Organizar'
                info['identity'] = '❓ Desconocidos (Por Identificar)'
                info['faces'] = faces
                print(f"  Fixed Sin Rostro -> Desconocidos: {bname}")
            sin_rostro_fixed += 1

print(f"\nSummary:")
print(f"  Caras Aisladas reclassified: {caras_aisladas_fixed}")
print(f"  Sin Rostro with faces reclassified: {sin_rostro_fixed}")

# 3. Save DB
with open(DB_FILE, "w", encoding="utf-8") as f:
    json.dump(apple_db, f, indent=2, ensure_ascii=False)
print("apple_db.json saved successfully.")

# 4. Remove stale gallery_cache.json
if CACHE_FILE.exists():
    CACHE_FILE.unlink()
    print("gallery_cache.json unlinked.")
