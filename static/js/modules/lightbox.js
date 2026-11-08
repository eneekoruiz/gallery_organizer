/**
 * Lightbox & Photo Viewer Module
 * Handles touch gestures, pinch-to-zoom, and keep-in-place updates on face reassignment.
 */

export function preserveLightboxPosition(currentIndex, totalItems) {
    if (currentIndex >= totalItems) {
        return Math.max(0, totalItems - 1);
    }
    return Math.max(0, currentIndex);
}
