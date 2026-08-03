from flask import Blueprint, jsonify, request, Response, send_file
import os
import json
import datetime
import exifread
import cv2
import numpy as np
import shutil
from pathlib import Path
import re
from app.globals import FOTOS_DIR, RESULTADOS_DIR, get_gallery_cache, set_gallery_cache, faces_cache, CONFIG_FILE
import app.globals as g
from app.utils.storage_adapters import get_adapter
from app.utils.faces import get_all_identities, sanitize_display_name
from app.utils.files import process_pending_deletions, load_overrides, find_relocated_file, get_file_key, generate_thumbnail, save_overrides, safe_remove_file



def api_identities():
    return jsonify(get_all_identities())

def get_gallery():
    process_pending_deletions()
    
    global FOTOS_DIR, RESULTADOS_DIR
    
    config_cache = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_cache = json.load(f)
        except Exception:
            pass
            
    mode = config_cache.get('mode', 'local')
    if mode == 'local':
        l_path = config_cache.get('local_path', '')
        if l_path:
            import pathlib
            FOTOS_DIR = pathlib.Path(l_path) / 'Fotos'
            RESULTADOS_DIR = pathlib.Path(l_path) / 'Resultados'
    
    gallery_cache = get_gallery_cache()
    if gallery_cache is not None:
        return jsonify(gallery_cache)
        
    gallery = {}
    valid_exts = {".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi"}
    seen_files = {}
    
    overrides = load_overrides()
    
    dup_data = {}
    try:
        with open('duplicate_groups.json', 'r') as df:
            dup_data = json.load(df)
    except:
        pass
    
    def scan_dir(base_dir, is_orig_dataset):
        if not base_dir.exists(): return
        ident_to_cat_map = {id_info["identidad"]: id_info["categoria"] for id_info in get_all_identities()}
        
        SMART_ALBUM_IDENTS = {
            'familia conmigo', 'familia sin mi', 'familia sin mí',
            'familiares conmigo', 'familiares sin mi', 'familiares sin mí',
            'conocidos conmigo', 'conocidos sin mi', 'conocidos sin mí',
            'mascotas conmigo',
        }

        def _walk_dir(current_dir):
            try:
                with os.scandir(current_dir) as it:
                    for entry in it:
                        if entry.is_dir(follow_symlinks=False):
                            _walk_dir(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            ext = os.path.splitext(entry.name)[1].lower()
                            if ext in valid_exts:
                                try:
                                    path_obj = Path(entry.path)
                                    rel_path = path_obj.relative_to(base_dir)
                                    parts = rel_path.parts
                                    
                                    if len(parts) >= 3:
                                        folder, subfolder = parts[0], parts[1]
                                    elif len(parts) == 2:
                                        folder, subfolder = parts[0], parts[0]
                                    else:
                                        folder, subfolder = base_dir.name, base_dir.name
                                    
                                    ident = subfolder
                                    is_smart_album_folder = ident.lower() in SMART_ALBUM_IDENTS

                                    ident_l, folder_l = ident.lower(), folder.lower()
                                    if is_smart_album_folder:
                                        cat = '__smart_album__'
                                    elif ident_l.startswith('persona') or ident_l.startswith('desconocid'):
                                        cat = 'Personas Sin Nombre'
                                    elif ident.startswith('C. '):
                                        cat = 'Conocidos'
                                    elif ident.startswith('F. '):
                                        cat = 'Familia'
                                    elif ident == 'YO' or folder == 'YO':
                                        cat, ident = 'YO', 'YO'
                                    else:
                                        cat = ident_to_cat_map.get(ident)
                                        if not cat:
                                            if 'sin_rostro' in ident_l or 'sin_rostro' in folder_l:
                                                if 'video' in ident_l or 'video' in folder_l or ext in ['.mp4', '.mov', '.avi']:
                                                    cat, ident = 'Pendientes / Sin Organizar', 'Videos Sin Rostro'
                                                else:
                                                    cat, ident = 'Pendientes / Sin Organizar', 'Fotos Sin Rostro'
                                            elif 'dudoso' in ident_l or 'dudoso' in folder_l:
                                                cat = 'Dudosos'
                                            elif 'para organizar' in ident_l or 'para organizar' in folder_l or 'pendiente' in ident_l or 'revision_interactiva' in folder_l:
                                                cat = 'Pendientes / Sin Organizar'
                                            else:
                                                cat = base_dir.name

                                    
                                    file_name = entry.name
                                    key = (cat, ident, file_name)
                                    abs_p = entry.path
                                    is_dudoso = "_Dudosos" in abs_p or "Revision_Interactiva" in abs_p
                                    
                                    st = entry.stat()
                                    file_key = f"{file_name}_{st.st_size}_{int(st.st_mtime)}"
                                    
                                    labels = ["Dataset"] if is_orig_dataset else ["IA"]
                                    if file_key in overrides and len(overrides[file_key]) > 0:
                                        labels.append("Manual")
                                    label = " + ".join(labels)

                                    if is_smart_album_folder:
                                        faces_in_file = faces_cache.get(abs_p, [])
                                        if file_key in overrides:
                                            faces_in_file = overrides[file_key]
                                        ids_in_file = [f_e.get('identity') for f_e in faces_in_file if f_e.get('identity')]
                                        num_f = len(ids_in_file) if ids_in_file else len(faces_cache.get(abs_p, []))
                                        has_yo_flag = ('YO' in ids_in_file)
                                        item_sa = {
                                            "path": abs_p,
                                            "name": file_name,
                                            "status": "Clasificado",
                                            "source": label,
                                            "type": "video" if ext in [".mp4", ".mov", ".avi"] else "image",
                                            "num_faces": num_f,
                                            "has_yo": has_yo_flag,
                                            "identities": list(set(ids_in_file)),
                                            "mtime": st.st_mtime,
                                            "from_smart_folder": True,
                                        }
                                        sa_key = ('__smart_album__', ident, file_name)
                                        seen_files[sa_key] = item_sa
                                        continue
                                        
                                    if key in seen_files:
                                        existing = seen_files[key]
                                        if label not in existing["source"]:
                                            existing["source"] = f"{existing['source']} + {label}"
                                    else:
                                        faces_in_file = faces_cache.get(abs_p, [])
                                        if file_key in overrides:
                                            faces_in_file = overrides[file_key]
                                            
                                        ids_in_file = [f_e.get('identity') for f_e in faces_in_file if f_e.get('identity')]
                                        num_f = len(ids_in_file) if len(ids_in_file) > 0 else len(faces_cache.get(abs_p, []))
                                        has_yo = ('YO' in ids_in_file) or any(str(x).upper() == 'YO' for x in ids_in_file)
                                        
                                        item = {
                                            "path": abs_p,
                                            "name": file_name,
                                            "status": "Dudoso" if is_dudoso else "Clasificado",
                                            "source": label,
                                            "type": "video" if ext in [".mp4", ".mov", ".avi"] else "image",
                                            "num_faces": num_f,
                                            "has_yo": has_yo,
                                            "identities": list(set(ids_in_file)),
                                            "mtime": st.st_mtime
                                        }
                                        seen_files[key] = item
                                except Exception:
                                    pass
            except Exception:
                pass

        _walk_dir(str(base_dir))


                        
    root_base = FOTOS_DIR.parent
    if root_base.exists():
        for sub in root_base.iterdir():
            if sub.is_dir():
                is_orig = (sub.name.lower() == 'fotos')
                scan_dir(sub, is_orig)
    else:
        if FOTOS_DIR.exists():
            scan_dir(FOTOS_DIR, True)
        if RESULTADOS_DIR.exists():
            scan_dir(RESULTADOS_DIR, False)


    # --- GDRIVE INTEGRATION ---
    if getattr(g, 'STORAGE_MODE', 'local') == 'gdrive':
        try:
            adapter = get_adapter('gdrive', {'gdrive_folder_id': getattr(g, 'CONFIG_CACHE', {}).get('gdrive_folder_id', '1Qr6KXPxcgdlzbSHVyDOg4cBb4GReSAfD')})
            cloud_files = adapter.list_files()
            for cf in cloud_files:
                # Use a tuple with size as mtime equivalent to prevent overwrites, 
                # but basically cloud files are in a flat 'inbox'
                key = (cf.get('name'), 0)
                if key not in seen_files:
                    seen_files[key] = {
                        'path': cf.get('path'),
                        'name': cf.get('name'),
                        'status': 'Nube (GDrive)',
                        'source': 'Google Drive API',
                        'type': 'image', 
                        'num_faces': 0,
                        'has_yo': False,
                        'identities': ['Desconocido'],
                        'mtime': 0,
                        'thumbnail': cf.get('thumbnail_link', '')
                    }
        except Exception as e:
            print('[ERROR] GDrive integration failed:', e)
    
    ident_to_cat_map = {id_info["identidad"]: id_info["categoria"] for id_info in get_all_identities()}
    added_paths = set()
    def add_to_gallery(cat, ident, item):

        if cat not in gallery: gallery[cat] = {}
        if ident not in gallery[cat]: gallery[cat][ident] = []
        k = (cat, ident, item['path'])
        if k not in added_paths:
            added_paths.add(k)
            gallery[cat][ident].append(item)

    for (cat, ident, filename), item in seen_files.items():
        # Items from smart album folders skip person indexing
        if cat == '__smart_album__':
            continue

        clean_ident = sanitize_display_name(ident)
        add_to_gallery(cat, clean_ident, item)
        
        if filename.lower().startswith('100_'):
            add_to_gallery('Eventos', 'Evento Lousada', item)
        
        faces_in_file = faces_cache.get(item['path'], [])
        file_k = get_file_key(item['path'])
        if file_k in overrides:
            faces_in_file = overrides[file_k]
            
        for f_entry in faces_in_file:
            other_id = f_entry.get('identity')
            if other_id and other_id != ident and not other_id.startswith('Desconocid') and not other_id.startswith('Falso_Positivo') and not other_id.startswith('Ignorar'):
                other_cat = ident_to_cat_map.get(other_id)
                if not other_cat:
                    if other_id.startswith('C. '): other_cat = 'Conocidos'
                    elif other_id.startswith('F. '): other_cat = 'Familia'
                    elif other_id == 'YO': other_cat = 'YO'
                    else: other_cat = 'Conocidos'
                    
                clean_other_id = sanitize_display_name(other_id)
                add_to_gallery(other_cat, clean_other_id, item)
        
        known_ids_in_file = set()
        for f_entry in faces_in_file:
            other_id = f_entry.get('identity')
            if other_id and not other_id.startswith('Desconocid') and not other_id.startswith('Falso_Positivo') and not other_id.startswith('Ignorar'):
                # Exclude smart album names from identity sets
                if other_id.lower() not in {
                    'familia conmigo', 'familia sin mi', 'familia sin mí',
                    'familiares conmigo', 'familiares sin mí',
                    'conocidos conmigo', 'conocidos sin mi', 'conocidos sin mí',
                }:
                    known_ids_in_file.add(other_id)
        
        has_yo = 'YO' in known_ids_in_file
        has_fam = any(x.startswith('F. ') for x in known_ids_in_file)
        has_con = any(x.startswith('C. ') for x in known_ids_in_file)

        # Smart album: Familia conmigo / Familia sin mí
        if has_yo and has_fam:
            add_to_gallery('Familia', 'Familia conmigo', item)
        elif has_fam and not has_yo:
            add_to_gallery('Familia', 'Familia sin mí', item)

        # Smart album: Conocidos conmigo / Conocidos sin mí (only if no family)
        if not has_fam:
            if has_yo and has_con:
                add_to_gallery('Conocidos', 'Conocidos conmigo', item)
            elif has_con and not has_yo:
                add_to_gallery('Conocidos', 'Conocidos sin mí', item)

        
    # Second pass: process items stashed from smart album folders
    # These get classified dynamically via face overrides written by the analysis script
    for (cat, ident, filename), item in seen_files.items():
        if cat != '__smart_album__':
            continue

        faces_in_file = faces_cache.get(item['path'], [])
        file_k = get_file_key(item['path'])
        if file_k in overrides:
            faces_in_file = overrides[file_k]

        known_ids = set()
        for f_entry in faces_in_file:
            other_id = f_entry.get('identity')
            if other_id and not other_id.startswith('Desconocid') and not other_id.startswith('Falso_Positivo') and not other_id.startswith('Ignorar'):
                known_ids.add(other_id)

        has_yo = 'YO' in known_ids
        has_fam = any(x.startswith('F. ') for x in known_ids)
        has_con = any(x.startswith('C. ') for x in known_ids)

        # Even without overrides, if folder is Familia conmigo treat as Familia conmigo
        if ident.lower() in {'familia conmigo', 'familiares conmigo'}:
            add_to_gallery('Familia', 'Familia conmigo', item)

        elif ident.lower() in {'familia sin mi', 'familia sin mí', 'familiares sin mi', 'familiares sin mí'}:
            add_to_gallery('Familia', 'Familia sin mí', item)
        else:
            # For any other smart album folder, use face-based classification
            if has_yo and has_fam:
                grp_cat, grp_ident = 'Familia', 'Familia conmigo'
            elif has_fam:
                grp_cat, grp_ident = 'Familia', 'Familia sin mí'
            elif has_yo and has_con:
                grp_cat, grp_ident = 'Conocidos', 'Conocidos conmigo'
            elif has_con:
                grp_cat, grp_ident = 'Conocidos', 'Conocidos sin mí'
            else:
                continue

            add_to_gallery(grp_cat, grp_ident, item)

    set_gallery_cache(gallery)
    return jsonify(dict(gallery))


def api_metadata():
    filepath = request.args.get('path')
    real_path = find_relocated_file(filepath)
    if not real_path:
        return jsonify({"error": "File not found"}), 404
    filepath = real_path
        
    stats = os.stat(filepath)
    size = f"{stats.st_size / (1024*1024):.2f} MB"
    mtime = datetime.datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M")
    
    res = "Desconocida"
    camera = "Desconocida"
    real_date = mtime

    if filepath.lower().endswith(('.jpg', '.jpeg', '.png')):
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
            with Image.open(filepath) as img:
                res = f"{img.width}x{img.height}"
                exif = img._getexif()
                if exif:
                    for tag, val in exif.items():
                        t_name = TAGS.get(tag, tag)
                        if t_name == 'Model':
                            camera = str(val)
                        elif t_name == 'DateTimeOriginal':
                            try:
                                parsed = datetime.datetime.strptime(str(val), '%Y:%m:%d %H:%M:%S')
                                real_date = parsed.strftime('%Y-%m-%d %H:%M')
                            except Exception:
                                pass
        except Exception:
            pass
            
    if real_date == mtime:
        import re
        match = re.search(r'(19\d{2}|20\d{2})([0-1]\d)([0-3]\d)', Path(filepath).name)
        if match:
            year, month, day = match.groups()
            try:
                parsed_date = datetime.datetime(int(year), int(month), int(day))
                real_date = f"{parsed_date.strftime('%Y-%m-%d')} (Archivo)"
            except ValueError:
                pass
    
    return jsonify({"size": size, "date": real_date, "camera": camera, "resolution": res})

def api_stats():
    gallery_cache = get_gallery_cache()
    if gallery_cache is None:
        get_gallery()
        gallery_cache = get_gallery_cache() or {}
        
    total_files = set()
    manual_files = set()
    ia_verified_files = set()
    dudosos_files = set()
    pendientes_files = set()
    breakdown = {}
    
    overrides = load_overrides()
    
    for cat, idents in (gallery_cache or {}).items():
        for ident, items in idents.items():
            count = len(items)
            cat_l = cat.lower()
            ident_l = ident.lower()
            
            label = f"[{cat}] {ident}" if cat != 'Conocidos' else ident
            breakdown[label] = breakdown.get(label, 0) + count
            
            for item in items:
                p = item.get('path', '')
                total_files.add(p)
                
                if 'dudoso' in cat_l or 'dudoso' in ident_l or '_dudoso' in cat_l or '_dudoso' in ident_l:
                    dudosos_files.add(p)
                elif 'persona' in cat_l or 'pendiente' in cat_l or 'sin organizar' in cat_l or 'sin_rostro' in cat_l or 'sin rostro' in cat_l or 'desconocid' in cat_l or 'ignorar' in cat_l or 'falso' in cat_l:
                    pendientes_files.add(p)
                else:
                    src = item.get('source', '')
                    if p in overrides or 'Manual' in src or 'Dataset' in src:
                        manual_files.add(p)
                    else:
                        ia_verified_files.add(p)
                        
    breakdown_sorted = dict(sorted(breakdown.items(), key=lambda item: item[1], reverse=True))
                
    return jsonify({
        "total": len(total_files),
        "manual_user": len(manual_files),
        "ia_verified": len(ia_verified_files),
        "dudosos": len(dudosos_files),
        "pendientes": len(pendientes_files),
        "clasificadas": len(manual_files) + len(ia_verified_files),
        "breakdown": breakdown_sorted
    })

def find_avatar_image(target_dir):
    valid_exts = {".jpg", ".jpeg", ".png"}
    if not target_dir: return None
    if isinstance(target_dir, str): target_dir = Path(target_dir)
    if not target_dir.exists(): return None
    if target_dir.is_file() and target_dir.suffix.lower() in valid_exts:
        return str(target_dir.resolve())
    if target_dir.is_dir():
        for root, dirs, files in os.walk(str(target_dir)):
            for f in files:
                if Path(f).suffix.lower() in valid_exts:
                    full_p = os.path.join(root, f)
                    try:
                        if os.path.getsize(full_p) > 1024:
                            return full_p
                    except:
                        pass
    return None

def api_person_avatar():
    cat = request.args.get('cat')
    ident = request.args.get('ident')
    if not cat or not ident:
        return "Missing params", 400
        
    first_img_path = None
    
    g_cache = get_gallery_cache()
    if g_cache and cat in g_cache and ident in g_cache[cat]:
        items = g_cache[cat][ident]
        valid_exts = {".jpg", ".jpeg", ".png"}
        for it in items:
            p = it.get('path')
            if p and Path(p).suffix.lower() in valid_exts and os.path.exists(p):
                first_img_path = p
                break

    if not first_img_path:
        first_img_path = find_avatar_image(RESULTADOS_DIR / cat / ident)
    if not first_img_path:
        first_img_path = find_avatar_image(FOTOS_DIR / cat / ident)
        
    if not first_img_path:
        for base_dir in [RESULTADOS_DIR, FOTOS_DIR]:
            if not base_dir or not base_dir.exists(): continue
            try:
                for sub in base_dir.iterdir():
                    if sub.is_dir():
                        candidate = find_avatar_image(sub / ident)
                        if candidate:
                            first_img_path = candidate
                            break
            except Exception:
                pass
            if first_img_path: break
            
    if not first_img_path:
        default_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 24 24" fill="#555"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>'''
        return Response(default_svg, mimetype='image/svg+xml')



        
    face_box = None
    overrides = load_overrides()
    file_key = get_file_key(first_img_path)
    
    if file_key in overrides:
        for ov in overrides[file_key]:
            if ov.get('identity') == ident:
                face_box = ov
                break
                
    if not face_box and first_img_path in faces_cache:
        for fc in faces_cache[first_img_path]:
            if fc.get('identity') == ident or fc.get('predicted_identity') == ident or fc.get('name') == ident:
                face_box = fc
                break
        # Only fallback if there's ONLY 1 face in the entire photo
        if not face_box and len(faces_cache[first_img_path]) == 1:
            face_box = faces_cache[first_img_path][0]

                
    try:
        file_bytes = np.fromfile(first_img_path, dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is None: return "Bad image", 404
        
        cropped = None
        if face_box:
            try:
                x, y, w, h = int(face_box['x']), int(face_box['y']), int(face_box['width']), int(face_box['height'])
                pad_x = int(w * 0.2)
                pad_y = int(h * 0.2)
                x1 = max(0, x - pad_x)
                y1 = max(0, y - pad_y)
                x2 = min(img.shape[1], x + w + pad_x)
                y2 = min(img.shape[0], y + h + pad_y)
                if x2 > x1 and y2 > y1:
                    cropped = img[y1:y2, x1:x2]
            except:
                pass
                
        if cropped is None or cropped.size == 0:
            h, w = img.shape[:2]
            sz = min(h, w)
            cropped = img[h//2 - sz//2 : h//2 + sz//2, w//2 - sz//2 : w//2 + sz//2]
            if cropped.size == 0:
                return "Invalid dimensions", 400
                
        _, buf = cv2.imencode('.jpg', cropped)
        res = Response(buf.tobytes(), mimetype='image/jpeg')
        res.headers['Cache-Control'] = 'public, max-age=86400'
        return res
    except Exception as e:
        return str(e), 500

def api_thumbnail():
    try:
        filepath = request.args.get('path')
        if not filepath:
            return jsonify({"error": "no path"}), 400
            
        real_path = find_relocated_file(filepath)
        if not real_path:
            return jsonify({"error": "not found"}), 404
            
        thumb = generate_thumbnail(real_path)
        if thumb and os.path.exists(thumb):
            resp = send_file(thumb, mimetype='image/webp')
            resp.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            return resp
        elif os.path.exists(real_path):
            return send_file(real_path, conditional=True)
        else:
            return jsonify({"error": "file gone"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def api_timeline():
    try:
        year = request.args.get('year')
        g_cache = get_gallery_cache()
        if g_cache is None:
            get_gallery()
            g_cache = get_gallery_cache() or {}
            
        items = []
        for cat, idents in g_cache.items():
            for ident, file_list in idents.items():
                for item in file_list:
                    p = item.get('path', '')
                    mtime = item.get('mtime') or (os.path.getmtime(p) if p and os.path.exists(p) else None)
                    if mtime:
                        item_year = str(datetime.datetime.fromtimestamp(mtime).year)
                        if not year or item_year == str(year):
                            items.append(item)
                            
        return jsonify(items)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def api_person_evolution():
    try:
        identity = request.args.get('identity', 'YO')
        g_cache = get_gallery_cache()
        if g_cache is None:
            get_gallery()
            g_cache = get_gallery_cache() or {}
            
        items = []
        for cat, idents in g_cache.items():
            if identity in idents:
                items.extend(idents[identity])
                
        items.sort(key=lambda x: x.get('mtime', 0))
        return jsonify({"identity": identity, "count": len(items), "items": items})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def api_map_locations():
    try:
        import elite_features
        g_cache = get_gallery_cache()
        if g_cache is None:
            get_gallery()
            g_cache = get_gallery_cache() or {}
            
        all_paths = []
        for cat, idents in g_cache.items():
            for ident, items in idents.items():
                for it in items:
                    p = it.get('path')
                    if p: all_paths.append(p)
                    
        locations = elite_features.get_exif_gps_locations(all_paths)
        return jsonify({"locations": locations, "count": len(locations)})
    except Exception as e:
        return jsonify({"locations": [], "count": 0, "error": str(e)})


def api_remove_from_folder():
    data = request.json
    filepath = data.get('path')
    cat = data.get('cat')
    ident = data.get('ident')
    
    if not filepath or not ident:
        return jsonify({"error": "Faltan parámetros"}), 400
        
    try:
        p_obj = Path(filepath)
        
        # Save manual override to Desconocidos
        overrides = load_overrides()
        file_key = get_file_key(filepath)
        overrides[file_key] = [{
            'x': 0, 'y': 0, 'width': 0, 'height': 0,
            'identity': 'Desconocida'
        }]
        save_overrides(overrides)
        
        # Invalidate gallery cache
        set_gallery_cache(None)
        
        # Move physical file if in Resultados
        if p_obj.exists() and RESULTADOS_DIR in p_obj.parents:
            target_dir = RESULTADOS_DIR / 'Personas Sin Nombre' / 'Desconocidos'
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / p_obj.name
            if target_path.exists() and target_path != p_obj:
                target_path = target_dir / f"{p_obj.stem}_removed{p_obj.suffix}"
            try:
                shutil.move(str(p_obj), str(target_path))
            except Exception as me:
                print("Physical move error:", me)
                
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_delete():
    data = request.json
    filepath = data.get('path')
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "Archivo no encontrado"}), 404
        
    orig_path = Path(filepath)
    try:
        if orig_path.is_relative_to(FOTOS_DIR):
            return jsonify({"error": "Dataset protegido: Las fotos del dataset manual original no pueden eliminarse físicamente."}), 403
    except ValueError:
        pass
        
    try:
        safe_remove_file(orig_path)
        set_gallery_cache(None)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_delete_group():
    try:
        data = request.json
        cat = data.get('cat')
        ident = data.get('ident')
        if not cat or not ident:
            return jsonify({"error": "Parámetros insuficientes"}), 400
            
        group_dir = RESULTADOS_DIR / cat / ident
        if group_dir.exists() and group_dir.is_dir():
            shutil.rmtree(str(group_dir), ignore_errors=True)
            set_gallery_cache(None)
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Carpeta no encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_batch_move():
    from app.globals import detector, recognizer
    import pickle
    
    try:
        data = request.json or {}
        files = data.get('files', [])
        target_cat = data.get('target_cat')
        target_ident = data.get('target_ident')
        
        if not files or not target_cat or not target_ident:
            return jsonify({"error": "Parámetros incompletos"}), 400
            
        target_dir = RESULTADOS_DIR / target_cat / target_ident
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            
        moved_count = 0
        new_features = []
        
        # Use globals if available, otherwise create
        local_detector = detector
        local_recognizer = recognizer
        if local_detector is None:
            local_detector = cv2.FaceDetectorYN.create(str(Path("models/face_detection_yunet.onnx")), "", (320, 320))
        if local_recognizer is None:
            local_recognizer = cv2.FaceRecognizerSF.create(str(Path("models/face_recognition_sface.onnx")), "")
            
        overrides = load_overrides()
        
        for fpath in files:
            p_obj = Path(fpath)
            if p_obj.exists():
                dest = target_dir / p_obj.name
                if dest.exists() and dest != p_obj:
                    dest = target_dir / f"moved_{p_obj.name}"
                try:
                    shutil.move(str(p_obj), str(dest))
                    moved_count += 1
                    
                    file_k = get_file_key(str(dest))
                    overrides[file_k] = [{
                        'x': 0, 'y': 0, 'width': 0, 'height': 0,
                        'identity': target_ident
                    }]
                    
                    img = cv2.imread(str(dest))
                    if img is not None and local_detector is not None and local_recognizer is not None:
                        h, w = img.shape[:2]
                        local_detector.setInputSize((w, h))
                        _, faces = local_detector.detect(img)
                        if faces is not None and len(faces) > 0:
                            aligned = local_recognizer.alignCrop(img, faces[0])
                            feat = local_recognizer.feature(aligned)
                            new_features.append(feat)
                except Exception as e:
                    print(f"Error moving {fpath}:", e)
                    
        save_overrides(overrides)
        
        if new_features:
            try:
                centroids = {}
                if os.path.exists('centroids.pkl'):
                    with open('centroids.pkl', 'rb') as cfile:
                        centroids = pickle.load(cfile)
                        
                key = (target_cat, target_ident)
                existing = centroids.get(key)
                all_f = new_features + ([existing] if existing is not None else [])
                avg_f = np.mean(all_f, axis=0)
                avg_f = avg_f / np.linalg.norm(avg_f)
                centroids[key] = avg_f
                
                with open('centroids.pkl', 'wb') as cfile:
                    pickle.dump(centroids, cfile)
                print(f"✓ Re-trained AI centroid for {target_ident} with {len(new_features)} moved faces!")
            except Exception as e:
                print("Centroid retrain error:", e)
                
        set_gallery_cache(None)
        
        return jsonify({
            "status": "success",
            "moved": moved_count,
            "retrained_faces": len(new_features)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_search_semantic():
    query = request.args.get('q', '')
    if not query:
        return jsonify({"results": []})
        
    gallery_cache = get_gallery_cache()
    if gallery_cache is None:
        get_gallery()
        gallery_cache = get_gallery_cache() or {}
        
    import elite_features
    results = elite_features.search_semantic_keywords(gallery_cache, query)
    return jsonify({"query": query, "count": len(results), "results": results})





