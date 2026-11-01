import os
import cv2
import pickle
import numpy as np
from pathlib import Path
import json

APP_DIR = Path(".")
RESULTADOS_DIR = APP_DIR / "Resultados"
CACHE_FILE = APP_DIR / "sface_cache_v7.pkl"
STATUS_FILE = APP_DIR / "auto_merge_status.json"

def update_status(status_text, progress=0):
    with open(STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump({"status": status_text, "progress": progress}, f)

try:
    detector = cv2.FaceDetectorYN.create("models/face_detection_yunet.onnx", "", (320, 320))
    recognizer = cv2.FaceRecognizerSF.create("models/face_recognition_sface.onnx", "")
except Exception as e:
    update_status(f"Error loading models: {e}", -1)
    exit(1)

def get_cosine_similarity(feat1, feat2):
    f1 = np.squeeze(feat1)
    f2 = np.squeeze(feat2)
    return np.dot(f1, f2) / (np.linalg.norm(f1) * np.linalg.norm(f2))

def run_auto_merge(threshold=0.68):
    update_status("Iniciando Auto-Fusión...", 0)
    
    if not CACHE_FILE.exists():
        update_status("No hay caché de caras conocidas.", -1)
        return
        
    with open(CACHE_FILE, 'rb') as f:
        known_faces = pickle.load(f)
        
    trusted = {}
    for name, data in known_faces.items():
        if "C." in name or "F." in name or "Familia" in name or "YO" in name:
            if "centroid" in data:
                trusted[name] = data["centroid"]
                
    if not trusted:
        update_status("No hay identidades de confianza para comparar.", -1)
        return
        
    unknown_dirs = [
        RESULTADOS_DIR / "Personas Sin Nombre",
        RESULTADOS_DIR / "Desconocidos"
    ]
    
    all_files = []
    for udir in unknown_dirs:
        if not udir.exists(): continue
        for root, dirs, files in os.walk(str(udir)):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    all_files.append(os.path.join(root, file))
                    
    total = len(all_files)
    if total == 0:
        update_status("No hay fotos desconocidas para escanear.", 100)
        return
        
    moved_count = 0
    import shutil
    
    for idx, path in enumerate(all_files):
        if idx % 10 == 0:
            update_status(f"Escaneando foto {idx}/{total}...", int((idx/total)*100))
            
        try:
            file_bytes = np.fromfile(path, dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        except:
            img = None
        if img is None: continue
        
        h, w = img.shape[:2]
        detector.setInputSize((w, h))
        _, faces = detector.detect(img)
        
        if faces is not None:
            best_match = None
            best_score = -1
            for face in faces:
                try:
                    aligned = recognizer.alignCrop(img, face)
                    feat = recognizer.feature(aligned)[0]
                except:
                    continue
                    
                for t_name, t_cent in trusted.items():
                    score = get_cosine_similarity(feat, t_cent)
                    if score > best_score:
                        best_score = score
                        best_match = t_name
                        
            if best_score > threshold and best_match:
                # We found a strong match! Move it to Conocidos physically.
                source_path = Path(path)
                cat = "Familia" if "F." in best_match or "Familia" in best_match else ("YO" if best_match == "YO" else "Conocidos")
                target_dir = RESULTADOS_DIR / cat / best_match
                target_dir.mkdir(parents=True, exist_ok=True)
                target_path = target_dir / source_path.name
                
                counter = 1
                while target_path.exists():
                    target_path = target_dir / f"{source_path.stem}_{counter}{source_path.suffix}"
                    counter += 1
                try:
                    shutil.move(str(source_path), str(target_path))
                    moved_count += 1
                except:
                    pass
                    
    # Limpiar directorios vacios
    for udir in unknown_dirs:
        if udir.exists():
            for root, dirs, files in os.walk(str(udir), topdown=False):
                for d in dirs:
                    dir_path = os.path.join(root, d)
                    try:
                        if not os.listdir(dir_path):
                            os.rmdir(dir_path)
                    except:
                        pass
                        
    update_status(f"Auto-Fusión completada. {moved_count} fotos reasignadas.", 100)

if __name__ == "__main__":
    run_auto_merge()
