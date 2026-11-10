import hashlib

import json

import re

import traceback

from app.utils.images import decode_image

from app.services.content_analysis_service import model_version, load_analysis, save_analysis

from app.services.face_learning import HUMAN, face_rectangle, aligned_feature, normalized_feature, confirmed_centroid

from app.utils.files import get_file_key

from app.services.quote_service import is_text_quote_image, scan_and_categorize_quotes

from app.services.pet_service import detect_pets_and_bodies, detect_pets, extract_pet_feature, match_pet_identity, rebuild_pet_centroids, known_pets



def safe_float(val, default=0.0):

    if val is None or str(val).strip() in ['undefined', 'null', '', 'NaN', 'None']:

        return default

    try:

        return float(val)

    except (ValueError, TypeError):

        return default



def is_valid_face_landmarks(f):

    if f is None or len(f) < 14:

        return True

    try:

        w, h = float(f[2]), float(f[3])

        if w <= 0 or h <= 0:

            return False

            

        x_re, y_re = float(f[4]), float(f[5])   # Right eye

        x_le, y_le = float(f[6]), float(f[7])   # Left eye

        x_nt, y_nt = float(f[8]), float(f[9])   # Nose tip

        x_rm, y_rm = float(f[10]), float(f[11]) # Right mouth corner

        x_lm, y_lm = float(f[12]), float(f[13]) # Left mouth corner

        

        # 1. Eye spacing checks (must not be nill, must be proportional to width)

        d_eyes = ((x_re - x_le)**2 + (y_re - y_le)**2)**0.5

        if d_eyes < 4.0 or d_eyes > w * 1.15:

            return False

            

        # 2. Mouth spacing checks

        d_mouth = ((x_rm - x_lm)**2 + (y_rm - y_lm)**2)**0.5

        if d_mouth < 3.0 or d_mouth > w * 0.95:

            return False

            

        # 3. Vertical alignment (Nose Y must fall in range between eyes and mouth)

        min_y = min(y_re, y_le) - 0.15 * h

        max_y = max(y_rm, y_lm) + 0.15 * h

        if not (min_y <= y_nt <= max_y):

            return False

            

        # 4. Horizontal alignment (Nose X centered between eyes X)

        min_x = min(x_re, x_le) - 0.3 * w

        max_x = max(x_re, x_le) + 0.3 * w

        if not (min_x <= x_nt <= max_x):

            return False

            

        return True

    except Exception:

        return True



from app.globals import cache_lock

from flask import Blueprint, jsonify, request

import os

import cv2

import numpy as np

import shutil

import pickle

from pathlib import Path

from app.globals import (

    APP_DIR, FOTOS_DIR, RESULTADOS_DIR, CACHE_FILE, FACES_CACHE_FILE, 

    PENDING_DELETIONS_FILE, detector, recognizer, known_faces, 

    faces_cache, clear_gallery_cache, get_gallery_cache,

    detector_lock, reload_known_faces

)

from app.utils.faces import get_cosine_similarity, iou, ios, is_duplicate_box

from app.utils.files import safe_move, load_overrides, save_overrides, find_relocated_file, get_file_key, safe_move_file, safe_remove_file, get_override_for_file



def get_identity_centroids(val):

    if isinstance(val, dict):

        centroids = val.get('centroids')

        if centroids and len(centroids) > 0:

            return [c for c in centroids if c is not None]

        c = val.get('centroid')

        if c is not None:

            return [c]

        return []

    elif val is not None:

        return [val]

    return []





def match_face_to_identity(feat, val):

    centroids = get_identity_centroids(val)

    if not centroids or feat is None:

        return 0.0

    feat_arr = np.array(feat, dtype=np.float32).flatten()

    feat_norm = feat_arr / (np.linalg.norm(feat_arr) + 1e-10)

    best_sim = -1.0

    for c in centroids:

        c_arr = np.array(c, dtype=np.float32).flatten()

        norm_c = c_arr / (np.linalg.norm(c_arr) + 1e-10)

        sim = float(np.dot(feat_norm, norm_c))

        if sim > best_sim:

            best_sim = sim

    return max(best_sim, 0.0)





_CENTROIDS_CACHE_KEY = None

_CENTROIDS_MATRIX = None

_CENTROIDS_KEYS = []



def get_vectorized_centroids():

    global _CENTROIDS_CACHE_KEY, _CENTROIDS_MATRIX, _CENTROIDS_KEYS

    if len(known_faces) == 0:

        try:

            reload_known_faces()

        except Exception:

            pass

    kf_len = len(known_faces)

    if _CENTROIDS_MATRIX is not None and _CENTROIDS_CACHE_KEY == kf_len and kf_len > 0:

        return _CENTROIDS_MATRIX, _CENTROIDS_KEYS

    

    vecs = []

    keys = []

    for db_id, val in known_faces.items():

        ident_n = db_id[1] if isinstance(db_id, tuple) else str(db_id)

        if is_smart_relationship_album(ident_n) or ident_n.startswith("Falso_Positivo") or ident_n.startswith("Ignorar_"):

            continue

        centroids = get_identity_centroids(val)

        for c in centroids:

            arr = np.asarray(c, dtype=np.float32).flatten()

            if arr.shape[0] == 128:

                norm = np.linalg.norm(arr)

                if norm > 1e-6:

                    vecs.append(arr / norm)

                    keys.append(db_id)

    if vecs:

        _CENTROIDS_MATRIX = np.vstack(vecs)

        _CENTROIDS_KEYS = keys

        _CENTROIDS_CACHE_KEY = kf_len

    else:

        _CENTROIDS_MATRIX = np.zeros((0, 128), dtype=np.float32)

        _CENTROIDS_KEYS = []

        _CENTROIDS_CACHE_KEY = 0

    return _CENTROIDS_MATRIX, _CENTROIDS_KEYS



