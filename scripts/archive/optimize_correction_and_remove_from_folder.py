import sys, re

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# 1. Update app.py
with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

# Fast Active Learning block inside apply_correction_to_file
old_al_block = """    # Active Learning
    if new_identidad not in ["Falso_Positivo", "Ignorar_Irrelevante"] and face_data:
        try:
            file_bytes = np.fromfile(str(orig_path), dtype=np.uint8)
            img_al = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img_al is not None:
                h_al, w_al, _ = img_al.shape
                detector.setInputSize((w_al, h_al))
                _, faces_al = detector.detect(img_al)
                if faces_al is not None:
                    for f in faces_al:
                        f_box = [int(f[0]), int(f[1]), int(f[2]), int(f[3])]
                        if iou(f_box, face_box) > 0.4:
                            aligned = recognizer.alignCrop(img_al, f)
                            feature = recognizer.feature(aligned)
                            dict_key = new_identidad
                            if dict_key in known_faces and 'centroid' in known_faces[dict_key]:
                                old_centroid = known_faces[dict_key]['centroid']
                                new_centroid = old_centroid * 0.85 + feature[0] * 0.15
                                new_centroid = new_centroid / np.linalg.norm(new_centroid)
                                known_faces[dict_key]['centroid'] = new_centroid
                            else:
                                known_faces[dict_key] = {'centroid': feature[0], 'names': [orig_path.name]}
                            with open(CACHE_FILE, 'wb') as cf:
                                pickle.dump(known_faces, cf)
                            break
        except Exception as e:
            print("AL Error:", e)"""

new_al_block = """    # Ultra-Fast Active Learning (Direct Crop Feature Extraction)
    if new_identidad not in ["Falso_Positivo", "Ignorar_Irrelevante"] and face_data:
        try:
            file_bytes = np.fromfile(str(orig_path), dtype=np.uint8)
            img_al = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img_al is not None:
                h_al, w_al, _ = img_al.shape
                x1 = max(0, int(face_data['x']))
                y1 = max(0, int(face_data['y']))
                x2 = min(w_al, x1 + int(face_data['width']))
                y2 = min(h_al, y1 + int(face_data['height']))
                
                if (x2 - x1) > 10 and (y2 - y1) > 10:
                    crop = img_al[y1:y2, x1:x2]
                    resized_crop = cv2.resize(crop, (112, 112))
                    feature = recognizer.feature(resized_crop)
                    dict_key = new_identidad
                    if dict_key in known_faces and 'centroid' in known_faces[dict_key]:
                        old_centroid = known_faces[dict_key]['centroid']
                        new_centroid = old_centroid * 0.85 + feature[0] * 0.15
                        new_centroid = new_centroid / np.linalg.norm(new_centroid)
                        known_faces[dict_key]['centroid'] = new_centroid
                    else:
                        known_faces[dict_key] = {'centroid': feature[0], 'names': [orig_path.name]}
                    with open(CACHE_FILE, 'wb') as cf:
                        pickle.dump(known_faces, cf)
        except Exception as e:
            print("AL Fast Error:", e)"""

if old_al_block in app_code:
    app_code = app_code.replace(old_al_block, new_al_block)
    print("✓ Replaced Active Learning with ultra-fast crop feature extraction!")

# Update remove_from_folder route in app.py
old_remove_route = """@app.route('/api/remove_from_folder', methods=['POST'])
def remove_from_folder():
    data = request.json
    filepath = data.get('path')
    cat = data.get('cat')
    ident = data.get('ident')
    
    if not filepath or not ident:
        return jsonify({"error": "Faltan parámetros"}), 400
        
    try:
        p_obj = Path(filepath)
        norm_path = str(p_obj)
        alt_path = norm_path.replace('\\\\', '/') if '\\\\' in norm_path else norm_path.replace('/', '\\\\')
        
        target_key = None
        if norm_path in faces_cache:
            target_key = norm_path
        elif alt_path in faces_cache:
            target_key = alt_path
        elif filepath in faces_cache:
            target_key = filepath
            
        if target_key:
            for face in faces_cache[target_key]:
                if face.get('identity') == ident or ident in str(face.get('identity', '')):
                    face['identity'] = 'Desconocida'
                    face['is_manual'] = True
            with open(FACES_CACHE_FILE, 'wb') as f:
                pickle.dump(faces_cache, f)
                
        if _GALLERY_CACHE and cat in _GALLERY_CACHE and ident in _GALLERY_CACHE[cat]:
            _GALLERY_CACHE[cat][ident] = [item for item in _GALLERY_CACHE[cat][ident] if Path(item['path']) != p_obj]
            
        if p_obj.exists():
            import shutil
            target_dir = Path('Resultados') / 'Desconocidos'
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / p_obj.name
            counter = 1
            while target_path.exists():
                target_path = target_dir / f"{p_obj.stem}_{counter}{p_obj.suffix}"
                counter += 1
            safe_move_file(p_obj, target_path)
            
            if target_key and target_key in faces_cache:
                faces_cache[str(target_path)] = faces_cache.pop(target_key)
                with open(FACES_CACHE_FILE, 'wb') as f:
                    pickle.dump(faces_cache, f)
                    
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500"""

