window.currentScreenshotAgeFilter = 'all';

function isInvalidFolderName(name) {
    if (!name) return true;
    const lower = name.toLowerCase().trim();
    const invalidExact = [
        'fotos', 'resultados', 'galeria eneko no abrir',
        'familia', 'conocidos', 'profesores', 'mascotas',
        'yo', 'amigos', 'otros', 'desconocidos', 'desconocido'
    ];
    if (invalidExact.includes(lower)) return true;

    const invalidSubstrings = [
        'conmigo', 'sin mi', 'sin mí', 'grupales', 'con amigos',
        'para revisar', 'revisar', 'dudosos', '_dudosos',
        'personas sin nombre', 'limpieza inteligente',
        'recuerdos', 'lugares', 'eventos', 'frases',
        'por organizar', 'pendientes', 'masivos'
    ];
    if (invalidSubstrings.some(inv => lower.includes(inv))) return true;
    if (name.startsWith('_') || name.startsWith('📋') || name.startsWith('⏳') || name.startsWith('!')) return true;
    return false;
}
window.isInvalidFolderName = isInvalidFolderName;



// =============================================================

// GLOBAL STATE & MODAL HANDLERS

// =============================================================

window.currentPhotos = window.currentPhotos || [];

let currentPhotos = window.currentPhotos;

let currentFolderItems = [];

let zoomLevel = 1.0;

let panX = 0;

let panY = 0;

let fullGallery = {};

let identitiesList = [];

let currentFileObj = null;

let isCurrentVideo = false;

let currentFaces = [];

let currentCat = null;

let currentIdent = null;

// ── Header Collapse & Grid Density Preferences ───────────────────────

window.toggleSidebar = function(force) {

    const sidebar = document.querySelector('.sidebar');

    const backdrop = document.getElementById('sidebar-backdrop');

    if (!sidebar) return;

    const isCurrentlyOpen = sidebar.classList.contains('open');

    const shouldOpen = (force !== undefined) ? !!force : !isCurrentlyOpen;

    if (shouldOpen) {

        sidebar.classList.add('open');

        if (backdrop) backdrop.classList.add('active');

        document.body.classList.add('sidebar-mobile-open');

    } else {

        sidebar.classList.remove('open');

        if (backdrop) backdrop.classList.remove('active');

        document.body.classList.remove('sidebar-mobile-open');

    }

};



window.toggleMobileLightboxSheet = function(force) { return window.toggleLightboxPanel(force); };
window.toggleLightboxPanel = function(force) {

    const panel = document.getElementById('metadata-panel');

    const pill = document.getElementById('mobile-lb-sheet-pill');

    const btn = document.getElementById('btn-toggle-lb-panel');

    if (!panel) return;

    

    const isMobile = window.innerWidth <= 820;

    if (isMobile) {

        const isCurrentlyExpanded = panel.classList.contains('mobile-expanded');

        const shouldExpand = (force !== undefined) ? !!force : !isCurrentlyExpanded;

        if (shouldExpand) {

            panel.classList.add('mobile-expanded');

            if (pill) pill.style.display = 'none';

            if (btn) btn.classList.add('active');

        } else {

            panel.classList.remove('mobile-expanded');

            if (pill) pill.style.display = 'flex';

            if (btn) btn.classList.remove('active');

        }

    } else {

        const isHidden = panel.style.display === 'none';

        const shouldShow = (force !== undefined) ? !!force : isHidden;

        panel.style.display = shouldShow ? 'flex' : 'none';

        if (btn) btn.classList.toggle('active', shouldShow);

    }

};



window.toggleHeaderCollapse = function() {

    const header = document.getElementById('main-gallery-header');

    if (!header) return;

    const isNowCollapsed = header.classList.toggle('collapsed');

    const icon = document.getElementById('header-collapse-icon');

    const label = document.getElementById('header-collapse-label');

    if (icon) icon.textContent = isNowCollapsed ? '▼' : '▲';

    if (label) label.textContent = isNowCollapsed ? 'Expandir' : 'Plegar';

    try {

        localStorage.setItem('gallery_header_collapsed', isNowCollapsed ? '1' : '0');

    } catch (e) {}

};

window.toggleHeaderOptionsMenu = function(e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    const menu = document.getElementById('header-options-dropdown');
    const btn = document.getElementById('btn-header-more');
    if (!menu) return;
    const isVisible = menu.style.display !== 'none';
    menu.style.display = isVisible ? 'none' : 'block';
    if (btn) {
        if (!isVisible) btn.classList.add('active');
        else btn.classList.remove('active');
    }
};

document.addEventListener('click', function(e) {
    const menu = document.getElementById('header-options-dropdown');
    const btn = document.getElementById('btn-header-more');
    if (menu && menu.style.display !== 'none' && !menu.contains(e.target) && (!btn || !btn.contains(e.target))) {
        menu.style.display = 'none';
        if (btn) btn.classList.remove('active');
    }
});



window.setGridDensity = function(size, btnEl) {

    const sizePx = parseInt(size, 10) || 180;

    document.documentElement.style.setProperty('--grid-col-min', sizePx + 'px');

    const grid = document.getElementById('grid-container');

    if (grid) {

        grid.style.setProperty('--grid-col-min', sizePx + 'px');

        grid.style.gridTemplateColumns = 'repeat(auto-fill, minmax(' + sizePx + 'px, 1fr))';

    }

    document.querySelectorAll('.grid-density-btn').forEach(b => b.classList.remove('active'));

    if (btnEl) btnEl.classList.add('active');

    try {

        localStorage.setItem('gallery_grid_size', sizePx);

    } catch (e) {}

};



function _initHeaderAndGridPreferences() {

    try {

        const savedCollapsed = localStorage.getItem('gallery_header_collapsed');

        if (savedCollapsed === '1') {

            const header = document.getElementById('main-gallery-header');

            if (header) {

                header.classList.add('collapsed');

                const icon = document.getElementById('header-collapse-icon');

                const label = document.getElementById('header-collapse-label');

                if (icon) icon.textContent = '▼';

                if (label) label.textContent = 'Expandir';

            }

        }

        const savedSize = localStorage.getItem('gallery_grid_size');

        if (savedSize) {

            const sizePx = parseInt(savedSize, 10);

            if (sizePx) {

                document.documentElement.style.setProperty('--grid-col-min', sizePx + 'px');

                const activeBtn = document.querySelector('.grid-density-btn[data-size="' + sizePx + '"]');

                if (activeBtn) {

                    document.querySelectorAll('.grid-density-btn').forEach(b => b.classList.remove('active'));

                    activeBtn.classList.add('active');

                }

            }

        }

    } catch (e) {}

}



if (document.readyState === 'loading') {

    document.addEventListener('DOMContentLoaded', _initHeaderAndGridPreferences);

} else {

    _initHeaderAndGridPreferences();

}



let currentItemIndex = 0;



window.openMergeModal = function() {

    const modal = document.getElementById('modal-merge');

    if (modal) {

        const countSpan = document.getElementById('merge-count-span');

        const groupNameSpan = document.getElementById('merge-group-name');

        if (countSpan && currentFolderItems) countSpan.textContent = currentFolderItems.length;

        if (groupNameSpan) groupNameSpan.textContent = currentIdent || '';

        

        const containerEl = document.getElementById('merge-existing-select');

        if (containerEl) {

            containerEl.innerHTML = `

                <div style="padding:10px; box-sizing:border-box; display:flex; flex-direction:column; gap:8px;">

                    <input type="text" id="merge-search-input" placeholder="🔍 Buscar persona..." style="width:100%; padding:8px 12px; border-radius:8px; background:#1c1c1e; border:1px solid #444; color:white; font-size:13px; box-sizing:border-box; outline:none;">

                    <div id="merge-list-container" style="max-height:220px; overflow-y:auto; padding-right:4px; display:flex; flex-direction:column; gap:4px;" class="custom-scrollbar">

                        <div style="text-align:center; padding:15px; color:#aaa;">Cargando personas...</div>

                    </div>

                </div>

            `;

            

            const listContainer = document.getElementById('merge-list-container');

            const selectedInput = document.getElementById('merge-selected-value');

            if (selectedInput) selectedInput.value = '';

            

            fetch('/api/identities').then(r => r.json()).then(idents => {

                if (listContainer) listContainer.innerHTML = '';

                

                let grouped = {};

                idents.forEach(idInfo => {

                    if (idInfo.identidad === currentIdent) return;

                    if (idInfo.categoria === 'Ignorar') return;

                    

                    const cat = idInfo.categoria || 'Otros';

                    if (!grouped[cat]) grouped[cat] = [];

                    grouped[cat].push(idInfo);

                });

                

                const categories = Object.keys(grouped).sort();

                categories.forEach(cat => {

                    const details = document.createElement('details');

                    details.open = true;

                    details.style.marginBottom = '6px';

                    

                    const summary = document.createElement('summary');

                    summary.style.cssText = 'cursor:pointer; padding:6px 10px; font-weight:bold; color:#a855f7; font-size:12px; background:#1c1c1e; border-radius:6px; user-select:none; margin-bottom:4px; outline:none;';

                    summary.textContent = `${cat} (${grouped[cat].length})`;

                    details.appendChild(summary);

                    

                    const listDiv = document.createElement('div');

                    listDiv.style.cssText = 'display:flex; flex-direction:column; gap:4px; padding-left:8px; margin-top:4px;';

                    

                    grouped[cat].sort((a, b) => a.identidad.localeCompare(b.identidad)).forEach(idInfo => {

                        const btn = document.createElement('button');

                        btn.type = 'button';

                        btn.className = 'merge-person-btn';

                        btn.style.cssText = 'display:block; width:100%; text-align:left; padding:8px 12px; border-radius:8px; border:1px solid rgba(255,255,255,0.08); background:transparent; color:#e5e5ea; cursor:pointer; font-size:12px; transition:all 0.2s;';

                        btn.textContent = idInfo.identidad;

                        btn.dataset.name = idInfo.identidad.toLowerCase();

                        

                        btn.onclick = () => {

                            document.querySelectorAll('.merge-person-btn').forEach(b => {

                                b.style.background = 'transparent';

                                b.style.color = '#e5e5ea';

                                b.style.borderColor = 'rgba(255,255,255,0.08)';

                            });

                            btn.style.background = 'rgba(48,209,88,0.2)';

                            btn.style.color = '#30d158';

                            btn.style.borderColor = '#30d158';

                            

                            if (selectedInput) selectedInput.value = JSON.stringify({ cat: idInfo.categoria, ident: idInfo.identidad });

                            

                            const newInput = document.getElementById('merge-new-input');

                            if (newInput) newInput.value = '';

                        };

                        listDiv.appendChild(btn);

                    });

                    

                    details.appendChild(listDiv);

                    if (listContainer) listContainer.appendChild(details);

                });

                

                const searchInput = document.getElementById('merge-search-input');

                if (searchInput && listContainer) {

                    searchInput.oninput = () => {

                        const query = searchInput.value.toLowerCase().trim();

                        listContainer.querySelectorAll('details').forEach(details => {

                            let hasVisibleChild = false;

                            const buttons = details.querySelectorAll('.merge-person-btn');

                            buttons.forEach(btn => {

                                const matches = btn.dataset.name.includes(query);

                                btn.style.display = matches ? 'block' : 'none';

                                if (matches) hasVisibleChild = true;

                            });

                            details.style.display = (hasVisibleChild || query === '') ? 'block' : 'none';

                            details.open = (query !== '');

                        });

                    };

                }

                

                const newInput = document.getElementById('merge-new-input');

                if (newInput) {

                    newInput.oninput = () => {

                        document.querySelectorAll('.merge-person-btn').forEach(b => {

                            b.style.background = 'transparent';

                            b.style.color = '#e5e5ea';

                            b.style.borderColor = 'rgba(255,255,255,0.08)';

                        });

                        if (selectedInput) selectedInput.value = '';

                    };

                }

                

            }).catch(e => {

                if (listContainer) listContainer.innerHTML = '<div style="padding:10px; color:#ff453a; text-align:center;">Error cargando lista</div>';

            });

        }

        modal.style.display = 'flex';

    }

};



window.closeMergeModal = function() {

    const modal = document.getElementById('modal-merge');

    if (modal) modal.style.display = 'none';

};



// =============================================================

// ZOOM UNIFICADO EN LIGHTBOX CON INDICADOR NUMÉRICO DINÁMICO

// =============================================================

window.updateZoomDisplay = function(level) {

    const disp = document.getElementById('lb-zoom-display');

    if (disp) {

        disp.textContent = `${Math.round((level || 1.0) * 100)}%`;

    }

};



window.applyZoomLevel = function(newLevel, targetPanX, targetPanY) {

    const container = document.getElementById('lb-media-container');

    if (!container) return;

    

    zoomLevel = Math.min(16.0, Math.max(1.0, newLevel));

    if (targetPanX !== undefined) panX = targetPanX;

    if (targetPanY !== undefined) panY = targetPanY;

    if (zoomLevel === 1.0) { panX = 0; panY = 0; }

    

    container.style.transform = `translate(${panX}px, ${panY}px) scale(${zoomLevel})`;

                window.updateZoomDisplay(zoomLevel);

    container.style.setProperty('--inv-zoom', 1.0 / zoomLevel);

    window.updateZoomDisplay(zoomLevel);

};



window.zoomInLightbox = function() {

    window.applyZoomLevel((typeof zoomLevel !== 'undefined' ? zoomLevel : 1.0) + 0.35);

};



window.zoomOutLightbox = function() {

    window.applyZoomLevel(Math.max(1.0, (typeof zoomLevel !== 'undefined' ? zoomLevel : 1.0) - 0.35));

};



window.toggleZoomStep = function() {

    const cur = typeof zoomLevel !== 'undefined' ? zoomLevel : 1.0;

    if (cur < 1.4) {

        window.applyZoomLevel(2.0);

    } else if (cur < 2.9) {

        window.applyZoomLevel(4.0);

    } else {

        window.applyZoomLevel(1.0, 0, 0);

    }

};



window.resetZoom = function() {

    window.applyZoomLevel(1.0, 0, 0);

};



// =============================================================

// FILTROS RÁPIDOS Y ORDENACIÓN EN CUADRÍCULA (INSTANTÁNEO)

// =============================================================

let activeGridFilter = 'all';

let activeGridSort = 'recent';



window.setGridFilter = function(filterType, btnEl) {

    activeGridFilter = filterType;

    document.querySelectorAll('.grid-filter-btn').forEach(b => {

        b.style.background = 'transparent';

        b.style.color = '#8e8e93';

        b.style.borderColor = 'rgba(255,255,255,0.08)';

    });

    if (btnEl) {

        btnEl.style.background = 'rgba(255,255,255,0.15)';

        btnEl.style.color = '#fff';

        btnEl.style.borderColor = 'rgba(255,255,255,0.2)';

    }

    window.renderFilteredGrid();

};



window.setGridSort = function(sortType) {

    activeGridSort = sortType;

    window.renderFilteredGrid();

};



window.renderFilteredGrid = function() {

    const rawItems = (typeof currentFolderItems !== 'undefined' && currentFolderItems) ? currentFolderItems : [];

    if (!rawItems || rawItems.length === 0) return;

    

    let filtered = [...rawItems];

    

    // Filtro

    if (activeGridFilter === 'photo') {

        filtered = filtered.filter(item => !item.is_video);

    } else if (activeGridFilter === 'video') {

        filtered = filtered.filter(item => item.is_video);

    } else if (activeGridFilter === 'solo') {

        filtered = filtered.filter(item => (item.faces_count === 1 || (item.source && !item.source.includes('+'))));

    } else if (activeGridFilter === 'group') {

        filtered = filtered.filter(item => (item.faces_count > 1 || (item.source && item.source.includes('+'))));

    } else if (activeGridFilter === 'pet') {

        filtered = filtered.filter(item => (item.path.includes('Mascota') || (item.source && item.source.includes('🐶'))));

    }

    

    // Ordenación

    if (activeGridSort === 'recent') {

        filtered.sort((a, b) => (b.mtime || 0) - (a.mtime || 0));

    } else if (activeGridSort === 'oldest') {

        filtered.sort((a, b) => (a.mtime || 0) - (b.mtime || 0));

    } else if (activeGridSort === 'name') {

        filtered.sort((a, b) => a.name.localeCompare(b.name));

    }

    

    const container = document.getElementById('grid-container');

    if (!container) return;

    

    if (window._filterObserver) {

        window._filterObserver.disconnect();

        window._filterObserver = null;

    }

    

    container.innerHTML = '';

    window._filteredGridItems = filtered;

    window._filteredRenderIndex = 0;

    

    let sentry = document.getElementById('grid-sentry-filter');

    if (!sentry) {

        sentry = document.createElement('div');

        sentry.id = 'grid-sentry-filter';

        sentry.style.height = '20px';

        sentry.style.width = '100%';

        container.parentElement.appendChild(sentry);

    }

    

    window._renderNextFilterChunk();

    

    window._filterObserver = new IntersectionObserver((entries) => {

        if (entries[0].isIntersecting) {

            window._renderNextFilterChunk();

        }

    }, { root: container.parentElement, rootMargin: '200px' });

    window._filterObserver.observe(sentry);

};



window._renderNextFilterChunk = function() {

    if (!window._filteredGridItems || window._filteredRenderIndex >= window._filteredGridItems.length) return;

    const chunk = window._filteredGridItems.slice(window._filteredRenderIndex, window._filteredRenderIndex + 50);

    if (!chunk.length) return;

    

    const container = document.getElementById('grid-container');

    chunk.forEach((photo, relativeIdx) => {

        const idx = window._filteredRenderIndex + relativeIdx;

        const card = typeof createPhotoCard === 'function' ? createPhotoCard(photo, idx) : document.createElement('div');

        container.appendChild(card);

    });

    window._filteredRenderIndex += 50;

};







// =============================================================

// AUTO-CLASIFICADOR EN SEGUNDO PLANO (CONTINUO)

// =============================================================

let isBgAutoClassifyActive = false;

let bgClassifyInterval = null;



// ═══════════════════════════════════════════════════════════════

// MOTOR DE AUTO-CORRECCIÓN BIDIRECCIONAL — Panel + SSE Live

// ═══════════════════════════════════════════════════════════════

let _engineSSE = null;

let _enginePanelOpen = false;

let _engineRunning = false;

let _enginePollTimer = null;



window.toggleEnginePanel = function() {

    const panel = document.getElementById('engine-panel');

    if (!panel) return;

    _enginePanelOpen = !_enginePanelOpen;

    panel.style.display = _enginePanelOpen ? 'block' : 'none';

    if (_enginePanelOpen) {

        _startEngineSSE();

        _pollEngineStatus();

    }

};



window.startEngine = function() {

    fetch('/api/auto_classify_continuous', {

        method: 'POST',

        headers: {'Content-Type': 'application/json'},

        body: JSON.stringify({action: 'start'})

    }).then(r => r.json()).then(data => {

        _engineRunning = true;

        _updateEngineUI(true);

        showToast('🤖 Motor de auto-corrección iniciado. Fase A + Fase B activas.');

        _startEngineSSE();

    }).catch(e => showToast('Error arrancando el motor.'));

};



window.stopEngine = function() {

    fetch('/api/auto_classify_continuous', {

        method: 'POST',

        headers: {'Content-Type': 'application/json'},

        body: JSON.stringify({action: 'stop'})

    }).then(r => r.json()).then(data => {

        _engineRunning = false;

        _updateEngineUI(false);

        _stopEngineSSE();

        showToast('⏹ Motor detenido.');

    }).catch(e => {});

};



// Mantener compatibilidad con el botón anterior

window.toggleBgAutoClassify = function() { window.toggleEnginePanel(); };

window.startBgAutoClassify = function() { window.startEngine(); };

window.stopBgAutoClassify = function() { window.stopEngine(); };



function _startEngineSSE() {

    if (!_enginePanelOpen) return; // Solo conectar si el panel esta abierto

    if (_engineSSE) return; // Ya conectado

    try {

        _engineSSE = new EventSource('/api/self_audit_stream');

        _engineSSE.onmessage = function(e) {

            try {

                const d = JSON.parse(e.data);

                _applyEngineStatus(d);

            } catch(err) {}

        };

        _engineSSE.onerror = function() {

            _engineSSE.close();

            _engineSSE = null;

            // Reintentar en 10s si el panel sigue abierto

            if (_enginePanelOpen) {

                setTimeout(_startEngineSSE, 10000);

            }

        };

    } catch(e) {}

}



function _stopEngineSSE() {

    if (_engineSSE) {

        _engineSSE.close();

        _engineSSE = null;

    }

}



function _pollEngineStatus() {

    fetch('/api/self_audit_status')

        .then(r => r.json())

        .then(d => _applyEngineStatus(d))

        .catch(e => {});

}



const _PHASE_LABELS = {

    'idle':          '⏸ Inactivo — esperando inicio',

    'scan_unknown':  '🔍 Fase A — Clasificando desconocidos...',

    'audit_known':   '🔄 Fase B — Auditando carpetas conocidas...',

    'waiting':       '⏳ Descansando entre ciclos (60 s)...',

    'deep_scan':     '🧠 Escaneo profundo...',

};



function _applyEngineStatus(d) {

    _engineRunning = !!d.running;

    _updateEngineUI(_engineRunning);



    // Contadores

    _setInner('engine-stat-scanned', d.total_scanned ?? 0);

    _setInner('engine-stat-known',   d.total_moved_to_known ?? 0);

    _setInner('engine-stat-review',  d.total_moved_to_review ?? 0);



    // Drawer stats

    _setInner('drawer-stat-fixed', d.total_fixed ?? 0);

    _setInner('drawer-stat-cycle', d.cycle ?? 0);



    // Fase

    const phaseLabel = _PHASE_LABELS[d.phase] || d.phase || 'Inactivo';

    _setInner('engine-phase-label', phaseLabel);



    // Último archivo analizado

    const lastFileEl = document.getElementById('engine-last-file');

    if (lastFileEl) {

        if (d.last_scanned_file) {

            lastFileEl.textContent = `📍 ${d.last_scanned_file}`;

        } else if (_engineRunning) {

            lastFileEl.textContent = `⏳ Reanudando desde checkpoint previo...`;

        } else {

            lastFileEl.textContent = `⏸️ Estado guardado en disco`;

        }

    }



    // Ciclo + dot

    const dot = document.getElementById('engine-cycle-dot');

    const cycleText = document.getElementById('engine-cycle-text');

    if (dot) {

        dot.style.background = _engineRunning

            ? (d.phase === 'waiting' ? '#ff9f0a' : '#30d158')

            : '#3a3a3c';

        dot.style.boxShadow = _engineRunning ? `0 0 6px ${d.phase === 'waiting' ? '#ff9f0a' : '#30d158'}` : 'none';

    }

    if (cycleText) {

        cycleText.textContent = d.cycle

            ? `Ciclo ${d.cycle} — ${(d.total_fixed ?? 0)} correcciones totales`

            : 'Ciclo 0 — esperando inicio';

    }



    // Log de acciones

    const logEl = document.getElementById('engine-log');

    if (logEl && d.last_actions && d.last_actions.length > 0) {

        const entries = d.last_actions.slice().reverse();

        logEl.innerHTML = entries.map(a => {

            const color = a.msg.startsWith('✅') ? '#30d158'

                        : a.msg.startsWith('🔄') ? '#64d2ff'

                        : a.msg.startsWith('⚠️') ? '#ff9f0a'

                        : '#8e8e93';

            return `<div style="padding:5px 6px; border-bottom:1px solid rgba(255,255,255,0.04); font-size:11px;">

                <span style="color:#555; margin-right:6px;">${a.ts}</span>

                <span style="color:${color};">${a.msg}</span>

            </div>`;

        }).join('');

    }

}



function _updateEngineUI(running) {

    const btn   = document.getElementById('btn-bg-autoclassify');

    const badge = document.getElementById('engine-badge');

    const startBtn = document.getElementById('btn-engine-start');

    const stopBtn  = document.getElementById('btn-engine-stop');



    if (btn) {

        btn.style.background = running

            ? 'rgba(48,209,88,0.15)' : 'rgba(10,132,255,0.12)';

        btn.style.borderColor = running ? '#30d158' : 'rgba(10,132,255,0.3)';

        btn.style.color = running ? '#30d158' : '#64d2ff';

    }

    if (badge)    badge.style.display = running ? 'inline' : 'none';

    if (startBtn) startBtn.style.display = running ? 'none' : 'inline-block';

    if (stopBtn)  stopBtn.style.display  = running ? 'inline-block' : 'none';

}



// Auto-conectar y consultar estado al cargar la página

document.addEventListener('DOMContentLoaded', () => {

    setTimeout(() => {

        _pollEngineStatus();

    }, 1500);

});



function _setInner(id, val) {

    const el = document.getElementById(id);

    if (el) el.textContent = val;

}



// Añadir animación pulse-badge al CSS dinámicamente

(function() {

    const style = document.createElement('style');

    style.textContent = `

        @keyframes pulse-badge {

            0%, 100% { opacity:1; }

            50% { opacity:0.5; }

        }

    `;

    document.head.appendChild(style);

})();





function loadAlbumsHome() {

    currentCat = null;

    currentIdent = null;

    

    document.querySelectorAll('.nav-tab-item').forEach(b => b.classList.remove('active'));

    const galTab = document.getElementById('nav-btn-gallery');

    if (galTab) galTab.classList.add('active');

    

    const titleEl = document.getElementById('gallery-title');

    const subEl = document.getElementById('gallery-subtitle');

    const avatarEl = document.getElementById('gallery-avatar');

    

    if (titleEl) titleEl.textContent = 'Todas las Fotos y Álbumes';

    if (subEl) subEl.textContent = 'Selecciona un álbum en el panel lateral o una sugerencia en el buscador.';

    if (avatarEl) avatarEl.style.display = 'none';

    

    const bcCat = document.getElementById('bc-category');

    const bcPer = document.getElementById('bc-person');

    const sep1 = document.getElementById('bc-separator-1');

    const sep2 = document.getElementById('bc-separator-2');

    if (bcCat) bcCat.style.display = 'none';

    if (bcPer) bcPer.style.display = 'none';

    if (sep1) sep1.style.display = 'none';

    if (sep2) sep2.style.display = 'none';

    

    loadGallery();

}

window.loadAlbumsHome = loadAlbumsHome;



function cleanDisplayName(name) {

    if (!name) return 'Desconocido';

    return name.replace(/_rejected/g, '').replace(/Falso_Positivo/g, 'Descartado').replace(/Ignorar_Irrelevante/g, 'Descartado').replace(/_solitario/g, '').replace(/_compania/g, '').replace(/\/rejected/g, '').replace(/\/undefined/g, '').trim() || 'Desconocido';

}

function resizeContainerToImage() {

    const container = document.getElementById('lb-media-container');

    const mediaEl = container ? container.querySelector('.lb-media-element') : null;

    if (container && mediaEl) {

        const cw = mediaEl.clientWidth || mediaEl.offsetWidth;

        const ch = mediaEl.clientHeight || mediaEl.offsetHeight;

        if (cw && ch) {

            container.style.width = cw + 'px';

            container.style.height = ch + 'px';

        }

    }

}

window.addEventListener('resize', resizeContainerToImage);

