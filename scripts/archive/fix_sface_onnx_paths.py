import os, shutil

# 1. Copy SFace model fallbacks
src_sface = os.path.join('models', 'face_recognition_sface.onnx')
if os.path.exists(src_sface):
    shutil.copy(src_sface, 'face_recognition_sface_2021dec.onnx')
    shutil.copy(src_sface, os.path.join('models', 'face_recognition_sface_2021dec.onnx'))
    print("Created SFace fallback ONNX copies")

# 2. Fix all python scripts
files_to_fix = ['auto_merge.py', 'recluster.py', 'smart_clean_worker.py']
for fname in files_to_fix:
    if os.path.exists(fname):
        with open(fname, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        content = content.replace('face_recognition_sface_2021dec.onnx', 'models/face_recognition_sface.onnx')
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {fname}")
