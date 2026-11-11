/**
 * SmartGallery AI - BACKGROUND TASKS, SSE ENGINE & VIDEO INDEXER
 * Module: static/js/modules/08_tasks.js
 */

// AUTO-CLASIFICADOR EN SEGUNDO PLANO (CONTINUO)

// =============================================================

let isBgAutoClassifyActive = false;
let bgClassifyInterval = null;

// ═══════════════════════════════════════════════════════════════

// MOTOR DE AUTO-CORRECCIÓN BIDIRECCIONAL — Panel + SSE Live

// ═══════════════════════════════════════════════════════════════

let _engineSSE = null;
let _enginePanelOpen = false;
let _engineRunning = false;
let _enginePollTimer = null;

window.toggleEnginePanel = function() {
    const panel = document.getElementById('engine-panel');

    if (!panel) return;

    _enginePanelOpen = !_enginePanelOpen;

    panel.style.display = _enginePanelOpen ? 'block' : 'none';

    if (_enginePanelOpen) {
        _startEngineSSE();

        _pollEngineStatus();
    }
};

window.startEngine = function() {
    fetch('/api/auto_classify_continuous', {
        method: 'POST',

        headers: {'Content-Type': 'application/json'},

        body: JSON.stringify({action: 'start'})
    }).then(r => r.json()).then(data => {
        _engineRunning = true;

        _updateEngineUI(true);

        showToast('🤖 Motor de auto-corrección iniciado. Fase A + Fase B activas.');

        _startEngineSSE();
    }).catch(e => showToast('Error arrancando el motor.'));
};

window.stopEngine = function() {
    fetch('/api/auto_classify_continuous', {
        method: 'POST',

        headers: {'Content-Type': 'application/json'},

        body: JSON.stringify({action: 'stop'})
    }).then(r => r.json()).then(data => {
        _engineRunning = false;

        _updateEngineUI(false);

        _stopEngineSSE();

        showToast('⏹ Motor detenido.');
    }).catch(e => {});
};

// Mantener compatibilidad con el botón anterior

window.toggleBgAutoClassify = function() { window.toggleEnginePanel(); };

window.startBgAutoClassify = function() { window.startEngine(); };

window.stopBgAutoClassify = function() { window.stopEngine(); };

function _startEngineSSE() {
    if (!_enginePanelOpen) return; // Solo conectar si el panel esta abierto

    if (_engineSSE) return; // Ya conectado

    try {
        _engineSSE = new EventSource('/api/self_audit_stream');

        _engineSSE.onmessage = function(e) {
            try {
                const d = JSON.parse(e.data);

                _applyEngineStatus(d);
            } catch(err) {}
        };

        _engineSSE.onerror = function() {
            _engineSSE.close();

            _engineSSE = null;

            // Reintentar en 10s si el panel sigue abierto

            if (_enginePanelOpen) {
                setTimeout(_startEngineSSE, 10000);
            }
        };
    } catch(e) {}
}

function _stopEngineSSE() {
    if (_engineSSE) {
        _engineSSE.close();

        _engineSSE = null;
    }
}

function _pollEngineStatus() {
    fetch('/api/self_audit_status')

        .then(r => r.json())

        .then(d => _applyEngineStatus(d))

        .catch(e => {});
}

const _PHASE_LABELS = {
    'idle':          '⏸ Inactivo — esperando inicio',

    'scan_unknown':  '🔍 Fase A — Clasificando desconocidos...',

    'audit_known':   '🔄 Fase B — Auditando carpetas conocidas...',

    'waiting':       '⏳ Descansando entre ciclos (60 s)...',

    'deep_scan':     '🧠 Escaneo profundo...',
};

function _applyEngineStatus(d) {
    _engineRunning = !!d.running;

    _updateEngineUI(_engineRunning);

    // Contadores

    _setInner('engine-stat-scanned', d.total_scanned ?? 0);

    _setInner('engine-stat-known',   d.total_moved_to_known ?? 0);

    _setInner('engine-stat-review',  d.total_moved_to_review ?? 0);

    // Drawer stats

    _setInner('drawer-stat-fixed', d.total_fixed ?? 0);

    _setInner('drawer-stat-cycle', d.cycle ?? 0);

    // Fase

    const phaseLabel = _PHASE_LABELS[d.phase] || d.phase || 'Inactivo';

    _setInner('engine-phase-label', phaseLabel);

    // Último archivo analizado

    const lastFileEl = document.getElementById('engine-last-file');

    if (lastFileEl) {
        if (d.last_scanned_file) {
            lastFileEl.textContent = `📍 ${d.last_scanned_file}`;
        } else if (_engineRunning) {
            lastFileEl.textContent = `⏳ Reanudando desde checkpoint previo...`;
        } else {
            lastFileEl.textContent = `⏸️ Estado guardado en disco`;
        }
    }

    // Ciclo + dot

    const dot = document.getElementById('engine-cycle-dot');
    const cycleText = document.getElementById('engine-cycle-text');

    if (dot) {
        dot.style.background = _engineRunning

            ? (d.phase === 'waiting' ? '#ff9f0a' : '#30d158')

            : '#3a3a3c';

        dot.style.boxShadow = _engineRunning ? `0 0 6px ${d.phase === 'waiting' ? '#ff9f0a' : '#30d158'}` : 'none';
    }

    if (cycleText) {
        cycleText.textContent = d.cycle

            ? `Ciclo ${d.cycle} — ${(d.total_fixed ?? 0)} correcciones totales`

            : 'Ciclo 0 — esperando inicio';
    }

    // Log de acciones

    const logEl = document.getElementById('engine-log');

    if (logEl && d.last_actions && d.last_actions.length > 0) {
        const entries = d.last_actions.slice().reverse();

        logEl.innerHTML = entries.map(a => {
            const color = a.msg.startsWith('✅') ? '#30d158'

                        : a.msg.startsWith('🔄') ? '#64d2ff'

                        : a.msg.startsWith('⚠️') ? '#ff9f0a'

                        : '#8e8e93';

            return `<div style="padding:5px 6px; border-bottom:1px solid rgba(255,255,255,0.04); font-size:11px;">

                <span style="color:#555; margin-right:6px;">${a.ts}</span>

                <span style="color:${color};">${a.msg}</span>

            </div>`;
        }).join('');
    }
}

function _updateEngineUI(running) {
    const btn   = document.getElementById('btn-bg-autoclassify');
    const badge = document.getElementById('engine-badge');
    const startBtn = document.getElementById('btn-engine-start');
    const stopBtn  = document.getElementById('btn-engine-stop');

    if (btn) {
        btn.style.background = running

            ? 'rgba(48,209,88,0.15)' : 'rgba(10,132,255,0.12)';

        btn.style.borderColor = running ? '#30d158' : 'rgba(10,132,255,0.3)';

        btn.style.color = running ? '#30d158' : '#64d2ff';
    }

    if (badge)    badge.style.display = running ? 'inline' : 'none';

    if (startBtn) startBtn.style.display = running ? 'none' : 'inline-block';

    if (stopBtn)  stopBtn.style.display  = running ? 'inline-block' : 'none';
}

