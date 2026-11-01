import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

endpoint_code = '''
@app.route('/api/clear_confidence_cache', methods=['POST'])
def api_clear_confidence_cache():
    global _CONFIDENCE_CACHE
    _CONFIDENCE_CACHE = {}
    if CONFIDENCE_CACHE_FILE.exists():
        try:
            CONFIDENCE_CACHE_FILE.unlink()
        except: pass
    return jsonify({"success": True})

def save_confidence_cache():
'''

if 'def save_confidence_cache():' in content:
    content = content.replace('def save_confidence_cache():', endpoint_code.strip())
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Injected /api/clear_confidence_cache!")
else:
    print("Could not find save_confidence_cache")
