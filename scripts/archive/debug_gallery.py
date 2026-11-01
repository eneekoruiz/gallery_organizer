from flask import Blueprint, jsonify, request, Response, send_file
import os
import json
import datetime
import exifread
import cv2
import numpy as np
from pathlib import Path
from app.globals import FOTOS_DIR, RESULTADOS_DIR, get_gallery_cache, set_gallery_cache, faces_cache, CONFIG_FILE
from app.utils.faces import get_all_identities, sanitize_display_name
from app.utils.files import process_pending_deletions, load_overrides, find_relocated_file, get_file_key, generate_thumbnail



api_gallery_bp = Blueprint('api_gallery', __name__)

@api_gallery_bp.route('/identities')
def api_identities():
    return jsonify(get_all_identities())

@api_gallery_bp.route('/gallery')
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
        
    print(f'Length of seen_files: {len(seen_files)}')
    print(f'FOTOS_DIR: {FOTOS_DIR}')
    ident_to_cat_map = {id_info["identidad"]: id_info["categoria"] for id_info in get_all_identities()}
        
        for root, dirs, files in os.walk(str(base_dir)):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in valid_exts:
                    path_obj = Path(root) / file
                    try:
                        rel_path = path_obj.relative_to(base_dir)
                        parts = rel_path.parts
                        
                        if len(parts) >= 3:
                            folder = parts[0]
                            subfolder = parts[1]
                        elif len(parts) == 2:
                            folder = parts[0]
                            subfolder = parts[0]
                        else:
                            folder = base_dir.name
                            subfolder = base_dir.name
                            
                        # --- SMART ALBUM GUARD ---
                        # These are dynamic groups, NOT real persons.
                        # Exclude them from person-based indexing; their photos
                        # will be picked up by the smart album logic below.
                        SMART_ALBUM_IDENTS = {
                            'familia conmigo', 'familia sin mi', 'familia sin mí',
                            'familiares conmigo', 'familiares sin mi', 'familiares sin mí',
                            'conocidos conmigo', 'conocidos sin mi', 'conocidos sin mí',
                            'mascotas conmigo',
                        }
                        is_smart_album_folder = ident.lower() in SMART_ALBUM_IDENTS

                        if not is_smart_album_folder:
                            cat = ident_to_cat_map.get(ident)
                        else:
                            cat = '__smart_album__'
                        
                        if not is_smart_album_folder and not cat:
                            ident_l = ident.lower()
                            folder_l = folder.lower()
                            if ident == 'YO' or folder == 'YO':
                                cat, ident = 'YO', 'YO'
                            elif ident.startswith('C. '):
                                cat = 'Conocidos'
                            elif ident.startswith('F. '):
                                cat = 'Familia'
                            elif ident.startswith('Persona_') or ident.startswith('Desconocid'):
                                cat = 'Personas Sin Nombre'
                            elif 'sin_rostro' in ident_l or 'sin_rostro' in folder_l:
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
                        
                        key = (cat, ident, file)
                        is_dudoso = "_Dudosos" in str(path_obj) or "Revision_Interactiva" in str(path_obj)
                        file_key = get_file_key(str(path_obj))
                        
                        labels = []
                        if is_orig_dataset:
                            labels.append("Dataset")
                        else:
                            labels.append("IA")
                            
                        if file_key in overrides and len(overrides[file_key]) > 0:
                            labels.append("Manual")
                            
                        label = " + ".join(labels)

                        # Files from smart album folders skip the seen_files person dict
                        # but we still build their item for smart album processing.
                        if is_smart_album_folder:
                            abs_p = str(path_obj)
                            faces_in_file = faces_cache.get(abs_p, [])
                            if file_key in overrides:
                                faces_in_file = overrides[file_key]
                            ids_in_file = [f_e.get('identity') for f_e in faces_in_file if f_e.get('identity')]
                            num_f = len(ids_in_file) if ids_in_file else len(faces_cache.get(abs_p, []))
                            has_yo_flag = ('YO' in ids_in_file)
                            item_sa = {
                                "path": abs_p,
                                "name": file,
                                "status": "Clasificado",
                                "source": label,
                                "type": "video" if ext in [".mp4", ".mov", ".avi"] else "image",
                                "num_faces": num_f,
                                "has_yo": has_yo_flag,
                                "identities": list(set(ids_in_file)),
                                "mtime": path_obj.stat().st_mtime,
                                "from_smart_folder": True,
                            }
                            # Stash in a special key so the post-scan loop picks it up
                            sa_key = ('__smart_album__', ident, file)
                            seen_files[sa_key] = item_sa
                            continue
                            
                        if key in seen_files:
                            existing = seen_files[key]
                            if label not in existing["source"]:
                                existing["source"] = f"{existing['source']} + {label}"
                        else:
                            abs_p = str(path_obj)
                            faces_in_file = faces_cache.get(abs_p, [])
                            if file_key in overrides:
                                faces_in_file = overrides[file_key]
                                
                            ids_in_file = [f_e.get('identity') for f_e in faces_in_file if f_e.get('identity')]
                            num_f = len(ids_in_file) if len(ids_in_file) > 0 else len(faces_cache.get(abs_p, []))
                            has_yo = ('YO' in ids_in_file) or any(str(x).upper() == 'YO' for x in ids_in_file)
                            
                            item = {
                                "path": str(path_obj),
                                "name": file,
                                "status": "Dudoso" if is_dudoso else "Clasificado",
                                "source": label,
                                "type": "video" if ext in [".mp4", ".mov", ".avi"] else "image",
                                "num_faces": num_f,
                                "has_yo": has_yo,
                                "identities": list(set(ids_in_file)),
                                "mtime": path_obj.stat().st_mtime
                            }
                            seen_files[key] = item

                    except Exception:
                        pass

                        
    root_base = FOTOS_DIR.parent
    if root_base.exists():
        for sub in root_base.iterdir():
            if sub.is_dir():
                is_orig = (sub.name.lower() == 'fotos')
                scan_dir(sub, is_orig)
    else:
        scan_dir(FOTOS_DIR, True)
        scan_dir(RESULTADOS_DIR, False)
    
    
    print(f'Length of seen_files: {len(seen_files)}')
    print(f'FOTOS_DIR: {FOTOS_DIR}')
    ident_to_cat_map = {id_info["identidad"]: id_info["categoria"] for id_info in get_all_identities()}
    
    for (cat, ident, filename), item in seen_files.items():
        # Items from smart album folders skip person indexing
        if cat == '__smart_album__':
            continue

        clean_ident = sanitize_display_name(ident)
        if cat not in gallery: gallery[cat] = {}
        if clean_ident not in gallery[cat]: gallery[cat][clean_ident] = []
        gallery[cat][clean_ident].append(item)
        
        if filename.lower().startswith('100_'):

            event_cat = 'Eventos'
            event_ident = 'Evento Lousada'
            if event_cat not in gallery: gallery[event_cat] = {}
            if event_ident not in gallery[event_cat]: gallery[event_cat][event_ident] = []
            if not any(x['path'] == item['path'] for x in gallery[event_cat][event_ident]):
                gallery[event_cat][event_ident].append(item)
        
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
                if other_cat not in gallery: gallery[other_cat] = {}
                if clean_other_id not in gallery[other_cat]: gallery[other_cat][clean_other_id] = []
                
                if not any(x['path'] == item['path'] for x in gallery[other_cat][clean_other_id]):
                    gallery[other_cat][clean_other_id].append(item)
        
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
            grp_cat = 'Familia'
            grp_ident = 'Familia conmigo'
            if grp_cat not in gallery: gallery[grp_cat] = {}
            if grp_ident not in gallery[grp_cat]: gallery[grp_cat][grp_ident] = []
            if not any(x['path'] == item['path'] for x in gallery[grp_cat][grp_ident]):
                gallery[grp_cat][grp_ident].append(item)
        elif has_fam and not has_yo:
            grp_cat = 'Familia'
            grp_ident = 'Familia sin mí'
            if grp_cat not in gallery: gallery[grp_cat] = {}
            if grp_ident not in gallery[grp_cat]: gallery[grp_cat][grp_ident] = []
            if not any(x['path'] == item['path'] for x in gallery[grp_cat][grp_ident]):
                gallery[grp_cat][grp_ident].append(item)

        # Smart album: Conocidos conmigo / Conocidos sin mí (only if no family)
        if not has_fam:
            if has_yo and has_con:
                grp_cat = 'Conocidos'
                grp_ident = 'Conocidos conmigo'
                if grp_cat not in gallery: gallery[grp_cat] = {}
                if grp_ident not in gallery[grp_cat]: gallery[grp_cat][grp_ident] = []
                if not any(x['path'] == item['path'] for x in gallery[grp_cat][grp_ident]):
                    gallery[grp_cat][grp_ident].append(item)
            elif has_con and not has_yo:
                grp_cat = 'Conocidos'
                grp_ident = 'Conocidos sin mí'
                if grp_cat not in gallery: gallery[grp_cat] = {}
                if grp_ident not in gallery[grp_cat]: gallery[grp_cat][grp_ident] = []
                if not any(x['path'] == item['path'] for x in gallery[grp_cat][grp_ident]):
                    gallery[grp_cat][grp_ident].append(item)


        
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
            if not known_ids:
                # No overrides yet — use folder membership as fallback signal
                grp_cat = 'Familia'
                grp_ident = 'Familia conmigo'
            elif has_yo and has_fam:
                grp_cat = 'Familia'
                grp_ident = 'Familia conmigo'
            elif has_fam:
                grp_cat = 'Familia'
                grp_ident = 'Familia conmigo'  # trust folder intent
            else:
                grp_cat = 'Familia'
                grp_ident = 'Familia conmigo'

            if grp_cat not in gallery: gallery[grp_cat] = {}
            if grp_ident not in gallery[grp_cat]: gallery[grp_cat][grp_ident] = []
            if not any(x['path'] == item['path'] for x in gallery[grp_cat][grp_ident]):
                gallery[grp_cat][grp_ident].append(item)

        elif ident.lower() in {'familia sin mi', 'familia sin mí', 'familiares sin mi', 'familiares sin mí'}:
            grp_cat = 'Familia'
            grp_ident = 'Familia sin mí'
            if grp_cat not in gallery: gallery[grp_cat] = {}
            if grp_ident not in gallery[grp_cat]: gallery[grp_cat][grp_ident] = []
            if not any(x['path'] == item['path'] for x in gallery[grp_cat][grp_ident]):
                gallery[grp_cat][grp_ident].append(item)
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

            if grp_cat not in gallery: gallery[grp_cat] = {}
            if grp_ident not in gallery[grp_cat]: gallery[grp_cat][grp_ident] = []
            if not any(x['path'] == item['path'] for x in gallery[grp_cat][grp_ident]):
                gallery[grp_cat][grp_ident].append(item)

    set_gallery_cache(gallery)

    
    resp_dict = dict(gallery)
    return jsonify(resp_dict)

