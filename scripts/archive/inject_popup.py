import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_popup = """                let notId = {categoria: "Ignorar", identidad: "Ignorar_Irrelevante"};
                selectOptionsHtml += `<option value='${JSON.stringify(notId)}' style="font-weight:bold; color:#ff9f0a;">🤔 Esto NO es ${folderName}</option>`;
            }
            selectOptionsHtml += `<option value='{"categoria": "Ignorar", "identidad": "Ignorar_Irrelevante"}'>👤 Ignorar cara (Persona irrelevante)</option>`;
            selectOptionsHtml += `<option value='{"categoria": "Ignorar", "identidad": "Falso_Positivo"}'>🚫 Esto NO es una cara</option>`;
            selectOptionsHtml += `<option value="NEW">➕ Crear nueva persona...</option>`;
            let selectHtml = `<select class="face-quick-select" onchange="quickReassignFace(this, ${faceNum})">`;
            selectHtml += selectOptionsHtml;
            let categories = {};
                identitiesList.forEach(id => {
                    if(!categories[id.categoria]) categories[id.categoria] = [];
                    categories[id.categoria].push(id);
                });
                for (let cat in categories) {
                    selectHtml += `<optgroup label="${cat}">`;
                    categories[cat].forEach(id => {
                        selectHtml += `<option value='${JSON.stringify(id)}'>${id.identidad}</option>`;
                    });
                    selectHtml += `</optgroup>`;
                }
                selectHtml += `</select>`;
                innerHtml += selectHtml;
                popup.innerHTML = innerHtml;
                box.appendChild(popup);
            };"""

new_popup = """            }
            innerHtml += generateReassignHTML(face, faceNum, 'quickReassignFace');
            popup.innerHTML = innerHtml;
            box.appendChild(popup);
        };"""

if old_popup in content:
    content = content.replace(old_popup, new_popup)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated popup")
else:
    print("Warning: old_popup not found")
