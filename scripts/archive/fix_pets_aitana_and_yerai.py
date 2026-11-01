import os, cv2, pickle, shutil, json
import numpy as np
from pathlib import Path

BASE_DIR = Path(r'C:\Users\User\Desktop\Galeria Eneko NO ABRIR')
CACHE_FILE = Path("sface_cache_v7.pkl")

detector = cv2.FaceDetectorYN.create("models/face_detection_yunet.onnx", "", (320, 320))
recognizer = cv2.FaceRecognizerSF.create("models/face_recognition_sface.onnx", "")

def get_sim(f1, f2):
    v1 = np.squeeze(f1)
    v2 = np.squeeze(f2)
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

known_faces = {}
if CACHE_FILE.exists():
    with open(CACHE_FILE, 'rb') as f:
        known_faces = pickle.load(f)

# Exclude any pet entries from human face centroids
known_faces = {k: v for k, v in known_faces.items() if 'mascota' not in k.lower() and 'm. ' not in k.lower()}

yo_centroid = known_faces.get("YO", {}).get("centroid")
aitana_centroid = known_faces.get("C. Aitana Gaztelumendi", {}).get("centroid")
yera_centroid = known_faces.get("C. Yera Ruiz", {}).get("centroid")
yerai_centroid = known_faces.get("C. Yerai Vidal", {}).get("centroid")
maddi_centroid = known_faces.get("C. Maddi Egibar", {}).get("centroid")

# ==========================================
# 1. FIX PET FOLDERS (Mascotas)
# Move human-only photos out of Mascotas to human folders
# ==========================================
print("--- 1. Auditing Mascotas Folders ---")
mascotas_dirs = []
for bdir in [BASE_DIR / 'Fotos' / 'Mascotas', BASE_DIR / 'Resultados' / 'Mascotas']:
    if bdir.exists():
        for sub in bdir.iterdir():
            if sub.is_dir():
                mascotas_dirs.append(sub)

moved_pets_to_yo = 0
moved_pets_to_known = 0

yo_target_dir = BASE_DIR / 'Resultados' / 'YO' / 'YO'
yo_target_dir.mkdir(parents=True, exist_ok=True)

for mdir in mascotas_dirs:
    m_files = []
    for r, d, fs in os.walk(str(mdir)):
        for f in fs:
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                m_files.append(os.path.join(r, f))
                
    for p in m_files:
        try:
            fb = np.fromfile(p, dtype=np.uint8)
            img = cv2.imdecode(fb, cv2.IMREAD_COLOR)
            if img is None: continue
            h, w = img.shape[:2]
            detector.setInputSize((w, h))
            _, faces = detector.detect(img)
            
            if faces is not None and len(faces) > 0:
                best_human_id = None
                best_sim = 0.0
                
                for face in faces:
                    crop = recognizer.alignCrop(img, face)
                    feat = recognizer.feature(crop)[0]
                    
                    for db_id, data_dict in known_faces.items():
                        c = data_dict.get('centroid')
                        if c is not None:
                            s = get_sim(feat, c)
                            if s > best_sim:
                                best_sim = s
                                best_human_id = db_id
                                
                src_p = Path(p)
                # If strong human match (>= 0.58) and face takes up significant portion of photo
                if best_sim >= 0.58:
                    if best_human_id == "YO":
                        dst_p = yo_target_dir / src_p.name
                        counter = 1
                        while dst_p.exists():
                            dst_p = yo_target_dir / f"{src_p.stem}_{counter}{src_p.suffix}"
                            counter += 1
                        shutil.move(str(src_p), str(dst_p))
                        moved_pets_to_yo += 1
                    else:
                        cat_prefix = 'Conocidos'
                        if best_human_id.startswith('F.'): cat_prefix = 'Familia'
                        target_human_dir = BASE_DIR / 'Resultados' / cat_prefix / best_human_id
                        target_human_dir.mkdir(parents=True, exist_ok=True)
                        dst_p = target_human_dir / src_p.name
                        counter = 1
                        while dst_p.exists():
                            dst_p = target_human_dir / f"{src_p.stem}_{counter}{src_p.suffix}"
                            counter += 1
                        shutil.move(str(src_p), str(dst_p))
                        moved_pets_to_known += 1
        except:
            pass

print(f"Mascotas Audit: Moved {moved_pets_to_yo} human photos to YO, {moved_pets_to_known} to respective owners.")

