// @ts-nocheck
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
            thumb.src = '/api/thumbnail?path=' + encodeURIComponent(item.path);
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
