import sys

with open('app.py', 'r', encoding='utf-8') as f:
    app_content = f.read()

# Inject num_faces calculation in get_gallery
old_item_str = """                                item = {
                                    "path": str(path_obj),
                                    "name": file,
                                    "status": "Dudoso" if is_dudoso else "Clasificado",
                                    "source": label,
                                    "type": "video" if ext in [".mp4", ".mov", ".avi"] else "image"
                                }"""

new_item_str = """                                abs_p = str(path_obj)
                                num_f = len(faces_cache.get(abs_p, []))
                                if num_f == 0 and file_key in overrides:
                                    num_f = len(overrides[file_key])
                                item = {
                                    "path": str(path_obj),
                                    "name": file,
                                    "status": "Dudoso" if is_dudoso else "Clasificado",
                                    "source": label,
                                    "type": "video" if ext in [".mp4", ".mov", ".avi"] else "image",
                                    "num_faces": num_f
                                }"""

if old_item_str in app_content:
    app_content = app_content.replace(old_item_str, new_item_str)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(app_content)
    print("Patched app.py with num_faces")
else:
    print("Could not find old_item_str in app.py")