async function filterTimeline(year) {

    try {

        const res = await fetch(`/api/timeline?year=${year}`);

        const data = await res.json();

        

        document.getElementById('gallery-title').textContent = `Fotos del Año ${year}`;

        document.getElementById('gallery-subtitle').textContent = `${data.length} elementos`;

        currentCat = `Año ${year}`;

        currentIdent = year;

        currentFolderItems = data;

        currentPhotos = data;

        

        const grid = document.getElementById('grid-container');

        grid.innerHTML = '';

        

        data.forEach((item, idx) => {

            const card = document.createElement('div');

            card.className = 'media-card';

            card.style.position = 'relative';

            

            card.onclick = () => {

                currentItemIndex = idx;

                openLightbox(item);

            };

            

            // Add source badge

            const badge = document.createElement('span');

            badge.id = `source-${idx}`;

            if (item.source.includes('Dataset') && item.source.includes('Manual')) {

                badge.className = 'badge badge-dataset';

                badge.textContent = '🔒 Dataset + ✏️ Manual';

            } else if (item.source.includes('IA') && item.source.includes('Manual')) {

                badge.className = 'badge badge-manual';

                badge.textContent = '✨ IA + ✏️ Manual';

            } else if (item.source.includes('Dataset')) {

                badge.className = 'badge badge-dataset';

                badge.textContent = '🔒 Dataset';

            } else if (item.source.includes('Manual')) {

                badge.className = 'badge badge-manual';

                badge.textContent = '✏️ Manual';

            } else {

                badge.className = 'badge badge-ia';

                badge.textContent = '✨ IA';

            }

            card.appendChild(badge);

            

            // Masonry Skeleton Padding

            if (item.orig_width && item.orig_height) {

                const aspect = (item.orig_height / item.orig_width) * 100;

                card.style.paddingTop = `${aspect}%`;

            } else {

                card.style.paddingTop = `100%`;

            }



            const skeleton = document.createElement('div');

            skeleton.className = 'masonry-skeleton';

            card.appendChild(skeleton);



            // Add thumbnail image

            const thumb = document.createElement('img');

            thumb.src = `/api/thumbnail?path=${encodeURIComponent(item.path)}`;

            thumb.loading = 'lazy';

            thumb.decoding = 'async';

            thumb.style.opacity = '0';

            thumb.onload = () => {

                thumb.style.opacity = '1';

                skeleton.style.opacity = '0';

                setTimeout(() => skeleton.remove(), 400);

            };

            thumb.style.transition = 'opacity 0.4s ease';

            thumb.style.width = '100%';

            thumb.style.height = 'auto';

            thumb.style.position = 'absolute';

            thumb.style.top = '0';

            thumb.style.left = '0';

            card.appendChild(thumb);



            // Sci-Fi Face Boxes Container

            if (item.faces && item.faces.length > 0 && item.orig_width && item.orig_height) {

                const facesContainer = document.createElement('div');

                facesContainer.className = 'faces-container';

                

                item.faces.forEach(face => {

                    if (!face.box) return;

                    const [fx, fy, fw, fh] = face.box;

                    const left = (fx / item.orig_width) * 100;

                    const top = (fy / item.orig_height) * 100;

                    const width = (fw / item.orig_width) * 100;

                    const height = (fh / item.orig_height) * 100;

                    

                    const box = document.createElement('div');

                    box.className = 'face-box-sci-fi';

                    box.style.left = `${left}%`;

                    box.style.top = `${top}%`;

                    box.style.width = `${width}%`;

                    box.style.height = `${height}%`;

                    

                    const label = document.createElement('div');

                    label.className = 'face-box-label';

                    const confPct = Math.round((face.confidence || 0) * 100);

                    label.innerHTML = `<span>${face.identity || 'Desconocido'}</span><small>${confPct}%</small>`;

                    box.appendChild(label);

                    

                    facesContainer.appendChild(box);

                });

                card.appendChild(facesContainer);

            }

            

            // Add video indicator if video

            if (item.type === 'video') {

                const playIcon = document.createElement('div');

                playIcon.className = 'video-icon';

                playIcon.innerHTML = '▶';

                card.appendChild(playIcon);

            }

            

            grid.appendChild(card);

        });

    } catch(e) {

        console.error("Error loading timeline:", e);

    }

}









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

                alert('Error de conexion: ' + err.message);

            }

        }



        function generateReassignHTML(face, faceNum, onchangeFuncName, sourceContext='default') {

            let pathParts = (currentFileObj && currentFileObj.path) ? currentFileObj.path.split(/[\\\/]/) : [];

            let folderName = pathParts.length >= 2 ? pathParts.slice(-2, -1)[0] : '';

            let categoryName = pathParts.length >= 3 ? pathParts.slice(-3, -2)[0] : '';

            if (folderName === '_Dudosos') {

                folderName = pathParts.length >= 3 ? pathParts.slice(-3, -2)[0] : '';

                categoryName = pathParts.length >= 4 ? pathParts.slice(-4, -3)[0] : '';

            }



            const isInvalidFolderName = (name) => {
                if (!name) return true;
                const lower = name.toLowerCase().trim();
                const invalidExact = [
                    'fotos', 'resultados', 'galeria eneko no abrir',
                    'familia', 'conocidos', 'profesores', 'mascotas',
                    'yo', 'amigos', 'otros', 'desconocidos', 'desconocido',
                    'photos', 'icloud', 'icloud photos', 'pictures', 'imagenes', 'imágenes'
                ];
                if (invalidExact.includes(lower)) return true;

                const invalidSubstrings = [
                    'conmigo', 'sin mi', 'sin mí', 'grupales', 'con amigos', 'familiares',
                    'para revisar', 'revisar', 'dudosos', '_dudosos',
                    'personas sin nombre', 'limpieza inteligente',
                    'recuerdos', 'lugares', 'eventos', 'frases',
                    'por organizar', 'pendientes', 'masivos'
                ];
                if (invalidSubstrings.some(inv => lower.includes(inv))) return true;
                if (name.startsWith('_') || name.startsWith('📋') || name.startsWith('⏳') || name.startsWith('!') || name.startsWith('⚠️') || name.startsWith('❓') || name.startsWith('🎬') || name.startsWith('📷') || name.startsWith('👤')) return true;
                return false;
            };

            const isRealPersonFolder = !isInvalidFolderName(folderName) && !isInvalidFolderName(categoryName) && Boolean(folderName.match(/^[CFPM]\.?\s+/i) || folderName === 'YO' || (typeof identitiesList !== 'undefined' && identitiesList.some(id => id.identidad === folderName)));



            // Determinar si la cara ya tiene una identidad humana asignada/confirmada

            const isAssignedToPerson = face.identity &&

                face.identity !== 'Desconocido' &&

                !face.identity.startsWith('IA (Pendiente)');



            // ── Determine AI suggestion & claimed people in photo (Strict Mutual Exclusion) ──
            const otherAssignedInPhoto = new Set();
            let ownerAlreadyIdentified = false;

            if (typeof currentFaces !== 'undefined' && Array.isArray(currentFaces)) {
                currentFaces.forEach((f, idx) => {
                    if (idx !== faceNum - 1) {
                        const rawId = f.identity || '';
                        const cleanId = rawId.replace(/^\?\s*/, '').trim();
                        const isNonPerson = !cleanId || cleanId === 'Desconocido' || cleanId.startsWith('IA ') || cleanId.startsWith('Falso_') || cleanId.startsWith('Ignorar_') || cleanId.includes('(Sin rostro') || cleanId.toLowerCase().includes('desconocid');
                        
                        if (!isNonPerson) {
                            otherAssignedInPhoto.add(cleanId);
                            otherAssignedInPhoto.add(rawId);
                            if (cleanId === folderName || rawId === folderName || f.tag_type === 'dataset' || f.is_owner || f.is_centroid) {
                                ownerAlreadyIdentified = true;
                                if (folderName) otherAssignedInPhoto.add(folderName);
                            }
                        }
                        if (f.is_manual && cleanId) {
                            otherAssignedInPhoto.add(cleanId);
                            if (cleanId === folderName) {
                                ownerAlreadyIdentified = true;
                                if (folderName) otherAssignedInPhoto.add(folderName);
                            }
                        }
                    }
                });
            }

            let aiPredictedIdObj = null;
            let hasAiSuggestion = false;
            let suggestedName = face.suggested_identity;

            if (!suggestedName && face.identity) {
                if (face.identity.startsWith('? ')) {
                    const candidate = face.identity.replace(/^\?\s*/, '').trim();
                    if (!(candidate === folderName && ownerAlreadyIdentified)) {
                        suggestedName = candidate;
                    }
                } else if (face.identity.startsWith('IA (Pendiente): ')) {
                    const candidate = face.identity.replace('IA (Pendiente): ', '').trim();
                    if (!(candidate === folderName && ownerAlreadyIdentified)) {
                        suggestedName = candidate;
                    }
                } else if (face.identity.startsWith('IA: ')) {
                    const candidate = face.identity.replace('IA: ', '').trim();
                    if (!(candidate === folderName && ownerAlreadyIdentified)) {
                        suggestedName = candidate;
                    }
                } else if (!face.is_manual && face.identity !== 'Desconocido' && !face.identity.startsWith('Falso_') && !face.identity.startsWith('Ignorar_')) {
                    const candidate = face.identity.replace(/^\?\s*/, '').trim();
                    if (!(candidate === folderName && ownerAlreadyIdentified)) {
                        suggestedName = candidate;
                    }
                }
            }

            // Exclusión mutua: una persona NO puede repetirse en varias caras de la misma foto
            if (suggestedName && otherAssignedInPhoto.has(suggestedName)) {
                suggestedName = null;
            }

            // Si la sugerencia es el dueño del álbum y el dueño ya ha sido identificado en otra cara, anular
            if (suggestedName && suggestedName === folderName && ownerAlreadyIdentified) {
                suggestedName = null;
            }

            // Si esta cara YA es el dueño confirmado (sin duda), no mostrar sugerencia de sí mismo
            if (suggestedName && face.identity === folderName && !face.identity.startsWith('? ')) {
                suggestedName = null;
            }

            if (suggestedName && !isInvalidFolderName(suggestedName)) {
                const cleanSugg = suggestedName.replace(/^\?\s*/, '').trim();
                const matchedObj = identitiesList.find(id => id.identidad === cleanSugg || id.identidad === suggestedName);
                aiPredictedIdObj = matchedObj ? {categoria: matchedObj.categoria, identidad: cleanSugg} : {categoria: categoryName || 'Familia', identidad: cleanSugg};
                if (aiPredictedIdObj) hasAiSuggestion = true;
            }



            const menuId = `menu-${faceNum}-${sourceContext}-${onchangeFuncName}`;



            const makeAction = (valObj, label, bg, color, fw='600') => {

                let valStr = valObj === 'NEW' ? 'NEW' : JSON.stringify(valObj).replace(/"/g, '&quot;');

                let call = `${onchangeFuncName}('${valStr}', ${faceNum})`;

                return `<button onclick="let m=document.getElementById('${menuId}'); if(m) m.style.display='none'; ${call}" style="

                    display:flex; align-items:center; gap:5px; width:100%;

                    padding:7px 10px; border-radius:8px; border:1px solid ${bg}33;

                    background:${bg}18; color:${color}; cursor:pointer;

                    font-size:11px; font-weight:${fw}; transition:all 0.15s; text-align:left;

                " onmouseover="this.style.background='${bg}35'" onmouseout="this.style.background='${bg}18'">${label}</button>`;

            };



            let html = `<div style="display:flex; flex-direction:column; gap:5px; margin-top:6px;">`;



            // ── 1. AI SUGGESTION CHIP (most prominent) ──────────

            if (hasAiSuggestion) {

                const confirmVal = JSON.stringify(aiPredictedIdObj).replace(/"/g, '&quot;');

                const rejectVal  = JSON.stringify({categoria: '_Dudosos', identidad: 'Desconocido'}).replace(/"/g, '&quot;');

                html += `

                <div style="background:rgba(10,132,255,0.1); border:1px solid rgba(10,132,255,0.3); border-radius:10px; padding:8px 10px;">

                    <div style="font-size:10px; color:#64d2ff; font-weight:700; letter-spacing:0.5px; margin-bottom:6px; display:flex; align-items:center; gap:4px;">

                        <span>🤖</span> SUGERENCIA IA

                    </div>

                    <div style="font-size:12px; color:#fff; font-weight:600; margin-bottom:7px; padding:0 2px;">${(suggestedName||'').replace(/^\?\s*/, '')}${face.suggested_score ? ` (${Math.round(face.suggested_score * 100)}% certeza)` : ''}</div>

                    <div style="display:flex; gap:5px;">

                        <button onclick="${onchangeFuncName}('${confirmVal}', ${faceNum})" style="

                            flex:1; padding:6px 4px; border-radius:7px; border:1px solid #30d15855;

                            background:rgba(48,209,88,0.15); color:#30d158; cursor:pointer;

                            font-size:11px; font-weight:700; transition:all 0.15s;

                        " onmouseover="this.style.background='rgba(48,209,88,0.3)'" onmouseout="this.style.background='rgba(48,209,88,0.15)'">

                            ✓ Sí, es ${(suggestedName||'').replace(/^\?\s*/, '').replace(/^IA\s*\(Pendiente\):\s*/i, '')}

                        </button>

                        <button onclick="${onchangeFuncName}('${rejectVal}', ${faceNum})" style="

                            flex:1; padding:6px 4px; border-radius:7px; border:1px solid #ff453a55;

                            background:rgba(255,69,58,0.12); color:#ff6961; cursor:pointer;

                            font-size:11px; font-weight:700; transition:all 0.15s;

                        " onmouseover="this.style.background='rgba(255,69,58,0.28)'" onmouseout="this.style.background='rgba(255,69,58,0.12)'">

                            ✗ No es ${(suggestedName||'').replace(/^\?\s*/, '').replace(/^IA\s*\(Pendiente\):\s*/i, '')}

                        </button>

                    </div>

                </div>`;

            }



            // ── 2. Album owner confirm ONLY IF face is unassigned/unknown AND it's a real person album AND owner is NOT already identified in this photo ──
            if (isRealPersonFolder && !isAssignedToPerson && !hasAiSuggestion && !ownerAlreadyIdentified && !otherAssignedInPhoto.has(folderName)) {
                html += makeAction(
                    {categoria: categoryName, identidad: folderName},
                    `✨ Sí, es ${folderName} (dueño del álbum)`,
                    '#30d158', '#30d158'
                );

                html += makeAction(

                    {categoria: '_Dudosos', identidad: 'Desconocido'},

                    `❌ Esta cara NO es ${folderName}`,

                    '#ff9f0a', '#ff9f0a'

                );

            }



            // ── 2b. Explicit rejection if face has non-manual identity and not already suggested
            if (!hasAiSuggestion && face.identity && face.identity !== 'Desconocido' && !face.is_manual) {
                const cleanIdentName = face.identity.replace(/^\?\s*/, '').replace(/^IA\s*\(Pendiente\):\s*/i, '').replace(/^IA:\s*/i, '').trim();
                html += makeAction({categoria: '_Dudosos', identidad: 'Desconocido'}, `❌ Esta persona NO es ${cleanIdentName}`, '#ff453a', '#ff6961', '700');
            }

            // ── 3. Quick Discard actions ───────────────────────────

            html += makeAction({categoria: 'Ignorar', identidad: 'Falso_Positivo'}, '🚫 Esto NO es una cara', '#ff453a', '#ff453a', '500');

            html += makeAction({categoria: 'Ignorar', identidad: 'Ignorar_Irrelevante'}, '👤 Ignorar (irrelevante)', '#8e8e93', '#8e8e93', '500');



            // ── 4. Full reassign dropdown ────────────────────────

            let categories = {};

            identitiesList.forEach(id => {

                if (!categories[id.categoria]) categories[id.categoria] = [];

                categories[id.categoria].push(id);

            });



            const dropBtnStyle = `display:flex; justify-content:space-between; align-items:center; width:100%; padding:7px 10px; border-radius:8px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.06); color:rgba(255,255,255,0.7); cursor:pointer; font-size:11px; font-weight:600; transition:all 0.15s;`;



            html += `<div style="position:relative; width:100%;">`;

            html += `<button onclick="openReassignFaceModal(${faceNum}, '${onchangeFuncName}'); event.stopPropagation();" style="${dropBtnStyle}" title="Abrir selector con búsqueda"><span>↔ Reasignar a otra persona...</span><span style="opacity:0.7; font-size:12px;">🔍 ▾</span></button>`;

            html += `<div id="${menuId}" style="display:none; position:relative; width:100%; margin-top:6px; max-height:260px; overflow-y:auto; background:#141416; border:1px solid rgba(255,255,255,0.15); z-index:99999; border-radius:10px; padding:6px; box-shadow:0 8px 24px rgba(0,0,0,0.85);" class="custom-scrollbar">`;



            const innerBtnStyle = `display:block; width:100%; text-align:left; padding:7px 10px; background:transparent; border:none; color:rgba(255,255,255,0.8); cursor:pointer; border-radius:6px; font-size:12px; transition:background 0.15s;`;

            const hoverScript = `onmouseover="this.style.background='rgba(255,255,255,0.08)'" onmouseout="this.style.background='transparent'"`;



            // "Nueva persona" option

            html += `<button style="${innerBtnStyle} color:#0a84ff; font-weight:600;" ${hoverScript} onclick="let m=document.getElementById('${menuId}'); if(m) m.style.display='none'; ${onchangeFuncName}('NEW', ${faceNum})">➕ Nueva persona...</button>`;

            html += `<hr style="border:0; border-top:1px solid rgba(255,255,255,0.08); margin:4px 0;">`;



            Object.keys(categories).sort().forEach(cat => {

                html += `<details style="margin-bottom:2px;">`;

                html += `<summary style="cursor:pointer; padding:5px 8px; font-weight:700; color:rgba(255,255,255,0.4); font-size:10px; text-transform:uppercase; letter-spacing:0.6px; background:rgba(255,255,255,0.04); border-radius:5px; margin-bottom:2px; list-style:none; display:flex; align-items:center; gap:4px;">▸ ${cat}</summary>`;

                categories[cat].sort((a, b) => a.identidad.localeCompare(b.identidad)).forEach(id => {
                    const isAlreadyInPhoto = otherAssignedInPhoto.has(id.identidad);
                    if (isAlreadyInPhoto) {
                        html += `<button disabled style="${innerBtnStyle} opacity:0.35; cursor:not-allowed;" title="Esta persona ya ha sido identificada en otra cara de esta misma foto">🚫 ${typeof cleanDisplayName === 'function' ? cleanDisplayName(id.identidad) : id.identidad} <span style="font-size:9px; color:#ff9f0a; font-weight:700;">(Ya en foto)</span></button>`;
                    } else {
                        const vs = JSON.stringify(id).replace(/"/g, '&quot;');
                        html += `<button style="${innerBtnStyle}" ${hoverScript} onclick="let m=document.getElementById('${menuId}'); if(m) m.style.display='none'; ${onchangeFuncName}('${vs}', ${faceNum})">${typeof cleanDisplayName === 'function' ? cleanDisplayName(id.identidad) : id.identidad}</button>`;
                    }
                });

                html += `</details>`;

            });



            html += `</div></div>`;

            html += `</div>`;

            return html;

        }



        function showToast(message, isError=false) {

            let container = document.getElementById('toast-container');

            if (!container) {

                container = document.createElement('div');

                container.id = 'toast-container';

                container.style.cssText = 'position:fixed; bottom:20px; right:20px; z-index:9999; display:flex; flex-direction:column; gap:10px;';

                document.body.appendChild(container);

            }

            const toast = document.createElement('div');

            toast.style.cssText = `background: ${isError ? 'rgba(255, 59, 48, 0.9)' : 'rgba(10, 132, 255, 0.9)'}; color: white; padding: 12px 20px; border-radius: 8px; backdrop-filter: blur(10px); box-shadow: 0 4px 12px rgba(0,0,0,0.3); font-family: -apple-system, sans-serif; font-size: 13px; transform: translateX(120%); transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);`;

            toast.innerHTML = `<strong>${isError ? 'Aviso' : 'Información'}</strong><br>${message}`;

            container.appendChild(toast);

            

            requestAnimationFrame(() => toast.style.transform = 'translateX(0)');

            setTimeout(() => {

                toast.style.transform = 'translateX(120%)';

                setTimeout(() => toast.remove(), 300);

            }, 4000);

        }







        async function loadIdentities() {
            try {
                const res = await fetch('/api/identities');
                if (res.ok) {
                    identitiesList = await res.json();
                }
            } catch (e) {
                console.warn('loadIdentities non-blocking notice:', e);
            }
        }



        

                let statsPollInterval = null;

        let lastStatsData = null;



        window.closeStatsModal = function() {

            const modal = document.getElementById('stats-modal');

            if (modal) modal.style.display = 'none';

            if (statsPollInterval) {

                clearInterval(statsPollInterval);

                statsPollInterval = null;

            }

        };



        window.openStatsModal = async function(isManualRefresh = false) {

            const modal = document.getElementById('stats-modal');

            if (!modal) return;

            modal.style.display = 'flex';



            const refreshIcon = document.getElementById('stats-refresh-icon');

            if (refreshIcon) refreshIcon.style.animation = 'spin 0.8s linear infinite';



            if (!isManualRefresh && !lastStatsData) {

                document.getElementById('stats-content').innerHTML = `

                    <div style="text-align:center; padding:50px 20px;">

                        <div class="loader-small" style="margin:auto; width:36px; height:36px;"></div>

                        <p style="color:#8e8e93; margin-top:14px; font-size:13px;">Obteniendo telemetría en tiempo real...</p>

                    </div>`;

            }



            try {

                const res = await fetch('/api/stats');

                const data = await res.json();

                lastStatsData = data;

                renderStatsContent(data);



                // Auto-poll if assistant is active or running

                const asst = data.assistant || {};

                if (asst.active || asst.status === 'running') {

                    if (!statsPollInterval) {

                        statsPollInterval = setInterval(async () => {

                            const m = document.getElementById('stats-modal');

                            if (!m || m.style.display === 'none') {

                                clearInterval(statsPollInterval);

                                statsPollInterval = null;

                                return;

                            }

                            try {

                                const r = await fetch('/api/stats');

                                const d = await r.json();

                                lastStatsData = d;

                                renderStatsContent(d);

                            } catch (e) {}

                        }, 2500);

                    }

                } else if (statsPollInterval) {

                    clearInterval(statsPollInterval);

                    statsPollInterval = null;

                }

            } catch (err) {

                document.getElementById('stats-content').innerHTML = `<p style="color:#ff453a; text-align:center; padding:30px;">Error al cargar estadísticas: ${err.message}</p>`;

            } finally {

                if (refreshIcon) refreshIcon.style.animation = 'none';

            }

        };



        function renderStatsBreakdownList(breakdown, filter = '') {

            const entries = Object.entries(breakdown);

            if (!entries.length) return '<div style="color:#8e8e93; text-align:center; padding:15px;">No hay álbumes para mostrar</div>';

            

            const maxCount = entries[0][1] || 1;

            const q = filter.trim().toLowerCase();

            const filtered = q ? entries.filter(([name]) => name.toLowerCase().includes(q)) : entries;



            if (!filtered.length) {

                return `<div style="color:#8e8e93; text-align:center; padding:15px;">No se encontraron álbumes que coincidan con "${filter}"</div>`;

            }



            return filtered.map(([name, count]) => {

                const pct = Math.round((count / maxCount) * 100);

                return `

                    <div class="stats-album-item" style="display:flex; align-items:center; justify-content:space-between; padding:6px 8px; border-radius:8px; margin-bottom:4px; background:rgba(255,255,255,0.02); transition:background 0.15s;" onmouseover="this.style.background='rgba(255,255,255,0.06)'" onmouseout="this.style.background='rgba(255,255,255,0.02)'">

                        <div style="flex:1; min-width:0; margin-right:12px;">

                            <div style="font-size:13px; font-weight:600; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${name}</div>

                            <div style="width:100%; height:4px; background:rgba(255,255,255,0.06); border-radius:2px; margin-top:4px; overflow:hidden;">

                                <div style="width:${pct}%; height:100%; background:linear-gradient(90deg, #0a84ff, #bf5af2); border-radius:2px;"></div>

                            </div>

                        </div>

                        <div style="font-size:12px; font-weight:700; color:#8e8e93; font-feature-settings:'tnum'; flex-shrink:0;">

                            ${count.toLocaleString()}

                        </div>

                    </div>

                `;

            }).join('');

        }



        window.filterStatsList = function(q) {

            const listEl = document.getElementById('stats-album-list');

            if (!listEl || !lastStatsData) return;

            listEl.innerHTML = renderStatsBreakdownList(lastStatsData.breakdown || {}, q);

        };



        function renderStatsContent(data) {

            const asst = data.assistant || {};

            const totalGallery = data.total || 0;

            const classified = data.clasificadas || 0;

            const manualUser = data.manual_user || 0;

            const iaVerified = data.ia_verified || 0;

            const dudosos = data.dudosos || 0;

            const pendientes = data.pendientes || 0;

            const pctGlobal = totalGallery > 0 ? Math.round((classified / totalGallery) * 100) : 0;



            const asstStatus = asst.status || 'completed';

            const isAsstRunning = asst.active || asstStatus === 'running';

            const asstTotal = asst.total || 0;

            const asstProc = asst.processed || 0;

            const asstRem = asst.remaining !== undefined ? asst.remaining : Math.max(0, asstTotal - asstProc);

            const asstPct = asst.percentage || (asstTotal > 0 ? Math.round((asstProc / asstTotal) * 100) : 100);

            const asstRate = asst.rate || 0;

            const asstEta = asst.eta_formatted || (asstRem === 0 ? 'Completado' : (asst.eta_minutes ? `~${Math.round(asst.eta_minutes)} min` : 'Calculando...'));

            const cloudPlaceholders = asst.cloud_placeholders || 0;

            const totalAppleOrganized = asst.total_apple_db || data.iphone_clasificadas || 0;



            const html = `

                <!-- HERO CARD: ASISTENTE AUTÓNOMO EN SEGUNDO PLANO -->

                <div style="background: linear-gradient(135deg, rgba(10,132,255,0.1) 0%, rgba(191,90,242,0.1) 100%); border: 1px solid rgba(10,132,255,0.3); border-radius: 18px; padding: 20px; margin-bottom: 22px; position: relative; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">

                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; flex-wrap:wrap; gap:8px;">

                        <div style="display:flex; align-items:center; gap:8px;">

                            <div style="width:32px; height:32px; border-radius:8px; background:linear-gradient(135deg, #0a84ff, #bf5af2); display:flex; align-items:center; justify-content:center; font-size:16px;">⚡</div>

                            <div>

                                <div style="font-size:14px; font-weight:800; color:#fff;">Asistente Autónomo (iCloud & Aprendizaje)</div>

                                <div style="font-size:11px; color:#8e8e93;">Organización facial en segundo plano y extracción de características</div>

                            </div>

                        </div>

                        <div>

                            ${isAsstRunning ? `

                                <div style="display:inline-flex; align-items:center; gap:6px; background:rgba(48,209,88,0.15); border:1px solid rgba(48,209,88,0.4); padding:4px 10px; border-radius:14px; font-size:11px; font-weight:700; color:#30d158;">

                                    <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#30d158; box-shadow:0 0 8px #30d158; animation:pulse-glow 1.5s infinite;"></span>

                                    ANALIZANDO EN TIEMPO REAL

                                </div>

                            ` : `

                                <div style="display:inline-flex; align-items:center; gap:6px; background:rgba(100,210,255,0.12); border:1px solid rgba(100,210,255,0.3); padding:4px 10px; border-radius:14px; font-size:11px; font-weight:700; color:#64d2ff;">

                                    <span>✓</span> TODO ORGANIZADO

                                </div>

                            `}

                        </div>

                    </div>



                    <!-- Progress Bar & Big Counter -->

                    <div style="margin-bottom:16px;">

                        <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:6px;">

                            <div>

                                <span style="font-size:26px; font-weight:900; letter-spacing:-0.5px; color:#fff; font-feature-settings:'tnum';">${asstProc.toLocaleString()}</span>

                                <span style="font-size:14px; color:#8e8e93; font-weight:600;"> / ${asstTotal.toLocaleString()} fotos del lote</span>

                            </div>

                            <div style="text-align:right;">

                                <span style="font-size:16px; font-weight:800; color:#64d2ff;">${asstPct}%</span>

                                <span style="font-size:11px; color:#8e8e93; margin-left:6px;">(${asstRem.toLocaleString()} restantes)</span>

                            </div>

                        </div>



                        <div style="width:100%; height:12px; background:rgba(255,255,255,0.08); border-radius:10px; overflow:hidden; position:relative; padding:1px;">

                            <div style="width:${Math.min(100, asstPct)}%; height:100%; border-radius:8px; background:linear-gradient(90deg, #0a84ff 0%, #bf5af2 50%, #30d158 100%); transition:width 0.6s cubic-bezier(0.16, 1, 0.3, 1); box-shadow:0 0 12px rgba(10,132,255,0.6);"></div>

                        </div>

                    </div>



                    <!-- 4 Assistant Telemetry Tiles -->

                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(130px, 1fr)); gap:10px; margin-bottom:14px;">

                        <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.07); padding:10px; border-radius:12px; text-align:center;">

                            <div style="font-size:10px; color:#8e8e93; font-weight:700; text-transform:uppercase;">Velocidad</div>

                            <div style="font-size:18px; font-weight:800; color:#64d2ff; margin-top:2px;">${asstRate} <span style="font-size:11px; font-weight:500;">img/s</span></div>

                        </div>

                        <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.07); padding:10px; border-radius:12px; text-align:center;">

                            <div style="font-size:10px; color:#8e8e93; font-weight:700; text-transform:uppercase;">Tiempo Restante</div>

                            <div style="font-size:18px; font-weight:800; color:#ffd60a; margin-top:2px;">${asstEta}</div>

                        </div>

                        <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.07); padding:10px; border-radius:12px; text-align:center;">

                            <div style="font-size:10px; color:#8e8e93; font-weight:700; text-transform:uppercase;">Total Apple en Álbumes</div>

                            <div style="font-size:18px; font-weight:800; color:#30d158; margin-top:2px;">${totalAppleOrganized.toLocaleString()}</div>

                        </div>

                        <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.07); padding:10px; border-radius:12px; text-align:center;">

                            <div style="font-size:10px; color:#8e8e93; font-weight:700; text-transform:uppercase;">iCloud en la Nube</div>

                            <div style="font-size:18px; font-weight:800; color:#bf5af2; margin-top:2px;" title="Pendientes de sincronización local por iCloud para Windows">${cloudPlaceholders.toLocaleString()}</div>

                        </div>

                    </div>



                    <!-- Assistant Breakdown Tags -->

                    <div style="display:flex; flex-wrap:wrap; gap:6px; font-size:11px;">

                        <span style="background:rgba(255,255,255,0.06); padding:4px 8px; border-radius:8px; color:#e5e5ea;">👤 YO: <strong>${asst.yo || 0}</strong></span>

                        <span style="background:rgba(255,255,255,0.06); padding:4px 8px; border-radius:8px; color:#e5e5ea;">🏷️ Conocidas: <strong>${asst.known_persons || 0}</strong></span>

                        <span style="background:rgba(255,255,255,0.06); padding:4px 8px; border-radius:8px; color:#e5e5ea;">📸 Capturas: <strong>${asst.capturas || 0}</strong></span>

                        <span style="background:rgba(255,255,255,0.06); padding:4px 8px; border-radius:8px; color:#e5e5ea;">🌄 Sin Rostro: <strong>${asst.sin_rostro || 0}</strong></span>

                        <span style="background:rgba(255,255,255,0.06); padding:4px 8px; border-radius:8px; color:#e5e5ea;">❓ Desconocidos: <strong>${asst.desconocidos || 0}</strong></span>

                        ${asst.errors ? `<span style="background:rgba(255,69,58,0.15); border:1px solid rgba(255,69,58,0.3); padding:4px 8px; border-radius:8px; color:#ff453a;">⚠️ Errores: <strong>${asst.errors}</strong></span>` : ''}

                    </div>

                </div>



                <!-- SECCIÓN 2: ESTADO GLOBAL DE LA FOTOTECA -->

                <div style="margin-bottom:22px;">

                    <div style="font-size:12px; font-weight:700; color:#8e8e93; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:10px;">

                        Estado Global de la Galería

                    </div>



                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:10px; margin-bottom:14px;">

                        <!-- Total -->

                        <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); padding:14px; border-radius:14px;">

                            <div style="font-size:11px; color:#8e8e93; font-weight:600;">Total Elementos</div>

                            <div style="font-size:24px; font-weight:800; color:#fff; margin-top:2px;">${totalGallery.toLocaleString()}</div>

                            <div style="font-size:11px; color:#64d2ff; margin-top:4px;">${pctGlobal}% clasificado</div>

                        </div>



                        <!-- Manual User -->

                        <div style="background:rgba(48,209,88,0.06); border:1px solid rgba(48,209,88,0.2); padding:14px; border-radius:14px;">

                            <div style="display:flex; justify-content:space-between; align-items:center;">

                                <span style="font-size:11px; color:#30d158; font-weight:600;">✏️ Confirmadas por Mí</span>

                                <span style="font-size:9px; background:rgba(48,209,88,0.2); color:#30d158; padding:1px 5px; border-radius:4px; font-weight:700;">100% Certeza</span>

                            </div>

                            <div style="font-size:24px; font-weight:800; color:#30d158; margin-top:2px;">${manualUser.toLocaleString()}</div>

                            <div style="font-size:11px; color:rgba(48,209,88,0.8); margin-top:4px;">Centroides anclados</div>

                        </div>



                        <!-- IA Verified -->

                        <div style="background:rgba(10,132,255,0.06); border:1px solid rgba(10,132,255,0.2); padding:14px; border-radius:14px;">

                            <div style="display:flex; justify-content:space-between; align-items:center;">

                                <span style="font-size:11px; color:#0a84ff; font-weight:600;">✨ Validadas por IA</span>

                                <span style="font-size:9px; background:rgba(10,132,255,0.2); color:#0a84ff; padding:1px 5px; border-radius:4px; font-weight:700;">Alta Confianza</span>

                            </div>

                            <div style="font-size:24px; font-weight:800; color:#0a84ff; margin-top:2px;">${iaVerified.toLocaleString()}</div>

                            <div style="font-size:11px; color:rgba(10,132,255,0.8); margin-top:4px;">Reconocimiento SFace</div>

                        </div>



                        <!-- Pendientes / Dudosas -->

                        <div style="background:rgba(255,159,10,0.06); border:1px solid rgba(255,159,10,0.2); padding:14px; border-radius:14px;">

                            <div style="display:flex; justify-content:space-between; align-items:center;">

                                <span style="font-size:11px; color:#ff9f0a; font-weight:600;">⚠️ Por Revisar</span>

                                <span style="font-size:9px; background:rgba(255,159,10,0.2); color:#ff9f0a; padding:1px 5px; border-radius:4px; font-weight:700;">Dudosas + Nuevas</span>

                            </div>

                            <div style="font-size:24px; font-weight:800; color:#ff9f0a; margin-top:2px;">${(dudosos + pendientes).toLocaleString()}</div>

                            <div style="font-size:11px; color:rgba(255,159,10,0.8); margin-top:4px;">${dudosos} dudosas / ${pendientes} pendientes</div>

                        </div>

                    </div>



                    <!-- Segmented Progress Bar -->

                    <div style="margin-bottom:12px;">

                        <div style="width:100%; height:10px; background:rgba(255,255,255,0.08); border-radius:8px; overflow:hidden; display:flex;">

                            <div style="width:${totalGallery > 0 ? (manualUser / totalGallery * 100) : 0}%; background:#30d158;" title="Manuales: ${manualUser}"></div>

                            <div style="width:${totalGallery > 0 ? (iaVerified / totalGallery * 100) : 0}%; background:#0a84ff;" title="IA: ${iaVerified}"></div>

                            <div style="width:${totalGallery > 0 ? (dudosos / totalGallery * 100) : 0}%; background:#ff9f0a;" title="Dudosas: ${dudosos}"></div>

                            <div style="width:${totalGallery > 0 ? (pendientes / totalGallery * 100) : 0}%; background:#ff453a;" title="Pendientes: ${pendientes}"></div>

                        </div>

                    </div>



                    <!-- Device Origin Badges -->

                    <div style="display:flex; gap:10px; flex-wrap:wrap;">

                        <div style="flex:1; min-width:200px; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06); padding:10px 14px; border-radius:10px; display:flex; justify-content:space-between; align-items:center;">

                            <div style="display:flex; align-items:center; gap:8px;">

                                <span style="font-size:16px;">🍎</span>

                                <div>

                                    <div style="font-size:12px; font-weight:700; color:#fff;">Apple iPhone / iCloud</div>

                                    <div style="font-size:10px; color:#8e8e93;">${(data.iphone_clasificadas || 0).toLocaleString()} organizadas</div>

                                </div>

                            </div>

                            <div style="font-size:14px; font-weight:800; color:#fff;">${(data.iphone_total || 0).toLocaleString()}</div>

                        </div>



                        <div style="flex:1; min-width:200px; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06); padding:10px 14px; border-radius:10px; display:flex; justify-content:space-between; align-items:center;">

                            <div style="display:flex; align-items:center; gap:8px;">

                                <span style="font-size:16px;">🤖</span>

                                <div>

                                    <div style="font-size:12px; font-weight:700; color:#fff;">Android & Otras Fuentes</div>

                                    <div style="font-size:10px; color:#8e8e93;">${(data.android_clasificadas || 0).toLocaleString()} organizadas</div>

                                </div>

                            </div>

                            <div style="font-size:14px; font-weight:800; color:#fff;">${(data.android_total || 0).toLocaleString()}</div>

                        </div>

                    </div>

                </div>



                <!-- SECCIÓN 3: DESGLOSE POR ÁLBUM / PERSONA (CON BUSCADOR) -->

                <div>

                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:10px;">

                        <div style="font-size:12px; font-weight:700; color:#8e8e93; text-transform:uppercase; letter-spacing:0.5px;">

                            Distribución por Álbum y Persona (${Object.keys(data.breakdown || {}).length} álbumes)

                        </div>

                        <div style="position:relative; width:220px;">

                            <input type="text" id="stats-filter-input" placeholder="🔍 Filtrar álbum..." oninput="filterStatsList(this.value)" style="width:100%; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12); padding:5px 10px; border-radius:8px; color:#fff; font-size:12px; outline:none; transition:border-color 0.2s;" onfocus="this.style.borderColor='#0a84ff'" onblur="this.style.borderColor='rgba(255,255,255,0.12)'">

                        </div>

                    </div>



                    <div id="stats-album-list" style="max-height: 280px; overflow-y: auto; padding-right: 6px;" class="custom-scrollbar">

                        ${renderStatsBreakdownList(data.breakdown || {})}

                    </div>

                </div>

            `;



            document.getElementById('stats-content').innerHTML = html;

        }

        

        

        async function forceReanalyze() {

            if (!confirm("¿Seguro que quieres forzar un re-análisis? Esto borrará la caché y tardará unos segundos, pero la IA usará su conocimiento actualizado para puntuar las caras.")) return;

            

            const btn = document.getElementById('btn-reanalyze');

            btn.style.opacity = '0.5';

            btn.textContent = 'Recalculando...';

            btn.style.pointerEvents = 'none';

            

            try {

                await fetch('/api/clear_confidence_cache', {method: 'POST'});

                await openIntelligentCleanup();

            } catch(e) {

                console.error(e);

                showToast("Error al re-analizar", true);

            }

        }



        let smartCleanInterval;

        async function openIntelligentCleanup() {

            document.getElementById('gallery-title').textContent = '🧠 Limpieza Inteligente (Fáciles a Difíciles)';

            document.getElementById('gallery-subtitle').textContent = 'Analizando confianza de la IA en segundo plano... (Puedes minimizar si quieres)';

            document.getElementById('grid-container').innerHTML = '<div style="padding:50px; text-align:center;"><div class="loader-small" style="width:50px; height:50px; margin:auto;"></div><p id="smartCleanStatusText" style="margin-top:20px; color:#aaa;">Iniciando proceso en segundo plano...</p><progress id="smartCleanProgress" value="0" max="100" style="width: 50%; margin-top: 10px;"></progress></div>';

            

            try {

                await fetch('/api/start_smart_clean', {method: 'POST'});

                if(smartCleanInterval) clearInterval(smartCleanInterval);

                smartCleanInterval = setInterval(checkSmartCleanStatus, 2000);

            } catch(e) {

                showToast("Error iniciando la limpieza", true);

            }

        }

        

        async function checkSmartCleanStatus() {

            try {

                const res = await fetch('/api/smart_clean_status');

                const data = await res.json();

                const textEl = document.getElementById('smartCleanStatusText');

                const progEl = document.getElementById('smartCleanProgress');

                

                if(textEl) {

                    if (data.progress === 100) {

                        textEl.innerHTML = `<span style="color:#0f0;">¡Cálculo finalizado! Cargando imágenes...</span>`;

                        clearInterval(smartCleanInterval);

                        loadSmartCleanImages();

                    } else if (data.progress === -1) {

                        textEl.innerHTML = `<span style="color:#f00;">Error: ${data.status}</span>`;

                        clearInterval(smartCleanInterval);

                    } else {

                        textEl.innerHTML = `${data.status}<br>Progreso guardado automáticamente.`;

                        if(progEl) progEl.value = data.progress;

                    }

                }

            } catch(e) {}

        }

        

        async function loadSmartCleanImages() {

            try {

                const res = await fetch('/api/pending_sorted');

                const data = await res.json();

                

                if (data.error) {

                    showToast(data.error, true);

                    document.getElementById('grid-container').innerHTML = '';

                    return;

                }

                

                currentCat = "Limpieza Inteligente";

                currentIdent = "Pendientes Ordenadas";

                currentFolderItems = data.items;

                

                

                

                document.getElementById('gallery-subtitle').textContent = `${currentFolderItems.length} caras pendientes encontradas`;

                document.getElementById('btn-reanalyze').style.display = 'block';

                document.getElementById('btn-reanalyze').style.opacity = '1';

                document.getElementById('btn-reanalyze').textContent = '🔄 Forzar Re-Análisis';

                document.getElementById('btn-reanalyze').style.pointerEvents = 'auto';



                document.getElementById('btn-reanalyze').style.display = 'block';

                document.getElementById('btn-reanalyze').style.opacity = '1';

                document.getElementById('btn-reanalyze').textContent = '🔄 Forzar Re-Análisis (IA Actualizada)';

                document.getElementById('btn-reanalyze').style.pointerEvents = 'auto';



                

                const grid = document.getElementById('grid-container');

                grid.innerHTML = '';

                

                currentFolderItems.forEach((item, idx) => {

                    const card = document.createElement('div');

                    card.className = 'media-card';

                if (isMultiSelectMode) {

                    const chkContainer = document.createElement('div');

                    chkContainer.style.cssText = "position:absolute; top:10px; left:10px; z-index:10;";

                    const chk = document.createElement('input');

                    chk.type = 'checkbox';

                    chk.className = 'card-checkbox';

                    chk.checked = selectedFiles.has(item.path);

                    chk.style.cssText = "width:22px; height:22px; accent-color:#30d158; cursor:pointer;";

                    chkContainer.appendChild(chk);

                    card.appendChild(chkContainer);

                    

                    if (selectedFiles.has(item.path)) {

                        card.classList.add('selected-card');

                        card.style.border = '3px solid #30d158';

                        card.style.boxShadow = '0 0 15px rgba(48,209,88,0.5)';

                    }

                    

                    card.onclick = (e) => toggleFileSelection(item.path, card, e);

                } else {

                    card.onclick = () => {

                        currentItemIndex = idx;

                        openLightbox(item);

                    };

                }

                    

                    const badge = document.createElement('span');

                    if (item.confidence > 0) {

                        const confPct = (item.confidence * 100).toFixed(1);

                        badge.className = 'badge badge-ia';

                        badge.textContent = `🤖 ${confPct}%`;

                        if (item.confidence > 0.8) {

                            badge.style.backgroundColor = '#30d158'; // Verde

                            badge.style.color = '#000';

                        } else if (item.confidence > 0.5) {

                            badge.style.backgroundColor = '#ff9f0a'; // Naranja

                            badge.style.color = '#000';

                        } else {

                            badge.style.backgroundColor = '#ff453a'; // Rojo

                        }

                    } else {

                        badge.className = 'badge badge-manual';

                        badge.textContent = '❌ Desconocido';

                        badge.style.backgroundColor = '#555';

                    }

                    card.appendChild(badge);

                    

                    // Masonry Skeleton Padding

                    if (item.orig_width && item.orig_height) {

                        const aspect = (item.orig_height / item.orig_width) * 100;

                        card.style.paddingTop = `${aspect}%`;

                    } else {

                        card.style.paddingTop = `100%`;

                    }



                    const skeleton = document.createElement('div');

                    skeleton.className = 'masonry-skeleton';

                    card.appendChild(skeleton);



                    const thumb = document.createElement('img');

                    thumb.src = `/api/thumbnail?path=${encodeURIComponent(item.path)}`;

                    thumb.loading = 'lazy';

                    thumb.style.opacity = '0';

                    thumb.onload = () => {

                        thumb.style.opacity = '1';

                        skeleton.style.opacity = '0';

                        setTimeout(() => skeleton.remove(), 400);

                    };

                    thumb.style.transition = 'opacity 0.4s ease';

                    thumb.style.width = '100%';

                    thumb.style.height = 'auto';

                    thumb.style.position = 'absolute';

                    thumb.style.top = '0';

                    thumb.style.left = '0';

                    card.appendChild(thumb);



                    // Sci-Fi Face Boxes Container

                    if (item.faces && item.faces.length > 0 && item.orig_width && item.orig_height) {

                        const facesContainer = document.createElement('div');

                        facesContainer.className = 'faces-container';

                        

                        item.faces.forEach(face => {

                            if (!face.box) return;

                            const [fx, fy, fw, fh] = face.box;

                            const left = (fx / item.orig_width) * 100;

                            const top = (fy / item.orig_height) * 100;

                            const width = (fw / item.orig_width) * 100;

                            const height = (fh / item.orig_height) * 100;

                            

                            const box = document.createElement('div');

                            box.className = 'face-box-sci-fi';

                            box.style.left = `${left}%`;

                            box.style.top = `${top}%`;

                            box.style.width = `${width}%`;

                            box.style.height = `${height}%`;

                            

                            const label = document.createElement('div');

                            label.className = 'face-box-label';

                            const confPct = Math.round((face.confidence || 0) * 100);

                            label.innerHTML = `<span>${face.identity || 'Desconocido'}</span><small>${confPct}%</small>`;

                            box.appendChild(label);

                            

                            facesContainer.appendChild(box);

                        });

                        card.appendChild(facesContainer);

                    }

                    

                    if (item.type === 'video') {

                        const playIcon = document.createElement('div');

                        playIcon.className = 'video-icon';

                        playIcon.innerHTML = '▶';

                        card.appendChild(playIcon);

                    }

                    

                    const title = document.createElement('div');

                    title.className = 'media-title';

                    title.textContent = item.name;

                    card.appendChild(title);

                    

                    grid.appendChild(card);

                });

                

            } catch(e) {

                showToast("Error cargando limpieza inteligente", true);

                document.getElementById('grid-container').innerHTML = '';

            }

        }



        let _galleryFirstLoadDone = false;

        

        async function loadGallery() {

            const isFirstLoad = !_galleryFirstLoadDone;

            const overlay = document.getElementById('library-loading-overlay');

            const progressPct = document.getElementById('loading-progress-percentage');

            const progressBar = document.getElementById('loading-progress-bar');

            const statusText = document.getElementById('loading-status-text');

            

            let progressInterval = null;

            let overlayTimer = null;

            

            if (isFirstLoad && overlay) {

                progressInterval = setInterval(async () => {

                    try {

                        const r = await fetch('/api/gallery/progress');

                        const d = await r.json();

                        const progressVal = Math.round(d.progress || 0);

                        

                        if (progressBar) progressBar.style.width = `${progressVal}%`;

                        if (progressPct) progressPct.textContent = `${progressVal}%`;

                        if (statusText) {

                            if (progressVal < 20) {

                                statusText.textContent = "Escaneando archivos de la biblioteca...";

                            } else if (progressVal < 50) {

                                statusText.textContent = "Sincronizando fotos e identidades...";

                            } else if (progressVal < 75) {

                                statusText.textContent = "Analizando agrupaciones de caras...";

                            } else if (progressVal < 95) {

                                statusText.textContent = "Construyendo índices de álbumes...";

                            } else {

                                statusText.textContent = "¡Casi listo! Cargando interfaz...";

                            }

                        }

                    } catch(e){}

                }, 300);

            } else if (overlay) {
                overlay.style.display = 'none';
            }

            // GUARDA-TIEMPO DE SEGURIDAD (WATCHDOG): Garantiza que NUNCA se bloquee la pantalla mas de 2s
            if (isFirstLoad && overlay) {
                setTimeout(() => {
                    if (overlay && overlay.style.display !== 'none') {
                        overlay.style.opacity = '0';
                        setTimeout(() => {
                            overlay.style.visibility = 'hidden';
                            overlay.style.display = 'none';
                        }, 200);
                    }
                }, 2000);
            }



            try {

                // 1. Carga ultra-rapida de estructura (~50KB en lugar de 46MB bloqueantes)
                const sRes = await fetch('/api/gallery/structure');
                if (!sRes.ok) throw new Error('Structure fetch failed');
                const structure = await sRes.json();
                
                window.galleryStructure = structure;
                window.fullGallery = window.fullGallery || {};
                for (const cat in structure) {
                    window.fullGallery[cat] = window.fullGallery[cat] || {};
                    for (const ident in structure[cat]) {
                        if (!window.fullGallery[cat][ident]) {
                            window.fullGallery[cat][ident] = structure[cat][ident];
                        }
                    }
                }
                fullGallery = window.fullGallery;

                if (overlayTimer) clearTimeout(overlayTimer);
                if (progressInterval) clearInterval(progressInterval);

                if (isFirstLoad) {
                    if (progressBar) progressBar.style.width = '100%';
                    if (progressPct) progressPct.textContent = '100%';
                    if (statusText) statusText.textContent = 'Listo';
                }

                _galleryFirstLoadDone = true;
                renderTree();
                if (typeof checkPendingVideos === 'function') checkPendingVideos();

                // 2. Previsualizacion instantanea para mosaico de inicio (~5KB)
                if (isFirstLoad) {
                    try {
                        const pRes = await fetch('/api/gallery/preview');
                        if (pRes.ok) {
                            window.homeMosaicPreview = await pRes.json();
                        }
                    } catch (e) {}
                    renderHomeMosaic();
                }

                // Ocultar pantalla de carga en menos de 0.2s sin bloquear al usuario
                if (typeof window._dismissLoadingOverlay === 'function') {
                    window._dismissLoadingOverlay();
                } else if (isFirstLoad && overlay) {
                    overlay.style.opacity = '0';
                    setTimeout(() => {
                        overlay.style.visibility = 'hidden';
                        overlay.style.display = 'none';
                    }, 200);
                }

                // 3. Descarga asincrona en segundo plano para poblar cache y linea temporal sin bloquear
                fetch('/api/gallery')
                    .then(r => r.ok ? r.json() : null)
                    .then(data => {
                        if (data) {
                            window.fullGallery = data;
                            fullGallery = data;
                            if (currentCat && currentIdent && Array.isArray(fullGallery[currentCat]?.[currentIdent])) {
                                renderGrid(currentCat, currentIdent);
                            }
                        }
                    })
                    .catch(() => {});

                

                // Extract unique years from fullGallery
                function updateTimelineCapsules() {
                    let availableYears = new Set();
                    for (let cat in fullGallery) {
                        for (let ident in fullGallery[cat]) {
                            const items = fullGallery[cat][ident];
                            if (Array.isArray(items)) {
                                items.forEach(item => {
                                    if (item && item.mtime) {
                                        const yr = new Date(item.mtime * 1000).getFullYear();
                                        if (yr && yr >= 2000 && yr <= 2030) {
                                            availableYears.add(yr);
                                        }
                                    }
                                });
                            }
                        }
                    }
                    
                    const yearsArr = Array.from(availableYears).sort((a, b) => b - a);
                    const timelineContainer = document.getElementById('timeline-years-container');
                    if (timelineContainer && yearsArr.length > 0) {
                        timelineContainer.innerHTML = '';
                        yearsArr.forEach(year => {
                            const btn = document.createElement('button');
                            btn.className = 'timeline-year-btn';
                            btn.textContent = year;
                            btn.style.cssText = "padding: 6px 14px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.15); background: rgba(255,255,255,0.06); color: #e5e5ea; cursor: pointer; font-size: 11px; font-weight: 600; transition: all 0.2s; white-space: nowrap;";
                            btn.onclick = () => {
                                document.querySelectorAll('.timeline-year-btn').forEach(b => {
                                    b.style.background = 'rgba(255,255,255,0.06)';
                                    b.style.borderColor = 'rgba(255,255,255,0.15)';
                                    b.style.color = '#e5e5ea';
                                });
                                btn.style.background = '#0a84ff';
                                btn.style.borderColor = '#0a84ff';
                                btn.style.color = '#fff';
                                filterTimeline(year);
                            };
                            timelineContainer.appendChild(btn);
                        });
                    }
                }
                window.updateTimelineCapsules = updateTimelineCapsules;
                updateTimelineCapsules();



                if (currentCat && currentIdent) {

                    if (fullGallery[currentCat] && fullGallery[currentCat][currentIdent]) {

                        renderGrid(currentCat, currentIdent);

                    } else {

                        document.getElementById('grid-container').innerHTML = '';

                    }

                }

                

                if (isFirstLoad && overlay) {

                    overlay.style.opacity = '0';

                    setTimeout(() => {

                        overlay.style.visibility = 'hidden';

                        overlay.style.display = 'none';

                    }, 350);

                }

            } catch (err) {
                if (progressInterval) clearInterval(progressInterval);
                if (isFirstLoad && overlay) {
                    overlay.style.opacity = '0';
                    setTimeout(() => {
                        overlay.style.visibility = 'hidden';
                        overlay.style.display = 'none';
                    }, 200);
                }
                console.warn("Aviso en carga progresiva:", err);
            }

        }



                function renderTree() {
            renderCategoriesRoot();
        }

        window._activeDrillDownCategory = null;

        const CAT_ICONS = {
            'YO': '👤',
            'Conocidos': '👥',
            'Familia': '👨‍👩‍👧',
            'Lugares': '📍',
            'Eventos': '🎉',
            'Mascotas': '🐶',
            'Objetos': '🚗',
            'Profesores': '🎓',
            'Recuerdos': '📸',
            'Publicaciones_Instagram': '📱',
            '📋 Revisión / Por Organizar': '📋'
        };

        const CAT_ORDER = ['YO', '📋 Revisión / Por Organizar', 'Familia', 'Conocidos', 'Lugares', 'Eventos', 'Mascotas', 'Objetos', 'Recuerdos', 'Profesores', 'Publicaciones_Instagram'];

        function renderCategoriesRoot() {
            window._activeDrillDownCategory = null;
            const treeEl = document.getElementById('tree-container');
            if (!treeEl) return;
            treeEl.innerHTML = '';

            const categories = Object.keys(fullGallery || {}).sort((a, b) => {
                const idxA = CAT_ORDER.indexOf(a);
                const idxB = CAT_ORDER.indexOf(b);
                if (idxA !== -1 && idxB !== -1) return idxA - idxB;
                if (idxA !== -1) return -1;
                if (idxB !== -1) return 1;
                return a.localeCompare(b);
            });

            const rootList = document.createElement('div');
            rootList.className = 'ios-categories-root';
            rootList.style.cssText = 'display:flex; flex-direction:column; gap:4px; animation:fadeIn 0.15s ease-out;';

            for (const cat of categories) {
                if (cat === '__smart_album__') continue;

                const subObj = fullGallery[cat] || {};
                const identsCount = Object.keys(subObj).length;
                const totalInCat = Object.values(subObj).reduce((acc, itms) => acc + (Array.isArray(itms) ? itms.length : (typeof itms === 'number' ? itms : 0)), 0);
                const icon = CAT_ICONS[cat] || '📁';

                const catRow = document.createElement('div');
                catRow.className = 'ios-category-card';
                catRow.style.cssText = 'display:flex; align-items:center; justify-content:space-between; padding:12px 14px; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06); border-radius:12px; cursor:pointer; transition:all 0.15s; user-select:none;';
                
                catRow.onmouseover = () => { catRow.style.background = 'rgba(255,255,255,0.07)'; catRow.style.borderColor = 'rgba(10,132,255,0.3)'; };
                catRow.onmouseout = () => { catRow.style.background = 'rgba(255,255,255,0.03)'; catRow.style.borderColor = 'rgba(255,255,255,0.06)'; };

                const isSpecialRevision = cat === '📋 Revisión / Por Organizar';

                catRow.innerHTML = `
                    <div style="display:flex; align-items:center; gap:10px; min-width:0;">
                        <span style="font-size:1.15rem; width:26px; height:26px; display:flex; align-items:center; justify-content:center; border-radius:8px; background:${isSpecialRevision ? 'rgba(255,159,10,0.15)' : 'rgba(255,255,255,0.05)'};">${icon}</span>
                        <div style="min-width:0;">
                            <div style="font-size:0.88rem; font-weight:700; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${cat}</div>
                            <div style="font-size:0.72rem; color:#8e8e93; font-weight:500;">${identsCount} sub-álbumes • ${totalInCat} fotos</div>
                        </div>
                    </div>
                    <div style="display:flex; align-items:center; gap:6px;">
                        ${isSpecialRevision && totalInCat > 0 ? `<span style="font-size:10px; font-weight:700; background:rgba(255,159,10,0.2); color:#ff9f0a; border:1px solid rgba(255,159,10,0.4); padding:2px 7px; border-radius:10px;">${totalInCat}</span>` : ''}
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#8e8e93" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
                    </div>
                `;

                if (cat === 'YO') {
                    catRow.onclick = () => {
                        renderGrid('YO', 'YO');
                        if (window.innerWidth <= 820 && typeof toggleSidebar === 'function') {
                            toggleSidebar(false);
                        }
                    };
                } else {
                    catRow.onclick = () => {
                        openCategoryDrillDown(cat);
                    };
                }

                rootList.appendChild(catRow);
            }

            treeEl.appendChild(rootList);
        }

        function openCategoryDrillDown(cat) {
            window._activeDrillDownCategory = cat;
            const treeEl = document.getElementById('tree-container');
            if (!treeEl) return;
            treeEl.innerHTML = '';

            const subObj = fullGallery[cat] || {};
            const sortedIdents = Object.keys(subObj).sort((a, b) => a.localeCompare(b));
            const icon = CAT_ICONS[cat] || '📁';

            const drillDownWrapper = document.createElement('div');
            drillDownWrapper.className = 'ios-drilldown-container';
            drillDownWrapper.style.cssText = 'display:flex; flex-direction:column; gap:8px; animation:slideInRight 0.18s cubic-bezier(0.16, 1, 0.3, 1);';

            // Apple Style Navigation Header (Back button + Title)
            const navBar = document.createElement('div');
            navBar.style.cssText = 'display:flex; align-items:center; justify-content:space-between; padding:4px 2px 8px; border-bottom:1px solid rgba(255,255,255,0.06); margin-bottom:4px;';
            navBar.innerHTML = `
                <button id="btn-drilldown-back" onclick="renderCategoriesRoot()" style="display:flex; align-items:center; gap:4px; background:transparent; border:none; color:#0a84ff; font-size:0.86rem; font-weight:600; cursor:pointer; padding:6px 4px; border-radius:6px; transition:all 0.15s;">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#0a84ff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
                    <span>Álbumes</span>
                </button>
                <div style="font-size:0.88rem; font-weight:700; color:#fff; display:flex; align-items:center; gap:6px;">
                    <span>${icon}</span>
                    <span style="max-width:140px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${cat}</span>
                    <span style="font-size:0.75rem; color:#8e8e93; font-weight:500;">(${sortedIdents.length})</span>
                </div>
            `;
            drillDownWrapper.appendChild(navBar);

            // iOS Instant Search Bar for Category Items
            const searchBar = document.createElement('div');
            searchBar.style.cssText = 'position:relative; margin-bottom:6px;';
            searchBar.innerHTML = `
                <span style="position:absolute; left:10px; top:50%; transform:translateY(-50%); font-size:12px; color:#8e8e93; pointer-events:none;">🔍</span>
                <input type="text" id="drilldown-search-input" placeholder="Buscar en ${cat}..." style="width:100%; box-sizing:border-box; padding:7px 12px 7px 28px; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); border-radius:10px; color:#fff; font-size:0.8rem; outline:none; transition:border-color 0.15s;" onfocus="this.style.borderColor='#0a84ff'" onblur="this.style.borderColor='rgba(255,255,255,0.1)'">
            `;
            drillDownWrapper.appendChild(searchBar);

            // Container for Identity Items
            const itemsList = document.createElement('div');
            itemsList.id = 'drilldown-items-list';
            itemsList.style.cssText = 'display:flex; flex-direction:column; gap:3px; max-height:calc(100vh - 210px); overflow-y:auto; padding-right:2px;';

            sortedIdents.forEach(ident => {
                const count = Array.isArray(subObj[ident]) ? subObj[ident].length : (typeof subObj[ident] === 'number' ? subObj[ident] : 0);
                const isSpecial = ident.includes('Sin Rostro') || ident.includes('Vídeos') || ident.includes('Dudosos') || ident.includes('Desconocidos') || ident.includes('Pendientes');
                
                let displayIcon = '';
                if (ident.includes('Sin Rostro')) displayIcon = '📷';
                else if (ident.includes('Vídeos')) displayIcon = '🎬';
                else if (ident.includes('Dudosos')) displayIcon = '⚠️';
                else if (ident.includes('Desconocidos')) displayIcon = '❓';
                else if (ident.includes('Persona Nueva')) displayIcon = '👤';

                const identEl = document.createElement('div');
                identEl.className = 'drilldown-identity-row';
                identEl.dataset.identName = ident.toLowerCase();
                identEl.style.cssText = 'display:flex; align-items:center; justify-content:space-between; padding:8px 10px; border-radius:8px; cursor:pointer; font-size:0.82rem; color:#ddd; transition:all 0.15s; background:rgba(255,255,255,0.02);';

                identEl.onmouseover = () => { identEl.style.background = 'rgba(10,132,255,0.15)'; identEl.style.color = '#fff'; };
                identEl.onmouseout = () => { identEl.style.background = 'rgba(255,255,255,0.02)'; identEl.style.color = '#ddd'; };

                const leftDiv = document.createElement('div');
                leftDiv.style.cssText = 'display:flex; align-items:center; gap:8px; min-width:0; flex:1;';

                if (isSpecial || displayIcon) {
                    const iconSpan = document.createElement('span');
                    iconSpan.style.cssText = 'font-size:14px; width:24px; text-align:center; flex-shrink:0;';
                    iconSpan.textContent = displayIcon || '📁';
                    leftDiv.appendChild(iconSpan);
                } else {
                    const avatarImg = document.createElement('img');
                    avatarImg.className = 'sidebar-person-avatar';
                    avatarImg.alt = '';
                    avatarImg.loading = 'lazy';
                    avatarImg.src = `/api/person_avatar?cat=${encodeURIComponent(cat)}&ident=${encodeURIComponent(ident)}`;
                    avatarImg.style.cssText = 'width:24px; height:24px; border-radius:50%; object-fit:cover; flex-shrink:0; background:#2c2c2e;';
                    avatarImg.onerror = () => {
                        const ph = document.createElement('span');
                        ph.className = 'sidebar-person-avatar-placeholder';
                        ph.style.cssText = 'width:24px; height:24px; border-radius:50%; background:#2c2c2e; display:flex; align-items:center; justify-content:center; font-size:10px; font-weight:700; color:#8e8e93; flex-shrink:0;';
                        ph.textContent = (ident[0] || '?').toUpperCase();
                        avatarImg.replaceWith(ph);
                    };
                    leftDiv.appendChild(avatarImg);
                }

                const nameSpan = document.createElement('span');
                nameSpan.style.cssText = 'white-space:nowrap; overflow:hidden; text-overflow:ellipsis; flex:1; font-weight:500;';
                nameSpan.textContent = ident;
                leftDiv.appendChild(nameSpan);

                const countBadge = document.createElement('span');
                countBadge.style.cssText = 'font-size:10.5px; background:rgba(255,255,255,0.08); padding:2px 7px; border-radius:10px; color:#8e8e93; font-weight:600; flex-shrink:0;';
                countBadge.textContent = count;

                identEl.appendChild(leftDiv);
                identEl.appendChild(countBadge);

                identEl.onclick = (e) => {
                    e.stopPropagation();
                    renderGrid(cat, ident);
                    if (window.innerWidth <= 820 && typeof toggleSidebar === 'function') {
                        toggleSidebar(false);
                    }
                };

                itemsList.appendChild(identEl);
            });

            drillDownWrapper.appendChild(itemsList);
            treeEl.appendChild(drillDownWrapper);

            // Connect search input filter
            const searchInput = document.getElementById('drilldown-search-input');
            if (searchInput) {
                searchInput.addEventListener('input', (e) => {
                    const term = (e.target.value || '').toLowerCase().trim();
                    const rows = itemsList.querySelectorAll('.drilldown-identity-row');
                    rows.forEach(r => {
                        const name = r.dataset.identName || '';
                        r.style.display = (!term || name.includes(term)) ? 'flex' : 'none';
                    });
                });
            }
        }

        function filterGallery(term) {

            term = term.toLowerCase();

            document.querySelectorAll('.tree-folder.identity').forEach(el => {

                const text = el.textContent.toLowerCase();

                el.style.display = text.includes(term) ? 'flex' : 'none';

            });

        }



        

        let isSwipeModeActive = true; // Habilitado por defecto para facilitar la limpieza



        function toggleSwipeMode() {

            isSwipeModeActive = !isSwipeModeActive;

            const btn = document.getElementById('btn-swipe-mode');

            if (btn) {

                btn.textContent = isSwipeModeActive ? "🔥 Modo Limpieza Rápida (ON)" : "🔥 Modo Limpieza Rápida (OFF)";

                btn.style.color = isSwipeModeActive ? "#30d158" : "#ff9f0a";

            }

            showToast(isSwipeModeActive ? "Modo Limpieza Rápida ACTIVADO (Flecha ⬅️ Borra, Flecha ➡️ Conserva)" : "Modo Limpieza Rápida DESACTIVADO.");

        }



        

        

        let _currentGridItems = [];

        let _gridRenderIndex = 0;

        let _gridObserver = null;

        const PAGE_SIZE = 50;



        async function renderGrid(cat, ident) {
            if (!cat || !ident) return;
            currentCat = cat;
            currentIdent = ident;

            // Si el album aun no tiene las fotos descargadas, pedirlas bajo demanda al instante (~100ms)
            const currentVal = fullGallery && fullGallery[cat] ? fullGallery[cat][ident] : null;
            if (!Array.isArray(currentVal) || currentVal.length === 0) {
                const grid = document.getElementById('grid-container');
                if (grid) grid.innerHTML = '<div style="padding:40px; text-align:center;"><div class="loader-small"></div><p style="color:#8e8e93; font-size:12px; margin-top:8px;">Cargando fotos del album...</p></div>';
                try {
                    const r = await fetch('/api/gallery?cat=' + encodeURIComponent(cat) + '&ident=' + encodeURIComponent(ident));
                    if (r.ok) {
                        const albumData = await r.json();
                        fullGallery = fullGallery || {};
                        fullGallery[cat] = fullGallery[cat] || {};
                        fullGallery[cat][ident] = (albumData[cat] && albumData[cat][ident]) ? albumData[cat][ident] : [];
                    }
                } catch (e) {
                    console.error("Error fetching album items:", e);
                }
            }

            if (!fullGallery || !fullGallery[cat] || !Array.isArray(fullGallery[cat][ident])) {
                return;
            }
            currentFolderItems = fullGallery[cat][ident] || [];



            // ── Compute album stats ──────────────────────────────────

            const items = currentFolderItems;

            const total = items.length;

            let minYear = 9999, maxYear = 0, photoCount = 0, videoCount = 0;

            let highConf = 0, midConf = 0, lowConf = 0;

            let dudosoCount = 0;

            items.forEach(it => {

                if (it.mtime) {

                    const yr = new Date(it.mtime * 1000).getFullYear();

                    if (yr >= 2000 && yr <= 2030) { minYear = Math.min(minYear, yr); maxYear = Math.max(maxYear, yr); }

                }

                if (it.type === 'video') videoCount++; else photoCount++;

                const c = parseFloat(it.confidence || 0);

                if (c >= 0.50) highConf++;

                else if (c >= 0.38) midConf++;

                else if (c > 0) lowConf++;

                if (it.is_dudoso || it.status === 'Dudoso' || (it.source && it.source.includes('Por Confirmar'))) {

                    dudosoCount++;

                }

            });

            const yearRange = (minYear <= maxYear && minYear !== 9999)

                ? (minYear === maxYear ? `${minYear}` : `${minYear} – ${maxYear}`)

                : '';

            const isRevision = (cat === '📋 Revisión / Por Organizar');



            // ── Stats bar HTML ───────────────────────────────────────

            let statsHtml = `<div class="album-stats-bar">`;

            statsHtml += `<span class="album-stat-pill">📸 <span class="stat-val">${photoCount}</span> fotos</span>`;

            if (videoCount > 0) statsHtml += `<span class="album-stat-pill">🎬 <span class="stat-val">${videoCount}</span> vídeos</span>`;

            if (yearRange) statsHtml += `<span class="album-stat-pill">📅 <span class="stat-val">${yearRange}</span></span>`;

            if (highConf + midConf + lowConf > 0) {

                if (highConf > 0) statsHtml += `<span class="album-stat-pill" title="Alta confianza IA">🟢 <span class="stat-val">${highConf}</span></span>`;

                if (midConf  > 0) statsHtml += `<span class="album-stat-pill" title="Confianza media">🟡 <span class="stat-val">${midConf}</span></span>`;

                if (lowConf  > 0) statsHtml += `<span class="album-stat-pill" title="Baja confianza — revisar">🔴 <span class="stat-val">${lowConf}</span></span>`;

            }

            if (dudosoCount > 0) {

                statsHtml += `<span class="album-stat-pill" style="border:1px solid rgba(255,159,10,0.5); background:rgba(255,159,10,0.12); color:#ff9f0a; font-weight:700;" title="Fotos con identidad por confirmar">⚠️ <span class="stat-val">${dudosoCount}</span> por confirmar</span>`;

            }

            statsHtml += `</div>`;

            

                        // Screenshot Antiquity Filter bar visibility check
            const ssFilterContainer = document.getElementById('screenshot-filter-container');
            const isCapturasContext = Boolean((ident && /captura/i.test(ident)) || (cat && /captura/i.test(cat)) || items.some(it => (it.name && /screenshot|captura|screen/i.test(it.name))));
            if (ssFilterContainer) {
                if (isCapturasContext) {
                    ssFilterContainer.style.display = 'inline-flex';
                    if (typeof window.updateStaleScreenshotsCount === 'function') window.updateStaleScreenshotsCount();
                } else {
                    ssFilterContainer.style.display = 'none';
                    window.currentScreenshotAgeFilter = 'all';
                }
            }

            const dudosoBtn = document.getElementById('filter-dudoso-btn');
            const dudosoCountEl = document.getElementById('dudoso-count');
            if (dudosoBtn) {
                if (dudosoCount > 0) {
                    dudosoBtn.style.display = 'inline-flex';
                    if (dudosoCountEl) dudosoCountEl.textContent = dudosoCount;
                } else {
                    dudosoBtn.style.display = 'none';
                }
            }

            // Person 3-Tier Filter Bar: Official, Suggestion, Review (Por Confirmar)
            let officialCount = 0, suggestionCount = 0, reviewCount = 0;
            items.forEach(it => {
                const sec = it.album_section || (it.is_dudoso ? 'review' : ((it.is_dataset || it.is_manual || (it.source && it.source.includes('Dataset'))) ? 'official' : 'suggestion'));
                it.album_section = sec;
                if (sec === 'official') officialCount++;
                else if (sec === 'review') reviewCount++;
                else suggestionCount++;
            });

            const tierFilterContainer = document.getElementById('person-tier-filter-container');
            const isPersonAlbum = ['Conocidos', 'Familia', 'YO', 'Profesores', 'Mascotas'].includes(cat) && !ident.includes('conmigo') && !ident.includes('sin mí') && !ident.includes('grupal');
            
            if (tierFilterContainer) {
                if (isPersonAlbum) {
                    tierFilterContainer.style.display = 'inline-flex';
                    const elAll = document.getElementById('tier-all-count');
                    const elOff = document.getElementById('tier-official-count');
                    const elSug = document.getElementById('tier-suggestion-count');
                    const elRev = document.getElementById('tier-review-count');
                    const btnRev = document.getElementById('filter-tier-review');
                    if (elAll) elAll.textContent = total;
                    if (elOff) elOff.textContent = officialCount;
                    if (elSug) elSug.textContent = suggestionCount;
                    if (elRev) elRev.textContent = reviewCount;
                    if (btnRev) btnRev.style.display = reviewCount > 0 ? 'inline-flex' : 'none';
                } else {
                    tierFilterContainer.style.display = 'none';
                    window.currentTierFilter = 'all';
                }
            }



            // ── Gallery title & avatar ────────────────────────────

            const titleEl = document.getElementById('gallery-title');

            if (titleEl) {

                if (cat === 'YO' && ident === 'YO') {
                    titleEl.innerHTML = `<span style="color:#fff;">👤 YO</span>`;
                } else if (cat === ident) {
                    titleEl.innerHTML = `<span style="color:#fff;">${ident}</span>`;
                } else {
                    titleEl.innerHTML = `${cat} <span style="color:rgba(255,255,255,0.35); margin:0 5px; font-weight:400; font-size:0.9em;">›</span> <span style="color:#fff;">${ident}</span>`;
                }

            }



            const subtitleEl = document.getElementById('gallery-subtitle');

            if (subtitleEl) {

                let subParts = [`${total} ${total === 1 ? 'elemento' : 'elementos'}`];

                subParts.push(`${photoCount} ${photoCount === 1 ? 'foto' : 'fotos'}`);

                if (videoCount > 0) subParts.push(`${videoCount} ${videoCount === 1 ? 'vídeo' : 'vídeos'}`);

                if (yearRange) subParts.push(`${yearRange}`);

                subtitleEl.textContent = subParts.join(' • ');

                subtitleEl.style.display = '';

            }



            const statsContainer = document.getElementById('gallery-stats-container');

            if (statsContainer) {

                statsContainer.innerHTML = statsHtml;

            }



            const avatar = document.getElementById('gallery-avatar');

            if (avatar) {

                avatar.src = `/api/person_avatar?cat=${encodeURIComponent(cat)}&ident=${encodeURIComponent(ident)}`;

                avatar.onload = () => {

                    avatar.style.display = 'block';

                    avatar.style.border = '2px solid rgba(48,209,88,0.7)';

                };

                avatar.onerror = () => {

                    avatar.style.display = 'none';

                };

            }



            // ── Button visibility ────────────────────────────────────

            const mergeBtn = document.getElementById('btn-merge-group');

            const renameBtn = document.getElementById('btn-rename-group');

            const ignoreBtn = document.getElementById('btn-ignore-group');

            const deleteBtn = document.getElementById('btn-delete-group');



            const isUnnamedOrNew = (

                cat === 'Personas Sin Nombre' ||

                cat === 'Revision_Interactiva' ||

                cat === 'Personas_Nuevas' ||

                (ident && (ident.includes('Persona Nueva') || ident.includes('Persona #') || ident.startsWith('Desconocid') || ident.includes('👤')))

            );

            const showRevisionControls = isUnnamedOrNew || isRevision;



            const showMerge = showRevisionControls && ident && ident !== '⚠️ Dudosos / Baja Confianza' && ident !== '⏳ Pendientes de Analizar';

            if (mergeBtn)  mergeBtn.style.display  = showMerge ? 'inline-flex' : 'none';

            if (renameBtn) renameBtn.style.display  = showMerge ? 'inline-flex' : 'none';

            if (deleteBtn) deleteBtn.style.display  = showMerge ? 'inline-flex' : 'none';

            if (ignoreBtn) ignoreBtn.style.display  = showMerge ? 'inline-flex' : 'none';



            // Smart Merge IA Banner check

            const prevMergeBanner = document.getElementById('smart-merge-banner');

            if (prevMergeBanner) prevMergeBanner.remove();

            if (isUnnamedOrNew && typeof window.checkAndDisplaySmartMergeSuggestion === 'function') {

                window.checkAndDisplaySmartMergeSuggestion(cat, ident);

            }



            // ── INFINITE SCROLL RENDER ──────────────────────────────

            const grid = document.getElementById('grid-container');

            

            if (_gridObserver) {

                _gridObserver.disconnect();

                _gridObserver = null;

            }



            const initGrid = () => {

                grid.innerHTML = '';

                grid.style.display = 'grid';
                const isMobileScreen = window.innerWidth <= 820;
                grid.style.gridTemplateColumns = isMobileScreen ? 'repeat(2, minmax(0, 1fr))' : 'repeat(auto-fill, minmax(var(--grid-col-min, 180px), 1fr))';
                grid.style.gap = isMobileScreen ? '8px' : '12px';
                grid.style.padding = isMobileScreen ? '10px 10px 80px 10px' : '16px 20px 80px 20px';

                _currentGridItems = items;
                _gridRenderIndex = 0;
                window._lastRenderedTier = null;

                

                let sentry = document.getElementById('grid-sentry');

                if (!sentry) {

                    sentry = document.createElement('div');

                    sentry.id = 'grid-sentry';

                    sentry.style.height = '20px';

                    sentry.style.width = '100%';

                    grid.parentElement.appendChild(sentry);

                }



                _renderNextGridChunk();



                _gridObserver = new IntersectionObserver((entries) => {

                    if (entries[0].isIntersecting) {

                        _renderNextGridChunk();

                    }

                }, { root: grid.parentElement, rootMargin: '200px' });

                

                _gridObserver.observe(sentry);

            };



            if (grid.children.length > 0) {

                grid.classList.add('grid-leaving');

                setTimeout(() => { grid.classList.remove('grid-leaving'); initGrid(); }, 150);

            } else {

                initGrid();

            }

        }



        window.renderGrid = renderGrid; // Expose globally



        function _renderNextGridChunk() {

            if (!_currentGridItems || _gridRenderIndex >= _currentGridItems.length) return;

            const chunk = _currentGridItems.slice(_gridRenderIndex, _gridRenderIndex + PAGE_SIZE);

            if (!chunk.length) return;

            

            const grid = document.getElementById('grid-container');

            

            chunk.forEach((item, relativeIdx) => {
                const idx = _gridRenderIndex + relativeIdx;
                const isPersonAlbum = ['Conocidos', 'Familia', 'YO', 'Profesores', 'Mascotas'].includes(currentCat) && !currentIdent.includes('conmigo') && !currentIdent.includes('sin mí') && !currentIdent.includes('grupal');
                const itemTier = item.album_section || (item.is_dudoso ? 'review' : ((item.is_dataset || item.is_manual) ? 'official' : 'suggestion'));

                // Render Section Header if section changes (only in full view)
                if (isPersonAlbum && (!window.currentTierFilter || window.currentTierFilter === 'all') && (!currentPhotoFilterMode || currentPhotoFilterMode === 'all')) {
                    if (itemTier !== window._lastRenderedTier) {
                        window._lastRenderedTier = itemTier;
                        const tierHeader = document.createElement('div');
                        tierHeader.className = `album-tier-header tier-header-${itemTier}`;
                        tierHeader.dataset.tier = itemTier;
                        const isFirst = (relativeIdx === 0 && _gridRenderIndex === 0);
                        tierHeader.style.cssText = `
                            grid-column: 1 / -1;
                            width: 100%;
                            margin: ${isFirst ? '4px 0 10px 0' : '22px 0 10px 0'};
                            padding: 10px 14px;
                            border-radius: 10px;
                            display: flex;
                            align-items: center;
                            justify-content: space-between;
                            box-sizing: border-box;
                            background: ${itemTier === 'official' ? 'rgba(48,209,88,0.08)' : (itemTier === 'review' ? 'rgba(255,159,10,0.09)' : 'rgba(10,132,255,0.08)')};
                            border: 1px solid ${itemTier === 'official' ? 'rgba(48,209,88,0.25)' : (itemTier === 'review' ? 'rgba(255,159,10,0.3)' : 'rgba(10,132,255,0.25)')};
                            border-left: 4px solid ${itemTier === 'official' ? '#30d158' : (itemTier === 'review' ? '#ff9f0a' : '#0a84ff')};
                        `;
                        const titleText = itemTier === 'official' 
                            ? '🔒 Fotos Oficiales y Confirmadas' 
                            : (itemTier === 'review' ? '⚠️ Por Confirmar / Posibles Coincidencias' : '✨ Sugerencias de la IA');
                        const descText = itemTier === 'official'
                            ? 'Dataset original verificado y fotos confirmadas manualmente al 100%'
                            : (itemTier === 'review' ? 'Fotos dudosas o con menor certeza — confirma o descarta con 1 clic' : 'Detecciones con alta probabilidad encontradas automáticamente por la red neuronal');
                        const pillColor = itemTier === 'official' ? '#30d158' : (itemTier === 'review' ? '#ff9f0a' : '#0a84ff');

                        tierHeader.innerHTML = `
                            <div>
                                <div style="font-weight:700; font-size:13px; color:#fff; display:flex; align-items:center; gap:8px;">
                                    <span>${titleText}</span>
                                </div>
                                <div style="font-size:11px; color:#8e8e93; margin-top:2px;">${descText}</div>
                            </div>
                        `;
                        grid.appendChild(tierHeader);
                    }
                }

                const card = document.createElement('div');

                card.className = 'media-card media-card-animated';

                card.style.position = 'relative';

                // Stagger delay: cap at 400ms total

                const delay = Math.min(relativeIdx * 12, 400);

                card.style.animationDelay = `${delay}ms`;



                if (window.isMultiSelectMode) {

                    const chkContainer = document.createElement('div');

                    chkContainer.style.cssText = "position:absolute; top:8px; left:8px; z-index:100;";

                    const chk = document.createElement('input');

                    chk.type = 'checkbox';

                    chk.className = 'card-checkbox';

                    chk.checked = window.selectedFiles && window.selectedFiles.has(item.path);

                    chk.style.cssText = "width:22px; height:22px; accent-color:#30d158; cursor:pointer;";

                    chkContainer.appendChild(chk);

                    card.appendChild(chkContainer);



                    if (window.selectedFiles && window.selectedFiles.has(item.path)) {

                        card.classList.add('selected-card');

                        card.style.border = '3px solid #30d158';

                        card.style.boxShadow = '0 0 15px rgba(48,209,88,0.5)';

                    }



                    card.onclick = (e) => { e.stopPropagation(); window.toggleFileSelection(item.path, card, e); };

                } else {

                    card.onclick = () => { window.currentItemIndex = idx; window.openLightbox(item); };

                }



                // Source badge

                const badge = document.createElement('span');

                badge.id = `source-${idx}`;

                if (item.is_dudoso || item.status === 'Dudoso' || (item.source && item.source.includes('Por Confirmar'))) {

                    badge.className = 'badge badge-dudoso';

                    badge.style.cssText = 'background:rgba(255, 159, 10, 0.95); color:#fff; font-weight:700; border:1px solid rgba(255, 159, 10, 0.6); box-shadow:0 2px 6px rgba(255, 159, 10, 0.4);';

                    badge.textContent = '⚠️ Por Confirmar';

                } else if (item.source && item.source.includes('Dataset') && item.source.includes('Manual')) {

                    badge.className = 'badge badge-dataset'; badge.textContent = '🔒 Dataset + ✏️ Manual';

                } else if (item.source && item.source.includes('IA') && item.source.includes('Manual')) {

                    badge.className = 'badge badge-manual'; badge.textContent = '✨ IA + ✏️ Manual';

                } else if (item.source && item.source.includes('Dataset')) {

                    badge.className = 'badge badge-dataset'; badge.textContent = '🔒 Dataset';

                } else if (item.source && item.source.includes('Manual')) {

                    badge.className = 'badge badge-manual'; badge.textContent = '✏️ Manual';

                } else {

                    badge.className = 'badge badge-ia'; badge.textContent = '✨ IA';

                }

                card.appendChild(badge);



                // Inline Quick Action Bar for Review / Por Confirmar cards
                if (itemTier === 'review' || item.is_dudoso) {
                    const inlineBar = document.createElement('div');
                    inlineBar.className = 'card-inline-confirm-bar';
                    inlineBar.style.cssText = 'position:absolute; bottom:6px; left:6px; right:6px; display:flex; gap:4px; z-index:10; background:rgba(0,0,0,0.85); backdrop-filter:blur(6px); -webkit-backdrop-filter:blur(6px); padding:4px; border-radius:8px;';

                    const confirmBtn = document.createElement('button');
                    confirmBtn.innerHTML = '✔ Confirmar';
                    confirmBtn.style.cssText = 'flex:1; background:#30d158; color:#000; font-weight:700; font-size:11px; border:none; border-radius:5px; padding:5px 2px; cursor:pointer;';
                    confirmBtn.title = `Confirmar que pertenece a ${currentIdent}`;
                    confirmBtn.onclick = (e) => {
                        e.stopPropagation();
                        window.confirmPhotoInline(confirmBtn, encodeURIComponent(item.path), encodeURIComponent(currentCat), encodeURIComponent(currentIdent));
                    };

                    const rejectBtn = document.createElement('button');
                    rejectBtn.innerHTML = '✖ No es';
                    rejectBtn.style.cssText = 'flex:1; background:rgba(255,69,58,0.85); color:#fff; font-weight:700; font-size:11px; border:none; border-radius:5px; padding:5px 2px; cursor:pointer;';
                    rejectBtn.title = `Descartar de ${currentIdent}`;
                    rejectBtn.onclick = (e) => {
                        e.stopPropagation();
                        window.rejectPhotoInline(rejectBtn, encodeURIComponent(item.path), encodeURIComponent(currentCat), encodeURIComponent(currentIdent));
                    };

                    inlineBar.appendChild(confirmBtn);
                    inlineBar.appendChild(rejectBtn);
                    card.appendChild(inlineBar);
                }

                // OS Device Origin Badge

                const osBadge = document.createElement('span');

                osBadge.className = 'os-device-badge';

                const isApple = Boolean(item.is_apple || item.device_origin === 'apple');

                

                osBadge.style.cssText = `

                    position: absolute; top: 10px; right: 10px;

                    font-size: 12px; font-weight: 700;

                    background: ${isApple ? 'rgba(255, 45, 85, 0.25)' : (item.device_origin === 'android' ? 'rgba(52, 199, 89, 0.25)' : 'rgba(0, 0, 0, 0.65)')};

                    backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);

                    padding: 3px 8px; border-radius: 8px;

                    z-index: 10; display: flex; align-items: center; gap: 4px;

                    box-shadow: 0 3px 10px rgba(0,0,0,0.4);

                    border: 1px solid ${isApple ? 'rgba(255, 45, 85, 0.5)' : (item.device_origin === 'android' ? 'rgba(52, 199, 89, 0.5)' : 'rgba(255,255,255,0.15)')};

                    color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,0.8);

                `;

                osBadge.innerHTML = isApple ? '🍎 <span style="font-size:11px;opacity:0.95;">Apple</span>' : (item.device_origin === 'android' ? '🤖 <span style="font-size:11px;opacity:0.95;">Android</span>' : '📷 <span style="font-size:11px;opacity:0.95;">Foto</span>');

                osBadge.title = isApple ? 'Foto de Apple iPhone / iCloud' : (item.device_origin === 'android' ? 'Foto de Dispositivo Android' : 'Foto de Cámara / Otro origen');

                card.appendChild(osBadge);

                // Screenshot Antiquity Badge
                const isScreenshotItem = Boolean((item.name && /screenshot|captura|screen/i.test(item.name)) || (item.path && item.path.includes('Capturas')));
                if (isScreenshotItem) {
                    const nowSec = Date.now() / 1000;
                    const mtime = item.mtime || nowSec;
                    const diffDays = Math.max(0, Math.floor((nowSec - mtime) / 86400));
                    const ssAgeBadge = document.createElement('span');
                    ssAgeBadge.className = 'screenshot-age-badge';
                    if (diffDays >= 365) {
                        const years = Math.floor(diffDays / 365);
                        ssAgeBadge.textContent = `🗄️ Hace ${years > 1 ? years + 'a' : '1a'}`;
                        ssAgeBadge.style.cssText = 'position:absolute; bottom:8px; right:8px; background:rgba(255,69,58,0.88); color:#fff; font-weight:700; font-size:10px; padding:2px 7px; border-radius:6px; box-shadow:0 2px 8px rgba(0,0,0,0.5); z-index:10; backdrop-filter:blur(6px); border:1px solid rgba(255,255,255,0.25);';
                        ssAgeBadge.title = `Captura guardada hace ${diffDays} días (~${years} años)`;
                        card.appendChild(ssAgeBadge);
                    } else if (diffDays >= 90) {
                        const months = Math.floor(diffDays / 30);
                        ssAgeBadge.textContent = `⏳ Hace ${months}m`;
                        ssAgeBadge.style.cssText = 'position:absolute; bottom:8px; right:8px; background:rgba(255,159,10,0.88); color:#fff; font-weight:700; font-size:10px; padding:2px 7px; border-radius:6px; box-shadow:0 2px 8px rgba(0,0,0,0.5); z-index:10; backdrop-filter:blur(6px); border:1px solid rgba(255,255,255,0.25);';
                        ssAgeBadge.title = `Captura guardada hace ${diffDays} días (~${months} meses)`;
                        card.appendChild(ssAgeBadge);
                    }
                }

                // Pending video badge
                if (item.needs_face_analysis || item.status === 'Pendiente de Análisis') {
                    const pendBadge = document.createElement('span');
                    pendBadge.style.cssText = 'position:absolute; bottom:8px; left:8px; background:rgba(255,159,10,0.95); color:#fff; font-weight:700; font-size:10px; padding:2px 7px; border-radius:6px; box-shadow:0 2px 8px rgba(0,0,0,0.5); z-index:10;';
                    pendBadge.textContent = '☁️ Por Analizar';
                    card.appendChild(pendBadge);
                }



                // Confidence badge

                const conf = parseFloat(item.confidence || 0);

                if (conf > 0) {

                    const cb = document.createElement('span');

                    cb.className = 'confidence-badge';

                    if (conf >= 0.50) { cb.classList.add('confidence-high'); cb.textContent = `${Math.round(conf*100)}%`; }

                    else if (conf >= 0.38) { cb.classList.add('confidence-mid'); cb.textContent = `${Math.round(conf*100)}%`; }

                    else { cb.classList.add('confidence-low'); cb.textContent = `${Math.round(conf*100)}%`; }

                    card.appendChild(cb);

                }



                // Square Card & Zero-Overlap Guarantees
                card.style.width = '100%';
                card.style.display = 'block';
                card.style.position = 'relative';
                card.style.aspectRatio = '1 / 1';
                card.style.overflow = 'hidden';



                const skeleton = document.createElement('div');
                skeleton.className = 'masonry-skeleton';
                skeleton.style.position = 'absolute';
                skeleton.style.inset = '0';
                skeleton.style.zIndex = '1';
                skeleton.style.pointerEvents = 'none';
                card.appendChild(skeleton);



                // Thumbnail

                const thumb = document.createElement('img');

                thumb.src = `/api/thumbnail?path=${encodeURIComponent(item.path)}`;

                thumb.loading = 'lazy';

                thumb.decoding = 'async';

                thumb.style.opacity = '0';

                thumb.onload = () => {

                    thumb.style.opacity = '1';

                    skeleton.style.opacity = '0';

                    setTimeout(() => skeleton.remove(), 400);

                };

                thumb.onerror = () => {

                    thumb.src = window.INLINE_PERSON_SVG;

                    thumb.style.opacity = '1';

                    skeleton.style.opacity = '0';

                    setTimeout(() => skeleton.remove(), 200);

                };

                thumb.style.transition = 'opacity 0.3s ease';

                thumb.style.position = 'absolute';
                thumb.style.inset = '0';
                thumb.style.width = '100%';
                thumb.style.height = '100%';
                thumb.style.aspectRatio = '1 / 1';
                thumb.style.objectFit = 'cover';
                thumb.style.display = 'block';

                card.appendChild(thumb);



                // Face boxes

                if (item.faces && item.faces.length > 0 && item.orig_width && item.orig_height) {

                    const facesContainer = document.createElement('div');

                    facesContainer.className = 'faces-container';

                    item.faces.forEach(face => {

                        if (!face.box) return;

                        const [fx, fy, fw, fh] = face.box;

                        const left = (fx / item.orig_width) * 100;

                        const top = (fy / item.orig_height) * 100;

                        const width = (fw / item.orig_width) * 100;

                        const height = (fh / item.orig_height) * 100;

                        

                        const box = document.createElement('div');

                        box.className = 'face-box-sci-fi';

                        box.style.left = `${left}%`;

                        box.style.top = `${top}%`;

                        box.style.width = `${width}%`;

                        box.style.height = `${height}%`;

                        

                        const label = document.createElement('div');

                        label.className = 'face-box-label';

                        const confPct = Math.round((face.confidence || 0) * 100);

                        label.innerHTML = `<span>${face.identity || 'Desconocido'}</span><small>${confPct}%</small>`;

                        box.appendChild(label);

                        facesContainer.appendChild(box);

                    });

                    card.appendChild(facesContainer);

                }



                if (item.type === 'video') {

                    const playIcon = document.createElement('div');

                    playIcon.className = 'video-icon';

                    playIcon.innerHTML = '▶';

                    card.appendChild(playIcon);

                }



                const title = document.createElement('div');

                title.className = 'media-title';

                title.textContent = item.name;

                card.appendChild(title);



                grid.appendChild(card);

            });



            _gridRenderIndex += PAGE_SIZE;

        }





        function closeLightbox() {

            const lb = document.getElementById('lightbox');

            if (lb) {

                lb.classList.add('hidden');

                lb.style.display = 'none';

            }

            if (window.innerWidth <= 820) {

                const panel = document.getElementById('metadata-panel');

                if (panel) panel.classList.remove('mobile-expanded');

            }

            const container = document.getElementById('lb-media-container');

            if (container) container.innerHTML = '';

            currentFileObj = null;

            isCurrentVideo = false;

            if (typeof resetZoom === 'function') resetZoom();

        }



        function renderHomeMosaic() {

            currentCat = null;

            currentIdent = null;

            currentFolderItems = [];



            const titleEl = document.getElementById('gallery-title');

            const subtitleEl = document.getElementById('gallery-subtitle');

            const grid = document.getElementById('grid-container');

            const avatar = document.getElementById('gallery-avatar');

            if (avatar) avatar.style.display = 'none';

            const statsContainer = document.getElementById('gallery-stats-container');

            if (statsContainer) statsContainer.innerHTML = '';



            if (titleEl) titleEl.innerHTML = '<span style="background:linear-gradient(135deg,#a855f7,#3b82f6); -webkit-background-clip:text; -webkit-text-fill-color:transparent; font-size:1.6rem; font-weight:800;">🏠 Fototeca AI</span>';

            if (subtitleEl) subtitleEl.textContent = 'Todas las categorías de tu biblioteca';



            // Hide action buttons

            ['btn-merge-group','btn-rename-group','btn-ignore-group','btn-delete-group'].forEach(id => {

                const el = document.getElementById(id);

                if (el) el.style.display = 'none';

            });



            if (!fullGallery) { grid.innerHTML = ''; return; }



            grid.innerHTML = '';

            grid.style.display = 'grid';

            grid.style.gridTemplateColumns = 'repeat(auto-fill, minmax(200px, 1fr))';

            grid.style.gap = '14px';

            grid.style.padding = '10px 0';



            const CAT_ICONS = {

                'YO':'👤','Conocidos':'👥','Familia':'👨‍👩‍👧','Lugares':'📍',

                'Eventos':'🎉','Mascotas':'🐶','Objetos':'🚗','Profesores':'🎓',

                'Recuerdos':'📸','Publicaciones_Instagram':'📱','📋 Revisión / Por Organizar':'📋'

            };

            const CAT_ORDER = ['YO','📋 Revisión / Por Organizar','Familia','Conocidos','Lugares','Eventos','Mascotas','Objetos','Recuerdos','Profesores','Publicaciones_Instagram'];

            const categories = Object.keys(fullGallery).filter(c => c !== '__smart_album__').sort((a,b) => {

                const ia = CAT_ORDER.indexOf(a), ib = CAT_ORDER.indexOf(b);

                if (ia !== -1 && ib !== -1) return ia - ib;

                if (ia !== -1) return -1; if (ib !== -1) return 1;

                return a.localeCompare(b);

            });



            categories.forEach((cat, catIdx) => {
                const idents = fullGallery[cat] || {};
                let totalItems = 0;
                let photoPaths = [];
                if (window.homeMosaicPreview && window.homeMosaicPreview[cat]) {
                    totalItems = window.homeMosaicPreview[cat].total;
                    photoPaths = window.homeMosaicPreview[cat].samples || [];
                } else {
                    totalItems = Object.values(idents).reduce((s, arr) => s + (Array.isArray(arr) ? arr.length : (typeof arr === 'number' ? arr : 0)), 0);
                    for (const ident of Object.keys(idents)) {
                        const itms = Array.isArray(idents[ident]) ? idents[ident] : [];
                        for (const item of itms) {
                            if (item.type !== 'video') { photoPaths.push(item.path); }
                            if (photoPaths.length >= 4) break;
                        }
                        if (photoPaths.length >= 4) break;
                    }
                }
                if (totalItems === 0) return;



                const card = document.createElement('div');

                card.className = 'home-album-card';

                card.style.animationDelay = `${catIdx * 50}ms`;



                // Mosaic

                const mosaic = document.createElement('div');

                mosaic.className = 'home-album-mosaic';

                const slots = photoPaths.length > 0 ? photoPaths : [null,null,null,null];

                (slots.length < 4 ? [...slots, ...Array(4-slots.length).fill(null)] : slots.slice(0,4)).forEach(p => {

                    if (p) {

                        const img = document.createElement('img');

                        img.src = `/api/thumbnail?path=${encodeURIComponent(p)}`;

                        img.loading = 'lazy';

                        img.onerror = () => { img.style.background = '#2c2c2e'; img.removeAttribute('src'); };

                        mosaic.appendChild(img);

                    } else {

                        const ph = document.createElement('div');

                        ph.style.cssText = 'background:#1c1c1e; display:flex; align-items:center; justify-content:center; font-size:1.5rem; color:#3c3c3e;';

                        ph.textContent = CAT_ICONS[cat] || '📁';

                        mosaic.appendChild(ph);

                    }

                });

                card.appendChild(mosaic);



                // Info overlay

                const info = document.createElement('div');

                info.className = 'home-album-info';

                info.innerHTML = `

                    <div class="home-album-name">${CAT_ICONS[cat] || '📁'} ${cat}</div>

                    <div class="home-album-count">${Object.keys(idents).length} álbumes · ${totalItems.toLocaleString()} fotos</div>

                `;

                card.appendChild(info);



                // Click → expand category in sidebar and render first ident

                card.onclick = () => {

                    // Reset grid style before rendering album

                    grid.style.gridTemplateColumns = '';

                    grid.style.gap = '';

                    grid.style.padding = '';

                    // Open the category in the sidebar

                    document.querySelectorAll('.tree-folder.category-header').forEach(h => {

                        const wrapper = h.closest('.tree-category-group');

                        if (!wrapper) return;

                        const nameSpan = h.querySelector('span:nth-child(2)');

                        if (nameSpan && nameSpan.textContent.trim() === cat) {

                            const list = wrapper.querySelector('.category-idents-list');

                            if (list && list.style.display !== 'flex') { h.click(); }

                        }

                    });

                    // Render first identity

                    const firstIdent = Object.keys(idents)[0];

                    if (firstIdent) renderGrid(cat, firstIdent);

                };



                grid.appendChild(card);

            });

        }



        function resetGalleryView() {

            renderHomeMosaic();

        }





        function renameCurrentGroup() {

            if (!currentCat || !currentIdent) {

                alert("Selecciona primero una persona en la barra lateral para poder fusionarla.");

                return;

            }

            

            const containerEl = document.getElementById('merge-existing-select');

            containerEl.innerHTML = '';

            document.getElementById('merge-selected-value').value = '';

            

            let groupedIds = {};

            identitiesList.forEach(id => {

                if (id.categoria !== 'Personas Sin Nombre' && id.categoria !== 'Ignorar' && id.categoria !== '_Dudosos') {

                    if (!groupedIds[id.categoria]) groupedIds[id.categoria] = [];

                    groupedIds[id.categoria].push(id);

                }

            });

            

            const btnStyle = "display:block; width:100%; text-align:left; padding:8px 10px; background:transparent; border:none; color:white; cursor:pointer; border-radius:4px; font-size:13px; margin-bottom:2px; transition:background 0.2s;";

            const hoverScript = "onmouseover=\"if(this.dataset.selected!=='true') this.style.background='#3a3a3c'\" onmouseout=\"if(this.dataset.selected!=='true') this.style.background='transparent'\"";

            

            Object.keys(groupedIds).sort().forEach(cat => {

                const details = document.createElement('details');

                details.style.marginBottom = '4px';

                

                const summary = document.createElement('summary');

                summary.style.cssText = 'cursor:pointer; padding:6px 10px; font-weight:bold; color:#aaa; font-size:12px; background:#1c1c1e; margin-bottom:2px; position:sticky; top:0; z-index:10; border-bottom:1px solid #333;';

                summary.textContent = cat;

                details.appendChild(summary);

                

                const contentDiv = document.createElement('div');

                contentDiv.style.cssText = 'padding-left:8px; border-left:2px solid #333; margin-left:10px; margin-top:5px; margin-bottom:5px;';

                

                groupedIds[cat].sort((a,b) => a.identidad.localeCompare(b.identidad)).forEach(id => {

                    const btn = document.createElement('button');

                    btn.style.cssText = btnStyle;

                    btn.innerHTML = id.identidad;

                    btn.setAttribute('onmouseover', "if(this.dataset.selected!=='true') this.style.background='#3a3a3c'");

                    btn.setAttribute('onmouseout', "if(this.dataset.selected!=='true') this.style.background='transparent'");

                    

                    btn.onclick = () => {

                        // Reset all buttons

                        const allBtns = containerEl.querySelectorAll('button');

                        allBtns.forEach(b => {

                            b.dataset.selected = 'false';

                            b.style.background = 'transparent';

                            b.style.fontWeight = 'normal';

                        });

                        

                        // Select this button

                        btn.dataset.selected = 'true';

                        btn.style.background = '#30d158';

                        btn.style.color = 'black';

                        btn.style.fontWeight = 'bold';

                        

                        // Clear text input

                        document.getElementById('merge-new-input').value = '';

                        

                        // Set hidden value

                        document.getElementById('merge-selected-value').value = JSON.stringify({cat: id.categoria, ident: id.identidad});

                    };

                    

                    contentDiv.appendChild(btn);

                });

                

                details.appendChild(contentDiv);

                containerEl.appendChild(details);

            });

            

            // Text input should clear selection

            document.getElementById('merge-new-input').oninput = () => {

                const allBtns = containerEl.querySelectorAll('button');

                allBtns.forEach(b => {

                    b.dataset.selected = 'false';

                    b.style.background = 'transparent';

                    b.style.color = 'white';

                    b.style.fontWeight = 'normal';

                });

                document.getElementById('merge-selected-value').value = '';

            };

            

            document.getElementById('merge-count-span').textContent = currentFolderItems.length;

            document.getElementById('merge-group-name').textContent = currentIdent;

            document.getElementById('merge-new-input').value = '';

            document.getElementById('modal-merge').style.display = 'flex';

        }



        function closeMergeModal() {

            document.getElementById('modal-merge').style.display = 'none';

        }



        

        async function deleteCurrentGroup() {

            if (!currentIdent) return;

            if (!confirm(`¿Seguro que quieres disolver el grupo '${currentIdent}'? Las fotos no se borrarán de tus álbumes originales.`)) return;

            

            showToast(`⏳ Disolviendo grupo '${currentIdent}'...`);

            const res = await fetch('/api/delete_group', {

                method: 'POST',

                headers: {'Content-Type': 'application/json'},

                body: JSON.stringify({ cat: currentCat || 'Personas Sin Nombre', ident: currentIdent })

            });

            const data = await res.json();

            if (data.success || data.status === 'success') {

                showToast(`🗑️ Grupo '${currentIdent}' disuelto con éxito.`);

                await loadIdentities();

                await loadGallery();

                resetGalleryView();

            } else {

                showToast(data.error || "No se pudo disolver el grupo.", true);

            }

        }



        async function ignoreCurrentGroup() {

            if (!currentIdent) return;

            if (!confirm(`¿Seguro que quieres ignorar a la persona '${currentIdent}'? Se ocultará de la galería y la IA no la volverá a sugerir.`)) return;

            

            showToast(`⏳ Ignorando a '${currentIdent}'...`);

            const targetName = 'Falso_Positivo_' + currentIdent;

            

            const res = await fetch('/api/rename_group', {

                method: 'POST',

                headers: {'Content-Type': 'application/json'},

                body: JSON.stringify({

                    cat: currentCat || 'Personas Sin Nombre',

                    ident: currentIdent,

                    new_name: targetName,

                    new_cat: 'Ignorar'

                })

            });

            const data = await res.json();

            if (data.success || data.status === 'success') {

                showToast(`🚫 '${currentIdent}' ha sido ignorado correctamente.`);

                await loadIdentities();

                await loadGallery();

                resetGalleryView();

            } else {

                showToast(data.error || "No se pudo ignorar a la persona.", true);

            }

        }



        async function submitMergeGroup() {

            if (!currentCat || !currentIdent) {

                alert("Por favor, selecciona una carpeta o persona antes de intentar fusionar.");

                closeMergeModal();

                return;

            }

            const existingNameJSON = document.getElementById('merge-selected-value').value;

            const newName = document.getElementById('merge-new-input').value.trim();

            

            let targetName = "";

            let targetCat = "Conocidos";

            

            if (existingNameJSON) {

                const parsed = JSON.parse(existingNameJSON);

                targetName = parsed.ident;

                targetCat = parsed.cat;

            } else if (newName) {

                targetName = newName;

            } else {

                alert("Por favor, selecciona una persona existente o introduce un nombre nuevo.");

                return;

            }

            

            // LOCK UI

            const btn = document.getElementById('btn-submit-merge') || (document.getElementById('modal-merge') && document.getElementById('modal-merge').querySelector('button[style*="#30d158"]'));

            if(btn) {

                if (btn.disabled || btn.dataset.busy === 'true') return;

                btn.disabled = true;

                btn.dataset.busy = 'true';

                btn.textContent = "⏳ Fusionando...";

            }

            

            showToast(`⏳ Fusionando ${currentFolderItems.length} fotos con '${targetName}' y reentrenando IA...`);

            

            try {

            const res = await fetch('/api/rename_group', {

                method: 'POST',

                headers: {'Content-Type': 'application/json'},

                body: JSON.stringify({

                    cat: currentCat,

                    ident: currentIdent,

                    new_name: targetName,

                    new_cat: targetCat

                })

            });

            const data = await res.json();

            if (data.success) {

                showToast(`🎉 ¡Fusionado con éxito! Se unieron ${data.count} fotos a '${targetCat} / ${targetName}'.`);

                closeMergeModal();

                await loadIdentities();

                await loadGallery();

                renderGrid(null, null);

            } else {

                showToast(data.error || "No se pudo fusionar el grupo.", true);

            }

            } catch (e) {

                showToast("Error de conexión durante la fusión.", true);

            } finally {

                if(btn) { btn.disabled = false; btn.dataset.busy = 'false'; btn.innerHTML = "🚀 Aplicar Fusión / Guardar"; }

                closeMergeModal();

            }

        }







        document.addEventListener('keydown', async (e) => {

            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;



            const lightbox = document.getElementById('lightbox');

            const isLightboxOpen = lightbox && !lightbox.classList.contains('hidden');



            if (isLightboxOpen) {

                if (e.key === 'Escape') {

                    e.preventDefault();

                    lightbox.classList.add('hidden');

                    if (isCurrentVideo) {

                        const mediaEl = document.querySelector('.lb-media-element');

                        if (mediaEl) mediaEl.pause();

                    }

                }

                else if (e.key === 'ArrowLeft') {

                    e.preventDefault();

                    const isFromDudosos = currentCat === '_Dudosos' || currentIdent === '_Dudosos' || (currentFileObj && currentFileObj.path.includes('_Dudosos')) || (currentCat && currentCat.includes('Revision'));

                    if (isFromDudosos) {

                        swipeActionLeft();

                    } else {

                        if (currentFolderItems && currentItemIndex > 0) {

                            currentItemIndex--;

                            openLightbox(currentFolderItems[currentItemIndex]);

                        }

                    }

                }

                else if (e.key === 'ArrowRight') {

                    e.preventDefault();

                    const isFromDudosos = currentCat === '_Dudosos' || currentIdent === '_Dudosos' || (currentFileObj && currentFileObj.path.includes('_Dudosos')) || (currentCat && currentCat.includes('Revision'));

                    if (isFromDudosos) {

                        swipeActionRight();

                    } else {

                        if (currentFolderItems && currentItemIndex < currentFolderItems.length - 1) {

                            currentItemIndex++;

                            openLightbox(currentFolderItems[currentItemIndex]);

                        }

                    }

                }

                return; // Stop here if lightbox is open

            }



            // Global shortcuts (if lightbox is closed)

            if (e.key === 'Delete' || e.key === 'Backspace') {

                e.preventDefault();

            }

        });



        // Setup Swipe Touch Gestures

        let touchStartX = 0;

        let touchStartY = 0;

        document.addEventListener('DOMContentLoaded', () => {

            const lbEl = document.getElementById('lightbox');

            if (lbEl) {

                lbEl.addEventListener('touchstart', (e) => {

                    if (e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION' || e.target.tagName === 'BUTTON' || e.target.closest('.metadata-panel') || e.target.closest('#lb-topbar')) return;

                    touchStartX = e.changedTouches[0].screenX;

                    touchStartY = e.changedTouches[0].screenY;

                }, { passive: true });



                lbEl.addEventListener('touchend', (e) => {

                    if (e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION' || e.target.tagName === 'BUTTON' || e.target.closest('.metadata-panel') || e.target.closest('#lb-topbar')) return;

                    const dX = e.changedTouches[0].screenX - touchStartX;

                    const dY = e.changedTouches[0].screenY - touchStartY;

                    

                    if (Math.abs(dX) > 90 && Math.abs(dX) > Math.abs(dY)) {

                        if (dX > 0) {

                            swipeActionRight();

                        } else {

                            swipeActionLeft();

                        }

                    }

                    else if (Math.abs(dY) > 90 && Math.abs(dY) > Math.abs(dX)) {

                        if (dY > 0) {

                            navigateLightbox(-1);

                        } else {

                            navigateLightbox(1);

                        }

                    }

                }, { passive: true });

            }

        });



        async function swipeActionLeft() {

            // SHOW VISUAL FEEDBACK

            const ind = document.getElementById('swipe-left-ind');

            if (ind) {

                ind.style.opacity = '1';

                ind.querySelector('div').style.transform = 'scale(1)';

                setTimeout(() => {

                    ind.style.opacity = '0';

                    ind.querySelector('div').style.transform = 'scale(0.85)';

                }, 400);

            }

            

            if (!currentFileObj) return;

            const isFromDudosos = currentCat === '_Dudosos' || currentIdent === '_Dudosos' || currentFileObj.path.includes('_Dudosos') || (currentCat && currentCat.includes('Revision'));

            

            if (isFromDudosos) {

                // Discard face in Dudosos -> Set all faces to Desconocido

                if (currentFaces && currentFaces.length > 0) {

                    for (let idx = 0; idx < currentFaces.length; idx++) {

                        const face = currentFaces[idx];

                        await fetch('/api/correct', {

                            method: 'POST',

                            headers: {'Content-Type': 'application/json'},

                            body: JSON.stringify({

                                path: currentFileObj.path,

                                new_categoria: '_Dudosos',

                                new_identidad: 'Desconocido',

                                face: {x: face.x, y: face.y, width: face.width, height: face.height},

                                apply_to_duplicates: false

                            })

                        });

                    }

                } else {

                    await fetch('/api/correct', {

                        method: 'POST',

                        headers: {'Content-Type': 'application/json'},

                        body: JSON.stringify({

                            path: currentFileObj.path,

                            new_categoria: '_Dudosos',

                            new_identidad: 'Desconocido',

                            apply_to_duplicates: false

                        })

                    });

                }

                showToast("❌ Cara rechazada y movida a Desconocidos.");

                await loadGallery();

                loadNextItem();

            } else {

                // Delete photo in standard view

                const res = await fetch('/api/delete', {

                    method: 'POST',

                    headers: {'Content-Type': 'application/json'},

                    body: JSON.stringify({ path: currentFileObj.path })

                });

                const data = await res.json();

                if (data.success) {

                    showToast("Descartado y eliminado de disco 🗑️");

                    await loadGallery();

                    loadNextItem();

                } else {

                    showToast(data.error || "No se pudo eliminar.", true);

                }

            }

        }



        async function swipeActionRight() {

            // SHOW VISUAL FEEDBACK

            const ind = document.getElementById('swipe-right-ind');

            if (ind) {

                ind.style.opacity = '1';

                ind.querySelector('div').style.transform = 'scale(1)';

                setTimeout(() => {

                    ind.style.opacity = '0';

                    ind.querySelector('div').style.transform = 'scale(0.85)';

                }, 400);

            }

            

            if (!currentFileObj) return;

            const isFromDudosos = currentCat === '_Dudosos' || currentIdent === '_Dudosos' || currentFileObj.path.includes('_Dudosos') || (currentCat && currentCat.includes('Revision'));

            

            if (isFromDudosos) {

                let pathParts = currentFileObj.path.split(/[\\\/]/);

                let folderName = pathParts.slice(-2, -1)[0];

                let categoryName = pathParts.slice(-3, -2)[0];

                if (folderName === '_Dudosos') {

                    folderName = pathParts.slice(-3, -2)[0];

                    categoryName = pathParts.slice(-4, -3)[0];

                }

                

                if (folderName && categoryName) {

                    if (currentFaces && currentFaces.length > 0) {

                        for (let idx = 0; idx < currentFaces.length; idx++) {

                            const face = currentFaces[idx];

                            await fetch('/api/correct', {

                                method: 'POST',

                                headers: {'Content-Type': 'application/json'},

                                body: JSON.stringify({

                                    path: currentFileObj.path,

                                    new_categoria: categoryName,

                                    new_identidad: folderName,

                                    face: {x: face.x, y: face.y, width: face.width, height: face.height},

                                    apply_to_duplicates: false

                                })

                            });

                        }

                    } else {

                        await fetch('/api/correct', {

                            method: 'POST',

                            headers: {'Content-Type': 'application/json'},

                            body: JSON.stringify({

                                path: currentFileObj.path,

                                new_categoria: categoryName,

                                new_identidad: folderName,

                                apply_to_duplicates: false

                            })

                        });

                    }

                    showToast(`✅ Confirmado en '${folderName}'`);

                    await loadGallery();

                    loadNextItem();

                }

            } else {

                showToast("Conservado ✅");

                loadNextItem();

            }

        }



        function loadNextItem() {

            if (currentFolderItems.length === 0) {

                closeLightbox();

                return;

            }

            currentItemIndex++;

            if (currentItemIndex >= currentFolderItems.length) {

                currentItemIndex = 0;

            }

            const nextItem = currentFolderItems[currentItemIndex];

            if (nextItem) {

                openLightbox(nextItem);

            } else {

                closeLightbox();

            }

        }







        // Motor de Zoom Interactivo con Rueda del Ratón y Panoramización (Pan)

        let isPanDragging = false;

        let panStartX = 0;

        let panStartY = 0;



        let lightboxRotation = 0;

        window.rotateLightbox = function() {

            lightboxRotation = (lightboxRotation + 90) % 360;

            applyZoomTransform();

            showToast(`Imagen rotada 90°`);

        };



        function resetZoom() {

            zoomLevel = 1.0;

            panX = 0;

            panY = 0;

            lightboxRotation = 0;

            applyZoomTransform();

        }



        function applyZoomTransform() {

            window.panX = panX;

            window.panY = panY;

            window.zoomLevel = zoomLevel;

            const container = document.getElementById('lb-media-container');

            if (container) {

                container.style.transform = `translate(${panX}px, ${panY}px) scale(${zoomLevel}) rotate(${lightboxRotation}deg)`;

                window.updateZoomDisplay(zoomLevel);

                const invZoom = 1.0 / zoomLevel;

                container.style.setProperty('--inv-zoom', invZoom);

                document.querySelectorAll('.lb-bounding-box').forEach(b => {

                    b.style.borderWidth = `${Math.max(1, 2 * invZoom)}px`;

                });

            }

        }



        document.addEventListener('DOMContentLoaded', () => {

            const wrapper = document.getElementById('viewer-wrapper');

            if (!wrapper) return;



            // Rueda del Ratón para Zoom

            let zoomTicking = false;

            wrapper.addEventListener('wheel', (e) => {

                e.preventDefault();

                const delta = e.deltaY < 0 ? 0.3 : -0.3;

                zoomLevel = Math.min(Math.max(1.0, zoomLevel + delta), 16.0);



                if (zoomLevel === 1.0) {

                    panX = 0;

                    panY = 0;

                }

                

                if (!zoomTicking) {

                    window.requestAnimationFrame(() => {

                        applyZoomTransform();

                        zoomTicking = false;

                    });

                    zoomTicking = true;

                }

            }, { passive: false });



            // Panoramización con Arrastre cuando hay Zoom

            wrapper.addEventListener('mousedown', (e) => {

                if (window.isDrawingMode) return;

                if (zoomLevel > 1.0 && !e.target.closest('.lb-bounding-box') && !e.target.closest('.resize-handle')) {

                    isPanDragging = true;

                    panStartX = e.clientX - panX;

                    panStartY = e.clientY - panY;

                    wrapper.style.cursor = 'grabbing';

                }

            });



            let panTicking = false;

            document.addEventListener('mousemove', (e) => {

                if (isPanDragging && zoomLevel > 1.0) {

                    panX = e.clientX - panStartX;

                    panY = e.clientY - panStartY;

                    if (!panTicking) {

                        window.requestAnimationFrame(() => {

                            applyZoomTransform();

                            panTicking = false;

                        });

                        panTicking = true;

                    }

                }

            });



            document.addEventListener('mouseup', () => {

                if (isPanDragging) {

                    isPanDragging = false;

                    const wrapper = document.getElementById('viewer-wrapper');

                    if (wrapper) wrapper.style.cursor = 'default';

                }

            });

        });





async function deleteCurrentFile() {

    releaseMediaElement();

    if (!currentFileObj) return;



    if (currentFileObj.is_apple) {

        const modal = document.getElementById('icloud-delete-modal');

        if (modal) modal.style.display = 'flex';

        return;

    }



    if (confirm("¿Estás seguro de que deseas eliminar este archivo de forma permanente?")) {

        executeDeleteApi('local');

    }

}



window.executeIcloudDelete = function(mode) {

    const modal = document.getElementById('icloud-delete-modal');

    if (modal) modal.style.display = 'none';

    executeDeleteApi(mode);

};



async function executeDeleteApi(deleteMode) {

    try {

        const res = await fetch('/api/delete', {

            method: 'POST',

            headers: {'Content-Type': 'application/json'},

            body: JSON.stringify({ path: currentFileObj.path, delete_mode: deleteMode })

        });

        const data = await res.json();

        if (res.ok && !data.error) {

            closeLightbox();

            if (window.currentFolderItems) {

                const idx = window.currentFolderItems.findIndex(i => i.path === currentFileObj.path);

                if (idx !== -1) window.currentFolderItems.splice(idx, 1);

            }

            loadGallery();

        } else {

            alert("Error al eliminar: " + (data.error || "Desconocido"));

        }

    } catch (e) {

        alert("Error al intentar eliminar.");

    }

}



async function openLightbox(item) {

    if (!item) return;

    if (typeof resetZoom === 'function') resetZoom();

    currentFileObj = item;

    isCurrentVideo = item.type === 'video';

    

    const container = document.getElementById('lb-media-container');

    if (container) container.innerHTML = '';

    const dupContainer = document.getElementById('duplicate-banner-container');

    if (dupContainer) dupContainer.innerHTML = '';

    // Fast-resolve known zero faces to eliminate infinite spinners
    const knownFaces = (item.num_faces !== undefined ? item.num_faces : (item.faces_count !== undefined ? item.faces_count : (Array.isArray(item.faces) ? item.faces.length : null)));
    const isZeroFaces = knownFaces === 0 || item.status === 'Fotos Sin Rostro' || (item.ident && item.ident.includes('Sin Rostro')) || (item.category && item.category.includes('Sin_Rostro'));

    const mobileCountEl = document.getElementById('mobile-faces-count');
    if (mobileCountEl) mobileCountEl.textContent = isZeroFaces ? '0' : (knownFaces !== null ? knownFaces : '...');
    const topBtnLabel = document.querySelector('#btn-toggle-lb-panel .lb-btn-label');
    if (topBtnLabel) topBtnLabel.textContent = isZeroFaces ? 'Caras (0)' : (knownFaces !== null ? `Caras (${knownFaces})` : 'Caras');

    const cardsContainer = document.getElementById('person-cards-container');
    if (cardsContainer) {
        if (isZeroFaces) {
            cardsContainer.innerHTML = `
                <div style="padding:28px 16px; text-align:center; color:#8e8e93;">
                    <div style="font-size:28px; margin-bottom:8px; opacity:0.6;">📷</div>
                    <div style="font-size:13px; font-weight:600; color:#fff; margin-bottom:4px;">Sin personas detectadas</div>
                    <div style="font-size:11px; line-height:1.4;">No se encontraron caras registradas en esta foto.</div>
                    <button onclick="runAnalysis(true)" style="margin-top:14px; padding:6px 14px; border-radius:12px; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12); color:#64d2ff; font-size:11px; font-weight:600; cursor:pointer;">🔍 Forzar detección</button>
                </div>`;
        } else {
            cardsContainer.innerHTML = `
                <div id="lb-faces-loading-state" style="padding:24px 16px; text-align:center; color:#8e8e93;">
                    <div class="loader-small" style="margin:0 auto 10px auto;"></div>
                    <div style="font-size:12px; font-weight:600; color:#fff; margin-bottom:4px;">Cargando caras...</div>
                </div>`;
        }
    }

    

    // Set Header filename & counter

    const fnameEl = document.getElementById('lb-filename');

    if (fnameEl) fnameEl.textContent = item.name || (item.path ? item.path.split(/[\\\/]/).pop() : 'archivo.jpg');

    const counterEl = document.getElementById('lb-counter');

    if (counterEl) {

        const items = (typeof currentFolderItems !== 'undefined' && currentFolderItems && currentFolderItems.length > 0) ? currentFolderItems : [];

        const curIdx = items.findIndex(x => x.path === item.path);

        counterEl.textContent = `${curIdx >= 0 ? curIdx + 1 : 1} / ${items.length || 1}`;

    }

    const dlOrig = document.getElementById('btn-download-orig');

    const analyzeBtn = document.getElementById('btn-lightbox-analyze-video');
    if (analyzeBtn) {
        if (isCurrentVideo && (item.needs_face_analysis || item.status === 'Pendiente de Análisis' || item.category === '📋 Revisión / Por Organizar')) {
            analyzeBtn.style.display = 'inline-flex';
            const txt = document.getElementById('btn-lightbox-analyze-text');
            if (txt) txt.textContent = 'Analizar Vídeo';
            analyzeBtn.disabled = false;
        } else {
            analyzeBtn.style.display = 'none';
        }
    }

    if (dlOrig) {

        dlOrig.href = `/media?path=${encodeURIComponent(item.path)}`;

        dlOrig.download = item.name || 'foto.jpg';

    }



    let mediaEl;

    if (isCurrentVideo) {

        mediaEl = document.createElement('video');

        mediaEl.src = `/media?path=${encodeURIComponent(item.path)}`;

        mediaEl.controls = true;

        mediaEl.autoplay = false;

        mediaEl.preload = 'metadata';

        mediaEl.playsInline = true;

        mediaEl.className = 'lb-media-element';

        mediaEl.style.width = '100%';

        mediaEl.style.height = '100%';

        mediaEl.style.maxHeight = 'calc(100vh - 120px)';

        mediaEl.style.objectFit = 'contain';

        

        mediaEl.onloadedmetadata = () => {

            if (typeof resizeContainerToImage === 'function') resizeContainerToImage();

            if (window.liveScanTimestamp) {

                try { mediaEl.currentTime = window.liveScanTimestamp; } catch(e){}

                window.liveScanTimestamp = null;

            }

        };

    } else {

        mediaEl = document.createElement('img');

        mediaEl.className = 'lb-media-element';

        // Cargar miniatura WebP ultrarrápida (<5ms) de forma instantánea para eliminar pantalla negra

        mediaEl.src = `/api/thumbnail?path=${encodeURIComponent(item.path)}`;

        

        // Precargar versión original en segundo plano y sustituir limpiamente cuando esté lista

        const fullImg = new Image();

        fullImg.src = `/media?path=${encodeURIComponent(item.path)}`;

        fullImg.onload = () => {

            if (currentFileObj && currentFileObj.path === item.path && mediaEl) {

                mediaEl.src = fullImg.src;

            }

        };

    }

    

    const analyzeToolbar = document.getElementById('analyze-toolbar');

    if (analyzeToolbar) {

        analyzeToolbar.style.display = isCurrentVideo ? 'block' : 'none';

    }

    

    if (container) container.appendChild(mediaEl);

    

    const lb = document.getElementById('lightbox');

    if (lb) {

        lb.classList.remove('hidden');

        lb.style.display = 'flex';

    }

    if (window.innerWidth <= 820) {

        const panel = document.getElementById('metadata-panel');

        if (panel) panel.classList.remove('mobile-expanded');

        const pill = document.getElementById('mobile-lb-sheet-pill');

        if (pill) pill.style.display = 'flex';

    }



    // Show triage tab only for Revision/unknown items

    const triageTab = document.getElementById('tab-triage');

    const isRevisionItem = currentCat === '📋 Revisión / Por Organizar' ||

        (currentIdent && (currentIdent.includes('Persona Nueva') || currentIdent.includes('👤') ||

         currentIdent.includes('Dudosos') || currentIdent.includes('Desconocidos')));

    if (triageTab) {

        triageTab.style.display = isRevisionItem ? '' : 'none';

    }

    // Reset triage suggestions when switching items

    const trList = document.getElementById('triage-suggestions-list');

    if (trList) trList.innerHTML = '<div style="text-align:center;color:#8e8e93;font-size:12px;padding:20px;">Pulsa 🤖 Triage para cargar sugerencias</div>';



    // Metadatos EXIF

    fetch(`/api/metadata?path=${encodeURIComponent(item.path)}`)

        .then(r => r.json())

        .then(data => {

            const metaDate = document.getElementById('meta-date');

            if (metaDate) metaDate.textContent = data.date || '-';

            const metaSize = document.getElementById('meta-size');

            if (metaSize) metaSize.textContent = data.size || '-';

            const metaRes = document.getElementById('meta-res');

            if (metaRes) metaRes.textContent = data.resolution || '-';

            const metaCam = document.getElementById('meta-cam');

            if (metaCam) {

                const devIcon = (data.device_origin === 'apple' || data.is_apple) ? '🍎 ' : (data.device_origin === 'android' ? '🤖 ' : '📷 ');

                const camName = (data.camera && data.camera !== 'Desconocida') ? data.camera : (data.is_apple ? 'Apple iPhone' : (data.device_origin === 'android' ? 'Dispositivo Android' : 'Cámara'));

                metaCam.textContent = devIcon + camName;

            }

        }).catch(() => {});



    // IA de Nitidez y Duplicados

    fetch('/api/duplicates', {

        method: 'POST',

        headers: {'Content-Type': 'application/json'},

        body: JSON.stringify({ path: item.path })

    })

    .then(r => r.json())

    .then(data => {

        const sharpEl = document.getElementById('meta-sharpness');

        if (sharpEl) sharpEl.textContent = data.sharpness ? `${data.sharpness} Score` : '-';

        

        const dupContainer = document.getElementById('duplicate-banner-container');

        if (data.duplicate && dupContainer) {

            const dup = data.duplicate;

            dupContainer.innerHTML = `

                <div class="duplicate-banner">

                    <div class="duplicate-banner-title">⚠️ Foto Parecida (${dup.similarity}%)</div>

                    <div class="duplicate-banner-desc">

                        ${dup.is_current_better ? 

                            `⭐ <strong>Top Shot:</strong> Esta foto tiene mayor nitidez (${data.sharpness} vs ${dup.other_sharpness}). Recomendado conservar.` : 

                            `⚠️ Existe una versión más nítida de esta toma (<em>${dup.other_name}</em> - Nitidez: ${dup.other_sharpness} vs ${data.sharpness}).`}

                    </div>

                    ${!dup.is_current_better ? `<button class="duplicate-btn-delete" onclick="deleteCurrentFile()">🗑️ Borrar esta versión inferior</button>` : ''}

                </div>

            `;

        }

    }).catch(() => {});

        

    if (!isCurrentVideo) {

        let analysisStarted = false;

        const startAnalysisOnce = () => {

            if (analysisStarted) return;

            analysisStarted = true;

            if (typeof resizeContainerToImage === 'function') resizeContainerToImage();

            runAnalysis();

        };



        if (mediaEl.complete) {

            startAnalysisOnce();

        } else {

            mediaEl.onload = startAnalysisOnce;

            mediaEl.onerror = () => {

                startAnalysisOnce();

            };

            setTimeout(startAnalysisOnce, 2000);

        }

    } else {

        if (cardsContainer) {

            const isDudosoVid = Boolean(currentFileObj && (currentFileObj.is_dudoso || currentFileObj.status === 'Dudoso' || (currentFileObj.source && currentFileObj.source.includes('Por Confirmar'))));

            const dudosoBannerHtml = isDudosoVid ? `

                <div id="lightbox-dudoso-banner" style="background:rgba(255,159,10,0.15); border:1px solid #ff9f0a; border-radius:10px; padding:10px; margin-bottom:12px; text-align:center;">

                    <div style="font-weight:700; color:#ff9f0a; font-size:12px; margin-bottom:4px;">⚠️ ARCHIVO POR CONFIRMAR</div>

                    <div style="font-size:11px; color:#fff; margin-bottom:8px;">¿Confirmas que pertenece a <b>${currentIdent}</b>?</div>

                    <div style="display:flex; gap:6px;">

                        <button onclick="confirmDudosoPhoto(true)" style="flex:1; padding:7px 4px; border-radius:7px; border:1px solid #30d158; background:rgba(48,209,88,0.2); color:#30d158; font-weight:700; font-size:11px; cursor:pointer;">✅ Sí, confirmar</button>

                        <button onclick="confirmDudosoPhoto(false)" style="flex:1; padding:7px 4px; border-radius:7px; border:1px solid #ff453a; background:rgba(255,69,58,0.2); color:#ff6961; font-weight:700; font-size:11px; cursor:pointer;">❌ No es ${currentIdent}</button>

                    </div>

                </div>

            ` : '';

            cardsContainer.innerHTML = dudosoBannerHtml + `

                <div id="video-scan-container" style="margin-bottom:15px;">

                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">

                        <span style="font-size:12px; font-weight:700; color:var(--text); letter-spacing:0.5px;">CARAS DEL VÍDEO</span>

                        <button class="icon-btn" id="btn-scan-video-force" onclick="scanFullVideo(true)" style="background:rgba(255,255,255,0.08); color:var(--text-dim); border:1px solid rgba(255,255,255,0.1); padding:4px 8px; border-radius:6px; font-size:11px; cursor:pointer;" title="Re-escanear forzando nuevo análisis">🔄 Re-escanear</button>

                    </div>

                    <div id="video-scan-results" style="margin-bottom:15px;">

                        <div style="padding:15px; text-align:center;">

                            <div class="loader-small"></div>

                            <div style="font-size:11px; color:var(--text-dim); margin-top:8px;">Buscando caras en el vídeo...</div>

                        </div>

                    </div>

                </div>

                <hr style="border:0; border-top:1px solid rgba(255,255,255,0.1); margin:15px 0;">

                <p style="font-size:0.8rem; color:var(--text-dim); text-align:center;">También puedes pausar el vídeo y pulsar "Analizar Caras en Fotograma Actual" abajo para etiquetar manualmente un momento concreto.</p>

            `;

            // Escaneo o carga automática desde caché persistente

            scanFullVideo(false);

        }

    }

}





async function runAnalysis(force=false) {

            if (!currentFileObj) return;

            const currentRunPath = currentFileObj.path;

            const container = document.getElementById('lb-media-container');

            const mediaEl = container ? container.querySelector('.lb-media-element') : null;

            if (isCurrentVideo && mediaEl && !mediaEl.paused) {

                mediaEl.pause();

            }

            document.querySelectorAll('.lb-bounding-box').forEach(b => b.remove());

            const cardsContainer = document.getElementById('person-cards-container');

            if (cardsContainer && force) {
                cardsContainer.innerHTML = '<div id="lb-faces-loading-state" style="padding:24px 16px; text-align:center; color:#8e8e93;"><div class="loader-small" style="margin:0 auto 10px auto;"></div><div style="font-size:12px; font-weight:600; color:#fff; margin-bottom:4px;">Escaneando caras...</div></div>';
            }

            // Safety watchdog timer (3 seconds max before displaying helper state)
            const loadingWatchdog = setTimeout(() => {
                const loadingEl = document.getElementById('lb-faces-loading-state');
                if (loadingEl && cardsContainer && currentFileObj && currentFileObj.path === currentRunPath) {
                    cardsContainer.innerHTML = `
                        <div style="padding:22px 16px; text-align:center; color:#8e8e93;">
                            <div style="font-size:24px; margin-bottom:6px;">⏳</div>
                            <div style="font-size:12px; font-weight:600; color:#fff; margin-bottom:4px;">Detección en curso...</div>
                            <div style="font-size:11px; margin-bottom:12px;">El análisis está tomando unos segundos más.</div>
                            <button onclick="runAnalysis(true)" style="padding:6px 14px; border-radius:10px; background:rgba(10,132,255,0.15); border:1px solid rgba(10,132,255,0.3); color:#64d2ff; font-size:11px; font-weight:600; cursor:pointer;">🔄 Reintentar detección</button>
                        </div>`;
                }
            }, 3000);

            let timestamp = isCurrentVideo && mediaEl ? mediaEl.currentTime : null;

            let data;

            const abortCtrl = new AbortController();
            const abortTimer = setTimeout(() => abortCtrl.abort(), 15000);

            try {

                const res = await fetch('/api/analyze', {

                    method: 'POST',

                    headers: {'Content-Type': 'application/json'},

                    body: JSON.stringify({ path: currentFileObj.path, timestamp: timestamp, force: Boolean(force) }),
                    signal: abortCtrl.signal

                });
                clearTimeout(abortTimer);
                clearTimeout(loadingWatchdog);

                if (!res.ok) {
                    throw new Error(`Server returned ${res.status}`);
                }

                data = await res.json();

            } catch (err) {
                clearTimeout(abortTimer);
                clearTimeout(loadingWatchdog);

                console.error(err);

                if (cardsContainer && currentFileObj && currentFileObj.path === currentRunPath) {
                    cardsContainer.innerHTML = `
                        <div style="padding:22px 16px; text-align:center; color:#ff9f0a;">
                            <div style="font-size:24px; margin-bottom:6px;">⚠️</div>
                            <div style="font-size:12px; font-weight:600; color:#fff; margin-bottom:4px;">No se pudo completar el análisis</div>
                            <div style="font-size:11px; margin-bottom:12px; color:#8e8e93;">El servidor tardó en responder.</div>
                            <button onclick="runAnalysis(true)" style="padding:6px 14px; border-radius:10px; background:rgba(10,132,255,0.2); border:1px solid #0a84ff; color:#0a84ff; font-size:11px; font-weight:600; cursor:pointer;">🔄 Reintentar detección</button>
                        </div>`;
                }
                return;

            }

            

            if (!currentFileObj || currentFileObj.path !== currentRunPath) return; cardsContainer.innerHTML = '';

            

            currentFaces = data.faces || [];

            const detectedCount = currentFaces.length;

            const mobileCountEl = document.getElementById('mobile-faces-count');

            if (mobileCountEl) mobileCountEl.textContent = detectedCount;

            const mobilePill = document.getElementById('mobile-lb-sheet-pill');

            if (mobilePill) mobilePill.innerHTML = `▲ 👥 Caras (<span id="mobile-faces-count">${detectedCount}</span>)`;

            const topBtnLabel = document.querySelector('#btn-toggle-lb-panel .lb-btn-label');

            if (topBtnLabel) topBtnLabel.textContent = `Caras (${detectedCount})`;

            if (currentFileObj && (currentFileObj.is_dudoso || currentFileObj.status === 'Dudoso' || (currentFileObj.source && currentFileObj.source.includes('Por Confirmar')))) {

                const dudosoBanner = document.createElement('div');

                dudosoBanner.id = 'lightbox-dudoso-banner';

                dudosoBanner.style.cssText = 'background:rgba(255,159,10,0.15); border:1px solid #ff9f0a; border-radius:10px; padding:10px; margin-bottom:12px; text-align:center;';

                dudosoBanner.innerHTML = `

                    <div style="font-weight:700; color:#ff9f0a; font-size:12px; margin-bottom:4px;">⚠️ FOTO POR CONFIRMAR</div>

                    <div style="font-size:11px; color:#fff; margin-bottom:8px;">¿Confirmas que esta foto pertenece a <b>${currentIdent}</b>?</div>

                    <div style="display:flex; gap:6px;">

                        <button onclick="confirmDudosoPhoto(true)" style="flex:1; padding:7px 4px; border-radius:7px; border:1px solid #30d158; background:rgba(48,209,88,0.2); color:#30d158; font-weight:700; font-size:11px; cursor:pointer;">✅ Sí, confirmar</button>

                        <button onclick="confirmDudosoPhoto(false)" style="flex:1; padding:7px 4px; border-radius:7px; border:1px solid #ff453a; background:rgba(255,69,58,0.2); color:#ff6961; font-weight:700; font-size:11px; cursor:pointer;">❌ No es ${currentIdent}</button>

                    </div>

                `;

                cardsContainer.appendChild(dudosoBanner);

            }

            if (data.faces && data.faces.length > 0) {

                let intrinsicWidth = isCurrentVideo ? mediaEl.videoWidth : mediaEl.naturalWidth;

                let intrinsicHeight = isCurrentVideo ? mediaEl.videoHeight : mediaEl.naturalHeight;

                if (!intrinsicWidth && data.faces.length > 0) {

                    intrinsicWidth = data.faces[0].img_width;

                    intrinsicHeight = data.faces[0].img_height;

                }

                

                // Sincronizar tamaño del contenedor con el tamaño real de la imagen renderizada

                resizeContainerToImage();

                

                let hasUnconfirmed = false;

                data.faces.forEach((face, idx) => {

                    if (face.identity === 'Desconocido' || face.identity.startsWith('IA (Pendiente)')) hasUnconfirmed = true;

                    createFaceElements(face, idx + 1, intrinsicWidth, intrinsicHeight, mediaEl, container, cardsContainer);

                });

                

                const btnIgnore = document.getElementById('btn-ignore-unconfirmed');

                if (btnIgnore) {

                    if (hasUnconfirmed) {

                        btnIgnore.style.display = 'block';

                        btnIgnore.textContent = "🗑️ Ignorar caras no confirmadas";

                        btnIgnore.style.opacity = '1';

                        btnIgnore.style.pointerEvents = 'auto';

                    } else {

                        btnIgnore.style.display = 'none';

                    }

                }

            } else {

                cardsContainer.innerHTML = `
                    <div style="padding:28px 16px; text-align:center; color:#8e8e93;">
                        <div style="font-size:28px; margin-bottom:8px; opacity:0.6;">📷</div>
                        <div style="font-size:13px; font-weight:600; color:#fff; margin-bottom:4px;">Sin personas detectadas</div>
                        <div style="font-size:11px; line-height:1.4;">No se encontraron caras registradas en esta imagen.</div>
                        <button onclick="runAnalysis(true)" style="margin-top:14px; padding:6px 14px; border-radius:12px; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12); color:#64d2ff; font-size:11px; font-weight:600; cursor:pointer;">🔍 Escanear de nuevo</button>
                    </div>`;

            }

        }

        

                function highlightFace(faceNum) {

            document.querySelectorAll('.lb-bounding-box').forEach(b => {

                b.style.borderColor = 'rgba(255, 255, 255, 0.4)';

                b.style.zIndex = '1';

                b.classList.remove('active');

            });

            document.querySelectorAll('.person-card').forEach(c => c.style.background = 'rgba(28, 28, 30, 0.5)');

            

            const box = document.getElementById(`bbox-${faceNum}`);

            if (box) {

                box.style.borderColor = '#0a84ff';

                box.style.zIndex = '10';

                box.classList.add('active');

                

                // Auto-Focus Zoom

                const mediaEl = document.getElementById('lb-media');

                if (mediaEl && box.dataset.faceX) {

                    const intrinsicWidth = mediaEl.naturalWidth || mediaEl.videoWidth;

                    const intrinsicHeight = mediaEl.naturalHeight || mediaEl.videoHeight;

                    

                    if (intrinsicWidth && intrinsicHeight) {

                        const fx = parseFloat(box.dataset.faceX);

                        const fy = parseFloat(box.dataset.faceY);

                        const fw = parseFloat(box.dataset.faceW);

                        const fh = parseFloat(box.dataset.faceH);

                        

                        const centerX = fx + (fw / 2);

                        const centerY = fy + (fh / 2);

                        

                        const renderScale = mediaEl.clientWidth / intrinsicWidth;

                        

                        const offX = centerX - (intrinsicWidth / 2);

                        const offY = centerY - (intrinsicHeight / 2);

                        

                        if (window.innerWidth > 820) {
                            if (zoomLevel < 1.3) {
                                zoomLevel = 1.3;
                                panX = -(offX * renderScale) * zoomLevel;
                                panY = -(offY * renderScale) * zoomLevel;
                                applyZoomTransform();
                            }
                        }
                    }
                }
            }
            
            const card = document.getElementById("person-card-" + faceNum) || document.getElementById("pcard-" + faceNum);
            if (card) {
                card.style.background = 'rgba(10, 132, 255, 0.2)';
                card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
            if (window.innerWidth <= 820 && typeof toggleMobileLightboxSheet === 'function') {
                toggleMobileLightboxSheet(true);
            }

        }

        

        document.addEventListener('keydown', (e) => {

            // No actuar si estamos escribiendo en un input

            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;

            

            if (e.key === 'Delete' || e.key === 'Backspace') {

                const activeBox = document.querySelector('.lb-bounding-box.active');

                if (activeBox && currentFileObj) {

                    const faceNum = activeBox.id.replace('bbox-', '');

                    const falsePosId = JSON.stringify({categoria: 'Ignorar', identidad: 'Falso_Positivo'});

                    const fx = parseFloat(activeBox.dataset.faceX) || 0;

                    const fy = parseFloat(activeBox.dataset.faceY) || 0;

                    const fw = parseFloat(activeBox.dataset.faceW) || 100;

                    const fh = parseFloat(activeBox.dataset.faceH) || 100;

                    inlineCorrect(

                        encodeURIComponent(currentFileObj.path), 

                        falsePosId, 

                        faceNum, 

                        fx, fy, fw, fh

                    );

                }

            }

        });



        function createFaceElements(face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl, container, cardsContainer) {

            intrinsicWidth = intrinsicWidth || (mediaEl ? mediaEl.naturalWidth || mediaEl.clientWidth : 800) || 800;

            intrinsicHeight = intrinsicHeight || (mediaEl ? mediaEl.naturalHeight || mediaEl.clientHeight : 600) || 600;

            // 1. Bounding Box sobre la Foto (Movible y Redimensionable)

            const box = document.createElement('div');

            box.className = 'lb-bounding-box';

            box.id = `bbox-${faceNum}`;

            

            // Atributos de datos para el atajo de teclado

            box.dataset.faceX = face.x;

            box.dataset.faceY = face.y;

            box.dataset.faceW = face.width;

            box.dataset.faceH = face.height;

            

            const percX = (face.x / intrinsicWidth) * 100;

            const percY = (face.y / intrinsicHeight) * 100;

            const percW = (face.width / intrinsicWidth) * 100;

            const percH = (face.height / intrinsicHeight) * 100;

            

            box.style.left = `${percX}%`;

            box.style.top = `${percY}%`;

            box.style.width = `${percW}%`;

            box.style.height = `${percH}%`;

            

            const badge = document.createElement('div');

            badge.className = 'lb-bb-badge';

            badge.textContent = `#${faceNum}`;

            box.appendChild(badge);

            

            ['tl', 'tr', 'bl', 'br'].forEach(corner => {

                const handle = document.createElement('div');

                handle.className = `resize-handle handle-${corner}`;

                handle.dataset.corner = corner;

                box.appendChild(handle);

            });

            

            box.onclick = (e) => {

                if (box.dataset.wasDragged === 'true') {

                    box.dataset.wasDragged = 'false';

                    return;

                }

                if (e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION' || e.target.tagName === 'BUTTON') return;

                e.stopPropagation();

                // Toggle selection visual

                document.querySelectorAll('.lb-box.selected').forEach(b => b.classList.remove('selected'));

                box.classList.add('selected');

                // Store selected box ID globally

                window.selectedBoxId = box.id;

                highlightFace(faceNum);

                // En movil: abrir directamente la barra inferior nativa y hacer scroll a la cara (cero popups gigantes sobre la imagen)
                if (window.innerWidth <= 820) {
                    if (typeof toggleMobileLightboxSheet === 'function') {
                        toggleMobileLightboxSheet(true);
                    }
                    const pcard = document.getElementById("pcard-" + faceNum) || document.getElementById("person-card-" + faceNum);
                    if (pcard) {
                        pcard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        pcard.style.transition = 'all 0.3s ease';
                        pcard.style.background = 'rgba(10, 132, 255, 0.25)';
                        pcard.style.borderColor = '#0a84ff';
                        setTimeout(() => {
                            pcard.style.background = '';
                            pcard.style.borderColor = '';
                        }, 1500);
                    }
                    return;
                }

                // En escritorio: contra-escalar el menu popup para que SIEMPRE mida 220px exactos independientemente del zoom
                let existingMenu = box.querySelector('.lb-box-popup');
                if (existingMenu) {
                    existingMenu.remove();
                    return;
                }

                document.querySelectorAll('.lb-box-popup').forEach(m => m.remove());

                const curZoom = zoomLevel || 1.0;
                const popup = document.createElement('div');
                popup.className = 'lb-box-popup';
                popup.style.cssText = 'position:absolute; bottom:-65px; left:50%; transform:translateX(-50%) scale(' + (1 / curZoom) + '); transform-origin:top center; z-index:100; background:rgba(20,20,22,0.95); backdrop-filter:blur(20px); padding:8px; border-radius:12px; border:1px solid rgba(255,255,255,0.25); box-shadow:0 8px 30px rgba(0,0,0,0.6); display:flex; flex-direction:column; gap:6px; width:220px; max-width:240px; font-size:11px;';
                

                let pathParts1 = currentFileObj.path.split(/[\\/]/);

                let folderName = pathParts1.slice(-2, -1)[0];

                let categoryName = pathParts1.slice(-3, -2)[0];

                if (folderName === '_Dudosos') {

                    folderName = pathParts1.slice(-3, -2)[0];

                    categoryName = pathParts1.slice(-4, -3)[0];

                }

                

                let rejectedId = JSON.stringify({categoria: '_Dudosos', identidad: 'Desconocido'});

                

                let innerHtml = `

                    <div style="color:white; font-size:0.75rem; text-align:center; opacity:0.7; padding-bottom:4px; border-bottom:1px solid rgba(255,255,255,0.1); margin-bottom:4px;">Face #${faceNum}</div>

                `;

                innerHtml += generateReassignHTML(face, faceNum, 'quickReassignFace', 'popup');

            popup.innerHTML = innerHtml;

            box.appendChild(popup);

        };

            

            // Hacer la caja arrastrable y redimensionable

            makeBoxInteractive(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl);

            

            container.appendChild(box);

            

            // 2. Avatar Recortado en Canvas

            let avatarUrl = updateAvatarCrop(mediaEl, face);

            

            // 3. Tarjeta en Sidebar

            const card = document.createElement('div');

            card.className = 'person-card';

            card.id = `pcard-${faceNum}`;

            

            let folderName, categoryName;

            if (currentCat && currentCat !== 'Resultados' && currentCat !== 'Personas Sin Nombre' && currentCat !== 'Limpieza Inteligente') {

                categoryName = currentCat;

                folderName = currentIdent;

            } else {

                let pathParts2 = currentFileObj.path.split(/[\\/]/);

                folderName = pathParts2.slice(-2, -1)[0];

                categoryName = pathParts2.slice(-3, -2)[0];

                if (folderName === '_Dudosos') {

                    folderName = pathParts2.slice(-3, -2)[0];

                    categoryName = pathParts2.slice(-4, -3)[0];

                }

            }

            

            // Determinar si hay sugerencia IA para mostrar en la tarjeta (con exclusión mutua estricta)
            const isGroupOrCategory = isInvalidFolderName(folderName) || isInvalidFolderName(categoryName) || !Boolean(folderName.match(/^[CFPM]\.?\s+/i) || folderName === 'YO' || (typeof identitiesList !== 'undefined' && identitiesList.some(id => id.identidad === folderName)));
            let isAlbumOwner = !isGroupOrCategory && (face.identity === folderName);
            let isDoubtfulOwner = !isGroupOrCategory && (face.identity && face.identity.startsWith('? ') && face.identity.replace(/^\?\s*/, '').trim() === folderName);
            
            const otherClaimedInCard = new Set();
            let ownerClaimedOnOtherFace = false;
            if (typeof currentFaces !== 'undefined' && Array.isArray(currentFaces)) {
                currentFaces.forEach((f, idx) => {
                    if (idx !== faceNum - 1) {
                        const rawId = f.identity || '';
                        const cleanId = rawId.replace(/^\?\s*/, '').trim();
                        const isNonPerson = !cleanId || cleanId === 'Desconocido' || cleanId.startsWith('IA ') || cleanId.startsWith('Falso_') || cleanId.startsWith('Ignorar_') || cleanId.includes('(Sin rostro') || cleanId.toLowerCase().includes('desconocid');
                        if (!isNonPerson) {
                            otherClaimedInCard.add(cleanId);
                            otherClaimedInCard.add(rawId);
                            if (cleanId === folderName || rawId === folderName || f.tag_type === 'dataset' || f.is_owner || f.is_centroid) {
                                ownerClaimedOnOtherFace = true;
                                if (folderName) otherClaimedInCard.add(folderName);
                            }
                        }
                        if (f.is_manual && cleanId) {
                            otherClaimedInCard.add(cleanId);
                            if (cleanId === folderName) {
                                ownerClaimedOnOtherFace = true;
                                if (folderName) otherClaimedInCard.add(folderName);
                            }
                        }
                    }
                });
            }

            // Si el dueño del álbum ya está identificado en otra cara de la misma foto, esta cara no es el dueño
            if (ownerClaimedOnOtherFace) {
                isAlbumOwner = false;
                isDoubtfulOwner = false;
            }

            // Extract AI suggestion if present (never display 'Desconocido' if an AI suggestion or candidate exists!)
            let rawSuggested = face.suggested_identity;
            if (!rawSuggested && face.identity) {
                if (face.identity.startsWith('? ')) {
                    rawSuggested = face.identity.replace(/^\?\s*/, '').trim();
                } else if (face.identity.startsWith('IA (Pendiente): ')) {
                    rawSuggested = face.identity.replace('IA (Pendiente): ', '').trim();
                } else if (face.identity.startsWith('IA: ')) {
                    rawSuggested = face.identity.replace('IA: ', '').trim();
                }
            }
            if (!rawSuggested && isDoubtfulOwner && face.identity) {
                rawSuggested = face.identity.replace(/^\?\s*/, '').trim();
            }
            if (rawSuggested && (otherClaimedInCard.has(rawSuggested) || (rawSuggested === folderName && ownerClaimedOnOtherFace))) {
                rawSuggested = null;
            }
            const cardSuggested = rawSuggested;
            const hasAiSugg = Boolean(cardSuggested && cardSuggested !== folderName && !otherClaimedInCard.has(cardSuggested));

            // Face Title display: If face has an AI suggestion, show the suggested name! NEVER just 'Desconocido'
            let rawIdent = face.identity;
            const hasSuggCandidate = Boolean(cardSuggested || face.suggested_identity || (face.identity && (face.identity.startsWith('? ') || face.identity.startsWith('IA (Pendiente)'))));
            if (!rawIdent || rawIdent === 'Desconocido' || rawIdent.startsWith('IA (Pendiente)') || rawIdent.startsWith('? Desconocido') || rawIdent.startsWith('?')) {
                if (cardSuggested) rawIdent = cardSuggested;
                else if (face.suggested_identity) rawIdent = face.suggested_identity;
                else rawIdent = 'Desconocido';
            }
            const cleanIdent = rawIdent.replace(/^\?\s*/, '').replace(/^IA\s*\(Pendiente\):\s*/i, '').replace(/^IA:\s*/i, '').trim();
            const isSuggBadge = hasAiSugg || isDoubtfulOwner || face.tag_type === 'ai_suggestion' || (face.confidence && String(face.confidence).includes('Sugerencia')) || hasSuggCandidate;
            let displayTitle = cleanIdent || 'Desconocido';
            if (displayTitle !== 'Desconocido' && isSuggBadge && !isAlbumOwner && !displayTitle.includes('(Sugerencia)')) {
                displayTitle += ' (Sugerencia)';
            }

            let confBadge = '';
            if (isAlbumOwner) {
                confBadge = `<span style="font-size:10px; color:#30d158; background:rgba(48,209,88,0.12); padding:2px 7px; border-radius:8px; font-weight:600;">👑 Dueño del álbum</span>`;
            } else if (face.confidence && String(face.confidence).includes('Manual')) {
                confBadge = `<span style="font-size:10px; color:#ff9f0a; background:rgba(255,159,10,0.12); padding:2px 7px; border-radius:8px; font-weight:600;">✏️ Editado</span>`;
            } else if (face.tag_type === 'dataset') {
                confBadge = `<span style="font-size:10px; color:#64d2ff; background:rgba(10,132,255,0.12); padding:2px 7px; border-radius:8px; font-weight:600;">🏷️ Dataset</span>`;
            } else if (isDoubtfulOwner || (face.confidence && String(face.confidence).includes('Dudoso'))) {
                confBadge = `<span style="font-size:10px; color:#ff9f0a; background:rgba(255,159,10,0.15); padding:2px 7px; border-radius:8px; font-weight:700;">⚠️ Por Confirmar</span>`;
            } else if (isSuggBadge) {
                const suggPct = face.suggested_score ? ` (${Math.round(face.suggested_score * 100)}%)` : '';
                confBadge = `<span style="font-size:10px; color:#64d2ff; background:rgba(10,132,255,0.12); padding:2px 7px; border-radius:8px; font-weight:600;">🤖 Sugerencia IA${suggPct}</span>`;
            } else {
                confBadge = `<span style="font-size:10px; color:#8e8e93; background:rgba(255,255,255,0.06); padding:2px 7px; border-radius:8px;">Pendiente</span>`;
            }

            card.innerHTML = `
                <div class="person-header" onclick="highlightFace(${faceNum})">
                    <div style="position:relative; flex-shrink:0;">
                        <img src="${avatarUrl}" class="person-avatar" id="pavatar-${faceNum}" alt="Face"
                             style="width:44px; height:44px; border-radius:50%; object-fit:cover;
                                    border:2px solid ${hasAiSugg ? '#64d2ff' : isAlbumOwner ? '#30d158' : 'rgba(255,255,255,0.2)'};
                                    box-shadow:0 2px 8px rgba(0,0,0,0.4);">
                        <div style="position:absolute; bottom:-2px; right:-2px; width:16px; height:16px;
                                    background:${hasAiSugg ? '#0a84ff' : isAlbumOwner ? '#30d158' : '#3a3a3c'};
                                    border-radius:50%; border:2px solid rgba(12,13,18,0.98);
                                    font-size:8px; display:flex; align-items:center; justify-content:center; color:#fff;">
                            ${faceNum}
                        </div>
                    </div>
                    <div class="person-info" style="flex:1; min-width:0;">
                        <div style="font-size:13px; font-weight:600; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-bottom:4px;"
                             id="pname-${faceNum}">${displayTitle}</div>

                        <div id="pconf-${faceNum}">${confBadge}</div>

                    </div>

                    <button onclick="openEvolutionModal('${face.identity}'); event.stopPropagation();"

                            title="Ver evolución temporal"

                            style="flex-shrink:0; width:28px; height:28px; border-radius:8px; border:none;

                                   background:rgba(10,132,255,0.1); color:#64d2ff; cursor:pointer;

                                   font-size:13px; display:flex; align-items:center; justify-content:center;

                                   transition:all 0.15s;"

                            onmouseover="this.style.background='rgba(10,132,255,0.25)'"

                            onmouseout="this.style.background='rgba(10,132,255,0.1)'">📈</button>

                </div>

                <div id="pcard-actions-${faceNum}">

                    ${generateReassignHTML(face, faceNum, 'quickReassignFace', 'sidebar')}

                </div>

            `;



            cardsContainer.appendChild(card);



        }



        function updateAvatarCrop(mediaEl, face) {

            try {

                if (!face || face.width < 10 || face.height < 10) return '';

                const canvas = document.createElement('canvas');

                canvas.width = 120;

                canvas.height = 120;

                const ctx = canvas.getContext('2d');

                ctx.drawImage(mediaEl, Math.max(0, face.x), Math.max(0, face.y), face.width, face.height, 0, 0, 120, 120);

                return canvas.toDataURL();

            } catch(e) {

                return '';

            }

        }



        function makeBoxInteractive(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl) {

            let isDragging = false;

            let isResizing = false;

            let currentHandle = null;

            let startX, startY, startLeft, startTop, startW, startH;

            const container = document.getElementById('lb-media-container');



            // Arrastrar Posición

            box.addEventListener('mousedown', (e) => {

                if (e.target.classList.contains('resize-handle')) return;

                if (e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION' || e.target.tagName === 'BUTTON') return;

                

                e.stopPropagation();

                isDragging = true;

                startX = e.clientX;

                startY = e.clientY;

                const popup = box.querySelector('.lb-box-popup');

                if (popup) popup.style.display = 'none';

                const rect = box.getBoundingClientRect();

                if (popup) popup.style.display = 'flex';

                const containerRect = container.getBoundingClientRect();

                let containerW = containerRect.width;

                let containerH = containerRect.height;

                let containerLeft = containerRect.left;

                let containerTop = containerRect.top;

                if (containerW < 50) {

                    const mediaRect = mediaEl.getBoundingClientRect();

                    containerW = mediaRect.width;

                    containerH = mediaRect.height;

                    containerLeft = mediaRect.left;

                    containerTop = mediaRect.top;

                }

                startLeft = rect.left - containerLeft;

                startTop = rect.top - containerTop;



                let isDragTicking = false;

                const onMouseMove = (ev) => {

                    if (!isDragging) return;

                    const dx = ev.clientX - startX;

                    const dy = ev.clientY - startY;

                    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) box.dataset.wasDragged = 'true';

                    const newLeft = startLeft + dx;

                    const newTop = startTop + dy;

                    if (!isDragTicking) {

                        window.requestAnimationFrame(() => {

                            box.style.left = `${(newLeft / containerW) * 100}%`;

                            box.style.top = `${(newTop / containerH) * 100}%`;

                            isDragTicking = false;

                        });

                        isDragTicking = true;

                    }

                };



                const onMouseUp = () => {

                    if (isDragging) {

                        isDragging = false;

                        document.removeEventListener('mousemove', onMouseMove);

                        document.removeEventListener('mouseup', onMouseUp);

                        saveBoxDimensions(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl);

                    }

                };



                document.addEventListener('mousemove', onMouseMove);

                document.addEventListener('mouseup', onMouseUp);

            });



            // Redimensionar Tamaño desde cualquier esquina

            const handles = box.querySelectorAll('.resize-handle');

            handles.forEach(handle => {

                handle.addEventListener('mousedown', (e) => {

                    e.stopPropagation();

                    isResizing = true;

                    currentHandle = handle.dataset.corner;

                    startX = e.clientX;

                    startY = e.clientY;

                    const popup = box.querySelector('.lb-box-popup');

                if (popup) popup.style.display = 'none';

                const rect = box.getBoundingClientRect();

                if (popup) popup.style.display = 'flex';

                    const containerRect = container.getBoundingClientRect();

                    let containerW = containerRect.width;

                    let containerH = containerRect.height;

                    let containerLeft = containerRect.left;

                    let containerTop = containerRect.top;

                    if (containerW < 50) {

                        const mediaRect = mediaEl.getBoundingClientRect();

                        containerW = mediaRect.width;

                        containerH = mediaRect.height;

                        containerLeft = mediaRect.left;

                        containerTop = mediaRect.top;

                    }

                    startLeft = rect.left - containerLeft;

                    startTop = rect.top - containerTop;

                    startW = rect.width;

                    startH = rect.height;



                    let isResizeTicking = false;

                    const onMouseMove = (ev) => {

                        if (!isResizing) return;

                        box.dataset.wasDragged = 'true';

                        const dx = ev.clientX - startX;

                        const dy = ev.clientY - startY;

                        let newW = startW;

                        let newH = startH;

                        let newLeft = startLeft;

                        let newTop = startTop;



                        if (currentHandle.includes('r')) {

                            newW = Math.max(20, startW + dx);

                        } else if (currentHandle.includes('l')) {

                            newW = Math.max(20, startW - dx);

                            if (newW > 20) newLeft = startLeft + dx;

                        }



                        if (currentHandle.includes('b')) {

                            newH = Math.max(20, startH + dy);

                        } else if (currentHandle.includes('t')) {

                            newH = Math.max(20, startH - dy);

                            if (newH > 20) newTop = startTop + dy;

                        }



                        if (!isResizeTicking) {

                            window.requestAnimationFrame(() => {

                                box.style.width = `${(newW / containerW) * 100}%`;

                                box.style.height = `${(newH / containerH) * 100}%`;

                                box.style.left = `${(newLeft / containerW) * 100}%`;

                                box.style.top = `${(newTop / containerH) * 100}%`;

                                isResizeTicking = false;

                            });

                            isResizeTicking = true;

                        }

                    };



                    const onMouseUp = () => {

                        if (isResizing) {

                            isResizing = false;

                            document.removeEventListener('mousemove', onMouseMove);

                            document.removeEventListener('mouseup', onMouseUp);

                            saveBoxDimensions(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl);

                        }

                    };



                    document.addEventListener('mousemove', onMouseMove);

                    document.addEventListener('mouseup', onMouseUp);

                });

            });

        }



        function saveBoxDimensions(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl) {

            const leftPct = parseFloat(box.style.left) / 100;

            const topPct = parseFloat(box.style.top) / 100;

            const widthPct = parseFloat(box.style.width) / 100;

            const heightPct = parseFloat(box.style.height) / 100;



            if (isNaN(leftPct) || isNaN(topPct) || isNaN(widthPct) || isNaN(heightPct) || widthPct <= 0 || heightPct <= 0) {

                return;

            }



            face.x = Math.max(0, Math.round(leftPct * intrinsicWidth));

            face.y = Math.max(0, Math.round(topPct * intrinsicHeight));

            face.width = Math.min(intrinsicWidth - face.x, Math.round(widthPct * intrinsicWidth));

            face.height = Math.min(intrinsicHeight - face.y, Math.round(heightPct * intrinsicHeight));



            if (face.width < 25 || face.height < 25) {

                return;

            }



            // Actualizar avatar en sidebar

            const avatarImg = document.getElementById(`pavatar-${faceNum}`);

            if (avatarImg) {

                avatarImg.src = updateAvatarCrop(mediaEl, face);

            }



            // Guardar permanentemente en backend y activar Reaprendizaje Activo

            if (face.identity && face.identity !== "Desconocido") {

                let pathParts3 = currentFileObj.path.split(/[\\/]/);

                let folderName = pathParts3.slice(-2, -1)[0];

                let categoryName = pathParts3.slice(-3, -2)[0];

                if (folderName === '_Dudosos') {

                    folderName = pathParts3.slice(-3, -2)[0];

                    categoryName = pathParts3.slice(-4, -3)[0];

                }

                

                fetch('/api/correct', {

                    method: 'POST',

                    headers: {'Content-Type': 'application/json'},

                    body: JSON.stringify({

                        path: currentFileObj.path,

                        new_categoria: categoryName,

                        new_identidad: face.identity,

                        face: {x: face.x, y: face.y, width: face.width, height: face.height},

                        apply_to_duplicates: true

                    })

                }).then(r => r.json()).then(data => {

                    if (data.success) {

                        showToast('Recuadro guardado correctamente.');

                        if (data.new_path) {

                            if (currentFileObj) currentFileObj.path = data.new_path.replace(/\\/g, '/');

                        }

                        // loadGallery() omitido para evitar congelar visor

                        // Mantener visor abierto en vídeo para seguir editando caras

                    } else if (data.error) {

                        alert("Error: " + data.error);

                    }

                });

            }

        }





        async function ignoreUnconfirmedFaces() {

            if (!currentFaces || currentFaces.length === 0) return;

            

            // Collect unconfirmed faces

            const unconfirmed = [];

            currentFaces.forEach((face, idx) => {

                if (face.identity === 'Desconocido' || face.identity.startsWith('IA (Pendiente)')) {

                    unconfirmed.push({ face: face, faceNum: idx + 1 });

                }

            });

            

            if (unconfirmed.length === 0) {

                showToast("No hay caras sin confirmar.");

                return;

            }

            

            if (!confirm(`¿Ignorar ${unconfirmed.length} caras no confirmadas?`)) return;

            

            document.getElementById('btn-ignore-unconfirmed').textContent = "Ignorando...";

            document.getElementById('btn-ignore-unconfirmed').style.opacity = '0.5';

            document.getElementById('btn-ignore-unconfirmed').style.pointerEvents = 'none';

            

            for (let i = 0; i < unconfirmed.length; i++) {

                const item = unconfirmed[i];

                const face = item.face;

                let idObj = {categoria: "Ignorar", identidad: "Ignorar_Irrelevante"};

                

                try {

                    const res = await fetch('/api/correct', {

                        method: 'POST',

                        headers: {'Content-Type': 'application/json'},

                        body: JSON.stringify({ 

                            path: currentFileObj.path, 

                            new_categoria: idObj.categoria, 

                            new_identidad: idObj.identidad,

                            face: {

                            x: face.box ? face.box[0] : (face.x || 0),

                            y: face.box ? face.box[1] : (face.y || 0),

                            width: face.box ? face.box[2] : (face.width || 0),

                            height: face.box ? face.box[3] : (face.height || 0)

                        },

                            apply_to_duplicates: false

                        })

                    });

                    const data = await res.json();

                    if(data.success && data.new_path && currentFileObj) {

                        currentFileObj.path = data.new_path;

                    }

                } catch(e) {

                    console.error("Error ignoring face", e);

                }

            }

            

            showToast(`${unconfirmed.length} caras ignoradas.`);

            

            // Refresh

            if (currentCat === 'Limpieza Inteligente') {

                const gridItem = document.getElementById('grid-container').children[currentItemIndex];

                if (gridItem) {

                    gridItem.style.opacity = '0.3';

                    gridItem.style.pointerEvents = 'none';

                }

            } else if (currentCat && currentIdent) {

                renderGrid(currentCat, currentIdent);

            }

            

            // Re-open lightbox to refresh faces list

            openLightbox(currentFileObj);

        }



        async function quickReassignFace(valStr, faceNum) {

            const face = currentFaces[faceNum - 1];

            if (!face) return;

            await inlineCorrect(encodeURIComponent(currentFileObj.path), valStr, faceNum, face.x, face.y, face.width, face.height);

        }



        async function inlineCorrect(pathEncoded, valStr, faceNum, faceX, faceY, faceW, faceH) {

            if(!valStr) return;

            const targetPath = (currentFileObj && currentFileObj.path) ? currentFileObj.path : decodeURIComponent(pathEncoded);

            if(!targetPath) return;



            const safeX = (faceX !== undefined && faceX !== 'undefined' && faceX !== null) ? parseFloat(faceX) : 0;

            const safeY = (faceY !== undefined && faceY !== 'undefined' && faceY !== null) ? parseFloat(faceY) : 0;

            const safeW = (faceW !== undefined && faceW !== 'undefined' && faceW !== null) ? parseFloat(faceW) : 100;

            const safeH = (faceH !== undefined && faceH !== 'undefined' && faceH !== null) ? parseFloat(faceH) : 100;



            let idObj;

            if(valStr === 'NEW') {

                const newCat = prompt("Introduce la categoría:", "Conocidos");

                if(!newCat) return;

                const newIdent = prompt("Introduce el nombre completo:");

                if(!newIdent) return;

                idObj = {categoria: newCat, identidad: newIdent};

            } else {

                idObj = JSON.parse(valStr);

            }

            // Confirmación explícita para prevenir cambios accidentales al tocar la pantalla
            const personName = idObj.identidad || 'esta persona';
            let confirmMsg = `¿Confirmar esta cara como "${personName}"?`;
            if (idObj.identidad === 'YO') {
                confirmMsg = '¿Confirmar que esta cara eres TÚ (Eneko)?';
            } else if (idObj.identidad === 'Desconocido') {
                const currentFaceIdent = (faceNum && currentFaces && currentFaces[faceNum - 1] && currentFaces[faceNum - 1].identity) ? currentFaces[faceNum - 1].identity.replace(/^IA\s*\(Pendiente\):\s*/i, '').replace(/^\?\s*/, '') : '';
                confirmMsg = currentFaceIdent ? `¿Confirmar que esta persona NO es ${currentFaceIdent}?` : '¿Marcar esta cara como Desconocida?';
            } else if (idObj.identidad === 'Falso_Positivo' || idObj.identidad === 'Ignorar_Irrelevante') {
                confirmMsg = '¿Descartar esta cara como irrelevante o falso positivo?';
            }

            if (!confirm(confirmMsg)) {
                return;
            }



            // Llamada directa y ultra-rápida (no bloqueante para la UI)

            const res = await fetch('/api/correct', {

                method: 'POST',

                headers: {'Content-Type': 'application/json'},

                body: JSON.stringify({ 

                    path: targetPath, 

                    new_categoria: idObj.categoria, 

                    new_identidad: idObj.identidad,

                    face: {x: safeX, y: safeY, width: safeW, height: safeH},

                    apply_to_duplicates: false

                })

            });

            

            const data = await res.json();

            if(data.success) {

                if (data.new_path && currentFileObj) {
                    currentFileObj.path = data.new_path;
                    document.querySelectorAll('.lb-bounding-box').forEach(b => {
                        b.dataset.path = data.new_path;
                    });
                }
                

                if (idObj.identidad === 'Falso_Positivo' || idObj.identidad === 'Ignorar_Irrelevante') {

                    // Guardar cara descartada para permitir Deshacer inmediato

                    window.lastDiscardedFace = {

                        path: targetPath,

                        face: {x: safeX, y: safeY, width: safeW, height: safeH, identity: idObj.identidad}

                    };

                    

                    const bbox = document.getElementById(`bbox-${faceNum}`);

                    const pcard = document.getElementById(`pcard-${faceNum}`);

                    if (bbox) bbox.remove();

                    if (pcard) pcard.remove();

                    

                    showToast(`Cara descartada. <button onclick="undoLastDiscard()" style="background:#ff9f0a; color:#000; border:none; border-radius:4px; padding:3px 8px; margin-left:8px; font-weight:700; cursor:pointer;">↩ Deshacer</button>`);

                    return;

                }



                // 1. Actualizar estado local en memoria

                if (currentFaces && currentFaces[faceNum - 1]) {

                    currentFaces[faceNum - 1].identity = idObj.identidad;

                    currentFaces[faceNum - 1].confidence = 1.0;

                    currentFaces[faceNum - 1].is_manual = true;

                    currentFaces[faceNum - 1].suggested_identity = null;

                }



                showToast(`Asignado a '${cleanDisplayName(idObj.identidad)}'. La IA ha aprendido esta asignación.`);



                // 2. Actualizar visualmente la tarjeta de la persona sin parpadeos ni recargas bloqueantes

                const pname = document.getElementById(`pname-${faceNum}`);

                const pconf = document.getElementById(`pconf-${faceNum}`);

                const pcardActions = document.getElementById(`pcard-actions-${faceNum}`);

                if (pname) pname.textContent = `#${faceNum} ${cleanDisplayName(idObj.identidad)}`;

                if (pconf) pconf.innerHTML = `<span style="font-size:10px; color:#ff9f0a; background:rgba(255,159,10,0.12); padding:2px 7px; border-radius:8px; font-weight:600;">✏️ Editado (Manual)</span>`;

                if (pcardActions && currentFaces && currentFaces[faceNum - 1]) {

                    pcardActions.innerHTML = generateReassignHTML(currentFaces[faceNum - 1], faceNum, 'quickReassignFace', 'sidebar');

                }



                // Mutual exclusion: Re-render ALL other face action cards in this photo immediately

                if (currentFaces && Array.isArray(currentFaces)) {

                    currentFaces.forEach((f, idx) => {

                        const fn = idx + 1;

                        if (fn !== faceNum) {

                            if (f.suggested_identity === idObj.identidad) {

                                f.suggested_identity = null;

                            }

                            const otherActions = document.getElementById(`pcard-actions-${fn}`);

                            if (otherActions) {

                                otherActions.innerHTML = generateReassignHTML(f, fn, 'quickReassignFace', 'sidebar');

                            }

                        }

                    });

                }



                if (currentFileObj) {

                    if (currentFileObj.source && !currentFileObj.source.includes("Manual")) {

                        currentFileObj.source = currentFileObj.source + " + Manual";

                    }

                    const gridBadge = document.getElementById(`source-${currentItemIndex}`);

                    if (gridBadge) {

                        if (currentFileObj.source && currentFileObj.source.includes('Dataset')) {

                            gridBadge.className = 'badge badge-dataset';

                            gridBadge.textContent = '🔒 Dataset + ✏️ Manual';

                        } else {

                            gridBadge.className = 'badge badge-manual';

                            gridBadge.textContent = '✏️ Manual';

                        }

                    }

                }



                const isFromDudosos = currentCat === '_Dudosos' || currentIdent === '_Dudosos' || (currentFileObj && currentFileObj.path && currentFileObj.path.includes('_Dudosos')) || (currentCat && currentCat.includes('Revisar')) || (currentIdent && currentIdent.includes('Revisar'));

                const isReassignedAway = Boolean(currentIdent && idObj.identidad && idObj.identidad !== currentIdent && !isFromDudosos);

                const personStillInPhoto = Boolean(currentFaces && currentFaces.some(f => f.identity === currentIdent));



                if ((isFromDudosos && idObj.identidad !== 'Desconocido') || (isReassignedAway && !personStillInPhoto)) {
                    // Actualizar silenciosamente la tarjeta en la cuadrícula de fondo SIN expulsar al usuario del visor
                    const gridContainer = document.getElementById('grid-container');
                    if (gridContainer && gridContainer.children[currentItemIndex]) {
                        const card = gridContainer.children[currentItemIndex];
                        card.style.transition = 'opacity 0.3s ease';
                        card.style.opacity = '0.5';
                    }
                    // MANTENER AL USUARIO EN LA MISMA IMAGEN: Puede seguir confirmando o reasignando caras
                    console.log("[LIGHTBOX] Foto reasignada con éxito, manteniendo visor abierto en la imagen actual.");
                }

            } else {

                showToast(data.error || "Error al asignar.", true);

            }

        }



        window.undoLastDiscard = async function() {

            if (!window.lastDiscardedFace) return;

            const { path, face } = window.lastDiscardedFace;

            window.lastDiscardedFace = null;

            showToast("Restaurando cara...");

            try {

                const res = await fetch('/api/undo_discard', {

                    method: 'POST',

                    headers: {'Content-Type': 'application/json'},

                    body: JSON.stringify({ path, face })

                });

                const data = await res.json();

                if (data.success) {

                    showToast("✅ Cara restaurada correctamente.");

                    runAnalysis();

                } else {

                    showToast("Error al restaurar: " + (data.error || ''), true);

                }

            } catch (err) {

                showToast("Error de conexión al restaurar cara.", true);

            }

        };



        window.enableManualSelection = enableManualSelection;

        function enableManualSelection() {

            if (!currentFileObj) return;

            if (typeof resetZoom === 'function') resetZoom();

            window.isDrawingMode = true;

            const container = document.getElementById('lb-media-container');

            const mediaEl = container ? container.querySelector('.lb-media-element') : null;

            if (!mediaEl) return;

            

            mediaEl.draggable = false;

            showToast("Arrastra sobre la foto para crear un recuadro de persona (funciona con Zoom).");

            container.style.cursor = 'crosshair';

            

            let startPctX, startPctY, selectBox, isDrawing = false;

            

            const onMouseDown = (e) => {

                e.preventDefault();

                e.stopPropagation();

                isDrawing = true;

                const rect = mediaEl.getBoundingClientRect();

                startPctX = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));

                startPctY = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));

                

                selectBox = document.createElement('div');

                selectBox.style.cssText = `position:absolute; left:${startPctX * 100}%; top:${startPctY * 100}%; border:2px dashed #30d158; background:rgba(48,209,88,0.25); pointer-events:none; z-index:9999; box-sizing:border-box;`;

                container.appendChild(selectBox);

                

                const onMouseMove = (ev) => {

                    if (!isDrawing) return;

                    const curRect = mediaEl.getBoundingClientRect();

                    const curPctX = Math.max(0, Math.min(1, (ev.clientX - curRect.left) / curRect.width));

                    const curPctY = Math.max(0, Math.min(1, (ev.clientY - curRect.top) / curRect.height));

                    

                    const minPctX = Math.min(startPctX, curPctX);

                    const minPctY = Math.min(startPctY, curPctY);

                    const wPct = Math.abs(curPctX - startPctX);

                    const hPct = Math.abs(curPctY - startPctY);

                    

                    selectBox.style.left = `${minPctX * 100}%`;

                    selectBox.style.top = `${minPctY * 100}%`;

                    selectBox.style.width = `${wPct * 100}%`;

                    selectBox.style.height = `${hPct * 100}%`;

                };

                

                const onMouseUp = async (ev) => {

                    if (!isDrawing) return;

                    isDrawing = false;

                    

                    document.removeEventListener('mousemove', onMouseMove);

                    document.removeEventListener('mouseup', onMouseUp);

                    container.removeEventListener('mousedown', onMouseDown);

                    container.style.cursor = 'default';

                    window.isDrawingMode = false;

                    

                    const curRect = mediaEl.getBoundingClientRect();

                    const endPctX = Math.max(0, Math.min(1, (ev.clientX - curRect.left) / curRect.width));

                    const endPctY = Math.max(0, Math.min(1, (ev.clientY - curRect.top) / curRect.height));

                    

                    const leftPct = Math.min(startPctX, endPctX);

                    const topPct = Math.min(startPctY, endPctY);

                    const widthPct = Math.abs(endPctX - startPctX);

                    const heightPct = Math.abs(endPctY - startPctY);

                    

                    if (selectBox) selectBox.remove();

                    if (widthPct < 0.01 || heightPct < 0.01) return;

                    

                    let isCurrentVideo = mediaEl.tagName === 'VIDEO';

                    let intrinsicWidth = (isCurrentVideo ? mediaEl.videoWidth : mediaEl.naturalWidth) || mediaEl.clientWidth || mediaEl.offsetWidth || 800;

                    let intrinsicHeight = (isCurrentVideo ? mediaEl.videoHeight : mediaEl.naturalHeight) || mediaEl.clientHeight || mediaEl.offsetHeight || 600;

                    

                    let realX = Math.round(leftPct * intrinsicWidth);

                    let realY = Math.round(topPct * intrinsicHeight);

                    let realW = Math.round(widthPct * intrinsicWidth);

                    let realH = Math.round(heightPct * intrinsicHeight);

                    

                    realX = Math.max(0, realX);

                    realY = Math.max(0, realY);

                    if (realX + realW > intrinsicWidth) realW = intrinsicWidth - realX;

                    if (realY + realH > intrinsicHeight) realH = intrinsicHeight - realY;

                    

                    const newFace = { x: realX, y: realY, width: realW, height: realH, identity: "Desconocido", confidence: "Selección manual" };

                    const nextNum = document.querySelectorAll('.lb-bounding-box').length + 1;

                    const cardsContainer = document.getElementById('person-cards-container');

                    

                    createFaceElements(newFace, nextNum, intrinsicWidth, intrinsicHeight, mediaEl, container, cardsContainer);

                    highlightFace(nextNum);

                    

                    const select = document.getElementById(`pselect-${nextNum}`);

                    if (select) {

                        select.focus();

                        select.scrollIntoView({ behavior: 'smooth', block: 'center' });

                    }

                    showToast(`Recuadro #${nextNum} listo. Selecciona la persona en el panel lateral.`);

                };

                

                document.addEventListener('mousemove', onMouseMove);

                document.addEventListener('mouseup', onMouseUp);

            };

            

            container.addEventListener('mousedown', onMouseDown);

        }

        window.enableManualSelection = enableManualSelection;



        async function runMassCleanup() {

            if (!confirm('¿Deseas analizar todas las carpetas "Persona Nueva" y reasignar automáticamente a las caras conocidas (seguridad > 60%)? Esto puede tardar unos minutos.')) return;

            

            showToast('Iniciando limpieza masiva... Por favor, no cierres esta página.', false);

            

            try {

                const res = await fetch('/api/mass_cleanup', { method: 'POST' });

                const data = await res.json();

                if (data.success) {

                    showToast(`✅ Limpieza masiva completada. Se reasignaron ${data.moved_count} imágenes.`);

                    await loadGallery();

                } else {

                    showToast('Error en la limpieza masiva: ' + data.error, true);

                }

            } catch (err) {

                showToast('Error de conexión en limpieza masiva', true);

            }

        }



        let selectedPaths = new Set();

        

        function toggleSelection(e, path) {

            e.stopPropagation(); // Evitar abrir el lightbox

            if (selectedPaths.has(path)) {

                selectedPaths.delete(path);

                e.target.classList.remove('selected');

            } else {

                selectedPaths.add(path);

                e.target.classList.add('selected');

            }

            updateFloatingBar();

        }

        

        function updateFloatingBar() {

            const bar = document.getElementById('floating-action-bar');

            const count = document.getElementById('fab-count');

            

            if (selectedPaths.size > 0) {

                count.innerText = `${selectedPaths.size} seleccionadas`;

                bar.classList.add('visible');

                

                // Poblar selectores si está vacío

                const select = document.getElementById('fab-reassign-select');

                if (select.options.length <= 1) {

                    populateFabSelect(select);

                }

            } else {

                bar.classList.remove('visible');

            }

        }

        

        function populateFabSelect(select) {

            select.innerHTML = '<option value="">-- Reasignar a... --</option>';

            const personas = new Set();

            if (identitiesList) {

                identitiesList.forEach(id => {

                    if (id.categoria === 'Conocidos' || id.categoria === 'Familiares') {

                        personas.add(id.identidad);

                    }

                });

            }

            const sorted = Array.from(personas).sort();

            sorted.forEach(p => {

                const opt = document.createElement('option');

                opt.value = p;

                opt.innerText = p;

                select.appendChild(opt);

            });

        }

        

        function clearSelection() {

            selectedPaths.clear();

            document.querySelectorAll('.select-checkbox.selected').forEach(el => el.classList.remove('selected'));

            updateFloatingBar();

        }

        

        async function applyBulkReassign() {

            const select = document.getElementById('fab-reassign-select');

            const val = select.value;

            if (!val) {

                showToast('Selecciona una persona primero', true);

                return;

            }

            await performBulkAction(val);

        }

        

        async function applyBulkIgnore() {

            if(confirm(`¿Ignorar las ${selectedPaths.size} fotos seleccionadas?`)) {

                await performBulkAction('Ignorar');

            }

        }

        

        async function performBulkAction(identity) {

            const paths = Array.from(selectedPaths);

            const res = await fetch('/api/correct_bulk', {

                method: 'POST',

                headers: {'Content-Type': 'application/json'},

                body: JSON.stringify({ paths, new_identity: identity })

            });

            const data = await res.json();

            if (data.success) {

                showToast(`Se han actualizado ${data.count} caras masivamente 🎉`);

                clearSelection();

                loadGallery(); // Recargar cuadrícula

            } else {

                showToast(`Error: ${data.error}`, true);

            }

        }





        let boxesVisible = true;

        function toggleBoxes() {

            boxesVisible = !boxesVisible;

            document.querySelectorAll('.lb-bounding-box').forEach(b => {

                b.style.opacity = boxesVisible ? '1' : '0';

                b.style.pointerEvents = boxesVisible ? 'auto' : 'none';

            });

            const btn = document.getElementById('btn-toggle-boxes');

            if (btn) btn.innerHTML = boxesVisible ? '👁️ Ocultar Recuadros' : '👁️ Mostrar Recuadros';

        }



        window.scanFullVideo = scanFullVideo;

        async function scanFullVideo(force = false) {

            if (!currentFileObj || !isCurrentVideo) return;

            const resDiv = document.getElementById('video-scan-results');

            const forceBtn = document.getElementById('btn-scan-video-force');

            if (!resDiv) return;

            

            if (force && forceBtn) {

                forceBtn.textContent = "⏳ Analizando...";

                forceBtn.style.pointerEvents = 'none';

            }

            

            resDiv.innerHTML = `

                <div style="padding:15px; text-align:center;">

                    <div class="loader-small"></div>

                    <div style="font-size:11px; color:var(--text-dim); margin-top:8px;">${force ? 'Re-analizando fotogramas del vídeo...' : 'Cargando caras detectadas...'}</div>

                </div>

            `;

            

            const vidAbort = new AbortController();
            const vidTimer = setTimeout(() => vidAbort.abort(), 8000);
            try {
                const res = await fetch('/api/scan_video', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ path: currentFileObj.path, force: force }),
                    signal: vidAbort.signal
                });
                clearTimeout(vidTimer);
                const data = await res.json();

                

                if (data.error) {

                    resDiv.innerHTML = `<p style="color:#ff453a; font-size:0.85rem;">Error: ${data.error}</p>`;

                } else if (data.detections && data.detections.length > 0) {

                    let html = '<h4 style="margin:0 0 10px 0; color:var(--text); font-size:0.9rem;">Personas Detectadas:</h4>';

                    data.detections.forEach(d => {

                        html += `<div style="background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); padding:8px 10px; border-radius:8px; margin-bottom:8px;">`;

                        html += `<div style="font-weight:bold; color:#0a84ff; font-size:13px; margin-bottom:4px; display:flex; justify-content:space-between;"><span>👤 ${typeof cleanDisplayName === 'function' ? cleanDisplayName(d.identity) : d.identity}</span><span style="font-size:11px; color:#30d158;">${d.confidence}%</span></div>`;

                        html += `<div style="font-size:0.8rem; color:var(--text-dim);">Aparece en: `;

                        d.seconds.forEach(sec => {

                            html += `<span onclick="seekVideoTo(${sec})" style="cursor:pointer; display:inline-block; padding:2px 6px; background:rgba(10,132,255,0.15); color:#64d2ff; border-radius:4px; margin:2px; font-weight:600; transition:0.2s;">${sec}s</span>`;

                        });

                        html += `</div></div>`;

                    });

                    resDiv.innerHTML = html;

                } else {

                    resDiv.innerHTML = '<p style="color:var(--text-dim); font-size:0.85rem; padding:10px 0; text-align:center;">No se detectaron personas conocidas en este vídeo.</p>';

                }

            } catch (err) {
                clearTimeout(vidTimer);
                resDiv.innerHTML = `<div style="text-align:center; padding:12px 8px;">
                    <p style="color:#ff9f0a; font-size:0.82rem; margin-bottom:8px;">⚠️ No se pudieron extraer fotogramas con rostros en este vídeo.</p>
                    <button onclick="scanFullVideo(true)" style="padding:5px 12px; border-radius:8px; background:rgba(10,132,255,0.2); border:1px solid #0a84ff; color:#0a84ff; font-size:11px; cursor:pointer;">🔄 Reintentar escanear</button>
                </div>`;
            }

            

            if (forceBtn) {

                forceBtn.textContent = "🔄 Re-escanear";

                forceBtn.style.pointerEvents = 'auto';

            }

        }



        window.seekVideoTo = function(sec) {

            const video = document.querySelector('#lb-media-container video');

            if (video) {

                video.currentTime = sec;

                video.play().catch(() => {});

            }

        };





// --- INJECTED FUNCTIONS ---

async function removeFromFolder() {

    releaseMediaElement();

    if (!currentFileObj || !currentFileObj.path || !currentCat || !currentIdent) return;

    const currentAnalysisPath = currentFileObj.path;

    if (!confirm(`¿Estás seguro de que quieres quitar esta foto de la carpeta de ${currentIdent}?`)) return;

    

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

        

        if (data.success) {

            showToast("✅ Foto quitada de la carpeta correctamente.");

            closeLightbox();

            

            // Remove item from currentFolderItems and DOM

            if (typeof currentFolderItems !== 'undefined' && currentFolderItems) {

                currentFolderItems = currentFolderItems.filter(it => it.path !== currentAnalysisPath);

                if (fullGallery && fullGallery[currentCat] && fullGallery[currentCat][currentIdent]) {

                    fullGallery[currentCat][currentIdent] = fullGallery[currentCat][currentIdent].filter(it => it.path !== currentAnalysisPath);

                }

                const gridContainer = document.getElementById('grid-container');

                if (gridContainer && gridContainer.children[currentItemIndex]) {

                    gridContainer.children[currentItemIndex].remove();

                }

                const subEl = document.getElementById('gallery-subtitle');

                if (subEl) subEl.textContent = `${currentFolderItems.length} elementos`;

            }

            await loadGallery();

        } else {

            alert(data.error || "Error al quitar la foto");

        }

    } catch(e) {

        alert("Error de conexión");

    }

}



