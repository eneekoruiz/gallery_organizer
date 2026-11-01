import os
import json
from pathlib import Path
import threading

APPLE_DB_FILE = Path(r"C:\Users\User\Desktop\ENEKO\smart_gallery_app\apple_db.json")
ICLOUD_PHOTOS_DIR = Path(r"C:\Users\User\Pictures\iCloud Photos\Photos")

_apple_db = {}
_apple_db_lock = threading.Lock()

def load_apple_db():
    global _apple_db
    with _apple_db_lock:
        if APPLE_DB_FILE.exists():
            try:
                with open(APPLE_DB_FILE, 'r', encoding='utf-8') as f:
                    _apple_db = json.load(f)
            except:
                _apple_db = {}
        else:
            _apple_db = {}
    return _apple_db

def save_apple_db():
    with _apple_db_lock:
        with open(APPLE_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(_apple_db, f, indent=4)

def is_apple_photo(path_str):
    if not path_str: return False
    p_norm = str(path_str).replace('\\', '/').lower()
    return (
        "icloud photos" in p_norm or 
        "apple" in p_norm or 
        "iphone" in p_norm or 
        p_norm.endswith(".heic") or 
        p_norm.endswith(".heif")
    )

def get_apple_photo_mapping(path_str):
    db = load_apple_db()
    return db.get(path_str, None)

def update_apple_photo_mapping(path_str, category, identity):
    db = load_apple_db()
    if path_str not in db:
        db[path_str] = {}
    db[path_str]['category'] = category
    db[path_str]['identity'] = identity
    save_apple_db()

def mark_apple_photo_deleted_locally(path_str):
    db = load_apple_db()
    if path_str not in db:
        db[path_str] = {}
    db[path_str]['deleted_locally'] = True
    save_apple_db()

def mark_apple_photo_deleted_icloud(path_str):
    db = load_apple_db()
    if path_str not in db:
        db[path_str] = {}
    db[path_str]['deleted_icloud'] = True
    save_apple_db()

def rename_apple_group(old_cat, old_ident, new_cat, new_ident):
    db = load_apple_db()
    changed = False
    for p, info in db.items():
        if info.get('category') == old_cat and info.get('identity') == old_ident:
            info['category'] = new_cat
            info['identity'] = new_ident
            changed = True
    if changed:
        save_apple_db()

def delete_apple_group(cat, ident):
    db = load_apple_db()
    changed = False
    keys_to_delete = []
    for p, info in db.items():
        if info.get('category') == cat and info.get('identity') == ident:
            keys_to_delete.append(p)
    for k in keys_to_delete:
        del db[k]
        changed = True
    if changed:
        save_apple_db()
