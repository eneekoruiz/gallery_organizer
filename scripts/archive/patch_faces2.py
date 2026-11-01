import os
import pickle

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_func = """        # Actualizar la caché de caras instantáneamente para la UI
        if filepath in faces_cache:
            for c_face in faces_cache[filepath]:
                c_box = [c_face['x'], c_face['y'], c_face['width'], c_face['height']]
                if iou(face_box, c_box) > 0.4:
                    c_face['identity'] = new_identidad
                    c_face['confidence'] = "100.0"
                    c_face['is_manual'] = True
                    break
            with open(FACES_CACHE_FILE, 'wb') as f:
                pickle.dump(faces_cache, f)"""

new_func = """        # Actualizar la caché de caras instantáneamente para la UI
        if filepath not in faces_cache:
            faces_cache[filepath] = []
            
        updated_cache = False
        for c_face in faces_cache[filepath]:
            c_box = [c_face['x'], c_face['y'], c_face['width'], c_face['height']]
            if iou(face_box, c_box) > 0.4:
                c_face['identity'] = new_identidad
                c_face['confidence'] = "100.0"
                c_face['is_manual'] = True
                updated_cache = True
                break
                
        if not updated_cache:
            faces_cache[filepath].append({
                'x': face_data['x'], 'y': face_data['y'],
                'width': face_data['width'], 'height': face_data['height'],
                'identity': new_identidad, 'confidence': "100.0", 'is_manual': True
            })
            
        try:
            with open(FACES_CACHE_FILE, 'wb') as f:
                pickle.dump(faces_cache, f)
        except Exception as e:
            print("Failed to save faces cache:", e)"""

if old_func in content:
    content = content.replace(old_func, new_func)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated apply_correction_to_file faces_cache logic successfully")
else:
    print("Failed to find old_func logic!")
