import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add spinner in runAnalysis
old_run_analysis_start = """async function runAnalysis(mediaEl, container) {
            if (!currentFileObj) return;
            
            const timestamp = isCurrentVideo ? mediaEl.currentTime : null;
            
            const res = await fetch('/api/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ path: currentFileObj.path, timestamp: timestamp })
            });"""

new_run_analysis_start = """async function runAnalysis(mediaEl, container) {
            if (!currentFileObj) return;
            
            const timestamp = isCurrentVideo ? mediaEl.currentTime : null;
            const cardsContainer = document.getElementById('person-cards-container');
            if (cardsContainer) {
                cardsContainer.innerHTML = `<div style="padding:25px; text-align:center; color:#0a84ff;">
                    <div style="display:inline-block; width:30px; height:30px; border:3px solid rgba(10,132,255,0.3); border-top-color:#0a84ff; border-radius:50%; animation:spin 0.8s linear infinite;"></div>
                    <p style="margin-top:12px; font-weight:bold; font-size:0.85rem;">⏳ Analizando fotograma con IA...</p>
                </div>`;
            }
            
            const res = await fetch('/api/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ path: currentFileObj.path, timestamp: timestamp })
            });"""

content = content.replace(old_run_analysis_start, new_run_analysis_start)

# 2. Add animation keyframes for spinner in HTML head or style
if '@keyframes spin' not in content:
    content = content.replace('</head>', '<style>@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>\n</head>')

# 3. Replace renameCurrentGroup to show interactive Merge Modal
old_rename_fn = """        async function renameCurrentGroup() {
            if (!currentCat || !currentIdent || currentCat !== 'Personas Sin Nombre') return;
            const newName = prompt(`Introduce el nombre real de la persona para las ${currentFolderItems.length} fotos de '${currentIdent}':`);
            if (!newName) return;
            
            const res = await fetch('/api/rename_group', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    cat: currentCat,
                    ident: currentIdent,
                    new_name: newName,
                    new_cat: 'Conocidos'
                })
            });
            const data = await res.json();
            if (data.success) {
                showToast(`¡Fantástico! Se han movido ${data.count} fotos a 'Conocidos / ${newName}'.`);
                await loadIdentities();
                await loadGallery();
                renderGrid('Conocidos', newName);
            } else {
                showToast(data.error || "No se pudo renombrar el grupo.", true);
            }
        }"""

new_rename_fn = """        function renameCurrentGroup() {
            if (!currentCat || !currentIdent || currentCat !== 'Personas Sin Nombre') return;
            
            const selectEl = document.getElementById('merge-existing-select');
            selectEl.innerHTML = '<option value="">-- Selecciona una persona existente --</option>';
            
            identitiesList.forEach(id => {
                if (id.categoria === 'Conocidos') {
                    const opt = document.createElement('option');
                    opt.value = id.identidad;
                    opt.textContent = id.identidad;
                    selectEl.appendChild(opt);
                }
            });
            
            document.getElementById('merge-count-span').textContent = currentFolderItems.length;
            document.getElementById('merge-group-name').textContent = currentIdent;
            document.getElementById('merge-new-input').value = '';
            document.getElementById('modal-merge').style.display = 'flex';
        }

        function closeMergeModal() {
            document.getElementById('modal-merge').style.display = 'none';
        }

        async function submitMergeGroup() {
            const existingName = document.getElementById('merge-existing-select').value;
            const newName = document.getElementById('merge-new-input').value.trim();
            
            const targetName = existingName || newName;
            if (!targetName) {
                alert("Por favor, selecciona una persona existente o introduce un nombre nuevo.");
                return;
            }
            
            closeMergeModal();
            showToast(`⏳ Fusionando ${currentFolderItems.length} fotos con '${targetName}' y reentrenando IA...`);
            
            const res = await fetch('/api/rename_group', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    cat: currentCat,
                    ident: currentIdent,
                    new_name: targetName,
                    new_cat: 'Conocidos'
                })
            });
            const data = await res.json();
            if (data.success) {
                showToast(`🎉 ¡Fusionado con éxito! Se unieron ${data.count} fotos a 'Conocidos / ${targetName}' y se reentrenó el modelo IA.`);
                await loadIdentities();
                await loadGallery();
                renderGrid('Conocidos', targetName);
            } else {
                showToast(data.error || "No se pudo fusionar el grupo.", true);
            }
        }"""

content = content.replace(old_rename_fn, new_rename_fn)

# 4. Add Modal HTML before </body>
modal_html = """
    <!-- Modal de Fusión / Renombrado de Grupo -->
    <div id="modal-merge" style="display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.85); backdrop-filter:blur(15px); z-index:9999; align-items:center; justify-content:center;">
        <div style="background:rgba(28,28,30,0.95); border:1px solid rgba(255,255,255,0.2); border-radius:18px; padding:25px; width:440px; max-width:90%; box-shadow:0 20px 50px rgba(0,0,0,0.8); color:white;">
            <h2 style="margin-top:0; font-size:1.25rem;">🤝 Fusionar o Renombrar Grupo</h2>
            <p style="font-size:0.85rem; color:#aaa; margin-bottom:20px;">
                Asigna las <strong id="merge-count-span">3</strong> fotos de '<span id="merge-group-name">Persona Nueva</span>' a una persona de tu galería para mejorar el aprendizaje IA:
            </p>
            
            <div style="margin-bottom:15px;">
                <label style="display:block; font-size:0.8rem; font-weight:bold; margin-bottom:6px; color:#30d158;">
                    🔗 Opción A: Fusionar con persona ya existente
                </label>
                <select id="merge-existing-select" style="width:100%; padding:10px; border-radius:8px; background:#2c2c2e; border:1px solid #444; color:white; font-size:0.9rem;">
                    <option value="">-- Selecciona persona --</option>
                </select>
            </div>
            
            <div style="text-align:center; font-size:0.8rem; color:#666; margin:10px 0;">— O BIEN —</div>
            
            <div style="margin-bottom:20px;">
                <label style="display:block; font-size:0.8rem; font-weight:bold; margin-bottom:6px; color:#0a84ff;">
                    ✨ Opción B: Crear una persona nueva
                </label>
                <input type="text" id="merge-new-input" placeholder="Nombre de la nueva persona..." style="width:100%; padding:10px; border-radius:8px; background:#2c2c2e; border:1px solid #444; color:white; font-size:0.9rem; box-sizing:border-box;">
            </div>
            
            <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:20px;">
                <button onclick="closeMergeModal()" style="background:transparent; border:none; color:#aaa; padding:10px 16px; font-size:0.9rem; cursor:pointer;">Cancelar</button>
                <button onclick="submitMergeGroup()" style="background:#30d158; color:white; border:none; padding:10px 20px; border-radius:8px; font-weight:bold; font-size:0.9rem; cursor:pointer;">🚀 Aplicar Fusión / Guardar</button>
            </div>
        </div>
    </div>
"""

content = content.replace('</body>', modal_html + '\n</body>')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("templates/index.html actualizado con Modal de Fusión estilo Apple y Loader de vídeo.")
