import os, pickle
from pathlib import Path

BASE_DIR = Path(r'C:\Users\User\Desktop\Galeria Eneko NO ABRIR')
FOTOS_DIR = BASE_DIR / 'Fotos'
RESULTADOS_DIR = BASE_DIR / 'Resultados'

# 1. Calculate gallery statistics
total_files = 0
ordered_files = 0
dudosos_pending_files = 0
unassigned_files = 0

categories_stats = {}

for bdir in [FOTOS_DIR, RESULTADOS_DIR]:
    if bdir.exists():
        for root, dirs, files in os.walk(str(bdir)):
            valid_fs = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi'))]
            cnt = len(valid_fs)
            total_files += cnt
            
            rel = os.path.relpath(root, str(bdir))
            parts = rel.split(os.sep)
            
            if len(parts) >= 2:
                cat = parts[0]
                ident = parts[1]
                
                if '_dudosos' in root.lower() or 'revision_interactiva' in root.lower():
                    dudosos_pending_files += cnt
                elif cat in ['Desconocidos', 'Sin_Clasificar', 'Unassigned']:
                    unassigned_files += cnt
                else:
                    ordered_files += cnt
                    categories_stats[cat] = categories_stats.get(cat, 0) + cnt
            elif len(parts) == 1 and parts[0] != '.':
                cat = parts[0]
                if cat in ['Desconocidos', 'Sin_Clasificar', 'Unassigned']:
                    unassigned_files += cnt
                elif '_dudosos' in root.lower():
                    dudosos_pending_files += cnt

print("=== GALLERY STATS ===")
print(f"Total files in gallery: {total_files}")
print(f"Ordered files (CONFIRMED): {ordered_files} ({(ordered_files/max(1, total_files))*100:.1f}%)")
print(f"Dudosos / Pending files: {dudosos_pending_files} ({(dudosos_pending_files/max(1, total_files))*100:.1f}%)")
print(f"Unassigned / Unknown files: {unassigned_files} ({(unassigned_files/max(1, total_files))*100:.1f}%)")
print("\nOrdered breakdown by category:")
for cat, cnt in sorted(categories_stats.items(), key=lambda x: x[1], reverse=True):
    print(f" - {cat}: {cnt} photos")

# 2. Patch api_person_avatar in app.py to use recursive find_avatar_image
with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

avatar_helper = """
def find_avatar_image(target_dir):
    valid_exts = {".jpg", ".jpeg", ".png"}
    if not target_dir: return None
    if isinstance(target_dir, str): target_dir = Path(target_dir)
    if not target_dir.exists(): return None
    if target_dir.is_file() and target_dir.suffix.lower() in valid_exts:
        return str(target_dir.resolve())
    if target_dir.is_dir():
        for root, dirs, files in os.walk(str(target_dir)):
            for f in files:
                if Path(f).suffix.lower() in valid_exts:
                    full_p = os.path.join(root, f)
                    try:
                        if os.path.getsize(full_p) > 1024:
                            return full_p
                    except:
                        pass
    return None
"""

if "def find_avatar_image" not in app_code:
    app_code = app_code.replace("def api_person_avatar():", avatar_helper + "\ndef api_person_avatar():")

old_find_first = """    # Find first valid image
    first_img_path = None
    valid_exts = {".jpg", ".jpeg", ".png"}
    if target_dir.is_file():
        if target_dir.suffix.lower() in valid_exts:
            first_img_path = str(target_dir.resolve())
    elif target_dir.is_dir():
        for f in target_dir.iterdir():
            if f.is_file() and f.suffix.lower() in valid_exts:
                first_img_path = str(f.resolve())
                break"""

new_find_first = """    # Find first valid image recursively
    first_img_path = find_avatar_image(RESULTADOS_DIR / cat / ident)
    if not first_img_path:
        first_img_path = find_avatar_image(FOTOS_DIR / cat / ident)"""

if old_find_first in app_code:
    app_code = app_code.replace(old_find_first, new_find_first)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(app_code)
    print("Patched api_person_avatar with recursive find_avatar_image!")
