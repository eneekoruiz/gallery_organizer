import sys, re

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# 1. Update app.py
with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

# Update /api/stats in app.py
new_stats_endpoint = """@app.route('/api/stats')
def api_stats():
    global _GALLERY_CACHE
    if _GALLERY_CACHE is None:
        get_gallery()
        
    total = 0
    manual_user = 0
    ia_verified = 0
    dudosos = 0
    pendientes = 0
    breakdown = {}
    
    overrides = load_overrides()
    
    for cat, idents in (_GALLERY_CACHE or {}).items():
        for ident, items in idents.items():
            count = len(items)
            total += count
            
            if cat == 'Personas Sin Nombre':
                pendientes += count
            elif '_Dudosos' in ident or cat == 'Revision_Interactiva':
                dudosos += count
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
    })"""

# Replace old api_stats in app.py
old_stats_pattern = r"@app\.route\('/api/stats'\)\s+def api_stats\(\):[\s\S]*?return jsonify\(\{[\s\S]*?\}\)"
app_code = re.sub(old_stats_pattern, new_stats_endpoint, app_code)

# Add /api/batch_move in app.py if not present
batch_move_code = """
@app.route('/api/batch_move', methods=['POST'])
def api_batch_move():
    data = request.json or {}
    files = data.get('files', [])
    target_cat = data.get('target_cat')
    target_ident = data.get('target_ident')
    
    if not files or not target_cat or not target_ident:
        return jsonify({"error": "Parametros incompletos"}), 400
        
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
                
                overrides[str(dest.resolve())] = {
                    "categoria": target_cat,
                    "identidad": target_ident,
                    "source": "Manual Batch Move"
                }
                
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
"""

if '/api/batch_move' not in app_code:
    app_code += "\n" + batch_move_code

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code)
print("Updated app.py with enhanced /api/stats and /api/batch_move!")
