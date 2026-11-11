/**
 * SmartGallery AI - MULTISELECT & BATCH ACTIONS & ICLOUD DELETION
 * Module: static/js/modules/06_selection.js
 */

        function toggleMultiSelectMode() {
            isMultiSelectMode = !isMultiSelectMode;

            const btn = document.getElementById('btn-toggle-multiselect');
            const bar = document.getElementById('batch-action-bar');

            if (btn) {
                btn.style.background = isMultiSelectMode ? "#30d158" : "rgba(255,255,255,0.06)";

                btn.style.color = isMultiSelectMode ? "#000" : "#e5e5ea";

                btn.textContent = isMultiSelectMode ? "✅ Seleccionando" : "☑️ Seleccionar";
            }

            if (!isMultiSelectMode) {
                clearBatchSelection();

                if (bar) bar.style.display = 'none';
            } else {
                if (bar) {
                    bar.style.display = 'flex';

                    updateBatchBar();
                }
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
            const selectAllBtn = document.getElementById('btn-batch-select-all');

            if (!bar) return;

            if (isMultiSelectMode) {
                bar.style.display = 'flex';

                const count = (window.selectedFiles && window.selectedFiles.size) || 0;

                if (countEl) countEl.textContent = `${count} seleccionada(s)`;

                if (selectAllBtn && window.currentFolderItems && window.currentFolderItems.length > 0) {
                    const allSelected = (count === window.currentFolderItems.length);

                    selectAllBtn.textContent = allSelected ? "☒ Desmarcar todas" : "☑ Seleccionar todas";
                }
            } else {
                bar.style.display = 'none';
            }
        }

        function toggleSelectAllAlbumPhotos() {
            const items = (window.currentFolderItems && window.currentFolderItems.length) ? window.currentFolderItems : ((typeof currentFolderItems !== 'undefined' && currentFolderItems.length) ? currentFolderItems : []);

            if (!items || !items.length) {
                showToast("No hay fotos en el álbum actual");

                return;
            }

            window.selectedFiles = window.selectedFiles || new Set();

            selectedFiles = selectedFiles || window.selectedFiles || new Set();

            window.selectedFiles = selectedFiles;

            const allSelected = (selectedFiles.size === items.length);

            if (allSelected) {
                clearBatchSelection();
            } else {
                items.forEach(it => {
                    const p = it.path || it;

                    if (p) window.selectedFiles.add(p);
                });

                document.querySelectorAll('.media-card').forEach(card => {
                    card.classList.add('selected-card');

                    card.style.border = '3px solid #30d158';

                    card.style.boxShadow = '0 0 15px rgba(48,209,88,0.5)';

                    const chk = card.querySelector('.card-checkbox');

                    if (chk) chk.checked = true;
                });

                updateBatchBar();
            }
        }

        window.toggleSelectAllAlbumPhotos = toggleSelectAllAlbumPhotos;

        async function trashSelectedPhotos() {
            if (!window.selectedFiles || window.selectedFiles.size === 0) {
                showToast("⚠️ Selecciona al menos una foto para enviar a la papelera");

                return;
            }

            const count = window.selectedFiles.size;
            const isEntire = Boolean(window.currentFolderItems && count === window.currentFolderItems.length);
            const msg = isEntire

                ? `¿Seguro que deseas enviar las ${count} fotos de "${currentIdent}" a la Papelera de reciclaje?\n\nLas fotos podrán recuperarse desde la papelera si cambias de opinión.`

                : `¿Seguro que deseas enviar las ${count} fotos seleccionadas a la Papelera de reciclaje?\n\nLas fotos podrán recuperarse desde la papelera si cambias de opinión.`;

            if (!confirm(msg)) return;

            showToast(`⏳ Enviando ${count} foto(s) a la Papelera...`);

            try {
                const res = await fetch('/api/batch_delete', {
                    method: 'POST',

                    headers: {'Content-Type': 'application/json'},

                    body: JSON.stringify({
                        paths: Array.from(window.selectedFiles),

                        cat: currentCat,

                        ident: currentIdent,

                        entire_album: isEntire
                    })
                });

                const data = await res.json();

                if (data.success) {
                    showToast(`🗑️ ${data.count || count} foto(s) enviadas a la Papelera correctamente.`);

                    clearBatchSelection();

                    if (isMultiSelectMode) toggleMultiSelectMode();

                    if (isEntire) {
                        if (typeof loadGallery === 'function') await loadGallery();

                        if (typeof renderTree === 'function') renderTree();

                        const grid = document.getElementById('grid-container');

                        if (grid) grid.innerHTML = `<div style="text-align:center; padding:60px 20px; color:#8e8e93;"><div style="font-size:40px; margin-bottom:12px;">🗑️</div><div style="font-size:1.1rem; color:#fff; font-weight:600;">Álbum vacío</div><div>Todas las fotos se han movido a la Papelera de reciclaje.</div></div>`;

                        const titleEl = document.getElementById('gallery-title');

                        if (titleEl) titleEl.textContent = "Álbum vacío";

                        const subEl = document.getElementById('gallery-subtitle');

                        if (subEl) subEl.textContent = "0 elementos";
                    } else {
                        if (typeof loadGallery === 'function') await loadGallery();

                        if (currentCat && currentIdent) renderGrid(currentCat, currentIdent);
                    }
                } else {
                    showToast(`❌ Error: ${data.error || "No se pudieron eliminar las fotos"}`, 'error');
                }
            } catch (e) {
                showToast(`❌ Error al conectar con el servidor: ${e}`, 'error');
            }
        }

        window.trashSelectedPhotos = trashSelectedPhotos;

        async function trashCurrentAlbumPhotos() {
            if (!currentIdent || currentIdent === 'Todas las Fotos') {
                showToast("⚠️ No hay un álbum seleccionado");

                return;
            }

            const count = (window.currentFolderItems && window.currentFolderItems.length) || 0;
            const countStr = count > 0 ? `${count} fotos` : "todas las fotos";
            const msg = `¿Seguro que deseas enviar ${countStr} de "${currentIdent}" a la Papelera de reciclaje?\n\nLas fotos podrán recuperarse desde la papelera de reciclaje si cambias de opinión.`;

            if (!confirm(msg)) return;

            showToast(`⏳ Enviando ${countStr} de "${currentIdent}" a la Papelera...`);

            try {
                const paths = window.currentFolderItems ? window.currentFolderItems.map(it => it.path || it) : [];
                const res = await fetch('/api/batch_delete', {
                    method: 'POST',

                    headers: {'Content-Type': 'application/json'},

                    body: JSON.stringify({
                        cat: currentCat,

                        ident: currentIdent,

                        entire_album: true,

                        paths: paths
                    })
                });

                const data = await res.json();

                if (data.success) {
                    showToast(`🗑️ ${data.count || count} foto(s) enviadas a la Papelera correctamente.`);

                    clearBatchSelection();

                    if (isMultiSelectMode) toggleMultiSelectMode();

                    if (typeof loadGallery === 'function') await loadGallery();

                    if (typeof renderTree === 'function') renderTree();

                    const grid = document.getElementById('grid-container');

                    if (grid) grid.innerHTML = `<div style="text-align:center; padding:60px 20px; color:#8e8e93;"><div style="font-size:40px; margin-bottom:12px;">🗑️</div><div style="font-size:1.1rem; color:#fff; font-weight:600;">Álbum vacío</div><div>Todas las fotos de "${currentIdent}" se han movido a la Papelera.</div></div>`;

                    const titleEl = document.getElementById('gallery-title');

                    if (titleEl) titleEl.textContent = "Álbum vacío";

                    const subEl = document.getElementById('gallery-subtitle');

                    if (subEl) subEl.textContent = "0 elementos";

                    const moreBtn = document.getElementById('btn-header-more');

                    if (moreBtn) moreBtn.style.display = 'none';
                } else {
                    showToast(`❌ Error: ${data.error || "No se pudieron eliminar las fotos"}`, 'error');
                }
            } catch (e) {
                showToast(`❌ Error al conectar con el servidor: ${e}`, 'error');
            }
        }

        window.trashCurrentAlbumPhotos = trashCurrentAlbumPhotos;

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

window.togglePresenceMenu = function(e) {
    if (e) {
        if (e.cancelable) e.preventDefault();
        e.stopPropagation();
    }
    const dropdown = document.getElementById('person-presence-dropdown');
    if (!dropdown) return;
    dropdown.style.display = (dropdown.style.display === 'block') ? 'none' : 'block';
};

window.selectPresenceFilter = function(mode) {
    const dropdown = document.getElementById('person-presence-dropdown');
    if (dropdown) dropdown.style.display = 'none';
    const labels = {
        'all': '👥 Todas',
        'solo': '👤 En solitario',
        'group': '👥 En compañía',
        'with_me': '🤝 Conmigo',
        'without_me': '🚫 Sin mí'
    };
    const lbl = document.getElementById('person-presence-current-label');
    if (lbl) lbl.textContent = labels[mode] || '👥 Todas';
    const btnMenu = document.getElementById('btn-person-presence-menu');
    setPhotoFilter(mode, btnMenu);
};

document.addEventListener('click', function(e) {
    const dropdown = document.getElementById('person-presence-dropdown');
    const btn = document.getElementById('btn-person-presence-menu');
    if (dropdown && dropdown.style.display === 'block') {
        if (!dropdown.contains(e.target) && !btn.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    }
});

