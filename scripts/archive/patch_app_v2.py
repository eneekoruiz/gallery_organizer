import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace api_correct and append api_delete
correct_code = """@app.route('/api/delete', methods=['POST'])
def api_delete():
    data = request.json
    filepath = data.get('path')
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "Archivo no encontrado"}), 404
        
    orig_path = Path(filepath)
    try:
        if orig_path.is_relative_to(FOTOS_DIR):
            return jsonify({"error": "Dataset protegido: Las fotos del dataset manual original no pueden eliminarse físicamente."}), 403
    except ValueError:
        pass
        
    try:
        os.remove(str(orig_path))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/correct', methods=['POST'])
def api_correct():
    data = request.json
    filepath = data.get('path')
    new_categoria = data.get('new_categoria')
    new_identidad = data.get('new_identidad')
    face_data = data.get('face')
    
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
        
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

    # File Management (Hardlinks)
    target_path = orig_path
    if new_categoria != "Ignorar":
        target_dir = RESULTADOS_DIR / new_categoria / new_identidad
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / orig_path.name
        counter = 1
        while target_path.exists():
            target_path = target_dir / f"{orig_path.stem}_{counter}{orig_path.suffix}"
            counter += 1
            
        try:
            # Crear enlace duro en la nueva carpeta
            os.link(str(orig_path), str(target_path))
            
            # Garbage Collector (solo si NO es una foto protegida del dataset manual)
            if not is_manual_source:
                current_folder = orig_path.parent.name
                if current_folder != "_Dudosos":
                    still_has_current = False
                    for ov in overrides.get(file_key, []):
                        if ov['identity'] == current_folder:
                            still_has_current = True
                            break
                    if not still_has_current:
                        try:
                            os.remove(str(orig_path))
                        except:
                            pass
                    
        except Exception as e:
            try:
                import shutil
                shutil.move(str(orig_path), str(target_path))
            except:
                pass

    return jsonify({"success": True, "new_path": str(target_path)})
"""

idx = content.find("@app.route('/api/correct'")
if idx == -1:
    print("Error: api_correct not found")
    exit(1)

main_idx = content.find("if __name__ == '__main__':")
head = content[:idx]
new_content = head + correct_code + "\n\n" + content[main_idx:]

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("app.py actualizado con /api/delete y fotos manuales habilitadas.")
