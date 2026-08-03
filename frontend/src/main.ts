// @ts-nocheck
import './store';
import './api';
import './ui/grid';

// The original main.js content starts here
// ===== Shared global state =====

function isStableDataset(category, identity) {
    const cat = (category || '').toLowerCase();
    const ident = (identity || '').toLowerCase();
    
    if (cat === 'personas sin nombre' || cat === '_dudosos' || cat === 'falsos_positivos' || cat === 'revision_interactiva') {
        if (!identity) return false;
    }
    if (ident.startsWith('persona nueva') || ident.includes('desconocid') || ident === 'ignorado' || ident === 'falso_positivo') {
        return false;
    }
    return true;
}

var fullGallery = {};
var identitiesList = [];
var currentCat = null;
var currentIdent = null;


function cleanDisplayName(name) {
    if (!name) return 'Desconocido';
    return name.replace(/_rejected/g, '').replace(/Falso_Positivo/g, 'Descartado').replace(/Ignorar_Irrelevante/g, 'Descartado').replace(/_solitario/g, '').replace(/_compania/g, '').replace(/\/rejected/g, '').replace(/\/undefined/g, '').trim() || 'Desconocido';
}
async function filterTimeline(year) {
    document.getElementById('timeline-display').textContent = year;
    const targetYear = parseInt(year);
    
    if (currentFolderItems && currentFolderItems.length > 0) {
        const filtered = currentFolderItems.filter(item => {
            if (!item.mtime) return true;
            const itemYear = new Date(item.mtime * 1000).getFullYear();
            return itemYear === targetYear;
        });
        
        const sub = document.querySelector('#gallery-title #gallery-subtitle') || document.getElementById('gallery-subtitle');
        if (sub) {
            sub.textContent = `${filtered.length} de ${currentFolderItems.length} elementos en ${year}`;
        }
        
        const grid = document.getElementById('grid-container');
        if (!grid) return;
        grid.innerHTML = '';
        
        if (filtered.length === 0) {
            grid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #888;">
                <h3>No hay fotos registradas en el año ${year} para esta selección.</h3>
            </div>`;
            return;
        }
        
        filtered.forEach((item, idx) => {
            const card = document.createElement('div');
            card.className = 'media-card';
            card.style.position = 'relative';
            card.onclick = () => { currentItemIndex = idx; openLightbox(item); };
            
            const thumb = document.createElement('img');
            thumb.src = `/api/thumbnail?path=${encodeURIComponent(item.path)}`;
            thumb.loading = 'lazy';
            thumb.decoding = 'async';
            thumb.style.width = '100%';
            thumb.style.height = '100%';
            thumb.style.objectFit = 'cover';
            card.appendChild(thumb);
            
            const title = document.createElement('div');
            title.className = 'card-title';
            title.textContent = item.path ? item.path.split(/[\/]/).pop() : `Foto ${idx+1}`;
            card.appendChild(title);
            
            grid.appendChild(card);
        });
        return;
    }

    try {
        const res = await fetch(`/api/timeline?year=${year}`);
        const data = await res.json();
        
        const titleEl = document.getElementById('gallery-title');
        if (titleEl) titleEl.textContent = `Fotos del Año ${year}`;
        const subEl = document.getElementById('gallery-subtitle');
        if (subEl) subEl.textContent = `${data.length || 0} elementos en ${year}`;
        
        const grid = document.getElementById('grid-container');
        if (!grid) return;
        grid.innerHTML = '';
        
        const items = Array.isArray(data) ? data : [];
        if (items.length === 0) {
            grid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #888;">
                <h3>No hay fotos registradas en el año ${year}.</h3>
            </div>`;
            return;
        }
        
        items.forEach((item, idx) => {
            const card = document.createElement('div');
            card.className = 'media-card';
            card.style.position = 'relative';
            card.onclick = () => { currentItemIndex = idx; openLightbox(item); };
            
            const thumb = document.createElement('img');
            thumb.src = `/api/thumbnail?path=${encodeURIComponent(item.path)}`;
            thumb.loading = 'lazy';
            thumb.decoding = 'async';
            thumb.style.width = '100%';
            thumb.style.height = '100%';
            thumb.style.objectFit = 'cover';
            card.appendChild(thumb);
            
            const title = document.createElement('div');
            title.className = 'card-title';
            title.textContent = item.path ? item.path.split(/[\/]/).pop() : `Foto ${idx+1}`;
            card.appendChild(title);
            
            grid.appendChild(card);
        });
    } catch(e) {
        console.error("Error in timeline filter:", e);
    }
}



        let isMultiSelectMode = false;
        let selectedFiles = new Set();

        function toggleMultiSelectMode() {
            isMultiSelectMode = !isMultiSelectMode;
            const btn = document.getElementById('btn-toggle-multiselect');
            if (btn) {
                btn.style.background = isMultiSelectMode ? "#30d158" : "#5e5ce6";
                btn.innerHTML = isMultiSelectMode ? `<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zm-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z"/></svg> Selección Activa` : `<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M14 1a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h12zM2 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2H2z"/><path d="M10.97 4.97a.75.75 0 0 1 1.071 1.05l-3.992 4.99a.75.75 0 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425a.235.235 0 0 1 .02-.022z"/></svg> Selección Múltiple`;
            }
            if (!isMultiSelectMode) {
                clearBatchSelection();
            }
            if (typeof currentCat !== 'undefined' && typeof currentIdent !== 'undefined') {
                renderGrid(currentCat, currentIdent);
            }
            showToast(isMultiSelectMode ? "Modo Selección Múltiple ACTIVADO." : "Modo Selección Múltiple DESACTIVADO.");
        }

        function toggleFileSelection(filepath, cardEl, event) {
            if (event) event.stopPropagation();
            if (selectedFiles.has(filepath)) {
                selectedFiles.delete(filepath);
                cardEl.classList.remove('selected-card');
                cardEl.style.border = 'none';
                cardEl.style.boxShadow = 'none';
                const chk = cardEl.querySelector('.card-checkbox');
                if (chk) chk.checked = false;
            } else {
                selectedFiles.add(filepath);
                cardEl.classList.add('selected-card');
                cardEl.style.border = '3px solid #30d158';
                cardEl.style.boxShadow = '0 0 15px rgba(48,209,88,0.5)';
                const chk = cardEl.querySelector('.card-checkbox');
                if (chk) chk.checked = true;
            }
            updateBatchBar();
        }

        function updateBatchBar() {
            const bar = document.getElementById('batch-action-bar');
            const countEl = document.getElementById('batch-count');
            if (selectedFiles.size > 0) {
                bar.style.display = 'flex';
                countEl.textContent = `${selectedFiles.size} foto(s) seleccionada(s)`;
                
                const select = document.getElementById('batch-target-select');
                if (select && select.options.length <= 1 && typeof identitiesList !== 'undefined' && identitiesList.length > 0) {
                    select.innerHTML = '<option value="">Seleccionar carpeta destino...</option>';
                    identitiesList.forEach(id => {
                        const opt = document.createElement('option');
                        opt.value = JSON.stringify(id);
                        opt.textContent = `${id.categoria} > ${id.identidad}`;
                        select.appendChild(opt);
                    });
                }
            } else {
                bar.style.display = 'none';
            }
        }

        function clearBatchSelection() {
            selectedFiles.clear();
            document.querySelectorAll('.selected-card').forEach(el => {
                el.classList.remove('selected-card');
                el.style.border = 'none';
                el.style.boxShadow = 'none';
            });
            document.querySelectorAll('.card-checkbox').forEach(el => el.checked = false);
            updateBatchBar();
        }

        async function executeBatchMove() {
            if (selectedFiles.size === 0) return;
            const select = document.getElementById('batch-target-select');
            if (!select.value) {
                alert("Por favor, selecciona una carpeta destino.");
                return;
            }
            
            const target = JSON.parse(select.value);
            const filesArray = Array.from(selectedFiles);
            
            showToast(`<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M8 15s-1.5-1-1.5-3 1.5-3 1.5-3 1.5 1 1.5 3-1.5 3-1.5 3zm0-12s3 1.5 3 4.5c0 1.5-1 3-3 4.5C6 10.5 5 9 5 7.5 5 4.5 8 3 8 3z"/></svg> Moviendo ${filesArray.length} fotos y re-entrenando IA...`);
            
            try {
                const res = await fetch('/api/batch_move', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        files: filesArray,
                        target_cat: target.categoria,
                        target_ident: target.identidad
                    })
                });
                const data = await res.json();
                
                if (data.status === 'success') {
                    showToast(`<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zm-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z"/></svg> ${data.moved} fotos movidas a ${target.identidad}. ¡Rostro re-entrenado automáticamente!`);
                    clearBatchSelection();
                    await loadGallery();
                    renderGrid(currentCat, currentIdent);
                } else {
                    alert("Error: " + (data.error || "No se pudieron mover las fotos"));
                }
            } catch (err) {
                alert("Error de conexión: " + err.message);
            }
        }

        let currentFileObj = null;
        let isCurrentVideo = false;
        let currentFaces = [];


                function generateReassignHTML(face, faceNum, onchangeFuncName) {
            let pathParts = currentFileObj.path.split(/[\\/]/);
            let folderName = pathParts.slice(-2, -1)[0];
            let categoryName = pathParts.slice(-3, -2)[0];
            if (folderName === '_Dudosos') {
                folderName = pathParts.slice(-3, -2)[0];
                categoryName = pathParts.slice(-4, -3)[0];
            }
            
            let aiPredictedIdObj = null;
            if (face.identity && face.identity !== 'Desconocido' && face.identity !== folderName) {
                aiPredictedIdObj = identitiesList.find(id => id.identidad === face.identity);
            }
            
            let html = `<div class="custom-dropdown" style="position:relative; width:100%; text-align:left;">`;
            html += `<button class="custom-dropdown-btn" onclick="let menu = document.getElementById('menu-${faceNum}-${onchangeFuncName}'); menu.style.display = menu.style.display==='block'?'none':'block'; event.stopPropagation();" style="width:100%; padding:8px; border-radius:6px; background:#333; color:white; border:1px solid #555; cursor:pointer; text-align:left; font-size:14px; display:flex; justify-content:space-between;"><span>Reasignar persona...</span><span>▾</span></button>`;
            html += `<div class="custom-dropdown-menu" id="menu-${faceNum}-${onchangeFuncName}" style="display:none; position:absolute; top:100%; left:0; width:220px; max-height:280px; overflow-y:auto; background:#1c1c1e; border:1px solid #444; z-index:99999; border-radius:8px; padding:4px; margin-top:4px; box-shadow:0 10px 30px rgba(0,0,0,0.8);">`;
            
            const btnStyle = "display:block; width:100%; text-align:left; padding:8px 10px; background:transparent; border:none; color:white; cursor:pointer; border-radius:4px; font-size:13px; margin-bottom:2px; transition:background 0.2s;";
            const hoverScript = "onmouseover=\"this.style.background='#3a3a3c'\" onmouseout=\"this.style.background='transparent'\"";
            
            const makeBtn = (valObj, text, color="white", fontWeight="normal") => {
                let valStr = valObj === 'NEW' ? 'NEW' : JSON.stringify(valObj).replace(/"/g, '&quot;');
                let call = `${onchangeFuncName}('${valStr}', ${faceNum})`;
                return `<button style="${btnStyle} color:${color}; font-weight:${fontWeight};" ${hoverScript} onclick="document.getElementById('menu-${faceNum}-${onchangeFuncName}').style.display='none'; ${call}">${text}</button>`;
            };
            
            if (aiPredictedIdObj) {
                html += makeBtn(aiPredictedIdObj, `<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M6 12.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1h-3a.5.5 0 0 1-.5-.5ZM3 8.062C3 6.76 4.235 5.765 5.53 5.889a28.02 28.02 0 0 1 4.94 0C11.765 5.765 13 6.76 13 8.062v1.157a.933.933 0 0 1-.765.935c-.845.147-2.34.346-4.235.346-1.895 0-3.39-.2-4.235-.346A.933.933 0 0 1 3 9.219V8.062Zm4.542-.827a.25.25 0 0 0-.217.068l-.92.9a24.767 24.767 0 0 1-1.871-.183.25.25 0 0 0-.068.495c.55.076 1.232.149 2.02.2a.25.25 0 0 0 .216-.068l.92-.9a.25.25 0 0 0-.08-.412Z"/></svg> Confirmar este rostro: ${face.identity}`, '#0a84ff', 'bold');
            }
            
            if (folderName && categoryName && folderName !== 'Resultados' && categoryName !== 'Galeria Eneko NO ABRIR') {
                if (!aiPredictedIdObj) {
                    html += makeBtn({categoria: categoryName, identidad: folderName}, `<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M5.121 12.596a.5.5 0 1 0-.242.97l.613.153a.5.5 0 0 0 .242-.97l-.613-.153zM10.879 12.596a.5.5 0 0 0 .242.97l.613-.153a.5.5 0 1 0-.242-.97l-.613.153zM8 15a.5.5 0 0 0 .5-.5V14a.5.5 0 0 0-1 0v.5a.5.5 0 0 0 .5.5zM3 8a.5.5 0 0 0 .5.5h.5a.5.5 0 0 0 0-1h-.5A.5.5 0 0 0 3 8zm9.5 0a.5.5 0 0 0 .5-.5h-.5a.5.5 0 0 0 0 1h.5a.5.5 0 0 0 .5-.5z"/></svg> Confirmar este rostro: ${folderName}`, '#30d158', 'bold');
                }
                const faceTarget = face.identity || folderName;
                html += makeBtn({categoria: '_Dudosos', identidad: 'Desconocido'}, `<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/><path d="M5.25 6.033h1.32c0-.781.458-1.384 1.36-1.384.775 0 1.236.48 1.236 1.096 0 .61-.341.875-.85 1.332-.572.518-.845.894-.845 1.57h1.336c0-.528.21-.773.743-1.25.618-.553 1.07-1.127 1.07-2.128 0-1.427-1.157-2.276-2.613-2.276-1.637 0-2.753 1.008-2.757 3.04zM7.18 10.457h1.614v1.654H7.18v-1.654z"/></svg> Este rostro NO es ${faceTarget} (Dudoso)`, '#ff9f0a', 'bold');
            }
            
            html += makeBtn({categoria: 'Ignorar', identidad: 'Ignorar_Irrelevante'}, `<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm2-3a2 2 0 1 1-4 0 2 2 0 0 1 4 0zm4 8c0 1-1 1-1 1H3s-1 0-1-1 1-4 6-4 6 3 6 4zm-1-.004c-.001-.246-.154-.986-.832-1.664C11.516 10.68 10.289 10 8 10c-2.29 0-3.516.68-4.168 1.332-.678.678-.83 1.418-.832 1.664h10z"/></svg> Ignorar cara (Irrelevante)`, '#ccc');
            html += makeBtn({categoria: 'Ignorar', identidad: 'Falso_Positivo'}, `<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/><path d="M11.854 4.146a.5.5 0 0 0-.707 0l-7 7a.5.5 0 0 0 .707.708l7-7a.5.5 0 0 0 0-.708z"/></svg> Esto NO es una cara`, '#ff453a');
            html += makeBtn('NEW', `<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4z"/></svg> Crear nueva persona...`, 'white', 'bold');
            
            html += `<hr style="border:0; border-top:1px solid #333; margin:6px 0;">`;
            
            let categories = {};
            // SMART ALBUMS are not real people — exclude from reassignment dropdown
            const SMART_ALBUM_NAMES = new Set([
                'Familia conmigo', 'Familia sin mí', 'Familia sin mi',
                'Familiares conmigo', 'Familiares sin mí', 'Familiares sin mi',
                'Conocidos conmigo', 'Conocidos sin mí', 'Conocidos sin mi',
                'Mascotas conmigo',
            ]);
            identitiesList.forEach(id => {
                if (SMART_ALBUM_NAMES.has(id.identidad)) return; // skip
                if (id.categoria === 'Ignorar' || id.categoria === '_Dudosos') return;
                if(!categories[id.categoria]) categories[id.categoria] = [];
                categories[id.categoria].push(id);
            });
            
            Object.keys(categories).sort().forEach(cat => {
                html += `<details style="margin-bottom:4px;">`;
                html += `<summary style="cursor:pointer; padding:6px 10px; font-weight:bold; color:#aaa; font-size:12px; background:#2c2c2e; border-radius:4px; margin-bottom:2px;">${cat}</summary>`;
                html += `<div style="padding-left:8px; border-left:2px solid #333; margin-left:10px;">`;
                categories[cat].sort((a,b) => a.identidad.localeCompare(b.identidad)).forEach(id => {
                    html += makeBtn(id, id.identidad);
                });
                html += `</div></details>`;
            });

            
            html += `</div></div>`;
            return html;
        }

        function showToast(message, isError=false) {
            let container = document.getElementById('toast-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'toast-container';
                container.style.cssText = 'position:fixed; bottom:20px; right:20px; z-index:9999; display:flex; flex-direction:column; gap:10px;';
                document.body.appendChild(container);
            }
            const toast = document.createElement('div');
            toast.style.cssText = `background: ${isError ? 'rgba(255, 59, 48, 0.9)' : 'rgba(10, 132, 255, 0.9)'}; color: white; padding: 12px 20px; border-radius: 8px; backdrop-filter: blur(10px); box-shadow: 0 4px 12px rgba(0,0,0,0.3); font-family: -apple-system, sans-serif; font-size: 13px; transform: translateX(120%); transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);`;
            toast.innerHTML = `<strong>${isError ? 'Aviso' : 'Información'}</strong><br>${message}`;
            container.appendChild(toast);
            
            requestAnimationFrame(() => toast.style.transform = 'translateX(0)');
            setTimeout(() => {
                toast.style.transform = 'translateX(120%)';
                setTimeout(() => toast.remove(), 300);
            }, 4000);
        }

        document.addEventListener("DOMContentLoaded", async () => {
            await loadIdentities();
            await loadGallery();
        });

        async function loadIdentities() {
            const res = await fetch('/api/identities');
            identitiesList = await res.json();
        }

        
        async function openStatsModal() {
            const modal = document.getElementById('stats-modal');
            if (modal) modal.style.display = 'flex';
            document.getElementById('stats-content').innerHTML = '<div style="text-align: center; padding: 20px;"><div class="loader-small"></div><p style="margin-top:10px; color:#aaa;">Cargando estadísticas completas de la galería...</p></div>';

            
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                
                if (data.error) {
                    document.getElementById('stats-content').innerHTML = `<p style="color:red">${data.error}</p>`;
                    return;
                }
                
                const percentage = data.total > 0 ? Math.round((data.clasificadas / data.total) * 100) : 0;
                
                document.getElementById('stats-content').innerHTML = `
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span>Total de fotos en la galería:</span>
                        <strong>${data.total}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; color: #30d158;">
                        <span>✏️ Ordenadas Oficialmente por Mí:</span>
                        <strong>${data.manual_user || 0}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; color: #0a84ff;">
                        <span><svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M5.121 12.596a.5.5 0 1 0-.242.97l.613.153a.5.5 0 0 0 .242-.97l-.613-.153zM10.879 12.596a.5.5 0 0 0 .242.97l.613-.153a.5.5 0 1 0-.242-.97l-.613.153zM8 15a.5.5 0 0 0 .5-.5V14a.5.5 0 0 0-1 0v.5a.5.5 0 0 0 .5.5zM3 8a.5.5 0 0 0 .5.5h.5a.5.5 0 0 0 0-1h-.5A.5.5 0 0 0 3 8zm9.5 0a.5.5 0 0 0 .5-.5h-.5a.5.5 0 0 0 0 1h.5a.5.5 0 0 0 .5-.5z"/></svg> Ordenadas Oficialmente por IA:</span>
                        <strong>${data.ia_verified || 0}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; color: #ff9f0a;">
                        <span>⚠️ Dudosas / Revisión:</span>
                        <strong>${data.dudosos || 0}</strong>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 20px; color: #ff453a;">
                        <span>❓ Sin Ordenar / Pendientes:</span>
                        <strong>${data.pendientes || 0}</strong>
                    </div>
                    
                    <div style="width: 100%; background-color: #333; border-radius: 10px; height: 20px; overflow: hidden;">
                        <div style="width: ${percentage}%; background-color: #30d158; height: 100%; text-align: center; font-size: 12px; line-height: 20px; color: black; font-weight: bold;">
                            ${percentage}%
                        </div>
                    </div>
                    <div style="text-align: center; font-size: 12px; color: #aaa; margin-top: 5px; margin-bottom: 20px;">Progreso Global de Clasificación</div>
                    
                    <h3 style="color: #0a84ff; font-size: 16px; margin-bottom: 10px; border-bottom: 1px solid #333; padding-bottom: 5px;">Desglose Completo por Álbum / Persona</h3>
                    <div style="max-height: 250px; overflow-y: auto; padding-right: 10px; font-size: 14px;" class="custom-scrollbar">
                        ${Object.entries(data.breakdown || {}).map(([name, count]) => `
                            <div style="display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #222;">
                                <span>${name}</span>
                                <span style="color: #aaa;">${count}</span>
                            </div>
                        `).join('')}
                    </div>
                `;
            } catch (err) {
                document.getElementById('stats-content').innerHTML = `<p style="color:red">Error al cargar estadísticas: ${err.message}</p>`;
            }
        }
        
        
        async function forceReanalyze() {
            if (!confirm("¿Seguro que quieres forzar un re-análisis? Esto borrará la caché y tardará unos segundos, pero la IA usará su conocimiento actualizado para puntuar las caras.")) return;
            
            const btn = document.getElementById('btn-reanalyze');
            btn.style.opacity = '0.5';
            btn.textContent = 'Recalculando...';
            btn.style.pointerEvents = 'none';
            
            try {
                await fetch('/api/clear_confidence_cache', {method: 'POST'});
                await openIntelligentCleanup();
            } catch(e) {
                console.error(e);
                showToast("Error al re-analizar", true);
            }
        }

        
        async function _forceReanalyze_duplicate() {
            if (!confirm("¿Seguro que quieres forzar un re-análisis? Esto borrará la caché y tardará unos segundos, pero la IA usará su conocimiento actualizado para puntuar las caras.")) return;
            
            const btn = document.getElementById('btn-reanalyze');
            btn.style.opacity = '0.5';
            btn.textContent = 'Recalculando...';
            btn.style.pointerEvents = 'none';
            
            try {
                await fetch('/api/clear_confidence_cache', {method: 'POST'});
                await openIntelligentCleanup();
            } catch(e) {
                console.error(e);
                showToast("Error al re-analizar", true);
            }
        }

        let smartCleanInterval;
        async function openIntelligentCleanup() {
            document.getElementById('gallery-title').innerHTML = 'Limpieza Inteligente (Fáciles a Difíciles)';
            document.getElementById('gallery-subtitle').textContent = 'Analizando confianza de la IA en segundo plano... (Puedes minimizar si quieres)';
            document.getElementById('grid-container').innerHTML = '<div style="padding:50px; text-align:center;"><div class="loader-small" style="width:50px; height:50px; margin:auto;"></div><p id="smartCleanStatusText" style="margin-top:20px; color:#aaa;">Iniciando proceso en segundo plano...</p><progress id="smartCleanProgress" value="0" max="100" style="width: 50%; margin-top: 10px;"></progress></div>';
            
            try {
                await fetch('/api/start_smart_clean', {method: 'POST'});
                if(smartCleanInterval) clearInterval(smartCleanInterval);
                smartCleanInterval = setInterval(checkSmartCleanStatus, 2000);
            } catch(e) {
                showToast("Error iniciando la limpieza", true);
            }
        }
        
        async function checkSmartCleanStatus() {
            try {
                const res = await fetch('/api/smart_clean_status');
                const data = await res.json();
                const textEl = document.getElementById('smartCleanStatusText');
                const progEl = document.getElementById('smartCleanProgress');
                
                if(textEl) {
                    if (data.progress === 100) {
                        textEl.innerHTML = `<span style="color:#0f0;">¡Cálculo finalizado! Cargando imágenes...</span>`;
                        clearInterval(smartCleanInterval);
                        loadSmartCleanImages();
                    } else if (data.progress === -1) {
                        textEl.innerHTML = `<span style="color:#f00;">Error: ${data.status}</span>`;
                        clearInterval(smartCleanInterval);
                    } else {
                        textEl.innerHTML = `${data.status}<br>Progreso guardado automáticamente.`;
                        if(progEl) progEl.value = data.progress;
                    }
                }
            } catch(e) {}
        }
        
        async function loadSmartCleanImages() {
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
                document.getElementById('btn-reanalyze').style.display = 'block';
                document.getElementById('btn-reanalyze').style.opacity = '1';
                document.getElementById('btn-reanalyze').innerHTML = '<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M8 3a5 5 0 1 0 4.546 2.914.5.5 0 0 1 .908-.417A6 6 0 1 1 8 2v1z"/><path d="M8 4.466V.534a.25.25 0 0 1 .41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 0 1 8 4.466z"/></svg> Forzar Re-Análisis';
                document.getElementById('btn-reanalyze').style.pointerEvents = 'auto';

                document.getElementById('btn-reanalyze').style.display = 'block';
                document.getElementById('btn-reanalyze').style.opacity = '1';
                document.getElementById('btn-reanalyze').innerHTML = '<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M8 3a5 5 0 1 0 4.546 2.914.5.5 0 0 1 .908-.417A6 6 0 1 1 8 2v1z"/><path d="M8 4.466V.534a.25.25 0 0 1 .41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 0 1 8 4.466z"/></svg> Forzar Re-Análisis (IA Actualizada)';
                document.getElementById('btn-reanalyze').style.pointerEvents = 'auto';

                
                const grid = document.getElementById('grid-container');
                grid.innerHTML = '';
                
                currentFolderItems.forEach((item, idx) => {
                    const card = document.createElement('div');
                    card.className = 'media-card';
                if (isMultiSelectMode) {
                    const chkContainer = document.createElement('div');
                    chkContainer.style.cssText = "position:absolute; top:10px; left:10px; z-index:10;";
                    const chk = document.createElement('input');
                    chk.type = 'checkbox';
                    chk.className = 'card-checkbox';
                    chk.checked = selectedFiles.has(item.path);
                    chk.style.cssText = "width:22px; height:22px; accent-color:#30d158; cursor:pointer;";
                    chkContainer.appendChild(chk);
                    card.appendChild(chkContainer);
                    
                    if (selectedFiles.has(item.path)) {
                        card.classList.add('selected-card');
                        card.style.border = '3px solid #30d158';
                        card.style.boxShadow = '0 0 15px rgba(48,209,88,0.5)';
                    }
                    
                    card.onclick = (e) => toggleFileSelection(item.path, card, e);
                } else {
                    card.onclick = () => {
                        currentItemIndex = idx;
                        openLightbox(item);
                    };
                }
                    
                    const badge = document.createElement('span');
                    if (item.confidence > 0) {
                        const confPct = (item.confidence * 100).toFixed(1);
                        badge.className = 'badge badge-ia';
                        badge.innerHTML = `<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M6 12.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1h-3a.5.5 0 0 1-.5-.5ZM3 8.062C3 6.76 4.235 5.765 5.53 5.889a28.02 28.02 0 0 1 4.94 0C11.765 5.765 13 6.76 13 8.062v1.157a.933.933 0 0 1-.765.935c-.845.147-2.34.346-4.235.346-1.895 0-3.39-.2-4.235-.346A.933.933 0 0 1 3 9.219V8.062Zm4.542-.827a.25.25 0 0 0-.217.068l-.92.9a24.767 24.767 0 0 1-1.871-.183.25.25 0 0 0-.068.495c.55.076 1.232.149 2.02.2a.25.25 0 0 0 .216-.068l.92-.9a.25.25 0 0 0-.08-.412Z"/></svg> ${confPct}%`;
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
                        badge.innerHTML = '<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/></svg> Desconocido';
                        badge.style.backgroundColor = '#555';
                    }
                    card.appendChild(badge);
                    
                    const thumb = document.createElement('img');
                    thumb.src = `/api/thumbnail?path=${encodeURIComponent(item.path)}`;
                    thumb.loading = 'lazy';
                    thumb.style.opacity = '0';
                    thumb.onload = () => thumb.style.opacity = '1';
                    thumb.style.transition = 'opacity 0.3s ease';
                    thumb.style.width = '100%';
                    thumb.style.height = '100%';
                    thumb.style.objectFit = 'cover';
                    card.appendChild(thumb);
                    
                    if (item.type === 'video') {
                        const playIcon = document.createElement('div');
                        playIcon.className = 'video-icon';
                        playIcon.innerHTML = '▶';
                        card.appendChild(playIcon);
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

        async function loadGallery() {
            const res = await fetch('/api/gallery');
            fullGallery = await res.json();
            renderTree();
            if (currentCat && currentIdent) {
                if (fullGallery[currentCat] && fullGallery[currentCat][currentIdent]) {
                    renderGrid(currentCat, currentIdent);
                } else {
                    document.getElementById('grid-container').innerHTML = '';
                }
            }
        }

                function renderTree() {
            const treeEl = document.getElementById('tree-container');
            if (!treeEl) return;
            treeEl.innerHTML = '';
            
            if (!fullGallery) return;

            // Reordenar categorías para que Objetos quede abajo del todo
            const categories = Object.keys(fullGallery).sort((a, b) => {
                if (a.toLowerCase().includes('objeto')) return 1;
                if (b.toLowerCase().includes('objeto')) return -1;
                return a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' });
            });

            for (const cat of categories) {
                const details = document.createElement('details');
                details.className = 'sidebar-category-group';
                details.style.marginBottom = '6px';
                
                const idents = Object.keys(fullGallery[cat]);
                let totalCatCount = 0;
                idents.forEach(id => { totalCatCount += fullGallery[cat][id].length; });

                const summary = document.createElement('summary');
                summary.className = 'sidebar-category-summary';
                summary.innerHTML = `<span style="display:flex; align-items:center; gap:8px;">📁 <strong>${cat}</strong></span> <span class="badge-count">${idents.length}</span>`;
                details.appendChild(summary);

                const contentDiv = document.createElement('div');
                contentDiv.className = 'sidebar-category-content';
                contentDiv.style.cssText = 'padding-left: 8px; border-left: 2px solid rgba(255,255,255,0.1); margin-left: 8px; margin-top: 4px; margin-bottom: 4px; display: flex; flex-direction: column; gap: 2px;';

                // Natural numeric sorting (Persona_1, Persona_2, ..., Persona_99, Persona_100, ..., Persona_260)
                const sortedIdents = idents.sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' }));

                for (const ident of sortedIdents) {
                    const identEl = document.createElement('div');
                    identEl.className = 'tree-folder identity';
                    const count = fullGallery[cat][ident].length;

                    // Smart albums are dynamic groups, not real people
                    const SMART_ALBUM_NAMES_SIDEBAR = new Set([
                        'Familia conmigo', 'Familia sin mí', 'Familia sin mi',
                        'Familiares conmigo', 'Familiares sin mí', 'Familiares sin mi',
                        'Conocidos conmigo', 'Conocidos sin mí', 'Conocidos sin mi',
                        'Mascotas conmigo',
                    ]);
                    const isSmartAlbum = SMART_ALBUM_NAMES_SIDEBAR.has(ident);

                    if (isSmartAlbum) {
                        identEl.innerHTML = `<span style="display:flex; align-items:center; gap:6px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-style:italic; color:#bf5af2;">✨ ${ident}</span> <span class="badge-count" style="background:#5e2d91;">${count}</span>`;
                        identEl.title = "Álbum inteligente dinámico — se rellena automáticamente";
                    } else {
                        identEl.innerHTML = `<span style="display:flex; align-items:center; gap:6px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;"><svg width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm2-3a2 2 0 1 1-4 0 2 2 0 0 1 4 0zm4 8c0 1-1 1-1 1H3s-1 0-1-1 1-4 6-4 6 3 6 4zm-1-.004c-.001-.246-.154-.986-.832-1.664C11.516 10.68 10.289 10 8 10c-2.29 0-3.516.68-4.168 1.332-.678.678-.83 1.418-.832 1.664h10z"/></svg> ${ident}</span> <span class="badge-count">${count}</span>`;
                    }
                    identEl.onclick = () => renderGrid(cat, ident);
                    contentDiv.appendChild(identEl);
                }


                details.appendChild(contentDiv);
                treeEl.appendChild(details);
            }
        }

        function filterGallery(term) {
            term = (term || '').toLowerCase().trim();
            document.querySelectorAll('.sidebar-category-group').forEach(group => {
                let hasMatch = false;
                group.querySelectorAll('.tree-folder.identity').forEach(el => {
                    const text = el.textContent.toLowerCase();
                    const match = text.includes(term);
                    el.style.display = match ? 'flex' : 'none';
                    if (match) hasMatch = true;
                });
                if (term) {
                    group.open = hasMatch;
                    group.style.display = hasMatch ? 'block' : 'none';
                } else {
                    group.open = false;
                    group.style.display = 'block';
                }
            });
        }


        
        let currentFolderItems = [];
        let currentItemIndex = -1;
        let isSwipeModeActive = true; // Habilitado por defecto para facilitar la limpieza

        function toggleSwipeMode() {
            isSwipeModeActive = !isSwipeModeActive;
            const btn = document.getElementById('btn-swipe-mode');
            if (btn) {
                btn.innerHTML = isSwipeModeActive ? `<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M8 16c3.314 0 6-2 6-5.5 0-1.5-.5-4-2.5-6 .25 1.5-1.25 2-1.25 2C11 4 9 .5 6 0c.357 2 .5 4-2 6-1.25 1-2 2.729-2 4.5C2 14 4.686 16 8 16Zm0-1c-1.657 0-3-1-3-2.75 0-.75.25-2 1.25-3C6.125 10 7 10.5 7 10.5c-.375-1.25.5-3.25 2-3.5-.179 1-.25 2 1 3 .625.5 1 1.364 1 2.25C11 14 9.657 15 8 15Z"/></svg> Modo Limpieza Rápida (ON)` : `<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M8 16c3.314 0 6-2 6-5.5 0-1.5-.5-4-2.5-6 .25 1.5-1.25 2-1.25 2C11 4 9 .5 6 0c.357 2 .5 4-2 6-1.25 1-2 2.729-2 4.5C2 14 4.686 16 8 16Zm0-1c-1.657 0-3-1-3-2.75 0-.75.25-2 1.25-3C6.125 10 7 10.5 7 10.5c-.375-1.25.5-3.25 2-3.5-.179 1-.25 2 1 3 .625.5 1 1.364 1 2.25C11 14 9.657 15 8 15Z"/></svg> Modo Limpieza Rápida (OFF)`;
                btn.style.color = isSwipeModeActive ? "#30d158" : "#ff9f0a";
            }
            showToast(isSwipeModeActive ? "Modo Limpieza Rápida ACTIVADO (Flecha ⬅️ Borra, Flecha ➡️ Conserva)" : "Modo Limpieza Rápida DESACTIVADO.");
        }

        
                function renderGrid(cat, ident) {
            if (!cat || !ident || !fullGallery || !fullGallery[cat] || !fullGallery[cat][ident]) {
                return;
            }
            currentCat = cat;
            currentIdent = ident;
            const btnTl = document.getElementById('btn-show-timeline'); if (btnTl) btnTl.style.display = isStableDataset(cat, ident) ? 'inline-flex' : 'none';
            currentFolderItems = fullGallery[cat][ident] || [];
            
            document.getElementById('gallery-title').textContent = `${cat} > ${ident}`;
            const sub = document.getElementById('gallery-subtitle');
            if (sub) {
                sub.style.display = 'block';
                sub.textContent = `${currentFolderItems.length} elementos`;
            }
            
            const avatar = document.getElementById('gallery-avatar');
            if (avatar) {
                avatar.src = `/api/person_avatar?cat=${encodeURIComponent(cat)}&ident=${encodeURIComponent(ident)}`;
                avatar.style.display = 'block';
                avatar.onerror = () => { avatar.style.display = 'none'; };
            }
            
            const renameBtn = document.getElementById('btn-rename-group');
            const ignoreBtn = document.getElementById('btn-ignore-group');
            const deleteBtn = document.getElementById('btn-delete-group');
            
            if (renameBtn && ignoreBtn && deleteBtn) {
                if (cat === 'Personas Sin Nombre') {
                    renameBtn.style.display = 'inline-flex';
                    ignoreBtn.style.display = 'inline-flex';
                    deleteBtn.style.display = 'inline-flex';
                } else {
                    renameBtn.style.display = 'none';
                    ignoreBtn.style.display = 'none';
                    deleteBtn.style.display = 'none';
                }
            }
            
            const grid = document.getElementById('grid-container');
            grid.innerHTML = '';
            
            // Sync Top HUD Zoom Slider with CSS grid
            const slider = document.getElementById('zoom-slider');
            const label = document.getElementById('zoom-label');
            if (slider && label) {
                const applyZoom = (val) => {
                    grid.style.setProperty('--card-size', val + 'px');
                    const cols = Math.max(1, Math.floor(grid.clientWidth / (parseInt(val) + 16)));
                    label.textContent = cols + '×';
                    localStorage.setItem('gallery-zoom', val);
                };
                const savedZoom = localStorage.getItem('gallery-zoom') || '180';
                slider.value = savedZoom;
                applyZoom(savedZoom);
                slider.oninput = (e) => applyZoom(e.target.value);
            }
            

            currentFolderItems.forEach((item, idx) => {
                const card = document.createElement('div');
                card.className = 'media-card';
                card.style.position = 'relative';
                
                if (isMultiSelectMode) {
                    const chkContainer = document.createElement('div');
                    chkContainer.style.cssText = "position:absolute; top:8px; left:8px; z-index:100;";
                    const chk = document.createElement('input');
                    chk.type = 'checkbox';
                    chk.className = 'card-checkbox';
                    chk.checked = selectedFiles.has(item.path);
                    chk.style.cssText = "width:22px; height:22px; accent-color:#30d158; cursor:pointer;";
                    chkContainer.appendChild(chk);
                    card.appendChild(chkContainer);
                    
                    if (selectedFiles.has(item.path)) {
                        card.classList.add('selected-card');
                        card.style.border = '3px solid #30d158';
                        card.style.boxShadow = '0 0 15px rgba(48,209,88,0.5)';
                    }
                    
                    card.onclick = (e) => {
                        e.stopPropagation();
                        toggleFileSelection(item.path, card, e);
                    };
                } else {
                    card.onclick = () => {
                        currentItemIndex = idx;
                        openLightbox(item);
                    };
                }
                
                const badge = document.createElement('span');
                badge.id = `source-${idx}`;
                if (item.source.includes('Dataset') && item.source.includes('Manual')) {
                    badge.className = 'badge badge-dataset';
                    badge.textContent = '🔒 Dataset + ✏️ Manual';
                } else if (item.source.includes('IA') && item.source.includes('Manual')) {
                    badge.className = 'badge badge-manual';
                    badge.innerHTML = '<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M5.121 12.596a.5.5 0 1 0-.242.97l.613.153a.5.5 0 0 0 .242-.97l-.613-.153zM10.879 12.596a.5.5 0 0 0 .242.97l.613-.153a.5.5 0 1 0-.242-.97l-.613.153zM8 15a.5.5 0 0 0 .5-.5V14a.5.5 0 0 0-1 0v.5a.5.5 0 0 0 .5.5zM3 8a.5.5 0 0 0 .5.5h.5a.5.5 0 0 0 0-1h-.5A.5.5 0 0 0 3 8zm9.5 0a.5.5 0 0 0 .5-.5h-.5a.5.5 0 0 0 0 1h.5a.5.5 0 0 0 .5-.5z"/></svg> IA + ✏️ Manual';
                } else if (item.source.includes('Dataset')) {
                    badge.className = 'badge badge-dataset';
                    badge.textContent = '🔒 Dataset';
                } else if (item.source.includes('Manual')) {
                    badge.className = 'badge badge-manual';
                    badge.textContent = '✏️ Manual';
                } else {
                    badge.className = 'badge badge-ia';
                    badge.innerHTML = '<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M5.121 12.596a.5.5 0 1 0-.242.97l.613.153a.5.5 0 0 0 .242-.97l-.613-.153zM10.879 12.596a.5.5 0 0 0 .242.97l.613-.153a.5.5 0 1 0-.242-.97l-.613.153zM8 15a.5.5 0 0 0 .5-.5V14a.5.5 0 0 0-1 0v.5a.5.5 0 0 0 .5.5zM3 8a.5.5 0 0 0 .5.5h.5a.5.5 0 0 0 0-1h-.5A.5.5 0 0 0 3 8zm9.5 0a.5.5 0 0 0 .5-.5h-.5a.5.5 0 0 0 0 1h.5a.5.5 0 0 0 .5-.5z"/></svg> IA';
                }
                card.appendChild(badge);
                
                const thumb = document.createElement('img');
                thumb.src = `/api/thumbnail?path=${encodeURIComponent(item.path)}`;
                thumb.loading = 'lazy';
                thumb.decoding = 'async';
                thumb.style.opacity = '0';
                thumb.onload = () => thumb.style.opacity = '1';
                thumb.style.transition = 'opacity 0.2s ease';
                thumb.style.width = '100%';
                thumb.style.height = '100%';
                thumb.style.objectFit = 'cover';
                card.appendChild(thumb);
                
                if (item.type === 'video') {
                    const playIcon = document.createElement('div');
                    playIcon.className = 'video-icon';
                    playIcon.innerHTML = '▶';
                    card.appendChild(playIcon);
                }
                
                const title = document.createElement('div');
                title.className = 'media-title';
                title.textContent = item.name;
                card.appendChild(title);
                
                grid.appendChild(card);
            });
        }
        
        // ===== Export key functions to global scope =====
        window.renderGrid = renderGrid;
        window.loadGallery = loadGallery;
        window.loadIdentities = loadIdentities;

        function closeLightbox() {
            const lb = document.getElementById('lightbox');
            if(lb) {
                lb.classList.add('hidden');
                lb.style.display = ''; // Limpiar el estilo inline
            }
            const container = document.getElementById('lb-media-container');
            if (container) container.innerHTML = '';
            currentFileObj = null;
            isCurrentVideo = false;
            if(typeof resetZoom === 'function') resetZoom();
        }

        function resetGalleryView() {
            currentCat = null;
            currentIdent = null;
            currentFolderItems = [];
            document.getElementById('gallery-title').textContent = 'Smart Gallery';
            document.getElementById('gallery-subtitle').textContent = 'Selecciona una categoría en la barra lateral';
            document.getElementById('grid-container').innerHTML = '';
            
            const renameBtn = document.getElementById('btn-rename-group');
            const ignoreBtn = document.getElementById('btn-ignore-group');
            const deleteBtn = document.getElementById('btn-delete-group');
            if (renameBtn) renameBtn.style.display = 'none';
            if (ignoreBtn) ignoreBtn.style.display = 'none';
            if (deleteBtn) deleteBtn.style.display = 'none';
        }

        function renameCurrentGroup() {
            if (!currentCat || !currentIdent) {
                alert("Selecciona primero una persona en la barra lateral para poder fusionarla.");
                return;
            }
            
            const containerEl = document.getElementById('merge-existing-select');
            containerEl.innerHTML = '';
            document.getElementById('merge-selected-value').value = '';
            
            let groupedIds = {};
            identitiesList.forEach(id => {
                if (id.categoria !== 'Personas Sin Nombre' && id.categoria !== 'Ignorar' && id.categoria !== '_Dudosos') {
                    if (!groupedIds[id.categoria]) groupedIds[id.categoria] = [];
                    groupedIds[id.categoria].push(id);
                }
            });
            
            const btnStyle = "display:block; width:100%; text-align:left; padding:8px 10px; background:transparent; border:none; color:white; cursor:pointer; border-radius:4px; font-size:13px; margin-bottom:2px; transition:background 0.2s;";
            const hoverScript = "onmouseover=\"if(this.dataset.selected!=='true') this.style.background='#3a3a3c'\" onmouseout=\"if(this.dataset.selected!=='true') this.style.background='transparent'\"";
            
            Object.keys(groupedIds).sort().forEach(cat => {
                const details = document.createElement('details');
                details.style.marginBottom = '4px';
                
                const summary = document.createElement('summary');
                summary.style.cssText = 'cursor:pointer; padding:6px 10px; font-weight:bold; color:#aaa; font-size:12px; background:#1c1c1e; margin-bottom:2px; position:sticky; top:0; z-index:10; border-bottom:1px solid #333;';
                summary.textContent = cat;
                details.appendChild(summary);
                
                const contentDiv = document.createElement('div');
                contentDiv.style.cssText = 'padding-left:8px; border-left:2px solid #333; margin-left:10px; margin-top:5px; margin-bottom:5px;';
                
                groupedIds[cat].sort((a,b) => a.identidad.localeCompare(b.identidad)).forEach(id => {
                    const btn = document.createElement('button');
                    btn.style.cssText = btnStyle;
                    btn.innerHTML = id.identidad;
                    btn.setAttribute('onmouseover', "if(this.dataset.selected!=='true') this.style.background='#3a3a3c'");
                    btn.setAttribute('onmouseout', "if(this.dataset.selected!=='true') this.style.background='transparent'");
                    
                    btn.onclick = () => {
                        // Reset all buttons
                        const allBtns = containerEl.querySelectorAll('button');
                        allBtns.forEach(b => {
                            b.dataset.selected = 'false';
                            b.style.background = 'transparent';
                            b.style.fontWeight = 'normal';
                        });
                        
                        // Select this button
                        btn.dataset.selected = 'true';
                        btn.style.background = '#30d158';
                        btn.style.color = 'black';
                        btn.style.fontWeight = 'bold';
                        
                        // Clear text input
                        document.getElementById('merge-new-input').value = '';
                        
                        // Set hidden value
                        document.getElementById('merge-selected-value').value = JSON.stringify({cat: id.categoria, ident: id.identidad});
                    };
                    
                    contentDiv.appendChild(btn);
                });
                
                details.appendChild(contentDiv);
                containerEl.appendChild(details);
            });
            
            // Text input should clear selection
            document.getElementById('merge-new-input').oninput = () => {
                const allBtns = containerEl.querySelectorAll('button');
                allBtns.forEach(b => {
                    b.dataset.selected = 'false';
                    b.style.background = 'transparent';
                    b.style.color = 'white';
                    b.style.fontWeight = 'normal';
                });
                document.getElementById('merge-selected-value').value = '';
            };
            
            document.getElementById('merge-count-span').textContent = currentFolderItems.length;
            document.getElementById('merge-group-name').textContent = currentIdent;
            document.getElementById('merge-new-input').value = '';
            document.getElementById('modal-merge').style.display = 'flex';
        }

        function closeMergeModal() {
            document.getElementById('modal-merge').style.display = 'none';
        }

        
        async function deleteCurrentGroup() {
            if (!currentCat || !currentIdent || currentCat !== 'Personas Sin Nombre') return;
            if (!confirm(`¿Seguro que quieres disolver el grupo '${currentIdent}'? Las fotos no se borrarán de tus álbumes.`)) return;
            
            showToast(`⏳ Disolviendo grupo '${currentIdent}'...`);
            const res = await fetch('/api/delete_group', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ cat: currentCat, ident: currentIdent })
            });
            const data = await res.json();
            if (data.success) {
                showToast(`<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z"/><path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4L4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/></svg> Grupo '${currentIdent}' disuelto con éxito.`);
                await loadIdentities();
                await loadGallery();
                resetGalleryView();
            } else {
                showToast(data.error || "No se pudo disolver el grupo.", true);
            }
        }

        async function ignoreCurrentGroup() {
            if (!currentCat || !currentIdent || currentCat !== 'Personas Sin Nombre') return;
            if (!confirm(`¿Seguro que quieres ignorar a la persona '${currentIdent}'? Se ocultará de la galería y la IA no la volverá a sugerir.`)) return;
            
            showToast(`⏳ Ignorando a '${currentIdent}'...`);
            const targetName = 'Falso_Positivo_' + currentIdent;
            
            const res = await fetch('/api/rename_group', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    cat: currentCat,
                    ident: currentIdent,
                    new_name: targetName,
                    new_cat: 'Ignorar'
                })
            });
            const data = await res.json();
            if (data.success) {
                showToast(`<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/><path d="M11.854 4.146a.5.5 0 0 0-.707 0l-7 7a.5.5 0 0 0 .707.708l7-7a.5.5 0 0 0 0-.708z"/></svg> '${currentIdent}' ha sido ignorado correctamente.`);
                await loadIdentities();
                await loadGallery();
                resetGalleryView();
            } else {
                showToast(data.error || "No se pudo ignorar a la persona.", true);
            }
        }

        async function submitMergeGroup() {
            if (!currentCat || !currentIdent) {
                alert("Por favor, selecciona una carpeta o persona antes de intentar fusionar.");
                closeMergeModal();
                return;
            }
            const existingNameJSON = document.getElementById('merge-selected-value').value;
            const newName = document.getElementById('merge-new-input').value.trim();
            
            let targetName = "";
            let targetCat = "Conocidos";
            
            if (existingNameJSON) {
                const parsed = JSON.parse(existingNameJSON);
                targetName = parsed.ident;
                targetCat = parsed.cat;
            } else if (newName) {
                targetName = newName;
                if (targetName.startsWith('F. ') || targetName.startsWith('F_')) {
                    targetCat = 'Familia';
                } else if (targetName.startsWith('C. ')) {
                    targetCat = 'Conocidos';
                } else if (targetName.startsWith('P. ')) {
                    targetCat = 'Profesores';
                } else {
                    targetCat = prompt("Introduce la categoría para esta nueva persona ('Familia' o 'Conocidos'):", "Familia") || "Familia";
                }
            } else {
                alert("Por favor, selecciona una persona existente o introduce un nombre nuevo.");
                return;
            }
            
            // LOCK UI
            const btn = document.getElementById('modal-merge').querySelector('button[style*="background: #30d158"]');
            if(btn) { btn.disabled = true; btn.textContent = "⏳ Fusionando..."; }
            
            showToast(`⏳ Fusionando ${currentFolderItems.length} fotos con '${targetName}' y reentrenando IA...`);
            
            try {
            const res = await fetch('/api/rename_group', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    cat: currentCat,
                    ident: currentIdent,
                    new_name: targetName,
                    new_cat: targetCat
                })
            });
            const data = await res.json();
            if (data.success) {
                showToast(`🎉 ¡Fusionado con éxito! Se unieron ${data.count} fotos a '${targetCat} / ${targetName}'.`);
                closeMergeModal();
                await loadIdentities();
                await loadGallery();
                renderGrid(null, null);
            } else {
                showToast(data.error || "No se pudo fusionar el grupo.", true);
            }
            } catch (e) {
                showToast("Error de conexión durante la fusión.", true);
            } finally {
                if(btn) { btn.disabled = false; btn.innerHTML = `<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M8 15s-1.5-1-1.5-3 1.5-3 1.5-3 1.5 1 1.5 3-1.5 3-1.5 3zm0-12s3 1.5 3 4.5c0 1.5-1 3-3 4.5C6 10.5 5 9 5 7.5 5 4.5 8 3 8 3z"/></svg> Aplicar Fusión / Guardar`; }
                closeMergeModal();
            }
        }



        window.resetFaceLearningConfirm = async function() {
            if (confirm("⚠️ ¿Deseas reiniciar completamente el aprendizaje de caras y limpiar los datos calculados de IA?\n\nEsta acción no se puede deshacer.")) {
                try {
                    const res = await fetch('/api/reset_face_learning', { method: 'POST' });
                    const data = await res.json();
                    if (data.success) {
                        alert("✅ " + data.message);
                        if (window.loadGallery) window.loadGallery();
                        if (window.loadIdentities) window.loadIdentities();
                    } else {
                        alert("❌ Error: " + (data.error || "No se pudo reiniciar el aprendizaje."));
                    }
                } catch(e) {
                    alert("❌ Error de conexión al reiniciar aprendizaje.");
                }
            }
        };

        window.rebuildCleanCentroidsConfirm = async function() {
            const btn = document.getElementById('btn-rebuild-centroids');
            if (btn) {
                btn.disabled = true;
                btn.textContent = '⏳ Recalculando centroides...';
            }
            try {
                const res = await fetch('/api/rebuild_clean_centroids', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    alert("✅ " + data.message);
                    if (window.loadGallery) window.loadGallery();
                    if (window.loadIdentities) window.loadIdentities();
                } else {
                    alert("❌ Error: " + (data.error || "No se pudo recalcular el modelo."));
                }
            } catch(e) {
                alert("❌ Error de conexión al recalcular el modelo.");
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = '🔄 Recalcular Modelo de IA Ahora';
                }
            }
        };



        document.addEventListener('keydown', async (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) return;

            const lightbox = document.getElementById('lightbox');
            const isLightboxOpen = lightbox && !lightbox.classList.contains('hidden');

            if (isLightboxOpen) {
                if (e.key === 'Escape') {
                    e.preventDefault();
                    lightbox.classList.add('hidden');
                    if (isCurrentVideo) {
                        const mediaEl = document.querySelector('.lb-media-element');
                        if (mediaEl) mediaEl.pause();
                    }
                }
                else if (e.key === 'ArrowLeft') {
                    e.preventDefault();
                    if (currentFolderItems && currentItemIndex > 0) {
                        currentItemIndex--;
                        openLightbox(currentFolderItems[currentItemIndex]);
                    }
                }
                else if (e.key === 'ArrowRight') {
                    e.preventDefault();
                    if (currentFolderItems && currentItemIndex < currentFolderItems.length - 1) {
                        currentItemIndex++;
                        openLightbox(currentFolderItems[currentItemIndex]);
                    }
                }
                else if (e.key === 'Delete' || e.key === 'Backspace') {
                    e.preventDefault();
                    const activeBox = document.querySelector('.lb-bounding-box.active');
                    if (activeBox && currentFileObj) {
                        const faceNum = activeBox.id.replace('bbox-', '');
                        const falsePosId = JSON.stringify({categoria: 'Ignorar', identidad: 'Falso_Positivo'});
                        if (typeof inlineCorrect === 'function') {
                            inlineCorrect(
                                encodeURIComponent(currentFileObj.path), 
                                falsePosId, 
                                faceNum, 
                                activeBox.dataset.faceX, 
                                activeBox.dataset.faceY, 
                                activeBox.dataset.faceW, 
                                activeBox.dataset.faceH
                            );
                        }
                    } else if (typeof deleteCurrentFile === 'function') {
                        deleteCurrentFile();
                    }
                }
                return; // Stop here if lightbox is open
            }

            // Global shortcuts (if lightbox is closed)
            if (e.key === 'Delete' || e.key === 'Backspace') {
                e.preventDefault();
                if (typeof selectedFiles !== 'undefined' && selectedFiles && selectedFiles.size > 0) {
                    if (typeof deleteSelectedFiles === 'function') {
                        deleteSelectedFiles();
                    }
                }
            }
        });



        async function swipeActionLeft() {
            // BORRAR Y SIGUIENTE
            const ind = document.getElementById('swipe-left-ind');
            if (ind) {
                ind.classList.add('swipe-active');
                setTimeout(() => ind.classList.remove('swipe-active'), 300);
            }
            
            if (currentFileObj) {
                const res = await fetch('/api/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ path: currentFileObj.path })
                });
                const data = await res.json();
                if (data.success) {
                    showToast(`Descartado y eliminado <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z"/><path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4L4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/></svg>`);
                    await loadGallery();
                    loadNextItem();
                } else {
                    showToast(data.error || "No se pudo eliminar.", true);
                }
            }
        }

        async function swipeActionRight() {
            // CONSERVAR / SIGUIENTE
            const ind = document.getElementById('swipe-right-ind');
            if (ind) {
                ind.classList.add('swipe-active');
                setTimeout(() => ind.classList.remove('swipe-active'), 300);
            }
            showToast(`Conservado <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zm-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z"/></svg>`);
            loadNextItem();
        }

        function loadNextItem() {
            if (currentFolderItems.length === 0) {
                closeLightbox();
                return;
            }
            currentItemIndex++;
            if (currentItemIndex >= currentFolderItems.length) {
                currentItemIndex = 0;
            }
            const nextItem = currentFolderItems[currentItemIndex];
            if (nextItem) {
                openLightbox(nextItem);
            } else {
                closeLightbox();
            }
        }



        // Motor de Zoom Interactivo con Rueda del Ratón y Panoramización (Pan)
        let zoomLevel = 1.0;
        let panX = 0;
        let panY = 0;
        let isPanDragging = false;
        let panStartX = 0;
        let panStartY = 0;

        function resetZoom() {
            zoomLevel = 1.0;
            panX = 0;
            panY = 0;
            applyZoomTransform();
        }

        function applyZoomTransform() {
            const container = document.getElementById('lb-media-container');
            if (container) {
                container.style.transform = `translate(${panX}px, ${panY}px) scale(${zoomLevel})`;
                
                const invZoom = 1.0 / zoomLevel;
                document.querySelectorAll('.resize-handle').forEach(h => {
                    h.style.transform = `scale(${invZoom})`;
                });
                document.querySelectorAll('.lb-bb-badge').forEach(b => {
                    b.style.transform = `scale(${invZoom})`;
                });
                document.querySelectorAll('.lb-bounding-box').forEach(b => {
                    b.style.borderWidth = `${2 * invZoom}px`;
                });
                document.querySelectorAll('.lb-box-popup').forEach(p => {
                    p.style.transform = `translateX(-50%) scale(${invZoom})`;
                });
            }
        }

        document.addEventListener('DOMContentLoaded', () => {
            const wrapper = document.getElementById('viewer-wrapper');
            if (!wrapper) return;

            // Rueda del Ratón para Zoom
            let zoomTicking = false;
            wrapper.addEventListener('wheel', (e) => {
                e.preventDefault();
                const delta = e.deltaY < 0 ? 0.3 : -0.3;
                zoomLevel = Math.min(Math.max(1.0, zoomLevel + delta), 16.0);

                if (zoomLevel === 1.0) {
                    panX = 0;
                    panY = 0;
                }
                
                if (!zoomTicking) {
                    window.requestAnimationFrame(() => {
                        applyZoomTransform();
                        zoomTicking = false;
                    });
                    zoomTicking = true;
                }
            }, { passive: false });

            // Panoramización con Arrastre cuando hay Zoom
            wrapper.addEventListener('mousedown', (e) => {
                if (window.isDrawingMode) return;
                if (zoomLevel > 1.0 && !e.target.closest('.lb-bounding-box') && !e.target.closest('.resize-handle')) {
                    isPanDragging = true;
                    panStartX = e.clientX - panX;
                    panStartY = e.clientY - panY;
                    wrapper.style.cursor = 'grabbing';
                }
            });

            let panTicking = false;
            document.addEventListener('mousemove', (e) => {
                if (isPanDragging && zoomLevel > 1.0) {
                    panX = e.clientX - panStartX;
                    panY = e.clientY - panStartY;
                    if (!panTicking) {
                        window.requestAnimationFrame(() => {
                            applyZoomTransform();
                            panTicking = false;
                        });
                        panTicking = true;
                    }
                }
            });

            document.addEventListener('mouseup', () => {
                if (isPanDragging) {
                    isPanDragging = false;
                    const wrapper = document.getElementById('viewer-wrapper');
                    if (wrapper) wrapper.style.cursor = 'default';
                }
            });
        });


