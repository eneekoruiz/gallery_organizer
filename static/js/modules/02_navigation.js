/**
 * SmartGallery AI - NAVIGATION & FILTERS & TIMELINE
 * Module: static/js/modules/02_navigation.js
 */

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

        window.selectedFiles = selectedFiles;

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

                // 3. Inicializacion ultra-ligera de capsulas temporales (~50 bytes)
                async function updateTimelineCapsules() {
                    try {
                        const res = await fetch('/api/gallery/years');
                        if (!res.ok) return;
                        const yearsArr = await res.json();
                        const timelineContainer = document.getElementById('timeline-years-container');
                        if (timelineContainer && Array.isArray(yearsArr) && yearsArr.length > 0) {
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
                    } catch (e) {
                        console.warn("Aviso al cargar cápsulas temporales:", e);
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

        window.loadGallery = loadGallery;
        window.loadGalleryData = loadGallery;
        window.refreshGallery = loadGallery;

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

        let isSwipeModeActive = false; // Deshabilitado por defecto para evitar acciones destructivas accidentales

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

            ['btn-merge-group','btn-rename-group','btn-ignore-group','btn-delete-group','btn-trash-album-photos'].forEach(id => {
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

function setPhotoFilter(mode, btnEl) {
    currentPhotoFilterMode = mode;
    const btnMenu = document.getElementById('btn-person-presence-menu');
    const lbl = document.getElementById('person-presence-current-label');
    if (['all', 'solo', 'group', 'with_me', 'without_me'].includes(mode)) {
        const labels = {
            'all': '👥 Todas',
            'solo': '👤 En solitario',
            'group': '👥 En compañía',
            'with_me': '🤝 Conmigo',
            'without_me': '🚫 Sin mí'
        };
        if (lbl) lbl.textContent = labels[mode] || '👥 Todas';
        if (btnMenu) {
            btnMenu.style.background = '#0a84ff';
            btnMenu.style.color = 'white';
            btnMenu.style.fontWeight = 'bold';
        }
    } else {
        document.querySelectorAll('#filter-toggle-container .filter-toggle-btn').forEach(b => {
            if (b !== btnMenu) {
                b.style.background = 'transparent';
                b.style.color = '#aaa';
                b.style.fontWeight = 'normal';
            }
        });
        if (btnEl && btnEl !== btnMenu) {
            btnEl.style.background = '#0a84ff';
            btnEl.style.color = 'white';
            btnEl.style.fontWeight = 'bold';
        }
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

