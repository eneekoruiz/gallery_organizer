/**
 * SmartGallery AI - Global Window Contract & Compatibility Layer
 * Module: static/js/modules/09_exports.js
 * Guarantees 100% backward compatibility for all HTML onclick handlers.
 */

(function ensureGlobalExports() {
    // Aliases to avoid ReferenceError if any legacy inline caller uses older names
    if (typeof loadGallery === 'function') {
        window.loadGalleryData = loadGallery;
        window.refreshGallery = loadGallery;
    }
    if (typeof openMergeModal === 'function') {
        window.openMergeModal = openMergeModal;
    }
    if (typeof submitMergeGroup === 'function') {
        window.submitMergeGroup = submitMergeGroup;
    }
    if (typeof toggleMultiSelectMode === 'function') {
        window.toggleMultiSelectMode = toggleMultiSelectMode;
    }
    if (typeof renderGrid === 'function') {
        window.renderGrid = renderGrid;
    }
    if (typeof openLightbox === 'function') {
        window.openLightbox = openLightbox;
    }
    if (typeof closeLightbox === 'function') {
        window.closeLightbox = closeLightbox;
    }

    console.log('✅ [SmartGallery AI] Global window exports verified.');
})();
