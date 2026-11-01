import sys, re

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

modals_html = """
<!-- MODAL DUPLICADOS EXACTOS -->
<div id="modal-duplicates" class="modal" style="display:none; position:fixed; z-index:9999; left:0; top:0; width:100%; height:100%; background:rgba(0,0,0,0.85); backdrop-filter:blur(8px); justify-content:center; align-items:center;">
    <div style="background:#1c1c1e; border:1px solid #ff9f0a; border-radius:16px; padding:25px; width:90%; max-width:900px; max-height:85vh; overflow-y:auto; color:#fff; box-shadow:0 10px 40px rgba(0,0,0,0.8);">
        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #3a3a3c; padding-bottom:15px; margin-bottom:20px;">
            <h2 style="margin:0; color:#ff9f0a; font-size:1.4rem; display:flex; align-items:center; gap:10px;">👯 Limpieza de Duplicados Exactos</h2>
            <button onclick="closeExactDuplicatesModal()" style="background:none; border:none; color:#8e8e93; font-size:1.8rem; cursor:pointer;">&times;</button>
        </div>
        <div id="duplicates-loading" style="text-align:center; padding:40px;">
            <div class="loader-small" style="margin:0 auto 15px auto;"></div>
            <p style="color:#aaa;">Escaneando galería en busca de réplicas exactas byte a byte...</p>
        </div>
        <div id="duplicates-content" style="display:none;"></div>
    </div>
</div>

<!-- MODAL FOTOS PARECIDAS -->
<div id="modal-similar" class="modal" style="display:none; position:fixed; z-index:9999; left:0; top:0; width:100%; height:100%; background:rgba(0,0,0,0.85); backdrop-filter:blur(8px); justify-content:center; align-items:center;">
    <div style="background:#1c1c1e; border:1px solid #bf5af2; border-radius:16px; padding:25px; width:90%; max-width:900px; max-height:85vh; overflow-y:auto; color:#fff; box-shadow:0 10px 40px rgba(0,0,0,0.8);">
        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #3a3a3c; padding-bottom:15px; margin-bottom:20px;">
            <h2 style="margin:0; color:#bf5af2; font-size:1.4rem; display:flex; align-items:center; gap:10px;">📸 Fotos Parecidas y Ráfagas</h2>
            <button onclick="closeSimilarPhotosModal()" style="background:none; border:none; color:#8e8e93; font-size:1.8rem; cursor:pointer;">&times;</button>
        </div>
        <div id="similar-loading" style="text-align:center; padding:40px;">
            <div class="loader-small" style="margin:0 auto 15px auto;"></div>
            <p style="color:#aaa;">Analizando varianza de nitidez y similitud en secuencias...</p>
        </div>
        <div id="similar-content" style="display:none;"></div>
    </div>
</div>
"""

# Insert HTML modals before </body>
if 'id="modal-duplicates"' not in html:
    html = html.replace('</body>', modals_html + '\n</body>')
    print("✓ Added HTML modals for Duplicados and Fotos Parecidas!")

