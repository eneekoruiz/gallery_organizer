import os
import sys
import pickle
from pathlib import Path
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.globals import detector, recognizer

# 1. First, find all SOLO photos in YO/YO to calculate the pure gold-standard Eneko centroid
yo_dir = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados\YO\YO")
valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif'}

yo_solo_vectors = []
print("=== CALCULATING PURE GOLD-STANDARD 'YO' CENTROID FROM SOLO PHOTOS ===")

files = [f for f in yo_dir.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]
print(f"Scanning {len(files)} photos in YO/YO...")

for f in files:
    try:
        img = cv2.imread(str(f))
        if img is None: continue
        detector.setInputSize((img.shape[1], img.shape[0]))
        _, faces = detector.detect(img)
        if faces is not None and len(faces) == 1:
            # Exactly ONE face in the photo! Pure solo photo!
            fv = recognizer.feature(recognizer.alignCrop(img, faces[0])).flatten()
            norm = np.linalg.norm(fv)
            if norm > 0:
                yo_solo_vectors.append(fv / norm)
    except Exception:
        pass

print(f"Found {len(yo_solo_vectors)} pure solo photos of Eneko!")
if len(yo_solo_vectors) >= 5:
    # Compute median / normalized mean vector
    mean_vec = np.mean(yo_solo_vectors, axis=0)
    yo_pure_centroid = mean_vec / np.linalg.norm(mean_vec)
    
    # Check consistency: pairwise similarity to centroid
    sims = [float(np.dot(v, yo_pure_centroid)) for v in yo_solo_vectors]
    print(f"Average similarity to pure centroid: {np.mean(sims):.3f} (Min: {np.min(sims):.3f}, Max: {np.max(sims):.3f})")
    
    # Save pure centroid
    with open('yo_pure_centroid.npy', 'wb') as f:
        np.save(f, yo_pure_centroid)
    print("Saved 'yo_pure_centroid.npy' successfully.")
else:
    print("WARNING: Not enough solo photos found.")
