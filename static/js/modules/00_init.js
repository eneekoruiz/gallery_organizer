/**
 * SmartGallery AI - Global Error Boundaries & Safety Interceptor
 * Module: static/js/modules/00_init.js
 */

window.SmartGallery = window.SmartGallery || {};
window.SmartGallery.version = "20261111_v62_modular";

// Global error boundary for async handlers to prevent white-screen crashes
window.addEventListener('unhandledrejection', function(event) {
    console.warn('[SmartGallery Async Boundary] Handled promise rejection:', event.reason);
    if (typeof window.showToast === 'function' && event.reason && event.reason.message) {
        // Suppress non-critical aborts
        if (event.reason.name !== 'AbortError') {
            console.warn('[SmartGallery] Non-critical background event:', event.reason.message);
        }
    }
});

console.log('🚀 [SmartGallery AI] Modular architecture initialized.');
