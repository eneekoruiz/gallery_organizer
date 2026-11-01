import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_code = """
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
"""

new_code = """
        let smartCleanInterval;
        async function openIntelligentCleanup() {
            document.getElementById('gallery-title').textContent = '🧠 Limpieza Inteligente (Fáciles a Difíciles)';
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
"""

content = content.replace(old_code, new_code)
with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Replaced openIntelligentCleanup in index.html")
