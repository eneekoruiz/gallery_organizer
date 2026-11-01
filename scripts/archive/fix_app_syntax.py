import sys

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Clean up app.py imports
content = "".join(lines)

# Fix Response import
if 'from flask import' in content and 'Response' not in content:
    content = content.replace('from flask import', 'from flask import Response,')

# Fix safe_file_helpers placement at top of file
safe_helpers = """
import gc, time, shutil, os

def safe_move_file(src, dst):
    src_str, dst_str = str(src), str(dst)
    gc.collect()
    for attempt in range(5):
        try:
            shutil.move(src_str, dst_str)
            return True
        except PermissionError:
            time.sleep(0.2)
            gc.collect()
    try:
        shutil.copy2(src_str, dst_str)
        try:
            os.remove(src_str)
        except:
            pass
        return True
    except Exception as e:
        raise e

def safe_remove_file(filepath):
    f_str = str(filepath)
    gc.collect()
    for attempt in range(5):
        try:
            os.remove(f_str)
            return True
        except PermissionError:
            time.sleep(0.2)
            gc.collect()
    return False
"""

# Re-read clean file from disk if needed, or remove broken indentation
clean_lines = []
skip = False
for line in lines:
    if 'import gc, time, shutil' in line:
        continue
    clean_lines.append(line)

content = "".join(clean_lines)

# Insert safe_helpers right after imports at top
import_end_idx = 0
for i, line in enumerate(clean_lines):
    if line.startswith('import ') or line.startswith('from '):
        import_end_idx = i

clean_lines.insert(import_end_idx + 1, safe_helpers + "\n")

content = "".join(clean_lines)
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed app.py imports and safe_helpers placement")
