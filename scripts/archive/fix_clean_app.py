import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

bad_block_3 = """    try:
            try:
        import json
        with open('duplicate_groups.json', 'r') as df:
            dup_map = json.load(df)
            if filepath in dup_map:
                g_id = dup_map[filepath]['group_id']
                files_to_process = [p for p, info in dup_map.items() if info['group_id'] == g_id]
    except:
        pass
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
    return False"""

good_block_3 = """    try:
        import json
        with open('duplicate_groups.json', 'r') as df:
            dup_map = json.load(df)
            if filepath in dup_map:
                g_id = dup_map[filepath]['group_id']
                files_to_process = [p for p, info in dup_map.items() if info['group_id'] == g_id]
    except:
        pass"""

if bad_block_3 in content:
    content = content.replace(bad_block_3, good_block_3)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Cleaned up bad try block and internal safe_remove_file in app.py")
else:
    print("Could not find bad_block_3")
