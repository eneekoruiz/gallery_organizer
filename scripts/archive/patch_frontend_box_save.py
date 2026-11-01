import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix isDragging = True to isDragging = true
content = content.replace("isDragging = True;", "isDragging = true;")

# Update saveBoxDimensions function
old_save_start = content.find("function saveBoxDimensions(")
old_save_end = content.find("async function inlineCorrect(", old_save_start)

new_save_fn = """function saveBoxDimensions(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl) {
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

            // Guardar permanentemente en backend y activar Reaprendizaje Activo
            if (face.identity && face.identity !== "Desconocido") {
                let folderName = currentFileObj.path.split(/[\\\\/]/).slice(-2, -1)[0];
                let categoryName = currentFileObj.path.split(/[\\\\/]/).slice(-3, -2)[0];
                
                fetch('/api/correct', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        path: currentFileObj.path,
                        new_categoria: categoryName,
                        new_identidad: face.identity,
                        face: {x: face.x, y: face.y, width: face.width, height: face.height}
                    })
                }).then(r => r.json()).then(data => {
                    if (data.success) {
                        showToast(`Recuadro #${faceNum} guardado y reaprendizaje activo.`);
                    }
                });
            }
        }
"""

content = content[:old_save_start] + new_save_fn + "\n\n" + content[old_save_end:]

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("index.html actualizado con guardado permanente de cajas y corrección isDragging.")
