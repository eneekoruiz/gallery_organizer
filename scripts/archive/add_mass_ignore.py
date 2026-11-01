import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

target = '<h3>PERSONAS DETECTADAS</h3>'
btn_code = '''
            <div id="lb-faces-cards"></div>
            <button id="btn-ignore-unconfirmed" onclick="ignoreUnconfirmedFaces()" style="margin-top: 15px; width: 100%; padding: 10px; background-color: #ff453a; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; display: none;">
                🗑️ Ignorar caras no confirmadas
            </button>
'''
if 'id="lb-faces-cards"></div>' in content:
    content = content.replace('<div id="lb-faces-cards"></div>', btn_code.strip())
    print("Injected button!")
else:
    print("Could not find target")

js_code = '''
        async function ignoreUnconfirmedFaces() {
            if (!currentFaces || currentFaces.length === 0) return;
            
            // Collect unconfirmed faces
            const unconfirmed = [];
            currentFaces.forEach((face, idx) => {
                if (face.identity === 'Desconocido' || face.identity.startsWith('IA (Pendiente)')) {
                    unconfirmed.push({ face: face, faceNum: idx + 1 });
                }
            });
            
            if (unconfirmed.length === 0) {
                showToast("No hay caras sin confirmar.");
                return;
            }
            
            if (!confirm(`¿Ignorar ${unconfirmed.length} caras no confirmadas?`)) return;
            
            document.getElementById('btn-ignore-unconfirmed').textContent = "Ignorando...";
            document.getElementById('btn-ignore-unconfirmed').style.opacity = '0.5';
            document.getElementById('btn-ignore-unconfirmed').style.pointerEvents = 'none';
            
            for (let i = 0; i < unconfirmed.length; i++) {
                const item = unconfirmed[i];
                const face = item.face;
                let idObj = {categoria: "Ignorar", identidad: "Ignorar_Irrelevante"};
                
                try {
                    const res = await fetch('/api/correct', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ 
                            path: currentFileObj.path, 
                            new_categoria: idObj.categoria, 
                            new_identidad: idObj.identidad,
                            face: {x: face.box[0], y: face.box[1], width: face.box[2], height: face.box[3]},
                            apply_to_duplicates: false
                        })
                    });
                    const data = await res.json();
                    if(data.success && data.new_path && currentFileObj) {
                        currentFileObj.path = data.new_path;
                    }
                } catch(e) {
                    console.error("Error ignoring face", e);
                }
            }
            
            showToast(`${unconfirmed.length} caras ignoradas.`);
            
            // Refresh
            if (currentCat === 'Limpieza Inteligente') {
                const gridItem = document.getElementById('grid-container').children[currentItemIndex];
                if (gridItem) {
                    gridItem.style.opacity = '0.3';
                    gridItem.style.pointerEvents = 'none';
                }
            } else if (currentCat && currentIdent) {
                renderGrid(currentCat, currentIdent);
            }
            
            // Re-open lightbox to refresh faces list
            openLightbox(currentFileObj);
        }
'''

js_target = 'async function inlineCorrect'
if js_target in content:
    content = content.replace(js_target, js_code + '\n        ' + js_target)
    print("Injected JS!")
else:
    print("Could not find JS target")

# Also need to show/hide the button if there are unconfirmed faces
show_btn_logic = '''
                let hasUnconfirmed = false;
                data.faces.forEach((face, idx) => {
                    if (face.identity === 'Desconocido' || face.identity.startsWith('IA (Pendiente)')) hasUnconfirmed = true;
                    createFaceElements(face, idx + 1, intrinsicWidth, intrinsicHeight, mediaEl, container, cardsContainer);
                });
                
                const btnIgnore = document.getElementById('btn-ignore-unconfirmed');
                if (btnIgnore) {
                    if (hasUnconfirmed) {
                        btnIgnore.style.display = 'block';
                        btnIgnore.textContent = "🗑️ Ignorar caras no confirmadas";
                        btnIgnore.style.opacity = '1';
                        btnIgnore.style.pointerEvents = 'auto';
                    } else {
                        btnIgnore.style.display = 'none';
                    }
                }
'''

show_btn_target = '''
                data.faces.forEach((face, idx) => {
                    createFaceElements(face, idx + 1, intrinsicWidth, intrinsicHeight, mediaEl, container, cardsContainer);
                });
'''

if show_btn_target in content:
    content = content.replace(show_btn_target, show_btn_logic)
    print("Injected Show/Hide button logic!")
else:
    print("Could not find show button target")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
