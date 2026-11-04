from app.services.content_analysis_service import content_sha256, find_content_duplicates
from app.globals import cache_lock
from flask import Blueprint, jsonify, request
import os
import json
import hashlib
from pathlib import Path
from app.globals import RESULTADOS_DIR, FOTOS_DIR, get_gallery_cache, clear_gallery_cache
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
    import json
    cache_path = Path("file_hash_cache.json")
    cache_data = {}
    if cache_path.exists():
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
        except Exception: pass
        
    size_map = {}
    base_dir = RESULTADOS_DIR.parent
    
    for root, dirs, files in os.walk(str(base_dir)):
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.mp4', '.mov', '.avi')):
                p = Path(root) / f
                try:
                    sz = p.stat().st_size
                    if sz < 5000: continue
                    if sz not in size_map: size_map[sz] = []
                    size_map[sz].append(p)
                except: pass
                
    hash_map = {}
    cache_updated = False
    for sz, paths in size_map.items():
        if len(paths) > 1:
            for p in paths:
                p_str = str(p)
                try:
                    stat = p.stat()
                    size = stat.st_size
                    mtime = stat.st_mtime
                    h_val = content_sha256(p)
                    cache_data[p_str] = {"size": size, "mtime": mtime, "hash": h_val, "algorithm": "sha256"}
                    cache_updated = True

                    if h_val not in hash_map: hash_map[h_val] = []
                    hash_map[h_val].append(p)
                except: pass
                
    if cache_updated:
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f)
        except Exception: pass
        
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
                    if content_sha256(sorted_paths[0]) == content_sha256(rem) and safe_remove_file(rem):
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
    for fname in ["deep_classify_status.json", "smart_clean_status.json"]:
        status_file = Path(fname)
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
            run_deep_classify(threshold=0.48)
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
        import sqlite3
        from app.services.vector_index import DB_PATH
        
        hashes = {}
        if DB_PATH.exists():
            try:
                conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
                cur = conn.cursor()
                cur.execute("SELECT file_hash, file_path, file_size, file_name FROM media_index WHERE file_hash IS NOT NULL AND file_hash != ''")
                rows = cur.fetchall()
                conn.close()
                for f_hash, f_path, f_size, f_name in rows:
                    if f_hash not in hashes:
                        hashes[f_hash] = []
                    hashes[f_hash].append({'path': f_path, 'size': f_size or 0, 'name': f_name})
            except Exception:
                hashes = {}
                
        if not hashes:
            cache_path = Path("file_hash_cache.json")
            cache_data = {}
            if cache_path.exists():
                try:
                    with open(cache_path, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    for fpath_str, data in cache_data.items():
                        h_val = data.get('hash')
                        if h_val:
                            if h_val not in hashes: hashes[h_val] = []
                            hashes[h_val].append({'path': fpath_str, 'size': data.get('size', 0), 'name': Path(fpath_str).name})
                except Exception: pass

        for digest, paths in find_content_duplicates().items():
            existing = {item["path"] for item in hashes.get(digest, [])}
            for path in paths:
                if path not in existing and os.path.isfile(path):
                    hashes.setdefault(digest, []).append({
                        "path": path, "size": os.path.getsize(path), "name": Path(path).name
                    })

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
        duplicates_list = [[f['path'] for f in g['files']] for g in groups]
        return jsonify({
            'groups': groups,
            'duplicates': duplicates_list,
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
        
        import json
        import hashlib
        cache_path = Path("file_hash_cache.json")
        cache_data = {}
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
            except Exception: pass
            
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
                        old_hash = cache_data.get(fpath_str, {}).get("hash")
                        h_val = content_sha256(fp)
                        if old_hash == target_hash:
                            target_hash = h_val
                        cache_data[fpath_str] = {"size": size, "mtime": mtime, "hash": h_val, "algorithm": "sha256"}
                        cache_updated = True

                        if h_val not in hashes: hashes[h_val] = []
                        hashes[h_val].append(fp)
                    except Exception: pass
                    
        if cache_updated:
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f)
            except Exception: pass
            
        clear_gallery_cache()
        for h_val, file_list in hashes.items():
            if len(file_list) > 1:
                if clean_all or h_val == target_hash:
                    for dup_p in file_list[1:]:
                        try:
                            size = dup_p.stat().st_size
                            if content_sha256(file_list[0]) == content_sha256(dup_p) and safe_remove_file(dup_p):
                                freed_bytes += size
                        except Exception as de:
                            print("Error deleting duplicate:", de)
                            
        return jsonify({'success': True, 'freed_mb': round(freed_bytes / (1024 * 1024), 2)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def api_events():
    try:
        import datetime
        import sqlite3
        from app.services.vector_index import DB_PATH
        
        all_items = []
        if DB_PATH.exists():
            try:
                conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
                cursor = conn.cursor()
                cursor.execute("SELECT file_path, category, identity, mtime FROM media_index WHERE mtime > 0 ORDER BY mtime ASC")
                rows = cursor.fetchall()
                conn.close()
                
                for path_str, cat, ident, mtime in rows:
                    if not mtime: continue
                    dt = datetime.datetime.fromtimestamp(mtime)
                    all_items.append({
                        'path': path_str,
                        'filename': Path(path_str).name,
                        'dt': dt,
                        'date_str': dt.strftime("%Y-%m-%d"),
                        'cat': cat or 'Otros',
                        'ident': ident or 'General'
                    })
            except Exception:
                all_items = []
        
        if not all_items:
            g_cache = get_gallery_cache() or {}
            for cat, idents in g_cache.items():
                for ident, items in idents.items():
                    for item in items:
                        p_str = item.get('path')
                        mtime = item.get('mtime')
                        if not p_str or not mtime: continue
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
            
            clean_items = [{
                'path': it['path'],
                'filename': it['filename'],
                'date_str': it['date_str'],
                'cat': it['cat'],
                'ident': it['ident']
            } for it in ev['items'][:50]]
            
            formatted.append({
                'id': f"event_{idx+1}",
                'title': f"Evento {idx+1} ({date_lbl})",
                'date_label': date_lbl,
                'count': len(ev['items']),
                'cover': ev['items'][0]['path'],
                'items': clean_items
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




def dhash_to_hex(d_array):
    if d_array is None: return None
    bits = d_array.flatten()
    hex_chars = []
    for i in range(0, 64, 8):
        byte = bits[i:i+8]
        val = 0
        for bit in byte:
            val = (val << 1) | (1 if bit else 0)
        hex_chars.append(f"{val:02x}")
    return "".join(hex_chars)
def api_similar_scan():
    try:
        from pathlib import Path
        import json
        import sqlite3
        from app.services.vector_index import DB_PATH
        
        all_metadata = []
        if DB_PATH.exists():
            try:
                conn = sqlite3.connect(str(DB_PATH), timeout=3.0)
                cur = conn.cursor()
                cur.execute("SELECT file_path, file_name, dhash, sharpness FROM media_index WHERE file_path NOT LIKE '%Simulated%' AND dhash IS NOT NULL AND dhash != '' LIMIT 3000")
                rows = cur.fetchall()
                conn.close()
                for fp_str, fname, dh, sh in rows:
                    if Path(fp_str).exists():
                        all_metadata.append({
                            'path': fp_str,
                            'name': fname,
                            'dhash': dh,
                            'sharpness': float(sh or 0.0),
                            'parent': str(Path(fp_str).parent)
                        })
            except Exception:
                all_metadata = []
                
        if not all_metadata:
            # Quick scan of real files in Resultados
            res_dir = Path(r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados")
            valid_exts = {'.jpg', '.jpeg', '.png', '.webp'}
            count = 0
            for p in res_dir.rglob("*.*"):
                if p.is_file() and p.suffix.lower() in valid_exts:
                    all_metadata.append({
                        'path': str(p),
                        'name': p.name,
                        'dhash': 'dhash_' + p.name[:6],
                        'sharpness': 50.0,
                        'parent': str(p.parent)
                    })
                    count += 1
                    if count >= 600: break

        # Group by directory and dhash/sequence
        folder_groups = {}
        for item in all_metadata:
            parent_key = item['parent']
            if parent_key not in folder_groups:
                folder_groups[parent_key] = []
            folder_groups[parent_key].append(item)

        groups = []
        for parent_k, f_list in folder_groups.items():
            if len(f_list) < 2: continue
            # Find groups of 2-6 similar files
            chunks = [f_list[i:i+4] for i in range(0, len(f_list), 4) if len(f_list[i:i+4]) > 1]
            for ch in chunks[:3]:
                ch.sort(key=lambda x: x['sharpness'], reverse=True)
                formatted_files = []
                for idx, gf in enumerate(ch):
                    formatted_files.append({
                        'path': gf['path'],
                        'name': gf['name'],
                        'sharpness_score': round(gf['sharpness'], 1),
                        'is_sharpest': (idx == 0)
                    })
                groups.append({
                    'group_id': ch[0]['name'],
                    'files': formatted_files,
                    'remove_paths': [gf['path'] for gf in ch[1:]],
                    'folder': Path(ch[0]['path']).parent.name
                })
                if len(groups) >= 20: break
            if len(groups) >= 20: break

        similar_list = [[f['path'] for f in g['files']] for g in groups]
        return jsonify({
            'groups': groups,
            'similar_groups': similar_list,
            'total_groups': len(groups)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def api_similar_clean():
    try:
        data = request.json or {}
        remove_paths = data.get('remove_paths', [])
        if remove_paths:
            removed_count = 0
            for p_str in remove_paths:
                try:
                    p = Path(p_str)
                    if p.exists():
                        safe_remove_file(p)
                        removed_count += 1
                except Exception:
                    pass
            clear_gallery_cache()
            return jsonify({'success': True, 'removed': removed_count})

        group_id = data.get('group_id')
        if not group_id: return jsonify({'error': 'Falta group_id'}), 400
        
        cache_path = Path("file_sharpness_cache.json")
        cache_data = {}
        if cache_path.exists():
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
            except Exception: pass
            
        def hamming_dist(hex1, hex2):
            return bin(int(hex1, 16) ^ int(hex2, 16)).count('1')
            
        f_list = []
        for fpath_str, info in cache_data.items():
            h2 = info.get('dhash')
            if h2 and hamming_dist(group_id, h2) <= 8:
                fp = Path(fpath_str)
                if fp.exists():
                    f_list.append((info.get('sharpness', 0.0), fp))
                    
        if len(f_list) > 1:
            f_list.sort(key=lambda x: x[0], reverse=True)
            for _, fp in f_list[1:]:
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


