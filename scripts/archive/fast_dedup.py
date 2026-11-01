import os, hashlib, pickle
from pathlib import Path

base_dir = Path(r'C:\Users\User\Desktop\Galeria Eneko NO ABRIR')

# 1. Group by file size first
size_map = {}
total_scanned = 0

for root, dirs, files in os.walk(str(base_dir)):
    for f in files:
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi')):
            p = Path(root) / f
            try:
                sz = p.stat().st_size
                if sz not in size_map:
                    size_map[sz] = []
                size_map[sz].append(p)
                total_scanned += 1
            except:
                pass

print(f"Scanned {total_scanned} files. Grouped into {len(size_map)} size buckets.")

# 2. Only hash files that share the EXACT SAME byte size!
hash_map = {}
candidate_count = 0

for sz, paths in size_map.items():
    if len(paths) > 1:
        candidate_count += len(paths)
        for p in paths:
            try:
                with open(p, 'rb') as f:
                    md5 = hashlib.md5(f.read()).hexdigest()
                if md5 not in hash_map:
                    hash_map[md5] = []
                hash_map[md5].append(p)
            except:
                pass

print(f"Hashed {candidate_count} size-matching candidate files.")

purged_count = 0
for md5, paths in hash_map.items():
    if len(paths) > 1:
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
                pass

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
