import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix selectHtml
old_select_html = '''            selectOptionsHtml += `<option value="NEW">➕ Crear nueva persona...</option>`;
                        let categories = {};'''
new_select_html = '''            selectOptionsHtml += `<option value="NEW">➕ Crear nueva persona...</option>`;
            let selectHtml = `<select class="face-quick-select" onchange="quickReassignFace(this, ${faceNum})">`;
            selectHtml += selectOptionsHtml;
            let categories = {};'''

if old_select_html in content:
    content = content.replace(old_select_html, new_select_html)
    print("Patched selectHtml bug")
else:
    print("Could not find old_select_html")
    
# 2. Make apply_to_duplicates automatic
old_dup_prompt = '''                if (dupData.duplicate) {
                    if (confirm(`Se han encontrado fotos muy similares a esta en la misma carpeta.\\n\\n¿Quieres aplicar este mismo cambio a la cara correspondiente en las fotos parecidas (el paquete)?`)) {
                        applyToDuplicates = true;
                    }
                }'''
new_dup_prompt = '''                if (dupData.duplicate) {
                    applyToDuplicates = true;
                }'''
if old_dup_prompt in content:
    content = content.replace(old_dup_prompt, new_dup_prompt)
    print("Patched dup prompt (Reassign)")
else:
    print("Could not find dup prompt (Reassign)")

# Quick reassign duplicate prompt
old_quick_dup_prompt = '''                if (dupData.duplicate) {
                    if (confirm(`Se han encontrado fotos muy similares a esta en la misma carpeta.\\n\\n¿Quieres aplicar este mismo cambio a la cara correspondiente en las fotos parecidas (el paquete)?`)) {
                        applyToDuplicates = true;
                    }
                }'''

# Usually it's the exact same block, but let's just do a regex replace all.
content = content.replace('''if (confirm(`Se han encontrado fotos muy similares a esta en la misma carpeta.\\n\\n¿Quieres aplicar este mismo cambio a la cara correspondiente en las fotos parecidas (el paquete)?`)) {
                        applyToDuplicates = true;
                    }''', 'applyToDuplicates = true;')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

