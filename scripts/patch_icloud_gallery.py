with open('app/services/gallery_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

target1 = """    root_base = FOTOS_DIR.parent
    if root_base.exists():
        for sub in root_base.iterdir():
            if sub.is_dir():
                is_orig = (sub.name.lower() == 'fotos')
                gather_files(sub, is_orig)
    else:
        if FOTOS_DIR.exists():
            gather_files(FOTOS_DIR, True)
        if RESULTADOS_DIR.exists():
            gather_files(RESULTADOS_DIR, False)

    total_files = len(all_file_targets)"""

replacement1 = """    root_base = FOTOS_DIR.parent
    if root_base.exists():
        for sub in root_base.iterdir():
            if sub.is_dir():
                is_orig = (sub.name.lower() == 'fotos')
                gather_files(sub, is_orig)
    else:
        if FOTOS_DIR.exists():
            gather_files(FOTOS_DIR, True)
        if RESULTADOS_DIR.exists():
            gather_files(RESULTADOS_DIR, False)

    icloud_dir = Path(r"C:\\Users\\User\\Pictures\\iCloud Photos\\Photos")
    if icloud_dir.exists():
        gather_files(icloud_dir, False)

    total_files = len(all_file_targets)"""

target2 = """    SMART_ALBUM_IDENTS = {
        'familia conmigo', 'familia sin mi', 'familia sin mí',
        'familiares conmigo', 'familiares sin mi', 'familiares sin mí',
        'conocidos conmigo', 'conocidos sin mi', 'conocidos sin mí',
        'mascotas conmigo',
    }
    KNOWN_CATEGORIES = {"Conocidos", "Familia", "YO", "Profesores", "Lugares", "Eventos", "Mascotas", "Objetos", "Recuerdos", "Publicaciones_Instagram"}
    ident_to_cat_map = {id_info["identidad"]: id_info["categoria"] for id_info in get_all_identities()}

    for filepath, is_orig_dataset, base_dir in all_file_targets:"""

replacement2 = """    SMART_ALBUM_IDENTS = {
        'familia conmigo', 'familia sin mi', 'familia sin mí',
        'familiares conmigo', 'familiares sin mi', 'familiares sin mí',
        'conocidos conmigo', 'conocidos sin mi', 'conocidos sin mí',
        'mascotas conmigo',
    }
    KNOWN_CATEGORIES = {"Conocidos", "Familia", "YO", "Profesores", "Lugares", "Eventos", "Mascotas", "Objetos", "Recuerdos", "Publicaciones_Instagram"}
    ident_to_cat_map = {id_info["identidad"]: id_info["categoria"] for id_info in get_all_identities()}
    classified_filenames = set()

    for filepath, is_orig_dataset, base_dir in all_file_targets:"""

target3 = """            elif "icloud photos" in abs_p_l or base_dir.name == "Photos":
                cat = "📋 Revisión / Por Organizar"
                ident = "🍎 Nuevas desde iCloud\""""

replacement3 = """            elif "icloud photos" in abs_p_l or base_dir.name == "Photos":
                if path_obj.name.lower() in classified_filenames:
                    continue
                cat = "📋 Revisión / Por Organizar"
                ident = "🍎 Nuevas desde iCloud\""""

target4 = """            file_name = path_obj.name
            key = (cat, ident, file_name)"""

replacement4 = """            file_name = path_obj.name
            is_icloud_file = ("icloud photos" in abs_p_l or base_dir.name == "Photos")
            if not is_icloud_file and not is_dudoso and cat != "📋 Revisión / Por Organizar":
                classified_filenames.add(file_name.lower())
            key = (cat, ident, file_name)"""

assert target1 in content, "target1 not found"
assert target2 in content, "target2 not found"
assert target3 in content, "target3 not found"
assert target4 in content, "target4 not found"

content = content.replace(target1, replacement1, 1)
content = content.replace(target2, replacement2, 1)
content = content.replace(target3, replacement3, 1)
content = content.replace(target4, replacement4, 1)

with open('app/services/gallery_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("SUCCESSFULLY PATCHED ICLOUD GALLERY INTEGRATION")