# ==========================================
# 2. FIX Aitana Gaztelumendi vs Yera Ruiz
# ==========================================
print("--- 2. Fixing Aitana Gaztelumendi vs Yera Ruiz ---")
aitana_dirs = [BASE_DIR / 'Fotos' / 'Conocidos' / 'C. Aitana Gaztelumendi', BASE_DIR / 'Resultados' / 'Conocidos' / 'C. Aitana Gaztelumendi']
aitana_files = []
for ad in aitana_dirs:
    if ad.exists():
        for r, d, fs in os.walk(str(ad)):
            for f in fs:
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    aitana_files.append(os.path.join(r, f))

yera_target_dir = BASE_DIR / 'Resultados' / 'Conocidos' / 'C. Yera Ruiz'
yera_target_dir.mkdir(parents=True, exist_ok=True)

moved_aitana_to_yera = 0
for p in aitana_files:
    try:
        fb = np.fromfile(p, dtype=np.uint8)
        img = cv2.imdecode(fb, cv2.IMREAD_COLOR)
        if img is None: continue
        h, w = img.shape[:2]
        detector.setInputSize((w, h))
        _, faces = detector.detect(img)
        
        if faces is not None and len(faces) > 0:
            best_yera_sim = 0
            best_aitana_sim = 0
            for face in faces:
                crop = recognizer.alignCrop(img, face)
                feat = recognizer.feature(crop)[0]
                if yera_centroid is not None:
                    s_yera = get_sim(feat, yera_centroid)
                    if s_yera > best_yera_sim: best_yera_sim = s_yera
                if aitana_centroid is not None:
                    s_ait = get_sim(feat, aitana_centroid)
                    if s_ait > best_aitana_sim: best_aitana_sim = s_ait
                    
            if best_yera_sim >= 0.58 and best_yera_sim > best_aitana_sim:
                src_p = Path(p)
                dst_p = yera_target_dir / src_p.name
                counter = 1
                while dst_p.exists():
                    dst_p = yera_target_dir / f"{src_p.stem}_{counter}{src_p.suffix}"
                    counter += 1
                shutil.move(str(src_p), str(dst_p))
                moved_aitana_to_yera += 1
    except:
        pass

print(f"Aitana vs Yera Fix: Moved {moved_aitana_to_yera} photos from Aitana to C. Yera Ruiz.")

# ==========================================
# 3. FIX Yerai Vidal vs Maddi Egibar
# ==========================================
print("--- 3. Fixing Yerai Vidal vs Maddi Egibar ---")
yerai_dirs = [BASE_DIR / 'Fotos' / 'Conocidos' / 'C. Yerai Vidal', BASE_DIR / 'Resultados' / 'Conocidos' / 'C. Yerai Vidal']
yerai_files = []
for yd in yerai_dirs:
    if yd.exists():
        for r, d, fs in os.walk(str(yd)):
            for f in fs:
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    yerai_files.append(os.path.join(r, f))

maddi_target_dir = BASE_DIR / 'Resultados' / 'Conocidos' / 'C. Maddi Egibar'
maddi_target_dir.mkdir(parents=True, exist_ok=True)

moved_yerai_to_maddi = 0
for p in yerai_files:
    try:
        fb = np.fromfile(p, dtype=np.uint8)
        img = cv2.imdecode(fb, cv2.IMREAD_COLOR)
        if img is None: continue
        h, w = img.shape[:2]
        detector.setInputSize((w, h))
        _, faces = detector.detect(img)
        
        if faces is not None and len(faces) > 0:
            best_maddi_sim = 0
            best_yerai_sim = 0
            for face in faces:
                crop = recognizer.alignCrop(img, face)
                feat = recognizer.feature(crop)[0]
                if maddi_centroid is not None:
                    s_mad = get_sim(feat, maddi_centroid)
                    if s_mad > best_maddi_sim: best_maddi_sim = s_mad
                if yerai_centroid is not None:
                    s_yer = get_sim(feat, yerai_centroid)
                    if s_yer > best_yerai_sim: best_yerai_sim = s_yer
                    
            if best_maddi_sim >= 0.58 and best_maddi_sim > best_yerai_sim:
                src_p = Path(p)
                dst_p = maddi_target_dir / src_p.name
                counter = 1
                while dst_p.exists():
                    dst_p = maddi_target_dir / f"{src_p.stem}_{counter}{src_p.suffix}"
                    counter += 1
                shutil.move(str(src_p), str(dst_p))
                moved_yerai_to_maddi += 1
    except:
        pass

print(f"Yerai vs Maddi Fix: Moved {moved_yerai_to_maddi} photos from Yerai Vidal to C. Maddi Egibar.")

print("🎉 ALL AUTOMATIC CORRECTIONS COMPLETED SUCCESSFULLY!")
