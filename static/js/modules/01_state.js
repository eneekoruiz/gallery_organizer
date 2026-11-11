/**
 * SmartGallery AI - GLOBAL STATE & UI PREFERENCES
 * Module: static/js/modules/01_state.js
 */

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
    if (isVisible) {
        menu.style.display = 'none';
        if (btn) btn.classList.remove('active');
        return;
    }
    menu.style.display = 'block';
    if (btn) btn.classList.add('active');

    // Bulletproof fixed clamp: NEVER cuts off or overflows on mobile
    if (btn) {
        const btnRect = btn.getBoundingClientRect();
        const vw = window.innerWidth;
        const menuWidth = Math.min(250, vw - 24);
        menu.style.position = 'fixed';
        menu.style.width = menuWidth + 'px';
        menu.style.maxWidth = 'calc(100vw - 24px)';
        menu.style.boxSizing = 'border-box';
        menu.style.top = (btnRect.bottom + 8) + 'px';
        let leftPos = btnRect.left;
        if (leftPos + menuWidth > vw - 12) {
            leftPos = Math.max(12, vw - menuWidth - 12);
        }
        if (leftPos < 12) leftPos = 12;
        menu.style.left = Math.round(leftPos) + 'px';
        menu.style.right = 'auto';
    }
};
document.addEventListener('click', (e) => {
    const menu = document.getElementById('header-options-dropdown');
    const btn = document.getElementById('btn-header-more');

    if (menu && menu.style.display !== 'none') {
        if (!menu.contains(e.target) && (!btn || !btn.contains(e.target))) {
            menu.style.display = 'none';

            if (btn) btn.classList.remove('active');
        }
    }
});

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

window.openMergeModal = function(e) {
    if (e) {
        try { e.stopPropagation(); e.preventDefault(); } catch(err){}
    }
    const headerMenu = document.getElementById('header-options-dropdown');
    if (headerMenu) headerMenu.style.display = 'none';
    const headerBtn = document.getElementById('btn-header-more');
    if (headerBtn) headerBtn.classList.remove('active');

    const modal = document.getElementById('modal-merge');
    if (modal) {
        modal.classList.remove('hidden');
        modal.style.display = 'flex';
        modal.style.zIndex = '100000';

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

        modal.classList.remove('hidden');
        modal.style.display = 'flex';
        modal.style.zIndex = '100000';
    }
};

window.closeMergeModal = function() {
    const modal = document.getElementById('modal-merge');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.add('hidden');
    }
};

window.renameCurrentGroup = function(e) {
    if (e) {
        try { e.stopPropagation(); e.preventDefault(); } catch(err){}
    }
    if (typeof window.openMergeModal === 'function') {
        window.openMergeModal(e);
    }
    setTimeout(() => {
        const inp = document.getElementById('merge-new-input');
        if (inp) {
            inp.focus();
            inp.select();
        }
    }, 120);
};

// =============================================================

