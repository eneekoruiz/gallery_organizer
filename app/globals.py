import os
from pathlib import Path
import pickle
import cv2
import threading
import json

BACKGROUND_TASKS_ENABLED = os.getenv('SMART_GALLERY_BACKGROUND_TASKS', '1') == '1'

# Lock for thread-safe cache reads/writes
cache_lock = threading.Lock()

# Rutas Principales
APP_DIR = Path(__file__).resolve().parent.parent
RESULTADOS_DIR = Path(os.getenv('GALLERY_RESULTADOS_DIR', r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados"))
FOTOS_DIR = Path(os.getenv('GALLERY_FOTOS_DIR', r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Fotos"))
CACHE_FILE = APP_DIR / "sface_cache_v7.pkl"
FACES_CACHE_FILE = APP_DIR / "faces_cache_v2.pkl"
PENDING_DELETIONS_FILE = APP_DIR / "pending_deletions.txt"
OVERRIDES_FILE = APP_DIR / "manual_overrides.json"
DHASH_CACHE_FILE = APP_DIR / "dhash_cache_v2.pkl"
CONFIDENCE_CACHE_FILE = APP_DIR / "confidence_cache.pkl"
THUMBNAILS_DIR = APP_DIR / ".thumbnails"
CONFIG_FILE = APP_DIR / "config.json"

if BACKGROUND_TASKS_ENABLED:
    THUMBNAILS_DIR.mkdir(exist_ok=True)

# ─── Gallery Cache (lightweight JSON, loaded eagerly) ───
_GALLERY_CACHE = None
GALLERY_CACHE_FILE = APP_DIR / "gallery_cache.json"
if GALLERY_CACHE_FILE.exists():
    try:
        with open(GALLERY_CACHE_FILE, 'r', encoding='utf-8') as f:
            _GALLERY_CACHE = json.load(f)
    except Exception:
        pass

_CONFIG_CACHE = None
STORAGE_MODE = 'local'

# ─── Heavy caches: deferred to background thread ───
faces_cache = {}
_DHASH_CACHE = {}
_CONFIDENCE_CACHE = {}

# ─── AI Models (Loaded eagerly in ~0.2s) ───
detector = None
recognizer = None
if BACKGROUND_TASKS_ENABLED:
    try:
        detector = cv2.FaceDetectorYN.create(
            str(APP_DIR / "models" / "face_detection_yunet.onnx"),
            "",
            (320, 320),
            0.35,
            0.3,
            5000
        )
        recognizer = cv2.FaceRecognizerSF.create(
            str(APP_DIR / "models" / "face_recognition_sface.onnx"),
            ""
        )
    except Exception as e:
        print(f"[BOOT] Error cargando modelos IA: {e}")
        detector = None
        recognizer = None

known_faces = {}

def get_detector():
    global detector
    return detector

def get_recognizer():
    global recognizer
    return recognizer

# ─── Boot readiness flag ───
_BOOT_READY = threading.Event()

def _load_heavy_caches():
    """Load all pickle caches and AI models in background thread.
    Server is already accepting HTTP requests while this runs."""
    global faces_cache, _DHASH_CACHE, _CONFIDENCE_CACHE
    global detector, recognizer, known_faces

    # 1. faces_cache (~29 MB pickle) — most critical
    if (APP_DIR / "faces_cache.pkl").exists():
        try:
            with open(APP_DIR / "faces_cache.pkl", 'rb') as f:
                faces_cache.update(pickle.load(f))
        except Exception:
            pass
    if FACES_CACHE_FILE.exists():
        try:
            with open(FACES_CACHE_FILE, 'rb') as f:
                faces_cache.update(pickle.load(f))
        except Exception:
            pass

    # 2. dHash cache (~2 MB)
    if DHASH_CACHE_FILE.exists():
        try:
            with open(DHASH_CACHE_FILE, 'rb') as f:
                _DHASH_CACHE.update(pickle.load(f))
        except Exception:
            pass

    # 3. Confidence cache (~113 KB)
    if CONFIDENCE_CACHE_FILE.exists():
        try:
            with open(CONFIDENCE_CACHE_FILE, 'rb') as f:
                _CONFIDENCE_CACHE.update(pickle.load(f))
        except Exception:
            pass

    # 4. AI Models already initialized eagerly at startup

    # 5. Known faces cache
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'rb') as f:
                cache_data = pickle.load(f)
                if isinstance(cache_data, list):
                    kf = {}
                    for item in cache_data:
                        kf[item['identidad']] = {'centroid': item['feature'], 'names': []}
                    known_faces.update(kf)
                elif isinstance(cache_data, dict):
                    known_faces.update(cache_data)
                    from app.services.face_learning import compute_appearance_centroids
                    for rec in known_faces.values():
                        if isinstance(rec, dict) and 'centroids' not in rec:
                            samples = list(rec.get('confirmed_samples', {}).values())
                            if samples:
                                rec['centroids'] = compute_appearance_centroids(samples)
                            elif rec.get('centroid') is not None:
                                rec['centroids'] = [rec['centroid']]
        except Exception:
            pass

    # Fallback to centroids.pkl when CACHE_FILE is empty (connects 406 identity brain)
    if not known_faces and (APP_DIR / "centroids.pkl").exists():
        try:
            with open(APP_DIR / "centroids.pkl", 'rb') as f:
                c_data = pickle.load(f)
                if isinstance(c_data, dict):
                    from app.services.face_learning import normalized_feature
                    for k, v in c_data.items():
                        ident_name = k[1] if isinstance(k, tuple) else str(k)
                        try:
                            v_norm = normalized_feature(v)
                            rec = {'centroid': v_norm, 'provenance': 'dataset_reference', 'names': [ident_name]}
                            known_faces[k] = rec
                            if ident_name not in known_faces:
                                known_faces[ident_name] = rec
                        except Exception:
                            pass
        except Exception as e:
            print(f"[BOOT] Error loading centroids.pkl fallback: {e}")

    _BOOT_READY.set()

# Start deferred loading immediately
if BACKGROUND_TASKS_ENABLED:
    threading.Thread(target=_load_heavy_caches, daemon=True, name="CacheLoader").start()
else:
    _BOOT_READY.set()

def wait_for_boot(timeout=30):
    """Block until heavy caches are loaded. Used by endpoints that need face data."""
    return _BOOT_READY.wait(timeout=timeout)

def set_gallery_cache(val):
    global _GALLERY_CACHE
    with cache_lock:
        _GALLERY_CACHE = val
        try:
            with open(GALLERY_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(val, f)
        except Exception as e:
            print(f'[CACHE] Error persisting gallery cache: {e}')

def get_gallery_cache():
    with cache_lock:
        return _GALLERY_CACHE

def clear_gallery_cache():
    global _GALLERY_CACHE
    with cache_lock:
        _GALLERY_CACHE = None
        try:
            if GALLERY_CACHE_FILE.exists():
                GALLERY_CACHE_FILE.unlink()
        except Exception as e:
            print(f'[CACHE] Error clearing gallery cache file: {e}')

_GALLERY_SCAN_PROGRESS = 0.0

def set_gallery_scan_progress(val):
    global _GALLERY_SCAN_PROGRESS
    _GALLERY_SCAN_PROGRESS = float(val)

def get_gallery_scan_progress():
    global _GALLERY_SCAN_PROGRESS
    return _GALLERY_SCAN_PROGRESS
