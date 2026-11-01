import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

replacement = '''
                showToast(`Asignado a '${idObj.identidad}'. Memoria guardada.`);
                
                if (typeof applyToDuplicates !== 'undefined' && applyToDuplicates) {
                    closeLightbox();
                    loadGallery();
                } else {
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
                    if (currentCat && currentIdent) {
                        renderGrid(currentCat, currentIdent);
                    }
                }
'''

start_idx = content.find("showToast(`Asignado a '${idObj.identidad}'. Memoria guardada.`);")
end_idx = content.find("            } else {\n                showToast(data.error", start_idx)

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + replacement.strip() + '\n' + content[end_idx:]
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched inlineCorrect successfully.")
else:
    print("Could not find targets")
