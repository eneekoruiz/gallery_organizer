with open('app/services/gallery_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """    if not candidate_paths:
        return Response(default_svg, mimetype='image/svg+xml')"""

replacement = """    if not candidate_paths:
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
        return Response(default_svg, mimetype='image/svg+xml')"""

if target in content:
    content = content.replace(target, replacement, 1)
    with open('app/services/gallery_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS")
else:
    print("TARGET NOT FOUND")
