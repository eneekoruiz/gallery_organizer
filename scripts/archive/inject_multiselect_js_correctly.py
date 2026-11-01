import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

multiselect_js = """
        let isMultiSelectMode = false;
        let selectedFiles = new Set();

        function toggleMultiSelectMode() {
            isMultiSelectMode = !isMultiSelectMode;
            const btn = document.getElementById('btn-toggle-multiselect');
            if (btn) {
                btn.style.background = isMultiSelectMode ? "#30d158" : "#5e5ce6";
                btn.textContent = isMultiSelectMode ? "✅ Selección Activa" : "☑️ Selección Múltiple";
            }
            if (!isMultiSelectMode) {
                clearBatchSelection();
            }
            if (typeof currentCat !== 'undefined' && typeof currentIdent !== 'undefined') {
                renderGrid(currentCat, currentIdent);
            }
            showToast(isMultiSelectMode ? "Modo Selección Múltiple ACTIVADO." : "Modo Selección Múltiple DESACTIVADO.");
        }

        function toggleFileSelection(filepath, cardEl, event) {
            if (event) event.stopPropagation();
            if (selectedFiles.has(filepath)) {
                selectedFiles.delete(filepath);
                cardEl.classList.remove('selected-card');
                cardEl.style.border = 'none';
                cardEl.style.boxShadow = 'none';
                const chk = cardEl.querySelector('.card-checkbox');
                if (chk) chk.checked = false;
            } else {
                selectedFiles.add(filepath);
                cardEl.classList.add('selected-card');
                cardEl.style.border = '3px solid #30d158';
                cardEl.style.boxShadow = '0 0 15px rgba(48,209,88,0.5)';
                const chk = cardEl.querySelector('.card-checkbox');
                if (chk) chk.checked = true;
            }
            updateBatchBar();
        }

        function updateBatchBar() {
            const bar = document.getElementById('batch-action-bar');
            const countEl = document.getElementById('batch-count');
            if (selectedFiles.size > 0) {
                bar.style.display = 'flex';
                countEl.textContent = `${selectedFiles.size} foto(s) seleccionada(s)`;
                
                const select = document.getElementById('batch-target-select');
                if (select && select.options.length <= 1 && typeof identitiesList !== 'undefined' && identitiesList.length > 0) {
                    select.innerHTML = '<option value="">Seleccionar carpeta destino...</option>';
                    identitiesList.forEach(id => {
                        const opt = document.createElement('option');
                        opt.value = JSON.stringify(id);
                        opt.textContent = `${id.categoria} > ${id.identidad}`;
                        select.appendChild(opt);
                    });
                }
            } else {
                bar.style.display = 'none';
            }
        }

        function clearBatchSelection() {
            selectedFiles.clear();
            document.querySelectorAll('.selected-card').forEach(el => {
                el.classList.remove('selected-card');
                el.style.border = 'none';
                el.style.boxShadow = 'none';
            });
            document.querySelectorAll('.card-checkbox').forEach(el => el.checked = false);
            updateBatchBar();
        }

        async function executeBatchMove() {
            if (selectedFiles.size === 0) return;
            const select = document.getElementById('batch-target-select');
            if (!select.value) {
                alert("Por favor, selecciona una carpeta destino.");
                return;
            }
            
            const target = JSON.parse(select.value);
            const filesArray = Array.from(selectedFiles);
            
            showToast(`🚀 Moviendo ${filesArray.length} fotos y re-entrenando IA...`);
            
            try {
                const res = await fetch('/api/batch_move', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        files: filesArray,
                        target_cat: target.categoria,
                        target_ident: target.identidad
                    })
                });
                const data = await res.json();
                
                if (data.status === 'success') {
                    showToast(`✅ ${data.moved} fotos movidas a ${target.identidad}. ¡Rostro re-entrenado automáticamente!`);
                    clearBatchSelection();
                    await loadGallery();
                    renderGrid(currentCat, currentIdent);
                } else {
                    alert("Error: " + (data.error || "No se pudieron mover las fotos"));
                }
            } catch (err) {
                alert("Error de conexión: " + err.message);
            }
        }
"""

if 'function toggleMultiSelectMode' not in html:
    html = html.replace('<script>', '<script>\n' + multiselect_js)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Injected multiselect JS functions right after <script> in index.html")
else:
    print("function toggleMultiSelectMode is already present in index.html")
