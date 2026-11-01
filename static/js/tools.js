// ============================================================
// TOOLS.JS - Background Tasks, Exports, Duplicates & Smart Tools
// ============================================================

window._taskPollingIntervals = {};
window._progressToasts = {};

function runBackgroundTask(url, payload, name, onComplete, onError) {
    fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: payload ? JSON.stringify(payload) : undefined
    }).then(r => r.json()).then(data => {
        const taskId = data.task_id;
        if (taskId) {
            showProgressToast(name, taskId);
            pollTask(taskId, name, onComplete, onError);
        } else if (data.status === 'started' || data.success) {
            if (typeof showToast === 'function') showToast(`🚀 ${name} iniciado en segundo plano`);
            if (onComplete) onComplete(data);
        }
    }).catch(err => {
        if (onError) onError(err);
        showErrorToast(name, err.message, null);
    });
}

function pollTask(taskId, name, onComplete, onError) {
    if (_taskPollingIntervals[taskId]) clearInterval(_taskPollingIntervals[taskId]);
    
    _taskPollingIntervals[taskId] = setInterval(async () => {
        try {
            const res = await fetch(`/api/task_status/${taskId}`);
            const data = await res.json();
            
            if (data.status === 'running') {
                updateProgressToast(taskId, data.progress || 0, data.message || 'Procesando...');
            } else if (data.status === 'completed') {
                clearInterval(_taskPollingIntervals[taskId]);
                delete _taskPollingIntervals[taskId];
                dismissProgressToast(taskId);
                if (typeof showToast === 'function') showToast(`✅ ${name} completado con éxito`);
                if (onComplete) onComplete(data.result);
                if (typeof loadGallery === 'function') loadGallery();
            } else if (data.status === 'failed') {
                clearInterval(_taskPollingIntervals[taskId]);
                delete _taskPollingIntervals[taskId];
                dismissProgressToast(taskId);
                showErrorToast(name, data.error || 'Error desconocido', taskId);
                if (onError) onError(data.error);
            }
        } catch(e) {}
    }, 1500);
}

function showProgressToast(name, taskId) {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px;align-items:flex-end;';
        document.body.appendChild(container);
    }
    
    const div = document.createElement('div');
    div.id = `ptoa-${taskId}`;
    div.style.cssText = 'background:rgba(20,20,24,0.95); border:1px solid rgba(10,132,255,0.4); border-radius:10px; padding:12px 16px; color:#fff; font-size:12px; min-width:260px; backdrop-filter:blur(10px); box-shadow:0 4px 20px rgba(0,0,0,0.5);';
    div.innerHTML = `
        <div style="font-weight:700; color:#64d2ff; margin-bottom:4px;">⏳ ${name}</div>
        <div id="ptxt-${taskId}" style="color:#aaa; font-size:11px; margin-bottom:6px;">Iniciando...</div>
        <div style="width:100%; height:4px; background:rgba(255,255,255,0.1); border-radius:2px; overflow:hidden;">
            <div id="pbar-${taskId}" style="width:0%; height:100%; background:#0a84ff; transition:width 0.3s;"></div>
        </div>
    `;
    container.appendChild(div);
    _progressToasts[taskId] = div;
}

function updateProgressToast(taskId, pct, text) {
    const bar = document.getElementById(`pbar-${taskId}`);
    const txt = document.getElementById(`ptxt-${taskId}`);
    if (bar) bar.style.width = `${Math.round(pct)}%`;
    if (txt) txt.textContent = `${Math.round(pct)}% - ${text}`;
}

function dismissProgressToast(taskId) {
    const el = document.getElementById(`ptoa-${taskId}`);
    if (el) { el.style.opacity = '0'; setTimeout(() => el.remove(), 300); }
    delete _progressToasts[taskId];
}

function showErrorToast(name, errorMsg, taskId) {
    const id = `etoa-${Date.now()}`;
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px;align-items:flex-end;';
        document.body.appendChild(container);
    }

    const div = document.createElement('div');
    div.id = id;
    div.style.cssText = 'background:rgba(30,12,12,0.97);border:1px solid rgba(255,69,58,0.5);border-radius:10px;padding:14px 16px;color:#fff;font-size:13px;min-width:280px;max-width:380px;backdrop-filter:blur(10px);box-shadow:0 4px 20px rgba(0,0,0,0.6);';
    div.innerHTML = `
        <div style="display:flex;align-items:flex-start;gap:8px;">
            <span style="font-size:18px;">❌</span>
            <div style="flex:1;">
                <div style="font-weight:600;color:#ff453a;margin-bottom:4px;">${name} falló</div>
                <div style="color:#ccc;font-size:11px;line-height:1.4;">${(errorMsg || '').substring(0, 200)}</div>
            </div>
            <button onclick="document.getElementById('${id}').remove()" style="background:none;border:none;color:#888;cursor:pointer;font-size:16px;">&times;</button>
        </div>
    `;
    container.appendChild(div);
    setTimeout(() => { if (document.getElementById(id)) div.remove(); }, 10000);
}

