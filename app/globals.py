import os
from pathlib import Path
import pickle
import cv2
import threading
import json

BACKGROUND_TASKS_ENABLED = os.getenv('SMART_GALLERY_BACKGROUND_TASKS', '1') == '1'

# Lock for thread-safe cache reads/writes
cache_lock = threading.Lock()
# Lock for OpenCV DNN FaceDetectorYN thread-safety
detector_lock = threading.Lock()

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

    # Merge reference identities with the latest human confirmations.
    reload_known_faces()

    _BOOT_READY.set()

def reload_known_faces():
    """Load all reference people; human profiles take precedence without upgrading legacy evidence."""
    from app.services.face_learning import normalized_feature, compute_appearance_centroids
    from app.services.group_album_service import is_group_album

    references = {}
    centroid_file = APP_DIR / 'centroids.pkl'
    if centroid_file.exists():
        try:
            with centroid_file.open('rb') as file:
                for key, value in pickle.load(file).items():
                    if (not isinstance(key, tuple) or len(key) != 2 or
                            key[0] not in {'Conocidos', 'Familia', 'Familiares', 'YO', 'Profesores'} or
                            is_group_album(key[1])):
                        continue
                    try:
                        feature = normalized_feature(value)
                    except (TypeError, ValueError):
                        continue
                    record = references.setdefault(key[1], {'centroid': feature, 'centroids': [],
                        'names': [], 'cat': key[0], 'provenance': 'dataset_reference'})
                    record['centroids'].append(feature)
        except Exception as error:
            print(f'[RELOAD] Error loading reference centroids: {error}')
    profiles = {}
    if CACHE_FILE.exists():
        try:
            with CACHE_FILE.open('rb') as file:
                profiles = pickle.load(file)
            if isinstance(profiles, list):
                profiles = {item['identidad']: {'centroid': item['feature'], 'names': []} for item in profiles}
            if not isinstance(profiles, dict):
                raise ValueError('Invalid face profiles')
        except Exception as error:
            print(f'[RELOAD] Error reloading known_faces: {error}')
            return
    for key, value in profiles.items():
        identity = key[1] if isinstance(key, tuple) and len(key) == 2 else str(key)
        if not isinstance(value, dict) or is_group_album(identity):
            continue
        record = dict(value)
        if 'centroids' not in record:
            samples = list(record.get('confirmed_samples', {}).values())
            if samples:
                record['centroids'] = compute_appearance_centroids(samples)
            elif record.get('centroid') is not None:
                record['centroids'] = [record['centroid']]
        if identity in references:
            record.setdefault('cat', references[identity]['cat'])
        references[identity] = record
    known_faces.clear()
    known_faces.update(references)

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
    if val is not None:
        _GALLERY_CACHE = val
        def _bg_dump(data):
            try:
                import tempfile
                with tempfile.NamedTemporaryFile('w', dir=GALLERY_CACHE_FILE.parent, delete=False, encoding='utf-8') as tf:
                    json.dump(data, tf)
                    tname = tf.name
                os.replace(tname, GALLERY_CACHE_FILE)
            except Exception as e:
                try:
                    if 'tname' in locals() and os.path.exists(tname): os.remove(tname)
                except Exception: pass
        threading.Thread(target=_bg_dump, args=(val,), daemon=False).start()

def get_gallery_cache():
    global _GALLERY_CACHE
    if _GALLERY_CACHE is not None:
        return _GALLERY_CACHE
    if GALLERY_CACHE_FILE.exists():
        try:
            with open(GALLERY_CACHE_FILE, 'r', encoding='utf-8') as f:
                _GALLERY_CACHE = json.load(f)
                return _GALLERY_CACHE
        except Exception:
            pass
    return None

def clear_gallery_cache():
    global _GALLERY_CACHE
    _GALLERY_CACHE = None
    try:
        if GALLERY_CACHE_FILE.exists():
            GALLERY_CACHE_FILE.unlink()
    except Exception:
        pass

_GALLERY_SCAN_PROGRESS = 0.0

def set_gallery_scan_progress(val):
    global _GALLERY_SCAN_PROGRESS
    _GALLERY_SCAN_PROGRESS = float(val)

def get_gallery_scan_progress():
    global _GALLERY_SCAN_PROGRESS
    return _GALLERY_SCAN_PROGRESS
