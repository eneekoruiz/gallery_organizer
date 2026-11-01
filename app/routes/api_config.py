from flask import Blueprint, request, jsonify
from pathlib import Path
import json

api_config_bp = Blueprint('api_config', __name__)

CONFIG_FILE = Path("config.json")

def load_system_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {"mode": "local", "local_path": r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR", "gdrive_folder_id": "1Qr6KXPxcgdlzbSHVyDOg4cBb4GReSAfD"}

def save_system_config(cfg):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)

@api_config_bp.route('/api/config', methods=['GET', 'POST'])
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
            folder_id = gdrive_url_or_id
            if 'folders/' in gdrive_url_or_id:
                folder_id = gdrive_url_or_id.split('folders/')[1].split('?')[0]
            cfg['gdrive_folder_id'] = folder_id
            
        save_system_config(cfg)
        
        # Clear the global caches so they rebuild from the new storage adapter
        import app.globals as g
        with g.cache_lock:
            g._GALLERY_CACHE = None
            g._CONFIG_CACHE = None
            g.STORAGE_MODE = mode
            g.faces_cache = {}
            g._DHASH_CACHE = {}
            g._CONFIDENCE_CACHE = {}
            
        return jsonify({"success": True, "config": cfg})
    else:
        return jsonify(load_system_config())
