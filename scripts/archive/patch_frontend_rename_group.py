import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Add button in header for renaming group
header_target = '<h1 id="gallery-title">Todas las Fotos</h1>'
header_replacement = '''<div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <h1 id="gallery-title">Todas las Fotos</h1>
                    <p id="gallery-subtitle">Selecciona un álbum en el panel izquierdo.</p>
                </div>
                <button id="btn-rename-group" class="premium-btn" onclick="renameCurrentGroup()" style="display:none; background:#30d158; color:white; width:auto; padding:10px 20px;">
                    🏷️ Renombrar todo este Grupo
                </button>
            </div>'''

content = content.replace(header_target, header_replacement)

# Remove the subtitle target replacement since it's already inside the div
subtitle_target = '<p id="gallery-subtitle">Selecciona un álbum en el panel izquierdo.</p>'
# Ensure we don't duplicate subtitle if content already replaced it

# Update renderGrid to toggle the btn-rename-group button visibility
old_render_start = content.find("function renderGrid(")
old_render_end = content.find("document.addEventListener('keydown'", old_render_start)

new_render_grid = """function renderGrid(cat, ident) {
            currentCat = cat;
            currentIdent = ident;
            currentFolderItems = fullGallery[cat][ident] || [];
            
            document.getElementById('gallery-title').textContent = `${cat} / ${ident}`;
            document.getElementById('gallery-subtitle').textContent = `${currentFolderItems.length} elementos`;
            
            const renameBtn = document.getElementById('btn-rename-group');
            if (renameBtn) {
                if (cat === 'Personas Sin Nombre') {
                    renameBtn.style.display = 'block';
                } else {
                    renameBtn.style.display = 'none';
                }
            }
            
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

        async function renameCurrentGroup() {
            if (!currentCat || !currentIdent || currentCat !== 'Personas Sin Nombre') return;
            const newName = prompt(`Introduce el nombre real de la persona para las ${currentFolderItems.length} fotos de '${currentIdent}':`);
            if (!newName) return;
            
            const res = await fetch('/api/rename_group', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    cat: currentCat,
                    ident: currentIdent,
                    new_name: newName,
                    new_cat: 'Conocidos'
                })
            });
            const data = await res.json();
            if (data.success) {
                showToast(`¡Fantástico! Se han movido ${data.count} fotos a 'Conocidos / ${newName}'.`);
                await loadIdentities();
                await loadGallery();
                renderGrid('Conocidos', newName);
            } else {
                showToast(data.error || "No se pudo renombrar el grupo.", true);
            }
        }
"""

content = content[:old_render_start] + new_render_grid + "\n\n" + content[old_render_end:]

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("index.html actualizado con botón de renombrado en lote de grupos.")
