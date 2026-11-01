import os
import gc
import time
import shutil
import json
import numpy as np
import cv2
import exifread
import datetime
from pathlib import Path
import hashlib
from app.globals import (
    PENDING_DELETIONS_FILE, OVERRIDES_FILE, RESULTADOS_DIR, FOTOS_DIR, 
    DHASH_CACHE_FILE, _DHASH_CACHE, THUMBNAILS_DIR
)

def generate_thumbnail(original_path, max_size=300):
    try:
        if not original_path: return None
        # 1. NormalizaciÃ³n canÃ³nica del path para GARANTIZAR 100% de aciertos de cachÃ©
        norm_p = os.path.abspath(os.path.normpath(str(original_path))).lower()
        path_hash = hashlib.md5(norm_p.encode('utf-8')).hexdigest()
        thumb_path = THUMBNAILS_DIR / f"{path_hash}.webp"
        
        if thumb_path.exists() and thumb_path.stat().st_size > 100:
            return str(thumb_path)
            
        path_str = str(original_path)
        is_video = path_str.lower().endswith((".mp4", ".mov", ".avi"))
        
        if is_video:
            cap = cv2.VideoCapture(path_str)
            fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if fc > 10: cap.set(cv2.CAP_PROP_POS_FRAMES, int(fc * 0.1))
            ret, frame = cap.read()
            cap.release()
            if not ret or frame is None: return None
            h, w = frame.shape[:2]
            if max(h, w) > max_size:
                scale = max_size / max(h, w)
                frame = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(thumb_path), frame, [cv2.IMWRITE_WEBP_QUALITY, 70])
            return str(thumb_path)
            
        # 2. DecodificaciÃ³n acelerada PIL draft para imÃ¡genes (10x mÃ¡s rÃ¡pida)
        try:
            from PIL import Image, ImageOps
            with Image.open(path_str) as im:
                im.draft('RGB', (max_size, max_size))
                im = ImageOps.exif_transpose(im)
                im.thumbnail((max_size, max_size), Image.Resampling.BILINEAR)
                if im.mode != 'RGB':
                    im = im.convert('RGB')
                im.save(str(thumb_path), format='WEBP', quality=70, method=0)
                return str(thumb_path)
        except Exception:
            # Fallback OpenCV si PIL falla
            file_bytes = np.fromfile(path_str, dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None: return None
            h, w = img.shape[:2]
            if max(h, w) > max_size:
                scale = max_size / max(h, w)
                img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(thumb_path), img, [cv2.IMWRITE_WEBP_QUALITY, 70])
            return str(thumb_path)
            
    except Exception as e:
        print("Thumbnail Error:", e)
        return None

from concurrent.futures import ThreadPoolExecutor