new_remove_route = """@app.route('/api/remove_from_folder', methods=['POST'])
def remove_from_folder():
    data = request.json
    filepath = data.get('path')
    cat = data.get('cat')
    ident = data.get('ident')
    
    if not filepath or not ident:
        return jsonify({"error": "Faltan parámetros"}), 400
        
    try:
        p_obj = Path(filepath)
        
        # Save manual override to Desconocidos
        overrides = load_overrides()
        file_key = get_file_key(filepath)
        overrides[file_key] = [{
            'x': 0, 'y': 0, 'width': 0, 'height': 0,
            'identity': 'Desconocida'
        }]
        save_overrides(overrides)
        
        # Invalidate gallery cache
        global _GALLERY_CACHE
        _GALLERY_CACHE = None
        
        # Move physical file if in Resultados
        if p_obj.exists() and RESULTADOS_DIR in p_obj.parents:
            target_dir = RESULTADOS_DIR / 'Personas Sin Nombre' / 'Desconocidos'
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / p_obj.name
            if target_path.exists() and target_path != p_obj:
                target_path = target_dir / f"{p_obj.stem}_removed{p_obj.suffix}"
            try:
                shutil.move(str(p_obj), str(target_path))
            except Exception as me:
                print("Physical move error:", me)
                
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500"""

if old_remove_route in app_code:
    app_code = app_code.replace(old_remove_route, new_remove_route)
    print("✓ Updated remove_from_folder route in app.py!")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code)

# 2. Update removeFromFolder in templates/index.html
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

new_remove_js = """async function removeFromFolder() {
    releaseMediaElement();
    if (!currentFileObj || !currentFileObj.path || !currentCat || !currentIdent) return;
    const currentAnalysisPath = currentFileObj.path;
    if (!confirm(`¿Estás seguro de que quieres quitar esta foto de la carpeta de ${currentIdent}?`)) return;
    
    try {
        const res = await fetch('/api/remove_from_folder', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                path: currentAnalysisPath,
                cat: currentCat,
                ident: currentIdent
            })
        });
        const data = await res.json();
        
        if (data.success) {
            showToast("✅ Foto quitada de la carpeta correctamente.");
            closeLightbox();
            
            // Remove item from currentFolderItems and DOM
            if (typeof currentFolderItems !== 'undefined' && currentFolderItems) {
                currentFolderItems = currentFolderItems.filter(it => it.path !== currentAnalysisPath);
                if (fullGallery && fullGallery[currentCat] && fullGallery[currentCat][currentIdent]) {
                    fullGallery[currentCat][currentIdent] = fullGallery[currentCat][currentIdent].filter(it => it.path !== currentAnalysisPath);
                }
                const gridContainer = document.getElementById('grid-container');
                if (gridContainer && gridContainer.children[currentItemIndex]) {
                    gridContainer.children[currentItemIndex].remove();
                }
                const subEl = document.getElementById('gallery-subtitle');
                if (subEl) subEl.textContent = `${currentFolderItems.length} elementos`;
            }
            await loadGallery();
        } else {
            alert(data.error || "Error al quitar la foto");
        }
    } catch(e) {
        alert("Error de conexión");
    }
}"""

html = re.sub(r"async function removeFromFolder\(\) \{[\s\S]*?\n\}", new_remove_js, html)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("✓ Updated removeFromFolder in index.html!")
