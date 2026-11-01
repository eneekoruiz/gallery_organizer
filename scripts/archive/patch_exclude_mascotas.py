import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_get_all_identities = """                    for ident in cat.iterdir():
                        if ident.is_dir():
                            c_name = cat.name
                            i_name = ident.name"""

new_get_all_identities = """                    if cat.name == 'Mascotas':
                        continue
                    for ident in cat.iterdir():
                        if ident.is_dir():
                            c_name = cat.name
                            i_name = ident.name"""

if old_get_all_identities in content:
    content = content.replace(old_get_all_identities, new_get_all_identities)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched Mascotas exclusion in get_all_identities in app.py")
else:
    print("Could not match old_get_all_identities in app.py")
