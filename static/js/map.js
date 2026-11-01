// ============================================================
// MAP.JS - Geographic Map & Events Visualizer with Leaflet
// ============================================================

let eventsMapInstance = null;

async function openEventsMapModal() {
    const modal = document.getElementById('modal-events-map');
    if (!modal) return;
    modal.style.display = 'flex';
    
    document.querySelectorAll('.nav-tab-item').forEach(b => b.classList.remove('active'));
    const mapTab = document.getElementById('nav-btn-map');
    if (mapTab) mapTab.classList.add('active');
    
    setTimeout(() => {
        initEventsMap();
    }, 150);
}

function closeEventsMapModal() {
    const modal = document.getElementById('modal-events-map');
    if (modal) modal.style.display = 'none';
    document.querySelectorAll('.nav-tab-item').forEach(b => b.classList.remove('active'));
    const galTab = document.getElementById('nav-btn-gallery');
    if (galTab) galTab.classList.add('active');
}

async function initEventsMap() {
    const mapContainer = document.getElementById('events-map-container');
    if (!mapContainer) return;
    
    if (!eventsMapInstance) {
        if (typeof L === 'undefined') {
            mapContainer.innerHTML = '<div style="padding:40px; text-align:center; color:#ff453a;">Leaflet Map no disponible en este momento.</div>';
            return;
        }
        eventsMapInstance = L.map('events-map-container', {
            zoomControl: true,
            attributionControl: false
        }).setView([43.5, 4.0], 4);
        
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            maxZoom: 19,
            subdomains: 'abcd'
        }).addTo(eventsMapInstance);
    }
    
    eventsMapInstance.invalidateSize();
    
    try {
        const res = await fetch('/api/map/locations');
        const data = await res.json();
        const locations = data.locations || [];
        
        if (window.mapMarkersGroup) {
            eventsMapInstance.removeLayer(window.mapMarkersGroup);
        }
        window.mapMarkersGroup = L.layerGroup().addTo(eventsMapInstance);
        
        const eventsListContent = document.getElementById('events-list-content');
        if (eventsListContent) eventsListContent.innerHTML = '';
        
        const bounds = [];
        const folderGroups = {};
        
        locations.forEach(loc => {
            if (loc.lat && loc.lng) {
                bounds.push([loc.lat, loc.lng]);
                const folder = loc.folder || 'UbicaciÃ³n';
                if (!folderGroups[folder]) folderGroups[folder] = [];
                folderGroups[folder].push(loc);
                
                const customIcon = L.divIcon({
                    className: 'custom-map-pin',
                    html: `<div style="width:14px; height:14px; background:#0a84ff; border:2px solid white; border-radius:50%; box-shadow:0 0 10px rgba(10,132,255,0.8);"></div>`,
                    iconSize: [14, 14],
                    iconAnchor: [7, 7]
                });
                
                const marker = L.marker([loc.lat, loc.lng], { icon: customIcon }).addTo(window.mapMarkersGroup);
                const popupHtml = `
                    <div style="font-family:-apple-system,sans-serif; color:#222; text-align:center; max-width:180px;">
                        <img src="/api/thumbnail?path=${encodeURIComponent(loc.path)}" style="width:100%; height:110px; object-fit:cover; border-radius:6px; margin-bottom:6px; box-shadow:0 2px 6px rgba(0,0,0,0.2);">
                        <div style="font-weight:700; font-size:12px; margin-bottom:2px;">${loc.folder || loc.name}</div>
                        <div style="font-size:10px; color:#666;">${loc.source || 'GPS'}</div>
                    </div>
                `;
                marker.bindPopup(popupHtml);
            }
        });
        
        if (bounds.length > 0) {
            eventsMapInstance.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
        }
        
        if (eventsListContent) {
            const eventKeys = Object.keys(folderGroups);
            if (eventKeys.length === 0) {
                eventsListContent.innerHTML = '<p style="color:#aaa; text-align:center; padding:30px;">No se han detectado Ã¡lbumes con coordenadas.</p>';
            } else {
                eventKeys.forEach(fName => {
                    const items = folderGroups[fName];
                    const sample = items[0];
                    const card = document.createElement('div');
                    card.style.cssText = 'background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); border-radius:12px; padding:12px; display:flex; align-items:center; gap:14px; cursor:pointer; transition:all 0.2s;';
                    card.onmouseover = () => card.style.background = 'rgba(255,255,255,0.1)';
                    card.onmouseout = () => card.style.background = 'rgba(255,255,255,0.05)';
                    card.onclick = () => {
                        closeEventsMapModal();
                        if (typeof renderGrid === 'function') renderGrid('Eventos', fName);
                    };
                    
                    card.innerHTML = `
                        <img src="/api/thumbnail?path=${encodeURIComponent(sample.path)}" style="width:64px; height:64px; border-radius:8px; object-fit:cover;">
                        <div style="flex:1;">
                            <div style="font-weight:700; font-size:14px; color:#fff;">${fName}</div>
                            <div style="font-size:12px; color:#0a84ff; margin-top:2px;">ðŸ“ ${sample.source || 'UbicaciÃ³n'}</div>
                            <div style="font-size:11px; color:#8e8e93; margin-top:2px;">${items.length} fotos registradas</div>
                        </div>
                        <div style="color:#0a84ff; font-size:18px;">&rsaquo;</div>
                    `;
                    eventsListContent.appendChild(card);
                });
            }
        }
    } catch(err) {}
}

function openMapModal(path) {
    openEventsMapModal();
}

window.openEventsMapModal = openEventsMapModal;
window.closeEventsMapModal = closeEventsMapModal;
window.initEventsMap = initEventsMap;
window.openMapModal = openMapModal;