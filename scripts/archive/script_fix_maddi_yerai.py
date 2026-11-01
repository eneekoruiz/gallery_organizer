import os, pickle, shutil, gc
from pathlib import Path

base_dir = Path(r'C:\Users\User\Desktop\Galeria Eneko NO ABRIR')
target_dir = base_dir / 'Resultados' / 'Conocidos' / 'C. Yerai Vidal'
target_dir.mkdir(parents=True, exist_ok=True)

# 1. Find all files in Maddi Egibar folders
maddi_files = []
for root, dirs, files in os.walk(str(base_dir)):
    if 'maddi egibar' in root.lower():
        for f in files:
            maddi_files.append(Path(root) / f)

print(f"Found {len(maddi_files)} files in Maddi Egibar folders.")

moved_count = 0
path_map = {} # old_path -> new_path

for src in maddi_files:
    if not src.exists(): continue
    dst = target_dir / src.name
    counter = 1
    while dst.exists():
        dst = target_dir / f"{src.stem}_{counter}{src.suffix}"
        counter += 1
        
    try:
        shutil.move(str(src), str(dst))
        moved_count += 1
        path_map[str(src)] = str(dst)
        path_map[str(src.resolve())] = str(dst.resolve())
    except Exception as e:
        print(f"Error moving {src}: {e}")

print(f"Successfully moved {moved_count} files to 'C. Yerai Vidal'.")

# 2. Update faces_cache.pkl
cache_file = Path("faces_cache.pkl")
if cache_file.exists():
    with open(cache_file, 'rb') as f:
        faces_cache = pickle.load(f)
        
    updated_cache = {}
    for k, v in faces_cache.items():
        new_k = path_map.get(k, k)
        # Update identities inside list
        if isinstance(v, list):
            for item in v:
                if isinstance(item, dict) and item.get('identity') == 'C. Maddi Egibar':
                    item['identity'] = 'C. Yerai Vidal'
                    item['is_manual'] = True
        updated_cache[new_k] = v
        
    with open(cache_file, 'wb') as f:
        pickle.dump(updated_cache, f)
    print("Updated faces_cache.pkl")

# 3. Clean up empty Maddi Egibar directories
for root, dirs, files in os.walk(str(base_dir), topdown=False):
    if 'maddi egibar' in root.lower():
        try:
            os.rmdir(root)
            print(f"Removed empty directory: {root}")
        except:
            pass

print("Finished manual correction of Maddi Egibar -> Yerai Vidal.")
