import os
import re
import json
import pickle
import shutil
import cv2
import numpy as np

print("=== STARTING BACKEND FIXES (MAYORAL, ALAIN TELLERIA, AIMAR SÁNCHEZ) ===")

# --- 1. RENAME FOLDER ON DISK FOR MAYORAL ---
conocidos_dir = r'C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados\Conocidos'
src_mayoral = os.path.join(conocidos_dir, 'C  Aitziber Mayoral')
dst_mayoral = os.path.join(conocidos_dir, 'C. Aitziber Mayoral')

if os.path.exists(src_mayoral):
    if os.path.exists(dst_mayoral):
        print(f"Destination {dst_mayoral} already exists! Moving files...")
        for f in os.listdir(src_mayoral):
            s = os.path.join(src_mayoral, f)
            d = os.path.join(dst_mayoral, f)
            if not os.path.exists(d):
                shutil.move(s, d)
        os.rmdir(src_mayoral)
        print("Merged and removed old folder.")
    else:
        os.rename(src_mayoral, dst_mayoral)
        print(f"Renamed folder: {src_mayoral} -> {dst_mayoral}")
else:
    print(f"Folder {src_mayoral} does not exist (already renamed or not found).")

# --- 2. EXTRACT AUTHENTIC VECTORS FOR ALAIN TELLERIA AND AIMAR SÁNCHEZ ---
det = cv2.FaceDetectorYN.create('face_detection_yunet_2023mar.onnx', '', (300, 300), 0.5, 0.3, 5000)
rec = cv2.FaceRecognizerSF.create('face_recognition_sface_2021dec.onnx', '')

def imread_unicode(p):
    with open(p, 'rb') as f:
        buf = f.read()
    arr = np.frombuffer(buf, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)

def get_face_vector(p):
    im = imread_unicode(p)
    if im is None: return None
    h, w = im.shape[:2]
    det.setInputSize((w, h))
    fcs = det.detect(im)[1]
    if fcs is None or len(fcs) == 0: return None
    best = max(fcs, key=lambda f: f[2]*f[3])
    al = rec.alignCrop(im, best)
    ft = rec.feature(al).flatten()
    return ft / np.linalg.norm(ft)

p_alain = os.path.join(dst_mayoral if 'C. Alain Telleria' in dst_mayoral else conocidos_dir, 'C. Alain Telleria', '4E779BC3-C796-4F95-A4F9-23B585CB4B54.jpg')
p_aimar_s = os.path.join(conocidos_dir, 'C. Aimar Sánchez', 'IMG_20200529_202507.jpg')

vec_alain = get_face_vector(p_alain)
vec_aimar_s = get_face_vector(p_aimar_s)

print(f"vec_alain extracted: {vec_alain is not None}")
print(f"vec_aimar_s extracted: {vec_aimar_s is not None}")
if vec_alain is not None and vec_aimar_s is not None:
    print(f"Authentic similarity Alain vs Aimar Sanchez: {float(np.dot(vec_alain, vec_aimar_s)):.4f}")

# --- 3. UPDATE centroids.pkl ---
print("\nUpdating centroids.pkl...")
with open('centroids.pkl', 'rb') as f:
    centroids = pickle.load(f)

# Rename Mayoral keys
if ('Conocidos', 'C  Aitziber Mayoral') in centroids:
    centroids[('Conocidos', 'C. Aitziber Mayoral')] = centroids.pop(('Conocidos', 'C  Aitziber Mayoral'))
if 'C  Aitziber Mayoral' in centroids:
    centroids['C. Aitziber Mayoral'] = centroids.pop('C  Aitziber Mayoral')

# Update Alain Telleria with real vector
if vec_alain is not None:
    centroids[('Conocidos', 'C. Alain Telleria')] = vec_alain
    centroids['C. Alain Telleria'] = vec_alain
    print("Alain Telleria centroid updated to authentic face!")

# Update Aimar Sánchez with real vector
if vec_aimar_s is not None:
    centroids[('Conocidos', 'C. Aimar Sánchez')] = vec_aimar_s
    centroids['C. Aimar Sánchez'] = vec_aimar_s
    centroids[('Conocidos', 'C. Aimar Sanchez')] = vec_aimar_s
    centroids['C. Aimar Sanchez'] = vec_aimar_s
    centroids[('iCloud Photos', 'C. Aimar Sánchez')] = vec_aimar_s
    print("Aimar Sánchez centroid updated to authentic face!")

with open('centroids.pkl', 'wb') as f:
    pickle.dump(centroids, f)
print("centroids.pkl saved.")

# --- 4. UPDATE sface_cache_v7.pkl ---
print("\nUpdating sface_cache_v7.pkl...")
with open('sface_cache_v7.pkl', 'rb') as f:
    sface = pickle.load(f)

# Mayoral rename
if 'C  Aitziber Mayoral' in sface:
    sface['C. Aitziber Mayoral'] = sface.pop('C  Aitziber Mayoral')

# Alain update
if vec_alain is not None and 'C. Alain Telleria' in sface:
    sface['C. Alain Telleria']['centroid'] = vec_alain
    sface['C. Alain Telleria']['centroids'] = [vec_alain]
    sface['C. Alain Telleria']['confirmed_samples'] = {'4E779BC3-C796-4F95-A4F9-23B585CB4B54.jpg': vec_alain}
    sface['C. Alain Telleria']['names'] = ['4E779BC3-C796-4F95-A4F9-23B585CB4B54.jpg']
    sface['C. Alain Telleria']['provenance'] = 'human_confirmed'

