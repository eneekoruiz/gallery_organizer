import sys, re

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

print("=== FIXING ALL REPORTED BUGS ===")

# 1. Update app.py for threaded=True & thumbnail caching
with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

# Make sure /api/thumbnail sets Cache-Control header
old_thumb_route = """@app.route('/api/thumbnail')
def api_thumbnail():
    path_param = request.args.get('path')
    if not path_param:
        return "Falta path", 400
    
    thumb = generate_thumbnail(path_param)
    if thumb and os.path.exists(thumb):
        return send_file(thumb, mimetype='image/webp')
    
    # Fallback to original
    if os.path.exists(path_param):
        return send_file(path_param)
    return "No encontrado", 404"""

new_thumb_route = """@app.route('/api/thumbnail')
def api_thumbnail():
    path_param = request.args.get('path')
    if not path_param:
        return "Falta path", 400
    
    thumb = generate_thumbnail(path_param)
    if thumb and os.path.exists(thumb):
        res = send_file(thumb, mimetype='image/webp')
        res.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        return res
    
    if os.path.exists(path_param):
        res = send_file(path_param)
        res.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        return res
    return "No encontrado", 404"""

if old_thumb_route in app_code:
    app_code = app_code.replace(old_thumb_route, new_thumb_route)

if "app.run(host='0.0.0.0', port=5000, debug=True)" in app_code:
    app_code = app_code.replace("app.run(host='0.0.0.0', port=5000, debug=True)", "app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code)
print("✓ Updated app.py with threaded=True and Cache-Control headers!")

# 2. Fix index.html duplicate renderGrid and card click in MultiSelect Mode
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Clean renderGrid implementation
clean_render_grid = """
        function renderGrid(cat, ident) {
            if (!cat || !ident || !fullGallery || !fullGallery[cat] || !fullGallery[cat][ident]) {
                return;
            }
            currentCat = cat;
            currentIdent = ident;
            currentFolderItems = fullGallery[cat][ident] || [];
            
            document.getElementById('gallery-title').innerHTML = `
                <div style="display:flex; align-items:center; gap:15px; margin-bottom:5px; margin-top:-10px;">
                    <img src="/api/person_avatar?cat=${encodeURIComponent(cat)}&ident=${encodeURIComponent(ident)}" 
                         style="width:75px; height:75px; object-fit:cover; border-radius:50%; display:none;" 
                         onerror="this.style.display='none';" onload="this.style.display='block'; this.style.border='3px solid #30d158'; this.style.boxShadow='0 0 12px rgba(48,209,88,0.4)';">
                    <div>
                        <div style="font-size: 1.4rem; margin:0;">${cat} <span style="color:#666;">&gt;</span> ${ident}</div>
                        <div id="gallery-subtitle" style="font-size: 0.9rem; font-weight:normal; color:#aaa; margin-top:2px;">${currentFolderItems.length} elementos</div>
                    </div>
                </div>
            `;
            
            const avatar = document.getElementById('gallery-avatar');
            if (avatar) {
                if (cat === 'Personas Sin Nombre') {
                    avatar.src = `/api/person_avatar?cat=${encodeURIComponent(cat)}&ident=${encodeURIComponent(ident)}`;
                    avatar.style.display = 'block';
                    avatar.onerror = () => { avatar.style.display = 'none'; };
                } else {
                    avatar.style.display = 'none';
                }
            }
            
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
                card.style.position = 'relative';
                
                if (isMultiSelectMode) {
                    const chkContainer = document.createElement('div');
                    chkContainer.style.cssText = "position:absolute; top:8px; left:8px; z-index:100;";
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
                    
                    card.onclick = (e) => {
                        e.stopPropagation();
                        toggleFileSelection(item.path, card, e);
                    };
                } else {
                    card.onclick = () => {
                        currentItemIndex = idx;
                        openLightbox(item);
                    };
                }
                
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
                
                const thumb = document.createElement('img');
                thumb.src = `/api/thumbnail?path=${encodeURIComponent(item.path)}`;
                thumb.loading = 'lazy';
                thumb.decoding = 'async';
                thumb.style.opacity = '0';
                thumb.onload = () => thumb.style.opacity = '1';
                thumb.style.transition = 'opacity 0.2s ease';
                thumb.style.width = '100%';
                thumb.style.height = '100%';
                thumb.style.objectFit = 'cover';
                card.appendChild(thumb);
                
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
        }
"""

# Replace all occurrences of renderGrid with the single clean renderGrid
grid_regex = r"function renderGrid\(cat, ident\) \{[\s\S]*?\n        \}"
html = re.sub(grid_regex, clean_render_grid, html)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✓ Fixed index.html renderGrid and multi-select click handling!")
