import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update inlineCorrect to remove loadGallery() and add DOM update
new_inline_correct = '''                        const pname = document.getElementById(`pname-${faceNum}`);
                        const pconf = document.getElementById(`pconf-${faceNum}`);
                        if (pname) pname.textContent = `#${faceNum} ${idObj.identidad}`;
                        if (pconf) pconf.textContent = '100.0% (Manual)';
                    }
                    
                    if (currentFileObj) {
                        if (!currentFileObj.source.includes("Manual")) {
                            currentFileObj.source = currentFileObj.source + " + Manual";
                        }
                        const gridBadge = document.getElementById(`source-${currentItemIndex}`);
                        if (gridBadge) {
                            if (currentFileObj.source.includes('Dataset')) {
                                gridBadge.className = 'badge badge-dataset';
                                gridBadge.textContent = '🔒 Dataset + ✏️ Manual';
                            } else {
                                gridBadge.className = 'badge badge-manual';
                                gridBadge.textContent = '✏️ Manual';
                            }
                        }
                    }

                    await loadIdentities();
                    if (currentCat === 'Limpieza Inteligente') {'''

content = re.sub(
    r'const pname = document.getElementById\(`pname-\$\{faceNum\}`\);.*?await loadIdentities\(\);\s*await loadGallery\(\);\s*if \(currentCat === \'Limpieza Inteligente\'\) \{',
    new_inline_correct,
    content,
    flags=re.DOTALL
)

# 2. Update renderGrid to add ID and handle combined flags
old_badge_logic = '''                const badge = document.createElement('span');
                if (item.source.includes('Dataset')) {
                    badge.className = 'badge badge-dataset';
                    badge.textContent = '🔒 Dataset';
                } else if (item.source.includes('Manual')) {
                    badge.className = 'badge badge-manual';
                    badge.textContent = '✏️ Manual';
                } else {
                    badge.className = 'badge badge-ia';
                    badge.textContent = '✨ IA';
                }
                card.appendChild(badge);'''

new_badge_logic = '''                const badge = document.createElement('span');
                badge.id = `source-${idx}`;
                if (item.source.includes('Dataset') && item.source.includes('Manual')) {
                    badge.className = 'badge badge-dataset';
                    badge.textContent = '🔒 Dataset + ✏️ Manual';
                } else if (item.source.includes('IA') && item.source.includes('Manual')) {
                    badge.className = 'badge badge-manual';
                    badge.textContent = '✨ IA + ✏️ Manual';
                } else if (item.source.includes('Dataset')) {
                    badge.className = 'badge badge-dataset';
                    badge.textContent = '🔒 Dataset';
                } else if (item.source.includes('Manual')) {
                    badge.className = 'badge badge-manual';
                    badge.textContent = '✏️ Manual';
                } else {
                    badge.className = 'badge badge-ia';
                    badge.textContent = '✨ IA';
                }
                card.appendChild(badge);'''

content = content.replace(old_badge_logic, new_badge_logic)

# 3. Replace flat <select> with Custom Accordion Dropdown
regex_replace_dropdown = r'let selectOptionsHtml = `<option value="">Reasignar persona...</option>`;.*?selectHtml \+= `</select>`;'

new_dropdown_logic = '''            let selectHtml = `<div class="custom-accordion">`;
            
            const makeItem = (valStr, text, color) => {
                let encodedPath = encodeURIComponent(currentFileObj.path);
                let safeValStr = valStr.replace(/'/g, "&#39;").replace(/"/g, "&quot;");
                return `<div class="accordion-item" style="color:${color || '#e0e0e0'};" onclick="inlineCorrect('${encodedPath}', '${safeValStr}', ${faceNum}, ${face.x}, ${face.y}, ${face.width}, ${face.height})">${text}</div>`;
            };
            
            selectHtml += `<div class="accordion-title" style="padding:10px; font-weight:bold; border-bottom:1px solid #333; margin-bottom:5px;">Reasignar persona...</div>`;
            
            if (categoryName !== 'Personas Sin Nombre' && categoryName !== 'Resultados') {
                if (currentCat !== 'Limpieza Inteligente' || (currentCat === 'Limpieza Inteligente' && face.identity === 'Desconocido')) {
                    let suggestedId = {categoria: categoryName, identidad: folderName};
                    selectHtml += makeItem(JSON.stringify(suggestedId), `✨ Sí, es (Dueño): ${folderName}`, '#30d158');
                }
                let notId = {categoria: "Ignorar", identidad: "Ignorar_Irrelevante"};
                selectHtml += makeItem(JSON.stringify(notId), `🤔 Esto NO es ${folderName}`, '#ff9f0a');
            }
            selectHtml += makeItem('{"categoria": "Ignorar", "identidad": "Ignorar_Irrelevante"}', '👤 Ignorar cara (Persona irrelevante)');
            selectHtml += makeItem('{"categoria": "Ignorar", "identidad": "Falso_Positivo"}', '🚫 Esto NO es una cara');
            selectHtml += makeItem('NEW', '➕ Crear nueva persona...');
            
            if(identitiesList && identitiesList.length > 0) {
                let categories = {};
                identitiesList.forEach(id => {
                    if(!categories[id.categoria]) categories[id.categoria] = [];
                    categories[id.categoria].push(id);
                });
                for (let cat in categories) {
                    selectHtml += `<details class="accordion-details"><summary class="accordion-summary">📂 ${cat}</summary><div class="accordion-content">`;
                    categories[cat].forEach(id => {
                        selectHtml += makeItem(JSON.stringify(id), id.identidad);
                    });
                    selectHtml += `</div></details>`;
                }
            }
            selectHtml += `</div>`;'''

content = re.sub(regex_replace_dropdown, new_dropdown_logic, content, flags=re.DOTALL)

# Add CSS for accordion
css_append = '''
        .custom-accordion {
            background: #1c1c1e;
            border-radius: 8px;
            max-height: 250px;
            overflow-y: auto;
            border: 1px solid #333;
            font-size: 14px;
        }
        .accordion-item {
            padding: 10px 15px;
            cursor: pointer;
            border-bottom: 1px solid #2a2a2c;
            transition: background 0.2s;
        }
        .accordion-item:hover {
            background: #2a2a2c;
        }
        .accordion-item:last-child {
            border-bottom: none;
        }
        .accordion-details {
            border-bottom: 1px solid #2a2a2c;
        }
        .accordion-summary {
            padding: 10px 15px;
            cursor: pointer;
            font-weight: 500;
            background: #232325;
            list-style: none;
        }
        .accordion-summary::-webkit-details-marker {
            display: none;
        }
        .accordion-summary:hover {
            background: #2a2a2c;
        }
        .accordion-content {
            background: #1c1c1e;
            padding-left: 15px;
        }
</style>
'''

content = content.replace('</style>', css_append)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("index.html patched!")
