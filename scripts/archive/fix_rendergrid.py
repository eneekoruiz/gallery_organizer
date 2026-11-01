import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

start_idx = content.find('function renderGrid(cat, ident) {')
end_idx = content.find('function resetGalleryView() {')

if start_idx == -1 or end_idx == -1:
    print("Could not find renderGrid or resetGalleryView")
    exit(1)

new_renderGrid = """function renderGrid(cat, ident) {
            currentCat = cat;
            currentIdent = ident;
            currentFolderItems = fullGallery[cat][ident] || [];
            
            document.getElementById('gallery-title').textContent = `${cat} / ${ident}`;
            document.getElementById('gallery-subtitle').textContent = `${currentFolderItems.length} elementos`;
            
            const renameBtn = document.getElementById('btn-rename-group');
            const ignoreBtn = document.getElementById('btn-ignore-group');
            const deleteBtn = document.getElementById('btn-delete-group');
            
            if (renameBtn && ignoreBtn && deleteBtn) {
                if (cat === 'Personas Sin Nombre') {
                    renameBtn.style.display = 'block';
                    ignoreBtn.style.display = 'block';
                    deleteBtn.style.display = 'block';
                } else {
                    renameBtn.style.display = 'none';
                    ignoreBtn.style.display = 'none';
                    deleteBtn.style.display = 'none';
                }
            }
            
            const grid = document.getElementById('grid-container');
            grid.innerHTML = '';
            
            currentFolderItems.forEach((item, idx) => {
                const card = document.createElement('div');
                card.className = 'media-card';
                
                let isStackedChild = false;
                if (item.group_id !== undefined && item.group_size > 1) {
                    if (!item.is_group_rep) {
                        isStackedChild = true;
                        card.style.display = 'none';
                        card.classList.add(`group-child-${item.group_id}`);
                    } else {
                        card.classList.add('media-stack');
                    }
                }
                
                card.onclick = () => {
                    currentItemIndex = idx;
                    openLightbox(item);
                };
                
                const badge = document.createElement('span');
                if (item.source.includes('Dataset')) {
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
                
                if (item.group_id !== undefined && item.group_size > 1 && item.is_group_rep) {
                    const groupBadge = document.createElement('div');
                    groupBadge.className = 'group-badge';
                    groupBadge.textContent = `📸 +${item.group_size - 1} Similares`;
                    groupBadge.onclick = (e) => {
                        e.stopPropagation();
                        const children = document.querySelectorAll(`.group-child-${item.group_id}`);
                        let isHidden = true;
                        if (children.length > 0 && children[0].style.display !== 'none') isHidden = false;
                        
                        children.forEach(c => {
                            c.style.display = isHidden ? 'block' : 'none';
                            if (isHidden) {
                                c.style.animation = 'fadeIn 0.3s ease';
                            }
                        });
                        
                        groupBadge.textContent = isHidden ? `🔽 Ocultar Similares` : `📸 +${item.group_size - 1} Similares`;
                        if (isHidden) {
                            card.classList.remove('media-stack');
                        } else {
                            card.classList.add('media-stack');
                        }
                    };
                    card.appendChild(groupBadge);
                }
                
                grid.appendChild(card);
            });
        }

        function closeLightbox() {
            const lb = document.getElementById('lightbox');
            if(lb) {
                lb.classList.add('hidden');
                lb.style.display = 'none';
            }
            const container = document.getElementById('lb-media-container');
            if (container) container.innerHTML = '';
            currentFileObj = null;
            isCurrentVideo = false;
            if(typeof resetZoom === 'function') resetZoom();
        }

        """

content = content[:start_idx] + new_renderGrid + content[end_idx:]

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed renderGrid and restored closeLightbox!")
