from app.utils.files import get_file_key
from app.services.apple_service import detect_device_origin
from app.services.group_album_service import group_albums, is_group_album, trusted_identities
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
from app.globals import APP_DIR, FOTOS_DIR, RESULTADOS_DIR, THUMBNAILS_DIR, get_gallery_cache, set_gallery_cache, faces_cache, CONFIG_FILE
import threading as _threading
_GALLERY_SCAN_LOCK = _threading.Lock()
import app.globals as g
from app.utils.storage_adapters import get_adapter
from app.utils.faces import get_all_identities, sanitize_display_name
from app.utils.files import process_pending_deletions, load_overrides, find_relocated_file, get_file_key, generate_thumbnail, save_overrides, safe_remove_file


def is_genuine_manual_override(ov_list):
    if not ov_list or not isinstance(ov_list, list):
        return False
    for ov in ov_list:
        if not isinstance(ov, dict):
            continue
        try:
            x = float(ov.get('x', 0))
            y = float(ov.get('y', 0))
            w = float(ov.get('width', 0))
            h = float(ov.get('height', 0))
        except (ValueError, TypeError):
            continue
        # Reject fake full-image dummy bounding boxes
        if (x == 0.0 and y == 0.0 and w == 100.0 and h == 100.0) or \
           (x == 10.0 and y == 10.0 and w == 100.0 and h == 100.0) or \
           (x == 100.0 and y == 100.0 and w == 100.0 and h == 100.0):
            continue
        # Reject automated script predictions
        if ov.get('from_familia_conmigo_analysis'):
            continue
        if ov.get('is_manual') is False:
            continue
        # Accept only if genuine human confirmation or explicit is_manual
        if ov.get('provenance') in ('human_confirmed', 'human') or ov.get('is_manual') is True:
            if w > 10 and h > 10 and ov.get('identity'):
                return True
    return False



def api_identities():
    return jsonify(get_all_identities())

