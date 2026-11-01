import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

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

# 1. Move teacher files (Amaia Iurrebaso) to Profesores/P. Amaia Iurrebaso
teacher_dir = BASE_DIR / 'Resultados' / 'Profesores' / 'P. Amaia Iurrebaso'
teacher_dir.mkdir(parents=True, exist_ok=True)

amaia_dirs = [BASE_DIR / 'Fotos' / 'Familia' / 'F. Amaia', BASE_DIR / 'Resultados' / 'Familia' / 'F. Amaia']

moved_teacher_count = 0
for ad in amaia_dirs:
    if ad.exists():
        for r, d, fs in os.walk(str(ad)):
            for f in fs:
                if 'iurrebaso' in f.lower():
                    src_p = Path(r) / f
                    dst_p = teacher_dir / f
                    try:
                        shutil.move(str(src_p), str(dst_p))
                        moved_teacher_count += 1
                        print(f"Moved teacher file: {f} -> P. Amaia Iurrebaso")
                    except Exception as e:
                        print(f"Error moving teacher file {f}: {e}")

# 2. Extract true face embedding for F. Amaia from DPSCamera_0010.JPG and Amaia.jpg
known_faces = {}
if CACHE_FILE.exists():
    with open(CACHE_FILE, 'rb') as f:
        known_faces = pickle.load(f)

yo_centroid = known_faces.get("YO", {}).get("centroid")

amaia_true_feats = []

# Check DPSCamera_0010.JPG and Amaia.jpg
for ad in amaia_dirs:
    if ad.exists():
        for f_name in ['DPSCamera_0010.JPG', 'Amaia.jpg', 'dpscamera_0010.jpg', 'amaia.jpg']:
            p = ad / f_name
            if p.exists():
                try:
                    fb = np.fromfile(str(p), dtype=np.uint8)
                    img = cv2.imdecode(fb, cv2.IMREAD_COLOR)
                    if img is None: continue
                    h, w = img.shape[:2]
                    detector.setInputSize((w, h))
                    _, faces = detector.detect(img)
                    if faces is None: continue
                    
                    for face in faces:
                        crop = recognizer.alignCrop(img, face)
                        feat = recognizer.feature(crop)[0]
                        # Exclude user's face if yo_centroid is available
                        if yo_centroid is not None:
                            sim_yo = get_sim(feat, yo_centroid)
                            if sim_yo >= 0.58:
                                print(f"Excluded YO's face in {f_name} (sim_yo = {sim_yo:.3f})")
                                continue
                        amaia_true_feats.append(feat)
                        print(f"Added true Amaia feature from {f_name}")
                except Exception as e:
                    print(f"Error reading {p}: {e}")

if len(amaia_true_feats) > 0:
    amaia_centroid = np.mean(amaia_true_feats, axis=0)
    amaia_centroid = amaia_centroid / np.linalg.norm(amaia_centroid)
    known_faces["F. Amaia"] = {"centroid": amaia_centroid}
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(known_faces, f)
    print("Updated F. Amaia's true centroid in sface_cache_v7.pkl!")
else:
    print("WARNING: Could not extract true features for F. Amaia!")
    amaia_centroid = None

# 3. Clean up F. Amaia folder by re-evaluating all files
amaia_files = []
for ad in amaia_dirs:
    if ad.exists():
        for r, d, fs in os.walk(str(ad)):
            for f in fs:
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi')):
                    amaia_files.append(os.path.join(r, f))

print(f"Re-evaluating {len(amaia_files)} files in F. Amaia...")

yo_target_dir = BASE_DIR / 'Resultados' / 'YO' / 'YO'
yo_target_dir.mkdir(parents=True, exist_ok=True)

moved_to_yo = 0
kept_in_amaia = 0

for p in amaia_files:
    # Skip reference files
    p_name_lower = Path(p).name.lower()
    if p_name_lower in ['dpscamera_0010.jpg', 'amaia.jpg']:
        kept_in_amaia += 1
        continue
        
    try:
        fb = np.fromfile(p, dtype=np.uint8)
        img = cv2.imdecode(fb, cv2.IMREAD_COLOR)
        if img is None: continue
        h, w = img.shape[:2]
        detector.setInputSize((w, h))
        _, faces = detector.detect(img)
        
        if faces is None or len(faces) == 0:
            continue
            
        has_amaia_face = False
        has_yo_face = False
        
        for face in faces:
            crop = recognizer.alignCrop(img, face)
            feat = recognizer.feature(crop)[0]
            
            if amaia_centroid is not None:
                sim_am = get_sim(feat, amaia_centroid)
                if sim_am >= 0.60:
                    has_amaia_face = True
                    
            if yo_centroid is not None:
                sim_yo = get_sim(feat, yo_centroid)
                if sim_yo >= 0.60:
                    has_yo_face = True
                    
        src_p = Path(p)
        if has_yo_face and not has_amaia_face:
            # File belongs to YO! Move to Resultados/YO/YO
            dst_p = yo_target_dir / src_p.name
            counter = 1
            while dst_p.exists():
                dst_p = yo_target_dir / f"{src_p.stem}_{counter}{src_p.suffix}"
                counter += 1
            shutil.move(str(src_p), str(dst_p))
            moved_to_yo += 1
        elif has_amaia_face:
            kept_in_amaia += 1
    except Exception as e:
        pass

print(f"🎉 SURGICAL CORRECTION FINISHED:")
print(f" - Moved {moved_teacher_count} teacher files to P. Amaia Iurrebaso.")
print(f" - Moved {moved_to_yo} user photos from F. Amaia to YO.")
print(f" - Kept {kept_in_amaia} genuine photos in F. Amaia.")
