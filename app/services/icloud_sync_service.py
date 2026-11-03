import os
import gc
import re
import time
import json
import pickle
import threading
import subprocess
from pathlib import Path
import cv2
import numpy as np

from app.globals import APP_DIR, THUMBNAILS_DIR, set_gallery_cache
from app.services.apple_service import load_apple_db, save_apple_db, ICLOUD_PHOTOS_DIR
from app.utils.files import generate_thumbnail

CENTROIDS_FILE = APP_DIR / "centroids.pkl"
FACES_CACHE_FILE = APP_DIR / "faces_cache_v2.pkl"
PROGRESS_FILE = APP_DIR / "scratch" / "apple_progress.json"
RESULTADOS_DIR = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados")

_SYNC_LOCK = threading.Lock()
_SYNC_THREAD = None
_STOP_REQUESTED = threading.Event()

_SYNC_STATE = {
    "running": False,
    "total_icloud": 0,
    "already_processed": 0,
    "pending_in_cloud": 0,
    "processed_this_run": 0,
    "known_assigned": 0,
    "dudosos_assigned": 0,
    "sin_rostro_assigned": 0,
    "new_persons_assigned": 0,
    "dehydrated_count": 0,
    "current_file": None,
    "current_identity": None,
    "rate_per_sec": 0.0,
    "elapsed_sec": 0.0,
    "eta_minutes": 0.0,
    "status": "idle",
    "started_at": None,
    "last_error": None
}