function openExactDuplicatesModal() {
    const modal = document.getElementById('modal-duplicates');
    if (!modal) return;
    modal.style.display = 'flex';
    const loading = document.getElementById('duplicates-loading');
    const content = document.getElementById('duplicates-content');
    if (loading) loading.style.display = 'block';
    if (content) {
        content.style.display = 'none';
        content.innerHTML = '';
    }
    fetch('/api/duplicates_scan').then(r => r.json()).then(data => {
        if (loading) loading.style.display = 'none';
        if (content) {
            content.style.display = 'block';
            if (!data.duplicates || data.duplicates.length === 0) {
                content.innerHTML = '<div style="text-align:center; padding:40px; color:#30d158; font-weight:600;">✨ ¡Genial! No se encontraron duplicados exactos.</div>';
                return;
            }
            let html = `<div style="padding:10px 0; color:#fff; font-size:14px; font-weight:600;">Se han encontrado <b>${data.duplicates.length}</b> grupos de duplicados idénticos:</div>`;
            html += '<div style="max-height:420px; overflow-y:auto; display:flex; flex-direction:column; gap:12px;" class="custom-scrollbar">';
            data.duplicates.forEach((group, idx) => {
                html += `<div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); padding:12px; border-radius:10px;">
                    <div style="font-size:12px; color:#64d2ff; font-weight:700; margin-bottom:8px;">Grupo #${idx+1} (${group.length} copias idénticas)</div>
                    <div style="display:flex; gap:10px; overflow-x:auto;">
                        ${group.map(p => `<img src="/api/thumbnail?path=${encodeURIComponent(p)}" style="width:90px; height:90px; object-fit:cover; border-radius:8px; border:1px solid rgba(255,255,255,0.1);" title="${p}">`).join('')}
                    </div>
                </div>`;
            });
            html += '</div>';
            content.innerHTML = html;
        }
    }).catch(e => {
        if (loading) loading.style.display = 'none';
        if (content) {
            content.style.display = 'block';
            content.innerHTML = '<div style="text-align:center; padding:30px; color:#ff453a;">Error al escanear duplicados.</div>';
        }
    });
}

function openSimilarPhotosModal() {
    const modal = document.getElementById('modal-similar');
    if (!modal) return;
    modal.style.display = 'flex';
    const loading = document.getElementById('similar-loading');
    const content = document.getElementById('similar-content');
    if (loading) loading.style.display = 'block';
    if (content) {
        content.style.display = 'none';
        content.innerHTML = '';
    }
    fetch('/api/similar_scan').then(r => r.json()).then(data => {
        if (loading) loading.style.display = 'none';
        if (content) {
            content.style.display = 'block';
            const groups = data.groups || [];
            if (groups.length === 0) {
                content.innerHTML = '<div style="text-align:center; padding:40px; color:#30d158; font-weight:600;">✨ ¡Genial! No se encontraron ráfagas o tomas repetidas.</div>';
                return;
            }
            let html = `<div style="padding:10px 0; color:#fff; font-size:14px; font-weight:600;">Se han encontrado <b>${groups.length}</b> secuencias de fotos similares:</div>`;
            html += '<div style="max-height:460px; overflow-y:auto; display:flex; flex-direction:column; gap:12px;" class="custom-scrollbar">';
            groups.forEach((g, idx) => {
                html += `<div style="background:rgba(255,255,255,0.04); border:1px solid rgba(191,90,242,0.25); padding:14px; border-radius:12px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <span style="font-size:12px; color:#ffd60a; font-weight:700;">📸 Ráfaga #${idx+1} (${g.files.length} tomas en ${g.folder})</span>
                    </div>
                    <div style="display:flex; gap:12px; overflow-x:auto; padding-bottom:6px;">
                        ${g.files.map((f, fIdx) => `
                            <div style="position:relative; flex-shrink:0; width:100px; text-align:center;">
                                <img src="/api/thumbnail?path=${encodeURIComponent(f.path)}" 
                                     style="width:100px; height:100px; object-fit:cover; border-radius:8px; border: ${f.is_sharpest ? '2px solid #30d158' : '1px solid rgba(255,255,255,0.1)'};" 
                                     title="${f.name}">
                                ${f.is_sharpest ? '<span style="position:absolute; top:4px; left:4px; background:#30d158; color:#000; font-size:9px; font-weight:800; padding:2px 4px; border-radius:4px;">MÁS NÍTIDA</span>' : ''}
                                <div style="font-size:10px; color:#8e8e93; margin-top:4px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${f.name}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>`;
            });
            html += '</div>';
            content.innerHTML = html;
        }
    }).catch(e => {
        if (loading) loading.style.display = 'none';
        if (content) {
            content.style.display = 'block';
            content.innerHTML = '<div style="text-align:center; padding:30px; color:#ff453a;">Error al escanear ráfagas similares.</div>';
        }
    });
}

function runMassCleanup() {
    if (!confirm('¿Deseas iniciar la Limpieza Global Inteligente? Se revisarán duplicados, fotos borrosas y capturas de texto.')) return;
    runBackgroundTask('/api/mass_cleanup', null, 'Limpieza Global Inteligente', (res) => {
        if (typeof showToast === 'function') showToast('✅ Limpieza Global finalizada con éxito');
    });
}

window.openExactDuplicatesModal = openExactDuplicatesModal;
window.openSimilarPhotosModal = openSimilarPhotosModal;
window.runMassCleanup = runMassCleanup;
window.runBackgroundTask = runBackgroundTask;
window.showErrorToast = showErrorToast;
window.showProgressToast = showProgressToast;
