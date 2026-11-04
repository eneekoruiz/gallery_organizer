import os
import json
import re
from pathlib import Path
import threading
import tempfile

APPLE_DB_FILE = Path(__file__).resolve().parents[2] / "apple_db.json"
ICLOUD_PHOTOS_DIR = Path(os.environ.get(
    "GALLERY_ICLOUD_PHOTOS_DIR", Path.home() / "Pictures" / "iCloud Photos" / "Photos"
))

_apple_db = {}
_apple_db_lock = threading.Lock()

_uuid_re = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.I)
_apple_img_re = re.compile(r'^img_[e]?\d{1,5}(_\d+)?\.(jpg|jpeg|png|heic|mov|mp4)$', re.I)
_android_date_re = re.compile(r'^(img|vid)[-_]?(19|20)\d{6}', re.I)
_wa_re = re.compile(r'^(img|vid|audi?o?|ptv)[-_]?(19|20)\d{6}[-_]?wa\d+', re.I)
_screenshot_re = re.compile(r'^(screenshot|screen|captura)[-_]?(19|20)?', re.I)
_snapchat_re = re.compile(r'^snapchat[-_]?\d+', re.I)

def load_apple_db(force_reload=False, *, strict=False):
    global _apple_db
    with _apple_db_lock:
        if _apple_db and not force_reload:
            return _apple_db
        if APPLE_DB_FILE.exists():
            try:
                with open(APPLE_DB_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("El índice iCloud no contiene un objeto JSON")
                _apple_db = data
            except (OSError, ValueError):
                if strict:
                    raise
                _apple_db = {}
        else:
            _apple_db = {}
    return _apple_db

def save_apple_db():
    with _apple_db_lock:
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=APPLE_DB_FILE.parent, delete=False
            ) as file:
                temp_path = Path(file.name)
                # Encode records in C without allocating a second copy of the whole index.
                file.write("{")
                for index, (path, info) in enumerate(_apple_db.items()):
                    if index:
                        file.write(",")
                    file.write(json.dumps(path) + ":" + json.dumps(info, separators=(",", ":")))
                file.write("}")
            os.replace(temp_path, APPLE_DB_FILE)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)


def detect_device_origin(path_str):
    if not path_str:
        return 'other'
    p_str = str(path_str)
    file_name = os.path.basename(p_str)
    ext = os.path.splitext(file_name)[1].lower()
    p_norm = p_str.replace('\\', '/').lower()

    if "icloud photos" in p_norm or "apple" in p_norm or "iphone" in p_norm:
        return "apple"
    if ext in [".heic", ".heif"]:
        return "apple"

    try:
        db = load_apple_db()
        if p_str in db or file_name in db:
            return "apple"
    except Exception:
        pass

    if _android_date_re.match(file_name) or _wa_re.match(file_name) or _screenshot_re.match(file_name) or _snapchat_re.match(file_name):
        return "android"
    if "whatsapp" in p_norm or "android" in p_norm:
        return "android"

    if _uuid_re.match(file_name) or _apple_img_re.match(file_name):
        return "apple"

    return "other"

def is_apple_photo(path_str):
    return detect_device_origin(path_str) == "apple"

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
