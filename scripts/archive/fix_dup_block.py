import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

bad_dup_block = """import json
        with open('duplicate_groups.json', 'r') as df:
            dup_data = json.load(df)
    except:
        pass"""

good_dup_block = """    try:
        with open('duplicate_groups.json', 'r') as df:
            dup_data = json.load(df)
    except:
        pass"""

if bad_dup_block in content:
    content = content.replace(bad_dup_block, good_dup_block)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed duplicate_groups block indentation")
else:
    print("Could not find bad_dup_block")
