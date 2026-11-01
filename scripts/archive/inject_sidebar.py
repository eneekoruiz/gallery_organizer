import sys
import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the sidebar dropdown generation
old_sidebar_dropdown = """            let selectOptionsHtml = `<option value="">Reasignar persona...</option>`;
            
            let aiPredictedIdObj = null;
            if (face.identity && face.identity !== 'Desconocido' && face.identity !== folderName) {
                aiPredictedIdObj = identitiesList.find(id => id.identidad === face.identity);
                if (aiPredictedIdObj) {
                    selectOptionsHtml += `<option value='${JSON.stringify(aiPredictedIdObj)}' style="font-weight:bold; color:#0a84ff;">🤖 Confirmar IA: ${face.identity}</option>`;
                }
            }
            
            if (categoryName !== 'Personas Sin Nombre' && categoryName !== 'Resultados' && categoryName !== 'Lugares' && categoryName !== 'Galeria Eneko NO ABRIR') {
                if (!aiPredictedIdObj) {
                    let suggestedId = {categoria: categoryName, identidad: folderName};
                    selectOptionsHtml += `<option value='${JSON.stringify(suggestedId)}' style="font-weight:bold; color:#30d158;">✨ Sí, es (Dueño): ${folderName}</option>`;
                }
            }
            selectOptionsHtml += `<option value='{"categoria": "Ignorar", "identidad": "Ignorar_Irrelevante"}'>👤 Ignorar cara (Persona irrelevante)</option>`;
            selectOptionsHtml += `<option value='{"categoria": "Ignorar", "identidad": "Falso_Positivo"}'>🚫 NO es persona</option>`;
            selectOptionsHtml += `<option value="NEW">➕ Crear nueva persona...</option>`;
            
            let categories = {};
            identitiesList.forEach(id => {
                if(!categories[id.categoria]) categories[id.categoria] = [];
                categories[id.categoria].push(id);
            });
            for (let cat in categories) {
                selectOptionsHtml += `<optgroup label="${cat}">`;
                categories[cat].forEach(id => {
                    selectOptionsHtml += `<option value='${JSON.stringify(id)}'>${id.identidad}</option>`;
                });
                selectOptionsHtml += `</optgroup>`;
            }
            
            card.innerHTML = `
                <div class="person-header" onclick="highlightFace(${faceNum})">
                    <img src="${avatarUrl}" class="person-avatar" id="pavatar-${faceNum}" alt="Face">
                    <div class="person-info">
                        <div class="person-name" id="pname-${faceNum}">#${faceNum} ${face.identity}</div>
                        <div class="person-confidence" id="pconf-${faceNum}">
                            ${face.identity === folderName"""

new_sidebar_dropdown = """            card.innerHTML = `
                <div class="person-header" onclick="highlightFace(${faceNum})">
                    <img src="${avatarUrl}" class="person-avatar" id="pavatar-${faceNum}" alt="Face">
                    <div class="person-info">
                        <div class="person-name" id="pname-${faceNum}">#${faceNum} ${face.identity}</div>
                        <div class="person-confidence" id="pconf-${faceNum}">
                            ${face.identity === folderName"""

if old_sidebar_dropdown in content:
    content = content.replace(old_sidebar_dropdown, new_sidebar_dropdown)
else:
    print("Warning: old_sidebar_dropdown not found")

# Replace the <select> tag in sidebar with the new HTML generator
old_sidebar_select = """                </div>
                <select class="person-select" id="pselect-${faceNum}" onchange="inlineCorrect(encodeURIComponent(currentFileObj.path), this.value, ${faceNum}, ${face.x}, ${face.y}, ${face.width}, ${face.height})">
                    ${selectOptionsHtml}
                </select>
            `;"""

new_sidebar_select = """                </div>
                ${generateReassignHTML(face, faceNum, 'quickReassignFace')}
            `;"""

if old_sidebar_select in content:
    content = content.replace(old_sidebar_select, new_sidebar_select)
else:
    print("Warning: old_sidebar_select not found")


with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated sidebar")
