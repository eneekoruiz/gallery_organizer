// UI.JS - Zoom Controls, Toast, Multi-Select & Search Spotlight
let zoomLevel = 1.0;
let panX = 0;
let panY = 0;

window.zoomLevel = zoomLevel;
window.panX = panX;
window.panY = panY;

window.updateZoomDisplay = function(level) {
    const disp = document.getElementById('lb-zoom-display');
    if (disp) {
        disp.textContent = `${Math.round((level || 1.0) * 100)}%`;
    }
};

window.applyZoomLevel = function(newLevel, targetPanX, targetPanY) {
    const container = document.getElementById('lb-media-container');
    if (!container) return;
    
    zoomLevel = Math.min(16.0, Math.max(1.0, newLevel || 1.0));
    window.zoomLevel = zoomLevel;
    
    if (targetPanX !== undefined) { panX = targetPanX; window.panX = panX; }
    if (targetPanY !== undefined) { panY = targetPanY; window.panY = panY; }
    if (zoomLevel === 1.0) { panX = 0; panY = 0; window.panX = 0; window.panY = 0; }
    
    container.style.transform = `translate(${panX}px, ${panY}px) scale(${zoomLevel})`;
    container.style.setProperty('--inv-zoom', 1.0 / zoomLevel);
    window.updateZoomDisplay(zoomLevel);
};

window.zoomInLightbox = function() {
    window.applyZoomLevel(zoomLevel + 0.35);
};

window.zoomOutLightbox = function() {
    window.applyZoomLevel(Math.max(1.0, zoomLevel - 0.35));
};

window.toggleZoomStep = function() {
    if (zoomLevel < 1.4) {
        window.applyZoomLevel(2.0);
    } else if (zoomLevel < 2.9) {
        window.applyZoomLevel(4.0);
    } else {
        window.applyZoomLevel(1.0, 0, 0);
    }
};

window.resetZoom = function() {
    window.applyZoomLevel(1.0, 0, 0);
};

window.activeGridFilter = 'all';
window.activeGridSort = 'recent';

window.setPhotoFilter = function(filterType, btnEl) {
    window.activeGridFilter = filterType;
    document.querySelectorAll('.filter-toggle-btn').forEach(b => {
        b.classList.remove('active');
    });
    if (btnEl) btnEl.classList.add('active');
    
    const items = window.currentFolderItems || [];
    if (!items.length) return;
    
    let filtered = items;
    if (filterType === 'solo') {
        filtered = items.filter(it => it.is_solo || it.face_count === 1);
    } else if (filterType === 'group') {
        filtered = items.filter(it => it.is_group || it.face_count > 1);
    } else if (filterType === 'with_me') {
        filtered = items.filter(it => it.has_yo);
    } else if (filterType === 'without_me') {
        filtered = items.filter(it => !it.has_yo);
    }
    
    if (typeof window.renderFilteredChunk === 'function') {
        window.renderFilteredChunk(filtered);
    }
};

window.toggleHideBlurry = function(btnEl) {
    if (!btnEl) return;
    const isCurrentlyActive = btnEl.classList.contains('active');
    if (isCurrentlyActive) {
        btnEl.classList.remove('active');
        btnEl.style.background = 'transparent';
        window.setPhotoFilter('all');
    } else {
        btnEl.classList.add('active');
        btnEl.style.background = 'rgba(255,159,10,0.2)';
        const items = window.currentFolderItems || [];
        const sharpOnly = items.filter(it => (it.sharpness || 0) >= 30);
        if (typeof window.renderFilteredChunk === 'function') {
            window.renderFilteredChunk(sharpOnly);
        }
    }
};

window.showToast = function(message, isError = false) {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position:fixed; bottom:24px; right:24px; z-index:99999; display:flex; flex-direction:column; gap:8px; pointer-events:none;';
        document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.style.cssText = `background:${isError ? 'rgba(255,69,58,0.95)' : 'rgba(18,20,26,0.95)'}; color:#fff; padding:10px 18px; border-radius:10px; font-size:13px; font-weight:500; border:1px solid ${isError ? 'rgba(255,69,58,0.4)' : 'rgba(255,255,255,0.12)'}; backdrop-filter:blur(20px); box-shadow:0 8px 30px rgba(0,0,0,0.6); pointer-events:auto; transform:translateY(20px); opacity:0; transition:all 0.25s ease;`;
    toast.textContent = message;
    container.appendChild(toast);
    
    requestAnimationFrame(() => {
        toast.style.transform = 'translateY(0)';
        toast.style.opacity = '1';
    });
    
    setTimeout(() => {
        toast.style.transform = 'translateY(20px)';
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 250);
    }, 3500);
};

