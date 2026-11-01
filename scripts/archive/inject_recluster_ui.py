import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

recluster_html = """
<button onclick="startRecluster()" style="width: 100%; margin-bottom: 10px; background: linear-gradient(45deg, #00C9FF, #92FE9D); color: #000; font-weight: bold; padding: 12px; border: none; border-radius: 8px; cursor: pointer;">
    🧩 Re-Agrupar Desconocidos
</button>
<div id="reclusterStatus" style="font-size: 12px; color: #aaa; text-align: center; display: none;"></div>
"""
content = content.replace('<div id="autoMergeStatus"', recluster_html + '\n<div id="autoMergeStatus"')

recluster_js = """
let reclusterInterval;
function startRecluster() {
    if(!confirm('Esto escaneará todas las fotos sueltas de Desconocidos y creará automáticamente nuevas "Personas Sin Nombre" agrupando a los que se parezcan. ¿Deseas comenzar?')) return;
    
    document.getElementById('reclusterStatus').style.display = 'block';
    document.getElementById('reclusterStatus').innerText = 'Iniciando...';
    
    fetch('/api/recluster_unknowns', {method: 'POST'})
    .then(r => r.json())
    .then(data => {
        if(reclusterInterval) clearInterval(reclusterInterval);
        reclusterInterval = setInterval(checkReclusterStatus, 2000);
    });
}
function checkReclusterStatus() {
    fetch('/api/recluster_status')
    .then(r => r.json())
    .then(data => {
        const el = document.getElementById('reclusterStatus');
        if(data.progress === 100) {
            el.innerHTML = `<span style="color:#0f0;">${data.status}</span>`;
            clearInterval(reclusterInterval);
            setTimeout(() => { location.reload(); }, 3000);
        } else if(data.progress === -1) {
            el.innerHTML = `<span style="color:#f00;">${data.status}</span>`;
            clearInterval(reclusterInterval);
        } else {
            el.innerHTML = `${data.status} <br><progress value="${data.progress}" max="100" style="width:100%;"></progress>`;
        }
    });
}
"""
content = content.replace('// Funciones Auxiliares', recluster_js + '\n// Funciones Auxiliares')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Injected recluster UI")
