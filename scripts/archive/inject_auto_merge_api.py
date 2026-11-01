import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

injection = """
import subprocess

@app.route('/api/auto_merge', methods=['POST'])
def start_auto_merge():
    # Lanzar auto_merge.py en background
    subprocess.Popen([sys.executable, "auto_merge.py"])
    return jsonify({"success": True})

@app.route('/api/auto_merge_status')
def get_auto_merge_status():
    status_file = Path("auto_merge_status.json")
    if status_file.exists():
        with open(status_file, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    return jsonify({"status": "Esperando...", "progress": 0})
"""

if '@app.route(\'/api/auto_merge\'' not in content:
    content = content.replace("@app.route('/api/mass_cleanup', methods=['POST'])", injection + "\n@app.route('/api/mass_cleanup', methods=['POST'])")
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Injected auto merge routes")
else:
    print("Already injected")
