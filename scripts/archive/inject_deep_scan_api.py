import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

deep_scan_injection = """
@app.route('/api/detect_deep', methods=['POST'])
def detect_deep():
    data = request.json
    filepath = data.get('path')
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
        
    try:
        img = cv2.imread(filepath)
        if img is None:
            return jsonify({"error": "Could not read image"}), 400
            
        h, w = img.shape[:2]
        
        # Deep Scan: lower score threshold and NMS threshold
        # Default is 0.9, we drop it to 0.5 to find "hidden" faces
        try:
            deep_detector = cv2.FaceDetectorYN.create("face_detection_yunet_2023mar.onnx", "", (w, h), score_threshold=0.5, nms_threshold=0.3)
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
"""

if '@app.route(\'/api/detect_deep\'' not in content:
    content = content.replace("@app.route('/api/correct', methods=['POST'])", deep_scan_injection + "\n@app.route('/api/correct', methods=['POST'])")
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Injected deep scan route")
else:
    print("Already injected")