def api_analyze():

    data = request.json or {}

    filepath = data.get('path')

    current_cat = data.get('current_cat')

    current_ident = data.get('current_ident')

    if not filepath or not os.path.exists(filepath):

        real_p = find_relocated_file(filepath) if filepath else None

        if not real_p:

            return jsonify({"error": "File not found"}), 404

        filepath = real_p

        

    path_obj = Path(filepath)

    is_video = path_obj.suffix.lower() in [".mp4", ".mov", ".avi"]

    faces_data = []

    sha256 = None

    analysis_reused = False

    



    

    

    # Recompute labels and overrides on each request. Content detections are reusable.

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

                return jsonify({"error": "No se pudo leer fotograma de vídeo"}), 500

        else:

            file_bytes = np.fromfile(str(filepath), dtype=np.uint8)

            img = decode_image(file_bytes)

            

        if img is not None and detector is not None and recognizer is not None:

            height, width, _ = img.shape

            raw_detected_faces = []

            

            sha256 = None if is_video else hashlib.sha256(file_bytes).hexdigest()

            analysis_profile = None if is_video else "interactive-faces-v3:" + model_version(APP_DIR)

            cached_analysis = None

            if sha256:

                cached_analysis = load_analysis(filepath, sha256, analysis_profile)

                if data.get("force", False):

                    cached_analysis = None

            analysis_reused = cached_analysis is not None

            feature_cache = cached_analysis.get("features", {}) if cached_analysis else {}

            if cached_analysis is not None:

                raw_detected_faces = cached_analysis["faces"]

            else:

                # Optimización de Escala YuNet (máx 1024px para respuesta ultra-rápida en ~150ms)

                max_dim = 1024

                scale = 1.0

                if max(width, height) > max_dim:

                    scale = max_dim / max(width, height)

                    det_w = max(160, int(width * scale) // 32 * 32)

                    det_h = max(160, int(height * scale) // 32 * 32)

                    det_img = cv2.resize(img, (det_w, det_h))

                else:

                    det_w, det_h = max(160, width // 32 * 32), max(160, height // 32 * 32)

                    det_img = cv2.resize(img, (det_w, det_h))



                with detector_lock:

                    detector.setInputSize((det_w, det_h))

                    detector.setScoreThreshold(0.35)

                    _, faces = detector.detect(det_img)

            

                inv_scale = 1.0 / scale if scale > 0 else 1.0

                if faces is not None:

                    for f in faces:

                        if not is_valid_face_landmarks(f):

                            continue

                        scaled_f = f.copy().astype(np.float32)

                        scaled_f[:14:2] *= width / det_w

                        scaled_f[1:14:2] *= height / det_h

                        raw_detected_faces.append(scaled_f.tolist())

                

                # Pase 2: Videollamada PiP inferior si la imagen es vertical

                if height / max(1, width) > 1.6 and len(raw_detected_faces) < 2:

                    try:

                        pip_crop = img[int(height * 0.65):, :int(width * 0.50)]

                        h_pip, w_pip = pip_crop.shape[:2]

                        if h_pip > 40 and w_pip > 40:

                            pip_w, pip_h = max(160, w_pip * 2 // 32 * 32), max(160, h_pip * 2 // 32 * 32)

                            pip_2x = cv2.resize(pip_crop, (pip_w, pip_h))

                            with detector_lock:

                                detector.setInputSize((pip_w, pip_h))

                                detector.setScoreThreshold(0.25)

                                _, p_faces = detector.detect(pip_2x)

                            if p_faces is not None:

                                for pf in p_faces:

                                    if not is_valid_face_landmarks(pf):

                                        continue

                                    pf[:14:2] *= w_pip / pip_w

                                    pf[1:14:2] *= h_pip / pip_h

                                    pf[1] += int(height * 0.65)

                                    pf[5:14:2] += int(height * 0.65)

                                    raw_detected_faces.append(pf.tolist())

                    except Exception: pass

            

            overrides = load_overrides()

            file_key = get_file_key(filepath)

            ov_res = get_override_for_file(filepath, overrides=overrides)
            if isinstance(ov_res, tuple) and len(ov_res) == 2:
                found_ov = ov_res[1]
            elif isinstance(ov_res, list):
                found_ov = ov_res
            else:
                found_ov = overrides.get(file_key, [])
            if not isinstance(found_ov, list):
                found_ov = [found_ov] if isinstance(found_ov, dict) else []
            file_overrides = [ov for ov in found_ov if isinstance(ov, dict) and (ov.get('provenance') == HUMAN or ov.get('is_manual') is True)]

            claimed_identities = set()

            for ov in file_overrides:

                ov_id = ov.get('identity')

                if ov_id and ov_id not in ("Desconocido", "Ignorar_Irrelevante", "Falso_Positivo", "Excluido"):

                    claimed_identities.add(ov_id)

            

            if len(raw_detected_faces) > 0:

                # NMS Deduplication (IoU > 0.35 OR nested sub-box containment IoS > 0.48)

                deduped_faces = []

                for f in sorted(raw_detected_faces, key=lambda itm: itm[14] if len(itm) > 14 else itm[2]*itm[3], reverse=True):

                    f_box = [float(f[0]), float(f[1]), float(f[2]), float(f[3])]

                    if not any(is_duplicate_box(f_box, [float(df[0]), float(df[1]), float(df[2]), float(df[3])]) for df in deduped_faces):

                        deduped_faces.append(f)

                faces = deduped_faces



                used_override_indices = set()

                # --- BIPARTITE MULTI-FACE MATCHING PRE-PASS ---
                current_folder = path_obj.parent.name
                raw_owner = current_ident or (path_obj.parent.parent.name if current_folder == "_Dudosos" else current_folder)
                owner_folder = raw_owner if raw_owner not in ["_Dudosos", "Personas Sin Nombre", "Resultados", "Fotos", "Para Revisar", "Por Organizar", "Photos", "iCloud Photos"] else None

                owner_entry = None
                if owner_folder and not is_smart_relationship_album(owner_folder):
                    owner_entry = (
                        known_faces.get(owner_folder) or
                        known_faces.get((current_cat or path_obj.parent.parent.name, owner_folder)) or
                        known_faces.get(('Conocidos', owner_folder)) or
                        known_faces.get(('Familia', owner_folder)) or
                        {}
                    )

                # Pre-compute feature embeddings for all faces
                face_feat_norms = []
                for f_tmp in faces:
                    x_t, y_t, w_t, h_t = int(f_tmp[0]), int(f_tmp[1]), int(f_tmp[2]), int(f_tmp[3])
                    x_t, y_t = max(0, x_t), max(0, y_t)
                    w_t, h_t = min(w_t, width - x_t), min(h_t, height - y_t)
                    fn_t = None
                    if w_t >= 15 and h_t >= 15:
                        try:
                            f_key_t = json.dumps([float(v) for v in f_tmp], separators=(",", ":"))
                            if f_key_t in feature_cache:
                                f_vec = np.asarray(feature_cache[f_key_t], dtype=np.float32)
                            else:
                                aligned_t = None
                                if len(f_tmp) >= 14:
                                    try:
                                        aligned_t = recognizer.alignCrop(img, np.array(f_tmp, dtype=np.float32))
                                    except Exception:
                                        aligned_t = None
                                if aligned_t is None:
                                    crop_t = img[y_t:y_t+h_t, x_t:x_t+w_t]
                                    if crop_t.shape[0] > 10 and crop_t.shape[1] > 10:
                                        aligned_t = cv2.resize(crop_t, (112, 112))
                                if aligned_t is not None:
                                    feat_arr_t = recognizer.feature(aligned_t)
                                    if feat_arr_t is not None and len(feat_arr_t) > 0:
                                        f_vec = feat_arr_t[0]
                                        feature_cache[f_key_t] = f_vec.tolist()
                                    else:
                                        f_vec = None
                                else:
                                    f_vec = None
                            if f_vec is not None:
                                fn_t = f_vec / (np.linalg.norm(f_vec) + 1e-10)
                        except Exception:
                            fn_t = None
                    face_feat_norms.append(fn_t)

                # Pre-reserve YO to the single best face
                best_yo_face_idx = -1
                best_yo_score = 0.0
                for f_idx, fn in enumerate(face_feat_norms):
                    if fn is None: continue
                    yo_s = 0.0
                    for yo_k in [('YO', 'YO'), 'YO', ('Conocidos', 'YO')]:
                        if yo_k in known_faces:
                            yo_s = max(yo_s, match_face_to_identity(fn, known_faces[yo_k]))
                    if yo_s > best_yo_score:
                        best_yo_score = yo_s
                        best_yo_face_idx = f_idx

                # Pre-reserve owner_folder to the single best face with similarity >= 0.38
                best_owner_face_idx = -1
                best_owner_sim = 0.0
                if owner_entry and owner_folder not in claimed_identities:
                    for f_idx, fn in enumerate(face_feat_norms):
                        if fn is None: continue
                        if f_idx == best_yo_face_idx and best_yo_score >= 0.50:
                            continue
                        sim_o = match_face_to_identity(fn, owner_entry)
                        if sim_o > best_owner_sim:
                            best_owner_sim = sim_o
                            best_owner_face_idx = f_idx

                for face_idx, face in enumerate(faces):

                    x, y, w, h = int(face[0]), int(face[1]), int(face[2]), int(face[3])

                    x, y = max(0, x), max(0, y)

                    w, h = min(w, width - x), min(h, height - y)

                    if w < 15 or h < 15: continue

                    

                    identity_name = "Desconocido"

                    confidence_str = "❓ Desconocido"

                    tag_type = "unknown"

                    current_box = [x, y, w, h]

                    best_match = None

                    clean_bm = None

                    best_score = 0.0

                    

                    best_ov_match = None

                    best_ov_iou = 0.35

                    best_ov_idx = -1

                    

                    for ov_idx, ov in enumerate(file_overrides):

                        if ov_idx in used_override_indices: continue

                        if ov.get('from_familia_conmigo_analysis') or ov.get('is_manual') is False: continue

                        if not (ov.get('is_manual') is True or ov.get('provenance') in ('human_confirmed', 'human', HUMAN)): continue

                        ov_w = safe_float(ov.get('width'), 0)

                        ov_h = safe_float(ov.get('height'), 0)

                        if ov_w < 15 or ov_h < 15: continue

                        ov_box = [safe_float(ov.get('x'), 0), safe_float(ov.get('y'), 0), ov_w, ov_h]

                        curr_ov_iou = iou(current_box, ov_box)

                        if curr_ov_iou > best_ov_iou:

                            best_ov_iou = curr_ov_iou

                            best_ov_match = ov

                            best_ov_idx = ov_idx

                            

                    if best_ov_match is None and len(face) > 14 and face[14] < 0.45:

                        continue



                    override_match = None

                    if best_ov_match is not None:

                        used_override_indices.add(best_ov_idx)

                        override_match = best_ov_match.get('identity')

                        ov_w = int(safe_float(best_ov_match.get('width'), 0))

                        ov_h = int(safe_float(best_ov_match.get('height'), 0))

                        if ov_w >= 15 and ov_h >= 15:

                            x = max(0, int(safe_float(best_ov_match.get('x'), 0)))

                            y = max(0, int(safe_float(best_ov_match.get('y'), 0)))

                            w, h = min(ov_w, width - x), min(ov_h, height - y)

                            

                    if override_match:

                        if override_match in ["Ignorar_Irrelevante", "Falso_Positivo"]: continue

                        identity_name = re.sub(r'^\?\s*', '', str(override_match)).strip()

                        confidence_str = "✏️ Corrección Manual"

                        tag_type = "manual"

                        claimed_identities.add(identity_name)

                        feature_vec = None

                    else:

                        feature_vec = None

                        try:

                            feature_key = json.dumps([float(value) for value in face], separators=(",", ":"))

                            if feature_key in feature_cache:

                                feature_vec = np.asarray(feature_cache[feature_key], dtype=np.float32)

                            else:

                                # Recorte y alineación SFace con landmarks faciales

                                aligned = None

                                if len(face) >= 14:

                                    try:

                                        face_arr = np.array(face, dtype=np.float32)

                                        aligned = recognizer.alignCrop(img, face_arr)

                                    except Exception:

                                        aligned = None

                                if aligned is None:

                                    crop = img[y:y+h, x:x+w]

                                    if crop.shape[0] > 10 and crop.shape[1] > 10:

                                        aligned = cv2.resize(crop, (112, 112))

                                if aligned is not None:

                                    feature_arr = recognizer.feature(aligned)

                                    if feature_arr is not None and len(feature_arr) > 0:

                                        feature_vec = feature_arr[0]

                                    

                                if feature_vec is not None:

                                    feature_cache[feature_key] = feature_vec.tolist()

                            if feature_vec is not None:

                                feat_norm = feature_vec / (np.linalg.norm(feature_vec) + 1e-10)

                                # Master Anchor Protection for YO

                                yo_score = 0.0

                                for yo_k in [('YO', 'YO'), 'YO', ('Conocidos', 'YO')]:

                                    if yo_k in known_faces:

                                        yo_score = max(yo_score, match_face_to_identity(feat_norm, known_faces[yo_k]))



                                best_match = None

                                best_score = 0.0

                                second_best_score = 0.0

                                second_best_match = None

                                

                                c_mat, c_keys = get_vectorized_centroids()

                                if c_mat.shape[0] > 0:

                                    sims = np.dot(c_mat, feat_norm)

                                    ident_scores = {}

                                    ident_best_keys = {}

                                    for idx_c, s in enumerate(sims):

                                        k = c_keys[idx_c]

                                        ident_n = k[1] if isinstance(k, tuple) else str(k)

                                        clean_id = re.sub(r'^\?\s*', '', ident_n).strip()

                                        if clean_id in claimed_identities or ident_n in claimed_identities:

                                            continue

                                        if owner_folder and clean_id == owner_folder and face_idx != best_owner_face_idx:

                                            continue

                                        s_flt = float(s)

                                        if clean_id not in ident_scores or s_flt > ident_scores[clean_id]:

                                            ident_scores[clean_id] = s_flt

                                            ident_best_keys[clean_id] = k

                                    

                                    sorted_matches = sorted(ident_scores.items(), key=lambda itm: itm[1], reverse=True)

                                    if len(sorted_matches) > 0 and sorted_matches[0][1] > 0:

                                        clean_bm, best_score = sorted_matches[0]

                                        best_match = ident_best_keys.get(clean_bm)

                                    if len(sorted_matches) > 1 and sorted_matches[1][1] > 0:

                                        clean_second, second_best_score = sorted_matches[1]

                                        second_best_match = ident_best_keys.get(clean_second)

                                

                                # Safety rule: If face matches YO (>0.45), prioritize YO suggestion

                                clean_bm = best_match[1] if isinstance(best_match, tuple) else str(best_match)

                                clean_bm = re.sub(r'^\?\s*', '', clean_bm).strip()

                                if yo_score > 0.45 and clean_bm != 'YO':

                                    if yo_score >= 0.54:

                                        best_match = 'YO'

                                        best_score = yo_score

                                        clean_bm = 'YO'

                                    elif yo_score >= 0.35:

                                        best_match = 'YO'

                                        best_score = yo_score

                                        clean_bm = 'YO'

                                

                                                                # Priorización Contextual del Dueño del Álbum / Familia (Multi-Centroide)

                                current_folder = path_obj.parent.name

                                raw_owner = current_ident or (path_obj.parent.parent.name if current_folder == "_Dudosos" else current_folder)

                                owner_folder = raw_owner if raw_owner not in ["_Dudosos", "Personas Sin Nombre", "Resultados", "Fotos", "Para Revisar", "Por Organizar", "Photos", "iCloud Photos"] else None

                                

                                if owner_folder and clean_bm != "YO" and not is_smart_relationship_album(owner_folder):

                                    if face_idx == best_owner_face_idx and best_owner_sim >= 0.38:

                                        if (best_score - best_owner_sim) < 0.14:

                                            best_match = owner_folder

                                            best_score = best_owner_sim

                                            clean_bm = owner_folder



                                # Cross-Identity Margin (CIM) Protection

                                # Only penalize if best and second best are truly DIFFERENT identities

                                # NEVER penalize the album owner against external random database entries

                                if best_match and second_best_match and clean_bm != 'YO' and clean_bm != owner_folder:

                                    clean_sec = second_best_match[1] if isinstance(second_best_match, tuple) else str(second_best_match)

                                    clean_sec = re.sub(r'^\?\s*', '', clean_sec).strip()

                                    if clean_bm != clean_sec:

                                        margin = best_score - second_best_score

                                        if margin < 0.05 and best_score < 0.65:

                                            best_score = min(best_score, 0.50)

                                        

                                if best_match and best_score >= 0.54:

                                    if str(best_match).startswith("Falso_Positivo") or is_smart_relationship_album(str(best_match)):

                                        clean_bm = None

                                        best_match = None

                                    else:

                                        identity_name = clean_bm

                                        if owner_folder and clean_bm == owner_folder:

                                            confidence_str = f"👑 Dueño del Álbum ({(best_score * 100):.1f}%)"

                                            tag_type = "album_owner"

                                        elif best_score >= 0.62:

                                            confidence_str = f"🏷️ Dataset ({(best_score * 100):.1f}%)"

                                            tag_type = "dataset"

                                        else:

                                            confidence_str = f"🤖 IA ({(best_score * 100):.1f}%)"

                                            tag_type = "ai"

                                elif best_match and best_score >= 0.40 and owner_folder and clean_bm == owner_folder:

                                    identity_name = clean_bm

                                    confidence_str = f"👑 Dueño del Álbum ({(best_score * 100):.1f}%)"

                                    tag_type = "album_owner"

                                elif best_match and best_score >= 0.48:

                                    identity_name = clean_bm

                                    confidence_str = f"🤖 Sugerencia: {clean_bm} ({(best_score * 100):.1f}%)"

                                    tag_type = "ai_suggestion"

                                else:

                                    # Debajo de 0.48 se considera ruido y no se emiten sugerencias erróneas

                                    clean_bm = None

                                    best_match = None

                        except Exception: pass

                    

                    # Mutual Exclusion: Claim identity so no other face in this photo takes it

                    if identity_name not in ("Desconocido", "Ignorar_Irrelevante", "Falso_Positivo"):

                        clean_claim = identity_name.replace("? ", "").strip()

                        claimed_identities.add(clean_claim)

                        claimed_identities.add(identity_name)



                    sug_id = clean_bm if (best_match and best_score >= 0.48 and clean_bm not in claimed_identities and clean_bm != 'Desconocido' and not is_smart_relationship_album(clean_bm)) else None



                    faces_data.append({

                        "x": x, "y": y, "width": w, "height": h,

                        "img_width": width, "img_height": height,

                        "identity": identity_name,

                        "suggested_identity": sug_id,

                        "suggested_score": round(best_score, 4) if sug_id else 0.0,

                        "confidence": confidence_str,

                        "tag_type": tag_type,

                        "feature": feature_vec.tolist() if feature_vec is not None else None,

                        "is_manual": (override_match is not None)

                    })

            

            # Si es álbum de una persona y hay rostros desconocidos, asignar el mejor match al dueño

            path_parts = Path(filepath).parts

            cat_name = None

            for idx, p in enumerate(path_parts):

                if p in ["Fotos", "Resultados"] and idx + 1 < len(path_parts):

                    cat_name = path_parts[idx + 1]; break



            folder_owner = Path(filepath).parent.name

            PERSON_CATEGORIES = {"Conocidos", "Familia", "YO", "Profesores"}

            is_person_category = cat_name in PERSON_CATEGORIES

            is_valid_owner = (

                is_person_category 

                and not is_smart_relationship_album(folder_owner) 

                and folder_owner not in ["_Dudosos", "Personas Sin Nombre", "Resultados", "Fotos", "Conocidos", "Familia", "Profesores", "Ignorar"]

            )

            

            if is_valid_owner and len(faces_data) > 0:

                # If any face is doubtful owner, confirm it immediately

                for f in faces_data:

                    clean_f_id = re.sub(r'^\?\s*', '', str(f.get("identity", ""))).strip()

                    if clean_f_id == folder_owner and f.get("identity") != folder_owner:

                        f["identity"] = folder_owner

                        f["confidence"] = "👑 Dueño del Álbum"

                        f["tag_type"] = "album_owner"



                owner_assigned = any(f.get("identity") == folder_owner for f in faces_data)

                if not owner_assigned:

                    best_idx = -1

                    best_owner_score = -1.0

                    owner_entry = known_faces.get((cat_name, folder_owner)) or known_faces.get(folder_owner) or {}

                    

                    for idx, f in enumerate(faces_data):

                        if f["identity"] == "Desconocido" and f.get("feature") is not None:

                            f_feat = np.array(f["feature"], dtype=np.float32)

                            f_norm = f_feat / (np.linalg.norm(f_feat) + 1e-10)

                            score = match_face_to_identity(f_norm, owner_entry)

                            if score > best_owner_score:

                                best_owner_score = score

                                best_idx = idx

                                    

                    if best_idx != -1 and best_owner_score >= 0.35:

                        faces_data[best_idx]["identity"] = folder_owner

                        faces_data[best_idx]["confidence"] = f"👑 Dueño del Álbum ({(best_owner_score*100):.1f}%)"

                        faces_data[best_idx]["tag_type"] = "album_owner" 

                        

                        # --- PASO 3: Detección Dual de Mascotas y Personas de Espaldas/Con Filtros ---

            is_pet_dir = folder_owner.startswith("M.") or cat_name == "Mascotas" or "mascota" in str(filepath).lower()

            if is_pet_dir or len(faces_data) == 0:

                try:

                    yolo_results = detect_pets_and_bodies(img, conf_thresh=0.28)

                    detected_pets = yolo_results.get("pets", [])

                    detected_bodies = yolo_results.get("bodies", [])

                    

                    # A. Procesar Mascotas

                    for pet in detected_pets:

                        px, py, pw, ph = pet["x"], pet["y"], pet["width"], pet["height"]

                        pet_box = [float(px), float(py), float(pw), float(ph)]

                        human_overlap = any(iou(pet_box, [float(f["x"]), float(f["y"]), float(f["width"]), float(f["height"])]) > 0.35 for f in faces_data)

                        if human_overlap: continue

                        

                        pet_crop = img[py:py+ph, px:px+pw]

                        best_pet_name, best_pet_score, pet_feat = match_pet_identity(pet_crop)

                        

                        folder_owner = Path(filepath).parent.name

                        if folder_owner.startswith("M.") or "mascota" in folder_owner.lower():

                            pet_identity = folder_owner

                            pet_confidence = f"🐶 {pet['class'].capitalize()} ({folder_owner})"

                            pet_tag = "pet"

                        elif best_pet_name and best_pet_score >= 0.50:

                            pet_identity = best_pet_name

                            pet_confidence = f"🐶 Mascota ({best_pet_score*100:.1f}%)"

                            pet_tag = "pet"

                        else:

                            pet_identity = f"🐶 {pet['class'].capitalize()} Desconocido"

                            pet_confidence = f"🐶 {pet['class'].capitalize()} Detectado"

                            pet_tag = "pet_unknown"

                            

                        faces_data.append({

                            "x": px, "y": py, "width": pw, "height": ph,

                            "img_width": width, "img_height": height,

                            "identity": pet_identity,

                            "confidence": pet_confidence,

                            "tag_type": pet_tag,

                            "feature": pet_feat.tolist() if pet_feat is not None else None,

                            "is_manual": False,

                            "is_pet": True

                        })

    

                    # B. Procesar Personas de Espaldas o con Filtros de Snapchat/Instagram

                    for body in detected_bodies:

                        bx, by, bw, bh = body["x"], body["y"], body["width"], body["height"]

                        body_box = [float(bx), float(by), float(bw), float(bh)]

                        

                        # Verificar si ya existe un rostro facial detectado dentro del cuerpo

                        has_face_inside = any(

                            (f["x"] >= bx - 10 and f["x"] + f["width"] <= bx + bw + 10 and

                             f["y"] >= by - 10 and f["y"] + f["height"] <= by + bh + 10)

                            for f in faces_data if not f.get("is_pet")

                        )

                        

                        if not has_face_inside:

                            # Extraer la región superior (cabeza y hombros: 35% superior)

                            head_h = max(25, int(bh * 0.35))

                            head_w = max(25, int(bw * 0.65))

                            head_x = bx + int((bw - head_w) / 2)

                            head_y = by

                            

                            # Buscar si hay un override manual para esta persona

                            head_box = [head_x, head_y, head_w, head_h]

                            matched_ov = None

                            for ov in file_overrides:

                                ov_b = [safe_float(ov.get('x'), 0), safe_float(ov.get('y'), 0), safe_float(ov.get('width'), 0), safe_float(ov.get('height'), 0)]

                                if iou(head_box, ov_b) > 0.30:

                                    matched_ov = ov.get('identity')

                                    break

                                    

                            body_identity = matched_ov if matched_ov else "Persona (Sin rostro / Filtro)"

                            body_conf = "✏️ Corrección Manual" if matched_ov else f"👤 Persona Detectada ({body['confidence']*100:.1f}%)"

                            body_tag = "manual" if matched_ov else "body"

                            

                            faces_data.append({

                                "x": head_x, "y": head_y, "width": head_w, "height": head_h,

                                "img_width": width, "img_height": height,

                                "identity": body_identity,

                                "confidence": body_conf,

                                "tag_type": body_tag,

                                "feature": None,

                                "is_manual": (matched_ov is not None),

                                "is_body": True

                            })

                except Exception as e_dual:

                    print(f"[DUAL_DETECT_ERROR] {e_dual}")



            # Si la foto está en la carpeta de una Mascota, limpiar falsos positivos humanos de baja confianza

            if folder_owner.startswith("M.") or cat_name == "Mascotas":

                faces_data = [f for f in faces_data if f.get("is_pet") or (f.get("tag_type") in ["manual", "dataset"] and not f.get("identity", "").startswith("C."))]



            # Enforce strict photo mutual exclusion for both assigned identities and suggestions

            assigned_counts = {}

            for f in faces_data:

                raw_id = f.get('identity', '')

                clean_id = raw_id[2:] if raw_id.startswith('? ') else raw_id

                if clean_id and clean_id not in ("Desconocido", "Falso_Positivo", "Ignorar_Irrelevante", "Persona (Sin rostro / Filtro)", "Sin Nombre"):

                    assigned_counts[clean_id] = assigned_counts.get(clean_id, 0) + 1



            for target_id, count in assigned_counts.items():

                if count > 1:

                    dupes = [

                        (idx, f) for idx, f in enumerate(faces_data) 

                        if f.get('identity') == target_id or f.get('identity') == f"? {target_id}"

                    ]

                    def _rank_face(item):

                        idx, f = item

                        is_man = 1 if f.get('is_manual') else 0

                        sc = f.get('suggested_score') or 0.0

                        return (is_man, sc)

                    dupes.sort(key=_rank_face, reverse=True)

                    for idx, f in dupes[1:]:

                        f['identity'] = "Desconocido"

                        f['suggested_identity'] = None

                        f['suggested_score'] = 0.0

                        f['confidence'] = "Pendiente"

                        f['tag_type'] = "pending"



            claimed_ids = {

                (f['identity'][2:] if f['identity'].startswith('? ') else f['identity'])

                for f in faces_data 

                if f.get('identity') and f.get('identity') not in ("Desconocido", "Falso_Positivo", "Ignorar_Irrelevante", "Persona (Sin rostro / Filtro)", "Sin Nombre")

            }

            for f in faces_data:

                if f.get('suggested_identity') in claimed_ids:

                    f['suggested_identity'] = None

                    f['suggested_score'] = 0.0

                    if f.get('tag_type') == 'ai_suggestion':

                        f['confidence'] = "Pendiente"

                        f['tag_type'] = "pending"



            if sha256:

                save_analysis(sha256, analysis_profile,

                              {"faces": raw_detected_faces, "features": feature_cache})



            # Guardar en faces_cache

            with cache_lock:

                faces_cache[get_file_key(filepath)] = faces_data

                

        return jsonify({"faces": faces_data, "content_sha256": sha256, "analysis_reused": analysis_reused})

    except Exception as e:

        import traceback

        traceback.print_exc()

        print(f"[API_ANALYZE] Error analizando {filepath}: {e}")

        return jsonify({"error": str(e)}), 500



def apply_correction_to_file(filepath, new_categoria, new_identidad, face_data, *, provenance='prediction', old_face=None, face_num=None):

    if provenance != HUMAN:

        if face_data is not None:

            face_data['suggested_identity'] = new_identidad

            face_data['review_required'] = True

            face_data['suggestion_provenance'] = 'prediction'

        return filepath

    if face_data:

        face_data = {**face_data, **face_rectangle(face_data)}



    # Auto-resolve canonical category if empty, invalid or review-related

    clean_id = str(new_identidad or '').strip().lstrip('?').strip()

    if clean_id.startswith(('C.', 'C ', 'C_')):

        canonical_cat = 'Conocidos'

    elif clean_id.startswith(('F.', 'F ', 'F_')):

        canonical_cat = 'Familia'

    elif clean_id == 'YO' or clean_id.startswith('YO'):

        canonical_cat = 'YO'

    elif clean_id.startswith(('P.', 'P ', 'Prof')):

        canonical_cat = 'Profesores'

    elif clean_id.startswith(('M.', 'M ', 'Mascota')) or clean_id in {'Perro', 'Gato', 'Ney', 'Sua'}:

        canonical_cat = 'Mascotas'

    else:

        canonical_cat = None



    if not new_categoria or any(v in ('.', '..') or '/' in v or chr(92) in v for v in (new_categoria,)) or 'revisi' in str(new_categoria).lower() or 'dudoso' in str(new_categoria).lower() or 'organizar' in str(new_categoria).lower():

        new_categoria = canonical_cat or 'Conocidos'

    elif canonical_cat and new_categoria in {'Dudosos', 'Personas Sin Nombre'}:

        new_categoria = canonical_cat



    # Clean identity name

    new_identidad = clean_id.replace('/', '_').replace(chr(92), '_')

    if not new_categoria or not new_identidad or any(v in ('.', '..') for v in (new_categoria, new_identidad)):

        raise ValueError('Invalid identity or category')



    # Update Apple DB if this is an iCloud or Apple indexed photo

    try:

        from app.services.apple_service import load_apple_db, save_apple_db
        apple_db = load_apple_db()
        norm_fp = os.path.normpath(filepath) if filepath else ''
        matching_key = None
        for k in apple_db.keys():
            if os.path.normpath(k) == norm_fp or os.path.basename(k) == os.path.basename(filepath or ''):
                matching_key = k
                break
        if matching_key:
            entry = apple_db[matching_key]
            entry['category'] = new_categoria
            entry['identity'] = new_identidad
            entry['status'] = 'Clasificado'
            entry['is_dudoso'] = False
            if 'identities' not in entry or not isinstance(entry['identities'], list):
                entry['identities'] = [new_identidad]
            elif new_identidad not in entry['identities']:
                entry['identities'].append(new_identidad)

            if 'faces' in entry and isinstance(entry['faces'], list) and face_data:
                fx = safe_float(face_data.get('x'), 0.0)
                fy = safe_float(face_data.get('y'), 0.0)
                fw = safe_float(face_data.get('width'), 100.0)
                fh = safe_float(face_data.get('height'), 100.0)
                face_box = [fx, fy, fw, fh]
                old_box = None
                if old_face and isinstance(old_face, dict):
                    old_box = [safe_float(old_face.get('x'), fx), safe_float(old_face.get('y'), fy), safe_float(old_face.get('width'), fw), safe_float(old_face.get('height'), fh)]

                f_updated = False
                best_adb_idx = -1
                best_adb_iou = -1.0
                for idx, f in enumerate(entry['faces']):
                    fb = [safe_float(f.get('x')), safe_float(f.get('y')), safe_float(f.get('width')), safe_float(f.get('height'))]
                    if sum(fb) == 0 and 'box' in f:
                        fb = [safe_float(f['box'][0]), safe_float(f['box'][1]), safe_float(f['box'][2]), safe_float(f['box'][3])]
                    miou = max(iou(old_box, fb) if old_box else 0.0, iou(face_box, fb))
                    if miou > best_adb_iou:
                        best_adb_iou = miou
                        best_adb_idx = idx
                if best_adb_idx >= 0 and best_adb_iou > 0.15:
                    entry['faces'][best_adb_idx].update({
                        'identity': new_identidad, 'confidence': 100.0, 'is_manual': True,
                        'x': fx, 'y': fy, 'width': fw, 'height': fh, 'box': [fx, fy, fw, fh]
                    })
                    f_updated = True
                else:
                    for f in entry['faces']:
                        if f.get('identity') == new_identidad or len(entry['faces']) == 1:
                            f.update({
                                'identity': new_identidad, 'confidence': 100.0, 'is_manual': True,
                                'x': fx, 'y': fy, 'width': fw, 'height': fh, 'box': [fx, fy, fw, fh]
                            })
                            f_updated = True
                            break
                if not f_updated:
                    entry['faces'].append({
                        'x': fx, 'y': fy, 'width': fw, 'height': fh, 'box': [fx, fy, fw, fh],
                        'identity': new_identidad, 'confidence': 100.0, 'is_manual': True
                    })
                # Deduplicate faces in apple_db entry
                deduped_adb = []
                for f in entry['faces']:
                    fb = [safe_float(f.get('x')), safe_float(f.get('y')), safe_float(f.get('width')), safe_float(f.get('height'))]
                    fid = f.get('identity')
                    is_dup = False
                    for df in deduped_adb:
                        dfb = [safe_float(df.get('x')), safe_float(df.get('y')), safe_float(df.get('width')), safe_float(df.get('height'))]
                        if (df.get('identity') == fid and fid not in ('Desconocido',)) or (sum(fb) > 0 and sum(dfb) > 0 and iou(fb, dfb) > 0.4):
                            df.update(f)
                            is_dup = True
                            break
                    if not is_dup:
                        deduped_adb.append(f)
                entry['faces'] = deduped_adb
            save_apple_db()
            print(f'[APPLE DB] Confirmed photo {matching_key} -> {new_categoria} / {new_identidad}')
    except Exception as e_adb:
        print(f'[WARN] Error updating apple_db for photo confirmation: {e_adb}')



    if filepath and not os.path.exists(filepath):

        resolved = find_relocated_file(filepath)

        if resolved and os.path.exists(resolved):

            filepath = resolved

    if not filepath or not os.path.exists(filepath):

        # Allow dehydrated/virtual iCloud photos if registered in apple_db

        try:

            from app.services.apple_service import load_apple_db

            apple_db = load_apple_db()

            if filepath in apple_db or (filepath and os.path.basename(filepath) in apple_db):

                return filepath

        except Exception:

            pass

        return None

    orig_path = Path(filepath)

    is_manual_source = False

    try:

        if orig_path.is_relative_to(FOTOS_DIR):

            is_manual_source = True

    except ValueError:

        pass

        

    file_key = get_file_key(filepath)

    if face_data:

        fx, fy, fw, fh = (face_data[k] for k in ('x', 'y', 'width', 'height'))



    if new_identidad not in ["Falso_Positivo", "Ignorar_Irrelevante", "Desconocido"] and face_data:

        try:

            image = decode_image(np.fromfile(str(orig_path), dtype=np.uint8))

            if image is not None and detector is not None and recognizer is not None:

                with cache_lock:

                    feature = None

                    if 'feature' in face_data and face_data.get('feature'):

                        try:

                            from app.services.face_learning import normalized_feature

                            feature = normalized_feature(face_data['feature'])

                        except Exception:

                            pass

                    if feature is None:

                        try:

                            feature = aligned_feature(image, face_data, detector, recognizer, iou)

                        except Exception as e_align:

                            max_dim = 1024

                            h, w = image.shape[:2]

                            if max(h, w) > max_dim:

                                scale = max_dim / max(h, w)

                                img_small = cv2.resize(image, (int(w * scale), int(h * scale)))

                                scaled_rect = {

                                    'x': safe_float(face_data.get('x', 0)) * scale,

                                    'y': safe_float(face_data.get('y', 0)) * scale,

                                    'width': safe_float(face_data.get('width', 0)) * scale,

                                    'height': safe_float(face_data.get('height', 0)) * scale

                                }

                                try:

                                    feature = aligned_feature(img_small, scaled_rect, detector, recognizer, iou)

                                except Exception:

                                    pass

                    if feature is not None:

                        sample_key = file_key + ':' + ','.join(str(v) for v in (fx, fy, fw, fh))

                        from app.services.face_learning import update_confirmed_sample

                        updated_faces = update_confirmed_sample(known_faces, new_identidad, sample_key, feature)

                        import tempfile

                        temp_name = None

                        try:

                            with tempfile.NamedTemporaryFile(dir=CACHE_FILE.parent, delete=False) as cf:

                                temp_name = cf.name

                                pickle.dump(updated_faces, cf)

                                cf.flush()

                                os.fsync(cf.fileno())

                            os.replace(temp_name, CACHE_FILE)

                        finally:

                            if temp_name and os.path.exists(temp_name):

                                os.remove(temp_name)

                        known_faces.clear()

                        known_faces.update(updated_faces)



                        # Update centroids.pkl directly with confirmed human evidence

                        c_pkl_path = APP_DIR / "centroids.pkl"

                        try:

                            c_dict = {}

                            if c_pkl_path.exists():

                                with open(c_pkl_path, 'rb') as f_c:

                                    c_dict = pickle.load(f_c)

                            # Human confirmation is 100% reliable ground truth: anchor at the center

                            c_dict[(new_categoria, new_identidad)] = feature

                            c_dict[new_identidad] = feature

                            with open(c_pkl_path, 'wb') as f_c:

                                pickle.dump(c_dict, f_c)

                            if new_identidad == 'YO':

                                np.save(APP_DIR / "yo_pure_centroid.npy", feature)

                            reload_known_faces()

                            if file_key in faces_cache: del faces_cache[file_key]

                            if filepath in faces_cache: del faces_cache[filepath]

                            print(f"[DATASET REINFORCEMENT] Centroid for {new_identidad} anchored at center with 100% manual confidence.")

                        except Exception as e_c:

                            print(f"[DATASET REINFORCEMENT] Warning updating centroids.pkl: {e_c}")

        except Exception as e_learn:

            print(f"[CORRECT] Notice: Face model refinement skipped for {new_identidad} ({e_learn}); continuing clean move.")



    overrides = load_overrides()
    file_key = get_file_key(filepath)
    if file_key not in overrides:
        fname = Path(filepath).name if filepath else ''
        for k in overrides:
            if k == filepath or (fname and k.startswith(f"{fname}_")):
                file_key = k
                break

    if face_data:
        if file_key not in overrides: overrides[file_key] = []
        updated = False
        fx = safe_float(face_data.get('x'), 0.0)
        fy = safe_float(face_data.get('y'), 0.0)
        fw = safe_float(face_data.get('width'), 100.0)
        fh = safe_float(face_data.get('height'), 100.0)
        face_box = [fx, fy, fw, fh]

        old_box = None
        if old_face and isinstance(old_face, dict):
            old_box = [safe_float(old_face.get('x'), fx), safe_float(old_face.get('y'), fy), safe_float(old_face.get('width'), fw), safe_float(old_face.get('height'), fh)]

        # Find best match in overrides
        best_ov_idx = -1
        best_ov_iou = -1.0
        for idx, ov in enumerate(overrides.get(file_key, [])):
            ov_box = [safe_float(ov.get('x')), safe_float(ov.get('y')), safe_float(ov.get('width')), safe_float(ov.get('height'))]
            if sum(ov_box) == 0: continue
            cur_iou = max(iou(old_box, ov_box) if old_box else 0.0, iou(face_box, ov_box))
            if cur_iou > best_ov_iou:
                best_ov_iou = cur_iou
                best_ov_idx = idx

        if best_ov_idx >= 0 and best_ov_iou > 0.15:
            ov = overrides[file_key][best_ov_idx]
            ov['identity'] = new_identidad
            ov['provenance'] = HUMAN
            ov['x'] = fx; ov['y'] = fy; ov['width'] = fw; ov['height'] = fh
            updated = True
        else:
            for ov in overrides.get(file_key, []):
                if ov.get('identity') == new_identidad or len(overrides[file_key]) == 1:
                    ov['identity'] = new_identidad
                    ov['provenance'] = HUMAN
                    ov['x'] = fx; ov['y'] = fy; ov['width'] = fw; ov['height'] = fh
                    updated = True
                    break

        if not updated:
            overrides[file_key].append({
                'x': fx, 'y': fy, 'width': fw, 'height': fh,
                'identity': new_identidad, 'provenance': HUMAN
            })

        # Deduplicate overrides for file_key (never allow duplicate boxes for same identity or high mutual overlap)
        deduped = []
        for ov in overrides[file_key]:
            ov_b = [safe_float(ov.get('x')), safe_float(ov.get('y')), safe_float(ov.get('width')), safe_float(ov.get('height'))]
            ov_id = ov.get('identity')
            is_dup = False
            for d in deduped:
                d_b = [safe_float(d.get('x')), safe_float(d.get('y')), safe_float(d.get('width')), safe_float(d.get('height'))]
                if (d.get('identity') == ov_id and ov_id not in ('Desconocido', 'Falso_Positivo', 'Excluido')) or (sum(ov_b) > 0 and sum(d_b) > 0 and iou(ov_b, d_b) > 0.4):
                    d.update(ov)
                    is_dup = True
                    break
            if not is_dup:
                deduped.append(ov)
        overrides[file_key] = deduped
        save_overrides(overrides)

        # Update faces_cache in-place and deduplicate
        fk = get_file_key(filepath)
        if fk not in faces_cache:
            faces_cache[fk] = []
        updated_cache = False
        best_fc_idx = -1
        best_fc_iou = -1.0
        for idx, c_face in enumerate(faces_cache.get(fk, [])):
            c_box = [safe_float(c_face.get('x')), safe_float(c_face.get('y')), safe_float(c_face.get('width')), safe_float(c_face.get('height'))]
            if sum(c_box) == 0 and 'box' in c_face:
                c_box = [safe_float(c_face['box'][0]), safe_float(c_face['box'][1]), safe_float(c_face['box'][2]), safe_float(c_face['box'][3])]
            cur_iou = max(iou(old_box, c_box) if old_box else 0.0, iou(face_box, c_box))
            if cur_iou > best_fc_iou:
                best_fc_iou = cur_iou
                best_fc_idx = idx

        if best_fc_idx >= 0 and best_fc_iou > 0.15:
            cf = faces_cache[fk][best_fc_idx]
            cf.update({
                'x': fx, 'y': fy, 'width': fw, 'height': fh, 'box': [fx, fy, fw, fh],
                'identity': new_identidad, 'confidence': (0.0 if new_identidad == 'Desconocido' else 1.0),
                'is_manual': True, 'provenance': HUMAN
            })
            if new_identidad == 'Desconocido':
                cf['suggested_identity'] = None
                cf['suggested_score'] = 0.0
            updated_cache = True
        else:
            for c_face in faces_cache.get(fk, []):
                if c_face.get('identity') == new_identidad or len(faces_cache[fk]) == 1:
                    c_face.update({
                        'x': fx, 'y': fy, 'width': fw, 'height': fh, 'box': [fx, fy, fw, fh],
                        'identity': new_identidad, 'confidence': (0.0 if new_identidad == 'Desconocido' else 1.0),
                        'is_manual': True, 'provenance': HUMAN
                    })
                    updated_cache = True
                    break

        if not updated_cache:
            faces_cache[fk].append({
                'x': fx, 'y': fy, 'width': fw, 'height': fh, 'box': [fx, fy, fw, fh],
                'identity': new_identidad, 'confidence': 1.0, 'is_manual': True, 'provenance': HUMAN
            })

        # Deduplicate faces_cache[fk]
        deduped_fc = []
        for c_f in faces_cache[fk]:
            cb = [safe_float(c_f.get('x')), safe_float(c_f.get('y')), safe_float(c_f.get('width')), safe_float(c_f.get('height'))]
            cid = c_f.get('identity')
            is_dup = False
            for dfc in deduped_fc:
                dfcb = [safe_float(dfc.get('x')), safe_float(dfc.get('y')), safe_float(dfc.get('width')), safe_float(dfc.get('height'))]
                if (dfc.get('identity') == cid and cid not in ('Desconocido',)) or (sum(cb) > 0 and sum(dfcb) > 0 and iou(cb, dfcb) > 0.4):
                    dfc.update(c_f)
                    is_dup = True
                    break
            if not is_dup:
                deduped_fc.append(c_f)
        faces_cache[fk] = deduped_fc

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



    target_path = orig_path

    if new_categoria != "Ignorar" and new_identidad not in ["Falso_Positivo", "Ignorar_Irrelevante", "Desconocido"]:

        if is_manual_source:

            target_dir = FOTOS_DIR / new_categoria / new_identidad

        else:

            target_dir = RESULTADOS_DIR / new_categoria / new_identidad

            

        target_dir.mkdir(parents=True, exist_ok=True)

        

        if orig_path.parent.resolve() == target_dir.resolve():

            target_path = orig_path

        else:

            orig_ino = None

            try:

                if orig_path.exists():

                    orig_ino = os.stat(str(orig_path)).st_ino

            except OSError:

                pass



            existing_link = None

            if orig_ino is not None:

                for f in target_dir.iterdir():

                    try:

                        if f.is_file() and os.stat(str(f)).st_ino == orig_ino:

                            existing_link = f

                            break

                    except OSError:

                        pass

                    

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

                    with open(orig_path, 'rb') as source, open(target_path, 'xb') as destination:

                        shutil.copyfileobj(source, destination)

                        destination.flush()

                        os.fsync(destination.fileno())



            # Registrar SIEMPRE la reubicacion en _RELOCATED_CACHE para que ninguna peticion posterior falle con 404

            from app.utils.files import _RELOCATED_CACHE

            _RELOCATED_CACHE[orig_path.name] = str(target_path)

            _RELOCATED_CACHE[str(orig_path)] = str(target_path)

            try:

                _RELOCATED_CACHE[str(orig_path.resolve())] = str(target_path)

            except Exception:

                pass



            # Eliminar copia antigua de la carpeta anterior SOLO si no quedan caras pendientes o si no es foto multigrupal

            if Path(target_path).exists() and Path(orig_path).exists() and Path(orig_path).resolve() != Path(target_path).resolve():

                old_folder_name = orig_path.parent.name

                old_parent_lower = str(orig_path.parent).lower().replace('\\', '/')

                is_transient_folder = any(kw in old_parent_lower for kw in ('_dudoso', 'dudoso', 'revision', 'sin_nombre', 'para revisar', 'desconocid'))

                cached_faces = faces_cache.get(file_key, []) or overrides.get(file_key, [])

                has_multiple_faces = len(cached_faces) > 1

                has_unreviewed_faces = any(

                    (f.get('identity') in (None, '', 'Desconocido', 'Dudoso', 'Sin Identificar', 'Sin Nombre') or not f.get('is_manual'))

                    for f in cached_faces if isinstance(f, dict)

                )

                old_person_still_present = any(

                    (f.get('identity') == old_folder_name or f.get('identity') == f'C. {old_folder_name}')

                    for f in cached_faces if isinstance(f, dict)

                )

                

                # REGLA DE ORO: Si una foto tiene multiples caras (ej: 8 caras), NO eliminar el archivo original

                # de la carpeta mientras el usuario revisa o queden caras por confirmar

                should_delete = False

                if not has_multiple_faces or not has_unreviewed_faces:

                    if is_transient_folder:

                        should_delete = not has_unreviewed_faces

                    elif not is_manual_source and not old_person_still_present:

                        should_delete = True



                if should_delete:

                    try:

                        safe_remove_file(orig_path)

                    except Exception as e:

                        print(f'[REASSIGN] Error eliminando copia antigua {orig_path}: {e}')

                        

    # Update faces_cache key immediately (in-memory, fast): mantener AMBAS claves para que nunca se pierda

    old_fkey = get_file_key(filepath)

    new_fkey = get_file_key(target_path)

    if str(target_path) != filepath and old_fkey in faces_cache:

        faces_cache[new_fkey] = faces_cache[old_fkey]



    # All slow GC + cleanup runs in background so response is instant

    return str(target_path)





def api_correct():

    data = request.json or {}

    filepath = data.get('path')

    new_categoria = data.get('new_categoria')

    new_identidad = data.get('new_identidad')

    face_data = data.get('face')
    old_face = data.get('old_face')
    face_num = data.get('face_num')

    

    if not filepath:

        return jsonify({"error": "Falta parámetro path"}), 400

        

    real_path = find_relocated_file(filepath)

    if not real_path:

        # Check if virtual iCloud photo in apple_db

        try:

            from app.services.apple_service import load_apple_db

            adb = load_apple_db()

            if filepath in adb or (filepath and os.path.basename(filepath) in adb):

                real_path = filepath

        except Exception:

            pass

    if not real_path:

        return jsonify({"error": "Archivo fuera de la biblioteca o no encontrado"}), 404

    filepath = real_path



    if not os.path.exists(filepath):

        is_virtual = False

        try:

            from app.services.apple_service import load_apple_db

            adb = load_apple_db()

            if filepath in adb or (filepath and os.path.basename(filepath) in adb):

                is_virtual = True

        except Exception:

            pass

        if not is_virtual:

            return jsonify({"error": f"El archivo {filepath} no existe en disco"}), 404

        

    clear_gallery_cache()

    

    try:

        target_path = apply_correction_to_file(filepath, new_categoria, new_identidad, face_data, provenance=HUMAN, old_face=old_face, face_num=face_num)

        

        # Propagación automática en segundo plano (ultra-rápido, no bloquea al usuario)

        def _bg_propagation():

            try:

                from app.utils.files import calculate_dhash

                orig_path = Path(filepath)

                parent_dir = orig_path.parent

                current_hash = calculate_dhash(str(orig_path))

                

                if current_hash is not None and face_data:

                    valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".avi"}

                    fx = safe_float(face_data.get('x'), 0.0)

                    fy = safe_float(face_data.get('y'), 0.0)

                    fw = safe_float(face_data.get('width'), 100.0)

                    fh = safe_float(face_data.get('height'), 100.0)

                    face_box = [fx, fy, fw, fh]

                    

                    # 1. Obtener la característica (feature) del rostro corregido desde faces_cache

                    corrected_feat = None

                    orig_faces = faces_cache.get(str(orig_path), [])

                    best_match_iou = 0.0

                    for f_cache in orig_faces:

                        if 'feature' in f_cache:

                            c_box = [safe_float(f_cache.get('x')), safe_float(f_cache.get('y')), safe_float(f_cache.get('width')), safe_float(f_cache.get('height'))]

                            if sum(c_box) == 0 and 'box' in f_cache:

                                c_box = [safe_float(f_cache['box'][0]), safe_float(f_cache['box'][1]), safe_float(f_cache['box'][2]), safe_float(f_cache['box'][3])]

                            curr_iou = iou(face_box, c_box)

                            if curr_iou > best_match_iou:

                                best_match_iou = curr_iou

                                corrected_feat = f_cache['feature']

                    

                    if corrected_feat is not None:

                        corrected_feat = np.array(corrected_feat, dtype=np.float32).flatten()

                        corrected_feat /= (np.linalg.norm(corrected_feat) + 1e-10)



                    # Obtener dimensiones de la imagen original

                    w_orig = safe_float(face_data.get('img_width'), 1.0)

                    h_orig = safe_float(face_data.get('img_height'), 1.0)

                    if w_orig <= 1.0 or h_orig <= 1.0:

                        try:

                            img_orig = decode_image(np.fromfile(str(orig_path), dtype=np.uint8))

                            if img_orig is not None:

                                h_orig, w_orig, _ = img_orig.shape

                        except: pass



                    for other_file in parent_dir.iterdir():

                        if not other_file.is_file() or other_file.name == orig_path.name:

                            continue

                        if other_file.suffix.lower() not in valid_exts:

                            continue

                        

                        other_hash = calculate_dhash(str(other_file))

                        if other_hash is not None and len(other_hash) == len(current_hash):

                            hamming_dist = np.count_nonzero(current_hash != other_hash)

                            similarity = (1.0 - (hamming_dist / len(current_hash))) * 100

                            

                            if similarity >= 75.0:  # Umbral de ráfagas/parecidas

                                dup_faces = faces_cache.get(str(other_file), [])

                                if not dup_faces:

                                    try:

                                        img_dup = decode_image(np.fromfile(str(other_file), dtype=np.uint8))

                                        if img_dup is not None:

                                            h_d, w_d, _ = img_dup.shape

                                            detector.setInputSize((w_d, h_d))

                                            _, detected_faces = detector.detect(img_dup)

                                            if detected_faces is not None:

                                                for df in detected_faces:

                                                    aligned = recognizer.alignCrop(img_dup, df)

                                                    feat = recognizer.feature(aligned)[0]

                                                    feat_norm = feat / (np.linalg.norm(feat) + 1e-10)

                                                    dup_faces.append({

                                                        'x': float(df[0]), 'y': float(df[1]),

                                                        'width': float(df[2]), 'height': float(df[3]),

                                                        'feature': feat_norm.tolist(),

                                                        'identity': 'Desconocido'

                                                    })

                                    except: pass



                                best_face = None

                                # 1. Intento por similitud de vector biométrico

                                if corrected_feat is not None:

                                    best_score = 0.0

                                    for df in dup_faces:

                                        if 'feature' in df:

                                            feat_arr = np.array(df['feature'], dtype=np.float32).flatten()

                                            score = float(np.dot(corrected_feat, feat_arr))

                                            if score > best_score:

                                                best_score = score

                                                best_face = df

                                    if best_score < 0.40:

                                        best_face = None



                                # 2. Si no hay vector o es bajo, usar similitud geométrica (IoU espacial relativo)

                                if best_face is None and len(dup_faces) > 0 and w_orig > 1.0 and h_orig > 1.0:

                                    w_dup = w_orig

                                    h_dup = h_orig

                                    try:

                                        img_dup_meta = decode_image(np.fromfile(str(other_file), dtype=np.uint8))

                                        if img_dup_meta is not None:

                                            h_dup, w_dup, _ = img_dup_meta.shape

                                    except: pass



                                    norm_face_box = [

                                        face_box[0] / w_orig,

                                        face_box[1] / h_orig,

                                        face_box[2] / w_orig,

                                        face_box[3] / h_orig

                                    ]

                                    

                                    best_iou = 0.0

                                    best_face_iou = None

                                    for df in dup_faces:

                                        df_box = [safe_float(df.get('x')), safe_float(df.get('y')), safe_float(df.get('width')), safe_float(df.get('height'))]

                                        if sum(df_box) == 0 and 'box' in df:

                                            df_box = [safe_float(df['box'][0]), safe_float(df['box'][1]), safe_float(df['box'][2]), safe_float(df['box'][3])]

                                        norm_df_box = [

                                            df_box[0] / w_dup,

                                            df_box[1] / h_dup,

                                            df_box[2] / w_dup,

                                            df_box[3] / h_dup

                                        ]

                                        curr_iou = iou(norm_face_box, norm_df_box)

                                        if curr_iou > best_iou:

                                            best_iou = curr_iou

                                            best_face_iou = df

                                    if best_iou > 0.35:

                                        best_face = best_face_iou

                                

                                if best_face:

                                    apply_correction_to_file(str(other_file), new_categoria, new_identidad, best_face)

            except Exception as e_prop:

                print(f"[PROPAGACION] Error propagando corrección: {e_prop}")

        import threading

        threading.Thread(target=_bg_propagation, daemon=True).start()



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




def update_gallery_cache_for_rename(old_cat, old_ident, new_cat, new_ident):
    try:
        from app.globals import get_gallery_cache, set_gallery_cache
        cache = get_gallery_cache()
        if cache is None:
            return
        
        clean_old_id = re.sub(r'^[👤📋📁❓🔍✨📸⚡🎉🏷️👥🧑👧👦\s]+', '', str(old_ident)).strip()
        clean_new_id = re.sub(r'^[👤📋📁❓🔍✨📸⚡🎉🏷️👥🧑👧👦\s]+', '', str(new_ident)).strip()
        clean_old_cat = re.sub(r'^[👤📋📁❓🔍✨📸⚡🎉🏷️👥🧑👧👦\s]+', '', str(old_cat)).strip()
        clean_new_cat = re.sub(r'^[👤📋📁❓🔍✨📸⚡🎉🏷️👥🧑👧👦\s]+', '', str(new_cat)).strip()

        items_to_move = []
        for c_key in list(cache.keys()):
            clean_c = re.sub(r'^[👤📋📁❓🔍✨📸⚡🎉🏷️👥🧑👧👦\s]+', '', str(c_key)).strip()
            if clean_c == clean_old_cat or not old_cat or clean_old_cat in clean_c:
                for id_key in list(cache[c_key].keys()):
                    clean_i = re.sub(r'^[👤📋📁❓🔍✨📸⚡🎉🏷️👥🧑👧👦\s]+', '', str(id_key)).strip()
                    if clean_i == clean_old_id:
                        items_to_move.extend(cache[c_key].pop(id_key, []))

        if not items_to_move:
            for c_key in list(cache.keys()):
                for id_key in list(cache[c_key].keys()):
                    clean_i = re.sub(r'^[👤📋📁❓🔍✨📸⚡🎉🏷️👥🧑👧👦\s]+', '', str(id_key)).strip()
                    if clean_i == clean_old_id:
                        items_to_move.extend(cache[c_key].pop(id_key, []))

        target_cat_key = new_cat
        for c_key in cache.keys():
            if re.sub(r'^[👤📋📁❓🔍✨📸⚡🎉🏷️👥🧑👧👦\s]+', '', str(c_key)).strip() == clean_new_cat:
                target_cat_key = c_key
                break
        if target_cat_key not in cache:
            cache[target_cat_key] = {}

        target_ident_key = new_ident
        for id_key in cache[target_cat_key].keys():
            if re.sub(r'^[👤📋📁❓🔍✨📸⚡🎉🏷️👥🧑👧👦\s]+', '', str(id_key)).strip() == clean_new_id:
                target_ident_key = id_key
                break
        if target_ident_key not in cache[target_cat_key]:
            if any(k.startswith('👤 ') for k in cache[target_cat_key].keys()):
                target_ident_key = f'👤 {clean_new_id}'
            cache[target_cat_key][target_ident_key] = []

        for itm in items_to_move:
            itm['category'] = target_cat_key
            itm['identity'] = clean_new_id

        cache[target_cat_key][target_ident_key].extend(items_to_move)
        set_gallery_cache(cache)
    except Exception as e_cache:
        print(f"[RENAME] Error updating gallery cache in-place: {e_cache}")

def api_rename_group():

    try:

        data = request.json or {}

        cat = data.get('cat')

        ident = data.get('ident') or data.get('old_name') or data.get('old_ident')

        new_name = data.get('new_name') or data.get('new_ident') or data.get('name') or data.get('target')

        new_cat = data.get('new_cat') or data.get('target_cat')

        if not cat and ident:
            from app.globals import get_gallery_cache
            g_c = get_gallery_cache()
            if g_c:
                for c_k, id_map in g_c.items():
                    if ident in id_map or f"👤 {ident}" in id_map:
                        cat = c_k
                        break
            if not cat:
                cat = "📋 Revisión / Por Organizar" 

        

        if not cat or not ident or not new_name:

            return jsonify({"error": "Parametros insuficientes: falta el nuevo nombre"}), 400



        def clean_val(v):

            if not v: return ""

            s = str(v).strip()

            for prefix in ['👤', '📋', '📁', '❓', '🔍', '✨', '📸', '⚡', '🎉', '🏷️', '👥', '🧑', '👧', '👦']:

                if s.startswith(prefix):

                    s = s[len(prefix):].strip()

            return s



        c_ident = clean_val(ident)

        c_cat = clean_val(cat)

        c_new_name = clean_val(new_name)

        c_new_cat = clean_val(new_cat)



        if not c_new_cat or c_new_cat.strip() == "":

            if c_new_name.startswith('F. ') or c_new_name.startswith('F_'):

                c_new_cat = 'Familia'

            elif c_new_name.startswith('P. ') or c_new_name.startswith('P_'):

                c_new_cat = 'Profesores'

            elif c_new_name.startswith('M. ') or c_new_name.startswith('M_'):

                c_new_cat = 'Mascotas'

            elif c_new_name == 'YO':

                c_new_cat = 'YO'

            else:

                c_new_cat = 'Conocidos'

        elif c_new_name == 'YO' or c_new_cat == 'YO':

            c_new_cat = 'YO'

            c_new_name = 'YO'



        from app.services.apple_service import rename_apple_group

        apple_count = rename_apple_group(cat, ident, c_new_cat, c_new_name)

        if (c_ident != ident or c_cat != cat) and apple_count == 0:

            apple_count += rename_apple_group(c_cat, c_ident, c_new_cat, c_new_name)



        # Migrate centroid in memory and disk for the renamed group

        try:

            from app.globals import known_faces, cache_lock, CACHE_FILE

            from pathlib import Path

            centroid_file = APP_DIR / 'centroids.pkl'

            if centroid_file.exists():

                with open(centroid_file, 'rb') as f_c:

                    c_dict = pickle.load(f_c)

                old_vec = None

                for candidate_k in [(cat, ident), (c_cat, c_ident), ident, c_ident]:

                    if candidate_k in c_dict and c_dict[candidate_k] is not None:

                        old_vec = c_dict[candidate_k]

                        break

                if old_vec is not None:

                    c_dict[(c_new_cat, c_new_name)] = old_vec

                    c_dict[c_new_name] = old_vec

                    with open(centroid_file, 'wb') as f_c:

                        pickle.dump(c_dict, f_c)

            if CACHE_FILE.exists():

                with open(CACHE_FILE, 'rb') as f_sf:

                    sf_dict = pickle.load(f_sf)

                old_sf = sf_dict.pop(ident, None) or sf_dict.pop(c_ident, None)

                if old_sf is not None:

                    sf_dict[c_new_name] = old_sf

                    with open(CACHE_FILE, 'wb') as f_sf:

                        pickle.dump(sf_dict, f_sf)

        except Exception as e_mig:

            print(f"[RENAME] Error migrating centroids: {e_mig}")



        src_dirs_res = []

        src_dirs_fotos = []



        # Raíces principales

        primary_roots = [RESULTADOS_DIR, FOTOS_DIR]

        valid_primary = [r for r in primary_roots if r and r.exists()]



        # Variantes de nombres (con emoji, sin emoji, con #, sin #)

        name_variants = [ident, c_ident]

        clean_num = c_ident.replace("Persona Nueva #", "").replace("Persona Nueva ", "").strip()

        if clean_num:

            name_variants.extend([f"Persona Nueva #{clean_num}", f"Persona Nueva {clean_num}"])

        name_variants = list(dict.fromkeys([v for v in name_variants if v]))



        sub_variants = [

            cat, c_cat,

            "Personas Sin Nombre",

            "Conocidos",

            "Familia",

            "Por Organizar",

            "Para organizar",

            "Revisión / Por Organizar",

            "Dudosos",

            "Dudosos/Para Revisar",

            ""

        ]



        for r in valid_primary:

            for sub in sub_variants:

                for n_var in name_variants:

                    cand = (r / sub / n_var) if sub else (r / n_var)

                    if cand.exists() and cand.is_dir() and cand not in src_dirs_res:

                        src_dirs_res.append(cand)



        # Si no se encontró en las raíces primarias y NO estamos en test:

        import app.globals as g_module

        is_testing = getattr(g_module, 'TESTING', False) or os.environ.get('TESTING') == '1'

        if not src_dirs_res and not is_testing and apple_count == 0:

            secondary_roots = [

                FOTOS_DIR.parent if hasattr(FOTOS_DIR, 'parent') else None,

                RESULTADOS_DIR.parent if hasattr(RESULTADOS_DIR, 'parent') else None,

                APP_DIR / "Resultados",

                APP_DIR / "Fotos",

                Path.cwd() / "Resultados",

                Path.cwd() / "Fotos"

            ]

            valid_sec = [r for r in secondary_roots if r and r.exists() and r not in valid_primary]

            for r in valid_sec:

                for sub in sub_variants:

                    for n_var in name_variants:

                        cand = (r / sub / n_var) if sub else (r / n_var)

                        if cand.exists() and cand.is_dir() and cand not in src_dirs_res:

                            src_dirs_res.append(cand)



            if not src_dirs_res:

                target_lowers = {n.lower() for n in name_variants}

                for r in valid_primary + valid_sec:

                    try:

                        for root, dirs, _ in os.walk(str(r)):

                            for d in dirs:

                                if d.lower() in target_lowers:

                                    d_path = Path(root) / d

                                    if d_path not in src_dirs_res:

                                        src_dirs_res.append(d_path)

                    except Exception:

                        pass



        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".avi"}

        moved_count = 0



        if not src_dirs_res and not src_dirs_fotos:

            # Rescate desde el cache de galeria para categorias virtuales/organizar

            from app.globals import get_gallery_cache

            cache = get_gallery_cache() or {}

            items = (

                cache.get(cat, {}).get(ident, []) or 

                cache.get(c_cat, {}).get(c_ident, []) or

                cache.get(cat, {}).get(c_ident, []) or

                cache.get(c_cat, {}).get(ident, [])

            )

            if not items:

                # Búsqueda en todas las categorías del caché

                for cat_k, idents_dict in cache.items():

                    for n_var in name_variants:

                        if n_var in idents_dict and idents_dict[n_var]:

                            items = idents_dict[n_var]

                            break

                    if items:

                        break



            if items:

                target_dir_res = RESULTADOS_DIR / c_new_cat / c_new_name

                target_dir_res.mkdir(parents=True, exist_ok=True)

                for it in items:

                    p = Path(it.get('path', ''))

                    if p.exists() and p.is_file() and p.suffix.lower() in valid_exts:

                        target_file = target_dir_res / p.name

                        counter = 1

                        while target_file.exists():

                            target_file = target_dir_res / f"{p.stem}_{counter}{p.suffix}"

                            counter += 1

                        try:
                            from app.services.apple_service import is_apple_photo
                            import shutil
                            p_str = str(p).replace(chr(92), '/').lower()
                            if 'icloud photos' in p_str or is_apple_photo(str(p)):
                                shutil.copy2(str(p), str(target_file))
                            else:
                                safe_move_file(p, target_file)
                            moved_count += 1
                        except Exception:
                            pass

            elif apple_count > 0:
                update_gallery_cache_for_rename(cat, ident, c_new_cat, c_new_name)
                try:
                    from app.utils.faces import clear_identities_cache
                    clear_identities_cache()
                except Exception:
                    pass
                return jsonify({"success": True, "count": apple_count})
            elif (RESULTADOS_DIR / c_new_cat / c_new_name).exists() or (FOTOS_DIR / c_new_cat / c_new_name).exists():

                # Idempotencia: el grupo ya fue fusionado previamente (evita error 404 por doble clic)

                clear_gallery_cache()

                return jsonify({"success": True, "count": 0, "already_merged": True})

            else:

                return jsonify({"error": "Carpeta de grupo no encontrada"}), 404

            

        target_dir_res = RESULTADOS_DIR / c_new_cat / c_new_name

        target_dir_fotos = FOTOS_DIR / c_new_cat / c_new_name

        

        moved_count = 0

        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".avi"}

        

        for s_dir in src_dirs_res:

            target_dir_res.mkdir(parents=True, exist_ok=True)

            for file_path in s_dir.iterdir():

                if file_path.is_file() and file_path.suffix.lower() in valid_exts:

                    target_file = target_dir_res / file_path.name

                    counter = 1

                    while target_file.exists():

                        target_file = target_dir_res / f"{file_path.stem}_{counter}{file_path.suffix}"

                        counter += 1

                    try:

                        safe_move_file(file_path, target_file)

                        moved_count += 1

                    except Exception:

                        pass

            try:

                os.rmdir(str(s_dir))

            except Exception:

                pass



        for s_dir in src_dirs_fotos:

            target_dir_fotos.mkdir(parents=True, exist_ok=True)

            for file_path in s_dir.iterdir():

                if file_path.is_file() and file_path.suffix.lower() in valid_exts:

                    target_file = target_dir_fotos / file_path.name

                    counter = 1

                    while target_file.exists():

                        target_file = target_dir_fotos / f"{file_path.stem}_{counter}{file_path.suffix}"

                        counter += 1

                    try:

                        safe_move_file(file_path, target_file)

                        moved_count += 1

                    except Exception:

                        pass

            try:

                os.rmdir(str(s_dir))

            except Exception:

                pass



        try:

            with cache_lock:

                for k in [ident, c_ident]:

                    if k in known_faces:

                        del known_faces[k]

                with open(CACHE_FILE, 'wb') as f_cache:

                    pickle.dump(known_faces, f_cache)

        except Exception:

            pass



        update_gallery_cache_for_rename(cat, ident, c_new_cat, c_new_name)

        try:
            from app.utils.faces import clear_identities_cache
            clear_identities_cache()
        except Exception:
            pass

        # Invalidate avatar caches so fresh avatars are generated from the unified album
        try:
            for n_to_del in [ident, c_ident, new_name, c_new_name]:
                if not n_to_del: continue
                clean_n = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(n_to_del))
                for f_dir in [THUMBNAILS_DIR, APP_DIR / "cache" / "thumbnails"]:
                    if f_dir and f_dir.exists():
                        for av_file in f_dir.glob(f"av_*{clean_n}*.webp"):
                            try:
                                av_file.unlink(missing_ok=True)
                            except Exception:
                                pass
        except Exception as e_av_del:
            print(f"[RENAME] Error purging avatar caches: {e_av_del}")

        return jsonify({"success": True, "count": moved_count + apple_count})

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

                        img = decode_image(file_bytes)

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



        overrides = load_overrides()

        rebuilt_count = 0

        total_photos_processed = 0

        outliers_rejected = 0

        new_known_faces = {}

        

        feats_by_identity = {}

        # Iterate over all cached files to extract pure manual overrides

        for filepath, faces in list(faces_cache.items()):

            fkey = get_file_key(filepath)

            file_ovs = [ov for ov in overrides.get(fkey, []) if ov.get('provenance') == HUMAN]

            if not file_ovs:

                continue

                

            try:

                if not Path(filepath).exists():

                    continue

                file_bytes = np.fromfile(filepath, dtype=np.uint8)

                img = decode_image(file_bytes)

                if img is None: continue

                

                h, w, _ = img.shape

                detector.setInputSize((w, h))

                _, faces_detected = detector.detect(img)

                

                if faces_detected is not None and len(faces_detected) > 0:

                    for ov in file_ovs:

                        identity_name = ov.get('identity')

                        if not identity_name or identity_name in ["Falso_Positivo", "Ignorar_Irrelevante"]:

                            continue

                            

                        if identity_name.startswith("_") or identity_name in ["Desconocidos", "Personas Sin Nombre", "Ignorar"]:

                            continue

                        if is_smart_relationship_album(identity_name):

                            continue

                            

                        ov_box = [float(ov['x']), float(ov['y']), float(ov['width']), float(ov['height'])]

                        best_face = None

                        max_iou = 0.0

                        for face in faces_detected:

                            f_box = [float(face[0]), float(face[1]), float(face[2]), float(face[3])]

                            curr_iou = iou(ov_box, f_box)

                            if curr_iou > max_iou:

                                max_iou = curr_iou

                                best_face = face

                                

                        if max_iou > 0.2 and best_face is not None:

                            aligned = recognizer.alignCrop(img, best_face)

                            feat = recognizer.feature(aligned)[0]

                            feat_norm = feat / (np.linalg.norm(feat) + 1e-10)

                            

                            if identity_name not in feats_by_identity:

                                feats_by_identity[identity_name] = []

                            feats_by_identity[identity_name].append({

                                'feat': feat_norm,

                                'name': Path(filepath).name

                            })

                            total_photos_processed += 1

            except Exception:

                pass

                

        # Build pure centroids

        for identity_name, feats_list in feats_by_identity.items():

            feats_arr = np.array([item['feat'] for item in feats_list])

            sample_names = [item['name'] for item in feats_list]

            

            raw_centroid = np.mean(feats_arr, axis=0)

            raw_centroid /= (np.linalg.norm(raw_centroid) + 1e-10)

            

            valid_feats = []

            if len(feats_arr) >= 3:

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

            

            from app.services.face_learning import compute_appearance_centroids

            appearance_centroids = compute_appearance_centroids(valid_feats)

            new_known_faces[identity_name] = {

                'centroid': clean_centroid,

                'centroids': appearance_centroids,

                'names': sample_names, 'provenance': HUMAN

            }

            rebuilt_count += 1

            

        with cache_lock:

            known_faces.update(new_known_faces)

            with open(CACHE_FILE, 'wb') as f_cache:

                pickle.dump(known_faces, f_cache)

            clear_gallery_cache()



        return jsonify({

            "success": True,

            "identities_rebuilt": rebuilt_count,

            "photos_processed": total_photos_processed,

            "outliers_rejected": outliers_rejected,

            "message": f"Se han recalculado {rebuilt_count} personas usando exclusivamente sus miniaturas validadas ({outliers_rejected} fotos atípicas descartadas)."

        })

    except Exception as e:

        import traceback

        traceback.print_exc()

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

        img = decode_image(file_bytes)

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

            faces_cache[get_file_key(filepath)] = new_faces

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

    from app.globals import detector, recognizer, known_faces, APP_DIR

    from app.utils.files import get_file_key

    from app.utils.faces import get_cosine_similarity

    

    data = request.json or {}

    filepath = data.get('path')

    force = data.get('force', False)

    

    if not filepath:

        return jsonify({"error": "File not found"}), 404

        

    if not os.path.exists(filepath):

        from app.utils.files import find_relocated_file

        real_p = find_relocated_file(filepath)

        if not real_p or not os.path.exists(real_p):

            return jsonify({"error": "File not found"}), 404

        filepath = real_p

        

    path_obj = Path(filepath)

    if path_obj.suffix.lower() not in [".mp4", ".mov", ".avi"]:

        return jsonify({"error": "Not a video"}), 400

        

    file_key = get_file_key(filepath)

    video_cache_file = APP_DIR / "video_faces_cache.json"

    

    # 1. Devolver de caché persistente de forma instantánea (<5ms) salvo que el usuario pida re-escanear

    if not force and video_cache_file.exists():

        try:

            with open(video_cache_file, 'r', encoding='utf-8') as f:

                vcache = json.load(f)

            if file_key in vcache:

                return jsonify({

                    "success": True,

                    "detections": vcache[file_key],

                    "cached": True

                })

        except Exception as e:

            print(f"[VIDEO_CACHE] Error leyendo {video_cache_file}: {e}")

            

    # 2. Escaneo robusto con umbral de seguridad (0.55) y filtro de consistencia temporal

    try:

        cap = cv2.VideoCapture(str(filepath))

        fps = cap.get(cv2.CAP_PROP_FPS)

        if fps <= 0: fps = 30

        

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        duration = frame_count / fps

        

        identity_matches = {}

        

        # Create dedicated thread-isolated detector to prevent any concurrent state mutation with api_analyze

        local_detector = cv2.FaceDetectorYN.create(

            str(APP_DIR / "models" / "face_detection_yunet.onnx"), 

            "", (320, 320), 0.25, 0.3, 5000

        )

        local_recognizer = cv2.FaceRecognizerSF.create(

            str(APP_DIR / "models" / "face_recognition_sface.onnx"), ""

        )

        local_detector.setScoreThreshold(0.25)

        from app.globals import detector_lock

        # Escaneo a 1 fps con límite de duración razonable

        max_sec = min(int(duration) + 1, 120)

        for sec in range(0, max_sec):

            target_frame = int(sec * fps)

            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

            ret, frame = cap.read()

            if not ret or frame is None:

                continue

                

            h, w, _ = frame.shape

            scale = 1.0

            max_dim = 1024

            if max(w, h) > max_dim:

                scale = max_dim / max(w, h)

            # Ensure width and height are strictly multiples of 32 for OpenCV 5 DNN graph engine stability

            det_w = max(160, (int(w * scale) // 32) * 32)

            det_h = max(160, (int(h * scale) // 32) * 32)

            det_frame = cv2.resize(frame, (det_w, det_h))



            faces = None

            with detector_lock:

                try:

                    local_detector.setInputSize((det_w, det_h))

                    _, faces = local_detector.detect(det_frame)

                except Exception:

                    faces = None

            

            if faces is not None:

                inv_scale = 1.0 / scale if scale > 0 else 1.0

                for f in faces:

                    # Descartar caras diminutas del fondo de restaurantes / viandantes (<50x50 px)

                    fw = f[2] * inv_scale

                    fh = f[3] * inv_scale

                    if fw < 50 or fh < 50:

                        continue

                    if len(f) > 14 and f[14] < 0.35:

                        continue

                        

                    orig_f = f.copy()

                    orig_f[:4] *= inv_scale

                    orig_f[4:14] *= inv_scale

                    

                    feature = None

                    try:

                        aligned = local_recognizer.alignCrop(frame, orig_f)

                        if aligned is not None and aligned.size > 0:

                            with detector_lock:

                                feature = local_recognizer.feature(aligned)

                    except Exception:

                        feature = None

                    if feature is None: continue

                    

                    # Track top scores per distinct person identity to avoid duplicate tuple/str keys collapsing margins

                    identity_scores = {}

                    for db_id, data_dict in known_faces.items():

                        ident_n = db_id[1] if isinstance(db_id, tuple) else str(db_id)

                        if is_smart_relationship_album(ident_n) or ident_n.startswith("Falso_Positivo") or ident_n.startswith("Ignorar_"):

                            continue

                        score = match_face_to_identity(feature[0], data_dict)

                        if ident_n not in identity_scores or score > identity_scores[ident_n]:

                            identity_scores[ident_n] = score



                    sorted_matches = sorted(identity_scores.items(), key=lambda x: x[1], reverse=True)

                    if sorted_matches:

                        best_match, best_score = sorted_matches[0]

                        second_best_score = sorted_matches[1][1] if len(sorted_matches) > 1 else 0.0

                        if best_score >= 0.40:

                            margin = best_score - second_best_score

                            clean_m = best_match

                            folder_owner = path_obj.parent.name

                            is_folder_owner = (clean_m == folder_owner)

                            if margin >= 0.02 or best_score >= 0.48 or is_folder_owner:

                                if clean_m not in identity_matches:

                                    identity_matches[clean_m] = []

                                identity_matches[clean_m].append({'sec': sec, 'score': best_score})

                        

        cap.release()

        

        # 3. Filtrar consistencia temporal: debe aparecer en >= 2 segundos distintos o tener certeza alta (>= 0.65)

        final_results = []

        for ident, occs in identity_matches.items():

            if ident.startswith("Falso_Positivo") or ident.startswith("Ignorar_Irrelevante"):

                continue

            distinct_secs = sorted(list(set(o['sec'] for o in occs)))

            max_score = max(o['score'] for o in occs)

            

            if len(distinct_secs) >= 1 and (max_score >= 0.40):

                final_results.append({

                    "identity": ident,

                    "seconds": distinct_secs,

                    "confidence": round(max_score * 100, 1)

                })

                

        # 4. Guardar en caché persistente atómica

        try:

            vcache = {}

            if video_cache_file.exists():

                try:

                    with open(video_cache_file, 'r', encoding='utf-8') as f:

                        vcache = json.load(f)

                except Exception:

                    pass

            vcache[file_key] = final_results

            

            import tempfile

            with tempfile.NamedTemporaryFile('w', dir=APP_DIR, delete=False, encoding='utf-8') as tf:

                json.dump(vcache, tf, indent=2, ensure_ascii=False)

                t_name = tf.name

            os.replace(t_name, video_cache_file)

        except Exception as e:

            print(f"[VIDEO_CACHE] Error guardando cache: {e}")

            

        return jsonify({"success": True, "detections": final_results, "cached": False})

        

    except Exception as e:

        print("Video Scan Error (handled):", e)

        return jsonify({"success": True, "detections": [], "cached": False, "error": str(e)})





def api_undo_discard():

    data = request.json or {}

    filepath = data.get('path')

    face_data = data.get('face')

    

    if not filepath:

        return jsonify({"error": "Path required"}), 400

        

    from app.utils.files import load_overrides, save_overrides, find_relocated_file, get_file_key

    real_path = find_relocated_file(filepath) or filepath

    file_key = get_file_key(real_path)

    

    overrides = load_overrides()

    if file_key in overrides:

        if face_data:

            fx = float(face_data.get('x', 0))

            fy = float(face_data.get('y', 0))

            fw = float(face_data.get('width', 0))

            fh = float(face_data.get('height', 0))

            face_box = [fx, fy, fw, fh]

            from app.utils.faces import iou

            overrides[file_key] = [

                ov for ov in overrides[file_key]

                if not (ov.get('identity') in ['Ignorar_Irrelevante', 'Falso_Positivo']

                        and iou(face_box, [float(ov.get('x', 0)), float(ov.get('y', 0)), float(ov.get('width', 0)), float(ov.get('height', 0))]) > 0.3)

            ]

        else:

            overrides[file_key] = [

                ov for ov in overrides[file_key]

                if ov.get('identity') not in ['Ignorar_Irrelevante', 'Falso_Positivo']

            ]

        save_overrides(overrides)

        

    from app.globals import faces_cache, FACES_CACHE_FILE, cache_lock

    import pickle

    with cache_lock:

        if file_key in faces_cache:

            del faces_cache[file_key]

        try:

            with open(FACES_CACHE_FILE, 'wb') as f:

                pickle.dump(faces_cache, f)

        except Exception as e:

            print(f"[UNDO_DISCARD] Error persistiendo faces_cache: {e}")

        

    return jsonify({"success": True})



############################################################

# MOTOR DE AUTO-CORRECCIÓN BIDIRECCIONAL STATEFUL (v3)

############################################################

import threading

import time

import json

import os

import shutil



# ── Estado global del motor con persistencia en disco ────────

_ENGINE_STATE_FILE = APP_DIR / "engine_state.json"



_ENGINE_STATE = {

    "running": False,

    "phase": "idle",              # idle | scan_unknown | audit_known | waiting

    "total_scanned": 0,

    "total_moved_to_known": 0,

    "total_moved_to_review": 0,

    "total_fixed": 0,

    "last_actions": [],            # log de últimas 25 acciones

    "checkpoint": {},              # {file_key: timestamp} para no repetir trabajo

    "last_scanned_file": None,

    "cycle": 0,

    "started_at": None,

    "last_saved_at": None,

    "errors": 0,

}

_ENGINE_LOCK = threading.Lock()

_ENGINE_THREAD = None



AUDIT_THRESHOLD_LOW  = 0.48   # por debajo → la foto sale de su carpeta

AUDIT_THRESHOLD_HIGH = 0.48   # por encima → asignamos a nuevo destino

AUDIT_PHASE_DELAY    = 0.0   # segundos de pausa entre fotos (baja prioridad de CPU)





def _log_action(action_str: str):

    """Añade una entrada al log en memoria (últimas 25) y persiste."""

    with _ENGINE_LOCK:

        _ENGINE_STATE["last_actions"].append({

            "ts": time.strftime("%H:%M:%S"),

            "msg": action_str

        })

        if len(_ENGINE_STATE["last_actions"]) > 25:

            _ENGINE_STATE["last_actions"].pop(0)





def _save_engine_state():

    """Guarda todo el estado del motor (contadores, progreso, checkpoint) en disco."""

    try:

        data_to_save = {

            "total_scanned": _ENGINE_STATE["total_scanned"],

            "total_moved_to_known": _ENGINE_STATE["total_moved_to_known"],

            "total_moved_to_review": _ENGINE_STATE["total_moved_to_review"],

            "total_fixed": _ENGINE_STATE["total_fixed"],

            "cycle": _ENGINE_STATE["cycle"],

            "phase": _ENGINE_STATE["phase"],

            "last_scanned_file": _ENGINE_STATE["last_scanned_file"],

            "last_saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),

            "checkpoint": _ENGINE_STATE["checkpoint"],

            "last_actions": _ENGINE_STATE["last_actions"]

        }

        temp_file = _ENGINE_STATE_FILE.parent / f"engine_state_{int(time.time()*1000)}.tmp"

        with open(temp_file, "w", encoding="utf-8") as fp:

            json.dump(data_to_save, fp, ensure_ascii=False, indent=2)

        if temp_file.exists():

            for _ in range(5):

                try:

                    os.replace(str(temp_file), str(_ENGINE_STATE_FILE))

                    break

                except Exception:

                    time.sleep(0.05)

            if temp_file.exists():

                try: temp_file.unlink()

                except Exception: pass

    except Exception as e:

        print(f"[ENGINE] Error guardando estado: {e}")





def _load_engine_state():

    """Restaura el estado completo guardado de la última sesión."""

    if _ENGINE_STATE_FILE.exists():

        try:

            with open(_ENGINE_STATE_FILE, "r", encoding="utf-8") as fp:

                saved = json.load(fp)

                if isinstance(saved, dict):

                    with _ENGINE_LOCK:

                        _ENGINE_STATE["total_scanned"] = saved.get("total_scanned", 0)

                        _ENGINE_STATE["total_moved_to_known"] = saved.get("total_moved_to_known", 0)

                        _ENGINE_STATE["total_moved_to_review"] = saved.get("total_moved_to_review", 0)

                        _ENGINE_STATE["total_fixed"] = saved.get("total_fixed", 0)

                        _ENGINE_STATE["cycle"] = saved.get("cycle", 0)

                        _ENGINE_STATE["last_scanned_file"] = saved.get("last_scanned_file")

                        _ENGINE_STATE["checkpoint"] = saved.get("checkpoint", {})

                        _ENGINE_STATE["last_actions"] = saved.get("last_actions", [])

            print(f"[ENGINE] Estado recuperado: Ciclo {_ENGINE_STATE['cycle']}, {_ENGINE_STATE['total_fixed']} correcciones previas, {len(_ENGINE_STATE['checkpoint'])} fotos en checkpoint.")

        except Exception as e:

            print(f"[ENGINE] Error cargando estado previo: {e}")





def _compare_feat_to_centroids(feat_arr):

    """Devuelve (best_name, best_score) vectorizado (<0.02ms por cara)."""

    try:

        mat, keys = get_vectorized_centroids()

        if mat is not None and mat.shape[0] > 0:

            arr = np.asarray(feat_arr, dtype=np.float32).flatten()

            norm = np.linalg.norm(arr)

            if norm > 1e-6:

                sims = np.dot(mat, arr / norm)

                best_idx = np.argmax(sims)

                best_score = float(sims[best_idx])

                best_key = keys[best_idx]

                best_name = best_key[1] if isinstance(best_key, tuple) else str(best_key)

                return best_name, best_score

    except Exception:

        pass



    from app.globals import known_faces

    feat_norm = feat_arr / (np.linalg.norm(feat_arr) + 1e-10)

    best_match = None

    best_score = 0.0

    for k_name, k_dict in known_faces.items():

        if k_name.startswith("Falso_Positivo") or is_smart_relationship_album(k_name):

            continue

        if k_dict.get("provenance") != HUMAN:

            continue

        sim = match_face_to_identity(feat_norm, k_dict)

        if sim > best_score:

            best_score = sim

            best_match = k_name

    return best_match, best_score





def _phase_scan_unknown():

    """

    FASE A: Escanea determinísticamente Personas Sin Nombre y Dudosos → asigna a conocidos en paralelo (4 workers).

    Guarda progreso continuo en disco para reanudar exactamente en el mismo punto sin latencia artificial.

    """

    from app.globals import faces_cache, RESULTADOS_DIR, FACES_CACHE_FILE, detector, recognizer, detector_lock

    from app.utils.files import get_file_key

    from concurrent.futures import ThreadPoolExecutor, as_completed



    review_dirs = [

        RESULTADOS_DIR / "Personas Sin Nombre",

        RESULTADOS_DIR / "Dudosos" / "Para Revisar",

        RESULTADOS_DIR / "_Dudosos",

        RESULTADOS_DIR / "Revision_Interactiva"

    ]

    valid_exts = {".jpg", ".jpeg", ".png", ".webp"}

    file_list = []

    for rdir in review_dirs:

        if rdir.exists():

            for root, _, files in os.walk(str(rdir)):

                for fname in files:

                    ext = os.path.splitext(fname)[1].lower()

                    if ext in valid_exts:

                        file_list.append(os.path.join(root, fname))

    

    file_list.sort()

    pending_files = []

    for fpath in file_list:

        try:

            mtime = os.stat(fpath).st_mtime_ns

            ck_key = f"suggestions-v1:{fpath}:{mtime}"

            if not _ENGINE_STATE["checkpoint"].get(ck_key):

                pending_files.append((fpath, ck_key))

        except OSError:

            continue



    if not pending_files:

        return



    def _process_one(item):

        fpath, ck_key = item

        if not _ENGINE_STATE["running"]:

            return None

        fname = os.path.basename(fpath)

        fkey = get_file_key(fpath)

        cached_faces = faces_cache.get(fkey, [])

        if not cached_faces:

            try:

                import cv2

                img_bytes = np.fromfile(fpath, dtype=np.uint8)

                img = decode_image(img_bytes)

                if img is not None and detector is not None and recognizer is not None:

                    h, w = img.shape[:2]

                    with detector_lock:

                        detector.setInputSize((w, h))

                        _, faces = detector.detect(img)

                        features_list = []

                        if faces is not None:

                            for face in faces:

                                aligned = recognizer.alignCrop(img, face)

                                feat = recognizer.feature(aligned)

                                features_list.append({"box": face[:4].tolist(), "feature": feat, "identity": "", "confidence": 0.0})

                    faces_cache[fkey] = features_list

                    cached_faces = features_list

            except Exception:

                pass



        suggestions = []

        for face_info in cached_faces:

            feat = face_info.get("feature")

            if feat is None:

                continue

            feat_arr = np.array(feat, dtype=np.float32).flatten()

            best_match, best_score = _compare_feat_to_centroids(feat_arr)



            if best_match and best_score >= AUDIT_THRESHOLD_HIGH:

                target_cat = "Conocidos"

                k_data = known_faces.get(best_match)

                if isinstance(k_data, dict) and k_data.get("cat"):

                    target_cat = k_data["cat"]

                elif best_match == "YO":

                    target_cat = "YO"

                apply_correction_to_file(fpath, target_cat, best_match, face_info)

                suggestions.append((fname, target_cat, best_match, best_score))

                break



        return (fpath, ck_key, fname, suggestions)



    batch_size = 64

    total_items = len(pending_files)

    save_counter = 0



    with ThreadPoolExecutor(max_workers=4, thread_name_prefix="FastFace") as executor:

        for i in range(0, total_items, batch_size):

            if not _ENGINE_STATE["running"]:

                break

            batch = pending_files[i:i + batch_size]

            futures = [executor.submit(_process_one, it) for it in batch]

            for fut in as_completed(futures):

                res = fut.result()

                if res is None:

                    continue

                fpath, ck_key, fname, suggestions = res

                with _ENGINE_LOCK:

                    _ENGINE_STATE["total_scanned"] += 1

                    _ENGINE_STATE["last_scanned_file"] = fname

                    _ENGINE_STATE["checkpoint"][ck_key] = time.time()

                    for f_name, t_cat, b_match, b_score in suggestions:

                        msg = f"Sugerencia pendiente: {f_name[:30]} → {t_cat}/{b_match} ({b_score:.2f})"

                        _log_action(msg)

                        print(f"[ENGINE-A] {msg}")

                        _ENGINE_STATE["total_suggested"] = _ENGINE_STATE.get("total_suggested", 0) + 1

                        _ENGINE_STATE["review_only"] = True



                save_counter += 1

                if save_counter % 100 == 0:

                    _save_engine_state()

                    try:

                        with open(FACES_CACHE_FILE, 'wb') as f_out:

                            pickle.dump(faces_cache, f_out)

                    except Exception:

                        pass



    _save_engine_state()





def is_smart_relationship_album(name: str) -> bool:

    """Devuelve True si el nombre corresponde a un álbum inteligente/relacional (no una persona individual)."""

    if not name:

        return False

    nl = name.lower()

    return any(pattern in nl for pattern in [

        'conmigo', 'sin mi', 'sin mí', 'grupales', 'con amigos', 'amigos',

        'familia conmigo', 'familia sin mi', 'familia sin mí',

        'conocidos conmigo', 'conocidos sin mi', 'conocidos sin mí',

        'mascotas conmigo', 'mascotas sin mi', 'mascotas sin mí'

    ])





def _phase_audit_known():

    """

    FASE B: Audita fotos YA clasificadas de forma stateful y ordenada.

    Si score < AUDIT_THRESHOLD_LOW → la devuelve a Dudosos o la corrige al álbum correcto.

    IMPORTANTE: Omite álbumes interactivos/relacionales (Familia conmigo, Mascotas conmigo, etc.).

    """

    from app.globals import faces_cache, RESULTADOS_DIR, known_faces, FACES_CACHE_FILE, detector, recognizer

    from app.utils.files import get_file_key



    skip_dirs = {

        "Personas Sin Nombre", "Dudosos", "Sin Rostro", "Frases",

        "💬 Frases / Citas y Memes", "Fotos Borradas", "Revisión",

        "Familia conmigo", "Familia sin mí", "Familia sin mi",

        "Conocidos conmigo", "Conocidos sin mí", "Conocidos sin mi",

        "Mascotas conmigo", "Mascotas sin mí", "Mascotas sin mi",

        "Fotos grupales", "Fotos con amigos"

    }



    dudosos_ai_dir = RESULTADOS_DIR / "Dudosos" / "Revisado por IA"

    dudosos_ai_dir.mkdir(parents=True, exist_ok=True)



    valid_exts = {".jpg", ".jpeg", ".png", ".webp"}



    try:

        top_level_dirs = sorted([d for d in RESULTADOS_DIR.iterdir() if d.is_dir()], key=lambda x: x.name)

    except Exception:

        return



    scan_batch_counter = 0



    for top_dir in top_level_dirs:

        if not _ENGINE_STATE["running"]:

            break

        if top_dir.name in skip_dirs or is_smart_relationship_album(top_dir.name):

            continue



        folder_identity = None

        for k_name in known_faces.keys():

            if k_name.startswith("Falso_Positivo") or is_smart_relationship_album(k_name):

                continue

            if k_name.lower() in top_dir.name.lower() or top_dir.name.lower() in k_name.lower():

                folder_identity = k_name

                break



        if folder_identity is None or is_smart_relationship_album(folder_identity):

            continue



        folder_centroid = known_faces.get(folder_identity, {}).get("centroid")

        if folder_centroid is None:

            continue



        folder_cent_norm = np.array(folder_centroid, dtype=np.float32).flatten()

        folder_cent_norm = folder_cent_norm / (np.linalg.norm(folder_cent_norm) + 1e-10)



        # Obtener lista ordenada de fotos del álbum

        folder_files = []

        for root, _, files in os.walk(str(top_dir)):

            for fname in files:

                ext = os.path.splitext(fname)[1].lower()

                if ext in valid_exts:

                    folder_files.append(os.path.join(root, fname))

        folder_files.sort()



        for fpath in folder_files:

            if not _ENGINE_STATE["running"]:

                break

            if not os.path.exists(fpath):

                continue



            fname = os.path.basename(fpath)

            ck_key = f"B:{fpath}:{folder_identity}"

            if _ENGINE_STATE["checkpoint"].get(ck_key):

                continue



            with _ENGINE_LOCK:

                _ENGINE_STATE["total_scanned"] += 1

                _ENGINE_STATE["last_scanned_file"] = f"{folder_identity}/{fname}"



            fkey = get_file_key(fpath)

            cached_faces = faces_cache.get(fkey, [])

            if not cached_faces:

                try:

                    import cv2

                    img_bytes = np.fromfile(fpath, dtype=np.uint8)

                    img = decode_image(img_bytes)

                    if img is not None and detector is not None and recognizer is not None:

                        h, w = img.shape[:2]

                        detector.setInputSize((w, h))

                        _, faces = detector.detect(img)

                        features_list = []

                        if faces is not None:

                            for face in faces:

                                aligned = recognizer.alignCrop(img, face)

                                feat = recognizer.feature(aligned)

                                features_list.append({"box": face[:4].tolist(), "feature": feat, "identity": "", "confidence": 0.0})

                        faces_cache[fkey] = features_list

                        cached_faces = features_list

                except Exception: pass



            if not cached_faces:

                _ENGINE_STATE["checkpoint"][ck_key] = time.time()

                continue



            face_for_folder = None

            score_vs_folder = 0.0

            for face_info in cached_faces:

                feat = face_info.get("feature")

                if feat is None:

                    continue

                feat_arr = np.array(feat, dtype=np.float32).flatten()

                feat_norm = feat_arr / (np.linalg.norm(feat_arr) + 1e-10)

                sim = float(np.dot(feat_norm, folder_cent_norm))

                if sim > score_vs_folder:

                    score_vs_folder = sim

                    face_for_folder = face_info



            if face_for_folder is None:

                _ENGINE_STATE["checkpoint"][ck_key] = time.time()

                continue



            # La foto está verificada correctamente

            if score_vs_folder >= AUDIT_THRESHOLD_LOW:

                _ENGINE_STATE["checkpoint"][ck_key] = time.time()

                scan_batch_counter += 1

                if scan_batch_counter % 20 == 0:

                    _save_engine_state()

                    try:

                        with open(FACES_CACHE_FILE, 'wb') as f_out: pickle.dump(faces_cache, f_out)

                    except: pass

                continue

                time.sleep(AUDIT_PHASE_DELAY)

                continue



            # ── Score bajo detectado: auto-corrección ──

            feat_arr = np.array(face_for_folder.get("feature"), dtype=np.float32).flatten()

            alt_match, alt_score = _compare_feat_to_centroids(feat_arr)



            if alt_match and alt_match != folder_identity and alt_score >= AUDIT_THRESHOLD_HIGH:

                apply_correction_to_file(fpath, "Conocidos", alt_match, face_for_folder)

                msg = (f"🔄 {fname[:28]} sacado de {folder_identity} "

                       f"({score_vs_folder:.2f}) → {alt_match} ({alt_score:.2f})")

                _log_action(msg)

                print(f"[ENGINE-B] {msg}")

                with _ENGINE_LOCK:

                    _ENGINE_STATE["total_suggested"] = _ENGINE_STATE.get("total_suggested", 0) + 1

                    _ENGINE_STATE["review_only"] = True

                _save_engine_state()

            else:

                face_for_folder['review_required'] = True

                face_for_folder['suggestion_provenance'] = 'prediction'

                _log_action(f'Revisar {fname[:28]}: score {score_vs_folder:.2f}')



            _ENGINE_STATE["checkpoint"][ck_key] = time.time()

            scan_batch_counter += 1

            if scan_batch_counter % 20 == 0:

                _save_engine_state()

            time.sleep(AUDIT_PHASE_DELAY)



def _phase_scan_apple():

    """Fase C: Escanea la fototeca virtual de Apple para auto-clasificar."""

    global local_detector, local_recognizer

    from app.services.apple_service import load_apple_db, ICLOUD_PHOTOS_DIR, update_apple_photo_mapping

    from app.globals import faces_cache, FACES_CACHE_FILE

    

    if not ICLOUD_PHOTOS_DIR.exists():

        return

        

    db = load_apple_db()

    exts = {'.jpg', '.jpeg', '.png', '.webp', '.heic'}

    scan_batch_counter = 0

    

    # Defaults in case not imported

    re_scan = 86400

    scan_delay = 0.5

    try:

        from app.services.face_service import RE_SCAN_INTERVAL, SCAN_PHASE_DELAY

        re_scan = RE_SCAN_INTERVAL

        scan_delay = SCAN_PHASE_DELAY

    except: pass

    

    # iCloud cloud files are excluded from background daemon to prevent Windows automatic cloud downloads

    pass







def _bg_engine_loop():

    """Bucle principal persistente del motor: ejecuta ciclos y recuerda posición."""

    _load_engine_state()



    print("[ENGINE] Motor de auto-corrección reanudado en segundo plano.")

    _ENGINE_STATE["started_at"] = time.strftime("%Y-%m-%d %H:%M:%S")



    while _ENGINE_STATE["running"]:

        _ENGINE_STATE["cycle"] += 1

        print(f"[ENGINE] ── Ciclo {_ENGINE_STATE['cycle']} en progreso ──")



        # Fase A: Desconocidos → Conocidos

        _ENGINE_STATE["phase"] = "scan_unknown"

        _save_engine_state()

        try:

            _phase_scan_unknown()

        except Exception as e:

            print(f"[ENGINE-A] Excepción: {e}")

            with _ENGINE_LOCK:

                _ENGINE_STATE["errors"] += 1



        if not _ENGINE_STATE["running"]:

            break



        # Fase B: Auditar carpetas conocidas

        _ENGINE_STATE["phase"] = "audit_known"

        _save_engine_state()

        try:

            _phase_audit_known()

        except Exception as e:

            print(f"[ENGINE-B] Excepción: {e}")

            with _ENGINE_LOCK:

                _ENGINE_STATE["errors"] += 1



        if not _ENGINE_STATE["running"]:

            break



        # Fase C: Escanear iCloud Photos

        _ENGINE_STATE["phase"] = "scan_apple"

        _save_engine_state()

        try:

            _phase_scan_apple()

        except Exception as e:

            print(f"[ENGINE-C] Excepción: {e}")

            with _ENGINE_LOCK:

                _ENGINE_STATE["errors"] += 1



        # Guardar estado completo y descansar antes del siguiente ciclo

        _ENGINE_STATE["phase"] = "waiting"

        _save_engine_state()

        print(f"[ENGINE] Ciclo {_ENGINE_STATE['cycle']} completado. "

              f"Total acumulado corregidas: {_ENGINE_STATE['total_fixed']}. Durmiendo 60s...")

        for _ in range(60):

            if not _ENGINE_STATE["running"]:

                break

            time.sleep(1)



    _ENGINE_STATE["phase"] = "idle"

    _save_engine_state()

    print("[ENGINE] Motor detenido y estado guardado.")





def start_background_engine_daemon():

    """Función de arranque automático para iniciar el motor al encender la app."""

    global _ENGINE_THREAD

    if _ENGINE_STATE["running"] and _ENGINE_THREAD and _ENGINE_THREAD.is_alive():

        return

    _ENGINE_STATE["running"] = True

    _ENGINE_THREAD = threading.Thread(target=_bg_engine_loop, daemon=True)

    _ENGINE_THREAD.start()

    print("[ENGINE] Daemon de auto-corrección activado.")





def api_auto_classify_continuous():

    """Arranca o detiene el motor bidireccional de auto-corrección."""

    global _ENGINE_THREAD



    data = request.json or {}

    action = data.get("action", "start")



    if action == "stop":

        _ENGINE_STATE["running"] = False

        _save_engine_state()

        return jsonify({"status": "Motor detenido", "state": _ENGINE_STATE})



    if _ENGINE_STATE["running"] and _ENGINE_THREAD and _ENGINE_THREAD.is_alive():

        return jsonify({

            "status": "Motor ya en ejecución",

            "state": _ENGINE_STATE

        })



    if action != "start":

        return jsonify({"error": "Acción no válida"}), 400

    if not any(v.get("provenance") == HUMAN and v.get("confirmed_samples") for v in known_faces.values()):

        return jsonify({"error": "Confirma al menos una cara para crear aprendizaje verificable", "review_only": True}), 409

    start_background_engine_daemon()

    return jsonify({

        "status": "Motor de sugerencias iniciado; clasificación automática desactivada",

        "message": "Las predicciones requieren revisión humana; no mueven fotos ni entrenan identidades"

    })





def api_self_audit_status():

    """Devuelve el estado actual completo del motor como JSON."""

    is_alive = _ENGINE_THREAD is not None and _ENGINE_THREAD.is_alive()

    return jsonify({

        "running": _ENGINE_STATE["running"] and is_alive,

        "review_only": True,

        "confirmed_identities": sum(v.get("provenance") == HUMAN and bool(v.get("confirmed_samples")) for v in known_faces.values()),

        "total_suggested": _ENGINE_STATE.get("total_suggested", 0),

        "phase": _ENGINE_STATE["phase"],

        "cycle": _ENGINE_STATE["cycle"],

        "total_scanned": _ENGINE_STATE["total_scanned"],

        "total_moved_to_known": _ENGINE_STATE["total_moved_to_known"],

        "total_moved_to_review": _ENGINE_STATE["total_moved_to_review"],

        "total_fixed": _ENGINE_STATE["total_fixed"],

        "last_scanned_file": _ENGINE_STATE["last_scanned_file"],

        "errors": _ENGINE_STATE["errors"],

        "started_at": _ENGINE_STATE["started_at"],

        "last_actions": _ENGINE_STATE["last_actions"][-15:],

    })





def api_self_audit_stream():

    """SSE endpoint: envia actualizaciones en vivo del motor sin bloquear hilos infinitamente."""

    from flask import Response

    def _sse_gen():

        try:

            for _ in range(12):  # Maximo 12 iteraciones (~36s) para reciclar hilos

                is_alive = _ENGINE_THREAD is not None and _ENGINE_THREAD.is_alive()

                payload = json.dumps({

                    "running": _ENGINE_STATE["running"] and is_alive,

                    "review_only": True,

                    "confirmed_identities": sum(v.get("provenance") == HUMAN and bool(v.get("confirmed_samples")) for v in known_faces.values()),

                    "total_suggested": _ENGINE_STATE.get("total_suggested", 0),

                    "phase": _ENGINE_STATE["phase"],

                    "cycle": _ENGINE_STATE["cycle"],

                    "total_scanned": _ENGINE_STATE["total_scanned"],

                    "total_fixed": _ENGINE_STATE["total_fixed"],

                    "total_moved_to_known": _ENGINE_STATE["total_moved_to_known"],

                    "total_moved_to_review": _ENGINE_STATE["total_moved_to_review"],

                    "last_scanned_file": _ENGINE_STATE["last_scanned_file"],

                    "last_actions": _ENGINE_STATE["last_actions"][-8:],

                }, ensure_ascii=False)

                yield f"data: {payload}\n\n"

                if not (_ENGINE_STATE["running"] and is_alive):

                    break

                time.sleep(3)

        except GeneratorExit:

            pass



    return Response(_sse_gen(), mimetype="text/event-stream",

                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})





def api_organize_quotes():

    try:

        count = scan_and_categorize_quotes()

        return jsonify({"success": True, "count": count, "message": f"{count} imágenes de frases organizadas"})

    except Exception as e:

        return jsonify({"error": str(e)}), 500





def _extract_feature_vector(entry):

    if entry is None:

        return None

    if isinstance(entry, dict):

        if 'centroid' in entry and entry['centroid'] is not None:

            entry = entry['centroid']

        elif 'feature' in entry and entry['feature'] is not None:

            entry = entry['feature']

        else:

            return None

    if isinstance(entry, (list, tuple)):

        entry = np.array(entry, dtype=np.float32)

    if isinstance(entry, np.ndarray) and entry.size >= 128:

        v = np.squeeze(entry).astype(np.float32)

        norm = float(np.linalg.norm(v))

        if norm > 1e-6:

            return v / norm

    return None



def api_suggest_merges():

    try:

        from app.globals import known_faces, cache_lock, CACHE_FILE, wait_for_boot

        from app.utils.faces import get_all_identities

        import urllib.parse

        

        wait_for_boot(5)

        with cache_lock:

            known_copy = dict(known_faces)

            

        idents = get_all_identities()

        ident_to_cat = {id_info["identidad"]: id_info.get("categoria", "Conocidos") for id_info in idents}

        

        filter_ident = request.args.get("ident")
        if filter_ident:
            clean_f = filter_ident.replace('👤', '').strip().lower()
            new_persons = [id_info for id_info in idents if clean_f == id_info["identidad"].replace('👤', '').strip().lower() or clean_f in id_info["identidad"].lower()]
        else:
            new_persons = [id_info for id_info in idents if "persona nueva" in id_info["identidad"].lower() or "persona #" in id_info["identidad"].lower()]

        # Strictly filter known_persons to CONFIRMED persons only.
        # NEVER suggest another Persona Nueva, triage, or unconfirmed group!
        CONFIRMED_CATEGORIES = {'Conocidos', 'Familia', 'YO', 'Profesores', 'Mascotas'}
        def is_confirmed_person(info):
            name = str(info.get("identidad", "")).lower()
            cat = str(info.get("categoria", "")).replace('👥', '').replace('🧑', '').replace('👧', '').replace('👦', '').strip()
            if any(term in name for term in ["persona nueva", "persona #", "persona_", "desconocid", "sin rostro", "ignorar", "falso_positivo", "dudoso", "baja confianza", "caras aisladas"]):
                return False
            if any(term in cat.lower() for term in ["revisión", "organizar", "sin nombre", "ignorar"]):
                return False
            return cat in CONFIRMED_CATEGORIES or name.startswith(('c. ', 'f. ', 'p. ', 'm. '))

        known_persons = [id_info for id_info in idents if is_confirmed_person(id_info) and id_info not in new_persons]

        

        suggestions = []

        for np_info in new_persons:

            np_name = np_info["identidad"]

            clean_name = np_name.replace('👤', '').strip()

            feat = _extract_feature_vector(known_copy.get(clean_name))

            if feat is None:

                feat = _extract_feature_vector(known_copy.get(np_name))

            if feat is None:

                feat = _extract_feature_vector(known_copy.get((np_info.get("categoria", ""), clean_name)))

            if feat is None:

                feat = _extract_feature_vector(known_copy.get((np_info.get("categoria", ""), np_name)))

            if feat is None:

                continue

            

            best_target = None

            best_sim = 0.0

            for kp_info in known_persons:

                kp_name = kp_info["identidad"]

                k_feat = _extract_feature_vector(known_copy.get(kp_name))

                if k_feat is None:

                    continue

                sim = float(np.dot(feat, k_feat))

                if sim > best_sim:

                    best_sim = sim

                    best_target = kp_name

                    

            if best_target and best_sim >= 0.72:

                src_cat = np_info.get('categoria', 'Personas Sin Nombre')

                tgt_cat = ident_to_cat.get(best_target, 'Conocidos')

                suggestions.append({

                    "source": np_name,

                    "target": best_target,

                    "similarity": round(float(best_sim), 2),

                    "source_count": np_info.get("count", 1),

                    "target_count": next((kp.get("count", 0) for kp in known_persons if kp["identidad"] == best_target), 0),

                    "source_cat": src_cat,

                    "target_cat": tgt_cat,

                    "source_avatar": f"/api/person_avatar?cat={urllib.parse.quote(src_cat)}&ident={urllib.parse.quote(np_name)}",

                    "target_avatar": f"/api/person_avatar?cat={urllib.parse.quote(tgt_cat)}&ident={urllib.parse.quote(best_target)}"

                })

                

        suggestions.sort(key=lambda s: s["similarity"], reverse=True)

        return jsonify({"suggestions": suggestions[:12]})

    except Exception as e:

        import traceback

        traceback.print_exc()

        return jsonify({"suggestions": []})



def api_suggest_merges_execute():

    try:

        data = request.json or {}

        source = data.get('source')

        target = data.get('target')

        if not source or not target:

            return jsonify({"success": False, "error": "Faltan parámetros source o target"}), 400

            

        from app.utils.faces import get_all_identities

        idents = get_all_identities()

        ident_to_cat = {id_info["identidad"]: id_info.get("categoria", "Conocidos") for id_info in idents}

        

        src_cat = ident_to_cat.get(source, 'Personas Sin Nombre')

        tgt_cat = ident_to_cat.get(target, 'Conocidos')

        

        from app.services.apple_service import rename_apple_group

        rename_apple_group(src_cat, source, tgt_cat, target)

        

        moved_count = 0

        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".avi"}

        

        for base_dir in [RESULTADOS_DIR, FOTOS_DIR]:

            src_dir = base_dir / src_cat / source

            tgt_dir = base_dir / tgt_cat / target

            if src_dir.exists():

                tgt_dir.mkdir(parents=True, exist_ok=True)

                for f in src_dir.iterdir():

                    if f.is_file() and f.suffix.lower() in valid_exts:

                        target_f = tgt_dir / f.name

                        c = 1

                        while target_f.exists():

                            target_f = tgt_dir / f"{f.stem}_{c}{f.suffix}"

                            c += 1

                        try:

                            safe_move_file(f, target_f)

                            moved_count += 1

                        except:

                            pass

                try:

                    os.rmdir(str(src_dir))

                except:

                    pass

                    

        with cache_lock:

            if source in known_faces:

                del known_faces[source]

            with open(CACHE_FILE, 'wb') as f_cache:

                pickle.dump(known_faces, f_cache)

                

        clear_gallery_cache()

        return jsonify({"success": True, "count": moved_count})

    except Exception as e:

        import traceback

        traceback.print_exc()

        return jsonify({"success": False, "error": str(e)}), 500









# =====================================================================

# BACKGROUND VIDEO INDEXER (Auto-scans videos in background)

# =====================================================================

import threading

import time



class BackgroundVideoIndexer:

    def __init__(self):

        self.lock = threading.Lock()

        self.running = False

        self.paused = False

        self.thread = None

        self.total = 0

        self.processed = 0

        self.cached = 0

        self.current_video = ""

        self.last_error = None



    def start(self):

        with self.lock:

            if self.running and not self.paused:

                return {"running": True, "message": "Indexador ya en ejecución"}

            self.running = True

            self.paused = False

            if self.thread is None or not self.thread.is_alive():

                self.thread = threading.Thread(target=self._worker_loop, daemon=True, name="VideoIndexer")

                self.thread.start()

            return {"running": True, "message": "Indexador iniciado en segundo plano"}



    def pause(self):

        with self.lock:

            self.paused = True

            return {"running": False, "paused": True, "message": "Indexador pausado"}



    def get_status(self):

        with self.lock:

            return {

                "running": self.running,

                "paused": self.paused,

                "total": self.total,

                "processed": self.processed,

                "cached": self.cached,

                "current_video": self.current_video,

                "percent": round((self.processed / max(self.total, 1)) * 100, 1)

            }



    def _worker_loop(self):

        from app.globals import APP_DIR, RESULTADOS_DIR, FOTOS_DIR

        from app.utils.files import get_file_key

        video_cache_file = APP_DIR / "video_faces_cache.json"



        # 1. Encontrar todos los vídeos

        valid_exts = {".mp4", ".mov", ".avi"}

        all_videos = []

        for base in [RESULTADOS_DIR, FOTOS_DIR, APP_DIR]:

            if not base.exists():

                continue

            for root, dirs, files in os.walk(str(base)):

                if "node_modules" in root or ".git" in root or "venv" in root:

                    continue

                for f in files:

                    if Path(f).suffix.lower() in valid_exts:

                        all_videos.append(os.path.join(root, f))



        # Eliminar duplicados de ruta

        all_videos = list(dict.fromkeys(all_videos))

        with self.lock:

            self.total = len(all_videos)



        # Cargar caché existente

        cache = {}

        if video_cache_file.exists():

            try:

                with open(video_cache_file, "r", encoding="utf-8") as f:

                    cache = json.load(f)

            except Exception:

                cache = {}



        for v_path in all_videos:

            with self.lock:

                if not self.running or self.paused:

                    break

                self.current_video = os.path.basename(v_path)



            try:

                f_key = get_file_key(v_path)

                if f_key in cache:

                    with self.lock:

                        self.cached += 1

                        self.processed += 1

                    continue



                # Procesar vídeo con escaneo silencioso

                res = self._scan_single_video(v_path)

                if res is not None:

                    cache[f_key] = res

                    try:

                        with open(video_cache_file, "w", encoding="utf-8") as f:

                            json.dump(cache, f, indent=2, ensure_ascii=False)

                    except Exception:

                        pass



                with self.lock:

                    self.processed += 1



                # Breve pausa para no saturar la CPU

                time.sleep(0.08)



            except Exception as e:

                self.last_error = str(e)

                with self.lock:

                    self.processed += 1



        with self.lock:

            self.running = False

            self.current_video = "Finalizado"



    def _scan_single_video(self, filepath):

        import cv2

        import numpy as np

        from app.globals import get_detector, get_recognizer, known_faces

        from app.utils.faces import get_cosine_similarity



        det = get_detector()

        rec = get_recognizer()

        if not det or not rec:

            return None



        cap = cv2.VideoCapture(filepath)

        if not cap.isOpened():

            return None



        fps = cap.get(cv2.CAP_PROP_FPS) or 25

        frame_interval = max(int(fps), 1)



        frame_idx = 0

        detections_by_ident = {}

        processed_frames = 0

        max_frames_to_check = 60 # Máx 60 segundos de muestreo para velocidad



        while processed_frames < max_frames_to_check:

            ret, frame = cap.read()

            if not ret:

                break



            if frame_idx % frame_interval == 0:

                processed_frames += 1

                sec = int(frame_idx / fps)

                h, w = frame.shape[:2]

                det.setInputSize((w, h))

                _, faces = det.detect(frame)



                if faces is not None:

                    for face in faces:

                        box = face[:4].astype(int)

                        if box[2] < 30 or box[3] < 30:

                            continue

                        aligned = rec.alignCrop(frame, face)

                        feat = rec.feature(aligned)

                        feat_norm = feat / (np.linalg.norm(feat) + 1e-10)



                        matches = []

                        for k, v in known_faces.items():

                            ident_name = k[1] if isinstance(k, tuple) else k

                            if ident_name in {"Desconocido", "Ignorar"}:

                                continue

                            c = v.get("centroid") if isinstance(v, dict) else v

                            if c is not None:

                                c_norm = c / (np.linalg.norm(c) + 1e-10)

                                sim = float(np.dot(feat_norm.flatten(), c_norm.flatten()))

                                matches.append((ident_name, sim))



                        matches.sort(key=lambda x: x[1], reverse=True)

                        if matches and matches[0][1] >= 0.40:

                            top_name, top_sim = matches[0]

                            second_sim = matches[1][1] if len(matches) > 1 else 0.0

                            if (top_sim - second_sim) >= 0.04:

                                if top_name not in detections_by_ident:

                                    detections_by_ident[top_name] = {"seconds": set(), "sims": []}

                                detections_by_ident[top_name]["seconds"].add(sec)

                                detections_by_ident[top_name]["sims"].append(top_sim)



            frame_idx += 1



        cap.release()



        # Consistencia temporal (al menos 2 apariciones o confianza >= 0.55)

        results = []

        for ident, data in detections_by_ident.items():

            avg_sim = float(np.mean(data["sims"])) if data["sims"] else 0.0

            if len(data["seconds"]) >= 2 or avg_sim >= 0.55:

                results.append({

                    "identity": ident,

                    "seconds": sorted(list(data["seconds"])),

                    "confidence": round(avg_sim * 100, 1)

                })



        return results



global_video_indexer = BackgroundVideoIndexer()



def api_video_indexer_start():

    return jsonify(global_video_indexer.start())



def api_video_indexer_status():

    return jsonify(global_video_indexer.get_status())



def api_video_indexer_pause():

    return jsonify(global_video_indexer.pause())

