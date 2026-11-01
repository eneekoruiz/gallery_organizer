import os, cv2, pickle, shutil, json
import numpy as np
from pathlib import Path

BASE_DIR = Path(r'C:\Users\User\Desktop\Galeria Eneko NO ABRIR')
CACHE_FILE = Path("sface_cache_v7.pkl")

detector = cv2.FaceDetectorYN.create("models/face_detection_yunet.onnx", "", (320, 320))
recognizer = cv2.FaceRecognizerSF.create("models/face_recognition_sface.onnx", "")

def get_sim(f1, f2):
    v1 = np.squeeze(f1)
    v2 = np.squeeze(f2)
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

# 1. Remove Sua & Mascotas from sface_cache_v7.pkl
if CACHE_FILE.exists():
    with open(CACHE_FILE, 'rb') as f:
        known_faces = pickle.load(f)
    for k in list(known_faces.keys()):
        if 'sua' in k.lower() or 'mascota' in k.lower() or 'm. ' in k.lower():
            del known_faces[k]
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(known_faces, f)

uxue_centroid = known_faces.get("F. Uxue", {}).get("centroid")
yo_centroid = known_faces.get("YO", {}).get("centroid")

# 2. Clean M. Sua folder
sua_dirs = [BASE_DIR / 'Resultados' / 'Mascotas' / 'M. Sua', BASE_DIR / 'Fotos' / 'Mascotas' / 'M. Sua']
sua_files = []
for sd in sua_dirs:
    if sd.exists():
        for r, d, fs in os.walk(str(sd)):
            for f in fs:
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    sua_files.append(os.path.join(r, f))

uxue_dir = BASE_DIR / 'Resultados' / 'Familia' / 'F. Uxue'
yo_dir = BASE_DIR / 'Resultados' / 'YO' / 'YO'
uxue_dir.mkdir(parents=True, exist_ok=True)
yo_dir.mkdir(parents=True, exist_ok=True)

moved_uxue = 0
moved_yo = 0

for p in sua_files:
    try:
        fb = np.fromfile(p, dtype=np.uint8)
        img = cv2.imdecode(fb, cv2.IMREAD_COLOR)
        if img is None: continue
        h, w = img.shape[:2]
        detector.setInputSize((w, h))
        _, faces = detector.detect(img)
        
        if faces is not None and len(faces) > 0:
            best_target = None
            best_score = 0
            for face in faces:
                crop = recognizer.alignCrop(img, face)
                feat = recognizer.feature(crop)[0]
                
                if uxue_centroid is not None:
                    s_ux = get_sim(feat, uxue_centroid)
                    if s_ux > best_score:
                        best_score = s_ux
                        best_target = 'UXUE'
                if yo_centroid is not None:
                    s_yo = get_sim(feat, yo_centroid)
                    if s_yo > best_score:
                        best_score = s_yo
                        best_target = 'YO'
                        
            src_p = Path(p)
            if best_target == 'UXUE' and best_score >= 0.55:
                dst_p = uxue_dir / src_p.name
                shutil.move(str(src_p), str(dst_p))
                moved_uxue += 1
            elif best_target == 'YO' and best_score >= 0.55:
                dst_p = yo_dir / src_p.name
                shutil.move(str(src_p), str(dst_p))
                moved_yo += 1
    except:
        pass

print(f"Cleaned M. Sua: Moved {moved_uxue} to F. Uxue, {moved_yo} to YO.")

# 3. Analyze and index all faces in Familia conmigo & Familia sin mi
fam_dirs = [
    BASE_DIR / 'Fotos' / 'Familia' / 'Familia conmigo',
    BASE_DIR / 'Fotos' / 'Familia' / 'Familia sin mí',
    BASE_DIR / 'Resultados' / 'Familia' / 'Familia conmigo',
    BASE_DIR / 'Resultados' / 'Familia' / 'Familia sin mí'
]

fam_files = []
for fd in fam_dirs:
    if fd.exists():
        for r, d, fs in os.walk(str(fd)):
            for f in fs:
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    fam_files.append(os.path.join(r, f))

print(f"Analyzing {len(fam_files)} files in Familia conmigo & Familia sin mí...")

faces_cache_file = Path("faces_cache.pkl")
faces_cache = {}
if faces_cache_file.exists():
    with open(faces_cache_file, 'rb') as f:
        faces_cache = pickle.load(f)

tagged_count = 0
for p in fam_files:
    try:
        fb = np.fromfile(p, dtype=np.uint8)
        img = cv2.imdecode(fb, cv2.IMREAD_COLOR)
        if img is None: continue
        h, w = img.shape[:2]
        detector.setInputSize((w, h))
        _, faces = detector.detect(img)
        if faces is None or len(faces) == 0: continue
        
        detected_entries = []
        for face in faces:
            crop = recognizer.alignCrop(img, face)
            feat = recognizer.feature(crop)[0]
            
            best_id = "Desconocido"
            best_sim = 0
            
            for db_id, data_dict in known_faces.items():
                centroid = data_dict.get('centroid')
                if centroid is not None:
                    sim = get_sim(feat, centroid)
                    if sim > best_sim:
                        best_sim = sim
                        best_id = db_id
                        
            if best_sim >= 0.60:
                detected_entries.append({
                    "identity": best_id,
                    "confidence": float(best_sim),
                    "box": [float(face[0]), float(face[1]), float(face[2]), float(face[3])]
                })
                
        if detected_entries:
            faces_cache[p] = detected_entries
            tagged_count += 1
    except:
        pass

with open(faces_cache_file, 'wb') as f:
    pickle.dump(faces_cache, f)

print(f"Successfully indexed and tagged faces for {tagged_count} photos in Familia folders!")
