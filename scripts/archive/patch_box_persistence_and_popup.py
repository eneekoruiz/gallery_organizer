import re

# 1. Update app.py
with open('app.py', 'r', encoding='utf-8') as f:
    app_content = f.read()

# Fix override coordinates update in api_correct
app_content = app_content.replace(
    "if iou(face_box, ov_box) > 0.4:\n                ov['identity'] = new_identidad\n                updated = True",
    "if iou(face_box, ov_box) > 0.4:\n                ov['identity'] = new_identidad\n                ov['x'] = face_data['x']\n                ov['y'] = face_data['y']\n                ov['width'] = face_data['width']\n                ov['height'] = face_data['height']\n                updated = True"
)

# Fix override coordinates override in api_analyze
app_content = app_content.replace(
    "if iou(current_box, ov_box) > 0.4:\n                            override_match = ov['identity']\n                            break",
    "if iou(current_box, ov_box) > 0.4:\n                            override_match = ov['identity']\n                            x, y, w, h = ov['x'], ov['y'], ov['width'], ov['height']\n                            break"
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_content)

print("app.py actualizado: las coordenadas redimensionadas ahora se guardan y cargan con precisión.")

# 2. Update index.html to add popup menu on box click
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

# Replace box.onclick in createFaceElements to show inline dropdown menu directly on box!
box_click_target = """box.onclick = (e) => {
                e.stopPropagation();
                highlightFace(faceNum);
            };"""

box_click_replacement = """box.onclick = (e) => {
                if (e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION') return;
                e.stopPropagation();
                highlightFace(faceNum);
                
                // Mostrar desplegable rápido directamente sobre la foto
                let existingMenu = box.querySelector('.lb-box-popup');
                if (existingMenu) {
                    existingMenu.remove();
                    return;
                }
                
                document.querySelectorAll('.lb-box-popup').forEach(m => m.remove());
                
                const popup = document.createElement('div');
                popup.className = 'lb-box-popup';
                popup.style.cssText = 'position:absolute; bottom:-45px; left:50%; transform:translateX(-50%); z-index:100; background:rgba(20,20,22,0.92); backdrop-filter:blur(15px); padding:4px; border-radius:8px; border:1px solid rgba(255,255,255,0.2); box-shadow:0 4px 15px rgba(0,0,0,0.5);';
                
                let folderName = currentFileObj.path.split(/[\\\\/]/).slice(-2, -1)[0];
                let categoryName = currentFileObj.path.split(/[\\\\/]/).slice(-3, -2)[0];
                
                let selectHtml = `<select class="person-select" style="margin:0; font-size:0.75rem; padding:4px 6px;" onchange="inlineCorrect(encodeURIComponent(currentFileObj.path), this.value, ${faceNum}, ${face.x}, ${face.y}, ${face.width}, ${face.height})">`;
                selectHtml += `<option value="">Asignar persona...</option>`;
                if (folderName && categoryName && folderName !== 'Resultados' && categoryName !== 'Galeria Eneko NO ABRIR') {
                    let suggestedId = {categoria: categoryName, identidad: folderName};
                    selectHtml += `<option value='${JSON.stringify(suggestedId)}' style="font-weight:bold; color:#0a84ff;">✨ Sí, es ${folderName}</option>`;
                }
                selectHtml += `<option value='{"categoria": "Ignorar", "identidad": "Ignorar_Irrelevante"}'>👤 Ignorar cara</option>`;
                selectOptionsHtml = selectHtml;
                
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
                popup.innerHTML = selectHtml;
                box.appendChild(popup);
            };"""

html_content = html_content.replace(box_click_target, box_click_replacement)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("templates/index.html actualizado: al pulsar sobre el recuadro de la foto ahora aparece el desplegable de asignación directa.")
