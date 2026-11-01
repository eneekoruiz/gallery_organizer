// ============================================================
// SELECTION.JS - Multi-Selection & Floating Action Bar (FAB)
// ============================================================

window.isMultiSelectMode = false;
window.selectedMediaItems = new Set();
window.selectedFiles = window.selectedMediaItems;

function toggleSelection(path, cardEl) {
    if (!path) return;
    if (selectedMediaItems.has(path)) {
        selectedMediaItems.delete(path);
        if (cardEl) {
            cardEl.classList.remove('selected-card');
            cardEl.style.border = '';
            cardEl.style.boxShadow = '';
            const chk = cardEl.querySelector('.card-checkbox');
            if (chk) chk.checked = false;
        }
    } else {
        selectedMediaItems.add(path);
        if (cardEl) {
            cardEl.classList.add('selected-card');
            cardEl.style.border = '3px solid #30d158';
            cardEl.style.boxShadow = '0 0 15px rgba(48,209,88,0.5)';
            const chk = cardEl.querySelector('.card-checkbox');
            if (chk) chk.checked = true;
        }
    }
    updateFloatingBar();
}

function updateFloatingBar() {
    const fab = document.getElementById('floating-action-bar');
    const fabCount = document.getElementById('fab-count');
    if (!fab) return;
    
    const count = selectedMediaItems.size;
    if (count > 0) {
        fab.classList.add('visible');
        if (fabCount) fabCount.textContent = `${count} seleccionadas`;
        populateFabSelect();
    } else {
        fab.classList.remove('visible');
    }
}

function populateFabSelect() {
    const sel = document.getElementById('fab-target-select');
    if (!sel || !fullGallery) return;
    sel.innerHTML = '<option value="">Mover a...</option>';
    
    for (const cat in fullGallery) {
        const grp = document.createElement('optgroup');
        grp.label = cat;
        for (const ident in fullGallery[cat]) {
            const opt = document.createElement('option');
            opt.value = JSON.stringify({ cat, ident });
            opt.textContent = ident;
            grp.appendChild(opt);
        }
        sel.appendChild(grp);
    }
}

function clearSelection() {
    selectedMediaItems.clear();
    document.querySelectorAll('.selected-card').forEach(c => {
        c.classList.remove('selected-card');
        c.style.border = '';
        c.style.boxShadow = '';
    });
    document.querySelectorAll('.card-checkbox').forEach(c => c.checked = false);
    updateFloatingBar();
}

function performBulkAction(action) {
    if (selectedMediaItems.size === 0) return;
    const paths = Array.from(selectedMediaItems);
    
    if (action === 'delete') {
        if (!confirm(`Â¿Eliminar ${paths.length} fotos seleccionadas?`)) return;
        fetch('/api/delete_file', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ paths: paths, delete_mode: 'local' })
        }).then(r => r.json()).then(data => {
            if (typeof showToast === 'function') showToast(`âœ… ${paths.length} fotos eliminadas`);
            clearSelection();
            if (typeof loadGallery === 'function') loadGallery();
        });
    } else if (action === 'move') {
        const sel = document.getElementById('fab-target-select');
        if (!sel || !sel.value) {
            if (typeof showToast === 'function') showToast("âš ï¸ Selecciona un destino para mover", true);
            return;
        }
        const target = JSON.parse(sel.value);
        fetch('/api/batch_move', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                files: paths,
                target_cat: target.cat,
                target_ident: target.ident
            })
        }).then(r => r.json()).then(data => {
            if (typeof showToast === 'function') showToast(`âœ… ${paths.length} fotos movidas a ${target.ident}`);
            clearSelection();
            if (typeof loadGallery === 'function') loadGallery();
        });
    }
}

function applyBulkReassign(targetIdent) {
    if (selectedMediaItems.size === 0) return;
    const paths = Array.from(selectedMediaItems);
    let targetCat = 'Conocidos';
    for (const c in fullGallery) {
        if (fullGallery[c][targetIdent]) { targetCat = c; break; }
    }
    
    fetch('/api/batch_move', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            files: paths,
            target_cat: targetCat,
            target_ident: targetIdent
        })
    }).then(r => r.json()).then(data => {
        if (typeof showToast === 'function') showToast(`âœ… ${paths.length} fotos asignadas a ${targetIdent}`);
        clearSelection();
        if (typeof loadGallery === 'function') loadGallery();
    });
}

function applyBulkIgnore() {
    if (selectedMediaItems.size === 0) return;
    const paths = Array.from(selectedMediaItems);
    fetch('/api/batch_move', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            files: paths,
            target_cat: "Ignorar",
            target_ident: "Caras_Ignoradas"
        })
    }).then(r => r.json()).then(data => {
        if (typeof showToast === 'function') showToast(`âœ… ${paths.length} fotos ignoradas`);
        clearSelection();
        if (typeof loadGallery === 'function') loadGallery();
    });
}

function applyBulkRemoveFromFolder() {
    if (selectedMediaItems.size === 0 || !currentCat || !currentIdent) return;
    const paths = Array.from(selectedMediaItems);
    fetch('/api/batch_move', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            files: paths,
            target_cat: "ðŸ“‹ RevisiÃ³n / Por Organizar",
            target_ident: "Desconocidos"
        })
    }).then(r => r.json()).then(data => {
        if (typeof showToast === 'function') showToast(`âœ… ${paths.length} fotos quitadas del Ã¡lbum`);
        clearSelection();
        if (typeof loadGallery === 'function') loadGallery();
    });
}

function removeFromFolder(path, cat, ident) {
    fetch('/api/batch_move', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            files: [path],
            target_cat: "ðŸ“‹ RevisiÃ³n / Por Organizar",
            target_ident: "Desconocidos"
        })
    }).then(r => r.json()).then(data => {
        if (typeof showToast === 'function') showToast("âœ… Foto quitada del Ã¡lbum");
        if (typeof closeLightbox === 'function') closeLightbox();
        if (typeof loadGallery === 'function') loadGallery();
    });
}

window.toggleSelection = toggleSelection;
window.updateFloatingBar = updateFloatingBar;
window.populateFabSelect = populateFabSelect;
window.clearSelection = clearSelection;
window.performBulkAction = performBulkAction;
window.applyBulkReassign = applyBulkReassign;
window.applyBulkIgnore = applyBulkIgnore;
window.applyBulkRemoveFromFolder = applyBulkRemoveFromFolder;
window.removeFromFolder = removeFromFolder;