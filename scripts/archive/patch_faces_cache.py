import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Load faces_cache
cache_load_code = '''
FACES_CACHE_FILE = APP_DIR / "faces_cache.pkl"
try:
    with open(FACES_CACHE_FILE, 'rb') as f:
        faces_cache = pickle.load(f)
except:
    faces_cache = {}
'''
content = content.replace("with open(CACHE_FILE, 'rb') as f:\n    known_faces = pickle.load(f)", "with open(CACHE_FILE, 'rb') as f:\n    known_faces = pickle.load(f)\n" + cache_load_code)

# 2. Patch api_analyze
# Find api_analyze
analyze_match = re.search(r'def api_analyze\(\):.*?try:', content, flags=re.DOTALL)
if analyze_match:
    old_analyze_start = analyze_match.group(0)
    
    new_analyze_start = old_analyze_start.replace("try:", '''
    if filepath in faces_cache:
        # Check if file modification time changed? Or just trust it.
        # Actually, let's just return it for max speed
        return jsonify({"faces": faces_cache[filepath]})
        
    try:''')
    content = content.replace(old_analyze_start, new_analyze_start)

# Now find where api_analyze returns the faces to cache them
# It ends with: return jsonify({"faces": results})
# Or something similar. Let's find "return jsonify({"faces": results})"
content = content.replace('return jsonify({"faces": results})', '''
    faces_cache[filepath] = results
    with open(FACES_CACHE_FILE, 'wb') as f:
        pickle.dump(faces_cache, f)
    return jsonify({"faces": results})''')

# 3. Patch api_correct to update faces_cache
# Find where it says "save_overrides(overrides)"
# We can inject faces_cache update right there.
cache_update_code = '''        save_overrides(overrides)
        
        # Actualizar la caché de caras instantáneamente para la UI
        if filepath in faces_cache:
            for c_face in faces_cache[filepath]:
                c_box = [c_face['x'], c_face['y'], c_face['width'], c_face['height']]
                if iou(face_box, c_box) > 0.4:
                    c_face['identity'] = new_identidad
                    c_face['confidence'] = "100.0"
                    c_face['is_manual'] = True
                    break
            with open(FACES_CACHE_FILE, 'wb') as f:
                pickle.dump(faces_cache, f)
'''
content = content.replace('        save_overrides(overrides)', cache_update_code)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("app.py patched for faces cache!")
