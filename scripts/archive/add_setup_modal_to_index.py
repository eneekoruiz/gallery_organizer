import sys, re

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

setup_modal_html = """
<!-- Modal de Configuración Inicial (Local vs Google Drive) -->
<div id="setup-modal" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.85); backdrop-filter: blur(12px); z-index: 10000; align-items: center; justify-content: center; padding: 20px;">
    <div style="background: rgba(22,25,35,0.95); border: 1px solid rgba(255,255,255,0.15); border-radius: 24px; padding: 32px; max-width: 540px; width: 100%; box-shadow: 0 20px 50px rgba(0,0,0,0.5); text-align: center; color: white;">
        <h2 style="font-size: 1.8rem; font-weight: 800; margin-bottom: 8px; background: linear-gradient(135deg, #a855f7, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">⚙️ Entorno de Almacenamiento</h2>
        <p style="color: #94a3b8; font-size: 0.95rem; margin-bottom: 24px;">Selecciona dónde procesar y organizar tus fotografías y vídeos:</p>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px;">
            <div id="opt-local" onclick="selectStorageMode('local')" style="background: rgba(255,255,255,0.05); border: 2px solid #a855f7; border-radius: 16px; padding: 20px; cursor: pointer; transition: all 0.2s;">
                <div style="font-size: 2.2rem; margin-bottom: 8px;">💻</div>
                <div style="font-weight: 700; font-size: 1.05rem;">Disco Local</div>
                <div style="color: #64748b; font-size: 0.8rem; margin-top: 4px;">Almacenamiento en PC</div>
            </div>
            <div id="opt-gdrive" onclick="selectStorageMode('gdrive')" style="background: rgba(255,255,255,0.02); border: 2px solid transparent; border-radius: 16px; padding: 20px; cursor: pointer; transition: all 0.2s;">
                <div style="font-size: 2.2rem; margin-bottom: 8px;">☁️</div>
                <div style="font-weight: 700; font-size: 1.05rem;">Google Drive</div>
                <div style="color: #64748b; font-size: 0.8rem; margin-top: 4px;">Conexión API Nube</div>
            </div>
        </div>

        <div id="field-local" style="margin-bottom: 20px; text-align: left;">
            <label style="font-size: 0.85rem; color: #94a3b8; display: block; margin-bottom: 6px;">Ruta del Directorio Local:</label>
            <input type="text" id="input-local-path" value="C:\\Users\\User\\Desktop\\Galeria Eneko NO ABRIR" style="width: 100%; background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.15); border-radius: 10px; padding: 12px; color: white; font-family: monospace; font-size: 0.9rem;">
        </div>

        <div id="field-gdrive" style="display: none; margin-bottom: 20px; text-align: left;">
            <label style="font-size: 0.85rem; color: #94a3b8; display: block; margin-bottom: 6px;">Enlace o ID de Carpeta de Google Drive:</label>
            <input type="text" id="input-gdrive-url" placeholder="https://drive.google.com/drive/folders/1Qr6K..." value="https://drive.google.com/drive/folders/1Qr6KXPxcgdlzbSHVyDOg4cBb4GReSAfD" style="width: 100%; background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.15); border-radius: 10px; padding: 12px; color: white; font-family: monospace; font-size: 0.9rem;">
        </div>

        <button onclick="saveStorageConfig()" style="width: 100%; background: linear-gradient(135deg, #a855f7, #6366f1); border: none; border-radius: 12px; padding: 14px; color: white; font-weight: 700; font-size: 1rem; cursor: pointer; box-shadow: 0 8px 20px rgba(168,85,247,0.3);">
            🚀 Guardar e Iniciar Galería
        </button>
    </div>
</div>
"""

setup_modal_js = """
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
"""

if 'id="setup-modal"' not in html:
    pos_body = html.find('</body>')
    if pos_body != -1:
        html = html[:pos_body] + setup_modal_html + "\n" + html[pos_body:]

if 'window.openSetupModal' not in html:
    pos_script = html.rfind('</script>')
    if pos_script != -1:
        html = html[:pos_script] + setup_modal_js + "\n" + html[pos_script:]

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✓ Embedded setup-modal HTML & JS into templates/index.html!")
