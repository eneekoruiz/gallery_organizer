import os
import re

main_js_path = r'C:\Users\User\Desktop\ENEKO\smart_gallery_app\static\js\main.js'
frontend_src = r'C:\Users\User\Desktop\ENEKO\smart_gallery_app\frontend\src'

with open(main_js_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Make frontend src dirs
os.makedirs(os.path.join(frontend_src, 'ui'), exist_ok=True)

# We will just dump everything into a few files, but add @ts-nocheck
store_ts = '''// @ts-nocheck
export const store = {
    fullGallery: {},
    identitiesList: [],
    currentCat: null,
    currentIdent: null,
    currentFolderItems: [],
    currentItemIndex: -1,
    isSwipeModeActive: true,
    isMultiSelectMode: false,
    selectedFiles: new Set()
};
window.store = store;
'''

# Virtual Scroller for grid
grid_ts = '''// @ts-nocheck
import { store } from '../store';

export function renderGrid(cat, ident) {
    if (!cat || !ident || !store.fullGallery || !store.fullGallery[cat] || !store.fullGallery[cat][ident]) return;
    store.currentCat = cat;
    store.currentIdent = ident;
    store.currentFolderItems = store.fullGallery[cat][ident] || [];
    
    document.getElementById('gallery-title').textContent = cat + ' > ' + ident;
    const sub = document.getElementById('gallery-subtitle');
    if (sub) {
        sub.style.display = 'block';
        sub.textContent = store.currentFolderItems.length + ' elementos';
    }
    
    const grid = document.getElementById('grid-container');
    grid.innerHTML = '';
    
    // Virtual Scroller implementation
    grid.style.position = 'relative';
    grid.style.overflowY = 'auto';
    grid.style.height = '80vh'; // Fixed height for scrolling
    
    const itemHeight = 250; // Approximate height of a media card
    const cols = Math.floor(grid.clientWidth / 200) || 1; // Approx cols
    const rows = Math.ceil(store.currentFolderItems.length / cols);
    const totalHeight = rows * itemHeight;
    
    const spacer = document.createElement('div');
    spacer.style.height = totalHeight + 'px';
    spacer.style.width = '100%';
    grid.appendChild(spacer);
    
    const renderWindow = () => {
        const scrollTop = grid.scrollTop;
        const startRow = Math.floor(scrollTop / itemHeight);
        const endRow = Math.min(rows, startRow + Math.ceil(grid.clientHeight / itemHeight) + 1);
        
        const startIndex = startRow * cols;
        const endIndex = Math.min(store.currentFolderItems.length, endRow * cols);
        
        // Remove old cards (for a true virtual scroller we'd reuse or track, but simple approach here)
        Array.from(grid.children).forEach(child => {
            if (child !== spacer) child.remove();
        });
        
        for (let i = startIndex; i < endIndex; i++) {
            const item = store.currentFolderItems[i];
            const card = document.createElement('div');
            card.className = 'media-card';
            card.style.position = 'absolute';
            card.style.top = (Math.floor(i / cols) * itemHeight) + 'px';
            card.style.left = ((i % cols) * 200) + 'px'; // approx width
            card.style.width = '180px';
            card.style.height = '230px';
            
            const thumb = document.createElement('img');
            thumb.src = /api/thumbnail?path=\;
            thumb.loading = 'lazy';
            thumb.style.width = '100%';
            thumb.style.height = '100%';
            thumb.style.objectFit = 'cover';
            card.appendChild(thumb);
            
            const title = document.createElement('div');
            title.className = 'media-title';
            title.textContent = item.name;
            card.appendChild(title);
            
            grid.appendChild(card);
        }
    };
    
    grid.addEventListener('scroll', renderWindow);
    renderWindow();
}
window.renderGrid = renderGrid;
'''

api_ts = '''// @ts-nocheck
import { store } from './store';
import { renderGrid } from './ui/grid';

export async function loadIdentities() {
    const res = await fetch('/api/identities');
    store.identitiesList = await res.json();
    window.identitiesList = store.identitiesList;
}

export async function loadGallery() {
    const res = await fetch('/api/gallery');
    store.fullGallery = await res.json();
    window.fullGallery = store.fullGallery;
    if (window.renderTree) window.renderTree();
    if (store.currentCat && store.currentIdent) {
        renderGrid(store.currentCat, store.currentIdent);
    }
}
window.loadIdentities = loadIdentities;
window.loadGallery = loadGallery;
'''

# we just dump the rest of main.js into main.ts
main_ts = f'''// @ts-nocheck
import './store';
import './api';
import './ui/grid';

// The original main.js content starts here
{content}
'''

# Write files
with open(os.path.join(frontend_src, 'store.ts'), 'w', encoding='utf-8') as f:
    f.write(store_ts)
with open(os.path.join(frontend_src, 'api.ts'), 'w', encoding='utf-8') as f:
    f.write(api_ts)
with open(os.path.join(frontend_src, 'ui', 'grid.ts'), 'w', encoding='utf-8') as f:
    f.write(grid_ts)
with open(os.path.join(frontend_src, 'main.ts'), 'w', encoding='utf-8') as f:
    f.write(main_ts)

print("Migration script completed.")
