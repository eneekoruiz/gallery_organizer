import os
import sys
import pickle
import cv2
import shutil
import numpy as np
from pathlib import Path

try:
    from sklearn.cluster import DBSCAN
except ImportError:
    DBSCAN = None

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

_orig_print = print
def print(*args, **kwargs):
    kwargs['flush'] = True
    _orig_print(*args, **kwargs)


APP_DIR = Path(__file__).resolve().parent
# Galeria base — siempre usar la ruta correcta de la galería del usuario
_GALLERY_BASE = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR")
if _GALLERY_BASE.exists():
    RESULTADOS_DIR = _GALLERY_BASE / "Resultados"
    FOTOS_DIR = _GALLERY_BASE / "Fotos" if (_GALLERY_BASE / "Fotos").exists() else None
else:
    # Fallback: usar directorio relativo al script
    RESULTADOS_DIR = APP_DIR / "Resultados"
    FOTOS_DIR = None
    if not RESULTADOS_DIR.exists():
        print("ADVERTENCIA: No se encontro el directorio Resultados. Verifica la ruta.")

print(f"RESULTADOS_DIR = {RESULTADOS_DIR}")
print(f"FOTOS_DIR      = {FOTOS_DIR}")


YUNET_PATH = str(APP_DIR / "face_detection_yunet_2023mar.onnx")
SFACE_PATH = str(APP_DIR / "face_recognition_sface_2021dec.onnx")

if not os.path.exists(YUNET_PATH):
    YUNET_PATH = str(APP_DIR / "models" / "face_detection_yunet.onnx")
if not os.path.exists(SFACE_PATH):
    SFACE_PATH = str(APP_DIR / "models" / "face_recognition_sface.onnx")

detector = cv2.FaceDetectorYN.create(YUNET_PATH, "", (320, 320), 0.55)
recognizer = cv2.FaceRecognizerSF.create(SFACE_PATH, "")

def get_cosine_similarity(f1, f2):
    v1 = np.squeeze(f1)
    v2 = np.squeeze(f2)
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-10))

def safe_move(src, dst):
    src_str, dst_str = str(src), str(dst)
    if src_str == dst_str: return
    # Nunca mover archivos del Dataset (Fotos/) — estan protegidos
    if FOTOS_DIR and Path(src_str).is_relative_to(FOTOS_DIR):
        print(f"  PROTEGIDO (Dataset): {Path(src_str).name} — omitido")
        return
    Path(dst_str).parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(src_str, dst_str)
    except Exception:
        shutil.copy2(src_str, dst_str)
        try: os.remove(src_str)
        except Exception: pass

print("======================================================================")
print("🚀 FASE 1: REENTRENAMIENTO PURIFICADO DE CENTROIDES Y RECHAZO DE OUTLIERS")
print("======================================================================")

target_cats = ["Conocidos", "Familia"]
valid_exts = {".jpg", ".jpeg", ".png", ".webp"}

known_centroids = {}
total_seeds = 0

# Escanear tanto Fotos/ (Dataset verificado) como Resultados/ para construir centroides limpios
scan_dirs_for_training = [RESULTADOS_DIR]
if FOTOS_DIR and FOTOS_DIR.exists():
    scan_dirs_for_training.append(FOTOS_DIR)
print(f"Directorios de entrenamiento: {[str(d) for d in scan_dirs_for_training]}")