@api_gallery_bp.route('/metadata')
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

@api_gallery_bp.route('/stats')
def api_stats():
    gallery_cache = get_gallery_cache()
    if gallery_cache is None:
        get_gallery()
        gallery_cache = get_gallery_cache() or {}
        
    total = 0
    manual_user = 0
    ia_verified = 0
    dudosos = 0
    pendientes = 0
    breakdown = {}
    
    overrides = load_overrides()
    
    for cat, idents in (gallery_cache or {}).items():
        for ident, items in idents.items():
            count = len(items)
            total += count
            
            cat_l = cat.lower()
            ident_l = ident.lower()
            
            if 'dudoso' in cat_l or 'dudoso' in ident_l or '_dudoso' in cat_l or '_dudoso' in ident_l:
                dudosos += count
            elif 'persona' in cat_l or 'pendiente' in cat_l or 'sin organizar' in cat_l or 'sin_rostro' in cat_l or 'sin rostro' in cat_l or 'desconocid' in cat_l or 'ignorar' in cat_l or 'falso' in cat_l:
                pendientes += count
            else:
                for item in items:
                    p = item.get('path', '')
                    src = item.get('source', '')
                    if p in overrides or 'Manual' in src or 'Dataset' in src:
                        manual_user += 1
                    else:
                        ia_verified += 1
                
                label = f"[{cat}] {ident}" if cat != 'Conocidos' else ident
                breakdown[label] = breakdown.get(label, 0) + count
                
    breakdown_sorted = dict(sorted(breakdown.items(), key=lambda item: item[1], reverse=True))
                
    return jsonify({
        "total": total,
        "manual_user": manual_user,
        "ia_verified": ia_verified,
        "dudosos": dudosos,
        "pendientes": pendientes,
        "clasificadas": manual_user + ia_verified,
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

@api_gallery_bp.route('/person_avatar')
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

@api_gallery_bp.route('/thumbnail')
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

@api_gallery_bp.route('/timeline')
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

@api_gallery_bp.route('/person/evolution')
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

@api_gallery_bp.route('/map/locations')
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




