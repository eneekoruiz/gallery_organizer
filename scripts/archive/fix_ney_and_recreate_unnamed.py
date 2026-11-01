import os, cv2, pickle, shutil, json
import numpy as np
from pathlib import Path
from sklearn.cluster import DBSCAN

BASE_DIR = Path(r'C:\Users\User\Desktop\Galeria Eneko NO ABRIR')
CACHE_FILE = Path("sface_cache_v7.pkl")

detector = cv2.FaceDetectorYN.create("models/face_detection_yunet.onnx", "", (320, 320))
recognizer = cv2.FaceRecognizerSF.create("models/face_recognition_sface.onnx", "")

def get_sim(f1, f2):
    v1 = np.squeeze(f1)
    v2 = np.squeeze(f2)
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

# 1. Remove Mascotas from sface_cache_v7.pkl
if CACHE_FILE.exists():
    with open(CACHE_FILE, 'rb') as f:
        known_faces = pickle.load(f)
        
    keys_to_del = [k for k in known_faces.keys() if 'mascota' in k.lower() or 'm. ' in k.lower() or 'ney' in k.lower()]
    for k in keys_to_del:
        del known_faces[k]
        print(f"Removed pet entry from cache: {k}")
        
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(known_faces, f)

yo_centroid = known_faces.get("YO", {}).get("centroid")
yerai_centroid = known_faces.get("C. Yerai Vidal", {}).get("centroid")

# 2. Audit and clean M. Ney files
ney_dirs = [BASE_DIR / 'Resultados' / 'Mascotas' / 'M. Ney', BASE_DIR / 'Fotos' / 'Mascotas' / 'M. Ney']
ney_files = []
for nd in ney_dirs:
    if nd.exists():
        for r, d, fs in os.walk(str(nd)):
            for f in fs:
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    ney_files.append(os.path.join(r, f))

print(f"Auditing {len(ney_files)} files in M. Ney...")
moved_yo = 0
moved_yerai = 0
moved_pn = 0

yo_dir = BASE_DIR / 'Resultados' / 'YO' / 'YO'
yerai_dir = BASE_DIR / 'Resultados' / 'Conocidos' / 'C. Yerai Vidal'
yo_dir.mkdir(parents=True, exist_ok=True)
yerai_dir.mkdir(parents=True, exist_ok=True)

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
                dst_p = yo_dir / src_p.name
                shutil.move(str(src_p), str(dst_p))
                moved_yo += 1
            elif best_target == 'YERAI' and best_score >= 0.58:
                dst_p = yerai_dir / src_p.name
                shutil.move(str(src_p), str(dst_p))
                moved_yerai += 1
    except Exception as e:
        pass

print(f"Cleaned M. Ney: Moved {moved_yo} to YO, {moved_yerai} to Yerai Vidal.")

# 3. Re-create Personas Sin Nombre clusters using DBSCAN
print("Re-clustering unassigned faces to recreate Personas Sin Nombre...")
unassigned_files = []
pn_restore_dir = BASE_DIR / 'Resultados' / 'Personas Sin Nombre' / 'Restauradas'
if pn_restore_dir.exists():
    for r, d, fs in os.walk(str(pn_restore_dir)):
        for f in fs:
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                unassigned_files.append(os.path.join(r, f))

# Also add unassigned files from Dudosos
dudosos_dir = BASE_DIR / 'Resultados' / 'Conocidos' / '_Dudosos'
if dudosos_dir.exists():
    for r, d, fs in os.walk(str(dudosos_dir)):
        for f in fs:
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                unassigned_files.append(os.path.join(r, f))

print(f"Clustering {len(unassigned_files)} unassigned files into Personas Sin Nombre...")

feats = []
valid_paths = []

for idx, p in enumerate(unassigned_files[:1500]): # cluster up to 1500 candidate faces
    try:
        fb = np.fromfile(p, dtype=np.uint8)
        img = cv2.imdecode(fb, cv2.IMREAD_COLOR)
        if img is None: continue
        h, w = img.shape[:2]
        detector.setInputSize((w, h))
        _, faces = detector.detect(img)
        if faces is None: continue
        
        for face in faces:
            crop = recognizer.alignCrop(img, face)
            feat = recognizer.feature(crop)[0]
            feats.append(feat)
            valid_paths.append(p)
            break # 1 main face per photo for clustering
    except:
        pass

if len(feats) > 0:
    X = np.array(feats)
    # Cosine distance matrix
    db = DBSCAN(eps=0.35, min_samples=3, metric='cosine').fit(X)
    labels = db.labels_
    
    unique_labels = set(labels)
    clusters_created = 0
    
    for lbl in unique_labels:
        if lbl == -1: continue # Noise
        cluster_name = f"Persona Nueva #{lbl + 1}"
        target_cluster_dir = BASE_DIR / 'Resultados' / 'Personas Sin Nombre' / cluster_name
        target_cluster_dir.mkdir(parents=True, exist_ok=True)
        
        indices = np.where(labels == lbl)[0]
        for idx in indices:
            src_p = Path(valid_paths[idx])
            if src_p.exists():
                dst_p = target_cluster_dir / src_p.name
                shutil.move(str(src_p), str(dst_p))
        clusters_created += 1
        
    print(f"Created {clusters_created} Personas Sin Nombre clusters!")
