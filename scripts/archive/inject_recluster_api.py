import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

injection = """
@app.route('/api/recluster_unknowns', methods=['POST'])
def start_recluster():
    subprocess.Popen([sys.executable, "recluster.py"])
    return jsonify({"success": True})

@app.route('/api/recluster_status')
def get_recluster_status():
    status_file = Path("recluster_status.json")
    if status_file.exists():
        with open(status_file, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify({"status": "Esperando...", "progress": 0})
"""

if '@app.route(\'/api/recluster_unknowns\'' not in content:
    content = content.replace("@app.route('/api/auto_merge', methods=['POST'])", injection + "\n@app.route('/api/auto_merge', methods=['POST'])")
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Injected recluster routes")
else:
    print("Already injected")
