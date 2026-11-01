// ============================================================
// MODALS.JS - Modals and Dialog Controllers
// ============================================================

window.currentActiveSuggestion = null;

window.openMergeModal = function() {
    const modal = document.getElementById('modal-merge');
    if (modal) modal.style.display = 'flex';
};

window.closeMergeModal = function() {
    const modal = document.getElementById('modal-merge');
    if (modal) modal.style.display = 'none';
};

window.closeSimilarPhotosModal = function() {
    const modal = document.getElementById('modal-similar');
    if (modal) modal.style.display = 'none';
};

window.closeExactDuplicatesModal = function() {
    const modal = document.getElementById('modal-duplicates');
    if (modal) modal.style.display = 'none';
};

window.closeSuggestionPreviewModal = function() {
    const modal = document.getElementById('modal-suggestion-preview');
    if (modal) modal.style.display = 'none';
    window.currentActiveSuggestion = null;
};

window.openSuggestionPreviewModal = function(sug) {
    window.currentActiveSuggestion = sug;
    const modal = document.getElementById('modal-suggestion-preview');
    if (!modal) return;

    const srcImg = document.getElementById('sug-source-img');
    const tgtImg = document.getElementById('sug-target-img');
    const srcName = document.getElementById('sug-source-name');
    const tgtName = document.getElementById('sug-target-name');
    const simBadge = document.getElementById('sug-similarity-badge');
    const srcCount = document.getElementById('sug-source-count');
    const tgtCount = document.getElementById('sug-target-count');

    const pct = Math.round((sug.similarity || 0.85) * 100);

    if (srcName) srcName.textContent = sug.source || 'Persona Nueva';
    if (tgtName) tgtName.textContent = sug.target || 'Identidad';
    if (simBadge) simBadge.textContent = `${pct}% Coincidencia`;
    if (srcCount) srcCount.textContent = `${sug.source_count || 1} fotos`;
    if (tgtCount) tgtCount.textContent = `${sug.target_count || 1} fotos`;

    const srcCat = sug.source_cat || 'Personas Sin Nombre';
    const tgtCat = sug.target_cat || 'Conocidos';

    if (srcImg) srcImg.src = `/api/person_avatar?ident=${encodeURIComponent(sug.source)}&cat=${encodeURIComponent(srcCat)}&t=${Date.now()}`;
    if (tgtImg) tgtImg.src = `/api/person_avatar?ident=${encodeURIComponent(sug.target)}&cat=${encodeURIComponent(tgtCat)}&t=${Date.now()}`;

    modal.style.display = 'flex';
};

window.confirmSuggestionMergeDirect = async function() {
    const sug = window.currentActiveSuggestion;
    if (!sug) return;

    const btn = document.getElementById('btn-sug-confirm-merge');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="loader-small" style="display:inline-block; width:14px; height:14px; vertical-align:middle; margin-right:6px;"></span> Fusionando...';
    }

    try {
        const res = await fetch('/api/suggest_merges_execute', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ source: sug.source, target: sug.target })
        });
        const data = await res.json();

        if (data.success) {
            if (typeof showToast === 'function') showToast(`🎉 ¡${sug.source} fusionado con éxito en ${sug.target}!`);
            window.closeSuggestionPreviewModal();
            if (typeof loadGallery === 'function') loadGallery();
            if (typeof window.loadSidebarIASuggestions === 'function') {
                setTimeout(window.loadSidebarIASuggestions, 500);
            }
        } else {
            if (typeof showToast === 'function') showToast(`Error al fusionar: ${data.error || 'Desconocido'}`, true);
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '✅ Confirmar Fusión';
            }
        }
    } catch (err) {
        if (typeof showToast === 'function') showToast('Error de conexión al procesar fusión', true);
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '✅ Confirmar Fusión';
        }
    }
};

window.viewSuggestionSourcePhotos = function() {
    const sug = window.currentActiveSuggestion;
    if (!sug) return;
    window.closeSuggestionPreviewModal();
    const cat = sug.source_cat || 'Personas Sin Nombre';
    if (typeof renderGrid === 'function') {
        renderGrid(cat, sug.source);
    }
};

window.openStatsModal = async function() {
    const modal = document.getElementById('stats-modal');
    if (!modal) return;
    modal.style.display = 'flex';
    const content = document.getElementById('stats-content');
    if (content) {
        content.innerHTML = '<div style="text-align:center; padding:30px;"><div class="loader-small" style="margin:auto;"></div><p style="margin-top:10px; color:#8e8e93;">Calculando estadísticas...</p></div>';
    }
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        if (content) {
            const percentage = data.total > 0 ? Math.round((data.clasificadas / data.total) * 100) : 0;
            content.innerHTML = `
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:14px;">
                    <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); padding:12px; border-radius:10px; text-align:center;">
                        <div style="font-size:11px; color:#8e8e93; font-weight:700; text-transform:uppercase;">Total Fotos</div>
                        <div style="font-size:22px; font-weight:800; color:#fff; margin-top:2px;">${data.total || 0}</div>
                    </div>
                    <div style="background:rgba(48,209,88,0.1); border:1px solid rgba(48,209,88,0.25); padding:12px; border-radius:10px; text-align:center;">
                        <div style="font-size:11px; color:#30d158; font-weight:700; text-transform:uppercase;">Clasificadas</div>
                        <div style="font-size:22px; font-weight:800; color:#30d158; margin-top:2px;">${data.clasificadas || 0} <span style="font-size:12px;">(${percentage}%)</span></div>
                    </div>
                </div>
                <div style="width:100%; background:rgba(255,255,255,0.08); border-radius:8px; height:12px; overflow:hidden; margin-bottom:16px;">
                    <div style="width:${percentage}%; background:#30d158; height:100%;"></div>
                </div>
            `;
        }
    } catch(err) {
        if (content) content.innerHTML = '<div style="color:#ff453a; text-align:center;">Error al cargar estadísticas</div>';
    }
};

window.closeStatsModal = function() {
    const modal = document.getElementById('stats-modal');
    if (modal) modal.style.display = 'none';
};

window.toggleSettingsDrawer = function(open) {
    const drawer = document.getElementById('settings-drawer');
    const overlay = document.getElementById('drawer-overlay');
    if (drawer && overlay) {
        drawer.style.display = open ? 'block' : 'none';
        overlay.style.display = open ? 'block' : 'none';
    }
};

window.openEventsMapModal = function() {
    const modal = document.getElementById('modal-events-map');
    if (modal) modal.style.display = 'flex';
};

window.closeEventsMapModal = function() {
    const modal = document.getElementById('modal-events-map');
    if (modal) modal.style.display = 'none';
};
