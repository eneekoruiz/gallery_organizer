import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

import os, cv2, pickle, shutil
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

amaia_dirs = [BASE_DIR / 'Fotos' / 'Familia' / 'F. Amaia', BASE_DIR / 'Resultados' / 'Familia' / 'F. Amaia']

print("1. Extracting EXCLUSIVELY Amaia's face features...")
amaia_real_feats = []

# A. From DPSCamera_0010.JPG (Amaia alone with sunglasses)
for ad in amaia_dirs:
    for fname in ['DPSCamera_0010.JPG', 'dpscamera_0010.jpg']:
        p = ad / fname
        if p.exists():
            fb = np.fromfile(str(p), dtype=np.uint8)
            img = cv2.imdecode(fb, cv2.IMREAD_COLOR)
            if img is not None:
                h, w = img.shape[:2]
                detector.setInputSize((w, h))
                _, faces = detector.detect(img)
                if faces is not None and len(faces) > 0:
                    crop = recognizer.alignCrop(img, faces[0])
                    feat = recognizer.feature(crop)[0]
                    amaia_real_feats.append(feat)
                    print(f"Extracted Amaia solo feature from {fname}")

# B. From Amaia.jpg (LEFT face ONLY! x < w * 0.4)
for ad in amaia_dirs:
    for fname in ['Amaia.jpg', 'amaia.jpg']:
        p = ad / fname
        if p.exists():
            fb = np.fromfile(str(p), dtype=np.uint8)
            img = cv2.imdecode(fb, cv2.IMREAD_COLOR)
            if img is not None:
                h, w = img.shape[:2]
                detector.setInputSize((w, h))
                _, faces = detector.detect(img)
                if faces is not None:
                    for face in faces:
                        # Amaia is on the left side of the image (x < w * 0.45)
                        if face[0] < (w * 0.45):
                            crop = recognizer.alignCrop(img, face)
                            feat = recognizer.feature(crop)[0]
                            amaia_real_feats.append(feat)
                            print(f"Extracted Amaia left face feature from {fname}")

if not amaia_real_feats:
    print("Error: Could not extract real features for Amaia!")
    sys.exit(1)

amaia_clean_centroid = np.mean(amaia_real_feats, axis=0)
amaia_clean_centroid = amaia_clean_centroid / np.linalg.norm(amaia_clean_centroid)

# Update sface_cache_v7.pkl
known_faces = {}
if CACHE_FILE.exists():
    with open(CACHE_FILE, 'rb') as f:
        known_faces = pickle.load(f)

known_faces["F. Amaia"] = {"centroid": amaia_clean_centroid}
with open(CACHE_FILE, 'wb') as f:
    pickle.dump(known_faces, f)

print("Updated sface_cache_v7.pkl with 100% clean Amaia centroid!")

# 2. Audit and clean ALL files in F. Amaia
yo_target_dir = BASE_DIR / 'Resultados' / 'YO' / 'YO'
yo_target_dir.mkdir(parents=True, exist_ok=True)

amaia_files = []
for ad in amaia_dirs:
    if ad.exists():
        for r, d, fs in os.walk(str(ad)):
            for f in fs:
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi')):
                    amaia_files.append(os.path.join(r, f))

moved_to_yo = 0
kept_in_amaia = 0

for p in amaia_files:
    fname_lower = Path(p).name.lower()
    if fname_lower in ['dpscamera_0010.jpg', 'amaia.jpg']:
        kept_in_amaia += 1
        continue
        
    try:
        fb = np.fromfile(p, dtype=np.uint8)
        img = cv2.imdecode(fb, cv2.IMREAD_COLOR)
        if img is None: continue
        h, w = img.shape[:2]
        detector.setInputSize((w, h))
        _, faces = detector.detect(img)
        
        has_real_amaia = False
        if faces is not None and len(faces) > 0:
            for face in faces:
                crop = recognizer.alignCrop(img, face)
                feat = recognizer.feature(crop)[0]
                sim_am = get_sim(feat, amaia_clean_centroid)
                if sim_am >= 0.62:
                    has_real_amaia = True
                    break
                    
        src_p = Path(p)
        if not has_real_amaia:
            # Move out of F. Amaia to YO (or remove from folder)
            dst_p = yo_target_dir / src_p.name
            counter = 1
            while dst_p.exists():
                dst_p = yo_target_dir / f"{src_p.stem}_{counter}{src_p.suffix}"
                counter += 1
            shutil.move(str(src_p), str(dst_p))
            moved_to_yo += 1
        else:
            kept_in_amaia += 1
    except Exception as e:
        pass

print(f"🎉 CLEANUP COMPLETE:")
print(f" - Moved {moved_to_yo} Carnival/makeup photos OUT of F. Amaia to YO.")
print(f" - Kept {kept_in_amaia} genuine photos in F. Amaia.")
