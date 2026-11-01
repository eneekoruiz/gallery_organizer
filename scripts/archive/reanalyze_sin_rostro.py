import os
import sys
import pickle
import cv2
import shutil
import numpy as np
import urllib.request
import json
from pathlib import Path

# Config
BASE_DIR = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR")
RESULTADOS_DIR = BASE_DIR / "Resultados"
sin_rostro_dir = BASE_DIR / "Revision_Interactiva" / "Sin_Rostro"
videos_sin_rostro_dir = BASE_DIR / "Revision_Interactiva" / "Videos_Sin_Rostro"
model_dir = Path(r"c:\Users\User\Desktop\ENEKO\smart_gallery_app\models")
centroids_path = Path(r"c:\Users\User\Desktop\ENEKO\smart_gallery_app\centroids.pkl")
faces_cache_path = Path(r"c:\Users\User\Desktop\ENEKO\smart_gallery_app\faces_cache.pkl")
overrides_path = Path(r"c:\Users\User\Desktop\ENEKO\smart_gallery_app\manual_overrides.json")

def notify_clear_cache():
    try:
        req = urllib.request.Request(
            'http://127.0.0.1:5000/api/clear_cache',
            method='POST'
        )
        with urllib.request.urlopen(req) as response:
            pass
    except Exception as e:
        print("[HTTP] Failed to clear Flask memory cache:", e)

def get_cosine_similarity(f1, f2):
    v1 = np.squeeze(f1)
    v2 = np.squeeze(f2)
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-10))

def get_file_key(filepath):
    p = Path(filepath)
    if not p.exists():
        return f"{p.name}_0_0"
    st = p.stat()
    return f"{p.name}_{st.st_size}_{int(st.st_mtime)}"

def resolve_category(identity):
    if identity.startswith('F. ') or identity.startswith('F_'):
        return 'Familia'
    elif identity.startswith('M. ') or identity.startswith('M_'):
        return 'Mascotas'
    elif identity.startswith('P. ') or identity.startswith('P_'):
        return 'Profesores'
    elif identity == 'YO':
        return 'YO'
    return 'Conocidos'

# Load files
if not centroids_path.exists():
    print("centroids.pkl not found!")
    sys.exit(1)

with open(centroids_path, 'rb') as f:
    centroids = pickle.load(f)

faces_cache = {}
if faces_cache_path.exists():
    try:
        with open(faces_cache_path, 'rb') as f:
            faces_cache = pickle.load(f)
    except:
        pass

print(f"Loaded {len(centroids)} centroids and {len(faces_cache)} cached face files.")

# Create models
detector = cv2.FaceDetectorYN.create(
    str(model_dir / "face_detection_yunet.onnx"), 
    "", 
    (320, 320),
    0.45, # Face detection threshold
    0.3,
    5000
)
recognizer = cv2.FaceRecognizerSF.create(
    str(model_dir / "face_recognition_sface.onnx"), 
    ""
)

