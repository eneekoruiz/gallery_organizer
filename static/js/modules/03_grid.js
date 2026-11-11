/**
 * SmartGallery AI - VIRTUALIZED PHOTO GRID & 3-TIER BADGES
 * Module: static/js/modules/03_grid.js
 */

        async function renderGrid(cat, ident) {
            if (!cat || !ident) return;

            currentCat = cat;

            currentIdent = ident;

            // Si el album aun no tiene las fotos descargadas, pedirlas bajo demanda al instante (~100ms)

            const currentVal = fullGallery && fullGallery[cat] ? fullGallery[cat][ident] : null;

            if (!Array.isArray(currentVal)) {
                const grid = document.getElementById('grid-container');

                if (grid) grid.innerHTML = '<div style="padding:40px; text-align:center;"><div class="loader-small"></div><p style="color:#8e8e93; font-size:12px; margin-top:8px;">Cargando fotos del album...</p></div>';

                try {
                    const r = await fetch('/api/gallery?cat=' + encodeURIComponent(cat) + '&ident=' + encodeURIComponent(ident));

                    if (r.ok) {
                        const albumData = await r.json();
                        fullGallery = fullGallery || {};
                        fullGallery[cat] = fullGallery[cat] || {};
                        let fetchedItems = null;
                        if (albumData[cat] && Array.isArray(albumData[cat][ident])) {
                            fetchedItems = albumData[cat][ident];
                        } else {
                            for (const cK in albumData) {
                                if (albumData[cK] && typeof albumData[cK] === 'object') {
                                    for (const iK in albumData[cK]) {
                                        if (Array.isArray(albumData[cK][iK])) {
                                            fetchedItems = albumData[cK][iK];
                                            break;
                                        }
                                    }
                                }
                                if (fetchedItems) break;
                            }
                        }
                        fullGallery[cat][ident] = fetchedItems || [];
                    }
                } catch (e) {
                    console.error("Error fetching album items:", e);
                }
            }

            fullGallery = fullGallery || {};
            fullGallery[cat] = fullGallery[cat] || {};
            if (!Array.isArray(fullGallery[cat][ident])) {
                fullGallery[cat][ident] = [];
            }
            currentFolderItems = fullGallery[cat][ident];
            window.currentFolderItems = currentFolderItems;
            currentCat = cat;
            currentIdent = ident;
            window.currentCat = cat;
            window.currentIdent = ident;

            // ── Compute album stats ──────────────────────────────────

            const items = currentFolderItems;
            const cleanCat = (cat || '').replace(/^[👥🧑👧👦👤📋📁❓🔍✨📸⚡🎉🏷️\s]+/, '').trim();
            const cleanIdent = (ident || '').replace(/^[👥🧑👧👦👤📋📁❓🔍✨📸⚡🎉🏷️\s]+/, '').trim().toLowerCase();
            const isPersonAlbum = ['Conocidos', 'Familia', 'YO', 'Profesores', 'Mascotas'].includes(cleanCat) && !cleanIdent.includes('conmigo') && !cleanIdent.includes('sin mí') && !cleanIdent.includes('grupal');
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

            if (dudosoCount > 0 && isPersonAlbum) {
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
                if (dudosoCount > 0 && isPersonAlbum) {
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
            const presenceMenuWrapper = document.getElementById('person-presence-menu-wrapper');
            const presenceDivider = document.getElementById('presence-divider');

            if (presenceMenuWrapper) {
                if (isPersonAlbum) {
                    presenceMenuWrapper.style.display = 'inline-flex';
                    if (presenceDivider) presenceDivider.style.display = 'block';
                } else {
                    presenceMenuWrapper.style.display = 'none';
                    if (presenceDivider) presenceDivider.style.display = 'none';
                    currentPhotoFilterMode = 'all';
                    const lbl = document.getElementById('person-presence-current-label');
                    if (lbl) lbl.textContent = '👥 Todas';
                    const btnMenu = document.getElementById('btn-person-presence-menu');
                    if (btnMenu) {
                        btnMenu.style.background = 'transparent';
                        btnMenu.style.color = '#aaa';
                    }
                }
            }

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
                const isNonPersonCollection = !isPersonAlbum && (!cleanIdent.startsWith('persona nueva'));
                if (isNonPersonCollection || cleanIdent.includes('sin rostro') || cleanIdent.includes('sin_rostro')) {
                    avatar.style.display = 'none';
                } else {
                    avatar.src = `/api/person_avatar?cat=${encodeURIComponent(cat)}&ident=${encodeURIComponent(ident)}&t=${Date.now()}`;

                    avatar.onload = () => {
                        avatar.style.display = 'block';

                        avatar.style.border = '2px solid rgba(48,209,88,0.7)';
                    };

                    avatar.onerror = () => {
                        avatar.style.display = 'none';
                    };
                }
            }

            // ── Button visibility ────────────────────────────────────

            const mergeBtn = document.getElementById('btn-merge-group');
            const renameBtn = document.getElementById('btn-rename-group');
            const ignoreBtn = document.getElementById('btn-ignore-group');
            const deleteBtn = document.getElementById('btn-delete-group');
            const trashAlbumBtn = document.getElementById('btn-trash-album-photos');
            const isUnnamedOrNew = (
                cat === 'Personas Sin Nombre' ||

                cat === 'Revision_Interactiva' ||

                cat === 'Personas_Nuevas' ||

                (ident && (ident.includes('Persona Nueva') || ident.includes('Persona #') || ident.startsWith('Desconocid') || ident.includes('👤')))
            );

            const showRevisionControls = isUnnamedOrNew || isRevision;
            const isSystemCollection = (
                !ident ||
                ident === 'Todas las Fotos' ||
                ident.includes('Dudosos / Baja Confianza') ||
                ident.includes('Pendientes de Analizar') ||
                ident.includes('Pendientes de Organizar') ||
                ident.includes('Vídeos Sin Rostro') ||
                ident.includes('Fotos Sin Rostro') ||
                ident === 'Favoritos' ||
                ident === 'Papelera'
            );

            const showMerge = !isSystemCollection;
            const showRename = !isSystemCollection;
            const showDelete = !isSystemCollection;
            const showIgnore = !isSystemCollection && isUnnamedOrNew;

            if (mergeBtn)  mergeBtn.style.display  = showMerge ? 'inline-flex' : 'none';
            if (renameBtn) renameBtn.style.display  = showRename ? 'inline-flex' : 'none';
            if (deleteBtn) deleteBtn.style.display  = showDelete ? 'inline-flex' : 'none';
            if (trashAlbumBtn) trashAlbumBtn.style.display = (ident && ident !== 'Todas las Fotos') ? 'inline-flex' : 'none';
            if (ignoreBtn) ignoreBtn.style.display  = showIgnore ? 'inline-flex' : 'none';

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

                if (isPersonAlbum && (item.is_dudoso || item.status === 'Dudoso' || (item.source && item.source.includes('Por Confirmar')))) {
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

                // Inline Quick Action Bar for Review / Por Confirmar cards (ONLY in genuine person albums)

                if (isPersonAlbum && (itemTier === 'review' || item.is_dudoso)) {
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

