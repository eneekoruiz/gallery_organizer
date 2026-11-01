import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Patch get_media
old_get_media = """@app.route('/media')
def get_media():
    filepath = request.args.get('path')
    if not filepath or not os.path.exists(filepath):
        return "Not found", 404
    return send_file(filepath, conditional=True)"""

new_get_media = """@app.route('/media')
def get_media():
    filepath = request.args.get('path')
    real_path = find_relocated_file(filepath)
    if not real_path:
        return "Not found", 404
    return send_file(real_path, conditional=True)"""

if old_get_media in content:
    content = content.replace(old_get_media, new_get_media)
    print("Patched get_media with find_relocated_file")

# 2. Patch api_duplicates
old_api_duplicates = """def api_duplicates():
    try:
        data = request.json
        filepath = data.get('path')
        if not filepath or not os.path.exists(filepath):
            return jsonify({"error": "Not found"}), 404"""

new_api_duplicates = """def api_duplicates():
    try:
        data = request.json
        filepath = data.get('path')
        real_path = find_relocated_file(filepath)
        if not real_path:
            return jsonify({"duplicate": False}), 200
        filepath = real_path"""

if old_api_duplicates in content:
    content = content.replace(old_api_duplicates, new_api_duplicates)
    print("Patched api_duplicates with find_relocated_file")

# 3. Patch api_thumbnail
old_api_thumbnail = """@app.route('/api/thumbnail')
def api_thumbnail():
    filepath = request.args.get('path')
    if not filepath or not os.path.exists(filepath):
        return "Not found", 404"""

new_api_thumbnail = """@app.route('/api/thumbnail')
def api_thumbnail():
    filepath = request.args.get('path')
    real_path = find_relocated_file(filepath)
    if not real_path:
        return "Not found", 404
    filepath = real_path"""

if old_api_thumbnail in content:
    content = content.replace(old_api_thumbnail, new_api_thumbnail)
    print("Patched api_thumbnail with find_relocated_file")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
