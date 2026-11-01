import re
import os

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add dhash caching
dhash_cache_code = '''
DHASH_CACHE_FILE = Path("dhash_cache.pkl")
_DHASH_CACHE = {}
if DHASH_CACHE_FILE.exists():
    try:
        import pickle
        with open(DHASH_CACHE_FILE, 'rb') as f:
            _DHASH_CACHE = pickle.load(f)
    except:
        pass

def save_dhash_cache():
    try:
        import pickle
        with open(DHASH_CACHE_FILE, 'wb') as f:
            pickle.dump(_DHASH_CACHE, f)
    except:
        pass

def calculate_dhash(filepath):
    global _DHASH_CACHE
    try:
        file_key = get_file_key(filepath)
        if file_key in _DHASH_CACHE:
            return _DHASH_CACHE[file_key]
            
        path_obj = Path(filepath)
        if path_obj.suffix.lower() in [".mp4", ".mov", ".avi"]:
            cap = cv2.VideoCapture(str(filepath))
            fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if fc > 10: cap.set(cv2.CAP_PROP_POS_FRAMES, fc // 2)
            ret, img = cap.read()
            cap.release()
            if not ret or img is None: return None
        else:
            file_bytes = np.fromfile(str(filepath), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None: return None
            
        resized = cv2.resize(img, (9, 8), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        h = (gray[:, 1:] > gray[:, :-1]).flatten()
        _DHASH_CACHE[file_key] = h
        return h
    except:
        return None
'''

# Replace old calculate_dhash
start_idx = content.find('def calculate_dhash(filepath):')
end_idx = content.find('@app.route(\'/api/duplicates\', methods=[\'POST\'])')
content = content[:start_idx] + dhash_cache_code + '\n' + content[end_idx:]

# 2. Modify get_gallery() to add group_id
get_gallery_end_idx = content.find('global _GALLERY_CACHE\n    _GALLERY_CACHE = gallery')

group_logic = '''
    # Group items by dhash similarity
    import numpy as np
    cache_dirty = False
    for cat in gallery:
        for ident in gallery[cat]:
            items = gallery[cat][ident]
            groups = []
            for item in items:
                h = calculate_dhash(item["path"])
                placed = False
                if h is not None:
                    for g in groups:
                        rep_hash = calculate_dhash(g[0]["path"])
                        if rep_hash is not None and len(h) == len(rep_hash):
                            hamming_dist = np.count_nonzero(h != rep_hash)
                            similarity = round((1.0 - (hamming_dist / len(h))) * 100, 1)
                            if similarity >= 85.0:
                                g.append(item)
                                placed = True
                                break
                if not placed:
                    groups.append([item])
            
            # Sort items within group (e.g. shortest name or random) and assign group_id
            for i, g in enumerate(groups):
                for item in g:
                    item["group_id"] = i
                    item["group_size"] = len(g)
                    item["is_group_rep"] = (item == g[0])
                    
    save_dhash_cache()
'''

content = content[:get_gallery_end_idx] + group_logic + '\n    ' + content[get_gallery_end_idx:]

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