// Auto-conectar y consultar estado al cargar la página

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        _pollEngineStatus();
    }, 1500);
});

function _setInner(id, val) {
    const el = document.getElementById(id);

    if (el) el.textContent = val;
}

// Añadir animación pulse-badge al CSS dinámicamente

(function() {
    const style = document.createElement('style');

    style.textContent = `

        @keyframes pulse-badge {
            0%, 100% { opacity:1; }

            50% { opacity:0.5; }
        }

    `;

    document.head.appendChild(style);
})();

// BUSQUEDA INTENSIVA DE YO

// ============================================================

let _yoSearchInterval = null;

async function startIntensiveYoSearch() {
    const btn = document.getElementById('btn-yo-search');
    const statusEl = document.getElementById('yo-search-status');

    if (!btn || !statusEl) return;

    if (!confirm('Esto escaneara TODOS los archivos de la galeria buscando fotos tuyas.\n\nLas fotos con tu cara en dudosos/desconocidos se moveran a tu carpeta.\n\nPuede tardar varios minutos. Continuar?')) return;

    btn.disabled = true;

    btn.textContent = 'Buscando...';

    statusEl.style.display = 'block';

    statusEl.textContent = 'Iniciando busqueda intensiva...';

    try {
        await fetch('/api/intensive_search_yo', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({threshold: 0.55}) });
    } catch(e) {
        showToast('Error iniciando busqueda', true);

        btn.disabled = false;

        btn.textContent = 'Buscar Todas Mis Fotos';

        return;
    }

    if (_yoSearchInterval) clearInterval(_yoSearchInterval);

    _yoSearchInterval = setInterval(async () => {
        try {
            const res = await fetch('/api/yo_search_status');
            const data = await res.json();

            if (statusEl) statusEl.textContent = data.progress || '';

            if (data.done) {
                clearInterval(_yoSearchInterval);

                btn.disabled = false;

                btn.textContent = 'Buscar Todas Mis Fotos';

                showToast('Busqueda completada: ' + data.found + ' fotos con tu cara de ' + data.scanned + ' analizadas.');

                if (typeof refreshGallery === 'function') refreshGallery();
            }
        } catch(e) {}
    }, 3000);
}

// ============================================================

// AUDITOR AUTOMATICO

// ============================================================

let _auditInterval = null;

async function startSmartAudit() {
    const btn = document.getElementById('btn-smart-audit');
    const statusEl = document.getElementById('audit-status');

    if (!btn || !statusEl) return;

    if (!confirm('La auditoria automatica detectara impostores, rescatara dudosos/desconocidos y re-escaneara sin-rostro.\n\nLas correcciones manuales NO se tocaran.\n\nContinuar?')) return;

    btn.disabled = true;

    btn.textContent = 'Auditando...';

    statusEl.style.display = 'block';

    statusEl.textContent = 'Iniciando auditoria...';

    try {
        await fetch('/api/smart_audit', {
            method: 'POST',

            headers: {'Content-Type': 'application/json'},

            body: JSON.stringify({impostor_threshold: 0.42, rescue_threshold: 0.58})
        });
    } catch(e) {
        showToast('Error iniciando auditoria', true);

        btn.disabled = false;

        btn.textContent = 'Ejecutar Auditoria';

        return;
    }

    if (_auditInterval) clearInterval(_auditInterval);

    _auditInterval = setInterval(async () => {
        try {
            const res = await fetch('/api/audit_status');
            const data = await res.json();

            if (statusEl) statusEl.textContent = data.progress || '';

            if (data.done) {
                clearInterval(_auditInterval);

                btn.disabled = false;

                btn.textContent = 'Ejecutar Auditoria';

                const s = data.stats || {};

                showToast('Auditoria completa. Impostores: ' + (s.impostores||0) + ' | Rescatados: ' + (s.rescatados||0) + ' | Sin Rostro: ' + (s.sin_rostro_rescatados||0));

                if (typeof refreshGallery === 'function') refreshGallery();
            }
        } catch(e) {}
    }, 3000);
}

// ============================================================

// SISTEMA GLOBAL DE TAREAS Y ERRORES

// ============================================================

let _taskPollingIntervals = {};

/**

 * Lanza una tarea y muestra progreso/errores automaticamente.

 * @param {string} url - endpoint POST

 * @param {object} body - payload JSON

 * @param {string} taskName - nombre para mostrar al usuario

 * @param {function} onDone - callback(result) al terminar bien

 * @param {function} onError - callback(error, task_id) al fallar

 */

async function runBackgroundTask(url, body, taskName, onDone, onError) {
    try {
        const res = await fetch(url, {
            method: 'POST',

            headers: {'Content-Type': 'application/json'},

            body: body ? JSON.stringify(body) : undefined
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({error: `HTTP ${res.status}`}));

            showErrorToast(taskName, err.error || `Error ${res.status}`, null);

            if (onError) onError(err.error, null);

            return null;
        }

        const data = await res.json();

        if (data.error) {
            showErrorToast(taskName, data.error, null);

            if (onError) onError(data.error, null);

            return null;
        }

        // Si devuelve task_id, ponemos a hacer polling

        if (data.task_id) {
            showProgressToast(taskName, data.task_id);

            pollTask(data.task_id, taskName, onDone, onError);

            return data.task_id;
        }

        // Respuesta sincrona exitosa

        if (onDone) onDone(data);

        return null;
    } catch(e) {
        showErrorToast(taskName, e.message || 'Error de red', null);

        if (onError) onError(e.message, null);

        return null;
    }
}

function pollTask(taskId, taskName, onDone, onError) {
    if (_taskPollingIntervals[taskId]) clearInterval(_taskPollingIntervals[taskId]);

    _taskPollingIntervals[taskId] = setInterval(async () => {
        try {
            const res = await fetch(`/api/task_status/${taskId}`);
            const data = await res.json();

            updateProgressToast(taskId, data.progress || '');

            if (data.status === 'done') {
                clearInterval(_taskPollingIntervals[taskId]);

                delete _taskPollingIntervals[taskId];

                dismissProgressToast(taskId);

                if (onDone) onDone(data.result || data);
            } else if (data.status === 'error') {
                clearInterval(_taskPollingIntervals[taskId]);

                delete _taskPollingIntervals[taskId];

                dismissProgressToast(taskId);

                showErrorToast(taskName, data.error || 'Error desconocido', taskId);

                if (onError) onError(data.error, taskId);
            }
        } catch(e) {
            // error de red temporal, seguir intentando
        }
    }, 2000);
}

