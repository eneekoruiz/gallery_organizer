// ============================================================
// GALLERY.JS - Apple Photos Grade Grid & Navigation Architecture
// ============================================================

window.currentCat = null;
window.currentIdent = null;
window.fullGallery = null;
window.galleryStructure = null;
window.currentFolderItems = [];

window.INLINE_PERSON_SVG = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23555'%3E%3Cpath d='M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z'/%3E%3C/svg%3E";

async function loadGallery() {
    const statusText = document.getElementById('loading-status-text');
    const fillBar = document.getElementById('loading-progress-bar');
    const overlay = document.getElementById('library-loading-overlay');

    try {
        if (fillBar) fillBar.style.width = '60%';
        if (statusText) statusText.textContent = 'Cargando fototeca...';

        const structRes = await fetch('/api/gallery/structure');
        if (!structRes.ok) throw new Error('Structure fetch failed');
        window.galleryStructure = await structRes.json();

        if (fillBar) fillBar.style.width = '100%';
        if (statusText) statusText.textContent = 'Listo';

        renderTree();
        
        if (!window.currentCat && !window.currentIdent) {
            renderHomeMosaic();
        }

        if (overlay) {
            overlay.style.opacity = '0';
            overlay.style.transition = 'opacity 0.15s ease';
            setTimeout(() => {
                overlay.style.visibility = 'hidden';
                overlay.style.display = 'none';
            }, 150);
        }

        if (window.currentCat && window.currentIdent && window.galleryStructure[window.currentCat]) {
            renderGrid(window.currentCat, window.currentIdent);
        }

    } catch (err) {
        console.error('Error loading gallery structure:', err);
        if (overlay) {
            overlay.style.opacity = '0';
            setTimeout(() => { overlay.style.display = 'none'; }, 150);
        }
    }
}
window.loadGallery = loadGallery;

function loadAlbumsHome() {
    window.currentCat = null;
    window.currentIdent = null;
    
    document.querySelectorAll('.nav-tab-item').forEach(b => b.classList.remove('active'));
    const galTab = document.getElementById('nav-btn-gallery');
    if (galTab) galTab.classList.add('active');
    
    const titleEl = document.getElementById('gallery-title');
    const subEl = document.getElementById('gallery-subtitle');
    const avatarEl = document.getElementById('gallery-avatar');
    
    if (titleEl) titleEl.textContent = 'Todas las Fotos';
    if (subEl) subEl.textContent = 'Explora tus álbumes y personas';
    if (avatarEl) avatarEl.style.display = 'none';
    
    const bcCat = document.getElementById('bc-category');
    const bcPer = document.getElementById('bc-person');
    const sep1 = document.getElementById('bc-separator-1');
    const sep2 = document.getElementById('bc-separator-2');
    if (bcCat) bcCat.style.display = 'none';
    if (bcPer) bcPer.style.display = 'none';
    if (sep1) sep1.style.display = 'none';
    if (sep2) sep2.style.display = 'none';
    
    renderHomeMosaic();
}
window.loadAlbumsHome = loadAlbumsHome;

