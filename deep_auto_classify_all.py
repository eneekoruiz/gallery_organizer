import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

import os, cv2, pickle, shutil, json
import numpy as np
from pathlib import Path

APP_DIR = Path(".")
RESULTADOS_DIR = APP_DIR / "Resultados"
CACHE_FILE = APP_DIR / "sface_cache_v7.pkl"
STATUS_FILE = APP_DIR / "deep_classify_status.json"
BASE_DIR = Path(r'C:\Users\User\Desktop\Galeria Eneko NO ABRIR')

def update_status(text, progress=0, details=None):
    data = {"status": text, "progress": progress}
    if details: data["details"] = details
    with open(STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f)

# 1. Load ONNX Models
detector = cv2.FaceDetectorYN.create("models/face_detection_yunet.onnx", "", (320, 320))
recognizer = cv2.FaceRecognizerSF.create("models/face_recognition_sface.onnx", "")

def get_sim(f1, f2):
    v1 = np.squeeze(f1)
    v2 = np.squeeze(f2)
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def run_deep_classify(threshold=0.65):
    update_status("Re-entrenando centroides con fotos confirmadas...", 5)
    
    # Cache para acelerar futuras ejecuciones
    feature_cache = {}
    cache_path = APP_DIR / "deep_features_cache.pkl"
    if cache_path.exists():
        try:
            with open(cache_path, 'rb') as f:
                feature_cache = pickle.load(f)
        except: pass
    cache_updated = False

    # 2. Extract / update centroids from all confirmed folders
    known_embeddings = {} # identity -> list of features
    
    confirmed_dirs = [
        BASE_DIR / 'Resultados' / 'Conocidos',
        BASE_DIR / 'Resultados' / 'Familia',
        BASE_DIR / 'Resultados' / 'YO'
    ]
    
    for cdir in confirmed_dirs:
        if not cdir.exists(): continue
        cat = cdir.name
        for root, dirs, files in os.walk(str(cdir)):
            if '_Dudosos' in root or 'rejected' in root.lower(): continue
            ident = Path(root).name
            if ident in [cat, 'Resultados']: continue
            
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    p = os.path.join(root, file)
                    try:
                        stat = os.stat(p)
                        sz, mt = stat.st_size, stat.st_mtime
                        p_str = str(p)
                        feats = []
                        if p_str in feature_cache and feature_cache[p_str]['sz'] == sz and feature_cache[p_str]['mt'] == mt:
                            feats = feature_cache[p_str]['feats']
                        else:
                            fb = np.fromfile(p, dtype=np.uint8)
                            img = cv2.imdecode(fb, cv2.IMREAD_COLOR)
                            if img is not None:
                                h, w = img.shape[:2]
                                detector.setInputSize((w, h))
                                _, faces = detector.detect(img)
                                if faces is not None:
                                    for face in faces:
                                        crop = recognizer.alignCrop(img, face)
                                        feat = recognizer.feature(crop)[0]
                                        feats.append(feat)
                            feature_cache[p_str] = {'sz': sz, 'mt': mt, 'feats': feats}
                            cache_updated = True
                        
                        if feats:
                            if ident not in known_embeddings:
                                known_embeddings[ident] = {'cat': cat, 'feats': []}
                            known_embeddings[ident]['feats'].extend(feats)
                    except:
                        pass

    # Build centroids
    centroids = {}
    for ident, data in known_embeddings.items():
        if len(data['feats']) > 0:
            avg_feat = np.mean(data['feats'], axis=0)
            avg_feat = avg_feat / np.linalg.norm(avg_feat)
            centroids[ident] = {'cat': data['cat'], 'centroid': avg_feat}
            
    print(f"Entrenadas {len(centroids)} personas confirmadas.")
    update_status(f"Centroides listos ({len(centroids)} personas). Escaneando fotos dudosas...", 15)
    
    # 3. Collect ALL pending / doubtful photos
    pending_files = []
    
    for root, dirs, files in os.walk(str(BASE_DIR)):
        is_pending = False
        if '_Dudosos' in root or 'rejected' in root.lower(): is_pending = True
        elif 'Revision_Interactiva' in root: is_pending = True
        elif 'Personas Sin Nombre' in root: is_pending = True
        elif 'Desconocidos' in root: is_pending = True
        
        if is_pending:
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    pending_files.append(os.path.join(root, file))

    total = len(pending_files)
    print(f"Total fotos dudosas/pendientes a clasificar: {total}")
    update_status(f"Clasificando {total} fotos dudosas...", 20)
    
    promoted_count = 0
    path_map = {}
    
    for idx, p in enumerate(pending_files):
        if idx % 20 == 0:
            prog = 20 + int((idx / max(1, total)) * 75)
            update_status(f"Procesando foto {idx}/{total} (Promovidas: {promoted_count})...", prog)
            
        if not os.path.exists(p): continue
        try:
            stat = os.stat(p)
            sz, mt = stat.st_size, stat.st_mtime
            p_str = str(p)
            feats = []
            if p_str in feature_cache and feature_cache[p_str]['sz'] == sz and feature_cache[p_str]['mt'] == mt:
                feats = feature_cache[p_str]['feats']
            else:
                fb = np.fromfile(p, dtype=np.uint8)
                img = cv2.imdecode(fb, cv2.IMREAD_COLOR)
                if img is not None:
                    h, w = img.shape[:2]
                    detector.setInputSize((w, h))
                    _, faces = detector.detect(img)
                    if faces is not None:
                        for face in faces:
                            crop = recognizer.alignCrop(img, face)
                            feat = recognizer.feature(crop)[0]
                            feats.append(feat)
                feature_cache[p_str] = {'sz': sz, 'mt': mt, 'feats': feats}
                cache_updated = True
                
            best_match_id = None
            best_match_cat = None
            best_sim = 0
            
            for feat in feats:
                for ident, cdata in centroids.items():
                    sim = get_sim(feat, cdata['centroid'])
                    if sim > best_sim:
                        best_sim = sim
                        best_match_id = ident
                        best_match_cat = cdata['cat']
                        
            if best_sim >= threshold and best_match_id:
                # Promote file to target folder!
                dst_dir = BASE_DIR / 'Resultados' / best_match_cat / best_match_id
                dst_dir.mkdir(parents=True, exist_ok=True)
                
                src_p = Path(p)
                dst_p = dst_dir / src_p.name
                counter = 1
                while dst_p.exists():
                    dst_p = dst_dir / f"{src_p.stem}_{counter}{src_p.suffix}"
                    counter += 1
                    
                shutil.move(str(src_p), str(dst_p))
                promoted_count += 1
                path_map[str(src_p)] = str(dst_p)
        except Exception as e:
            pass

    if cache_updated:
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(feature_cache, f)
        except: pass

    # Update faces_cache.pkl
    faces_cache_file = Path("faces_cache.pkl")
    if faces_cache_file.exists() and path_map:
        with open(faces_cache_file, 'rb') as f:
            faces_cache = pickle.load(f)
        for old_p, new_p in path_map.items():
            if old_p in faces_cache:
                faces_cache[new_p] = faces_cache.pop(old_p)
        with open(faces_cache_file, 'wb') as f:
            pickle.dump(faces_cache, f)

    update_status(f"🎉 Proceso completado: Se clasificaron automáticamente {promoted_count} fotos a sus dueños.", 100, {"promoted": promoted_count})
    print(f"🎉 PROMOTED {promoted_count} PHOTOS AUTOMATICALLY!")

if __name__ == "__main__":
    run_deep_classify()
