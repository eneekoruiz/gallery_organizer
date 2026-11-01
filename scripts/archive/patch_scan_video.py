import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

scan_video_endpoint = '''
@app.route('/api/scan_video', methods=['POST'])
def api_scan_video():
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
        
        # Scan 1 frame per second
        for sec in range(0, int(duration) + 1):
            target_frame = int(sec * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue
                
            h, w, _ = frame.shape
            detector.setInputSize((w, h))
            _, faces = detector.detect(frame)
            
            if faces is not None:
                for f in faces:
                    aligned = recognizer.alignCrop(frame, f)
                    feature = recognizer.feature(aligned)
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
        
        # Format results
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
'''

if '@app.route(\'/api/scan_video\'' not in content:
    content += '\n' + scan_video_endpoint
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added /api/scan_video endpoint")
else:
    print("Endpoint already exists")
