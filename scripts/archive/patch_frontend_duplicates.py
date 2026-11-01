import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update Details card HTML in index.html to include Sharpness and Duplicate Container
details_target = '<div class="meta-item"><span class="meta-label">Cámara</span><span class="meta-value" id="meta-cam">-</span></div>'
details_replacement = '<div class="meta-item"><span class="meta-label">Cámara</span><span class="meta-value" id="meta-cam">-</span></div>\n                    <div class="meta-item"><span class="meta-label">Nitidez IA</span><span class="meta-value sharpness-badge" id="meta-sharpness">-</span></div>'

content = content.replace(details_target, details_replacement)

duplicate_container_target = '<h3>Personas Detectadas</h3>'
duplicate_container_replacement = '<div id="duplicate-banner-container"></div>\n                <h3>Personas Detectadas</h3>'

content = content.replace(duplicate_container_target, duplicate_container_replacement)

# 2. Fix enableManualSelection to use document.addEventListener('mouseup') and focus dropdown
old_manual_fn_start = content.find("function enableManualSelection()")
old_manual_fn_end = content.find("function closeLightbox()", old_manual_fn_start)

new_manual_fn = """function enableManualSelection() {
            if (!currentFileObj) return;
            const container = document.getElementById('lb-media-container');
            const mediaEl = container.querySelector('.lb-media-element');
            if (!mediaEl) return;
            
            showToast("Arrastra sobre la foto para crear un recuadro de persona.");
            container.style.cursor = 'crosshair';
            
            let startX, startY, selectBox, isDrawing = false;
            
            const onMouseDown = (e) => {
                e.preventDefault();
                isDrawing = true;
                const rect = container.getBoundingClientRect();
                startX = e.clientX - rect.left;
                startY = e.clientY - rect.top;
                
                selectBox = document.createElement('div');
                selectBox.style.cssText = `position:absolute; left:${startX}px; top:${startY}px; border:2px dashed #30d158; background:rgba(48,209,88,0.25); pointer-events:none; z-index:9999;`;
                container.appendChild(selectBox);
                
                const onMouseMove = (ev) => {
                    if (!isDrawing) return;
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
                    if (!isDrawing) return;
                    isDrawing = false;
                    
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
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
                    
                    // Abrir y enfocar el desplegable inmediatamente en el sidebar
                    const select = document.getElementById(`pselect-${nextNum}`);
                    if (select) {
                        select.focus();
                        select.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                    showToast(`Recuadro #${nextNum} listo. Selecciona la persona en el panel lateral.`);
                };
                
                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            };
            
            container.addEventListener('mousedown', onMouseDown);
        }
"""

content = content[:old_manual_fn_start] + new_manual_fn + "\n\n" + content[old_manual_fn_end:]

# 3. Add Duplicate Check to openLightbox
open_lb_start = content.find("async function openLightbox(item)")
open_lb_end = content.find("async function runAnalysis()", open_lb_start)

new_open_lb = """async function openLightbox(item) {
            currentFileObj = item;
            isCurrentVideo = item.type === 'video';
            
            const container = document.getElementById('lb-media-container');
            container.innerHTML = '';
            document.getElementById('duplicate-banner-container').innerHTML = '';
            
            let mediaEl;
            if (isCurrentVideo) {
                mediaEl = document.createElement('video');
                mediaEl.src = `/media?path=${encodeURIComponent(item.path)}`;
                mediaEl.controls = true;
                mediaEl.autoplay = false;
                mediaEl.className = 'lb-media-element';
                if(window.liveScanTimestamp) {
                    mediaEl.currentTime = window.liveScanTimestamp;
                    window.liveScanTimestamp = null;
                }
                document.getElementById('analyze-toolbar').style.display = 'block';
            } else {
                mediaEl = document.createElement('img');
                mediaEl.src = `/media?path=${encodeURIComponent(item.path)}`;
                mediaEl.className = 'lb-media-element';
                document.getElementById('analyze-toolbar').style.display = 'none';
            }
            
            container.appendChild(mediaEl);
            document.getElementById('lightbox').classList.remove('hidden');
            
            // Metadatos
            fetch(`/api/metadata?path=${encodeURIComponent(item.path)}`)
                .then(r => r.json())
                .then(data => {
                    document.getElementById('meta-date').textContent = data.date || '-';
                    document.getElementById('meta-size').textContent = data.size || '-';
                    document.getElementById('meta-res').textContent = data.resolution || '-';
                    document.getElementById('meta-cam').textContent = data.camera || '-';
                });

            // IA de Nitidez y Duplicados
            fetch('/api/duplicates', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ path: item.path })
            })
            .then(r => r.json())
            .then(data => {
                const sharpEl = document.getElementById('meta-sharpness');
                if (sharpEl) sharpEl.textContent = data.sharpness ? `${data.sharpness} Score` : '-';
                
                const dupContainer = document.getElementById('duplicate-banner-container');
                if (data.duplicate && dupContainer) {
                    const dup = data.duplicate;
                    dupContainer.innerHTML = `
                        <div class="duplicate-banner">
                            <div class="duplicate-banner-title">⚠️ Foto Parecida (${dup.similarity}%)</div>
                            <div class="duplicate-banner-desc">
                                ${dup.is_current_better ? 
                                    `⭐ <strong>Top Shot:</strong> Esta foto tiene mayor nitidez (${data.sharpness} vs ${dup.other_sharpness}). Recomendado conservar.` : 
                                    `⚠️ Existe una versión más nítida de esta toma (<em>${dup.other_name}</em> - Nitidez: ${dup.other_sharpness} vs ${data.sharpness}).`}
                            </div>
                            ${!dup.is_current_better ? `<button class="duplicate-btn-delete" onclick="deleteCurrentFile()">🗑️ Borrar esta versión inferior</button>` : ''}
                        </div>
                    `;
                }
            });
                
            if (!isCurrentVideo) {
                if (mediaEl.complete) runAnalysis();
                else mediaEl.onload = () => runAnalysis();
            } else {
                document.getElementById('person-cards-container').innerHTML = '<p style="font-size:0.8rem; color:var(--text-dim);">Haz clic en "Analizar Caras" para escanear el fotograma.</p>';
            }
        }
"""

content = content[:open_lb_start] + new_open_lb + "\n\n" + content[open_lb_end:]

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("index.html actualizado con solución del arrastre global e IA de duplicados/nitidez.")