async function deleteCurrentFile() {
    releaseMediaElement();
    if (!currentFileObj) return;
    if (confirm("¿Estás seguro de que deseas eliminar este archivo de forma permanente?")) {
        try {
            const res = await fetch('/api/delete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ path: currentFileObj.path })
            });
            const data = await res.json();
            if (res.ok && !data.error) {
                closeLightbox();
                loadGallery();
            } else {
                alert("Error al eliminar: " + (data.error || "Desconocido"));
            }
        } catch (e) {
            alert("Error al intentar eliminar.");
        }
    }
}

async function openLightbox(item) {
            resetZoom();
            currentFileObj = item;
            isCurrentVideo = item.type === 'video';
            
            const container = document.getElementById('lb-media-container');
            container.innerHTML = '';
            document.getElementById('duplicate-banner-container').innerHTML = '';
            document.getElementById('person-cards-container').innerHTML = '<div style="padding:20px; text-align:center;"><div class="loader-small"></div></div>';
            
            let mediaEl;
            if (isCurrentVideo) {
                mediaEl = document.createElement('video');
                mediaEl.src = `/media?path=${encodeURIComponent(item.path)}`;
                mediaEl.controls = true;
                mediaEl.autoplay = false;
                mediaEl.preload = 'auto';
                mediaEl.playsInline = true;
                mediaEl.className = 'lb-media-element';
                mediaEl.style.width = '100%';
                mediaEl.style.height = '100%';
                mediaEl.style.maxHeight = 'calc(100vh - 120px)';
                mediaEl.style.objectFit = 'contain';
                
                mediaEl.onloadedmetadata = () => {
                    if (window.liveScanTimestamp) {
                        try { mediaEl.currentTime = window.liveScanTimestamp; } catch(e){}
                        window.liveScanTimestamp = null;
                    }
                };
                document.getElementById('analyze-toolbar').style.display = 'block';
            } else {
                mediaEl = document.createElement('img');
                mediaEl.src = `/media?path=${encodeURIComponent(item.path)}`;
                mediaEl.className = 'lb-media-element';
                document.getElementById('analyze-toolbar').style.display = 'none';
            }
            
            container.appendChild(mediaEl);
            document.getElementById('lightbox').classList.remove('hidden');
            
            // Metadatos
            fetch(`/api/metadata?path=${encodeURIComponent(item.path)}`)
                .then(r => r.json())
                .then(data => {
                    document.getElementById('meta-date').textContent = data.date || '-';
                    document.getElementById('meta-size').textContent = data.size || '-';
                    document.getElementById('meta-res').textContent = data.resolution || '-';
                    document.getElementById('meta-cam').textContent = data.camera || '-';
                });

            // IA de Nitidez y Duplicados
            fetch('/api/duplicates', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ path: item.path })
            })
            .then(r => r.json())
            .then(data => {
                const sharpEl = document.getElementById('meta-sharpness');
                if (sharpEl) sharpEl.textContent = data.sharpness ? `${data.sharpness} Score` : '-';
                
                const dupContainer = document.getElementById('duplicate-banner-container');
                if (data.duplicate && dupContainer) {
                    const dup = data.duplicate;
                    dupContainer.innerHTML = `
                        <div class="duplicate-banner">
                            <div class="duplicate-banner-title">⚠️ Foto Parecida (${dup.similarity}%)</div>
                            <div class="duplicate-banner-desc">
                                ${dup.is_current_better ? 
                                    `🌟 <strong>Top Shot:</strong> Esta foto tiene mayor nitidez (${data.sharpness} vs ${dup.other_sharpness}). Recomendado conservar.` : 
                                    `⚠️ Existe una versión más nítida de esta toma (<em>${dup.other_name}</em> - Nitidez: ${dup.other_sharpness} vs ${data.sharpness}).`}
                            </div>
                            <div style="display: flex; gap: 10px; margin-top: 10px;">
                                ${!dup.is_current_better ? `<button class="duplicate-btn-delete" onclick="deleteCurrentFile()" style="flex: 1;"><svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z"/><path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4L4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/></svg> Borrar versión inferior</button>` : ''}
                                <button onclick="openCompareModal('${encodeURIComponent(currentFileObj.path)}', '${encodeURIComponent(dup.other_path)}')" style="flex: 1; padding: 10px; border-radius: 8px; border: none; background: #0a84ff; color: white; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 5px;"><svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M0 2a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V2zm4.5 5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zm7 0a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zM2 13h12V9.5l-3.715-3.715a.5.5 0 0 0-.707 0L6 9.36l-1.578-1.578a.5.5 0 0 0-.707 0L2 11.5V13z"/></svg> Comparar</button>
                            </div>
                        </div>
                    `;
                }
            });
                
            if (!isCurrentVideo) {
                if (mediaEl.complete) runAnalysis();
                else mediaEl.onload = () => runAnalysis();
            } else {
                document.getElementById('person-cards-container').innerHTML = `
                    <button class="icon-btn" id="btn-scan-video" onclick="scanFullVideo()" style="width:100%; margin-bottom:15px; background:var(--glass-bg); color:var(--text); border:1px solid rgba(255,255,255,0.1); padding:10px; border-radius:12px; font-weight:bold; cursor:pointer;">🎬 Escanear Vídeo Completo (1 fps)</button>
                    <div id="video-scan-results" style="margin-bottom:15px;"></div>
                    <hr style="border:0; border-top:1px solid rgba(255,255,255,0.1); margin:15px 0;">
                    <p style="font-size:0.8rem; color:var(--text-dim); text-align:center;">O haz clic en "Analizar Caras en Fotograma Actual" abajo para corregir manualmente el fotograma visible.</p>
                `;
            }
        }


async function runAnalysis() {
            if (!currentFileObj) return;
            const currentRunPath = currentFileObj.path;
            const container = document.getElementById('lb-media-container');
            const mediaEl = container.querySelector('.lb-media-element');
            if (!mediaEl) return;
            
            if (isCurrentVideo && !mediaEl.paused) {
                mediaEl.pause();
            }
            
            document.querySelectorAll('.lb-bounding-box').forEach(b => b.remove());
            const cardsContainer = document.getElementById('person-cards-container');
            cardsContainer.innerHTML = '<div style="padding:20px; text-align:center;"><div class="loader-small"></div></div>';
            
            let timestamp = isCurrentVideo ? mediaEl.currentTime : null;
            let data;
            try {
                const res = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ path: currentFileObj.path, timestamp: timestamp, force: true })
                });
                data = await res.json();
            } catch (err) {
                console.error(err);
                cardsContainer.innerHTML = '<div style="padding:20px; text-align:center; color:#ff453a;">Error de conexión. Reintentando...</div>';
                return;
            }
            
            if (!currentFileObj || currentFileObj.path !== currentRunPath) return; cardsContainer.innerHTML = '';
            
            currentFaces = data.faces || [];
            if (data.faces && data.faces.length > 0) {
                let intrinsicWidth = isCurrentVideo ? mediaEl.videoWidth : mediaEl.naturalWidth;
                let intrinsicHeight = isCurrentVideo ? mediaEl.videoHeight : mediaEl.naturalHeight;
                if (!intrinsicWidth && data.faces.length > 0) {
                    intrinsicWidth = data.faces[0].img_width;
                    intrinsicHeight = data.faces[0].img_height;
                }
                
                // Sincronizar tamaño del contenedor con el tamaño real de la imagen renderizada
                if (mediaEl.clientWidth && mediaEl.clientHeight) {
                    container.style.width = mediaEl.clientWidth + 'px';
                    container.style.height = mediaEl.clientHeight + 'px';
                }
                
                let hasUnconfirmed = false;
                data.faces.forEach((face, idx) => {
                    if (face.identity === 'Desconocido' || face.identity.startsWith('IA (Pendiente)')) hasUnconfirmed = true;
                    createFaceElements(face, idx + 1, intrinsicWidth, intrinsicHeight, mediaEl, container, cardsContainer);
                });
                
                const btnIgnore = document.getElementById('btn-ignore-unconfirmed');
                if (btnIgnore) {
                    if (hasUnconfirmed) {
                        btnIgnore.style.display = 'block';
                        btnIgnore.innerHTML = `<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z"/><path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4L4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/></svg> Ignorar caras no confirmadas`;
                        btnIgnore.style.opacity = '1';
                        btnIgnore.style.pointerEvents = 'auto';
                    } else {
                        btnIgnore.style.display = 'none';
                    }
                }
            } else {
                cardsContainer.innerHTML = '<p style="font-size:0.8rem; color:var(--text-dim);">No se han detectado personas en este fotograma.</p>';
            }
        }
        
                function highlightFace(faceNum) {
            document.querySelectorAll('.lb-bounding-box').forEach(b => {
                b.style.borderColor = 'rgba(255, 255, 255, 0.4)';
                b.style.zIndex = '1';
                b.classList.remove('active');
            });
            document.querySelectorAll('.person-card').forEach(c => c.style.background = 'rgba(28, 28, 30, 0.5)');
            
            const box = document.getElementById(`bbox-${faceNum}`);
            if (box) {
                box.style.borderColor = '#0a84ff';
                box.style.zIndex = '10';
                box.classList.add('active');
                
                // Auto-Focus Zoom
                const mediaEl = document.getElementById('lb-media');
                if (mediaEl && box.dataset.faceX) {
                    const intrinsicWidth = mediaEl.naturalWidth || mediaEl.videoWidth;
                    const intrinsicHeight = mediaEl.naturalHeight || mediaEl.videoHeight;
                    
                    if (intrinsicWidth && intrinsicHeight) {
                        const fx = parseFloat(box.dataset.faceX);
                        const fy = parseFloat(box.dataset.faceY);
                        const fw = parseFloat(box.dataset.faceW);
                        const fh = parseFloat(box.dataset.faceH);
                        
                        const centerX = fx + (fw / 2);
                        const centerY = fy + (fh / 2);
                        
                        const renderScale = mediaEl.clientWidth / intrinsicWidth;
                        
                        const offX = centerX - (intrinsicWidth / 2);
                        const offY = centerY - (intrinsicHeight / 2);
                        
                        zoomLevel = 4.0; // Fixed zoom 400%
                        panX = -(offX * renderScale) * zoomLevel;
                        panY = -(offY * renderScale) * zoomLevel;
                        
                        applyZoomTransform();
                    }
                }
            }
            
            const card = document.getElementById(`person-card-${faceNum}`);
            if (card) {
                card.style.background = 'rgba(10, 132, 255, 0.2)';
                card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
        
        document.addEventListener('keydown', (e) => {
            // No actuar si estamos escribiendo en un input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;
            
            if (e.key === 'Delete' || e.key === 'Backspace') {
                const activeBox = document.querySelector('.lb-bounding-box.active');
                if (activeBox && currentFileObj) {
                    const faceNum = activeBox.id.replace('bbox-', '');
                    const falsePosId = JSON.stringify({categoria: 'Ignorar', identidad: 'Falso_Positivo'});
                    inlineCorrect(
                        encodeURIComponent(currentFileObj.path), 
                        falsePosId, 
                        faceNum, 
                        activeBox.dataset.faceX, 
                        activeBox.dataset.faceY, 
                        activeBox.dataset.faceW, 
                        activeBox.dataset.faceH
                    );
                }
            }
        });

        function createFaceElements(face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl, container, cardsContainer) {
            // 1. Bounding Box sobre la Foto (Movible y Redimensionable)
            const box = document.createElement('div');
            box.className = 'lb-bounding-box';
            box.id = `bbox-${faceNum}`;
            
            // Atributos de datos para el atajo de teclado
            box.dataset.faceX = face.x;
            box.dataset.faceY = face.y;
            box.dataset.faceW = face.width;
            box.dataset.faceH = face.height;
            
            const percX = (face.x / intrinsicWidth) * 100;
            const percY = (face.y / intrinsicHeight) * 100;
            const percW = (face.width / intrinsicWidth) * 100;
            const percH = (face.height / intrinsicHeight) * 100;
            
            box.style.left = `${percX}%`;
            box.style.top = `${percY}%`;
            box.style.width = `${percW}%`;
            box.style.height = `${percH}%`;
            
            const badge = document.createElement('div');
            badge.className = 'lb-bb-badge';
            badge.textContent = `#${faceNum}`;
            box.appendChild(badge);
            
            ['tl', 'tr', 'bl', 'br'].forEach(corner => {
                const handle = document.createElement('div');
                handle.className = `resize-handle handle-${corner}`;
                handle.dataset.corner = corner;
                box.appendChild(handle);
            });
            
            box.onclick = (e) => {
                if (box.dataset.wasDragged === 'true') {
                    box.dataset.wasDragged = 'false';
                    return;
                }
                if (e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION' || e.target.tagName === 'BUTTON') return;
                e.stopPropagation();
                highlightFace(faceNum);
                
                // Zoom dinámico al hacer clic en la caja si no está zoomeado
                if (zoomLevel === 1.0) {
                    zoomLevel = 2.5;
                    const percCenterX = (face.x + face.width / 2) / intrinsicWidth;
                    const percCenterY = (face.y + face.height / 2) / intrinsicHeight;
                    const container = document.getElementById('lb-media-container');
                    const cw = container.offsetWidth;
                    const ch = container.offsetHeight;
                    panX = (cw / 2 - cw * percCenterX) * zoomLevel;
                    panY = (ch / 2 - ch * percCenterY) * zoomLevel;
                    applyZoomTransform();
                }
                
                // Mostrar desplegable rápido directamente sobre la foto
                let existingMenu = box.querySelector('.lb-box-popup');
                if (existingMenu) {
                    existingMenu.remove();
                    return;
                }
                
                document.querySelectorAll('.lb-box-popup').forEach(m => m.remove());
                
                const popup = document.createElement('div');
                popup.className = 'lb-box-popup';
                popup.style.cssText = 'position:absolute; bottom:-65px; left:50%; transform:translateX(-50%); z-index:100; background:rgba(20,20,22,0.95); backdrop-filter:blur(20px); padding:8px; border-radius:12px; border:1px solid rgba(255,255,255,0.25); box-shadow:0 8px 30px rgba(0,0,0,0.6); display:flex; flex-direction:column; gap:6px; min-width:210px;';
                
                let pathParts1 = currentFileObj.path.split(/[\\/]/);
                let folderName = pathParts1.slice(-2, -1)[0];
                let categoryName = pathParts1.slice(-3, -2)[0];
                if (folderName === '_Dudosos') {
                    folderName = pathParts1.slice(-3, -2)[0];
                    categoryName = pathParts1.slice(-4, -3)[0];
                }
                
                let rejectedId = JSON.stringify({categoria: '_Dudosos', identidad: 'Desconocido'});
                
                let innerHtml = `
                    <div style="color:white; font-size:0.75rem; text-align:center; opacity:0.7; padding-bottom:4px; border-bottom:1px solid rgba(255,255,255,0.1); margin-bottom:4px;">Face #${faceNum}</div>
                `;
                innerHtml += generateReassignHTML(face, faceNum, 'quickReassignFace');
            popup.innerHTML = innerHtml;
            box.appendChild(popup);
        };
            
            // Hacer la caja arrastrable y redimensionable
            makeBoxInteractive(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl);
            
            container.appendChild(box);
            
            // 2. Avatar Recortado en Canvas
            let avatarUrl = updateAvatarCrop(mediaEl, face);
            
            // 3. Tarjeta en Sidebar
            const card = document.createElement('div');
            card.className = 'person-card';
            card.id = `pcard-${faceNum}`;
            
            let folderName, categoryName;
            if (currentCat && currentCat !== 'Resultados' && currentCat !== 'Personas Sin Nombre' && currentCat !== 'Limpieza Inteligente') {
                categoryName = currentCat;
                folderName = currentIdent;
            } else {
                let pathParts2 = currentFileObj.path.split(/[\\/]/);
                folderName = pathParts2.slice(-2, -1)[0];
                categoryName = pathParts2.slice(-3, -2)[0];
                if (folderName === '_Dudosos') {
                    folderName = pathParts2.slice(-3, -2)[0];
                    categoryName = pathParts2.slice(-4, -3)[0];
                }
            }
            
            card.innerHTML = `
                <div class="person-header" onclick="highlightFace(${faceNum})">
                    <img src="${avatarUrl}" class="person-avatar" id="pavatar-${faceNum}" alt="Face">
                    <div class="person-info">
                        <div class="person-name" id="pname-${faceNum}" style="display:flex; justify-content:space-between; align-items:center;">
                            <span>#${faceNum} ${face.identity}</span>
                            <button onclick="openEvolutionModal('${face.identity}'); event.stopPropagation();" style="background:#0a84ff; border:none; color:white; border-radius:4px; padding:2px 6px; font-size:10px; cursor:pointer;">📈 Evolución</button>
                        </div>
                        <div class="person-confidence" id="pconf-${faceNum}">
                            ${face.identity === folderName 
                                ? (face.confidence ? '<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M5.121 12.596a.5.5 0 1 0-.242.97l.613.153a.5.5 0 0 0 .242-.97l-.613-.153zM10.879 12.596a.5.5 0 0 0 .242.97l.613-.153a.5.5 0 1 0-.242-.97l-.613.153zM8 15a.5.5 0 0 0 .5-.5V14a.5.5 0 0 0-1 0v.5a.5.5 0 0 0 .5.5zM3 8a.5.5 0 0 0 .5.5h.5a.5.5 0 0 0 0-1h-.5A.5.5 0 0 0 3 8zm9.5 0a.5.5 0 0 0 .5-.5h-.5a.5.5 0 0 0 0 1h.5a.5.5 0 0 0 .5-.5z"/></svg> ' + face.confidence + ' (Propietario del Álbum)' : '<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M5.121 12.596a.5.5 0 1 0-.242.97l.613.153a.5.5 0 0 0 .242-.97l-.613-.153zM10.879 12.596a.5.5 0 0 0 .242.97l.613-.153a.5.5 0 1 0-.242-.97l-.613.153zM8 15a.5.5 0 0 0 .5-.5V14a.5.5 0 0 0-1 0v.5a.5.5 0 0 0 .5.5zM3 8a.5.5 0 0 0 .5.5h.5a.5.5 0 0 0 0-1h-.5A.5.5 0 0 0 3 8zm9.5 0a.5.5 0 0 0 .5-.5h-.5a.5.5 0 0 0 0 1h.5a.5.5 0 0 0 .5-.5z"/></svg> (Propietario del Álbum)') 
                                : (face.confidence ? (String(face.confidence).includes('Manual') ? '✏️ Editado a Mano' : face.confidence) : '<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M6 12.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1h-3a.5.5 0 0 1-.5-.5ZM3 8.062C3 6.76 4.235 5.765 5.53 5.889a28.02 28.02 0 0 1 4.94 0C11.765 5.765 13 6.76 13 8.062v1.157a.933.933 0 0 1-.765.935c-.845.147-2.34.346-4.235.346-1.895 0-3.39-.2-4.235-.346A.933.933 0 0 1 3 9.219V8.062Zm4.542-.827a.25.25 0 0 0-.217.068l-.92.9a24.767 24.767 0 0 1-1.871-.183.25.25 0 0 0-.068.495c.55.076 1.232.149 2.02.2a.25.25 0 0 0 .216-.068l.92-.9a.25.25 0 0 0-.08-.412Z"/></svg> IA (Pendiente)')}
                        </div>
                    </div>
                </div>
                ${generateReassignHTML(face, faceNum, 'quickReassignFace')}
            `;
            
            cardsContainer.appendChild(card);
        }

        function updateAvatarCrop(mediaEl, face) {
            try {
                const canvas = document.createElement('canvas');
                canvas.width = 100;
                canvas.height = 100;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(mediaEl, Math.max(0, face.x), Math.max(0, face.y), face.width, face.height, 0, 0, 100, 100);
                return canvas.toDataURL();
            } catch(e) {
                return '';
            }
        }

        function makeBoxInteractive(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl) {
            let isDragging = false;
            let isResizing = false;
            let currentHandle = null;
            let startX, startY, startLeft, startTop, startW, startH;
            const container = document.getElementById('lb-media-container');

            // Arrastrar Posición
            box.addEventListener('mousedown', (e) => {
                if (e.target.classList.contains('resize-handle')) return;
                if (e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION' || e.target.tagName === 'BUTTON') return;
                
                e.stopPropagation();
                isDragging = true;
                startX = e.clientX;
                startY = e.clientY;
                const popup = box.querySelector('.lb-box-popup');
                if (popup) popup.style.display = 'none';
                const rect = box.getBoundingClientRect();
                if (popup) popup.style.display = 'flex';
                const containerRect = container.getBoundingClientRect();
                startLeft = rect.left - containerRect.left;
                startTop = rect.top - containerRect.top;

                let isDragTicking = false;
                const onMouseMove = (ev) => {
                    if (!isDragging) return;
                    const dx = ev.clientX - startX;
                    const dy = ev.clientY - startY;
                    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) box.dataset.wasDragged = 'true';
                    const newLeft = startLeft + dx;
                    const newTop = startTop + dy;
                    if (!isDragTicking) {
                        window.requestAnimationFrame(() => {
                            box.style.left = `${(newLeft / containerRect.width) * 100}%`;
                            box.style.top = `${(newTop / containerRect.height) * 100}%`;
                            isDragTicking = false;
                        });
                        isDragTicking = true;
                    }
                };

                const onMouseUp = () => {
                    if (isDragging) {
                        isDragging = false;
                        document.removeEventListener('mousemove', onMouseMove);
                        document.removeEventListener('mouseup', onMouseUp);
                        saveBoxDimensions(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl);
                    }
                };

                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            });

            // Redimensionar Tamaño desde cualquier esquina
            const handles = box.querySelectorAll('.resize-handle');
            handles.forEach(handle => {
                handle.addEventListener('mousedown', (e) => {
                    e.stopPropagation();
                    isResizing = true;
                    currentHandle = handle.dataset.corner;
                    startX = e.clientX;
                    startY = e.clientY;
                    const popup = box.querySelector('.lb-box-popup');
                if (popup) popup.style.display = 'none';
                const rect = box.getBoundingClientRect();
                if (popup) popup.style.display = 'flex';
                    const containerRect = container.getBoundingClientRect();
                    startLeft = rect.left - containerRect.left;
                    startTop = rect.top - containerRect.top;
                    startW = rect.width;
                    startH = rect.height;

                    let isResizeTicking = false;
                    const onMouseMove = (ev) => {
                        if (!isResizing) return;
                        box.dataset.wasDragged = 'true';
                        const dx = ev.clientX - startX;
                        const dy = ev.clientY - startY;
                        let newW = startW;
                        let newH = startH;
                        let newLeft = startLeft;
                        let newTop = startTop;

                        if (currentHandle.includes('r')) {
                            newW = Math.max(20, startW + dx);
                        } else if (currentHandle.includes('l')) {
                            newW = Math.max(20, startW - dx);
                            if (newW > 20) newLeft = startLeft + dx;
                        }

                        if (currentHandle.includes('b')) {
                            newH = Math.max(20, startH + dy);
                        } else if (currentHandle.includes('t')) {
                            newH = Math.max(20, startH - dy);
                            if (newH > 20) newTop = startTop + dy;
                        }

                        if (!isResizeTicking) {
                            window.requestAnimationFrame(() => {
                                box.style.width = `${(newW / containerRect.width) * 100}%`;
                                box.style.height = `${(newH / containerRect.height) * 100}%`;
                                box.style.left = `${(newLeft / containerRect.width) * 100}%`;
                                box.style.top = `${(newTop / containerRect.height) * 100}%`;
                                isResizeTicking = false;
                            });
                            isResizeTicking = true;
                        }
                    };

                    const onMouseUp = () => {
                        if (isResizing) {
                            isResizing = false;
                            document.removeEventListener('mousemove', onMouseMove);
                            document.removeEventListener('mouseup', onMouseUp);
                            saveBoxDimensions(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl);
                        }
                    };

                    document.addEventListener('mousemove', onMouseMove);
                    document.addEventListener('mouseup', onMouseUp);
                });
            });
        }

        function saveBoxDimensions(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl) {
            const container = document.getElementById('lb-media-container');
            
            // Ocultar temporalmente el popup para que getBoundingClientRect no lo incluya y no estropee las coordenadas
            const popup = box.querySelector('.lb-box-popup');
            if (popup) popup.style.display = 'none';
            
            const rect = box.getBoundingClientRect();
            const mediaRect = mediaEl.getBoundingClientRect();
            
            if (popup) popup.style.display = 'flex';

            const scaleX = intrinsicWidth / mediaRect.width;
            const scaleY = intrinsicHeight / mediaRect.height;

            face.x = Math.round((rect.left - mediaRect.left) * scaleX);
            face.y = Math.round((rect.top - mediaRect.top) * scaleY);
            face.width = Math.round(rect.width * scaleX);
            face.height = Math.round(rect.height * scaleY);

            // Actualizar avatar en sidebar
            const avatarImg = document.getElementById(`pavatar-${faceNum}`);
            if (avatarImg) {
                avatarImg.src = updateAvatarCrop(mediaEl, face);
            }

            // Guardar permanentemente en backend y activar Reaprendizaje Activo
            if (face.identity && face.identity !== "Desconocido") {
                let pathParts3 = currentFileObj.path.split(/[\\/]/);
                let folderName = pathParts3.slice(-2, -1)[0];
                let categoryName = pathParts3.slice(-3, -2)[0];
                if (folderName === '_Dudosos') {
                    folderName = pathParts3.slice(-3, -2)[0];
                    categoryName = pathParts3.slice(-4, -3)[0];
                }
                
                fetch('/api/correct', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        path: currentFileObj.path,
                        new_categoria: categoryName,
                        new_identidad: face.identity,
                        face: {x: face.x, y: face.y, width: face.width, height: face.height},
                        apply_to_duplicates: true
                    })
                }).then(r => r.json()).then(data => {
                    if (data.success) {
                        showToast('Recuadro guardado. Actualizando galería...');
                        if (data.new_path) {
                            if (currentFileObj) currentFileObj.path = data.new_path.replace(/\\/g, '/');
                        }
                        loadGallery();
                        if (isCurrentVideo) {
                            setTimeout(() => closeLightbox(), 500);
                        }
                    } else if (data.error) {
                        alert("Error: " + data.error);
                    }
                });
            }
        }


        async function ignoreUnconfirmedFaces() {
            if (!currentFaces || currentFaces.length === 0) return;
            
            // Collect unconfirmed faces
            const unconfirmed = [];
            currentFaces.forEach((face, idx) => {
                if (face.identity === 'Desconocido' || face.identity.startsWith('IA (Pendiente)')) {
                    unconfirmed.push({ face: face, faceNum: idx + 1 });
                }
            });
            
            if (unconfirmed.length === 0) {
                showToast("No hay caras sin confirmar.");
                return;
            }
            
            if (!confirm(`¿Ignorar ${unconfirmed.length} caras no confirmadas?`)) return;
            
            document.getElementById('btn-ignore-unconfirmed').textContent = "Ignorando...";
            document.getElementById('btn-ignore-unconfirmed').style.opacity = '0.5';
            document.getElementById('btn-ignore-unconfirmed').style.pointerEvents = 'none';
            
            for (let i = 0; i < unconfirmed.length; i++) {
                const item = unconfirmed[i];
                const face = item.face;
                let idObj = {categoria: "Ignorar", identidad: "Ignorar_Irrelevante"};
                
                try {
                    const res = await fetch('/api/correct', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ 
                            path: currentFileObj.path, 
                            new_categoria: idObj.categoria, 
                            new_identidad: idObj.identidad,
                            face: {
                            x: face.box ? face.box[0] : (face.x || 0),
                            y: face.box ? face.box[1] : (face.y || 0),
                            width: face.box ? face.box[2] : (face.width || 0),
                            height: face.box ? face.box[3] : (face.height || 0)
                        },
                            apply_to_duplicates: false
                        })
                    });
                    const data = await res.json();
                    if(data.success && data.new_path && currentFileObj) {
                        currentFileObj.path = data.new_path;
                    }
                } catch(e) {
                    console.error("Error ignoring face", e);
                }
            }
            
            showToast(`${unconfirmed.length} caras ignoradas.`);
            
            // Refresh
            if (currentCat === 'Limpieza Inteligente') {
                const gridItem = document.getElementById('grid-container').children[currentItemIndex];
                if (gridItem) {
                    gridItem.style.opacity = '0.3';
                    gridItem.style.pointerEvents = 'none';
                }
            } else if (currentCat && currentIdent) {
                renderGrid(currentCat, currentIdent);
            }
            
            // Re-open lightbox to refresh faces list
            openLightbox(currentFileObj);
        }

        async function quickReassignFace(valStr, faceNum) {
            const face = currentFaces[faceNum - 1];
            if (!face) return;
            await inlineCorrect(encodeURIComponent(currentFileObj.path), valStr, faceNum, face.x, face.y, face.width, face.height);
        }

        async function inlineCorrect(pathEncoded, valStr, faceNum, faceX, faceY, faceW, faceH) {
            releaseMediaElement();
            if(!valStr) return;
            const targetPath = (currentFileObj && currentFileObj.path) ? currentFileObj.path : decodeURIComponent(pathEncoded);
            if(!targetPath) return;

            let idObj;
            if(valStr === 'NEW') {
                const newIdent = prompt("Introduce el nombre completo (ej: 'F. Laura' para Familia o 'C. Pedro' para Conocidos):");
                if(!newIdent) return;
                let defaultCat = "Familia";
                if (newIdent.startsWith("C. ")) {
                    defaultCat = "Conocidos";
                } else if (newIdent.startsWith("F. ") || newIdent.startsWith("F_")) {
                    defaultCat = "Familia";
                } else if (newIdent.startsWith("P. ")) {
                    defaultCat = "Profesores";
                }
                const newCat = prompt("Introduce la categoría ('Familia', 'Conocidos', etc.):", defaultCat);
                if(!newCat) return;
                idObj = {categoria: newCat, identidad: newIdent};
            } else {
                idObj = JSON.parse(valStr);
            }
            
            // === INSTANT UI FEEDBACK (before network request) ===
            const pcardEl = document.getElementById(`pcard-${faceNum}`);
            const pnameEl = document.getElementById(`pname-${faceNum}`);
            const pconfEl = document.getElementById(`pconf-${faceNum}`);
            const selectEl = document.querySelector(`#pcard-${faceNum} select`);
            if (selectEl) { selectEl.disabled = true; selectEl.style.opacity = '0.5'; }
            if (pnameEl) {
                pnameEl.textContent = `⏳ Guardando ${idObj.identidad}...`;
                pnameEl.style.color = '#ff9f0a';
            }
            showToast(`⏳ Asignando a '${idObj.identidad}'...`);

            let applyToDuplicates = false;
            try {
                const dupRes = await fetch('/api/duplicates', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ path: targetPath })
                });
                const dupData = await dupRes.json();
                if (dupData.duplicate) {
                    applyToDuplicates = true;
                }
            } catch (e) {
                console.error("Error checking duplicates", e);
            }

            const res = await fetch('/api/correct', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ 
                    path: targetPath, 
                    new_categoria: idObj.categoria, 
                    new_identidad: idObj.identidad,
                    face: {x: faceX, y: faceY, width: faceW, height: faceH},
                    apply_to_duplicates: applyToDuplicates
                })
            });
            
            const data = await res.json();
            // Re-enable select
            if (selectEl) { selectEl.disabled = false; selectEl.style.opacity = '1'; }
            if(data.success) {
                if (data.new_path && currentFileObj) {
                    currentFileObj.path = data.new_path;
                }
                showToast(`Asignado a '${idObj.identidad}'. Memoria guardada.`);
                
                if (typeof applyToDuplicates !== 'undefined' && applyToDuplicates) {
                    closeLightbox();
                    loadGallery();
                } else {
                    // Actualizar localmente SIN PARPADEO
                    if (idObj.identidad === 'Ignorar_Irrelevante' || idObj.identidad === 'Falso_Positivo') {
                        const bbox = document.getElementById(`bbox-${faceNum}`);
                        const pcard = document.getElementById(`pcard-${faceNum}`);
                        if (bbox) bbox.remove();
                        if (pcard) pcard.remove();
                    } else {
                                                const pname = document.getElementById(`pname-${faceNum}`);
                        const pconf = document.getElementById(`pconf-${faceNum}`);
                        if (pname) pname.textContent = `#${faceNum} ${idObj.identidad}`;
                        if (pconf) pconf.textContent = '100.0% (Manual)';
                    }
                    
                    if (currentFileObj) {
                        if (!currentFileObj.source.includes("Manual")) {
                            currentFileObj.source = currentFileObj.source + " + Manual";
                        }
                        const gridBadge = document.getElementById(`source-${currentItemIndex}`);
                        if (gridBadge) {
                            if (currentFileObj.source.includes('Dataset')) {
                                gridBadge.className = 'badge badge-dataset';
                                gridBadge.textContent = '🔒 Dataset + ✏️ Manual';
                            } else {
                                gridBadge.className = 'badge badge-manual';
                                gridBadge.textContent = '✏️ Manual';
                            }
                        }
                    }

                    await loadIdentities();
                    if (currentCat === 'Limpieza Inteligente') {
                        // Don't re-render grid because it's a dynamic list
                        // But we should remove the current item from the list visually
                        const gridItem = document.getElementById('grid-container').children[currentItemIndex];
                        if (gridItem) {
                            gridItem.style.opacity = '0.3';
                            gridItem.style.pointerEvents = 'none';
                        }
                    } else if (currentCat && currentIdent) {
                        renderGrid(currentCat, currentIdent);
                    }
                }
            } else {
                showToast(data.error || "Error al asignar.", true);
            }
        }

        function enableManualSelection() {
            if (!currentFileObj) return;
            resetZoom(); // Prevenir panning y offsets erróneos
            window.isDrawingMode = true;
            const container = document.getElementById('lb-media-container');
            const mediaEl = container.querySelector('.lb-media-element');
            if (!mediaEl) return;
            
            mediaEl.draggable = false;
            
            showToast("Arrastra sobre la foto para crear un recuadro de persona.");
            container.style.cursor = 'crosshair';
            
            let startX, startY, selectBox, isDrawing = false;
            
            const onMouseDown = (e) => {
                e.preventDefault();
                isDrawing = true;
                const rect = container.getBoundingClientRect();
                startX = e.clientX - rect.left;
                startY = e.clientY - rect.top;
                
                selectBox = document.createElement('div');
                selectBox.style.cssText = `position:absolute; left:${startX}px; top:${startY}px; border:2px dashed #30d158; background:rgba(48,209,88,0.25); pointer-events:none; z-index:9999; box-sizing:border-box;`;
                container.appendChild(selectBox);
                
                const onMouseMove = (ev) => {
                    if (!isDrawing) return;
                    const currentX = ev.clientX - rect.left;
                    const currentY = ev.clientY - rect.top;
                    const width = Math.abs(currentX - startX);
                    const height = Math.abs(currentY - startY);
                    selectBox.style.left = `${Math.min(startX, currentX)}px`;
                    selectBox.style.top = `${Math.min(startY, currentY)}px`;
                    selectBox.style.width = `${width}px`;
                    selectBox.style.height = `${height}px`;
                };
                
                const onMouseUp = async (ev) => {
                    if (!isDrawing) return;
                    isDrawing = false;
                    
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                    container.removeEventListener('mousedown', onMouseDown);
                    container.style.cursor = 'default';
                    window.isDrawingMode = false;
                    
                    const rect = container.getBoundingClientRect();
                    const endX = ev.clientX - rect.left;
                    const endY = ev.clientY - rect.top;
                    
                    const boxW = Math.abs(endX - startX);
                    const boxH = Math.abs(endY - startY);
                    
                    if (selectBox) selectBox.remove();
                    if (boxW < 10 || boxH < 10) return;
                    
                    let isCurrentVideo = mediaEl.tagName === 'VIDEO';
                    let intrinsicWidth = isCurrentVideo ? mediaEl.videoWidth : mediaEl.naturalWidth;
                    let intrinsicHeight = isCurrentVideo ? mediaEl.videoHeight : mediaEl.naturalHeight;
                    
                    const mediaRect = mediaEl.getBoundingClientRect();
                    const containerRect = container.getBoundingClientRect();
                    
                    const offsetX = mediaRect.left - containerRect.left;
                    const offsetY = mediaRect.top - containerRect.top;
                    
                    const mediaStartX = startX - offsetX;
                    const mediaStartY = startY - offsetY;
                    const mediaEndX = endX - offsetX;
                    const mediaEndY = endY - offsetY;
                    
                    const scaleX = intrinsicWidth / mediaRect.width;
                    const scaleY = intrinsicHeight / mediaRect.height;
                    
                    let realX = Math.round(Math.min(mediaStartX, mediaEndX) * scaleX);
                    let realY = Math.round(Math.min(mediaStartY, mediaEndY) * scaleY);
                    let realW = Math.round(boxW * scaleX);
                    let realH = Math.round(boxH * scaleY);
                    
                    realX = Math.max(0, realX);
                    realY = Math.max(0, realY);
                    if (realX + realW > intrinsicWidth) realW = intrinsicWidth - realX;
                    if (realY + realH > intrinsicHeight) realH = intrinsicHeight - realY;
                    
                    const newFace = { x: realX, y: realY, width: realW, height: realH, identity: "Desconocido", confidence: "Selección manual" };
                    const nextNum = document.querySelectorAll('.lb-bounding-box').length + 1;
                    const cardsContainer = document.getElementById('person-cards-container');
                    
                    createFaceElements(newFace, nextNum, intrinsicWidth, intrinsicHeight, mediaEl, container, cardsContainer);
                    highlightFace(nextNum);
                    
                    const select = document.getElementById(`pselect-${nextNum}`);
                    if (select) {
                        select.focus();
                        select.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                    showToast(`Recuadro #${nextNum} listo. Selecciona la persona en el panel lateral.`);
                };
                
                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            };
            
            container.addEventListener('mousedown', onMouseDown);
        }

        async function runMassCleanup() {
            if (!confirm('¿Deseas analizar todas las carpetas "Persona Nueva" y reasignar automáticamente a las caras conocidas (seguridad > 60%)? Esto puede tardar unos minutos.')) return;
            
            showToast('Iniciando limpieza masiva... Por favor, no cierres esta página.', false);
            
            try {
                const res = await fetch('/api/mass_cleanup', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    showToast(`<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zm-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z"/></svg> Limpieza masiva completada. Se reasignaron ${data.moved_count} imágenes.`);
                    await loadGallery();
                } else {
                    showToast('Error en la limpieza masiva: ' + data.error, true);
                }
            } catch (err) {
                showToast('Error de conexión en limpieza masiva', true);
            }
        }

        let selectedPaths = new Set();
        
        function toggleSelection(e, path) {
            e.stopPropagation(); // Evitar abrir el lightbox
            if (selectedPaths.has(path)) {
                selectedPaths.delete(path);
                e.target.classList.remove('selected');
            } else {
                selectedPaths.add(path);
                e.target.classList.add('selected');
            }
            updateFloatingBar();
        }
        
        function updateFloatingBar() {
            const bar = document.getElementById('floating-action-bar');
            const count = document.getElementById('fab-count');
            
            if (selectedPaths.size > 0) {
                count.innerText = `${selectedPaths.size} seleccionadas`;
                bar.classList.add('visible');
                
                // Poblar selectores si está vacío
                const select = document.getElementById('fab-reassign-select');
                if (select.options.length <= 1) {
                    populateFabSelect(select);
                }
            } else {
                bar.classList.remove('visible');
            }
        }
        
        function populateFabSelect(select) {
            select.innerHTML = '<option value="">-- Reasignar a... --</option>';
            const personas = new Set();
            if (identitiesList) {
                identitiesList.forEach(id => {
                    if (id.categoria === 'Conocidos' || id.categoria === 'Familiares') {
                        personas.add(id.identidad);
                    }
                });
            }
            const sorted = Array.from(personas).sort();
            sorted.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p;
                opt.innerText = p;
                select.appendChild(opt);
            });
        }
        
        function clearSelection() {
            selectedPaths.clear();
            document.querySelectorAll('.select-checkbox.selected').forEach(el => el.classList.remove('selected'));
            updateFloatingBar();
        }
        
        async function applyBulkReassign() {
            const select = document.getElementById('fab-reassign-select');
            const val = select.value;
            if (!val) {
                showToast('Selecciona una persona primero', true);
                return;
            }
            await performBulkAction(val);
        }
        
        async function applyBulkIgnore() {
            if(confirm(`¿Ignorar las ${selectedPaths.size} fotos seleccionadas?`)) {
                await performBulkAction('Ignorar');
            }
        }
        
        async function performBulkAction(identity) {
            const paths = Array.from(selectedPaths);
            const res = await fetch('/api/correct_bulk', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ paths, new_identity: identity })
            });
            const data = await res.json();
            if (data.success) {
                showToast(`Se han actualizado ${data.count} caras masivamente 🎉`);
                clearSelection();
                loadGallery(); // Recargar cuadrícula
            } else {
                showToast(`Error: ${data.error}`, true);
            }
        }


        let boxesVisible = true;
        function toggleBoxes() {
            boxesVisible = !boxesVisible;
            document.querySelectorAll('.lb-bounding-box').forEach(b => {
                b.style.opacity = boxesVisible ? '1' : '0';
                b.style.pointerEvents = boxesVisible ? 'auto' : 'none';
            });
            const btn = document.getElementById('btn-toggle-boxes');
            if (btn) btn.innerHTML = boxesVisible ? '<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8zM1.173 8a13.133 13.133 0 0 1 1.66-2.043C4.12 4.668 5.88 3.5 8 3.5c2.12 0 3.879 1.168 5.168 2.457A13.133 13.133 0 0 1 14.828 8c-.058.087-.122.183-.195.288-.335.48-.83 1.12-1.465 1.755C11.879 11.332 10.119 12.5 8 12.5c-2.12 0-3.879-1.168-5.168-2.457A13.134 13.134 0 0 1 1.172 8z"/><path d="M8 5.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5zM4.5 8a3.5 3.5 0 1 1 7 0 3.5 3.5 0 0 1-7 0z"/></svg> Ocultar Recuadros' : '<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8zM1.173 8a13.133 13.133 0 0 1 1.66-2.043C4.12 4.668 5.88 3.5 8 3.5c2.12 0 3.879 1.168 5.168 2.457A13.133 13.133 0 0 1 14.828 8c-.058.087-.122.183-.195.288-.335.48-.83 1.12-1.465 1.755C11.879 11.332 10.119 12.5 8 12.5c-2.12 0-3.879-1.168-5.168-2.457A13.134 13.134 0 0 1 1.172 8z"/><path d="M8 5.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5zM4.5 8a3.5 3.5 0 1 1 7 0 3.5 3.5 0 0 1-7 0z"/></svg> Mostrar Recuadros';
        }

        async function scanFullVideo() {
            if (!currentFileObj || !isCurrentVideo) return;
            const btn = document.getElementById('btn-scan-video');
            const resDiv = document.getElementById('video-scan-results');
            if(!btn || !resDiv) return;
            
            btn.textContent = "⏳ Escaneando (puede tardar unos segundos)...";
            btn.style.pointerEvents = 'none';
            btn.style.opacity = '0.5';
            resDiv.innerHTML = '<div style="text-align:center;"><div class="loader-small"></div></div>';
            
            try {
                const res = await fetch('/api/scan_video', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ path: currentFileObj.path })
                });
                const data = await res.json();
                
                if (data.error) {
                    resDiv.innerHTML = `<p style="color:#ff453a;">Error: ${data.error}</p>`;
                } else if (data.detections && data.detections.length > 0) {
                    let html = '<h4 style="margin:0 0 10px 0; color:var(--text); font-size:0.9rem;">Personas Detectadas:</h4>';
                    data.detections.forEach(d => {
                        html += `<div style="background:rgba(0,0,0,0.3); padding:8px; border-radius:8px; margin-bottom:8px;">`;
                        html += `<div style="font-weight:bold; color:#0a84ff; margin-bottom:4px;"><svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm2-3a2 2 0 1 1-4 0 2 2 0 0 1 4 0zm4 8c0 1-1 1-1 1H3s-1 0-1-1 1-4 6-4 6 3 6 4zm-1-.004c-.001-.246-.154-.986-.832-1.664C11.516 10.68 10.289 10 8 10c-2.29 0-3.516.68-4.168 1.332-.678.678-.83 1.418-.832 1.664h10z"/></svg> ${d.identity}</div>`;
                        html += `<div style="font-size:0.8rem; color:var(--text-dim);">Segundos: `;
                        d.seconds.forEach(sec => {
                            html += `<span onclick="document.getElementById('lb-media-container').querySelector('video').currentTime = ${sec}" style="cursor:pointer; display:inline-block; padding:2px 6px; background:rgba(255,255,255,0.1); border-radius:4px; margin:2px; transition:0.2s;">${sec}s</span>`;
                        });
                        html += `</div></div>`;
                    });
                    resDiv.innerHTML = html;
                } else {
                    resDiv.innerHTML = '<p style="color:var(--text-dim); font-size:0.8rem;">No se encontraron caras conocidas en todo el vídeo.</p>';
                }
            } catch (err) {
                resDiv.innerHTML = '<p style="color:#ff453a;">Error de conexión al escanear vídeo.</p>';
            }
            
            btn.textContent = "🎬 Volver a Escanear Vídeo";
            btn.style.pointerEvents = 'auto';
            btn.style.opacity = '1';
        }


