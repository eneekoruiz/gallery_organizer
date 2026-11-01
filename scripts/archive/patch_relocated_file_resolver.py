import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

find_relocated_func = """
def find_relocated_file(filepath):
    if not filepath:
        return None
    if os.path.exists(filepath):
        return filepath
    filename = Path(filepath).name
    for bdir in [RESULTADOS_DIR, FOTOS_DIR]:
        if bdir.exists():
            for root, dirs, files in os.walk(str(bdir)):
                if filename in files:
                    return os.path.join(root, filename)
    return None
"""

if "def find_relocated_file" not in content:
    content = content.replace("def get_file_key", find_relocated_func + "\ndef get_file_key")
    print("Added find_relocated_file helper function to app.py")

# Patch api_metadata
old_metadata = """@app.route('/api/metadata')
def api_metadata():
    filepath = request.args.get('path')
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404"""

new_metadata = """@app.route('/api/metadata')
def api_metadata():
    filepath = request.args.get('path')
    real_path = find_relocated_file(filepath)
    if not real_path:
        return jsonify({"error": "File not found"}), 404
    filepath = real_path"""

if old_metadata in content:
    content = content.replace(old_metadata, new_metadata)
    print("Patched api_metadata with find_relocated_file in app.py")

# Patch media_file
old_media = """@app.route('/media')
def media_file():
    filepath = request.args.get('path')
    if not filepath or not os.path.exists(filepath):
        return "File not found", 404"""

new_media = """@app.route('/media')
def media_file():
    filepath = request.args.get('path')
    real_path = find_relocated_file(filepath)
    if not real_path:
        return "File not found", 404
    filepath = real_path"""

if old_media in content:
    content = content.replace(old_media, new_media)
    print("Patched media_file with find_relocated_file in app.py")

# Patch api_duplicates
old_dup = """@app.route('/api/duplicates', methods=['POST'])
def api_duplicates():
    data = request.json
    filepath = data.get('path')
    if not filepath or not os.path.exists(filepath):
        return jsonify({"duplicate": False}), 404"""

new_dup = """@app.route('/api/duplicates', methods=['POST'])
def api_duplicates():
    data = request.json
    filepath = data.get('path')
    real_path = find_relocated_file(filepath)
    if not real_path:
        return jsonify({"duplicate": False}), 200
    filepath = real_path"""

if old_dup in content:
    content = content.replace(old_dup, new_dup)
    print("Patched api_duplicates with find_relocated_file in app.py")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
