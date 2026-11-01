import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Patch get_all_identities
old_get_all = """                            if i_name.upper() == 'YO':
                                c_name = 'YO'
                                i_name = 'YO'"""

new_get_all = """                            if i_name.upper() == 'YO':
                                c_name = 'YO'
                                i_name = 'YO'
                            elif c_name == 'Recuerdos' or i_name == 'Recuerdos':
                                c_name = 'Recuerdos'
                                i_name = 'Recuerdos'"""

if old_get_all in content:
    content = content.replace(old_get_all, new_get_all)
    print("Patched get_all_identities for Recuerdos in app.py")

# 2. Patch get_gallery scan_dir
old_get_gal = """                            elif cat == 'Publicaciones_Instagram' or ident == 'Publicaciones_Instagram':
                                cat = 'Publicaciones_Instagram'
                                ident = 'Publicaciones_Instagram'"""

new_get_gal = """                            elif cat == 'Publicaciones_Instagram' or ident == 'Publicaciones_Instagram':
                                cat = 'Publicaciones_Instagram'
                                ident = 'Publicaciones_Instagram'
                            elif cat == 'Recuerdos' or ident == 'Recuerdos':
                                cat = 'Recuerdos'
                                ident = 'Recuerdos'"""

if old_get_gal in content:
    content = content.replace(old_get_gal, new_get_gal)
    print("Patched get_gallery scan_dir for Recuerdos in app.py")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