def get_gallery(force_reload=False):
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
    
    from flask import has_request_context, has_app_context
    if not force_reload and has_request_context():
        force_reload = (request.args.get('force') == 'true')
    gallery_cache = get_gallery_cache()
    if gallery_cache is not None and not force_reload:
        return jsonify(gallery_cache) if has_app_context() else gallery_cache

    gallery = {}
    valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".mp4", ".mov", ".avi"}
    seen_files = {}
    
    overrides = load_overrides()
    
    import pickle, os
    dim_cache = {}
    dim_file = os.path.join(str(FOTOS_DIR.parent), 'dim_cache_v2.pkl')
    if os.path.exists(dim_file):
        try:
            with open(dim_file, 'rb') as f:
                dim_cache = pickle.load(f)
        except Exception as e:
            print(f'[WARN] dim_cache load failed: {e}')
            
    qual_cache = {}
    qual_file = os.path.join(str(FOTOS_DIR.parent), 'quality_cache_v2.pkl')
    if os.path.exists(qual_file):
        try:
            with open(qual_file, 'rb') as f:
                qual_cache = pickle.load(f)
        except Exception as e:
            print(f'[WARN] qual_cache load failed: {e}')
    
    dup_data = {}
    try:
        with open('duplicate_groups.json', 'r') as df:
            dup_data = json.load(df)
    except Exception as e:
        print(f'[WARN] duplicate_groups.json load failed: {e}')
    
    from app.globals import set_gallery_scan_progress
    set_gallery_scan_progress(0.0)

    all_file_targets = []
    
    def gather_files(base_dir, is_orig_dataset):
        if not base_dir.exists():
            return
        for root, dirs, files in os.walk(str(base_dir)):
            parts = Path(root).relative_to(base_dir).parts
            if "Ignorar" in parts or any(p.startswith("Falso_Positivo") or p.startswith("Ignorar_") for p in parts):
                continue
            for file in files:
                f_up = file.upper()
                if f_up.startswith("!00_") or f_up.startswith("_00_") or "CENTROIDE" in f_up:
                    continue
                ext = os.path.splitext(file)[1].lower()
                if ext in valid_exts:
                    all_file_targets.append((os.path.join(root, file), is_orig_dataset, base_dir))

    root_base = FOTOS_DIR.parent
    if root_base.exists():
        for sub in root_base.iterdir():
            if sub.is_dir():
                is_orig = (sub.name.lower() == 'fotos')
                gather_files(sub, is_orig)
    else:
        if FOTOS_DIR.exists():
            gather_files(FOTOS_DIR, True)
        if RESULTADOS_DIR.exists():
            gather_files(RESULTADOS_DIR, False)


    total_files = len(all_file_targets)
    processed = 0

    KNOWN_CATEGORIES = {"Conocidos", "Familia", "YO", "Profesores", "Lugares", "Eventos", "Mascotas", "Objetos", "Recuerdos", "Publicaciones_Instagram"}
    ident_to_cat_map = {id_info["identidad"]: id_info["categoria"] for id_info in get_all_identities()}
    classified_filenames = set()

    for filepath, is_orig_dataset, base_dir in all_file_targets:
        try:
            abs_p = filepath
            abs_p_l = abs_p.lower()
            path_obj = Path(abs_p)
            rel_path = path_obj.relative_to(base_dir)
            parts = rel_path.parts
            
            # Detectar subcarpeta _Dudosos específica de persona: e.g. ('Conocidos', 'C. Pablo Luque', '_Dudosos', 'IMG_001.JPG')
            folder_dudoso = any(p.lower() in ('_dudosos', 'dudoso', 'dudosos', 'revision_interactiva') for p in parts[:-1])
            is_in_person_dudosos = (len(parts) >= 4 and parts[0] in KNOWN_CATEGORIES and parts[2].lower() in ('_dudosos', 'dudoso', 'dudosos'))
            
            if is_in_person_dudosos:
                folder, subfolder = parts[0], parts[1]
                is_dudoso = True
            elif len(parts) >= 3:
                folder, subfolder = parts[0], parts[1]
                is_dudoso = folder_dudoso
                # If folder is Dudosos and subfolder is a person, preserve person identity and mark dudoso
                if folder.lower() in ('dudosos', '_dudosos') and (subfolder.startswith(('C.', 'C ', 'F.', 'F ', 'YO', 'P.', 'M.')) or subfolder in ident_to_cat_map):
                    folder = ident_to_cat_map.get(subfolder) or ('Conocidos' if subfolder.startswith(('C.', 'C ')) else 'Familia' if subfolder.startswith(('F.', 'F ')) else 'YO' if subfolder == 'YO' else 'Profesores' if subfolder.startswith('P.') else 'Mascotas' if subfolder.startswith('M.') else 'Conocidos')
                    is_dudoso = True
            elif len(parts) == 2:
                folder, subfolder = parts[0], parts[0]
                is_dudoso = folder_dudoso
            else:
                folder, subfolder = base_dir.name, base_dir.name
                is_dudoso = folder_dudoso
            
            ident = subfolder
            is_smart_album_folder = is_group_album(ident)
            folder_l = folder.lower()
            subfolder_l = subfolder.lower()
            ext = os.path.splitext(path_obj.name)[1].lower()

            if is_smart_album_folder:
                cat = '__smart_album__'
            elif is_in_person_dudosos or (folder in KNOWN_CATEGORIES and not ("_dudoso" in folder_l or "_dudoso" in subfolder_l)):
                cat = folder
                ident = subfolder
                if folder == "YO" or subfolder == "YO":
                    cat, ident = "YO", "YO"
            elif "para revisar" in abs_p_l or "para organizar" in folder_l or "pendiente" in folder_l or "para organizar" in subfolder_l:
                cat = "📋 Revisión / Por Organizar"
                ident = "⏳ Pendientes de Organizar"
            elif "_dudosos" in abs_p_l or "dudoso" in subfolder_l or "dudoso" in folder_l:
                cat = "📋 Revisión / Por Organizar"
                ident = "⚠️ Dudosos / Baja Confianza"
            elif "sin_rostro" in abs_p_l or "sin_rostro" in folder_l or "sin_rostro" in subfolder_l:
                cat = "📋 Revisión / Por Organizar"
                ident = "🎬 Vídeos Sin Rostro" if ext in [".mp4", ".mov", ".avi"] else "📷 Fotos Sin Rostro"
            elif folder == "Personas Sin Nombre" or "desconocid" in folder_l or "desconocid" in subfolder_l:
                cat = "📋 Revisión / Por Organizar"
                if "persona nueva" in subfolder_l or "persona #" in subfolder_l:
                    ident = f"👤 {subfolder}"
                else:
                    ident = "❓ Desconocidos (Por Identificar)"
            elif folder == "YO" or subfolder == "YO":
                cat, ident = "YO", "YO"
            else:
                cat = ident_to_cat_map.get(ident, folder)

            file_name = path_obj.name
            is_icloud_file = ("icloud photos" in abs_p_l or base_dir.name == "Photos")
            if not is_icloud_file and not is_dudoso and cat != "📋 Revisión / Por Organizar":
                classified_filenames.add(file_name.lower())
            key = (cat, ident, file_name)
            is_dudoso = is_dudoso or folder_dudoso
            
            st = os.stat(abs_p)
            file_key = f"{file_name}_{st.st_size}_{int(st.st_mtime)}"
            
            is_dataset_file = bool(is_orig_dataset or re.match(r'^(Foto|Fotos|Video|Videos|Vídeo|Vídeos)\b', file_name, re.IGNORECASE) or ('/Fotos/' in abs_p.replace('\\', '/')))
            is_manual_file = is_genuine_manual_override(overrides.get(file_key))
            
            labels = ["Dataset"] if is_dataset_file else ["IA"]
            if is_manual_file:
                labels.append("Manual")
            if is_dudoso:
                labels.append("⚠️ Por Confirmar")
            label = " + ".join(labels)
            
            if is_smart_album_folder:
                faces_in_file = faces_cache.get(get_file_key(abs_p), [])
                if file_key in overrides:
                    faces_in_file = overrides[file_key]
                ids_in_file = [f_e.get('identity') for f_e in faces_in_file if f_e.get('identity')]
                num_f = len(ids_in_file) if ids_in_file else len(faces_cache.get(get_file_key(abs_p), []))
                has_yo_flag = ('YO' in ids_in_file)
                item_sa = {
                    "path": abs_p,
                    "name": file_name,
                    "status": "Clasificado",
                    "source": label,
                    "is_dataset": is_dataset_file,
                    "is_manual": is_manual_file,
                    "type": "video" if ext in [".mp4", ".mov", ".avi"] else "image",
                    "num_faces": num_f,
                    "has_yo": has_yo_flag,
                    "identities": list(set(ids_in_file)),
                    "mtime": st.st_mtime,
                    "is_apple": (detect_device_origin(abs_p) == "apple"),
                    "device_origin": detect_device_origin(abs_p),
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
                faces_in_file = faces_cache.get(get_file_key(abs_p), [])
                if file_key in overrides:
                    faces_in_file = overrides[file_key]
                    
                ids_in_file = [f_e.get('identity') for f_e in faces_in_file if f_e.get('identity')]
                num_f = len(ids_in_file) if len(ids_in_file) > 0 else len(faces_cache.get(get_file_key(abs_p), []))
                has_yo = ('YO' in ids_in_file) or any(str(x).upper() == 'YO' for x in ids_in_file)
                
                item = {
                    "path": abs_p,
                    "name": file_name,
                    "status": "Dudoso" if is_dudoso else "Clasificado",
                    "is_dudoso": bool(is_dudoso),
                    "source": label,
                    "is_dataset": is_dataset_file,
                    "is_manual": is_manual_file,
                    "type": "video" if ext in [".mp4", ".mov", ".avi"] else "image",
                    "num_faces": num_f,
                    "has_yo": has_yo,
                    "identities": list(set(ids_in_file)),
                    "mtime": st.st_mtime,
                    "confidence": max(
                        (float(f_e.get("confidence", 0) or f_e.get("score", 0) or 0)
                         for f_e in faces_in_file
                         if str(f_e.get("identity", "")).strip() == str(ident).strip()),
                        default=0.0
                    ),
                    "is_apple": (detect_device_origin(abs_p) == "apple"),
                    "device_origin": detect_device_origin(abs_p),
                    "orig_width": dim_cache.get(get_file_key(abs_p), [0, 0])[0],
                    "orig_height": dim_cache.get(get_file_key(abs_p), [0, 0])[1],
                    "quality_score": qual_cache.get(get_file_key(abs_p), 100.0),
                    "faces": [{"box": f_e.get("box") or [f_e.get("x", 0), f_e.get("y", 0), f_e.get("width", 0), f_e.get("height", 0)], "identity": f_e.get("identity", "Desconocido"), "confidence": f_e.get("confidence", f_e.get("score", 0))} for f_e in faces_in_file]
                }
                seen_files[key] = item
        except Exception:
            pass
            
        processed += 1
        if total_files > 0 and (processed % 50 == 0 or processed == total_files):
            set_gallery_scan_progress((processed / total_files) * 100.0)

    set_gallery_scan_progress(100.0)


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
    added_names = set()
    def add_to_gallery(cat, ident, item):
        fname_upper = str(item.get('name', '')).upper()
        pname_upper = str(item.get('path', '')).replace('\\', '/').split('/')[-1].upper()
        if fname_upper.startswith('!00_') or fname_upper.startswith('_00_') or 'CENTROIDE' in fname_upper or 'CENTROIDE' in pname_upper:
            return  # Archivos de centroide interno: NUNCA agregar como foto a la galería
        if isinstance(ident, str):
            ident = sanitize_display_name(ident)
            if ident.startswith('? ') or ident.startswith('?'):
                ident = ident.lstrip('?').strip()
        cat_l = str(cat).lower()
        ident_l = str(ident).lower()
        p_l = str(item.get('path', '')).lower()
        
        # Check if ident is a known person identity
        clean_id_check = ident.replace('👤', '').replace('⚠️', '').replace('⏳', '').replace('❓', '').strip()
        is_known_person = (
            clean_id_check in ident_to_cat_map
            or clean_id_check.startswith(('C.', 'C ', 'C_'))
            or clean_id_check.startswith(('F.', 'F ', 'F_'))
            or clean_id_check == 'YO' or clean_id_check.startswith('YO')
            or clean_id_check.startswith(('P.', 'P ', 'Prof'))
            or clean_id_check.startswith(('M.', 'M ', 'Mascota'))
        )

        if is_known_person:
            # Force canonical category - NO person album ever lives in Review
            canonical = ident_to_cat_map.get(clean_id_check)
            if not canonical:
                if clean_id_check.startswith(('C.', 'C ', 'C_')): canonical = 'Conocidos'
                elif clean_id_check.startswith(('F.', 'F ', 'F_')): canonical = 'Familia'
                elif clean_id_check == 'YO' or clean_id_check.startswith('YO'): canonical = 'YO'
                elif clean_id_check.startswith(('P.', 'P ', 'Prof')): canonical = 'Profesores'
                elif clean_id_check.startswith(('M.', 'M ', 'Mascota')) or clean_id_check in {'Perro', 'Gato', 'Ney', 'Sua'}: canonical = 'Mascotas'
                else: canonical = 'Conocidos'
            cat = canonical
            ident = clean_id_check

            # 3-Tier Classification for Person Albums
            p_norm = p_l.replace('\\', '/')
            is_dud = (
                item.get('is_dudoso') 
                or item.get('status') == 'Dudoso' 
                or item.get('needs_confirmation')
                or ('/_dudoso' in p_norm)
                or ('/dudoso' in p_norm)
                or (cat == "📋 Revisión / Por Organizar" and 'dudoso' in ident_l)
            )
            is_official = (
                item.get('is_dataset')
                or item.get('is_manual')
                or 'Dataset' in str(item.get('source', ''))
                or 'Manual' in str(item.get('source', ''))
                or (item.get('status') == 'Clasificado' and not is_dud and float(item.get('confidence') or 0.0) >= 0.55)
            )
            if is_official and not is_dud:
                item['album_section'] = 'official'
                item['is_dudoso'] = False
            elif is_dud:
                item['album_section'] = 'review'
                item['is_dudoso'] = True
            else:
                item['album_section'] = 'suggestion'
                item['is_dudoso'] = False
        else:
            is_person_album = (cat in KNOWN_CATEGORIES and not ident.startswith('⚠️') and not ident.startswith('⏳') and not ident.startswith('❓') and not ident.startswith('👤'))
            if not is_person_album and ('_dudoso' in cat_l or '_dudoso' in ident_l or '_dudoso' in p_l or 'dudoso' in ident_l):
                cat = "📋 Revisión / Por Organizar"
                ident = "⚠️ Dudosos / Baja Confianza"
            elif 'sin_rostro' in cat_l or 'sin_rostro' in ident_l or 'sin_rostro' in p_l:
                cat = "📋 Revisión / Por Organizar"
                ident = "🎬 Vídeos Sin Rostro" if item.get('type') == 'video' else "📷 Fotos Sin Rostro"
            elif 'aislada' in ident_l or 'ocasiona' in ident_l:
                cat = "📋 Revisión / Por Organizar"
                ident = "👥 Caras Aisladas / Ocasionales"
            elif cat == 'Personas Sin Nombre' or 'desconocid' in cat_l or 'desconocid' in ident_l or 'persona' in ident_l or 'mascota nueva' in ident_l:
                cat = "📋 Revisión / Por Organizar"
                if 'persona nueva' in ident_l or 'persona #' in ident_l:
                    clean_num = ident.replace('👤', '').strip()
                    ident = f"👤 {clean_num}"
                else:
                    ident = "❓ Desconocidos (Por Identificar)"
            elif not is_person_album and cat in ['_Dudosos', 'Revision_Interactiva', 'Falsos_Positivos']:
                cat = "📋 Revisión / Por Organizar"
                ident = "⚠️ Dudosos / Baja Confianza"
        
        if cat not in gallery: gallery[cat] = {}
        if ident not in gallery[cat]: gallery[cat][ident] = []
        k = (cat, ident, item['path'])
        fname_k = (cat, ident, item['name'].lower())
        if k not in added_paths and fname_k not in added_names:
            added_paths.add(k)
            added_names.add(fname_k)
            gallery[cat][ident].append(item)

    for (cat, ident, filename), item in seen_files.items():
        # Items from smart album folders skip person indexing
        if cat == '__smart_album__':
            continue

        clean_ident = sanitize_display_name(ident)
        file_k = get_file_key(item['path'])
        faces_in_file = overrides.get(file_k) or faces_cache.get(file_k) or faces_cache.get(item['path'], [])

        # Gallery Integrity Shield: Never render an image in person folder if AI/Manual confirmed
        # other identities and folder owner does NOT appear in the image.
        should_add_to_owner = True
        is_person_folder = (cat in KNOWN_CATEGORIES and not any(w in ident.lower() for w in ['conmigo', 'sin m\xc3\xad', 'sin mi', 'grupal', 'grupo']))
        
        if is_person_folder and not item.get('is_dataset'):
            norm_ident = clean_ident.lower().replace('c. ', '').replace('f. ', '').strip()
            if faces_in_file:
                confirmed_ids = [
                    f_e.get('identity') for f_e in faces_in_file 
                    if f_e.get('identity') and not f_e.get('identity').startswith('Desconocid') 
                    and not f_e.get('identity').startswith('Falso_Positivo') 
                    and not f_e.get('identity').startswith('Ignorar')
                ]
                if confirmed_ids:
                    owner_found = any(
                        norm_ident in cid.lower().replace('c. ', '').replace('f. ', '').strip() or
                        cid.lower().replace('c. ', '').replace('f. ', '').strip() in norm_ident
                        for cid in confirmed_ids
                    )
                    if not owner_found:
                        should_add_to_owner = False
            elif (file_k in faces_cache or item['path'] in faces_cache) and not item.get('is_dudoso'):
                # Foto escaneada explicitamente sin caras detectadas: redirigir a Sin Rostro
                should_add_to_owner = False
                add_to_gallery("📋 Revisión / Por Organizar", "🎬 Vídeos Sin Rostro" if item.get('type') == 'video' else "📷 Fotos Sin Rostro", item)

        if should_add_to_owner:
            add_to_gallery(cat, clean_ident, item)
        
        if filename.lower().startswith('100_'):
            add_to_gallery('Eventos', 'Evento Lousada', item)
            
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
        
        for group_cat, group_ident in group_albums(faces_in_file, ident_to_cat_map):
            add_to_gallery(group_cat, group_ident, item)

    # Existing group folders need the same face evidence as dynamically added groups.
    for (cat, ident, filename), item in seen_files.items():
        if cat != '__smart_album__':
            continue
        file_k = get_file_key(item['path'])
        faces_in_file = overrides.get(file_k) or faces_cache.get(file_k) or faces_cache.get(item['path'], [])
        albums = group_albums(faces_in_file, ident_to_cat_map)
        identities, unresolved = trusted_identities(faces_in_file, ident_to_cat_map)
        for group_cat, group_ident in albums:
            add_to_gallery(group_cat, group_ident, item)
        for identity in identities:
            category = ident_to_cat_map.get(identity) or ('YO' if identity == 'YO' else
                       'Familia' if identity.startswith('F. ') else
                       'Mascotas' if identity.startswith('M. ') or identity in {'Perro', 'Gato', 'Ney', 'Sua'} else 'Conocidos')
            add_to_gallery(category, sanitize_display_name(identity), item)
        if unresolved or not identities:
            add_to_gallery('📋 Revisión / Por Organizar', '⚠️ Grupos por confirmar', item)

    # --- VIRTUAL ICLOUD PHOTOS INTEGRATION (apple_db.json) ---
    try:
        from app.services.apple_service import load_apple_db
        apple_db = load_apple_db(force_reload=True)
        for p_str, info in apple_db.items():
            if not info or info.get('deleted_locally'):
                continue
            if info.get('cloud_source') == 'icloud' or 'icloud photos' in str(p_str).lower():
                fname = os.path.basename(p_str)
                cat = info.get('category', '📋 Revisión / Por Organizar')
                ident = info.get('identity', '❓ Desconocidos (Por Identificar)')
                k_check = (cat, ident, p_str)
                fname_check = (cat, ident, fname.lower())
                if k_check in added_paths or fname_check in added_names:
                    continue
                faces_in_file = info.get('faces', [])
                num_f = info.get('num_faces', len(faces_in_file))
                ids_in_file = [f.get('identity') for f in faces_in_file if f.get('identity')]
                item_apple = {
                    "path": p_str,
                    "name": fname,
                    "status": info.get('status', 'Clasificado'),
                    "source": "iCloud Photos (Virtual)",
                    "is_dataset": False,
                    "is_manual": False,
                    "type": "video" if fname.lower().endswith(('.mp4', '.mov', '.avi')) else "image",
                    "num_faces": num_f,
                    "has_yo": ('YO' in ids_in_file),
                    "identities": list(set(ids_in_file)),
                    "mtime": info.get('mtime', 0),
                    "is_apple": True,
                    "device_origin": "apple",
                    "is_virtual": True,
                    "dehydrated": True,
                    "faces": faces_in_file
                }
                # Resolve canonical category if identity is known
                canonical_cat = ident_to_cat_map.get(ident)
                if not canonical_cat:
                    if ident.startswith('C. ') or ident.startswith('C '):
                        canonical_cat = 'Conocidos'
                    elif ident.startswith('F. ') or ident.startswith('F '):
                        canonical_cat = 'Familia'
                    elif ident == 'YO':
                        canonical_cat = 'YO'
                    elif ident.startswith('P. ') or ident.startswith('Prof'):
                        canonical_cat = 'Profesores'
                    elif ident.startswith('M. ') or ident in {'Perro', 'Gato', 'Ney', 'Sua'}:
                        canonical_cat = 'Mascotas'

                if canonical_cat and (not cat or cat in {'📋 Revisión / Por Organizar', 'Dudosos', 'Personas Sin Nombre'}):
                    cat = canonical_cat

                clean_ident = sanitize_display_name(ident)
                matching_faces_for_entry = [
                    f for f in faces_in_file 
                    if sanitize_display_name(f.get('identity', '').replace('IA (Pendiente): ', '').replace('IA: ', '').strip()) == clean_ident
                ]
                
                # Add primary entry if classified by Apple Photos for this person/album
                if not is_group_album(ident):
                    item_entry = dict(item_apple)
                    if matching_faces_for_entry:
                        top_m_face = matching_faces_for_entry[0]
                        f_raw = top_m_face.get('identity', '')
                        is_pend = f_raw.startswith('IA (Pendiente):') or top_m_face.get('review_required') or top_m_face.get('status') == 'Dudoso'
                        is_conf = top_m_face.get('is_manual') or top_m_face.get('confidence') == 100.0 or 'Manual' in str(top_m_face.get('confidence', '')) or (not is_pend and float(top_m_face.get('confidence') or 0.0) >= 65.0)
                        if is_conf:
                            item_entry['album_section'] = 'official'
                            item_entry['is_dudoso'] = False
                        elif is_pend:
                            item_entry['album_section'] = 'review'
                            item_entry['is_dudoso'] = True
                            item_entry['needs_confirmation'] = True
                        else:
                            item_entry['album_section'] = 'suggestion'
                            item_entry['is_dudoso'] = False
                        add_to_gallery(cat, clean_ident, item_entry)
                    elif clean_ident and not clean_ident.startswith(('Desconocid', 'Falso_Positivo', 'Ignorar', 'Persona Nueva')):
                        # Foto sugerida por la IA de Apple Photos / iPhone para esta persona
                        is_pend = (info.get('status') == 'Dudoso' or info.get('review_required'))
                        if is_pend:
                            item_entry['album_section'] = 'review'
                            item_entry['is_dudoso'] = True
                            item_entry['needs_confirmation'] = True
                        else:
                            item_entry['album_section'] = 'suggestion'
                            item_entry['is_dudoso'] = False
                        add_to_gallery(cat, clean_ident, item_entry)

                # Add to individual person albums for each recognized face in faces_in_file
                for f in faces_in_file:
                    f_raw = f.get('identity', '')
                    if not f_raw:
                        continue
                    f_clean = f_raw.replace('IA (Pendiente): ', '').replace('IA: ', '').strip()
                    if f_clean and not f_clean.startswith('Desconocid') and not f_clean.startswith('Falso_Positivo') and not f_clean.startswith('Ignorar') and not f_clean.startswith('Persona Nueva'):
                        f_cat = ident_to_cat_map.get(f_clean)
                        if not f_cat:
                            if f_clean.startswith('C. ') or f_clean.startswith('C '):
                                f_cat = 'Conocidos'
                            elif f_clean.startswith('F. ') or f_clean.startswith('F '):
                                f_cat = 'Familia'
                            elif f_clean == 'YO':
                                f_cat = 'YO'
                            elif f_clean.startswith('P. '):
                                f_cat = 'Profesores'
                            else:
                                f_cat = 'Conocidos'
                        
                        item_face = dict(item_apple)
                        is_pend = f_raw.startswith('IA (Pendiente):') or f.get('review_required') or f.get('status') == 'Dudoso'
                        is_conf = f.get('is_manual') or f.get('confidence') == 100.0 or 'Manual' in str(f.get('confidence', '')) or (not is_pend and float(f.get('confidence') or 0.0) >= 65.0)
                        if is_conf:
                            item_face['album_section'] = 'official'
                            item_face['is_dudoso'] = False
                        elif is_pend:
                            item_face['album_section'] = 'review'
                            item_face['is_dudoso'] = True
                            item_face['needs_confirmation'] = True
                        else:
                            item_face['album_section'] = 'suggestion'
                            item_face['is_dudoso'] = False
                        add_to_gallery(f_cat, sanitize_display_name(f_clean), item_face)

                albums = group_albums(faces_in_file, ident_to_cat_map)
                for group_cat, group_ident in albums:
                    add_to_gallery(group_cat, group_ident, item_apple)
                if is_group_album(ident) and not albums:
                    add_to_gallery('📋 Revisión / Por Organizar', '⚠️ Grupos por confirmar', item_apple)
    except Exception as e_app:
        print(f"[WARN] Error integrating apple_db virtual photos: {e_app}")

    # Sort person album items by 3-tier sections: official -> suggestion -> review
    section_order = {'official': 0, 'suggestion': 1, 'review': 2}
    for c, idents in gallery.items():
        if c in KNOWN_CATEGORIES:
            for id_name, items in idents.items():
                if isinstance(items, list):
                    items.sort(key=lambda x: (
                        section_order.get(x.get('album_section', 'suggestion'), 1),
                        -(x.get('mtime') or 0)
                    ))

    set_gallery_cache(gallery)
    result = dict(gallery)
    set_gallery_cache(result)
    from flask import has_app_context
    if has_app_context():
        return jsonify(result)
    return result


def api_metadata():
    filepath = request.args.get('path')
    real_path = find_relocated_file(filepath)
    if not real_path:
        return jsonify({"error": "File not found"}), 404
    filepath = real_path
        
    stats = os.stat(filepath)
    size_bytes = stats.st_size
    size = f"{size_bytes / (1024*1024):.2f} MB"
    mtime = datetime.datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    
    res = "Desconocida"
    camera = "Desconocida"
    lens = ""
    aperture = ""
    shutter = ""
    iso = ""
    focal_length = ""
    megapixels = ""
    real_date = mtime
    gps_info = None
    is_live_photo = False
    
    # Check if matching Live Photo .mov exists
    fpath_obj = Path(filepath)
    if fpath_obj.suffix.lower() in ['.jpg', '.jpeg', '.heic', '.heif', '.png']:
        mov_match = fpath_obj.with_suffix('.mov')
        MOV_match = fpath_obj.with_suffix('.MOV')
        if mov_match.exists() or MOV_match.exists():
            is_live_photo = True

    if filepath.lower().endswith(('.jpg', '.jpeg', '.png', '.heic', '.heif')):
        try:
            from PIL import Image, ExifTags
            with Image.open(filepath) as img:
                w, h = img.width, img.height
                res = f"{w} × {h}"
                mp = (w * h) / 1000000.0
                megapixels = f"{mp:.1f} MP" if mp >= 1 else f"{mp*1000:.0f} KP"
                
                exif_raw = img._getexif()
                if exif_raw:
                    exif_data = {}
                    for tag_id, val in exif_raw.items():
                        tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                        exif_data[tag_name] = val
                    
                    make = str(exif_data.get('Make', '')).strip()
                    model = str(exif_data.get('Model', '')).strip()
                    if model:
                        camera = f"{make} {model}".strip() if make and make.lower() not in model.lower() else model
                    elif make:
                        camera = make
                    
                    lens_val = exif_data.get('LensModel')
                    if lens_val:
                        lens = str(lens_val).strip()
                        
                    fnum = exif_data.get('FNumber')
                    if fnum:
                        try:
                            f_val = float(fnum)
                            aperture = f"f/{f_val:.1f}" if f_val % 1 != 0 else f"f/{int(f_val)}"
                        except Exception: pass
                        
                    exp_time = exif_data.get('ExposureTime')
                    if exp_time:
                        try:
                            exp_val = float(exp_time)
                            if exp_val < 1.0 and exp_val > 0:
                                shutter = f"1/{int(round(1.0/exp_val))}s"
                            else:
                                shutter = f"{exp_val:.1f}s"
                        except Exception: pass
                        
                    iso_val = exif_data.get('ISOSpeedRatings')
                    if iso_val:
                        iso = f"ISO {iso_val}"
                        
                    focal = exif_data.get('FocalLength')
                    if focal:
                        try:
                            focal_val = float(focal)
                            focal_length = f"{focal_val:.1f} mm" if focal_val % 1 != 0 else f"{int(focal_val)} mm"
                        except Exception: pass

                    dt_orig = exif_data.get('DateTimeOriginal')
                    if dt_orig:
                        try:
                            parsed = datetime.datetime.strptime(str(dt_orig), '%Y:%m:%d %H:%M:%S')
                            real_date = parsed.strftime('%Y-%m-%d %H:%M:%S')
                        except Exception: pass
                        
                    # GPS Coordinates
                    gps_tags = exif_data.get('GPSInfo')
                    if gps_tags:
                        try:
                            gps_parsed = {}
                            for t in gps_tags:
                                sub_name = ExifTags.GPSTAGS.get(t, t)
                                gps_parsed[sub_name] = gps_tags[t]
                                
                            lat_raw = gps_parsed.get('GPSLatitude')
                            lat_ref = gps_parsed.get('GPSLatitudeRef', 'N')
                            lng_raw = gps_parsed.get('GPSLongitude')
                            lng_ref = gps_parsed.get('GPSLongitudeRef', 'E')
                            
                            if lat_raw and lng_raw:
                                lat = float(lat_raw[0]) + float(lat_raw[1])/60.0 + float(lat_raw[2])/3600.0
                                if lat_ref == 'S': lat = -lat
                                lng = float(lng_raw[0]) + float(lng_raw[1])/60.0 + float(lng_raw[2])/3600.0
                                if lng_ref == 'W': lng = -lng
                                gps_info = {"lat": round(lat, 6), "lng": round(lng, 6)}
                        except Exception: pass
        except Exception:
            pass
            
    if real_date == mtime:
        import re
        match = re.search(r'(19\d{2}|20\d{2})([0-1]\d)([0-3]\d)', Path(filepath).name)
        if match:
            year, month, day = match.groups()
            try:
                parsed_date = datetime.datetime(int(year), int(month), int(day))
                real_date = f"{parsed_date.strftime('%Y-%m-%d')} (Estimada)"
            except ValueError:
                pass
    
    file_origin = detect_device_origin(filepath)
    if not camera or camera == "Desconocida":
        if file_origin == "apple":
            camera = "Apple iPhone"
        elif file_origin == "android":
            camera = "Dispositivo Android"
    return jsonify({
        "size": size,
        "date": real_date,
        "camera": camera,
        "lens": lens,
        "aperture": aperture,
        "shutter": shutter,
        "iso": iso,
        "focal_length": focal_length,
        "megapixels": megapixels,
        "resolution": res,
        "gps": gps_info,
        "is_live_photo": is_live_photo,
        "device_origin": file_origin,
        "is_apple": (file_origin == "apple")
    })

def api_stats():
    from app.services.apple_service import is_apple_photo
    gallery_cache = get_gallery_cache()
    if gallery_cache is None:
        get_gallery()
        gallery_cache = get_gallery_cache() or {}
        
    total_files = set()
    manual_files = set()
    ia_verified_files = set()
    dudosos_files = set()
    pendientes_files = set()
    
    iphone_total_files = set()
    iphone_classified_files = set()
    android_total_files = set()
    android_classified_files = set()
    
    breakdown = {}
    overrides = load_overrides()
    
    for cat, idents in (gallery_cache or {}).items():
        if cat == '__smart_album__': continue
        for ident, items in idents.items():
            count = len(items)
            cat_l = cat.lower()
            ident_l = ident.lower()
            
            label = f"[{cat}] {ident}" if cat != 'Conocidos' else ident
            breakdown[label] = breakdown.get(label, 0) + count
            
            for item in items:
                p = item.get('path', '')
                if not p: continue
                total_files.add(p)
                
                is_iphone = is_apple_photo(p)
                if is_iphone:
                    iphone_total_files.add(p)
                else:
                    android_total_files.add(p)
                
                if cat == "📋 Revisión / Por Organizar" or 'revisión' in cat_l or 'organizar' in cat_l:
                    if 'dudoso' in ident_l:
                        dudosos_files.add(p)
                    else:
                        pendientes_files.add(p)
                elif 'dudoso' in cat_l or 'dudoso' in ident_l or '_dudoso' in p.lower():
                    dudosos_files.add(p)
                else:
                    src = item.get('source', '')
                    if p in overrides or 'Manual' in src or 'Dataset' in src:
                        manual_files.add(p)
                    else:
                        ia_verified_files.add(p)
                        
                    if is_iphone:
                        iphone_classified_files.add(p)
                    else:
                        android_classified_files.add(p)
                        
    breakdown_sorted = dict(sorted(breakdown.items(), key=lambda item: item[1], reverse=True))

    # Telemetría del Asistente en Segundo Plano y Sincronización iCloud
    import time, json
    progress_file = APP_DIR / "scratch" / "apple_progress.json"
    apple_db_file = APP_DIR / "apple_db.json"
    
    total_apple_db = 0
    if apple_db_file.exists():
        try:
            with open(apple_db_file, 'r', encoding='utf-8') as f_adb:
                total_apple_db = len(json.load(f_adb))
        except Exception:
            pass

    assistant_data = {
        "active": False,
        "status": "completed",
        "total": 0,
        "processed": 0,
        "remaining": 0,
        "percentage": 100.0,
        "rate": 0.0,
        "eta_minutes": 0,
        "eta_formatted": "Completado",
        "cloud_placeholders": 0,
        "icloud_total": 0,
        "yo": 0,
        "known_persons": 0,
        "capturas": 0,
        "sin_rostro": 0,
        "desconocidos": 0,
        "errors": 0,
        "total_apple_db": total_apple_db,
        "last_update_seconds_ago": 999999
    }

    if progress_file.exists():
        try:
            mtime = progress_file.stat().st_mtime
            sec_ago = max(0, int(time.time() - mtime))
            with open(progress_file, 'r', encoding='utf-8') as pf:
                pdata = json.load(pf)
                
            p_total = int(pdata.get('total', 0))
            p_proc = int(pdata.get('processed', 0))
            p_rem = max(0, p_total - p_proc)
            p_pct = round((p_proc / p_total * 100), 1) if p_total > 0 else 100.0
            p_rate = float(pdata.get('rate', 0.0))
            p_eta_m = float(pdata.get('eta_minutes', 0.0))
            
            if p_rem == 0 or pdata.get('status') == 'completed':
                eta_fmt = "Completado"
            elif p_eta_m > 60:
                eta_fmt = f"{int(p_eta_m // 60)}h {int(p_eta_m % 60)}m"
            elif p_eta_m > 0:
                eta_fmt = f"{int(p_eta_m)} min"
            else:
                eta_fmt = "Calculando..."

            is_recently_active = (sec_ago < 90 and pdata.get('status') == 'running')
            
            assistant_data.update({
                "active": is_recently_active,
                "status": "running" if is_recently_active else pdata.get('status', 'completed'),
                "total": p_total,
                "processed": p_proc,
                "remaining": p_rem,
                "percentage": p_pct,
                "rate": p_rate,
                "eta_minutes": p_eta_m,
                "eta_formatted": eta_fmt,
                "cloud_placeholders": pdata.get('cloud_placeholders', 0),
                "icloud_total": pdata.get('icloud_total', 0),
                "yo": pdata.get('yo', 0),
                "known_persons": pdata.get('known_persons', 0),
                "capturas": pdata.get('capturas', 0),
                "sin_rostro": pdata.get('sin_rostro', 0),
                "desconocidos": pdata.get('desconocidos', 0),
                "errors": pdata.get('errors', 0),
                "last_update_seconds_ago": sec_ago
            })
        except Exception as e_p:
            print("Error loading apple_progress.json:", e_p)

    try:
        from app.services.face_service import _ENGINE_STATE, _ENGINE_THREAD
        engine_alive = _ENGINE_THREAD is not None and _ENGINE_THREAD.is_alive()
        assistant_data["engine"] = {
            "running": bool(_ENGINE_STATE.get("running") and engine_alive),
            "phase": _ENGINE_STATE.get("phase", "idle"),
            "cycle": _ENGINE_STATE.get("cycle", 0),
            "total_scanned": _ENGINE_STATE.get("total_scanned", 0),
            "total_suggested": _ENGINE_STATE.get("total_suggested", 0),
            "total_fixed": _ENGINE_STATE.get("total_fixed", 0)
        }
    except Exception:
        pass
                
    return jsonify({
        "total": len(total_files),
        "manual_user": len(manual_files),
        "ia_verified": len(ia_verified_files),
        "dudosos": len(dudosos_files),
        "pendientes": len(pendientes_files),
        "clasificadas": len(manual_files) + len(ia_verified_files),
        "iphone_total": len(iphone_total_files),
        "iphone_clasificadas": len(iphone_classified_files),
        "android_total": len(android_total_files),
        "android_clasificadas": len(android_classified_files),
        "breakdown": breakdown_sorted,
        "assistant": assistant_data,
        "supervisor": __import__('app.services.supervisor_service', fromlist=['get_supervisor_status']).get_supervisor_status()
    })

def find_avatar_image(target_dir):
    valid_exts = {".jpg", ".jpeg", ".png"}
    if not target_dir: return None
    if isinstance(target_dir, str): target_dir = Path(target_dir)
    if not target_dir.exists(): return None
    centroid_cover = target_dir / "!00_CARA_CENTROIDE.jpg" if target_dir.is_dir() else None
    if centroid_cover and centroid_cover.exists():
        return str(centroid_cover.resolve())
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

    clean_ident = ident.replace('👤', '').lstrip('?').strip()
    ident_clean = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(ident))
    clean_ident_clean = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(clean_ident))
    cat_clean = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(cat))

    bypass_cache = bool(request.args.get('refresh') or request.args.get('t') or request.args.get('nocache'))
    if not bypass_cache:
        for folder_dir in [THUMBNAILS_DIR, APP_DIR / "cache" / "thumbnails"]:
            for c_cand, i_cand in [
                (cat_clean, ident_clean),
                (cat_clean, clean_ident_clean)
            ]:
                avatar_cache_file = folder_dir / f"av_{c_cand}_{i_cand}.webp"
                if avatar_cache_file.exists() and avatar_cache_file.stat().st_size > 200:
                    res = send_file(str(avatar_cache_file), mimetype='image/webp')
                    res.headers['Cache-Control'] = 'public, max-age=3600, must-revalidate'
                    return res

    default_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 24 24" fill="#666"><circle cx="12" cy="8" r="4"/><path d="M12 14c-6.1 0-8 4-8 4v2h16v-2s-1.9-4-8-4z"/></svg>'''

    valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
    
    items = []
    g_cache = get_gallery_cache()
    clean_cat = re.sub(r'^[👤📋📁❓🔍✨📸⚡🎉🏷️👥🧑👧👦\s]+', '', str(cat)).strip()
    clean_ident_base = clean_ident.replace('C. ', '').replace('F. ', '').replace('P. ', '').replace('M. ', '').strip()

    if g_cache:
        for c_k, c_idents in g_cache.items():
            c_k_clean = re.sub(r'^[👤📋📁❓🔍✨📸⚡🎉🏷️👥🧑👧👦\s]+', '', str(c_k)).strip()
            if c_k == cat or c_k_clean == clean_cat or not cat:
                for i_k, i_items in c_idents.items():
                    i_k_clean = re.sub(r'^[👤📋📁❓🔍✨📸⚡🎉🏷️👥🧑👧👦\s]+', '', str(i_k)).strip()
                    i_k_base = i_k_clean.replace('C. ', '').replace('F. ', '').replace('P. ', '').replace('M. ', '').strip()
                    if i_k == ident or i_k_clean == clean_ident or i_k_base == clean_ident_base or i_k_clean.lower() == clean_ident.lower():
                        items.extend(i_items)

    candidate_paths = [it.get('path') for it in items if it.get('path') and Path(it.get('path')).suffix.lower() in valid_exts and os.path.exists(it.get('path'))]

    # Also search disk in all known candidate directories
    search_dirs = [
        RESULTADOS_DIR / cat / ident,
        RESULTADOS_DIR / clean_cat / clean_ident,
        RESULTADOS_DIR / "Personas Sin Nombre" / ident,
        RESULTADOS_DIR / "Personas Sin Nombre" / clean_ident,
        RESULTADOS_DIR / "Conocidos" / clean_ident,
        RESULTADOS_DIR / "Familia" / clean_ident,
        FOTOS_DIR / cat / ident,
        FOTOS_DIR / clean_cat / clean_ident,
        FOTOS_DIR / "Conocidos" / clean_ident,
        FOTOS_DIR / "Familia" / clean_ident,
        FOTOS_DIR / clean_ident,
    ]
    for base_dir in search_dirs:
        if base_dir.exists() and base_dir.is_dir():
            for p in base_dir.iterdir():
                if p.suffix.lower() in valid_exts and p.is_file():
                    candidate_paths.append(str(p))

    # Also inspect apple_db.json for iCloud / virtual photos belonging to this person
    try:
        import json
        apple_db_path = APP_DIR / 'apple_db.json'
        if apple_db_path.exists():
            with open(apple_db_path, 'r', encoding='utf-8') as f_adb:
                adb = json.load(f_adb)
            clean_ident_lower = clean_ident.lower()
            clean_base_lower = clean_ident_base.lower()
            for p_path, meta in adb.items():
                m_ident = str(meta.get('identity', '')).strip()
                m_clean = re.sub(r'^[👤📋📁❓🔍✨📸⚡🎉🏷️👥🧑👧👦\s]+', '', m_ident).lower()
                m_base = m_clean.replace('c. ', '').replace('f. ', '').replace('p. ', '').replace('m. ', '').strip()
                if m_clean == clean_ident_lower or m_base == clean_base_lower or m_ident == ident:
                    if Path(p_path).suffix.lower() in valid_exts and os.path.exists(p_path):
                        candidate_paths.append(p_path)
    except Exception:
        pass

    candidate_paths = list(dict.fromkeys(candidate_paths))

    if not candidate_paths:
        video_exts = {".mp4", ".mov", ".avi"}
        video_paths = [it.get('path') for it in items if it.get('path') and Path(it.get('path')).suffix.lower() in video_exts and os.path.exists(it.get('path'))]
        if not video_paths:
            for base_dir in [RESULTADOS_DIR / cat / ident, FOTOS_DIR / cat / ident]:
                if base_dir.exists():
                    for p in base_dir.iterdir():
                        if p.suffix.lower() in video_exts and p.is_file():
                            video_paths.append(str(p))
                            
        for v_path in video_paths:
            cap = cv2.VideoCapture(str(v_path))
            if cap.isOpened():
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if total_frames > 15:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, min(30, total_frames // 2))
                ret, frame = cap.read()
                cap.release()
                if ret and frame is not None:
                    h_img, w_img = frame.shape[:2]
                    crop_sz = min(h_img, w_img)
                    cx, cy = w_img // 2, h_img // 2
                    x1 = max(0, cx - crop_sz // 2)
                    y1 = max(0, cy - crop_sz // 2)
                    crop = frame[y1:y1+crop_sz, x1:x1+crop_sz]
                    if crop.size > 0:
                        target_save_file = THUMBNAILS_DIR / f"av_{cat_clean}_{ident_clean}.webp"
                        avatar_img = cv2.resize(crop, (160, 160), interpolation=cv2.INTER_LANCZOS4)
                        try:
                            cv2.imwrite(str(target_save_file), avatar_img, [cv2.IMWRITE_WEBP_QUALITY, 92])
                        except Exception: pass
                        _, buf = cv2.imencode('.webp', avatar_img, [cv2.IMWRITE_WEBP_QUALITY, 92])
                        res = Response(buf.tobytes(), mimetype='image/webp')
                        res.headers['Cache-Control'] = 'public, max-age=604800, immutable'
                        return res

    if not candidate_paths:
        return Response(default_svg, mimetype='image/svg+xml')

    try:
        from app.globals import detector, recognizer
        target_save_file = THUMBNAILS_DIR / f"av_{cat_clean}_{ident_clean}.webp"
        
        # Sort candidate paths with highest precision:
        # Priority 0: Exact filename match to person name (e.g. Martín Sánchez.jpg) or _00_CENTROIDE_
        # Priority 1: Photos inside FOTOS_DIR (dataset ground-truth)
        # Priority 2: Photos from person's own directory
        # Priority 3: Photos from iCloud / apple_db
        clean_ident_lower = clean_ident.lower()
        clean_base_lower = clean_ident_base.lower()
        def get_avatar_prio(p_str):
            p = Path(p_str)
            stem_lower = p.stem.lower()
            if stem_lower == clean_ident_lower or stem_lower == clean_base_lower or '_00_centroide_' in stem_lower:
                return (0, -os.path.getsize(p_str))
            p_str_low = p_str.lower()
            if 'fotos' in p_str_low and 'icloud' not in p_str_low:
                return (1, -os.path.getsize(p_str))
            if clean_ident_lower in p_str_low or clean_base_lower in p_str_low:
                return (2, -os.path.getsize(p_str))
            return (3, -os.path.getsize(p_str))

        candidate_paths.sort(key=get_avatar_prio)
        
        # Special Case 1: Pets (Mascotas) and Group Albums (Familia conmigo, etc.)
        # These should NEVER use a single human face detector! Use a smart center crop of the best photo!
        is_pet = (cat == 'Mascotas' or ident.startswith('M.') or 'mascota' in cat.lower())
        is_group = any(w in ident.lower() for w in ['conmigo', 'sin mí', 'sin mi', 'grupal', 'grupo', 'eventos', 'recuerdos']) or cat in ['Lugares', 'Eventos', 'Recuerdos', 'Objetos', 'Frases']
        
        if is_pet or is_group:
            for c_path in candidate_paths:
                file_bytes = np.fromfile(c_path, dtype=np.uint8)
                img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                if img is None: continue
                h_img, w_img = img.shape[:2]
                crop_sz = min(h_img, w_img)
                cx, cy = w_img // 2, h_img // 2
                x1 = max(0, cx - crop_sz // 2)
                y1 = max(0, cy - crop_sz // 2)
                crop = img[y1:y1+crop_sz, x1:x1+crop_sz]
                if crop.size > 0:
                    avatar_img = cv2.resize(crop, (160, 160), interpolation=cv2.INTER_LANCZOS4)
                    try:
                        cv2.imwrite(str(target_save_file), avatar_img, [cv2.IMWRITE_WEBP_QUALITY, 92])
                    except Exception: pass
                    _, buf = cv2.imencode('.webp', avatar_img, [cv2.IMWRITE_WEBP_QUALITY, 92])
                    res = Response(buf.tobytes(), mimetype='image/webp')
                    res.headers['Cache-Control'] = 'public, max-age=3600, must-revalidate'
                    return res

        # Load centroids from centroids.pkl
        centroids_map = {}
        c_pkl = APP_DIR / "centroids.pkl"
        if c_pkl.exists():
            try:
                with open(c_pkl, 'rb') as f:
                    centroids_map = pickle.load(f)
            except Exception:
                pass

        target_centroid = None
        for cand_k in [
            (cat, ident), (cat, clean_ident),
            (clean_cat, clean_ident),
            ident, clean_ident,
            clean_ident_base,
            f"C. {clean_ident_base}", f"F. {clean_ident_base}",
            f"👤 {clean_ident}"
        ]:
            if cand_k in centroids_map and centroids_map[cand_k] is not None:
                target_centroid = centroids_map[cand_k]
                break

        if target_centroid is None:
            clean_target_lower = clean_ident.lower()
            clean_target_base = clean_ident_base.lower()
            for k, v in centroids_map.items():
                if v is None: continue
                if isinstance(k, (tuple, list)) and len(k) > 1:
                    k_ident = str(k[1]).lower()
                else:
                    k_ident = str(k).lower()
                k_clean = re.sub(r'^[👤📋📁❓🔍✨📸⚡🎉🏷️👥🧑👧👦\s]+', '', k_ident).strip()
                k_base = k_clean.replace('c. ', '').replace('f. ', '').replace('p. ', '').replace('m. ', '').strip()
                if k_clean == clean_target_lower or k_base == clean_target_base or k_ident == clean_target_lower:
                    target_centroid = v
                    break

        yo_centroid = centroids_map.get(('YO', 'YO'))
        if yo_centroid is None:
            yo_centroid = centroids_map.get('YO')
        yo_norm = yo_centroid / (np.linalg.norm(yo_centroid) + 1e-10) if yo_centroid is not None else None
        target_norm = target_centroid / (np.linalg.norm(target_centroid) + 1e-10) if target_centroid is not None else None

        best_crop = None
        best_quality = -1.0
        fallback_crop = None
        
        for c_path in candidate_paths[:25]:
            if not c_path or not os.path.exists(c_path): continue
            file_bytes = np.fromfile(c_path, dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is None: continue
            
            h_img, w_img = img.shape[:2]
            if fallback_crop is None:
                crop_sz = min(h_img, w_img)
                cx, cy = w_img // 2, h_img // 2
                x1 = max(0, cx - crop_sz // 2)
                y1 = max(0, cy - crop_sz // 2)
                fallback_crop = img[y1:y1+crop_sz, x1:x1+crop_sz]
            
            # Scaled detection for YuNet (1024px)
            max_dim = 1024
            scale = 1.0
            if max(w_img, h_img) > max_dim:
                scale = max_dim / max(w_img, h_img)
                det_w = max(160, int(w_img * scale))
                det_h = max(160, int(h_img * scale))
                det_img = cv2.resize(img, (det_w, det_h), interpolation=cv2.INTER_AREA)
            else:
                det_w, det_h = w_img, h_img
                det_img = img
                
            inv_scale = 1.0 / scale
            detected_faces = []
            
            if detector is not None:
                try:
                    detector.setInputSize((det_w, det_h))
                    detector.setScoreThreshold(0.55)
                    _, det_faces = detector.detect(det_img)
                    if det_faces is not None and len(det_faces) > 0:
                        for df in det_faces:
                            if df[14] >= 0.55:
                                df_scaled = df.copy()
                                df_scaled[0] *= inv_scale
                                df_scaled[1] *= inv_scale
                                df_scaled[2] *= inv_scale
                                df_scaled[3] *= inv_scale
                                for l_idx in range(4, 14, 2):
                                    df_scaled[l_idx] *= inv_scale
                                    df_scaled[l_idx+1] *= inv_scale
                                detected_faces.append(df_scaled)
                except Exception:
                    pass
                    
            for face_raw in detected_faces:
                try:
                    x, y, w, h = int(face_raw[0]), int(face_raw[1]), int(face_raw[2]), int(face_raw[3])
                    if w < 24 or h < 24: continue
                    
                    # Extract embedding to verify identity
                    sim = 0.5
                    if recognizer is not None:
                        try:
                            aligned = recognizer.alignCrop(img, face_raw)
                            feat = recognizer.feature(aligned)[0]
                            feat_norm = feat / (np.linalg.norm(feat) + 1e-10)
                            
                            # Differentiate between Target and Eneko (YO)
                            sim_yo = float(np.dot(feat_norm, yo_norm)) if yo_norm is not None else 0.0
                            sim_target = float(np.dot(feat_norm, target_norm)) if target_norm is not None else 0.5
                            
                            # CRITICAL: NEVER pick Eneko's face for family members / acquaintances!
                            if cat != 'YO' and yo_norm is not None:
                                if sim_yo >= sim_target or (sim_yo > 0.45 and sim_target < sim_yo + 0.08):
                                    continue
                                    
                            if target_norm is not None and sim_target < 0.45:
                                continue
                                
                            sim = sim_target
                        except Exception:
                            sim = 0.5
                        
                    x1, y1 = max(0, x), max(0, y)
                    x2, y2 = min(w_img, x + w), min(h_img, y + h)
                    if x2 <= x1 or y2 <= y1: continue
                    
                    face_box = img[y1:y2, x1:x2]
                    gray = cv2.cvtColor(face_box, cv2.COLOR_BGR2GRAY)
                    
                    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
                    sharpness_score = min(lap_var / 350.0, 1.0)
                    size_score = min(np.sqrt(w * h) / 160.0, 1.0)
                    
                    quality = 0.60 * sim + 0.25 * sharpness_score + 0.15 * size_score
                    
                    if quality > best_quality:
                        best_quality = quality
                        pad_x = int(min(w * 0.15, x, w_img - (x + w)))
                        pad_y = int(min(h * 0.15, y, h_img - (y + h)))
                        px1, py1 = max(0, x - pad_x), max(0, y - pad_y)
                        px2, py2 = min(w_img, x + w + pad_x), min(h_img, y + h + pad_y)
                        best_crop = img[py1:py2, px1:px2]
                except Exception:
                    pass
                    
        # For people, NEVER fallback to a blind center crop of a random photo! Return SVG avatar.
        if best_crop is None or best_crop.size == 0:
            if is_pet or is_group:
                if fallback_crop is not None and fallback_crop.size > 0:
                    best_crop = fallback_crop
                else:
                    return Response(default_svg, mimetype='image/svg+xml')
            else:
                return Response(default_svg, mimetype='image/svg+xml')

        # Resize avatar to crisp 160x160 webp with Lanczos interpolation
        avatar_img = cv2.resize(best_crop, (160, 160), interpolation=cv2.INTER_LANCZOS4)
        try:
            cv2.imwrite(str(target_save_file), avatar_img, [cv2.IMWRITE_WEBP_QUALITY, 92])
            cache_out = APP_DIR / "cache" / "thumbnails" / f"av_{cat_clean}_{ident_clean}.webp"
            cv2.imwrite(str(cache_out), avatar_img, [cv2.IMWRITE_WEBP_QUALITY, 92])
        except Exception:
            pass

        _, buf = cv2.imencode('.webp', avatar_img, [cv2.IMWRITE_WEBP_QUALITY, 92])
        res = Response(buf.tobytes(), mimetype='image/webp')
        res.headers['Cache-Control'] = 'public, max-age=604800, immutable'
        return res
    except Exception:
        return Response(default_svg, mimetype='image/svg+xml')

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
            resp = send_file(thumb, mimetype='image/webp', conditional=True)
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



def api_events_timeline():
    try:
        import datetime
        from app.globals import get_gallery_cache
        g_cache = get_gallery_cache()
        if g_cache is None:
            get_gallery()
            g_cache = get_gallery_cache() or {}

        year_groups = {}
        for cat, idents in g_cache.items():
            if cat in ['__smart_album__', 'Fotos Sin Rostro']:
                continue
            for ident, items in idents.items():
                if not items:
                    continue
                y_counts = {}
                for it in items:
                    m = it.get('mtime')
                    if m:
                        try:
                            yr = datetime.datetime.fromtimestamp(m).year
                            if 2000 <= yr <= 2030:
                                y_counts[yr] = y_counts.get(yr, 0) + 1
                        except Exception:
                            pass
                top_year = max(y_counts.items(), key=lambda x: x[1])[0] if y_counts else 2024
                if top_year not in year_groups:
                    year_groups[top_year] = []

                sample_thumbs = [it['path'] for it in items[:3]]
                year_groups[top_year].append({
                    "title": ident,
                    "category": cat,
                    "count": len(items),
                    "cover": items[0]['path'] if items else "",
                    "sample_thumbs": sample_thumbs
                })

        sorted_years = sorted(year_groups.keys(), reverse=True)
        timeline = []
        for yr in sorted_years:
            evs = sorted(year_groups[yr], key=lambda x: x['count'], reverse=True)
            timeline.append({
                "year": yr,
                "events": evs
            })

        return jsonify({"timeline": timeline, "years": sorted_years})
    except Exception as e:
        return jsonify({"timeline": [], "years": [], "error": str(e)}), 500


def api_remove_from_folder():
    """
    Quitar una foto de la carpeta de una persona significa que esa persona
    NO aparece en la foto. La foto se re-clasifica excluyendo al propietario
    actual de la carpeta. Si se encuentra otra persona -> va a su carpeta.
    Si no -> va a _Dudosos para revisión manual.
    """
    import pickle
    data = request.json
    filepath = data.get('path')
    cat = data.get('cat')
    ident = data.get('ident')   # La persona que se excluye (dueño de la carpeta actual)
    
    if not filepath or not ident:
        return jsonify({"error": "Faltan parámetros"}), 400
        
    try:
        p_obj = Path(filepath)
        if not p_obj.exists():
            from app.utils.files import find_relocated_file
            relocated = find_relocated_file(filepath)
            if relocated and os.path.exists(relocated):
                p_obj = Path(relocated)
                filepath = relocated
            else:
                is_adb_virtual = False
                try:
                    from app.services.apple_service import load_apple_db
                    adb = load_apple_db()
                    if filepath in adb or (filepath and os.path.basename(filepath) in adb):
                        is_adb_virtual = True
                except Exception:
                    pass
                if not is_adb_virtual:
                    return jsonify({"error": "Archivo no encontrado en disco"}), 404

        # Si el archivo está en Fotos/ (Dataset), moverlo primero a Resultados/
        # para que el Dataset solo tenga fotos 100% verificadas
        try:
            if p_obj.is_relative_to(FOTOS_DIR):
                staging_dir = RESULTADOS_DIR / (cat or 'Conocidos') / ident
                staging_dir.mkdir(parents=True, exist_ok=True)
                staging_dest = staging_dir / p_obj.name
                counter = 1
                while staging_dest.exists() and staging_dest.resolve() != p_obj.resolve():
                    staging_dest = staging_dir / f"{p_obj.stem}_{counter}{p_obj.suffix}"
                    counter += 1
                if staging_dest.resolve() != p_obj.resolve():
                    shutil.move(str(p_obj), str(staging_dest))
                    p_obj = staging_dest
                    filepath = str(staging_dest)
        except (ValueError, Exception):
            pass  # No estaba en FOTOS_DIR, continuar normal

        # 1. Registrar que esta persona (ident) NO está en este archivo
        overrides = load_overrides()
        file_key = get_file_key(filepath)
        
        existing = overrides.get(file_key, [])
        # Añadir entrada de exclusión para esta identidad
        exclusion_entry = {
            'x': 0, 'y': 0, 'width': 0, 'height': 0,
            'identity': 'Excluido',
            'excluded_from': ident,
            'is_manual': True
        }
        # Eliminar cualquier override previo que asignara a esta identidad
        existing = [ov for ov in existing if ov.get('identity') != ident]
        existing.append(exclusion_entry)
        overrides[file_key] = existing
        save_overrides(overrides)

        # Actualizar apple_db.json si es foto de iCloud/Apple
        try:
            from app.services.apple_service import load_apple_db, save_apple_db
            adb = load_apple_db()
            norm_fp = os.path.normpath(filepath) if filepath else ''
            matching_key = None
            for k in adb.keys():
                if os.path.normpath(k) == norm_fp or os.path.basename(k) == os.path.basename(filepath or ''):
                    matching_key = k
                    break
            if matching_key:
                entry = adb[matching_key]
                if entry.get('identity') == ident:
                    entry['identity'] = 'Desconocido'
                    entry['status'] = 'Dudoso'
                if 'faces' in entry and isinstance(entry['faces'], list):
                    for f in entry['faces']:
                        if f.get('identity') == ident or f.get('suggested_identity') == ident:
                            f['identity'] = 'Desconocido'
                            f['suggested_identity'] = None
                            f['suggested_score'] = 0.0
                            f['is_manual'] = False
                if 'identities' in entry and isinstance(entry['identities'], list):
                    entry['identities'] = [i for i in entry['identities'] if i != ident]
                save_apple_db()
                print(f"[APPLE DB] Removed {ident} from {matching_key}")
        except Exception as e_adb:
            print(f"[WARN] Error updating apple_db on remove_from_folder: {e_adb}")

        
        # Invalidar caché
        set_gallery_cache(None)

        # 2. Re-clasificar en background: buscar la identidad real, excluyendo a `ident`
        def _reclassify_background(p_obj=p_obj, excluded_ident=ident, excluded_cat=cat):
            try:
                from app.globals import detector, recognizer, known_faces, faces_cache, FACES_CACHE_FILE, cache_lock
                import pickle

                # Cargar centroids del pkl
                centroids = {}
                centroid_file = Path("centroids.pkl")
                if centroid_file.exists():
                    try:
                        with open(centroid_file, 'rb') as cf:
                            centroids = pickle.load(cf)
                    except Exception:
                        pass
                
                file_bytes = np.fromfile(str(p_obj), dtype=np.uint8)
                img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                if img is None:
                    return
                    
                h, w, _ = img.shape
                max_sz = 1000
                faces_detected = None
                if max(h, w) > max_sz:
                    nw = max_sz if w > h else int(w * max_sz / h)
                    nh = max_sz if h >= w else int(h * max_sz / w)
                    img_small = cv2.resize(img, (nw, nh))
                    detector.setInputSize((nw, nh))
                    _, faces_small = detector.detect(img_small)
                    if faces_small is not None and len(faces_small) > 0:
                        faces_detected = faces_small.copy()
                        sx, sy = w / nw, h / nh
                        for face in faces_detected:
                            face[0] *= sx; face[1] *= sy
                            face[2] *= sx; face[3] *= sy
                            for li in range(4, 14, 2):
                                face[li] *= sx; face[li+1] *= sy
                else:
                    detector.setInputSize((w, h))
                    _, faces_detected = detector.detect(img)
                
                if faces_detected is None or len(faces_detected) == 0:
                    # Sin cara detectable → _Dudosos
                    _move_to_dudosos(p_obj)
                    return
                
                best_match_ident = None
                best_match_cat = None
                best_score = 0.0
                
                for face in faces_detected:
                    try:
                        aligned = recognizer.alignCrop(img, face)
                        feat = recognizer.feature(aligned)[0]
                        feat_norm = feat / (np.linalg.norm(feat) + 1e-10)
                    except Exception:
                        continue
                    
                    # Buscar en centroids.pkl (clave = (cat, ident))
                    for (c_cat, c_ident), centroid in centroids.items():
                        if c_ident == excluded_ident:
                            continue  # Excluir al dueño de la carpeta actual
                        score = float(np.dot(feat_norm, centroid) / (np.linalg.norm(centroid) + 1e-10))
                        if score > best_score:
                            best_score = score
                            best_match_ident = c_ident
                            best_match_cat = c_cat
                    
                    # También buscar en known_faces (sface_cache_v7.pkl)
                    for db_id, data_dict in known_faces.items():
                        if db_id == excluded_ident:
                            continue
                        centroid = data_dict.get('centroid')
                        if centroid is not None:
                            score = float(np.dot(feat_norm, centroid) / (np.linalg.norm(centroid) + 1e-10))
                            if score > best_score:
                                best_score = score
                                best_match_ident = db_id
                                best_match_cat = None  # inferir después
                
                CONFIDENCE_THRESHOLD = 0.58
                if best_match_ident and best_score >= CONFIDENCE_THRESHOLD:
                    # Mover a la carpeta del mejor candidato
                    if best_match_cat is None:
                        # Inferir categoría
                        if best_match_ident.startswith("F. "):
                            best_match_cat = "Familia"
                        elif best_match_ident.startswith("M. "):
                            best_match_cat = "Mascotas"
                        elif best_match_ident.startswith("P. "):
                            best_match_cat = "Profesores"
                        elif best_match_ident == "YO":
                            best_match_cat = "YO"
                        else:
                            best_match_cat = "Conocidos"
                    
                    dest_dir = RESULTADOS_DIR / best_match_cat / best_match_ident
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest_path = dest_dir / p_obj.name
                    counter = 1
                    while dest_path.exists() and dest_path.resolve() != p_obj.resolve():
                        dest_path = dest_dir / f"{p_obj.stem}_{counter}{p_obj.suffix}"
                        counter += 1
                    
                    if dest_path.resolve() != p_obj.resolve():
                        try:
                            shutil.move(str(p_obj), str(dest_path))
                        except Exception:
                            pass
                    
                    # Actualizar override con la nueva identidad
                    ov_overrides = load_overrides()
                    new_fkey = get_file_key(str(dest_path))
                    ov_overrides[new_fkey] = [{
                        'x': 0, 'y': 0, 'width': 0, 'height': 0,
                        'identity': best_match_ident,
                        'is_manual': False,
                        'confidence': f"{best_score:.2f}"
                    }]
                    save_overrides(ov_overrides)
                    
                    # Migrar clave en faces_cache
                    src_str = str(p_obj)
                    dst_str = str(dest_path)
                    with cache_lock:
                        if src_str in faces_cache:
                            faces_cache[dst_str] = faces_cache.pop(src_str)
                        try:
                            with open(FACES_CACHE_FILE, 'wb') as f:
                                pickle.dump(faces_cache, f)
                        except Exception:
                            pass
                    
                    print(f"Reclasificado: {p_obj.name} -> [{best_match_cat}] {best_match_ident} (score: {best_score:.2f})")
                else:
                    # No hay match suficiente → _Dudosos
                    _move_to_dudosos(p_obj)
                    print(f"Sin match claro para {p_obj.name} (best score: {best_score:.2f}) -> _Dudosos")
                    
            except Exception as e:
                print(f"Error en reclasificacion background: {e}")
                _move_to_dudosos(p_obj)

        def _move_to_dudosos(p):
            try:
                dudosos_dir = RESULTADOS_DIR / 'Conocidos' / '_Dudosos'
                dudosos_dir.mkdir(parents=True, exist_ok=True)
                dest = dudosos_dir / p.name
                counter = 1
                while dest.exists() and dest.resolve() != p.resolve():
                    dest = dudosos_dir / f"{p.stem}_{counter}{p.suffix}"
                    counter += 1
                if dest.resolve() != p.resolve():
                    shutil.move(str(p), str(dest))
            except Exception as me:
                print("Error moviendo a _Dudosos:", me)

        import threading
        threading.Thread(target=_reclassify_background, daemon=True).start()
                
        return jsonify({"success": True, "message": f"Foto removida de {ident}. Re-clasificando en background..."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_delete():
    from app.globals import faces_cache, FACES_CACHE_FILE
    from app.services.apple_service import is_apple_photo, mark_apple_photo_deleted_locally, mark_apple_photo_deleted_icloud
    
    data = request.json or {}
    path = data.get('path')
    delete_mode = data.get('delete_mode', 'local') # 'local' o 'icloud'
    
    if not path or not os.path.exists(path):
        return jsonify({"error": "Archivo no encontrado"}), 404
        
    try:
        if is_apple_photo(path):
            if delete_mode == 'local':
                mark_apple_photo_deleted_locally(path)
                return jsonify({"success": True})
            elif delete_mode == 'icloud':
                mark_apple_photo_deleted_icloud(path)
                return jsonify({"success": True})
                
        # Flujo Android normal
        try:
            import send2trash
            send2trash.send2trash(path)
        except Exception:
            os.remove(path)
            
        if path in faces_cache:
            del faces_cache[path]
            with open(FACES_CACHE_FILE, 'wb') as f:
                import pickle
                pickle.dump(faces_cache, f)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_delete_group():
    try:
        data = request.json or {}
        cat = data.get('cat', '').strip()
        ident = data.get('ident', '').strip()
        if not ident:
            return jsonify({"error": "Parámetros insuficientes"}), 400

        def clean_val(v):
            if not v: return ""
            s = str(v).strip()
            for prefix in ['👤', '📋', '📁', '❓', '🔍', '✨', '📸', '⚡', '🎉', '🏷️', '👥', '🧑', '👧', '👦']:
                if s.startswith(prefix):
                    s = s[len(prefix):].strip()
            return s

        c_ident = clean_val(ident)
        c_cat = clean_val(cat)

        target_dir = RESULTADOS_DIR / "Dudosos" / "Para Revisar"
        target_dir.mkdir(parents=True, exist_ok=True)

        matching_dirs = []
        candidates = [
            RESULTADOS_DIR / cat / ident,
            RESULTADOS_DIR / c_cat / c_ident,
            RESULTADOS_DIR / "Personas Sin Nombre" / c_ident,
            RESULTADOS_DIR / "Personas Sin Nombre" / ident,
            RESULTADOS_DIR / "Conocidos" / c_ident,
            RESULTADOS_DIR / "Conocidos" / ident,
            RESULTADOS_DIR / "Sin_Rostro" / c_ident,
            RESULTADOS_DIR / "Sin_Rostro" / ident,
            FOTOS_DIR / cat / ident,
            FOTOS_DIR / c_cat / c_ident,
            FOTOS_DIR / "Personas Sin Nombre" / c_ident,
            FOTOS_DIR / "Personas Sin Nombre" / ident,
            FOTOS_DIR / "Conocidos" / c_ident,
            FOTOS_DIR / "Conocidos" / ident,
        ]
        for p in candidates:
            if p.exists() and p.is_dir() and p not in matching_dirs:
                matching_dirs.append(p)

        if not matching_dirs and RESULTADOS_DIR.exists():
            for sub in RESULTADOS_DIR.iterdir():
                if sub.is_dir() and sub.name not in ["temp", "cache", ".thumbnails"]:
                    cand = sub / c_ident
                    if cand.is_dir() and cand not in matching_dirs:
                        matching_dirs.append(cand)
                    cand_raw = sub / ident
                    if cand_raw.is_dir() and cand_raw not in matching_dirs:
                        matching_dirs.append(cand_raw)

        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".avi"}
        moved_count = 0
        from app.utils.file_ops import safe_move_file

        for g_dir in matching_dirs:
            for f in list(g_dir.iterdir()):
                if f.is_file() and f.suffix.lower() in valid_exts:
                    target_file = target_dir / f.name
                    counter = 1
                    while target_file.exists():
                        target_file = target_dir / f"{f.stem}_{counter}{f.suffix}"
                        counter += 1
                    try:
                        safe_move_file(str(f), str(target_file))
                        moved_count += 1
                    except Exception:
                        pass
            try:
                os.rmdir(str(g_dir))
            except Exception:
                shutil.rmtree(str(g_dir), ignore_errors=True)

        from app.services.apple_service import delete_apple_group
        delete_apple_group(cat, ident)
        if c_ident != ident or c_cat != cat:
            delete_apple_group(c_cat, c_ident)

        # Invalidate known_faces
        try:
            from app.globals import cache_lock, known_faces, CACHE_FILE
            import pickle
            with cache_lock:
                for k in [ident, c_ident]:
                    if k in known_faces:
                        del known_faces[k]
                with open(CACHE_FILE, 'wb') as f_cache:
                    pickle.dump(known_faces, f_cache)
        except Exception:
            pass

        # Clean overrides and clear cache
        overrides = load_overrides()
        keys_to_del = [k for k, v in overrides.items() if ident in str(v) or c_ident in str(v)]
        if keys_to_del:
            for k in keys_to_del:
                del overrides[k]
            save_overrides(overrides)

        set_gallery_cache(None)
        try:
            from app.utils.faces import clear_identities_cache
            clear_identities_cache()
        except Exception:
            pass

        return jsonify({"success": True, "message": f"Grupo '{ident}' disuelto correctamente ({moved_count} fotos movidas a revisión)."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_batch_delete():
    from app.globals import faces_cache, FACES_CACHE_FILE, clear_gallery_cache, cache_lock, known_faces, CACHE_FILE
    from app.services.apple_service import is_apple_photo, mark_apple_photo_deleted_locally, delete_apple_group
    import pickle
    try:
        import send2trash
    except ImportError:
        send2trash = None

    try:
        data = request.json or {}
        paths = data.get('paths') or data.get('files') or []
        cat = str(data.get('cat', '')).strip()
        ident = str(data.get('ident', '')).strip()
        is_entire_album = bool(data.get('entire_album', False))

        def clean_val(v):
            if not v: return ""
            s = str(v).strip()
            for prefix in ['👤', '📋', '📁', '❓', '🔍', '✨', '📸', '⚡', '🎉', '🏷️', '👥', '🧑', '👧', '👦', '⚠️', '⏳']:
                if s.startswith(prefix):
                    s = s[len(prefix):].strip()
            return s

        c_ident = clean_val(ident)
        c_cat = clean_val(cat)

        file_paths = []
        for item in paths:
            if isinstance(item, str) and item:
                file_paths.append(item)
            elif isinstance(item, dict) and item.get('path'):
                file_paths.append(item['path'])

        # If entire_album or no paths provided, resolve all photos of this album
        if (is_entire_album or not file_paths) and ident:
            from app.globals import get_gallery_cache
            cache = get_gallery_cache()
            if not cache:
                from app.services.gallery_service import get_gallery
                cache = get_gallery()

            album_items = []
            if cache and cat in cache and ident in cache[cat]:
                album_items = cache[cat][ident]
            elif cache and c_cat in cache and c_ident in cache[c_cat]:
                album_items = cache[c_cat][c_ident]
            elif cache:
                for c, idents in cache.items():
                    if ident in idents:
                        album_items = idents[ident]
                        break
                    if c_ident in idents:
                        album_items = idents[c_ident]
                        break

            for it in album_items:
                p = it.get('path') if isinstance(it, dict) else str(it)
                if p and p not in file_paths:
                    file_paths.append(p)

        if not file_paths and not ident:
            return jsonify({"error": "No se indicaron fotos ni álbum para eliminar"}), 400

        trashed_count = 0
        cache_dirty = False

        for p in file_paths:
            try:
                if is_apple_photo(p):
                    mark_apple_photo_deleted_locally(p)
                    trashed_count += 1
                elif os.path.exists(p):
                    try:
                        if send2trash:
                            send2trash.send2trash(p)
                        else:
                            os.remove(p)
                    except Exception:
                        try:
                            os.remove(p)
                        except Exception:
                            pass
                    trashed_count += 1

                if p in faces_cache:
                    del faces_cache[p]
                    cache_dirty = True
            except Exception as e:
                print(f"[BATCH DELETE ERROR] Error eliminando {p}: {e}")

        if cache_dirty:
            try:
                with open(FACES_CACHE_FILE, 'wb') as f:
                    pickle.dump(faces_cache, f)
            except Exception:
                pass

        if is_entire_album and ident:
            candidates = [
                RESULTADOS_DIR / cat / ident,
                RESULTADOS_DIR / c_cat / c_ident,
                RESULTADOS_DIR / "Personas Sin Nombre" / c_ident,
                RESULTADOS_DIR / "Personas Sin Nombre" / ident,
                RESULTADOS_DIR / "Conocidos" / c_ident,
                RESULTADOS_DIR / "Conocidos" / ident,
                FOTOS_DIR / cat / ident,
                FOTOS_DIR / c_cat / c_ident,
                FOTOS_DIR / "Personas Sin Nombre" / c_ident,
                FOTOS_DIR / "Personas Sin Nombre" / ident,
                FOTOS_DIR / "Conocidos" / c_ident,
                FOTOS_DIR / "Conocidos" / ident,
            ]
            valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".avi"}
            for d in candidates:
                if d.exists() and d.is_dir():
                    try:
                        has_media = any(f.suffix.lower() in valid_exts for f in d.iterdir() if f.is_file())
                        if not has_media:
                            shutil.rmtree(str(d), ignore_errors=True)
                    except Exception:
                        pass

            delete_apple_group(cat, ident)
            if c_ident != ident or c_cat != cat:
                delete_apple_group(c_cat, c_ident)

            try:
                with cache_lock:
                    for k in [ident, c_ident]:
                        if k in known_faces:
                            del known_faces[k]
                    with open(CACHE_FILE, 'wb') as f_cache:
                        pickle.dump(known_faces, f_cache)
            except Exception:
                pass

            overrides = load_overrides()
            keys_to_del = [k for k, v in overrides.items() if ident in str(v) or c_ident in str(v)]
            if keys_to_del:
                for k in keys_to_del:
                    del overrides[k]
                save_overrides(overrides)

        clear_gallery_cache(unlink_file=True)
        try:
            from app.utils.faces import clear_identities_cache
            clear_identities_cache()
        except Exception:
            pass

        return jsonify({
            "success": True,
            "count": trashed_count,
            "message": f"{trashed_count} foto(s) enviadas a la Papelera"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_batch_move():
    from app.globals import detector, recognizer
    from app.services.apple_service import is_apple_photo, update_apple_photo_mapping
    import pickle
    
    try:
        data = request.json or {}
        files = data.get('files', [])
        target_cat = data.get('target_cat')
        target_ident = data.get('target_ident')
        
        if not files or not target_cat or not target_ident:
            return jsonify({"error": "Parámetros incompletos"}), 400
            
        target_dir = FOTOS_DIR / target_cat / target_ident
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
        
        for fobj in files:
            if isinstance(fobj, str):
                p = fobj
            else:
                p = fobj.get('path')
            
            if p and os.path.exists(p):
                # Si es foto de Apple, actualizamos BD en vez de mover
                if is_apple_photo(p):
                    update_apple_photo_mapping(p, target_cat, target_ident)
                    moved_count += 1
                    continue
                    
                p_obj = Path(p)
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
                    
                    # Migrate faces_cache key
                    if str(dest) != str(p_obj) and str(p_obj) in faces_cache:
                        faces_cache[str(dest)] = faces_cache.pop(str(p_obj))
                    
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
        
        # Save faces_cache to disk in background (non-blocking)
        def _save_faces_cache_batch():
            try:
                from app.globals import FACES_CACHE_FILE, cache_lock
                with cache_lock:
                    with open(FACES_CACHE_FILE, 'wb') as f:
                        pickle.dump(faces_cache, f)
            except Exception:
                pass
        import threading
        threading.Thread(target=_save_faces_cache_batch, daemon=True).start()
        if new_features and target_cat != "Mascotas":
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






import zipfile
import io
import urllib.parse

def api_export_zip():
    try:
        data = request.get_json(silent=True) or {}
        paths = data.get('paths')
        album_name = data.get('name')
        
        if not paths:
            cat = request.args.get('cat')
            ident = request.args.get('ident')
            if not cat or not ident:
                return jsonify({"error": "Parámetros insuficientes"}), 400
            
            album_name = ident
            g_cache = get_gallery_cache()
            if g_cache is None:
                get_gallery()
                g_cache = get_gallery_cache() or {}
            
            items = g_cache.get(cat, {}).get(ident, [])
            paths = [item['path'] for item in items if 'path' in item]
            
        if not paths:
            return jsonify({"error": "No hay fotos para exportar"}), 404
            
        album_name = album_name or "album_fotos"
        safe_name = "".join(c for c in album_name if c.isalnum() or c in (' ', '_', '-')).strip()
        safe_name = safe_name.replace(' ', '_')
        
        memory_file = io.BytesIO()
        used_names = set()
        
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for p in paths:
                real_p = find_relocated_file(p) or p
                if os.path.exists(real_p) and os.path.isfile(real_p):
                    base_fn = os.path.basename(real_p)
                    archive_fn = base_fn
                    counter = 1
                    while archive_fn in used_names:
                        stem, ext = os.path.splitext(base_fn)
                        archive_fn = f"{stem}_{counter}{ext}"
                        counter += 1
                    used_names.add(archive_fn)
                    zf.write(real_p, arcname=archive_fn)
                    
        memory_file.seek(0)
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{safe_name}.zip"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
