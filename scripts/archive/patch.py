import os

file_path = r"C:\Users\User\Desktop\Eneko\smart_gallery_app\templates\index.html"
with open(file_path, "r", encoding="utf-8") as f:
    html = f.read()

# 1. Settings gear button
settings_btn = """
        <div style="margin-bottom: 20px; font-weight: bold; color: #8e8e93; text-align: center; border: 1px solid #8e8e93; border-radius: 8px; padding: 10px; cursor: pointer; background: rgba(142,142,147,0.1);" onclick="openSetupModal()">
            ⚙️ Configuración
        </div>
"""
if "openSetupModal()" not in html:
    html = html.replace(
        'onclick="openSimilarPhotosModal()">\n            📸 Fotos Parecidas y Ráfagas\n        </div>',
        'onclick="openSimilarPhotosModal()">\n            📸 Fotos Parecidas y Ráfagas\n        </div>' + settings_btn
    )

# 2. PWA manifest link in <head> and SW script before </body>
manifest_link = '    <link rel="manifest" href="/static/manifest.json">\n'
if "manifest.json" not in html:
    html = html.replace('</head>', manifest_link + '</head>')

sw_script = "<script>if('serviceWorker' in navigator){navigator.serviceWorker.register('/static/sw.js')}</script>\n"
if "serviceWorker" not in html:
    html = html.replace('</body>', sw_script + '</body>')

# 3. Semantic search
html = html.replace(
    'oninput="filterGallery(this.value)"',
    'oninput="semanticSearch(this.value)"'
)
semantic_script = """
<script>
async function semanticSearch(term) {
    if (term.length < 2) {
        if(typeof filterGallery === 'function') filterGallery(term);
        return;
    }
    try {
        const res = await fetch('/api/search/semantic?q=' + encodeURIComponent(term));
        const data = await res.json();
        
        document.getElementById('gallery-title').textContent = 'Resultados Búsqueda Semántica';
        document.getElementById('gallery-subtitle').textContent = `"${term}"`;
        currentCat = 'Búsqueda Semántica';
        
        const grid = document.getElementById('grid-container');
        grid.innerHTML = '';
        currentPhotos = data;
        
        data.forEach((photo, idx) => {
            const card = document.createElement('div');
            card.className = 'media-card';
            card.innerHTML = `<img src="/api/media/${photo.filename}" loading="lazy" onclick="openLightbox(${idx})">`;
            grid.appendChild(card);
        });
    } catch(e) {
        console.error(e);
    }
}
</script>
"""
if "function semanticSearch" not in html:
    html = html.replace('</body>', semantic_script + '</body>')

# 4. Timeline Slider
timeline_html = """
<div style="margin-top: 15px; width: 100%;">
    <input type="range" id="timeline-slider" min="2014" max="2026" value="2026" 
           style="width: 100%; cursor: pointer; accent-color: #0a84ff;" 
           onchange="filterTimeline(this.value)">
    <div style="text-align: center; color: #8e8e93; font-size: 14px; margin-top: 5px;" id="timeline-display">2026</div>
</div>
<script>
async function filterTimeline(year) {
    document.getElementById('timeline-display').textContent = year;
    try {
        const res = await fetch(`/api/timeline?year=${year}`);
        const data = await res.json();
        
        document.getElementById('gallery-title').textContent = `Fotos del Año ${year}`;
        document.getElementById('gallery-subtitle').textContent = `${data.length} elementos`;
        currentCat = `Año ${year}`;
        
        const grid = document.getElementById('grid-container');
        grid.innerHTML = '';
        currentPhotos = data;
        
        data.forEach((photo, idx) => {
            const card = document.createElement('div');
            card.className = 'media-card';
            card.innerHTML = `<img src="/api/media/${photo.filename}" loading="lazy" onclick="openLightbox(${idx})">`;
            grid.appendChild(card);
        });
    } catch(e) {
        console.error(e);
    }
}
</script>
"""
if "filterTimeline" not in html:
    html = html.replace(
        '<!-- Toggle Solo vs Acompañado -->',
        timeline_html + '\n                        <!-- Toggle Solo vs Acompañado -->'
    )

# 5. Map button in sidebar & Leaflet
leaflet_head = """
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
"""
if "leaflet.css" not in html:
    html = html.replace('</head>', leaflet_head + '</head>')

map_btn = """
        <div style="margin-bottom: 20px; font-weight: bold; color: #32ade6; text-align: center; border: 1px solid #32ade6; border-radius: 8px; padding: 10px; cursor: pointer; background: rgba(50,173,230,0.1);" onclick="openMapModal()">
            🗺️ Mapa
        </div>
"""
if "openMapModal()" not in html:
    html = html.replace(
        '⚙️ Configuración\n        </div>',
        '⚙️ Configuración\n        </div>' + map_btn
    )

map_modal = """
    <div id="modal-map" class="lightbox hidden" style="z-index: 3000;">
        <div style="background-color: #1c1c1e; padding: 20px; border-radius: 12px; width: 80%; height: 80%; color: white; border: 1px solid #333; position: relative; display: flex; flex-direction: column;">
            <button onclick="document.getElementById('modal-map').classList.add('hidden')" style="position: absolute; top: 10px; right: 10px; background: none; border: none; color: white; font-size: 24px; cursor: pointer; z-index: 4000;">✕</button>
            <h2 style="margin-top: 0; color: #32ade6; text-align: center;">🗺️ Mapa de Fotos</h2>
            <div id="map-container" style="flex: 1; border-radius: 8px; overflow: hidden; background: #000;"></div>
        </div>
    </div>
    <script>
    let mapInstance = null;
    async function openMapModal() {
        document.getElementById('modal-map').classList.remove('hidden');
        if (!mapInstance) {
            mapInstance = L.map('map-container').setView([40.4168, -3.7038], 5);
            L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                attribution: '&copy; OpenStreetMap contributors &copy; CARTO'
            }).addTo(mapInstance);
        }
        
        try {
            const res = await fetch('/api/map/locations');
            const locations = await res.json();
            locations.forEach(loc => {
                L.marker([loc.lat, loc.lon]).addTo(mapInstance).bindPopup(`<img src="/api/media/${loc.filename}" style="width:100px;">`);
            });
        } catch(e) {
            console.error(e);
        }
    }
    </script>
"""
if "modal-map" not in html:
    html = html.replace('</body>', map_modal + '</body>')

