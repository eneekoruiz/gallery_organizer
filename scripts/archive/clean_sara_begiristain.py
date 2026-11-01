import os, shutil, json, pickle, sys
import numpy as np
import cv2
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# Paths
BASE_DIR = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR")
SARA_DIR = BASE_DIR / "Resultados" / "Conocidos" / "C. Sara Begiristain"
YO_DIR = BASE_DIR / "Resultados" / "YO" / "YO"

if not YO_DIR.exists():
    YO_DIR.mkdir(parents=True, exist_ok=True)

# OpenCV models
yunet_path = "models/face_detection_yunet_2023mar.onnx"
sface_path = "models/face_recognition_sface_2021dec.onnx"

detector = cv2.FaceDetectorYN.create(yunet_path, "", (320, 320))
recognizer = cv2.FaceRecognizerSF.create(sface_path, "")

print("--- CLEANING C. SARA BEGIRISTAIN ---")

moved_count = 0
for file_path in list(SARA_DIR.glob("*.*")):
    # Move Screenshot_2020-04-23 directly as indicated by user prompt and screenshot
    if "Screenshot_2020-04-23" in file_path.name:
        dest_path = YO_DIR / file_path.name
        if dest_path.exists():
            dest_path = YO_DIR / f"moved_{file_path.name}"
        shutil.move(str(file_path), str(dest_path))
        print(f"✓ Moved screenshot photo to YO: {file_path.name}")
        moved_count += 1

print(f"Total photos moved to YO: {moved_count}")

# Retrain Sara Begiristain centroid from remaining photos
sara_feats = []
for file_path in SARA_DIR.glob("*.*"):
    img = cv2.imread(str(file_path))
    if img is None: continue
    h, w = img.shape[:2]
    detector.setInputSize((w, h))
    _, faces = detector.detect(img)
    if faces is not None and len(faces) > 0:
        aligned = recognizer.alignCrop(img, faces[0])
        feat = recognizer.feature(aligned)
        sara_feats.append(feat)

if sara_feats:
    avg_feat = np.mean(sara_feats, axis=0)
    avg_feat = avg_feat / np.linalg.norm(avg_feat)
    
    centroids = {}
    try:
        with open('centroids.pkl', 'rb') as f:
            centroids = pickle.load(f)
    except:
        pass
    
    centroids[('Conocidos', 'C. Sara Begiristain')] = avg_feat
    with open('centroids.pkl', 'wb') as f:
        pickle.dump(centroids, f)
    print("✓ Retrained centroid for C. Sara Begiristain!")

print("Done cleaning C. Sara Begiristain.")
