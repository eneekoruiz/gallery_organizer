import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add toggle button next to 'Personas Detectadas'
old_title = '<h3>Personas Detectadas</h3>'
new_title = '''<div style="display:flex; justify-content:space-between; align-items:center; margin-top:20px;">
                    <h3 style="margin:0;">Personas Detectadas</h3>
                    <button id="btn-toggle-boxes" onclick="toggleBoxes()" style="background:var(--card-bg); border:1px solid rgba(255,255,255,0.1); color:#0a84ff; cursor:pointer; font-size:0.8rem; padding:4px 8px; border-radius:6px;">👁️ Ocultar Recuadros</button>
                </div>'''

if 'btn-toggle-boxes' not in content:
    content = content.replace(old_title, new_title, 1)

# 2. Add toggleBoxes function (if not present already from previous attempt)
toggle_js = '''
        let boxesVisible = true;
        function toggleBoxes() {
            boxesVisible = !boxesVisible;
            document.querySelectorAll('.lb-bounding-box').forEach(b => {
                b.style.opacity = boxesVisible ? '1' : '0';
                b.style.pointerEvents = boxesVisible ? 'auto' : 'none';
            });
            const btn = document.getElementById('btn-toggle-boxes');
            if (btn) btn.innerHTML = boxesVisible ? '👁️ Ocultar Recuadros' : '👁️ Mostrar Recuadros';
        }
'''
if 'function toggleBoxes()' not in content:
    content = content.replace('</script>\n</body>', toggle_js + '\n</script>\n</body>')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
    
print("Patched UI zooming and toggle successfully")
