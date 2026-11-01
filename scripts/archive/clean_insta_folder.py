import os, cv2, pickle, shutil, json
import numpy as np
from pathlib import Path

BASE_DIR = Path(r'C:\Users\User\Desktop\Galeria Eneko NO ABRIR')
INSTA_DIR = BASE_DIR / 'Resultados' / 'Publicaciones_Instagram'
YO_DIR = BASE_DIR / 'Resultados' / 'YO' / 'YO'
YO_DIR.mkdir(parents=True, exist_ok=True)

detector = cv2.FaceDetectorYN.create("models/face_detection_yunet.onnx", "", (320, 320))
recognizer = cv2.FaceRecognizerSF.create("models/face_recognition_sface.onnx", "")

# Load sface_cache_v7.pkl for YO centroid
with open("sface_cache_v7.pkl", "rb") as f:
    known_faces = pickle.load(f)

yo_centroid = known_faces.get("YO", {}).get("centroid")

def get_sim(f1, f2):
    v1 = np.squeeze(f1)
    v2 = np.squeeze(f2)
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

restored_to_yo = 0
restored_to_unknown = 0

if INSTA_DIR.exists():
    insta_files = [os.path.join(r, f) for r, d, fs in os.walk(str(INSTA_DIR)) for f in fs if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    print(f"Auditing {len(insta_files)} files in Publicaciones_Instagram for faces...")
    
    for p in insta_files:
        try:
            fb = np.fromfile(p, dtype=np.uint8)
            img = cv2.imdecode(fb, cv2.IMREAD_COLOR)
            if img is None: continue
            h, w = img.shape[:2]
            detector.setInputSize((w, h))
            _, faces = detector.detect(img)
            
            # If it has faces, it is NOT a pure text/instagram quote!
            if faces is not None and len(faces) > 0:
                is_yo = False
                if yo_centroid is not None:
                    for face in faces:
                        crop = recognizer.alignCrop(img, face)
                        feat = recognizer.feature(crop)[0]
                        sim = get_sim(feat, yo_centroid)
                        if sim >= 0.60:
                            is_yo = True
                            break
                            
                src_p = Path(p)
                if is_yo or 'snapchat' in src_p.name.lower():
                    dst_p = YO_DIR / src_p.name
                    counter = 1
                    while dst_p.exists():
                        dst_p = YO_DIR / f"{src_p.stem}_{counter}{src_p.suffix}"
                        counter += 1
                    shutil.move(str(src_p), str(dst_p))
                    restored_to_yo += 1
                else:
                    # Move back to Personas Sin Nombre
                    dst_dir = BASE_DIR / 'Resultados' / 'Personas Sin Nombre' / 'Restauradas'
                    dst_dir.mkdir(parents=True, exist_ok=True)
                    dst_p = dst_dir / src_p.name
                    counter = 1
                    while dst_p.exists():
                        dst_p = dst_dir / f"{src_p.stem}_{counter}{src_p.suffix}"
                        counter += 1
                    shutil.move(str(src_p), str(dst_p))
                    restored_to_unknown += 1
        except Exception as e:
            pass

print(f"Restored {restored_to_yo} selfie/Snapchat photos to YO!")
print(f"Restored {restored_to_unknown} non-text photos to Personas Sin Nombre!")
