import sys, re

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Disable "Analizar Caras en Fotograma Actual" until video is loaded
old_video_btn = '<button onclick="scanVideoCurrentFrame()" class="btn btn-primary" style="padding: 10px 20px; font-weight: 700;">🔍 Analizar Caras en Fotograma Actual</button>'
new_video_btn = '<button id="btn-scan-video" onclick="scanVideoCurrentFrame()" class="btn btn-primary" disabled style="padding: 10px 20px; font-weight: 700; opacity: 0.5;">⌛ Cargando Vídeo para Análisis...</button>'

if old_video_btn in html:
    html = html.replace(old_video_btn, new_video_btn)

# Enable button when video metadata / frame is ready
video_onloaded = """
const vElem = document.getElementById('lb-video');
if (vElem) {
    vElem.oncanplay = function() {
        const btn = document.getElementById('btn-scan-video');
        if (btn) {
            btn.disabled = false;
            btn.style.opacity = "1";
            btn.innerText = "🔍 Analizar Caras en Fotograma Actual";
        }
    };
}
"""

# 2. Add Quick Clean Mode Top Sidebar Button
quick_clean_sidebar_btn = """
<button onclick="openQuickCleanMode()" class="sidebar-btn" style="background: linear-gradient(135deg, #ef4444, #f97316); color: white; margin-bottom: 8px;">
    🔥 Modo Limpieza Rápida (Dudosos & Duplicados)
</button>
"""

quick_clean_js = """
function openQuickCleanMode() {
    loadCategoryFilter('_Dudosos', 'Desconocido');
    openQuickCleanOverlay();
}
window.openQuickCleanMode = openQuickCleanMode;
"""

if 'openQuickCleanMode' not in html:
    pos_side = html.find('<!-- Panel de Botones Principales Superior -->')
    if pos_side != -1:
        html = html[:pos_side + len('<!-- Panel de Botones Principales Superior -->')] + "\n" + quick_clean_sidebar_btn + html[pos_side + len('<!-- Panel de Botones Principales Superior -->'):]

    pos_sc = html.rfind('</script>')
    if pos_sc != -1:
        html = html[:pos_sc] + quick_clean_js + "\n" + video_onloaded + "\n" + html[pos_sc:]

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✓ Updated templates/index.html with video load check and top sidebar Quick Clean button!")
