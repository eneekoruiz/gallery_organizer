// ==========================================
// STATE.JS - Estado Global Reactivo de la Galería
// ==========================================

export const state = {
    currentCat: null,
    currentIdent: null,
    currentFolderItems: [],
    fullGallery: {},
    allIdentitiesList: [],
    
    // Lightbox & Visor
    currentFileObj: null,
    currentRunPath: null,
    isCurrentVideo: false,
    currentFaces: [],
    selectedBoxId: null,
    isDrawingMode: false,
    isPanning: false,
    
    // Zoom & Pan
    zoomLevel: 1.0,
    panX: 0,
    panY: 0,
    
    // Filtros de Galería
    currentPhotoFilter: 'all', // 'all', 'solo', 'group', 'with_me', 'without_me'
    multiSelectActive: false,
    selectedPhotos: new Set()
};

export function resetZoomState() {
    state.zoomLevel = 1.0;
    state.panX = 0;
    state.panY = 0;
}

export function safeFloat(val, fallback = 0.0) {
    if (val === undefined || val === null || val === '' || val === 'undefined' || val === 'null' || val === 'NaN') {
        return fallback;
    }
    const parsed = parseFloat(val);
    return isNaN(parsed) ? fallback : parsed;
}
