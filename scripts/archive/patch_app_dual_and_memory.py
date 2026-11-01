import sys, re
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

# 1. Add imports for storage_adapters and state_memory
imports_block = """import storage_adapters
from state_memory import state_memory
"""
if "import storage_adapters" not in app_code:
    app_code = imports_block + app_code

# 2. Add config management endpoints
config_endpoints = """
CONFIG_FILE = Path("config.json")

def load_system_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {"mode": "local", "local_path": r"C:\\Users\\User\\Desktop\\Galeria Eneko NO ABRIR", "gdrive_folder_id": "1Qr6KXPxcgdlzbSHVyDOg4cBb4GReSAfD"}

def save_system_config(cfg):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    if request.method == 'POST':
        data = request.json or {}
        mode = data.get('mode', 'local')
        local_path = data.get('local_path')
        gdrive_url_or_id = data.get('gdrive_url_or_id')
        
        cfg = load_system_config()
        cfg['mode'] = mode
        if local_path:
            cfg['local_path'] = local_path
        if gdrive_url_or_id:
            # Extract folder ID if full link was provided
            folder_id = gdrive_url_or_id
            if 'folders/' in gdrive_url_or_id:
                folder_id = gdrive_url_or_id.split('folders/')[1].split('?')[0]
            cfg['gdrive_folder_id'] = folder_id
            
        save_system_config(cfg)
        global _GALLERY_CACHE
        _GALLERY_CACHE = None
        return jsonify({"success": True, "config": cfg})
    else:
        return jsonify(load_system_config())

@app.route('/api/delta_sync', methods=['POST'])
def api_delta_sync():
    try:
        cfg = load_system_config()
        adapter = storage_adapters.get_adapter(cfg.get('mode', 'local'), cfg)
        all_files = adapter.list_files()
        unprocessed = state_memory.get_unprocessed_files(all_files)
        
        state_memory.update_delta_sync_time()
        global _GALLERY_CACHE
        _GALLERY_CACHE = None
        
        return jsonify({
            "success": True,
            "total_files": len(all_files),
            "unprocessed_files": len(unprocessed)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
"""

pos = app_code.find("if __name__ == '__main__':")
if pos != -1:
    app_code = app_code[:pos] + config_endpoints + "\n" + app_code[pos:]
else:
    app_code += config_endpoints

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code)

print("✓ Injected storage_adapters, config endpoints, and delta_sync into app.py!")
