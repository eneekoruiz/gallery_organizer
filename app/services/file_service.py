from app.globals import cache_lock
from flask import Blueprint, jsonify, request
import os
import json
import hashlib
from pathlib import Path
from app.globals import RESULTADOS_DIR, get_gallery_cache, clear_gallery_cache
from app.utils.files import calculate_sharpness, calculate_dhash, find_relocated_file, safe_remove_file, get_file_key
from app.utils.workers import run_recluster, run_smart_clean, run_auto_merge

def api_duplicates():
    try:
        data = request.json or {}
        filepath = data.get('path')
        if not filepath:
            return jsonify({"duplicate": None, "sharpness": 0.0}), 200
            
        real_path = find_relocated_file(filepath)
        if not real_path or not os.path.exists(real_path):
            return jsonify({"duplicate": None, "sharpness": 0.0}), 200
        filepath = real_path
            
        path_obj = Path(filepath)
        parent_dir = path_obj.parent
        
        current_sharpness = calculate_sharpness(filepath)
        current_hash = calculate_dhash(filepath)
        
        if current_hash is None:
            return jsonify({"sharpness": current_sharpness, "duplicate": None})
            
        valid_exts = {".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi"}
        duplicate_info = None
        
        for other_file in parent_dir.iterdir():
            if not other_file.is_file() or other_file.name == path_obj.name: continue
            if other_file.suffix.lower() not in valid_exts: continue
            
            other_hash = calculate_dhash(str(other_file))
            if other_hash is not None and len(other_hash) == len(current_hash):
                import numpy as np
                hamming_dist = np.count_nonzero(current_hash != other_hash)
                similarity = round((1.0 - (hamming_dist / len(current_hash))) * 100, 1)
                
                if similarity >= 75.0:
                    other_sharpness = calculate_sharpness(str(other_file))
                    is_better = current_sharpness >= other_sharpness
                    duplicate_info = {
                        "other_name": other_file.name,
                        "other_path": str(other_file),
                        "similarity": similarity,
                        "other_sharpness": other_sharpness,
                        "is_current_better": is_better
                    }
                    break
                    
        return jsonify({
            "sharpness": current_sharpness,
            "duplicate": duplicate_info
        })
    except Exception as e:
        return jsonify({"sharpness": 100.0, "duplicate": None})

def api_purge_exact_duplicates():
    import hashlib
    size_map = {}
    base_dir = RESULTADOS_DIR.parent
    
    for root, dirs, files in os.walk(str(base_dir)):
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi')):
                p = Path(root) / f
                try:
                    sz = p.stat().st_size
                    if sz not in size_map: size_map[sz] = []
                    size_map[sz].append(p)
                except: pass
                
    hash_map = {}
    for sz, paths in size_map.items():
        if len(paths) > 1:
            for p in paths:
                try:
                    with cache_lock:
                        with open(p, 'rb') as f:
                            md5 = hashlib.md5(f.read()).hexdigest()
                    if md5 not in hash_map: hash_map[md5] = []
                    hash_map[md5].append(p)
                except: pass
                
    purged_count = 0
    for md5, paths in hash_map.items():
        if len(paths) > 1:
            def score_path(p):
                p_str = str(p)
                score = 0
                if 'Resultados' in p_str: score += 10
                if 'Conocidos' in p_str or 'Familia' in p_str or 'YO' in p_str: score += 10
                if '_Dudosos' in p_str: score -= 5
                return score
            sorted_paths = sorted(paths, key=score_path, reverse=True)
            for rem in sorted_paths[1:]:
                try:
                    safe_remove_file(rem)
                    purged_count += 1
                except: pass
                
    clear_gallery_cache()
    return jsonify({"success": True, "purged_count": purged_count})

def start_recluster_endpoint():
    run_recluster()
    return jsonify({"success": True})

def start_smart_clean_endpoint():
    run_smart_clean()
    return jsonify({"success": True})

def get_smart_clean_status():
    status_file = Path("smart_clean_status.json")
    if status_file.exists():
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        except Exception:
            pass
    return jsonify({"status": "Esperando...", "progress": 0})

