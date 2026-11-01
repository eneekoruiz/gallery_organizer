import os
import cv2
import numpy as np
from pathlib import Path
import shutil
import json

try:
    from sklearn.cluster import DBSCAN
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "scikit-learn"])
    from sklearn.cluster import DBSCAN

APP_DIR = Path(".")
RESULTADOS_DIR = APP_DIR / "Resultados"
STATUS_FILE = APP_DIR / "recluster_status.json"

def update_status(status_text, progress=0):
    with open(STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump({"status": status_text, "progress": progress}, f)

try:
    detector = cv2.FaceDetectorYN.create("models/face_detection_yunet.onnx", "", (320, 320))
    recognizer = cv2.FaceRecognizerSF.create("models/face_recognition_sface.onnx", "")
except Exception as e:
    update_status(f"Error loading models: {e}", -1)
    exit(1)

def run_recluster():
    update_status("Iniciando Re-Clustering de Desconocidos...", 0)
    
    unknown_dir = RESULTADOS_DIR / "Desconocidos"
    if not unknown_dir.exists():
        update_status("No hay carpeta de Desconocidos.", 100)
        return
        
    all_files = []
    for root, dirs, files in os.walk(str(unknown_dir)):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                all_files.append(os.path.join(root, file))
                
    total = len(all_files)
    if total == 0:
        update_status("No hay fotos en Desconocidos.", 100)
        return
        
    embeddings = []
    valid_files = []
    
    for idx, path in enumerate(all_files):
        if idx % 10 == 0:
            update_status(f"Extrayendo rasgos {idx}/{total}...", int((idx/total)*50))
            
        img = cv2.imread(path)
        if img is None: continue
        
        h, w = img.shape[:2]
        detector.setInputSize((w, h))
        _, faces = detector.detect(img)
        
        if faces is not None:
            # Just take the first face for clustering
            face = faces[0]
            try:
                aligned = recognizer.alignCrop(img, face)
                feat = recognizer.feature(aligned)[0]
                embeddings.append(np.squeeze(feat))
                valid_files.append(path)
            except:
                pass
                
    if not embeddings:
        update_status("No se pudieron extraer rasgos.", 100)
        return
        
    update_status("Calculando clusters (agrupaciones)...", 60)
    
    X = np.array(embeddings)
    # Cosine distance: 1 - cosine_similarity
    # DBSCAN eps for cosine distance typically around 0.3 to 0.4
    clustering = DBSCAN(eps=0.35, min_samples=3, metric='cosine').fit(X)
    
    labels = clustering.labels_
    
    # Find next available persona ID
    psn_dir = RESULTADOS_DIR / "Personas Sin Nombre"
    psn_dir.mkdir(parents=True, exist_ok=True)
    existing = [d.name for d in psn_dir.iterdir() if d.is_dir() and "Persona Nueva #" in d.name]
    highest_id = 0
    for e in existing:
        try:
            num = int(e.split("#")[1])
            if num > highest_id:
                highest_id = num
        except:
            pass
            
    clusters_created = 0
    moved_files = 0
    
    unique_labels = set(labels)
    for label in unique_labels:
        if label == -1:
            continue # Noise
            
        highest_id += 1
        new_name = f"Persona Nueva #{highest_id:03d}"
        target_dir = psn_dir / new_name
        target_dir.mkdir(parents=True, exist_ok=True)
        clusters_created += 1
        
        # Move files
        for i, l in enumerate(labels):
            if l == label:
                source_path = Path(valid_files[i])
                target_path = target_dir / source_path.name
                counter = 1
                while target_path.exists():
                    target_path = target_dir / f"{source_path.stem}_{counter}{source_path.suffix}"
                    counter += 1
                try:
                    shutil.move(str(source_path), str(target_path))
                    moved_files += 1
                except:
                    pass
                    
    # Clean up empty directories
    for root, dirs, files in os.walk(str(unknown_dir), topdown=False):
        for d in dirs:
            dir_path = os.path.join(root, d)
            try:
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
            except:
                pass
                
    update_status(f"Re-Clustering completado. {clusters_created} nuevas personas creadas con {moved_files} fotos.", 100)

if __name__ == "__main__":
    run_recluster()
