import sys

with open('app.py', 'r', encoding='utf-8') as f:
    app_content = f.read()

bad_line = 'deep_detector = cv2.FaceDetectorYN.create("face_detection_yunet_2023mar.onnx", "", (w, h), score_threshold=0.5, nms_threshold=0.3)'
good_line = 'deep_detector = cv2.FaceDetectorYN.create(str(APP_DIR / "models" / "face_detection_yunet.onnx"), "", (w, h), score_threshold=0.5, nms_threshold=0.3)'

if bad_line in app_content:
    app_content = app_content.replace(bad_line, good_line)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(app_content)
    print("Patched deep_detector ONNX path")
else:
    print("Could not find the ONNX line")
