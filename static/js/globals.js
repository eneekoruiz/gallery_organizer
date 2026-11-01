// Global application state variables
window.fullGallery = null;
window.currentCat = null;
window.currentIdent = null;
window.currentFolderItems = [];
window.currentItemIndex = 0;
window.currentFileObj = null;
window.isMultiSelectMode = false;
window.selectedFiles = new Set();
window.triageMatchesCache = [];
window._galleryFirstLoadDone = false;

// Zero-network dependency inline SVG person placeholder
window.INLINE_PERSON_SVG = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23636366'%3E%3Cpath d='M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z'/%3E%3C/svg%3E";