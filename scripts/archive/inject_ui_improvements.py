import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Inject Auto-Merge button in Sidebar
auto_merge_html = """
<hr style="border-color: #333;">
<button onclick="startAutoMerge()" style="width: 100%; margin-bottom: 10px; background: linear-gradient(45deg, #FFD700, #FFA500); color: #000; font-weight: bold; padding: 12px; border: none; border-radius: 8px; cursor: pointer;">
    ✨ Auto-Fusión Mágica
</button>
<div id="autoMergeStatus" style="font-size: 12px; color: #aaa; text-align: center; display: none;"></div>
"""
content = content.replace('<button onclick="showMassCleanup()">Limpieza de Duplicados</button>', '<button onclick="showMassCleanup()">Limpieza de Duplicados</button>\n' + auto_merge_html)

# 2. Inject JS for Auto-Merge
auto_merge_js = """
let autoMergeInterval;
function startAutoMerge() {
    if(!confirm('Esto escaneará a todas las Personas Sin Nombre y Desconocidos, comparándolas con las caras de Conocidos y Familiares que ya has definido. ¡Las que coincidan al 85% se reasignarán automáticamente! ¿Deseas comenzar?')) return;
    
    document.getElementById('autoMergeStatus').style.display = 'block';
    document.getElementById('autoMergeStatus').innerText = 'Iniciando...';
    
    fetch('/api/auto_merge', {method: 'POST'})
    .then(r => r.json())
    .then(data => {
        if(autoMergeInterval) clearInterval(autoMergeInterval);
        autoMergeInterval = setInterval(checkAutoMergeStatus, 2000);
    });
}
function checkAutoMergeStatus() {
    fetch('/api/auto_merge_status')
    .then(r => r.json())
    .then(data => {
        const el = document.getElementById('autoMergeStatus');
        if(data.progress === 100) {
            el.innerHTML = `<span style="color:#0f0;">${data.status}</span>`;
            clearInterval(autoMergeInterval);
            setTimeout(() => { location.reload(); }, 3000);
        } else if(data.progress === -1) {
            el.innerHTML = `<span style="color:#f00;">${data.status}</span>`;
            clearInterval(autoMergeInterval);
        } else {
            el.innerHTML = `${data.status} <br><progress value="${data.progress}" max="100" style="width:100%;"></progress>`;
        }
    });
}
"""
content = content.replace('// Funciones Auxiliares', auto_merge_js + '\n// Funciones Auxiliares')

# 3. Inject "Deep Scan" Button when face detection fails
deep_scan_js = """
function triggerDeepScan() {
    if (!currentAnalysisPath) return;
    showLoading();
    fetch('/api/detect_deep', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({path: currentAnalysisPath})
    })
    .then(r => r.json())
    .then(data => {
        hideLoading();
        if (data.error) {
            alert(data.error);
        } else if (!data.faces || data.faces.length === 0) {
            alert("No se ha encontrado ninguna persona, ni siquiera con la detección profunda.");
        } else {
            alert("¡Detección profunda exitosa! Recargando imagen...");
            runAnalysis(currentAnalysisPath);
        }
    })
    .catch(err => {
        hideLoading();
        console.error(err);
    });
}
"""
content = content.replace('// Funciones Auxiliares', deep_scan_js + '\n// Funciones Auxiliares')

# Modify `runAnalysis` to show the deep scan button if 0 faces found
# Find `if (!data.faces || data.faces.length === 0)` inside runAnalysis
replacement = """
if (!data.faces || data.faces.length === 0) {
            if(confirm("No se han detectado personas en este fotograma.\\n\\n¿Deseas intentar una 🔍 Detección Profunda? (Tardará unos segundos más)")) {
                triggerDeepScan();
            }
            return;
        }
"""
content = content.replace("""if (!data.faces || data.faces.length === 0) {
            alert("No se han detectado personas en este fotograma.");
            return;
        }""", replacement)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Injected UI improvements")