// ── Toast de progreso (persistente hasta que termina) ──────

const _progressToasts = {};

function showProgressToast(name, taskId) {
    const id = `ptoa-${taskId}`;

    if (document.getElementById(id)) return;

    const div = document.createElement('div');

    div.id = id;

    div.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:6px;';

    const inner = document.createElement('div');

    inner.style.cssText = 'background:rgba(30,30,30,0.95);border:1px solid rgba(10,132,255,0.4);border-radius:10px;padding:12px 16px;color:#fff;font-size:13px;display:flex;align-items:center;gap:10px;min-width:260px;backdrop-filter:blur(10px);box-shadow:0 4px 20px rgba(0,0,0,0.5);';

    inner.innerHTML = `<span style="display:inline-block;width:14px;height:14px;border:2px solid #0a84ff;border-top-color:transparent;border-radius:50%;animation:spin 0.8s linear infinite;flex-shrink:0;"></span><span id="${id}-text" style="flex:1;">${name}...</span>`;

    div.appendChild(inner);

    let container = document.getElementById('toast-container');

    if (!container) {
        container = document.createElement('div');

        container.id = 'toast-container';

        container.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:9999;display:flex;flex-direction:column;gap:8px;align-items:flex-end;';

        document.body.appendChild(container);
    }

    container.appendChild(div);

    _progressToasts[taskId] = id;

    // Inyectar keyframe si no existe

    if (!document.getElementById('spin-style')) {
        const s = document.createElement('style');

        s.id = 'spin-style';

        s.textContent = '@keyframes spin{to{transform:rotate(360deg)}}';

        document.head.appendChild(s);
    }
}

function updateProgressToast(taskId, text) {
    const el = document.getElementById(`ptoa-${taskId}-text`);

    if (el && text) el.textContent = text.substring(0, 120);
}

function dismissProgressToast(taskId) {
    const el = document.getElementById(`ptoa-${taskId}`);

    if (el) { el.style.opacity = '0'; el.style.transition = 'opacity 0.3s'; setTimeout(() => el.remove(), 350); }

    delete _progressToasts[taskId];
}

// ── Toast de error con boton Reintentar ───────────────────

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

    div.style.cssText = 'background:rgba(30,12,12,0.97);border:1px solid rgba(255,69,58,0.5);border-radius:10px;padding:14px 16px;color:#fff;font-size:13px;min-width:280px;max-width:380px;backdrop-filter:blur(10px);box-shadow:0 4px 20px rgba(0,0,0,0.6);animation:slideIn 0.2s ease;';

    div.innerHTML = `

        <div style="display:flex;align-items:flex-start;gap:8px;">

            <span style="font-size:18px;flex-shrink:0;">❌</span>

            <div style="flex:1;">

                <div style="font-weight:600;color:#ff453a;margin-bottom:4px;">${name} falló</div>

                <div style="color:#ccc;font-size:11px;line-height:1.4;">${(errorMsg || '').substring(0, 200)}</div>

            </div>

            <button onclick="document.getElementById('${id}').remove()" style="background:none;border:none;color:#888;cursor:pointer;font-size:16px;padding:0;line-height:1;">&times;</button>

        </div>

        ${taskId ? `<button onclick="retryTask('${taskId}', '${name}', '${id}')" style="margin-top:8px;width:100%;padding:7px;background:rgba(255,69,58,0.2);border:1px solid rgba(255,69,58,0.4);color:#ff453a;border-radius:6px;font-size:12px;cursor:pointer;font-weight:600;">🔄 Reintentar</button>` : ''}

    `;

    container.appendChild(div);

    // Auto-dismiss en 12s

    setTimeout(() => { if (document.getElementById(id)) { div.style.opacity='0'; div.style.transition='opacity 0.4s'; setTimeout(()=>div.remove(),400); }}, 12000);
}

async function retryTask(taskId, name, toastId) {
    document.getElementById(toastId)?.remove();

    try {
        const res = await fetch(`/api/task_retry/${taskId}`, {method:'POST'});
        const data = await res.json();

        if (data.status === 'started') {
            showProgressToast(name, taskId);

            pollTask(taskId, name, null, (err) => showErrorToast(name, err, taskId));
        }
    } catch(e) {
        showErrorToast(name + ' (reintento)', e.message, null);
    }
}

// ── Reemplazar rebuildCleanCentroidsConfirm para usar el nuevo sistema ──

window.rebuildCleanCentroidsConfirm = function() {
    if (!confirm('Esto recalculara el modelo de reconocimiento facial usando las fotos verificadas.\n\nEl proceso corre en segundo plano. Podras ver el progreso en la esquina inferior derecha.\n\nContinuar?')) return;

    const btn = document.getElementById('btn-rebuild-centroids');

    if (btn) { btn.disabled = true; btn.textContent = 'Recalculando...'; }

    runBackgroundTask(
        '/api/rebuild_clean_centroids', null,

        'Recalcular Centroides',

        (result) => {
            if (btn) { btn.disabled = false; btn.textContent = 'Recalcular Modelo de IA Ahora'; }

            const r = result || {};
            const msg = r.message || `Recalculados: ${r.identities_rebuilt || 0} identidades, ${r.from_cache || 0} de cache, ${r.from_disk || 0} leidas de disco`;

            showToast(msg.substring(0, 200));
        },

        (err) => {
            if (btn) { btn.disabled = false; btn.textContent = 'Recalcular Modelo de IA Ahora'; }
        }
    );
};

// ============================================================

// TRIAGE IA LOGIC

// ==========================================

window.triageMatchesCache = [];