// --- INJECTED FUNCTIONS ---
async function removeFromFolder() {
    releaseMediaElement();
    if (!currentFileObj || !currentFileObj.path || !currentCat || !currentIdent) return;
    const currentAnalysisPath = currentFileObj.path;
    if (!confirm(`¿Estás seguro de que quieres quitar esta foto de la carpeta de ${currentIdent}?`)) return;
    
    try {
        const res = await fetch('/api/remove_from_folder', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                path: currentAnalysisPath,
                cat: currentCat,
                ident: currentIdent
            })
        });
        const data = await res.json();
        
        if (data.success) {
            showToast(`<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zm-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z"/></svg> Foto quitada de la carpeta correctamente.`);
            closeLightbox();
            
            // Remove item from currentFolderItems and DOM
            if (typeof currentFolderItems !== 'undefined' && currentFolderItems) {
                currentFolderItems = currentFolderItems.filter(it => it.path !== currentAnalysisPath);
                if (fullGallery && fullGallery[currentCat] && fullGallery[currentCat][currentIdent]) {
                    fullGallery[currentCat][currentIdent] = fullGallery[currentCat][currentIdent].filter(it => it.path !== currentAnalysisPath);
                }
                const gridContainer = document.getElementById('grid-container');
                if (gridContainer && gridContainer.children[currentItemIndex]) {
                    gridContainer.children[currentItemIndex].remove();
                }
                const subEl = document.getElementById('gallery-subtitle');
                if (subEl) subEl.textContent = `${currentFolderItems.length} elementos`;
            }
            await loadGallery();
        } else {
            alert(data.error || "Error al quitar la foto");
        }
    } catch(e) {
        alert("Error de conexión");
    }
}

