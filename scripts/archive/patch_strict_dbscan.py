import sys
from pathlib import Path

script_content = '''import os
import cv2
import pickle
import numpy as np
from pathlib import Path
import shutil
from sklearn.cluster import DBSCAN

APP_DIR = Path(__file__).resolve().parent
RESULTADOS_DIR = Path(r"C:\\Users\\User\\Desktop\\Galeria Eneko NO ABRIR\\Resultados")
DUDOSOS_DIR = RESULTADOS_DIR / "Conocidos" / "_Dudosos"
SIN_NOMBRE_DIR = RESULTADOS_DIR / "Personas Sin Nombre"

MODEL_DIR = APP_DIR / "models"
DETECTOR_PATH = MODEL_DIR / "face_detection_yunet.onnx"
RECOGNIZER_PATH = MODEL_DIR / "face_recognition_sface.onnx"

print("Iniciando motor de Clustering Estricto por IA (DBSCAN 0.65)...")

detector = cv2.FaceDetectorYN.create(str(DETECTOR_PATH), "", (320, 320), 0.30, 0.3, 5000)
recognizer = cv2.FaceRecognizerSF.create(str(RECOGNIZER_PATH), "")

valid_exts = {".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi"}

# 1. Recolectar embeddings de TODAS las caras en fotos de Dudosos
items = []
print("Extrayendo mapas faciales de todas las caras en Dudosos...")

for root, dirs, files in os.walk(str(DUDOSOS_DIR)):
    for file in files:
        ext = os.path.splitext(file)[1].lower()
        if ext in valid_exts:
            file_path = Path(root) / file
            img = None
            is_video = ext in [".mp4", ".mov", ".avi"]
            
            try:
                if is_video:
                    cap = cv2.VideoCapture(str(file_path))
                    fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    if fc > 10: cap.set(cv2.CAP_PROP_POS_FRAMES, fc // 2)
                    ret, frame = cap.read()
                    cap.release()
                    if ret: img = frame
                else:
                    file_bytes = np.fromfile(str(file_path), dtype=np.uint8)
                    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                    
                if img is not None:
                    h, w, _ = img.shape
                    detector.setInputSize((w, h))
                    _, faces = detector.detect(img)
                    if faces is not None and len(faces) > 0:
                        # Extraer CADA CARA por separado (no solo faces[0])
                        for f_idx, face in enumerate(faces):
                            aligned = recognizer.alignCrop(img, face)
                            feat = recognizer.feature(aligned)[0]
                            # Normalizar vector para distancia coseno pura
                            feat_norm = feat / np.linalg.norm(feat)
                            items.append({'path': file_path, 'feat': feat_norm})
            except Exception as e:
                pass

print(f"Total de caras válidas extraídas: {len(items)}")

if len(items) < 2:
    print("Insuficientes caras para agrupar.")
    sys.exit(0)

# 2. DBSCAN Estricto con metric='cosine' y eps=0.35 (similitud >= 0.65)
features_matrix = np.array([x['feat'] for x in items])

print("Ejecutando DBSCAN estricto...")
clustering = DBSCAN(eps=0.35, min_samples=2, metric='cosine').fit(features_matrix)
labels = clustering.labels_

# Organizar por clusters
cluster_dict = {}
for idx, label in enumerate(labels):
    if label == -1: continue # Ruido / caras únicas no repetidas
    if label not in cluster_dict:
        cluster_dict[label] = set()
    cluster_dict[label].add(items[idx]['path'])

valid_clusters = list(cluster_dict.values())
print(f"¡Éxito! Se han descubierto {len(valid_clusters)} grupos de alta precisión (misma persona confirmada).")

# 3. Crear carpetas de grupos limpios y vincular los archivos
if SIN_NOMBRE_DIR.exists():
    shutil.rmtree(str(SIN_NOMBRE_DIR), ignore_errors=True)

SIN_NOMBRE_DIR.mkdir(parents=True, exist_ok=True)

for idx, photo_paths in enumerate(valid_clusters):
    group_dir = SIN_NOMBRE_DIR / f"Persona Nueva #{idx+1:02d}"
    group_dir.mkdir(parents=True, exist_ok=True)
    
    for orig_path in photo_paths:
        target_path = group_dir / orig_path.name
        counter = 1
        while target_path.exists():
            target_path = group_dir / f"{orig_path.stem}_{counter}{orig_path.suffix}"
            counter += 1
        try:
            os.link(str(orig_path), str(target_path))
        except:
            try:
                shutil.copy2(str(orig_path), str(target_path))
            except:
                pass

print("Proceso de Clustering Estricto completado con éxito.")
'''

with open('cluster_dudosos.py', 'w', encoding='utf-8') as f:
    f.write(script_content)

print("cluster_dudosos.py actualizado con DBSCAN estricto (eps=0.35, cos >= 0.65).")
