import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Add Sidebar Buttons
sidebar_btns = """
        <div style="margin-top: 10px; margin-bottom: 10px; font-weight: bold; color: #ff9f0a; text-align: center; border: 1px solid #ff9f0a; border-radius: 8px; padding: 10px; cursor: pointer; background: rgba(255,159,10,0.1);" onclick="openExactDuplicatesModal()">
            👯 Limpieza de Duplicados Exactos
        </div>
        <div style="margin-bottom: 10px; font-weight: bold; color: #bf5af2; text-align: center; border: 1px solid #bf5af2; border-radius: 8px; padding: 10px; cursor: pointer; background: rgba(191,90,242,0.1);" onclick="openSimilarPhotosModal()">
            📸 Fotos Parecidas y Ráfagas
        </div>
"""

if 'openExactDuplicatesModal()' not in html:
    html = html.replace('<div style="margin-top: 10px; margin-bottom: 10px; font-weight: bold; color: #0a84ff;', sidebar_btns + '\n        <div style="margin-top: 10px; margin-bottom: 10px; font-weight: bold; color: #0a84ff;')

# 2. Add Modals HTML
modals_html = """
    <!-- Modal Duplicados Exactos -->
    <div id="modal-duplicates" class="modal hidden">
        <div class="modal-content" style="max-width: 850px;">
            <div class="modal-header">
                <h2>👯 Limpieza de Duplicados Exactos</h2>
                <button class="icon-btn" onclick="document.getElementById('modal-duplicates').classList.add('hidden')">✕</button>
            </div>
            <div id="duplicates-content" style="padding: 15px 0;">
                <div class="loader-small"></div> Escaneando duplicados idénticos...
            </div>
        </div>
    </div>

    <!-- Modal Fotos Parecidas -->
    <div id="modal-similar" class="modal hidden">
        <div class="modal-content" style="max-width: 850px;">
            <div class="modal-header">
                <h2>📸 Limpieza de Fotos Parecidas y Ráfagas</h2>
                <button class="icon-btn" onclick="document.getElementById('modal-similar').classList.add('hidden')">✕</button>
            </div>
            <div id="similar-content" style="padding: 15px 0;">
                <div class="loader-small"></div> Analizando nitidez de ráfagas con IA...
            </div>
        </div>
    </div>
"""

if 'modal-duplicates' not in html:
    html = html.replace('</body>', modals_html + '\n</body>')

