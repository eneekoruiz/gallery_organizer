import os, hashlib, pickle
from pathlib import Path

base_dir = Path(r'C:\Users\User\Desktop\Galeria Eneko NO ABRIR')

# Collect all media files
all_files = []
for root, dirs, files in os.walk(str(base_dir)):
    for f in files:
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi')):
            all_files.append(Path(root) / f)

print(f"Scanning {len(all_files)} total media files for exact duplicates...")

hash_map = {} # md5 -> list of Path objects
for p in all_files:
    if not p.exists(): continue
    try:
        with open(p, 'rb') as f:
            # Read first 1MB + size for fast hashing, then full hash
            data = f.read()
            md5 = hashlib.md5(data).hexdigest()
        if md5 not in hash_map:
            hash_map[md5] = []
        hash_map[md5].append(p)
    except Exception as e:
        pass

purged_count = 0
kept_files = []

for md5, paths in hash_map.items():
    if len(paths) > 1:
        # Sort paths to keep the best one:
        # 1. Prefer Resultados/Conocidos, Familia, YO over Fotos or _Dudosos
        def score_path(p):
            p_str = str(p)
            score = 0
            if 'Resultados' in p_str: score += 10
            if 'Conocidos' in p_str or 'Familia' in p_str or 'YO' in p_str: score += 10
            if '_Dudosos' in p_str: score -= 5
            return score
            
        sorted_paths = sorted(paths, key=score_path, reverse=True)
        keep_p = sorted_paths[0]
        remove_p_list = sorted_paths[1:]
        
        for rem in remove_p_list:
            try:
                os.remove(str(rem))
                purged_count += 1
            except Exception as e:
                print(f"Error removing {rem}: {e}")

print(f"✅ PURGED {purged_count} EXACT DUPLICATE FILES from disk!")

# Update faces_cache.pkl
cache_file = Path("faces_cache.pkl")
if cache_file.exists():
    with open(cache_file, 'rb') as f:
        faces_cache = pickle.load(f)
    cleaned_faces_cache = {k: v for k, v in faces_cache.items() if os.path.exists(k)}
    with open(cache_file, 'wb') as f:
        pickle.dump(cleaned_faces_cache, f)
    print("Cleaned faces_cache.pkl")