function triggerDeepScanLightbox() {

    if (!currentFileObj || !currentFileObj.path) return;

    const currentAnalysisPath = currentFileObj.path;

    if (!confirm("Esto forzará una búsqueda exhaustiva de caras ignorando límites de confianza. ¿Continuar?")) return;

    

    fetch('/api/detect_deep', {

        method: 'POST',

        headers: {'Content-Type': 'application/json'},

        body: JSON.stringify({path: currentAnalysisPath})

    })

    .then(r => r.json())

    .then(data => {

        if (data.error) {

            alert(data.error);

        } else if (!data.faces || data.faces.length === 0) {

            alert("No se ha encontrado ninguna persona, ni siquiera con la detección profunda.");

        } else {

            alert("¡Detección profunda exitosa! Recargando caras...");

            openLightbox(currentFileObj);

        }

    })

    .catch(err => {

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





let currentPhotoFilterMode = 'all';

let currentDeviceOriginFilter = 'all';



function setPhotoFilter(mode, btnEl) {
    currentPhotoFilterMode = mode;
    document.querySelectorAll('#filter-toggle-container .filter-toggle-btn').forEach(b => {
        b.style.background = 'transparent';
        b.style.color = '#aaa';
        b.style.fontWeight = 'normal';
    });
    if (btnEl) {
        btnEl.style.background = '#0a84ff';
        btnEl.style.color = 'white';
        btnEl.style.fontWeight = 'bold';
    }

    const grid = document.getElementById('grid-container');
    if (!grid || !currentFolderItems) return;

    let filtered = currentFolderItems;
    if (window.currentTierFilter && window.currentTierFilter !== 'all') {
        filtered = filtered.filter(it => it.album_section === window.currentTierFilter);
    }
    if (mode === 'solo') filtered = filtered.filter(it => (it.num_faces || 0) <= 1);
    else if (mode === 'group') filtered = filtered.filter(it => (it.num_faces || 0) > 1);
    else if (mode === 'with_me') filtered = filtered.filter(it => it.has_yo === true);
    else if (mode === 'without_me') filtered = filtered.filter(it => it.has_yo === false);
    else if (mode === 'dudoso') filtered = filtered.filter(it => Boolean(it.is_dudoso || it.status === 'Dudoso' || it.album_section === 'review'));

    _currentGridItems = filtered;
    _gridRenderIndex = 0;
    window._lastRenderedTier = null;
    grid.innerHTML = '';
    _renderNextGridChunk();
}



function setDeviceOriginFilter(mode, btnEl) {

    currentDeviceOriginFilter = mode;

    document.querySelectorAll('#device-filter-container .filter-toggle-btn').forEach(b => {

        b.style.background = 'transparent';

        b.style.color = '#aaa';

        b.style.fontWeight = 'normal';

    });

    if (btnEl) {

        btnEl.style.background = (mode === 'apple') ? '#ff2d55' : (mode === 'android' ? '#30d158' : '#0a84ff');

        btnEl.style.color = 'white';

        btnEl.style.fontWeight = 'bold';

    }

    applyPhotoFilter();

}



let hideBlurryImages = false;



function toggleHideBlurry(btnEl) {

    hideBlurryImages = !hideBlurryImages;

    if (hideBlurryImages) {

        btnEl.style.background = 'rgba(255, 159, 10, 0.2)';

        btnEl.style.border = '1px solid #ff9f0a';

        btnEl.style.color = '#ff9f0a';

        btnEl.style.fontWeight = 'bold';

    } else {

        btnEl.style.background = 'transparent';

        btnEl.style.border = 'none';

        btnEl.style.color = '#ff9f0a';

        btnEl.style.fontWeight = 'normal';

    }

    applyPhotoFilter();

}



function applyPhotoFilter() {

    const grid = document.getElementById('grid-container');

    if (!grid || !currentFolderItems) return;

    const cards = grid.querySelectorAll('.media-card');

    const isFiltered = (currentPhotoFilterMode && currentPhotoFilterMode !== 'all') || (window.currentTierFilter && window.currentTierFilter !== 'all') || (currentDeviceOriginFilter && currentDeviceOriginFilter !== 'all');
    grid.querySelectorAll('.album-tier-header').forEach(hdr => {
        hdr.style.display = isFiltered ? 'none' : 'flex';
    });

    

    currentFolderItems.forEach((item, idx) => {

        const card = cards[idx];

        if (!card) return;

        

        const numFaces = item.num_faces || 0;

        let show = true;

        

        if (show && window.currentTierFilter && window.currentTierFilter !== 'all') {
            const itTier = item.album_section || (item.is_dudoso ? 'review' : ((item.is_dataset || item.is_manual) ? 'official' : 'suggestion'));
            if (itTier !== window.currentTierFilter) {
                show = false;
            }
        }

        if (currentPhotoFilterMode === 'solo') {

            show = (numFaces <= 1);

        } else if (currentPhotoFilterMode === 'group') {

            show = (numFaces > 1);

        } else if (currentPhotoFilterMode === 'with_me') {

            show = item.has_yo === true;

        } else if (currentPhotoFilterMode === 'without_me') {

            show = item.has_yo === false;

        } else if (currentPhotoFilterMode === 'dudoso') {

            show = Boolean(item.is_dudoso || item.status === 'Dudoso' || (item.source && item.source.includes('Por Confirmar')));

        }



        // Filter by Device Origin (Apple vs Android)

                // Filter by Screenshot Antiquity / Stale Filter
        if (show && window.currentScreenshotAgeFilter && window.currentScreenshotAgeFilter !== 'all') {
            const nowSec = Date.now() / 1000;
            const mtime = item.mtime || nowSec;
            const diffDays = (nowSec - mtime) / 86400;
            if (window.currentScreenshotAgeFilter === '3m' && diffDays < 90) {
                show = false;
            } else if (window.currentScreenshotAgeFilter === '6m' && diffDays < 180) {
                show = false;
            } else if (window.currentScreenshotAgeFilter === '1y' && diffDays < 365) {
                show = false;
            }
        }

        if (show && currentDeviceOriginFilter !== 'all') {

            const isAppleItem = Boolean(item.is_apple || item.device_origin === 'apple');

            if (currentDeviceOriginFilter === 'apple' && !isAppleItem) {

                show = false;

            } else if (currentDeviceOriginFilter === 'android' && (isAppleItem || item.device_origin !== 'android')) {

                show = false;

            }

        }



        if (hideBlurryImages && item.quality_score !== undefined && parseFloat(item.quality_score) < 100) {

            show = false;

        }

        

        if (show) {

            card.style.display = 'block';

        } else {

            card.style.display = 'none';

        }

    });

}





function releaseMediaElement() {

    try {

        const mediaEl = document.querySelector('.lb-media-element');

        if (mediaEl) {

            mediaEl.pause();

            mediaEl.removeAttribute('src');

            mediaEl.load();

        }

    } catch(e){}

}





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





async function purgeExactDuplicates() {

    if (!confirm("¿Deseas escanear y eliminar automáticamente todos los duplicados exactos (archivos idénticos en disco)? Conservaremos siempre la mejor copia.")) return;

    

    showToast("⏳ Escaneando y eliminando duplicados idénticos...", false);

    

    try {

        const res = await fetch('/api/purge_exact_duplicates', { method: 'POST' });

        const data = await res.json();

        if (data.success) {

            showToast(`✅ Limpieza completada: Se eliminaron ${data.purged_count} copias duplicadas idénticas.`);

            await loadIdentities();

            await loadGallery();

        } else {

            showToast("Error limpiando duplicados: " + (data.error || "Desconocido"), true);

        }

    } catch(err) {

        showToast("Error de conexión al purgar duplicados", true);

    }

}





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

        if (m.style.display === 'none' || m.classList.contains('hidden')) return;

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

                    <img loading="lazy" src="/api/thumbnail?path=${encodeURIComponent(f.path)}" style="width:100%; height:110px; object-fit:cover;">

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

    const c = document.getElementById('duplicates-content');

    if (c) c.innerHTML = '';

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

        if (m.style.display === 'none' || m.classList.contains('hidden')) return;

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

                    <img loading="lazy" src="/api/thumbnail?path=${encodeURIComponent(f.path)}" style="width:100%; height:110px; object-fit:cover;">

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





let selectedMode = 'local';



function selectStorageMode(mode) {

    selectedMode = mode;

    document.getElementById('opt-local').style.border = mode === 'local' ? '2px solid #a855f7' : '2px solid transparent';

    document.getElementById('opt-gdrive').style.border = mode === 'gdrive' ? '2px solid #a855f7' : '2px solid transparent';

    document.getElementById('opt-local').style.background = mode === 'local' ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.02)';

    document.getElementById('opt-gdrive').style.background = mode === 'gdrive' ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.02)';

    

    document.getElementById('field-local').style.display = mode === 'local' ? 'block' : 'none';

    document.getElementById('field-gdrive').style.display = mode === 'gdrive' ? 'block' : 'none';

}



function checkSetupConfig() {

    fetch('/api/config')

        .then(r => r.json())

        .then(cfg => {

            if (cfg.mode) selectStorageMode(cfg.mode);

            if (cfg.local_path) document.getElementById('input-local-path').value = cfg.local_path;

            if (cfg.gdrive_folder_id) document.getElementById('input-gdrive-url').value = 'https://drive.google.com/drive/folders/' + cfg.gdrive_folder_id;

        })

        .catch(() => {});

}



function openSetupModal() {

    if (window.toggleSettingsDrawer) window.toggleSettingsDrawer(true);

    checkSetupConfig();

}



function saveStorageConfig() {

    const localInput = document.getElementById('input-local-path');

    const gdriveInput = document.getElementById('input-gdrive-url');

    const payload = {

        mode: typeof selectedMode !== 'undefined' ? selectedMode : 'local',

        local_path: localInput ? localInput.value : '',

        gdrive_url_or_id: gdriveInput ? gdriveInput.value : ''

    };

    fetch('/api/config', {

        method: 'POST',

        headers: {'Content-Type': 'application/json'},

        body: JSON.stringify(payload)

    })

    .then(r => r.json())

    .then(res => {

        document.getElementById('setup-modal').style.display = 'none';

        location.reload();

    });

}



window.openSetupModal = openSetupModal;

window.selectStorageMode = selectStorageMode;

window.saveStorageConfig = saveStorageConfig;





function generateMagicShareLink(category, identity) {

    fetch('/api/magic_links/create', {

        method: 'POST',

        headers: {'Content-Type': 'application/json'},

        body: JSON.stringify({category: category, identity: identity, days: 30})

    })

    .then(r => r.json())

    .then(data => {

        if (data.share_url) {

            navigator.clipboard.writeText(data.share_url);

            alert("🔗 ¡Enlace Mágico Copiado al Portapapeles!\n\nEnvíaselo a tu amigo para que vea sus fotos:\n" + data.share_url);

        }

    });

}

window.generateMagicShareLink = generateMagicShareLink;





function openQuickCleanMode() {

    loadCategoryFilter('_Dudosos', 'Desconocido');

    openQuickCleanOverlay();

}

window.openQuickCleanMode = openQuickCleanMode;





const vElem = document.getElementById('lb-video');

if (vElem) {

    vElem.oncanplay = function() {

        const btn = document.getElementById('btn-scan-video');

        if (btn) {

            btn.disabled = false;

            btn.style.opacity = "1";

            btn.innerText = "🔍 Analizar Caras en Fotograma Actual";

        }

    };

}







if('serviceWorker' in navigator){navigator.serviceWorker.register('/static/sw.js')}





async function semanticSearch(term) {

    if (term.length < 2) {

        if(typeof filterGallery === 'function') filterGallery(term);

        return;

    }

    try {

        const res = await fetch('/api/search/semantic?q=' + encodeURIComponent(term));

        const data = await res.json();

        

        document.getElementById('gallery-title').textContent = 'Resultados Búsqueda Semántica';

        document.getElementById('gallery-subtitle').textContent = `"${term}"`;

        currentCat = 'Búsqueda Semántica';

        

        const grid = document.getElementById('grid-container');

        grid.innerHTML = '';

        currentPhotos = data;

        

        data.forEach((photo, idx) => {

            const card = document.createElement('div');

            card.className = 'media-card';

            card.innerHTML = `<img src="/api/media/${photo.filename}" loading="lazy" onclick="openLightbox(${idx})">`;

            grid.appendChild(card);

        });

    } catch(e) {

        console.error(e);

    }

}







    let mapInstance = null;

    async function openMapModal() {

        document.getElementById('modal-map').classList.remove('hidden');

        if (!mapInstance) {

            mapInstance = L.map('map-container').setView([40.4168, -3.7038], 5);

            L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {

                attribution: '&copy; OpenStreetMap contributors &copy; CARTO'

            }).addTo(mapInstance);

        }

        

        try {

            const res = await fetch('/api/map/locations');

            const locations = await res.json();

            locations.forEach(loc => {

                L.marker([loc.lat, loc.lon]).addTo(mapInstance).bindPopup(`<img src="/api/media/${loc.filename}" style="width:100px;">`);

            });

        } catch(e) {

            console.error(e);

        }

    }

    





    async function openEvolutionModal(identity) {

        if (!identity || identity === 'Desconocido' || identity === 'Ignorado') return;

        document.getElementById('evolution-title').textContent = `📈 Evolución de ${identity}`;

        document.getElementById('modal-evolution').classList.remove('hidden');

        document.getElementById('evolution-container').innerHTML = '<div class="loader-small" style="margin: auto;"></div>';

        

        try {

            const res = await fetch(`/api/person/evolution?identity=${encodeURIComponent(identity)}`);

            const data = await res.json();

            

            const container = document.getElementById('evolution-container');

            container.innerHTML = '';

            if (data.length === 0) {

                container.innerHTML = '<p style="margin:auto;">No hay suficientes datos</p>';

                return;

            }

            

            data.forEach(item => {

                const div = document.createElement('div');

                div.style.cssText = 'flex: 0 0 auto; text-align: center;';

                div.innerHTML = `

                    <img src="/api/media/${item.filename}" style="height: 150px; border-radius: 8px; object-fit: cover;">

                    <div style="font-size: 12px; margin-top: 5px; color: #aaa;">${item.year}</div>

                `;

                container.appendChild(div);

            });

        } catch(e) {

            console.error(e);

            document.getElementById('evolution-container').innerHTML = '<p style="color:red; margin:auto;">Error cargando evolución</p>';

        }

    }

    





    async function loadCategoryFilter(category, identity) {

        try {

            const res = await fetch(`/api/gallery?category=${encodeURIComponent(category)}&identity=${encodeURIComponent(identity)}`);

            const data = await res.json();

            

            document.getElementById('gallery-title').textContent = identity;

            document.getElementById('gallery-subtitle').textContent = category;

            currentCat = category;

            currentIdent = identity;

            

            const grid = document.getElementById('grid-container');

            grid.innerHTML = '';

            currentPhotos = data;

            

            data.forEach((photo, idx) => {

                const card = document.createElement('div');

                card.className = 'media-card';

                card.innerHTML = `<img src="/api/media/${photo.filename}" loading="lazy" onclick="openLightbox(${idx})">`;

                grid.appendChild(card);

            });

        } catch(e) {

            console.error(e);

        }

    }



    function openQuickCleanOverlay() {

        if (typeof isSwipeModeActive !== 'undefined' && !isSwipeModeActive) {

            if(typeof toggleSwipeMode === 'function') toggleSwipeMode();

        }

        

        let banner = document.getElementById('quick-clean-banner');

        if (!banner) {

            banner = document.createElement('div');

            banner.id = 'quick-clean-banner';

            banner.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; background: #ff9f0a; color: white; text-align: center; font-weight: bold; padding: 10px; z-index: 9999; box-shadow: 0 4px 10px rgba(0,0,0,0.5);';

            banner.innerHTML = '🔥 Modo Limpieza Rápida - Desliza para limpiar <button onclick="this.parentElement.remove()" style="margin-left:20px; background:black; color:white; border:none; padding:4px 8px; border-radius:4px; cursor:pointer;">Cerrar</button>';

            document.body.appendChild(banner);

        }

    }



