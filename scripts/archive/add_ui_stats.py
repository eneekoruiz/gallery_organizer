import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Add Stats button to sidebar
sidebar_btn = '''
        <div style="margin-top: 20px; font-weight: bold; color: #ffcc00; text-align: center; border: 1px solid #ffcc00; border-radius: 8px; padding: 10px; cursor: pointer; background: rgba(255,204,0,0.1);" onclick="openStatsModal()">
            📊 Estadísticas
        </div>
        <div style="margin-top: 10px; margin-bottom: 20px; font-weight: bold; color: #0a84ff; text-align: center; border: 1px solid #0a84ff; border-radius: 8px; padding: 10px; cursor: pointer; background: rgba(10,132,255,0.1);" onclick="openIntelligentCleanup()">
            🧠 Limpieza Inteligente
        </div>
'''

sidebar_target = '<aside class="sidebar">'
if sidebar_target in content:
    content = content.replace(sidebar_target, sidebar_target + sidebar_btn)
else:
    print("Could not find sidebar target")

# Add Stats modal to body
stats_modal = '''
    <!-- STATS MODAL -->
    <div id="stats-modal" class="lightbox hidden" style="z-index: 2000;">
        <div style="background-color: #1e1e1e; padding: 30px; border-radius: 12px; width: 400px; max-width: 90%; color: white; border: 1px solid #333; position: relative;">
            <button onclick="document.getElementById('stats-modal').classList.add('hidden')" style="position: absolute; top: 10px; right: 10px; background: none; border: none; color: white; font-size: 20px; cursor: pointer;">✕</button>
            <h2 style="margin-top: 0; color: #ffcc00; text-align: center;">📊 Estadísticas globales</h2>
            
            <div id="stats-content" style="font-size: 16px; line-height: 1.8;">
                <div style="text-align: center; padding: 20px;"><div class="loader-small"></div></div>
            </div>
        </div>
    </div>
'''

body_target = '<body>'
if body_target in content:
    content = content.replace(body_target, body_target + stats_modal)
else:
    print("Could not find body target")

# Add JS functions for stats and intelligent cleanup
js_functions = '''
        async function openStatsModal() {
            document.getElementById('stats-modal').classList.remove('hidden');
            document.getElementById('stats-content').innerHTML = '<div style="text-align: center; padding: 20px;"><div class="loader-small"></div></div>';
            
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                
                if (data.error) {
                    document.getElementById('stats-content').innerHTML = `<p style="color:red">${data.error}</p>`;
                    return;
                }
                
                const percentage = data.total > 0 ? Math.round((data.clasificadas / data.total) * 100) : 0;
                
                document.getElementById('stats-content').innerHTML = `
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span>Total de elementos (caras detectadas):</span>
                        <strong>${data.total}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px; color: #30d158;">
                        <span>Clasificadas (Conocidos):</span>
                        <strong>${data.clasificadas}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 20px; color: #ff9f0a;">
                        <span>Pendientes por ordenar:</span>
                        <strong>${data.pendientes}</strong>
                    </div>
                    
                    <div style="width: 100%; background-color: #333; border-radius: 10px; height: 20px; overflow: hidden;">
                        <div style="width: ${percentage}%; background-color: #30d158; height: 100%; text-align: center; font-size: 12px; line-height: 20px; color: black; font-weight: bold;">
                            ${percentage}%
                        </div>
                    </div>
                    <div style="text-align: center; font-size: 12px; color: #aaa; margin-top: 5px;">Progreso de clasificación</div>
                `;
            } catch(e) {
                document.getElementById('stats-content').innerHTML = `<p style="color:red">Error cargando estadísticas.</p>`;
            }
        }
        
        async function openIntelligentCleanup() {
            document.getElementById('gallery-title').textContent = '🧠 Limpieza Inteligente (Fáciles a Difíciles)';
            document.getElementById('gallery-subtitle').textContent = 'Analizando confianza de la IA... (Esto tardará dependiendo del número de fotos)';
            document.getElementById('grid-container').innerHTML = '<div style="padding:50px; text-align:center;"><div class="loader-small" style="width:50px; height:50px; margin:auto;"></div><p style="margin-top:20px; color:#aaa;">Extrayendo y puntuando caras de todas las pendientes...<br>Por favor, espera sin cerrar la página.</p></div>';
            
            try {
                const res = await fetch('/api/pending_sorted');
                const data = await res.json();
                
                if (data.error) {
                    showToast(data.error, true);
                    document.getElementById('grid-container').innerHTML = '';
                    return;
                }
                
                currentCat = "Limpieza Inteligente";
                currentIdent = "Pendientes Ordenadas";
                currentFolderItems = data.items;
                
                document.getElementById('gallery-subtitle').textContent = `${currentFolderItems.length} caras pendientes encontradas`;
                
                const grid = document.getElementById('grid-container');
                grid.innerHTML = '';
                
                currentFolderItems.forEach((item, idx) => {
                    const card = document.createElement('div');
                    card.className = 'media-card';
                    card.onclick = () => {
                        currentItemIndex = idx;
                        openLightbox(item);
                    };
                    
                    const badge = document.createElement('span');
                    if (item.confidence > 0) {
                        const confPct = (item.confidence * 100).toFixed(1);
                        badge.className = 'badge badge-ia';
                        badge.textContent = `🤖 ${confPct}%`;
                        if (item.confidence > 0.8) {
                            badge.style.backgroundColor = '#30d158'; // Verde
                            badge.style.color = '#000';
                        } else if (item.confidence > 0.5) {
                            badge.style.backgroundColor = '#ff9f0a'; // Naranja
                            badge.style.color = '#000';
                        } else {
                            badge.style.backgroundColor = '#ff453a'; // Rojo
                        }
                    } else {
                        badge.className = 'badge badge-manual';
                        badge.textContent = '❌ Desconocido';
                        badge.style.backgroundColor = '#555';
                    }
                    card.appendChild(badge);
                    
                    if (item.type === 'video') {
                        const video = document.createElement('video');
                        video.src = `/media?path=${encodeURIComponent(item.path)}#t=0.5`;
                        video.preload = 'metadata';
                        card.appendChild(video);
                        const playIcon = document.createElement('div');
                        playIcon.className = 'play-icon';
                        playIcon.textContent = '▶';
                        card.appendChild(playIcon);
                    } else {
                        const img = document.createElement('img');
                        img.src = `/media?path=${encodeURIComponent(item.path)}`;
                        img.loading = 'lazy';
                        card.appendChild(img);
                    }
                    
                    const title = document.createElement('div');
                    title.className = 'media-title';
                    title.textContent = item.name;
                    card.appendChild(title);
                    
                    grid.appendChild(card);
                });
                
            } catch(e) {
                showToast("Error cargando limpieza inteligente", true);
                document.getElementById('grid-container').innerHTML = '';
            }
        }
'''

js_target = 'async function loadGallery()'
if js_target in content:
    content = content.replace(js_target, js_functions + '\n        ' + js_target)
else:
    print("Could not find JS target")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Added UI buttons and modals to index.html successfully.")
