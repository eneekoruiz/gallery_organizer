import os, sys, pickle, cv2, shutil
import numpy as np
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

BASE_DIR = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR")
RESULTADOS_DIR = BASE_DIR / "Resultados"

yunet_path = "models/face_detection_yunet_2023mar.onnx"
sface_path = "models/face_recognition_sface_2021dec.onnx"

detector = cv2.FaceDetectorYN.create(yunet_path, "", (320, 320))
recognizer = cv2.FaceRecognizerSF.create(sface_path, "")

def get_cosine_similarity(feat1, feat2):
    f1 = np.squeeze(feat1)
    f2 = np.squeeze(feat2)
    return np.dot(f1, f2) / (np.linalg.norm(f1) * np.linalg.norm(f2))

print("==================================================")
print("🚀 FASE 1: RE-ENTRENAMIENTO PROFUNDO DE CENTROIDES")
print("==================================================")

centroids = {}
identity_features = {}

valid_exts = {".jpg", ".jpeg", ".png", ".webp"}

# Walk confirmed categories
for cat in RESULTADOS_DIR.iterdir():
    if cat.is_dir() and cat.name not in ["Personas Sin Nombre", "Revision_Interactiva", "Ignorar"]:
        for ident in cat.iterdir():
            if ident.is_dir() and not ident.name.startswith("_"):
                key = (cat.name, ident.name)
                features = []
                for fp in list(ident.glob("*.*"))[:25]:
                    if fp.suffix.lower() in valid_exts:
                        img = cv2.imread(str(fp))
                        if img is None: continue
                        h, w = img.shape[:2]
                        detector.setInputSize((w, h))
                        _, faces = detector.detect(img)
                        if faces is not None and len(faces) > 0:
                            aligned = recognizer.alignCrop(img, faces[0])
                            feat = recognizer.feature(aligned)
                            features.append(feat)
                if features:
                    avg_feat = np.mean(features, axis=0)
                    avg_feat = avg_feat / np.linalg.norm(avg_feat)
                    centroids[key] = avg_feat
                    print(f"✓ Centroide entrenado para {cat.name} > {ident.name} ({len(features)} muestras)")

with open('centroids.pkl', 'wb') as f:
    pickle.dump(centroids, f)

print(f"\n✓ Se han entrenado {len(centroids)} identidades reconocidas.")

print("\n==================================================")
print("🔍 FASE 2: ESCANEO Y CLASIFICACIÓN DE DUDOSOS Y VIDEOS")
print("==================================================")

pending_dirs = []
for root, dirs, files in os.walk(str(RESULTADOS_DIR)):
    rname = Path(root).name
    if "Sin Nombre" in root or "_Dudosos" in root or "Desconocido" in root:
        pending_dirs.append(root)

print(f"Directorios pendientes encontrados: {len(pending_dirs)}")

promoted_count = 0

for pdir in pending_dirs:
    for f in list(Path(pdir).glob("*.*")):
        ext = f.suffix.lower()
        if ext in {".jpg", ".jpeg", ".png", ".webp"}:
            img = cv2.imread(str(f))
            if img is None: continue
            
            # Multi-Scale Detection (1.0x, 1.5x upscaling)
            best_match = None
            best_sim = -1.0
            second_sim = -1.0
            
            h_orig, w_orig = img.shape[:2]
            scales = [1.0]
            if min(h_orig, w_orig) < 600:
                scales.append(1.5)
                
            for scale in scales:
                if scale != 1.0:
                    scaled_img = cv2.resize(img, (0, 0), fx=scale, fy=scale)
                else:
                    scaled_img = img
                    
                sh, sw = scaled_img.shape[:2]
                detector.setInputSize((sw, sh))
                _, faces = detector.detect(scaled_img)
                
                if faces is not None:
                    for face in faces:
                        aligned = recognizer.alignCrop(scaled_img, face)
                        feat = recognizer.feature(aligned)
                        
                        # Compare against all centroids
                        sims = []
                        for key, cent in centroids.items():
                            sim = get_cosine_similarity(cent, feat)
                            sims.append((sim, key))
                            
                        sims.sort(key=lambda x: x[0], reverse=True)
                        if sims:
                            top_sim, top_key = sims[0]
                            sec_sim = sims[1][0] if len(sims) > 1 else 0.0
                            if top_sim > best_sim:
                                best_sim = top_sim
                                second_sim = sec_sim
                                best_match = top_key
                                
            # Auto-Promotion Threshold
            if best_match and best_sim >= 0.58 and (best_sim - second_sim) >= 0.05:
                cat_target, ident_target = best_match
                dest_dir = RESULTADOS_DIR / cat_target / ident_target
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_path = dest_dir / f.name
                if dest_path.exists() and dest_path != f:
                    dest_path = dest_dir / f"promoted_{f.name}"
                try:
                    shutil.move(str(f), str(dest_path))
                    promoted_count += 1
                    print(f"✨ PROMOVIDA: {f.name} -> {cat_target} > {ident_target} (Confianza: {best_sim*100:.1f}%)")
                except Exception as me:
                    pass

        elif ext in {".mp4", ".mov", ".avi"}:
            cap = cv2.VideoCapture(str(f))
            if not cap.isOpened(): continue
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            
            sample_seconds = [1.0, 3.0, 5.0, 8.0, 12.0]
            best_match = None
            best_sim = -1.0
            second_sim = -1.0
            
            for sec in sample_seconds:
                frame_idx = int(sec * fps)
                if frame_idx >= total_frames: break
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret or frame is None: continue
                
                fh, fw = frame.shape[:2]
                detector.setInputSize((fw, fh))
                _, faces = detector.detect(frame)
                if faces is not None:
                    for face in faces:
                        aligned = recognizer.alignCrop(frame, face)
                        feat = recognizer.feature(aligned)
                        
                        sims = []
                        for key, cent in centroids.items():
                            sim = get_cosine_similarity(cent, feat)
                            sims.append((sim, key))
                            
                        sims.sort(key=lambda x: x[0], reverse=True)
                        if sims:
                            top_sim, top_key = sims[0]
                            sec_sim = sims[1][0] if len(sims) > 1 else 0.0
                            if top_sim > best_sim:
                                best_sim = top_sim
                                second_sim = sec_sim
                                best_match = top_key
            cap.release()
            
            if best_match and best_sim >= 0.58 and (best_sim - second_sim) >= 0.05:
                cat_target, ident_target = best_match
                dest_dir = RESULTADOS_DIR / cat_target / ident_target
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_path = dest_dir / f.name
                if dest_path.exists() and dest_path != f:
                    dest_path = dest_dir / f"promoted_{f.name}"
                try:
                    shutil.move(str(f), str(dest_path))
                    promoted_count += 1
                    print(f"🎥 VÍDEO PROMOVIDO: {f.name} -> {cat_target} > {ident_target} (Confianza: {best_sim*100:.1f}%)")
                except Exception as me:
                    pass

print("\n==================================================")
print(f"✅ PROCESO COMPLETADO: {promoted_count} fotos y vídeos dudosos han sido oficialmente promogidos y organizados.")
print("==================================================")
