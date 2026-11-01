import os
import sys
import pickle
from pathlib import Path
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.globals import detector, recognizer

with open('centroids.pkl', 'rb') as f:
    centroids = pickle.load(f)

yo_vec = np.array(centroids[('YO', 'YO')]).flatten()
yo_norm = yo_vec / np.linalg.norm(yo_vec)

june_vec = np.array(centroids[('Conocidos', 'C. June Sesen')]).flatten()
june_norm = june_vec / np.linalg.norm(june_vec)

june_dir = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados\Conocidos\C. June Sesen")

print("=== ANALYZING ALL PHOTOS IN C. JUNE SESEN ===")
files = sorted([f for f in june_dir.iterdir() if f.is_file()])

for f in files:
    try:
        img = cv2.imread(str(f))
        if img is None:
            print(f"{f.name:30} | Could not read image")
            continue
        detector.setInputSize((img.shape[1], img.shape[0]))
        _, faces = detector.detect(img)
        if faces is None or len(faces) == 0:
            print(f"{f.name:30} | 0 faces detected")
            continue
            
        face_sims = []
        for face in faces:
            fv = recognizer.feature(recognizer.alignCrop(img, face)).flatten()
            norm = np.linalg.norm(fv)
            if norm > 0:
                fv_norm = fv / norm
                s_yo = float(np.dot(fv_norm, yo_norm))
                s_june = float(np.dot(fv_norm, june_norm))
                face_sims.append((s_yo, s_june))
                
        # Report
        yo_matches = [s for s in face_sims if s[0] >= 0.45]
        june_matches = [s for s in face_sims if s[1] >= 0.45]
        
        sim_summary = ", ".join([f"(yo:{s[0]:.2f}, june:{s[1]:.2f})" for s in face_sims])
        print(f"{f.name[:35]:35} | Faces: {len(faces)} | {sim_summary}")
    except Exception as e:
        print(f"{f.name:30} | Error: {e}")