# Walk files
image_files = []
if sin_rostro_dir.exists():
    image_files = [f for f in sin_rostro_dir.iterdir() if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png']]

video_files = []
if videos_sin_rostro_dir.exists():
    video_files = [f for f in videos_sin_rostro_dir.iterdir() if f.is_file() and f.suffix.lower() in ['.mp4', '.mov', '.avi']]

print(f"Found {len(image_files)} images and {len(video_files)} videos in faceless folders.")

total_processed = 0
promoted = 0
unknowns = 0
cleared_count = 0

def save_state():
    try:
        with open(faces_cache_path, 'wb') as f_out:
            pickle.dump(faces_cache, f_out)
        notify_clear_cache()
    except Exception as se:
        print("Error saving faces cache:", se)

status_file = Path("reanalyze_status.json")

# Process Images
for idx, f in enumerate(image_files):
    total_processed += 1
    if idx % 10 == 0:
        print(f"Processing image {idx}/{len(image_files)}... Promoted: {promoted}, Unknowns: {unknowns}")
        with open(status_file, "w") as sf:
            json.dump({
                "status": "processing_images",
                "progress": f"{idx}/{len(image_files)}",
                "promoted": promoted,
                "unknowns": unknowns
            }, sf)
            
    try:
        file_bytes = np.fromfile(str(f), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is None: continue
        
        h, w = img.shape[:2]
        detector.setInputSize((w, h))
        _, faces = detector.detect(img)
        
        if faces is not None and len(faces) > 0:
            # We found faces!
            detected_faces = []
            best_score = 0
            best_match = None
            
            for f_idx, face in enumerate(faces):
                x, y, w_f, h_f = map(int, face[:4])
                conf = face[-1]
                
                # Check match
                aligned = recognizer.alignCrop(img, face)
                feat = recognizer.feature(aligned)[0]
                feat_norm = feat / (np.linalg.norm(feat) + 1e-10)
                
                face_best_score = 0
                face_best_match = None
                for key, cent in centroids.items():
                    cent_id = key[1] if isinstance(key, tuple) else key
                    cent_cat = key[0] if isinstance(key, tuple) else resolve_category(cent_id)
                    
                    score = get_cosine_similarity(feat_norm, cent)
                    if score > face_best_score:
                        face_best_score = score
                        face_best_match = (cent_cat, cent_id)
                        
                identity_name = "Desconocido"
                if face_best_score >= 0.58:
                    identity_name = face_best_match[1]
                    if face_best_score > best_score:
                        best_score = face_best_score
                        best_match = face_best_match
                        
                detected_faces.append({
                    "x": x, "y": y, "width": w_f, "height": h_f,
                    "identity": identity_name,
                    "confidence": f"{face_best_score*100:.1f}" if face_best_score > 0 else "0.0",
                    "is_manual": False
                })
                
            # Determine destination folder
            if best_score >= 0.58:
                cat_target, ident_target = best_match
                dest_dir = RESULTADOS_DIR / cat_target / ident_target
                promoted += 1
            else:
                dest_dir = RESULTADOS_DIR / 'Personas Sin Nombre' / 'Desconocidos'
                unknowns += 1
                
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / f.name
            if dest_path.exists() and dest_path != f:
                dest_path = dest_dir / f"recovered_{f.name}"
                
            # Move file
            shutil.move(str(f), str(dest_path))
            
            # Save faces metadata under the new path
            new_path_str = str(dest_path)
            faces_cache[new_path_str] = detected_faces
            
            # Clean old path if exists in cache
            old_path_str = str(f)
            if old_path_str in faces_cache:
                faces_cache.pop(old_path_str, None)
                
            cleared_count += 1
            if cleared_count % 15 == 0:
                save_state()
    except Exception as ex:
        print(f"Error processing image {f.name}: {ex}")

save_state()

# Process Videos
for idx, f in enumerate(video_files):
    total_processed += 1
    print(f"Processing video {idx}/{len(video_files)}: {f.name}")
    with open(status_file, "w") as sf:
        json.dump({
            "status": "processing_videos",
            "progress": f"{idx}/{len(video_files)}",
            "promoted": promoted,
            "unknowns": unknowns
        }, sf)
        
    try:
        cap = cv2.VideoCapture(str(f))
        if not cap.isOpened(): continue
        
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps
        
        # Sample frames every 2 seconds
        found_any_face = False
        best_score = 0
        best_match = None
        
        for sec in range(1, int(duration), 2):
            target_frame = int(sec * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ret, frame = cap.read()
            if not ret or frame is None: continue
            
            h, w = frame.shape[:2]
            detector.setInputSize((w, h))
            _, faces = detector.detect(frame)
            
            if faces is not None and len(faces) > 0:
                found_any_face = True
                
                # Check first face in the frame
                face = faces[0]
                aligned = recognizer.alignCrop(frame, face)
                feat = recognizer.feature(aligned)[0]
                feat_norm = feat / (np.linalg.norm(feat) + 1e-10)
                
                for key, cent in centroids.items():
                    cent_id = key[1] if isinstance(key, tuple) else key
                    cent_cat = key[0] if isinstance(key, tuple) else resolve_category(cent_id)
                    
                    score = get_cosine_similarity(feat_norm, cent)
                    if score > best_score:
                        best_score = score
                        best_match = (cent_cat, cent_id)
                        
        cap.release()
        
        if found_any_face:
            # We found faces in the video!
            if best_score >= 0.58:
                cat_target, ident_target = best_match
                dest_dir = RESULTADOS_DIR / cat_target / ident_target
                promoted += 1
                identity_name = ident_target
            else:
                dest_dir = RESULTADOS_DIR / 'Personas Sin Nombre' / 'Desconocidos'
                unknowns += 1
                identity_name = "Desconocido"
                
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_path = dest_dir / f.name
            if dest_path.exists() and dest_path != f:
                dest_path = dest_dir / f"recovered_{f.name}"
                
            # Move file
            shutil.move(str(f), str(dest_path))
            
            new_path_str = str(dest_path)
            # Default face box for videos
            faces_cache[new_path_str] = [{
                "x": 0, "y": 0, "width": 0, "height": 0,
                "identity": identity_name,
                "confidence": f"{best_score*100:.1f}" if best_score > 0 else "0.0",
                "is_manual": False
            }]
            
            old_path_str = str(f)
            if old_path_str in faces_cache:
                faces_cache.pop(old_path_str, None)
                
            save_state()
    except Exception as ex:
        print(f"Error processing video {f.name}: {ex}")

# Final save
save_state()
with open(status_file, "w") as sf:
    json.dump({
        "status": "completed",
        "total_images": len(image_files),
        "total_videos": len(video_files),
        "promoted": promoted,
        "unknowns": unknowns
    }, sf)

print(f"FINISHED! Promoted: {promoted}, Unknowns: {unknowns}")
