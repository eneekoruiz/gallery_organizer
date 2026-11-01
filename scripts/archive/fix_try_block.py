import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

empty_try_block = """    dup_data = {}
    try:
        

def safe_move_file"""

fixed_block = """    dup_data = {}
    try:
        with open('duplicate_groups.json', 'r') as df:
            dup_data = json.load(df)
    except:
        pass

def safe_move_file"""

if empty_try_block in content:
    content = content.replace(empty_try_block, fixed_block)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed empty try block in app.py")
else:
    print("Could not find empty_try_block")
