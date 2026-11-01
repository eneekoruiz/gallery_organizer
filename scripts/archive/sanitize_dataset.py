import os
import cv2
import pickle
import numpy as np
import shutil
from pathlib import Path

# Configuración de directorios y modelos
APP_DIR = Path(__file__).resolve().parent
RESULTADOS_DIR = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados")
CACHE_FILE = APP_DIR / "sface_cache_v7.pkl"

MODEL_DIR = APP_DIR / "models"
DETECTOR_PATH = MODEL_DIR / "face_detection_yunet.onnx"
RECOGNIZER_PATH = MODEL_DIR / "face_recognition_sface.onnx"

print("Cargando modelos IA...")
detector = cv2.FaceDetectorYN.create(str(DETECTOR_PATH), "", (320, 320), 0.9, 0.3, 5000)
recognizer = cv2.FaceRecognizerSF.create(str(RECOGNIZER_PATH), "")

print("Cargando memoria limpia...")
known_faces = {}
if CACHE_FILE.exists():
    with open(CACHE_FILE, 'rb') as f:
        known_faces = pickle.load(f)

def get_cosine_similarity(feat1, feat2):
    return np.dot(feat1, feat2) / (np.linalg.norm(feat1) * np.linalg.norm(feat2))

conocidos_dir = RESULTADOS_DIR / "Conocidos"
dudosos_root = conocidos_dir / "_Dudosos"

valid_exts = {".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi"}

total_audited = 0
total_moved = 0

print("Iniciando purga de fantasmas...")
for person_dir in conocidos_dir.iterdir():
    if not person_dir.is_dir() or person_dir.name == "_Dudosos":
        continue
        
    person_name = person_dir.name
    # Buscar su centroide
    person_data = known_faces.get(person_name)
    if not person_data or 'centroid' not in person_data:
        print(f"La persona '{person_name}' no tiene centroide en memoria. Saltando...")
        continue
        
    centroid = person_data['centroid']
    
    for file_path in person_dir.iterdir():
        if not file_path.is_file(): continue
        if file_path.suffix.lower() not in valid_exts: continue
        
        total_audited += 1
        is_video = file_path.suffix.lower() in [".mp4", ".mov", ".avi"]
        
        # Leer media
        img = None
        if is_video:
            cap = cv2.VideoCapture(str(file_path))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            target_frame = frame_count // 2 if frame_count > 10 else 0
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ret, frame = cap.read()
            cap.release()
            if ret: img = frame
        else:
            file_bytes = np.fromfile(str(file_path), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            
        if img is None:
            continue
            
        # Detectar caras
        height, width, _ = img.shape
        detector.setInputSize((width, height))
        _, faces = detector.detect(img)
        
        match_found = False
        if faces is not None:
            for face in faces:
                try:
                    aligned = recognizer.alignCrop(img, face)
                    feature = recognizer.feature(aligned)
                    score = get_cosine_similarity(feature[0], centroid)
                    
                    if score > 0.3:
                        match_found = True
                        break
                except:
                    pass
                    
        # Si ninguna cara coincide, es un fantasma. ¡EXPULSAR!
        if not match_found:
            dudosos_dest = dudosos_root / f"{person_name}_rejected"
            dudosos_dest.mkdir(parents=True, exist_ok=True)
            
            target_path = dudosos_dest / file_path.name
            counter = 1
            while target_path.exists():
                target_path = dudosos_dest / f"{file_path.stem}_{counter}{file_path.suffix}"
                counter += 1
                
            shutil.move(str(file_path), str(target_path))
            print(f"[EXPULSADO] {person_name}/{file_path.name} -> movido a Dudosos.")
            total_moved += 1

print("="*40)
print(f"Purga finalizada.")
print(f"Archivos auditados: {total_audited}")
print(f"Fantasmas expulsados: {total_moved}")
print("="*40)
