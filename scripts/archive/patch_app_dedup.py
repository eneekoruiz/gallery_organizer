import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_gallery_route = """@app.route('/api/gallery')
def get_gallery():
    gallery = {}
    valid_exts = {".jpg", ".jpeg", ".png", ".mp4", ".mov", ".avi"}
    seen_files = {}
    
    def scan_dir(base_dir, source_label):
        if not base_dir.exists(): return
        for root, dirs, files in os.walk(str(base_dir)):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in valid_exts:
                    path_obj = Path(root) / file
                    try:
                        rel_path = path_obj.relative_to(base_dir)
                        parts = rel_path.parts
                        if len(parts) >= 2:
                            cat = parts[0]
                            ident = parts[1]
                            
                            key = (cat, ident, file)
                            is_dudoso = "_Dudosos" in str(path_obj)
                            
                            if key in seen_files:
                                existing = seen_files[key]
                                if source_label not in existing["source"]:
                                    existing["source"] = f"{existing['source']} + {source_label}"
                            else:
                                item = {
                                    "path": str(path_obj),
                                    "name": file,
                                    "status": "Dudoso" if is_dudoso else "Clasificado",
                                    "source": source_label,
                                    "type": "video" if ext in [".mp4", ".mov", ".avi"] else "image"
                                }
                                seen_files[key] = item
                    except Exception:
                        pass
                        
    scan_dir(FOTOS_DIR, "Manual")
    scan_dir(RESULTADOS_DIR, "IA")
    
    for (cat, ident, filename), item in seen_files.items():
        if cat not in gallery: gallery[cat] = {}
        if ident not in gallery[cat]: gallery[cat][ident] = []
        gallery[cat][ident].append(item)
        
    return jsonify(gallery)
"""

idx_start = content.find("@app.route('/api/gallery')")
idx_end = content.find("@app.route('/api/metadata')", idx_start)

content = content[:idx_start] + new_gallery_route + "\n\n" + content[idx_end:]

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("app.py actualizado con deduplicación de galería por clave (cat, ident, filename).")
