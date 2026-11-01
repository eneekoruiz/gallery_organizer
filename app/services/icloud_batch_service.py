import os
import sys
import time
import subprocess
import threading
from pathlib import Path
import cv2
import numpy as np

ICLOUD_PHOTOS_DIR = Path(r"C:\Users\User\Pictures\iCloud Photos\Photos")

_batch_worker_thread = None
_stop_batch_event = threading.Event()
_pause_batch_event = threading.Event()

_batch_status = {
    "is_running": False,
    "is_paused": False,
    "processed": 0,
    "total": 0,
    "current_file": "",
    "faces_found": 0,
    "errors": 0
}

def free_up_file_space(file_path):
    try:
        p_str = str(file_path)
        subprocess.run(["attrib", "+U", "-P", p_str], capture_output=True, timeout=5)
    except Exception:
        pass

def get_icloud_sync_status():
    global _batch_status
    return dict(_batch_status)

def start_icloud_batch_indexing(include_videos=False, batch_size=30):
    global _batch_worker_thread, _stop_batch_event, _pause_batch_event, _batch_status
    
    if _batch_worker_thread and _batch_worker_thread.is_alive():
        return {"status": "already_running"}

    _stop_batch_event.clear()
    _pause_batch_event.clear()
    
    def _worker():
        global _batch_status
        _batch_status["is_running"] = True
        _batch_status["is_paused"] = False
        _batch_status["processed"] = 0
        _batch_status["errors"] = 0
        
        if not ICLOUD_PHOTOS_DIR.exists():
            _batch_status["is_running"] = False
            return

        valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
        if include_videos:
            valid_exts.update({".mp4", ".mov", ".avi"})

        all_files = [
            f for f in ICLOUD_PHOTOS_DIR.iterdir() 
            if f.is_file() and f.suffix.lower() in valid_exts
        ]
        
        _batch_status["total"] = len(all_files)
        
        from app.utils.files import generate_thumbnail, get_file_key
        from app.services.vector_index import vector_engine
        from app.globals import detector, recognizer, faces_cache, cache_lock, known_faces
        
        processed_count = 0
        
        for idx, file_path in enumerate(all_files):
            if _stop_batch_event.is_set():
                break
                
            while _pause_batch_event.is_set():
                time.sleep(0.5)
                if _stop_batch_event.is_set():
                    break

            _batch_status["current_file"] = file_path.name
            
            try:
                thumb = generate_thumbnail(file_path)
                
                if file_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                    try:
                        file_bytes = np.fromfile(str(file_path), dtype=np.uint8)
                        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                        if img is not None and detector is not None:
                            h, w = img.shape[:2]
                            detector.setInputSize((w, h))
                            _, faces = detector.detect(img)
                            if faces is not None and len(faces) > 0:
                                _batch_status["faces_found"] += len(faces)
                                fk = get_file_key(str(file_path))
                                detected_list = []
                                for face in faces:
                                    box = [int(face[0]), int(face[1]), int(face[2]), int(face[3])]
                                    conf = float(face[-1])
                                    matched_ident = "Desconocido"
                                    if recognizer is not None and conf >= 0.50:
                                        try:
                                            aligned = recognizer.alignCrop(img, face)
                                            feat = recognizer.feature(aligned)[0]
                                            feat_norm = feat / (np.linalg.norm(feat) + 1e-10)
                                            best_sim = 0.0
                                            best_ident = None
                                            with cache_lock:
                                                for k, v in known_faces.items():
                                                    c = v.get('centroid') if isinstance(v, dict) else None
                                                    if c is not None:
                                                        sim = float(np.dot(feat_norm, c))
                                                        if sim > best_sim:
                                                            best_sim = sim
                                                            best_ident = k[1] if isinstance(k, tuple) else str(k)
                                            if best_sim >= 0.62 and best_ident:
                                                matched_ident = best_ident
                                        except Exception:
                                            pass
                                    detected_list.append({
                                        "box": box,
                                        "confidence": conf,
                                        "identity": matched_ident
                                    })
                                with cache_lock:
                                    faces_cache[fk] = detected_list
                    except Exception:
                        pass

                # Extract Apple EXIF metadata into apple_db.json
                try:
                    from PIL import Image, ExifTags
                    with Image.open(str(file_path)) as pil_img:
                        ex = pil_img._getexif()
                        if ex:
                            d = {ExifTags.TAGS.get(k, k): v for k, v in ex.items() if k in ExifTags.TAGS}
                            meta = {}
                            if d.get('Make'): meta['make'] = str(d.get('Make')).strip()
                            if d.get('Model'): meta['model'] = str(d.get('Model')).strip()
                            if d.get('DateTimeOriginal'): meta['date'] = str(d.get('DateTimeOriginal')).strip()
                            if d.get('LensModel'): meta['lens'] = str(d.get('LensModel')).strip()
                            if meta:
                                from app.services.apple_service import load_apple_db, save_apple_db
                                db = load_apple_db()
                                fp_str = str(file_path)
                                if fp_str not in db:
                                    db[fp_str] = {
                                        'original_icloud_path': fp_str,
                                        'category': 'iCloud',
                                        'identity': 'Pendiente',
                                        'metadata': meta
                                    }
                                else:
                                    db[fp_str]['metadata'] = meta
                                save_apple_db()
                except Exception:
                    pass
                
                free_up_file_space(file_path)
                
                processed_count += 1
                _batch_status["processed"] = processed_count

                time.sleep(0.03)

            except Exception:
                _batch_status["errors"] += 1

        _batch_status["is_running"] = False

    _batch_worker_thread = threading.Thread(target=_worker, daemon=True, name="iCloudBatchWorker")
    _batch_worker_thread.start()
    return {"status": "started", "total_files": _batch_status["total"]}

def pause_icloud_batch():
    global _pause_batch_event, _batch_status
    _pause_batch_event.set()
    _batch_status["is_paused"] = True
    return {"status": "paused"}

def resume_icloud_batch():
    global _pause_batch_event, _batch_status
    _pause_batch_event.clear()
    _batch_status["is_paused"] = False
    return {"status": "resumed"}

def stop_icloud_batch():
    global _stop_batch_event, _pause_batch_event, _batch_status
    _stop_batch_event.set()
    _pause_batch_event.clear()
    _batch_status["is_running"] = False
    _batch_status["is_paused"] = False
    return {"status": "stopped"}