function triggerDeepScanLightbox() {
    if (!currentFileObj || !currentFileObj.path) return;
    const currentAnalysisPath = currentFileObj.path;
    if (!confirm("Esto forzará una búsqueda exhaustiva de caras ignorando límites de confianza. ¿Continuar?")) return;
    
    fetch('/api/detect_deep', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({path: currentAnalysisPath})
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else if (!data.faces || data.faces.length === 0) {
            alert("No se ha encontrado ninguna persona, ni siquiera con la detección profunda.");
        } else {
            alert("¡Detección profunda exitosa! Recargando caras...");
            openLightbox(currentFileObj);
        }
    })
    .catch(err => {
        console.error(err);
    });
}

function toggleMetadata() {
    const sidebar = document.getElementById('metadata-panel');
    if (sidebar.style.display === 'none' || sidebar.style.display === '') {
        sidebar.style.display = 'block';
    } else {
        sidebar.style.display = 'none';
    }
}
// --- END INJECTED FUNCTIONS ---


let currentPhotoFilterMode = 'all';

function setPhotoFilter(mode, btnEl) {
    currentPhotoFilterMode = mode;
    document.querySelectorAll('.filter-toggle-btn').forEach(b => {
        b.style.background = 'transparent';
        b.style.color = '#aaa';
        b.style.fontWeight = 'normal';
    });
    if (btnEl) {
        btnEl.style.background = '#0a84ff';
        btnEl.style.color = 'white';
        btnEl.style.fontWeight = 'bold';
    }
    applyPhotoFilter();
}

