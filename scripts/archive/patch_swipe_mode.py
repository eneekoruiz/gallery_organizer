import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Insert Swipe Indicators & Toggle Button
toolbar_target = '<button class="icon-btn" onclick="enableManualSelection()" title="Marcar persona manualmente">➕ Marcar Persona</button>'
toolbar_replacement = '<button class="icon-btn" onclick="enableManualSelection()" title="Marcar persona manualmente">➕ Marcar Persona</button>\n                <button class="icon-btn" id="btn-swipe-mode" onclick="toggleSwipeMode()" style="color:#ff9f0a; font-weight:600;">🔥 Modo Limpieza Rápida (Teclas/Swipe)</button>'

content = content.replace(toolbar_target, toolbar_replacement)

# Insert indicators before </body>
indicators_html = """
    <!-- Indicadores Flotantes del Modo Limpieza Rápida (Swipe Tinder) -->
    <div id="swipe-left-ind" class="swipe-overlay-indicator swipe-indicator-left">🗑️ BORRAR (⬅️)</div>
    <div id="swipe-right-ind" class="swipe-overlay-indicator swipe-indicator-right">✅ CONSERVAR (➡️)</div>
"""
content = content.replace('</body>', indicators_html + '\n</body>')

# 2. Add Swipe Logic & Keyboard listener inside <script>
script_extension = """
        let currentFolderItems = [];
        let currentItemIndex = -1;
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

        function renderGrid(cat, ident) {
            currentCat = cat;
            currentIdent = ident;
            currentFolderItems = fullGallery[cat][ident] || [];
            
            document.getElementById('gallery-title').textContent = `${cat} / ${ident}`;
            document.getElementById('gallery-subtitle').textContent = `${currentFolderItems.length} elementos`;
            
            const grid = document.getElementById('grid-container');
            grid.innerHTML = '';
            
            currentFolderItems.forEach((item, idx) => {
                const card = document.createElement('div');
                card.className = 'media-card';
                card.onclick = () => {
                    currentItemIndex = idx;
                    openLightbox(item);
                };
                
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

        // Navegación Acelerada por Teclado (Teclas ⬅️ y ➡️)
        document.addEventListener('keydown', async (e) => {
            const lightbox = document.getElementById('lightbox');
            if (!lightbox || lightbox.classList.contains('hidden')) return;
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;

            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                await swipeActionLeft();
            } else if (e.key === 'ArrowRight') {
                e.preventDefault();
                await swipeActionRight();
            }
        });

        async function swipeActionLeft() {
            // BORRAR Y SIGUIENTE
            const ind = document.getElementById('swipe-left-ind');
            if (ind) {
                ind.classList.add('swipe-active');
                setTimeout(() => ind.classList.remove('swipe-active'), 300);
            }
            
            if (currentFileObj) {
                const res = await fetch('/api/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ path: currentFileObj.path })
                });
                const data = await res.json();
                if (data.success) {
                    showToast("Descartado y eliminado 🗑️");
                    await loadGallery();
                    loadNextItem();
                } else {
                    showToast(data.error || "No se pudo eliminar.", true);
                }
            }
        }

        async function swipeActionRight() {
            // CONSERVAR / SIGUIENTE
            const ind = document.getElementById('swipe-right-ind');
            if (ind) {
                ind.classList.add('swipe-active');
                setTimeout(() => ind.classList.remove('swipe-active'), 300);
            }
            showToast("Conservado ✅");
            loadNextItem();
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
"""

# Replace renderGrid function in content
renderGrid_idx = content.find("function renderGrid(")
renderGrid_end = content.find("async function openLightbox(", renderGrid_idx)
content = content[:renderGrid_idx] + script_extension + "\n\n" + content[renderGrid_end:]

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("index.html actualizado con Modo Limpieza Rápida (Swipe / Teclas ⬅️ ➡️).")
