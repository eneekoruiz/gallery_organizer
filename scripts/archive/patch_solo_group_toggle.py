import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add filter buttons to header
header_target = """                    <div>
                        <h1 id="gallery-title" style="margin:0; font-size:2rem; font-weight:800; letter-spacing:-0.5px;">Todas las Fotos</h1>
                        <p id="gallery-subtitle" style="margin:5px 0 0 0; color:#888; font-size:0.9rem;">Selecciona un álbum en el panel izquierdo.</p>
                    </div>"""

header_replacement = """                    <div>
                        <h1 id="gallery-title" style="margin:0; font-size:2rem; font-weight:800; letter-spacing:-0.5px;">Todas las Fotos</h1>
                        <p id="gallery-subtitle" style="margin:5px 0 0 0; color:#888; font-size:0.9rem;">Selecciona un álbum en el panel izquierdo.</p>
                        
                        <!-- Toggle Solo vs Acompañado -->
                        <div id="filter-toggle-container" style="display:inline-flex; background:rgba(255,255,255,0.08); padding:3px; border-radius:10px; border:1px solid rgba(255,255,255,0.12); gap:4px; margin-top:10px;">
                            <button class="filter-toggle-btn" onclick="setPhotoFilter('all', this)" style="padding:5px 14px; border-radius:7px; border:none; background:#0a84ff; color:white; font-size:12px; font-weight:bold; cursor:pointer; transition:all 0.2s;">🌐 Todas</button>
                            <button class="filter-toggle-btn" onclick="setPhotoFilter('solo', this)" style="padding:5px 14px; border-radius:7px; border:none; background:transparent; color:#aaa; font-size:12px; cursor:pointer; transition:all 0.2s;">👤 En solitario</button>
                            <button class="filter-toggle-btn" onclick="setPhotoFilter('group', this)" style="padding:5px 14px; border-radius:7px; border:none; background:transparent; color:#aaa; font-size:12px; cursor:pointer; transition:all 0.2s;">👥 En compañía</button>
                        </div>
                    </div>"""

if header_target in content:
    content = content.replace(header_target, header_replacement)

# 2. Add filter functions to JS
js_filter = """
let currentPhotoFilterMode = 'all';

function setPhotoFilter(mode, btnEl) {
    currentPhotoFilterMode = mode;
    document.querySelectorAll('.filter-toggle-btn').forEach(b => {
        b.style.background = 'transparent';
        b.style.color = '#aaa';
        b.style.fontWeight = 'normal';
    });
    if (btnEl) {
        btnEl.style.background = '#0a84ff';
        btnEl.style.color = 'white';
        btnEl.style.fontWeight = 'bold';
    }
    applyPhotoFilter();
}

function applyPhotoFilter() {
    const grid = document.getElementById('grid-container');
    if (!grid || !currentFolderItems) return;
    const cards = grid.children;
    
    currentFolderItems.forEach((item, idx) => {
        const card = cards[idx];
        if (!card) return;
        
        const numFaces = item.num_faces || 0;
        let show = true;
        
        if (currentPhotoFilterMode === 'solo') {
            show = (numFaces <= 1);
        } else if (currentPhotoFilterMode === 'group') {
            show = (numFaces > 1);
        }
        
        if (show) {
            card.style.display = 'flex';
        } else {
            card.style.display = 'none';
        }
    });
}
"""

if 'function setPhotoFilter' not in content:
    content = content.replace("</script>", js_filter + "\n</script>")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Injected Solo vs Acompañado filter toggle")