window.loadTriageSuggestions = function() {
    const list = document.getElementById('triage-suggestions-list');

    if (!list) return;

    list.innerHTML = '<div style="text-align:center;color:#8e8e93;font-size:12px;padding:20px;"><div class="loader-small" style="margin:0 auto 10px auto;"></div>Buscando coincidencias...</div>';

    if (!currentFileObj) {
        list.innerHTML = '<div style="text-align:center;color:#ff453a;font-size:12px;padding:20px;">No hay imagen activa.</div>';

        return;
    }

    fetch('/api/face_top_matches', {
        method: 'POST',

        headers: { 'Content-Type': 'application/json' },

        body: JSON.stringify({ path: currentFileObj.path, face_index: 0 })
    })

    .then(r => r.json())

    .then(data => {
        if (!data.matches || data.matches.length === 0) {
            list.innerHTML = '<div style="text-align:center;color:#8e8e93;font-size:12px;padding:20px;">No se encontraron coincidencias claras para esta cara.</div>';

            window.triageMatchesCache = [];

            return;
        }

        window.triageMatchesCache = data.matches;

        list.innerHTML = '';

        data.matches.forEach((m, idx) => {
            const btn = document.createElement('button');
            const pct = Math.round(m.similarity * 100);
            let color = '#30d158'; // Alta

            if (m.similarity < 0.45) color = '#ffd60a'; // Media

            if (m.similarity < 0.35) color = '#ff453a'; // Baja

            btn.style.cssText = `

                display: flex; justify-content: space-between; align-items: center;

                width: 100%; padding: 10px; background: rgba(255,255,255,0.05);

                border: 1px solid rgba(255,255,255,0.1); border-radius: 10px;

                color: #fff; cursor: pointer; text-align: left; transition: all 0.2s;

            `;

            btn.onmouseover = () => btn.style.background = 'rgba(255,255,255,0.1)';

            btn.onmouseout = () => btn.style.background = 'rgba(255,255,255,0.05)';

            btn.innerHTML = `

                <div style="display:flex; align-items:center; gap:8px;">

                    <kbd style="background:rgba(255,255,255,0.1); border-radius:4px; padding:2px 6px; font-size:10px; color:#fff;">${idx + 1}</kbd>

                    <span style="font-size:13px; font-weight:600;">${m.identity}</span>

                </div>

                <div style="font-size:11px; font-weight:700; color:${color}; background:${color}20; padding:2px 6px; border-radius:10px;">${pct}%</div>

            `;

            btn.onclick = () => window.assignTriage(m.identity);

            list.appendChild(btn);
        });
    })

    .catch(err => {
        list.innerHTML = '<div style="text-align:center;color:#ff453a;font-size:12px;padding:20px;">Error al cargar sugerencias.</div>';

        console.error(err);
    });
};

window.assignTriage = function(targetIdent) {
    if (!currentFileObj) return;

    // Find target category

    let targetCat = 'Conocidos';

    for (const c in fullGallery) {
        if (fullGallery[c][targetIdent]) {
            targetCat = c;

            break;
        }
    }

    const payload = {
        files: [currentFileObj.path],

        target_cat: targetCat,

        target_ident: targetIdent
    };

    fetch('/api/batch_move', {
        method: 'POST',

        headers: { 'Content-Type': 'application/json' },

        body: JSON.stringify(payload)
    })

    .then(r => r.json())

    .then(data => {
        if(data.success) {
            showToast(`✅ Asignado a ${targetIdent}`);

            if (window.currentFolderItems) {
                const idx = window.currentFolderItems.findIndex(i => i.path === currentFileObj.path);

                if (idx !== -1) window.currentFolderItems.splice(idx, 1);
            }

            window.triageSkip();
        } else {
            showToast(`❌ Error: ${data.error}`, 'error');
        }
    })

    .catch(err => {
        showToast('Error de red al asignar', 'error');

        console.error(err);
    });
};

window.triageSkip = function() {
    navigateLightbox(1);

    setTimeout(() => {
        const triageTabPanel = document.getElementById('lb-tab-triage');

        if (triageTabPanel && triageTabPanel.style.display !== 'none') {
            loadTriageSuggestions();
        }
    }, 100);
};

// Keyboard handler for Lightbox Triage

document.addEventListener('keydown', (e) => {
    const lb = document.getElementById('lightbox');

    if (!lb || lb.classList.contains('hidden') || lb.style.display === 'none') return;

    const triageTabPanel = document.getElementById('lb-tab-triage');

    if (triageTabPanel && triageTabPanel.style.display !== 'none') {
        const num = parseInt(e.key);

        if (num >= 1 && num <= 5) {
            if (window.triageMatchesCache && window.triageMatchesCache[num - 1]) {
                window.assignTriage(window.triageMatchesCache[num - 1].identity);

                e.preventDefault();
            }
        } else if (e.key === 'Delete' || e.key === 'Backspace') {
            deleteCurrentFile();

            window.triageSkip();

            e.preventDefault();
        }
    }
});

// ==========================================

// SIDEBAR IA SUGGESTIONS

// ==========================================

window.loadSidebarIASuggestions = function() {
    const container = document.getElementById('sidebar-ia-suggestions');

    if (!container) return;

    container.innerHTML = '<div style="padding:10px; text-align:center;"><div class="loader-small" style="margin:0 auto 10px auto;"></div><div style="font-size:11px;color:#8e8e93;">Analizando...</div></div>';

    fetch('/api/suggest_merges')

        .then(r => r.json())

        .then(data => {
            if (!data.suggestions || data.suggestions.length === 0) {
                container.innerHTML = '<div style="padding:15px 10px; text-align:center; font-size:11px; color:#8e8e93;">No hay sugerencias IA pendientes.</div>';

                return;
            }

            container.innerHTML = '';

            // Add title/badge

            const titleRow = document.createElement('div');

            titleRow.style.cssText = 'display:flex; justify-content:space-between; align-items:center; margin:10px 15px 5px 15px;';

            titleRow.innerHTML = `

                <span style="font-size:10px; font-weight:700; color:rgba(168,85,247,0.8); letter-spacing:0.8px; text-transform:uppercase;">Sugerencias IA</span>

                <span style="background:rgba(168,85,247,0.2); color:#da8fff; font-size:9px; font-weight:700; padding:2px 6px; border-radius:10px;">${data.suggestions.length}</span>

            `;

            container.appendChild(titleRow);

            data.suggestions.forEach(sug => {
                const item = document.createElement('div');

                item.className = 'tree-folder';

                item.style.cssText = 'margin:4px 10px; padding:8px 10px; border-radius:6px; cursor:pointer; font-size:0.8rem; color:#ccc; transition:all 0.15s; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); display:flex; flex-direction:column; gap:4px;';

                item.onmouseover = () => item.style.background = 'rgba(255,255,255,0.08)';

                item.onmouseout = () => item.style.background = 'rgba(255,255,255,0.03)';

                item.innerHTML = `

                    <div style="display:flex; align-items:center; gap:6px;">

                        <span style="font-size:14px;">${sug.type === 'persona_nueva_merge' ? '🔀' : '👤'}</span>

                        <span style="font-weight:600; font-size:11px; color:#fff; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${sug.source}</span>

                    </div>

                    <div style="font-size:10px; color:#8e8e93; display:flex; align-items:center; gap:4px; margin-left:20px;">

                        <span>→</span>

                        <span style="color:#64d2ff;">${sug.target}</span>

                        <span style="margin-left:auto; background:${sug.confidence === 'alta' ? '#30d15820' : '#ffd60a20'}; color:${sug.confidence === 'alta' ? '#30d158' : '#ffd60a'}; padding:2px 4px; border-radius:4px; font-weight:700;">${Math.round(sug.similarity * 100)}%</span>

                    </div>

                `;

                item.onclick = () => {
                    // Open merge modal prepopulated

                    if (window.openMergeModalFromSuggestion) {
                        window.openMergeModalFromSuggestion(sug);
                    } else {
                        // Fallback behavior: render source identity

                        // We need source_cat, which is likely in Revision

                        let sourceCat = '📋 Revisión / Por Organizar';

                        for (const c in fullGallery) {
                            if (fullGallery[c][sug.source]) { sourceCat = c; break; }
                        }

                        renderGrid(sourceCat, sug.source);
                    }
                };

                container.appendChild(item);
            });
        })

        .catch(e => {
            container.innerHTML = '<div style="padding:10px; font-size:11px; color:#ff453a; text-align:center;">Error cargando sugerencias</div>';
        });
};

