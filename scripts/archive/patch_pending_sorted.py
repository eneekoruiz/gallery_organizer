import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace api_pending_sorted completely
old_code = """
def api_pending_sorted():
    global _GALLERY_CACHE, detector, recognizer, known_faces
    if _GALLERY_CACHE is None:
        load_gallery_cache()
        
    items_to_sort = []
    
    # Recoger solo fotos de Personas Sin Nombre
    if 'Personas Sin Nombre' in _GALLERY_CACHE:
        for ident, items in _GALLERY_CACHE['Personas Sin Nombre'].items():
            for item in items:
                items_to_sort.append(item)
                
    if 'Resultados' in _GALLERY_CACHE:
        for ident, items in _GALLERY_CACHE['Resultados'].items():
            for item in items:
                items_to_sort.append(item)
                
    # Extraer caras y calcular score para ordenarlos
    dirty = False
    for item in items_to_sort:
        time.sleep(0.02)  # Yield GIL to prevent UI blocking
        filepath = item['path']
        file_key = get_file_key(filepath)
        
        # Usamos cache si existe
        if file_key in _CONFIDENCE_CACHE:
            item['confidence'] = _CONFIDENCE_CACHE[file_key]
            continue
            
        max_conf = 0.0
        try:
            path_obj = Path(filepath)
            is_video = path_obj.suffix.lower() in [".mp4", ".mov", ".avi"]
            img = None
            if is_video:
                cap = cv2.VideoCapture(str(filepath))
                fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if fc > 10: cap.set(cv2.CAP_PROP_POS_FRAMES, fc // 2)
                ret, frame = cap.read()
                cap.release()
                if ret: img = frame
            else:
                file_bytes = np.fromfile(str(filepath), dtype=np.uint8)
                img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                
            if img is not None and detector is not None and recognizer is not None:
                h, w, _ = img.shape
                detector.setInputSize((w, h))
                _, faces = detector.detect(img)
                if faces is not None:
                    for face in faces:
                        aligned = recognizer.alignCrop(img, face)
                        feature = recognizer.feature(aligned)
                        
                        best_score = 0
                        for db_id, data_dict in known_faces.items():
                            centroid = data_dict.get('centroid')
                            if centroid is not None:
                                score = get_cosine_similarity(feature[0], centroid)
                                if score > best_score:
                                    best_score = score
                                    
                        if best_score > max_conf:
                            max_conf = best_score
        except Exception:
            pass
            
        item['confidence'] = max_conf
        _CONFIDENCE_CACHE[file_key] = max_conf
        dirty = True
        
        # Guardado incremental para no perder el progreso si tarda mucho
        if len(_CONFIDENCE_CACHE) % 10 == 0:
            save_confidence_cache()
            
    if dirty:
        save_confidence_cache()
        
    items_to_sort.sort(key=lambda x: x.get('confidence', 0.0), reverse=True)
    return jsonify({"items": items_to_sort})
"""

new_code = """
@app.route('/api/start_smart_clean', methods=['POST'])
def start_smart_clean():
    subprocess.Popen([sys.executable, "smart_clean_worker.py"])
    return jsonify({"success": True})

@app.route('/api/smart_clean_status')
def get_smart_clean_status():
    status_file = Path("smart_clean_status.json")
    if status_file.exists():
        with open(status_file, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify({"status": "Esperando...", "progress": 0})

def api_pending_sorted():
    global _GALLERY_CACHE
    if _GALLERY_CACHE is None:
        load_gallery_cache()
        
    items_to_sort = []
    
    if 'Personas Sin Nombre' in _GALLERY_CACHE:
        for ident, items in _GALLERY_CACHE['Personas Sin Nombre'].items():
            for item in items:
                items_to_sort.append(item)
                
    if 'Resultados' in _GALLERY_CACHE:
        for ident, items in _GALLERY_CACHE['Resultados'].items():
            for item in items:
                items_to_sort.append(item)
                
    # Solamente leer de la cache, NO calcular nada aqui. El script en background ya lo hizo.
    for item in items_to_sort:
        file_key = get_file_key(item['path'])
        item['confidence'] = _CONFIDENCE_CACHE.get(file_key, 0.0)
        
    items_to_sort.sort(key=lambda x: x.get('confidence', 0.0), reverse=True)
    return jsonify({"items": items_to_sort})
"""
if "def api_pending_sorted():" in content:
    # the function might not match old_code string exactly because I didn't grep the exact indents
    # Let's use re to replace it
    import re
    # We will just replace everything from "def api_pending_sorted():" up to "return jsonify({"items": items_to_sort})"
    pattern = re.compile(r"def api_pending_sorted\(\):.*?return jsonify\(\{[\"']items[\"']: items_to_sort\}\)", re.DOTALL)
    content = pattern.sub(new_code.strip(), content)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Replaced api_pending_sorted and added background endpoints")
else:
    print("Could not find api_pending_sorted")