for cat_name in target_cats:
  for train_dir in scan_dirs_for_training:
    cat_dir = train_dir / cat_name
    if not cat_dir.exists(): continue

    for ident_dir in cat_dir.iterdir():
        if not ident_dir.is_dir() or ident_dir.name.startswith("_") or ident_dir.name in ["Desconocidos", "Personas Sin Nombre", "Ignorar"]:
            continue

        identity_name = ident_dir.name
        feats = []

        for img_file in ident_dir.glob("*.*"):
            if img_file.suffix.lower() not in valid_exts: continue
            try:
                file_bytes = np.fromfile(str(img_file), dtype=np.uint8)
                img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                if img is None: continue

                h, w, _ = img.shape
                max_sz = 1000
                if max(h, w) > max_sz:
                    if w > h:
                        new_w = max_sz
                        new_h = int(h * max_sz / w)
                    else:
                        new_h = max_sz
                        new_w = int(w * max_sz / h)
                    img_resized = cv2.resize(img, (new_w, new_h))
                    detector.setInputSize((new_w, new_h))
                    _, faces = detector.detect(img_resized)
                    if faces is not None and len(faces) > 0:
                        face = faces[0].copy()
                        scale_x = w / new_w
                        scale_y = h / new_h
                        face[0] *= scale_x
                        face[1] *= scale_y
                        face[2] *= scale_x
                        face[3] *= scale_y
                        for l_idx in range(4, 14, 2):
                            face[l_idx] *= scale_x
                            face[l_idx+1] *= scale_y
                        aligned = recognizer.alignCrop(img, face)
                        feat = recognizer.feature(aligned)[0]
                        feat_norm = feat / (np.linalg.norm(feat) + 1e-10)
                        feats.append(feat_norm)
                else:
                    detector.setInputSize((w, h))
                    _, faces = detector.detect(img)
                    if faces is not None and len(faces) > 0:
                        aligned = recognizer.alignCrop(img, faces[0])
                        feat = recognizer.feature(aligned)[0]
                        feat_norm = feat / (np.linalg.norm(feat) + 1e-10)
                        feats.append(feat_norm)
            except Exception: pass

        if len(feats) > 0:
            feats_arr = np.array(feats)
            raw_mean = np.mean(feats_arr, axis=0)
            raw_mean /= (np.linalg.norm(raw_mean) + 1e-10)

            valid_feats = []
            for feat in feats_arr:
                if get_cosine_similarity(raw_mean, feat) >= 0.35:
                    valid_feats.append(feat)

            if len(valid_feats) == 0:
                valid_feats = feats_arr

            clean_centroid = np.mean(valid_feats, axis=0)
            clean_centroid /= (np.linalg.norm(clean_centroid) + 1e-10)

            key = (cat_name, identity_name)
            known_centroids[key] = clean_centroid
            total_seeds += 1
            print(f"✓ Semilla purificada: [{cat_name}] {identity_name} ({len(valid_feats)}/{len(feats)} muestras válidas)")

print(f"\n✅ Fase 1 completada. Se han purificado {total_seeds} centroides faciales humanos.")

# Entrenar de forma separada los centroides de Mascotas usando YOLOv8 + MobileNetV3
print("\n🐾 Entrenando centroides de Mascotas...")
try:
    import torch
    import torchvision.models as models
    import torchvision.transforms as transforms
    from PIL import Image
    from app.services.face_service import AnimalDetector
    
    animal_detector = AnimalDetector.get_instance()
    new_centroids_mascotas = {}
    
    for base_dir in [FOTOS_DIR, RESULTADOS_DIR]:
        cat_dir = base_dir / "Mascotas"
        if not cat_dir.exists(): continue
        for ident_dir in cat_dir.iterdir():
            if not ident_dir.is_dir() or ident_dir.name.startswith("_") or ident_dir.name in ["Desconocidos", "Personas Sin Nombre", "Ignorar"]:
                continue
            
            pet_name = ident_dir.name
            if pet_name not in new_centroids_mascotas:
                new_centroids_mascotas[pet_name] = []
                
            for img_file in ident_dir.glob("*.*"):
                if img_file.suffix.lower() not in valid_exts: continue
                try:
                    file_bytes = np.fromfile(str(img_file), dtype=np.uint8)
                    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                    if img is None: continue
                    
                    results = animal_detector.yolo_model(img, verbose=False)
                    for r in results:
                        for box in r.boxes:
                            cls = int(box.cls[0])
                            if cls in [15, 16]:
                                x1, y1, x2, y2 = map(int, box.xyxy[0])
                                w = x2 - x1
                                h = y2 - y1
                                head_h = int(h * 0.40)
                                crop = img[y1:y1+head_h, x1:x1+w]
                                feat = animal_detector.extract_feature(crop)
                                if feat is not None:
                                    new_centroids_mascotas[pet_name].append(feat)
                                    break
                except Exception: pass
                
    averaged_centroids = {}
    for pet_name, feats in new_centroids_mascotas.items():
        if len(feats) > 0:
            feats_arr = np.array(feats)
            raw_centroid = np.mean(feats_arr, axis=0)
            raw_centroid /= (np.linalg.norm(raw_centroid) + 1e-10)
            averaged_centroids[pet_name] = raw_centroid
            print(f"✓ Semilla purificada (Mascota): [Mascotas] {pet_name} ({len(feats)} muestras)")
            
    animal_detector.centroids_mascotas = averaged_centroids
    animal_detector.save_centroids()
    print("✅ Entrenamiento de Mascotas completado.")
