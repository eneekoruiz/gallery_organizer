import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

bad_block_2 = """    # Reaprendizaje Activo: Process identical duplicate bursts
    try:
        

def safe_move_file"""

good_block_2 = """    # Reaprendizaje Activo: Process identical duplicate bursts
    try:
        import json
        with open('duplicate_groups.json', 'r') as df:
            dup_map = json.load(df)
            if filepath in dup_map:
                g_id = dup_map[filepath]['group_id']
                files_to_process = [p for p, info in dup_map.items() if info['group_id'] == g_id]
    except:
        pass"""

if bad_block_2 in content:
    content = content.replace(bad_block_2, good_block_2)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed duplicate safe_move_file inside api_correct")
else:
    print("Could not find bad_block_2")