function applyPhotoFilter() {
    const grid = document.getElementById('grid-container');
    if (!grid || !currentFolderItems) return;
    const cards = grid.children;
    
    currentFolderItems.forEach((item, idx) => {
        const card = cards[idx];
        if (!card) return;
        
        const numFaces = item.num_faces || 0;
        const hasYo = item.has_yo || (item.identities && (item.identities.includes('YO') || item.identities.includes('yo')));
        let show = true;
        
        if (currentPhotoFilterMode === 'solo') {
            show = (numFaces === 1);
        } else if (currentPhotoFilterMode === 'group') {
            show = (numFaces > 1);
        } else if (currentPhotoFilterMode === 'with_me') {
            show = !!hasYo;
        } else if (currentPhotoFilterMode === 'without_me') {
            show = !hasYo;
        }
        
        if (show) {
            card.style.display = 'flex';
        } else {
            card.style.display = 'none';
        }
    });
}


function releaseMediaElement() {
    try {
        const mediaEl = document.querySelector('.lb-media-element');
        if (mediaEl) {
            mediaEl.pause();
            mediaEl.removeAttribute('src');
            mediaEl.load();
        }
    } catch(e){}
}


async function applyBulkRemoveFromFolder() {
    if (selectedPaths.size === 0) return;
    if (!currentCat || !currentIdent) {
        showToast("Abre un álbum específico primero.", true);
        return;
    }
    if (!confirm(`¿Seguro que quieres quitar las ${selectedPaths.size} fotos seleccionadas de '${currentIdent}' y enviarlas a re-análisis?`)) return;
    
    showToast(`⏳ Quitando ${selectedPaths.size} fotos de '${currentIdent}'...`);
    let count = 0;
    
    for (const path of Array.from(selectedPaths)) {
        try {
            const res = await fetch('/api/remove_from_folder', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    path: path,
                    cat: currentCat,
                    ident: currentIdent
                })
            });
            const data = await res.json();
            if (data.success) count++;
        } catch(e){}
    }
    
    showToast(`<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zm-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z"/></svg> ${count} fotos quitadas correctamente.`);
    clearSelection();
    await loadIdentities();
    await loadGallery();
}


