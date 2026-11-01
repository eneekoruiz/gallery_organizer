import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_detect = """@app.route('/api/detect_deep', methods=['POST'])
def detect_deep():
    data = request.json
    filepath = data.get('path')
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
        
    try:
        img = cv2.imread(filepath)
        if img is None:
            return jsonify({"error": "Could not read image"}), 400"""

new_detect = """@app.route('/api/detect_deep', methods=['POST'])
def detect_deep():
    data = request.json
    filepath = data.get('path')
    if not filepath:
        return jsonify({"error": "File not found"}), 404
        
    p_obj = Path(filepath)
    if not p_obj.exists():
        alt_p = Path(filepath.replace('/', '\\\\')) if '/' in filepath else Path(filepath.replace('\\\\', '/'))
        if alt_p.exists():
            p_obj = alt_p
        else:
            return jsonify({"error": "File not found"}), 404
            
    filepath = str(p_obj)
        
    try:
        file_bytes = np.fromfile(filepath, dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({"error": "Could not read image"}), 400"""

if old_detect in content:
    content = content.replace(old_detect, new_detect)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched detect_deep with np.fromfile for Unicode Windows paths")
else:
    print("Could not find old_detect in app.py")
