import os
import json
from pathlib import Path

FOTOS_DIR = Path("Fotos")
GALLERY_DATA_FILE = Path("duplicate_groups.json")

def find_duplicates():
    files_by_key = {}
    valid_exts = {".jpg", ".jpeg", ".png"} # only photos, videos are huge
    
    print("Clustering photos by size & timestamp...")
    for root, dirs, files in os.walk(str(FOTOS_DIR)):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in valid_exts:
                p = Path(root) / file
                try:
                    stat = p.stat()
                    # Key: File size and modification time (rounded to 2 seconds for burst photos)
                    size = stat.st_size
                    mtime = int(stat.st_mtime) // 2
                    key = f"{size}_{mtime}"
                    if key not in files_by_key:
                        files_by_key[key] = []
                    files_by_key[key].append(str(p.resolve()))
                except Exception:
                    pass

    groups = {}
    group_id_counter = 1
    
    for key, paths in files_by_key.items():
        if len(paths) > 1:
            # Check if they are actually the same filename (duplicates across categories) or burst photos
            group_id = f"g_{group_id_counter}"
            for p in paths:
                groups[p] = {
                    "group_id": group_id,
                    "group_size": len(paths),
                    "is_rep": (p == paths[0])
                }
            group_id_counter += 1
            
    with open(GALLERY_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(groups, f)
    
    print(f"Found {group_id_counter - 1} duplicate groups.")

if __name__ == "__main__":
    find_duplicates()
