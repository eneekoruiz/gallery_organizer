import sys, os, cv2, pickle, shutil
import numpy as np
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

BASE_DIR = Path(r'C:\Users\User\Desktop\Galeria Eneko NO ABRIR')
CACHE_FILE = Path("sface_cache_v7.pkl")

print("1. Loading YuNet and SFace models...")
detector = cv2.FaceDetectorYN.create("models/face_detection_yunet.onnx", "", (320, 320))
recognizer = cv2.FaceRecognizerSF.create("models/face_recognition_sface.onnx", "")

def get_sim(f1, f2):
    v1 = np.squeeze(f1)
    v2 = np.squeeze(f2)
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

# 2. Re-train centroids from all confirmed photos
print("2. Re-training human face centroids from confirmed photos...")
confirmed_features = {}

for bdir in [BASE_DIR / 'Fotos', BASE_DIR / 'Resultados']:
    if bdir.exists():
        for root, dirs, files in os.walk(str(bdir)):
            if '_dudosos' in root.lower() or 'revision_interactiva' in root.lower() or 'mascotas' in root.lower():
                continue
            rel = os.path.relpath(root, str(bdir))
            parts = rel.split(os.sep)
            if len(parts) >= 2:
                cat = parts[0]
                ident = parts[1]
                if cat in ['Desconocidos', 'Sin_Clasificar', 'Ignorar']: continue
                
                valid_fs = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                for f in valid_fs[:15]: # sample up to 15 images per person
                    p = os.path.join(root, f)
                    try:
                        fb = np.fromfile(p, dtype=np.uint8)
                        img = cv2.imdecode(fb, cv2.IMREAD_COLOR)
                        if img is None: continue
                        h, w = img.shape[:2]
                        detector.setInputSize((w, h))
                        _, faces = detector.detect(img)
                        if faces is not None and len(faces) > 0:
                            crop = recognizer.alignCrop(img, faces[0])
                            feat = recognizer.feature(crop)[0]
                            if ident not in confirmed_features:
                                confirmed_features[ident] = {"cat": cat, "feats": []}
                            confirmed_features[ident]["feats"].append(feat)
                    except:
                        pass

trained_centroids = {}
for ident, data in confirmed_features.items():
    if len(data["feats"]) > 0:
        c = np.mean(data["feats"], axis=0)
        c = c / np.linalg.norm(c)
        trained_centroids[ident] = {"cat": data["cat"], "centroid": c}

print(f"Re-trained centroids for {len(trained_centroids)} confirmed people.")

# Save updated sface_cache_v7.pkl
with open(CACHE_FILE, 'wb') as f:
    pickle.dump(trained_centroids, f)

# 3. Scan all photos in _Dudosos and Revision_Interactiva
print("3. Scanning doubtful/pending photos for high-precision classification...")
dudosos_files = []
for bdir in [BASE_DIR / 'Fotos', BASE_DIR / 'Resultados']:
    if bdir.exists():
        for root, dirs, files in os.walk(str(bdir)):
            if '_dudosos' in root.lower() or 'revision_interactiva' in root.lower():
                for f in files:
                    if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                        dudosos_files.append(os.path.join(root, f))

print(f"Total doubtful photos to evaluate: {len(dudosos_files)}")

promoted_count = 0

for idx, p in enumerate(dudosos_files):
    if idx % 100 == 0:
        print(f"Evaluated {idx}/{len(dudosos_files)} doubtful photos...")
        
    try:
        fb = np.fromfile(p, dtype=np.uint8)
        img = cv2.imdecode(fb, cv2.IMREAD_COLOR)
        if img is None: continue
        h, w = img.shape[:2]
        detector.setInputSize((w, h))
        _, faces = detector.detect(img)
        if faces is None or len(faces) == 0: continue
        
        # Rank top matching identities
        for face in faces:
            crop = recognizer.alignCrop(img, face)
            feat = recognizer.feature(crop)[0]
            
            sims = []
            for db_id, data_dict in trained_centroids.items():
                c = data_dict.get('centroid')
                cat = data_dict.get('cat')
                if c is not None:
                    s = get_sim(feat, c)
                    sims.append((s, db_id, cat))
                    
            sims.sort(key=lambda x: x[0], reverse=True)
            
            # High-precision safety rule:
            # 1. Best match similarity must be >= 0.65
            # 2. Margin between 1st and 2nd best match must be >= 0.07 to prevent confusion
            if len(sims) >= 1:
                best_sim, best_id, best_cat = sims[0]
                second_sim = sims[1][0] if len(sims) > 1 else 0.0
                
                if best_sim >= 0.65 and (best_sim - second_sim) >= 0.07:
                    # Safe to promote! Move file to Resultados/best_cat/best_id
                    src_p = Path(p)
                    target_dir = BASE_DIR / 'Resultados' / best_cat / best_id
                    target_dir.mkdir(parents=True, exist_ok=True)
                    dst_p = target_dir / src_p.name
                    counter = 1
                    while dst_p.exists():
                        dst_p = target_dir / f"{src_p.stem}_{counter}{src_p.suffix}"
                        counter += 1
                    shutil.move(str(src_p), str(dst_p))
                    promoted_count += 1
                    break
    except Exception as e:
        pass

print(f"🎉 HIGH-PRECISION DEEP CLASSIFICATION COMPLETE:")
print(f" - Safely promoted {promoted_count} doubtful photos to confirmed albums!")
