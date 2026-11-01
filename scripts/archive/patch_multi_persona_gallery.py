import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_gallery_loop = """    for (cat, ident, filename), item in seen_files.items():
        if cat not in gallery: gallery[cat] = {}
        if ident not in gallery[cat]: gallery[cat][ident] = []
        gallery[cat][ident].append(item)"""

new_gallery_loop = """    ident_to_cat_map = {id_info["identidad"]: id_info["categoria"] for id_info in get_all_identities()}

    for (cat, ident, filename), item in seen_files.items():
        if cat not in gallery: gallery[cat] = {}
        if ident not in gallery[cat]: gallery[cat][ident] = []
        gallery[cat][ident].append(item)
        
        # Inclusión Virtual Multi-Persona: La foto aparece en el álbum de cada persona presente
        faces_in_file = faces_cache.get(item['path'], [])
        file_k = get_file_key(item['path'])
        if file_k in overrides:
            faces_in_file = overrides[file_k]
            
        for f_entry in faces_in_file:
            other_id = f_entry.get('identity')
            if other_id and other_id != ident and not other_id.startswith('Desconocid') and not other_id.startswith('Falso_Positivo') and not other_id.startswith('Ignorar'):
                other_cat = ident_to_cat_map.get(other_id)
                if not other_cat:
                    if other_id.startswith('C. '): other_cat = 'Conocidos'
                    elif other_id.startswith('F. '): other_cat = 'Familia'
                    elif other_id == 'YO': other_cat = 'YO'
                    else: other_cat = 'Conocidos'
                    
                if other_cat not in gallery: gallery[other_cat] = {}
                if other_id not in gallery[other_cat]: gallery[other_cat][other_id] = []
                
                if not any(x['path'] == item['path'] for x in gallery[other_cat][other_id]):
                    gallery[other_cat][other_id].append(item)"""

if old_gallery_loop in content:
    content = content.replace(old_gallery_loop, new_gallery_loop)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched multi-persona virtual gallery index in app.py")
else:
    print("Could not find old_gallery_loop in app.py")
