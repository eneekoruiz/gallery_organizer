import sys

with open('auto_merge.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix threshold to 0.68
content = content.replace('def run_auto_merge(threshold=0.85):', 'def run_auto_merge(threshold=0.68):')

# Fix cv2.imread
old_read = """        img = cv2.imread(path)
        if img is None: continue"""

new_read = """        try:
            file_bytes = np.fromfile(path, dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        except:
            img = None
        if img is None: continue"""

if old_read in content:
    content = content.replace(old_read, new_read)

with open('auto_merge.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched auto_merge.py threshold to 0.68 and fixed Unicode path reading")
