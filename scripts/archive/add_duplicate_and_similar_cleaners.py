import os, sys, json, hashlib, cv2, shutil
import numpy as np
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# Read app.py
with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

new_backend_routes = """
# ==========================================
# 👯 SISTEMA INTERACTIVO DE DUPLICADOS Y SIMILARES
# ==========================================

def get_fast_fingerprint_file(filepath):
    try:
        st = os.stat(filepath)
        size = st.st_size
        if size == 0: return None
        hasher = hashlib.md5()
        hasher.update(f"{size}".encode('utf-8'))
        with open(filepath, 'rb') as f:
            chunk1 = f.read(128 * 1024)
            hasher.update(chunk1)
            if size > 512 * 1024:
                f.seek(size - 128 * 1024)
                chunk2 = f.read(128 * 1024)
                hasher.update(chunk2)
        return hasher.hexdigest()
    except:
        return None

def compute_sharpness_score(filepath):
    try:
        ext = Path(filepath).suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
            return 50.0
        img = cv2.imread(str(filepath), cv2.IMREAD_GRAYSCALE)
        if img is None: return 0.0
        # Resize for fast calculation
        h, w = img.shape[:2]
        if max(h, w) > 640:
            scale = 640.0 / max(h, w)
            img = cv2.resize(img, (0, 0), fx=scale, fy=scale)
        score = cv2.Laplacian(img, cv2.CV_64F).var()
        return round(float(score), 1)
    except:
        return 0.0

@app.route('/api/duplicates_scan')
def api_duplicates_scan():
    valid_exts = {".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi", ".webp", ".heic"}
    all_files = []
    
    for base_dir in [RESULTADOS_DIR, FOTOS_DIR]:
        if base_dir.exists():
            for root, dirs, files in os.walk(str(base_dir)):
                for f in files:
                    if Path(f).suffix.lower() in valid_exts:
                        all_files.append(os.path.join(root, f))
                        
    def hash_worker(fp):
        return (fp, get_fast_fingerprint_file(fp))

    with ThreadPoolExecutor(max_workers=16) as executor:
        results = list(executor.map(hash_worker, all_files))
        
    hash_groups = {}
    for fp, h in results:
        if h:
            if h not in hash_groups: hash_groups[h] = []
            hash_groups[h].append(fp)
            
    dup_groups = []
    total_reclaimable = 0
    
    for h, fpaths in hash_groups.items():
        if len(fpaths) > 1:
            files_data = []
            group_bytes = 0
            for idx, fp in enumerate(fpaths):
                sz = os.path.getsize(fp) if os.path.exists(fp) else 0
                if idx > 0: group_bytes += sz
                files_data.append({
                    "path": fp,
                    "name": Path(fp).name,
                    "size_mb": f"{sz / (1024*1024):.2f} MB",
                    "bytes": sz,
                    "is_keeper": (idx == 0)
                })
            total_reclaimable += group_bytes
            dup_groups.append({
                "group_id": h,
                "reclaimable_bytes": group_bytes,
                "reclaimable_mb": f"{group_bytes / (1024*1024):.2f} MB",
                "files": files_data
            })
            
    dup_groups.sort(key=lambda x: x['reclaimable_bytes'], reverse=True)
    
    return jsonify({
        "total_groups": len(dup_groups),
        "reclaimable_bytes": total_reclaimable,
        "reclaimable_gb": f"{total_reclaimable / (1024**3):.2f} GB",
        "groups": dup_groups[:50]
    })

@app.route('/api/duplicates_clean', methods=['POST'])
def api_duplicates_clean():
    data = request.json or {}
    files_to_delete = data.get('files', [])
    
    deleted_count = 0
    freed_bytes = 0
    
    for fp in files_to_delete:
        if os.path.exists(fp):
            try:
                sz = os.path.getsize(fp)
                os.remove(fp)
                deleted_count += 1
                freed_bytes += sz
            except Exception as e:
                print("Error deleting duplicate:", e)
                
    global _GALLERY_CACHE
    _GALLERY_CACHE = None
    
    return jsonify({
        "status": "success",
        "deleted_count": deleted_count,
        "freed_gb": f"{freed_bytes / (1024**3):.2f} GB"
    })

@app.route('/api/similar_scan')
def api_similar_scan():
    valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
    folder_files = {}
    
    for base_dir in [RESULTADOS_DIR, FOTOS_DIR]:
        if base_dir.exists():
            for root, dirs, files in os.walk(str(base_dir)):
                imgs = [os.path.join(root, f) for f in files if Path(f).suffix.lower() in valid_exts]
                if len(imgs) > 1:
                    folder_files[root] = imgs
                    
    burst_groups = []
    
    for folder, imgs in folder_files.items():
        # Sort by filename which usually reflects sequence/timestamp
        imgs.sort()
        current_burst = [imgs[0]]
        
        for i in range(1, len(imgs)):
            prev_name = Path(imgs[i-1]).stem.lower()
            curr_name = Path(imgs[i]).stem.lower()
            
            # Check prefix similarity or close sequence
            prefix_len = min(len(prev_name), len(curr_name), 10)
            if prefix_len > 4 and prev_name[:prefix_len] == curr_name[:prefix_len]:
                current_burst.append(imgs[i])
            else:
                if len(current_burst) > 1:
                    burst_groups.append(current_burst)
                current_burst = [imgs[i]]
                
        if len(current_burst) > 1:
            burst_groups.append(current_burst)
            
    formatted_bursts = []
    for burst in burst_groups[:30]:
        files_info = []
        for fp in burst:
            score = compute_sharpness_score(fp)
            sz = os.path.getsize(fp) if os.path.exists(fp) else 0
            files_info.append({
                "path": fp,
                "name": Path(fp).name,
                "size_mb": f"{sz / (1024*1024):.2f} MB",
                "sharpness": score
            })
        files_info.sort(key=lambda x: x['sharpness'], reverse=True)
        # Mark keeper as highest sharpness score
        for idx, fi in enumerate(files_info):
            fi['is_sharpest'] = (idx == 0)
            
        formatted_bursts.append({
            "folder": Path(burst[0]).parent.name,
            "count": len(files_info),
            "files": files_info
        })
        
    return jsonify({
        "total_burst_groups": len(formatted_bursts),
        "bursts": formatted_bursts
    })
"""

if '/api/duplicates_scan' not in app_code:
    app_code += "\n" + new_backend_routes

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code)

print("Updated app.py with duplicates and similar photos scanner endpoints!")
