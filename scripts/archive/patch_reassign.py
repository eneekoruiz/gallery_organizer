import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    app_content = f.read()

old_func = """
        async function quickReassignFace(selectEl, faceNum) {
            const face = currentFaces[faceNum - 1];
            if (!face) return;
            await inlineCorrect(encodeURIComponent(currentFileObj.path), selectEl.value, faceNum, face.x, face.y, face.width, face.height);
        }
"""
new_func = """
        async function quickReassignFace(valStr, faceNum) {
            const face = currentFaces[faceNum - 1];
            if (!face) return;
            await inlineCorrect(encodeURIComponent(currentFileObj.path), valStr, faceNum, face.x, face.y, face.width, face.height);
        }
"""

if old_func in app_content:
    app_content = app_content.replace(old_func, new_func)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(app_content)
    print("Patched quickReassignFace")
else:
    print("Could not find quickReassignFace")
