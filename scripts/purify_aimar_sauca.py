import cv2
import os
import json
import pickle
import shutil
import numpy as np

print("=== STARTING AIMAR SAUCA PURIFICATION ===")

# 1. Load detector and recognizer
detector_path = 'face_detection_yunet_2023mar.onnx'
recognizer_path = 'face_recognition_sface_2021dec.onnx'

img_path = r'C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados\Conocidos\C. Aimar Sauca\1733665109461.jpg'
img = cv2.imread(img_path)
h, w = img.shape[:2]

detector = cv2.FaceDetectorYN.create(detector_path, '', (w, h), 0.5, 0.3, 5000)
recognizer = cv2.FaceRecognizerSF.create(recognizer_path, '')

faces = detector.detect(img)[1]
print(f"Detected {len(faces)} faces in 1733665109461.jpg")

# Find the yawning boy (box closest to x=768, y=2358)
target_face = None
min_dist = float('inf')
for f in faces:
    x, y, bw, bh = f[:4]
    dist = (x - 768)**2 + (y - 2358)**2
    if dist < min_dist:
        min_dist = dist
        target_face = f

print(f"Target face selected: box={target_face[:4].astype(int)}, conf={target_face[14]:.3f}")

aligned = recognizer.alignCrop(img, target_face)
feat = recognizer.feature(aligned).flatten()
real_aimar_vector = feat / np.linalg.norm(feat)
print("Real Aimar Sauca vector computed! Norm:", np.linalg.norm(real_aimar_vector))

# 2. Update centroids.pkl
print("\nUpdating centroids.pkl...")
with open('centroids.pkl', 'rb') as f:
    centroids = pickle.load(f)

centroids[('Conocidos', 'C. Aimar Sauca')] = real_aimar_vector
centroids['C. Aimar Sauca'] = real_aimar_vector

with open('centroids.pkl', 'wb') as f:
    pickle.dump(centroids, f)
print("centroids.pkl updated successfully.")

# 3. Update sface_cache_v7.pkl
print("\nUpdating sface_cache_v7.pkl...")
with open('sface_cache_v7.pkl', 'rb') as f:
    sface = pickle.load(f)

if 'C. Aimar Sauca' in sface:
    sface['C. Aimar Sauca']['centroid'] = real_aimar_vector
    sface['C. Aimar Sauca']['centroids'] = [real_aimar_vector]
    sface['C. Aimar Sauca']['confirmed_samples'] = {
        '1733665109461.jpg:768,2358,191,239': real_aimar_vector
    }
    sface['C. Aimar Sauca']['names'] = ['1733665109461.jpg:768,2358,191,239']
    sface['C. Aimar Sauca']['provenance'] = 'human_confirmed'

with open('sface_cache_v7.pkl', 'wb') as f:
    pickle.dump(sface, f)
print("sface_cache_v7.pkl updated successfully.")

# 4. Clean manual_overrides.json
print("\nCleaning manual_overrides.json...")
with open('manual_overrides.json', 'r', encoding='utf-8') as f:
    overrides = json.load(f)

to_del = [k for k in overrides.keys() if '!00_CARA_CENTROIDE' in k]
for k in to_del:
    print(f"Deleting bad centroid override: {k}")
    del overrides[k]

with open('manual_overrides.json', 'w', encoding='utf-8') as f:
    json.dump(overrides, f, indent=2, ensure_ascii=False)

# 5. Check other files in Aimar Sauca's folder
print("\nChecking items in C. Aimar Sauca folder...")
folder = r'C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados\Conocidos\C. Aimar Sauca'
review_folder = r'C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados\Revisión\Por Organizar'
os.makedirs(review_folder, exist_ok=True)

# Remove empty subfolder if present
empty_sub = os.path.join(folder, 'C. Aimar Sauca')
if os.path.isdir(empty_sub) and len(os.listdir(empty_sub)) == 0:
    os.rmdir(empty_sub)
    print("Removed empty nested directory:", empty_sub)

