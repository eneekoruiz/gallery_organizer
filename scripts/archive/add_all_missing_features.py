import sys, re
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

# 1. Ultra-fast non-blocking api_correct
fast_api_correct = """@app.route('/api/correct', methods=['POST'])
def api_correct():
    data = request.json
    filepath = data.get('path')
    new_categoria = data.get('new_categoria')
    new_identidad = data.get('new_identidad')
    face_data = data.get('face')
    
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
        
    global _GALLERY_CACHE
    _GALLERY_CACHE = None
    
    try:
        # Perform instant file move and memory update
        target_path = apply_correction_to_file(filepath, new_categoria, new_identidad, face_data)
        
        # Non-blocking background thread for heavy disk persistence
        def bg_save():
            try:
                process_pending_deletions()
            except Exception as e:
                print("BG Save error:", e)
                
        import threading
        threading.Thread(target=bg_save, daemon=True).start()
        
        return jsonify({"success": True, "new_path": str(target_path) if target_path else filepath})
    except Exception as e:
        return jsonify({"error": str(e)}), 500"""

old_correct_pattern = r"@app\.route\('/api/correct', methods=\['POST'\]\)[\s\S]*?return jsonify\(\{\"success\": True\}\)"
if re.search(old_correct_pattern, app_code):
    app_code = re.sub(old_correct_pattern, fast_api_correct, app_code)
    print("✓ Replaced api_correct with ultra-fast instant handler!")