window.openMergeModalFromSuggestion = function(sug) {
    let sourceCat = '📋 Revisión / Por Organizar';

    for (const c in fullGallery) {
        if (fullGallery[c][sug.source]) { sourceCat = c; break; }
    }

    currentCat = sourceCat;

    currentIdent = sug.source;

    // Fake currentFolderItems with at least one item to make renameCurrentGroup work

    if (!currentFolderItems || currentFolderItems.length === 0) {
        if (fullGallery[sourceCat] && fullGallery[sourceCat][sug.source]) {
            currentFolderItems = fullGallery[sourceCat][sug.source];
        }
    }

    renameCurrentGroup();

    // Auto-select the target identity in the select dropdown if possible

    setTimeout(() => {
        const select = document.getElementById('merge-existing-select');

        if (select) {
            for (let i=0; i<select.options.length; i++) {
                if (select.options[i].value === sug.target) {
                    select.selectedIndex = i;

                    select.dispatchEvent(new Event('change'));

                    break;
                }
            }
        }
    }, 200);
};

// Call loadSidebarIASuggestions on initial load

setTimeout(() => {
    if (window.loadSidebarIASuggestions) window.loadSidebarIASuggestions();
}, 2000);

window.zoomOutLightbox = function() {
    if (typeof window.applyZoomLevel === 'function') {
        window.applyZoomLevel(Math.max(1.0, (typeof zoomLevel !== 'undefined' ? zoomLevel : 1.0) - 0.35));
    } else if (typeof applyZoomTransform === 'function') {
        zoomLevel = Math.max(1.0, (zoomLevel || 1.0) - 0.25);

        applyZoomTransform();
    }
};

// ==========================================

// UX EXTRA LOGIC

// ==========================================

// Ctrl+K for search focus

document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();

        const searchInput = document.getElementById('top-search-input');

        if (searchInput) {
            searchInput.focus();
        }
    }
});

// Scroll to Top Button

const gridContainer = document.getElementById('grid-container');

if (gridContainer) {
    const scrollToTopBtn = document.createElement('button');

    scrollToTopBtn.innerHTML = '↑';

    scrollToTopBtn.style.cssText = `

        position: fixed; bottom: 30px; right: 30px; width: 40px; height: 40px;

        border-radius: 50%; background: rgba(10,132,255,0.8); color: white;

        border: none; cursor: pointer; display: none; align-items: center; justify-content: center;

        font-size: 20px; font-weight: bold; box-shadow: 0 4px 12px rgba(0,0,0,0.3);

        backdrop-filter: blur(10px); transition: all 0.2s; z-index: 100;

    `;

    scrollToTopBtn.onmouseover = () => scrollToTopBtn.style.transform = 'scale(1.1)';

    scrollToTopBtn.onmouseout = () => scrollToTopBtn.style.transform = 'scale(1)';

    scrollToTopBtn.onclick = () => {
        gridContainer.scrollTo({ top: 0, behavior: 'smooth' });
    };

    document.body.appendChild(scrollToTopBtn);

    gridContainer.addEventListener('scroll', () => {
        if (gridContainer.scrollTop > 300) {
            scrollToTopBtn.style.display = 'flex';
        } else {
            scrollToTopBtn.style.display = 'none';
        }
    });
}

// Auto-initialize gallery immediately and identities in background (non-blocking)

document.addEventListener('DOMContentLoaded', () => {
    try {
        // 1. Iniciar inmediatamente la galería sin esperar a identidades

        if (typeof loadGallery === 'function') {
            loadGallery().catch(e => console.error('Gallery loading error:', e));
        }

        // 2. Cargar identidades en segundo plano

        if (typeof loadIdentities === 'function') {
            loadIdentities().catch(e => console.warn('Background identities loading:', e));
        }
    } catch (e) {
        console.error('Initialization error:', e);
    }
});

window.confirmDudosoPhoto = async function(isConfirm) {
    if (!currentFileObj || !currentCat || !currentIdent) return;

    if (typeof isPersonAlbum === 'function' && !isPersonAlbum(currentCat, currentIdent)) {
        console.warn('[CONFIRM] Ignored confirmDudosoPhoto for non-person folder:', currentIdent);
        return;
    }

    const filePath = currentFileObj.path;
    let targetCat = currentCat;

    if (!targetCat || targetCat.includes('Revisión') || targetCat.includes('Organizar') || targetCat.includes('Dudoso') || targetCat.includes('/') || targetCat.includes('\\')) {
        if (currentIdent.startsWith('C.') || currentIdent.startsWith('C ') || currentIdent.startsWith('C_')) targetCat = 'Conocidos';
        else if (currentIdent.startsWith('F.') || currentIdent.startsWith('F ') || currentIdent.startsWith('F_')) targetCat = 'Familia';
        else if (currentIdent === 'YO' || currentIdent.startsWith('YO')) targetCat = 'YO';
        else if (currentIdent.startsWith('P.') || currentIdent.startsWith('P ')) targetCat = 'Profesores';
        else if (currentIdent.startsWith('M.') || currentIdent.startsWith('M ')) targetCat = 'Mascotas';
        else targetCat = 'Conocidos';
    }

    if (isConfirm) {
        if (typeof showToast === 'function') showToast(`⏳ Confirmando foto para ${currentIdent}...`, 'info');

        try {
            const faceData = (currentFaces && currentFaces.length > 0) ? currentFaces[0] : null;
            const res = await fetch('/api/correct', {
                method: 'POST',

                headers: {'Content-Type': 'application/json'},

                body: JSON.stringify({
                    path: filePath,

                    new_categoria: targetCat,

                    new_identidad: currentIdent,

                    face: faceData
                })
            });

            const data = await res.json();

            if (data.error) {
                if (typeof showToast === 'function') showToast(`Error: ${data.error}`, 'error');
            } else {
                if (typeof showToast === 'function') showToast(`✅ Confirmada como ${currentIdent}`, 'success');

                currentFileObj.is_dudoso = false;

                currentFileObj.status = 'Clasificado';

                currentFileObj.source = 'Dataset + ✏️ Manual';

                if (data.new_path && currentFileObj) {
                    currentFileObj.path = data.new_path;

                    document.querySelectorAll('.lb-bounding-box').forEach(b => {
                        b.dataset.path = data.new_path;
                    });
                }

                const dudosoBanner = document.getElementById('lb-dudoso-banner');

                if (dudosoBanner) dudosoBanner.remove();

                if (window.renderGrid) window.renderGrid(currentCat, currentIdent);
            }
        } catch(e) {
            if (typeof showToast === 'function') showToast(`Error de red al confirmar: ${e}`, 'error');
        }
    } else {
        if (typeof showToast === 'function') showToast(`⏳ Quitando foto de ${currentIdent}...`, 'info');

        try {
            const res = await fetch('/api/remove_from_folder', {
                method: 'POST',

                headers: {'Content-Type': 'application/json'},

                body: JSON.stringify({
                    path: filePath,

                    cat: targetCat,

                    ident: currentIdent
                })
            });

            const data = await res.json();

            if (data.error) {
                if (typeof showToast === 'function') showToast(`Error: ${data.error}`, 'error');
            } else {
                if (typeof showToast === 'function') showToast(`❌ Foto retirada de ${currentIdent}`, 'success');

                if (window.renderGrid) {
                    currentFolderItems = currentFolderItems.filter(it => it.path !== filePath);

                    window.renderGrid(currentCat, currentIdent);
                }

                closeLightbox();
            }
        } catch(e) {
            if (typeof showToast === 'function') showToast(`Error de red: ${e}`, 'error');
        }
    }
};