def _save_progress_file():
    try:
        PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(_SYNC_STATE, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def get_icloud_sync_status():
    with _SYNC_LOCK:
        return dict(_SYNC_STATE)

def stop_icloud_sync():
    global _SYNC_THREAD
    _STOP_REQUESTED.set()
    with _SYNC_LOCK:
        _SYNC_STATE["status"] = "stopping"
    if _SYNC_THREAD and _SYNC_THREAD.is_alive():
        _SYNC_THREAD.join(timeout=3.0)
    with _SYNC_LOCK:
        _SYNC_STATE["running"] = False
        _SYNC_STATE["status"] = "stopped"
        _save_progress_file()
    return get_icloud_sync_status()

def _create_windows_url_shortcut(target_path, cat, ident):
    try:
        target_dir = RESULTADOS_DIR / cat / ident
        target_dir.mkdir(parents=True, exist_ok=True)
        file_name = os.path.basename(target_path)
        shortcut_file = target_dir / f"{file_name}.url"
        if not shortcut_file.exists():
            norm_target = target_path.replace("\\", "/")
            content = f"[InternetShortcut]\r\nURL=file:///{norm_target}\r\nIconFile=C:\\Windows\\System32\\shell32.dll\r\nIconIndex=301\r\n"
            shortcut_file.write_text(content, encoding="utf-8")
    except Exception:
        pass

def _dehydrate_cloud_file(filepath):
    """Marca el archivo como desanclado / liberar espacio (0 KB en disco local)."""
    try:
        subprocess.run(["attrib", "+U", "-P", str(filepath)], capture_output=True, timeout=5)
        return True
    except Exception:
        return False

def _ensure_icloud_client_running():
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Process -Name 'iCloudPhotos' -ErrorAction SilentlyContinue"], capture_output=True, text=True, timeout=5)
        if not res.stdout or "iCloudPhotos" not in res.stdout:
            appx_path = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\iCloudPhotos-AppX.exe")
            if os.path.exists(appx_path):
                subprocess.Popen([appx_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(2.5)
    except Exception:
        pass

def _run_icloud_worker(batch_size=None):
    _ensure_icloud_client_running()
    global _SYNC_THREAD
    t_start = time.time()
    
    # Modelos YuNet y SFace dedicados para el hilo de fondo
    try:
        det = cv2.FaceDetectorYN.create(str(APP_DIR / "models/face_detection_yunet.onnx"), "", (320, 320))
        rec = cv2.FaceRecognizerSF.create(str(APP_DIR / "models/face_recognition_sface.onnx"), "")
    except Exception as e:
        with _SYNC_LOCK:
            _SYNC_STATE["last_error"] = f"Error cargando modelos ONNX: {e}"
            _SYNC_STATE["running"] = False
            _SYNC_STATE["status"] = "error"
            _save_progress_file()
        return

    # Cargar centroides de personas conocidas
    centroids = {}
    if CENTROIDS_FILE.exists():
        try:
            with open(CENTROIDS_FILE, "rb") as f:
                centroids = pickle.load(f)
        except Exception:
            centroids = {}

    # Cargar cache de caras
    faces_cache = {}
    if FACES_CACHE_FILE.exists():
        try:
            with open(FACES_CACHE_FILE, "rb") as f:
                faces_cache = pickle.load(f)
        except Exception:
            faces_cache = {}

    # Cargar base de datos Apple
    apple_db = load_apple_db()
    existing_basenames = {os.path.basename(p).lower() for p in apple_db}

    # Escanear archivos en iCloud Photos
    if not ICLOUD_PHOTOS_DIR.exists():
        with _SYNC_LOCK:
            _SYNC_STATE["last_error"] = f"No existe la carpeta de iCloud: {ICLOUD_PHOTOS_DIR}"
            _SYNC_STATE["running"] = False
            _SYNC_STATE["status"] = "error"
            _save_progress_file()
        return

    valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov"}
    try:
        all_icloud = [f for f in os.listdir(ICLOUD_PHOTOS_DIR) if os.path.splitext(f)[1].lower() in valid_exts]
    except Exception as e:
        with _SYNC_LOCK:
            _SYNC_STATE["last_error"] = f"Error listando iCloud: {e}"
            _SYNC_STATE["running"] = False
            _SYNC_STATE["status"] = "error"
            _save_progress_file()
        return

    # Filtrar solo las pendientes
    pending_files = [f for f in all_icloud if f.lower() not in existing_basenames]

    # Identificar el número más alto de 'Persona Nueva #...'
    highest_new_person = 0
    persona_re = re.compile(r'Persona Nueva #(\d+)', re.I)
    for cat_tup in centroids.keys():
        if isinstance(cat_tup, tuple) and len(cat_tup) == 2:
            m = persona_re.search(cat_tup[1])
            if m:
                highest_new_person = max(highest_new_person, int(m.group(1)))
    for p_info in apple_db.values():
        ident = p_info.get("identity", "")
        m = persona_re.search(ident)
        if m:
            highest_new_person = max(highest_new_person, int(m.group(1)))

    with _SYNC_LOCK:
        _SYNC_STATE["total_icloud"] = len(all_icloud)
        _SYNC_STATE["already_processed"] = len(existing_basenames)
        _SYNC_STATE["pending_in_cloud"] = len(pending_files)
        _SYNC_STATE["status"] = "running"
        _SYNC_STATE["started_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _save_progress_file()

    processed_counter = 0
    screenshot_re = re.compile(r'^(screenshot|screen|captura)[-_]?(19|20)?', re.I)

    for fname in pending_files:
        if _STOP_REQUESTED.is_set():
            break

        abs_p = str(ICLOUD_PHOTOS_DIR / fname)
        with _SYNC_LOCK:
            _SYNC_STATE["current_file"] = fname

        is_vid = fname.lower().endswith(('.mp4', '.mov', '.avi'))
        try:
            if is_vid:
                cap = cv2.VideoCapture(abs_p)
                ret, frame = cap.read()
                cap.release()
                img = frame if (ret and frame is not None) else None
            else:
                img = cv2.imread(abs_p)
                if img is None:
                    time.sleep(1.2)
                    img = cv2.imread(abs_p)
                if img is None:
                    from PIL import Image
                    with Image.open(abs_p) as pil_img:
                        img = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)
        except Exception:
            img = None

        if img is None:
            continue

        try:
            h, w = img.shape[:2]
            
            # 2. Generar miniatura WebP (~20-25 KB) para carga instantánea
            generate_thumbnail(abs_p, max_size=320)

            # 3. Detección y reconocimiento facial
            det.setInputSize((w, h))
            _, raw_faces = det.detect(img)
            
            detected_faces = []
            assigned_cat = "📋 Revisión / Por Organizar"
            assigned_ident = "📷 Fotos Sin Rostro"
            photo_status = "Clasificado"

            if raw_faces is not None and len(raw_faces) > 0:
                best_photo_match_sim = -1.0
                best_photo_match_tuple = None

                for face in raw_faces:
                    # Validar landmarks
                    if len(face) < 14: continue
                    box = [float(face[0]), float(face[1]), float(face[2]), float(face[3])]
                    aligned = rec.alignCrop(img, face)
                    feat = rec.feature(aligned).flatten()
                    norm_feat = feat / (np.linalg.norm(feat) + 1e-10)

                    # Comparar con centroides conocidos
                    best_sim = -1.0
                    best_ident_tup = None
                    for id_tup, c_vec in centroids.items():
                        norm_c = c_vec.flatten() / (np.linalg.norm(c_vec) + 1e-10)
                        sim = float(np.dot(norm_feat, norm_c))
                        if sim > best_sim:
                            best_sim = sim
                            best_ident_tup = id_tup

                    face_identity = "Desconocido"
                    face_confidence = 0.0

                    if best_ident_tup and best_sim >= 0.58:
                        face_identity = best_ident_tup[1]
                        face_confidence = round(best_sim * 100, 1)
                        if best_sim > best_photo_match_sim:
                            best_photo_match_sim = best_sim
                            best_photo_match_tuple = best_ident_tup
                    elif best_ident_tup and best_sim >= 0.46:
                        face_identity = f"IA (Pendiente): {best_ident_tup[1]}"
                        face_confidence = round(best_sim * 100, 1)
                        if best_sim > best_photo_match_sim:
                            best_photo_match_sim = best_sim
                            best_photo_match_tuple = ("📋 Revisión / Por Organizar", best_ident_tup[1])
                            photo_status = "Dudoso"
                    else:
                        # Cara desconocida: buscar si coincide con una 'Persona Nueva #...' ya registrada
                        matched_new_person = None
                        new_person_sim = -1.0
                        for id_tup, c_vec in centroids.items():
                            if isinstance(id_tup, tuple) and "Persona Nueva" in id_tup[1]:
                                norm_c = c_vec.flatten() / (np.linalg.norm(c_vec) + 1e-10)
                                sim = float(np.dot(norm_feat, norm_c))
                                if sim > new_person_sim:
                                    new_person_sim = sim
                                    matched_new_person = id_tup

                        if matched_new_person and new_person_sim >= 0.52:
                            face_identity = matched_new_person[1]
                            face_confidence = round(new_person_sim * 100, 1)
                            if new_person_sim > best_photo_match_sim:
                                best_photo_match_sim = new_person_sim
                                best_photo_match_tuple = matched_new_person
                        else:
                            # Crear nueva Persona Nueva
                            highest_new_person += 1
                            new_name = f"Persona Nueva #{highest_new_person}"
                            centroids[("📋 Revisión / Por Organizar", new_name)] = norm_feat
                            face_identity = new_name
                            face_confidence = 100.0
                            if best_photo_match_sim < 0:
                                best_photo_match_sim = 0.50
                                best_photo_match_tuple = ("📋 Revisión / Por Organizar", new_name)

                    detected_faces.append({
                        "x": box[0],
                        "y": box[1],
                        "width": box[2],
                        "height": box[3],
                        "box": box,
                        "identity": face_identity,
                        "confidence": face_confidence,
                        "feature": feat.tolist(),
                        "img_width": w,
                        "img_height": h
                    })

                # Asignación de carpeta para la foto
                if best_photo_match_tuple:
                    assigned_cat = best_photo_match_tuple[0]
                    assigned_ident = best_photo_match_tuple[1]
                else:
                    assigned_cat = "📋 Revisión / Por Organizar"
                    assigned_ident = "❓ Desconocidos (Por Identificar)"
            else:
                # Sin caras detectadas
                if screenshot_re.search(fname):
                    assigned_cat = "Publicaciones_Instagram"
                    assigned_ident = "Capturas"
                else:
                    assigned_cat = "📋 Revisión / Por Organizar"
                    assigned_ident = "📷 Fotos Sin Rostro"

            # 4. Guardar en apple_db con supervisión IA activa en tiempo real (100% de fotos)
            entry = {
                "category": assigned_cat,
                "identity": assigned_ident,
                "cloud_source": "icloud",
                "is_virtual": True,
                "dehydrated": True,
                "status": photo_status,
                "num_faces": len(detected_faces),
                "faces": detected_faces,
                "mtime": os.path.getmtime(abs_p) if os.path.exists(abs_p) else time.time()
            }
            try:
                from app.services.supervisor_service import supervise_and_adapt_decision
                mod, _ = supervise_and_adapt_decision(abs_p, entry, centroids)
                if mod:
                    assigned_cat = entry["category"]
                    assigned_ident = entry["identity"]
                    photo_status = entry["status"]
            except Exception:
                pass

            apple_db[abs_p] = entry
            if detected_faces:
                faces_cache[abs_p] = detected_faces

            # 5. Deshidratar inmediatamente para dejar 0 KB en disco
            _dehydrate_cloud_file(abs_p)

            # 6. Crear acceso directo virtual en Resultados con la categoría supervisada
            _create_windows_url_shortcut(abs_p, assigned_cat, assigned_ident)

            # 7. Actualizar telemetría en memoria
            processed_counter += 1
            elapsed = time.time() - t_start
            rate = processed_counter / max(1.0, elapsed)
            remaining = len(pending_files) - processed_counter
            eta = (remaining / max(0.01, rate)) / 60.0

            with _SYNC_LOCK:
                _SYNC_STATE["processed_this_run"] = processed_counter
                _SYNC_STATE["already_processed"] = len(existing_basenames) + processed_counter
                _SYNC_STATE["pending_in_cloud"] = remaining
                _SYNC_STATE["current_identity"] = f"{assigned_cat} / {assigned_ident}"
                _SYNC_STATE["dehydrated_count"] += 1
                if assigned_cat not in ("📋 Revisión / Por Organizar", "Publicaciones_Instagram"):
                    _SYNC_STATE["known_assigned"] += 1
                elif "Persona Nueva" in assigned_ident:
                    _SYNC_STATE["new_persons_assigned"] += 1
                elif photo_status == "Dudoso":
                    _SYNC_STATE["dudosos_assigned"] += 1
                elif "Sin Rostro" in assigned_ident:
                    _SYNC_STATE["sin_rostro_assigned"] += 1

                _SYNC_STATE["rate_per_sec"] = round(rate, 2)
                _SYNC_STATE["elapsed_sec"] = round(elapsed, 1)
                _SYNC_STATE["eta_minutes"] = round(eta, 1)

            # Guardado periódico a disco cada 10 fotos y auditoría de decisiones por el Supervisor IA
            if processed_counter % 10 == 0:
                save_apple_db()
                try:
                    with open(CENTROIDS_FILE, "wb") as cf:
                        pickle.dump(centroids, cf)
                    with open(FACES_CACHE_FILE, "wb") as ff:
                        pickle.dump(faces_cache, ff)
                except Exception:
                    pass
                _save_progress_file()
                set_gallery_cache(None) # Invalidar para que aparezcan en tiempo real
                gc.collect()

                # Auditoría periódica cada 20 fotos
                if processed_counter % 20 == 0:
                    try:
                        from app.services.supervisor_service import audit_recent_decisions
                        audit_recent_decisions(n=30)
                    except Exception as e_sup:
                        pass

            # Pausa suave de 50ms para mantener uso de CPU < 8%
            time.sleep(0.05)

        except Exception as e:
            with _SYNC_LOCK:
                _SYNC_STATE["last_error"] = f"Error en {fname}: {e}"

    # Guardado final
    save_apple_db()
    try:
        with open(CENTROIDS_FILE, "wb") as cf:
            pickle.dump(centroids, cf)
        with open(FACES_CACHE_FILE, "wb") as ff:
            pickle.dump(faces_cache, ff)
    except Exception:
        pass
    
    set_gallery_cache(None)
    with _SYNC_LOCK:
        _SYNC_STATE["running"] = False
        _SYNC_STATE["status"] = "completed" if not _STOP_REQUESTED.is_set() else "stopped"
        _save_progress_file()

def start_icloud_sync(batch_size=None):
    global _SYNC_THREAD, _STOP_REQUESTED
    with _SYNC_LOCK:
        if _SYNC_STATE["running"] and _SYNC_THREAD and _SYNC_THREAD.is_alive():
            return {"status": "already_running", "state": dict(_SYNC_STATE)}
        
        _STOP_REQUESTED.clear()
        _SYNC_STATE["running"] = True
        _SYNC_STATE["status"] = "starting"
        _SYNC_STATE["last_error"] = None
        _save_progress_file()

    _SYNC_THREAD = threading.Thread(target=_run_icloud_worker, args=(batch_size,), daemon=True, name="iCloudVirtualSyncWorker")
    _SYNC_THREAD.start()
    return {"status": "started", "state": get_icloud_sync_status()}
