import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

bad_snippet = """import json
        with open('duplicate_groups.json', 'r') as df:"""

good_snippet = """    try:
        import json
        with open('duplicate_groups.json', 'r') as df:"""

if bad_snippet in content:
    content = content.replace(bad_snippet, good_snippet)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed missing try in app.py")
else:
    print("Could not find bad_snippet")