# Check 77865e78-3a51-468e-b537-3c427946a996.jpg
photo_77865 = os.path.join(folder, '77865e78-3a51-468e-b537-3c427946a996.jpg')
if os.path.exists(photo_77865):
    im_77865 = cv2.imread(photo_77865)
    if im_77865 is not None:
        h2, w2 = im_77865.shape[:2]
        det2 = cv2.FaceDetectorYN.create(detector_path, '', (w2, h2), 0.5, 0.3, 5000)
        fcs2 = det2.detect(im_77865)[1]
        has_real_aimar = False
        max_sim = 0.0
        if fcs2 is not None:
            for fc in fcs2:
                al = recognizer.alignCrop(im_77865, fc)
                ft = recognizer.feature(al).flatten()
                ft = ft / np.linalg.norm(ft)
                sim = float(np.dot(ft, real_aimar_vector))
                if sim > max_sim:
                    max_sim = sim
                if sim >= 0.38:
                    has_real_aimar = True
        print(f"77865e78-3a51-468e-b537-3c427946a996.jpg: max_sim to real Aimar={max_sim:.4f}, has_aimar={has_real_aimar}")
        if not has_real_aimar:
            dest = os.path.join(review_folder, '77865e78-3a51-468e-b537-3c427946a996.jpg')
            shutil.move(photo_77865, dest)
            print(f"MOVED false positive {photo_77865} -> {dest}")

# Check IMG_4246(1).JPEG
img_4246 = os.path.join(folder, 'IMG_4246(1).JPEG')
if os.path.exists(img_4246):
    im_4246 = cv2.imread(img_4246)
    if im_4246 is not None:
        h3, w3 = im_4246.shape[:2]
        det3 = cv2.FaceDetectorYN.create(detector_path, '', (w3, h3), 0.5, 0.3, 5000)
        fcs3 = det3.detect(im_4246)[1]
        has_aimar = False
        max_sim = 0.0
        if fcs3 is not None:
            for fc in fcs3:
                al = recognizer.alignCrop(im_4246, fc)
                ft = recognizer.feature(al).flatten()
                ft = ft / np.linalg.norm(ft)
                sim = float(np.dot(ft, real_aimar_vector))
                if sim > max_sim:
                    max_sim = sim
                if sim >= 0.38:
                    has_aimar = True
        print(f"IMG_4246(1).JPEG: max_sim to real Aimar={max_sim:.4f}, has_aimar={has_aimar}")

# 6. Audit apple_db.json
print("\nAuditing apple_db.json for false C. Aimar Sauca tags...")
with open('apple_db.json', 'r', encoding='utf-8') as f:
    apple_db = json.load(f)

reassigned = 0
for file_key, data in apple_db.items():
    faces_list = data.get('faces', [])
    modified = False
    for fc in faces_list:
        lbl = fc.get('label', '')
        if 'Aimar Sauca' in lbl:
            emb = fc.get('embedding')
            if emb:
                emb_arr = np.array(emb, dtype=np.float32).flatten()
                norm = np.linalg.norm(emb_arr)
                if norm > 0:
                    emb_arr = emb_arr / norm
                    sim = float(np.dot(emb_arr, real_aimar_vector))
                    if sim < 0.38:
                        print(f"Reassigning false face in {file_key}: sim was only {sim:.4f}")
                        fc['label'] = 'Desconocido'
                        fc['category'] = 'Desconocido'
                        fc['confidence'] = 0.0
                        modified = True
                        reassigned += 1
            else:
                # If no embedding, check if manual
                if not fc.get('is_manual'):
                    fc['label'] = 'Desconocido'
                    fc['category'] = 'Desconocido'
                    modified = True
                    reassigned += 1

print(f"Total misassigned faces reclassified in apple_db: {reassigned}")
with open('apple_db.json', 'w', encoding='utf-8') as f:
    json.dump(apple_db, f, indent=2, ensure_ascii=False)

# 7. Invalidate gallery cache
if os.path.exists('gallery_cache.json'):
    os.remove('gallery_cache.json')
    print("Invalidated gallery_cache.json")

print("=== PURIFICATION COMPLETE ===")
