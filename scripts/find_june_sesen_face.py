import sys
import pickle
from pathlib import Path
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.globals import detector, recognizer

img_p = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados\Conocidos\C. June Sesen\Fotos June Sesen.jpg")
img = cv2.imread(str(img_p))
detector.setInputSize((img.shape[1], img.shape[0]))
_, faces = detector.detect(img)

candidates = []
for idx, face in enumerate(faces):
    fv = recognizer.feature(recognizer.alignCrop(img, face)).flatten()
    norm = np.linalg.norm(fv)
    if norm > 0:
        candidates.append((idx, fv / norm))

# Test which candidate matches the most photos in C. June Sesen
test_files = [
    Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados\Conocidos\C. June Sesen\020-1.jpg"),
    Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados\Conocidos\C. June Sesen\114.JPG"),
    Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados\Conocidos\C. June Sesen\115.JPG"),
    Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados\Conocidos\C. June Sesen\IMG_0077.jpg")
]

scores = {idx: 0.0 for idx, _ in candidates}

for tf in test_files:
    timg = cv2.imread(str(tf))
    if timg is None: continue
    h, w = timg.shape[:2]
    scale = 1024.0 / max(h, w)
    timg_small = cv2.resize(timg, (int(w*scale), int(h*scale)))
    detector.setInputSize((timg_small.shape[1], timg_small.shape[0]))
    _, tfaces = detector.detect(timg_small)
    if tfaces is None: continue
    
    for tface in tfaces:
        fv = recognizer.feature(recognizer.alignCrop(timg, tface / scale)).flatten()
        norm = np.linalg.norm(fv)
        if norm > 0:
            fn = fv / norm
            for idx, cv_vec in candidates:
                sim = float(np.dot(cv_vec, fn))
                if sim > scores[idx]:
                    scores[idx] = sim

for idx, score in scores.items():
    print(f"Candidate Face {idx} in Fotos June Sesen.jpg max match in June album: {score:.3f}")
