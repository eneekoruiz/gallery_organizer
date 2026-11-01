# coding: utf-8
import pathlib
import re

content = pathlib.Path('app/services/face_service.py').read_text(encoding='utf-8')

replacement = '''def api_rename_group():
    try:
        data = request.json or {}
        cat = data.get('cat')
        ident = data.get('ident')
        new_name = data.get('new_name') or data.get('new_ident') or data.get('name')
        new_cat = data.get('new_cat')
        
        if not cat or not ident or not new_name:
            return jsonify({"error": "Parametros insuficientes: falta el nuevo nombre"}), 400

        if not new_cat or new_cat.strip() == "":
            if new_name.startswith('F. ') or new_name.startswith('F_'):
                new_cat = 'Familia'
            elif new_name.startswith('P. ') or new_name.startswith('P_'):
                new_cat = 'Profesores'
            elif new_name.startswith('M. ') or new_name.startswith('M_'):
                new_cat = 'Mascotas'
            elif new_name == 'YO':
                new_cat = 'YO'
            else:
                new_cat = 'Conocidos'

        src_dir_res = RESULTADOS_DIR / cat / ident
        src_dir_fotos = FOTOS_DIR / cat / ident
        
        if not src_dir_res.exists() and not src_dir_fotos.exists():
            return jsonify({"error": "Carpeta de grupo no encontrada"}), 404
            
        target_dir_res = RESULTADOS_DIR / new_cat / new_name
        target_dir_res.mkdir(parents=True, exist_ok=True)
        
        target_dir_fotos = FOTOS_DIR / new_cat / new_name
        
        moved_count = 0
        valid_exts = {".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi"}
        
        if src_dir_res.exists():
            for file_path in src_dir_res.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in valid_exts:
                    target_file = target_dir_res / file_path.name
                    counter = 1
                    while target_file.exists():
                        target_file = target_dir_res / f"{file_path.stem}_{counter}{file_path.suffix}"
                        counter += 1
                    try:
                        safe_move(str(file_path), str(target_file))
                        moved_count += 1
                    except Exception as e:
                        try:
                            safe_move_file(file_path, target_file)
                            moved_count += 1
                        except:
                            pass
            try:
                os.rmdir(str(src_dir_res))
            except:
                pass

        if src_dir_fotos.exists():
            target_dir_fotos.mkdir(parents=True, exist_ok=True)
            for file_path in src_dir_fotos.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in valid_exts:
                    target_file = target_dir_fotos / file_path.name
                    counter = 1
                    while target_file.exists():
                        target_file = target_dir_fotos / f"{file_path.stem}_{counter}{file_path.suffix}"
                        counter += 1
                    try:
                        safe_move_file(file_path, target_file)
                        moved_count += 1
                    except:
                        pass
            try:
                os.rmdir(str(src_dir_fotos))
            except:
                pass

        try:
            new_feats = []
            for file_path in target_dir_res.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                    file_bytes = np.fromfile(str(file_path), dtype=np.uint8)
                    img_al = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                    if img_al is not None and detector is not None and recognizer is not None:
                        h_al, w_al, _ = img_al.shape
                        detector.setInputSize((w_al, h_al))
                        _, faces_al = detector.detect(img_al)
                        if faces_al is not None and len(faces_al) > 0:
                            aligned = recognizer.alignCrop(img_al, faces_al[0])
                            feat = recognizer.feature(aligned)[0]
                            new_feats.append(feat)
                            
            if len(new_feats) > 0:
                avg_new = np.mean(new_feats, axis=0)
                if new_name in known_faces and 'centroid' in known_faces[new_name]:
                    old_cent = known_faces[new_name]['centroid']
                    known_faces[new_name]['centroid'] = 0.7 * old_cent + 0.3 * avg_new
                else:
                    known_faces[new_name] = {'centroid': avg_new, 'names': []}
                    
                with cache_lock:
                    with open(CACHE_FILE, 'wb') as f_cache:
                        pickle.dump(known_faces, f_cache)
        except Exception as ex_retrain:
            pass
        
        clear_gallery_cache()
        return jsonify({"success": True, "count": moved_count})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Error interno en el servidor: {str(e)}"}), 500
'''

# Find the block and replace
new_content = re.sub(r'def api_rename_group\(\).*?(?=def api_relearn_cascade)', replacement + '\n', content, flags=re.DOTALL)
pathlib.Path('app/services/face_service.py').write_text(new_content, encoding='utf-8')
