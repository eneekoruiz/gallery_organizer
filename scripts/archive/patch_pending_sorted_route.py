import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

if "@app.route('/api/pending_sorted')" not in content:
    content = content.replace("def api_pending_sorted():", "@app.route('/api/pending_sorted')\ndef api_pending_sorted():")
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed missing route decorator")
else:
    print("Decorator already exists")
