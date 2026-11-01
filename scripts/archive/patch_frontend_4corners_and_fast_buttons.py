import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace handles creation in createFaceElements
old_handle_creation = """            const handle = document.createElement('div');
            handle.className = 'resize-handle';
            box.appendChild(handle);"""

new_handle_creation = """            ['tl', 'tr', 'bl', 'br'].forEach(corner => {
                const handle = document.createElement('div');
                handle.className = `resize-handle handle-${corner}`;
                handle.dataset.corner = corner;
                box.appendChild(handle);
            });"""

content = content.replace(old_handle_creation, new_handle_creation)

# Replace mousedown logic for dragging & 4-corner resizing
old_drag_logic = """            let isDragging = false;
            let isResizing = false;
            let startX, startY, startW, startH, startLeft, startTop;

            box.onmousedown = (e) => {
                if (e.target.classList.contains('resize-handle')) {
                    isResizing = true;
                } else {
                    isDragging = true;
                }
                startX = e.clientX;
                startY = e.clientY;
                startW = box.offsetWidth;
                startH = box.offsetHeight;
                startLeft = box.offsetLeft;
                startTop = box.offsetTop;
                highlightFace(faceNum);
                e.stopPropagation();
            };

            const onMouseMove = (e) => {
                if (!isDragging && !isResizing) return;
                const containerRect = container.getBoundingClientRect();
                const dx = e.clientX - startX;
                const dy = e.clientY - startY;

                if (isResizing) {
                    const newW = Math.max(30, startW + dx);
                    const newH = Math.max(30, startH + dy);
                    box.style.width = `${(newW / containerRect.width) * 100}%`;
                    box.style.height = `${(newH / containerRect.height) * 100}%`;
                } else if (isDragging) {
                    const newLeft = startLeft + dx;
                    const newTop = startTop + dy;
                    box.style.left = `${(newLeft / containerRect.width) * 100}%`;
                    box.style.top = `${(newTop / containerRect.height) * 100}%`;
                }
            };

            const onMouseUp = () => {
                if (isDragging || isResizing) {
                    isDragging = false;
                    isResizing = false;
                    saveBoxDimensions(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl);
                }
            };"""

new_drag_logic = """            let isDragging = false;
            let activeCorner = null;
            let startX, startY, startW, startH, startLeft, startTop;

            box.onmousedown = (e) => {
                if (e.target.classList.contains('resize-handle')) {
                    activeCorner = e.target.dataset.corner;
                } else {
                    isDragging = true;
                }
                startX = e.clientX;
                startY = e.clientY;
                startW = box.offsetWidth;
                startH = box.offsetHeight;
                startLeft = box.offsetLeft;
                startTop = box.offsetTop;
                highlightFace(faceNum);
                e.stopPropagation();
            };

            const onMouseMove = (e) => {
                if (!isDragging && !activeCorner) return;
                const containerRect = container.getBoundingClientRect();
                const dx = e.clientX - startX;
                const dy = e.clientY - startY;

                if (activeCorner) {
                    let newL = startLeft, newT = startTop, newW = startW, newH = startH;
                    if (activeCorner.includes('r')) newW = Math.max(30, startW + dx);
                    if (activeCorner.includes('l')) {
                        newW = Math.max(30, startW - dx);
                        newL = startLeft + (startW - newW);
                    }
                    if (activeCorner.includes('b')) newH = Math.max(30, startH + dy);
                    if (activeCorner.includes('t')) {
                        newH = Math.max(30, startH - dy);
                        newT = startTop + (startH - newH);
                    }
                    box.style.width = `${(newW / containerRect.width) * 100}%`;
                    box.style.height = `${(newH / containerRect.height) * 100}%`;
                    box.style.left = `${(newL / containerRect.width) * 100}%`;
                    box.style.top = `${(newT / containerRect.height) * 100}%`;
                } else if (isDragging) {
                    const newLeft = startLeft + dx;
                    const newTop = startTop + dy;
                    box.style.left = `${(newLeft / containerRect.width) * 100}%`;
                    box.style.top = `${(newTop / containerRect.height) * 100}%`;
                }
            };

            const onMouseUp = () => {
                if (isDragging || activeCorner) {
                    isDragging = false;
                    activeCorner = null;
                    saveBoxDimensions(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl);
                }
            };"""

content = content.replace(old_drag_logic, new_drag_logic)

# Replace box.onclick to show 1-click action buttons popup
old_popup = """                const popup = document.createElement('div');
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
                box.appendChild(popup);"""

new_popup = """                const popup = document.createElement('div');
                popup.className = 'lb-box-popup';
                popup.style.cssText = 'position:absolute; bottom:-65px; left:50%; transform:translateX(-50%); z-index:100; background:rgba(20,20,22,0.95); backdrop-filter:blur(20px); padding:8px; border-radius:12px; border:1px solid rgba(255,255,255,0.25); box-shadow:0 8px 30px rgba(0,0,0,0.6); display:flex; flex-direction:column; gap:6px; min-width:210px;';
                
                let folderName = currentFileObj.path.split(/[\\\\/]/).slice(-2, -1)[0];
                let categoryName = currentFileObj.path.split(/[\\\\/]/).slice(-3, -2)[0];
                
                let innerHtml = '';
                if (folderName && categoryName && folderName !== 'Resultados' && categoryName !== 'Galeria Eneko NO ABRIR') {
                    let suggestedId = JSON.stringify({categoria: categoryName, identidad: folderName});
                    innerHtml += `<button style="background:#30d158; color:white; border:none; padding:6px 12px; border-radius:6px; font-weight:bold; font-size:0.8rem; cursor:pointer;" onclick="inlineCorrect(encodeURIComponent(currentFileObj.path), '${encodeURIComponent(suggestedId)}', ${faceNum}, ${face.x}, ${face.y}, ${face.width}, ${face.height})">✨ Sí, es ${folderName}</button>`;
                }
                
                let falsePosId = JSON.stringify({categoria: 'Ignorar', identidad: 'Falso_Positivo'});
                innerHtml += `<button style="background:#ff3b30; color:white; border:none; padding:5px 10px; border-radius:6px; font-size:0.75rem; cursor:pointer;" onclick="inlineCorrect(encodeURIComponent(currentFileObj.path), '${encodeURIComponent(falsePosId)}', ${faceNum}, ${face.x}, ${face.y}, ${face.width}, ${face.height})">🚫 Esto NO es una cara</button>`;
                
                let selectHtml = `<select class="person-select" style="margin:0; font-size:0.75rem; padding:4px 6px;" onchange="inlineCorrect(encodeURIComponent(currentFileObj.path), this.value, ${faceNum}, ${face.x}, ${face.y}, ${face.width}, ${face.height})">`;
                selectHtml += `<option value="">📋 Reasignar a otra persona...</option>`;
                selectHtml += `<option value='{"categoria": "Ignorar", "identidad": "Ignorar_Irrelevante"}'>👤 Ignorar cara</option>`;
                
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
                box.appendChild(popup);"""

content = content.replace(old_popup, new_popup)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("templates/index.html actualizado con 4 esquinas de redimensionado y botones en 1 clic.")
