import re
import subprocess
import os

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

start_idx = content.find('function enableManualSelection()')
if start_idx == -1:
    start_idx = content.find('               function enableManualSelection()')
    
end_idx = content.find('</script>', start_idx)

new_code = """        function enableManualSelection() {
            if (!currentFileObj) return;
            const container = document.getElementById('lb-media-container');
            const mediaEl = container.querySelector('.lb-media-element');
            if (!mediaEl) return;
            
            mediaEl.draggable = false;
            
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
                    
                    let isCurrentVideo = mediaEl.tagName === 'VIDEO';
                    let intrinsicWidth = isCurrentVideo ? mediaEl.videoWidth : mediaEl.naturalWidth;
                    let intrinsicHeight = isCurrentVideo ? mediaEl.videoHeight : mediaEl.naturalHeight;
                    
                    const mediaRect = mediaEl.getBoundingClientRect();
                    const containerRect = container.getBoundingClientRect();
                    
                    const offsetX = mediaRect.left - containerRect.left;
                    const offsetY = mediaRect.top - containerRect.top;
                    
                    const mediaStartX = startX - offsetX;
                    const mediaStartY = startY - offsetY;
                    const mediaEndX = endX - offsetX;
                    const mediaEndY = endY - offsetY;
                    
                    const scaleX = intrinsicWidth / mediaRect.width;
                    const scaleY = intrinsicHeight / mediaRect.height;
                    
                    let realX = Math.round(Math.min(mediaStartX, mediaEndX) * scaleX);
                    let realY = Math.round(Math.min(mediaStartY, mediaEndY) * scaleY);
                    let realW = Math.round(boxW * scaleX);
                    let realH = Math.round(boxH * scaleY);
                    
                    realX = Math.max(0, realX);
                    realY = Math.max(0, realY);
                    if (realX + realW > intrinsicWidth) realW = intrinsicWidth - realX;
                    if (realY + realH > intrinsicHeight) realH = intrinsicHeight - realY;
                    
                    const newFace = { x: realX, y: realY, width: realW, height: realH, identity: "Desconocido", confidence: "Selección manual" };
                    const nextNum = document.querySelectorAll('.lb-bounding-box').length + 1;
                    const cardsContainer = document.getElementById('person-cards-container');
                    
                    createFaceElements(newFace, nextNum, intrinsicWidth, intrinsicHeight, mediaEl, container, cardsContainer);
                    highlightFace(nextNum);
                    
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

        async function runMassCleanup() {
            if (!confirm('¿Deseas analizar todas las carpetas "Persona Nueva" y reasignar automáticamente a las caras conocidas (seguridad > 60%)? Esto puede tardar unos minutos.')) return;
            
            showToast('Iniciando limpieza masiva... Por favor, no cierres esta página.', false);
            
            try {
                const res = await fetch('/api/mass_cleanup', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    showToast(`✅ Limpieza masiva completada. Se reasignaron ${data.moved_count} imágenes.`);
                    await loadGallery();
                } else {
                    showToast('Error en la limpieza masiva: ' + data.error, true);
                }
            } catch (err) {
                showToast('Error de conexión en limpieza masiva', true);
            }
        }
"""

content = content[:start_idx] + new_code + content[end_idx:]

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

with open('temp.js', 'w', encoding='utf-8') as out:
    out.write(content[content.find('<script>')+8 : content.rfind('</script>')])

result = subprocess.run(['node', '-c', 'temp.js'], capture_output=True, text=True)
if result.returncode != 0:
    print('Error in syntax:')
    print(result.stderr)
else:
    print('Syntax OK!')
os.remove('temp.js')
