import sys, re

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

new_batch_move = """@app.route('/api/batch_move', methods=['POST'])
def api_batch_move():
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
        
        detector = cv2.FaceDetectorYN.create("models/face_detection_yunet_2023mar.onnx", "", (320, 320))
        recognizer = cv2.FaceRecognizerSF.create("models/face_recognition_sface_2021dec.onnx", "")
        
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
                    
                    file_k = str(dest.resolve())
                    overrides[file_k] = [{
                        'x': 0, 'y': 0, 'width': 0, 'height': 0,
                        'identity': target_ident
                    }]
                    
                    img = cv2.imread(str(dest))
                    if img is not None:
                        h, w = img.shape[:2]
                        detector.setInputSize((w, h))
                        _, faces = detector.detect(img)
                        if faces is not None and len(faces) > 0:
                            aligned = recognizer.alignCrop(img, faces[0])
                            feat = recognizer.feature(aligned)
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
                
        global _GALLERY_CACHE
        _GALLERY_CACHE = None
        
        return jsonify({
            "status": "success",
            "moved": moved_count,
            "retrained_faces": len(new_features)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500"""

old_batch_pattern = r"@app\.route\('/api/batch_move', methods=\['POST'\]\)[\s\S]*?return jsonify\(\{[\s\S]*?\}\)"
app_code = re.sub(old_batch_pattern, new_batch_move, app_code)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code)

print("✓ Fixed api_batch_move overrides format and added global exception handling!")
