import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_logic = """                            key = f"{cat.name}/{ident.name}"
                            if key not in seen:
                                identities.append({"categoria": cat.name, "identidad": ident.name})"""

new_logic = """                            c_name = cat.name
                            i_name = ident.name
                            if i_name.upper() == 'YO':
                                c_name = 'YO'
                                i_name = 'YO'
                            key = f"{c_name}/{i_name}"
                            if key not in seen:
                                identities.append({"categoria": c_name, "identidad": i_name})"""

if old_logic in content:
    content = content.replace(old_logic, new_logic)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Patched get_all_identities YO logic')
else:
    print('Could not patch get_all_identities')