function renderTree() {
    const treeEl = document.getElementById('tree-container');
    const dataSource = window.galleryStructure || window.fullGallery;
    if (!treeEl || !dataSource) return;
    treeEl.innerHTML = '';
    
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
        'Revisión / Por Organizar': '📋'
    };

    const CAT_ORDER = ['YO', 'Revisión / Por Organizar', 'Familia', 'Conocidos', 'Lugares', 'Eventos', 'Mascotas', 'Objetos', 'Recuerdos', 'Profesores', 'Publicaciones_Instagram'];
    
    const categories = Object.keys(dataSource).sort((a, b) => {
        const cleanA = a.replace(/^[^\w\s]+/, '').trim();
        const cleanB = b.replace(/^[^\w\s]+/, '').trim();
        const idxA = CAT_ORDER.indexOf(cleanA);
        const idxB = CAT_ORDER.indexOf(cleanB);
        if (idxA !== -1 && idxB !== -1) return idxA - idxB;
        if (idxA !== -1) return -1;
        if (idxB !== -1) return 1;
        return a.localeCompare(b);
    });

    for (const cat of categories) {
        if (cat === '__smart_album__') continue;
        
        const catWrapper = document.createElement('div');
        catWrapper.className = 'tree-category-group';
        catWrapper.style.cssText = 'margin-bottom: 4px; border-radius: 8px;';
        
        const cleanCatName = cat.replace(/^[^\w\s]+/, '').trim();
        const icon = CAT_ICONS[cleanCatName] || '📁';
        
        const catHeader = document.createElement('div');
        catHeader.className = 'tree-header';
        catHeader.style.cssText = 'padding: 6px 10px; font-weight: 700; font-size: 11px; color: #8e8e93; text-transform: uppercase; letter-spacing: 0.5px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; border-radius: 6px;';
        catHeader.innerHTML = `
            <div style="display:flex; align-items:center; gap:6px;">
                <span>${icon}</span>
                <span>${cleanCatName}</span>
            </div>
            <span class="tree-count" style="font-size:10px; color:#666;">${Object.keys(dataSource[cat] || {}).length}</span>
        `;
        
        const identsList = document.createElement('div');
        identsList.className = 'tree-identities';
        identsList.style.cssText = 'display: flex; flex-direction: column; gap: 1px; padding-left: 6px;';
        
        catHeader.onclick = () => {
            const isCollapsed = identsList.style.display === 'none';
            identsList.style.display = isCollapsed ? 'flex' : 'none';
        };

        const idents = Object.keys(dataSource[cat] || {}).sort((a,b) => a.localeCompare(b));
        for (const ident of idents) {
            const identEl = document.createElement('div');
            identEl.className = 'tree-folder identity-item';
            identEl.style.cssText = 'padding: 5px 10px; border-radius: 6px; font-size: 12px; color: #ccc; cursor: pointer; display: flex; align-items: center; justify-content: space-between; gap: 8px; transition: all 0.15s;';
            
            const rawVal = dataSource[cat][ident];
            const count = typeof rawVal === 'number' ? rawVal : (Array.isArray(rawVal) ? rawVal.length : 0);
            
            let displayIcon = '';
            if (ident.includes('Sin Rostro')) displayIcon = '📷';
            else if (ident.includes('Vídeo') || ident.includes('Video')) displayIcon = '🎬';
            else if (ident.includes('Dudosos')) displayIcon = '⚠️';
            else if (ident.includes('Desconocidos')) displayIcon = '❓';
            else if (ident.includes('iCloud')) displayIcon = '🍏';
            else if (ident.includes('Persona Nueva')) displayIcon = '👤';

            const leftDiv = document.createElement('div');
            leftDiv.style.cssText = 'display:flex; align-items:center; gap:7px; min-width:0; flex:1;';

            if (displayIcon) {
                const iconSpan = document.createElement('span');
                iconSpan.style.cssText = 'font-size:13px; flex-shrink:0;';
                iconSpan.textContent = displayIcon;
                leftDiv.appendChild(iconSpan);
            } else {
                const avatarImg = document.createElement('img');
                avatarImg.className = 'sidebar-person-avatar';
                avatarImg.style.cssText = 'width:20px; height:20px; border-radius:50%; object-fit:cover; flex-shrink:0; border:1px solid rgba(255,255,255,0.15);';
                avatarImg.loading = 'lazy';
                avatarImg.src = `/api/person_avatar?cat=${encodeURIComponent(cat)}&ident=${encodeURIComponent(ident)}`;
                avatarImg.onerror = function() {
                    this.onerror = null;
                    const ph = document.createElement('span');
                    ph.style.cssText = 'width:20px; height:20px; border-radius:50%; background:rgba(255,255,255,0.1); display:inline-flex; align-items:center; justify-content:center; font-size:10px; font-weight:700; color:#8e8e93; flex-shrink:0;';
                    ph.textContent = (ident[0] || '?').toUpperCase();
                    this.replaceWith(ph);
                };
                leftDiv.appendChild(avatarImg);
            }

            const cleanName = ident.replace(/^[^\w\s]+/, '').trim();
            const nameSpan = document.createElement('span');
            nameSpan.style.cssText = 'white-space:nowrap; overflow:hidden; text-overflow:ellipsis; flex:1; font-weight:500;';
            nameSpan.textContent = cleanName;
            leftDiv.appendChild(nameSpan);

            const countBadge = document.createElement('span');
            countBadge.style.cssText = 'font-size:10px; background:rgba(255,255,255,0.06); padding:1px 6px; border-radius:8px; color:#8e8e93; flex-shrink:0; font-weight:600;';
            countBadge.textContent = count;

            identEl.appendChild(leftDiv);
            identEl.appendChild(countBadge);
            
            identEl.onclick = (e) => {
                e.stopPropagation();
                document.querySelectorAll('.identity-item').forEach(el => {
                    el.style.background = 'transparent';
                    el.style.color = '#ccc';
                });
                identEl.style.background = 'rgba(10,132,255,0.2)';
                identEl.style.color = '#fff';
                renderGrid(cat, ident);
            };
            identsList.appendChild(identEl);
        }
        
        catWrapper.appendChild(catHeader);
        catWrapper.appendChild(identsList);
        treeEl.appendChild(catWrapper);
    }
}
window.renderTree = renderTree;