async function purgeExactDuplicates() {
    if (!confirm("¿Deseas escanear y eliminar automáticamente todos los duplicados exactos (archivos idénticos en disco)? Conservaremos siempre la mejor copia.")) return;
    
    showToast("⏳ Escaneando y eliminando duplicados idénticos...", false);
    
    try {
        const res = await fetch('/api/purge_exact_duplicates', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast(`<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zm-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z"/></svg> Limpieza completada: Se eliminaron ${data.purged_count} copias duplicadas idénticas.`);
            await loadIdentities();
            await loadGallery();
        } else {
            showToast("Error limpiando duplicados: " + (data.error || "Desconocido"), true);
        }
    } catch(err) {
        showToast("Error de conexión al purgar duplicados", true);
    }
}


// ==========================================
// FUNCIONES DE LIMPIEZA DE DUPLICADOS EXACTOS
// ==========================================
window.openExactDuplicatesModal = async function() {
    const m = document.getElementById('modal-duplicates');
    if (!m) return;
    m.style.display = 'flex';
    document.getElementById('duplicates-loading').style.display = 'block';
    document.getElementById('duplicates-content').style.display = 'none';
    
    try {
        const res = await fetch('/api/duplicates_scan');
        const data = await res.json();
        
        document.getElementById('duplicates-loading').style.display = 'none';
        const container = document.getElementById('duplicates-content');
        container.style.display = 'block';
        
        if (!data.groups || data.groups.length === 0) {
            container.innerHTML = `<div style="text-align:center; padding:30px; color:#30d158;">
                <h3>🎉 ¡No se han encontrado duplicados exactos!</h3>
                <p style="color:#aaa;">Tu galería está 100% libre de imágenes idénticas repetidas.</p>
            </div>`;
            return;
        }
        
        let htmlStr = `<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; background:rgba(255,159,10,0.1); padding:15px; border-radius:10px; border:1px solid #ff9f0a;">
            <div>
                <strong style="color:#ff9f0a;">Se han detectado ${data.groups.length} grupos de duplicados exactos.</strong>
                <div style="font-size:0.9rem; color:#aaa;">Espacio recuperable: ${data.total_waste_mb} MB</div>
            </div>
            <button onclick="cleanAllExactDuplicates()" style="background:#ff9f0a; color:#000; font-weight:bold; border:none; padding:10px 18px; border-radius:8px; cursor:pointer;">
                ⚡ Limpiar Todos (${data.total_waste_mb} MB)
            </button>
        </div>`;
        
        data.groups.forEach((g, idx) => {
            htmlStr += `<div style="background:#2c2c2e; border-radius:12px; padding:15px; margin-bottom:15px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <span style="font-weight:bold; color:#ffcc00;">Grupo ${idx+1} (${g.files.length} copias idénticas - ${g.waste_mb} MB descartables)</span>
                    <button onclick="cleanExactDuplicatesGroup('${g.hash}')" style="background:rgba(255,159,10,0.2); color:#ff9f0a; border:1px solid #ff9f0a; padding:6px 12px; border-radius:6px; cursor:pointer; font-weight:bold;">
                        Conservar 1 y Borrar ${g.files.length-1}
                    </button>
                </div>
                <div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap:10px;">`;
            
            g.files.forEach((f, fIdx) => {
                htmlStr += `<div style="position:relative; background:#1c1c1e; border-radius:8px; overflow:hidden; border:2px solid ${fIdx===0?'#30d158':'#555'};">
                    <img src="/api/thumbnail?path=${encodeURIComponent(f.path)}" style="width:100%; height:110px; object-fit:cover;">
                    <div style="padding:5px; font-size:0.75rem; word-break:break-all; color:${fIdx===0?'#30d158':'#aaa'};">
                        ${fIdx===0?'⭐ CONSERVAR':`Copia ${fIdx}`} (${(f.size/1024/1024).toFixed(1)}MB)
                    </div>
                </div>`;
            });
            htmlStr += `</div></div>`;
        });
        
        container.innerHTML = htmlStr;
    } catch(e) {
        document.getElementById('duplicates-loading').style.display = 'none';
        alert("Error al escanear duplicados: " + e);
    }
};

