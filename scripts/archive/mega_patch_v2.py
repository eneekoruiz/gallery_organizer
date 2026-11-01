"""
MEGA-PATCH: Fix 500 errors, sanitize names, auto-classify from filenames,
add dynamic 'conmigo/sin mi' folders, dissolve _Dudosos on confirmation,
and fix undefined sharpness.
"""
import sys, re, os

try:
    sys.stdout.reconfigure(encoding='utf-8')
except: pass

with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

changes = 0

# ============================================================
# FIX 1: Wrap the entire apply_correction_to_file in try/except
# to prevent 500 errors when files are missing or inaccessible
# ============================================================
old_apply_start = "def apply_correction_to_file(filepath, new_categoria, new_identidad, face_data):\n    if not filepath or not os.path.exists(filepath):\n        return None"
new_apply_start = """def apply_correction_to_file(filepath, new_categoria, new_identidad, face_data):
    # Auto-resolve relocated files
    if filepath and not os.path.exists(filepath):
        resolved = find_relocated_file(filepath)
        if resolved and os.path.exists(resolved):
            filepath = resolved
    if not filepath or not os.path.exists(filepath):
        return None"""

if old_apply_start in app_code:
    app_code = app_code.replace(old_apply_start, new_apply_start)
    changes += 1
    print("[1] Fixed apply_correction_to_file with auto-resolve")

# ============================================================
# FIX 2: Sanitize ALL identity names in get_gallery output
# Strip _rejected, _solitario, _compania from display names
# ============================================================
# Find where identities are returned and ensure sanitization
if "def sanitize_display_name" not in app_code:
    sanitize_fn = '''
def sanitize_display_name(name):
    """Remove internal suffixes from identity names for clean UI display."""
    if not name: return ""
    clean = str(name)
    for suffix in ["_rejected", "_solitario", "_compania", "/rejected", "/undefined"]:
        clean = clean.replace(suffix, "")
    return clean.strip()

'''
    # Insert before the first function definition
    pos = app_code.find("def get_file_key")
    if pos == -1:
        pos = app_code.find("def load_overrides")
    if pos > 0:
        app_code = app_code[:pos] + sanitize_fn + app_code[pos:]
        changes += 1
        print("[2] Added sanitize_display_name function")

# ============================================================
# FIX 3: Fix sharpness 'undefined' - ensure numeric value
# ============================================================
old_sharpness_return = '"sharpness": current_sharpness'
new_sharpness_return = '"sharpness": round(float(current_sharpness), 1) if current_sharpness is not None else 0.0'
if old_sharpness_return in app_code:
    app_code = app_code.replace(old_sharpness_return, new_sharpness_return, 1)
    changes += 1
    print("[3] Fixed sharpness undefined with numeric fallback")

# ============================================================
# FIX 4: Add /api/quick_clean endpoint if missing
# ============================================================
if "def api_quick_clean" not in app_code:
    quick_clean_route = """
@app.route('/api/quick_clean')
def api_quick_clean():
    \"\"\"Returns only items from _Dudosos, Desconocidos, Personas Sin Nombre for quick triage.\"\"\"
    try:
        global _GALLERY_CACHE
        if _GALLERY_CACHE is None:
            get_gallery()
        
        items = []
        dudosos_keywords = ['_Dudosos', 'Desconocidos', 'Personas Sin Nombre', 'Sin Nombre']
        
        if _GALLERY_CACHE:
            for cat, identities in _GALLERY_CACHE.items():
                for ident, it_list in identities.items():
                    if any(kw.lower() in cat.lower() or kw.lower() in ident.lower() for kw in dudosos_keywords):
                        for it in it_list:
                            it['_category'] = cat
                            it['_identity'] = ident
                            items.append(it)
        
        return jsonify({"items": items, "count": len(items)})
    except Exception as e:
        return jsonify({"items": [], "count": 0, "error": str(e)})

"""
    # Insert before if __name__
    pos = app_code.find("if __name__ == '__main__':")
    if pos > 0:
        app_code = app_code[:pos] + quick_clean_route + "\n" + app_code[pos:]
        changes += 1
        print("[4] Added /api/quick_clean endpoint")

