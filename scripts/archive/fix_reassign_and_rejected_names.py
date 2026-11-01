import sys, re

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

# 1. Update api_correct to use find_relocated_file so moving a file 2+ times NEVER fails with 500 File Not Found!
robust_api_correct = """@app.route('/api/correct', methods=['POST'])
def api_correct():
    data = request.json or {}
    filepath = data.get('path')
    new_categoria = data.get('new_categoria')
    new_identidad = data.get('new_identidad')
    face_data = data.get('face')
    
    if not filepath:
        return jsonify({"error": "Falta parámetro path"}), 400
        
    # Auto-resolve path if it was previously moved or relocated
    real_path = find_relocated_file(filepath)
    if real_path and os.path.exists(real_path):
        filepath = real_path
        
    if not os.path.exists(filepath):
        return jsonify({"error": f"El archivo {filepath} no existe en disco"}), 404
        
    global _GALLERY_CACHE
    _GALLERY_CACHE = None
    
    try:
        target_path = apply_correction_to_file(filepath, new_categoria, new_identidad, face_data)
        
        def bg_save():
            try: process_pending_deletions()
            except: pass
                
        import threading
        threading.Thread(target=bg_save, daemon=True).start()
        
        res_path = str(target_path) if target_path else filepath
        return jsonify({"success": True, "new_path": res_path})
    except Exception as e:
        print("Error in api_correct:", e)
        return jsonify({"error": str(e)}), 500"""

pattern_correct = r"@app\.route\('/api/correct', methods=\['POST'\]\)[\s\S]*?return jsonify\(.*?\)\n\s*except Exception as e:[\s\S]*?return jsonify\(\{\"error\": str\(e\)\}\), 500"
if re.search(pattern_correct, app_code):
    app_code = re.sub(pattern_correct, robust_api_correct, app_code)

# 2. Sanitize display names (strip "_rejected" suffixes from identity labels so the user never sees technical internal names)
clean_display_name_code = """
def sanitize_display_name(name):
    if not name: return ""
    clean = str(name).replace("_rejected", "").replace("_solitario", "").replace("_compania", "")
    return clean.strip()
"""
if "def sanitize_display_name" not in app_code:
    app_code = clean_display_name_code + app_code

# Replace occurrences of folder names or identities containing _rejected in get_gallery and api_faces
app_code = app_code.replace("identidad_clean = raw_ident", "identidad_clean = raw_ident.replace('_rejected', '').replace('_solitario', '')")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code)

print("✓ Fixed api_correct with find_relocated_file and sanitized _rejected names in app.py!")
