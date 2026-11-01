import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the folderName logic in index.html
old_logic = '''            let pathParts2 = currentFileObj.path.split(/[\\\\/]/);
            let folderName = pathParts2.slice(-2, -1)[0];
            let categoryName = pathParts2.slice(-3, -2)[0];
            if (folderName === '_Dudosos') {
                folderName = pathParts2.slice(-3, -2)[0];
                categoryName = pathParts2.slice(-4, -3)[0];
            }'''

new_logic = '''            let folderName, categoryName;
            if (currentCat && currentCat !== 'Resultados' && currentCat !== 'Personas Sin Nombre' && currentCat !== 'Limpieza Inteligente') {
                categoryName = currentCat;
                folderName = currentIdent;
            } else {
                let pathParts2 = currentFileObj.path.split(/[\\\\/]/);
                folderName = pathParts2.slice(-2, -1)[0];
                categoryName = pathParts2.slice(-3, -2)[0];
                if (folderName === '_Dudosos') {
                    folderName = pathParts2.slice(-3, -2)[0];
                    categoryName = pathParts2.slice(-4, -3)[0];
                }
            }'''

# Also, when we generate the dropdown, we must check if categoryName == 'Lugares'
# We patched this in the previous step, so we need to find it:
# if (categoryName !== 'Personas Sin Nombre' && categoryName !== 'Resultados') {
old_dropdown_condition = '''if (categoryName !== 'Personas Sin Nombre' && categoryName !== 'Resultados') {'''
new_dropdown_condition = '''if (categoryName !== 'Personas Sin Nombre' && categoryName !== 'Resultados' && categoryName !== 'Lugares') {'''

if old_logic in content:
    content = content.replace(old_logic, new_logic)
else:
    print("WARNING: Could not find old_logic")

if old_dropdown_condition in content:
    content = content.replace(old_dropdown_condition, new_dropdown_condition)
else:
    print("WARNING: Could not find old_dropdown_condition")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("index.html owner logic patched!")
