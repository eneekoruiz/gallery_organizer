import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

thumbnail_logic = '''
import hashlib

THUMBNAILS_DIR = APP_DIR / ".thumbnails"
THUMBNAILS_DIR.mkdir(exist_ok=True)

def generate_thumbnail(original_path, max_size=400):
    try:
        path_str = str(original_path)
        path_hash = hashlib.md5(path_str.encode('utf-8')).hexdigest()
        thumb_path = THUMBNAILS_DIR / f"{path_hash}.webp"
        
        if thumb_path.exists():
            return str(thumb_path)
            
        is_video = path_str.lower().endswith((".mp4", ".mov", ".avi"))
        img = None
        
        if is_video:
            cap = cv2.VideoCapture(path_str)
            fc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if fc > 10: cap.set(cv2.CAP_PROP_POS_FRAMES, fc // 2)
            ret, frame = cap.read()
            if ret: img = frame
            cap.release()
        else:
            file_bytes = np.fromfile(path_str, dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            
        if img is None:
            return None
            
        # Resize maintaining aspect ratio
        h, w = img.shape[:2]
        if max(h, w) > max_size:
            scale = max_size / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
        # Save as webp for maximum compression and speed
        cv2.imwrite(str(thumb_path), img, [cv2.IMWRITE_WEBP_QUALITY, 60])
        return str(thumb_path)
    except Exception as e:
        print("Thumbnail Error:", e)
        return None

@app.route('/api/thumbnail')
def api_thumbnail():
    path_param = request.args.get('path')
    if not path_param:
        return "Falta path", 400
    
    thumb = generate_thumbnail(path_param)
    if thumb and os.path.exists(thumb):
        return send_file(thumb, mimetype='image/webp')
    
    # Fallback to original
    if os.path.exists(path_param):
        return send_file(path_param)
    return "No encontrado", 404

'''

# Inject right before the last if __name__ == '__main__'
if 'def api_thumbnail' not in content:
    content = content.replace("if __name__ == '__main__':", thumbnail_logic + "\nif __name__ == '__main__':")
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched /api/thumbnail!")
else:
    print("Already patched.")