modals_js = """
// ==========================================
// FUNCIONES DE LIMPIEZA DE DUPLICADOS EXACTOS
// ==========================================
window.openExactDuplicatesModal = async function() {
    const m = document.getElementById('modal-duplicates');
    if (!m) return;
    m.style.display = 'flex';
    document.getElementById('duplicates-loading').style.display = 'block';
    document.getElementById('duplicates-content').style.display = 'none';
    
    try {
        const res = await fetch('/api/duplicates_scan');
        const data = await res.json();
        
        document.getElementById('duplicates-loading').style.display = 'none';
        const container = document.getElementById('duplicates-content');
        container.style.display = 'block';
        
        if (!data.groups || data.groups.length === 0) {
            container.innerHTML = `<div style="text-align:center; padding:30px; color:#30d158;">
                <h3>🎉 ¡No se han encontrado duplicados exactos!</h3>
                <p style="color:#aaa;">Tu galería está 100% libre de imágenes idénticas repetidas.</p>
            </div>`;
            return;
        }
        
        let htmlStr = `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; background:rgba(255,159,10,0.1); padding:15px; border-radius:10px; border:1px solid #ff9f0a;">
            <div>
                <strong style="color:#ff9f0a;">Se han detectado ${data.groups.length} grupos de duplicados exactos.</strong>
                <div style="font-size:0.9rem; color:#aaa;">Espacio recuperable: ${data.total_waste_mb} MB</div>
            </div>
            <button onclick="cleanAllExactDuplicates()" style="background:#ff9f0a; color:#000; font-weight:bold; border:none; padding:10px 18px; border-radius:8px; cursor:pointer;">
                ⚡ Limpiar Todos (${data.total_waste_mb} MB)
            </button>
        </div>`;
        
        data.groups.forEach((g, idx) => {
            htmlStr += `<div style="background:#2c2c2e; border-radius:12px; padding:15px; margin-bottom:15px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <span style="font-weight:bold; color:#ffcc00;">Grupo ${idx+1} (${g.files.length} copias idénticas - ${g.waste_mb} MB descartables)</span>
                    <button onclick="cleanExactDuplicatesGroup('${g.hash}')" style="background:rgba(255,159,10,0.2); color:#ff9f0a; border:1px solid #ff9f0a; padding:6px 12px; border-radius:6px; cursor:pointer; font-weight:bold;">
                        Conservar 1 y Borrar ${g.files.length-1}
                    </button>
                </div>
                <div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap:10px;">`;
            
            g.files.forEach((f, fIdx) => {
                htmlStr += `<div style="position:relative; background:#1c1c1e; border-radius:8px; overflow:hidden; border:2px solid ${fIdx===0?'#30d158':'#555'};">
                    <img src="/api/thumbnail?path=${encodeURIComponent(f.path)}" style="width:100%; height:110px; object-fit:cover;">
                    <div style="padding:5px; font-size:0.75rem; word-break:break-all; color:${fIdx===0?'#30d158':'#aaa'};">
                        ${fIdx===0?'⭐ CONSERVAR':`Copia ${fIdx}`} (${(f.size/1024/1024).toFixed(1)}MB)
                    </div>
                </div>`;
            });
            htmlStr += `</div></div>`;
        });
        
        container.innerHTML = htmlStr;
    } catch(e) {
        document.getElementById('duplicates-loading').style.display = 'none';
        alert("Error al escanear duplicados: " + e);
    }
};

window.closeExactDuplicatesModal = function() {
    const m = document.getElementById('modal-duplicates');
    if (m) m.style.display = 'none';
};

window.cleanExactDuplicatesGroup = async function(hash) {
    if (!confirm("¿Deseas eliminar las copias duplicadas de este grupo y conservar solo 1?")) return;
    try {
        const res = await fetch('/api/duplicates_clean', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ hash: hash })
        });
        const data = await res.json();
        if (data.success) {
            showToast("✅ Duplicados eliminados correctamente.");
            openExactDuplicatesModal();
            loadGallery();
        }
    } catch(e) { alert("Error de conexión"); }
};

window.cleanAllExactDuplicates = async function() {
    if (!confirm("¿Seguro que deseas eliminar automáticamente TODOS los duplicados exactos detectados y liberar espacio?")) return;
    try {
        const res = await fetch('/api/duplicates_clean', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ clean_all: true })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`🎉 ¡Limpieza masiva completada! Liberados ${data.freed_mb} MB.`);
            openExactDuplicatesModal();
            loadGallery();
        }
    } catch(e) { alert("Error de conexión"); }
};


// ==========================================
// FUNCIONES DE FOTOS PARECIDAS Y RÁFAGAS
// ==========================================
window.openSimilarPhotosModal = async function() {
    const m = document.getElementById('modal-similar');
    if (!m) return;
    m.style.display = 'flex';
    document.getElementById('similar-loading').style.display = 'block';
    document.getElementById('similar-content').style.display = 'none';
    
    try {
        const res = await fetch('/api/similar_scan');
        const data = await res.json();
        
        document.getElementById('similar-loading').style.display = 'none';
        const container = document.getElementById('similar-content');
        container.style.display = 'block';
        
        if (!data.groups || data.groups.length === 0) {
            container.innerHTML = `<div style="text-align:center; padding:30px; color:#30d158;">
                <h3>📸 ¡No hay ráfagas ni fotos muy parecidas acumuladas!</h3>
                <p style="color:#aaa;">Todas tus secuencias de fotos son únicas y nítidas.</p>
            </div>`;
            return;
        }
        
        let htmlStr = `<div style="margin-bottom:20px; background:rgba(191,90,242,0.1); padding:15px; border-radius:10px; border:1px solid #bf5af2;">
            <strong style="color:#bf5af2;">Se han detectado ${data.groups.length} ráfagas o secuencias de fotos parecidas.</strong>
            <div style="font-size:0.9rem; color:#aaa;">La IA ha evaluado la nitidez mediante la varianza de Laplaciano para destacar la foto de mejor calidad.</div>
        </div>`;
        
        data.groups.forEach((g, idx) => {
            htmlStr += `<div style="background:#2c2c2e; border-radius:12px; padding:15px; margin-bottom:15px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <span style="font-weight:bold; color:#d0fd38;">Secuencia ${idx+1} (${g.files.length} fotos del mismo momento)</span>
                    <button onclick="cleanSimilarGroup('${g.group_id}')" style="background:rgba(191,90,242,0.2); color:#bf5af2; border:1px solid #bf5af2; padding:6px 12px; border-radius:6px; cursor:pointer; font-weight:bold;">
                        Conservar la MÁS NÍTIDA y Borrar el Resto
                    </button>
                </div>
                <div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap:10px;">`;
            
            g.files.forEach((f) => {
                const isBest = f.is_sharpest;
                htmlStr += `<div style="position:relative; background:#1c1c1e; border-radius:8px; overflow:hidden; border:2px solid ${isBest?'#30d158':'#444'};">
                    <img src="/api/thumbnail?path=${encodeURIComponent(f.path)}" style="width:100%; height:110px; object-fit:cover;">
                    <div style="padding:5px; font-size:0.75rem; color:${isBest?'#30d158':'#aaa'}; font-weight:${isBest?'bold':'normal'};">
                        ${isBest?'⭐ MÁS NÍTIDA':`Simil (${f.sharpness_score}pt)`}
                    </div>
                </div>`;
            });
            htmlStr += `</div></div>`;
        });
        
        container.innerHTML = htmlStr;
    } catch(e) {
        document.getElementById('similar-loading').style.display = 'none';
        alert("Error al escanear fotos parecidas: " + e);
    }
};

window.closeSimilarPhotosModal = function() {
    const m = document.getElementById('modal-similar');
    if (m) m.style.display = 'none';
};

window.cleanSimilarGroup = async function(groupId) {
    if (!confirm("¿Deseas conservar únicamente la foto más nítida de esta secuencia y descartar las demás?")) return;
    try {
        const res = await fetch('/api/similar_clean', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ group_id: groupId })
        });
        const data = await res.json();
        if (data.success) {
            showToast("✅ Ráfaga optimizada conservando la foto más nítida.");
            openSimilarPhotosModal();
            loadGallery();
        }
    } catch(e) { alert("Error de conexión"); }
};
"""

# Insert JS before </script>
if 'window.openExactDuplicatesModal' not in html:
    html = html.replace('</script>', modals_js + '\n</script>')
    print("✓ Added JS handlers for openExactDuplicatesModal and openSimilarPhotosModal!")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✓ Successfully embedded modals and JS handlers into index.html!")