window.closeExactDuplicatesModal = function() {
    const m = document.getElementById('modal-duplicates');
    if (m) m.style.display = 'none';
};

window.cleanExactDuplicatesGroup = async function(hash) {
    if (!confirm("¿Deseas eliminar las copias duplicadas de este grupo y conservar solo 1?")) return;
    try {
        const res = await fetch('/api/duplicates_clean', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ hash: hash })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zm-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z"/></svg> Duplicados eliminados correctamente.`);
            openExactDuplicatesModal();
            loadGallery();
        }
    } catch(e) { alert("Error de conexión"); }
};

window.cleanAllExactDuplicates = async function() {
    if (!confirm("¿Seguro que deseas eliminar automáticamente TODOS los duplicados exactos detectados y liberar espacio?")) return;
    try {
        const res = await fetch('/api/duplicates_clean', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ clean_all: true })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`🎉 ¡Limpieza masiva completada! Liberados ${data.freed_mb} MB.`);
            openExactDuplicatesModal();
            loadGallery();
        }
    } catch(e) { alert("Error de conexión"); }
};


// ==========================================
// FUNCIONES DE FOTOS PARECIDAS Y RÁFAGAS
// ==========================================
window.openSimilarPhotosModal = async function() {
    const m = document.getElementById('modal-similar');
    if (!m) return;
    m.style.display = 'flex';
    document.getElementById('similar-loading').style.display = 'block';
    document.getElementById('similar-content').style.display = 'none';
    
    try {
        const res = await fetch('/api/similar_scan');
        const data = await res.json();
        
        document.getElementById('similar-loading').style.display = 'none';
        const container = document.getElementById('similar-content');
        container.style.display = 'block';
        
        if (!data.groups || data.groups.length === 0) {
            container.innerHTML = `<div style="text-align:center; padding:30px; color:#30d158;">
                <h3><svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M15 12a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h1.172a3 3 0 0 0 2.12-.879l.83-.828A1 1 0 0 1 6.827 3h2.344a1 1 0 0 1 .707.293l.828.828A3 3 0 0 0 12.828 5H14a1 1 0 0 1 1 1v6zM2 4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-1.172a2 2 0 0 1-1.414-.586l-.828-.828A2 2 0 0 0 9.172 2H6.828a2 2 0 0 0-1.414.586l-.828.828A2 2 0 0 1 3.172 4H2z"/><path d="M8 11a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5zm0 1a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM3 6.5a.5.5 0 1 1-1 0 .5.5 0 0 1 1 0z"/></svg> ¡No hay ráfagas ni fotos muy parecidas acumuladas!</h3>
                <p style="color:#aaa;">Todas tus secuencias de fotos son únicas y nítidas.</p>
            </div>`;
            return;
        }
        
        let htmlStr = `<div style="margin-bottom:20px; background:rgba(191,90,242,0.1); padding:15px; border-radius:10px; border:1px solid #bf5af2;">
            <strong style="color:#bf5af2;">Se han detectado ${data.groups.length} ráfagas o secuencias de fotos parecidas.</strong>
            <div style="font-size:0.9rem; color:#aaa;">La IA ha evaluado la nitidez mediante la varianza de Laplaciano para destacar la foto de mejor calidad.</div>
        </div>`;
        
        data.groups.forEach((g, idx) => {
            htmlStr += `<div style="background:#2c2c2e; border-radius:12px; padding:15px; margin-bottom:15px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <span style="font-weight:bold; color:#d0fd38;">Secuencia ${idx+1} (${g.files.length} fotos del mismo momento)</span>
                    <button onclick="cleanSimilarGroup('${g.group_id}')" style="background:rgba(191,90,242,0.2); color:#bf5af2; border:1px solid #bf5af2; padding:6px 12px; border-radius:6px; cursor:pointer; font-weight:bold;">
                        Conservar la MÁS NÍTIDA y Borrar el Resto
                    </button>
                </div>
                <div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap:10px;">`;
            
            g.files.forEach((f) => {
                const isBest = f.is_sharpest;
                htmlStr += `<div style="position:relative; background:#1c1c1e; border-radius:8px; overflow:hidden; border:2px solid ${isBest?'#30d158':'#444'};">
                    <img src="/api/thumbnail?path=${encodeURIComponent(f.path)}" style="width:100%; height:110px; object-fit:cover;">
                    <div style="padding:5px; font-size:0.75rem; color:${isBest?'#30d158':'#aaa'}; font-weight:${isBest?'bold':'normal'};">
                        ${isBest?'⭐ MÁS NÍTIDA':`Simil (${f.sharpness_score}pt)`}
                    </div>
                </div>`;
            });
            htmlStr += `</div></div>`;
        });
        
        container.innerHTML = htmlStr;
    } catch(e) {
        document.getElementById('similar-loading').style.display = 'none';
        alert("Error al escanear fotos parecidas: " + e);
    }
};

window.closeSimilarPhotosModal = function() {
    const m = document.getElementById('modal-similar');
    if (m) m.style.display = 'none';
};

window.cleanSimilarGroup = async function(groupId) {
    if (!confirm("¿Deseas conservar únicamente la foto más nítida de esta secuencia y descartar las demás?")) return;
    try {
        const res = await fetch('/api/similar_clean', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ group_id: groupId })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zm-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z"/></svg> Ráfaga optimizada conservando la foto más nítida.`);
            openSimilarPhotosModal();
            loadGallery();
        }
    } catch(e) { alert("Error de conexión"); }
};


let selectedMode = 'local';

function selectStorageMode(mode) {
    selectedMode = mode;
    document.getElementById('opt-local').style.border = mode === 'local' ? '2px solid #a855f7' : '2px solid transparent';
    document.getElementById('opt-gdrive').style.border = mode === 'gdrive' ? '2px solid #a855f7' : '2px solid transparent';
    document.getElementById('opt-local').style.background = mode === 'local' ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.02)';
    document.getElementById('opt-gdrive').style.background = mode === 'gdrive' ? 'rgba(255,255,255,0.08)' : 'rgba(255,255,255,0.02)';
    
    document.getElementById('field-local').style.display = mode === 'local' ? 'block' : 'none';
    document.getElementById('field-gdrive').style.display = mode === 'gdrive' ? 'block' : 'none';
}

function checkSetupConfig() {
    fetch('/api/config')
        .then(r => r.json())
        .then(cfg => {
            if (cfg.mode) selectStorageMode(cfg.mode);
            if (cfg.local_path) document.getElementById('input-local-path').value = cfg.local_path;
            if (cfg.gdrive_folder_id) document.getElementById('input-gdrive-url').value = 'https://drive.google.com/drive/folders/' + cfg.gdrive_folder_id;
        })
        .catch(() => {});
}

function openSetupModal() {
    document.getElementById('setup-modal').style.display = 'flex';
    checkSetupConfig();
}

function saveStorageConfig() {
    const payload = {
        mode: selectedMode,
        local_path: document.getElementById('input-local-path').value,
        gdrive_url_or_id: document.getElementById('input-gdrive-url').value
    };
    fetch('/api/config', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(res => {
        document.getElementById('setup-modal').style.display = 'none';
        location.reload();
    });
}

window.openSetupModal = openSetupModal;
window.selectStorageMode = selectStorageMode;
window.saveStorageConfig = saveStorageConfig;


function generateMagicShareLink(category, identity) {
    fetch('/api/magic_links/create', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({category: category, identity: identity, days: 30})
    })
    .then(r => r.json())
    .then(data => {
        if (data.share_url) {
            navigator.clipboard.writeText(data.share_url);
            alert("🔗 ¡Enlace Mágico Copiado al Portapapeles!\n\nEnvíaselo a tu amigo para que vea sus fotos:\n" + data.share_url);
        }
    });
}
window.generateMagicShareLink = generateMagicShareLink;


function openQuickCleanMode() {
    loadCategoryFilter('_Dudosos', 'Desconocido');
    openQuickCleanOverlay();
}
window.openQuickCleanMode = openQuickCleanMode;


const vElem = document.getElementById('lb-video');
if (vElem) {
    vElem.oncanplay = function() {
        const btn = document.getElementById('btn-scan-video');
        if (btn) {
            btn.disabled = false;
            btn.style.opacity = "1";
            btn.innerHTML = `<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z"/></svg> Analizar Caras en Fotograma Actual`;
        }
    };
}



if('serviceWorker' in navigator){navigator.serviceWorker.register('/static/sw.js')}async function semanticSearch(term) {
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


    async function openEvolutionModal(identity) {
        if (!identity || !isStableDataset(currentCat, identity)) { showToast('Asigna un nombre a esta persona para analizar su evolución temporal.', 'info'); return; }
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
            banner.innerHTML = '<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M8 16c3.314 0 6-2 6-5.5 0-1.5-.5-4-2.5-6 .25 1.5-1.25 2-1.25 2C11 4 9 .5 6 0c.357 2 .5 4-2 6-1.25 1-2 2.729-2 4.5C2 14 4.686 16 8 16Zm0-1c-1.657 0-3-1-3-2.75 0-.75.25-2 1.25-3C6.125 10 7 10.5 7 10.5c-.375-1.25.5-3.25 2-3.5-.179 1-.25 2 1 3 .625.5 1 1.364 1 2.25C11 14 9.657 15 8 15Z"/></svg> Modo Limpieza Rápida - Desliza para limpiar <button onclick="this.parentElement.remove()" style="margin-left:20px; background:black; color:white; border:none; padding:4px 8px; border-radius:4px; cursor:pointer;">Cerrar</button>';
            document.body.appendChild(banner);
        }
    }

function triggerRelearnCascade(identity) {
    if (!identity || identity === 'Falso_Positivo' || identity === 'Ignorar_Irrelevante') return;
    fetch('/api/relearn_cascade', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({identity: identity})
    })
    .then(r => r.json())
    .then(data => {
        if (data.promoted > 0) {
            showToast('<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0zM4.5 5a.5.5 0 0 1 0-1h7a.5.5 0 0 1 0 1h-7zM3 8a.5.5 0 0 1 0-1h10a.5.5 0 0 1 0 1H3zm1.5 3a.5.5 0 0 1 0-1h7a.5.5 0 0 1 0 1h-7z"/></svg> Re-aprendizaje: ' + data.promoted + ' fotos promovidas de _Dudosos a ' + identity, 'success');
            loadIdentities();
        }
    })
    .catch(() => {});
}


