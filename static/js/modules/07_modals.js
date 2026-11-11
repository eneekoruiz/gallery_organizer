/**
 * SmartGallery AI - MODALS (MERGE, RENAME, DUPLICATES, MAPS)
 * Module: static/js/modules/07_modals.js
 */

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
            if (window._isSubmittingMerge) return;
            if (!currentCat || !currentIdent) {
                alert("Por favor, selecciona una carpeta o persona antes de intentar fusionar.");
                closeMergeModal();
                return;
            }
            window._isSubmittingMerge = true;

            const existingNameJSON = document.getElementById('merge-selected-value') ? document.getElementById('merge-selected-value').value : '';
            const newNameInput = document.getElementById('merge-new-input');
            const newName = newNameInput ? newNameInput.value.trim() : '';
            let targetName = "";
            let targetCat = "Conocidos";

            if (existingNameJSON) {
                try {
                    const parsed = JSON.parse(existingNameJSON);
                    targetName = parsed.ident;
                    targetCat = parsed.cat || "Conocidos";
                } catch (e) {
                    targetName = existingNameJSON;
                }
            } else if (newName) {
                targetName = newName;
                if (targetName.startsWith('F. ') || targetName.startsWith('F_')) targetCat = 'Familia';
                else if (targetName.startsWith('P. ') || targetName.startsWith('P_')) targetCat = 'Profesores';
                else if (targetName.startsWith('M. ') || targetName.startsWith('M_')) targetCat = 'Mascotas';
                else if (targetName === 'YO') targetCat = 'YO';
                else targetCat = 'Conocidos';
            } else {
                alert("Por favor, selecciona una persona existente o introduce un nombre nuevo.");
                return;
            }

            // 1. CAPTURAR CONTEXTO PREVIO
            const oldIdent = currentIdent;
            const oldCat = currentCat;
            const oldItems = Array.isArray(currentFolderItems) ? [...currentFolderItems] : [];

            // 2. CERRAR MODAL DE INMEDIATO (Cero bloqueo: el usuario puede navegar libremente)
            closeMergeModal();

            // 3. ACTUALIZACIÓN OPTIMISTA INMEDIATA (Título, cabecera, migas de pan y sidebar)
            currentIdent = targetName;
            currentCat = targetCat;

            const titleEl = document.getElementById('gallery-title');
            if (titleEl) {
                if (targetCat === 'YO' && targetName === 'YO') {
                    titleEl.innerHTML = `<span style="color:#fff;">👤 YO</span>`;
                } else if (targetCat === targetName) {
                    titleEl.innerHTML = `<span style="color:#fff;">${targetName}</span>`;
                } else {
                    titleEl.innerHTML = `${targetCat} <span style="color:rgba(255,255,255,0.35); margin:0 5px; font-weight:400; font-size:0.9em;">›</span> <span style="color:#fff;">${targetName}</span>`;
                }
            }

            const avatarEl = document.getElementById('gallery-avatar');
            if (avatarEl) {
                avatarEl.src = `/api/person_avatar?cat=${encodeURIComponent(targetCat)}&ident=${encodeURIComponent(targetName)}&t=${Date.now()}`;
            }

            // Actualizar metadatos de los elementos en memoria
            oldItems.forEach(it => {
                it.category = targetCat;
                it.identity = targetName;
            });

            // Actualizar fullGallery en memoria
            window.fullGallery = window.fullGallery || {};
            window.fullGallery[targetCat] = window.fullGallery[targetCat] || {};

            let destItems = window.fullGallery[targetCat][targetName] || [];

            // Si el destino no tenía las fotos en memoria, cargarlas bajo demanda del servidor
            if (!Array.isArray(destItems) || destItems.length === 0) {
                try {
                    const r = await fetch(`/api/gallery?cat=${encodeURIComponent(targetCat)}&ident=${encodeURIComponent(targetName)}`);
                    if (r.ok) {
                        const albumData = await r.json();
                        destItems = (albumData && albumData[targetCat] && albumData[targetCat][targetName]) ? albumData[targetCat][targetName] : [];
                    }
                } catch (e) {
                    console.warn("No se pudieron precargar fotos preexistentes de destino:", e);
                }
            }

            // Unificar fotos preexistentes del destino + fotos recién fusionadas (sin duplicados)
            const seenPaths = new Set();
            const unifiedItems = [];
            for (const it of destItems) {
                if (it && it.path && !seenPaths.has(it.path)) {
                    seenPaths.add(it.path);
                    unifiedItems.push(it);
                }
            }
            for (const it of oldItems) {
                if (it && it.path && !seenPaths.has(it.path)) {
                    seenPaths.add(it.path);
                    it.category = targetCat;
                    it.identity = targetName;
                    unifiedItems.push(it);
                }
            }

            window.fullGallery[targetCat][targetName] = unifiedItems;
            if (window.fullGallery[oldCat] && window.fullGallery[oldCat][oldIdent]) {
                delete window.fullGallery[oldCat][oldIdent];
            }

            // Actualizar currentFolderItems con la lista unificada completa
            currentFolderItems = unifiedItems;

            // Actualizar galleryStructure en memoria
            if (window.galleryStructure) {
                if (window.galleryStructure[oldCat] && window.galleryStructure[oldCat][oldIdent] !== undefined) {
                    delete window.galleryStructure[oldCat][oldIdent];
                }
                window.galleryStructure[targetCat] = window.galleryStructure[targetCat] || {};
                window.galleryStructure[targetCat][targetName] = unifiedItems.length;
            }

            // Actualizar contador del encabezado
            const countEl = document.getElementById('gallery-count');
            if (countEl) {
                countEl.textContent = `${unifiedItems.length} elementos • ${unifiedItems.length} fotos`;
            }

            // Actualizar filas de drilldown del sidebar inmediatamente
            const cleanOldLower = oldIdent.toLowerCase().replace(/^[👤📋📁❓🔍✨📸⚡🎉🏷️👥🧑👧👦\s]+/, '').trim();
            document.querySelectorAll('.drilldown-identity-row').forEach(row => {
                const rowName = (row.dataset.identName || '').toLowerCase().replace(/^[👤📋📁❓🔍✨📸⚡🎉🏷️👥🧑👧👦\s]+/, '').trim();
                if (rowName === cleanOldLower) {
                    row.remove();
                }
            });

            // Renderizar la cuadrícula con TODAS las fotos unificadas
            if (typeof renderGrid === 'function') {
                await renderGrid(targetCat, targetName);
            }

            // 4. NOTIFICACIÓN FLOTANTE NO BLOQUEANTE (Sincronización en segundo plano)
            showToast(`🔄 Fusionando '${oldIdent}' con '${targetName}' en segundo plano...`);

            // 5. SINCRONIZACIÓN ASÍNCRONA EN SEGUNDO PLANO
            try {
                fetch('/api/rename_group', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        cat: oldCat,
                        ident: oldIdent,
                        new_name: targetName,
                        new_cat: targetCat
                    })
                })
                .then(res => res.json())
                .then(data => {
                    if (data && data.success) {
                        showToast(`🎉 ¡Fusión con '${targetName}' completada con éxito!`);
                        const av = document.getElementById('gallery-avatar');
                        if (av) {
                            av.src = `/api/person_avatar?cat=${encodeURIComponent(targetCat)}&ident=${encodeURIComponent(targetName)}&t=${Date.now()}`;
                        }
                        if (typeof loadIdentities === 'function') {
                            loadIdentities().catch(() => {});
                        }
                    } else {
                        showToast((data && data.error) || "No se pudo fusionar en el servidor.", true);
                    }
                })
                .catch(e => {
                    console.error("Error en sincronización de fusión:", e);
                    showToast("Error de conexión durante la fusión en segundo plano.", true);
                })
                .finally(() => {
                    window._isSubmittingMerge = false;
                });
            } catch (err) {
                console.error("Error iniciando fusión:", err);
                window._isSubmittingMerge = false;
            }
        }

        window.deleteCurrentGroup = deleteCurrentGroup;
        window.ignoreCurrentGroup = ignoreCurrentGroup;
        window.submitMergeGroup = submitMergeGroup;
        window.closeMergeModal = closeMergeModal;
        window.resetGalleryView = resetGalleryView;

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

                    if (typeof navigateLightbox === 'function') {
                        navigateLightbox(-1);
                    } else if (currentFolderItems && currentItemIndex > 0) {
                        currentItemIndex--;

                        openLightbox(currentFolderItems[currentItemIndex]);
                    }
                }
                else if (e.key === 'ArrowRight') {
                    e.preventDefault();

                    if (typeof navigateLightbox === 'function') {
                        navigateLightbox(1);
                    } else if (currentFolderItems && currentItemIndex < currentFolderItems.length - 1) {
                        currentItemIndex++;

                        openLightbox(currentFolderItems[currentItemIndex]);
                    }
                }

                return; // Stop here if lightbox is open
            }

            // Global shortcuts (if lightbox is closed)

            if (e.key === 'Delete' || e.key === 'Backspace') {
                e.preventDefault();
            }
        });

        // Setup Mobile Touch Controls (Pinch-to-zoom, pan when zoomed, photo navigation ONLY)

        // NOTA CRÍTICA: Deslizar la pantalla NUNCA acepta ni descarta/elimina fotos.

        let touchStartX = 0;
        let touchStartY = 0;
        let touchInitialDist = 0;
        let initialZoom = 1.0;
        let isPinching = false;
        let isTouchPanning = false;
        let touchPanStartX = 0;
        let touchPanStartY = 0;
        let lastTapTime = 0;

        document.addEventListener('DOMContentLoaded', () => {
            const lbEl = document.getElementById('lightbox');

            if (lbEl) {
                lbEl.addEventListener('touchstart', (e) => {
                    if (e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION' || e.target.tagName === 'BUTTON' || e.target.closest('.metadata-panel') || e.target.closest('#lb-topbar') || e.target.closest('.lb-box-popup')) return;

                    if (e.touches && e.touches.length === 2) {
                        isPinching = true;

                        isTouchPanning = false;

                        touchInitialDist = Math.hypot(
                            e.touches[0].clientX - e.touches[1].clientX,

                            e.touches[0].clientY - e.touches[1].clientY
                        );

                        initialZoom = (typeof zoomLevel !== 'undefined' ? zoomLevel : 1.0);

                        return;
                    }

                    if (e.touches && e.touches.length === 1) {
                        isPinching = false;

                        touchStartX = e.touches[0].clientX;

                        touchStartY = e.touches[0].clientY;

                        touchPanStartX = e.touches[0].clientX - (typeof panX !== 'undefined' ? panX : 0);

                        touchPanStartY = e.touches[0].clientY - (typeof panY !== 'undefined' ? panY : 0);

                        // Doble toque para hacer zoom rápido 2x / 1x

                        const now = Date.now();

                        if (now - lastTapTime < 300) {
                            if (typeof window.toggleZoomStep === 'function') {
                                window.toggleZoomStep();
                            }

                            lastTapTime = 0;

                            return;
                        }

                        lastTapTime = now;

                        if (typeof zoomLevel !== 'undefined' && zoomLevel > 1.05) {
                            isTouchPanning = true;
                        } else {
                            isTouchPanning = false;
                        }
                    }
                }, { passive: true });

                lbEl.addEventListener('touchmove', (e) => {
                    if (isPinching && e.touches && e.touches.length === 2) {
                        const dist = Math.hypot(
                            e.touches[0].clientX - e.touches[1].clientX,

                            e.touches[0].clientY - e.touches[1].clientY
                        );

                        if (touchInitialDist > 0) {
                            const scale = dist / touchInitialDist;
                            const newZoom = Math.min(16.0, Math.max(1.0, initialZoom * scale));

                            if (typeof window.applyZoomLevel === 'function') {
                                window.applyZoomLevel(newZoom);
                            }
                        }

                        return;
                    }

                    if (isTouchPanning && e.touches && e.touches.length === 1 && typeof zoomLevel !== 'undefined' && zoomLevel > 1.05) {
                        panX = e.touches[0].clientX - touchPanStartX;

                        panY = e.touches[0].clientY - touchPanStartY;

                        if (typeof applyZoomTransform === 'function') {
                            applyZoomTransform();
                        } else if (typeof window.applyZoomLevel === 'function') {
                            window.applyZoomLevel(zoomLevel, panX, panY);
                        }
                    }
                }, { passive: true });

                lbEl.addEventListener('touchend', (e) => {
                    if (isPinching) {
                        if (!e.touches || e.touches.length < 2) isPinching = false;

                        return;
                    }

                    if (isTouchPanning) {
                        isTouchPanning = false;

                        return;
                    }

                    if (e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION' || e.target.tagName === 'BUTTON' || e.target.closest('.metadata-panel') || e.target.closest('#lb-topbar')) return;

                    // Si la imagen tiene zoom, el arrastre es para inspeccionar detalles, NUNCA cambiar de foto

                    if (typeof zoomLevel !== 'undefined' && zoomLevel > 1.05) {
                        return;
                    }

                    if (e.changedTouches && e.changedTouches.length > 0) {
                        const dX = e.changedTouches[0].clientX - touchStartX;
                        const dY = e.changedTouches[0].clientY - touchStartY;

                        // Navegación táctil estándar de foto (solo a 1x):

                        // Deslizar izquierda = siguiente foto, deslizar derecha = foto anterior.

                        // NUNCA descarta ni confirma fotos.

                        if (Math.abs(dX) > 110 && Math.abs(dX) > Math.abs(dY) * 2) {
                            if (dX > 0) {
                                if (typeof navigateLightbox === 'function') navigateLightbox(-1);
                            } else {
                                if (typeof navigateLightbox === 'function') navigateLightbox(1);
                            }
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

function isPersonAlbum(cat, ident) {
    if (!ident) return false;
    const s = String(ident).trim();
    const l = s.toLowerCase();
    // Non-person / review / system folders
    if (l.includes('dudoso') || l.includes('desconocid') || l.includes('sin rostro') ||
        l.includes('pendiente') || l.includes('grupos por confirmar') || l.includes('caras aisladas') ||
        l.includes('excluid') || l.includes('falso_positivo') || l.includes('ignorar') ||
        l.includes('baja confianza') || l.includes('por identificar') || l.includes('por organizar') ||
        l.includes('revisión') || l.includes('revision')) {
        return false;
    }
    if (cat) {
        const catL = String(cat).toLowerCase();
        if (catL.includes('eventos') || catL.includes('lugares') || catL.includes('recuerdos') ||
            catL.includes('objetos') || catL.includes('frases') || catL.includes('revisión') ||
            catL.includes('organizar') || catL.includes('dudoso')) {
            return false;
        }
    }
    const knownPersonCats = ['Conocidos', 'Familia', 'YO', 'Profesores', 'Mascotas'];
    if (cat && knownPersonCats.includes(cat)) {
        return true;
    }
    if (s.startsWith('C.') || s.startsWith('F.') || s.startsWith('P.') || s.startsWith('M.') || s === 'YO') {
        return true;
    }
    return false;
}
window.isPersonAlbum = isPersonAlbum;

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
            const targetLower = (sug.target || '').toLowerCase();
            if (targetLower.includes('persona nueva') || targetLower.includes('persona #') || targetLower.includes('desconocid')) return;

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
    if (window._isQuickMerging) return;
    window._isQuickMerging = true;

    const btn = document.getElementById('btn-quick-merge-exec');
    if (btn) {
        btn.textContent = '⏳ Fusionando...';
        btn.style.pointerEvents = 'none';
    }

    fetch('/api/rename_group', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            cat: currentCat || '📋 Revisión / Por Organizar',
            ident: source,
            new_name: target,
            new_cat: targetCat || 'Conocidos'
        })
    })
    .then(r => r.json())
    .then(async data => {
        const b = document.getElementById('smart-merge-banner');
        if (b) b.remove();

        if (typeof showToast === 'function') {
            showToast(`🎉 ¡Fusión con '${target}' completada con éxito!`);
        } else {
            alert(`✓ Fusionado con éxito en ${target}`);
        }

        const av = document.getElementById('gallery-avatar');
        if (av) {
            av.src = `/api/person_avatar?cat=${encodeURIComponent(targetCat || 'Conocidos')}&ident=${encodeURIComponent(target)}&t=${Date.now()}`;
        }

        if (typeof loadIdentities === 'function') {
            loadIdentities().catch(() => {});
        }

        if (window.fullGallery && window.fullGallery[targetCat || 'Conocidos']) {
            delete window.fullGallery[targetCat || 'Conocidos'][target];
        }
        if (window.fullGallery && window.fullGallery[currentCat || '📋 Revisión / Por Organizar']) {
            delete window.fullGallery[currentCat || '📋 Revisión / Por Organizar'][source];
        }
        if (typeof renderGrid === 'function') {
            await renderGrid(targetCat || 'Conocidos', target);
        } else if (typeof loadAlbumsHome === 'function') {
            loadAlbumsHome();
        }
    })
    .catch(err => {
        console.error("Error en executeQuickMerge:", err);
        if (typeof showToast === 'function') {
            showToast('Error en fusión: ' + err, true);
        } else {
            alert('Error en fusión: ' + err);
        }
        if (btn) {
            btn.textContent = '✓ Fusionar con 1 Clic';
            btn.style.pointerEvents = '';
        }
    })
    .finally(() => {
        window._isQuickMerging = false;
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

