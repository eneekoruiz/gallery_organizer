import re

# 1. Update templates/index.html to fix makeBoxInteractive signature & add Video Timestamps
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html_code = f.read()

# Fix makeBoxInteractive signature
old_sig = "function makeBoxInteractive(box, handle, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl) {"
new_sig = "function makeBoxInteractive(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl) {"

html_code = html_code.replace(old_sig, new_sig)

# Fix handle.addEventListener in old block if present
old_handle_block = """            // Redimensionar Tamaño
            handle.addEventListener('mousedown', (e) => {"""

if old_handle_block in html_code:
    # Replace entire old makeBoxInteractive with clean version
    clean_mbi = """        function makeBoxInteractive(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl) {
            let isDragging = false;
            let activeCorner = null;
            let startX, startY, startLeft, startTop, startW, startH;
            const container = document.getElementById('lb-media-container');

            box.addEventListener('mousedown', (e) => {
                if (e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION' || e.target.tagName === 'BUTTON') return;
                
                const handle = e.target.closest('.resize-handle');
                if (handle) {
                    activeCorner = handle.dataset.corner;
                } else {
                    isDragging = true;
                }
                
                e.stopPropagation();
                startX = e.clientX;
                startY = e.clientY;
                const rect = box.getBoundingClientRect();
                const containerRect = container.getBoundingClientRect();
                startLeft = rect.left - containerRect.left;
                startTop = rect.top - containerRect.top;
                startW = rect.width;
                startH = rect.height;
                
                highlightFace(faceNum);

                const onMouseMove = (ev) => {
                    if (!isDragging && !activeCorner) return;
                    const dx = ev.clientX - startX;
                    const dy = ev.clientY - startY;

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
                        document.removeEventListener('mousemove', onMouseMove);
                        document.removeEventListener('mouseup', onMouseUp);
                        saveBoxDimensions(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl);
                    }
                };

                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            });
        }"""
        
    start_pos = html_code.find("function makeBoxInteractive(")
    end_pos = html_code.find("function updateAvatarCrop(", start_pos)
    if start_pos != -1 and end_pos != -1:
        html_code = html_code[:start_pos] + clean_mbi + "\n\n        " + html_code[end_pos:]

# Add timestamp badge in video sidebar
old_card_info = """<div class="person-name" id="pname-${faceNum}">#${faceNum} ${face.identity}</div>"""

new_card_info = """<div class="person-name" id="pname-${faceNum}">#${faceNum} ${face.identity}</div>
${isCurrentVideo ? `<button onclick="jumpToVideoTime(${data_ts_val})" style="margin-top:4px; background:rgba(10,132,255,0.2); color:#0a84ff; border:1px solid #0a84ff; padding:3px 8px; border-radius:6px; font-size:0.75rem; font-weight:bold; cursor:pointer;">⏱️ Saltar al Minuto/Segundo ${formatTime(data_ts_val)}</button>` : ''}"""

# Fix video playback in openLightbox
old_video_elem = """const video = document.createElement('video');
                video.src = '/api/raw?path=' + encodeURIComponent(fileObj.path);
                video.controls = true;
                video.className = 'lb-media-element';"""

new_video_elem = """const video = document.createElement('video');
                video.src = '/api/raw?path=' + encodeURIComponent(fileObj.path);
                video.controls = true;
                video.preload = 'metadata';
                video.playsInline = true;
                video.className = 'lb-media-element';
                video.onloadedmetadata = () => {
                    if (video.duration > 0) {
                        video.currentTime = Math.min(1.0, video.duration / 2);
                    }
                };"""

html_code = html_code.replace(old_video_elem, new_video_elem)

# Add jumpToVideoTime and formatTime helper functions
helper_fns = """
        function formatTime(seconds) {
            if (!seconds && seconds !== 0) return "00:00";
            const m = Math.floor(seconds / 60);
            const s = Math.floor(seconds % 60);
            return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
        }

        function jumpToVideoTime(timeSec) {
            const mediaEl = document.querySelector('.lb-media-element');
            if (mediaEl && mediaEl.tagName === 'VIDEO') {
                mediaEl.currentTime = timeSec;
                mediaEl.play();
                runAnalysis(mediaEl, document.getElementById('lb-media-container'));
                showToast(`⏱️ Saltando al minuto/segundo ${formatTime(timeSec)}...`);
            }
        }
"""

if 'function jumpToVideoTime' not in html_code:
    html_code = html_code.replace('function closeLightbox() {', helper_fns + '\nfunction closeLightbox() {')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html_code)

print("templates/index.html actualizado: corregida la firma de makeBoxInteractive, añadido botón de salto a minuto/segundo en vídeos y arreglada la reproducción.")