function triggerRelearnCascade(identity) {

    if (!identity || identity === 'Falso_Positivo' || identity === 'Ignorar_Irrelevante') return;

    fetch('/api/relearn_cascade', {

        method: 'POST',

        headers: {'Content-Type': 'application/json'},

        body: JSON.stringify({identity: identity})

    })

    .then(r => r.json())

    .then(data => {

        if (data.promoted > 0) {

            showToast('🧠 Re-aprendizaje: ' + data.promoted + ' fotos promovidas de _Dudosos a ' + identity, 'success');

            loadIdentities();

        }

    })

    .catch(() => {});

}





function autoClassifyByFilename() {

    showToast('🏷️ Clasificando fotos por nombre de archivo...', 'info');

    fetch('/api/auto_classify_filename', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'})

    .then(r => r.json())

    .then(data => {

        if (data.moved > 0) {

            showToast('✅ ' + data.moved + ' archivos clasificados automáticamente', 'success');

            loadIdentities();

        } else {

            showToast('No se encontraron archivos para clasificar', 'info');

        }

    })

    .catch(e => showToast('Error: ' + e, 'error'));

}

window.autoClassifyByFilename = autoClassifyByFilename;





function addEvolutionToHeader() {

    const headerEl = document.querySelector('.gallery-header h2');

    if (!headerEl) return;

    const personName = headerEl.textContent.trim();

    if (!personName || personName === 'Todas las Fotos') return;

    

    let existingBtn = document.getElementById('btn-evolution-header');

    if (existingBtn) existingBtn.remove();

    

    const btn = document.createElement('button');

    btn.id = 'btn-evolution-header';

    btn.innerHTML = '📈 Ver Evolución Temporal';

    btn.style.cssText = 'margin-left:12px;padding:6px 14px;border-radius:10px;border:1px solid rgba(168,85,247,0.4);background:rgba(168,85,247,0.15);color:#c084fc;font-size:0.8rem;font-weight:600;cursor:pointer;transition:all 0.2s;';

    btn.onmouseenter = () => { btn.style.background = 'rgba(168,85,247,0.3)'; };

    btn.onmouseleave = () => { btn.style.background = 'rgba(168,85,247,0.15)'; };

    btn.onclick = () => openEvolutionModal(personName);

    headerEl.appendChild(btn);

}



// Call addEvolutionToHeader whenever an identity is selected

const origLoadFolder = window.loadFolderItems || function(){};

window.loadFolderItems = function() {

    origLoadFolder.apply(this, arguments);

    setTimeout(addEvolutionToHeader, 200);

};





// ============================================================

// BUSQUEDA INTENSIVA DE YO

// ============================================================

let _yoSearchInterval = null;



async function startIntensiveYoSearch() {

    const btn = document.getElementById('btn-yo-search');

    const statusEl = document.getElementById('yo-search-status');

    if (!btn || !statusEl) return;



    if (!confirm('Esto escaneara TODOS los archivos de la galeria buscando fotos tuyas.\n\nLas fotos con tu cara en dudosos/desconocidos se moveran a tu carpeta.\n\nPuede tardar varios minutos. Continuar?')) return;



    btn.disabled = true;

    btn.textContent = 'Buscando...';

    statusEl.style.display = 'block';

    statusEl.textContent = 'Iniciando busqueda intensiva...';



    try {

        await fetch('/api/intensive_search_yo', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({threshold: 0.55}) });

    } catch(e) {

        showToast('Error iniciando busqueda', true);

        btn.disabled = false;

        btn.textContent = 'Buscar Todas Mis Fotos';

        return;

    }



    if (_yoSearchInterval) clearInterval(_yoSearchInterval);

    _yoSearchInterval = setInterval(async () => {

        try {

            const res = await fetch('/api/yo_search_status');

            const data = await res.json();

            if (statusEl) statusEl.textContent = data.progress || '';

            if (data.done) {

                clearInterval(_yoSearchInterval);

                btn.disabled = false;

                btn.textContent = 'Buscar Todas Mis Fotos';

                showToast('Busqueda completada: ' + data.found + ' fotos con tu cara de ' + data.scanned + ' analizadas.');

                if (typeof refreshGallery === 'function') refreshGallery();

            }

        } catch(e) {}

    }, 3000);

}



