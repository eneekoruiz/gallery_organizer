import os
import hashlib
import re
import time
import json
import pickle
import threading
import tempfile
import subprocess
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from io import BytesIO
from pathlib import Path
import cv2
import numpy as np

from app.globals import APP_DIR, CACHE_FILE, RESULTADOS_DIR, cache_lock, set_gallery_cache
from app.services.face_learning import rank_known_identities
from app.services.content_analysis_service import content_sha256, model_version, load_analysis, save_analysis
from app.services.apple_service import load_apple_db, save_apple_db, ICLOUD_PHOTOS_DIR
from app.utils.files import generate_thumbnail
from app.services.supervisor_service import save_supervisor_state, supervise_and_adapt_decision

CENTROIDS_FILE = APP_DIR / "centroids.pkl"
PROGRESS_FILE = APP_DIR / "scratch" / "apple_progress.json"

_SYNC_LOCK = threading.Lock()
_SYNC_THREAD = None
_STOP_REQUESTED = threading.Event()

_SYNC_STATE = {
    "running": False,
    "total_icloud": 0,
    "already_processed": 0,
    "pending_in_cloud": 0,
    "processed_this_run": 0,
    "reused_analysis": 0,
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
        if not (_SYNC_THREAD and _SYNC_THREAD.is_alive()):
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
        result = subprocess.run(["attrib", "+U", "-P", str(filepath)], capture_output=True, timeout=5)
        return result.returncode == 0
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

def _icloud_read_priority(source):
    video = Path(source.name).suffix.lower() in {'.mp4', '.mov', '.avi'}
    try:
        info = source.stat(follow_symlinks=False)
    except OSError:
        return (int(video) * 2 + 1, float('inf'))
    recall = getattr(info, 'st_file_attributes', 0) & 0x441000
    return (int(video) * 2 + int(bool(recall)), info.st_size)


def _read_icloud_media(path):
    before = os.stat(path)
    revision = (before.st_size, before.st_mtime_ns)
    if Path(path).suffix.lower() in {".mp4", ".mov", ".avi"}:
        sha256 = content_sha256(path)
        cap = cv2.VideoCapture(path, cv2.CAP_FFMPEG, [
            cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 25000,
            cv2.CAP_PROP_READ_TIMEOUT_MSEC, 12000,
        ])
        try:
            ok, frame = cap.read()
            after = os.stat(path)
            if revision != (after.st_size, after.st_mtime_ns):
                raise OSError(f"File changed while reading: {path}")
            return (frame, sha256, revision) if ok and frame is not None else None
        finally:
            cap.release()

    data = np.fromfile(path, dtype=np.uint8)
    after = os.stat(path)
    if revision != (after.st_size, after.st_mtime_ns):
        raise OSError(f"File changed while reading: {path}")
    sha256 = hashlib.sha256(data).hexdigest()
    image = cv2.imdecode(data, cv2.IMREAD_COLOR) if data.size else None
    if image is None:
        from PIL import Image, ImageOps
        with Image.open(BytesIO(data.tobytes())) as photo:
            image = cv2.cvtColor(np.asarray(ImageOps.exif_transpose(photo).convert("RGB")), cv2.COLOR_RGB2BGR)
    return (image, sha256, revision) if image is not None else None


def _prefetch_icloud_media(paths, stop, workers=4):
    """Keep a small window of reads in flight while one consumer classifies."""
    paths = iter(paths)
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="iCloudRead") as executor:
        pending = {}

        def submit_next():
            if not stop.is_set() and (path := next(paths, None)) is not None:
                pending[executor.submit(_read_icloud_media, path)] = path

        for _ in range(workers):
            submit_next()
        try:
            while pending and not stop.is_set():
                ready, _ = wait(pending, timeout=0.5, return_when=FIRST_COMPLETED)
                for future in ready:
                    if stop.is_set():
                        return
                    path = pending.pop(future)
                    try:
                        image = future.result()
                    except (OSError, ValueError, cv2.error):
                        image = None
                    yield path, image
                    submit_next()
        finally:
            for future in pending:
                future.cancel()


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

    analysis_profile = "icloud-first-frame-v2:" + model_version(APP_DIR)
    centroids = {}
    new_centroids = {}
    centroid_mtime = None
    profile_mtime = None
    confirmed_profiles = {}

    def refresh_centroids():
        nonlocal centroid_mtime, centroids, profile_mtime, confirmed_profiles
        try:
            mtime = CENTROIDS_FILE.stat().st_mtime_ns
        except FileNotFoundError:
            return
        if mtime != centroid_mtime:
            with CENTROIDS_FILE.open("rb") as file:
                centroids = pickle.load(file)
            centroids.update(new_centroids)
            centroid_mtime = mtime
        current_profile_mtime = CACHE_FILE.stat().st_mtime_ns if CACHE_FILE.exists() else None
        if current_profile_mtime is not None and current_profile_mtime != profile_mtime:
            with CACHE_FILE.open("rb") as file:
                confirmed_profiles = pickle.load(file)
            if not isinstance(confirmed_profiles, dict):
                raise ValueError("Invalid confirmed identity profiles")
            profile_mtime = current_profile_mtime

    def save_new_centroids():
        if not new_centroids:
            return
        with cache_lock:
            refresh_centroids()
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(dir=CENTROIDS_FILE.parent, delete=False) as file:
                    temp_path = Path(file.name)
                    pickle.dump(centroids, file)
                os.replace(temp_path, CENTROIDS_FILE)
                new_centroids.clear()
            finally:
                if temp_path is not None:
                    temp_path.unlink(missing_ok=True)

    try:
        with cache_lock:
            refresh_centroids()
    except (OSError, EOFError, pickle.UnpicklingError) as error:
        with _SYNC_LOCK:
            _SYNC_STATE.update(running=False, status="error", last_error=f"Centroides: {error}")
            _save_progress_file()
        return

    apple_db = load_apple_db(strict=True)
    indexed_paths = {os.path.normcase(os.path.normpath(path)): entry for path, entry in apple_db.items()}

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
        with os.scandir(ICLOUD_PHOTOS_DIR) as entries:
            all_icloud = {entry.name: entry for entry in entries
                          if os.path.splitext(entry.name)[1].lower() in valid_exts}
    except Exception as e:
        with _SYNC_LOCK:
            _SYNC_STATE["last_error"] = f"Error listando iCloud: {e}"
            _SYNC_STATE["running"] = False
            _SYNC_STATE["status"] = "error"
            _save_progress_file()
        return

    # Legacy records retain their mappings; changed files are queued again.
    pending_files = []
    for name, source in all_icloud.items():
        previous = indexed_paths.get(os.path.normcase(os.path.normpath(source.path)))
        if previous is None:
            pending_files.append(name)
            continue
        try:
            info = source.stat(follow_symlinks=False)
        except OSError:
            pending_files.append(name)
            continue
        changed = (previous.get("mtime_ns") != info.st_mtime_ns
                   if "mtime_ns" in previous else previous.get("mtime") != info.st_mtime)
        if (changed or previous.get("size", info.st_size) != info.st_size
                or previous.get("analysis_profile", analysis_profile) != analysis_profile):
            pending_files.append(name)
    pending_files.sort(key=lambda name: _icloud_read_priority(all_icloud[name]))
    total_pending = len(pending_files)
    already_processed = len(all_icloud) - total_pending
    if batch_size is not None:
        pending_files = pending_files[:batch_size]

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
        _SYNC_STATE["already_processed"] = already_processed
        _SYNC_STATE["pending_in_cloud"] = total_pending
        _SYNC_STATE["status"] = "running"
        _SYNC_STATE["started_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _save_progress_file()

    processed_counter = 0
    screenshot_re = re.compile(r'^(screenshot|screen|captura)[-_]?(19|20)?', re.I)

    paths = (str(ICLOUD_PHOTOS_DIR / name) for name in pending_files)
    for abs_p, media in _prefetch_icloud_media(paths, _STOP_REQUESTED):
        fname = os.path.basename(abs_p)
        with _SYNC_LOCK:
            _SYNC_STATE["current_file"] = fname

        if media is None:
            with _SYNC_LOCK:
                _SYNC_STATE["last_error"] = f"No se pudo leer {fname}"
            continue

        try:
            img, sha256, revision = media
            h, w = img.shape[:2]
            
            # 2. Generar miniatura WebP (~20-25 KB) para carga instantánea
            preview = generate_thumbnail(abs_p, max_size=320, decoded_image=img)

            # Reuse detections and embeddings; classify with the current identity profiles.
            cached_analysis = load_analysis(abs_p, sha256, analysis_profile)
            analysis_reused = cached_analysis is not None
            if cached_analysis is None:
                scale = min(1.0, 1024 / max(w, h))
                det_w = max(160, int(w * scale) // 32 * 32)
                det_h = max(160, int(h * scale) // 32 * 32)
                det.setInputSize((det_w, det_h))
                _, raw_faces = det.detect(cv2.resize(img, (det_w, det_h)))
                extracted = []
                if raw_faces is not None:
                    raw_faces[:, :14:2] *= w / det_w
                    raw_faces[:, 1:14:2] *= h / det_h
                    for face in raw_faces:
                        if len(face) < 15:
                            continue
                        feat = rec.feature(rec.alignCrop(img, face)).flatten()
                        extracted.append({"landmarks": face.tolist(), "feature": feat.tolist()})
                cached_analysis = {"faces": extracted}
                save_analysis(sha256, analysis_profile, cached_analysis)
            extracted = cached_analysis["faces"]

            detected_faces = []
            assigned_cat = "📋 Revisión / Por Organizar"
            assigned_ident = "📷 Fotos Sin Rostro"
            photo_status = "Clasificado"

            if extracted:
                with cache_lock:
                    refresh_centroids()
                    profiles = dict(confirmed_profiles)
                best_photo_match_sim = -1.0
                best_photo_match_tuple = None

                for cached_face in extracted:
                    face = np.asarray(cached_face["landmarks"], dtype=np.float32)
                    box = [float(face[0]), float(face[1]), float(face[2]), float(face[3])]
                    feat = np.asarray(cached_face["feature"], dtype=np.float32)
                    norm_feat = feat / (np.linalg.norm(feat) + 1e-10)

                    ranked = rank_known_identities(norm_feat, centroids, profiles)
                    best_sim, best_ident_tup = ranked[0] if ranked else (-1.0, None)
                    margin = best_sim - ranked[1][0] if len(ranked) > 1 else float("inf")

                    face_identity = "Desconocido"
                    face_confidence = 0.0

                    if best_ident_tup and best_sim >= 0.65 and margin >= 0.08:
                        face_identity = best_ident_tup[1]
                        face_confidence = round(best_sim * 100, 1)
                        if best_sim > best_photo_match_sim:
                            best_photo_match_sim = best_sim
                            best_photo_match_tuple = best_ident_tup
                            photo_status = "Clasificado"
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
                            new_key = ("📋 Revisión / Por Organizar", new_name)
                            new_centroids[new_key] = norm_feat
                            centroids[new_key] = norm_feat
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
                "content_sha256": sha256,
                "analysis_profile": analysis_profile,
                "category": assigned_cat,
                "identity": assigned_ident,
                "cloud_source": "icloud",
                "is_virtual": True,
                "dehydrated": False,
                "status": photo_status,
                "num_faces": len(detected_faces),
                "faces": detected_faces,
                "size": revision[0],
                "mtime_ns": revision[1],
                "mtime": revision[1] / 1e9
            }
            supervise_and_adapt_decision(abs_p, entry, centroids, learn=False)
            assigned_cat = entry["category"]
            assigned_ident = entry["identity"]
            photo_status = entry["status"]

            current = os.stat(abs_p)
            if revision != (current.st_size, current.st_mtime_ns):
                raise OSError(f"File changed during classification: {abs_p}")
            apple_db[abs_p] = entry

            # 5. Deshidratar inmediatamente para dejar 0 KB en disco
            if preview:
                entry["dehydrated"] = _dehydrate_cloud_file(abs_p)

            # 6. Crear acceso directo virtual en Resultados con la categoría supervisada
            _create_windows_url_shortcut(abs_p, assigned_cat, assigned_ident)

            # 7. Actualizar telemetría en memoria
            processed_counter += 1
            elapsed = time.time() - t_start
            rate = processed_counter / max(1.0, elapsed)
            remaining = total_pending - processed_counter
            eta = (remaining / max(0.01, rate)) / 60.0

            with _SYNC_LOCK:
                _SYNC_STATE["processed_this_run"] = processed_counter
                _SYNC_STATE["reused_analysis"] += int(analysis_reused)
                _SYNC_STATE["already_processed"] = already_processed + processed_counter
                _SYNC_STATE["pending_in_cloud"] = remaining
                _SYNC_STATE["current_identity"] = f"{assigned_cat} / {assigned_ident}"
                _SYNC_STATE["dehydrated_count"] += int(entry["dehydrated"])
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
                save_new_centroids()
                save_apple_db()
                _save_progress_file()
                set_gallery_cache(None) # Invalidar para que aparezcan en tiempo real

                save_supervisor_state()


        except Exception as e:
            with _SYNC_LOCK:
                _SYNC_STATE["last_error"] = f"Error en {fname}: {e}"

    # Guardado final
    save_new_centroids()
    save_apple_db()
    save_supervisor_state()
    
    set_gallery_cache(None)
    with _SYNC_LOCK:
        _SYNC_STATE["running"] = False
        _SYNC_STATE["status"] = "stopped" if _STOP_REQUESTED.is_set() else (
            "incomplete" if processed_counter < total_pending else "completed"
        )
        _save_progress_file()

def _run_icloud_sync(batch_size):
    try:
        _run_icloud_worker(batch_size)
    except Exception as error:
        with _SYNC_LOCK:
            _SYNC_STATE.update(running=False, status="error", last_error=str(error))
            _save_progress_file()


def start_icloud_sync(batch_size=None):
    global _SYNC_THREAD, _STOP_REQUESTED
    with _SYNC_LOCK:
        if _SYNC_THREAD and _SYNC_THREAD.is_alive():
            return {"status": "already_running", "state": dict(_SYNC_STATE)}
        
        _STOP_REQUESTED.clear()
        _SYNC_STATE["running"] = True
        for key in ("processed_this_run", "reused_analysis", "known_assigned", "dudosos_assigned",
                    "new_persons_assigned", "sin_rostro_assigned", "dehydrated_count",
                    "rate_per_sec", "elapsed_sec", "eta_minutes"):
            _SYNC_STATE[key] = 0
        _SYNC_STATE["current_file"] = None
        _SYNC_STATE["current_identity"] = None
        _SYNC_STATE["status"] = "starting"
        _SYNC_STATE["last_error"] = None
        _save_progress_file()

        _SYNC_THREAD = threading.Thread(target=_run_icloud_sync, args=(batch_size,), daemon=True, name="iCloudVirtualSyncWorker")
        _SYNC_THREAD.start()
    return {"status": "started", "state": get_icloud_sync_status()}
