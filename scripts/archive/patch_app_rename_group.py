import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

rename_group_code = """@app.route('/api/rename_group', methods=['POST'])
def api_rename_group():
    data = request.json
    cat = data.get('cat')
    ident = data.get('ident')
    new_name = data.get('new_name')
    new_cat = data.get('new_cat', 'Conocidos')
    
    if not cat or not ident or not new_name:
        return jsonify({"error": "Parámetros insuficientes"}), 400
        
    src_dir = RESULTADOS_DIR / cat / ident
    if not src_dir.exists():
        return jsonify({"error": "Carpeta de grupo no encontrada"}), 404
        
    target_dir = RESULTADOS_DIR / new_cat / new_name
    target_dir.mkdir(parents=True, exist_ok=True)
    
    moved_count = 0
    valid_exts = {".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi"}
    
    for file_path in src_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in valid_exts:
            target_file = target_dir / file_path.name
            counter = 1
            while target_file.exists():
                target_file = target_dir / f"{file_path.stem}_{counter}{file_path.suffix}"
                counter += 1
            try:
                os.link(str(file_path), str(target_file))
                os.remove(str(file_path))
                moved_count += 1
            except:
                try:
                    import shutil
                    shutil.move(str(file_path), str(target_file))
                    moved_count += 1
                except:
                    pass
                    
    try:
        os.rmdir(str(src_dir))
    except:
        pass
        
    return jsonify({"success": True, "count": moved_count})
"""

idx = content.find("@app.route('/api/correct'")
head = content[:idx]
new_content = head + rename_group_code + "\n\n" + content[idx:]

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("app.py actualizado con endpoint /api/rename_group.")