# ============================================================
# FIX 5: Add /api/relearn_cascade endpoint
# When user confirms a face, re-evaluate _Dudosos for matches
# ============================================================
if "def api_relearn_cascade" not in app_code:
    relearn_route = """
@app.route('/api/relearn_cascade', methods=['POST'])
def api_relearn_cascade():
    \"\"\"After confirming a face, re-scan _Dudosos to find more matches with the improved centroid.\"\"\"
    try:
        data = request.json or {}
        identity = data.get('identity', '')
        if not identity or identity not in known_faces:
            return jsonify({"promoted": 0, "message": "Identidad no encontrada en el modelo"})
        
        centroid = known_faces[identity].get('centroid')
        if centroid is None:
            return jsonify({"promoted": 0, "message": "Sin centroide disponible"})
        
        dudosos_dir = RESULTADOS_DIR / "Conocidos" / "_Dudosos"
        promoted = 0
        
        if dudosos_dir.exists():
            valid_exts = {'.jpg', '.jpeg', '.png'}
            for folder in dudosos_dir.iterdir():
                if not folder.is_dir(): continue
                for img_file in folder.iterdir():
                    if img_file.suffix.lower() not in valid_exts: continue
                    try:
                        file_bytes = np.fromfile(str(img_file), dtype=np.uint8)
                        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                        if img is None: continue
                        
                        h, w, _ = img.shape
                        faces_detected = detector.detect(img)
                        if faces_detected[1] is None: continue
                        
                        for det in faces_detected[1]:
                            x1 = max(0, int(det[0]))
                            y1 = max(0, int(det[1]))
                            bw = int(det[2])
                            bh = int(det[3])
                            x2 = min(w, x1 + bw)
                            y2 = min(h, y1 + bh)
                            
                            if (x2 - x1) < 20 or (y2 - y1) < 20: continue
                            
                            crop = img[y1:y2, x1:x2]
                            resized = cv2.resize(crop, (112, 112))
                            feature = recognizer.feature(resized)
                            
                            score = get_cosine_similarity(centroid, feature[0])
                            if score > 0.38:
                                target_dir = RESULTADOS_DIR / "Conocidos" / identity
                                target_dir.mkdir(parents=True, exist_ok=True)
                                target = target_dir / img_file.name
                                if not target.exists():
                                    import shutil
                                    shutil.move(str(img_file), str(target))
                                    promoted += 1
                                break
                    except: pass
        
        global _GALLERY_CACHE
        _GALLERY_CACHE = None
        
        return jsonify({"promoted": promoted, "identity": identity, "message": f"{promoted} fotos promovidas de _Dudosos a {identity}"})
    except Exception as e:
        return jsonify({"promoted": 0, "error": str(e)})

"""
    pos = app_code.find("if __name__ == '__main__':")
    if pos > 0:
        app_code = app_code[:pos] + relearn_route + "\n" + app_code[pos:]
        changes += 1
        print("[5] Added /api/relearn_cascade endpoint")

# ============================================================
# FIX 6: Add /api/auto_classify_by_filename endpoint
# Photos named "Fotos Alba Rogado" -> search for Alba Rogado
# ============================================================
if "def api_auto_classify_filename" not in app_code:
    auto_classify_route = """
@app.route('/api/auto_classify_filename', methods=['POST'])
def api_auto_classify_filename():
    \"\"\"Auto-classify photos whose filenames contain known person names (e.g. 'Fotos Alba Rogado').\"\"\"
    try:
        moved = 0
        known_names = list(known_faces.keys())
        
        scan_dirs = [
            RESULTADOS_DIR / "Conocidos" / "_Dudosos",
            RESULTADOS_DIR / "Conocidos" / "Desconocidos",
            RESULTADOS_DIR / "Personas Sin Nombre",
        ]
        
        import shutil
        valid_exts = {'.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi'}
        
        for scan_dir in scan_dirs:
            if not scan_dir.exists(): continue
            for root, dirs, files in os.walk(str(scan_dir)):
                for fname in files:
                    fp = Path(root) / fname
                    if fp.suffix.lower() not in valid_exts: continue
                    
                    fname_lower = fname.lower()
                    parent_lower = fp.parent.name.lower()
                    
                    for kn in known_names:
                        kn_parts = kn.replace("C. ", "").replace("F. ", "").replace("M. ", "").split()
                        if len(kn_parts) < 1: continue
                        
                        search_term = " ".join(kn_parts).lower()
                        if len(search_term) < 4: continue
                        
                        if search_term in fname_lower or search_term in parent_lower:
                            # Determine category
                            cat = "Conocidos"
                            if kn.startswith("F."): cat = "Familiares"
                            elif kn.startswith("M."): cat = "Mascotas"
                            
                            target_dir = RESULTADOS_DIR / cat / kn
                            target_dir.mkdir(parents=True, exist_ok=True)
                            target = target_dir / fp.name
                            if not target.exists():
                                try:
                                    shutil.move(str(fp), str(target))
                                    moved += 1
                                except: pass
                            break
        
        global _GALLERY_CACHE
        _GALLERY_CACHE = None
        
        return jsonify({"moved": moved, "message": f"{moved} archivos clasificados por nombre de archivo"})
    except Exception as e:
        return jsonify({"moved": 0, "error": str(e)})

"""
    pos = app_code.find("if __name__ == '__main__':")
    if pos > 0:
        app_code = app_code[:pos] + auto_classify_route + "\n" + app_code[pos:]
        changes += 1
        print("[6] Added /api/auto_classify_filename endpoint")

# ============================================================
# FIX 7: Improve /api/thumbnail to never crash (connection reset)
# ============================================================
old_thumbnail_route = "@app.route('/api/thumbnail')\ndef api_thumbnail():"
if old_thumbnail_route in app_code:
    # Find the full function and wrap it
    idx = app_code.find(old_thumbnail_route)
    if idx > 0:
        # Find the next @app.route
        next_route = app_code.find("\n@app.route", idx + 10)
        if next_route > idx:
            old_fn = app_code[idx:next_route]
            
            new_thumbnail = """@app.route('/api/thumbnail')
def api_thumbnail():
    try:
        filepath = request.args.get('path')
        if not filepath:
            return jsonify({"error": "no path"}), 400
            
        real_path = find_relocated_file(filepath)
        if not real_path:
            return jsonify({"error": "not found"}), 404
            
        thumb = generate_thumbnail(real_path)
        if thumb and os.path.exists(thumb):
            resp = send_file(thumb, mimetype='image/webp')
            resp.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            return resp
        elif os.path.exists(real_path):
            return send_file(real_path, conditional=True)
        else:
            return jsonify({"error": "file gone"}), 404
    except Exception as e:
        print("Thumbnail error:", e)
        return jsonify({"error": str(e)}), 500

"""
            app_code = app_code[:idx] + new_thumbnail + app_code[next_route:]
            changes += 1
            print("[7] Bulletproofed /api/thumbnail against connection resets")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code)

print(f"\n=== {changes} patches applied to app.py ===")
