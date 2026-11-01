import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

import os, cv2, pickle, json
import numpy as np
from pathlib import Path

BASE_DIR = Path(r'C:\Users\User\Desktop\Galeria Eneko NO ABRIR')
CACHE_FILE = Path("sface_cache_v7.pkl")

print("1. Loading face detection and recognition ONNX models...")
detector = cv2.FaceDetectorYN.create("models/face_detection_yunet.onnx", "", (320, 320))
recognizer = cv2.FaceRecognizerSF.create("models/face_recognition_sface.onnx", "")

def get_sim(f1, f2):
    v1 = np.squeeze(f1)
    v2 = np.squeeze(f2)
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

known_faces = {}
if CACHE_FILE.exists():
    with open(CACHE_FILE, 'rb') as f:
        known_faces = pickle.load(f)

# Exclude pets
known_faces = {k: v for k, v in known_faces.items() if 'mascota' not in k.lower() and 'm. ' not in k.lower()}

print(f"Loaded {len(known_faces)} trusted human face centroids.")

# Collect all files in Familia conmigo & Familia sin mi
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

print(f"Total files in Familia folders to scan: {len(fam_files)}")

faces_cache_file = Path("faces_cache.pkl")
faces_cache = {}
if faces_cache_file.exists():
    with open(faces_cache_file, 'rb') as f:
        faces_cache = pickle.load(f)

scanned_count = 0
faces_found_count = 0

for idx, p in enumerate(fam_files):
    if idx % 25 == 0:
        print(f"Deep scanning photo {idx}/{len(fam_files)}...")
        
    try:
        fb = np.fromfile(p, dtype=np.uint8)
        img = cv2.imdecode(fb, cv2.IMREAD_COLOR)
        if img is None: continue
        h, w = img.shape[:2]
        
        # Multi-scale YuNet detection for deep precision
        all_faces_in_img = []
        for scale in [1.0, 0.75, 0.5]:
            sw = max(64, int(w * scale))
            sh = max(64, int(h * scale))
            detector.setInputSize((sw, sh))
            if scale != 1.0:
                resized_img = cv2.resize(img, (sw, sh))
                _, faces = detector.detect(resized_img)
            else:
                _, faces = detector.detect(img)
                
            if faces is not None:
                for face in faces:
                    # Adjust box back to original coordinates
                    box = [
                        float(face[0] / scale),
                        float(face[1] / scale),
                        float(face[2] / scale),
                        float(face[3] / scale)
                    ]
                    # Check for overlap with existing detected faces
                    is_dup = False
                    for existing in all_faces_in_img:
                        eb = existing['box']
                        if abs(eb[0] - box[0]) < 20 and abs(eb[1] - box[1]) < 20:
                            is_dup = True
                            break
                            
                    if not is_dup:
                        # Extract face crop
                        try:
                            # Use original face box for crop
                            orig_face = face.copy()
                            if scale != 1.0:
                                orig_face[0] /= scale
                                orig_face[1] /= scale
                                orig_face[2] /= scale
                                orig_face[3] /= scale
                                orig_face[4:14] /= scale
                                
                            aligned = recognizer.alignCrop(img, orig_face)
                            feat = recognizer.feature(aligned)[0]
                            
                            best_id = "Desconocido"
                            best_sim = 0.0
                            
                            for db_id, data_dict in known_faces.items():
                                centroid = data_dict.get('centroid')
                                if centroid is not None:
                                    sim = get_sim(feat, centroid)
                                    if sim > best_sim:
                                        best_sim = sim
                                        best_id = db_id
                                        
                            if best_sim >= 0.58:
                                all_faces_in_img.append({
                                    "identity": best_id,
                                    "confidence": float(best_sim),
                                    "box": box,
                                    "x": box[0],
                                    "y": box[1],
                                    "width": box[2],
                                    "height": box[3]
                                })
                        except:
                            pass
                            
        if all_faces_in_img:
            faces_cache[p] = all_faces_in_img
            faces_found_count += len(all_faces_in_img)
            
        scanned_count += 1
    except Exception as e:
        pass

with open(faces_cache_file, 'wb') as f:
    pickle.dump(faces_cache, f)

print(f"🎉 DEEP SCAN COMPLETED: Scanned {scanned_count} files, detected {faces_found_count} faces across Familia folders.")
