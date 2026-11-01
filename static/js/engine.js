// =============================================================
// ENGINE.JS - Motor de Auto-Corrección Bidireccional & SSE Live
// =============================================================

window.isBgAutoClassifyActive = false;
window.bgClassifyInterval = null;

window._engineSSE = null;
window._enginePanelOpen = false;
window._engineRunning = false;
window._enginePollTimer = null;

window.toggleEnginePanel = function() {
    const panel = document.getElementById('engine-panel');
    if (!panel) return;
    window._enginePanelOpen = !window._enginePanelOpen;
    panel.style.display = window._enginePanelOpen ? 'block' : 'none';
    if (window._enginePanelOpen) {
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
        window._engineRunning = true;
        _updateEngineUI(true);
        if (typeof showToast === 'function') {
            showToast('🤖 Motor de auto-corrección iniciado.');
        }
        _startEngineSSE();
    }).catch(e => {
        if (typeof showToast === 'function') showToast('Error arrancando el motor.', true);
    });
};

window.stopEngine = function() {
    fetch('/api/auto_classify_continuous', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action: 'stop'})
    }).then(r => r.json()).then(data => {
        window._engineRunning = false;
        _updateEngineUI(false);
        _stopEngineSSE();
        if (typeof showToast === 'function') showToast('⏹ Motor detenido.');
    }).catch(e => {});
};

window.toggleBgAutoClassify = function() { window.toggleEnginePanel(); };
window.startBgAutoClassify = function() { window.startEngine(); };
window.stopBgAutoClassify = function() { window.stopEngine(); };

function _startEngineSSE() {
    if (window._engineSSE) return;
    try {
        window._engineSSE = new EventSource('/api/self_audit_stream');
        window._engineSSE.onmessage = function(e) {
            try {
                const d = JSON.parse(e.data);
                _applyEngineStatus(d);
            } catch(err) {}
        };
        window._engineSSE.onerror = function() {
            if (window._engineSSE) {
                window._engineSSE.close();
                window._engineSSE = null;
            }
            if (window._enginePanelOpen) {
                setTimeout(_startEngineSSE, 10000);
            }
        };
    } catch(e) {}
}

function _stopEngineSSE() {
    if (window._engineSSE) {
        window._engineSSE.close();
        window._engineSSE = null;
    }
}

function _pollEngineStatus() {
    fetch('/api/self_audit_status')
        .then(r => r.json())
        .then(d => _applyEngineStatus(d))
        .catch(e => {});
}

window._PHASE_LABELS = {
    'idle':          '⏸ Inactivo — esperando inicio',
    'scan_unknown':  '🔍 Fase A — Clasificando desconocidos...',
    'audit_known':   '🔄 Fase B — Auditando carpetas conocidas...',
    'waiting':       '⏳ Descansando entre ciclos (60 s)...',
    'deep_scan':     '🧠 Escaneo profundo...',
};

function _applyEngineStatus(d) {
    window._engineRunning = !!d.running;
    _updateEngineUI(window._engineRunning);

    _setInner('engine-stat-scanned', d.total_scanned ?? 0);
    _setInner('engine-stat-known',   d.total_moved_to_known ?? 0);
    _setInner('engine-stat-review',  d.total_moved_to_review ?? 0);
    _setInner('drawer-stat-fixed',   d.total_fixed ?? 0);
    _setInner('drawer-stat-cycle',   d.cycle ?? 0);

    const phaseLabel = window._PHASE_LABELS[d.phase] || d.phase || 'Inactivo';
    _setInner('engine-phase-label', phaseLabel);

    const lastFileEl = document.getElementById('engine-last-file');
    if (lastFileEl) {
        if (d.last_scanned_file) {
            lastFileEl.textContent = `📍 ${d.last_scanned_file}`;
        } else if (window._engineRunning) {
            lastFileEl.textContent = `⏳ Reanudando desde checkpoint previo...`;
        } else {
            lastFileEl.textContent = `⏸️ Estado guardado en disco`;
        }
    }

    const dot = document.getElementById('engine-cycle-dot');
    const cycleText = document.getElementById('engine-cycle-text');
    if (dot) {
        dot.style.background = window._engineRunning
            ? (d.phase === 'waiting' ? '#ff9f0a' : '#30d158')
            : '#3a3a3c';
        dot.style.boxShadow = window._engineRunning ? `0 0 6px ${d.phase === 'waiting' ? '#ff9f0a' : '#30d158'}` : 'none';
    }
    if (cycleText) {
        cycleText.textContent = d.cycle
            ? `Ciclo ${d.cycle} — ${(d.total_fixed ?? 0)} correcciones totales`
            : 'Ciclo 0 — esperando inicio';
    }

    const logEl = document.getElementById('engine-log');
    if (logEl && d.last_actions && d.last_actions.length > 0) {
        const entries = d.last_actions.slice().reverse();
        logEl.innerHTML = entries.map(a => {
            const color = a.msg && a.msg.startsWith('✅') ? '#30d158'
                        : a.msg && a.msg.startsWith('🔄') ? '#64d2ff'
                        : a.msg && a.msg.startsWith('⚠️') ? '#ff9f0a'
                        : '#8e8e93';
            return `<div style="padding:5px 6px; border-bottom:1px solid rgba(255,255,255,0.04); font-size:11px;">
                <span style="color:#555; margin-right:6px;">${a.ts || ''}</span>
                <span style="color:${color};">${a.msg || ''}</span>
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
        btn.style.background = running ? 'rgba(48,209,88,0.15)' : 'rgba(10,132,255,0.12)';
        btn.style.borderColor = running ? '#30d158' : 'rgba(10,132,255,0.3)';
        btn.style.color = running ? '#30d158' : '#64d2ff';
    }
    if (badge)    badge.style.display = running ? 'inline' : 'none';
    if (startBtn) startBtn.style.display = running ? 'none' : 'inline-block';
    if (stopBtn)  stopBtn.style.display  = running ? 'inline-block' : 'none';
}

function _setInner(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        _pollEngineStatus();
        _startEngineSSE();
    }, 1500);
});
