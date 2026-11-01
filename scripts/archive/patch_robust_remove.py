import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_route = """@app.route('/api/remove_from_folder', methods=['POST'])
def remove_from_folder():
    data = request.json
    filepath = data.get('path')
    cat = data.get('cat')
    ident = data.get('ident')
    
    if not filepath or not ident:
        return jsonify({"error": "Faltan parámetros"}), 400
        
    try:
        if filepath in faces_cache:
            modified = False
            for face in faces_cache[filepath]:
                if face.get('identity') == ident:
                    face['identity'] = 'Desconocida'
                    face['is_manual'] = True
                    modified = True
            
            if modified:
                with open(FACES_CACHE_FILE, 'wb') as f:
                    pickle.dump(faces_cache, f)
                    
                # Remover de gallery cache en memoria
                if _GALLERY_CACHE and cat in _GALLERY_CACHE and ident in _GALLERY_CACHE[cat]:
                    _GALLERY_CACHE[cat][ident] = [item for item in _GALLERY_CACHE[cat][ident] if item['path'] != filepath]
                
                # Mover el archivo fisicamente si es posible
                import shutil
                try:
                    source_path = Path(filepath)
                    if source_path.exists():
                        target_dir = Path('Resultados') / 'Desconocidos'
                        target_dir.mkdir(parents=True, exist_ok=True)
                        target_path = target_dir / source_path.name
                        counter = 1
                        while target_path.exists():
                            target_path = target_dir / f"{source_path.stem}_{counter}{source_path.suffix}"
                            counter += 1
                        shutil.move(str(source_path), str(target_path))
                        
                        # Actualizar la key en faces_cache ya que el archivo se movió
                        faces_cache[str(target_path)] = faces_cache.pop(filepath)
                        with open(FACES_CACHE_FILE, 'wb') as f:
                            pickle.dump(faces_cache, f)
                except Exception as e:
                    print("Error moviendo fisicamente:", e)
                    
                return jsonify({"success": True})
        
        return jsonify({"error": "No se encontró la cara con esa identidad en la caché"}), 404
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500"""

new_route = """@app.route('/api/remove_from_folder', methods=['POST'])
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
            shutil.move(str(p_obj), str(target_path))
            
            if target_key and target_key in faces_cache:
                faces_cache[str(target_path)] = faces_cache.pop(target_key)
                with open(FACES_CACHE_FILE, 'wb') as f:
                    pickle.dump(faces_cache, f)
                    
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500"""

if old_route in content:
    content = content.replace(old_route, new_route)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Robust remove_from_folder route patched into app.py")
else:
    print("Could not find old_route")
