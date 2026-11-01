import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_avatar_lookup = """    if not face_box and first_img_path in faces_cache:
        for fc in faces_cache[first_img_path]:
            if fc.get('identity') == ident:
                face_box = fc
                break"""

new_avatar_lookup = """    if not face_box and first_img_path in faces_cache:
        for fc in faces_cache[first_img_path]:
            if fc.get('identity') == ident:
                face_box = fc
                break
        if not face_box and len(faces_cache[first_img_path]) > 0:
            face_box = faces_cache[first_img_path][0]"""

if old_avatar_lookup in content:
    content = content.replace(old_avatar_lookup, new_avatar_lookup)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched face_box fallback lookup in api_person_avatar")
else:
    print("Could not match old_avatar_lookup in app.py")
