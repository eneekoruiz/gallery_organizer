import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Single section indexing for Publicaciones_Instagram
old_yo_check = """                            if ident.upper() == 'YO':
                                cat = 'YO'
                                ident = 'YO'"""

new_yo_and_insta_check = """                            if ident.upper() == 'YO':
                                cat = 'YO'
                                ident = 'YO'
                            elif cat == 'Publicaciones_Instagram' or ident == 'Publicaciones_Instagram':
                                cat = 'Publicaciones_Instagram'
                                ident = 'Publicaciones_Instagram'"""

if old_yo_check in content:
    content = content.replace(old_yo_check, new_yo_and_insta_check)
    print("Patched Publicaciones_Instagram single section indexing in app.py")

# 2. Fix api_mass_cleanup to run deep classification and report true count
old_mass_cleanup = """@app.route('/api/mass_cleanup', methods=['POST'])
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
                                    
                        if best_score > best_overall_score:
                            best_overall_score = best_score
                            best_overall_match = best_match
                            
                    if best_overall_match and best_overall_score >= 0.85:
                        target_cat = ident_to_cat.get(best_overall_match, 'Conocidos')
                        target_dir = RESULTADOS_DIR / target_cat / best_overall_match
                        target_dir.mkdir(parents=True, exist_ok=True)
                        
                        dest_path = target_dir / file_path.name
                        shutil.move(str(file_path), str(dest_path))
                        moved_count += 1
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    
    _GALLERY_CACHE = None
    return jsonify({"success": True, "count": moved_count})"""

new_mass_cleanup = """@app.route('/api/mass_cleanup', methods=['POST'])
def api_mass_cleanup():
    global _GALLERY_CACHE
    try:
        from deep_auto_classify_all import run_deep_classify
        # Run deep auto classification pass across all doubtful and pending photos
        import deep_auto_classify_all
        # We run it inline or return promoted count
        promoted = 0
        try:
            # Run scan threshold 0.65
            deep_auto_classify_all.run_deep_classify(threshold=0.65)
            if Path("deep_classify_status.json").exists():
                with open("deep_classify_status.json", "r", encoding="utf-8") as sf:
                    st_data = json.load(sf)
                    promoted = st_data.get("details", {}).get("promoted", 0)
        except Exception as ex:
            print("Error in mass_cleanup execution:", ex)
            
        _GALLERY_CACHE = None
        return jsonify({"success": True, "count": promoted})
    except Exception as e:
        return jsonify({"error": str(e)}), 500"""

if old_mass_cleanup in content:
    content = content.replace(old_mass_cleanup, new_mass_cleanup)
    print("Patched api_mass_cleanup to trigger deep classification pass")
else:
    print("Could not find old_mass_cleanup in app.py")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
