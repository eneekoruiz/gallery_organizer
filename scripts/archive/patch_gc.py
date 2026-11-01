import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove is_manual_source block
old_gc_cond = '''            if not other_faces_same_person:
                if not is_manual_source:
                    should_garbage_collect = True'''
new_gc_cond = '''            if not other_faces_same_person:
                should_garbage_collect = True'''
if old_gc_cond in content:
    content = content.replace(old_gc_cond, new_gc_cond)
    print("Patched GC condition")
else:
    print("Could not find GC condition")

# 2. Add to pending deletions if remove fails
old_remove = '''    if should_garbage_collect:
        try:
            os.remove(str(orig_path))
        except Exception:
            pass'''
new_remove = '''    if should_garbage_collect:
        try:
            os.remove(str(orig_path))
        except Exception:
            try:
                with open(PENDING_DELETIONS_FILE, 'a') as f:
                    f.write(str(orig_path) + '\\n')
            except Exception:
                pass'''
if old_remove in content:
    content = content.replace(old_remove, new_remove)
    print("Patched os.remove logic")
else:
    print("Could not find os.remove logic")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
