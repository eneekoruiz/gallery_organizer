import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_block = """
        if target_path and _GALLERY_CACHE is not None:
            try:
                old_path_str = str(Path(current_filepath))
                removed_item = None
"""

new_block = """
        if target_path and _GALLERY_CACHE is not None:
            try:
                if current_filepath in faces_cache and str(target_path) != current_filepath:
                    faces_cache[str(target_path)] = faces_cache[current_filepath]
                    with open(FACES_CACHE_FILE, 'wb') as f:
                        import pickle
                        pickle.dump(faces_cache, f)
            except Exception as e:
                print("Error copying faces_cache to new path:", e)
                
            try:
                old_path_str = str(Path(current_filepath))
                removed_item = None
"""
if old_block in content:
    content = content.replace(old_block, new_block)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed api_correct faces_cache propagation")
else:
    print("Could not find block in api_correct")
