import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Update runAnalysis to sync container size with mediaEl size
run_analysis_old = """            if (data.faces && data.faces.length > 0) {
                let intrinsicWidth = isCurrentVideo ? mediaEl.videoWidth : mediaEl.naturalWidth;
                let intrinsicHeight = isCurrentVideo ? mediaEl.videoHeight : mediaEl.naturalHeight;
                if (!intrinsicWidth && data.faces.length > 0) {
                    intrinsicWidth = data.faces[0].img_width;
                    intrinsicHeight = data.faces[0].img_height;
                }
                
                data.faces.forEach((face, idx) => {
                    createFaceElements(face, idx + 1, intrinsicWidth, intrinsicHeight, mediaEl, container, cardsContainer);
                });
            }"""

run_analysis_new = """            if (data.faces && data.faces.length > 0) {
                let intrinsicWidth = isCurrentVideo ? mediaEl.videoWidth : mediaEl.naturalWidth;
                let intrinsicHeight = isCurrentVideo ? mediaEl.videoHeight : mediaEl.naturalHeight;
                if (!intrinsicWidth && data.faces.length > 0) {
                    intrinsicWidth = data.faces[0].img_width;
                    intrinsicHeight = data.faces[0].img_height;
                }
                
                // Sincronizar tamaño del contenedor con el tamaño real de la imagen renderizada
                if (mediaEl.clientWidth && mediaEl.clientHeight) {
                    container.style.width = mediaEl.clientWidth + 'px';
                    container.style.height = mediaEl.clientHeight + 'px';
                }
                
                data.faces.forEach((face, idx) => {
                    createFaceElements(face, idx + 1, intrinsicWidth, intrinsicHeight, mediaEl, container, cardsContainer);
                });
            }"""

content = content.replace(run_analysis_old, run_analysis_new)

# Update confidence label in createFaceElements to indicate ✏️ Editado a mano
conf_label_old = '<div class="person-confidence" id="pconf-${faceNum}">${face.confidence || \'Asignación manual\'}</div>'
conf_label_new = '<div class="person-confidence" id="pconf-${faceNum}">${face.confidence ? (face.confidence.includes(\'Manual\') ? \'✏️ Editado a Mano\' : face.confidence) : \'✏️ Editado a Mano\'}</div>'

content = content.replace(conf_label_old, conf_label_new)

# Update saveBoxDimensions scale calculation to use mediaEl.getBoundingClientRect()
save_dim_old = """function saveBoxDimensions(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl) {
            const container = document.getElementById('lb-media-container');
            const rect = box.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();

            const scaleX = intrinsicWidth / containerRect.width;
            const scaleY = intrinsicHeight / containerRect.height;

            face.x = Math.round((rect.left - containerRect.left) * scaleX);
            face.y = Math.round((rect.top - containerRect.top) * scaleY);
            face.width = Math.round(rect.width * scaleX);
            face.height = Math.round(rect.height * scaleY);"""

save_dim_new = """function saveBoxDimensions(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl) {
            const container = document.getElementById('lb-media-container');
            const rect = box.getBoundingClientRect();
            const mediaRect = mediaEl.getBoundingClientRect();

            const scaleX = intrinsicWidth / mediaRect.width;
            const scaleY = intrinsicHeight / mediaRect.height;

            face.x = Math.round((rect.left - mediaRect.left) * scaleX);
            face.y = Math.round((rect.top - mediaRect.top) * scaleY);
            face.width = Math.round(rect.width * scaleX);
            face.height = Math.round(rect.height * scaleY);"""

content = content.replace(save_dim_old, save_dim_new)

# Update manual selection scale calculation
manual_scale_old = """const scaleX = intrinsicWidth / rect.width;
                    const scaleY = intrinsicHeight / rect.height;"""

manual_scale_new = """const mediaRect = mediaEl.getBoundingClientRect();
                    const scaleX = intrinsicWidth / mediaRect.width;
                    const scaleY = intrinsicHeight / mediaRect.height;"""

content = content.replace(manual_scale_old, manual_scale_new)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("index.html actualizado con alineación milimétrica sobre la foto real e indicador ✏️ Editado a Mano.")