# 6. Face Evolution button
if "openEvolutionModal" not in html:
    html = html.replace(
        '<div class="person-name" id="pname-${faceNum}">#${faceNum} ${face.identity}</div>',
        """<div class="person-name" id="pname-${faceNum}" style="display:flex; justify-content:space-between; align-items:center;">
                            <span>#${faceNum} ${face.identity}</span>
                            <button onclick="openEvolutionModal('${face.identity}'); event.stopPropagation();" style="background:#0a84ff; border:none; color:white; border-radius:4px; padding:2px 6px; font-size:10px; cursor:pointer;">📈 Evolución</button>
                        </div>"""
    )
    
    evo_modal = """
    <!-- Evolution Modal -->
    <div id="modal-evolution" class="lightbox hidden" style="z-index: 3000;">
        <div style="background-color: #1c1c1e; padding: 20px; border-radius: 12px; width: 90%; max-width: 1000px; color: white; border: 1px solid #333; position: relative;">
            <button onclick="document.getElementById('modal-evolution').classList.add('hidden')" style="position: absolute; top: 10px; right: 10px; background: none; border: none; color: white; font-size: 24px; cursor: pointer; z-index: 4000;">✕</button>
            <h2 id="evolution-title" style="margin-top: 0; color: #0a84ff; text-align: center;">📈 Evolución de</h2>
            <div id="evolution-container" style="display: flex; overflow-x: auto; gap: 10px; padding: 10px; background: #000; border-radius: 8px; align-items: center; min-height: 200px;">
            </div>
        </div>
    </div>
    <script>
    async function openEvolutionModal(identity) {
        if (!identity || identity === 'Desconocido' || identity === 'Ignorado') return;
        document.getElementById('evolution-title').textContent = `📈 Evolución de ${identity}`;
        document.getElementById('modal-evolution').classList.remove('hidden');
        document.getElementById('evolution-container').innerHTML = '<div class="loader-small" style="margin: auto;"></div>';
        
        try {
            const res = await fetch(`/api/person/evolution?identity=${encodeURIComponent(identity)}`);
            const data = await res.json();
            
            const container = document.getElementById('evolution-container');
            container.innerHTML = '';
            if (data.length === 0) {
                container.innerHTML = '<p style="margin:auto;">No hay suficientes datos</p>';
                return;
            }
            
            data.forEach(item => {
                const div = document.createElement('div');
                div.style.cssText = 'flex: 0 0 auto; text-align: center;';
                div.innerHTML = `
                    <img src="/api/media/${item.filename}" style="height: 150px; border-radius: 8px; object-fit: cover;">
                    <div style="font-size: 12px; margin-top: 5px; color: #aaa;">${item.year}</div>
                `;
                container.appendChild(div);
            });
        } catch(e) {
            console.error(e);
            document.getElementById('evolution-container').innerHTML = '<p style="color:red; margin:auto;">Error cargando evolución</p>';
        }
    }
    </script>
"""
    html = html.replace('</body>', evo_modal + '</body>')

# 7. Quick Clean functions
quick_clean_script = """
<script>
    async function loadCategoryFilter(category, identity) {
        try {
            const res = await fetch(`/api/gallery?category=${encodeURIComponent(category)}&identity=${encodeURIComponent(identity)}`);
            const data = await res.json();
            
            document.getElementById('gallery-title').textContent = identity;
            document.getElementById('gallery-subtitle').textContent = category;
            currentCat = category;
            currentIdent = identity;
            
            const grid = document.getElementById('grid-container');
            grid.innerHTML = '';
            currentPhotos = data;
            
            data.forEach((photo, idx) => {
                const card = document.createElement('div');
                card.className = 'media-card';
                card.innerHTML = `<img src="/api/media/${photo.filename}" loading="lazy" onclick="openLightbox(${idx})">`;
                grid.appendChild(card);
            });
        } catch(e) {
            console.error(e);
        }
    }

    function openQuickCleanOverlay() {
        if (typeof isSwipeModeActive !== 'undefined' && !isSwipeModeActive) {
            if(typeof toggleSwipeMode === 'function') toggleSwipeMode();
        }
        
        let banner = document.getElementById('quick-clean-banner');
        if (!banner) {
            banner = document.createElement('div');
            banner.id = 'quick-clean-banner';
            banner.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; background: #ff9f0a; color: white; text-align: center; font-weight: bold; padding: 10px; z-index: 9999; box-shadow: 0 4px 10px rgba(0,0,0,0.5);';
            banner.innerHTML = '🔥 Modo Limpieza Rápida - Desliza para limpiar <button onclick="this.parentElement.remove()" style="margin-left:20px; background:black; color:white; border:none; padding:4px 8px; border-radius:4px; cursor:pointer;">Cerrar</button>';
            document.body.appendChild(banner);
        }
    }
</script>
"""
if "function loadCategoryFilter" not in html:
    html = html.replace('</body>', quick_clean_script + '</body>')


with open(file_path, "w", encoding="utf-8") as f:
    f.write(html)

print("Patch applied successfully.")