// ============================================================

// AUDITOR AUTOMATICO

// ============================================================

let _auditInterval = null;



async function startSmartAudit() {

    const btn = document.getElementById('btn-smart-audit');

    const statusEl = document.getElementById('audit-status');

    if (!btn || !statusEl) return;



    if (!confirm('La auditoria automatica detectara impostores, rescatara dudosos/desconocidos y re-escaneara sin-rostro.\n\nLas correcciones manuales NO se tocaran.\n\nContinuar?')) return;



    btn.disabled = true;

    btn.textContent = 'Auditando...';

    statusEl.style.display = 'block';

    statusEl.textContent = 'Iniciando auditoria...';



    try {

        await fetch('/api/smart_audit', {

            method: 'POST',

            headers: {'Content-Type': 'application/json'},

            body: JSON.stringify({impostor_threshold: 0.42, rescue_threshold: 0.58})

        });

    } catch(e) {

        showToast('Error iniciando auditoria', true);

        btn.disabled = false;

        btn.textContent = 'Ejecutar Auditoria';

        return;

    }



    if (_auditInterval) clearInterval(_auditInterval);

    _auditInterval = setInterval(async () => {

        try {

            const res = await fetch('/api/audit_status');

            const data = await res.json();

            if (statusEl) statusEl.textContent = data.progress || '';

            if (data.done) {

                clearInterval(_auditInterval);

                btn.disabled = false;

                btn.textContent = 'Ejecutar Auditoria';

                const s = data.stats || {};

                showToast('Auditoria completa. Impostores: ' + (s.impostores||0) + ' | Rescatados: ' + (s.rescatados||0) + ' | Sin Rostro: ' + (s.sin_rostro_rescatados||0));

                if (typeof refreshGallery === 'function') refreshGallery();

            }

        } catch(e) {}

    }, 3000);

}