let _currentGridItems = [];
let _renderChunkIndex = 0;
const CHUNK_SIZE = 48;
let _gridObserver = null;

async function renderGrid(cat, ident) {
    window.currentCat = cat;
    window.currentIdent = ident;

    const grid = document.getElementById('grid-container');
    const titleEl = document.getElementById('gallery-title');
    const subTitleEl = document.getElementById('gallery-subtitle');
    const avatarEl = document.getElementById('gallery-avatar');
    const bcCat = document.getElementById('bc-category');
    const bcPer = document.getElementById('bc-person');
    const sep1 = document.getElementById('bc-separator-1');
    const sep2 = document.getElementById('bc-separator-2');

    if (!grid) return;

    if (_gridObserver) {
        _gridObserver.disconnect();
        _gridObserver = null;
    }

    grid.className = 'gallery-grid';
    grid.style.cssText = 'display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 14px; padding: 16px 20px 80px 20px; overflow-y: auto; flex: 1;';
    grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: #8e8e93;"><div class="loader-small" style="margin:auto;"></div><p style="margin-top:10px;">Cargando fotos...</p></div>';

    const cleanName = ident.replace(/^[^\w\s]+/, '').trim();
    if (titleEl) titleEl.textContent = cleanName;
    if (subTitleEl) subTitleEl.textContent = `Categoría: ${cat}`;
    if (bcCat) { bcCat.textContent = cat; bcCat.style.display = 'inline'; }
    if (bcPer) { bcPer.textContent = cleanName; bcPer.style.display = 'inline'; }
    if (sep1) sep1.style.display = 'inline';
    if (sep2) sep2.style.display = 'inline';

    if (avatarEl) {
        avatarEl.src = `/api/person_avatar?cat=${encodeURIComponent(cat)}&ident=${encodeURIComponent(ident)}`;
        avatarEl.style.display = 'block';
        avatarEl.onerror = () => { avatarEl.style.display = 'none'; };
    }

    try {
        const res = await fetch(`/api/gallery/items?cat=${encodeURIComponent(cat)}&ident=${encodeURIComponent(ident)}`);
        const data = await res.json();
        
        _currentGridItems = data.items || [];
        window.currentFolderItems = _currentGridItems;
        _renderChunkIndex = 0;

        if (subTitleEl) subTitleEl.textContent = `${_currentGridItems.length} fotos`;

        grid.innerHTML = '';
        if (_currentGridItems.length === 0) {
            grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 60px; color: #8e8e93;">No hay fotos en este álbum</div>';
            return;
        }

        renderNextChunk();

        let sentry = document.getElementById('grid-sentry');
        if (!sentry) {
            sentry = document.createElement('div');
            sentry.id = 'grid-sentry';
            sentry.style.cssText = 'grid-column: 1/-1; height: 40px; width: 100%;';
            grid.parentElement.appendChild(sentry);
        }

        _gridObserver = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting && _renderChunkIndex < _currentGridItems.length) {
                renderNextChunk();
            }
        }, { rootMargin: '500px' });

        _gridObserver.observe(sentry);

    } catch (err) {
        console.error('Error fetching gallery items:', err);
        grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: #ff453a;">Error al cargar las fotos.</div>';
    }
}
window.renderGrid = renderGrid;

function renderNextChunk() {
    const grid = document.getElementById('grid-container');
    if (!grid) return;

    const chunk = _currentGridItems.slice(_renderChunkIndex, _renderChunkIndex + CHUNK_SIZE);
    _renderChunkIndex += chunk.length;

    const fragment = document.createDocumentFragment();

    chunk.forEach((item, localIdx) => {
        const globalIdx = _renderChunkIndex - chunk.length + localIdx;
        const card = createMediaCard(item, globalIdx);
        fragment.appendChild(card);
    });

    grid.appendChild(fragment);
}

