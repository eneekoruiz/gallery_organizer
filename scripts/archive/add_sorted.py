import os

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

api_sorted_code = '''
CONFIDENCE_CACHE_FILE = Path("confidence_cache.pkl")
_CONFIDENCE_CACHE = {}
if CONFIDENCE_CACHE_FILE.exists():
    try:
        import pickle
        with open(CONFIDENCE_CACHE_FILE, 'rb') as f:
            _CONFIDENCE_CACHE = pickle.load(f)
    except: pass

def save_confidence_cache():
    try:
        import pickle
        with open(CONFIDENCE_CACHE_FILE, 'wb') as f:
            pickle.dump(_CONFIDENCE_CACHE, f)
    except: pass

@app.route('/api/pending_sorted')
def api_pending_sorted():
    global _GALLERY_CACHE, detector, recognizer, known_faces
    if _GALLERY_CACHE is None:
        return jsonify({"error": "La galería aún no se ha cargado"}), 400
        
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
        
    if dirty:
        save_confidence_cache()
        
    # Ordenar: Las MÁS confidentes (cerca de 1.0) primero (Fáciles), luego las menos (0.0)
    items_to_sort.sort(key=lambda x: x.get('confidence', 0.0), reverse=True)
    
    return jsonify({"items": items_to_sort})
'''

end_idx = content.find("if __name__ == '__main__':")
if end_idx != -1:
    content = content[:end_idx] + api_sorted_code + '\n' + content[end_idx:]
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added /api/pending_sorted to app.py")
else:
    print("Could not find main block")
