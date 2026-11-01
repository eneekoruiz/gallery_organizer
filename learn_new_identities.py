import os
import cv2
import pickle
import numpy as np
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
FOTOS_DIR = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Fotos")
CACHE_FILE = APP_DIR / "sface_cache_v7.pkl"
MODEL_DIR = APP_DIR / "models"
DETECTOR_PATH = MODEL_DIR / "face_detection_yunet.onnx"
RECOGNIZER_PATH = MODEL_DIR / "face_recognition_sface.onnx"

print("Cargando IA...")
detector = cv2.FaceDetectorYN.create(str(DETECTOR_PATH), "", (320, 320), 0.9, 0.3, 5000)
recognizer = cv2.FaceRecognizerSF.create(str(RECOGNIZER_PATH), "")

with open(CACHE_FILE, 'rb') as f:
    known_faces = pickle.load(f)

yo_dir = FOTOS_DIR / "Conocidos" / "YO"
if not yo_dir.exists():
    print("La carpeta YO no existe en Fotos/Conocidos")
    exit(1)

if "YO" in known_faces:
    print("YO ya está en la memoria. Recalculando...")

features = []
valid_exts = {".jpg", ".jpeg", ".png"}

for file_path in yo_dir.iterdir():
    if not file_path.is_file() or file_path.suffix.lower() not in valid_exts:
        continue
        
    file_bytes = np.fromfile(str(file_path), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if img is None: continue
    
    height, width, _ = img.shape
    detector.setInputSize((width, height))
    _, faces = detector.detect(img)
    
    if faces is not None and len(faces) > 0:
        # Asumimos que la cara principal es la primera
        try:
            aligned = recognizer.alignCrop(img, faces[0])
            feat = recognizer.feature(aligned)
            features.append(feat[0])
            print(f"Extraída feature de: {file_path.name}")
        except Exception as e:
            print(f"Error con {file_path.name}: {e}")

if features:
    avg_feat = np.mean(features, axis=0)
    avg_feat = avg_feat / np.linalg.norm(avg_feat)
    
    known_faces["YO"] = {'centroid': avg_feat, 'names': [f.name for f in yo_dir.iterdir() if f.suffix.lower() in valid_exts]}
    
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(known_faces, f)
        
    print(f"¡Identidad 'YO' aprendida! {len(features)} caras procesadas.")
else:
    print("No se encontraron caras en la carpeta YO.")
