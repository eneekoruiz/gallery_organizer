import os, sys, shutil, pickle, cv2
import numpy as np
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

BASE_DIR = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR")
RESULTADOS_DIR = BASE_DIR / "Resultados"

source_dir = RESULTADOS_DIR / "Conocidos" / "Casa nueva"
target_dir = RESULTADOS_DIR / "YO" / "YO"

target_dir.mkdir(parents=True, exist_ok=True)

if not source_dir.exists():
    print(f"Directory {source_dir} not found!")
    sys.exit(1)

moved_files = []
for fp in list(source_dir.glob("*.*")):
    dest_path = target_dir / fp.name
    if dest_path.exists() and dest_path != fp:
        dest_path = target_dir / f"moved_{fp.name}"
    try:
        shutil.move(str(fp), str(dest_path))
        moved_files.append(dest_path)
        print(f"✓ Movida a YO > YO: {fp.name}")
    except Exception as e:
        print(f"Error moving {fp.name}:", e)

# Remove empty source folder
try:
    shutil.rmtree(str(source_dir), ignore_errors=True)
    print("✓ Carpeta 'Casa nueva' eliminada de Conocidos.")
except Exception as e:
    pass

# Update overrides.json
overrides_file = Path("overrides.json")
overrides = {}
if overrides_file.exists():
    import json
    try:
        with open(overrides_file, 'r', encoding='utf-8') as f:
            overrides = json.load(f)
    except: pass

for mf in moved_files:
    file_k = str(mf.resolve())
    overrides[file_k] = [{
        'x': 0, 'y': 0, 'width': 0, 'height': 0,
        'identity': 'YO'
    }]

with open("overrides.json", 'w', encoding='utf-8') as f:
    import json
    json.dump(overrides, f, indent=2)
print("✓ Overrides actualizados para YO.")

# Feature Extraction and Retraining
yunet_path = "models/face_detection_yunet_2023mar.onnx"
sface_path = "models/face_recognition_sface_2021dec.onnx"

detector = cv2.FaceDetectorYN.create(yunet_path, "", (320, 320))
recognizer = cv2.FaceRecognizerSF.create(sface_path, "")

new_features = []
for mf in moved_files:
    img = cv2.imread(str(mf))
    if img is not None:
        h, w = img.shape[:2]
        detector.setInputSize((w, h))
        _, faces = detector.detect(img)
        if faces is not None and len(faces) > 0:
            aligned = recognizer.alignCrop(img, faces[0])
            feat = recognizer.feature(aligned)
            new_features.append(feat)

if new_features:
    centroids = {}
    if os.path.exists('centroids.pkl'):
        try:
            with open('centroids.pkl', 'rb') as cf:
                centroids = pickle.load(cf)
        except: pass
        
    key = ("YO", "YO")
    existing = centroids.get(key)
    all_f = new_features + ([existing] if existing is not None else [])
    avg_f = np.mean(all_f, axis=0)
    avg_f = avg_f / np.linalg.norm(avg_f)
    centroids[key] = avg_f
    
    with open('centroids.pkl', 'wb') as cf:
        pickle.dump(centroids, cf)
    print(f"✨ Centroide neuronal de IA re-entrenado para 'YO' con {len(new_features)} nuevas muestras faciales de Casa nueva.")

print("==================================================")
print("✅ PROCESO DE REASIGNACIÓN Y REENTRENAMIENTO A 'YO' COMPLETADO CON ÉXITO")
print("==================================================")
