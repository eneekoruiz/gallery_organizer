import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

bulk_endpoint = '''
@app.route('/api/correct_bulk', methods=['POST'])
def api_correct_bulk():
    data = request.json
    paths = data.get('paths', [])
    new_identity = data.get('new_identity', '')
    
    if not paths or not new_identity:
        return jsonify({"success": False, "error": "Faltan datos"})
        
    global _GALLERY_CACHE
    overrides = load_overrides()
    
    # Check if folder exists
    dest_dir = DATASET_DIR / new_identity
    if new_identity != 'Ignorar' and not dest_dir.exists():
        dest_dir.mkdir(parents=True, exist_ok=True)
        if _GALLERY_CACHE is not None and 'Conocidos' in _GALLERY_CACHE:
            if new_identity not in _GALLERY_CACHE['Conocidos']:
                _GALLERY_CACHE['Conocidos'][new_identity] = []
                
    success_count = 0
    for file_path in paths:
        try:
            # Add to overrides
            file_key = get_file_key(file_path)
            
            if file_key not in overrides:
                overrides[file_key] = []
                
            # Assume we only reassign the primary face (idx 0) for bulk actions 
            # or we reassign all faces in that image if it's a false positive etc.
            # But wait, usually bulk is used on images that have ONE main face, 
            # or the user wants to reassign the first face. Let's reassign idx 0.
            
            # Find if there is an override for face_idx 0
            idx_found = False
            for ov in overrides[file_key]:
                if ov['face_idx'] == 0:
                    ov['identity'] = new_identity
                    ov['is_manual'] = True
                    idx_found = True
                    break
            
            if not idx_found:
                overrides[file_key].append({
                    "face_idx": 0,
                    "identity": new_identity,
                    "is_manual": True
                })
                
            # If identity matches a known person, copy the image to their dataset folder
            # to reinforce learning (as requested by user previously)
            if new_identity != 'Ignorar' and new_identity != 'Desconocido' and not new_identity.startswith('IA '):
                src_path = Path(file_path)
                if src_path.exists():
                    dest_file = dest_dir / src_path.name
                    if not dest_file.exists():
                        shutil.copy2(src_path, dest_file)
            
            success_count += 1
        except Exception as e:
            print(f"Error bulk correcting {file_path}: {e}")
            
    save_overrides(overrides)
    
    # Reload gallery to reflect changes
    load_gallery_cache()
    
    return jsonify({"success": True, "count": success_count})
'''

if 'def api_correct_bulk' not in content:
    content = content.replace("if __name__ == '__main__':", bulk_endpoint + "\nif __name__ == '__main__':")
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched /api/correct_bulk!")
else:
    print("Already patched.")
