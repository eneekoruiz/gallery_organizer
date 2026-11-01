import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Video Frame Reading in api_analyze
old_video_seek = """        if is_video:
            cap = cv2.VideoCapture(str(filepath))
            fps = cap.get(cv2.CAP_PROP_FPS)
            if timestamp_in is not None:
                timestamp = float(timestamp_in)
                cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
                ret, img = cap.read()
            else:
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                target_frame = 0
                if frame_count > 10:
                    target_frame = frame_count // 2
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                ret, img = cap.read()
                if fps > 0: timestamp = target_frame / fps
            cap.release()
            if not ret: return jsonify({"error": "Cannot read video"})"""

new_video_seek = """        if is_video:
            cap = cv2.VideoCapture(str(filepath))
            fps = cap.get(cv2.CAP_PROP_FPS)
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
                    ret, img = cap.read()
            else:
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                target_frame = 0
                if frame_count > 10:
                    target_frame = frame_count // 2
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                ret, img = cap.read()
                if fps > 0: timestamp = target_frame / fps
            cap.release()
            if not ret or img is None: return jsonify({"error": "Cannot read video frame"})"""

content = content.replace(old_video_seek, new_video_seek)

# 2. Update api_rename_group to support centroid retraining
old_rename_end = """    try:
        os.rmdir(str(src_dir))
    except:
        pass
        
    return jsonify({"success": True, "count": moved_count})"""

new_rename_end = """    try:
        os.rmdir(str(src_dir))
    except:
        pass

    # Reaprendizaje Activo de la Persona (Actualización de Centroide en Caché)
    try:
        new_feats = []
        for file_path in target_dir.iterdir():
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
                
            with open(CACHE_FILE, 'wb') as f_cache:
                pickle.dump(known_faces, f_cache)
    except Exception as ex_retrain:
        print(f"Aviso de reentrenamiento: {ex_retrain}")
        
    return jsonify({"success": True, "count": moved_count})"""

content = content.replace(old_rename_end, new_rename_end)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("app.py actualizado: decodificación fiable de fotogramas de vídeo y reentrenamiento IA en api_rename_group.")
