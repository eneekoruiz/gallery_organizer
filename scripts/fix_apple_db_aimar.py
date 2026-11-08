import json
import pickle
import os
import numpy as np

print("=== FIXING APPLE_DB FALSE AIMAR SAUCA ASSIGNMENTS ===")

with open('centroids.pkl', 'rb') as f:
    centroids = pickle.load(f)

norm_centroids = {}
for k, v in centroids.items():
    if isinstance(k, tuple):
        arr = np.array(v, dtype=np.float32).flatten()
        n = np.linalg.norm(arr)
        if n > 0:
            norm_centroids[k] = arr / n

v_real_aimar = norm_centroids[('Conocidos', 'C. Aimar Sauca')]

with open('apple_db.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

reassigned = 0

for photo_path, photo_data in db.items():
    faces = photo_data.get('faces', [])
    modified = False
    
    for i, fc in enumerate(faces):
        ident = str(fc.get('identity', ''))
        sugg = str(fc.get('suggested_identity', ''))
        lbl = str(fc.get('label', ''))
        
        if 'Aimar Sauca' in ident or 'Aimar Sauca' in sugg or 'Aimar Sauca' in lbl:
            feat = fc.get('feature') or fc.get('embedding')
            if feat:
                arr = np.array(feat, dtype=np.float32).flatten()
                norm = np.linalg.norm(arr)
                if norm > 0:
                    vec = arr / norm
                    sim_aimar = float(np.dot(vec, v_real_aimar))
                    
                    if sim_aimar < 0.38:
                        # Find best legitimate match
                        scores = []
                        for ckey, cvec in norm_centroids.items():
                            if ckey[1] == 'C. Aimar Sauca': continue
                            sim = float(np.dot(vec, cvec))
                            scores.append((sim, ckey))
                        scores.sort(reverse=True)
                        
                        top_sim, top_ckey = scores[0] if scores else (0.0, ('', 'Desconocido'))
                        new_name = top_ckey[1] if top_sim >= 0.45 else 'Desconocido'
                        
                        print(f"Reassigning face {i} in {os.path.basename(photo_path)}: sim to Aimar was {sim_aimar:.4f} -> {new_name} ({top_sim:.4f})")
                        fc['identity'] = new_name
                        fc['suggested_identity'] = None
                        fc['suggested_score'] = 0.0
                        fc['label'] = new_name
                        fc['category'] = top_ckey[0] if top_sim >= 0.45 else 'Desconocido'
                        modified = True
                        reassigned += 1
            else:
                fc['identity'] = 'Desconocido'
                fc['suggested_identity'] = None
                fc['label'] = 'Desconocido'
                modified = True
                reassigned += 1

    if modified:
        # Rebuild photo identities list
        clean_idents = []
        for fc in faces:
            id_val = fc.get('identity')
            if id_val and id_val not in clean_idents:
                clean_idents.append(id_val)
        photo_data['identities'] = clean_idents

print(f"\nTotal misassigned faces fixed in apple_db: {reassigned}")

with open('apple_db.json', 'w', encoding='utf-8') as f:
    json.dump(db, f, indent=2, ensure_ascii=False)

if os.path.exists('gallery_cache.json'):
    os.remove('gallery_cache.json')
    print("Deleted stale gallery_cache.json")

print("=== REBUILDING CACHE ===")
from app.services import gallery_service
gallery_service.get_gallery(force_reload=True)
print("=== DONE! ===")
