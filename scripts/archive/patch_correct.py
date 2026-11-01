import os

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_correct = """def api_correct():
    data = request.json
    filepath = data.get('path')
    new_categoria = data.get('new_categoria')
    new_identidad = data.get('new_identidad')
    face_data = data.get('face')
    apply_to_duplicates = data.get('apply_to_duplicates', False)
    
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
        
    files_to_process = [filepath]
    if apply_to_duplicates:
        try:
            current_hash = calculate_dhash(filepath)
            if current_hash is not None:
                parent_dir = Path(filepath).parent
                valid_exts = {".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi"}
                for other_file in parent_dir.iterdir():
                    if not other_file.is_file() or other_file.name == Path(filepath).name: continue
                    if other_file.suffix.lower() not in valid_exts: continue
                    other_hash = calculate_dhash(str(other_file))
                    if other_hash is not None and len(other_hash) == len(current_hash):
                        hamming_dist = np.count_nonzero(current_hash != other_hash)
                        similarity = round((1.0 - (hamming_dist / len(current_hash))) * 100, 1)
                        if similarity >= 75.0:
                            files_to_process.append(str(other_file))
        except Exception as e:
            print("Error finding duplicates:", e)
            
    final_target_path = None
    for current_filepath in files_to_process:
        target_path = apply_correction_to_file(current_filepath, new_categoria, new_identidad, face_data)
        if current_filepath == filepath:
            final_target_path = target_path
            
    clear_gallery_cache()
    process_pending_deletions()
    
    if final_target_path:
        return jsonify({"success": True, "new_path": str(final_target_path)})
    return jsonify({"success": True})"""

new_correct = """def api_correct():
    data = request.json
    filepath = data.get('path')
    new_categoria = data.get('new_categoria')
    new_identidad = data.get('new_identidad')
    face_data = data.get('face')
    apply_to_duplicates = data.get('apply_to_duplicates', False)
    
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
        
    files_to_process = [filepath]
    
    # Reaprendizaje Activo: Process identical duplicate bursts
    try:
        import json
        with open('duplicate_groups.json', 'r') as df:
            dup_data = json.load(df)
            
        abs_path = str(Path(filepath).resolve())
        if abs_path in dup_data:
            group_id = dup_data[abs_path]['group_id']
            for other_path_str, d_info in dup_data.items():
                if d_info['group_id'] == group_id and other_path_str != abs_path:
                    if os.path.exists(other_path_str):
                        files_to_process.append(other_path_str)
    except Exception as e:
        print("Error finding duplicates from json:", e)
            
    final_target_path = None
    global _GALLERY_CACHE
    
    for current_filepath in files_to_process:
        target_path = apply_correction_to_file(current_filepath, new_categoria, new_identidad, face_data)
        if target_path and _GALLERY_CACHE is not None:
            try:
                old_path_str = str(Path(current_filepath))
                removed_item = None
                
                # Buscamos el elemento antiguo y lo borramos de la categoría antigua
                for cat_key, idents in list(_GALLERY_CACHE.items()):
                    for ident_key, items in list(idents.items()):
                        for idx, it in enumerate(items):
                            if it['path'] == old_path_str:
                                removed_item = items.pop(idx)
                                break
                        if removed_item: break
                    if removed_item: break
                
                if removed_item:
                    removed_item['path'] = str(target_path)
                    removed_item['name'] = Path(target_path).name
                    if new_categoria != "Ignorar" and new_identidad not in ["Falso_Positivo", "Ignorar_Irrelevante"]:
                        dest_cat = new_categoria
                        if new_identidad.startswith("Persona Nueva"): dest_cat = "Personas Sin Nombre"
                        
                        if dest_cat not in _GALLERY_CACHE:
                            _GALLERY_CACHE[dest_cat] = {}
                        if new_identidad not in _GALLERY_CACHE[dest_cat]:
                            _GALLERY_CACHE[dest_cat][new_identidad] = []
                        _GALLERY_CACHE[dest_cat][new_identidad].append(removed_item)
            except Exception as e:
                print("Cache update error:", e)
                
        if current_filepath == filepath:
            final_target_path = target_path
            
    # clear_gallery_cache() # Ya no destruimos la caché entera, actualización en caliente
    process_pending_deletions()
    
    if final_target_path:
        return jsonify({"success": True, "new_path": str(final_target_path)})
    return jsonify({"success": True})"""

if old_correct in content:
    content = content.replace(old_correct, new_correct)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated api_correct logic successfully")
else:
    print("Failed to find old_correct logic!")
