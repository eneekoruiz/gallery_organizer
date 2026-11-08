/**
 * Grid & Media Cards Module
 * Handles zero-overlap responsive grid rendering, infinite chunk scrolling,
 * and media badge indicators.
 */

export const GRID_CONFIG = {
    PAGE_SIZE: 60,
    ASPECT_RATIO: '1 / 1',
    GAP_MOBILE: '8px',
    GAP_DESKTOP: '12px'
};

export function setupZeroOverlapGrid(container) {
    if (!container) return;
    container.style.display = 'grid';
    container.style.gridAutoRows = 'max-content';
    const isMobile = window.innerWidth <= 820;
    container.style.gridTemplateColumns = isMobile 
        ? 'repeat(2, minmax(0, 1fr))' 
        : 'repeat(auto-fill, minmax(var(--grid-col-min, 180px), 1fr))';
    container.style.gap = isMobile ? GRID_CONFIG.GAP_MOBILE : GRID_CONFIG.GAP_DESKTOP;
}

export function formatCardSquare(card, img) {
    if (card) {
        card.style.width = '100%';
        card.style.display = 'block';
        card.style.position = 'relative';
        card.style.aspectRatio = GRID_CONFIG.ASPECT_RATIO;
        card.style.overflow = 'hidden';
    }
    if (img) {
        img.style.position = 'absolute';
        img.style.inset = '0';
        img.style.width = '100%';
        img.style.height = '100%';
        img.style.aspectRatio = GRID_CONFIG.ASPECT_RATIO;
        img.style.objectFit = 'cover';
        img.style.display = 'block';
    }
}
