import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

replacement = '''
            if (folderName && categoryName && folderName !== 'Resultados' && categoryName !== 'Galeria Eneko NO ABRIR') {
                if (!aiPredictedIdObj) {
                    let suggestedId = {categoria: categoryName, identidad: folderName};
                    selectOptionsHtml += `<option value='${JSON.stringify(suggestedId)}' style="font-weight:bold; color:#30d158;">✨ Sí, es (Dueño): ${folderName}</option>`;
                }
                let notId = {categoria: "Ignorar", identidad: "Ignorar_Irrelevante"};
                selectOptionsHtml += `<option value='${JSON.stringify(notId)}' style="font-weight:bold; color:#ff9f0a;">🤔 Esto NO es ${folderName}</option>`;
            }
            selectOptionsHtml += `<option value='{"categoria": "Ignorar", "identidad": "Ignorar_Irrelevante"}'>👤 Ignorar cara (Persona irrelevante)</option>`;
            selectOptionsHtml += `<option value='{"categoria": "Ignorar", "identidad": "Falso_Positivo"}'>🚫 Esto NO es una cara</option>`;
            selectOptionsHtml += `<option value="NEW">➕ Crear nueva persona...</option>`;
'''

start_idx = content.find("            if (folderName && categoryName && folderName !== 'Resultados'")
end_idx = content.find("            let categories = {};")

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + replacement.strip() + '\n            ' + content[end_idx:]
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched dropdown successfully.")
else:
    print("Could not find dropdown target")
