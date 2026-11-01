import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update /api/gallery scanning logic
old_gallery_code = """    def scan_dir(base_dir, source_label):
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
    scan_dir(RESULTADOS_DIR, "IA")"""

new_gallery_code = """    overrides = load_overrides()
    
    def scan_dir(base_dir, is_orig_dataset):
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
                            file_key = get_file_key(str(path_obj))
                            
                            # Determinación estricta de la etiqueta (Dataset vs Manual vs IA)
                            if is_orig_dataset:
                                label = "Dataset"
                            elif file_key in overrides and len(overrides[file_key]) > 0:
                                label = "Manual"
                            else:
                                label = "IA"
                                
                            if key in seen_files:
                                existing = seen_files[key]
                                if label not in existing["source"]:
                                    existing["source"] = f"{existing['source']} + {label}"
                            else:
                                item = {
                                    "path": str(path_obj),
                                    "name": file,
                                    "status": "Dudoso" if is_dudoso else "Clasificado",
                                    "source": label,
                                    "type": "video" if ext in [".mp4", ".mov", ".avi"] else "image"
                                }
                                seen_files[key] = item
                    except Exception:
                        pass
                        
    scan_dir(FOTOS_DIR, True)
    scan_dir(RESULTADOS_DIR, False)"""

content = content.replace(old_gallery_code, new_gallery_code)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("app.py actualizado con la lógica de etiquetado triple (Dataset, Manual, IA).")
