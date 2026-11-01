import os, cv2, pickle, shutil, json
import numpy as np
from pathlib import Path
from sklearn.cluster import DBSCAN

BASE_DIR = Path(r'C:\Users\User\Desktop\Galeria Eneko NO ABRIR')
CACHE_FILE = Path("sface_cache_v7.pkl")

# 1. Purge Mascotas from cache
if CACHE_FILE.exists():
    with open(CACHE_FILE, 'rb') as f:
        known_faces = pickle.load(f)
    for k in list(known_faces.keys()):
        if 'mascota' in k.lower() or 'm. ' in k.lower() or 'ney' in k.lower():
            del known_faces[k]
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(known_faces, f)

yo_centroid = known_faces.get("YO", {}).get("centroid")
yerai_centroid = known_faces.get("C. Yerai Vidal", {}).get("centroid")

detector = cv2.FaceDetectorYN.create("models/face_detection_yunet.onnx", "", (320, 320))
recognizer = cv2.FaceRecognizerSF.create("models/face_recognition_sface.onnx", "")

def get_sim(f1, f2):
    v1 = np.squeeze(f1)
    v2 = np.squeeze(f2)
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

# 2. Clean M. Ney folder
ney_dirs = [BASE_DIR / 'Resultados' / 'Mascotas' / 'M. Ney', BASE_DIR / 'Fotos' / 'Mascotas' / 'M. Ney']
ney_files = []
for nd in ney_dirs:
    if nd.exists():
        for r, d, fs in os.walk(str(nd)):
            for f in fs:
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    ney_files.append(os.path.join(r, f))

yo_dir = BASE_DIR / 'Resultados' / 'YO' / 'YO'
yerai_dir = BASE_DIR / 'Resultados' / 'Conocidos' / 'C. Yerai Vidal'
yo_dir.mkdir(parents=True, exist_ok=True)
yerai_dir.mkdir(parents=True, exist_ok=True)

moved_yo = 0
moved_yerai = 0

for p in ney_files:
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
                if yo_centroid is not None:
                    s_yo = get_sim(feat, yo_centroid)
                    if s_yo > best_score:
                        best_score = s_yo
                        best_target = 'YO'
                if yerai_centroid is not None:
                    s_ye = get_sim(feat, yerai_centroid)
                    if s_ye > best_score:
                        best_score = s_ye
                        best_target = 'YERAI'
            src_p = Path(p)
            if best_target == 'YO' and best_score >= 0.58:
                shutil.move(str(src_p), str(yo_dir / src_p.name))
                moved_yo += 1
            elif best_target == 'YERAI' and best_score >= 0.58:
                shutil.move(str(src_p), str(yerai_dir / src_p.name))
                moved_yerai += 1
    except:
        pass

print(f"Cleaned M. Ney: {moved_yo} moved to YO, {moved_yerai} moved to Yerai Vidal.")

# 3. Collect unassigned candidate files from _Dudosos and Revision_Interactiva
candidate_files = []
for root, dirs, files in os.walk(str(BASE_DIR)):
    if '_Dudosos' in root or 'Revision_Interactiva' in root or 'Restauradas' in root:
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                candidate_files.append(os.path.join(root, f))

print(f"Scanning {len(candidate_files)} candidate files for Personas Sin Nombre clustering...")

feats = []
valid_paths = []

for idx, p in enumerate(candidate_files[:600]): # fast batch of 600 files
    try:
        fb = np.fromfile(p, dtype=np.uint8)
        img = cv2.imdecode(fb, cv2.IMREAD_COLOR)
        if img is None: continue
        h, w = img.shape[:2]
        detector.setInputSize((w, h))
        _, faces = detector.detect(img)
        if faces is None or len(faces) == 0: continue
        
        for face in faces:
            crop = recognizer.alignCrop(img, face)
            feat = recognizer.feature(crop)[0]
            feats.append(feat)
            valid_paths.append(p)
            break
    except:
        pass

if len(feats) > 0:
    X = np.array(feats)
    db = DBSCAN(eps=0.35, min_samples=3, metric='cosine').fit(X)
    labels = db.labels_
    
    unique_labels = set(labels)
    created = 0
    
    for lbl in unique_labels:
        if lbl == -1: continue
        cluster_name = f"Persona Nueva #{lbl + 1}"
        target_cluster_dir = BASE_DIR / 'Resultados' / 'Personas Sin Nombre' / cluster_name
        target_cluster_dir.mkdir(parents=True, exist_ok=True)
        
        indices = np.where(labels == lbl)[0]
        for idx in indices:
            src_p = Path(valid_paths[idx])
            if src_p.exists():
                dst_p = target_cluster_dir / src_p.name
                shutil.move(str(src_p), str(dst_p))
        created += 1
        
    print(f"🎉 Created {created} Personas Sin Nombre clusters!")