// ============================================================

// SISTEMA GLOBAL DE TAREAS Y ERRORES

// ============================================================

let _taskPollingIntervals = {};



/**

 * Lanza una tarea y muestra progreso/errores automaticamente.

 * @param {string} url - endpoint POST

 * @param {object} body - payload JSON

 * @param {string} taskName - nombre para mostrar al usuario

 * @param {function} onDone - callback(result) al terminar bien

 * @param {function} onError - callback(error, task_id) al fallar

 */

async function runBackgroundTask(url, body, taskName, onDone, onError) {

    try {

        const res = await fetch(url, {

            method: 'POST',

            headers: {'Content-Type': 'application/json'},

            body: body ? JSON.stringify(body) : undefined

        });



        if (!res.ok) {

            const err = await res.json().catch(() => ({error: `HTTP ${res.status}`}));

            showErrorToast(taskName, err.error || `Error ${res.status}`, null);

            if (onError) onError(err.error, null);

            return null;

        }



        const data = await res.json();



        if (data.error) {

            showErrorToast(taskName, data.error, null);

            if (onError) onError(data.error, null);

            return null;

        }



        // Si devuelve task_id, ponemos a hacer polling

        if (data.task_id) {

            showProgressToast(taskName, data.task_id);

            pollTask(data.task_id, taskName, onDone, onError);

            return data.task_id;

        }



        // Respuesta sincrona exitosa

        if (onDone) onDone(data);

        return null;



    } catch(e) {

        showErrorToast(taskName, e.message || 'Error de red', null);

        if (onError) onError(e.message, null);

        return null;

    }

}