def api_pending_sorted():
    g_cache = get_gallery_cache()
    if g_cache is None:
        from app.routes.api_gallery import get_gallery
        get_gallery()
        g_cache = get_gallery_cache() or {}
        
    items_to_sort = []
    
    if 'Personas Sin Nombre' in g_cache:
        for ident, items in g_cache['Personas Sin Nombre'].items():
            for item in items:
                items_to_sort.append(item)
                
    if 'Resultados' in g_cache:
        for ident, items in g_cache['Resultados'].items():
            for item in items:
                items_to_sort.append(item)
                
    conf_cache = {}
    if Path("confidence_cache.json").exists():
        try:
            with open("confidence_cache.json", "r", encoding="utf-8") as cf:
                conf_cache = json.load(cf)
        except Exception:
            pass

    for item in items_to_sort:
        p = item.get('path', '')
        file_key = get_file_key(p)
        item['confidence'] = conf_cache.get(file_key, 0.0)
        
    items_to_sort.sort(key=lambda x: x.get('confidence', 0.0), reverse=True)
    return jsonify({"items": items_to_sort})


def api_mass_cleanup():
    promoted = 0
    try:
        try:
            from deep_auto_classify_all import run_deep_classify
            run_deep_classify(threshold=0.65)
        except ImportError:
            pass
        if Path("deep_classify_status.json").exists():
            with open("deep_classify_status.json", "r", encoding="utf-8") as sf:
                st_data = json.load(sf)
                promoted = st_data.get("details", {}).get("promoted", 0)
    except Exception as ex:
        print("Error in mass_cleanup execution:", ex)
    clear_gallery_cache()
    return jsonify({"success": True, "moved_count": promoted})


