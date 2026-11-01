// ============================================================
// LIGHTBOX.JS - Media Viewer, Gestures & Full Action Controls
// ============================================================

let isCurrentVideo = false;
let currentFileObj = null;
let currentItemIndex = 0;
let currentRotation = 0;
let currentZoom = 1.0;

window.isCurrentVideo = isCurrentVideo;
window.currentFileObj = currentFileObj;
window.currentItemIndex = currentItemIndex;

async function openLightbox(item) {
    if (!item) return;
    currentRotation = 0;
    currentZoom = 1.0;
    
    currentFileObj = item;
    window.currentFileObj = item;
    isCurrentVideo = item.type === 'video' || (item.path && item.path.match(/\.(mp4|mov|avi|mkv)$/i));
    window.isCurrentVideo = isCurrentVideo;
    
    const container = document.getElementById('lb-media-container');
    if (container) {
        container.innerHTML = '';
        container.style.transform = 'none';
    }
    
    const lb = document.getElementById('lightbox');
    if (lb) {
        lb.classList.remove('hidden');
        lb.style.display = 'flex';
    }

    const titleEl = document.getElementById('lb-filename');
    if (titleEl) titleEl.textContent = item.name || '';
    
    const zoomDisp = document.getElementById('lb-zoom-display');
    if (zoomDisp) zoomDisp.textContent = '100%';

    const cardsContainer = document.getElementById('person-cards-container') || document.getElementById('lb-faces-list');
    if (cardsContainer) {
        cardsContainer.innerHTML = '<div style="color:#64d2ff; font-size:12px; padding:15px; text-align:center;"><div class="loader-small" style="margin:0 auto 8px auto;"></div>Escaneando rostros con IA...</div>';
    }

    if (isCurrentVideo) {
        const video = document.createElement('video');
        video.className = 'lb-media-element';
        video.src = `/api/media?path=${encodeURIComponent(item.path)}`;
        video.controls = true;
        video.autoplay = true;
        video.style.cssText = 'max-width:100%; max-height:100%; object-fit:contain; border-radius:8px;';
        if (container) container.appendChild(video);
        if (cardsContainer) {
            cardsContainer.innerHTML = '<div style="color:#8e8e93; font-size:12px; padding:20px; text-align:center;">🎬 Archivo de vídeo.</div>';
        }
    } else {
        const img = document.createElement('img');
        img.className = 'lb-media-element';
        img.src = `/api/media?path=${encodeURIComponent(item.path)}`;
        img.style.cssText = 'max-width:100%; max-height:100%; object-fit:contain; border-radius:8px; transition:transform 0.15s ease;';
        img.onload = () => {
            if (window.triggerDeepScanLightbox) {
                window.triggerDeepScanLightbox(img, container, cardsContainer);
            }
        };
        if (container) container.appendChild(img);
    }

    // Auto-update counter
    updateLightboxCounter();
}

function updateLightboxCounter() {
    const counter = document.getElementById('lb-counter');
    if (!counter || !window.currentFolderItems || window.currentFolderItems.length === 0) return;
    const items = window.currentFolderItems;
    const idx = items.findIndex(p => p.path === (currentFileObj ? currentFileObj.path : ''));
    if (idx !== -1) {
        counter.textContent = `${idx + 1} / ${items.length}`;
    }
}

function closeLightbox() {
    const lb = document.getElementById('lightbox');
    if (lb) {
        lb.classList.add('hidden');
        lb.style.display = 'none';
    }
    const container = document.getElementById('lb-media-container');
    if (container) {
        const media = container.querySelector('video, img');
        if (media && media.tagName === 'VIDEO') {
            media.pause();
            media.src = '';
        }
        container.innerHTML = '';
    }
    currentFileObj = null;
    window.currentFileObj = null;
}

