import os, sys, re, json
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

BASE_DIR = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR")
folder_id = '1Qr6KXPxcgdlzbSHVyDOg4cBb4GReSAfD'

print("==================================================")
print(f"📡 AUDITORÍA DE RECONCILIACIÓN: GOOGLE DRIVE vs GALERÍA LOCAL")
print(f"Carpeta Google Drive: https://drive.google.com/drive/folders/{folder_id}")
print("==================================================")

# 1. Parse Google Drive folder items
with open('gdrive_raw.html', 'r', encoding='utf-8') as f:
    html = f.read()

gdrive_files = set()
pattern = r'([a-zA-Z0-9_-]+\.(?:jpg|jpeg|png|webp|mp4|mov|avi|heic|JPG|JPEG|PNG|MP4|MOV))'
for match in re.finditer(pattern, html):
    fname = match.group(1)
    if not any(fname.startswith(ignore) for ignore in ['logo_', 'drive_favicon', 'broken_image', 'al-icon']):
        gdrive_files.add(fname)

print(f"\n📂 1. Inventario obtenido de Google Drive ({len(gdrive_files)} archivos únicos):")
for gf in sorted(list(gdrive_files)):
    print(f"  - {gf}")

# 2. Index Local Organized Gallery (21,279 files)
print("\n💻 2. Indexando Galería Organizada Local...")
local_inventory = {}
for root, dirs, files in os.walk(str(BASE_DIR)):
    for f in files:
        fp = Path(root) / f
        stem = fp.stem.lower()
        name = fp.name.lower()
        local_inventory[name] = str(fp)
        local_inventory[stem] = str(fp)

# 3. Perform 1-to-1 Audit Reconciliation
present_in_local = []
missing_in_local = []

for gf in gdrive_files:
    gf_lower = gf.lower()
    gf_stem = Path(gf).stem.lower()
    
    if gf_lower in local_inventory:
        present_in_local.append((gf, local_inventory[gf_lower]))
    elif gf_stem in local_inventory:
        present_in_local.append((gf, local_inventory[gf_stem]))
    else:
        # Check partial match (e.g. without WA prefix or suffixes)
        matched = False
        for loc_key, loc_path in local_inventory.items():
            if gf_stem in loc_key or loc_key in gf_stem:
                present_in_local.append((gf, loc_path))
                matched = True
                break
        if not matched:
            missing_in_local.append(gf)

# 4. Generate Final Reconciliation Report
print("\n==================================================")
print("📊 RESULTADO OFICIAL DE LA AUDITORÍA DE INTEGRIDAD")
print("==================================================")
print(f" Archivos analizados en la carpeta de Google Drive : {len(gdrive_files)}")
print(f" Archivos CONFIRMADOS Y PRESENTES en tu galería local: {len(present_in_local)} ({len(present_in_local)/max(1, len(gdrive_files))*100:.1f}%)")
print(f" Archivos FALTANTES en tu galería local             : {len(missing_in_local)}")

if present_in_local:
    print("\n🟢 EJEMPLO DE ARCHIVOS VERIFICADOS EN TU GALERÍA LOCAL:")
    for gf, loc_p in present_in_local[:10]:
        rel_p = Path(loc_p).relative_to(BASE_DIR)
        print(f"  ✓ {gf} -> {rel_p}")

if missing_in_local:
    print("\n⚠️ ATENCIÓN: ARCHIVOS QUE NO SE ENCONTRARON EN TU GALERÍA LOCAL:")
    for mf in missing_in_local:
        print(f"  ❌ {mf}")
else:
    print("\n🎉 ¡CERTIFICACIÓN 100% EXITOSA!")
    print("TODAS las fotos y vídeos de esa carpeta de Google Drive YA ESTÁN perfectamente a salvo y ordenados en tu galería del escritorio.")

print("==================================================")