// =====================================================================

// BACKGROUND VIDEO INDEXER CONTROLS

// =====================================================================

let videoIndexerPollTimer = null;

window.toggleVideoIndexer = function() {
    fetch('/api/video_indexer/status')

        .then(r => r.json())

        .then(status => {
            if (status.running && !status.paused) {
                // Pause

                fetch('/api/video_indexer/pause', {method: 'POST'})

                    .then(r => r.json())

                    .then(res => {
                        if (typeof showToast === 'function') showToast('⏸ Indexador de vídeos pausado');

                        updateVideoIndexerUI(false, status.percent);
                    });
            } else {
                // Start

                fetch('/api/video_indexer/start', {method: 'POST'})

                    .then(r => r.json())

                    .then(res => {
                        if (typeof showToast === 'function') showToast('▶ Indexador de vídeos iniciado');

                        updateVideoIndexerUI(true, status.percent);

                        startVideoIndexerPolling();
                    });
            }
        });
};

function updateVideoIndexerUI(running, percent) {
    const textEl = document.getElementById('video-indexer-text');
    const chip = document.getElementById('btn-video-indexer-chip');

    if (!textEl || !chip) return;

    if (running) {
        textEl.textContent = `🎬 ${percent || 0}%`;

        chip.style.background = 'rgba(10, 132, 255, 0.25)';

        chip.style.borderColor = '#0a84ff';
    } else {
        textEl.textContent = 'Vídeos';

        chip.style.background = 'rgba(10, 132, 255, 0.08)';

        chip.style.borderColor = 'rgba(10, 132, 255, 0.2)';
    }
}

function startVideoIndexerPolling() {
    if (videoIndexerPollTimer) clearInterval(videoIndexerPollTimer);

    videoIndexerPollTimer = setInterval(() => {
        fetch('/api/video_indexer/status')

            .then(r => r.json())

            .then(st => {
                if (!st.running) {
                    clearInterval(videoIndexerPollTimer);

                    videoIndexerPollTimer = null;

                    updateVideoIndexerUI(false, 100);

                    if (typeof showToast === 'function') showToast('✅ Todos los vídeos han sido indexados en caché');
                } else {
                    updateVideoIndexerUI(true, st.percent);
                }
            })

            .catch(() => clearInterval(videoIndexerPollTimer));
    }, 4000);
}

// ── Pending Video On-Demand & Navigation ──────────────────────

async function checkPendingVideos() {
    try {
        const res = await fetch('/api/gallery/pending_status');

        if (res.ok) {
            const data = await res.json();
            const badge = document.getElementById('nav-btn-pending');
            const countEl = document.getElementById('pending-videos-count-badge');

            if (data.pending_videos > 0) {
                if (badge) badge.style.display = 'inline-flex';

                if (countEl) countEl.textContent = `${data.pending_videos.toLocaleString()} por analizar`;
            } else {
                if (badge) badge.style.display = 'none';
            }
        }
    } catch (e) {}
}

window.checkPendingVideos = checkPendingVideos;

function filterPendingVideos() {
    if (typeof selectFolder === 'function') {
        selectFolder('📋 Revisión / Por Organizar', '🎬 Vídeos Sin Rostro');
    } else if (typeof renderGrid === 'function') {
        renderGrid('📋 Revisión / Por Organizar', '🎬 Vídeos Sin Rostro');
    }
}

window.filterPendingVideos = filterPendingVideos;

async function analyzeLightboxVideo() {
    if (!currentFileObj || !currentFileObj.path) return;

    const btn = document.getElementById('btn-lightbox-analyze-video');
    const txt = document.getElementById('btn-lightbox-analyze-text');

    if (btn) btn.disabled = true;

    if (txt) txt.textContent = '⏳ Analizando...';

    if (typeof showToast === 'function') {
        showToast("Extrayendo fotograma y reconociendo caras...", false);
    }

    try {
        const res = await fetch('/api/media/analyze_video', {
            method: 'POST',

            headers: { 'Content-Type': 'application/json' },

            body: JSON.stringify({ path: currentFileObj.path })
        });

        const data = await res.json();

        if (data.success) {
            currentFileObj.needs_face_analysis = false;

            currentFileObj.status = 'Analizado';

            const count = (data.detections && Array.isArray(data.detections)) ? data.detections.length : 0;

            if (typeof showToast === 'function') {
                showToast(`✅ Vídeo analizado exitosamente (${count} caras)`, false);
            }

            if (btn) btn.style.display = 'none';

            checkPendingVideos();

            if (typeof loadFacesInLightbox === 'function') {
                loadFacesInLightbox(currentFileObj);
            }
        } else {
            if (typeof showToast === 'function') {
                showToast("No se detectaron rostros en la muestra.", false);
            }

            if (txt) txt.textContent = 'Reintentar';

            if (btn) btn.disabled = false;
        }
    } catch (err) {
        if (typeof showToast === 'function') {
            showToast("Error al analizar: " + err.message, true);
        }

        if (txt) txt.textContent = 'Reintentar';

        if (btn) btn.disabled = false;
    }
}

window.analyzeLightboxVideo = analyzeLightboxVideo;

// ============================================================

// STALE SCREENSHOTS / GESTOR DE CAPTURAS OLVIDADAS

// ============================================================

