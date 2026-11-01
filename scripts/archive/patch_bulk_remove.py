import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Patch floating action bar HTML
old_fab_html = """        <button class="fab-btn" onclick="applyBulkReassign()" style="color:#0a84ff; font-weight:bold;">Aplicar</button>
        <button class="fab-btn" onclick="applyBulkIgnore()" style="color:#ff453a;">Ignorar Todo</button>"""

new_fab_html = """        <button class="fab-btn" onclick="applyBulkReassign()" style="color:#0a84ff; font-weight:bold;">Aplicar</button>
        <button class="fab-btn" onclick="applyBulkRemoveFromFolder()" style="color:#ff9f0a; font-weight:bold;">❌ Quitar de esta carpeta</button>
        <button class="fab-btn" onclick="applyBulkIgnore()" style="color:#ff453a;">Ignorar Todo</button>"""

if old_fab_html in content:
    content = content.replace(old_fab_html, new_fab_html)

# 2. Add applyBulkRemoveFromFolder JS function
bulk_remove_js = """
async function applyBulkRemoveFromFolder() {
    if (selectedPaths.size === 0) return;
    if (!currentCat || !currentIdent) {
        showToast("Abre un álbum específico primero.", true);
        return;
    }
    if (!confirm(`¿Seguro que quieres quitar las ${selectedPaths.size} fotos seleccionadas de '${currentIdent}' y enviarlas a re-análisis?`)) return;
    
    showToast(`⏳ Quitando ${selectedPaths.size} fotos de '${currentIdent}'...`);
    let count = 0;
    
    for (const path of Array.from(selectedPaths)) {
        try {
            const res = await fetch('/api/remove_from_folder', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    path: path,
                    cat: currentCat,
                    ident: currentIdent
                })
            });
            const data = await res.json();
            if (data.success) count++;
        } catch(e){}
    }
    
    showToast(`✅ ${count} fotos quitadas correctamente.`);
    clearSelection();
    await loadIdentities();
    await loadGallery();
}
"""

if 'function applyBulkRemoveFromFolder()' not in content:
    content = content.replace("</script>", bulk_remove_js + "\n</script>")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Injected applyBulkRemoveFromFolder into index.html")
