from pathlib import Path
import cv2
import pickle

RESULTADOS_DIR = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados")
FOTOS_DIR = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Fotos")
APP_DIR = Path(__file__).resolve().parent.parent.parent
CACHE_FILE = APP_DIR / "sface_cache_v7.pkl"
FACES_CACHE_FILE = APP_DIR / "faces_cache.pkl"

faces_cache = {}
if FACES_CACHE_FILE.exists():
    try:
        with open(FACES_CACHE_FILE, 'rb') as f:
            faces_cache = pickle.load(f)
    except:
        faces_cache = {}

try:
    detector = cv2.FaceDetectorYN.create(
        str(APP_DIR / "models" / "face_detection_yunet.onnx"), 
        "", 
        (320, 320),
        0.70,
        0.3,
        5000
    )
    recognizer = cv2.FaceRecognizerSF.create(
        str(APP_DIR / "models" / "face_recognition_sface.onnx"), 
        ""
    )
    with open(CACHE_FILE, 'rb') as f:
        known_faces = pickle.load(f)
except Exception as e:
    print(f"Error cargando IA: {e}")
    detector = None
    recognizer = None
    known_faces = {}

_GALLERY_CACHE = None
_CONFIG_CACHE = None
STORAGE_MODE = 'local'
PENDING_DELETIONS_FILE = APP_DIR / "pending_deletions.txt"

def clear_gallery_cache():
    global _GALLERY_CACHE
    _GALLERY_CACHE = None