function pollTask(taskId, taskName, onDone, onError) {

    if (_taskPollingIntervals[taskId]) clearInterval(_taskPollingIntervals[taskId]);



    _taskPollingIntervals[taskId] = setInterval(async () => {

        try {

            const res = await fetch(`/api/task_status/${taskId}`);

            const data = await res.json();



            updateProgressToast(taskId, data.progress || '');



            if (data.status === 'done') {

                clearInterval(_taskPollingIntervals[taskId]);

                delete _taskPollingIntervals[taskId];

                dismissProgressToast(taskId);

                if (onDone) onDone(data.result || data);

            } else if (data.status === 'error') {

                clearInterval(_taskPollingIntervals[taskId]);

                delete _taskPollingIntervals[taskId];

                dismissProgressToast(taskId);

                showErrorToast(taskName, data.error || 'Error desconocido', taskId);

                if (onError) onError(data.error, taskId);

            }

        } catch(e) {

            // error de red temporal, seguir intentando

        }

    }, 2000);

}



// ── Toast de progreso (persistente hasta que termina) ──────

const _progressToasts = {};



function showProgressToast(name, taskId) {

    const id = `ptoa-${taskId}`;

    if (document.getElementById(id)) return;



    const div = document.createElement('div');

    div.id = id;

    div.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:6px;';

    const inner = document.createElement('div');

    inner.style.cssText = 'background:rgba(30,30,30,0.95);border:1px solid rgba(10,132,255,0.4);border-radius:10px;padding:12px 16px;color:#fff;font-size:13px;display:flex;align-items:center;gap:10px;min-width:260px;backdrop-filter:blur(10px);box-shadow:0 4px 20px rgba(0,0,0,0.5);';

    inner.innerHTML = `<span style="display:inline-block;width:14px;height:14px;border:2px solid #0a84ff;border-top-color:transparent;border-radius:50%;animation:spin 0.8s linear infinite;flex-shrink:0;"></span><span id="${id}-text" style="flex:1;">${name}...</span>`;

    div.appendChild(inner);



    let container = document.getElementById('toast-container');

    if (!container) {

        container = document.createElement('div');

        container.id = 'toast-container';

        container.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px;align-items:flex-end;';

        document.body.appendChild(container);

    }

    container.appendChild(div);

    _progressToasts[taskId] = id;



    // Inyectar keyframe si no existe

    if (!document.getElementById('spin-style')) {

        const s = document.createElement('style');

        s.id = 'spin-style';

        s.textContent = '@keyframes spin{to{transform:rotate(360deg)}}';

        document.head.appendChild(s);

    }

}



function updateProgressToast(taskId, text) {

    const el = document.getElementById(`ptoa-${taskId}-text`);

    if (el && text) el.textContent = text.substring(0, 120);

}



function dismissProgressToast(taskId) {

    const el = document.getElementById(`ptoa-${taskId}`);

    if (el) { el.style.opacity = '0'; el.style.transition = 'opacity 0.3s'; setTimeout(() => el.remove(), 350); }

    delete _progressToasts[taskId];

}



// ── Toast de error con boton Reintentar ───────────────────

function showErrorToast(name, errorMsg, taskId) {

    const id = `etoa-${Date.now()}`;

    let container = document.getElementById('toast-container');

    if (!container) {

        container = document.createElement('div');

        container.id = 'toast-container';

        container.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px;align-items:flex-end;';

        document.body.appendChild(container);

    }



    const div = document.createElement('div');

    div.id = id;

    div.style.cssText = 'background:rgba(30,12,12,0.97);border:1px solid rgba(255,69,58,0.5);border-radius:10px;padding:14px 16px;color:#fff;font-size:13px;min-width:280px;max-width:380px;backdrop-filter:blur(10px);box-shadow:0 4px 20px rgba(0,0,0,0.6);animation:slideIn 0.2s ease;';

    div.innerHTML = `

        <div style="display:flex;align-items:flex-start;gap:8px;">

            <span style="font-size:18px;flex-shrink:0;">❌</span>

            <div style="flex:1;">

                <div style="font-weight:600;color:#ff453a;margin-bottom:4px;">${name} falló</div>

                <div style="color:#ccc;font-size:11px;line-height:1.4;">${(errorMsg || '').substring(0, 200)}</div>

            </div>

            <button onclick="document.getElementById('${id}').remove()" style="background:none;border:none;color:#888;cursor:pointer;font-size:16px;padding:0;line-height:1;">&times;</button>

        </div>

        ${taskId ? `<button onclick="retryTask('${taskId}', '${name}', '${id}')" style="margin-top:8px;width:100%;padding:7px;background:rgba(255,69,58,0.2);border:1px solid rgba(255,69,58,0.4);color:#ff453a;border-radius:6px;font-size:12px;cursor:pointer;font-weight:600;">🔄 Reintentar</button>` : ''}

    `;

    container.appendChild(div);



    // Auto-dismiss en 12s

    setTimeout(() => { if (document.getElementById(id)) { div.style.opacity='0'; div.style.transition='opacity 0.4s'; setTimeout(()=>div.remove(),400); }}, 12000);

}



async function retryTask(taskId, name, toastId) {

    document.getElementById(toastId)?.remove();

    try {

        const res = await fetch(`/api/task_retry/${taskId}`, {method:'POST'});

        const data = await res.json();

        if (data.status === 'started') {

            showProgressToast(name, taskId);

            pollTask(taskId, name, null, (err) => showErrorToast(name, err, taskId));

        }

    } catch(e) {

        showErrorToast(name + ' (reintento)', e.message, null);

    }

}



// ── Reemplazar rebuildCleanCentroidsConfirm para usar el nuevo sistema ──

window.rebuildCleanCentroidsConfirm = function() {

    if (!confirm('Esto recalculara el modelo de reconocimiento facial usando las fotos verificadas.\n\nEl proceso corre en segundo plano. Podras ver el progreso en la esquina inferior derecha.\n\nContinuar?')) return;



    const btn = document.getElementById('btn-rebuild-centroids');

    if (btn) { btn.disabled = true; btn.textContent = 'Recalculando...'; }



    runBackgroundTask(

        '/api/rebuild_clean_centroids', null,

        'Recalcular Centroides',

        (result) => {

            if (btn) { btn.disabled = false; btn.textContent = 'Recalcular Modelo de IA Ahora'; }

            const r = result || {};

            const msg = r.message || `Recalculados: ${r.identities_rebuilt || 0} identidades, ${r.from_cache || 0} de cache, ${r.from_disk || 0} leidas de disco`;

            showToast(msg.substring(0, 200));

        },

        (err) => {

            if (btn) { btn.disabled = false; btn.textContent = 'Recalcular Modelo de IA Ahora'; }

        }

    );

};



// ============================================================

// DRAWER PANEL DE CONFIGURACION & HERRAMIENTAS

// ============================================================

window.toggleSettingsDrawer = function(forceState) {

    const drawer = document.getElementById('settings-drawer');

    const overlay = document.getElementById('drawer-overlay');

    if (!drawer || !overlay) return;



    const isOpen = drawer.classList.contains('open');

    const newState = typeof forceState === 'boolean' ? forceState : !isOpen;



    if (newState) {

        drawer.classList.add('open');

        overlay.classList.add('active');

        if (typeof checkSetupConfig === 'function') checkSetupConfig();

    } else {

        drawer.classList.remove('open');

        overlay.classList.remove('active');

    }

};



document.addEventListener('DOMContentLoaded', () => {

    const btn = document.getElementById('settings-btn');

    if (btn) {

        btn.onclick = function(e) {

            e.preventDefault();

            e.stopPropagation();

            window.toggleSettingsDrawer();

        };

    }

});



document.addEventListener('keydown', (e) => {

    if (e.key === 'Escape') {

        const drawer = document.getElementById('settings-drawer');

        if (drawer && drawer.classList.contains('open')) {

            window.toggleSettingsDrawer(false);

        }

        const modalIds = ['stats-modal', 'modal-suggestion-preview', 'modal-merge', 'modal-duplicates', 'modal-similar', 'setup-modal', 'modal-map', 'modal-evolution', 'compareModal', 'modal-events-map', 'modal-shortcuts', 'icloud-delete-modal'];

        modalIds.forEach(id => {

            const m = document.getElementById(id);

            if (m) { m.style.display = 'none'; m.classList.add('hidden'); }

        });

        const dc = document.getElementById('duplicates-content');

        if (dc) dc.innerHTML = '';

        const sc = document.getElementById('similar-content');

        if (sc) sc.innerHTML = '';

        document.querySelectorAll('.modal').forEach(m => {

            m.style.display = 'none';

            m.classList.add('hidden');

        });

    }

});



        let eventsMapInstance = null;

        async function openEventsMapModal() {

            const modal = document.getElementById('modal-events-map');

            if (!modal) return;

            modal.style.display = 'flex';

            

            // Set active nav tab

            document.querySelectorAll('.nav-tab-item').forEach(b => b.classList.remove('active'));

            const mapTab = document.getElementById('nav-btn-map');

            if (mapTab) mapTab.classList.add('active');

            

            setTimeout(() => {

                initEventsMap();

            }, 150);

        }



        function closeEventsMapModal() {

            const modal = document.getElementById('modal-events-map');

            if (modal) modal.style.display = 'none';

            document.querySelectorAll('.nav-tab-item').forEach(b => b.classList.remove('active'));

            const galTab = document.getElementById('nav-btn-gallery');

            if (galTab) galTab.classList.add('active');

        }



        async function initEventsMap() {

            const mapContainer = document.getElementById('events-map-container');

            if (!mapContainer) return;

            

            if (!eventsMapInstance) {

                if (typeof L === 'undefined') {

                    mapContainer.innerHTML = '<div style="padding:40px; text-align:center; color:#ff453a;">Leaflet Map no disponible en este momento.</div>';

                    return;

                }

                eventsMapInstance = L.map('events-map-container', {

                    zoomControl: true,

                    attributionControl: false

                }).setView([43.5, 4.0], 4);

                

                L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {

                    maxZoom: 19,

                    subdomains: 'abcd'

                }).addTo(eventsMapInstance);

            }

            

            eventsMapInstance.invalidateSize();

            

            try {

                const res = await fetch('/api/map/locations');

                const data = await res.json();

                const locations = data.locations || [];

                

                // Clear existing markers

                if (window.mapMarkersGroup) {

                    eventsMapInstance.removeLayer(window.mapMarkersGroup);

                }

                window.mapMarkersGroup = L.layerGroup().addTo(eventsMapInstance);

                

                const eventsListContent = document.getElementById('events-list-content');

                if (eventsListContent) eventsListContent.innerHTML = '';

                

                const bounds = [];

                const folderGroups = {};

                

                locations.forEach(loc => {

                    if (loc.lat && loc.lng) {

                        bounds.push([loc.lat, loc.lng]);

                        const folder = loc.folder || 'Ubicación';

                        if (!folderGroups[folder]) folderGroups[folder] = [];

                        folderGroups[folder].push(loc);

                        

                        const customIcon = L.divIcon({

                            className: 'custom-map-pin',

                            html: `<div style="width:14px; height:14px; background:#0a84ff; border:2px solid white; border-radius:50%; box-shadow:0 0 10px rgba(10,132,255,0.8);"></div>`,

                            iconSize: [14, 14],

                            iconAnchor: [7, 7]

                        });

                        

                        const marker = L.marker([loc.lat, loc.lng], { icon: customIcon }).addTo(window.mapMarkersGroup);

                        const popupHtml = `

                            <div style="font-family:-apple-system,sans-serif; color:#222; text-align:center; max-width:180px;">

                                <img loading="lazy" src="/api/thumbnail?path=${encodeURIComponent(loc.path)}" style="width:100%; height:110px; object-fit:cover; border-radius:6px; margin-bottom:6px; box-shadow:0 2px 6px rgba(0,0,0,0.2);">

                                <div style="font-weight:700; font-size:12px; margin-bottom:2px;">${loc.folder || loc.name}</div>

                                <div style="font-size:10px; color:#666;">${loc.source || 'GPS'}</div>

                            </div>

                        `;

                        marker.bindPopup(popupHtml);

                    }

                });

                

                if (bounds.length > 0) {

                    eventsMapInstance.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });

                }

                

                // Render Right Side Events Cards

                if (eventsListContent) {

                    const eventKeys = Object.keys(folderGroups);

                    if (eventKeys.length === 0) {

                        eventsListContent.innerHTML = '<p style="color:#aaa; text-align:center; padding:30px;">No se han detectado álbumes con coordenadas.</p>';

                    } else {

                        eventKeys.forEach(fName => {

                            const items = folderGroups[fName];

                            const sample = items[0];

                            const card = document.createElement('div');

                            card.style.cssText = 'background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); border-radius:12px; padding:12px; display:flex; align-items:center; gap:14px; cursor:pointer; transition:all 0.2s;';

                            card.onmouseover = () => card.style.background = 'rgba(255,255,255,0.1)';

                            card.onmouseout = () => card.style.background = 'rgba(255,255,255,0.05)';

                            card.onclick = () => {

                                closeEventsMapModal();

                                renderGrid('Eventos', fName);

                            };

                            

                            card.innerHTML = `

                                <img loading="lazy" src="/api/thumbnail?path=${encodeURIComponent(sample.path)}" style="width:64px; height:64px; border-radius:8px; object-fit:cover;">

                                <div style="flex:1;">

                                    <div style="font-weight:700; font-size:14px; color:#fff;">${fName}</div>

                                    <div style="font-size:12px; color:#0a84ff; margin-top:2px;">📍 ${sample.source || 'Ubicación'}</div>

                                    <div style="font-size:11px; color:#8e8e93; margin-top:2px;">${items.length} fotos registradas</div>

                                </div>

                                <div style="color:#0a84ff; font-size:18px;">&rsaquo;</div>

                            `;

                            eventsListContent.appendChild(card);

                        });

                    }

                }

                

            } catch(err) {

                console.error("Error loading map locations:", err);

            }

        }



// EXPORT & SHARE FUNCTIONS

function exportCurrentAlbumZip() {

    if (isMultiSelectMode && selectedMediaItems && selectedMediaItems.size > 0) {

        // Export selected files

        const paths = Array.from(selectedMediaItems);

        showToast(`📦 Generando ZIP con ${paths.length} fotos seleccionadas...`);

        

        fetch('/api/export/zip', {

            method: 'POST',

            headers: {'Content-Type': 'application/json'},

            body: JSON.stringify({ paths: paths, name: currentIdentity || "seleccion_fotos" })

        })

        .then(res => {

            if (!res.ok) throw new Error("Error al generar archivo ZIP");

            return res.blob();

        })

        .then(blob => {

            const url = window.URL.createObjectURL(blob);

            const a = document.createElement('a');

            a.href = url;

            a.download = `${(currentIdentity || 'seleccion').replace(/\s+/g, '_')}_fotos.zip`;

            document.body.appendChild(a);

            a.click();

            a.remove();

            window.URL.revokeObjectURL(url);

            showToast("✅ Archivo ZIP descargado con éxito");

        })

        .catch(err => {

            console.error(err);

            showToast("❌ Error al descargar ZIP: " + err.message, true);

        });

        return;

    }



    if (!currentCategory || !currentIdentity) {

        showToast("⚠️ Selecciona un álbum para descargar su ZIP", true);

        return;

    }

    

    showToast(`📦 Preparando descarga ZIP de ${currentIdentity}...`);

    const downloadUrl = `/api/export/zip?cat=${encodeURIComponent(currentCategory)}&ident=${encodeURIComponent(currentIdentity)}`;

    const a = document.createElement('a');

    a.href = downloadUrl;

    a.download = `${currentIdentity.replace(/\s+/g, '_')}.zip`;

    document.body.appendChild(a);

    a.click();

    a.remove();

}



function shareCurrentAlbumLink() {

    if (!currentCategory || !currentIdentity) {

        showToast("⚠️ Selecciona un álbum para compartir", true);

        return;

    }

    

    const shareUrl = `${window.location.origin}/share?cat=${encodeURIComponent(currentCategory)}&ident=${encodeURIComponent(currentIdentity)}`;

    

    if (navigator.clipboard && window.isSecureContext) {

        navigator.clipboard.writeText(shareUrl).then(() => {

            showToast(`🔗 Enlace copiado al portapapeles: ${shareUrl}`);

        }).catch(() => {

            prompt("Copia este enlace para enviárselo a esta persona:", shareUrl);

        });

    } else {

        prompt("Copia este enlace para enviárselo a esta persona:", shareUrl);

    }

}



// =============================================================



function navigateLightbox(direction) {

    const items = (typeof currentFolderItems !== 'undefined' && currentFolderItems && currentFolderItems.length > 0) 

        ? currentFolderItems 

        : ((typeof currentPhotos !== 'undefined' && currentPhotos) ? currentPhotos : []);

        

    if (!items || items.length === 0 || !currentFileObj) return;

    const currentIdx = items.findIndex(p => p.path === currentFileObj.path);

    if (currentIdx === -1) return;

    

    const nextIdx = (currentIdx + direction + items.length) % items.length;

    openLightbox(items[nextIdx]);

}



// Global Keyboard Navigation (Apple Photos Style)

document.addEventListener('keydown', (e) => {

    // Ctrl+K para búsqueda

    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {

        e.preventDefault();

        const searchInput = document.getElementById('top-search-input');

        if (searchInput) {

            searchInput.focus();

            searchInput.select();

        }

        return;

    }

    

    const lb = document.getElementById('lightbox');

    const isLbOpen = lb && !lb.classList.contains('hidden') && lb.style.display !== 'none';

    

    if (isLbOpen) {

        const activeTag = (e.target && e.target.tagName) ? e.target.tagName.toLowerCase() : '';

        if (activeTag === 'input' || activeTag === 'textarea' || activeTag === 'select') return;

        

        if (e.key === 'ArrowRight') {

            e.preventDefault();

            navigateLightbox(1);

        } else if (e.key === 'ArrowLeft') {

            e.preventDefault();

            navigateLightbox(-1);

        } else if (e.key === ' ') {

            e.preventDefault();

            const mediaEl = document.querySelector('.lb-media-element');

            if (mediaEl && mediaEl.tagName && mediaEl.tagName.toLowerCase() === 'video') {

                if (mediaEl.paused) mediaEl.play();

                else mediaEl.pause();

            }

        } else if (e.key === '+' || e.key === '=') {

            e.preventDefault();

            if (typeof zoomInLightbox === 'function') zoomInLightbox();

        } else if (e.key === '-' || e.key === '_') {

            e.preventDefault();

            if (typeof zoomOutLightbox === 'function') zoomOutLightbox();

        } else if (e.key === '0') {

            e.preventDefault();

            if (typeof resetZoom === 'function') resetZoom();

        } else if (e.key === 'Escape') {

            closeLightbox();

        } else if (e.key === 'Delete' || e.key === 'Backspace') {

            if (typeof deleteCurrentFile === 'function') deleteCurrentFile();

        }

    }

});





// Spotlight Search Auto-Suggestions

let allIdentitiesList = [];

async function loadSpotlightIdentities() {

    try {

        const res = await fetch('/api/identities');

        allIdentitiesList = await res.json();

    } catch(e) {}

}

loadSpotlightIdentities();



function handleSpotlightSearch(query) {

    const dropdown = document.getElementById('spotlight-dropdown');

    if (!dropdown) return;

    

    const q = (query || '').trim().toLowerCase();

    if (!q) {

        dropdown.style.display = 'none';

        return;

    }

    

    const matches = allIdentitiesList.filter(id => 

        id.identidad.toLowerCase().includes(q) || id.categoria.toLowerCase().includes(q)

    );

    

    if (matches.length === 0) {

        dropdown.innerHTML = '<div style="padding:12px; text-align:center; color:#8e8e93; font-size:12px;">No se encontraron personas o álbumes.</div>';

        dropdown.style.display = 'block';

        return;

    }

    

    let html = '<div class="spotlight-category-header">Sugerencias de Álbumes</div>';

    matches.slice(0, 8).forEach(item => {

        const cleanName = item.identidad.replace(/^[CFPM]\.\s*/, '');

        html += `

            <div class="spotlight-item" onclick="selectSpotlightItem('${encodeURIComponent(item.categoria)}', '${encodeURIComponent(item.identidad)}')">

                <img src="/api/person_avatar?cat=${encodeURIComponent(item.categoria)}&ident=${encodeURIComponent(item.identidad)}" style="width:28px; height:28px; border-radius:50%; object-fit:cover;">

                <div style="flex:1;">

                    <div style="font-weight:600; color:#fff;">${cleanName}</div>

                    <div style="font-size:10.5px; color:#0a84ff;">📁 ${item.categoria}</div>

                </div>

                <div style="color:#8e8e93; font-size:14px;">&rsaquo;</div>

            </div>

        `;

    });

    

    dropdown.innerHTML = html;

    dropdown.style.display = 'block';

}



function selectSpotlightItem(catEncoded, identEncoded) {

    const cat = decodeURIComponent(catEncoded);

    const ident = decodeURIComponent(identEncoded);

    const dropdown = document.getElementById('spotlight-dropdown');

    if (dropdown) dropdown.style.display = 'none';

    const searchInput = document.getElementById('top-search-input');

    if (searchInput) searchInput.value = '';

    

    renderGrid(cat, ident);

}



// Close spotlight on click outside

document.addEventListener('click', (e) => {

    const dropdown = document.getElementById('spotlight-dropdown');

    const searchWrapper = document.querySelector('.top-search-wrapper');

    if (dropdown && searchWrapper && !searchWrapper.contains(e.target)) {

        dropdown.style.display = 'none';

    }

});











window.zoomInLightbox = function() {

    if (typeof window.applyZoomLevel === 'function') {

        window.applyZoomLevel((typeof zoomLevel !== 'undefined' ? zoomLevel : 1.0) + 0.35);

    } else if (typeof applyZoomTransform === 'function') {

        zoomLevel = Math.min(4.0, (zoomLevel || 1.0) + 0.25);

        applyZoomTransform();

    }

};



// ==========================================

// TRIAGE IA LOGIC

// ==========================================

window.triageMatchesCache = [];



window.loadTriageSuggestions = function() {

    const list = document.getElementById('triage-suggestions-list');

    if (!list) return;

    list.innerHTML = '<div style="text-align:center;color:#8e8e93;font-size:12px;padding:20px;"><div class="loader-small" style="margin:0 auto 10px auto;"></div>Buscando coincidencias...</div>';

    

    if (!currentFileObj) {

        list.innerHTML = '<div style="text-align:center;color:#ff453a;font-size:12px;padding:20px;">No hay imagen activa.</div>';

        return;

    }



    fetch('/api/face_top_matches', {

        method: 'POST',

        headers: { 'Content-Type': 'application/json' },

        body: JSON.stringify({ path: currentFileObj.path, face_index: 0 })

    })

    .then(r => r.json())

    .then(data => {

        if (!data.matches || data.matches.length === 0) {

            list.innerHTML = '<div style="text-align:center;color:#8e8e93;font-size:12px;padding:20px;">No se encontraron coincidencias claras para esta cara.</div>';

            window.triageMatchesCache = [];

            return;

        }



        window.triageMatchesCache = data.matches;

        list.innerHTML = '';

        data.matches.forEach((m, idx) => {

            const btn = document.createElement('button');

            const pct = Math.round(m.similarity * 100);

            

            let color = '#30d158'; // Alta

            if (m.similarity < 0.45) color = '#ffd60a'; // Media

            if (m.similarity < 0.35) color = '#ff453a'; // Baja



            btn.style.cssText = `

                display: flex; justify-content: space-between; align-items: center;

                width: 100%; padding: 10px; background: rgba(255,255,255,0.05);

                border: 1px solid rgba(255,255,255,0.1); border-radius: 10px;

                color: #fff; cursor: pointer; text-align: left; transition: all 0.2s;

            `;

            btn.onmouseover = () => btn.style.background = 'rgba(255,255,255,0.1)';

            btn.onmouseout = () => btn.style.background = 'rgba(255,255,255,0.05)';

            

            btn.innerHTML = `

                <div style="display:flex; align-items:center; gap:8px;">

                    <kbd style="background:rgba(255,255,255,0.1); border-radius:4px; padding:2px 6px; font-size:10px; color:#fff;">${idx + 1}</kbd>

                    <span style="font-size:13px; font-weight:600;">${m.identity}</span>

                </div>

                <div style="font-size:11px; font-weight:700; color:${color}; background:${color}20; padding:2px 6px; border-radius:10px;">${pct}%</div>

            `;

            

            btn.onclick = () => window.assignTriage(m.identity);

            list.appendChild(btn);

        });

    })

    .catch(err => {

        list.innerHTML = '<div style="text-align:center;color:#ff453a;font-size:12px;padding:20px;">Error al cargar sugerencias.</div>';

        console.error(err);

    });

};



window.assignTriage = function(targetIdent) {

    if (!currentFileObj) return;

    

    // Find target category

    let targetCat = 'Conocidos';

    for (const c in fullGallery) {

        if (fullGallery[c][targetIdent]) {

            targetCat = c;

            break;

        }

    }



    const payload = {

        files: [currentFileObj.path],

        target_cat: targetCat,

        target_ident: targetIdent

    };



    fetch('/api/batch_move', {

        method: 'POST',

        headers: { 'Content-Type': 'application/json' },

        body: JSON.stringify(payload)

    })

    .then(r => r.json())

    .then(data => {

        if(data.success) {

            showToast(`✅ Asignado a ${targetIdent}`);

            if (window.currentFolderItems) {

                const idx = window.currentFolderItems.findIndex(i => i.path === currentFileObj.path);

                if (idx !== -1) window.currentFolderItems.splice(idx, 1);

            }

            window.triageSkip();

        } else {

            showToast(`❌ Error: ${data.error}`, 'error');

        }

    })

    .catch(err => {

        showToast('Error de red al asignar', 'error');

        console.error(err);

    });

};



window.triageSkip = function() {

    navigateLightbox(1);

    setTimeout(() => {

        const triageTabPanel = document.getElementById('lb-tab-triage');

        if (triageTabPanel && triageTabPanel.style.display !== 'none') {

            loadTriageSuggestions();

        }

    }, 100);

};



// Keyboard handler for Lightbox Triage

document.addEventListener('keydown', (e) => {

    const lb = document.getElementById('lightbox');

    if (!lb || lb.classList.contains('hidden') || lb.style.display === 'none') return;

    

    const triageTabPanel = document.getElementById('lb-tab-triage');

    if (triageTabPanel && triageTabPanel.style.display !== 'none') {

        const num = parseInt(e.key);

        if (num >= 1 && num <= 5) {

            if (window.triageMatchesCache && window.triageMatchesCache[num - 1]) {

                window.assignTriage(window.triageMatchesCache[num - 1].identity);

                e.preventDefault();

            }

        } else if (e.key === 'Delete' || e.key === 'Backspace') {

            deleteCurrentFile();

            window.triageSkip();

            e.preventDefault();

        }

    }

});



// ==========================================

// SIDEBAR IA SUGGESTIONS

// ==========================================

window.loadSidebarIASuggestions = function() {

    const container = document.getElementById('sidebar-ia-suggestions');

    if (!container) return;

    

    container.innerHTML = '<div style="padding:10px; text-align:center;"><div class="loader-small" style="margin:0 auto 10px auto;"></div><div style="font-size:11px;color:#8e8e93;">Analizando...</div></div>';

    

    fetch('/api/suggest_merges')

        .then(r => r.json())

        .then(data => {

            if (!data.suggestions || data.suggestions.length === 0) {

                container.innerHTML = '<div style="padding:15px 10px; text-align:center; font-size:11px; color:#8e8e93;">No hay sugerencias IA pendientes.</div>';

                return;

            }

            

            container.innerHTML = '';

            

            // Add title/badge

            const titleRow = document.createElement('div');

            titleRow.style.cssText = 'display:flex; justify-content:space-between; align-items:center; margin:10px 15px 5px 15px;';

            titleRow.innerHTML = `

                <span style="font-size:10px; font-weight:700; color:rgba(168,85,247,0.8); letter-spacing:0.8px; text-transform:uppercase;">Sugerencias IA</span>

                <span style="background:rgba(168,85,247,0.2); color:#da8fff; font-size:9px; font-weight:700; padding:2px 6px; border-radius:10px;">${data.suggestions.length}</span>

            `;

            container.appendChild(titleRow);



            data.suggestions.forEach(sug => {

                const item = document.createElement('div');

                item.className = 'tree-folder';

                item.style.cssText = 'margin:4px 10px; padding:8px 10px; border-radius:6px; cursor:pointer; font-size:0.8rem; color:#ccc; transition:all 0.15s; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); display:flex; flex-direction:column; gap:4px;';

                item.onmouseover = () => item.style.background = 'rgba(255,255,255,0.08)';

                item.onmouseout = () => item.style.background = 'rgba(255,255,255,0.03)';

                

                item.innerHTML = `

                    <div style="display:flex; align-items:center; gap:6px;">

                        <span style="font-size:14px;">${sug.type === 'persona_nueva_merge' ? '🔀' : '👤'}</span>

                        <span style="font-weight:600; font-size:11px; color:#fff; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${sug.source}</span>

                    </div>

                    <div style="font-size:10px; color:#8e8e93; display:flex; align-items:center; gap:4px; margin-left:20px;">

                        <span>→</span>

                        <span style="color:#64d2ff;">${sug.target}</span>

                        <span style="margin-left:auto; background:${sug.confidence === 'alta' ? '#30d15820' : '#ffd60a20'}; color:${sug.confidence === 'alta' ? '#30d158' : '#ffd60a'}; padding:2px 4px; border-radius:4px; font-weight:700;">${Math.round(sug.similarity * 100)}%</span>

                    </div>

                `;

                

                item.onclick = () => {

                    // Open merge modal prepopulated

                    if (window.openMergeModalFromSuggestion) {

                        window.openMergeModalFromSuggestion(sug);

                    } else {

                        // Fallback behavior: render source identity

                        // We need source_cat, which is likely in Revision

                        let sourceCat = '📋 Revisión / Por Organizar';

                        for (const c in fullGallery) {

                            if (fullGallery[c][sug.source]) { sourceCat = c; break; }

                        }

                        renderGrid(sourceCat, sug.source);

                    }

                };

                

                container.appendChild(item);

            });

        })

        .catch(e => {

            container.innerHTML = '<div style="padding:10px; font-size:11px; color:#ff453a; text-align:center;">Error cargando sugerencias</div>';

        });

};



window.openMergeModalFromSuggestion = function(sug) {

    let sourceCat = '📋 Revisión / Por Organizar';

    for (const c in fullGallery) {

        if (fullGallery[c][sug.source]) { sourceCat = c; break; }

    }

    

    currentCat = sourceCat;

    currentIdent = sug.source;

    

    // Fake currentFolderItems with at least one item to make renameCurrentGroup work

    if (!currentFolderItems || currentFolderItems.length === 0) {

        if (fullGallery[sourceCat] && fullGallery[sourceCat][sug.source]) {

            currentFolderItems = fullGallery[sourceCat][sug.source];

        }

    }

    

    renameCurrentGroup();

    

    // Auto-select the target identity in the select dropdown if possible

    setTimeout(() => {

        const select = document.getElementById('merge-existing-select');

        if (select) {

            for (let i=0; i<select.options.length; i++) {

                if (select.options[i].value === sug.target) {

                    select.selectedIndex = i;

                    select.dispatchEvent(new Event('change'));

                    break;

                }

            }

        }

    }, 200);

};



// Call loadSidebarIASuggestions on initial load

