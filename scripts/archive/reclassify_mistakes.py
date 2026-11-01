import os
import cv2
import pickle
import numpy as np
import shutil
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
RESULTADOS_DIR = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados")
CACHE_FILE = APP_DIR / "sface_cache_v7.pkl"
MODEL_DIR = APP_DIR / "models"
DETECTOR_PATH = MODEL_DIR / "face_detection_yunet.onnx"
RECOGNIZER_PATH = MODEL_DIR / "face_recognition_sface.onnx"

print("Cargando IA...")
detector = cv2.FaceDetectorYN.create(str(DETECTOR_PATH), "", (320, 320), 0.55, 0.3, 5000)
recognizer = cv2.FaceRecognizerSF.create(str(RECOGNIZER_PATH), "")

with open(CACHE_FILE, 'rb') as f:
    known_faces = pickle.load(f)

def get_cosine_similarity(feat1, feat2):
    return np.dot(feat1, feat2) / (np.linalg.norm(feat1) * np.linalg.norm(feat2))

iraide_dir = RESULTADOS_DIR / "Conocidos" / "C. Iraide Mitxelena"
yo_dir_res = RESULTADOS_DIR / "Conocidos" / "YO"

if not iraide_dir.exists():
    print("No se encontró la carpeta de C. Iraide Mitxelena en Resultados")
    exit(1)

yo_dir_res.mkdir(parents=True, exist_ok=True)

valid_exts = {".jpg", ".jpeg", ".png"}

moved = 0
for file_path in iraide_dir.iterdir():
    if not file_path.is_file() or file_path.suffix.lower() not in valid_exts:
        continue
        
    file_bytes = np.fromfile(str(file_path), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if img is None: continue
    
    height, width, _ = img.shape
    detector.setInputSize((width, height))
    _, faces = detector.detect(img)
    
    is_yo = False
    
    if faces is not None:
        for face in faces:
            try:
                aligned = recognizer.alignCrop(img, face)
                feat = recognizer.feature(aligned)
                
                best_match = None
                best_score = -1
                
                for ident, data in known_faces.items():
                    if 'centroid' in data:
                        score = get_cosine_similarity(feat[0], data['centroid'])
                        if score > best_score:
                            best_score = score
                            best_match = ident
                
                # Si la mejor coincidencia es YO y tiene sentido (>0.25)
                if best_match == "YO" and best_score > 0.25:
                    is_yo = True
                    break
            except:
                pass
                
    if is_yo:
        target = yo_dir_res / file_path.name
        counter = 1
        while target.exists():
            target = yo_dir_res / f"{file_path.stem}_{counter}{file_path.suffix}"
            counter += 1
            
        shutil.move(str(file_path), str(target))
        print(f"Movido a YO: {file_path.name}")
        moved += 1

print(f"Finalizado. {moved} fotos recuperadas y movidas a YO.")
