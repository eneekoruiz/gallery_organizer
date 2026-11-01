import './ui.js';
import './modals.js';
import './boxes.js';
import './selection.js';
import './lightbox.js';
import './gallery.js';
import './tools.js';
import './map.js';
import './triage.js';
import './engine.js';

document.addEventListener('DOMContentLoaded', () => {
    console.log('✨ Smart Gallery Initialized');
    
    // Auto-load gallery structure & albums immediately
    if (typeof window.loadGallery === 'function') {
        window.loadGallery().catch(err => {
            console.error('Error loading gallery:', err);
        });
    }

    // Auto-load sidebar suggestions with safety timeout
    if (typeof window.loadSidebarIASuggestions === 'function') {
        window.loadSidebarIASuggestions();
    }
});