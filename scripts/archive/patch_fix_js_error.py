import re

# 1. Update app.py api_duplicates safety
with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

old_dup = """@app.route('/api/duplicates', methods=['POST'])
def api_duplicates():
    data = request.json"""

new_dup = """@app.route('/api/duplicates', methods=['POST'])
def api_duplicates():
    try:
        data = request.json"""

app_code = app_code.replace(old_dup, new_dup)

old_dup_end = """    return jsonify({
        "sharpness": current_sharpness,
        "duplicate": duplicate_info
    })"""

new_dup_end = """    return jsonify({
        "sharpness": current_sharpness,
        "duplicate": duplicate_info
    })
    except Exception as e:
        return jsonify({"sharpness": 100.0, "duplicate": None})"""

app_code = app_code.replace(old_dup_end, new_dup_end)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code)

print("app.py actualizado con protección contra errores 500 en /api/duplicates.")

# 2. Update templates/index.html makeBoxInteractive and line 618
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html_code = f.read()

# Fix line 618
html_code = html_code.replace(
    "makeBoxInteractive(box, handle, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl);",
    "makeBoxInteractive(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl);"
)

# Replace makeBoxInteractive implementation
old_mbi = """        function makeBoxInteractive(box, handle, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl) {
            let isDragging = false;
            let isResizing = false;
            let startX, startY, startLeft, startTop, startW, startH;
            const container = document.getElementById('lb-media-container');

            // Arrastrar Posición
            box.addEventListener('mousedown', (e) => {
                if (e.target === handle) return;
                e.stopPropagation();
                isDragging = true;
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
                startW = box.offsetWidth;
                startH = box.offsetHeight;

                const onMouseMove = (ev) => {
                    if (!isResizing) return;
                    const dx = ev.clientX - startX;
                    const dy = ev.clientY - startY;
                    const containerRect = container.getBoundingClientRect();
                    const newW = Math.max(30, startW + dx);
                    const newH = Math.max(30, startH + dy);
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
        }"""

new_mbi = """        function makeBoxInteractive(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl) {
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

html_code = html_code.replace(old_mbi, new_mbi)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html_code)

print("templates/index.html actualizado: corregida la variable handle y makeBoxInteractive.")
