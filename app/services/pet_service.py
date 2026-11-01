# -*- coding: utf-8 -*-
import os
import cv2
import numpy as np
from pathlib import Path
import threading

_yolo_model = None
_yolo_lock = threading.Lock()

known_pets = {} # pet_name -> {"centroid": np.array, "count": int}
pet_cache_lock = threading.Lock()

def get_yolo_model():
    global _yolo_model
    if _yolo_model is None:
        with _yolo_lock:
            if _yolo_model is None:
                try:
                    from ultralytics import YOLO
                    _yolo_model = YOLO("yolov8n.pt")
                except Exception as e:
                    print(f"[PET_SERVICE] Error cargando YOLO: {e}")
                    _yolo_model = False
    return _yolo_model if _yolo_model is not False else None

def detect_pets_and_bodies(img_bgr, conf_thresh=0.25):
    """
    Detecta de forma ultrarrápida:
    1. Mascotas (perro, gato, caballo, etc.)
    2. Cuerpos humanos (personas de espaldas, con filtros de Snapchat/Instagram, etc.)
    """
    model = get_yolo_model()
    if model is None or img_bgr is None:
        return {"pets": [], "bodies": []}
        
    h, w = img_bgr.shape[:2]
    max_dim = 640
    scale = 1.0
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        in_w = int(w * scale)
        in_h = int(h * scale)
        in_img = cv2.resize(img_bgr, (in_w, in_h))
    else:
        in_img = img_bgr
        
    try:
        results = model.predict(source=in_img, conf=conf_thresh, verbose=False)
        detected_pets = []
        detected_bodies = []
        inv_scale = 1.0 / scale if scale > 0 else 1.0
        
        PET_CLASSES = {"dog", "cat", "bird", "horse", "sheep", "cow"}
        
        if results and len(results) > 0:
            res = results[0]
            for box in res.boxes:
                cls_id = int(box.cls[0])
                cls_name = res.names[cls_id]
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].tolist()
                x1 = max(0, int(xyxy[0] * inv_scale))
                y1 = max(0, int(xyxy[1] * inv_scale))
                x2 = min(w, int(xyxy[2] * inv_scale))
                y2 = min(h, int(xyxy[3] * inv_scale))
                bw = x2 - x1
                bh = y2 - y1
                
                if bw >= 20 and bh >= 20:
                    item = {
                        "x": x1, "y": y1, "width": bw, "height": bh,
                        "class": cls_name, "confidence": conf
                    }
                    if cls_name == "person":
                        detected_bodies.append(item)
                    elif cls_name in PET_CLASSES:
                        detected_pets.append(item)
                        
        return {"pets": detected_pets, "bodies": detected_bodies}
    except Exception as e:
        print(f"[PET_SERVICE] Error en detección YOLO: {e}")
        return {"pets": [], "bodies": []}

def detect_pets(img_bgr, conf_thresh=0.28):
    return detect_pets_and_bodies(img_bgr, conf_thresh).get("pets", [])

def extract_pet_feature(crop_bgr):
    """Extrae descriptor 128D de textura, morfología y espacio de color de la mascota."""
    if crop_bgr is None or crop_bgr.shape[0] < 10 or crop_bgr.shape[1] < 10:
        return None
        
    resized = cv2.resize(crop_bgr, (112, 112))
    hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(resized, cv2.COLOR_BGR2LAB)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    
    blocks = []
    for r in range(2):
        for c in range(2):
            b_hsv = hsv[r*56:(r+1)*56, c*56:(c+1)*56]
            b_lab = lab[r*56:(r+1)*56, c*56:(c+1)*56]
            b_gray = gray[r*56:(r+1)*56, c*56:(c+1)*56]
            
            h_hist = cv2.calcHist([b_hsv], [0], None, [8], [0, 180]).flatten()
            s_hist = cv2.calcHist([b_hsv], [1], None, [8], [0, 256]).flatten()
            l_hist = cv2.calcHist([b_lab], [0], None, [8], [0, 256]).flatten()
            
            gx = cv2.Sobel(b_gray, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(b_gray, cv2.CV_32F, 0, 1, ksize=3)
            mag = np.sqrt(gx**2 + gy**2)
            mag_hist = cv2.calcHist([mag.astype(np.uint8)], [0], None, [8], [0, 256]).flatten()
            
            block_feat = np.concatenate([h_hist, s_hist, l_hist, mag_hist])
            blocks.append(block_feat)
            
    feat = np.concatenate(blocks)
    norm = feat / (np.linalg.norm(feat) + 1e-10)
    return norm

def rebuild_pet_centroids():
    """Entrena y actualiza los centroides de cada mascota."""
    from app.globals import FOTOS_DIR, RESULTADOS_DIR
    samples = {}
    valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
    
    for b_dir in [FOTOS_DIR, RESULTADOS_DIR]:
        if not b_dir.exists(): continue
        mascotas_dir = b_dir / "Mascotas"
        if not mascotas_dir.exists(): continue
        
        for p_folder in mascotas_dir.iterdir():
            if p_folder.is_dir() and (p_folder.name.startswith("M.") or "mascota nueva" in p_folder.name.lower()):
                pet_name = p_folder.name
                if pet_name not in samples: samples[pet_name] = []
                
                for f in p_folder.iterdir():
                    if f.is_file() and f.suffix.lower() in valid_exts:
                        try:
                            img_bytes = np.fromfile(str(f), dtype=np.uint8)
                            img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
                            if img is not None:
                                pets_found = detect_pets(img, conf_thresh=0.25)
                                if pets_found:
                                    best_pet = max(pets_found, key=lambda p: p["width"] * p["height"])
                                    crop = img[best_pet["y"]:best_pet["y"]+best_pet["height"], best_pet["x"]:best_pet["x"]+best_pet["width"]]
                                else:
                                    h, w = img.shape[:2]
                                    crop = img[int(h*0.15):int(h*0.85), int(w*0.15):int(w*0.85)]
                                    
                                feat = extract_pet_feature(crop)
                                if feat is not None:
                                    samples[pet_name].append(feat)
                        except Exception: pass
                        
    with pet_cache_lock:
        known_pets.clear()
        for pet_name, feat_list in samples.items():
            if len(feat_list) > 0:
                mean_v = np.mean(feat_list, axis=0)
                norm_c = mean_v / (np.linalg.norm(mean_v) + 1e-10)
                known_pets[pet_name] = {
                    "centroid": norm_c,
                    "count": len(feat_list)
                }
                print(f"[PET_SERVICE] Centroide 🐶 {pet_name} entrenado con {len(feat_list)} fotos.")
    return known_pets

def match_pet_identity(crop_bgr):
    """Devuelve (best_pet_name, confidence_score, feature_vec)."""
    feat = extract_pet_feature(crop_bgr)
    if feat is None or not known_pets:
        return None, 0.0, None
        
    best_name = None
    best_score = 0.0
    
    for p_name, p_data in known_pets.items():
        c = p_data.get("centroid")
        if c is not None:
            score = float(np.dot(feat, c))
            if score > best_score:
                best_score = score
                best_name = p_name
                
    return best_name, best_score, feat