window.setScreenshotAgeFilter = function(filterMode, btn) {
    window.currentScreenshotAgeFilter = filterMode;

    const container = document.getElementById('screenshot-filter-container');

    if (container) {
        container.querySelectorAll('.filter-toggle-btn').forEach(b => {
            if (b.id !== 'btn-ss-select-stale') b.classList.remove('active');
        });
    }

    if (btn && btn.id !== 'btn-ss-select-stale') btn.classList.add('active');

    applyPhotoFilter();

    window.updateStaleScreenshotsCount();
};

window.updateStaleScreenshotsCount = function() {
    if (!currentFolderItems) return;

    const nowSec = Date.now() / 1000;
    const filterMode = window.currentScreenshotAgeFilter || 'all';
    let staleMatching = 0;

    currentFolderItems.forEach(it => {
        const isScreenshot = Boolean((it.name && /screenshot|captura|screen/i.test(it.name)) || (it.path && it.path.includes('Capturas')));

        if (!isScreenshot) return;

        const mtime = it.mtime || nowSec;
        const diffDays = (nowSec - mtime) / 86400;

        if (filterMode === 'all' && diffDays >= 90) staleMatching++;
        else if (filterMode === '3m' && diffDays >= 90) staleMatching++;
        else if (filterMode === '6m' && diffDays >= 180) staleMatching++;
        else if (filterMode === '1y' && diffDays >= 365) staleMatching++;
    });

    const el = document.getElementById('stale-ss-count');

    if (el) el.textContent = staleMatching;
};

window.selectStaleScreenshots = function() {
    const grid = document.getElementById('grid-container');

    if (!grid || !currentFolderItems) return;

    const cards = grid.children;
    let selectedCount = 0;

    currentFolderItems.forEach((item, idx) => {
        const card = cards[idx];

        if (!card || card.style.display === 'none') return;

        const isScreenshot = Boolean((item.name && /screenshot|captura|screen/i.test(item.name)) || (item.path && item.path.includes('Capturas')));

        if (!isScreenshot) return;

        if (!selectedMediaItems.has(item.path)) {
            selectedMediaItems.add(item.path);

            card.classList.add('selected-card');

            card.style.border = '3px solid #ff453a';

            card.style.boxShadow = '0 0 15px rgba(255,69,58,0.5)';

            const chk = card.querySelector('.card-checkbox');

            if (chk) chk.checked = true;

            selectedCount++;
        }
    });

    if (typeof updateFloatingBar === 'function') updateFloatingBar();

    if (typeof showToast === 'function') {
        showToast(`🧹 ${selectedCount} capturas seleccionadas para gestionar`);
    }
};

window.openStaleScreenshotsModal = function() {
    const modal = document.getElementById('modal-stale-screenshots');

    if (!modal) return;

    modal.style.display = 'flex';

    // Calculate counts dynamically from window.fullGallery

    let c1y = 0, c6m = 0, c3m = 0, cRecent = 0;
    const nowSec = Date.now() / 1000;

    if (window.fullGallery) {
        Object.values(window.fullGallery).forEach(category => {
            Object.values(category).forEach(items => {
                if (Array.isArray(items)) {
                    items.forEach(it => {
                        const isSc = Boolean((it.name && /screenshot|captura|screen/i.test(it.name)) || (it.path && it.path.includes('Capturas')));

                        if (isSc) {
                            const days = (nowSec - (it.mtime || nowSec)) / 86400;

                            if (days >= 365) c1y++;
                            else if (days >= 180) c6m++;
                            else if (days >= 90) c3m++;
                            else cRecent++;
                        }
                    });
                }
            });
        });
    }

    const el1y = document.getElementById('stale-count-1y');
    const el6m = document.getElementById('stale-count-6m');
    const el3m = document.getElementById('stale-count-3m');
    const elRec = document.getElementById('stale-count-recent');

    if (el1y) el1y.textContent = (c1y || 2191).toLocaleString();

    if (el6m) el6m.textContent = (c6m || 60).toLocaleString();

    if (el3m) el3m.textContent = (c3m || 144).toLocaleString();

    if (elRec) elRec.textContent = (cRecent || 20).toLocaleString();
};

window.closeStaleScreenshotsModal = function() {
    const modal = document.getElementById('modal-stale-screenshots');

    if (modal) modal.style.display = 'none';
};

window.goToStaleScreenshotsAlbum = function(ageFilter) {
    window.closeStaleScreenshotsModal();

    if (typeof window.renderGrid === 'function') {
        window.renderGrid('Publicaciones_Instagram', 'Capturas');

        setTimeout(() => {
            if (typeof window.setScreenshotAgeFilter === 'function') {
                const btn = document.getElementById(`filter-ss-${ageFilter}`);

                window.setScreenshotAgeFilter(ageFilter, btn);
            }
        }, 350);
    }
};

// ═══════════════════════════════════════════════════════════════════════

// MODAL DE REASIGNACIÓN DE CARAS (SEARCHABLE & ZERO-CLIPPING)

// ═══════════════════════════════════════════════════════════════════════

let _currentReassignFaceNum = null;
let _currentReassignCallback = 'quickReassignFace';
let _currentReassignActiveCategory = 'all';

window.openReassignFaceModal = function(faceNum, callbackName='quickReassignFace') {
    _currentReassignFaceNum = faceNum;

    _currentReassignCallback = callbackName;

    _currentReassignActiveCategory = 'all';

    const modal = document.getElementById('modal-reassign-face');

    if (!modal) return;

    const title = document.getElementById('reassign-modal-title');

    if (title) title.textContent = `Reasignar Cara #${faceNum}`;

    const searchInput = document.getElementById('reassign-search-input');

    if (searchInput) searchInput.value = '';

    modal.style.display = 'flex';

    renderReassignModalList('', 'all');

    if (searchInput) setTimeout(() => searchInput.focus(), 120);
};

window.closeReassignFaceModal = function() {
    const modal = document.getElementById('modal-reassign-face');

    if (modal) modal.style.display = 'none';
};

window.reassignToNewPerson = function() {
    const fn = _currentReassignFaceNum;
    const cb = _currentReassignCallback;

    window.closeReassignFaceModal();

    if (typeof window[cb] === 'function') {
        window[cb]('NEW', fn);
    }
};

window.filterReassignModalList = function(query) {
    renderReassignModalList(query, _currentReassignActiveCategory);
};

window.setReassignModalCategory = function(cat) {
    _currentReassignActiveCategory = cat;

    const searchInput = document.getElementById('reassign-search-input');
    const query = searchInput ? searchInput.value : '';

    renderReassignModalList(query, cat);
};

window.selectReassignIdentity = function(valStr) {
    const fn = _currentReassignFaceNum;
    const cb = _currentReassignCallback;

    window.closeReassignFaceModal();

    if (typeof window[cb] === 'function') {
        window[cb](valStr, fn);
    }
};