# 3. Add JS Functions
cleaners_js = """
        // ==========================================
        // 👯 INTERACTIVE DUPLICATES & BURST CLEANERS
        // ==========================================
        let currentDuplicateGroups = [];

        async function openExactDuplicatesModal() {
            document.getElementById('modal-duplicates').classList.remove('hidden');
            const container = document.getElementById('duplicates-content');
            container.innerHTML = '<div style="text-align:center; padding:30px;"><div class="loader-small"></div><p style="margin-top:10px; color:#aaa;">Escaneando duplicados idénticos en la galería...</p></div>';
            
            try {
                const res = await fetch('/api/duplicates_scan');
                const data = await res.json();
                currentDuplicateGroups = data.groups || [];
                
                if (currentDuplicateGroups.length === 0) {
                    container.innerHTML = '<div style="text-align:center; padding:30px; color:#30d158;">🎉 ¡Felicidades! No se han encontrado fotos ni vídeos duplicados exactos.</div>';
                    return;
                }
                
                container.innerHTML = `
                    <div style="background:rgba(255,159,10,0.12); border:1px solid #ff9f0a; border-radius:12px; padding:15px; margin-bottom:20px; display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <h3 style="margin:0; color:#ff9f0a; font-size:16px;">Se han detectado ${data.total_groups} grupos de duplicados</h3>
                            <p style="margin:4px 0 0 0; font-size:13px; color:#ccc;">Puedes recuperar hasta <strong style="color:#30d158;">${data.reclaimable_gb}</strong> conservando 1 copia de cada uno.</p>
                        </div>
                        <button onclick="cleanAllExactDuplicates()" style="background:#ff9f0a; color:black; font-weight:bold; border:none; border-radius:8px; padding:10px 18px; cursor:pointer; font-size:13px;">
                            ⚡ Conservar solo 1 copia de cada grupo
                        </button>
                    </div>

                    <div style="max-height:480px; overflow-y:auto; padding-right:8px;" class="custom-scrollbar">
                        ${currentDuplicateGroups.map((g, gIdx) => `
                            <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.1); border-radius:10px; padding:12px; margin-bottom:12px;">
                                <div style="display:flex; justify-content:space-between; margin-bottom:10px; font-size:13px;">
                                    <span>Grupo #${gIdx+1} - Liberable: <strong style="color:#30d158;">${g.reclaimable_mb}</strong></span>
                                </div>
                                <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(140px, 1fr)); gap:10px;">
                                    ${g.files.map(f => `
                                        <div style="background:#1c1c1e; border-radius:8px; padding:6px; position:relative; text-align:center;">
                                            ${f.is_keeper ? '<span style="position:absolute; top:4px; left:4px; background:#30d158; color:black; font-weight:bold; font-size:10px; padding:2px 6px; border-radius:4px;">CONSERVADA</span>' : ''}
                                            <img src="/api/thumbnail?path=${encodeURIComponent(f.path)}" style="width:100%; height:90px; object-fit:cover; border-radius:6px; margin-bottom:4px;">
                                            <div style="font-size:10px; color:#aaa; word-break:break-all;">${f.name}</div>
                                            <div style="font-size:10px; color:#666;">${f.size_mb}</div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `;
            } catch (err) {
                container.innerHTML = `<p style="color:red">Error: ${err.message}</p>`;
            }
        }

        async function cleanAllExactDuplicates() {
            if (!confirm("¿Deseas eliminar automáticamente las copias duplicadas de todos los grupos y conservar solo 1 copia principal de cada una?")) return;
            
            let filesToDelete = [];
            currentDuplicateGroups.forEach(g => {
                g.files.forEach((f, idx) => {
                    if (idx > 0) filesToDelete.push(f.path);
                });
            });
            
            showToast(`⚡ Eliminando ${filesToDelete.length} duplicados exactos...`);
            
            try {
                const res = await fetch('/api/duplicates_clean', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ files: filesToDelete })
                });
                const data = await res.json();
                showToast(`✅ ¡Proceso completado! Se han liberado ${data.freed_gb} de disco duro.`);
                document.getElementById('modal-duplicates').classList.add('hidden');
                await loadGallery();
            } catch (err) {
                alert("Error al limpiar duplicados: " + err.message);
            }
        }

        async function openSimilarPhotosModal() {
            document.getElementById('modal-similar').classList.remove('hidden');
            const container = document.getElementById('similar-content');
            container.innerHTML = '<div style="text-align:center; padding:30px;"><div class="loader-small"></div><p style="margin-top:10px; color:#aaa;">Analizando ráfagas y nivel de nitidez por IA...</p></div>';
            
            try {
                const res = await fetch('/api/similar_scan');
                const data = await res.json();
                const bursts = data.bursts || [];
                
                if (bursts.length === 0) {
                    container.innerHTML = '<div style="text-align:center; padding:30px; color:#30d158;">🎉 No se han encontrado ráfagas ni fotos parecidas para optimizar.</div>';
                    return;
                }
                
                container.innerHTML = `
                    <div style="background:rgba(191,90,242,0.12); border:1px solid #bf5af2; border-radius:12px; padding:15px; margin-bottom:20px; display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <h3 style="margin:0; color:#bf5af2; font-size:16px;">Se han detectado ${data.total_burst_groups} grupos de ráfagas</h3>
                            <p style="margin:4px 0 0 0; font-size:13px; color:#ccc;">La IA ha calculado la nitidez de cada foto para recomendarte la mejor.</p>
                        </div>
                    </div>

                    <div style="max-height:480px; overflow-y:auto; padding-right:8px;" class="custom-scrollbar">
                        ${bursts.map((b, bIdx) => `
                            <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.1); border-radius:10px; padding:12px; margin-bottom:12px;">
                                <div style="display:flex; justify-content:space-between; margin-bottom:10px; font-size:13px;">
                                    <span>Carpeta: <strong style="color:#bf5af2;">${b.folder}</strong> (${b.count} fotos parecidas)</span>
                                </div>
                                <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(150px, 1fr)); gap:10px;">
                                    ${b.files.map(f => `
                                        <div style="background:#1c1c1e; border-radius:8px; padding:6px; position:relative; text-align:center;">
                                            ${f.is_sharpest ? '<span style="position:absolute; top:4px; left:4px; background:#bf5af2; color:white; font-weight:bold; font-size:10px; padding:2px 6px; border-radius:4px;">⭐ MÁS NÍTIDA</span>' : ''}
                                            <img src="/api/thumbnail?path=${encodeURIComponent(f.path)}" style="width:100%; height:95px; object-fit:cover; border-radius:6px; margin-bottom:4px;">
                                            <div style="font-size:10px; color:#aaa; word-break:break-all;">${f.name}</div>
                                            <div style="font-size:10px; color:${f.is_sharpest ? '#bf5af2':'#666'}; font-weight:bold;">Nitidez IA: ${f.sharpness}</div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `;
            } catch (err) {
                container.innerHTML = `<p style="color:red">Error: ${err.message}</p>`;
            }
        }
"""

if 'openExactDuplicatesModal()' not in html:
    html = html.replace('<script>', '<script>\n' + cleaners_js)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Injected cleaner modals and JS functions into index.html")
else:
    print("Cleaner JS functions already present in index.html")
