import sys
import pickle
from pathlib import Path
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.globals import detector, recognizer

with open('centroids.pkl', 'rb') as f:
    centroids = pickle.load(f)

yo_norm = centroids[('YO', 'YO')]
yo_norm = yo_norm / np.linalg.norm(yo_norm)

june_norm = centroids.get(('Conocidos', 'C. June Sesen'))
if june_norm is not None:
    june_norm = june_norm / np.linalg.norm(june_norm)

june_dir = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados\Conocidos\C. June Sesen")

print(f"=== CHECKING JUNE SESEN FILES ===")
files = sorted([f for f in june_dir.iterdir() if f.is_file()])

for f in files:
    try:
        img = cv2.imread(str(f))
        if img is None: continue
        # Downscale for fast detection if large
        h, w = img.shape[:2]
        scale = 1.0
        if max(h, w) > 1280:
            scale = 1280.0 / max(h, w)
            img_small = cv2.resize(img, (int(w * scale), int(h * scale)))
        else:
            img_small = img
            
        detector.setInputSize((img_small.shape[1], img_small.shape[0]))
        _, faces = detector.detect(img_small)
        if faces is None or len(faces) == 0:
            continue
            
        for face in faces:
            # Rescale face bbox back to original image
            if scale != 1.0:
                face = face / scale
            fv = recognizer.feature(recognizer.alignCrop(img, face)).flatten()
            norm = np.linalg.norm(fv)
            if norm > 0:
                fv_norm = fv / norm
                s_yo = float(np.dot(fv_norm, yo_norm))
                s_june = float(np.dot(fv_norm, june_norm)) if june_norm is not None else 0
                if s_yo >= 0.45 or s_june >= 0.45:
                    print(f"  {f.name[:30]:30} | sim_yo={s_yo:.3f} | sim_june={s_june:.3f} | faces={len(faces)}", flush=True)
    except Exception as e:
        pass
