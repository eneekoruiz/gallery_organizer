import re

html_content = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Apple Photos - AI Edition</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>

    <!-- Sidebar: Jerarquía -->
    <aside class="sidebar">
        <h2>Smart Gallery</h2>
        <div class="search-bar">
            <input type="text" placeholder="Buscar categoría o persona..." oninput="filterGallery(this.value)">
        </div>
        <div id="tree-container" class="tree-container">
            <div class="loader-small"></div> Cargando biblioteca...
        </div>
    </aside>

    <!-- Main Content: Mosaico -->
    <main class="gallery-main">
        <header class="gallery-header">
            <h1 id="gallery-title">Todas las Fotos</h1>
            <p id="gallery-subtitle">Selecciona un álbum en el panel izquierdo.</p>
        </header>
        
        <div id="grid-container" class="grid-container">
            <!-- Thumbnails -->
        </div>
    </main>

    <!-- Lightbox (Visor Detallado) -->
    <div id="lightbox" class="lightbox hidden">
        <div class="lightbox-toolbar">
            <div class="toolbar-left">
                <button class="icon-btn" onclick="closeLightbox()">Cerrar ✕</button>
                <button class="icon-btn" onclick="deleteCurrentFile()" title="Eliminar archivo" style="color: #ff453a;">🗑️ Eliminar</button>
                <button class="icon-btn" onclick="enableManualSelection()" title="Marcar persona manualmente">➕ Marcar Persona</button>
            </div>
            <div class="toolbar-center">
                <span id="lb-filename" class="lb-title">archivo.jpg</span>
            </div>
            <div class="toolbar-right">
                <button class="icon-btn" onclick="toggleMetadata()" title="Info y Personas">ℹ️ Personas</button>
            </div>
        </div>
    
        <!-- Barra de Herramientas de Análisis -->
        <div id="analyze-toolbar" style="display: none; position: absolute; bottom: 25px; left: 50%; transform: translateX(-50%); z-index: 101;">
            <button class="premium-btn" onclick="runAnalysis()" style="background: rgba(10, 132, 255, 0.85); backdrop-filter: blur(12px); width: auto; padding: 10px 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.4);">
                🔍 Analizar Caras en Fotograma Actual
            </button>
        </div>

        <div class="lightbox-content">
            <!-- Zona del visor multimedia -->
            <div class="viewer-wrapper" id="viewer-wrapper">
                <div id="lb-media-container" class="lb-media-container">
                    <!-- Media y Bounding Boxes -->
                </div>
            </div>

            <!-- Panel Lateral Derecho (Metadatos y Personas Apple Style) -->
            <aside class="metadata-panel" id="metadata-panel">
                <h3>Detalles</h3>
                <div class="meta-card">
                    <div class="meta-item"><span class="meta-label">Fecha</span><span class="meta-value" id="meta-date">-</span></div>
                    <div class="meta-item"><span class="meta-label">Tamaño</span><span class="meta-value" id="meta-size">-</span></div>
                    <div class="meta-item"><span class="meta-label">Resolución</span><span class="meta-value" id="meta-res">-</span></div>
                    <div class="meta-item"><span class="meta-label">Cámara</span><span class="meta-value" id="meta-cam">-</span></div>
                </div>

                <h3>Personas Detectadas</h3>
                <div id="person-cards-container">
                    <p style="font-size: 0.8rem; color: var(--text-dim);">Abre una foto o analiza caras para ver la lista.</p>
                </div>
            </aside>
        </div>
    </div>

    <script>
        let fullGallery = {};
        let identitiesList = [];
        let currentFileObj = null;
        let isCurrentVideo = false;
        let currentCat = null;
        let currentIdent = null;

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

        document.addEventListener("DOMContentLoaded", async () => {
            await loadIdentities();
            await loadGallery();
        });

        async function loadIdentities() {
            const res = await fetch('/api/identities');
            identitiesList = await res.json();
        }

        async function loadGallery() {
            const res = await fetch('/api/gallery');
            fullGallery = await res.json();
            renderTree();
            if (currentCat && currentIdent) {
                if (fullGallery[currentCat] && fullGallery[currentCat][currentIdent]) {
                    renderGrid(currentCat, currentIdent);
                } else {
                    document.getElementById('grid-container').innerHTML = '';
                }
            }
        }

        function renderTree() {
            const treeEl = document.getElementById('tree-container');
            treeEl.innerHTML = '';
            for (const cat in fullGallery) {
                const catEl = document.createElement('div');
                catEl.className = 'tree-folder category';
                catEl.textContent = `📁 ${cat}`;
                treeEl.appendChild(catEl);
                for (const ident in fullGallery[cat]) {
                    const identEl = document.createElement('div');
                    identEl.className = 'tree-folder identity';
                    const count = fullGallery[cat][ident].length;
                    identEl.innerHTML = `👤 ${ident} <span class="badge-count">${count}</span>`;
                    identEl.onclick = () => renderGrid(cat, ident);
                    treeEl.appendChild(identEl);
                }
            }
        }

        function filterGallery(term) {
            term = term.toLowerCase();
            document.querySelectorAll('.tree-folder.identity').forEach(el => {
                const text = el.textContent.toLowerCase();
                el.style.display = text.includes(term) ? 'flex' : 'none';
            });
        }

        function renderGrid(cat, ident) {
            currentCat = cat;
            currentIdent = ident;
            document.getElementById('gallery-title').textContent = `${cat} / ${ident}`;
            document.getElementById('gallery-subtitle').textContent = `${fullGallery[cat][ident].length} elementos`;
            
            const grid = document.getElementById('grid-container');
            grid.innerHTML = '';
            
            fullGallery[cat][ident].forEach(item => {
                const card = document.createElement('div');
                card.className = 'media-card';
                card.onclick = () => openLightbox(item);
                
                const badge = document.createElement('span');
                badge.className = `badge ${item.source === 'Manual' ? 'badge-manual' : 'badge-ia'}`;
                badge.textContent = item.source === 'Manual' ? '🔒 Manual' : '✨ IA';
                card.appendChild(badge);
                
                if (item.type === 'video') {
                    const video = document.createElement('video');
                    video.src = `/media?path=${encodeURIComponent(item.path)}#t=0.5`;
                    video.preload = 'metadata';
                    card.appendChild(video);
                    const playIcon = document.createElement('div');
                    playIcon.className = 'play-icon';
                    playIcon.textContent = '▶';
                    card.appendChild(playIcon);
                } else {
                    const img = document.createElement('img');
                    img.src = `/media?path=${encodeURIComponent(item.path)}`;
                    img.loading = 'lazy';
                    card.appendChild(img);
                }
                
                const title = document.createElement('div');
                title.className = 'media-title';
                title.textContent = item.name;
                card.appendChild(title);
                grid.appendChild(card);
            });
        }

        async function openLightbox(item) {
            currentFileObj = item;
            isCurrentVideo = item.type === 'video';
            
            const container = document.getElementById('lb-media-container');
            container.innerHTML = '';
            
            let mediaEl;
            if (isCurrentVideo) {
                mediaEl = document.createElement('video');
                mediaEl.src = `/media?path=${encodeURIComponent(item.path)}`;
                mediaEl.controls = true;
                mediaEl.autoplay = false;
                mediaEl.className = 'lb-media-element';
                if(window.liveScanTimestamp) {
                    mediaEl.currentTime = window.liveScanTimestamp;
                    window.liveScanTimestamp = null;
                }
                document.getElementById('analyze-toolbar').style.display = 'block';
            } else {
                mediaEl = document.createElement('img');
                mediaEl.src = `/media?path=${encodeURIComponent(item.path)}`;
                mediaEl.className = 'lb-media-element';
                document.getElementById('analyze-toolbar').style.display = 'none';
            }
            
            container.appendChild(mediaEl);
            document.getElementById('lightbox').classList.remove('hidden');
            
            // Cargar metadatos
            fetch(`/api/metadata?path=${encodeURIComponent(item.path)}`)
                .then(r => r.json())
                .then(data => {
                    document.getElementById('meta-date').textContent = data.date || '-';
                    document.getElementById('meta-size').textContent = data.size || '-';
                    document.getElementById('meta-res').textContent = data.resolution || '-';
                    document.getElementById('meta-cam').textContent = data.camera || '-';
                });
                
            // Esperar a que cargue la imagen para analizar caras
            if (!isCurrentVideo) {
                if (mediaEl.complete) runAnalysis();
                else mediaEl.onload = () => runAnalysis();
            } else {
                document.getElementById('person-cards-container').innerHTML = '<p style="font-size:0.8rem; color:var(--text-dim);">Haz clic en "Analizar Caras" para escanear el fotograma.</p>';
            }
        }

        async function runAnalysis() {
            if (!currentFileObj) return;
            const container = document.getElementById('lb-media-container');
            const mediaEl = container.querySelector('.lb-media-element');
            if (!mediaEl) return;
            
            document.querySelectorAll('.lb-bounding-box').forEach(b => b.remove());
            
            let timestamp = isCurrentVideo ? mediaEl.currentTime : null;
            const res = await fetch('/api/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ path: currentFileObj.path, timestamp: timestamp })
            });
            const data = await res.json();
            
            const cardsContainer = document.getElementById('person-cards-container');
            cardsContainer.innerHTML = '';
            
            if (data.faces && data.faces.length > 0) {
                let intrinsicWidth = isCurrentVideo ? mediaEl.videoWidth : mediaEl.naturalWidth;
                let intrinsicHeight = isCurrentVideo ? mediaEl.videoHeight : mediaEl.naturalHeight;
                if (!intrinsicWidth && data.faces.length > 0) {
                    intrinsicWidth = data.faces[0].img_width;
                    intrinsicHeight = data.faces[0].img_height;
                }
                
                data.faces.forEach((face, idx) => {
                    const faceNum = idx + 1;
                    
                    // 1. Crear Caja sobre la foto (Pulcra)
                    const box = document.createElement('div');
                    box.className = 'lb-bounding-box';
                    box.id = `bbox-${faceNum}`;
                    
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
                    
                    box.onclick = (e) => {
                        e.stopPropagation();
                        highlightFace(faceNum);
                    };
                    
                    container.appendChild(box);
                    
                    // 2. Generar Avatar Recortado en Canvas
                    let avatarUrl = '';
                    try {
                        const canvas = document.createElement('canvas');
                        canvas.width = 100;
                        canvas.height = 100;
                        const ctx = canvas.getContext('2d');
                        ctx.drawImage(mediaEl, face.x, face.y, face.width, face.height, 0, 0, 100, 100);
                        avatarUrl = canvas.toDataURL();
                    } catch(e) {}
                    
                    // 3. Crear Tarjeta estilo Apple Photos en el Sidebar
                    const card = document.createElement('div');
                    card.className = 'person-card';
                    card.id = `pcard-${faceNum}`;
                    
                    let folderName = currentFileObj.path.split(/[\\\\/]/).slice(-2, -1)[0];
                    let categoryName = currentFileObj.path.split(/[\\\\/]/).slice(-3, -2)[0];
                    
                    let selectOptionsHtml = `<option value="">Reasignar persona...</option>`;
                    if (folderName && categoryName && folderName !== 'Resultados' && categoryName !== 'Galeria Eneko NO ABRIR') {
                        let suggestedId = {categoria: categoryName, identidad: folderName};
                        selectOptionsHtml += `<option value='${JSON.stringify(suggestedId)}' style="font-weight:bold; color:#0a84ff;">✨ Sí, es ${folderName}</option>`;
                    }
                    selectOptionsHtml += `<option value='{"categoria": "Ignorar", "identidad": "Ignorar_Irrelevante"}'>👤 Ignorar cara (Persona irrelevante)</option>`;
                    selectOptionsHtml += `<option value='{"categoria": "Ignorar", "identidad": "Falso_Positivo"}'>🚫 NO es persona</option>`;
                    selectOptionsHtml += `<option value="NEW">➕ Crear nueva persona...</option>`;
                    
                    let categories = {};
                    identitiesList.forEach(id => {
                        if(!categories[id.categoria]) categories[id.categoria] = [];
                        categories[id.categoria].push(id);
                    });
                    for (let cat in categories) {
                        selectOptionsHtml += `<optgroup label="${cat}">`;
                        categories[cat].forEach(id => {
                            selectOptionsHtml += `<option value='${JSON.stringify(id)}'>${id.identidad}</option>`;
                        });
                        selectOptionsHtml += `</optgroup>`;
                    }
                    
                    card.innerHTML = `
                        <div class="person-header" onclick="highlightFace(${faceNum})">
                            <img src="${avatarUrl}" class="person-avatar" alt="Face">
                            <div class="person-info">
                                <div class="person-name">#${faceNum} ${face.identity}</div>
                                <div class="person-confidence">${face.confidence || 'Asignación manual'}</div>
                            </div>
                        </div>
                        <select class="person-select" onchange="inlineCorrect(encodeURIComponent(currentFileObj.path), this.value, ${face.x}, ${face.y}, ${face.width}, ${face.height})">
                            ${selectOptionsHtml}
                        </select>
                    `;
                    
                    cardsContainer.appendChild(card);
                });
            } else {
                cardsContainer.innerHTML = '<p style="font-size:0.8rem; color:var(--text-dim);">No se han detectado personas en este fotograma.</p>';
            }
        }

        function highlightFace(faceNum) {
            document.querySelectorAll('.lb-bounding-box').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.person-card').forEach(c => c.classList.remove('active'));
            
            const box = document.getElementById(`bbox-${faceNum}`);
            const card = document.getElementById(`pcard-${faceNum}`);
            if (box) box.classList.add('active');
            if (card) {
                card.classList.add('active');
                card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }

        async function inlineCorrect(pathEncoded, valStr, faceX, faceY, faceW, faceH) {
            if(!valStr) return;
            let idObj;
            if(valStr === 'NEW') {
                const newCat = prompt("Introduce la categoría (ej. Conocidos, Familia, Lugares):", "Conocidos");
                if(!newCat) return;
                const newIdent = prompt("Introduce el nombre completo de la persona/lugar:");
                if(!newIdent) return;
                idObj = {categoria: newCat, identidad: newIdent};
            } else {
                idObj = JSON.parse(valStr);
            }
            
            const res = await fetch('/api/correct', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ 
                    path: decodeURIComponent(pathEncoded), 
                    new_categoria: idObj.categoria, 
                    new_identidad: idObj.identidad,
                    face: {x: faceX, y: faceY, width: faceW, height: faceH}
                })
            });
            
            const data = await res.json();
            if(data.success) {
                showToast(`Asignado a '${idObj.identidad}'. Memoria guardada.`);
                await loadIdentities();
                await loadGallery();
                await runAnalysis();
            } else {
                showToast(data.error || "Error al asignar.", true);
            }
        }

        async function deleteCurrentFile() {
            if (!currentFileObj) return;
            if (!confirm(`¿Seguro que deseas eliminar '${currentFileObj.name}'?`)) return;
            
            const res = await fetch('/api/delete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ path: currentFileObj.path })
            });
            const data = await res.json();
            if (data.success) {
                showToast("Archivo eliminado correctamente.");
                closeLightbox();
                await loadGallery();
            } else {
                showToast(data.error || "No se pudo eliminar el archivo.", true);
            }
        }

        function enableManualSelection() {
            if (!currentFileObj) return;
            const container = document.getElementById('lb-media-container');
            const mediaEl = container.querySelector('.lb-media-element');
            if (!mediaEl) return;
            
            showToast("Arrastra sobre la imagen para seleccionar un cuerpo/cara.");
            container.style.cursor = 'crosshair';
            
            let startX, startY, selectBox;
            const onMouseDown = (e) => {
                const rect = container.getBoundingClientRect();
                startX = e.clientX - rect.left;
                startY = e.clientY - rect.top;
                
                selectBox = document.createElement('div');
                selectBox.style.cssText = `position:absolute; left:${startX}px; top:${startY}px; border:2px dashed #30d158; background:rgba(48,209,88,0.2); pointer-events:none; z-index:999;`;
                container.appendChild(selectBox);
                
                const onMouseMove = (ev) => {
                    const currentX = ev.clientX - rect.left;
                    const currentY = ev.clientY - rect.top;
                    const width = Math.abs(currentX - startX);
                    const height = Math.abs(currentY - startY);
                    selectBox.style.left = `${Math.min(startX, currentX)}px`;
                    selectBox.style.top = `${Math.min(startY, currentY)}px`;
                    selectBox.style.width = `${width}px`;
                    selectBox.style.height = `${height}px`;
                };
                
                const onMouseUp = async (ev) => {
                    container.removeEventListener('mousemove', onMouseMove);
                    container.removeEventListener('mouseup', onMouseUp);
                    container.removeEventListener('mousedown', onMouseDown);
                    container.style.cursor = 'default';
                    
                    const rect = container.getBoundingClientRect();
                    const endX = ev.clientX - rect.left;
                    const endY = ev.clientY - rect.top;
                    
                    const boxW = Math.abs(endX - startX);
                    const boxH = Math.abs(endY - startY);
                    if (boxW < 10 || boxH < 10) {
                        if (selectBox) selectBox.remove();
                        return;
                    }
                    
                    let intrinsicWidth = isCurrentVideo ? mediaEl.videoWidth : mediaEl.naturalWidth;
                    let intrinsicHeight = isCurrentVideo ? mediaEl.videoHeight : mediaEl.naturalHeight;
                    
                    const scaleX = intrinsicWidth / rect.width;
                    const scaleY = intrinsicHeight / rect.height;
                    
                    const realX = Math.round(Math.min(startX, endX) * scaleX);
                    const realY = Math.round(Math.min(startY, endY) * scaleY);
                    const realW = Math.round(boxW * scaleX);
                    const realH = Math.round(boxH * scaleY);
                    
                    if (selectBox) selectBox.remove();
                    
                    const newIdent = prompt("Introduce la persona/lugar para esta selección manual:");
                    if (newIdent) {
                        await inlineCorrect(encodeURIComponent(currentFileObj.path), JSON.stringify({categoria: "Conocidos", identidad: newIdent}), realX, realY, realW, realH);
                    }
                };
                
                container.addEventListener('mousemove', onMouseMove);
                container.addEventListener('mouseup', onMouseUp);
            };
            
            container.addEventListener('mousedown', onMouseDown);
        }

        function closeLightbox() {
            document.getElementById('lightbox').classList.add('hidden');
            document.getElementById('lb-media-container').innerHTML = '';
        }

        function toggleMetadata() {
            document.getElementById('metadata-panel').classList.toggle('hidden');
        }
    </script>
</body>
</html>
"""

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("templates/index.html actualizado.")