function createMediaCard(item, index) {
    const card = document.createElement('div');
    card.className = 'media-card';
    card.dataset.index = index;
    card.dataset.path = item.path;
    card.style.cssText = 'position: relative; border-radius: 12px; overflow: hidden; background: #14151a; cursor: pointer; transition: transform 0.18s ease, box-shadow 0.18s ease; display: flex; flex-direction: column; height: 250px; width: 100%;';

    const isVideo = item.type === 'video' || (item.path && item.path.match(/\.(mp4|mov|avi|mkv)$/i));
    const thumbUrl = `/api/thumbnail?path=${encodeURIComponent(item.path)}`;
    const isApple = item.is_apple || (item.path && item.path.includes('iCloud Photos')) || (item.name && (item.name.startsWith('IMG_') && !item.name.includes('_20')));
    const isDataset = Boolean(item.is_dataset || (item.source && item.source.toLowerCase().includes('dataset')) || (item.name && /^(Foto|Fotos|Video|Videos|Vídeo|Vídeos)\b/i.test(item.name)) || (item.path && (item.path.includes('Dataset') || item.path.includes('Entrenamiento') || item.path.includes('\\Fotos\\') || item.path.includes('/Fotos/'))));
    const isManual = Boolean(item.is_manual || item.has_override || (item.source && item.source.toLowerCase().includes('manual')));
    const isAI = !isDataset && !isManual;

    // Badges HTML
    let badgeHtml = '';
    if (isDataset) {
        badgeHtml = '<span class="badge badge-dataset" style="position:absolute; bottom:8px; left:8px; font-size:10px; font-weight:700; padding:3px 8px; border-radius:6px; background:rgba(255,159,10,0.3); color:#ffd60a; border:1px solid rgba(255,159,10,0.5); backdrop-filter:blur(8px); z-index:5;">🏷️ Dataset</span>';
    } else if (isManual) {
        badgeHtml = '<span class="badge badge-manual" style="position:absolute; bottom:8px; left:8px; font-size:10px; font-weight:700; padding:3px 8px; border-radius:6px; background:rgba(10,132,255,0.3); color:#64d2ff; border:1px solid rgba(10,132,255,0.5); backdrop-filter:blur(8px); z-index:5;">👤 Manual</span>';
    } else {
        badgeHtml = '<span class="badge badge-ia" style="position:absolute; bottom:8px; left:8px; font-size:10px; font-weight:700; padding:3px 8px; border-radius:6px; background:rgba(191,90,242,0.3); color:#da8fff; border:1px solid rgba(191,90,242,0.5); backdrop-filter:blur(8px); z-index:5;">✨ IA</span>';
    }

    // Origin Badge (Apple vs Android)
    let originBadge = '';
    if (isApple) {
        originBadge = '<div style="position:absolute; top:8px; left:8px; background:rgba(0,0,0,0.65); border:1px solid rgba(255,255,255,0.15); border-radius:6px; padding:2px 6px; font-size:11px; backdrop-filter:blur(6px); z-index:5; display:flex; align-items:center; gap:3px;" title="Origen: Apple iCloud"><span>🍏</span><span style="font-size:9px; color:#fff; font-weight:600;">iCloud</span></div>';
    } else if (isAndroid) {
        originBadge = '<div style="position:absolute; top:8px; left:8px; background:rgba(0,0,0,0.65); border:1px solid rgba(52,199,89,0.3); border-radius:6px; padding:2px 6px; font-size:11px; backdrop-filter:blur(6px); z-index:5; display:flex; align-items:center; gap:3px;" title="Origen: Android / Cámara Local"><span>🤖</span><span style="font-size:9px; color:#30d158; font-weight:600;">Android</span></div>';
    }

    card.innerHTML = `
        <div class="media-thumb-wrap" style="position:relative; width:100%; height:205px; min-height:205px; max-height:205px; background:#181920; overflow:hidden; border-radius:12px 12px 0 0;">
            <img src="${thumbUrl}" 
                 loading="lazy" 
                 alt="${item.name || ''}"
                 style="width:100%; height:100%; object-fit:cover; display:block; opacity:1 !important; transition:transform 0.25s ease;"
                 onerror="this.onerror=null; this.src=window.INLINE_PERSON_SVG;">
            ${badgeHtml}
            ${originBadge}
            ${isVideo ? '<div style="position:absolute; bottom:8px; right:8px; background:rgba(0,0,0,0.75); border-radius:6px; padding:3px 7px; font-size:10px; color:#fff; font-weight:600; backdrop-filter:blur(6px); z-index:5;">🎬 Vídeo</div>' : ''}
            ${item.has_yo ? '<div style="position:absolute; top:8px; right:8px; background:rgba(10,132,255,0.9); border-radius:6px; padding:3px 7px; font-size:10px; font-weight:700; color:#fff; backdrop-filter:blur(6px); z-index:5;">YO</div>' : ''}
        </div>
        <div class="media-card-info" style="padding:8px 10px; font-size:11px; color:#aaa; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; background:#14151a; height:45px; display:flex; align-items:center;">
            ${item.name || ''}
        </div>
    `;

    card.onmouseenter = () => {
        card.style.transform = 'translateY(-4px)';
        card.style.boxShadow = '0 10px 28px rgba(0,0,0,0.7)';
    };
    card.onmouseleave = () => {
        card.style.transform = 'translateY(0)';
        card.style.boxShadow = 'none';
    };

    card.onclick = () => {
        if (typeof window.openLightbox === 'function') {
            window.currentItemIndex = index;
            window.openLightbox(item);
        }
    };

    return card;
}

