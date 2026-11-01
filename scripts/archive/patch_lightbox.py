import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Limpieza Global button with Quitar de esta carpeta and Detección Profunda
old_toolbar = """
            <div class="toolbar-right">
                <button class="icon-btn" onclick="runMassCleanup()" title="Limpieza Global: Reasigna automáticamente carpetas Persona Nueva a caras conocidas (Tarda unos minutos)">🧹 Limpieza Global</button>
                <button class="icon-btn" onclick="resetZoom()" title="Resetear Zoom">🔍 100%</button>
                <button class="icon-btn" onclick="toggleMetadata()" title="Info y Personas">ℹ️ Personas</button>
            </div>
"""

new_toolbar = """
            <div class="toolbar-right">
                <button class="icon-btn" onclick="removeFromFolder()" title="Quitar persona de esta carpeta" style="color: #ff453a; font-weight: bold;">❌ Quitar de esta carpeta</button>
                <button class="icon-btn" onclick="triggerDeepScanLightbox()" title="Forzar una búsqueda profunda de caras en esta foto" style="color: #0a84ff; font-weight: bold;">🔍 Detección Profunda</button>
                <button class="icon-btn" onclick="resetZoom()" title="Resetear Zoom">🔍 100%</button>
                <button class="icon-btn" onclick="toggleMetadata()" title="Info y Personas">ℹ️ Personas</button>
            </div>
"""
if old_toolbar in content:
    content = content.replace(old_toolbar, new_toolbar)
    print("Replaced toolbar in index.html")
else:
    print("Could not find toolbar in index.html to replace")

# Add removeFromFolder and triggerDeepScanLightbox functions
js_injections = """
async function removeFromFolder() {
    if (!currentAnalysisPath || !currentCat || !currentIdent) return;
    if (!confirm(`¿Estás seguro de que quieres quitar esta foto de la carpeta de ${currentIdent}?`)) return;
    
    showLoading();
    try {
        const res = await fetch('/api/remove_from_folder', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                path: currentAnalysisPath,
                cat: currentCat,
                ident: currentIdent
            })
        });
        const data = await res.json();
        hideLoading();
        
        if (data.success) {
            showToast("Foto quitada correctamente.");
            closeLightbox();
            // Remove from grid visually
            if (currentFolderItems) {
                const gridItem = document.getElementById('grid-container').children[currentItemIndex];
                if (gridItem) {
                    gridItem.style.opacity = '0.3';
                    gridItem.style.pointerEvents = 'none';
                }
            } else {
                location.reload();
            }
        } else {
            alert(data.error || "Error al quitar la foto");
        }
    } catch(e) {
        hideLoading();
        alert("Error de conexión");
    }
}

function triggerDeepScanLightbox() {
    if (!currentAnalysisPath) return;
    if (!confirm("Esto forzará una búsqueda exhaustiva de caras ignorando límites de confianza. ¿Continuar?")) return;
    
    showLoading();
    fetch('/api/detect_deep', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({path: currentAnalysisPath})
    })
    .then(r => r.json())
    .then(data => {
        hideLoading();
        if (data.error) {
            alert(data.error);
        } else if (!data.faces || data.faces.length === 0) {
            alert("No se ha encontrado ninguna persona, ni siquiera con la detección profunda.");
        } else {
            alert("¡Detección profunda exitosa! Recargando caras...");
            runAnalysis(currentAnalysisPath);
        }
    })
    .catch(err => {
        hideLoading();
        console.error(err);
    });
}
"""
content = content.replace('// Funciones Auxiliares', js_injections + '\n// Funciones Auxiliares')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
