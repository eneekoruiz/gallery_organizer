import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Inject faces_cache definition
faces_cache_def = '''
FACES_CACHE_FILE = Path("faces_cache.pkl")
faces_cache = {}
if FACES_CACHE_FILE.exists():
    try:
        with open(FACES_CACHE_FILE, 'rb') as f:
            faces_cache = pickle.load(f)
    except:
        faces_cache = {}
'''
if 'FACES_CACHE_FILE = Path("faces_cache.pkl")' not in content:
    content = content.replace('CACHE_FILE = APP_DIR / "sface_cache_v7.pkl"', 'CACHE_FILE = APP_DIR / "sface_cache_v7.pkl"\n' + faces_cache_def)


# 2. Fix api_pending_sorted returning 400
old_pending = '''def api_pending_sorted():
    global _GALLERY_CACHE, detector, recognizer, known_faces
    if _GALLERY_CACHE is None:
        return jsonify({"error": "La galería aún no se ha cargado"}), 400'''

new_pending = '''def api_pending_sorted():
    global _GALLERY_CACHE, detector, recognizer, known_faces
    if _GALLERY_CACHE is None:
        load_gallery_cache()'''

# Fix for encoding issue string in original: "La galera an no se ha cargado"
# Let's just use regex to replace the start of the function
pattern = re.compile(r'def api_pending_sorted\(\):\s+global _GALLERY_CACHE, detector, recognizer, known_faces\s+if _GALLERY_CACHE is None:\s+return jsonify\(\{"error": ".*?"\}\), 400', re.DOTALL)

if pattern.search(content):
    content = pattern.sub(new_pending, content)
else:
    print("Could not find api_pending_sorted block")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched app.py!")