# 2. Add cleaner endpoints before if __name__ == '__main__':
cleaner_endpoints = """
@app.route('/api/duplicates_scan')
def api_duplicates_scan():
    try:
        import hashlib
        hashes = {}
        valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.mp4', '.mov'}
        
        for root, dirs, files in os.walk(str(RESULTADOS_DIR)):
            for f in files:
                fp = Path(root) / f
                if fp.suffix.lower() in valid_exts and fp.exists():
                    try:
                        size = fp.stat().st_size
                        if size < 5000: continue # Skip tiny thumbs
                        
                        # Read first 1MB + size for ultra-fast hash
                        with open(fp, 'rb') as fh:
                            chunk = fh.read(1024 * 1024)
                        h_val = hashlib.md5(chunk + str(size).encode()).hexdigest()
                        
                        if h_val not in hashes:
                            hashes[h_val] = []
                        hashes[h_val].append({'path': str(fp), 'size': size, 'name': fp.name})
                    except:
                        pass
                        
        groups = []
        total_waste_bytes = 0
        for h_val, file_list in hashes.items():
            if len(file_list) > 1:
                group_waste = sum(f['size'] for f in file_list[1:])
                total_waste_bytes += group_waste
                groups.append({
                    'hash': h_val,
                    'files': file_list,
                    'waste_mb': round(group_waste / (1024 * 1024), 2)
                })
                
        groups.sort(key=lambda x: x['waste_mb'], reverse=True)
        return jsonify({
            'groups': groups,
            'total_waste_mb': round(total_waste_bytes / (1024 * 1024), 2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/duplicates_clean', methods=['POST'])
def api_duplicates_clean():
    try:
        data = request.json or {}
        target_hash = data.get('hash')
        clean_all = data.get('clean_all', False)
        
        import hashlib
        freed_bytes = 0
        
        hashes = {}
        valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.mp4', '.mov'}
        for root, dirs, files in os.walk(str(RESULTADOS_DIR)):
            for f in files:
                fp = Path(root) / f
                if fp.suffix.lower() in valid_exts and fp.exists():
                    try:
                        size = fp.stat().st_size
                        if size < 5000: continue
                        with open(fp, 'rb') as fh:
                            chunk = fh.read(1024 * 1024)
                        h_val = hashlib.md5(chunk + str(size).encode()).hexdigest()
                        if h_val not in hashes: hashes[h_val] = []
                        hashes[h_val].append(fp)
                    except: pass
                    
        global _GALLERY_CACHE
        _GALLERY_CACHE = None
        
        for h_val, file_list in hashes.items():
            if len(file_list) > 1:
                if clean_all or h_val == target_hash:
                    # Keep master (file_list[0]), delete rest
                    for dup_p in file_list[1:]:
                        try:
                            freed_bytes += dup_p.stat().st_size
                            dup_p.unlink()
                        except Exception as de:
                            print("Error deleting duplicate:", de)
                            
        return jsonify({'success': True, 'freed_mb': round(freed_bytes / (1024 * 1024), 2)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/similar_scan')
def api_similar_scan():
    try:
        valid_exts = {'.jpg', '.jpeg', '.png', '.webp'}
        image_files = []
        for root, dirs, files in os.walk(str(RESULTADOS_DIR)):
            for f in files:
                fp = Path(root) / f
                if fp.suffix.lower() in valid_exts and fp.exists():
                    image_files.append(fp)
                    
        # Group by stem prefix (e.g. IMG_20220815_120401, IMG_20220815_120402)
        prefixes = {}
        for fp in image_files:
            prefix = fp.stem[:14] if len(fp.stem) >= 14 else fp.stem
            if prefix not in prefixes: prefixes[prefix] = []
            prefixes[prefix].append(fp)
            
        groups = []
        for pref, f_list in prefixes.items():
            if len(f_list) > 1:
                evaluated = []
                for fp in f_list:
                    score = 0.0
                    try:
                        img = cv2.imread(str(fp), cv2.IMREAD_GRAYSCALE)
                        if img is not None:
                            score = cv2.Laplacian(img, cv2.CV_64F).var()
                    except: pass
                    evaluated.append({
                        'path': str(fp),
                        'name': fp.name,
                        'sharpness_score': round(score, 1)
                    })
                    
                evaluated.sort(key=lambda x: x['sharpness_score'], reverse=True)
                for idx, ev in enumerate(evaluated):
                    ev['is_sharpest'] = (idx == 0)
                    
                groups.append({
                    'group_id': pref,
                    'files': evaluated
                })
                
        groups = groups[:15] # Top 15 burst sequences
        return jsonify({'groups': groups})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/similar_clean', methods=['POST'])
def api_similar_clean():
    try:
        data = request.json or {}
        group_id = data.get('group_id')
        if not group_id:
            return jsonify({'error': 'Falta group_id'}), 400
            
        valid_exts = {'.jpg', '.jpeg', '.png', '.webp'}
        f_list = []
        for root, dirs, files in os.walk(str(RESULTADOS_DIR)):
            for f in files:
                fp = Path(root) / f
                if fp.suffix.lower() in valid_exts and fp.exists():
                    prefix = fp.stem[:14] if len(fp.stem) >= 14 else fp.stem
                    if prefix == group_id:
                        f_list.append(fp)
                        
        if len(f_list) > 1:
            evaluated = []
            for fp in f_list:
                score = 0.0
                try:
                    img = cv2.imread(str(fp), cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        score = cv2.Laplacian(img, cv2.CV_64F).var()
                except: pass
                evaluated.append((score, fp))
                
            evaluated.sort(key=lambda x: x[0], reverse=True)
            # Master is evaluated[0][1], remove others
            for _, dup_p in evaluated[1:]:
                try:
                    dup_p.unlink()
                except Exception as de:
                    print("Error deleting burst file:", de)
                    
        global _GALLERY_CACHE
        _GALLERY_CACHE = None
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
"""

pos = app_code.find("if __name__ == '__main__':")
if pos != -1:
    app_code = app_code[:pos] + cleaner_endpoints + "\n" + app_code[pos:]

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code)

print("✓ Re-inserted duplicates_scan, duplicates_clean, similar_scan, and similar_clean endpoints into app.py!")

# 3. Enhance mobile responsiveness in static/style.css
css_path = Path('static/style.css')
if css_path.exists():
    with open(css_path, 'r', encoding='utf-8') as f:
        css = f.read()
        
    responsive_css = """
/* Responsive UX Enhancements */
@media (max-width: 1024px) {
    .app-container { flex-direction: column; }
    .sidebar { width: 100% !important; max-height: 350px; border-right: none; border-bottom: 1px solid rgba(255,255,255,0.1); }
    .gallery-main { width: 100% !important; }
    .gallery-grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)) !important; }
}

@media (max-width: 600px) {
    .gallery-grid { grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)) !important; gap: 8px !important; }
    .sidebar-button-stack { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .lb-content-container { max-width: 98vw !important; max-height: 90vh !important; }
}
"""
    if "/* Responsive UX Enhancements */" not in css:
        css += responsive_css
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(css)
        print("✓ Enhanced static/style.css with responsive layout rules!")
