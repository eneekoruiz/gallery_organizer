from app.globals import cache_lock
from flask import Blueprint, jsonify, request
import os
import cv2
import numpy as np
import shutil
import pickle
from pathlib import Path
from app.globals import (
    FOTOS_DIR, RESULTADOS_DIR, CACHE_FILE, FACES_CACHE_FILE, 
    PENDING_DELETIONS_FILE, detector, recognizer, known_faces, 
    faces_cache, clear_gallery_cache, get_gallery_cache
)
from app.utils.faces import get_cosine_similarity, iou
from app.utils.files import safe_move, load_overrides, save_overrides, find_relocated_file, get_file_key, safe_move_file, safe_remove_file

def api_analyze():
    data = request.json
    filepath = data.get('path')
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
        
    path_obj = Path(filepath)
    is_video = path_obj.suffix.lower() in [".mp4", ".mov", ".avi"]
    faces_data = []
    
    force_reanalyze = data.get('force', False) or is_video or (data.get('timestamp') is not None)
    if not force_reanalyze and filepath in faces_cache:
        return jsonify({"faces": faces_cache[filepath]})
        
    try:
        timestamp_in = data.get('timestamp')
        timestamp = 0.0
        
        if is_video:
            cap = cv2.VideoCapture(str(filepath))
            fps = cap.get(cv2.CAP_PROP_FPS)
            img = None
            if timestamp_in is not None:
                timestamp = float(timestamp_in)
                if fps > 0:
                    target_frame = max(0, int(timestamp * fps))
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                    ret, img = cap.read()
                else:
                    ret = False
                if not ret or img is None:
                    cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
                    ret, frame = cap.read()
                    if ret: img = frame
                if img is None:
                    cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
                    ret, frame = cap.read()
                    if ret: img = frame
            else:
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                target_frame = 0
                if frame_count > 10:
                    target_frame = frame_count // 2
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                ret, frame = cap.read()
                if ret: img = frame
                if fps > 0: timestamp = target_frame / fps
            cap.release()
            
            if img is None:
                return jsonify({"error": "No se pudo leer el fotograma del vídeo (Windows Codec Error)"}), 500
        else:
            file_bytes = np.fromfile(str(filepath), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            
        if img is not None:
            height, width, _ = img.shape
            
        if img is not None and detector is not None and recognizer is not None:
            detector.setInputSize((width, height))
            detector.setScoreThreshold(0.55)
            h_f, w_f = img.shape[:2]
            detector.setInputSize((w_f, h_f))
            _, faces = detector.detect(img)
            
            overrides = load_overrides()
            file_key = get_file_key(filepath)
            file_overrides = overrides.get(file_key, [])
            
            if faces is not None:
                for face in faces:
                    x, y, w, h = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                    x, y = max(0, x), max(0, y)
                    w, h = min(w, width - x), min(h, height - y)
                    
                    identity_name = "Desconocido"
                    confidence_str = ""
                    current_box = [x, y, w, h]
                    
                    override_match = None
                    for ov in file_overrides:
                        ov_box = [ov['x'], ov['y'], ov['width'], ov['height']]
                        if iou(current_box, ov_box) > 0.4:
                            override_match = ov['identity']
                            x, y, w, h = ov['x'], ov['y'], ov['width'], ov['height']
                            break
                            
                    if override_match:
                        if override_match in ["Ignorar_Irrelevante", "Falso_Positivo"]:
                            continue
                        identity_name = override_match
                        confidence_str = "100.0%"
                    else:
                        try:
                            aligned = recognizer.alignCrop(img, face)
                            feature = recognizer.feature(aligned)
                            best_match = None
                            best_score = 0
                            for db_id, data_dict in known_faces.items():
                                centroid = data_dict.get('centroid')
                                if centroid is not None:
                                    score = get_cosine_similarity(feature[0], centroid)
                                    if score > best_score:
                                        best_score = score
                                        best_match = db_id
                            
                            if best_match and best_score > 0.45:
                                if best_match.startswith("Falso_Positivo"):
                                    continue
                                identity_name = best_match
                                confidence_str = f"{(best_score * 100):.1f}%"
                            elif best_match and best_score > 0.30:
                                current_folder = path_obj.parent.name
                                owner_folder = path_obj.parent.parent.name if current_folder == "_Dudosos" else current_folder
                                if best_match == owner_folder:
                                    identity_name = f"? {best_match}"
                                    confidence_str = f"{(best_score * 100):.1f}% (Dudoso)"
                        except:
                            pass
                    
                    faces_data.append({
                        "x": x, "y": y, "width": w, "height": h,
                        "img_width": width, "img_height": height,
                        "identity": identity_name,
                        "confidence": confidence_str,
                        "feature": feature[0] if ('feature' in locals() and feature is not None) else None
                    })
            
            folder_owner = Path(filepath).parent.name
            is_valid_owner = folder_owner not in ["_Dudosos", "Personas Sin Nombre", "Resultados", "Fotos", "Conocidos", "Ignorar"]
            
            if is_valid_owner and len(faces_data) > 0:
                owner_assigned = any(f["identity"] == folder_owner for f in faces_data)
                if not owner_assigned:
                    best_idx = -1
                    best_owner_score = -1.0
                    owner_centroid = known_faces.get(folder_owner, {}).get('centroid')
                    
                    for idx, f in enumerate(faces_data):
                        if f["identity"] == "Desconocido":
                            if owner_centroid is not None and f.get("feature") is not None:
                                score = get_cosine_similarity(f["feature"], owner_centroid)
                                if score > best_owner_score:
                                    best_owner_score = score
                                    best_idx = idx
                                    
                    if best_idx == -1:
                        for idx, f in enumerate(faces_data):
                            if f["identity"] == "Desconocido":
                                best_idx = idx
                                break
                                
                    if best_idx != -1:
                        faces_data[best_idx]["identity"] = folder_owner
                        faces_data[best_idx]["confidence"] = "✨ 100.0% (Propietario del Álbum)"
            
            elif is_valid_owner and len(faces_data) == 0 and width > 0 and height > 0:
                faces_data.append({
                    "x": int(width * 0.15),
                    "y": int(height * 0.15),
                    "width": int(width * 0.70),
                    "height": int(height * 0.70),
                    "img_width": width,
                    "img_height": height,
                    "identity": folder_owner,
                    "confidence": "✨ Recuadro de Rescate (Álbum)"
                })
                        
            for f in faces_data:
                if "feature" in f: del f["feature"]

    except Exception as e:
        return jsonify({"error": str(e)})
        
    return jsonify({"faces": faces_data, "timestamp": timestamp})

def apply_correction_to_file(filepath, new_categoria, new_identidad, face_data):
    if filepath and not os.path.exists(filepath):
        resolved = find_relocated_file(filepath)
        if resolved and os.path.exists(resolved):
            filepath = resolved
    if not filepath or not os.path.exists(filepath):
        return None
    orig_path = Path(filepath)
    is_manual_source = False
    try:
        if orig_path.is_relative_to(FOTOS_DIR):
            is_manual_source = True
    except ValueError:
        pass
        
    overrides = load_overrides()
    file_key = get_file_key(filepath)
    
    if face_data:
        if file_key not in overrides: overrides[file_key] = []
        updated = False
        face_box = [face_data['x'], face_data['y'], face_data['width'], face_data['height']]
        for ov in overrides[file_key]:
            ov_box = [ov['x'], ov['y'], ov['width'], ov['height']]
            if iou(face_box, ov_box) > 0.4:
                ov['identity'] = new_identidad
                ov['x'] = face_data['x']
                ov['y'] = face_data['y']
                ov['width'] = face_data['width']
                ov['height'] = face_data['height']
                updated = True
                break
        if not updated:
            overrides[file_key].append({
                'x': face_data['x'], 'y': face_data['y'], 
                'width': face_data['width'], 'height': face_data['height'],
                'identity': new_identidad
            })
        save_overrides(overrides)
        
        if filepath not in faces_cache:
            faces_cache[filepath] = []
            
        updated_cache = False
        for c_face in faces_cache[filepath]:
            c_box = [c_face['x'], c_face['y'], c_face['width'], c_face['height']]
            if iou(face_box, c_box) > 0.4:
                c_face['identity'] = new_identidad
                c_face['confidence'] = "100.0"
                c_face['is_manual'] = True
                updated_cache = True
                break
                
        if not updated_cache:
            faces_cache[filepath].append({
                'x': face_data['x'], 'y': face_data['y'],
                'width': face_data['width'], 'height': face_data['height'],
                'identity': new_identidad, 'confidence': "100.0", 'is_manual': True
            })
            
        # Save faces_cache to disk in background (non-blocking)
        def _save_faces_cache():
            try:
                with cache_lock:
                    with open(FACES_CACHE_FILE, 'wb') as f:
                        pickle.dump(faces_cache, f)
            except Exception:
                pass
        import threading
        threading.Thread(target=_save_faces_cache, daemon=True).start()

    if new_identidad not in ["Falso_Positivo", "Ignorar_Irrelevante"] and face_data:
        # Update centroid in background — slow cv2 operation
        def _update_centroid(orig_path=orig_path, face_data=face_data, new_identidad=new_identidad):
            try:
                file_bytes = np.fromfile(str(orig_path), dtype=np.uint8)
                img_al = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                if img_al is not None:
                    h_al, w_al, _ = img_al.shape
                    x1 = max(0, int(face_data['x']))
                    y1 = max(0, int(face_data['y']))
                    x2 = min(w_al, x1 + int(face_data['width']))
                    y2 = min(h_al, y1 + int(face_data['height']))
                    if (x2 - x1) > 10 and (y2 - y1) > 10:
                        crop = img_al[y1:y2, x1:x2]
                        resized_crop = cv2.resize(crop, (112, 112))
                        feature = recognizer.feature(resized_crop)
                        dict_key = new_identidad
                        if dict_key in known_faces and 'centroid' in known_faces[dict_key]:
                            old_centroid = known_faces[dict_key]['centroid']
                            new_centroid = old_centroid * 0.85 + feature[0] * 0.15
                            new_centroid = new_centroid / np.linalg.norm(new_centroid)
                            known_faces[dict_key]['centroid'] = new_centroid
                        else:
                            known_faces[dict_key] = {'centroid': feature[0], 'names': [orig_path.name]}
                        with cache_lock:
                            with open(CACHE_FILE, 'wb') as cf:
                                pickle.dump(known_faces, cf)
            except Exception:
                pass
        import threading
        threading.Thread(target=_update_centroid, daemon=True).start()

    target_path = orig_path
    if new_categoria != "Ignorar" and new_identidad not in ["Falso_Positivo", "Ignorar_Irrelevante"]:
        if is_manual_source:
            target_dir = FOTOS_DIR / new_categoria / new_identidad
        else:
            target_dir = RESULTADOS_DIR / new_categoria / new_identidad
            
        target_dir.mkdir(parents=True, exist_ok=True)
        
        if orig_path.parent.resolve() == target_dir.resolve():
            target_path = orig_path
        else:
            orig_ino = os.stat(str(orig_path)).st_ino
            existing_link = None
            for f in target_dir.iterdir():
                if f.is_file() and os.stat(str(f)).st_ino == orig_ino:
                    existing_link = f
                    break
                    
            if existing_link:
                target_path = existing_link
            else:
                target_path = target_dir / orig_path.name
                counter = 1
                while target_path.exists():
                    target_path = target_dir / f"{orig_path.stem}_{counter}{orig_path.suffix}"
                    counter += 1
                try:
                    os.link(str(orig_path), str(target_path))
                except Exception:
                    try:
                        shutil.copy2(str(orig_path), str(target_path))
                    except Exception:
                        pass
                        
            orig_str = str(orig_path)
            if "_Dudosos" in orig_str or "Desconocidos" in orig_str or "Personas Sin Nombre" in orig_str:
                try:
                    if os.path.exists(orig_str):
                        os.remove(orig_str)
                except Exception as e:
                    pass
            
    # Update faces_cache key immediately (in-memory, fast)
    if str(target_path) != filepath and filepath in faces_cache:
        faces_cache[str(target_path)] = faces_cache.pop(filepath)

    # All slow GC + cleanup runs in background so response is instant
    def _background_gc(orig_path=orig_path, target_path=target_path, face_data=face_data, filepath=filepath):
        import threading
        try:
            if target_path == orig_path:
                return

            overrides = load_overrides()
            file_key = get_file_key(str(orig_path))
            other_faces_same_person = False
            face_box = [face_data['x'], face_data['y'], face_data['width'], face_data['height']] if face_data else None

            if file_key in overrides:
                for ov in overrides[file_key]:
                    if ov.get('identity') == orig_path.parent.name and (face_box is None or iou([ov['x'], ov['y'], ov['width'], ov['height']], face_box) <= 0.4):
                        other_faces_same_person = True
                        break

            if not other_faces_same_person:
                try:
                    file_bytes = np.fromfile(str(orig_path), dtype=np.uint8)
                    img_gc = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                    if img_gc is not None:
                        h_gc, w_gc, _ = img_gc.shape
                        detector.setInputSize((w_gc, h_gc))
                        _, faces_gc = detector.detect(img_gc)
                        if faces_gc is not None:
                            for f in faces_gc:
                                f_box = [int(f[0]), int(f[1]), int(f[2]), int(f[3])]
                                if face_box and iou(f_box, face_box) > 0.4:
                                    continue
                                aligned = recognizer.alignCrop(img_gc, f)
                                feature = recognizer.feature(aligned)
                                if feature is None:
                                    continue
                                best_score = 0
                                best_match = None
                                for db_id, data_dict in known_faces.items():
                                    centroid = data_dict.get('centroid')
                                    if centroid is not None:
                                        score = get_cosine_similarity(feature[0], centroid)
                                        if score > best_score:
                                            best_score = score
                                            best_match = db_id
                                if best_match == orig_path.parent.name and best_score > 0.30:
                                    other_faces_same_person = True
                                    break
                except Exception:
                    pass

            if not other_faces_same_person:
                try:
                    safe_remove_file(orig_path)
                except Exception:
                    try:
                        with cache_lock:
                            with open(PENDING_DELETIONS_FILE, 'a') as pf:
                                pf.write(str(orig_path) + '\n')
                    except Exception:
                        pass

            # Persist faces_cache after key rename
            try:
                with open(FACES_CACHE_FILE, 'wb') as f:
                    pickle.dump(faces_cache, f)
            except Exception:
                pass

        except Exception:
            pass

    import threading
    threading.Thread(target=_background_gc, daemon=True).start()

    return str(target_path)


def api_correct():
    data = request.json or {}
    filepath = data.get('path')
    new_categoria = data.get('new_categoria')
    new_identidad = data.get('new_identidad')
    face_data = data.get('face')
    
    if not filepath:
        return jsonify({"error": "Falta parámetro path"}), 400
        
    real_path = find_relocated_file(filepath)
    if real_path and os.path.exists(real_path):
        filepath = real_path
        
    if not os.path.exists(filepath):
        return jsonify({"error": f"El archivo {filepath} no existe en disco"}), 404
        
    clear_gallery_cache()
    
    try:
        target_path = apply_correction_to_file(filepath, new_categoria, new_identidad, face_data)
        
        def bg_save():
            try:
                from app.utils.files import safe_move, process_pending_deletions
                process_pending_deletions()
            except: pass
                
        import threading
        threading.Thread(target=bg_save, daemon=True).start()
        
        res_path = str(target_path) if target_path else filepath
        return jsonify({"success": True, "new_path": res_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def api_rename_group():
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

def api_relearn_cascade():
    try:
        data = request.json or {}
        identity = data.get('identity', '')
        if not identity or identity not in known_faces:
            return jsonify({"promoted": 0, "message": "Identidad no encontrada en el modelo"})
        
        centroid = known_faces[identity].get('centroid')
        if centroid is None:
            return jsonify({"promoted": 0, "message": "Sin centroide disponible"})
        
        dudosos_dir = RESULTADOS_DIR / "Conocidos" / "_Dudosos"
        promoted = 0
        
        if dudosos_dir.exists():
            valid_exts = {'.jpg', '.jpeg', '.png'}
            for folder in dudosos_dir.iterdir():
                if not folder.is_dir(): continue
                for img_file in folder.iterdir():
                    if img_file.suffix.lower() not in valid_exts: continue
                    try:
                        file_bytes = np.fromfile(str(img_file), dtype=np.uint8)
                        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                        if img is None: continue
                        
                        h, w, _ = img.shape
                        faces_detected = detector.detect(img)
                        if faces_detected[1] is None: continue
                        
                        for det in faces_detected[1]:
                            x1 = max(0, int(det[0]))
                            y1 = max(0, int(det[1]))
                            bw = int(det[2])
                            bh = int(det[3])
                            x2 = min(w, x1 + bw)
                            y2 = min(h, y1 + bh)
                            
                            if (x2 - x1) < 20 or (y2 - y1) < 20: continue
                            
                            crop = img[y1:y2, x1:x2]
                            resized = cv2.resize(crop, (112, 112))
                            feature = recognizer.feature(resized)
                            
                            score = get_cosine_similarity(centroid, feature[0])
                            if score > 0.38:
                                target_dir = RESULTADOS_DIR / "Conocidos" / identity
                                target_dir.mkdir(parents=True, exist_ok=True)
                                target = target_dir / img_file.name
                                if not target.exists():
                                    import shutil
                                    safe_move(str(img_file), str(target))
                                    promoted += 1
                                break
                    except: pass
        
        clear_gallery_cache()
        return jsonify({"promoted": promoted, "identity": identity, "message": f"{promoted} fotos promovidas de _Dudosos a {identity}"})
    except Exception as e:
        return jsonify({"promoted": 0, "error": str(e)})


def api_auto_classify_filename():
    try:
        moved = 0
        known_names = list(known_faces.keys())
        
        scan_dirs = [
            RESULTADOS_DIR / "Conocidos" / "_Dudosos",
            RESULTADOS_DIR / "Conocidos" / "Desconocidos",
            RESULTADOS_DIR / "Personas Sin Nombre",
        ]
        
        import shutil
        valid_exts = {'.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi'}
        
        for scan_dir in scan_dirs:
            if not scan_dir.exists(): continue
            for root, dirs, files in os.walk(str(scan_dir)):
                for fname in files:
                    fp = Path(root) / fname
                    if fp.suffix.lower() not in valid_exts: continue
                    
                    fname_lower = fname.lower()
                    parent_lower = fp.parent.name.lower()
                    
                    for kn in known_names:
                        kn_parts = kn.replace("C. ", "").replace("F. ", "").replace("M. ", "").split()
                        if len(kn_parts) < 1: continue
                        
                        search_term = " ".join(kn_parts).lower()
                        if len(search_term) < 4: continue
                        
                        if search_term in fname_lower or search_term in parent_lower:
                            cat = "Conocidos"
                            if kn.startswith("F."): cat = "Familiares"
                            elif kn.startswith("M."): cat = "Mascotas"
                            
                            target_dir = RESULTADOS_DIR / cat / kn
                            target_dir.mkdir(parents=True, exist_ok=True)
                            target = target_dir / fp.name
                            if not target.exists():
                                try:
                                    safe_move(str(fp), str(target))
                                    moved += 1
                                except: pass
                            break
        
        clear_gallery_cache()
        return jsonify({"moved": moved, "message": f"{moved} archivos clasificados por nombre de archivo"})
    except Exception as e:
        return jsonify({"moved": 0, "error": str(e)})

def api_reset_face_learning():
    try:
        with cache_lock:
            known_faces.clear()
            faces_cache.clear()
            if os.path.exists(CACHE_FILE):
                try: os.remove(CACHE_FILE)
                except: pass
            if os.path.exists(FACES_CACHE_FILE):
                try: os.remove(FACES_CACHE_FILE)
                except: pass
            clear_gallery_cache()
        return jsonify({"success": True, "message": "Aprendizaje de IA y caché de caras reiniciados correctamente."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def api_rebuild_clean_centroids():
    try:
        if detector is None or recognizer is None:
            return jsonify({"success": False, "error": "Modelos de IA no cargados."}), 500

        target_cats = ["Conocidos", "Familiares", "Mascotas"]
        valid_exts = {".jpg", ".jpeg", ".png"}
        
        rebuilt_count = 0
        total_photos_processed = 0
        outliers_rejected = 0
        new_known_faces = {}

        for cat in target_cats:
            cat_dir = RESULTADOS_DIR / cat
            if not cat_dir.exists():
                continue

            for ident_dir in cat_dir.iterdir():
                if not ident_dir.is_dir():
                    continue
                identity_name = ident_dir.name
                if identity_name.startswith("_") or identity_name in ["Desconocidos", "Personas Sin Nombre", "Ignorar"]:
                    continue

                feats = []
                sample_names = []

                for img_file in ident_dir.iterdir():
                    if not img_file.is_file() or img_file.suffix.lower() not in valid_exts:
                        continue
                    try:
                        file_bytes = np.fromfile(str(img_file), dtype=np.uint8)
                        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                        if img is None:
                            continue
                        
                        h, w, _ = img.shape
                        detector.setInputSize((w, h))
                        _, faces_detected = detector.detect(img)
                        if faces_detected is not None and len(faces_detected) > 0:
                            aligned = recognizer.alignCrop(img, faces_detected[0])
                            feat = recognizer.feature(aligned)[0]
                            feat_norm = feat / (np.linalg.norm(feat) + 1e-10)
                            feats.append(feat_norm)
                            sample_names.append(img_file.name)
                            total_photos_processed += 1
                    except Exception:
                        pass

                if len(feats) > 0:
                    feats_arr = np.array(feats)
                    raw_centroid = np.mean(feats_arr, axis=0)
                    raw_centroid /= (np.linalg.norm(raw_centroid) + 1e-10)

                    valid_feats = []
                    for idx, feat in enumerate(feats_arr):
                        sim = get_cosine_similarity(raw_centroid, feat)
                        if sim >= 0.35:
                            valid_feats.append(feat)
                        else:
                            outliers_rejected += 1

                    if len(valid_feats) == 0:
                        valid_feats = feats_arr

                    clean_centroid = np.mean(valid_feats, axis=0)
                    clean_centroid /= (np.linalg.norm(clean_centroid) + 1e-10)

                    new_known_faces[identity_name] = {
                        'centroid': clean_centroid,
                        'names': sample_names
                    }
                    rebuilt_count += 1

        with cache_lock:
            known_faces.clear()
            known_faces.update(new_known_faces)
            with open(CACHE_FILE, 'wb') as f_cache:
                pickle.dump(known_faces, f_cache)
            clear_gallery_cache()

        return jsonify({
            "success": True,
            "identities_rebuilt": rebuilt_count,
            "photos_processed": total_photos_processed,
            "outliers_rejected": outliers_rejected,
            "message": f"Se han recalculado {rebuilt_count} personas limpiamente desde el dataset confirmado ({outliers_rejected} fotos atípicas descartadas)."
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def api_detect_deep():
    from app.globals import APP_DIR
    data = request.json
    filepath = data.get('path')
    if not filepath:
        return jsonify({"error": "File not found"}), 404
        
    p_obj = Path(filepath)
    if not p_obj.exists():
        alt_p = Path(filepath.replace('/', '\\')) if '/' in filepath else Path(filepath.replace('\\', '/'))
        if alt_p.exists():
            p_obj = alt_p
        else:
            return jsonify({"error": "File not found"}), 404
            
    filepath = str(p_obj)
        
    try:
        file_bytes = np.fromfile(filepath, dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({"error": "Could not read image"}), 400
            
        h, w = img.shape[:2]
        
        try:
            deep_detector = cv2.FaceDetectorYN.create(str(APP_DIR / "models" / "face_detection_yunet.onnx"), "", (w, h), score_threshold=0.5, nms_threshold=0.3)
            _, faces = deep_detector.detect(img)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
        if faces is not None:
            new_faces = []
            for face in faces:
                x, y, w_f, h_f = map(int, face[:4])
                conf = face[-1]
                new_faces.append({
                    "x": x, "y": y, "width": w_f, "height": h_f,
                    "identity": "Desconocida",
                    "confidence": f"{conf*100:.1f}",
                    "is_manual": False
                })
            
            # Update cache!
            faces_cache[filepath] = new_faces
            with open(FACES_CACHE_FILE, 'wb') as f:
                pickle.dump(faces_cache, f)
            
            return jsonify({"faces": new_faces})
        else:
            return jsonify({"faces": []})
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def api_correct_bulk():
    data = request.json
    paths = data.get('paths', [])
    new_identity = data.get('new_identity', '')
    
    if not paths or not new_identity:
        return jsonify({"success": False, "error": "Faltan datos"})
        
    clear_gallery_cache()
    overrides = load_overrides()
    
    # Resolve category
    new_cat = 'Conocidos'
    if new_identity.startswith('F. ') or new_identity.startswith('F_'):
        new_cat = 'Familia'
    elif new_identity.startswith('P. ') or new_identity.startswith('P_'):
        new_cat = 'Profesores'
    elif new_identity.startswith('M. ') or new_identity.startswith('M_'):
        new_cat = 'Mascotas'
    elif new_identity == 'YO':
        new_cat = 'YO'
        
    dest_dir = RESULTADOS_DIR / new_cat / new_identity
    if new_identity != 'Ignorar' and not dest_dir.exists():
        dest_dir.mkdir(parents=True, exist_ok=True)
                
    success_count = 0
    for file_path in paths:
        try:
            file_key = get_file_key(file_path)
            
            if file_key not in overrides:
                overrides[file_key] = []
                
            idx_found = False
            for ov in overrides[file_key]:
                if ov.get('face_idx') == 0:
                    ov['identity'] = new_identity
                    ov['is_manual'] = True
                    idx_found = True
                    break
            
            if not idx_found:
                overrides[file_key].append({
                    "face_idx": 0,
                    "identity": new_identity,
                    "is_manual": True
                })
                
            if new_identity != 'Ignorar' and new_identity != 'Desconocido' and not new_identity.startswith('IA '):
                src_path = Path(file_path)
                if src_path.exists():
                    dest_file = dest_dir / src_path.name
                    if not dest_file.exists():
                        shutil.copy2(src_path, dest_file)
            
            success_count += 1
        except Exception as e:
            print(f"Error bulk correcting {file_path}: {e}")
            
    save_overrides(overrides)
    
    return jsonify({"success": True, "count": success_count})


def api_clear_confidence_cache():
    from app.globals import CONFIDENCE_CACHE_FILE
    import app.globals as g
    
    with g.cache_lock:
        g._CONFIDENCE_CACHE = {}
        
    if CONFIDENCE_CACHE_FILE.exists():
        try:
            CONFIDENCE_CACHE_FILE.unlink()
        except:
            pass
            
    return jsonify({"success": True})


def api_scan_video():
    from app.globals import detector, recognizer, known_faces
    from app.utils.faces import get_cosine_similarity
    
    data = request.json
    filepath = data.get('path')
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
        
    path_obj = Path(filepath)
    if path_obj.suffix.lower() not in [".mp4", ".mov", ".avi"]:
        return jsonify({"error": "Not a video"}), 400
        
    try:
        cap = cv2.VideoCapture(str(filepath))
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0: fps = 30
        
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps
        
        results = {}
        
        local_detector = detector
        local_recognizer = recognizer
        
        if local_detector is None or local_recognizer is None:
            from app.globals import APP_DIR
            local_detector = cv2.FaceDetectorYN.create(
                str(APP_DIR / "models" / "face_detection_yunet.onnx"), 
                "", 
                (320, 320),
                0.70,
                0.3,
                5000
            )
            local_recognizer = cv2.FaceRecognizerSF.create(
                str(APP_DIR / "models" / "face_recognition_sface.onnx"), 
                ""
            )
            
        for sec in range(0, int(duration) + 1):
            target_frame = int(sec * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue
                
            h, w, _ = frame.shape
            local_detector.setInputSize((w, h))
            _, faces = local_detector.detect(frame)
            
            if faces is not None:
                for f in faces:
                    aligned = local_recognizer.alignCrop(frame, f)
                    feature = local_recognizer.feature(aligned)
                    if feature is None: continue
                    
                    best_score = 0
                    best_match = None
                    for db_id, data_dict in known_faces.items():
                        centroid = data_dict.get('centroid')
                        if centroid is not None:
                            score = get_cosine_similarity(feature[0], centroid)
                            if score > best_score:
                                best_score = score
                                best_match = db_id
                                
                    if best_match and best_score > 0.60:
                        if best_match not in results:
                            results[best_match] = []
                        results[best_match].append(sec)
                        
        cap.release()
        
        final_results = []
        for ident, secs in results.items():
            if ident.startswith("Falso_Positivo") or ident.startswith("Ignorar_Irrelevante"):
                continue
            final_results.append({
                "identity": ident,
                "seconds": sorted(list(set(secs)))
            })
            
        return jsonify({"success": True, "detections": final_results})
        
    except Exception as e:
        print("Video Scan Error:", e)
        return jsonify({"error": str(e)}), 500



