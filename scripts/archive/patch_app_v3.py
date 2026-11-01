import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

quality_code = """
def calculate_sharpness(filepath):
    try:
        path_obj = Path(filepath)
        if path_obj.suffix.lower() in [".mp4", ".mov", ".avi"]:
            cap = cv2.VideoCapture(str(filepath))
            fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if fc > 10: cap.set(cv2.CAP_PROP_POS_FRAMES, fc // 2)
            ret, frame = cap.read()
            cap.release()
            if not ret or frame is None: return 0.0
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            file_bytes = np.fromfile(str(filepath), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None: return 0.0
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return round(cv2.Laplacian(gray, cv2.CV_64F).var(), 1)
    except:
        return 0.0

def calculate_dhash(filepath):
    try:
        path_obj = Path(filepath)
        if path_obj.suffix.lower() in [".mp4", ".mov", ".avi"]:
            cap = cv2.VideoCapture(str(filepath))
            fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if fc > 10: cap.set(cv2.CAP_PROP_POS_FRAMES, fc // 2)
            ret, img = cap.read()
            cap.release()
            if not ret or img is None: return None
        else:
            file_bytes = np.fromfile(str(filepath), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None: return None
        resized = cv2.resize(img, (9, 8), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        return (gray[:, 1:] > gray[:, :-1]).flatten()
    except:
        return None

@app.route('/api/duplicates', methods=['POST'])
def api_duplicates():
    data = request.json
    filepath = data.get('path')
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "Not found"}), 404
        
    path_obj = Path(filepath)
    parent_dir = path_obj.parent
    
    current_sharpness = calculate_sharpness(filepath)
    current_hash = calculate_dhash(filepath)
    
    if current_hash is None:
        return jsonify({"sharpness": current_sharpness, "duplicate": None})
        
    valid_exts = {".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi"}
    duplicate_info = None
    
    for other_file in parent_dir.iterdir():
        if not other_file.is_file() or other_file.name == path_obj.name: continue
        if other_file.suffix.lower() not in valid_exts: continue
        
        other_hash = calculate_dhash(str(other_file))
        if other_hash is not None and len(other_hash) == len(current_hash):
            hamming_dist = np.count_nonzero(current_hash != other_hash)
            similarity = round((1.0 - (hamming_dist / len(current_hash))) * 100, 1)
            
            if similarity >= 85.0:
                other_sharpness = calculate_sharpness(str(other_file))
                is_better = current_sharpness >= other_sharpness
                duplicate_info = {
                    "other_name": other_file.name,
                    "other_path": str(other_file),
                    "similarity": similarity,
                    "other_sharpness": other_sharpness,
                    "is_current_better": is_better
                }
                break
                
    return jsonify({
        "sharpness": current_sharpness,
        "duplicate": duplicate_info
    })
"""

# Insert quality_code right before @app.route('/api/analyze')
idx = content.find("@app.route('/api/analyze'")
head = content[:idx]
new_content = head + quality_code + "\n\n" + content[idx:]

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("app.py actualizado con cálculo de nitidez e IA de duplicados.")
