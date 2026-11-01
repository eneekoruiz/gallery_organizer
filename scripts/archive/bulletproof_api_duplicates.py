import sys, re

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

bulletproof_duplicates = """@app.route('/api/duplicates', methods=['POST'])
def api_duplicates():
    try:
        data = request.json or {}
        filepath = data.get('path')
        if not filepath:
            return jsonify({"duplicate": False, "sharpness": 0.0}), 200
            
        real_path = find_relocated_file(filepath)
        if not real_path or not os.path.exists(real_path):
            return jsonify({"duplicate": False, "sharpness": 0.0}), 200
        filepath = real_path
            
        path_obj = Path(filepath)
        parent_dir = path_obj.parent
        
        current_sharpness = 0.0
        try:
            current_sharpness = calculate_sharpness(filepath)
        except: pass
        
        current_hash = None
        try:
            current_hash = calculate_dhash(filepath)
        except: pass
        
        if current_hash is None:
            return jsonify({"sharpness": current_sharpness, "duplicate": None})
            
        valid_exts = {".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi"}
        duplicate_info = None
        
        if parent_dir.exists():
            for other_file in parent_dir.iterdir():
                try:
                    if not other_file.is_file() or other_file.name == path_obj.name: continue
                    if other_file.suffix.lower() not in valid_exts: continue
                    
                    other_hash = calculate_dhash(str(other_file))
                    if other_hash is not None and len(other_hash) == len(current_hash):
                        hamming_dist = np.count_nonzero(current_hash != other_hash)
                        similarity = round((1.0 - (hamming_dist / len(current_hash))) * 100, 1)
                        if similarity >= 85.0:
                            duplicate_info = {
                                "duplicate": True,
                                "path": str(other_file),
                                "similarity": similarity
                            }
                            break
                except: pass
                
        return jsonify({
            "sharpness": current_sharpness,
            "duplicate": duplicate_info["duplicate"] if duplicate_info else False,
            "duplicate_info": duplicate_info
        })
    except Exception as e:
        return jsonify({"sharpness": 0.0, "duplicate": False, "error": str(e)}), 200"""

pattern = r"@app\.route\('/api/duplicates', methods=\['POST'\]\)[\s\S]*?return jsonify\(.*?\)"
if re.search(pattern, app_code):
    app_code = re.sub(pattern, bulletproof_duplicates, app_code)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code)

print("✓ Bulletproofed /api/duplicates route in app.py!")
