import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the stray decorator
bad_str = "@app.route('/api/pending_sorted')\n@app.route('/api/start_smart_clean', methods=['POST'])"
good_str = "@app.route('/api/start_smart_clean', methods=['POST'])"

if bad_str in content:
    content = content.replace(bad_str, good_str)
    
if "def api_pending_sorted():" in content and "@app.route('/api/pending_sorted')" not in content:
    content = content.replace("def api_pending_sorted():", "@app.route('/api/pending_sorted')\ndef api_pending_sorted():")
    
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed pending_sorted route")