function renderHomeMosaic() {
    const grid = document.getElementById('grid-container');
    const titleEl = document.getElementById('gallery-title');
    const subTitleEl = document.getElementById('gallery-subtitle');
    const avatarEl = document.getElementById('gallery-avatar');
    
    if (!grid) return;

    if (titleEl) titleEl.textContent = 'Fototeca';
    if (subTitleEl) subTitleEl.textContent = 'Personas y Álbumes Destacados';
    if (avatarEl) avatarEl.style.display = 'none';

    grid.className = 'gallery-grid';
    grid.style.cssText = 'display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 16px; padding: 20px; overflow-y: auto; flex: 1;';
    grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px;"><div class="loader-small" style="margin:auto;"></div></div>';

    const struct = window.galleryStructure;
    if (!struct) return;

    grid.innerHTML = '';
    const fragment = document.createDocumentFragment();

    const priorityCats = ['YO', 'Familia', 'Conocidos'];
    priorityCats.forEach(cat => {
        if (!struct[cat]) return;
        const idents = Object.keys(struct[cat]);
        idents.forEach(ident => {
            const rawVal = struct[cat][ident];
            const count = typeof rawVal === 'number' ? rawVal : (Array.isArray(rawVal) ? rawVal.length : 0);
            if (count < 2) return;

            const cleanName = ident.replace(/^[^\w\s]+/, '').trim();
            const personCard = document.createElement('div');
            personCard.style.cssText = 'display:flex; flex-direction:column; align-items:center; cursor:pointer; text-align:center; padding:14px 10px; border-radius:14px; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06); transition:all 0.2s ease;';
            
            personCard.innerHTML = `
                <div style="width:84px; height:84px; border-radius:50%; overflow:hidden; border:2px solid rgba(10,132,255,0.5); box-shadow:0 4px 14px rgba(0,0,0,0.4); margin-bottom:8px; background:#1c1c1e;">
                    <img src="/api/person_avatar?cat=${encodeURIComponent(cat)}&ident=${encodeURIComponent(ident)}"
                         loading="lazy"
                         style="width:100%; height:100%; object-fit:cover;"
                         onerror="this.onerror=null; this.src=window.INLINE_PERSON_SVG;">
                </div>
                <div style="font-size:12px; font-weight:600; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; width:100%; max-width:120px;">
                    ${cleanName}
                </div>
                <div style="font-size:10px; color:#8e8e93; margin-top:2px;">
                    ${count} fotos
                </div>
            `;

            personCard.onmouseenter = () => {
                personCard.style.transform = 'scale(1.05)';
                personCard.style.background = 'rgba(255,255,255,0.06)';
            };
            personCard.onmouseleave = () => {
                personCard.style.transform = 'scale(1)';
                personCard.style.background = 'rgba(255,255,255,0.03)';
            };

            personCard.onclick = () => {
                renderGrid(cat, ident);
            };

            fragment.appendChild(personCard);
        });
    });

    grid.appendChild(fragment);
}
window.renderHomeMosaic = renderHomeMosaic;