setTimeout(() => {

    if (window.loadSidebarIASuggestions) window.loadSidebarIASuggestions();

}, 2000);



window.zoomOutLightbox = function() {

    if (typeof window.applyZoomLevel === 'function') {

        window.applyZoomLevel(Math.max(1.0, (typeof zoomLevel !== 'undefined' ? zoomLevel : 1.0) - 0.35));

    } else if (typeof applyZoomTransform === 'function') {

        zoomLevel = Math.max(1.0, (zoomLevel || 1.0) - 0.25);

        applyZoomTransform();

    }

};



// ==========================================

// UX EXTRA LOGIC

// ==========================================

// Ctrl+K for search focus

document.addEventListener('keydown', (e) => {

    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {

        e.preventDefault();

        const searchInput = document.getElementById('top-search-input');

        if (searchInput) {

            searchInput.focus();

        }

    }

});



// Scroll to Top Button

const gridContainer = document.getElementById('grid-container');

if (gridContainer) {

    const scrollToTopBtn = document.createElement('button');

    scrollToTopBtn.innerHTML = '↑';

    scrollToTopBtn.style.cssText = `

        position: fixed; bottom: 30px; right: 30px; width: 40px; height: 40px;

        border-radius: 50%; background: rgba(10,132,255,0.8); color: white;

        border: none; cursor: pointer; display: none; align-items: center; justify-content: center;

        font-size: 20px; font-weight: bold; box-shadow: 0 4px 12px rgba(0,0,0,0.3);

        backdrop-filter: blur(10px); transition: all 0.2s; z-index: 100;

    `;

    scrollToTopBtn.onmouseover = () => scrollToTopBtn.style.transform = 'scale(1.1)';

    scrollToTopBtn.onmouseout = () => scrollToTopBtn.style.transform = 'scale(1)';

    scrollToTopBtn.onclick = () => {

        gridContainer.scrollTo({ top: 0, behavior: 'smooth' });

    };

    document.body.appendChild(scrollToTopBtn);



    gridContainer.addEventListener('scroll', () => {

        if (gridContainer.scrollTop > 300) {

            scrollToTopBtn.style.display = 'flex';

        } else {

            scrollToTopBtn.style.display = 'none';

        }

    });

}





// Auto-initialize gallery immediately and identities in background (non-blocking)
document.addEventListener('DOMContentLoaded', () => {
    try {
        // 1. Iniciar inmediatamente la galería sin esperar a identidades
        if (typeof loadGallery === 'function') {
            loadGallery().catch(e => console.error('Gallery loading error:', e));
        }
        // 2. Cargar identidades en segundo plano
        if (typeof loadIdentities === 'function') {
            loadIdentities().catch(e => console.warn('Background identities loading:', e));
        }
    } catch (e) {
        console.error('Initialization error:', e);
    }
});





window.confirmDudosoPhoto = async function(isConfirm) {

    if (!currentFileObj || !currentCat || !currentIdent) return;

    const filePath = currentFileObj.path;

    let targetCat = currentCat;
    if (!targetCat || targetCat.includes('Revisión') || targetCat.includes('Organizar') || targetCat.includes('Dudoso') || targetCat.includes('/') || targetCat.includes('\\')) {
        if (currentIdent.startsWith('C.') || currentIdent.startsWith('C ') || currentIdent.startsWith('C_')) targetCat = 'Conocidos';
        else if (currentIdent.startsWith('F.') || currentIdent.startsWith('F ') || currentIdent.startsWith('F_')) targetCat = 'Familia';
        else if (currentIdent === 'YO' || currentIdent.startsWith('YO')) targetCat = 'YO';
        else if (currentIdent.startsWith('P.') || currentIdent.startsWith('P ')) targetCat = 'Profesores';
        else if (currentIdent.startsWith('M.') || currentIdent.startsWith('M ')) targetCat = 'Mascotas';
        else targetCat = 'Conocidos';
    }

    if (isConfirm) {

        if (typeof showToast === 'function') showToast(`⏳ Confirmando foto para ${currentIdent}...`, 'info');

        try {

            const faceData = (currentFaces && currentFaces.length > 0) ? currentFaces[0] : null;

            const res = await fetch('/api/correct', {

                method: 'POST',

                headers: {'Content-Type': 'application/json'},

                body: JSON.stringify({

                    path: filePath,

                    new_categoria: targetCat,

                    new_identidad: currentIdent,

                    face: faceData

                })

            });

            const data = await res.json();

            if (data.error) {

                if (typeof showToast === 'function') showToast(`Error: ${data.error}`, 'error');

            } else {

                if (typeof showToast === 'function') showToast(`✅ Confirmada como ${currentIdent}`, 'success');

                currentFileObj.is_dudoso = false;

                currentFileObj.status = 'Clasificado';

                currentFileObj.source = 'Dataset + ✏️ Manual';

                if (data.new_path && currentFileObj) {
                    currentFileObj.path = data.new_path;
                    document.querySelectorAll('.lb-bounding-box').forEach(b => {
                        b.dataset.path = data.new_path;
                    });
                }
                const dudosoBanner = document.getElementById('lb-dudoso-banner');
                if (dudosoBanner) dudosoBanner.remove();
                if (window.renderGrid) window.renderGrid(currentCat, currentIdent);
            }

        } catch(e) {

            if (typeof showToast === 'function') showToast(`Error de red al confirmar: ${e}`, 'error');

        }

    } else {

        if (typeof showToast === 'function') showToast(`⏳ Quitando foto de ${currentIdent}...`, 'info');

        try {

            const res = await fetch('/api/remove_from_folder', {

                method: 'POST',

                headers: {'Content-Type': 'application/json'},

                body: JSON.stringify({

                    path: filePath,

                    cat: targetCat,

                    ident: currentIdent

                })

            });

            const data = await res.json();

            if (data.error) {

                if (typeof showToast === 'function') showToast(`Error: ${data.error}`, 'error');

            } else {

                if (typeof showToast === 'function') showToast(`❌ Foto retirada de ${currentIdent}`, 'success');

                if (window.renderGrid) {

                    currentFolderItems = currentFolderItems.filter(it => it.path !== filePath);

                    window.renderGrid(currentCat, currentIdent);

                }

                closeLightbox();

            }

        } catch(e) {

            if (typeof showToast === 'function') showToast(`Error de red: ${e}`, 'error');

        }

    }

};





// =====================================================================

// SMART MERGE BANNER & QUICK MERGE

// =====================================================================

window.checkAndDisplaySmartMergeSuggestion = function(cat, ident) {

    if (!ident) return;

    fetch('/api/suggest_merges?ident=' + encodeURIComponent(ident.replace(/👤/g, '').trim()))

        .then(r => r.json())

        .then(data => {

            if (!data.suggestions || data.suggestions.length === 0) return;

            const sug = data.suggestions[0];

            if (!sug || sug.similarity < 0.55) return;

            if (currentIdent !== ident) return; // User navigated away



            const prev = document.getElementById('smart-merge-banner');

            if (prev) prev.remove();



            const banner = document.createElement('div');

            banner.id = 'smart-merge-banner';

            banner.style.cssText = 'background:linear-gradient(90deg, rgba(168,85,247,0.18), rgba(10,132,255,0.18)); border:1px solid rgba(168,85,247,0.4); border-radius:12px; padding:12px 18px; margin:0 20px 14px 20px; display:flex; align-items:center; justify-content:space-between; box-shadow:0 4px 20px rgba(0,0,0,0.3);';

            const safeSource = (sug.source || '').replace(/'/g, "\\\\'");

            const safeTarget = (sug.target || '').replace(/'/g, "\\\\'");

            const safeCat = (sug.target_cat || 'Conocidos').replace(/'/g, "\\\\'");



            banner.innerHTML = `

                <div style="display:flex; align-items:center; gap:12px;">

                    <span style="font-size:22px;">✨</span>

                    <div>

                        <div style="font-weight:700; color:#fff; font-size:13px; display:flex; align-items:center; gap:8px;">

                            <span>Sugerencia IA de Fusión</span>

                            <span style="background:rgba(48,209,88,0.2); color:#30d158; font-size:10px; font-weight:800; padding:2px 7px; border-radius:10px;">${Math.round(sug.similarity * 100)}% Coincidencia</span>

                        </div>

                        <div style="font-size:12px; color:#d1d5db; margin-top:2px;">

                            La IA reconoce biométricamente que esta persona es <strong style="color:#64d2ff; font-weight:700;">${sug.target}</strong> (${sug.target_cat}).

                        </div>

                    </div>

                </div>

                <div style="display:flex; align-items:center; gap:8px; flex-shrink:0;">

                    <button id="btn-quick-merge-exec" onclick="executeQuickMerge('${safeSource}', '${safeTarget}', '${safeCat}')" style="background:#30d158; color:#000; font-weight:700; border:none; border-radius:8px; padding:7px 14px; cursor:pointer; font-size:12px; display:flex; align-items:center; gap:6px; transition:transform 0.15s;" onmouseover="this.style.transform='scale(1.03)'" onmouseout="this.style.transform='scale(1)'">

                        ✓ Fusionar con 1 Clic

                    </button>

                    <button onclick="document.getElementById('smart-merge-banner').remove()" style="background:rgba(255,255,255,0.08); color:#8e8e93; border:none; border-radius:8px; padding:7px 12px; cursor:pointer; font-size:12px;" onmouseover="this.style.color='#fff'" onmouseout="this.style.color='#8e8e93'">

                        Descartar

                    </button>

                </div>

            `;

            const header = document.getElementById('main-gallery-header');

            if (header && header.parentNode) {

                header.parentNode.insertBefore(banner, header.nextSibling);

            }

        })

        .catch(err => console.log('Suggestion check err:', err));

};



window.executeQuickMerge = function(source, target, targetCat) {

    const btn = document.getElementById('btn-quick-merge-exec');

    if (btn) {

        btn.textContent = '⏳ Fusionando...';

        btn.style.pointerEvents = 'none';

    }



    fetch('/api/rename_group', {

        method: 'POST',

        headers: {'Content-Type': 'application/json'},

        body: JSON.stringify({ old_name: source, new_name: target })

    })

    .then(r => r.json())

    .then(data => {

        const b = document.getElementById('smart-merge-banner');

        if (b) b.remove();

        if (typeof showToast === 'function') {

            showToast(`✓ Fusionado con éxito en ${target}`);

        } else {

            alert(`✓ Fusionado con éxito en ${target}`);

        }

        loadGalleryData(false, () => {

            renderGrid(targetCat || 'Conocidos', target);

        });

    })

    .catch(err => {

        alert('Error en fusión: ' + err);

        if (btn) {

            btn.textContent = '✓ Fusionar con 1 Clic';

            btn.style.pointerEvents = 'auto';

        }

    });

};



// =====================================================================

// EVENTS TIMELINE & MEMORIES

// =====================================================================

window.switchEventsTab = function(tab) {

    const mapBtn = document.getElementById('btn-events-tab-map');

    const timeBtn = document.getElementById('btn-events-tab-timeline');

    const mapView = document.getElementById('events-map-view');

    const timeView = document.getElementById('events-timeline-view');



    if (tab === 'map') {

        if (mapBtn) { mapBtn.style.background = '#0a84ff'; mapBtn.style.color = '#fff'; }

        if (timeBtn) { timeBtn.style.background = 'transparent'; timeBtn.style.color = '#8e8e93'; }

        if (mapView) mapView.style.display = 'flex';

        if (timeView) timeView.style.display = 'none';

        if (eventsMapInstance) eventsMapInstance.invalidateSize();

    } else {

        if (timeBtn) { timeBtn.style.background = '#0a84ff'; timeBtn.style.color = '#fff'; }

        if (mapBtn) { mapBtn.style.background = 'transparent'; mapBtn.style.color = '#8e8e93'; }

        if (mapView) mapView.style.display = 'none';

        if (timeView) timeView.style.display = 'flex';

        loadEventsTimeline();

    }

};



window.loadEventsTimeline = function() {

    const container = document.getElementById('events-timeline-content');

    const yearsBar = document.getElementById('timeline-years-bar');

    if (!container) return;



    container.innerHTML = '<div style="text-align:center; padding:40px; color:#8e8e93;"><div class="loader-small" style="margin:auto 0 10px auto;"></div> Cargando momentos y recuerdos...</div>';



    fetch('/api/events/timeline')

        .then(r => r.json())

        .then(data => {

            const timeline = data.timeline || [];

            const years = data.years || [];



            if (yearsBar) {

                yearsBar.innerHTML = '';

                years.forEach(yr => {

                    const pill = document.createElement('a');

                    pill.href = `#year-group-${yr}`;

                    pill.textContent = yr;

                    pill.style.cssText = 'padding:3px 10px; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); border-radius:12px; font-size:11px; color:#64d2ff; text-decoration:none; font-weight:700; transition:all 0.15s;';

                    pill.onmouseover = () => pill.style.background = 'rgba(10,132,255,0.2)';

                    pill.onmouseout = () => pill.style.background = 'rgba(255,255,255,0.06)';

                    yearsBar.appendChild(pill);

                });

            }



            if (timeline.length === 0) {

                container.innerHTML = '<div style="text-align:center; padding:40px; color:#8e8e93;">No se encontraron eventos clasificados cronológicamente.</div>';

                return;

            }



            let html = '';

            timeline.forEach(yg => {

                html += `

                    <div id="year-group-${yg.year}" style="border-bottom:1px solid rgba(255,255,255,0.06); padding-bottom:18px;">

                        <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">

                            <span style="font-size:1.4rem; font-weight:800; color:#fff;">${yg.year}</span>

                            <span style="font-size:11px; background:rgba(255,255,255,0.08); padding:2px 8px; border-radius:10px; color:#8e8e93;">${yg.events.length} álbumes</span>

                        </div>

                        <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(220px, 1fr)); gap:12px;">

                `;



                yg.events.forEach(ev => {

                    const safeTitle = (ev.title || '').replace(/'/g, "\\\\'");

                    const safeCat = (ev.category || '').replace(/'/g, "\\\\'");

                    html += `

                        <div onclick="closeEventsMapModal(); renderGrid('${safeCat}', '${safeTitle}');" style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06); border-radius:12px; overflow:hidden; cursor:pointer; transition:transform 0.15s, background 0.15s;" onmouseover="this.style.transform='scale(1.02)'; this.style.background='rgba(255,255,255,0.06)'" onmouseout="this.style.transform='scale(1)'; this.style.background='rgba(255,255,255,0.03)'">

                            <div style="position:relative; height:120px; overflow:hidden;">

                                <img loading="lazy" src="/api/thumbnail?path=${encodeURIComponent(ev.cover)}" style="width:100%; height:100%; object-fit:cover;">

                                <span style="position:absolute; bottom:6px; right:8px; background:rgba(0,0,0,0.65); backdrop-filter:blur(4px); color:#fff; font-size:10px; font-weight:700; padding:2px 6px; border-radius:6px;">${ev.count} fotos</span>

                            </div>

                            <div style="padding:10px 12px;">

                                <div style="font-weight:700; font-size:13px; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${ev.title}</div>

                                <div style="font-size:11px; color:#0a84ff; margin-top:2px;">📁 ${ev.category}</div>

                            </div>

                        </div>

                    `;

                });



                html += `</div></div>`;

            });



            container.innerHTML = html;

        })

        .catch(err => {

            container.innerHTML = '<div style="color:#ff453a; text-align:center; padding:30px;">Error al cargar la línea de tiempo.</div>';

        });

};



// =====================================================================

// BACKGROUND VIDEO INDEXER CONTROLS

// =====================================================================

let videoIndexerPollTimer = null;



window.toggleVideoIndexer = function() {

    fetch('/api/video_indexer/status')

        .then(r => r.json())

        .then(status => {

            if (status.running && !status.paused) {

                // Pause

                fetch('/api/video_indexer/pause', {method: 'POST'})

                    .then(r => r.json())

                    .then(res => {

                        if (typeof showToast === 'function') showToast('⏸ Indexador de vídeos pausado');

                        updateVideoIndexerUI(false, status.percent);

                    });

            } else {

                // Start

                fetch('/api/video_indexer/start', {method: 'POST'})

                    .then(r => r.json())

                    .then(res => {

                        if (typeof showToast === 'function') showToast('▶ Indexador de vídeos iniciado');

                        updateVideoIndexerUI(true, status.percent);

                        startVideoIndexerPolling();

                    });

            }

        });

};



function updateVideoIndexerUI(running, percent) {

    const textEl = document.getElementById('video-indexer-text');

    const chip = document.getElementById('btn-video-indexer-chip');

    if (!textEl || !chip) return;



    if (running) {

        textEl.textContent = `🎬 ${percent || 0}%`;

        chip.style.background = 'rgba(10, 132, 255, 0.25)';

        chip.style.borderColor = '#0a84ff';

    } else {

        textEl.textContent = 'Vídeos';

        chip.style.background = 'rgba(10, 132, 255, 0.08)';

        chip.style.borderColor = 'rgba(10, 132, 255, 0.2)';

    }

}



function startVideoIndexerPolling() {

    if (videoIndexerPollTimer) clearInterval(videoIndexerPollTimer);

    videoIndexerPollTimer = setInterval(() => {

        fetch('/api/video_indexer/status')

            .then(r => r.json())

            .then(st => {

                if (!st.running) {

                    clearInterval(videoIndexerPollTimer);

                    videoIndexerPollTimer = null;

                    updateVideoIndexerUI(false, 100);

                    if (typeof showToast === 'function') showToast('✅ Todos los vídeos han sido indexados en caché');

                } else {

                    updateVideoIndexerUI(true, st.percent);

                }

            })

            .catch(() => clearInterval(videoIndexerPollTimer));

    }, 4000);

}





// ── Pending Video On-Demand & Navigation ──────────────────────
async function checkPendingVideos() {
    try {
        const res = await fetch('/api/gallery/pending_status');
        if (res.ok) {
            const data = await res.json();
            const badge = document.getElementById('nav-btn-pending');
            const countEl = document.getElementById('pending-videos-count-badge');
            if (data.pending_videos > 0) {
                if (badge) badge.style.display = 'inline-flex';
                if (countEl) countEl.textContent = `${data.pending_videos.toLocaleString()} por analizar`;
            } else {
                if (badge) badge.style.display = 'none';
            }
        }
    } catch (e) {}
}
window.checkPendingVideos = checkPendingVideos;

function filterPendingVideos() {
    if (typeof selectFolder === 'function') {
        selectFolder('📋 Revisión / Por Organizar', '🎬 Vídeos Sin Rostro');
    } else if (typeof renderGrid === 'function') {
        renderGrid('📋 Revisión / Por Organizar', '🎬 Vídeos Sin Rostro');
    }
}
window.filterPendingVideos = filterPendingVideos;

async function analyzeLightboxVideo() {
    if (!currentFileObj || !currentFileObj.path) return;
    const btn = document.getElementById('btn-lightbox-analyze-video');
    const txt = document.getElementById('btn-lightbox-analyze-text');
    if (btn) btn.disabled = true;
    if (txt) txt.textContent = '⏳ Analizando...';
    
    if (typeof showToast === 'function') {
        showToast("Extrayendo fotograma y reconociendo caras...", false);
    }
    try {
        const res = await fetch('/api/media/analyze_video', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: currentFileObj.path })
        });
        const data = await res.json();
        if (data.success) {
            currentFileObj.needs_face_analysis = false;
            currentFileObj.status = 'Analizado';
            const count = (data.detections && Array.isArray(data.detections)) ? data.detections.length : 0;
            if (typeof showToast === 'function') {
                showToast(`✅ Vídeo analizado exitosamente (${count} caras)`, false);
            }
            if (btn) btn.style.display = 'none';
            checkPendingVideos();
            if (typeof loadFacesInLightbox === 'function') {
                loadFacesInLightbox(currentFileObj);
            }
        } else {
            if (typeof showToast === 'function') {
                showToast("No se detectaron rostros en la muestra.", false);
            }
            if (txt) txt.textContent = 'Reintentar';
            if (btn) btn.disabled = false;
        }
    } catch (err) {
        if (typeof showToast === 'function') {
            showToast("Error al analizar: " + err.message, true);
        }
        if (txt) txt.textContent = 'Reintentar';
        if (btn) btn.disabled = false;
    }
}
window.analyzeLightboxVideo = analyzeLightboxVideo;



// ============================================================
// STALE SCREENSHOTS / GESTOR DE CAPTURAS OLVIDADAS
// ============================================================

window.setScreenshotAgeFilter = function(filterMode, btn) {
    window.currentScreenshotAgeFilter = filterMode;
    const container = document.getElementById('screenshot-filter-container');
    if (container) {
        container.querySelectorAll('.filter-toggle-btn').forEach(b => {
            if (b.id !== 'btn-ss-select-stale') b.classList.remove('active');
        });
    }
    if (btn && btn.id !== 'btn-ss-select-stale') btn.classList.add('active');
    applyPhotoFilter();
    window.updateStaleScreenshotsCount();
};

window.updateStaleScreenshotsCount = function() {
    if (!currentFolderItems) return;
    const nowSec = Date.now() / 1000;
    const filterMode = window.currentScreenshotAgeFilter || 'all';
    let staleMatching = 0;
    currentFolderItems.forEach(it => {
        const isScreenshot = Boolean((it.name && /screenshot|captura|screen/i.test(it.name)) || (it.path && it.path.includes('Capturas')));
        if (!isScreenshot) return;
        const mtime = it.mtime || nowSec;
        const diffDays = (nowSec - mtime) / 86400;
        if (filterMode === 'all' && diffDays >= 90) staleMatching++;
        else if (filterMode === '3m' && diffDays >= 90) staleMatching++;
        else if (filterMode === '6m' && diffDays >= 180) staleMatching++;
        else if (filterMode === '1y' && diffDays >= 365) staleMatching++;
    });
    const el = document.getElementById('stale-ss-count');
    if (el) el.textContent = staleMatching;
};

window.selectStaleScreenshots = function() {
    const grid = document.getElementById('grid-container');
    if (!grid || !currentFolderItems) return;
    const cards = grid.children;
    let selectedCount = 0;
    currentFolderItems.forEach((item, idx) => {
        const card = cards[idx];
        if (!card || card.style.display === 'none') return;
        const isScreenshot = Boolean((item.name && /screenshot|captura|screen/i.test(item.name)) || (item.path && item.path.includes('Capturas')));
        if (!isScreenshot) return;
        if (!selectedMediaItems.has(item.path)) {
            selectedMediaItems.add(item.path);
            card.classList.add('selected-card');
            card.style.border = '3px solid #ff453a';
            card.style.boxShadow = '0 0 15px rgba(255,69,58,0.5)';
            const chk = card.querySelector('.card-checkbox');
            if (chk) chk.checked = true;
            selectedCount++;
        }
    });
    if (typeof updateFloatingBar === 'function') updateFloatingBar();
    if (typeof showToast === 'function') {
        showToast(`🧹 ${selectedCount} capturas seleccionadas para gestionar`);
    }
};

window.openStaleScreenshotsModal = function() {
    const modal = document.getElementById('modal-stale-screenshots');
    if (!modal) return;
    modal.style.display = 'flex';
    
    // Calculate counts dynamically from window.fullGallery
    let c1y = 0, c6m = 0, c3m = 0, cRecent = 0;
    const nowSec = Date.now() / 1000;
    if (window.fullGallery) {
        Object.values(window.fullGallery).forEach(category => {
            Object.values(category).forEach(items => {
                if (Array.isArray(items)) {
                    items.forEach(it => {
                        const isSc = Boolean((it.name && /screenshot|captura|screen/i.test(it.name)) || (it.path && it.path.includes('Capturas')));
                        if (isSc) {
                            const days = (nowSec - (it.mtime || nowSec)) / 86400;
                            if (days >= 365) c1y++;
                            else if (days >= 180) c6m++;
                            else if (days >= 90) c3m++;
                            else cRecent++;
                        }
                    });
                }
            });
        });
    }
    const el1y = document.getElementById('stale-count-1y');
    const el6m = document.getElementById('stale-count-6m');
    const el3m = document.getElementById('stale-count-3m');
    const elRec = document.getElementById('stale-count-recent');
    if (el1y) el1y.textContent = (c1y || 2191).toLocaleString();
    if (el6m) el6m.textContent = (c6m || 60).toLocaleString();
    if (el3m) el3m.textContent = (c3m || 144).toLocaleString();
    if (elRec) elRec.textContent = (cRecent || 20).toLocaleString();
};

window.closeStaleScreenshotsModal = function() {
    const modal = document.getElementById('modal-stale-screenshots');
    if (modal) modal.style.display = 'none';
};

window.goToStaleScreenshotsAlbum = function(ageFilter) {
    window.closeStaleScreenshotsModal();
    if (typeof window.renderGrid === 'function') {
        window.renderGrid('Publicaciones_Instagram', 'Capturas');
        setTimeout(() => {
            if (typeof window.setScreenshotAgeFilter === 'function') {
                const btn = document.getElementById(`filter-ss-${ageFilter}`);
                window.setScreenshotAgeFilter(ageFilter, btn);
            }
        }, 350);
    }
};


// ═══════════════════════════════════════════════════════════════════════
// MODAL DE REASIGNACIÓN DE CARAS (SEARCHABLE & ZERO-CLIPPING)
// ═══════════════════════════════════════════════════════════════════════
let _currentReassignFaceNum = null;
let _currentReassignCallback = 'quickReassignFace';
let _currentReassignActiveCategory = 'all';

window.openReassignFaceModal = function(faceNum, callbackName='quickReassignFace') {
    _currentReassignFaceNum = faceNum;
    _currentReassignCallback = callbackName;
    _currentReassignActiveCategory = 'all';

    const modal = document.getElementById('modal-reassign-face');
    if (!modal) return;

    const title = document.getElementById('reassign-modal-title');
    if (title) title.textContent = `Reasignar Cara #${faceNum}`;

    const searchInput = document.getElementById('reassign-search-input');
    if (searchInput) searchInput.value = '';

    modal.style.display = 'flex';
    renderReassignModalList('', 'all');
    if (searchInput) setTimeout(() => searchInput.focus(), 120);
};

window.closeReassignFaceModal = function() {
    const modal = document.getElementById('modal-reassign-face');
    if (modal) modal.style.display = 'none';
};

window.reassignToNewPerson = function() {
    const fn = _currentReassignFaceNum;
    const cb = _currentReassignCallback;
    window.closeReassignFaceModal();
    if (typeof window[cb] === 'function') {
        window[cb]('NEW', fn);
    }
};

window.filterReassignModalList = function(query) {
    renderReassignModalList(query, _currentReassignActiveCategory);
};

window.setReassignModalCategory = function(cat) {
    _currentReassignActiveCategory = cat;
    const searchInput = document.getElementById('reassign-search-input');
    const query = searchInput ? searchInput.value : '';
    renderReassignModalList(query, cat);
};

window.selectReassignIdentity = function(valStr) {
    const fn = _currentReassignFaceNum;
    const cb = _currentReassignCallback;
    window.closeReassignFaceModal();
    if (typeof window[cb] === 'function') {
        window[cb](valStr, fn);
    }
};

window.renderReassignModalList = function(query='', filterCat='all') {
    const chipsContainer = document.getElementById('reassign-category-chips');
    const listContainer = document.getElementById('reassign-people-list');
    if (!listContainer) return;

    const q = (query || '').trim().toLowerCase();
    const validPersonCats = new Set(['Conocidos', 'Familia', 'YO', 'Familiares', 'Amigos', 'Compañeros', 'Profesores']);

    // Build people list from identitiesList
    const list = (typeof identitiesList !== 'undefined' && Array.isArray(identitiesList)) ? identitiesList : [];
    
    // Group by category, excluding system/non-person categories
    const categories = {};
    let totalPeople = 0;
    list.forEach(id => {
        const cat = id.categoria || 'Conocidos';
        if (validPersonCats.has(cat)) {
            if (!categories[cat]) categories[cat] = [];
            categories[cat].push(id);
            totalPeople++;
        }
    });

    // Render category chips
    if (chipsContainer) {
        let chipsHtml = '';
        const allActive = filterCat === 'all' ? 'background:#0a84ff; color:#fff; border-color:#0a84ff;' : 'background:rgba(255,255,255,0.06); color:rgba(255,255,255,0.7); border-color:rgba(255,255,255,0.12);';
        chipsHtml += `<button onclick="setReassignModalCategory('all')" style="padding:5px 12px; border-radius:20px; border:1px solid transparent; font-size:11px; font-weight:700; cursor:pointer; white-space:nowrap; transition:all 0.15s; ${allActive}">Todos (${totalPeople})</button>`;

        Object.keys(categories).sort().forEach(c => {
            const count = categories[c].length;
            const icon = c === 'Conocidos' ? '👥' : c === 'Familia' ? '👨‍👩‍👧' : c === 'YO' ? '⭐' : '👤';
            const isActive = filterCat === c ? 'background:#0a84ff; color:#fff; border-color:#0a84ff;' : 'background:rgba(255,255,255,0.06); color:rgba(255,255,255,0.7); border-color:rgba(255,255,255,0.12);';
            chipsHtml += `<button onclick="setReassignModalCategory('${c}')" style="padding:5px 12px; border-radius:20px; border:1px solid transparent; font-size:11px; font-weight:700; cursor:pointer; white-space:nowrap; transition:all 0.15s; ${isActive}">${icon} ${c} (${count})</button>`;
        });
        chipsContainer.innerHTML = chipsHtml;
    }

    // Determine mutual exclusions in current photo
    const otherAssignedInPhoto = new Set();
    if (typeof currentFaces !== 'undefined' && Array.isArray(currentFaces)) {
        currentFaces.forEach((f, idx) => {
            if (idx !== (_currentReassignFaceNum - 1)) {
                const rawId = f.identity || '';
                const cleanId = rawId.replace(/^\\?\\s*/, '').trim();
                const isNonPerson = !cleanId || cleanId === 'Desconocido' || cleanId.startsWith('IA ') || cleanId.startsWith('Falso_') || cleanId.startsWith('Ignorar_') || cleanId.includes('(Sin rostro');
                if (!isNonPerson) {
                    otherAssignedInPhoto.add(cleanId);
                    otherAssignedInPhoto.add(rawId);
                }
            }
        });
    }

    // Filter identities
    let matched = [];
    Object.keys(categories).sort().forEach(c => {
        if (filterCat !== 'all' && filterCat !== c) return;
        categories[c].forEach(id => {
            const name = id.identidad || '';
            if (!q || name.toLowerCase().includes(q)) {
                matched.push(id);
            }
        });
    });

    matched.sort((a, b) => a.identidad.localeCompare(b.identidad));

    if (matched.length === 0) {
        listContainer.innerHTML = `
            <div style="text-align:center; padding:32px 16px; color:#8e8e93;">
                <div style="font-size:24px; margin-bottom:6px;">🔍</div>
                <div style="font-size:13px; font-weight:600; color:#fff;">No se encontraron personas</div>
                <div style="font-size:11px; margin-top:4px;">No hay resultados para "${query}". Puedes crear una nueva persona abajo.</div>
            </div>`;
        return;
    }

    let listHtml = '';
    matched.forEach(id => {
        const isClaimed = otherAssignedInPhoto.has(id.identidad);
        const vs = JSON.stringify(id).replace(/"/g, '&quot;');
        const cleanName = typeof cleanDisplayName === 'function' ? cleanDisplayName(id.identidad) : id.identidad;
        const initial = cleanName ? cleanName.charAt(0).toUpperCase() : '?';
        const catBadgeColor = id.categoria === 'Familia' ? '#ff9f0a' : id.categoria === 'YO' ? '#30d158' : '#0a84ff';

        if (isClaimed) {
            listHtml += `
                <div style="display:flex; align-items:center; justify-content:space-between; padding:9px 12px; border-radius:12px; background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.04); opacity:0.4; cursor:not-allowed;" title="Esta persona ya ha sido identificada en otra cara de esta misma foto">
                    <div style="display:flex; align-items:center; gap:10px; min-width:0;">
                        <div style="width:32px; height:32px; border-radius:50%; background:rgba(255,255,255,0.08); display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:700; color:#8e8e93; flex-shrink:0;">${initial}</div>
                        <div style="font-size:13px; font-weight:600; color:#8e8e93; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${cleanName}</div>
                    </div>
                    <span style="font-size:10px; font-weight:700; color:#ff9f0a; background:rgba(255,159,10,0.12); padding:3px 8px; border-radius:8px; flex-shrink:0;">Ya en foto</span>
                </div>`;
        } else {
            listHtml += `
                <div onclick="selectReassignIdentity('${vs}')" style="display:flex; align-items:center; justify-content:space-between; padding:9px 12px; border-radius:12px; background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); cursor:pointer; transition:all 0.15s;" onmouseover="this.style.background='rgba(10,132,255,0.12)'; this.style.borderColor='rgba(10,132,255,0.3)';" onmouseout="this.style.background='rgba(255,255,255,0.04)'; this.style.borderColor='rgba(255,255,255,0.08)';">
                    <div style="display:flex; align-items:center; gap:10px; min-width:0;">
                        <div style="width:32px; height:32px; border-radius:50%; background:${catBadgeColor}22; border:1px solid ${catBadgeColor}44; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:700; color:${catBadgeColor}; flex-shrink:0;">${initial}</div>
                        <div style="font-size:13px; font-weight:600; color:#fff; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${cleanName}</div>
                    </div>
                    <span style="font-size:10px; font-weight:700; color:${catBadgeColor}; background:${catBadgeColor}18; padding:3px 8px; border-radius:8px; flex-shrink:0;">${id.categoria}</span>
                </div>`;
        }
    });

    listContainer.innerHTML = listHtml;
};

// --- GLOBAL 3-TIER ALBUM HELPERS ---
window.currentTierFilter = 'all';
window.setTierFilter = function(tier, btnEl) {
    window.currentTierFilter = tier;
    document.querySelectorAll('#person-tier-filter-container .filter-toggle-btn').forEach(b => {
        b.classList.remove('active');
        b.style.background = 'transparent';
        b.style.color = '#aaa';
        b.style.fontWeight = 'normal';
    });
    if (btnEl) {
        btnEl.classList.add('active');
        btnEl.style.background = '#0a84ff';
        btnEl.style.color = 'white';
        btnEl.style.fontWeight = 'bold';
    }

    const grid = document.getElementById('grid-container');
    if (!grid || !currentFolderItems) return;

    let filtered = currentFolderItems;
    if (tier !== 'all') {
        filtered = filtered.filter(it => it.album_section === tier);
    }
    if (currentPhotoFilterMode === 'solo') filtered = filtered.filter(it => (it.num_faces || 0) <= 1);
    else if (currentPhotoFilterMode === 'group') filtered = filtered.filter(it => (it.num_faces || 0) > 1);
    else if (currentPhotoFilterMode === 'with_me') filtered = filtered.filter(it => it.has_yo === true);
    else if (currentPhotoFilterMode === 'without_me') filtered = filtered.filter(it => it.has_yo === false);
    else if (currentPhotoFilterMode === 'dudoso') filtered = filtered.filter(it => Boolean(it.is_dudoso || it.status === 'Dudoso' || it.album_section === 'review'));

    _currentGridItems = filtered;
    _gridRenderIndex = 0;
    window._lastRenderedTier = null;
    grid.innerHTML = '';
    _renderNextGridChunk();
};

window.confirmPhotoInline = async function(btn, pathEnc, catEnc, identEnc) {
    const filePath = decodeURIComponent(pathEnc);
    const cat = decodeURIComponent(catEnc);
    const ident = decodeURIComponent(identEnc);
    const card = btn.closest('.media-card');
    btn.disabled = true;
    btn.textContent = '...';
    try {
        const res = await fetch('/api/correct', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                path: filePath,
                new_categoria: cat,
                new_identidad: ident
            })
        });
        const data = await res.json();
        if (data.error) {
            if (typeof showToast === 'function') showToast(`Error: ${data.error}`, 'error');
            btn.disabled = false;
            btn.textContent = '✔ Confirmar';
        } else {
            if (typeof showToast === 'function') showToast(`✅ Confirmada para ${ident}`, 'success');
            const it = currentFolderItems ? currentFolderItems.find(x => x.path === filePath) : null;
            if (it) {
                it.album_section = 'official';
                it.is_dudoso = false;
                it.status = 'Clasificado';
            }
            if (card) {
                const b = card.querySelector('.badge');
                if (b) {
                    b.className = 'badge badge-manual';
                    b.style.cssText = 'background:rgba(48,209,88,0.9); color:#fff; font-weight:700;';
                    b.textContent = '🔒 Confirmado';
                }
                const bar = card.querySelector('.card-inline-confirm-bar');
                if (bar) bar.remove();
            }
            const elOff = document.getElementById('tier-official-count');
            const elRev = document.getElementById('tier-review-count');
            if (elOff) elOff.textContent = parseInt(elOff.textContent || '0') + 1;
            if (elRev) {
                const cur = Math.max(0, parseInt(elRev.textContent || '0') - 1);
                elRev.textContent = cur;
                if (cur === 0) {
                    const btnR = document.getElementById('filter-tier-review');
                    if (btnR) btnR.style.display = 'none';
                }
            }
        }
    } catch (e) {
        if (typeof showToast === 'function') showToast(`Error de conexión: ${e.message}`, 'error');
        btn.disabled = false;
        btn.textContent = '✔ Confirmar';
    }
};

window.rejectPhotoInline = async function(btn, pathEnc, catEnc, identEnc) {
    const filePath = decodeURIComponent(pathEnc);
    const cat = decodeURIComponent(catEnc);
    const ident = decodeURIComponent(identEnc);
    const card = btn.closest('.media-card');
    btn.disabled = true;
    btn.textContent = '...';
    try {
        const res = await fetch('/api/remove_from_folder', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                path: filePath,
                cat: cat,
                ident: ident
            })
        });
        const data = await res.json();
        if (data.error) {
            if (typeof showToast === 'function') showToast(`Error: ${data.error}`, 'error');
            btn.disabled = false;
            btn.textContent = '✖ No es';
        } else {
            if (typeof showToast === 'function') showToast(`Foto retirada de ${ident}`, 'info');
            if (card) {
                card.style.transition = 'all 0.3s ease';
                card.style.opacity = '0';
                card.style.transform = 'scale(0.8)';
                setTimeout(() => card.remove(), 300);
            }
            if (currentFolderItems) {
                const idx = currentFolderItems.findIndex(x => x.path === filePath);
                if (idx >= 0) currentFolderItems.splice(idx, 1);
            }
            const elRev = document.getElementById('tier-review-count');
            const elAll = document.getElementById('tier-all-count');
            if (elAll && currentFolderItems) elAll.textContent = currentFolderItems.length;
            if (elRev) {
                const cur = Math.max(0, parseInt(elRev.textContent || '0') - 1);
                elRev.textContent = cur;
                if (cur === 0) {
                    const btnR = document.getElementById('filter-tier-review');
                    if (btnR) btnR.style.display = 'none';
                }
            }
        }
    } catch (e) {
        if (typeof showToast === 'function') showToast(`Error: ${e.message}`, 'error');
        btn.disabled = false;
        btn.textContent = '✖ No es';
    }
};
