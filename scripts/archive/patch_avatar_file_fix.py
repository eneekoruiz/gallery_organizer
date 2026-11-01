import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_avatar_block = """    target_dir = RESULTADOS_DIR / cat / ident
    if not target_dir.exists():
        target_dir = FOTOS_DIR / cat / ident
        
    if not target_dir.exists():
        return jsonify({"error": "Persona not found"}), 404
        
    for f in target_dir.iterdir():"""

new_avatar_block = """    target_dir = RESULTADOS_DIR / cat / ident
    if not target_dir.exists():
        target_dir = FOTOS_DIR / cat / ident
        
    if not target_dir.exists():
        return jsonify({"error": "Persona not found"}), 404
        
    if target_dir.is_file():
        return send_file(str(target_dir))
        
    for f in target_dir.iterdir():"""

if old_avatar_block in content:
    content = content.replace(old_avatar_block, new_avatar_block)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched target_dir.is_file check in api_person_avatar in app.py")
else:
    print("Could not match old_avatar_block in app.py")
