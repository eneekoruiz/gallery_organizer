import sys, re

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

# Remove all previous definitions of api_duplicates_scan, api_duplicates_clean, api_similar_scan, api_similar_clean
routes_to_remove = [
    r"@app\.route\('/api/duplicates_scan'[\s\S]*?(?=@app\.route|\Z)",
    r"@app\.route\('/api/duplicates_clean'[\s\S]*?(?=@app\.route|\Z)",
    r"@app\.route\('/api/similar_scan'[\s\S]*?(?=@app\.route|\Z)",
    r"@app\.route\('/api/similar_clean'[\s\S]*?(?=@app\.route|\Z)"
]

for pattern in routes_to_remove:
    app_code = re.sub(pattern, "", app_code)

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
                        if size < 5000: continue
                        with open(fp, 'rb') as fh:
                            chunk = fh.read(1024 * 1024)
                        h_val = hashlib.md5(chunk + str(size).encode()).hexdigest()
                        if h_val not in hashes: hashes[h_val] = []
                        hashes[h_val].append({'path': str(fp), 'size': size, 'name': fp.name})
                    except: pass
                        
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
                    for dup_p in file_list[1:]:
                        try:
                            freed_bytes += dup_p.stat().st_size
                            dup_p.unlink()
                        except Exception as de: print("Error deleting duplicate:", de)
                            
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
                groups.append({'group_id': pref, 'files': evaluated})
                
        groups = groups[:15]
        return jsonify({'groups': groups})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/similar_clean', methods=['POST'])
def api_similar_clean():
    try:
        data = request.json or {}
        group_id = data.get('group_id')
        if not group_id: return jsonify({'error': 'Falta group_id'}), 400
        valid_exts = {'.jpg', '.jpeg', '.png', '.webp'}
        f_list = []
        for root, dirs, files in os.walk(str(RESULTADOS_DIR)):
            for f in files:
                fp = Path(root) / f
                if fp.suffix.lower() in valid_exts and fp.exists():
                    prefix = fp.stem[:14] if len(fp.stem) >= 14 else fp.stem
                    if prefix == group_id: f_list.append(fp)
                        
        if len(f_list) > 1:
            evaluated = []
            for fp in f_list:
                score = 0.0
                try:
                    img = cv2.imread(str(fp), cv2.IMREAD_GRAYSCALE)
                    if img is not None: score = cv2.Laplacian(img, cv2.CV_64F).var()
                except: pass
                evaluated.append((score, fp))
            evaluated.sort(key=lambda x: x[0], reverse=True)
            for _, dup_p in evaluated[1:]:
                try: dup_p.unlink()
                except Exception as de: print("Error deleting burst file:", de)
                    
        global _GALLERY_CACHE
        _GALLERY_CACHE = None
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
"""

pos = app_code.find("if __name__ == '__main__':")
if pos != -1:
    app_code = app_code[:pos] + cleaner_endpoints + "\n" + app_code[pos:]
else:
    app_code += cleaner_endpoints + "\nif __name__ == '__main__':\n    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)\n"

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code)

print("✓ Cleaned duplicate route declarations in app.py!")