function autoClassifyByFilename() {
    showToast('<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M2 2v4.586l7 7L13.586 9l-7-7H2zM1 2a1 1 0 0 1 1-1h4.586a1 1 0 0 1 .707.293l7 7a1 1 0 0 1 0 1.414l-4.586 4.586a1 1 0 0 1-1.414 0l-7-7A1 1 0 0 1 1 6.586V2z"/><path d="M4.5 5a.5.5 0 1 0 0-1 .5.5 0 0 0 0 1z"/></svg> Clasificando fotos por nombre de archivo...', 'info');
    fetch('/api/auto_classify_filename', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'})
    .then(r => r.json())
    .then(data => {
        if (data.moved > 0) {
            showToast('<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zm-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z"/></svg> ' + data.moved + ' archivos clasificados automáticamente', 'success');
            loadIdentities();
        } else {
            showToast('No se encontraron archivos para clasificar', 'info');
        }
    })
    .catch(e => showToast('Error: ' + e, 'error'));
}
window.autoClassifyByFilename = autoClassifyByFilename;


function addEvolutionToHeader() {
    const headerEl = document.querySelector('.gallery-header h2');
    if (!headerEl) return;
    const personName = headerEl.textContent.trim();
    let existingBtn = document.getElementById('btn-evolution-header');
    if (existingBtn) existingBtn.remove();
    if (!personName || personName === 'Todas las Fotos' || !isStableDataset(currentCat, personName)) return;
    
    const btn = document.createElement('button');
    btn.id = 'btn-evolution-header';
    btn.innerHTML = '📈 Ver Evolución Temporal';
    btn.style.cssText = 'margin-left:12px;padding:6px 14px;border-radius:10px;border:1px solid rgba(168,85,247,0.4);background:rgba(168,85,247,0.15);color:#c084fc;font-size:0.8rem;font-weight:600;cursor:pointer;transition:all 0.2s;';
    btn.onmouseenter = () => { btn.style.background = 'rgba(168,85,247,0.3)'; };
    btn.onmouseleave = () => { btn.style.background = 'rgba(168,85,247,0.15)'; };
    btn.onclick = () => openEvolutionModal(personName);
    headerEl.appendChild(btn);
}

// Call addEvolutionToHeader whenever an identity is selected
const origLoadFolder = window.loadFolderItems || function(){};
window.loadFolderItems = function() {
    origLoadFolder.apply(this, arguments);
    setTimeout(addEvolutionToHeader, 200);
};



        async function loadAlbumsHome() {
        document.getElementById('apple-breadcrumbs').style.display = 'none';
        document.getElementById('gallery-title').textContent = 'Álbumes';
        document.getElementById('gallery-subtitle').textContent = 'Categorías principales';
        document.getElementById('gallery-avatar').style.display = 'none';
        const btnTl = document.getElementById('btn-show-timeline'); if (btnTl) btnTl.style.display = 'none';
        const renameBtn = document.getElementById('btn-rename-group'); if (renameBtn) renameBtn.style.display = 'none';
        const ignoreBtn = document.getElementById('btn-ignore-group'); if (ignoreBtn) ignoreBtn.style.display = 'none';
        const deleteBtn = document.getElementById('btn-delete-group'); if (deleteBtn) deleteBtn.style.display = 'none';
        
        const grid = document.getElementById('grid-container');
        grid.innerHTML = '';
        
        const categories = {};
        identitiesList.forEach(id => {
            if(!categories[id.categoria]) categories[id.categoria] = [];
            categories[id.categoria].push(id);
        });
        
        for (const cat in categories) {
            const card = document.createElement('div');
            card.className = 'album-cover-card';
            card.style.cssText = 'background: rgba(255,255,255,0.05); border-radius: 16px; padding: 20px; cursor: pointer; text-align: center; border: 1px solid rgba(255,255,255,0.1); backdrop-filter: blur(10px); transition: transform 0.2s;';
            card.innerHTML = `<h2 style="margin:0; font-size: 24px; color: white;">${cat}</h2><p style="color: #888; font-size: 14px;">${categories[cat].length} personas</p>`;
            card.onmouseover = () => card.style.transform = 'scale(1.05)';
            card.onmouseout = () => card.style.transform = 'scale(1)';
            card.onclick = () => loadCategory(cat, categories[cat]);
            grid.appendChild(card);
        }
    }
    
    function loadCategory(cat, people) {
        document.getElementById('apple-breadcrumbs').style.display = 'flex';
        document.getElementById('bc-separator-1').style.display = 'inline';
        document.getElementById('bc-category').style.display = 'inline';
        document.getElementById('bc-category').textContent = cat;
        document.getElementById('bc-separator-2').style.display = 'none';
        document.getElementById('bc-person').style.display = 'none';
        
        document.getElementById('gallery-title').textContent = cat;
        const staticSub = document.querySelector('p#gallery-subtitle'); if (staticSub) { staticSub.style.display = 'block'; staticSub.textContent = `${people.length} personas`; }
        const btnTl = document.getElementById('btn-show-timeline'); if (btnTl) btnTl.style.display = isStableDataset(cat, null) ? 'block' : 'none';
        
        const grid = document.getElementById('grid-container');
        grid.innerHTML = '';
        
        people.forEach(person => {
            const card = document.createElement('div');
            card.className = 'album-cover-card';
            card.style.cssText = 'background: rgba(255,255,255,0.05); border-radius: 16px; padding: 20px; cursor: pointer; text-align: center; border: 1px solid rgba(255,255,255,0.1); backdrop-filter: blur(10px); transition: transform 0.2s;';
            card.innerHTML = `<h3 style="margin:0; font-size: 18px; color: white;">${person.identidad}</h3>`;
            card.onmouseover = () => card.style.transform = 'scale(1.05)';
            card.onmouseout = () => card.style.transform = 'scale(1)';
            card.onclick = () => {
                document.getElementById('bc-separator-2').style.display = 'inline';
                document.getElementById('bc-person').style.display = 'inline';
                document.getElementById('bc-person').innerHTML = person.identidad;
                renderGrid(cat, person.identidad);
            };
            grid.appendChild(card);
        });
    }

    // Override the default load behavior (using window scope)
    const originalLoadGallery = window.loadGallery;
    window.loadGallery = async function() {
        if (!identitiesList || !identitiesList.length) {
            await window.loadIdentities();
        }
        await originalLoadGallery();
        loadAlbumsHome();
    };


function openCompareModal(path1, path2) {
    document.getElementById('compare-img-1').src = '/media?path=' + path1;
    document.getElementById('compare-img-2').src = '/media?path=' + path2;
    document.getElementById('compare-path-1').innerHTML = decodeURIComponent(path1);
    document.getElementById('compare-path-2').innerHTML = decodeURIComponent(path2);
    document.getElementById('compareModal').style.display = 'flex';
}
function closeCompareModal() {
    document.getElementById('compareModal').style.display = 'none';
}

// ==========================================
// MAPA INTERACTIVO Y EVENTOS ORGANIZADOS
// ==========================================
let eventsLeafletMap = null;

window.openEventsMapModal = async function() {
    const modal = document.getElementById('modal-events-map');
    if (!modal) return;
    modal.style.display = 'flex';
    
    const mapDiv = document.getElementById('events-map-container');
    if (mapDiv && typeof L !== 'undefined') {
        setTimeout(async () => {
            if (!eventsLeafletMap) {
                eventsLeafletMap = L.map('events-map-container').setView([40.4167, -3.7037], 5);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    maxZoom: 19,
                    attribution: '© OpenStreetMap'
                }).addTo(eventsLeafletMap);
            }
            eventsLeafletMap.invalidateSize();
            
            try {
                const res = await fetch('/api/map/locations');
                const data = await res.json();
                const locs = data.locations || [];
                
                eventsLeafletMap.eachLayer((layer) => {
                    if (layer instanceof L.Marker) eventsLeafletMap.removeLayer(layer);
                });
                
                if (locs.length > 0) {
                    const bounds = [];
                    locs.forEach(loc => {
                        const marker = L.marker([loc.lat, loc.lng]).addTo(eventsLeafletMap);
                        marker.bindPopup(`<b>${loc.name}</b><br><img src="/api/thumbnail?path=${encodeURIComponent(loc.path)}" style="width:120px; border-radius:6px; margin-top:5px;">`);
                        bounds.push([loc.lat, loc.lng]);
                    });
                    eventsLeafletMap.fitBounds(bounds);
                }
            } catch(e) { console.error("Map fetch error:", e); }
        }, 300);
    }
    
    const content = document.getElementById('events-list-content');
    content.innerHTML = '<div style="text-align:center; padding:40px;"><div class="loader-small" style="margin:auto;"></div> Cargando eventos...</div>';
    
    try {
        const res = await fetch('/api/events');
        const data = await res.json();
        const events = data.events || [];
        
        if (events.length === 0) {
            content.innerHTML = '<div style="text-align:center; padding:30px; color:#888;">No se detectaron eventos suficientes por fecha/ubicación.</div>';
            return;
        }
        
        let html = '';
        events.forEach((ev, idx) => {
            const pathsJson = JSON.stringify(ev.items.map(it => it.path)).replace(/"/g, '&quot;');
            html += `
            <div style="background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); border-radius:14px; padding:15px; display:flex; gap:15px; align-items:center;">
                <img src="/api/thumbnail?path=${encodeURIComponent(ev.cover)}" style="width:90px; height:90px; object-fit:cover; border-radius:10px; flex-shrink:0;">
                <div style="flex:1;">
                    <h4 style="margin:0 0 5px 0; color:white; font-size:1.05rem;">${ev.title}</h4>
                    <div style="font-size:0.85rem; color:#aaa;">📅 ${ev.date_label} &nbsp;|&nbsp; 📸 <strong>${ev.count} fotos</strong></div>
                    <button onclick="createEventAlbum('${ev.title.replace(/'/g, "\\'")}', '${pathsJson}')" style="margin-top:10px; background:#0a84ff; color:white; border:none; padding:6px 14px; border-radius:8px; font-weight:600; cursor:pointer; font-size:0.85rem;">
                        📁 Crear Álbum de este Evento
                    </button>
                </div>
            </div>`;
        });
        content.innerHTML = html;
    } catch(e) {
        content.innerHTML = `<div style="color:red; text-align:center;">Error cargando eventos: ${e}</div>`;
    }
};

window.closeEventsMapModal = function() {
    const modal = document.getElementById('modal-events-map');
    if (modal) modal.style.display = 'none';
};

window.createEventAlbum = async function(title, pathsJson) {
    let paths = [];
    try {
        paths = JSON.parse(pathsJson.replace(/&quot;/g, '"'));
    } catch(e) { return; }
    
    const albumName = prompt(`Escribe el nombre para el nuevo álbum de este evento:`, title);
    if (!albumName) return;
    
    try {
        const res = await fetch('/api/create_event_folder', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ event_name: albumName, paths: paths })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message || `Álbum '${albumName}' creado con éxito.`);
            await loadGallery();
        } else {
            showToast(data.error || "Error al crear el álbum del evento", true);
        }
    } catch(e) {
        showToast("Error de conexión al crear álbum", true);
    }
};


// Explicitly expose functions to window scope for HTML onclick bindings
window.closeLightbox = typeof closeLightbox !== 'undefined' ? closeLightbox : window.closeLightbox;
window.openLightbox = typeof openLightbox !== 'undefined' ? openLightbox : window.openLightbox;
window.deleteCurrentFile = typeof deleteCurrentFile !== 'undefined' ? deleteCurrentFile : window.deleteCurrentFile;
window.enableManualSelection = typeof enableManualSelection !== 'undefined' ? enableManualSelection : window.enableManualSelection;
window.toggleSwipeMode = typeof toggleSwipeMode !== 'undefined' ? toggleSwipeMode : window.toggleSwipeMode;
window.autoClassifyByFilename = typeof autoClassifyByFilename !== 'undefined' ? autoClassifyByFilename : window.autoClassifyByFilename;
window.removeFromFolder = typeof removeFromFolder !== 'undefined' ? removeFromFolder : window.removeFromFolder;
window.triggerDeepScanLightbox = typeof triggerDeepScanLightbox !== 'undefined' ? triggerDeepScanLightbox : window.triggerDeepScanLightbox;
window.resetZoom = typeof resetZoom !== 'undefined' ? resetZoom : window.resetZoom;
window.toggleMetadata = typeof toggleMetadata !== 'undefined' ? toggleMetadata : window.toggleMetadata;
window.runAnalysis = typeof runAnalysis !== 'undefined' ? runAnalysis : window.runAnalysis;
window.toggleBoxes = typeof toggleBoxes !== 'undefined' ? toggleBoxes : window.toggleBoxes;
window.ignoreUnconfirmedFaces = typeof ignoreUnconfirmedFaces !== 'undefined' ? ignoreUnconfirmedFaces : window.ignoreUnconfirmedFaces;
window.scanFullVideo = typeof scanFullVideo !== 'undefined' ? scanFullVideo : window.scanFullVideo;

window.renameCurrentGroup = typeof renameCurrentGroup !== 'undefined' ? renameCurrentGroup : window.renameCurrentGroup;
window.ignoreCurrentGroup = typeof ignoreCurrentGroup !== 'undefined' ? ignoreCurrentGroup : window.ignoreCurrentGroup;
window.deleteCurrentGroup = typeof deleteCurrentGroup !== 'undefined' ? deleteCurrentGroup : window.deleteCurrentGroup;
window.submitMergeGroup = typeof submitMergeGroup !== 'undefined' ? submitMergeGroup : window.submitMergeGroup;
window.closeMergeModal = typeof closeMergeModal !== 'undefined' ? closeMergeModal : window.closeMergeModal;

window.applyBulkIgnore = typeof applyBulkIgnore !== 'undefined' ? applyBulkIgnore : window.applyBulkIgnore;
window.applyBulkReassign = typeof applyBulkReassign !== 'undefined' ? applyBulkReassign : window.applyBulkReassign;
window.applyBulkRemoveFromFolder = typeof applyBulkRemoveFromFolder !== 'undefined' ? applyBulkRemoveFromFolder : window.applyBulkRemoveFromFolder;
window.clearBatchSelection = typeof clearBatchSelection !== 'undefined' ? clearBatchSelection : window.clearBatchSelection;
window.clearSelection = typeof clearSelection !== 'undefined' ? clearSelection : window.clearSelection;
window.closeCompareModal = typeof closeCompareModal !== 'undefined' ? closeCompareModal : window.closeCompareModal;
window.closeEventsMapModal = typeof closeEventsMapModal !== 'undefined' ? closeEventsMapModal : window.closeEventsMapModal;
window.closeExactDuplicatesModal = typeof closeExactDuplicatesModal !== 'undefined' ? closeExactDuplicatesModal : window.closeExactDuplicatesModal;
window.closeSimilarPhotosModal = typeof closeSimilarPhotosModal !== 'undefined' ? closeSimilarPhotosModal : window.closeSimilarPhotosModal;

window.executeBatchMove = typeof executeBatchMove !== 'undefined' ? executeBatchMove : window.executeBatchMove;
window.forceReanalyze = typeof forceReanalyze !== 'undefined' ? forceReanalyze : window.forceReanalyze;
window.loadAlbumsHome = typeof loadAlbumsHome !== 'undefined' ? loadAlbumsHome : window.loadAlbumsHome;
window.rebuildCleanCentroidsConfirm = typeof rebuildCleanCentroidsConfirm !== 'undefined' ? rebuildCleanCentroidsConfirm : window.rebuildCleanCentroidsConfirm;
window.resetFaceLearningConfirm = typeof resetFaceLearningConfirm !== 'undefined' ? resetFaceLearningConfirm : window.resetFaceLearningConfirm;
window.saveStorageConfig = typeof saveStorageConfig !== 'undefined' ? saveStorageConfig : window.saveStorageConfig;
window.selectStorageMode = typeof selectStorageMode !== 'undefined' ? selectStorageMode : window.selectStorageMode;
window.setPhotoFilter = typeof setPhotoFilter !== 'undefined' ? setPhotoFilter : window.setPhotoFilter;
window.toggleMultiSelectMode = typeof toggleMultiSelectMode !== 'undefined' ? toggleMultiSelectMode : window.toggleMultiSelectMode;

window.renderTree = typeof renderTree !== 'undefined' ? renderTree : window.renderTree;
window.loadGallery = typeof loadGallery !== 'undefined' ? loadGallery : window.loadGallery;
window.loadIdentities = typeof loadIdentities !== 'undefined' ? loadIdentities : window.loadIdentities;
window.openExactDuplicatesModal = typeof openExactDuplicatesModal !== 'undefined' ? openExactDuplicatesModal : window.openExactDuplicatesModal;
window.openSimilarPhotosModal = typeof openSimilarPhotosModal !== 'undefined' ? openSimilarPhotosModal : window.openSimilarPhotosModal;
window.openIntelligentCleanup = typeof openIntelligentCleanup !== 'undefined' ? openIntelligentCleanup : window.openIntelligentCleanup;
window.runMassCleanup = typeof runMassCleanup !== 'undefined' ? runMassCleanup : window.runMassCleanup;
window.openStatsModal = typeof openStatsModal !== 'undefined' ? openStatsModal : window.openStatsModal;
window.filterTimeline = typeof filterTimeline !== 'undefined' ? filterTimeline : window.filterTimeline;
window.quickReassignFace = typeof quickReassignFace !== 'undefined' ? quickReassignFace : window.quickReassignFace;






// --- SSE PROGRESS BAR LOGIC ---
function initializeSSE() {
    const eventSource = new EventSource('/api/stream/events');
    
    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'smart_clean_progress') {
                const textEl = document.getElementById('smartCleanStatusText');
                const progEl = document.getElementById('smartCleanProgress');
                if (textEl) textEl.textContent = data.status || 'Procesando...';
                if (progEl) progEl.value = data.progress || 0;
            }
        } catch (e) {
            console.error('Error parsing SSE:', e);
        }
    };
    
    eventSource.onerror = function() {
        console.warn('SSE connection lost, reconnecting...');
    };
}
document.addEventListener('DOMContentLoaded', () => {
    if (typeof loadIdentities === 'function') loadIdentities();
    else if (window.loadIdentities) window.loadIdentities();
    
    if (typeof loadGallery === 'function') loadGallery();
    else if (window.loadGallery) window.loadGallery();

    const viewStatsBtn = document.getElementById('view-stats-btn');
    if (viewStatsBtn) {
        viewStatsBtn.addEventListener('click', () => {
            if (typeof openStatsModal === 'function') openStatsModal();
            else if (window.openStatsModal) window.openStatsModal();
        });
    }

    const settingsBtn = document.getElementById('settings-btn');

    const settingsModal = document.getElementById('settings-modal');
    const settingsClose = document.getElementById('settings-close');
    const storageMode = document.getElementById('storage-mode') as HTMLSelectElement;
    const gdriveSettings = document.getElementById('gdrive-settings');
    const gdriveLink = document.getElementById('gdrive-link') as HTMLInputElement;
    const saveSettingsBtn = document.getElementById('save-settings-btn');

    if (settingsBtn && settingsModal && settingsClose && storageMode) {
        settingsBtn.addEventListener('click', () => {
            // Fetch current config
            fetch('/api/config')
                .then(res => res.json())
                .then(cfg => {
                    storageMode.value = cfg.mode || 'local';
                    gdriveLink.value = cfg.gdrive_folder_id || '';
                    if (storageMode.value === 'gdrive') {
                        gdriveSettings.style.display = 'block';
                    } else {
                        gdriveSettings.style.display = 'none';
                    }
                    settingsModal.style.display = 'flex';
                });
        });

        settingsClose.addEventListener('click', () => {
            settingsModal.style.display = 'none';
        });

        storageMode.addEventListener('change', () => {
            if (storageMode.value === 'gdrive') {
                gdriveSettings.style.display = 'block';
            } else {
                gdriveSettings.style.display = 'none';
            }
        });

        saveSettingsBtn.addEventListener('click', () => {
            const mode = storageMode.value;
            const link = gdriveLink.value;
            fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode: mode, gdrive_url_or_id: link })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    settingsModal.style.display = 'none';
                    alert('Configuración guardada. Recargando la galería con el nuevo entorno...');
                    window.location.reload();
                } else {
                    alert('Error guardando configuración');
                }
            });
        });
    }
});
// ----------------------------