window.handleSpotlightSearch = function(query) {
    const dropdown = document.getElementById('spotlight-dropdown');
    if (!dropdown) return;
    const q = (query || '').trim().toLowerCase();
    if (!q) {
        dropdown.style.display = 'none';
        return;
    }
    
    const struct = window.galleryStructure || {};
    const matches = [];
    
    for (const cat in struct) {
        for (const ident in struct[cat]) {
            if (ident.toLowerCase().includes(q)) {
                matches.push({ cat, ident, count: struct[cat][ident] });
            }
        }
    }
    
    if (matches.length === 0) {
        dropdown.innerHTML = '<div style="padding:10px; color:#8e8e93; font-size:12px; text-align:center;">No se encontraron resultados</div>';
    } else {
        dropdown.innerHTML = matches.slice(0, 8).map(m => `
            <div style="display:flex; align-items:center; gap:10px; padding:8px 10px; border-radius:8px; cursor:pointer; transition:background 0.15s;"
                 onmouseover="this.style.background='rgba(255,255,255,0.08)'"
                 onmouseout="this.style.background='transparent'"
                 onclick="window.renderGrid('${m.cat.replace(/'/g, "\\'")}', '${m.ident.replace(/'/g, "\\'")}'); document.getElementById('spotlight-dropdown').style.display='none';">
                <img src="/api/person_avatar?cat=${encodeURIComponent(m.cat)}&ident=${encodeURIComponent(m.ident)}"
                     style="width:24px; height:24px; border-radius:50%; object-fit:cover; background:#222;"
                     onerror="this.style.display='none'">
                <div style="flex:1; min-width:0;">
                    <div style="font-size:12px; font-weight:600; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${m.ident}</div>
                    <div style="font-size:10px; color:#8e8e93;">${m.cat}</div>
                </div>
            </div>
        `).join('');
    }
    dropdown.style.display = 'block';
};

document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('spotlight-dropdown');
    const input = document.getElementById('top-search-input');
    if (dropdown && input && !dropdown.contains(e.target) && e.target !== input) {
        dropdown.style.display = 'none';
    }
});

// ============================================================
// SCREEN WAKE LOCK - Keep Mobile & Desktop Screen Awake
// ============================================================
window.wakeLockSentinel = null;
window.wakeLockEnabled = true;

window.requestWakeLock = async function(showToastNotice = false) {
    if (!window.wakeLockEnabled) return;
    try {
        if ('wakeLock' in navigator) {
            window.wakeLockSentinel = await navigator.wakeLock.request('screen');
            window.wakeLockSentinel.addEventListener('release', () => {
                console.log('📱 Screen Wake Lock released');
                window.updateWakeLockUI(false);
            });
            console.log('💡 Screen Wake Lock is active!');
            window.updateWakeLockUI(true);
            if (showToastNotice && typeof window.showToast === 'function') {
                window.showToast('💡 Pantalla activa: la pantalla de tu móvil no se apagará');
            }
        } else {
            console.log('Wake Lock API not supported; using fallback keep-awake');
            window.updateWakeLockUI(true);
        }
    } catch (err) {
        console.warn('Could not acquire wake lock:', err);
        window.updateWakeLockUI(false);
    }
};

window.releaseWakeLock = async function() {
    if (window.wakeLockSentinel !== null) {
        try {
            await window.wakeLockSentinel.release();
            window.wakeLockSentinel = null;
        } catch (e) {}
    }
    window.updateWakeLockUI(false);
    if (typeof window.showToast === 'function') {
        window.showToast('📱 Pantalla activa desactivada');
    }
};

window.toggleWakeLock = async function() {
    window.wakeLockEnabled = !window.wakeLockEnabled;
    if (window.wakeLockEnabled) {
        await window.requestWakeLock(true);
    } else {
        await window.releaseWakeLock();
    }
};

window.updateWakeLockUI = function(isActive) {
    const btn = document.getElementById('nav-btn-wakelock');
    const txt = document.getElementById('wakelock-text');
    const icon = document.getElementById('wakelock-icon');
    if (!btn) return;
    if (isActive) {
        btn.style.background = 'rgba(48,209,88,0.15)';
        btn.style.color = '#30d158';
        if (txt) txt.textContent = 'Pantalla Activa: ON';
        if (icon) icon.textContent = '💡';
    } else {
        btn.style.background = 'transparent';
        btn.style.color = '#8e8e93';
        if (txt) txt.textContent = 'Pantalla: OFF';
        if (icon) icon.textContent = '📱';
    }
};

// Re-acquire wake lock when tab becomes visible again
document.addEventListener('visibilitychange', async () => {
    if (window.wakeLockEnabled && document.visibilityState === 'visible') {
        await window.requestWakeLock(false);
    }
});

// Auto-request on first user gesture / touch for mobile browsers requiring gesture
['click', 'touchstart', 'scroll'].forEach(evtName => {
    window.addEventListener(evtName, () => {
        if (window.wakeLockEnabled && !window.wakeLockSentinel) {
            window.requestWakeLock(false);
        }
    }, { once: true, passive: true });
});

// Auto-activate on load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => window.requestWakeLock(false));
} else {
    window.requestWakeLock(false);
}