except Exception as mae_err:
    print("❌ Error entrenando Mascotas:", mae_err)

print("\n======================================================================")
print("🔍 FASE 2: REESCANEO PROFUNDO DE 'RECUERDOS', 'DUDOSOS' Y 'SIN NOMBRE'")
print("======================================================================")

scan_targets = []
for root, dirs, files in os.walk(str(RESULTADOS_DIR)):
    rpath = Path(root)
    rname = rpath.name.lower()
    if "sin nombre" in rname or "_dudosos" in rname or "desconocid" in rname or "recuerdos" in rname:
        scan_targets.append(rpath)

print(f"Directorio(s) objetivo(s) a escanear: {len(scan_targets)}")

promoted_count = 0

for target_dir in scan_targets:
    if not target_dir.exists(): continue
    for img_file in list(target_dir.glob("*.*")):
        if img_file.suffix.lower() not in valid_exts: continue
        try:
            file_bytes = np.fromfile(str(img_file), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None: continue

            h, w, _ = img.shape
            max_sz = 1000
            faces = None
            if max(h, w) > max_sz:
                if w > h:
                    new_w = max_sz
                    new_h = int(h * max_sz / w)
                else:
                    new_h = max_sz
                    new_w = int(w * max_sz / h)
                img_resized = cv2.resize(img, (new_w, new_h))
                detector.setInputSize((new_w, new_h))
                _, faces_resized = detector.detect(img_resized)
                if faces_resized is not None and len(faces_resized) > 0:
                    faces = faces_resized.copy()
                    scale_x = w / new_w
                    scale_y = h / new_h
                    for face in faces:
                        face[0] *= scale_x
                        face[1] *= scale_y
                        face[2] *= scale_x
                        face[3] *= scale_y
                        for l_idx in range(4, 14, 2):
                            face[l_idx] *= scale_x
                            face[l_idx+1] *= scale_y
            else:
                detector.setInputSize((w, h))
                _, faces = detector.detect(img)

            if faces is None or len(faces) == 0: continue

            for face in faces:
                aligned = recognizer.alignCrop(img, face)
                feat = recognizer.feature(aligned)[0]
                feat_norm = feat / (np.linalg.norm(feat) + 1e-10)

                best_match = None
                best_score = 0.0

                for (cat_name, ident_name), centroid in known_centroids.items():
                    sim = get_cosine_similarity(centroid, feat_norm)
                    if sim > best_score:
                        best_score = sim
                        best_match = (cat_name, ident_name)

                if best_match and best_score >= 0.58:
                    cat_target, ident_target = best_match
                    dest = RESULTADOS_DIR / cat_target / ident_target / img_file.name
                    counter = 1
                    while dest.exists():
                        dest = RESULTADOS_DIR / cat_target / ident_target / f"{img_file.stem}_{counter}{img_file.suffix}"
                        counter += 1
                    safe_move(img_file, dest)
                    promoted_count += 1
                    print(f"✨ Promovida foto: {img_file.name} ➔ [{cat_target}] {ident_target} (Confianza: {best_score:.2f})")
                    break
        except Exception: pass

print(f"\n✅ Fase 2 completada. Se han clasificado {promoted_count} fotos con alta confianza.")

print("\n======================================================================")
print("🧩 FASE 3: RE-CLUSTERING DBSCAN DE CARAS SIN NOMBRE RESTANTES")
print("======================================================================")

if DBSCAN is not None:
    sin_nombre_dir = RESULTADOS_DIR / "Personas Sin Nombre"
    if sin_nombre_dir.exists():
        orphan_files = []
        orphan_features = []

        for img_file in sin_nombre_dir.glob("*.*"):
            if img_file.suffix.lower() not in valid_exts: continue
            try:
                file_bytes = np.fromfile(str(img_file), dtype=np.uint8)
                img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                if img is None: continue

                h, w, _ = img.shape
                max_sz = 1000
                if max(h, w) > max_sz:
                    if w > h:
                        new_w = max_sz
                        new_h = int(h * max_sz / w)
                    else:
                        new_h = max_sz
                        new_w = int(w * max_sz / h)
                    img_resized = cv2.resize(img, (new_w, new_h))
                    detector.setInputSize((new_w, new_h))
                    _, faces = detector.detect(img_resized)
                    if faces is not None and len(faces) > 0:
                        face = faces[0].copy()
                        scale_x = w / new_w
                        scale_y = h / new_h
                        face[0] *= scale_x
                        face[1] *= scale_y
                        face[2] *= scale_x
                        face[3] *= scale_y
                        for l_idx in range(4, 14, 2):
                            face[l_idx] *= scale_x
                            face[l_idx+1] *= scale_y
                        aligned = recognizer.alignCrop(img, face)
                        feat = recognizer.feature(aligned)[0]
                        feat_norm = feat / (np.linalg.norm(feat) + 1e-10)
                        orphan_files.append(img_file)
                        orphan_features.append(feat_norm)
                else:
                    detector.setInputSize((w, h))
                    _, faces = detector.detect(img)
                    if faces is not None and len(faces) > 0:
                        aligned = recognizer.alignCrop(img, faces[0])
                        feat = recognizer.feature(aligned)[0]
                        feat_norm = feat / (np.linalg.norm(feat) + 1e-10)
                        orphan_files.append(img_file)
                        orphan_features.append(feat_norm)
            except Exception: pass

        if len(orphan_features) >= 3:
            X = np.array(orphan_features)
            db = DBSCAN(eps=0.45, min_samples=2, metric='cosine').fit(X)
            labels = db.labels_

            grouped_count = 0
            for idx, label in enumerate(labels):
                if label != -1:
                    group_folder = sin_nombre_dir / f"Persona Nueva {label + 1}"
                    dest = group_folder / orphan_files[idx].name
                    safe_move(orphan_files[idx], dest)
                    grouped_count += 1

            print(f"✓ DBSCAN agrupó {grouped_count} fotos en carpetas ordenadas tipo 'Persona Nueva N'.")
else:
    print("⚠️ sklearn.cluster DBSCAN no disponible. Saltando Fase 3.")

print("\n======================================================================")
print("💾 GUARDANDO MODELO Y LIMPIANDO CACHÉ")
print("======================================================================")

save_known = {}
for (cat, ident), cent in known_centroids.items():
    save_known[ident] = {'centroid': cent, 'names': []}

cache_file = APP_DIR / "sface_cache_v7.pkl"
with open(cache_file, 'wb') as f:
    pickle.dump(save_known, f)

print(f"✓ Modelo guardado en {cache_file.name}")
print("\n🎉 REANÁLISIS MAESTRO FINALIZADO CON ÉXITO.")