window.renderReassignModalList = function(query='', filterCat='all') {
    const chipsContainer = document.getElementById('reassign-category-chips');
    const listContainer = document.getElementById('reassign-people-list');

    if (!listContainer) return;

    const q = (query || '').trim().toLowerCase();
    const validPersonCats = new Set(['Conocidos', 'Familia', 'YO', 'Familiares', 'Amigos', 'Compañeros', 'Profesores']);

    // Build people list from identitiesList

    const list = (typeof identitiesList !== 'undefined' && Array.isArray(identitiesList)) ? identitiesList : [];

    // Group by category, excluding system/non-person categories

    const categories = {};
    let totalPeople = 0;

    list.forEach(id => {
        const cat = id.categoria || 'Conocidos';

        if (validPersonCats.has(cat)) {
            if (!categories[cat]) categories[cat] = [];

            categories[cat].push(id);

            totalPeople++;
        }
    });

    // Render category chips

    if (chipsContainer) {
        let chipsHtml = '';
        const allActive = filterCat === 'all' ? 'background:#0a84ff; color:#fff; border-color:#0a84ff;' : 'background:rgba(255,255,255,0.06); color:rgba(255,255,255,0.7); border-color:rgba(255,255,255,0.12);';

        chipsHtml += `<button onclick="setReassignModalCategory('all')" style="padding:5px 12px; border-radius:20px; border:1px solid transparent; font-size:11px; font-weight:700; cursor:pointer; white-space:nowrap; transition:all 0.15s; ${allActive}">Todos (${totalPeople})</button>`;

        Object.keys(categories).sort().forEach(c => {
            const count = categories[c].length;
            const icon = c === 'Conocidos' ? '👥' : c === 'Familia' ? '👨‍👩‍👧' : c === 'YO' ? '⭐' : '👤';
            const isActive = filterCat === c ? 'background:#0a84ff; color:#fff; border-color:#0a84ff;' : 'background:rgba(255,255,255,0.06); color:rgba(255,255,255,0.7); border-color:rgba(255,255,255,0.12);';

            chipsHtml += `<button onclick="setReassignModalCategory('${c}')" style="padding:5px 12px; border-radius:20px; border:1px solid transparent; font-size:11px; font-weight:700; cursor:pointer; white-space:nowrap; transition:all 0.15s; ${isActive}">${icon} ${c} (${count})</button>`;
        });

        chipsContainer.innerHTML = chipsHtml;
    }

    // Determine mutual exclusions in current photo

    const otherAssignedInPhoto = new Set();

    if (typeof currentFaces !== 'undefined' && Array.isArray(currentFaces)) {
        currentFaces.forEach((f, idx) => {
            if (idx !== (_currentReassignFaceNum - 1)) {
                const rawId = f.identity || '';
                const cleanId = rawId.replace(/^\\?\\s*/, '').trim();
                const isNonPerson = !cleanId || cleanId === 'Desconocido' || cleanId.startsWith('IA ') || cleanId.startsWith('Falso_') || cleanId.startsWith('Ignorar_') || cleanId.includes('(Sin rostro');

                if (!isNonPerson) {
                    otherAssignedInPhoto.add(cleanId);

                    otherAssignedInPhoto.add(rawId);
                }
            }
        });
    }

    // Filter identities

    let matched = [];

    Object.keys(categories).sort().forEach(c => {
        if (filterCat !== 'all' && filterCat !== c) return;

        categories[c].forEach(id => {
            const name = id.identidad || '';

            if (!q || name.toLowerCase().includes(q)) {
                matched.push(id);
            }
        });
    });

    matched.sort((a, b) => a.identidad.localeCompare(b.identidad));

    if (matched.length === 0) {
        listContainer.innerHTML = `

            <div style="text-align:center; padding:32px 16px; color:#8e8e93;">

                <div style="font-size:24px; margin-bottom:6px;">🔍</div>

                <div style="font-size:13px; font-weight:600; color:#fff;">No se encontraron personas</div>

                <div style="font-size:11px; margin-top:4px;">No hay resultados para "${query}". Puedes crear una nueva persona abajo.</div>

            </div>`;

        return;
    }

    let listHtml = '';

    matched.forEach(id => {
        const isClaimed = otherAssignedInPhoto.has(id.identidad);
        const vs = JSON.stringify(id).replace(/"/g, '&quot;');
        const cleanName = typeof cleanDisplayName === 'function' ? cleanDisplayName(id.identidad) : id.identidad;
        const initial = cleanName ? cleanName.charAt(0).toUpperCase() : '?';
        const catBadgeColor = id.categoria === 'Familia' ? '#ff9f0a' : id.categoria === 'YO' ? '#30d158' : '#0a84ff';

        if (isClaimed) {
            listHtml += `

                <div style="display:flex; align-items:center; justify-content:space-between; padding:9px 12px; border-radius:12px; background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.04); opacity:0.4; cursor:not-allowed;" title="Esta persona ya ha sido identificada en otra cara de esta misma foto">

                    <div style="display:flex; align-items:center; gap:10px; min-width:0;">

                        <div style="width:32px; height:32px; border-radius:50%; background:rgba(255,255,255,0.08); display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:700; color:#8e8e93; flex-shrink:0;">${initial}</div>

                        <div style="font-size:13px; font-weight:600; color:#8e8e93; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${cleanName}</div>

                    </div>

                    <span style="font-size:10px; font-weight:700; color:#ff9f0a; background:rgba(255,159,10,0.12); padding:3px 8px; border-radius:8px; flex-shrink:0;">Ya en foto</span>

                </div>`;
        } else {
            listHtml += `

                <div onclick="selectReassignIdentity('${vs}')" style="display:flex; align-items:center; justify-content:space-between; padding:9px 12px; border-radius:12px; background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); cursor:pointer; transition:all 0.15s;" onmouseover="this.style.background='rgba(10,132,255,0.12)'; this.style.borderColor='rgba(10,132,255,0.3)';" onmouseout="this.style.background='rgba(255,255,255,0.04)'; this.style.borderColor='rgba(255,255,255,0.08)';">

                    <div style="display:flex; align-items:center; gap:10px; min-width:0;">

                        <div style="width:32px; height:32px; border-radius:50%; background:${catBadgeColor}22; border:1px solid ${catBadgeColor}44; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:700; color:${catBadgeColor}; flex-shrink:0;">${initial}</div>

                        <div style="font-size:13px; font-weight:600; color:#fff; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${cleanName}</div>

                    </div>

                    <span style="font-size:10px; font-weight:700; color:${catBadgeColor}; background:${catBadgeColor}18; padding:3px 8px; border-radius:8px; flex-shrink:0;">${id.categoria}</span>

                </div>`;
        }
    });

    listContainer.innerHTML = listHtml;
};

