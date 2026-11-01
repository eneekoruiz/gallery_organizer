import os, cv2, pickle, shutil
import numpy as np
from pathlib import Path

base_dir = Path(r'C:\Users\User\Desktop\Galeria Eneko NO ABRIR')
target_insta_dir = base_dir / 'Resultados' / 'Publicaciones_Instagram'
target_insta_dir.mkdir(parents=True, exist_ok=True)

detector = cv2.FaceDetectorYN.create("models/face_detection_yunet.onnx", "", (320, 320))

# Scan files in Personas Sin Nombre, Desconocidos, and Screenshots without faces
files_to_scan = []
for root, dirs, files in os.walk(str(base_dir)):
    for f in files:
        f_lower = f.lower()
        if f_lower.endswith(('.jpg', '.jpeg', '.png')):
            full_p = os.path.join(root, f)
            # Match explicitly named screenshots or files in Personas Sin Nombre
            if 'screenshot' in f_lower or 'insta' in f_lower or 'story' in f_lower or 'quote' in f_lower or 'personas sin nombre' in root.lower():
                files_to_scan.append(full_p)

print(f"Candidates to check for Instagram/Text posts: {len(files_to_scan)}")

moved_count = 0
path_map = {}

for idx, p in enumerate(files_to_scan):
    if not os.path.exists(p): continue
    
    # Check if file has 0 faces
    try:
        fb = np.fromfile(p, dtype=np.uint8)
        img = cv2.imdecode(fb, cv2.IMREAD_COLOR)
        if img is None: continue
        h, w = img.shape[:2]
        detector.setInputSize((w, h))
        _, faces = detector.detect(img)
        
        num_faces = len(faces) if faces is not None else 0
        
        # If it has 0 faces and matches screenshot/text patterns or square/portrait ratio without faces
        is_insta_candidate = False
        f_name_lower = os.path.basename(p).lower()
        
        if num_faces == 0:
            if 'screenshot' in f_name_lower or 'insta' in f_name_lower or 'story' in f_name_lower or 'quote' in f_name_lower:
                is_insta_candidate = True
            elif 'personas sin nombre' in p.lower():
                # Aspect ratio check for Instagram posts (1:1 square or 4:5 portrait or 9:16 story)
                aspect = w / float(h)
                if 0.75 <= aspect <= 1.35 or 0.5 <= aspect <= 0.6:
                    is_insta_candidate = True
                    
        if is_insta_candidate:
            src = Path(p)
            dst = target_insta_dir / src.name
            counter = 1
            while dst.exists():
                dst = target_insta_dir / f"{src.stem}_{counter}{src.suffix}"
                counter += 1
                
            shutil.move(str(src), str(dst))
            moved_count += 1
            path_map[str(src)] = str(dst)
    except Exception as e:
        pass

print(f"Moved {moved_count} Instagram posts / text quotes / memes to 'Publicaciones_Instagram'.")

# Update faces_cache.pkl
cache_file = Path("faces_cache.pkl")
if cache_file.exists() and path_map:
    with open(cache_file, 'rb') as f:
        faces_cache = pickle.load(f)
    for old_p, new_p in path_map.items():
        if old_p in faces_cache:
            faces_cache[new_p] = faces_cache.pop(old_p)
    with open(cache_file, 'wb') as f:
        pickle.dump(faces_cache, f)
    print("Updated faces_cache.pkl")