function navigateLightbox(direction) {
    const items = (window.currentFolderItems && window.currentFolderItems.length > 0) ? window.currentFolderItems : [];
    if (!items || items.length === 0 || !currentFileObj) return;
    const currentIdx = items.findIndex(p => p.path === currentFileObj.path);
    if (currentIdx === -1) return;
    
    const nextIdx = (currentIdx + direction + items.length) % items.length;
    openLightbox(items[nextIdx]);
}

function zoomInLightbox() {
    currentZoom = Math.min(4.0, currentZoom + 0.25);
    applyMediaTransform();
}

function zoomOutLightbox() {
    currentZoom = Math.max(0.5, currentZoom - 0.25);
    applyMediaTransform();
}

function toggleZoomStep() {
    if (currentZoom === 1.0) currentZoom = 2.0;
    else if (currentZoom === 2.0) currentZoom = 4.0;
    else currentZoom = 1.0;
    applyMediaTransform();
}

function rotateLightbox() {
    currentRotation = (currentRotation + 90) % 360;
    applyMediaTransform();
}

function applyMediaTransform() {
    const media = document.querySelector('#lb-media-container img, #lb-media-container video');
    if (media) {
        media.style.transform = `scale(${currentZoom}) rotate(${currentRotation}deg)`;
    }
    const zoomDisp = document.getElementById('lb-zoom-display');
    if (zoomDisp) {
        zoomDisp.textContent = `${Math.round(currentZoom * 100)}%`;
    }
}

function shareCurrentPhoto() {
    if (!currentFileObj || !currentFileObj.path) return;
    const url = `${window.location.origin}/api/media?path=${encodeURIComponent(currentFileObj.path)}`;
    if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(() => {
            if (typeof showToast === 'function') showToast('🔗 ¡Enlace de imagen copiado al portapapeles!');
        }).catch(() => {
            prompt("Copia el enlace:", url);
        });
    } else {
        prompt("Copia el enlace:", url);
    }
}

function deleteCurrentFile() {
    if (!currentFileObj || !currentFileObj.path) return;
    const name = currentFileObj.name || 'esta foto';
    if (!confirm(`¿Deseas descartar/eliminar ${name}?`)) return;
    
    fetch('/api/delete_media', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ path: currentFileObj.path })
    }).then(r => r.json()).then(data => {
        if (data.success) {
            if (typeof showToast === 'function') showToast('🗑️ Foto descartada con éxito');
            // Remove from memory
            if (window.currentFolderItems) {
                window.currentFolderItems = window.currentFolderItems.filter(p => p.path !== currentFileObj.path);
            }
            if (window.currentFolderItems && window.currentFolderItems.length > 0) {
                navigateLightbox(1);
            } else {
                closeLightbox();
            }
            if (typeof loadGallery === 'function') loadGallery();
        } else {
            if (typeof showToast === 'function') showToast('Error al descartar la foto', true);
        }
    }).catch(() => {
        if (typeof showToast === 'function') showToast('Error de conexión', true);
    });
}

// Global Keyboard Handler
document.addEventListener('keydown', (e) => {
    const lb = document.getElementById('lightbox');
    if (!lb || lb.style.display === 'none' || lb.classList.contains('hidden')) return;

    if (e.key === 'Escape') {
        closeLightbox();
    } else if (e.key === 'ArrowRight') {
        navigateLightbox(1);
    } else if (e.key === 'ArrowLeft') {
        navigateLightbox(-1);
    } else if (e.key === 'Delete' || e.key === 'Backspace') {
        deleteCurrentFile();
    } else if (e.key === '+' || e.key === '=') {
        zoomInLightbox();
    } else if (e.key === '-') {
        zoomOutLightbox();
    }
});

// Window Bindings
window.openLightbox = openLightbox;
window.closeLightbox = closeLightbox;
window.navigateLightbox = navigateLightbox;
window.zoomInLightbox = zoomInLightbox;
window.zoomOutLightbox = zoomOutLightbox;
window.toggleZoomStep = toggleZoomStep;
window.rotateLightbox = rotateLightbox;
window.shareCurrentPhoto = shareCurrentPhoto;
window.deleteCurrentFile = deleteCurrentFile;