# Aimar Sánchez update
if vec_aimar_s is not None and 'C. Aimar Sánchez' in sface:
    sface['C. Aimar Sánchez']['centroid'] = vec_aimar_s
    sface['C. Aimar Sánchez']['centroids'] = [vec_aimar_s]
    sface['C. Aimar Sánchez']['confirmed_samples'] = {'IMG_20200529_202507.jpg': vec_aimar_s}
    sface['C. Aimar Sánchez']['names'] = ['IMG_20200529_202507.jpg']
    sface['C. Aimar Sánchez']['provenance'] = 'human_confirmed'

with open('sface_cache_v7.pkl', 'wb') as f:
    pickle.dump(sface, f)
print("sface_cache_v7.pkl saved.")

# --- 5. AUDIT AND UPDATE apple_db.json ---
print("\nAuditing apple_db.json...")
with open('apple_db.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

mayoral_fixed = 0
alain_fixed = 0
aimar_s_fixed = 0

for photo_path, data in db.items():
    # 5a. Fix Mayoral name variations
    if data.get('identity') == 'C  Aitziber Mayoral':
        data['identity'] = 'C. Aitziber Mayoral'
        mayoral_fixed += 1
    
    faces = data.get('faces', [])
    for fc in faces:
        if fc.get('identity') == 'C  Aitziber Mayoral':
            fc['identity'] = 'C. Aitziber Mayoral'
            mayoral_fixed += 1
        if fc.get('suggested_identity') == 'C  Aitziber Mayoral':
            fc['suggested_identity'] = 'C. Aitziber Mayoral'
            mayoral_fixed += 1
        if fc.get('label') == 'C  Aitziber Mayoral':
            fc['label'] = 'C. Aitziber Mayoral'
            mayoral_fixed += 1

    # 5b. Specific fix for f0b50702-7900-43cd-871e-e8842589d6f4.jpg
    if 'f0b50702-7900-43cd-871e-e8842589d6f4' in photo_path:
        print(f"Correcting f0b50702...")
        # Face 0: C. Martín Sánchez (similarity 0.9455)
        if len(faces) > 0:
            faces[0]['identity'] = 'C. Martín Sánchez'
            faces[0]['category'] = 'Conocidos'
            faces[0]['suggested_identity'] = None
            faces[0]['suggested_score'] = 0.0
            faces[0]['is_manual'] = True
        # Face 1: Unknown boy, NOT Alain Telleria, NOT Aimar Sánchez
        if len(faces) > 1:
            faces[1]['identity'] = 'Desconocido'
            faces[1]['category'] = 'Desconocido'
            faces[1]['suggested_identity'] = None
            faces[1]['suggested_score'] = 0.0
            faces[1]['is_manual'] = False
        # Face 2: C. Kaiet Cubero (similarity 0.9635)
        if len(faces) > 2:
            faces[2]['identity'] = 'C. Kaiet Cubero'
            faces[2]['category'] = 'Conocidos'
            faces[2]['suggested_identity'] = None
            faces[2]['suggested_score'] = 0.0
            faces[2]['is_manual'] = True
        
        data['identity'] = 'C. Martín Sánchez'
        data['category'] = 'Conocidos'
        data['identities'] = ['C. Martín Sánchez', 'Desconocido', 'C. Kaiet Cubero']
        alain_fixed += 1

    # 5c. Audit any faces tagged with Alain Telleria or Aimar Sánchez
    for fc in faces:
        ident = str(fc.get('identity', ''))
        sugg = str(fc.get('suggested_identity', ''))
        feat = fc.get('feature') or fc.get('embedding')
        if feat:
            arr = np.array(feat, dtype=np.float32).flatten()
            norm = np.linalg.norm(arr)
            if norm > 0:
                vec = arr / norm
                
                # Check Alain
                if 'Alain Telleria' in ident or 'Alain Telleria' in sugg:
                    if vec_alain is not None:
                        sim = float(np.dot(vec, vec_alain))
                        if sim < 0.38 and not fc.get('is_manual'):
                            print(f"Reclassifying false Alain face in {os.path.basename(photo_path)} (sim={sim:.4f})")
                            fc['identity'] = 'Desconocido'
                            fc['suggested_identity'] = None
                            fc['suggested_score'] = 0.0
                            alain_fixed += 1
                
                # Check Aimar Sánchez
                if 'Aimar Sánchez' in ident or 'Aimar Sanchez' in ident or 'Aimar Sánchez' in sugg or 'Aimar Sanchez' in sugg:
                    if vec_aimar_s is not None:
                        sim = float(np.dot(vec, vec_aimar_s))
                        if sim < 0.38 and not fc.get('is_manual'):
                            print(f"Reclassifying false Aimar Sánchez face in {os.path.basename(photo_path)} (sim={sim:.4f})")
                            fc['identity'] = 'Desconocido'
                            fc['suggested_identity'] = None
                            fc['suggested_score'] = 0.0
                            aimar_s_fixed += 1

    # Rebuild photo identities array
    clean_idents = []
    for fc in faces:
        iv = fc.get('identity')
        if iv and iv not in clean_idents:
            clean_idents.append(iv)
    data['identities'] = clean_idents

print(f"Mayoral entries unified: {mayoral_fixed}")
print(f"Alain Telleria entries cleaned: {alain_fixed}")
print(f"Aimar Sánchez entries cleaned: {aimar_s_fixed}")

with open('apple_db.json', 'w', encoding='utf-8') as f:
    json.dump(db, f, indent=2, ensure_ascii=False)
print("apple_db.json saved.")

# Invalidate cache file
if os.path.exists('gallery_cache.json'):
    os.remove('gallery_cache.json')
    print("Deleted gallery_cache.json for clean rebuild.")

print("=== BACKEND FIXES COMPLETED SUCCESSFULLY ===")
