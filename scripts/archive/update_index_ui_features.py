import sys, re

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Replace openStatsModal in templates/index.html
new_open_stats = """        async function openStatsModal() {
            document.getElementById('stats-modal').classList.remove('hidden');
            document.getElementById('stats-content').innerHTML = '<div style="text-align: center; padding: 20px;"><div class="loader-small"></div><p style="margin-top:10px; color:#aaa;">Cargando estadísticas completas de la galería...</p></div>';
            
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                
                if (data.error) {
                    document.getElementById('stats-content').innerHTML = `<p style="color:red">${data.error}</p>`;
                    return;
                }
                
                const percentage = data.total > 0 ? Math.round((data.clasificadas / data.total) * 100) : 0;
                
                document.getElementById('stats-content').innerHTML = `
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span>Total de fotos en la galería:</span>
                        <strong>${data.total}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; color: #30d158;">
                        <span>✏️ Ordenadas Oficialmente por Mí:</span>
                        <strong>${data.manual_user || 0}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; color: #0a84ff;">
                        <span>✨ Ordenadas Oficialmente por IA:</span>
                        <strong>${data.ia_verified || 0}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; color: #ff9f0a;">
                        <span>⚠️ Dudosas / Revisión:</span>
                        <strong>${data.dudosos || 0}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 20px; color: #ff453a;">
                        <span>❓ Sin Ordenar / Pendientes:</span>
                        <strong>${data.pendientes || 0}</strong>
                    </div>
                    
                    <div style="width: 100%; background-color: #333; border-radius: 10px; height: 20px; overflow: hidden;">
                        <div style="width: ${percentage}%; background-color: #30d158; height: 100%; text-align: center; font-size: 12px; line-height: 20px; color: black; font-weight: bold;">
                            ${percentage}%
                        </div>
                    </div>
                    <div style="text-align: center; font-size: 12px; color: #aaa; margin-top: 5px; margin-bottom: 20px;">Progreso Global de Clasificación</div>
                    
                    <h3 style="color: #0a84ff; font-size: 16px; margin-bottom: 10px; border-bottom: 1px solid #333; padding-bottom: 5px;">Desglose Completo por Álbum / Persona</h3>
                    <div style="max-height: 250px; overflow-y: auto; padding-right: 10px; font-size: 14px;" class="custom-scrollbar">
                        ${Object.entries(data.breakdown || {}).map(([name, count]) => `
                            <div style="display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #222;">
                                <span>${name}</span>
                                <span style="color: #aaa;">${count}</span>
                            </div>
                        `).join('')}
                    </div>
                `;
            } catch (err) {
                document.getElementById('stats-content').innerHTML = `<p style="color:red">Error al cargar estadísticas: ${err.message}</p>`;
            }
        }"""

# Replace old openStatsModal implementation
html = re.sub(r"async function openStatsModal\(\) \{[\s\S]*?\}\s*\}", new_open_stats, html)

# 2. Inject Multi-Select button into Header
multiselect_btn_html = """
                    <button id="btn-toggle-multiselect" class="premium-btn" onclick="toggleMultiSelectMode()" style="background:#5e5ce6; color:white; width:auto; padding:10px 18px;">
                        ☑️ Selección Múltiple
                    </button>
"""
if 'btn-toggle-multiselect' not in html:
    html = html.replace('<button id="btn-reanalyze"', multiselect_btn_html + '\n                    <button id="btn-reanalyze"')

# 3. Add Floating Batch Bar HTML before closing body tag
batch_bar_html = """
    <!-- Floating Batch Action Bar -->
    <div id="batch-action-bar" style="display:none; position:fixed; bottom:25px; left:50%; transform:translateX(-50%); z-index:9999; background:rgba(20,20,25,0.92); backdrop-filter:blur(20px); border:1px solid rgba(255,255,255,0.18); border-radius:16px; padding:12px 24px; box-shadow:0 12px 40px rgba(0,0,0,0.6); align-items:center; gap:16px;">
        <span id="batch-count" style="font-weight:bold; color:#30d158; font-size:14px;">0 seleccionadas</span>
        
        <select id="batch-target-select" style="background:#2c2c2e; color:white; border:1px solid #444; border-radius:8px; padding:8px 14px; font-size:13px; outline:none; max-width:220px;">
            <option value="">Seleccionar carpeta destino...</option>
        </select>
        
        <button onclick="executeBatchMove()" style="background:#30d158; color:black; font-weight:bold; border:none; border-radius:8px; padding:8px 18px; font-size:13px; cursor:pointer; transition:all 0.2s;">
            🚀 Mover y Entrenar IA
        </button>
        
        <button onclick="clearBatchSelection()" style="background:transparent; color:#888; border:none; font-size:16px; cursor:pointer; padding:4px 8px;">
            ✕
        </button>
    </div>
"""
if 'batch-action-bar' not in html:
    html = html.replace('</body>', batch_bar_html + '\n</body>')

# 4. Add Multi-Select JS Logic
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
            renderGrid(currentCat, currentIdent);
            showToast(isMultiSelectMode ? "Modo Selección Múltiple ACTIVADO." : "Modo Selección Múltiple DESACTIVADO.");
        }

        function toggleFileSelection(filepath, cardEl, event) {
            if (event) event.stopPropagation();
            if (selectedFiles.has(filepath)) {
                selectedFiles.delete(filepath);
                cardEl.classList.remove('selected-card');
                const chk = cardEl.querySelector('.card-checkbox');
                if (chk) chk.checked = false;
            } else {
                selectedFiles.add(filepath);
                cardEl.classList.add('selected-card');
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
                
                // Populate batch target select if empty
                const select = document.getElementById('batch-target-select');
                if (select && select.options.length <= 1 && identitiesList.length > 0) {
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
            document.querySelectorAll('.selected-card').forEach(el => el.classList.remove('selected-card'));
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

if 'toggleMultiSelectMode' not in html:
    html = html.replace('function renderGrid(cat, ident) {', multiselect_js + '\n        function renderGrid(cat, ident) {')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✓ Successfully updated index.html with stats modal & batch selection logic!")
