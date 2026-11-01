import os

files_to_fix = ['auto_merge.py', 'recluster.py', 'smart_clean_worker.py']
target_str = 'face_detection_yunet_2023mar.onnx'

for fname in files_to_fix:
    if os.path.exists(fname):
        with open(fname, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        if target_str in content:
            # Replace any occurrence of the target filename with the relative path to models/face_detection_yunet.onnx
            content = content.replace(target_str, 'models/face_detection_yunet.onnx')
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f'Successfully updated {fname}')
