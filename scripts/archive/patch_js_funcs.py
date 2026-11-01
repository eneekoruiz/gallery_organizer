import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

js_to_add = """
// --- INJECTED FUNCTIONS ---
async function removeFromFolder() {
    if (!currentAnalysisPath || !currentCat || !currentIdent) return;
    if (!confirm(`¿Estás seguro de que quieres quitar esta foto de la carpeta de ${currentIdent}?`)) return;
    
    // showLoading();
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
        // hideLoading();
        
        if (data.success) {
            showToast("Foto quitada correctamente.");
            closeLightbox();
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
        // hideLoading();
        alert("Error de conexión");
    }
}

function triggerDeepScanLightbox() {
    if (!currentAnalysisPath) return;
    if (!confirm("Esto forzará una búsqueda exhaustiva de caras ignorando límites de confianza. ¿Continuar?")) return;
    
    // showLoading();
    fetch('/api/detect_deep', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({path: currentAnalysisPath})
    })
    .then(r => r.json())
    .then(data => {
        // hideLoading();
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
        // hideLoading();
        console.error(err);
    });
}

function toggleMetadata() {
    const sidebar = document.getElementById('metadata-panel');
    if (sidebar.style.display === 'none' || sidebar.style.display === '') {
        sidebar.style.display = 'block';
    } else {
        sidebar.style.display = 'none';
    }
}
// --- END INJECTED FUNCTIONS ---
"""

if 'removeFromFolder()' not in content:
    content = content.replace("</script>", js_to_add + "\n</script>")
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Injected JS functions successfully")
else:
    print("JS functions already present")
