import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace runAnalysis, enableManualSelection, inlineCorrect functions with updated versions
new_functions = """
        async function runAnalysis() {
            if (!currentFileObj) return;
            const container = document.getElementById('lb-media-container');
            const mediaEl = container.querySelector('.lb-media-element');
            if (!mediaEl) return;
            
            document.querySelectorAll('.lb-bounding-box').forEach(b => b.remove());
            
            let timestamp = isCurrentVideo ? mediaEl.currentTime : null;
            const res = await fetch('/api/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ path: currentFileObj.path, timestamp: timestamp })
            });
            const data = await res.json();
            
            const cardsContainer = document.getElementById('person-cards-container');
            cardsContainer.innerHTML = '';
            
            if (data.faces && data.faces.length > 0) {
                let intrinsicWidth = isCurrentVideo ? mediaEl.videoWidth : mediaEl.naturalWidth;
                let intrinsicHeight = isCurrentVideo ? mediaEl.videoHeight : mediaEl.naturalHeight;
                if (!intrinsicWidth && data.faces.length > 0) {
                    intrinsicWidth = data.faces[0].img_width;
                    intrinsicHeight = data.faces[0].img_height;
                }
                
                data.faces.forEach((face, idx) => {
                    createFaceElements(face, idx + 1, intrinsicWidth, intrinsicHeight, mediaEl, container, cardsContainer);
                });
            } else {
                cardsContainer.innerHTML = '<p style="font-size:0.8rem; color:var(--text-dim);">No se han detectado personas en este fotograma.</p>';
            }
        }

        function createFaceElements(face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl, container, cardsContainer) {
            // 1. Bounding Box sobre la Foto (Movible y Redimensionable)
            const box = document.createElement('div');
            box.className = 'lb-bounding-box';
            box.id = `bbox-${faceNum}`;
            
            const percX = (face.x / intrinsicWidth) * 100;
            const percY = (face.y / intrinsicHeight) * 100;
            const percW = (face.width / intrinsicWidth) * 100;
            const percH = (face.height / intrinsicHeight) * 100;
            
            box.style.left = `${percX}%`;
            box.style.top = `${percY}%`;
            box.style.width = `${percW}%`;
            box.style.height = `${percH}%`;
            
            const badge = document.createElement('div');
            badge.className = 'lb-bb-badge';
            badge.textContent = `#${faceNum}`;
            box.appendChild(badge);
            
            const handle = document.createElement('div');
            handle.className = 'resize-handle';
            box.appendChild(handle);
            
            box.onclick = (e) => {
                e.stopPropagation();
                highlightFace(faceNum);
            };
            
            // Hacer la caja arrastrable y redimensionable
            makeBoxInteractive(box, handle, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl);
            
            container.appendChild(box);
            
            // 2. Avatar Recortado en Canvas
            let avatarUrl = updateAvatarCrop(mediaEl, face);
            
            // 3. Tarjeta en Sidebar
            const card = document.createElement('div');
            card.className = 'person-card';
            card.id = `pcard-${faceNum}`;
            
            let folderName = currentFileObj.path.split(/[\\\\/]/).slice(-2, -1)[0];
            let categoryName = currentFileObj.path.split(/[\\\\/]/).slice(-3, -2)[0];
            
            let selectOptionsHtml = `<option value="">Reasignar persona...</option>`;
            if (folderName && categoryName && folderName !== 'Resultados' && categoryName !== 'Galeria Eneko NO ABRIR') {
                let suggestedId = {categoria: categoryName, identidad: folderName};
                selectOptionsHtml += `<option value='${JSON.stringify(suggestedId)}' style="font-weight:bold; color:#0a84ff;">✨ Sí, es ${folderName}</option>`;
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
                        <div class="person-confidence" id="pconf-${faceNum}">${face.confidence || 'Asignación manual'}</div>
                    </div>
                </div>
                <select class="person-select" id="pselect-${faceNum}" onchange="inlineCorrect(encodeURIComponent(currentFileObj.path), this.value, ${faceNum}, ${face.x}, ${face.y}, ${face.width}, ${face.height})">
                    ${selectOptionsHtml}
                </select>
            `;
            
            cardsContainer.appendChild(card);
        }

        function updateAvatarCrop(mediaEl, face) {
            try {
                const canvas = document.createElement('canvas');
                canvas.width = 100;
                canvas.height = 100;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(mediaEl, Math.max(0, face.x), Math.max(0, face.y), face.width, face.height, 0, 0, 100, 100);
                return canvas.toDataURL();
            } catch(e) {
                return '';
            }
        }

        function makeBoxInteractive(box, handle, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl) {
            let isDragging = false;
            let isResizing = false;
            let startX, startY, startLeft, startTop, startW, startH;
            const container = document.getElementById('lb-media-container');

            // Arrastrar Posición
            box.addEventListener('mousedown', (e) => {
                if (e.target === handle) return;
                e.stopPropagation();
                isDragging = True;
                startX = e.clientX;
                startY = e.clientY;
                const rect = box.getBoundingClientRect();
                const containerRect = container.getBoundingClientRect();
                startLeft = rect.left - containerRect.left;
                startTop = rect.top - containerRect.top;

                const onMouseMove = (ev) => {
                    if (!isDragging) return;
                    const dx = ev.clientX - startX;
                    const dy = ev.clientY - startY;
                    const newLeft = startLeft + dx;
                    const newTop = startTop + dy;
                    box.style.left = `${(newLeft / containerRect.width) * 100}%`;
                    box.style.top = `${(newTop / containerRect.height) * 100}%`;
                };

                const onMouseUp = () => {
                    if (isDragging) {
                        isDragging = false;
                        document.removeEventListener('mousemove', onMouseMove);
                        document.removeEventListener('mouseup', onMouseUp);
                        saveBoxDimensions(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl);
                    }
                };

                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            });

            // Redimensionar Tamaño
            handle.addEventListener('mousedown', (e) => {
                e.stopPropagation();
                isResizing = true;
                startX = e.clientX;
                startY = e.clientY;
                const rect = box.getBoundingClientRect();
                const containerRect = container.getBoundingClientRect();
                startW = rect.width;
                startH = rect.height;

                const onMouseMove = (ev) => {
                    if (!isResizing) return;
                    const dw = ev.clientX - startX;
                    const dh = ev.clientY - startY;
                    const newW = Math.max(20, startW + dw);
                    const newH = Math.max(20, startH + dh);
                    box.style.width = `${(newW / containerRect.width) * 100}%`;
                    box.style.height = `${(newH / containerRect.height) * 100}%`;
                };

                const onMouseUp = () => {
                    if (isResizing) {
                        isResizing = false;
                        document.removeEventListener('mousemove', onMouseMove);
                        document.removeEventListener('mouseup', onMouseUp);
                        saveBoxDimensions(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl);
                    }
                };

                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            });
        }

        function saveBoxDimensions(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl) {
            const container = document.getElementById('lb-media-container');
            const rect = box.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();

            const scaleX = intrinsicWidth / containerRect.width;
            const scaleY = intrinsicHeight / containerRect.height;

            face.x = Math.round((rect.left - containerRect.left) * scaleX);
            face.y = Math.round((rect.top - containerRect.top) * scaleY);
            face.width = Math.round(rect.width * scaleX);
            face.height = Math.round(rect.height * scaleY);

            // Actualizar avatar en sidebar
            const avatarImg = document.getElementById(`pavatar-${faceNum}`);
            if (avatarImg) {
                avatarImg.src = updateAvatarCrop(mediaEl, face);
            }
        }

        async function inlineCorrect(pathEncoded, valStr, faceNum, faceX, faceY, faceW, faceH) {
            if(!valStr) return;
            let idObj;
            if(valStr === 'NEW') {
                const newCat = prompt("Introduce la categoría:", "Conocidos");
                if(!newCat) return;
                const newIdent = prompt("Introduce el nombre completo:");
                if(!newIdent) return;
                idObj = {categoria: newCat, identidad: newIdent};
            } else {
                idObj = JSON.parse(valStr);
            }
            
            const res = await fetch('/api/correct', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ 
                    path: decodeURIComponent(pathEncoded), 
                    new_categoria: idObj.categoria, 
                    new_identidad: idObj.identidad,
                    face: {x: faceX, y: faceY, width: faceW, height: faceH}
                })
            });
            
            const data = await res.json();
            if(data.success) {
                showToast(`Asignado a '${idObj.identidad}'. Memoria guardada.`);
                
                // Actualizar localmente SIN PARPADEO
                if (idObj.identidad === 'Ignorar_Irrelevante' || idObj.identidad === 'Falso_Positivo') {
                    const bbox = document.getElementById(`bbox-${faceNum}`);
                    const pcard = document.getElementById(`pcard-${faceNum}`);
                    if (bbox) bbox.remove();
                    if (pcard) pcard.remove();
                } else {
                    const pname = document.getElementById(`pname-${faceNum}`);
                    const pconf = document.getElementById(`pconf-${faceNum}`);
                    if (pname) pname.textContent = `#${faceNum} ${idObj.identidad}`;
                    if (pconf) pconf.textContent = '100.0% (Manual)';
                }
                await loadIdentities();
                await loadGallery();
            } else {
                showToast(data.error || "Error al asignar.", true);
            }
        }

        function enableManualSelection() {
            if (!currentFileObj) return;
            const container = document.getElementById('lb-media-container');
            const mediaEl = container.querySelector('.lb-media-element');
            if (!mediaEl) return;
            
            showToast("Arrastra sobre la foto para crear un recuadro de persona.");
            container.style.cursor = 'crosshair';
            
            let startX, startY, selectBox;
            const onMouseDown = (e) => {
                const rect = container.getBoundingClientRect();
                startX = e.clientX - rect.left;
                startY = e.clientY - rect.top;
                
                selectBox = document.createElement('div');
                selectBox.style.cssText = `position:absolute; left:${startX}px; top:${startY}px; border:2px dashed #30d158; background:rgba(48,209,88,0.2); pointer-events:none; z-index:999;`;
                container.appendChild(selectBox);
                
                const onMouseMove = (ev) => {
                    const currentX = ev.clientX - rect.left;
                    const currentY = ev.clientY - rect.top;
                    const width = Math.abs(currentX - startX);
                    const height = Math.abs(currentY - startY);
                    selectBox.style.left = `${Math.min(startX, currentX)}px`;
                    selectBox.style.top = `${Math.min(startY, currentY)}px`;
                    selectBox.style.width = `${width}px`;
                    selectBox.style.height = `${height}px`;
                };
                
                const onMouseUp = async (ev) => {
                    container.removeEventListener('mousemove', onMouseMove);
                    container.removeEventListener('mouseup', onMouseUp);
                    container.removeEventListener('mousedown', onMouseDown);
                    container.style.cursor = 'default';
                    
                    const rect = container.getBoundingClientRect();
                    const endX = ev.clientX - rect.left;
                    const endY = ev.clientY - rect.top;
                    
                    const boxW = Math.abs(endX - startX);
                    const boxH = Math.abs(endY - startY);
                    if (selectBox) selectBox.remove();
                    if (boxW < 10 || boxH < 10) return;
                    
                    let intrinsicWidth = isCurrentVideo ? mediaEl.videoWidth : mediaEl.naturalWidth;
                    let intrinsicHeight = isCurrentVideo ? mediaEl.videoHeight : mediaEl.naturalHeight;
                    
                    const scaleX = intrinsicWidth / rect.width;
                    const scaleY = intrinsicHeight / rect.height;
                    
                    const realX = Math.round(Math.min(startX, endX) * scaleX);
                    const realY = Math.round(Math.min(startY, endY) * scaleY);
                    const realW = Math.round(boxW * scaleX);
                    const realH = Math.round(boxH * scaleY);
                    
                    const newFace = { x: realX, y: realY, width: realW, height: realH, identity: "Desconocido", confidence: "Selección manual" };
                    const nextNum = document.querySelectorAll('.lb-bounding-box').length + 1;
                    const cardsContainer = document.getElementById('person-cards-container');
                    
                    createFaceElements(newFace, nextNum, intrinsicWidth, intrinsicHeight, mediaEl, container, cardsContainer);
                    highlightFace(nextNum);
                    
                    // Enfocar desplegable en el sidebar
                    const select = document.getElementById(`pselect-${nextNum}`);
                    if (select) select.focus();
                };
                
                container.addEventListener('mousemove', onMouseMove);
                container.addEventListener('mouseup', onMouseUp);
            };
            
            container.addEventListener('mousedown', onMouseDown);
        }
"""

# Replace in content
runAnalysis_idx = content.find("async function runAnalysis()")
closeLightbox_idx = content.find("function closeLightbox()")
content = content[:runAnalysis_idx] + new_functions + "\n\n" + content[closeLightbox_idx:]

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("index.html actualizado con cajas interactiva, rediseño manual y eliminación de parpadeos.")
