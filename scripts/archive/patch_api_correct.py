import re
import os

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

start_idx = content.find('def api_correct():')
end_idx = content.find('@app.route(\'/api/delete_group\', methods=[\'POST\'])')

helper_func = '''
def apply_correction_to_file(filepath, new_categoria, new_identidad, face_data):
    if not filepath or not os.path.exists(filepath):
        return None
    orig_path = Path(filepath)
    is_manual_source = False
    try:
        if orig_path.is_relative_to(FOTOS_DIR):
            is_manual_source = True
    except ValueError:
        pass
        
    overrides = load_overrides()
    file_key = get_file_key(filepath)
    
    # Memoria Absoluta Guardado
    if face_data:
        if file_key not in overrides: overrides[file_key] = []
        updated = False
        face_box = [face_data['x'], face_data['y'], face_data['width'], face_data['height']]
        for ov in overrides[file_key]:
            ov_box = [ov['x'], ov['y'], ov['width'], ov['height']]
            if iou(face_box, ov_box) > 0.4:
                ov['identity'] = new_identidad
                ov['x'] = face_data['x']
                ov['y'] = face_data['y']
                ov['width'] = face_data['width']
                ov['height'] = face_data['height']
                updated = True
                break
        if not updated:
            overrides[file_key].append({
                'x': face_data['x'], 'y': face_data['y'], 
                'width': face_data['width'], 'height': face_data['height'],
                'identity': new_identidad
            })
        save_overrides(overrides)
        
    # Active Learning
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
            print("AL Error:", e)

    # File Management
    target_path = orig_path
    if new_categoria != "Ignorar" and new_identidad not in ["Falso_Positivo", "Ignorar_Irrelevante"]:
        if is_manual_source:
            target_dir = FOTOS_DIR / new_categoria / new_identidad
        else:
            target_dir = RESULTADOS_DIR / new_categoria / new_identidad
            
        target_dir.mkdir(parents=True, exist_ok=True)
        
        if orig_path.parent.resolve() == target_dir.resolve():
            target_path = orig_path
        else:
            orig_ino = os.stat(str(orig_path)).st_ino
            existing_link = None
            for f in target_dir.iterdir():
                if f.is_file() and os.stat(str(f)).st_ino == orig_ino:
                    existing_link = f
                    break
                    
            if existing_link:
                target_path = existing_link
            else:
                target_path = target_dir / orig_path.name
                counter = 1
                while target_path.exists():
                    target_path = target_dir / f"{orig_path.stem}_{counter}{orig_path.suffix}"
                    counter += 1
                try:
                    os.link(str(orig_path), str(target_path))
                except Exception:
                    try:
                        import shutil
                        shutil.copy2(str(orig_path), str(target_path))
                    except Exception:
                        pass
            
    # Garbage Collector
    should_garbage_collect = False
    if target_path != orig_path:
        try:
            overrides = load_overrides()
            file_key = get_file_key(str(orig_path))
            other_faces_same_person = False
            has_other_people = False
            
            if file_key in overrides:
                for ov in overrides[file_key]:
                    if ov.get('identity') == orig_path.parent.name and (face_data is None or iou([ov['x'], ov['y'], ov['width'], ov['height']], face_box) <= 0.4):
                        other_faces_same_person = True
                    elif ov.get('identity') not in ["Falso_Positivo", "Ignorar_Irrelevante"]:
                        has_other_people = True
            
            if not other_faces_same_person:
                file_bytes = np.fromfile(str(orig_path), dtype=np.uint8)
                img_gc = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                if img_gc is not None:
                    h_gc, w_gc, _ = img_gc.shape
                    detector.setInputSize((w_gc, h_gc))
                    _, faces_gc = detector.detect(img_gc)
                    if faces_gc is not None:
                        for f in faces_gc:
                            f_box = [int(f[0]), int(f[1]), int(f[2]), int(f[3])]
                            if face_data and iou(f_box, face_box) > 0.4:
                                continue
                                
                            aligned = recognizer.alignCrop(img_gc, f)
                            feature = recognizer.feature(aligned)
                            if feature is None: continue
                            
                            best_score = 0
                            best_match = None
                            for db_id, data_dict in known_faces.items():
                                centroid = data_dict.get('centroid')
                                if centroid is not None:
                                    score = get_cosine_similarity(feature[0], centroid)
                                    if score > best_score:
                                        best_score = score
                                        best_match = db_id
                                        
                            if best_match == orig_path.parent.name and best_score > 0.60:
                                other_faces_same_person = True
                                break
                                
            if not other_faces_same_person:
                should_garbage_collect = True
                
        except Exception as e:
            print("GC Error:", e)

    if should_garbage_collect:
        try:
            os.remove(str(orig_path))
        except Exception:
            pass
            
    return str(target_path)
'''

api_correct_wrapper = '''
def api_correct():
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
                        if similarity >= 85.0:
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
        return jsonify({"success": True, "new_path": final_target_path})
    return jsonify({"success": True})
'''

new_content = content[:start_idx] + helper_func + '\n' + api_correct_wrapper + '\n' + content[end_idx:]

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
