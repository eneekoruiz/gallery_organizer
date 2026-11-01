import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pickle
import cv2
import numpy as np
from app.globals import detector, recognizer

with open('centroids.pkl', 'rb') as f:
    centroids = pickle.load(f)

sergio_c = centroids.get(('Conocidos', 'C. Sergio Lacasa'))
sergio_norm = sergio_c / np.linalg.norm(sergio_c)

folder = Path(r'C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados\Conocidos\C. Sergio Lacasa')
files = list(folder.iterdir())
print(f"Total files in C. Sergio Lacasa: {len(files)}")

for p in files:
    if not p.is_file(): continue
    b = np.fromfile(str(p), dtype=np.uint8)
    img = cv2.imdecode(b, cv2.IMREAD_COLOR)
    if img is None: continue
    h, w = img.shape[:2]
    detector.setInputSize((w, h))
    _, faces = detector.detect(img)
    best_sim = -1
    if faces is not None:
        for face in faces:
            aligned = recognizer.alignCrop(img, face)
            feat = recognizer.feature(aligned)[0]
            sim = float(np.dot(feat / np.linalg.norm(feat), sergio_norm))
            if sim > best_sim: best_sim = sim
    has_sergio = (best_sim >= 0.50)
    tag = "SI CONTIENE A SERGIO" if has_sergio else "NO CONTIENE A SERGIO"
    print(f"  {p.name}: {len(faces) if faces is not None else 0} caras, best_sim={best_sim:.3f} -> {tag}")
