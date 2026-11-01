import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace api_person_avatar
old_code = """
        if face_box:
            x, y, w, h = int(face_box['x']), int(face_box['y']), int(face_box['width']), int(face_box['height'])
            # Expand box slightly for a better avatar
            pad_x = int(w * 0.2)
            pad_y = int(h * 0.2)
            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(img.shape[1], x + w + pad_x)
            y2 = min(img.shape[0], y + h + pad_y)
            cropped = img[y1:y2, x1:x2]
        else:
            # Fallback to center crop if no face box found
            h, w = img.shape[:2]
            sz = min(h, w)
            cropped = img[h//2 - sz//2 : h//2 + sz//2, w//2 - sz//2 : w//2 + sz//2]
            
        _, buf = cv2.imencode('.jpg', cropped)
"""

new_code = """
        cropped = None
        if face_box:
            try:
                x, y, w, h = int(face_box['x']), int(face_box['y']), int(face_box['width']), int(face_box['height'])
                pad_x = int(w * 0.2)
                pad_y = int(h * 0.2)
                x1 = max(0, x - pad_x)
                y1 = max(0, y - pad_y)
                x2 = min(img.shape[1], x + w + pad_x)
                y2 = min(img.shape[0], y + h + pad_y)
                if x2 > x1 and y2 > y1:
                    cropped = img[y1:y2, x1:x2]
            except:
                pass
                
        if cropped is None or cropped.size == 0:
            h, w = img.shape[:2]
            sz = min(h, w)
            cropped = img[h//2 - sz//2 : h//2 + sz//2, w//2 - sz//2 : w//2 + sz//2]
            if cropped.size == 0:
                return "Invalid dimensions", 400
                
        _, buf = cv2.imencode('.jpg', cropped)
"""
if old_code in content:
    content = content.replace(old_code, new_code)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed api_person_avatar 500 error")
else:
    print("Code not found for api_person_avatar fix")
