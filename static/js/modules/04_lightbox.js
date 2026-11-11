/**
 * SmartGallery AI - FULLSCREEN LIGHTBOX & UNIFIED ZOOM
 * Module: static/js/modules/04_lightbox.js
 */

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
            const isSystemFolder = !currentIdent ||
                currentIdent.includes('Dudosos') ||
                currentIdent.includes('Baja Confianza') ||
                currentIdent.includes('Desconocid') ||
                currentIdent.includes('Sin Rostro') ||
                currentIdent.includes('Caras Aisladas') ||
                currentIdent.includes('Pendiente') ||
                (currentCat && (currentCat.includes('Revisión') || currentCat.includes('Organizar')));
            const isPerson = (!isSystemFolder && typeof isPersonAlbum === 'function') ? isPersonAlbum(currentCat, currentIdent) : false;
            const hasManualEdit = Boolean(
                currentFileObj && (
                    currentFileObj.is_manual ||
                    (currentFileObj.source && currentFileObj.source.includes('Manual')) ||
                    (currentFileObj.status === 'Clasificado' && !currentFileObj.is_dudoso)
                )
            );

            const isDudosoVid = Boolean(
                isPerson && !hasManualEdit &&
                currentFileObj && (currentFileObj.is_dudoso || currentFileObj.status === 'Dudoso' || currentFileObj.album_section === 'review' || (currentFileObj.source && currentFileObj.source.includes('Por Confirmar')))
            );

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

