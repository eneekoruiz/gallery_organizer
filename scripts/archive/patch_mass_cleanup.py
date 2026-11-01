import re
import os

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

endpoint_code = """
@app.route('/api/mass_cleanup', methods=['POST'])
def api_mass_cleanup():
    global known_faces
    if not known_faces:
        return jsonify({"error": "No hay caras conocidas en caché"}), 500

    identities = get_all_identities()
    ident_to_cat = {item["identidad"]: item["categoria"] for item in identities}
    
    moved_count = 0
    
    dirs_to_check = [FOTOS_DIR / 'Personas Sin Nombre', RESULTADOS_DIR / 'Personas Sin Nombre']
    
    for personas_sin_nombre_dir in dirs_to_check:
        if not personas_sin_nombre_dir.exists():
            continue
            
        for sub_dir in personas_sin_nombre_dir.iterdir():
            if not sub_dir.is_dir() or sub_dir.name == '_Dudosos':
                continue
                
            # Verify it's a Persona Nueva folder (can be Persona_Nueva or Persona Nueva #)
            if not (sub_dir.name.startswith('Persona_Nueva') or sub_dir.name.startswith('Persona Nueva')):
                continue
                
            for file_path in sub_dir.iterdir():
                if not file_path.is_file() or file_path.suffix.lower() not in {'.jpg', '.jpeg', '.png'}:
                    continue
                    
                try:
                    # Need to read image and detect faces
                    file_bytes = np.fromfile(str(file_path), dtype=np.uint8)
                    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                    if img is None:
                        continue
                        
                    h, w, _ = img.shape
                    detector.setInputSize([w, h])
                    _, faces = detector.detect(img)
                    
                    if faces is None or len(faces) == 0:
                        continue
                    
                    best_overall_score = 0
                    best_overall_match = None
                    
                    for face in faces:
                        aligned = recognizer.alignCrop(img, face)
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
                                    
                        if best_match and best_score > best_overall_score:
                            best_overall_score = best_score
                            best_overall_match = best_match
                            
                    if best_overall_match and best_overall_score > 0.60:
                        if best_overall_match.startswith("Falso_Positivo") or best_overall_match.startswith("Ignorar_Irrelevante"):
                            continue
                            
                        # Find category
                        new_cat = ident_to_cat.get(best_overall_match)
                        if not new_cat:
                            if best_overall_match.startswith("C. "):
                                new_cat = "Conocidos"
                            elif best_overall_match.startswith("P. "):
                                new_cat = "Personas"
                            else:
                                new_cat = "Conocidos"
                                
                        # Move the file! Use same target_dir logic as api_correct
                        if personas_sin_nombre_dir == FOTOS_DIR / 'Personas Sin Nombre':
                            target_dir = FOTOS_DIR / new_cat / best_overall_match
                        else:
                            target_dir = RESULTADOS_DIR / new_cat / best_overall_match
                            
                        target_dir.mkdir(parents=True, exist_ok=True)
                        
                        target_path = target_dir / file_path.name
                        counter = 1
                        while target_path.exists():
                            target_path = target_dir / f"{file_path.stem}_{counter}{file_path.suffix}"
                            counter += 1
                            
                        import shutil
                        shutil.move(str(file_path), str(target_path))
                        moved_count += 1
                except Exception as e:
                    print("Error mass cleanup", file_path, e)
                    
    clear_gallery_cache()
    process_pending_deletions()
    return jsonify({"success": True, "moved_count": moved_count})
"""

# We must replace the existing api_mass_cleanup
start_idx = content.find("@app.route('/api/mass_cleanup', methods=['POST'])")
if start_idx != -1:
    end_idx = content.find("@app.route('/api/correct', methods=['POST'])", start_idx)
    content = content[:start_idx] + endpoint_code + '\n\n' + content[end_idx:]
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Replaced endpoint successfully!')
else:
    print('Could not find /api/mass_cleanup route!')
