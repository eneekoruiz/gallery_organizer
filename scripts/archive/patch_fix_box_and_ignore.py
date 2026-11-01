import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Clean box.onclick leftover code
old_box_leftover = """                let innerHtml = `
                    <div style="color:white; font-size:0.75rem; text-align:center; opacity:0.7; padding-bottom:4px; border-bottom:1px solid rgba(255,255,255,0.1); margin-bottom:4px;">Face #${faceNum}</div>
                `;
    if (folderName && categoryName && folderName !== 'Resultados' && categoryName !== 'Galeria Eneko NO ABRIR') {
                if (!aiPredictedIdObj) {
                    let suggestedId = {categoria: categoryName, identidad: folderName};
                    selectOptionsHtml += `<option value='${JSON.stringify(suggestedId)}' style="font-weight:bold; color:#30d158;">✨ Sí, es (Dueño): ${folderName}</option>`;
                }
            }
            innerHtml += generateReassignHTML(face, faceNum, 'quickReassignFace');"""

new_box_clean = """                let innerHtml = `
                    <div style="color:white; font-size:0.75rem; text-align:center; opacity:0.7; padding-bottom:4px; border-bottom:1px solid rgba(255,255,255,0.1); margin-bottom:4px;">Face #${faceNum}</div>
                `;
                innerHtml += generateReassignHTML(face, faceNum, 'quickReassignFace');"""

if old_box_leftover in content:
    content = content.replace(old_box_leftover, new_box_clean)
    print("Cleaned box.onclick leftover code")

# 2. Fix face.box in ignoreUnconfirmedFaces
old_face_box = """face: {x: face.box[0], y: face.box[1], width: face.box[2], height: face.box[3]}"""

new_face_box = """face: {
                            x: face.box ? face.box[0] : (face.x || 0),
                            y: face.box ? face.box[1] : (face.y || 0),
                            width: face.box ? face.box[2] : (face.width || 0),
                            height: face.box ? face.box[3] : (face.height || 0)
                        }"""

if old_face_box in content:
    content = content.replace(old_face_box, new_face_box)
    print("Fixed face.box in ignoreUnconfirmedFaces")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