def api_duplicates_scan():
    try:
        cache_path = Path("file_hash_cache.json")
        cache_data = {}
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
            except Exception: pass
            
        hashes = {}
        valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.mp4', '.mov'}
        cache_updated = False
        
        for root, dirs, files in os.walk(str(RESULTADOS_DIR)):
            for f in files:
                fp = Path(root) / f
                if fp.suffix.lower() in valid_exts and fp.exists():
                    try:
                        stat = fp.stat()
                        size = stat.st_size
                        mtime = stat.st_mtime
                        if size < 5000: continue
                        
                        fpath_str = str(fp)
                        h_val = None
                        
                        if fpath_str in cache_data and cache_data[fpath_str]['size'] == size and cache_data[fpath_str]['mtime'] == mtime:
                            h_val = cache_data[fpath_str]['hash']
                        else:
                            with open(fp, 'rb') as fh:
                                chunk = fh.read(1024 * 1024)
                            h_val = hashlib.md5(chunk + str(size).encode()).hexdigest()
                            cache_data[fpath_str] = {'size': size, 'mtime': mtime, 'hash': h_val}
                            cache_updated = True
                            
                        if h_val not in hashes: hashes[h_val] = []
                        hashes[h_val].append({'path': fpath_str, 'size': size, 'name': fp.name})
                    except Exception: pass
                    
        if cache_updated:
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f)
            except Exception: pass

        groups = []
        total_waste_bytes = 0
        for h_val, file_list in hashes.items():
            if len(file_list) > 1:
                group_waste = sum(f['size'] for f in file_list[1:])
                total_waste_bytes += group_waste
                groups.append({
                    'hash': h_val,
                    'files': file_list,
                    'waste_mb': round(group_waste / (1024 * 1024), 2)
                })
                
        groups.sort(key=lambda x: x['waste_mb'], reverse=True)
        return jsonify({
            'groups': groups,
            'total_waste_mb': round(total_waste_bytes / (1024 * 1024), 2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def api_duplicates_clean():
    try:
        data = request.json or {}
        target_hash = data.get('hash')
        clean_all = data.get('clean_all', False)
        freed_bytes = 0
        hashes = {}
        valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.mp4', '.mov'}
        for root, dirs, files in os.walk(str(RESULTADOS_DIR)):
            for f in files:
                fp = Path(root) / f
                if fp.suffix.lower() in valid_exts and fp.exists():
                    try:
                        size = fp.stat().st_size
                        if size < 5000: continue
                        with cache_lock:
                            with open(fp, 'rb') as fh:
                                chunk = fh.read(1024 * 1024)
                        h_val = hashlib.md5(chunk + str(size).encode()).hexdigest()
                        if h_val not in hashes: hashes[h_val] = []
                        hashes[h_val].append(fp)
                    except Exception: pass
                    
        clear_gallery_cache()
        for h_val, file_list in hashes.items():
            if len(file_list) > 1:
                if clean_all or h_val == target_hash:
                    for dup_p in file_list[1:]:
                        try:
                            freed_bytes += dup_p.stat().st_size
                            safe_remove_file(dup_p)
                        except Exception as de: print("Error deleting duplicate:", de)
                            
        return jsonify({'success': True, 'freed_mb': round(freed_bytes / (1024 * 1024), 2)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def api_events():
    try:
        import datetime
        g_cache = get_gallery_cache()
        if g_cache is None:
            from app.routes.api_gallery import get_gallery
            get_gallery()
            g_cache = get_gallery_cache() or {}
            
        all_items = []
        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov"}
        
        for cat, idents in g_cache.items():
            for ident, items in idents.items():
                for item in items:
                    p_str = item.get('path')
                    if not p_str: continue
                    ext = Path(p_str).suffix.lower()
                    if ext not in valid_exts: continue
                    
                    mtime = item.get('mtime')
                    if not mtime: continue
                    dt = datetime.datetime.fromtimestamp(mtime)
                        
                    all_items.append({
                        'path': p_str,
                        'filename': Path(p_str).name,
                        'dt': dt,
                        'date_str': dt.strftime("%Y-%m-%d"),
                        'cat': cat,
                        'ident': ident
                    })
                    
        all_items.sort(key=lambda x: x['dt'])
        
        events = []
        current_event = None
        
        for item in all_items:
            if current_event is None:
                current_event = {
                    'start_date': item['dt'],
                    'end_date': item['dt'],
                    'items': [item]
                }
            else:
                time_diff = (item['dt'] - current_event['end_date']).total_seconds() / 3600.0
                if time_diff <= 48:
                    current_event['end_date'] = item['dt']
                    current_event['items'].append(item)
                else:
                    events.append(current_event)
                    current_event = {
                        'start_date': item['dt'],
                        'end_date': item['dt'],
                        'items': [item]
                    }
                    
        if current_event:
            events.append(current_event)
            
        formatted = []
        for idx, ev in enumerate(events):
            if len(ev['items']) < 2: continue
            start_s = ev['start_date'].strftime("%d/%m/%Y")
            end_s = ev['end_date'].strftime("%d/%m/%Y")
            date_lbl = start_s if start_s == end_s else f"{start_s} - {end_s}"
            
            formatted.append({
                'id': f"event_{idx+1}",
                'title': f"Evento {idx+1} ({date_lbl})",
                'date_label': date_lbl,
                'count': len(ev['items']),
                'cover': ev['items'][0]['path'],
                'items': ev['items']
            })
            
        formatted.sort(key=lambda x: x['count'], reverse=True)
        return jsonify({"events": formatted, "total_events": len(formatted)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def api_create_event_folder():
    try:
        import shutil
        data = request.json or {}
        event_name = data.get('event_name', '').strip()
        file_paths = data.get('paths', [])
        
        if not event_name or not file_paths:
            return jsonify({"error": "Nombre de evento o fotos no especificadas"}), 400
            
        safe_folder_name = "".join([c if c.isalnum() or c in " _-" else "_" for c in event_name])
        target_dir = RESULTADOS_DIR / "Eventos" / safe_folder_name
        target_dir.mkdir(parents=True, exist_ok=True)
        
        copied = 0
        for fp in file_paths:
            p = Path(fp)
            if p.exists():
                dst = target_dir / p.name
                shutil.copy2(str(p), str(dst))
                copied += 1
                
        clear_gallery_cache()
        return jsonify({
            "success": True, 
            "folder": str(target_dir), 
            "copied": copied,
            "message": f"Álbum '{safe_folder_name}' creado con {copied} fotos."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500



def api_similar_scan():
    try:
        import cv2
        cache_path = Path("file_sharpness_cache.json")
        cache_data = {}
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
            except Exception: pass
            
        valid_exts = {'.jpg', '.jpeg', '.png', '.webp'}
        image_files = []
        for root, dirs, files in os.walk(str(RESULTADOS_DIR)):
            for f in files:
                fp = Path(root) / f
                if fp.suffix.lower() in valid_exts and fp.exists():
                    image_files.append(fp)
                    
        prefixes = {}
        for fp in image_files:
            prefix = fp.stem[:14] if len(fp.stem) >= 14 else fp.stem
            if prefix not in prefixes: prefixes[prefix] = []
            prefixes[prefix].append(fp)
            
        groups = []
        cache_updated = False
        
        for pref, f_list in prefixes.items():
            if len(f_list) > 1:
                evaluated = []
                for fp in f_list:
                    score = 0.0
                    try:
                        stat = fp.stat()
                        size = stat.st_size
                        mtime = stat.st_mtime
                        fpath_str = str(fp)
                        
                        if fpath_str in cache_data and cache_data[fpath_str]['size'] == size and cache_data[fpath_str]['mtime'] == mtime:
                            score = cache_data[fpath_str]['sharpness']
                        else:
                            img = cv2.imread(fpath_str, cv2.IMREAD_GRAYSCALE)
                            if img is not None:
                                score = cv2.Laplacian(img, cv2.CV_64F).var()
                            cache_data[fpath_str] = {'size': size, 'mtime': mtime, 'sharpness': score}
                            cache_updated = True
                    except Exception: pass
                    
                    evaluated.append({
                        'path': str(fp),
                        'name': fp.name,
                        'sharpness_score': round(score, 1)
                    })
                
                evaluated.sort(key=lambda x: x['sharpness_score'], reverse=True)
                for idx, ev in enumerate(evaluated):
                    ev['is_sharpest'] = (idx == 0)
                groups.append({'group_id': pref, 'files': evaluated})
                
        if cache_updated:
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f)
            except Exception: pass
                
        groups = groups[:15]
        return jsonify({'groups': groups})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def api_similar_clean():
    try:
        import cv2
        data = request.json or {}
        group_id = data.get('group_id')
        if not group_id: return jsonify({'error': 'Falta group_id'}), 400
        valid_exts = {'.jpg', '.jpeg', '.png', '.webp'}
        f_list = []
        for root, dirs, files in os.walk(str(RESULTADOS_DIR)):
            for f in files:
                fp = Path(root) / f
                if fp.suffix.lower() in valid_exts and fp.exists():
                    prefix = fp.stem[:14] if len(fp.stem) >= 14 else fp.stem
                    if prefix == group_id: f_list.append(fp)
                        
        if len(f_list) > 1:
            evaluated = []
            for fp in f_list:
                score = 0.0
                try:
                    img = cv2.imread(str(fp), cv2.IMREAD_GRAYSCALE)
                    if img is not None: score = cv2.Laplacian(img, cv2.CV_64F).var()
                except Exception: pass
                evaluated.append((score, fp))
            evaluated.sort(key=lambda x: x[0], reverse=True)
            for _, fp in evaluated[1:]:
                try: safe_remove_file(fp)
                except Exception: pass
                
        clear_gallery_cache()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def api_sharpness():
    try:
        path = request.args.get('path')
        if not path:
            return jsonify({'sharpness': None}), 400
        score = calculate_sharpness(path)
        return jsonify({'sharpness': score})
    except Exception as e:
        return jsonify({'sharpness': None, 'error': str(e)}), 500


def api_clear_cache():
    try:
        clear_gallery_cache()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