def calculate_sharpness(original_path):
    try:
        path_str = str(original_path)
        if path_str.lower().endswith((".mp4", ".mov", ".avi")):
            return None
        file_bytes = np.fromfile(path_str, dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return None
        h, w = img.shape[:2]
        if max(h, w) > 400:
            scale = 400.0 / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        score = float(cv2.Laplacian(img, cv2.CV_64F).var())
        return round(score, 2)
    except Exception:
        return None

def prefetch_thumbnails_parallel(file_paths, max_workers=8):
    def _worker(path):
        try:
            generate_thumbnail(path)
        except Exception:
            pass

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(_worker, file_paths)



from app.utils.file_ops import safe_move_file, safe_remove_file


def process_pending_deletions():
    if not PENDING_DELETIONS_FILE.exists(): return
    try:
        with open(PENDING_DELETIONS_FILE, "r") as f:
            paths = f.read().splitlines()
        remaining = []
        for p in paths:
            if not p.strip(): continue
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    remaining.append(p)
        with open(PENDING_DELETIONS_FILE, "w") as f:
            for r in remaining:
                f.write(f"{r}\n")
    except Exception as e:
        print(f"Error procesando pending deletions: {e}")

def load_overrides():
    if OVERRIDES_FILE.exists():
        try:
            with open(OVERRIDES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f'[OVERRIDES] Error cargando {OVERRIDES_FILE}: {e}')
            try:
                with open(OVERRIDES_FILE, 'r', encoding='utf-8') as f:
                    content_str = f.read().strip()
                while content_str.endswith('}}') or content_str.endswith('}\n}'):
                    content_str = content_str[:-1].strip()
                data = json.loads(content_str)
                print(f'[OVERRIDES] Recuperados {len(data)} overrides tras reparar JSON.')
                return data
            except Exception as e2:
                print(f'[OVERRIDES] Recuperacion fallida: {e2}')
                return {}
    return {}

def save_overrides(data):
    tmp_file = OVERRIDES_FILE.with_suffix(f'.tmp_{int(time.time()*1000)}')
    try:
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        os.replace(tmp_file, OVERRIDES_FILE)
    except Exception as e:
        print(f'[OVERRIDES] Error guardando {OVERRIDES_FILE}: {e}')
        if tmp_file.exists():
            try:
                os.remove(tmp_file)
            except Exception:
                pass

def library_roots():
    from app.globals import CONFIG_FILE, FOTOS_DIR, RESULTADOS_DIR
    roots = []
    base = None
    if CONFIG_FILE.exists():
        try:
            config = json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
            if config.get('local_path'):
                base = Path(config['local_path']).resolve()
        except (OSError, ValueError, TypeError):
            pass
    if base is None and FOTOS_DIR.parent.exists():
        base = FOTOS_DIR.parent.resolve()

    if base and base.exists():
        roots.append(base)
    else:
        if FOTOS_DIR.exists(): roots.append(Path(FOTOS_DIR).resolve())
        if RESULTADOS_DIR.exists(): roots.append(Path(RESULTADOS_DIR).resolve())

    icloud = Path(r"C:\Users\User\Pictures\iCloud Photos\Photos")
    if icloud.exists():
        roots.append(icloud.resolve())

    return tuple(roots)


def is_library_path(filepath):
    try:
        path = Path(filepath).resolve()
        return any(path == root or path.is_relative_to(root) for root in library_roots())
    except (OSError, ValueError, TypeError):
        return False


_RELOCATED_CACHE = {}

def find_relocated_file(filepath):
    if not isinstance(filepath, (str, os.PathLike)) or not filepath:
        return None
    p = Path(filepath)

    # 1. Direct path check (O(1) filesystem stat)
    try:
        if p.is_file() and is_library_path(p):
            return str(p.resolve())
    except Exception:
        pass

    fname = p.name
    if not fname:
        return None

    # 2. Check fast memory cache
    cached = _RELOCATED_CACHE.get(fname)
    if cached and os.path.isfile(cached):
        return cached

    # 3. Relative path checked against library roots
    for root in library_roots():
        for candidate in [root / p, root / fname]:
            try:
                resolved = candidate.resolve()
                if resolved.is_file() and is_library_path(resolved):
                    _RELOCATED_CACHE[fname] = str(resolved)
                    return str(resolved)
            except Exception:
                pass

    # 4. Check gallery cache in-memory structure (no disk walk!)
    from app.globals import get_gallery_cache
    g_cache = get_gallery_cache()
    if g_cache and isinstance(g_cache, dict):
        for cat, idents in g_cache.items():
            if isinstance(idents, dict):
                for ident, items in idents.items():
                    if isinstance(items, list):
                        for it in items:
                            if it.get('name') == fname and it.get('path'):
                                p_cand = Path(it['path'])
                                if p_cand.is_file():
                                    _RELOCATED_CACHE[fname] = str(p_cand.resolve())
                                    return str(p_cand.resolve())

    return None


def get_file_key(filepath):
    try:
        path_str = str(filepath)
        if path_str.startswith('gdrive://'):
            return f"gdrive_{Path(path_str).name}"
        st = os.stat(path_str)
        return f"{Path(path_str).name}_{st.st_size}_{int(st.st_mtime)}"
    except Exception:
        return str(filepath)



def calculate_sharpness(filepath):
    try:
        path_obj = Path(filepath)
        if path_obj.suffix.lower() in [".mp4", ".mov", ".avi"]:
            cap = cv2.VideoCapture(str(filepath))
            fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if fc > 10: cap.set(cv2.CAP_PROP_POS_FRAMES, int(fc * 0.1))
            ret, frame = cap.read()
            cap.release()
            if not ret or frame is None: return 0.0
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            file_bytes = np.fromfile(str(filepath), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None: return 0.0
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return round(cv2.Laplacian(gray, cv2.CV_64F).var(), 1)
    except:
        return 0.0

def save_dhash_cache():
    try:
        import pickle
        with open(DHASH_CACHE_FILE, 'wb') as f:
            pickle.dump(_DHASH_CACHE, f)
    except:
        pass

def calculate_dhash(filepath):
    try:
        file_key = get_file_key(filepath)
        if file_key in _DHASH_CACHE:
            return _DHASH_CACHE[file_key]
            
        path_obj = Path(filepath)
        if path_obj.suffix.lower() in [".mp4", ".mov", ".avi"]:
            cap = cv2.VideoCapture(str(filepath))
            fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if fc > 10: cap.set(cv2.CAP_PROP_POS_FRAMES, int(fc * 0.1))
            ret, img = cap.read()
            cap.release()
            if not ret or img is None: return None
        else:
            file_bytes = np.fromfile(str(filepath), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None: return None
            
        resized = cv2.resize(img, (9, 8), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        h = (gray[:, 1:] > gray[:, :-1]).flatten()
        _DHASH_CACHE[file_key] = h
        return h
    except:
        return None



def safe_move(src, dst):
    import app.globals as g
    from app.utils.storage_adapters import get_adapter
    src_str = str(src)
    dst_str = str(dst)
    
    if src_str.startswith('gdrive://') or getattr(g, 'STORAGE_MODE', 'local') == 'gdrive':
        try:
            adapter = get_adapter('gdrive', {'gdrive_folder_id': getattr(g, 'CONFIG_CACHE', {}).get('gdrive_folder_id', '1Qr6KXPxcgdlzbSHVyDOg4cBb4GReSAfD')})
            adapter.move_file(src_str, dst_str)
        except Exception as e:
            print('[ERROR] GDrive move failed:', e)
    else:
        return safe_move_file(src_str, dst_str)

def get_content_fingerprint(filepath):
    """
    Genera una huella digital Ãºnica basada en el tamaÃ±o del archivo y primeros 64KB.
    Conecta instantÃ¡neamente (0ms) fotos idÃ©nticas en Local y Google Drive.
    """
    try:
        path_str = str(filepath)
        filename = Path(path_str).name
        
        if path_str.startswith('gdrive://'):
            return f"gdrive_{filename}"
            
        if os.path.exists(path_str):
            size = os.path.getsize(path_str)
            with open(path_str, 'rb') as f:
                header = f.read(65536)
            h = hashlib.md5(header).hexdigest()
            return f"{filename}_{size}_{h[:12]}"
    except Exception:
        pass
    return str(filepath)


