import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add time.sleep(0.01) to api_pending_sorted
import time_import_logic
time_import_logic = '''import time
'''
if 'import time' not in content:
    content = time_import_logic + content

old_loop_start = '''    for item in items_to_sort:
        filepath = item['path']'''

new_loop_start = '''    for item in items_to_sort:
        time.sleep(0.02)  # Yield GIL to prevent UI blocking during massive scan
        filepath = item['path']'''

if old_loop_start in content:
    content = content.replace(old_loop_start, new_loop_start)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched loop yield!")
else:
    print("Could not find the exact loop start string.")

