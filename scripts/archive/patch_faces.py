import os

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_func = """    if should_garbage_collect:
        try:
            os.remove(str(orig_path))
        except Exception:
            try:
                with open(PENDING_DELETIONS_FILE, 'a') as f:
                    f.write(str(orig_path) + '\\n')
            except Exception:
                pass
            
    return str(target_path)"""

new_func = """    if should_garbage_collect:
        try:
            os.remove(str(orig_path))
        except Exception:
            try:
                with open(PENDING_DELETIONS_FILE, 'a') as f:
                    f.write(str(orig_path) + '\\n')
            except Exception:
                pass
                
    if str(target_path) != filepath and filepath in faces_cache:
        faces_cache[str(target_path)] = faces_cache.pop(filepath)
        try:
            with open(FACES_CACHE_FILE, 'wb') as f:
                pickle.dump(faces_cache, f)
        except Exception as e:
            print("Failed to save faces cache:", e)
            
    return str(target_path)"""

if old_func in content:
    content = content.replace(old_func, new_func)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated apply_correction_to_file logic successfully")
else:
    print("Failed to find old_func logic!")
